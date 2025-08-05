"""
나비얌 챗봇 트레이너
의도 분류, 엔티티 추출 등 기본 컴포넌트 학습
"""

import numpy as np
from typing import List, Dict, Any, Tuple
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report, f1_score
from sklearn.linear_model import LogisticRegression
from sklearn.feature_extraction.text import TfidfVectorizer
import logging

from data.data_structure import NaviyamKnowledge, TrainingData, IntentType
from models.koalpaca_model import KoAlpacaModel
from nlp.preprocessor import NaviyamTextPreprocessor

logger = logging.getLogger(__name__)


class NaviyamTrainer:
    """나비얌 챗봇 트레이너"""

    def __init__(self, model: KoAlpacaModel, config):
        """
        Args:
            model: KoAlpaca 모델
            config: TrainingConfig
        """
        self.model = model
        self.config = config
        self.preprocessor = NaviyamTextPreprocessor()

        # 학습된 컴포넌트들
        self.intent_classifier = None
        self.entity_extractor = None
        self.vectorizer = None

        # 학습 통계
        self.training_history = {
            "intent_classification": {},
            "entity_extraction": {},
            "conversation_quality": {}
        }

    def train_intent_classifier(self, knowledge: NaviyamKnowledge) -> float:
        """의도 분류기 학습"""
        logger.info("의도 분류기 학습 시작...")

        # 학습 데이터 준비
        training_data = self._prepare_intent_training_data(knowledge)

        if len(training_data) == 0:
            logger.warning("의도 분류 학습 데이터가 없습니다")
            return 0.0

        # 데이터 전처리
        texts, labels = zip(*training_data)

        # 텍스트 벡터화
        self.vectorizer = TfidfVectorizer(
            max_features=1000,
            ngram_range=(1, 2),
            stop_words=None  # 한국어는 별도 처리
        )

        X = self.vectorizer.fit_transform(texts)
        y = np.array(labels)

        # 학습/검증 분할
        X_train, X_val, y_train, y_val = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )

        # 로지스틱 회귀 분류기 학습
        self.intent_classifier = LogisticRegression(
            max_iter=1000,
            random_state=42
        )

        self.intent_classifier.fit(X_train, y_train)

        # 성능 평가
        y_pred = self.intent_classifier.predict(X_val)
        accuracy = accuracy_score(y_val, y_pred)

        # 상세 리포트
        report = classification_report(y_val, y_pred, output_dict=True)

        # 학습 통계 저장
        self.training_history["intent_classification"] = {
            "accuracy": accuracy,
            "classification_report": report,
            "training_samples": len(X_train),
            "validation_samples": len(X_val)
        }

        logger.info(f"의도 분류기 학습 완료: 정확도 {accuracy:.3f}")

        return accuracy

    def _prepare_intent_training_data(self, knowledge: NaviyamKnowledge) -> List[Tuple[str, str]]:
        """의도 분류 학습 데이터 준비"""
        training_data = []

        # 기본 패턴 데이터
        intent_patterns = {
            IntentType.FOOD_REQUEST: [
                "치킨 먹고 싶어", "피자 추천해줘", "뭐 먹을까", "맛집 알려줘",
                "한식 먹고 싶어", "중식 어때", "음식 추천", "메뉴 추천해줘"
            ],
            IntentType.BUDGET_INQUIRY: [
                "만원으로 뭐 먹을까", "5천원 예산", "저렴한 곳", "가격 알려줘",
                "얼마예요", "비싸요", "싼 곳", "가성비 좋은 곳"
            ],
            IntentType.LOCATION_INQUIRY: [
                "근처 맛집", "주변 음식점", "가까운 곳", "여기서 가까운",
                "우리 동네", "인근 가게", "걸어서 갈 수 있는", "지역 맛집"
            ],
            IntentType.TIME_INQUIRY: [
                "지금 열린 곳", "몇시까지 해", "영업시간", "현재 영업중",
                "문 열어", "언제까지", "밤늦게 하는 곳", "24시간"
            ],
            IntentType.COUPON_INQUIRY: [
                "할인 쿠폰", "혜택 있나", "이벤트", "할인해줘",
                "쿠폰 써서", "공짜", "무료", "싸게 먹을 수 있는"
            ],
            IntentType.GENERAL_CHAT: [
                "안녕", "안녕하세요", "고마워", "감사해요",
                "잘 먹었어", "맛있었어", "좋았어", "어떻게 지내",
                "반가워", "하이", "헬로", "괜찮아"
            ]
        }

        # 패턴 기반 데이터 추가
        for intent, patterns in intent_patterns.items():
            for pattern in patterns:
                training_data.append((pattern, intent.value))

        # 리뷰 데이터 활용
        for review in knowledge.reviews:
            if review.get('comment'):
                # 리뷰는 일반 대화로 분류
                training_data.append((review['comment'], IntentType.GENERAL_CHAT.value))

        # 실제 메뉴 이름 기반 데이터
        for menu in list(knowledge.menus.values())[:20]:  # 상위 20개
            training_data.append((f"{menu.name} 먹고 싶어", IntentType.FOOD_REQUEST.value))
            training_data.append((f"{menu.name} 얼마예요", IntentType.BUDGET_INQUIRY.value))

        logger.info(f"의도 분류 학습 데이터 준비: {len(training_data)}개")
        return training_data

    def train_entity_extractor(self, knowledge: NaviyamKnowledge) -> float:
        """엔티티 추출기 학습 (규칙 기반)"""
        logger.info("엔티티 추출기 학습 시작...")

        # 엔티티 패턴 구축
        self._build_entity_patterns(knowledge)

        # 테스트 데이터로 성능 평가
        test_data = self._prepare_entity_test_data()

        correct_extractions = 0
        total_extractions = len(test_data)

        for test_case in test_data:
            input_text = test_case["input"]
            expected_entities = test_case["expected"]

            # 엔티티 추출 테스트
            extracted = self._extract_entities_for_evaluation(input_text)

            # 정확도 계산 (간단한 버전)
            if self._compare_entities(extracted, expected_entities):
                correct_extractions += 1

        f1 = correct_extractions / max(total_extractions, 1)

        # 학습 통계 저장
        self.training_history["entity_extraction"] = {
            "f1_score": f1,
            "test_samples": total_extractions,
            "correct_extractions": correct_extractions
        }

        logger.info(f"엔티티 추출기 학습 완료: F1 {f1:.3f}")

        return f1

    def _build_entity_patterns(self, knowledge: NaviyamKnowledge):
        """엔티티 패턴 구축"""
        # 음식 종류 패턴
        self.food_patterns = set()
        for menu in knowledge.menus.values():
            self.food_patterns.add(menu.name.lower())

        for shop in knowledge.shops.values():
            self.food_patterns.add(shop.category.lower())

        # 예산 패턴 (정규식 기반)
        self.budget_patterns = [
            r'(\d+)\s*원',
            r'(\d+)\s*천원',
            r'(\d+)\s*만원'
        ]

        # 위치 패턴
        self.location_patterns = ['근처', '주변', '가까운', '인근', '동네']

        # 동반자 패턴
        self.companion_patterns = ['친구', '가족', '혼자', '애인', '동생', '형', '누나']

    def _prepare_entity_test_data(self) -> List[Dict]:
        """엔티티 추출 테스트 데이터 준비"""
        test_data = [
            {
                "input": "치킨 먹고 싶어",
                "expected": {"food_type": "치킨"}
            },
            {
                "input": "만원으로 뭐 먹을까",
                "expected": {"budget": 10000}
            },
            {
                "input": "친구랑 근처 맛집",
                "expected": {"companions": ["친구"], "location_preference": "근처"}
            },
            {
                "input": "5천원으로 혼자 먹을 수 있는",
                "expected": {"budget": 5000, "companions": ["혼자"]}
            }
        ]

        return test_data

    def _extract_entities_for_evaluation(self, text: str) -> Dict:
        """평가용 엔티티 추출"""
        import re

        entities = {}
        text_lower = text.lower()

        # 음식 종류 추출
        for food in self.food_patterns:
            if food in text_lower:
                entities["food_type"] = food
                break

        # 예산 추출
        for pattern in self.budget_patterns:
            matches = re.findall(pattern, text)
            if matches:
                amount = int(matches[0])
                if '만원' in text:
                    amount *= 10000
                elif '천원' in text:
                    amount *= 1000
                entities["budget"] = amount
                break

        # 위치 추출
        for location in self.location_patterns:
            if location in text_lower:
                entities["location_preference"] = location
                break

        # 동반자 추출
        companions = []
        for companion in self.companion_patterns:
            if companion in text_lower:
                companions.append(companion)
        if companions:
            entities["companions"] = companions

        return entities

    def _compare_entities(self, extracted: Dict, expected: Dict) -> bool:
        """엔티티 비교 (간단한 버전)"""
        for key, expected_value in expected.items():
            if key not in extracted:
                return False

            extracted_value = extracted[key]

            if isinstance(expected_value, list):
                if not isinstance(extracted_value, list):
                    return False
                # 리스트는 교집합이 있으면 성공
                if not set(expected_value) & set(extracted_value):
                    return False
            else:
                if extracted_value != expected_value:
                    return False

        return True

    def evaluate_intent_classification(self, eval_data: List[Dict]) -> Dict[str, float]:
        """의도 분류 평가"""
        if not self.intent_classifier or not self.vectorizer:
            return {"accuracy": 0.0}

        correct = 0
        total = len(eval_data)

        for item in eval_data:
            input_text = item["input"]
            expected_intent = item["expected_intent"]

            # 벡터화
            X = self.vectorizer.transform([input_text])

            # 예측
            predicted_intent = self.intent_classifier.predict(X)[0]

            if predicted_intent == expected_intent:
                correct += 1

        accuracy = correct / max(total, 1)

        return {"accuracy": accuracy, "correct": correct, "total": total}

    def evaluate_entity_extraction(self, eval_data: List[Dict]) -> Dict[str, float]:
        """엔티티 추출 평가"""
        correct = 0
        total = 0

        for item in eval_data:
            input_text = item["input"]

            # 예상 엔티티들 확인
            expected_entities = {}
            if "expected_food" in item:
                expected_entities["food_type"] = item["expected_food"]
            if "expected_budget" in item:
                expected_entities["budget"] = item["expected_budget"]
            if "expected_companions" in item:
                expected_entities["companions"] = item["expected_companions"]

            if expected_entities:
                total += len(expected_entities)
                extracted = self._extract_entities_for_evaluation(input_text)

                for key, expected_value in expected_entities.items():
                    if key in extracted and extracted[key] == expected_value:
                        correct += 1

        f1 = correct / max(total, 1)

        return {"f1": f1, "correct": correct, "total": total}

    def evaluate_conversation_quality(self, eval_data: List[Dict]) -> float:
        """대화 품질 평가"""
        quality_scores = []

        for item in eval_data:
            input_text = item["input"]

            # 간단한 품질 지표들
            score = 0.0

            # 1. 입력 이해도 (의도 분류 신뢰도)
            if self.intent_classifier and self.vectorizer:
                X = self.vectorizer.transform([input_text])
                probabilities = self.intent_classifier.predict_proba(X)[0]
                max_prob = max(probabilities)
                score += max_prob * 0.4  # 40% 가중치

            # 2. 엔티티 추출 성공도
            extracted_entities = self._extract_entities_for_evaluation(input_text)
            entity_score = min(len(extracted_entities) * 0.2, 1.0)  # 엔티티 개수 기반
            score += entity_score * 0.3  # 30% 가중치

            # 3. 입력 텍스트 복잡도 (길이 기반 간단 계산)
            text_complexity = min(len(input_text) / 50, 1.0)
            score += text_complexity * 0.3  # 30% 가중치

            quality_scores.append(score)

        avg_quality = sum(quality_scores) / max(len(quality_scores), 1)

        # 통계 저장
        self.training_history["conversation_quality"] = {
            "avg_quality": avg_quality,
            "quality_scores": quality_scores,
            "eval_samples": len(eval_data)
        }

        return avg_quality

    def get_training_report(self) -> Dict[str, Any]:
        """학습 리포트 생성"""
        report = {
            "timestamp": "generated_at_runtime",
            "model_info": {
                "base_model": self.model.config.model_name if self.model else "Unknown",
                "quantization": "8bit" if self.model and self.model.config.use_8bit else "None"
            },
            "training_config": {
                "batch_size": self.config.batch_size,
                "learning_rate": self.config.learning_rate,
                "epochs": self.config.epochs
            },
            "performance": self.training_history,
            "component_status": {
                "intent_classifier": self.intent_classifier is not None,
                "entity_extractor": hasattr(self, 'food_patterns'),
                "vectorizer": self.vectorizer is not None
            }
        }

        return report

    def save_trained_components(self, save_path: str):
        """학습된 컴포넌트 저장"""
        import pickle
        from pathlib import Path

        save_dir = Path(save_path)
        save_dir.mkdir(parents=True, exist_ok=True)

        # 의도 분류기 저장
        if self.intent_classifier:
            with open(save_dir / "intent_classifier.pkl", "wb") as f:
                pickle.dump(self.intent_classifier, f)

        # 벡터라이저 저장
        if self.vectorizer:
            with open(save_dir / "vectorizer.pkl", "wb") as f:
                pickle.dump(self.vectorizer, f)

        # 엔티티 패턴 저장
        if hasattr(self, 'food_patterns'):
            entity_patterns = {
                'food_patterns': list(self.food_patterns),
                'budget_patterns': self.budget_patterns,
                'location_patterns': self.location_patterns,
                'companion_patterns': self.companion_patterns
            }

            with open(save_dir / "entity_patterns.pkl", "wb") as f:
                pickle.dump(entity_patterns, f)

        # 학습 히스토리 저장
        with open(save_dir / "training_history.pkl", "wb") as f:
            pickle.dump(self.training_history, f)

        logger.info(f"학습된 컴포넌트 저장 완료: {save_dir}")

    def load_trained_components(self, load_path: str):
        """학습된 컴포넌트 로드"""
        import pickle
        from pathlib import Path

        load_dir = Path(load_path)

        try:
            # 의도 분류기 로드
            classifier_file = load_dir / "intent_classifier.pkl"
            if classifier_file.exists():
                with open(classifier_file, "rb") as f:
                    self.intent_classifier = pickle.load(f)

            # 벡터라이저 로드
            vectorizer_file = load_dir / "vectorizer.pkl"
            if vectorizer_file.exists():
                with open(vectorizer_file, "rb") as f:
                    self.vectorizer = pickle.load(f)

            # 엔티티 패턴 로드
            patterns_file = load_dir / "entity_patterns.pkl"
            if patterns_file.exists():
                with open(patterns_file, "rb") as f:
                    patterns = pickle.load(f)
                    self.food_patterns = set(patterns['food_patterns'])
                    self.budget_patterns = patterns['budget_patterns']
                    self.location_patterns = patterns['location_patterns']
                    self.companion_patterns = patterns['companion_patterns']

            # 학습 히스토리 로드
            history_file = load_dir / "training_history.pkl"
            if history_file.exists():
                with open(history_file, "rb") as f:
                    self.training_history = pickle.load(f)

            logger.info(f"학습된 컴포넌트 로드 완료: {load_dir}")

        except Exception as e:
            logger.error(f"컴포넌트 로드 실패: {e}")


# 편의 함수들
def create_trainer(model: KoAlpacaModel, config) -> NaviyamTrainer:
    """트레이너 생성 (편의 함수)"""
    return NaviyamTrainer(model, config)


def quick_intent_training(knowledge: NaviyamKnowledge) -> float:
    """빠른 의도 분류기 학습 (편의 함수)"""
    from ..models.koalpaca_model import KoAlpacaModel

    # 더미 설정
    class DummyConfig:
        batch_size = 4
        learning_rate = 1e-4
        epochs = 1

    trainer = NaviyamTrainer(None, DummyConfig())
    return trainer.train_intent_classifier(knowledge)