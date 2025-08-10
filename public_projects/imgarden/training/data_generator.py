"""
나비얌 챗봇 학습 데이터 생성기
기존 데이터를 대화쌍으로 변환
"""

import random
from typing import List, Dict, Any
import logging
from datetime import datetime

from data.data_structure import (
    TrainingData, IntentType, ExtractedEntity,
    NaviyamKnowledge, NaviyamShop, NaviyamMenu
)

logger = logging.getLogger(__name__)


class NaviyamDataGenerator:
    """나비얌 학습 데이터 생성기"""

    def __init__(self, knowledge: NaviyamKnowledge):
        """
        Args:
            knowledge: 나비얌 지식베이스
        """
        self.knowledge = knowledge

        # 데이터 생성 템플릿들
        self.conversation_templates = self._build_conversation_templates()

        # 동의어 사전
        self.synonyms = self._build_synonym_dict()

        # 생성 통계
        self.generation_stats = {
            "basic_conversations": 0,
            "naviyam_specific": 0,
            "augmented_data": 0,
            "total_generated": 0
        }

    def _build_conversation_templates(self) -> Dict[str, List[Dict]]:
        """대화 템플릿 구축"""
        templates = {
            "food_request": [
                {
                    "input_patterns": ["{food} 먹고 싶어", "{food} 드시고 싶어", "{food} 추천해줘"],
                    "response_patterns": ["{food} 좋은 선택이에요! 추천해드릴게요.", "{food} 맛있겠네요! 좋은 곳 찾아드릴게요!"]
                },
                {
                    "input_patterns": ["뭐 먹을까", "무엇을 먹을까", "메뉴 추천해줘"],
                    "response_patterns": ["어떤 음식이 드시고 싶으세요?", "좋아하는 음식 종류가 있나요?"]
                }
            ],
            "budget_inquiry": [
                {
                    "input_patterns": ["{budget}원으로 뭐 먹을까", "{budget}원 예산으로", "{budget}원 이하로"],
                    "response_patterns": ["{budget}원이면 좋은 메뉴들이 많아요!", "{budget}원 예산에 맞는 곳 찾아드릴게요!"]
                }
            ],
            "location_inquiry": [
                {
                    "input_patterns": ["근처 맛집", "주변 음식점", "가까운 곳"],
                    "response_patterns": ["근처 좋은 곳들 찾아드릴게요!", "주변에 맛있는 곳들 있어요!"]
                }
            ],
            "coupon_inquiry": [
                {
                    "input_patterns": ["할인 쿠폰", "쿠폰 있어", "혜택 있나"],
                    "response_patterns": ["사용 가능한 쿠폰들 찾아드릴게요!", "좋은 혜택들이 있어요!"]
                }
            ],
            "time_inquiry": [
                {
                    "input_patterns": ["지금 열린 곳", "현재 영업중", "몇시까지 해"],
                    "response_patterns": ["지금 열린 곳들 확인해드릴게요!", "운영시간 알려드릴게요!"]
                }
            ],
            "general_chat": [
                {
                    "input_patterns": ["안녕", "안녕하세요", "하이"],
                    "response_patterns": ["안녕하세요! 맛있는 음식 찾아드릴게요!", "반가워요! 어떤 음식 드시고 싶으세요?"]
                },
                {
                    "input_patterns": ["고마워", "감사해요", "잘 먹었어"],
                    "response_patterns": ["천만에요! 맛있게 드셨다니 기뻐요!", "도움이 되어서 좋아요!"]
                }
            ]
        }

        return templates

    def _build_synonym_dict(self) -> Dict[str, List[str]]:
        """동의어 사전 구축"""
        return {
            "먹고싶어": ["드시고싶어", "먹고파", "드시고파", "땡겨", "당겨"],
            "추천해줘": ["알려줘", "소개해줘", "말해줘", "찾아줘"],
            "뭐": ["무엇을", "어떤걸", "어떤거"],
            "맛집": ["맛있는곳", "좋은곳", "괜찮은곳", "유명한곳"],
            "근처": ["주변", "가까운", "인근", "동네"],
            "할인": ["세일", "할인", "저렴", "싸게"],
            "좋아": ["괜찮아", "맘에들어", "마음에들어", "좋더라"]
        }

    def generate_basic_conversations(self, target_count: int = 200) -> List[TrainingData]:
        """기본 대화쌍 생성"""
        conversations = []

        # 음식 종류별 대화 생성
        food_types = self._extract_food_types()
        for food_type in food_types:
            conversations.extend(self._generate_food_conversations(food_type))

        # 예산별 대화 생성
        budgets = [3000, 5000, 7000, 10000, 15000, 20000]
        for budget in budgets:
            conversations.extend(self._generate_budget_conversations(budget))

        # 일반 대화 생성
        conversations.extend(self._generate_general_conversations())

        # 위치 관련 대화 생성
        conversations.extend(self._generate_location_conversations())

        # 시간 관련 대화 생성
        conversations.extend(self._generate_time_conversations())

        # 목표 개수만큼 샘플링
        if len(conversations) > target_count:
            conversations = random.sample(conversations, target_count)

        self.generation_stats["basic_conversations"] = len(conversations)
        logger.info(f"기본 대화쌍 {len(conversations)}개 생성")

        return conversations

    def _extract_food_types(self) -> List[str]:
        """지식베이스에서 음식 종류 추출"""
        food_types = set()

        # 가게 카테고리에서 추출
        for shop in self.knowledge.shops.values():
            if shop.category:
                food_types.add(shop.category)

        # 메뉴 이름에서 추출 (간단한 패턴)
        common_foods = ["치킨", "피자", "햄버거", "라면", "김치찌개", "된장찌개", "비빔밥"]
        for menu in self.knowledge.menus.values():
            for food in common_foods:
                if food in menu.name:
                    food_types.add(food)

        return list(food_types)[:10]  # 상위 10개

    def _generate_food_conversations(self, food_type: str) -> List[TrainingData]:
        """음식 종류별 대화 생성"""
        conversations = []
        templates = self.conversation_templates["food_request"]

        for template in templates:
            for input_pattern in template["input_patterns"]:
                if "{food}" in input_pattern:
                    input_text = input_pattern.format(food=food_type)
                    response_text = random.choice(template["response_patterns"]).format(food=food_type)

                    conversations.append(TrainingData(
                        input_text=input_text,
                        target_intent=IntentType.FOOD_REQUEST,
                        target_entities=ExtractedEntity(food_type=food_type),
                        expected_response=response_text,
                        domain="naviyam"
                    ))

        return conversations

    def _generate_budget_conversations(self, budget: int) -> List[TrainingData]:
        """예산별 대화 생성"""
        conversations = []
        templates = self.conversation_templates["budget_inquiry"]

        for template in templates:
            for input_pattern in template["input_patterns"]:
                input_text = input_pattern.format(budget=budget)
                response_text = random.choice(template["response_patterns"]).format(budget=budget)

                conversations.append(TrainingData(
                    input_text=input_text,
                    target_intent=IntentType.BUDGET_INQUIRY,
                    target_entities=ExtractedEntity(budget=budget),
                    expected_response=response_text,
                    domain="naviyam"
                ))

        return conversations

    def _generate_general_conversations(self) -> List[TrainingData]:
        """일반 대화 생성"""
        conversations = []
        templates = self.conversation_templates["general_chat"]

        for template in templates:
            for input_pattern in template["input_patterns"]:
                response_text = random.choice(template["response_patterns"])

                conversations.append(TrainingData(
                    input_text=input_pattern,
                    target_intent=IntentType.GENERAL_CHAT,
                    target_entities=ExtractedEntity(),
                    expected_response=response_text,
                    domain="naviyam"
                ))

        return conversations

    def _generate_location_conversations(self) -> List[TrainingData]:
        """위치 관련 대화 생성"""
        conversations = []
        templates = self.conversation_templates["location_inquiry"]

        for template in templates:
            for input_pattern in template["input_patterns"]:
                response_text = random.choice(template["response_patterns"])

                conversations.append(TrainingData(
                    input_text=input_pattern,
                    target_intent=IntentType.LOCATION_INQUIRY,
                    target_entities=ExtractedEntity(location_preference="근처"),
                    expected_response=response_text,
                    domain="naviyam"
                ))

        return conversations

    def _generate_time_conversations(self) -> List[TrainingData]:
        """시간 관련 대화 생성"""
        conversations = []
        templates = self.conversation_templates["time_inquiry"]

        for template in templates:
            for input_pattern in template["input_patterns"]:
                response_text = random.choice(template["response_patterns"])

                conversations.append(TrainingData(
                    input_text=input_pattern,
                    target_intent=IntentType.TIME_INQUIRY,
                    target_entities=ExtractedEntity(time_preference="지금"),
                    expected_response=response_text,
                    domain="naviyam"
                ))

        return conversations

    def generate_naviyam_specific_conversations(self, target_count: int = 100) -> List[TrainingData]:
        """나비얌 특화 대화쌍 생성"""
        conversations = []

        # 착한가게 관련 대화
        conversations.extend(self._generate_good_influence_conversations())

        # 실제 가게 기반 대화
        conversations.extend(self._generate_real_shop_conversations())

        # 실제 메뉴 기반 대화
        conversations.extend(self._generate_real_menu_conversations())

        # 쿠폰 관련 대화
        conversations.extend(self._generate_coupon_conversations())

        # 리뷰 기반 대화
        conversations.extend(self._generate_review_based_conversations())

        # 목표 개수 조정
        if len(conversations) > target_count:
            conversations = random.sample(conversations, target_count)

        self.generation_stats["naviyam_specific"] = len(conversations)
        logger.info(f"나비얌 특화 대화쌍 {len(conversations)}개 생성")

        return conversations

    def _generate_good_influence_conversations(self) -> List[TrainingData]:
        """착한가게 관련 대화 생성"""
        conversations = [
            TrainingData(
                input_text="착한가게 추천해줘",
                target_intent=IntentType.FOOD_REQUEST,
                target_entities=ExtractedEntity(),
                expected_response="착한가게들 추천드릴게요! 맛도 좋고 지역사회에도 도움이 되는 곳들이에요 ✨",
                domain="naviyam"
            ),
            TrainingData(
                input_text="의미있는 곳에서 먹고 싶어",
                target_intent=IntentType.FOOD_REQUEST,
                target_entities=ExtractedEntity(),
                expected_response="좋은 마음이시네요! 착한가게들로 추천드릴게요!",
                domain="naviyam"
            ),
            TrainingData(
                input_text="지역사회에 도움되는 가게",
                target_intent=IntentType.FOOD_REQUEST,
                target_entities=ExtractedEntity(),
                expected_response="착한가게들이 바로 그런 곳이에요! 찾아드릴게요!",
                domain="naviyam"
            )
        ]

        return conversations

    def _generate_real_shop_conversations(self) -> List[TrainingData]:
        """실제 가게 기반 대화 생성"""
        conversations = []

        # 상위 5개 가게로 대화 생성
        shops = list(self.knowledge.shops.values())[:5]

        for shop in shops:
            # 가게 이름 직접 언급
            conversations.append(TrainingData(
                input_text=f"{shop.name} 어때?",
                target_intent=IntentType.FOOD_REQUEST,
                target_entities=ExtractedEntity(),
                expected_response=f"{shop.name}는 {shop.category} 전문이에요! 좋은 선택이에요!",
                domain="naviyam"
            ))

            # 사장님 메시지 활용
            if shop.owner_message:
                conversations.append(TrainingData(
                    input_text=f"{shop.name} 맛있어?",
                    target_intent=IntentType.GENERAL_CHAT,
                    target_entities=ExtractedEntity(),
                    expected_response=f"사장님이 '{shop.owner_message}'라고 하시네요! 자신있어 하시는 것 같아요!",
                    domain="naviyam"
                ))

        return conversations

    def _generate_real_menu_conversations(self) -> List[TrainingData]:
        """실제 메뉴 기반 대화 생성"""
        conversations = []

        # 인기 메뉴들로 대화 생성
        popular_menus = [menu for menu in self.knowledge.menus.values() if menu.is_popular][:10]

        for menu in popular_menus:
            shop = self.knowledge.shops.get(menu.shop_id)
            if shop:
                conversations.append(TrainingData(
                    input_text=f"{menu.name} 먹고 싶어",
                    target_intent=IntentType.FOOD_REQUEST,
                    target_entities=ExtractedEntity(food_type=menu.name),
                    expected_response=f"{menu.name}는 {shop.name}에서 {menu.price}원에 드실 수 있어요! 인기 메뉴예요!",
                    domain="naviyam"
                ))

        return conversations

    def _generate_coupon_conversations(self) -> List[TrainingData]:
        """쿠폰 관련 대화 생성"""
        conversations = []

        # 실제 쿠폰 기반
        for coupon in list(self.knowledge.coupons.values())[:5]:
            conversations.append(TrainingData(
                input_text="할인 쿠폰 있어?",
                target_intent=IntentType.COUPON_INQUIRY,
                target_entities=ExtractedEntity(),
                expected_response=f"{coupon.name} 쿠폰으로 {coupon.amount}원 할인받으실 수 있어요!",
                domain="naviyam"
            ))

        return conversations

    def _generate_review_based_conversations(self) -> List[TrainingData]:
        """리뷰 기반 대화 생성"""
        conversations = []

        # 긍정 리뷰 활용
        positive_reviews = [r for r in self.knowledge.reviews if r.get('sentiment') == 'positive'][:5]

        for review in positive_reviews:
            if review.get('comment'):
                conversations.append(TrainingData(
                    input_text="이 가게 어때?",
                    target_intent=IntentType.GENERAL_CHAT,
                    target_entities=ExtractedEntity(),
                    expected_response=f"다른 분이 '{review['comment'][:30]}...'라고 하셨어요! 좋은 것 같아요!",
                    domain="naviyam"
                ))

        return conversations

    def augment_data(self, original_data: List[TrainingData], augmentation_ratio: float = 0.5) -> List[TrainingData]:
        """데이터 증강"""
        augmented = []

        # 증강할 데이터 개수 계산
        target_count = int(len(original_data) * augmentation_ratio)
        sample_data = random.sample(original_data, min(target_count, len(original_data)))

        for original in sample_data:
            # 동의어 치환
            augmented.extend(self._apply_synonym_substitution(original))

            # 문체 변경
            augmented.extend(self._apply_style_variation(original))

            # 감정 표현 추가
            augmented.extend(self._apply_emotion_variation(original))

        self.generation_stats["augmented_data"] = len(augmented)
        logger.info(f"데이터 증강 {len(augmented)}개 생성")

        return augmented

    def _apply_synonym_substitution(self, original: TrainingData) -> List[TrainingData]:
        """동의어 치환"""
        variations = []

        for word, synonyms in self.synonyms.items():
            if word in original.input_text:
                for synonym in synonyms[:2]:  # 상위 2개만
                    new_text = original.input_text.replace(word, synonym)
                    if new_text != original.input_text:
                        variations.append(TrainingData(
                            input_text=new_text,
                            target_intent=original.target_intent,
                            target_entities=original.target_entities,
                            expected_response=original.expected_response,
                            domain=original.domain
                        ))

        return variations[:2]  # 최대 2개

    def _apply_style_variation(self, original: TrainingData) -> List[TrainingData]:
        """문체 변경"""
        variations = []

        # 존댓말 <-> 반말 변환
        if "요" in original.input_text:
            casual_text = original.input_text.replace("요", "").replace("습니다", "어").replace("해요", "해")
            variations.append(TrainingData(
                input_text=casual_text,
                target_intent=original.target_intent,
                target_entities=original.target_entities,
                expected_response=original.expected_response,
                domain=original.domain
            ))
        else:
            polite_text = original.input_text.replace("해", "해요").replace("어", "어요")
            if polite_text != original.input_text:
                variations.append(TrainingData(
                    input_text=polite_text,
                    target_intent=original.target_intent,
                    target_entities=original.target_entities,
                    expected_response=original.expected_response,
                    domain=original.domain
                ))

        return variations

    def _apply_emotion_variation(self, original: TrainingData) -> List[TrainingData]:
        """감정 표현 추가"""
        variations = []

        # 긍정적 감정 표현 추가
        if original.target_intent == IntentType.FOOD_REQUEST:
            emotions = ["ㅋㅋ", "!", "~~", "^^"]
            for emotion in emotions[:2]:
                if emotion not in original.input_text:
                    new_text = original.input_text + " " + emotion
                    variations.append(TrainingData(
                        input_text=new_text,
                        target_intent=original.target_intent,
                        target_entities=original.target_entities,
                        expected_response=original.expected_response,
                        domain=original.domain
                    ))

        return variations[:1]  # 최대 1개

    def get_generation_statistics(self) -> Dict[str, Any]:
        """데이터 생성 통계"""
        total = sum(self.generation_stats.values())

        return {
            **self.generation_stats,
            "total_generated": total,
            "knowledge_base_utilization": {
                "shops_used": len(self.knowledge.shops),
                "menus_used": len(self.knowledge.menus),
                "reviews_used": len(self.knowledge.reviews),
                "coupons_used": len(self.knowledge.coupons)
            }
        }


# 편의 함수들
def generate_training_dataset(
        knowledge: NaviyamKnowledge,
        basic_count: int = 200,
        naviyam_count: int = 100,
        augmentation_ratio: float = 0.3
) -> List[TrainingData]:
    """전체 학습 데이터셋 생성 (편의 함수)"""

    generator = NaviyamDataGenerator(knowledge)

    # 기본 대화 생성
    basic_conversations = generator.generate_basic_conversations(basic_count)

    # 나비얌 특화 대화 생성
    naviyam_conversations = generator.generate_naviyam_specific_conversations(naviyam_count)

    # 전체 데이터 통합
    all_conversations = basic_conversations + naviyam_conversations

    # 데이터 증강
    augmented_data = generator.augment_data(all_conversations, augmentation_ratio)

    # 최종 데이터셋
    final_dataset = all_conversations + augmented_data

    logger.info(f"전체 학습 데이터셋 생성 완료: {len(final_dataset)}개")

    return final_dataset