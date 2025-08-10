"""
LoRA 자동 학습 스케줄러
주기적 학습 실행, 트리거 조건 관리, 백그라운드 실행을 담당
"""

import logging
import threading
import time
import queue
from typing import Dict, Any, Callable, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SchedulerConfig:
    """스케줄러 설정"""
    training_interval_hours: int = 6  # 학습 주기 (시간)
    min_samples_for_training: int = 50  # 최소 학습 샘플 수
    max_concurrent_training: int = 1  # 동시 학습 작업 수
    enable_auto_scheduling: bool = True  # 자동 스케줄링 활성화
    retry_on_failure: bool = True  # 실패 시 재시도
    max_retry_count: int = 3  # 최대 재시도 횟수


class LoRAScheduler:
    """LoRA 자동 학습 스케줄러"""
    
    def __init__(self, config: SchedulerConfig = None):
        """
        Args:
            config: 스케줄러 설정
        """
        self.config = config or SchedulerConfig()
        
        # 스케줄링 상태
        self.is_running = False
        self.last_training_time = None
        self.training_queue = queue.Queue()
        self.worker_thread = None
        
        # 통계
        self.total_training_runs = 0
        self.successful_runs = 0
        self.failed_runs = 0
        
        # 콜백 함수들
        self.data_collector_callback: Optional[Callable] = None
        self.training_callback: Optional[Callable] = None
        self.evaluation_callback: Optional[Callable] = None
        self.deployment_callback: Optional[Callable] = None
        
        logger.info("LoRAScheduler 초기화 완료")
    
    def set_callbacks(self, 
                     data_collector: Callable = None,
                     trainer: Callable = None, 
                     evaluator: Callable = None,
                     deployment_manager: Callable = None):
        """콜백 함수 설정
        
        Args:
            data_collector: 데이터 수집 함수
            trainer: 학습 실행 함수
            evaluator: 평가 실행 함수
            deployment_manager: 배포 관리 함수
        """
        self.data_collector_callback = data_collector
        self.training_callback = trainer
        self.evaluation_callback = evaluator
        self.deployment_callback = deployment_manager
        
        logger.info("콜백 함수 설정 완료")
    
    def start_auto_training(self):
        """자동 학습 시작"""
        if self.is_running:
            logger.warning("이미 자동 학습이 실행 중입니다")
            return
        
        if not self.config.enable_auto_scheduling:
            logger.info("자동 스케줄링이 비활성화되어 있습니다")
            return
        
        logger.info("자동 LoRA 학습 스케줄러 시작")
        self.is_running = True
        
        # 백그라운드 스레드 시작
        self.worker_thread = threading.Thread(target=self._auto_training_loop, daemon=True)
        self.worker_thread.start()
        
        logger.info(f"자동 학습 시작됨 (주기: {self.config.training_interval_hours}시간)")
    
    def stop_auto_training(self):
        """자동 학습 중지"""
        if not self.is_running:
            return
        
        logger.info("자동 LoRA 학습 스케줄러 중지")
        self.is_running = False
        
        # 스레드 종료 대기
        if self.worker_thread and self.worker_thread.is_alive():
            self.worker_thread.join(timeout=5.0)
        
        logger.info("자동 학습 중지됨")
    
    def _auto_training_loop(self):
        """자동 학습 루프 (백그라운드 실행)"""
        logger.info("자동 학습 루프 시작")
        
        while self.is_running:
            try:
                # 학습 트리거 조건 확인
                if self.should_trigger_training():
                    logger.info("학습 트리거 조건 만족, 자동 학습 실행")
                    
                    # 학습 작업을 큐에 추가
                    self.training_queue.put({
                        "type": "auto_training",
                        "triggered_at": datetime.now(),
                        "retry_count": 0
                    })
                    
                    # 학습 실행
                    self._process_training_queue()
                
                # 다음 확인까지 대기 (10분 간격)
                time.sleep(600)  # 10분
                
            except Exception as e:
                logger.error(f"자동 학습 루프 오류: {e}")
                time.sleep(300)  # 5분 후 재시도
        
        logger.info("자동 학습 루프 종료")
    
    def should_trigger_training(self) -> bool:
        """학습 트리거 조건 확인
        
        Returns:
            학습 실행 여부
        """
        # 1. 시간 기반 트리거
        if self.last_training_time:
            time_since_last = datetime.now() - self.last_training_time
            if time_since_last < timedelta(hours=self.config.training_interval_hours):
                return False
        else:
            # 첫 실행인 경우 바로 트리거
            return True
        
        # 2. 데이터 수집량 확인
        if self.data_collector_callback:
            try:
                recent_data_count = self.data_collector_callback()
                if recent_data_count < self.config.min_samples_for_training:
                    logger.debug(f"학습 데이터 부족: {recent_data_count} < {self.config.min_samples_for_training}")
                    return False
            except Exception as e:
                logger.warning(f"데이터 수집량 확인 실패: {e}")
                return False
        
        # 3. 동시 학습 작업 수 확인
        if not self.training_queue.empty():
            logger.debug("이미 대기 중인 학습 작업이 있습니다")
            return False
        
        logger.info("학습 트리거 조건 만족")
        return True
    
    def _process_training_queue(self):
        """학습 큐 처리"""
        while not self.training_queue.empty() and self.is_running:
            try:
                training_job = self.training_queue.get_nowait()
                self._execute_training_job(training_job)
                
            except queue.Empty:
                break
            except Exception as e:
                logger.error(f"학습 작업 처리 실패: {e}")
    
    def _execute_training_job(self, training_job: Dict[str, Any]):
        """학습 작업 실행
        
        Args:
            training_job: 학습 작업 정보
        """
        job_id = f"auto_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        logger.info(f"자동 학습 작업 시작: {job_id}")
        
        try:
            self.total_training_runs += 1
            
            # 1. 데이터 수집
            if not self.data_collector_callback:
                raise ValueError("데이터 수집 콜백이 설정되지 않았습니다")
            
            training_data = self.data_collector_callback()
            if len(training_data) < self.config.min_samples_for_training:
                raise ValueError(f"학습 데이터 부족: {len(training_data)} < {self.config.min_samples_for_training}")
            
            # 2. 모델 학습
            if not self.training_callback:
                raise ValueError("학습 콜백이 설정되지 않았습니다")
            
            adapter_name = f"auto_adapter_{job_id}"
            training_result = self.training_callback(adapter_name, training_data)
            
            # 3. 성능 평가
            if self.evaluation_callback:
                performance = self.evaluation_callback(adapter_name)
                
                # 4. 배포 결정
                if self.deployment_callback:
                    deployment_result = self.deployment_callback(adapter_name, performance)
                    training_result["deployment_result"] = deployment_result
            
            # 5. 성공 처리
            self.successful_runs += 1
            self.last_training_time = datetime.now()
            
            logger.info(f"자동 학습 작업 완료: {job_id}")
            logger.info(f"학습 결과: {training_result}")
            
        except Exception as e:
            logger.error(f"자동 학습 작업 실패: {job_id} - {e}")
            self.failed_runs += 1
            
            # 재시도 처리
            if (self.config.retry_on_failure and 
                training_job.get("retry_count", 0) < self.config.max_retry_count):
                
                training_job["retry_count"] = training_job.get("retry_count", 0) + 1
                retry_delay = 300 * training_job["retry_count"]  # 5분, 10분, 15분...
                
                logger.info(f"학습 재시도 예약: {retry_delay}초 후 ({training_job['retry_count']}/{self.config.max_retry_count})")
                
                # 재시도 작업을 별도 스레드로 예약
                retry_thread = threading.Thread(
                    target=self._schedule_retry,
                    args=(training_job, retry_delay),
                    daemon=True
                )
                retry_thread.start()
    
    def _schedule_retry(self, training_job: Dict[str, Any], delay_seconds: int):
        """재시도 작업 스케줄링"""
        time.sleep(delay_seconds)
        if self.is_running:
            self.training_queue.put(training_job)
            logger.info("재시도 작업이 큐에 추가되었습니다")
    
    def manual_trigger_training(self, adapter_name: str = None) -> bool:
        """수동 학습 트리거
        
        Args:
            adapter_name: 어댑터 이름 (None이면 자동 생성)
            
        Returns:
            학습 시작 성공 여부
        """
        if not self.is_running:
            logger.warning("스케줄러가 실행되지 않았습니다")
            return False
        
        adapter_name = adapter_name or f"manual_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        training_job = {
            "type": "manual_training",
            "adapter_name": adapter_name,
            "triggered_at": datetime.now(),
            "retry_count": 0
        }
        
        self.training_queue.put(training_job)
        logger.info(f"수동 학습 트리거: {adapter_name}")
        
        return True
    
    def get_scheduler_status(self) -> Dict[str, Any]:
        """스케줄러 상태 반환"""
        next_training_time = None
        if self.last_training_time:
            next_training_time = (self.last_training_time + 
                                timedelta(hours=self.config.training_interval_hours))
        
        return {
            "is_running": self.is_running,
            "config": {
                "training_interval_hours": self.config.training_interval_hours,
                "min_samples_for_training": self.config.min_samples_for_training,
                "enable_auto_scheduling": self.config.enable_auto_scheduling
            },
            "statistics": {
                "total_training_runs": self.total_training_runs,
                "successful_runs": self.successful_runs,
                "failed_runs": self.failed_runs,
                "success_rate": (self.successful_runs / max(self.total_training_runs, 1)) * 100
            },
            "timing": {
                "last_training_time": self.last_training_time.isoformat() if self.last_training_time else None,
                "next_training_time": next_training_time.isoformat() if next_training_time else None
            },
            "queue": {
                "pending_jobs": self.training_queue.qsize()
            }
        }