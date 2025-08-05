"""
나비얌 LoRA 배치 훈련 스케줄러
다중 훈련 작업 관리 및 시스템 리소스 최적화
"""

import asyncio
import threading
import queue
import time
import logging
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, Future
from pathlib import Path
from enum import Enum
import json

from .lora_trainer import NaviyamLoRATrainer, LoRATrainingConfig
from data.data_structure import NaviyamKnowledge, LearningData
from models.koalpaca_model import KoAlpacaModel
from inference.data_collector import LearningDataCollector

logger = logging.getLogger(__name__)

class JobStatus(Enum):
    """훈련 작업 상태"""
    PENDING = "pending"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRY = "retry"

class JobPriority(Enum):
    """훈련 작업 우선순위"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4

@dataclass
class TrainingJob:
    """훈련 작업 정의"""
    job_id: str
    job_type: str  # "auto", "manual", "user_specific", "domain_specific"
    priority: JobPriority
    config: LoRATrainingConfig
    data_filter: Dict[str, Any]  # 데이터 필터링 조건
    created_at: datetime
    scheduled_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: JobStatus = JobStatus.PENDING
    retry_count: int = 0
    max_retries: int = 3
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    progress: float = 0.0
    estimated_duration: Optional[timedelta] = None
    actual_duration: Optional[timedelta] = None
    resources_required: Dict[str, Any] = field(default_factory=dict)
    callbacks: List[Callable] = field(default_factory=list)

@dataclass
class SystemResources:
    """시스템 리소스 상태"""
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    gpu_usage: float = 0.0
    gpu_memory_usage: float = 0.0
    disk_usage: float = 0.0
    active_jobs: int = 0
    max_concurrent_jobs: int = 2
    last_updated: datetime = field(default_factory=datetime.now)

@dataclass
class SchedulerConfig:
    """스케줄러 설정"""
    max_concurrent_jobs: int = 2
    max_queue_size: int = 50
    resource_check_interval: int = 30  # 초
    job_timeout_hours: int = 8
    auto_cleanup_days: int = 7
    priority_boost_hours: int = 24  # 우선순위 자동 상승 시간
    enable_adaptive_scheduling: bool = True
    enable_resource_monitoring: bool = True
    enable_job_persistence: bool = True
    
    # 리소스 임계값
    max_cpu_usage: float = 85.0
    max_memory_usage: float = 80.0
    max_gpu_usage: float = 90.0
    min_available_disk_gb: float = 5.0

class BatchTrainingScheduler:
    """나비얌 배치 훈련 스케줄러"""
    
    def __init__(self, 
                 trainer: NaviyamLoRATrainer, 
                 config: SchedulerConfig = None):
        """
        Args:
            trainer: LoRA 훈련기
            config: 스케줄러 설정
        """
        self.trainer = trainer
        self.config = config or SchedulerConfig()
        
        # 작업 관리
        self.job_queue = queue.PriorityQueue(maxsize=self.config.max_queue_size)
        self.active_jobs = {}  # {job_id: TrainingJob}
        self.completed_jobs = {}  # {job_id: TrainingJob}
        self.job_history = []  # List[TrainingJob]
        
        # 실행기
        self.executor = ThreadPoolExecutor(max_workers=self.config.max_concurrent_jobs)
        self.running_futures = {}  # {job_id: Future}
        
        # 리소스 모니터링
        self.system_resources = SystemResources()
        self.resource_monitor_thread = None
        self.is_monitoring = False
        
        # 스케줄러 상태
        self.is_running = False
        self.scheduler_thread = None
        self.last_cleanup_time = datetime.now()
        
        # 콜백 및 이벤트
        self.job_callbacks = {
            JobStatus.STARTED: [],
            JobStatus.COMPLETED: [],
            JobStatus.FAILED: [],
            JobStatus.CANCELLED: []
        }
        
        # 지속성
        self.persistence_file = Path("./data/scheduler_state.json")
        self.persistence_file.parent.mkdir(parents=True, exist_ok=True)
        
        logger.info("배치 훈련 스케줄러 초기화 완료")
    
    def start(self):
        """스케줄러 시작"""
        if self.is_running:
            logger.warning("스케줄러가 이미 실행 중입니다")
            return
        
        self.is_running = True
        
        # 저장된 상태 복원
        if self.config.enable_job_persistence:
            self._restore_state()
        
        # 리소스 모니터링 시작
        if self.config.enable_resource_monitoring:
            self._start_resource_monitoring()
        
        # 메인 스케줄러 루프 시작
        self.scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self.scheduler_thread.start()
        
        logger.info("배치 훈련 스케줄러 시작")
    
    def stop(self):
        """스케줄러 중지"""
        if not self.is_running:
            return
        
        self.is_running = False
        self.is_monitoring = False
        
        # 실행 중인 작업들 대기
        for job_id, future in self.running_futures.items():
            logger.info(f"작업 완료 대기: {job_id}")
            try:
                future.result(timeout=30)  # 30초 대기
            except Exception as e:
                logger.warning(f"작업 {job_id} 강제 종료: {e}")
                future.cancel()
        
        # 스레드 정리
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=10)
        
        if self.resource_monitor_thread:
            self.resource_monitor_thread.join(timeout=5)
        
        # 실행기 종료
        self.executor.shutdown(wait=True)
        
        # 상태 저장
        if self.config.enable_job_persistence:
            self._save_state()
        
        logger.info("배치 훈련 스케줄러 중지")
    
    def submit_job(self, 
                   job_type: str,
                   config: LoRATrainingConfig,
                   data_filter: Dict[str, Any] = None,
                   priority: JobPriority = JobPriority.NORMAL,
                   scheduled_at: datetime = None,
                   callbacks: List[Callable] = None) -> str:
        """훈련 작업 제출"""
        
        # 작업 ID 생성
        job_id = f"{job_type}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        
        # 훈련 작업 생성
        job = TrainingJob(
            job_id=job_id,
            job_type=job_type,
            priority=priority,
            config=config,
            data_filter=data_filter or {},
            created_at=datetime.now(),
            scheduled_at=scheduled_at,
            callbacks=callbacks or []
        )
        
        # 리소스 요구사항 추정
        job.resources_required = self._estimate_job_resources(job)
        job.estimated_duration = self._estimate_job_duration(job)
        
        try:
            # 우선순위 큐에 추가 (우선순위가 높을수록 낮은 숫자)
            priority_value = -priority.value  # 역순으로 정렬
            self.job_queue.put((priority_value, job.created_at, job), timeout=1)
            
            logger.info(f"훈련 작업 제출: {job_id} (우선순위: {priority.name})")
            
            # 콜백 호출
            self._trigger_callbacks(JobStatus.PENDING, job)
            
            return job_id
            
        except queue.Full:
            logger.error(f"작업 큐가 가득참: {job_id}")
            raise RuntimeError("작업 큐가 가득참")
    
    def cancel_job(self, job_id: str) -> bool:
        """훈련 작업 취소"""
        # 실행 중인 작업 취소
        if job_id in self.running_futures:
            future = self.running_futures[job_id]
            success = future.cancel()
            
            if success:
                job = self.active_jobs.get(job_id)
                if job:
                    job.status = JobStatus.CANCELLED
                    job.completed_at = datetime.now()
                    self._move_job_to_completed(job)
                    self._trigger_callbacks(JobStatus.CANCELLED, job)
                
                logger.info(f"실행 중인 작업 취소: {job_id}")
                return True
            else:
                logger.warning(f"실행 중인 작업 취소 실패: {job_id}")
                return False
        
        # 대기 중인 작업 취소 (큐에서 제거는 복잡하므로 상태만 변경)
        # 실제 구현에서는 큐 재구성이나 다른 방법 필요
        logger.info(f"대기 중인 작업 취소 요청: {job_id}")
        return True
    
    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """작업 상태 조회"""
        # 활성 작업 확인
        if job_id in self.active_jobs:
            job = self.active_jobs[job_id]
            return self._job_to_dict(job)
        
        # 완료된 작업 확인
        if job_id in self.completed_jobs:
            job = self.completed_jobs[job_id]
            return self._job_to_dict(job)
        
        # 히스토리에서 확인
        for job in self.job_history:
            if job.job_id == job_id:
                return self._job_to_dict(job)
        
        return None
    
    def get_queue_status(self) -> Dict[str, Any]:
        """큐 상태 조회"""
        return {
            "queue_size": self.job_queue.qsize(),
            "max_queue_size": self.config.max_queue_size,
            "active_jobs": len(self.active_jobs),
            "max_concurrent_jobs": self.config.max_concurrent_jobs,
            "completed_jobs": len(self.completed_jobs),
            "system_resources": {
                "cpu_usage": self.system_resources.cpu_usage,
                "memory_usage": self.system_resources.memory_usage,
                "gpu_usage": self.system_resources.gpu_usage,
                "gpu_memory_usage": self.system_resources.gpu_memory_usage,
                "last_updated": self.system_resources.last_updated.isoformat()
            }
        }
    
    def get_job_list(self, 
                     status_filter: Optional[JobStatus] = None,
                     limit: int = 50) -> List[Dict[str, Any]]:
        """작업 목록 조회"""
        all_jobs = []
        
        # 활성 작업 추가
        all_jobs.extend(self.active_jobs.values())
        
        # 완료된 작업 추가
        all_jobs.extend(self.completed_jobs.values())
        
        # 상태 필터 적용
        if status_filter:
            all_jobs = [job for job in all_jobs if job.status == status_filter]
        
        # 생성 시간 역순 정렬
        all_jobs.sort(key=lambda x: x.created_at, reverse=True)
        
        # 제한 적용
        all_jobs = all_jobs[:limit]
        
        return [self._job_to_dict(job) for job in all_jobs]
    
    def add_job_callback(self, status: JobStatus, callback: Callable):
        """작업 상태 변경 콜백 추가"""
        if status in self.job_callbacks:
            self.job_callbacks[status].append(callback)
    
    def _scheduler_loop(self):
        """메인 스케줄러 루프"""
        logger.info("스케줄러 루프 시작")
        
        while self.is_running:
            try:
                # 리소스 상태 확인
                if self.config.enable_resource_monitoring:
                    if not self._check_system_resources():
                        time.sleep(self.config.resource_check_interval)
                        continue
                
                # 실행 가능한 작업 수 확인
                available_slots = self.config.max_concurrent_jobs - len(self.active_jobs)
                
                if available_slots <= 0:
                    time.sleep(5)  # 짧은 대기
                    continue
                
                # 완료된 작업 정리
                self._cleanup_completed_jobs()
                
                # 다음 작업 가져오기
                try:
                    priority, created_at, job = self.job_queue.get(timeout=5)
                    
                    # 스케줄된 시간 확인
                    if job.scheduled_at and datetime.now() < job.scheduled_at:
                        # 다시 큐에 넣기
                        self.job_queue.put((priority, created_at, job))
                        time.sleep(10)
                        continue
                    
                    # 작업 실행
                    self._execute_job(job)
                    
                except queue.Empty:
                    # 큐가 비어있으면 짧은 대기
                    time.sleep(2)
                    continue
                
                # 정기 정리 작업
                if datetime.now() - self.last_cleanup_time > timedelta(hours=1):
                    self._periodic_cleanup()
                    self.last_cleanup_time = datetime.now()
                
            except Exception as e:
                logger.error(f"스케줄러 루프 오류: {e}")
                time.sleep(10)  # 오류 후 긴 대기
        
        logger.info("스케줄러 루프 종료")
    
    def _execute_job(self, job: TrainingJob):
        """작업 실행"""
        try:
            # 작업 상태 업데이트
            job.status = JobStatus.RUNNING
            job.started_at = datetime.now()
            self.active_jobs[job.job_id] = job
            
            logger.info(f"훈련 작업 시작: {job.job_id}")
            self._trigger_callbacks(JobStatus.RUNNING, job)
            
            # 비동기로 실행
            future = self.executor.submit(self._run_training_job, job)
            self.running_futures[job.job_id] = future
            
            # 완료 콜백 등록
            future.add_done_callback(lambda f: self._job_completed(job.job_id, f))
            
        except Exception as e:
            logger.error(f"작업 실행 실패: {job.job_id} - {e}")
            job.status = JobStatus.FAILED
            job.error_message = str(e)
            job.completed_at = datetime.now()
            self._move_job_to_completed(job)
            self._trigger_callbacks(JobStatus.FAILED, job)
    
    def _run_training_job(self, job: TrainingJob) -> Dict[str, Any]:
        """실제 훈련 실행"""
        try:
            # 데이터 준비
            training_data = self._prepare_job_data(job)
            
            if len(training_data) < job.config.min_samples_for_training:
                raise ValueError(f"훈련 데이터 부족: {len(training_data)}")
            
            # 어댑터 이름 생성
            adapter_name = f"{job.job_type}_{job.job_id}"
            
            # LoRA 훈련 실행
            result = self.trainer.train_lora_adapter(
                adapter_name=adapter_name,
                training_data=training_data,
                save_best=True
            )
            
            # 성능 평가
            performance = self.trainer._evaluate_adapter_performance(adapter_name)
            result.update(performance)
            
            return result
            
        except Exception as e:
            logger.error(f"훈련 실행 오류: {job.job_id} - {e}")
            raise
    
    def _job_completed(self, job_id: str, future: Future):
        """작업 완료 처리"""
        job = self.active_jobs.get(job_id)
        if not job:
            return
        
        job.completed_at = datetime.now()
        job.actual_duration = job.completed_at - job.started_at
        
        try:
            # 결과 가져오기
            result = future.result()
            job.status = JobStatus.COMPLETED
            job.result = result
            job.progress = 100.0
            
            logger.info(f"훈련 작업 완료: {job_id}")
            self._trigger_callbacks(JobStatus.COMPLETED, job)
            
        except Exception as e:
            # 실패 처리
            job.status = JobStatus.FAILED
            job.error_message = str(e)
            job.retry_count += 1
            
            logger.error(f"훈련 작업 실패: {job_id} - {e}")
            
            # 재시도 여부 결정
            if job.retry_count < job.max_retries and self._should_retry_job(job, e):
                job.status = JobStatus.RETRY
                # 재시도 작업을 큐에 다시 추가
                retry_job = self._create_retry_job(job)
                priority_value = -job.priority.value
                self.job_queue.put((priority_value, retry_job.created_at, retry_job))
                logger.info(f"작업 재시도 예약: {job_id} (시도 {job.retry_count}/{job.max_retries})")
            else:
                self._trigger_callbacks(JobStatus.FAILED, job)
        
        finally:
            # 정리
            self._move_job_to_completed(job)
            if job_id in self.running_futures:
                del self.running_futures[job_id]
    
    def _prepare_job_data(self, job: TrainingJob) -> List[Dict]:
        """작업별 데이터 준비"""
        # 기본적으로는 trainer의 데이터 수집 사용
        all_data = self.trainer._collect_training_data()
        
        # 필터 적용
        if job.data_filter:
            filtered_data = []
            for data in all_data:
                if self._matches_filter(data, job.data_filter):
                    filtered_data.append(data)
            return filtered_data
        
        return all_data
    
    def _matches_filter(self, data: Dict, filter_criteria: Dict) -> bool:
        """데이터 필터링 조건 확인"""
        for key, value in filter_criteria.items():
            if key == "min_quality_score":
                if data.get("quality_score", 0) < value:
                    return False
            elif key == "max_age_days":
                data_time = data.get("timestamp", datetime.min)
                if isinstance(data_time, str):
                    data_time = datetime.fromisoformat(data_time)
                age = datetime.now() - data_time
                if age.days > value:
                    return False
            elif key == "user_types":
                if data.get("user_type") not in value:
                    return False
            elif key == "intent_types":
                if data.get("intent") not in value:
                    return False
        
        return True
    
    def _start_resource_monitoring(self):
        """리소스 모니터링 시작"""
        self.is_monitoring = True
        self.resource_monitor_thread = threading.Thread(
            target=self._resource_monitor_loop, 
            daemon=True
        )
        self.resource_monitor_thread.start()
        logger.info("리소스 모니터링 시작")
    
    def _resource_monitor_loop(self):
        """리소스 모니터링 루프"""
        import psutil
        
        while self.is_monitoring:
            try:
                # CPU 및 메모리 사용률
                self.system_resources.cpu_usage = psutil.cpu_percent(interval=1)
                self.system_resources.memory_usage = psutil.virtual_memory().percent
                self.system_resources.disk_usage = psutil.disk_usage('/').percent
                
                # GPU 사용률 (nvidia-ml-py 사용)
                try:
                    import pynvml
                    pynvml.nvmlInit()
                    handle = pynvml.nvmlDeviceGetHandleByIndex(0)
                    gpu_util = pynvml.nvmlDeviceGetUtilizationRates(handle)
                    self.system_resources.gpu_usage = gpu_util.gpu
                    
                    mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                    self.system_resources.gpu_memory_usage = (mem_info.used / mem_info.total) * 100
                except:
                    # GPU 모니터링 실패시 기본값
                    pass
                
                self.system_resources.active_jobs = len(self.active_jobs)
                self.system_resources.last_updated = datetime.now()
                
                time.sleep(self.config.resource_check_interval)
                
            except Exception as e:
                logger.warning(f"리소스 모니터링 오류: {e}")
                time.sleep(30)
    
    def _check_system_resources(self) -> bool:
        """시스템 리소스 확인"""
        resources = self.system_resources
        
        # CPU 사용률 확인
        if resources.cpu_usage > self.config.max_cpu_usage:
            logger.debug(f"CPU 사용률 높음: {resources.cpu_usage}%")
            return False
        
        # 메모리 사용률 확인
        if resources.memory_usage > self.config.max_memory_usage:
            logger.debug(f"메모리 사용률 높음: {resources.memory_usage}%")
            return False
        
        # GPU 사용률 확인
        if resources.gpu_usage > self.config.max_gpu_usage:
            logger.debug(f"GPU 사용률 높음: {resources.gpu_usage}%")
            return False
        
        return True
    
    def _estimate_job_resources(self, job: TrainingJob) -> Dict[str, Any]:
        """작업 리소스 요구사항 추정"""
        base_memory = 2.0  # GB
        base_gpu_memory = 4.0  # GB
        
        # 배치 크기에 따른 조정
        batch_multiplier = job.config.batch_size / 4
        
        # 에포크 수에 따른 조정
        epoch_multiplier = job.config.epochs / 3
        
        return {
            "estimated_memory_gb": base_memory * batch_multiplier,
            "estimated_gpu_memory_gb": base_gpu_memory * batch_multiplier,
            "estimated_cpu_cores": 2,
            "estimated_disk_gb": 1.0 * epoch_multiplier
        }
    
    def _estimate_job_duration(self, job: TrainingJob) -> timedelta:
        """작업 소요시간 추정"""
        # 기본 시간 (분)
        base_minutes = 30
        
        # 설정에 따른 조정
        batch_factor = job.config.batch_size / 4
        epoch_factor = job.config.epochs / 3
        data_factor = job.config.max_samples_per_batch / 200
        
        estimated_minutes = base_minutes * batch_factor * epoch_factor * data_factor
        
        return timedelta(minutes=max(estimated_minutes, 15))  # 최소 15분
    
    def _should_retry_job(self, job: TrainingJob, error: Exception) -> bool:
        """작업 재시도 여부 결정"""
        # 치명적인 오류는 재시도 안함
        fatal_errors = [
            "CUDA out of memory",
            "No module named",
            "ImportError",
            "ModuleNotFoundError"
        ]
        
        error_str = str(error)
        if any(fatal in error_str for fatal in fatal_errors):
            return False
        
        # 데이터 부족은 재시도 안함
        if "훈련 데이터 부족" in error_str:
            return False
        
        return True
    
    def _create_retry_job(self, original_job: TrainingJob) -> TrainingJob:
        """재시도 작업 생성"""
        retry_job = TrainingJob(
            job_id=f"{original_job.job_id}_retry_{original_job.retry_count}",
            job_type=original_job.job_type,
            priority=original_job.priority,
            config=original_job.config,
            data_filter=original_job.data_filter,
            created_at=datetime.now(),
            retry_count=original_job.retry_count,
            max_retries=original_job.max_retries,
            callbacks=original_job.callbacks
        )
        
        return retry_job
    
    def _cleanup_completed_jobs(self):
        """완료된 작업 정리"""
        current_time = datetime.now()
        jobs_to_remove = []
        
        for job_id, job in self.completed_jobs.items():
            # 완료된지 오래된 작업 제거
            if job.completed_at:
                age = current_time - job.completed_at
                if age.days > self.config.auto_cleanup_days:
                    jobs_to_remove.append(job_id)
        
        for job_id in jobs_to_remove:
            job = self.completed_jobs.pop(job_id)
            self.job_history.append(job)
            
        if jobs_to_remove:
            logger.info(f"오래된 작업 {len(jobs_to_remove)}개 정리 완료")
    
    def _periodic_cleanup(self):
        """정기 정리 작업"""
        logger.info("정기 정리 작업 시작")
        
        # 완료된 작업 정리
        self._cleanup_completed_jobs()
        
        # 실패한 Future 정리
        failed_futures = []
        for job_id, future in self.running_futures.items():
            if future.done() and future.exception():
                failed_futures.append(job_id)
        
        for job_id in failed_futures:
            del self.running_futures[job_id]
        
        # 히스토리 크기 제한
        if len(self.job_history) > 1000:
            self.job_history = self.job_history[-500:]  # 최근 500개만 유지
        
        # 상태 저장
        if self.config.enable_job_persistence:
            self._save_state()
        
        logger.info("정기 정리 작업 완료")
    
    def _move_job_to_completed(self, job: TrainingJob):
        """작업을 완료 목록으로 이동"""
        if job.job_id in self.active_jobs:
            del self.active_jobs[job.job_id]
        
        self.completed_jobs[job.job_id] = job
    
    def _trigger_callbacks(self, status: JobStatus, job: TrainingJob):
        """콜백 호출"""
        callbacks = self.job_callbacks.get(status, [])
        for callback in callbacks:
            try:
                callback(job)
            except Exception as e:
                logger.warning(f"콜백 실행 실패: {e}")
        
        # 작업별 콜백도 호출
        for callback in job.callbacks:
            try:
                callback(status, job)
            except Exception as e:
                logger.warning(f"작업 콜백 실행 실패: {e}")
    
    def _job_to_dict(self, job: TrainingJob) -> Dict[str, Any]:
        """작업을 딕셔너리로 변환"""
        return {
            "job_id": job.job_id,
            "job_type": job.job_type,
            "priority": job.priority.name,
            "status": job.status.value,
            "progress": job.progress,
            "created_at": job.created_at.isoformat(),
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "estimated_duration": str(job.estimated_duration) if job.estimated_duration else None,
            "actual_duration": str(job.actual_duration) if job.actual_duration else None,
            "retry_count": job.retry_count,
            "max_retries": job.max_retries,
            "error_message": job.error_message,
            "result": job.result
        }
    
    def _save_state(self):
        """스케줄러 상태 저장"""
        try:
            state = {
                "active_jobs": [self._job_to_dict(job) for job in self.active_jobs.values()],
                "completed_jobs": [self._job_to_dict(job) for job in self.completed_jobs.values()],
                "last_cleanup_time": self.last_cleanup_time.isoformat(),
                "system_resources": {
                    "cpu_usage": self.system_resources.cpu_usage,
                    "memory_usage": self.system_resources.memory_usage,
                    "gpu_usage": self.system_resources.gpu_usage,
                    "active_jobs": self.system_resources.active_jobs,
                    "last_updated": self.system_resources.last_updated.isoformat()
                }
            }
            
            with open(self.persistence_file, "w", encoding="utf-8") as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            logger.warning(f"상태 저장 실패: {e}")
    
    def _restore_state(self):
        """스케줄러 상태 복원"""
        try:
            if not self.persistence_file.exists():
                return
            
            with open(self.persistence_file, "r", encoding="utf-8") as f:
                state = json.load(f)
            
            # 완료된 작업만 복원 (활성 작업은 복원하지 않음)
            for job_data in state.get("completed_jobs", []):
                # TrainingJob 재구성은 복잡하므로 기본 정보만 복원
                pass
            
            logger.info("스케줄러 상태 복원 완료")
            
        except Exception as e:
            logger.warning(f"상태 복원 실패: {e}")

# 편의 함수들
def create_batch_scheduler(trainer: NaviyamLoRATrainer, 
                          config: SchedulerConfig = None) -> BatchTrainingScheduler:
    """배치 스케줄러 생성"""
    return BatchTrainingScheduler(trainer, config)

def create_default_scheduler_config() -> SchedulerConfig:
    """기본 스케줄러 설정 생성"""
    return SchedulerConfig(
        max_concurrent_jobs=2,
        max_queue_size=20,
        resource_check_interval=30,
        job_timeout_hours=4,
        auto_cleanup_days=3,
        enable_adaptive_scheduling=True,
        enable_resource_monitoring=True,
        enable_job_persistence=True
    )

def submit_auto_training_job(scheduler: BatchTrainingScheduler) -> str:
    """자동 훈련 작업 제출 (편의 함수)"""
    from .lora_trainer import LoRATrainingConfig
    
    config = LoRATrainingConfig(
        epochs=2,
        batch_size=4,
        learning_rate=1e-4,
        min_samples_for_training=30,
        auto_training_enabled=False  # 수동 작업이므로 False
    )
    
    return scheduler.submit_job(
        job_type="auto",
        config=config,
        priority=JobPriority.NORMAL
    )