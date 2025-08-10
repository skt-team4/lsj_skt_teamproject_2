"""
나비얌 LoRA 어댑터 훈련 시스템
실시간 학습 데이터 수집과 연동된 점진적 학습
"""

import torch
import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
import queue
import threading
import time

from datasets import Dataset
from transformers import TrainingArguments, Trainer, DataCollatorForLanguageModeling
from peft import LoraConfig, get_peft_model, TaskType

from data.data_structure import NaviyamKnowledge, LearningData
from models.koalpaca_model import KoAlpacaModel
from inference.data_collector import LearningDataCollector

logger = logging.getLogger(__name__)

@dataclass
class LoRATrainingConfig:
    """LoRA 훈련 설정"""
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
    
    # 데이터 수집 설정
    min_samples_for_training: int = 50
    max_samples_per_batch: int = 200
    quality_threshold: float = 0.7
    
    # 스케줄링 설정
    training_interval_hours: int = 6
    auto_training_enabled: bool = True
    max_daily_trainings: int = 4
    
    def __post_init__(self):
        if self.target_modules is None:
            # KoAlpaca 기본 타겟 모듈
            self.target_modules = ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]

class NaviyamLoRATrainer:
    """나비얌 LoRA 어댑터 훈련 시스템"""
    
    def __init__(self, model: KoAlpacaModel, config: LoRATrainingConfig, data_collector: LearningDataCollector):
        """
        Args:
            model: KoAlpaca 모델
            config: LoRA 훈련 설정
            data_collector: 학습 데이터 수집기
        """
        self.model = model
        self.config = config
        self.data_collector = data_collector
        
        # 훈련 상태
        self.is_training = False
        self.last_training_time = None
        self.training_history = []
        self.current_adapter_version = 0
        
        # 비동기 훈련 큐
        self.training_queue = queue.Queue()
        self.training_executor = ThreadPoolExecutor(max_workers=1)
        self.training_thread = None
        
        # 어댑터 관리
        self.active_adapters = {}  # {adapter_name: adapter_path}
        self.adapter_performance = {}  # {adapter_name: performance_metrics}
        
        # 저장 경로
        self.base_save_path = Path("./models/lora_adapters")
        self.base_save_path.mkdir(parents=True, exist_ok=True)
        
        logger.info("나비얌 LoRA 훈련 시스템 초기화 완료")
    
    def start_auto_training(self):
        """자동 훈련 시작"""
        if not self.config.auto_training_enabled:
            logger.info("자동 훈련이 비활성화되어 있습니다")
            return
            
        if self.training_thread and self.training_thread.is_alive():
            logger.warning("이미 자동 훈련이 실행 중입니다")
            return
            
        self.training_thread = threading.Thread(target=self._auto_training_loop, daemon=True)
        self.training_thread.start()
        logger.info("자동 LoRA 훈련 시작")
    
    def stop_auto_training(self):
        """자동 훈련 중지"""
        self.config.auto_training_enabled = False
        if self.training_thread:
            self.training_thread.join(timeout=5)
        logger.info("자동 LoRA 훈련 중지")
    
    def _auto_training_loop(self):
        """자동 훈련 루프"""
        logger.info("자동 훈련 루프 시작")
        
        while self.config.auto_training_enabled:
            try:
                # 훈련 조건 확인
                if self._should_trigger_training():
                    logger.info("훈련 조건 충족 - 자동 훈련 시작")
                    
                    # 비동기로 훈련 실행
                    future = self.training_executor.submit(self._execute_auto_training)
                    
                    # 훈련 완료까지 대기 (타임아웃 설정)
                    try:
                        result = future.result(timeout=3600)  # 1시간 타임아웃
                        logger.info(f"자동 훈련 완료: {result}")
                    except Exception as e:
                        logger.error(f"자동 훈련 실패: {e}")
                
                # 다음 체크까지 대기 (30분)
                time.sleep(1800)
                
            except Exception as e:
                logger.error(f"자동 훈련 루프 오류: {e}")
                time.sleep(300)  # 5분 후 재시도
    
    def _should_trigger_training(self) -> bool:
        """훈련 실행 조건 확인"""
        # 이미 훈련 중이면 스킵
        if self.is_training:
            return False
        
        # 일일 훈련 횟수 확인
        today = datetime.now().date()
        today_trainings = [
            t for t in self.training_history 
            if t['timestamp'].date() == today
        ]
        if len(today_trainings) >= self.config.max_daily_trainings:
            logger.info(f"일일 최대 훈련 횟수 초과: {len(today_trainings)}/{self.config.max_daily_trainings}")
            return False
        
        # 마지막 훈련 시간 확인
        if self.last_training_time:
            time_since_last = datetime.now() - self.last_training_time
            if time_since_last < timedelta(hours=self.config.training_interval_hours):
                return False
        
        # 수집된 데이터 확인
        stats = self.data_collector.get_collection_statistics()
        total_samples = stats['quality_stats']['valid_samples']
        
        if total_samples < self.config.min_samples_for_training:
            logger.debug(f"훈련 데이터 부족: {total_samples}/{self.config.min_samples_for_training}")
            return False
        
        logger.info(f"훈련 조건 충족: {total_samples}개 샘플, {time_since_last if self.last_training_time else 'first time'}")
        return True
    
    def _execute_auto_training(self) -> Dict[str, Any]:
        """자동 훈련 실행"""
        try:
            # 최신 학습 데이터 수집
            training_data = self._collect_training_data()
            
            if len(training_data) < self.config.min_samples_for_training:
                return {"status": "skipped", "reason": "insufficient_data", "samples": len(training_data)}
            
            # LoRA 어댑터 훈련
            adapter_name = f"auto_v{self.current_adapter_version}_{datetime.now().strftime('%Y%m%d_%H%M')}"
            
            result = self.train_lora_adapter(
                adapter_name=adapter_name,
                training_data=training_data,
                save_best=True
            )
            
            # 성능 평가
            performance = self._evaluate_adapter_performance(adapter_name)
            result.update(performance)
            
            # 기존 어댑터와 성능 비교
            if self._should_deploy_new_adapter(adapter_name, performance):
                self._deploy_adapter(adapter_name)
                result["deployed"] = True
            else:
                result["deployed"] = False
                logger.info(f"새 어댑터 성능 부족 - 배포 스킵: {adapter_name}")
            
            return result
            
        except Exception as e:
            logger.error(f"자동 훈련 실행 실패: {e}")
            return {"status": "failed", "error": str(e)}
    
    def train_lora_adapter(self, adapter_name: str, training_data: List[Dict], 
                          save_best: bool = True) -> Dict[str, Any]:
        """LoRA 어댑터 훈련"""
        logger.info(f"LoRA 어댑터 훈련 시작: {adapter_name} ({len(training_data)}개 샘플)")
        
        self.is_training = True
        training_start_time = datetime.now()
        
        try:
            # LoRA 설정
            lora_config = LoraConfig(
                task_type=TaskType.CAUSAL_LM,
                r=self.config.lora_r,
                lora_alpha=self.config.lora_alpha,
                lora_dropout=self.config.lora_dropout,
                target_modules=self.config.target_modules,
                bias="none",
                inference_mode=False,
            )
            
            # PEFT 모델 생성 (기존 어댑터가 있다면 제거 후 새로 생성)
            if hasattr(self.model.model, 'peft_config'):
                # 기존 어댑터 제거
                self.model.model = self.model.model.base_model.model
            
            peft_model = get_peft_model(self.model.model, lora_config)
            
            # 훈련 데이터 준비
            train_dataset, eval_dataset = self._prepare_datasets(training_data)
            
            # 훈련 설정
            training_args = self._get_training_arguments(adapter_name)
            
            # 데이터 콜레이터
            data_collator = DataCollatorForLanguageModeling(
                tokenizer=self.model.tokenizer,
                mlm=False,
                pad_to_multiple_of=8
            )
            
            # 트레이너 생성
            trainer = Trainer(
                model=peft_model,
                args=training_args,
                train_dataset=train_dataset,
                eval_dataset=eval_dataset,
                data_collator=data_collator,
                tokenizer=self.model.tokenizer,
            )
            
            # 훈련 실행
            logger.info(f"훈련 시작: {len(train_dataset)}개 학습, {len(eval_dataset)}개 검증")
            train_result = trainer.train()
            
            # 어댑터 저장
            adapter_path = self.base_save_path / adapter_name
            adapter_path.mkdir(parents=True, exist_ok=True)
            
            peft_model.save_pretrained(str(adapter_path))
            
            # 훈련 결과 저장
            training_duration = datetime.now() - training_start_time
            
            result = {
                "adapter_name": adapter_name,
                "status": "completed",
                "training_loss": train_result.training_loss,
                "training_duration_minutes": training_duration.total_seconds() / 60,
                "training_samples": len(train_dataset),
                "eval_samples": len(eval_dataset),
                "adapter_path": str(adapter_path),
                "timestamp": training_start_time
            }
            
            # 활성 어댑터 목록에 추가
            self.active_adapters[adapter_name] = str(adapter_path)
            
            # 훈련 히스토리 업데이트
            self.training_history.append(result)
            self.last_training_time = training_start_time
            self.current_adapter_version += 1
            
            # 모델에 새 어댑터 로드
            self.model.model = peft_model
            
            logger.info(f"LoRA 어댑터 훈련 완료: {adapter_name} (손실: {train_result.training_loss:.4f})")
            
            return result
            
        except Exception as e:
            logger.error(f"LoRA 어댑터 훈련 실패: {e}")
            raise
        finally:
            self.is_training = False
    
    def _collect_training_data(self) -> List[Dict]:
        """훈련용 데이터 수집"""
        logger.info("훈련 데이터 수집 시작")
        
        # 데이터 수집기에서 최신 데이터 가져오기
        all_data = self.data_collector.get_recent_data(days=7)  # 최근 7일 데이터
        
        # 품질 필터링
        quality_data = []
        for data in all_data:
            if self._is_high_quality_data(data):
                quality_data.append(data)
        
        # 최대 샘플 수 제한
        if len(quality_data) > self.config.max_samples_per_batch:
            # 최신 데이터 우선으로 샘플링
            quality_data = sorted(quality_data, key=lambda x: x.get('timestamp', datetime.min), reverse=True)
            quality_data = quality_data[:self.config.max_samples_per_batch]
        
        # 훈련 형태로 변환
        training_samples = []
        for data in quality_data:
            sample = self._convert_to_training_sample(data)
            if sample:
                training_samples.append(sample)
        
        logger.info(f"훈련 데이터 수집 완료: {len(training_samples)}개 샘플")
        return training_samples
    
    def _is_high_quality_data(self, data: Dict) -> bool:
        """데이터 품질 확인"""
        # 기본 필드 확인
        if not data.get('user_input') or not data.get('bot_response'):
            return False
        
        # 길이 확인
        if len(data['user_input']) < 3 or len(data['bot_response']) < 5:
            return False
        
        # 품질 점수 확인
        quality_score = data.get('quality_score', 0.0)
        if quality_score < self.config.quality_threshold:
            return False
        
        # 특정 패턴 제외 (오류 메시지 등)
        error_patterns = ["오류", "실패", "죄송", "모르겠"]
        bot_response = data['bot_response'].lower()
        if any(pattern in bot_response for pattern in error_patterns):
            return False
        
        return True
    
    def _convert_to_training_sample(self, data: Dict) -> Optional[Dict]:
        """데이터를 훈련 샘플로 변환"""
        try:
            user_input = data['user_input']
            bot_response = data['bot_response']
            
            # 나비얌 프롬프트 형식
            prompt_template = """당신은 나비얌, 아동을 위한 착한가게 추천 AI입니다.
친근하고 따뜻한 톤으로 음식을 추천해주세요.

사용자: {user_input}
나비얌: {bot_response}"""
            
            formatted_text = prompt_template.format(
                user_input=user_input,
                bot_response=bot_response
            )
            
            # 토크나이징
            tokens = self.model.tokenizer(
                formatted_text,
                truncation=True,
                padding=False,
                max_length=512,
                return_tensors=None
            )
            
            return {
                "input_ids": tokens["input_ids"],
                "attention_mask": tokens["attention_mask"],
                "labels": tokens["input_ids"].copy()  # Causal LM에서는 input과 label이 동일
            }
            
        except Exception as e:
            logger.warning(f"훈련 샘플 변환 실패: {e}")
            return None
    
    def _prepare_datasets(self, training_data: List[Dict]) -> Tuple[Dataset, Dataset]:
        """훈련/검증 데이터셋 준비"""
        # 토크나이징된 데이터만 필터링
        valid_data = [sample for sample in training_data if sample is not None]
        
        # 8:2 분할
        split_idx = int(len(valid_data) * 0.8)
        train_data = valid_data[:split_idx]
        eval_data = valid_data[split_idx:] if split_idx < len(valid_data) else valid_data[-5:]  # 최소 5개 평가 샘플
        
        train_dataset = Dataset.from_list(train_data)
        eval_dataset = Dataset.from_list(eval_data)
        
        return train_dataset, eval_dataset
    
    def _get_training_arguments(self, adapter_name: str) -> TrainingArguments:
        """훈련 인자 설정"""
        output_dir = self.base_save_path / f"{adapter_name}_checkpoints"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        return TrainingArguments(
            output_dir=str(output_dir),
            
            # 기본 설정
            num_train_epochs=self.config.epochs,
            per_device_train_batch_size=self.config.batch_size,
            per_device_eval_batch_size=self.config.batch_size,
            gradient_accumulation_steps=self.config.gradient_accumulation_steps,
            
            # 학습률
            learning_rate=self.config.learning_rate,
            warmup_steps=self.config.warmup_steps,
            
            # 로깅 및 저장
            logging_steps=10,
            save_steps=50,
            eval_steps=50,
            evaluation_strategy="steps",
            save_strategy="steps",
            
            # 최적화
            load_best_model_at_end=True,
            metric_for_best_model="eval_loss",
            greater_is_better=False,
            
            # 메모리 최적화
            dataloader_pin_memory=False,
            remove_unused_columns=False,
            fp16=torch.cuda.is_available(),
            
            # 기타
            seed=42,
            report_to=None,
            save_total_limit=2,
        )
    
    def _evaluate_adapter_performance(self, adapter_name: str) -> Dict[str, float]:
        """어댑터 성능 평가"""
        logger.info(f"어댑터 성능 평가: {adapter_name}")
        
        try:
            # 테스트 프롬프트
            test_prompts = [
                {"input": "치킨 먹고 싶어", "expected_keywords": ["치킨", "추천", "가게"]},
                {"input": "착한가게 알려줘", "expected_keywords": ["착한가게", "추천"]},
                {"input": "만원으로 뭐 먹을까", "expected_keywords": ["만원", "메뉴", "추천"]},
                {"input": "고마워", "expected_keywords": ["천만", "맛있게"]},
                {"input": "안녕", "expected_keywords": ["안녕", "반가", "도움"]}
            ]
            
            total_score = 0.0
            response_scores = []
            
            for prompt in test_prompts:
                try:
                    # 응답 생성
                    response = self._generate_test_response(prompt["input"])
                    
                    # 키워드 매칭 점수
                    keyword_score = self._calculate_keyword_score(response, prompt["expected_keywords"])
                    
                    # 응답 품질 점수
                    quality_score = self._calculate_response_quality(response)
                    
                    # 종합 점수
                    combined_score = (keyword_score * 0.6 + quality_score * 0.4)
                    response_scores.append(combined_score)
                    total_score += combined_score
                    
                except Exception as e:
                    logger.warning(f"테스트 프롬프트 평가 실패: {e}")
                    response_scores.append(0.0)
            
            avg_score = total_score / max(len(test_prompts), 1)
            
            performance_metrics = {
                "overall_score": avg_score,
                "individual_scores": response_scores,
                "test_count": len(test_prompts),
                "evaluation_timestamp": datetime.now().isoformat()
            }
            
            # 어댑터 성능 저장
            self.adapter_performance[adapter_name] = performance_metrics
            
            logger.info(f"어댑터 성능 평가 완료: {adapter_name} (점수: {avg_score:.3f})")
            
            return performance_metrics
            
        except Exception as e:
            logger.error(f"어댑터 성능 평가 실패: {e}")
            return {"overall_score": 0.0, "error": str(e)}
    
    def _generate_test_response(self, input_text: str) -> str:
        """테스트용 응답 생성"""
        try:
            prompt = f"사용자: {input_text}\n나비얌: "
            
            inputs = self.model.tokenizer(
                prompt,
                return_tensors="pt",
                truncation=True,
                max_length=256
            )
            
            with torch.no_grad():
                outputs = self.model.model.generate(
                    **inputs,
                    max_new_tokens=100,
                    temperature=0.7,
                    do_sample=True,
                    pad_token_id=self.model.tokenizer.eos_token_id
                )
            
            # 입력 부분 제거하고 응답만 추출
            generated = self.model.tokenizer.decode(outputs[0], skip_special_tokens=True)
            response = generated[len(prompt):].strip()
            
            return response
            
        except Exception as e:
            logger.warning(f"테스트 응답 생성 실패: {e}")
            return ""
    
    def _calculate_keyword_score(self, response: str, expected_keywords: List[str]) -> float:
        """키워드 매칭 점수 계산"""
        if not response:
            return 0.0
        
        response_lower = response.lower()
        matched_keywords = sum(1 for keyword in expected_keywords if keyword in response_lower)
        
        return matched_keywords / max(len(expected_keywords), 1)
    
    def _calculate_response_quality(self, response: str) -> float:
        """응답 품질 점수 계산"""
        if not response:
            return 0.0
        
        score = 0.0
        
        # 길이 적절성 (10-100자)
        length = len(response)
        if 10 <= length <= 100:
            score += 0.3
        elif 5 <= length <= 150:
            score += 0.2
        
        # 나비얌 특화 표현
        naviyam_keywords = ["추천", "가게", "메뉴", "착한가게", "맛있", "드릴게요", "어떠세요"]
        for keyword in naviyam_keywords:
            if keyword in response:
                score += 0.1
        
        # 이모티콘 사용
        emojis = ["😊", "🍽️", "✨", "👍", "😄"]
        if any(emoji in response for emoji in emojis):
            score += 0.1
        
        # 부정적 표현 제외
        negative_words = ["모르겠", "죄송", "실패", "오류"]
        if any(word in response for word in negative_words):
            score -= 0.2
        
        return max(0.0, min(1.0, score))
    
    def _should_deploy_new_adapter(self, adapter_name: str, performance: Dict[str, float]) -> bool:
        """새 어댑터 배포 여부 결정"""
        new_score = performance.get("overall_score", 0.0)
        
        # 최소 품질 기준
        if new_score < 0.6:
            return False
        
        # 기존 어댑터와 비교
        if not self.adapter_performance:
            return True  # 첫 번째 어댑터
        
        # 최고 성능 어댑터와 비교
        best_score = max(
            perf.get("overall_score", 0.0) 
            for perf in self.adapter_performance.values()
        )
        
        # 5% 이상 개선되어야 배포
        improvement_threshold = 0.05
        return new_score > (best_score + improvement_threshold)
    
    def _deploy_adapter(self, adapter_name: str):
        """어댑터 배포 (활성화)"""
        try:
            adapter_path = self.active_adapters.get(adapter_name)
            if not adapter_path:
                raise ValueError(f"어댑터 경로를 찾을 수 없습니다: {adapter_name}")
            
            # 현재 활성 어댑터로 설정하는 로직
            # (실제로는 모델 로딩 시스템과 연동)
            
            logger.info(f"어댑터 배포 완료: {adapter_name}")
            
            # 배포 기록
            deployment_record = {
                "adapter_name": adapter_name,
                "deployed_at": datetime.now().isoformat(),
                "performance": self.adapter_performance.get(adapter_name, {})
            }
            
            # 배포 기록 저장
            deployment_file = self.base_save_path / "deployments.jsonl"
            with open(deployment_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(deployment_record, ensure_ascii=False) + "\n")
                
        except Exception as e:
            logger.error(f"어댁터 배포 실패: {e}")
            raise
    
    def get_training_status(self) -> Dict[str, Any]:
        """훈련 상태 조회"""
        return {
            "is_training": self.is_training,
            "last_training_time": self.last_training_time.isoformat() if self.last_training_time else None,
            "current_adapter_version": self.current_adapter_version,
            "active_adapters": list(self.active_adapters.keys()),
            "training_history_count": len(self.training_history),
            "auto_training_enabled": self.config.auto_training_enabled,
            "next_training_check": self._get_next_training_time().isoformat() if self.last_training_time else "soon"
        }
    
    def _get_next_training_time(self) -> datetime:
        """다음 훈련 예정 시간"""
        if not self.last_training_time:
            return datetime.now()
        
        return self.last_training_time + timedelta(hours=self.config.training_interval_hours)
    
    def get_adapter_performance_report(self) -> Dict[str, Any]:
        """어댑터 성능 리포트"""
        if not self.adapter_performance:
            return {"message": "평가된 어댑터가 없습니다"}
        
        # 최고 성능 어댑터
        best_adapter = max(
            self.adapter_performance.items(),
            key=lambda x: x[1].get("overall_score", 0.0)
        )
        
        # 평균 성능
        avg_score = sum(
            perf.get("overall_score", 0.0) 
            for perf in self.adapter_performance.values()
        ) / len(self.adapter_performance)
        
        return {
            "total_adapters": len(self.adapter_performance),
            "best_adapter": {
                "name": best_adapter[0],
                "score": best_adapter[1].get("overall_score", 0.0)
            },
            "average_score": avg_score,
            "performance_history": [
                {
                    "adapter": name,
                    "score": perf.get("overall_score", 0.0),
                    "evaluated_at": perf.get("evaluation_timestamp")
                }
                for name, perf in self.adapter_performance.items()
            ]
        }
    
    def cleanup_old_adapters(self, keep_count: int = 5):
        """오래된 어댑터 정리"""
        if len(self.active_adapters) <= keep_count:
            return
        
        # 성능 기준으로 정렬 (낮은 성능 어댑터 제거)
        sorted_adapters = sorted(
            self.active_adapters.items(),
            key=lambda x: self.adapter_performance.get(x[0], {}).get("overall_score", 0.0),
            reverse=True
        )
        
        # 상위 어댑터만 유지
        adapters_to_keep = dict(sorted_adapters[:keep_count])
        adapters_to_remove = dict(sorted_adapters[keep_count:])
        
        # 파일 시스템에서 제거
        for adapter_name, adapter_path in adapters_to_remove.items():
            try:
                import shutil
                if Path(adapter_path).exists():
                    shutil.rmtree(adapter_path)
                logger.info(f"어댑터 제거: {adapter_name}")
            except Exception as e:
                logger.warning(f"어댑터 제거 실패 {adapter_name}: {e}")
        
        # 메모리에서 제거
        self.active_adapters = adapters_to_keep
        
        for adapter_name in adapters_to_remove:
            if adapter_name in self.adapter_performance:
                del self.adapter_performance[adapter_name]
        
        logger.info(f"어댑터 정리 완료: {len(adapters_to_remove)}개 제거, {len(adapters_to_keep)}개 유지")

# 편의 함수들
def create_lora_trainer(model: KoAlpacaModel, data_collector: LearningDataCollector, 
                       config: LoRATrainingConfig = None) -> NaviyamLoRATrainer:
    """LoRA 훈련기 생성"""
    if config is None:
        config = LoRATrainingConfig()
    
    return NaviyamLoRATrainer(model, config, data_collector)

def start_auto_lora_training(trainer: NaviyamLoRATrainer):
    """자동 LoRA 훈련 시작 (편의 함수)"""
    trainer.start_auto_training()
    return trainer.get_training_status()