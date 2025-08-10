"""
LoRA 모델 학습 담당 클래스
실제 학습 로직, 데이터셋 준비, 학습 인자 설정을 담당
"""

import torch
import logging
from typing import List, Dict, Any, Tuple
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass

from datasets import Dataset
from transformers import TrainingArguments, Trainer, DataCollatorForLanguageModeling
from peft import LoraConfig, get_peft_model, TaskType

from models.koalpaca_model import KoAlpacaModel

logger = logging.getLogger(__name__)


@dataclass
class LoRATrainingConfig:
    """LoRA 학습 설정"""
    # LoRA 하이퍼파라미터
    lora_r: int = 16
    lora_alpha: int = 32
    lora_dropout: float = 0.1
    target_modules: List[str] = None
    
    # 훈련 하이퍼파라미터
    learning_rate: float = 1e-4
    batch_size: int = 4
    gradient_accumulation_steps: int = 4
    epochs: int = 3
    warmup_steps: int = 100
    
    # 저장 설정
    output_dir: str = "./outputs/lora_adapters"
    save_steps: int = 100
    eval_steps: int = 50
    
    def __post_init__(self):
        if self.target_modules is None:
            self.target_modules = ["q_proj", "v_proj", "k_proj", "o_proj"]


class LoRATrainerCore:
    """LoRA 모델 학습 핵심 클래스"""
    
    def __init__(self, model: KoAlpacaModel, config: LoRATrainingConfig = None):
        """
        Args:
            model: 학습할 기본 모델
            config: LoRA 학습 설정
        """
        self.model = model
        self.config = config or LoRATrainingConfig()
        
        # 학습 상태
        self.is_training = False
        self.current_adapter = None
        
        logger.info("LoRATrainerCore 초기화 완료")
    
    def train_lora_adapter(self, adapter_name: str, training_data: List[Dict], 
                          validation_split: float = 0.1) -> Dict[str, Any]:
        """LoRA 어댑터 학습
        
        Args:
            adapter_name: 어댑터 이름
            training_data: 토크나이징된 학습 데이터
            validation_split: 검증 데이터 비율
            
        Returns:
            학습 결과 정보
        """
        logger.info(f"LoRA 어댑터 학습 시작: {adapter_name}")
        
        try:
            self.is_training = True
            self.current_adapter = adapter_name
            
            # 1. 데이터셋 준비
            train_dataset, eval_dataset = self.prepare_datasets(training_data, validation_split)
            
            # 2. LoRA 모델 준비
            lora_model = self._prepare_lora_model()
            
            # 3. 학습 인자 설정
            training_args = self.get_training_arguments(adapter_name)
            
            # 4. 데이터 콜레이터 설정
            data_collator = DataCollatorForLanguageModeling(
                tokenizer=self.model.tokenizer,
                mlm=False  # Causal LM이므로 MLM 비활성화
            )
            
            # 5. 트레이너 생성
            trainer = Trainer(
                model=lora_model,
                args=training_args,
                train_dataset=train_dataset,
                eval_dataset=eval_dataset,
                data_collator=data_collator,
                tokenizer=self.model.tokenizer
            )
            
            # 6. 학습 실행
            logger.info("학습 시작...")
            start_time = datetime.now()
            train_result = trainer.train()
            end_time = datetime.now()
            
            # 7. 모델 저장
            adapter_path = Path(self.config.output_dir) / adapter_name
            adapter_path.mkdir(parents=True, exist_ok=True)
            trainer.save_model(str(adapter_path))
            
            # 8. 학습 결과 정리
            training_result = {
                "adapter_name": adapter_name,
                "training_time": (end_time - start_time).total_seconds(),
                "train_loss": train_result.training_loss,
                "train_samples": len(training_data),
                "eval_samples": len(eval_dataset) if eval_dataset else 0,
                "adapter_path": str(adapter_path),
                "trained_at": end_time.isoformat()
            }
            
            # 평가 결과 추가
            if eval_dataset:
                eval_result = trainer.evaluate()
                training_result["eval_loss"] = eval_result.get("eval_loss", 0.0)
            
            logger.info(f"LoRA 어댑터 학습 완료: {adapter_name}")
            logger.info(f"학습 시간: {training_result['training_time']:.2f}초")
            logger.info(f"최종 손실: {training_result['train_loss']:.4f}")
            
            return training_result
            
        except Exception as e:
            logger.error(f"LoRA 어댑터 학습 실패: {e}")
            raise
        finally:
            self.is_training = False
            self.current_adapter = None
    
    def prepare_datasets(self, training_data: List[Dict], 
                        validation_split: float = 0.1) -> Tuple[Dataset, Dataset]:
        """훈련/검증 데이터셋 준비
        
        Args:
            training_data: 토크나이징된 학습 데이터
            validation_split: 검증 데이터 비율
            
        Returns:
            (훈련 데이터셋, 검증 데이터셋)
        """
        # 유효한 데이터만 필터링
        valid_data = [sample for sample in training_data if sample is not None]
        
        if len(valid_data) < 2:
            raise ValueError(f"학습 데이터가 부족합니다: {len(valid_data)}개")
        
        # 훈련/검증 분할
        split_idx = int(len(valid_data) * (1 - validation_split))
        train_data = valid_data[:split_idx]
        eval_data = valid_data[split_idx:] if validation_split > 0 else []
        
        # Dataset 객체 생성
        train_dataset = Dataset.from_list(train_data)
        eval_dataset = Dataset.from_list(eval_data) if eval_data else None
        
        logger.info(f"데이터셋 준비 완료 - 훈련: {len(train_data)}, 검증: {len(eval_data)}")
        
        return train_dataset, eval_dataset
    
    def _prepare_lora_model(self):
        """LoRA 모델 준비"""
        # LoRA 설정
        lora_config = LoraConfig(
            r=self.config.lora_r,
            lora_alpha=self.config.lora_alpha,
            target_modules=self.config.target_modules,
            lora_dropout=self.config.lora_dropout,
            bias="none",
            task_type=TaskType.CAUSAL_LM
        )
        
        # LoRA 모델 생성
        lora_model = get_peft_model(self.model.model, lora_config)
        
        # 학습 가능한 파라미터 확인
        trainable_params = sum(p.numel() for p in lora_model.parameters() if p.requires_grad)
        total_params = sum(p.numel() for p in lora_model.parameters())
        
        logger.info(f"LoRA 모델 준비 완료")
        logger.info(f"학습 가능 파라미터: {trainable_params:,} / {total_params:,} "
                   f"({100 * trainable_params / total_params:.2f}%)")
        
        return lora_model
    
    def get_training_arguments(self, adapter_name: str) -> TrainingArguments:
        """학습 인자 설정
        
        Args:
            adapter_name: 어댑터 이름
            
        Returns:
            학습 인자 객체
        """
        output_dir = Path(self.config.output_dir) / adapter_name
        
        training_args = TrainingArguments(
            output_dir=str(output_dir),
            num_train_epochs=self.config.epochs,
            per_device_train_batch_size=self.config.batch_size,
            per_device_eval_batch_size=self.config.batch_size,
            gradient_accumulation_steps=self.config.gradient_accumulation_steps,
            learning_rate=self.config.learning_rate,
            warmup_steps=self.config.warmup_steps,
            logging_steps=10,
            save_steps=self.config.save_steps,
            eval_steps=self.config.eval_steps,
            evaluation_strategy="steps" if self.config.eval_steps > 0 else "no",
            save_strategy="steps",
            load_best_model_at_end=True,
            metric_for_best_model="eval_loss",
            greater_is_better=False,
            save_total_limit=3,
            remove_unused_columns=False,
            dataloader_pin_memory=False,
            fp16=torch.cuda.is_available(),  # GPU 사용 시 혼합 정밀도 활성화
            report_to=[]  # wandb 등 비활성화
        )
        
        logger.info(f"학습 인자 설정 완료: {adapter_name}")
        
        return training_args
    
    def get_training_status(self) -> Dict[str, Any]:
        """현재 학습 상태 반환"""
        return {
            "is_training": self.is_training,
            "current_adapter": self.current_adapter,
            "model_loaded": self.model is not None,
            "config": {
                "lora_r": self.config.lora_r,
                "lora_alpha": self.config.lora_alpha,
                "learning_rate": self.config.learning_rate,
                "batch_size": self.config.batch_size,
                "epochs": self.config.epochs
            }
        }