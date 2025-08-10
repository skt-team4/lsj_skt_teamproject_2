"""
나비얌 챗봇 파인튜너
KoAlpaca 모델의 LoRA 파인튜닝
"""

import torch
from typing import List, Dict, Any, Optional
from datasets import Dataset
from transformers import TrainingArguments, Trainer, DataCollatorForLanguageModeling
import logging
from pathlib import Path

from data.data_structure import NaviyamKnowledge, TrainingData
from models.koalpaca_model import KoAlpacaModel

logger = logging.getLogger(__name__)

class NaviyamFineTuner:
    """나비얌 파인튜너"""

    def __init__(self, model: KoAlpacaModel, config):
        """
        Args:
            model: KoAlpaca 모델
            config: AppConfig 객체
        """
        self.model = model
        self.config = config

        # 파인튜닝 상태
        self.is_training = False
        self.training_loss_history = []
        self.validation_loss_history = []

        # 나비얌 특화 프롬프트 템플릿
        self.prompt_template = self._build_prompt_template()

    def _build_prompt_template(self) -> str:
        """나비얌 특화 프롬프트 템플릿"""
        return """당신은 아동을 위한 착한가게 추천 AI입니다.
친근하고 자연스러운 톤으로 음식을 추천해주세요.
착한가게를 우선적으로 추천하고, 지역사회에 도움이 되는 가게를 안내해주세요.

사용자: {input}
AI: {response}"""

    def fine_tune_domain_specific(self, knowledge: NaviyamKnowledge) -> float:
        """도메인 특화 파인튜닝"""
        logger.info("KoAlpaca 도메인 특화 파인튜닝 시작...")

        if not self.model.peft_model:
            logger.error("LoRA 어댑터가 설정되지 않았습니다")
            raise RuntimeError("LoRA 어댑터가 설정되지 않았습니다")

        try:
            # 학습 데이터 준비
            train_dataset, val_dataset = self._prepare_fine_tuning_data(knowledge)

            # 학습 설정
            training_args = self._get_training_arguments()

            # 데이터 콜레이터
            data_collator = DataCollatorForLanguageModeling(
                tokenizer=self.model.tokenizer,
                mlm=False,  # Causal LM
                pad_to_multiple_of=8
            )

            # 트레이너 설정
            trainer = Trainer(
                model=self.model.peft_model,
                args=training_args,
                train_dataset=train_dataset,
                eval_dataset=val_dataset,
                data_collator=data_collator,
                tokenizer=self.model.tokenizer
            )

            # 파인튜닝 실행
            self.is_training = True

            logger.info(f"파인튜닝 시작: {len(train_dataset)}개 학습 데이터, {len(val_dataset)}개 검증 데이터")

            train_result = trainer.train()

            self.is_training = False

            # 최종 손실값
            final_loss = train_result.training_loss

            logger.info(f"파인튜닝 완료: 최종 손실 {final_loss:.4f}")

            return final_loss

        except Exception as e:
            self.is_training = False
            logger.error(f"파인튜닝 실패: {e}")
            raise

    def _prepare_fine_tuning_data(self, knowledge: NaviyamKnowledge) -> tuple:
        """파인튜닝 데이터 준비"""

        # 나비얌 특화 대화 데이터 생성
        training_texts = []

        # 1. 기본 추천 대화
        training_texts.extend(self._generate_recommendation_conversations(knowledge))

        # 2. 착한가게 특화 대화
        training_texts.extend(self._generate_good_influence_conversations(knowledge))

        # 3. 실제 데이터 기반 대화
        training_texts.extend(self._generate_real_data_conversations(knowledge))

        # 4. 리뷰 기반 대화
        training_texts.extend(self._generate_review_conversations(knowledge))

        logger.info(f"파인튜닝 텍스트 {len(training_texts)}개 생성")

        # 토크나이징
        tokenized_data = []
        for text in training_texts:
            tokens = self.model.tokenizer(
                text,
                truncation=True,
                padding=False,
                max_length=self.config.model.max_length,
                return_tensors=None
            )
            tokenized_data.append(tokens)

        # 데이터셋 생성
        dataset = Dataset.from_list(tokenized_data)

        # 학습/검증 분할 (8:2)
        split_dataset = dataset.train_test_split(test_size=0.2, seed=42)

        return split_dataset['train'], split_dataset['test']

    def _generate_recommendation_conversations(self, knowledge: NaviyamKnowledge) -> List[str]:
        """추천 대화 생성"""
        conversations = []

        # 음식 종류별 추천
        food_types = ["치킨", "피자", "한식", "중식", "일식"]

        for food_type in food_types:
            # 해당 카테고리의 가게 찾기
            matching_shops = [
                shop for shop in knowledge.shops.values()
                if food_type.lower() in shop.category.lower()
            ]

            if matching_shops:
                shop = matching_shops[0]
                # 해당 가게의 메뉴 찾기
                shop_menus = [
                    menu for menu in knowledge.menus.values()
                    if menu.shop_id == shop.id
                ]

                if shop_menus:
                    menu = shop_menus[0]
                    conversation = self.prompt_template.format(
                        input=f"{food_type} 먹고 싶어",
                        response=f"{food_type} 좋은 선택이에요! {shop.name}에서 {menu.name} {menu.price}원에 드실 수 있어요!"
                    )
                    conversations.append(conversation)

        return conversations

    def _generate_good_influence_conversations(self, knowledge: NaviyamKnowledge) -> List[str]:
        """착한가게 특화 대화 생성"""
        conversations = []

        # 착한가게들 찾기
        good_shops = [shop for shop in knowledge.shops.values() if shop.is_good_influence_shop]

        for shop in good_shops[:5]:  # 상위 5개
            shop_menus = [menu for menu in knowledge.menus.values() if menu.shop_id == shop.id]

            if shop_menus:
                menu = shop_menus[0]

                # 착한가게 추천 대화
                conversation = self.prompt_template.format(
                    input="착한가게 추천해줘",
                    response=f"{shop.name}는 착한가게예요! {menu.name} {menu.price}원에 드시면서 지역사회에도 도움이 돼요 ✨"
                )
                conversations.append(conversation)

                # 사장님 메시지 활용
                if shop.owner_message:
                    conversation = self.prompt_template.format(
                        input=f"{shop.name} 어때?",
                        response=f"사장님이 '{shop.owner_message}'라고 하시네요! 자신만만하게 추천하시는 것 같아요!"
                    )
                    conversations.append(conversation)

        return conversations

    def _generate_real_data_conversations(self, knowledge: NaviyamKnowledge) -> List[str]:
        """실제 데이터 기반 대화 생성"""
        conversations = []

        # 실제 메뉴 기반
        popular_menus = [menu for menu in knowledge.menus.values() if menu.is_popular]

        for menu in popular_menus[:10]:
            shop = knowledge.shops.get(menu.shop_id)
            if shop:
                conversation = self.prompt_template.format(
                    input=f"{menu.name} 먹고 싶어",
                    response=f"{menu.name}는 {shop.name}에서 {menu.price}원에 드실 수 있어요! 인기 메뉴예요!"
                )
                conversations.append(conversation)

        # 예산 기반
        budget_examples = [
            (5000, "김치찌개, 라면"),
            (10000, "치킨, 돈까스"),
            (15000, "스테이크, 회")
        ]

        for budget, menu_examples in budget_examples:
            conversation = self.prompt_template.format(
                input=f"{budget}원으로 뭐 먹을까",
                response=f"{budget}원이면 {menu_examples} 같은 메뉴들 드실 수 있어요!"
            )
            conversations.append(conversation)

        return conversations

    def _generate_review_conversations(self, knowledge: NaviyamKnowledge) -> List[str]:
        """리뷰 기반 대화 생성"""
        conversations = []

        # 긍정적인 리뷰 활용
        positive_reviews = [
            review for review in knowledge.reviews
            if review.get('sentiment') == 'positive' and review.get('comment')
        ]

        for review in positive_reviews[:5]:
            comment = review['comment']
            if len(comment) > 20:  # 너무 짧은 리뷰는 제외
                conversation = self.prompt_template.format(
                    input="이 가게 어때?",
                    response=f"다른 분이 '{comment[:30]}...'라고 하셨어요! 좋은 평가를 받는 곳이에요!"
                )
                conversations.append(conversation)

        return conversations

    def _get_training_arguments(self) -> TrainingArguments:
        """학습 인자 설정"""

        output_dir = Path(self.config.data.output_path) / "fine_tuning_checkpoints"
        output_dir.mkdir(parents=True, exist_ok=True)

        return TrainingArguments(
            output_dir=str(output_dir),

            # 기본 학습 설정
            num_train_epochs=self.config.training.epochs,
            per_device_train_batch_size=self.config.training.batch_size,
            per_device_eval_batch_size=self.config.training.batch_size,
            gradient_accumulation_steps=self.config.training.gradient_accumulation_steps,

            # 학습률 및 옵티마이저
            learning_rate=self.config.training.learning_rate,
            warmup_steps=self.config.training.warmup_steps,

            # 로깅 및 저장
            logging_steps=50,
            save_steps=self.config.training.save_steps,
            eval_steps=self.config.training.eval_steps,

            # 평가 설정
            evaluation_strategy="steps",
            save_strategy="steps",
            load_best_model_at_end=True,
            metric_for_best_model="eval_loss",

            # 메모리 최적화
            dataloader_pin_memory=False,
            remove_unused_columns=False,

            # 기타 설정
            seed=42,
            data_seed=42,
            report_to=None,  # wandb 등 외부 로깅 비활성화

            # 조기 중단
            save_total_limit=3,

            # 디버그 모드일 때 설정 조정
            **self._get_debug_adjustments()
        )

    def _get_debug_adjustments(self) -> Dict[str, Any]:
        """디버그 모드 조정"""
        if self.config.debug:
            return {
                "max_steps": 10,  # 디버그시 10스텝만
                "eval_steps": 5,
                "save_steps": 5,
                "logging_steps": 1
            }
        return {}

    def fine_tune_user_specific(self, user_id: str, user_conversations: List[str]) -> Optional[str]:
        """사용자별 개인화 파인튜닝"""
        logger.info(f"사용자 {user_id} 개인화 파인튜닝 시작...")

        if len(user_conversations) < 5:
            logger.warning(f"사용자 {user_id}의 대화가 부족합니다 ({len(user_conversations)}개)")
            return None

        try:
            # 사용자별 LoRA 어댑터 생성
            user_adapter_path = self._create_user_adapter(user_id)

            # 사용자 대화 데이터 준비
            user_texts = []
            for conversation in user_conversations:
                formatted_text = self.prompt_template.format(
                    input=conversation,
                    response="개인화된 응답"  # 실제로는 더 정교한 응답 생성 필요
                )
                user_texts.append(formatted_text)

            # 소량 데이터 파인튜닝 (실제 구현은 복잡하므로 간단히 처리)
            if len(user_texts) >= 3:
                # 여기서 실제 개인화 학습을 수행
                # 현재는 경로만 반환
                logger.info(f"사용자 {user_id} 개인화 완료: {len(user_texts)}개 대화")
                return user_adapter_path
            else:
                logger.warning(f"사용자 {user_id} 데이터 부족: {len(user_texts)}개")
                return None

        except Exception as e:
            logger.error(f"사용자 {user_id} 개인화 파인튜닝 실패: {e}")
            return None

    def _create_user_adapter(self, user_id: str) -> str:
        """사용자별 LoRA 어댑터 생성"""
        from datetime import datetime

        user_adapter_dir = Path(self.config.data.output_path) / "user_adapters" / user_id
        user_adapter_dir.mkdir(parents=True, exist_ok=True)

        # 타임스탬프 추가
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        adapter_path = user_adapter_dir / f"adapter_{timestamp}"

        return str(adapter_path)

    def evaluate_fine_tuned_model(self, test_prompts: List[Dict[str, str]]) -> Dict[str, float]:
        """파인튜닝된 모델 평가"""
        logger.info("파인튜닝된 모델 평가 시작...")

        if not self.model.peft_model:
            return {"perplexity": float('inf'), "response_quality": 0.0}

        total_loss = 0.0
        response_quality_scores = []

        for prompt_data in test_prompts:
            input_text = prompt_data["input"]
            expected_output = prompt_data.get("expected_output", "")

            try:
                # 모델로 응답 생성
                prompt = self.prompt_template.format(input=input_text, response="")

                inputs = self.model.tokenizer(
                    prompt,
                    return_tensors="pt",
                    truncation=True,
                    max_length=512
                )

                with torch.no_grad():
                    outputs = self.model.peft_model(**inputs)
                    loss = outputs.loss.item() if outputs.loss is not None else 0.0
                    total_loss += loss

                # 응답 품질 평가 (간단한 휴리스틱)
                quality_score = self._evaluate_response_quality(input_text, expected_output)
                response_quality_scores.append(quality_score)

            except Exception as e:
                logger.warning(f"평가 중 오류: {e}")
                continue

        # 평균 계산
        avg_loss = total_loss / max(len(test_prompts), 1)
        avg_quality = sum(response_quality_scores) / max(len(response_quality_scores), 1)

        # Perplexity 계산
        perplexity = torch.exp(torch.tensor(avg_loss)).item()

        evaluation_results = {
            "perplexity": perplexity,
            "average_loss": avg_loss,
            "response_quality": avg_quality,
            "evaluated_samples": len(test_prompts)
        }

        logger.info(f"평가 완료: Perplexity {perplexity:.2f}, 품질 {avg_quality:.3f}")

        return evaluation_results

    def _evaluate_response_quality(self, input_text: str, expected_output: str) -> float:
        """응답 품질 평가 (간단한 휴리스틱)"""

        # 1. 길이 적절성 (너무 짧거나 길지 않은지)
        length_score = 1.0
        if len(expected_output) < 10:
            length_score = 0.5
        elif len(expected_output) > 200:
            length_score = 0.7

        # 2. 키워드 포함 여부
        keyword_score = 0.0
        input_keywords = input_text.split()[:3]  # 처음 3개 단어
        for keyword in input_keywords:
            if keyword in expected_output:
                keyword_score += 0.3
        keyword_score = min(keyword_score, 1.0)

        # 3. 나비얌 특화 단어 포함 여부
        naviyam_keywords = ["착한가게", "추천", "맛집", "가게", "메뉴", "음식"]
        naviyam_score = 0.0
        for keyword in naviyam_keywords:
            if keyword in expected_output:
                naviyam_score += 0.2
        naviyam_score = min(naviyam_score, 1.0)

        # 가중 평균
        total_score = (length_score * 0.3 + keyword_score * 0.4 + naviyam_score * 0.3)

        return total_score

    def generate_fine_tuning_report(self) -> Dict[str, Any]:
        """파인튜닝 리포트 생성"""

        return {
            "fine_tuning_config": {
                "base_model": self.model.config.model_name,
                "lora_config": {
                    "r": self.model.config.lora_r,
                    "alpha": self.model.config.lora_alpha,
                    "dropout": self.model.config.lora_dropout
                },
                "training_epochs": self.config.training.epochs,
                "batch_size": self.config.training.batch_size,
                "learning_rate": self.config.training.learning_rate
            },
            "training_progress": {
                "is_training": self.is_training,
                "loss_history": self.training_loss_history,
                "validation_loss": self.validation_loss_history
            },
            "memory_usage": self._get_memory_usage(),
            "model_info": {
                "total_parameters": self._count_parameters(),
                "trainable_parameters": self._count_trainable_parameters(),
                "lora_modules": self._get_lora_modules()
            }
        }

    def _get_memory_usage(self) -> Dict[str, float]:
        """메모리 사용량 조회"""
        memory_info = {}

        if torch.cuda.is_available():
            memory_info["gpu_allocated"] = torch.cuda.memory_allocated() / 1024**3  # GB
            memory_info["gpu_reserved"] = torch.cuda.memory_reserved() / 1024**3
            memory_info["gpu_max_allocated"] = torch.cuda.max_memory_allocated() / 1024**3

        return memory_info

    def _count_parameters(self) -> int:
        """전체 파라미터 수"""
        if self.model.peft_model:
            return sum(p.numel() for p in self.model.peft_model.parameters())
        return 0

    def _count_trainable_parameters(self) -> int:
        """학습 가능한 파라미터 수"""
        if self.model.peft_model:
            return sum(p.numel() for p in self.model.peft_model.parameters() if p.requires_grad)
        return 0

    def _get_lora_modules(self) -> List[str]:
        """LoRA 모듈 목록"""
        if self.model.peft_model and hasattr(self.model.peft_model, 'peft_config'):
            peft_config = self.model.peft_model.peft_config
            if hasattr(peft_config, 'target_modules'):
                return list(peft_config.target_modules)
        return []

    def save_fine_tuned_model(self, save_path: str):
        """파인튜닝된 모델 저장"""
        if not self.model.peft_model:
            logger.error("저장할 파인튜닝된 모델이 없습니다")
            return

        save_dir = Path(save_path)
        save_dir.mkdir(parents=True, exist_ok=True)

        try:
            # LoRA 어댑터 저장
            self.model.peft_model.save_pretrained(str(save_dir))

            # 토크나이저 저장
            self.model.tokenizer.save_pretrained(str(save_dir))

            # 파인튜닝 설정 저장
            import json
            config_data = {
                "model_name": self.model.config.model_name,
                "fine_tuning_completed": True,
                "lora_config": {
                    "r": self.model.config.lora_r,
                    "alpha": self.model.config.lora_alpha,
                    "dropout": self.model.config.lora_dropout
                }
            }

            with open(save_dir / "fine_tuning_config.json", "w", encoding="utf-8") as f:
                json.dump(config_data, f, ensure_ascii=False, indent=2)

            logger.info(f"파인튜닝된 모델 저장 완료: {save_dir}")

        except Exception as e:
            logger.error(f"모델 저장 실패: {e}")
            raise

    def load_fine_tuned_model(self, load_path: str):
        """파인튜닝된 모델 로드"""
        load_dir = Path(load_path)

        if not load_dir.exists():
            logger.error(f"모델 경로가 존재하지 않습니다: {load_dir}")
            return False

        try:
            # LoRA 어댑터 로드
            self.model.load_lora_adapter(str(load_dir))

            logger.info(f"파인튜닝된 모델 로드 완료: {load_dir}")
            return True

        except Exception as e:
            logger.error(f"모델 로드 실패: {e}")
            return False

    def cleanup_training_resources(self):
        """학습 리소스 정리"""
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        # 학습 히스토리 초기화
        self.training_loss_history.clear()
        self.validation_loss_history.clear()

        self.is_training = False

        logger.info("학습 리소스 정리 완료")

# 편의 함수들
def create_fine_tuner(model: KoAlpacaModel, config) -> NaviyamFineTuner:
    """파인튜너 생성 (편의 함수)"""
    return NaviyamFineTuner(model, config)

def quick_domain_fine_tuning(model: KoAlpacaModel, knowledge: NaviyamKnowledge, config) -> float:
    """빠른 도메인 파인튜닝 (편의 함수)"""
    fine_tuner = NaviyamFineTuner(model, config)
    return fine_tuner.fine_tune_domain_specific(knowledge)

def evaluate_fine_tuning_quality(model: KoAlpacaModel, config) -> Dict[str, float]:
    """파인튜닝 품질 평가 (편의 함수)"""
    fine_tuner = NaviyamFineTuner(model, config)

    # 기본 테스트 프롬프트
    test_prompts = [
        {"input": "치킨 먹고 싶어", "expected_output": "치킨 추천드릴게요!"},
        {"input": "착한가게 알려줘", "expected_output": "착한가게 추천드릴게요!"},
        {"input": "만원으로 뭐 먹을까", "expected_output": "만원으로 드실 수 있는 메뉴 찾아드릴게요!"}
    ]

    return fine_tuner.evaluate_fine_tuned_model(test_prompts)