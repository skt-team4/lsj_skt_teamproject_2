"""
리팩토링된 LoRA 학습 시스템 통합 컨트롤러

기존의 NaviyamLoRATrainer와 동일한 인터페이스를 제공하면서
내부적으로는 분리된 컴포넌트들을 조합하여 사용합니다.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass

from models.koalpaca_model import KoAlpacaModel
from inference.data_collector import LearningDataCollector

# 새로 생성된 컴포넌트들
from .lora_data_manager import LoRADataManager, DataQualityConfig
from .lora_trainer_core import LoRATrainerCore, LoRATrainingConfig
from .lora_evaluator import LoRAEvaluator
from .lora_scheduler import LoRAScheduler, SchedulerConfig
from .lora_deployment_manager import LoRADeploymentManager

logger = logging.getLogger(__name__)


@dataclass
class RefactoredLoRAConfig:
    """리팩토링된 LoRA 시스템 전체 설정"""
    # 기존 설정 호환성
    lora_r: int = 16
    lora_alpha: int = 32
    lora_dropout: float = 0.1
    target_modules: List[str] = None
    learning_rate: float = 1e-4
    batch_size: int = 4
    gradient_accumulation_steps: int = 4
    epochs: int = 3
    warmup_steps: int = 100
    
    # 데이터 관련
    min_samples_for_training: int = 50
    max_samples_per_batch: int = 200
    quality_threshold: float = 0.7
    
    # 스케줄링 관련
    training_interval_hours: int = 6
    enable_auto_scheduling: bool = True
    
    # 배포 관련
    deployment_threshold: float = 0.7
    keep_adapter_count: int = 5
    
    def __post_init__(self):
        if self.target_modules is None:
            self.target_modules = ["q_proj", "v_proj", "k_proj", "o_proj"]


class NaviyamLoRATrainerRefactored:
    """리팩토링된 나비얌 LoRA 학습 시스템
    
    기존 NaviyamLoRATrainer와 동일한 인터페이스를 제공하면서
    내부적으로는 책임별로 분리된 컴포넌트들을 사용합니다.
    """
    
    def __init__(self, model: KoAlpacaModel, config: RefactoredLoRAConfig, 
                 data_collector: LearningDataCollector):
        """
        Args:
            model: 기본 모델
            config: 전체 설정
            data_collector: 데이터 수집기
        """
        self.model = model
        self.config = config
        self.data_collector = data_collector
        
        # 분리된 컴포넌트들 초기화
        self._initialize_components()
        
        # 기존 호환성을 위한 상태 변수들
        self.is_training = False
        self.auto_training_enabled = False
        
        logger.info("NaviyamLoRATrainerRefactored 초기화 완료")
    
    def _initialize_components(self):
        """컴포넌트들 초기화"""
        # 1. 데이터 관리자
        data_quality_config = DataQualityConfig(
            min_input_length=3,
            min_response_length=5,
            quality_threshold=self.config.quality_threshold,
            max_samples_per_batch=self.config.max_samples_per_batch
        )
        self.data_manager = LoRADataManager(self.data_collector, data_quality_config)
        
        # 2. 학습 코어
        training_config = LoRATrainingConfig(
            lora_r=self.config.lora_r,
            lora_alpha=self.config.lora_alpha,
            lora_dropout=self.config.lora_dropout,
            target_modules=self.config.target_modules,
            learning_rate=self.config.learning_rate,
            batch_size=self.config.batch_size,
            gradient_accumulation_steps=self.config.gradient_accumulation_steps,
            epochs=self.config.epochs,
            warmup_steps=self.config.warmup_steps
        )
        self.trainer_core = LoRATrainerCore(self.model, training_config)
        
        # 3. 평가기
        self.evaluator = LoRAEvaluator(self.model)
        
        # 4. 스케줄러
        scheduler_config = SchedulerConfig(
            training_interval_hours=self.config.training_interval_hours,
            min_samples_for_training=self.config.min_samples_for_training,
            enable_auto_scheduling=self.config.enable_auto_scheduling
        )
        self.scheduler = LoRAScheduler(scheduler_config)
        
        # 5. 배포 관리자
        self.deployment_manager = LoRADeploymentManager()
        
        # 6. 스케줄러 콜백 설정
        self._setup_scheduler_callbacks()
        
        logger.info("모든 컴포넌트 초기화 완료")
    
    def _setup_scheduler_callbacks(self):
        """스케줄러 콜백 함수 설정"""
        self.scheduler.set_callbacks(
            data_collector=self._callback_collect_data,
            trainer=self._callback_train_adapter,
            evaluator=self._callback_evaluate_adapter,
            deployment_manager=self._callback_deploy_adapter
        )
    
    def _callback_collect_data(self) -> List[Dict]:
        """스케줄러용 데이터 수집 콜백"""
        training_data = self.data_manager.collect_training_data()
        return self.data_manager.convert_to_training_samples(
            training_data, self.model.tokenizer
        )
    
    def _callback_train_adapter(self, adapter_name: str, training_data: List[Dict]) -> Dict[str, Any]:
        """스케줄러용 학습 콜백"""
        return self.trainer_core.train_lora_adapter(adapter_name, training_data)
    
    def _callback_evaluate_adapter(self, adapter_name: str) -> Dict[str, float]:
        """스케줄러용 평가 콜백"""
        return self.evaluator.evaluate_adapter_performance(adapter_name)
    
    def _callback_deploy_adapter(self, adapter_name: str, performance: Dict[str, float]) -> Dict[str, Any]:
        """스케줄러용 배포 콜백"""
        should_deploy = self.evaluator.should_deploy_adapter(
            adapter_name, performance, self.config.deployment_threshold
        )
        
        if should_deploy:
            return self.deployment_manager.deploy_adapter(adapter_name, performance)
        else:
            return {
                "success": False, 
                "reason": "성능 기준 미달성",
                "adapter_name": adapter_name
            }
    
    # =============================================================================
    # 기존 인터페이스 호환성 메서드들
    # =============================================================================
    
    def start_auto_training(self):
        """자동 학습 시작 (기존 인터페이스 호환)"""
        self.auto_training_enabled = True
        self.scheduler.start_auto_training()
        logger.info("자동 학습 시작됨")
    
    def stop_auto_training(self):
        """자동 학습 중지 (기존 인터페이스 호환)"""
        self.auto_training_enabled = False
        self.scheduler.stop_auto_training()
        logger.info("자동 학습 중지됨")
    
    def train_lora_adapter(self, adapter_name: str, training_data: List[Dict], 
                          validation_split: float = 0.1) -> Dict[str, Any]:
        """LoRA 어댑터 학습 (기존 인터페이스 호환)
        
        이 메서드는 기존 코드와의 호환성을 위해 유지됩니다.
        내부적으로는 분리된 컴포넌트들을 사용합니다.
        """
        logger.info(f"LoRA 어댑터 학습 시작: {adapter_name}")
        
        try:
            self.is_training = True
            
            # 1. 데이터 준비 (이미 토크나이징된 데이터라고 가정)
            if not training_data:
                # 데이터가 없으면 새로 수집
                raw_data = self.data_manager.collect_training_data()
                training_data = self.data_manager.convert_to_training_samples(
                    raw_data, self.model.tokenizer
                )
            
            # 2. 학습 실행
            training_result = self.trainer_core.train_lora_adapter(
                adapter_name, training_data, validation_split
            )
            
            # 3. 성능 평가
            performance = self.evaluator.evaluate_adapter_performance(adapter_name)
            training_result["performance"] = performance
            
            # 4. 배포 결정
            deployment_result = self._callback_deploy_adapter(adapter_name, performance)
            training_result["deployment"] = deployment_result
            
            logger.info(f"LoRA 어댑터 학습 완료: {adapter_name}")
            return training_result
            
        except Exception as e:
            logger.error(f"LoRA 어댑터 학습 실패: {e}")
            raise
        finally:
            self.is_training = False
    
    def get_training_status(self) -> Dict[str, Any]:
        """훈련 상태 조회 (기존 인터페이스 호환)"""
        trainer_status = self.trainer_core.get_training_status()
        scheduler_status = self.scheduler.get_scheduler_status()
        production_info = self.deployment_manager.get_current_production_info()
        
        return {
            "is_training": trainer_status["is_training"],
            "auto_training_enabled": self.auto_training_enabled,
            "current_adapter": trainer_status["current_adapter"],
            "scheduler": scheduler_status,
            "production": production_info,
            "components": {
                "data_manager": "initialized",
                "trainer_core": "initialized", 
                "evaluator": "initialized",
                "scheduler": "initialized",
                "deployment_manager": "initialized"
            }
        }
    
    def get_adapter_performance_report(self) -> Dict[str, Any]:
        """어댑터 성능 리포트 (기존 인터페이스 호환)"""
        deployment_history = self.deployment_manager.get_deployment_history(limit=5)
        current_production = self.deployment_manager.get_current_production_info()
        
        return {
            "current_production": current_production,
            "recent_deployments": deployment_history,
            "total_deployments": len(deployment_history),
            "scheduler_stats": self.scheduler.get_scheduler_status()["statistics"]
        }
    
    def cleanup_old_adapters(self, keep_count: int = None):
        """오래된 어댑터 정리 (기존 인터페이스 호환)"""
        keep_count = keep_count or self.config.keep_adapter_count
        return self.deployment_manager.cleanup_old_adapters(keep_count)
    
    # =============================================================================
    # 새로운 고급 기능들 (리팩토링의 장점 활용)
    # =============================================================================
    
    def manual_trigger_training(self, adapter_name: str = None) -> bool:
        """수동 학습 트리거"""
        return self.scheduler.manual_trigger_training(adapter_name)
    
    def rollback_adapter(self, target_adapter: str = None) -> Dict[str, Any]:
        """어댑터 롤백"""
        return self.deployment_manager.rollback_adapter(target_adapter)
    
    def get_data_statistics(self) -> Dict[str, Any]:
        """데이터 통계 정보"""
        recent_data = self.data_manager.collect_training_data()
        return self.data_manager.get_data_statistics(recent_data)
    
    def compare_adapter_performance(self, adapter_names: List[str]) -> str:
        """여러 어댑터 성능 비교"""
        performances = {}
        for adapter_name in adapter_names:
            try:
                performance = self.evaluator.evaluate_adapter_performance(adapter_name)
                performances[adapter_name] = performance
            except Exception as e:
                logger.warning(f"어댑터 평가 실패: {adapter_name} - {e}")
        
        return self.evaluator.compare_adapters(performances)
    
    def force_deploy_adapter(self, adapter_name: str) -> Dict[str, Any]:
        """강제 어댑터 배포"""
        # 성능 평가 없이 강제 배포
        dummy_performance = {"overall_score": 1.0}  # 강제 배포용 더미 성능
        return self.deployment_manager.deploy_adapter(
            adapter_name, dummy_performance, force_deploy=True
        )


# =============================================================================
# 기존 코드 호환성을 위한 팩토리 함수들
# =============================================================================

def create_lora_trainer(model: KoAlpacaModel, data_collector: LearningDataCollector, 
                       config_dict: Dict[str, Any] = None) -> NaviyamLoRATrainerRefactored:
    """리팩토링된 LoRA 트레이너 생성 (기존 인터페이스 호환)"""
    
    # 기존 설정을 새 설정으로 변환
    if config_dict is None:
        config_dict = {}
    
    config = RefactoredLoRAConfig(
        lora_r=config_dict.get('lora_r', 16),
        lora_alpha=config_dict.get('lora_alpha', 32),
        lora_dropout=config_dict.get('lora_dropout', 0.1),
        learning_rate=config_dict.get('learning_rate', 1e-4),
        batch_size=config_dict.get('batch_size', 4),
        epochs=config_dict.get('epochs', 3),
        min_samples_for_training=config_dict.get('min_samples_for_training', 50),
        training_interval_hours=config_dict.get('training_interval_hours', 6)
    )
    
    return NaviyamLoRATrainerRefactored(model, config, data_collector)


def start_auto_lora_training(trainer: NaviyamLoRATrainerRefactored):
    """자동 LoRA 학습 시작 (기존 인터페이스 호환)"""
    trainer.start_auto_training()
    logger.info("리팩토링된 자동 LoRA 학습 시작됨")