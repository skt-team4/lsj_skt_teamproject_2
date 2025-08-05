"""
텍스트 전처리 모듈
아동 친화적 표현 보존하면서 정제
"""

import re
import string
from typing import List, Dict, Optional, Tuple
import logging
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class EmotionType(Enum):
    """감정 타입"""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    EXCITED = "excited"  # 신남, 기대
    DISAPPOINTED = "disappointed"  # 실망


@dataclass
class PreprocessResult:
    """전처리 결과"""
    original_text: str  # 원본 텍스트
    cleaned_text: str  # 정제된 텍스트
    normalized_text: str  # 정규화된 텍스트
    extracted_keywords: List[str]  # 추출된 키워드
    emotion: EmotionType  # 감정 분석 결과
    confidence: float  # 신뢰도
    preserved_expressions: List[str]  # 보존된 표현들


class NaviyamTextPreprocessor:
    """나비얌 특화 텍스트 전처리기"""

    def __init__(self, preserve_expressions: bool = True):
        """
        Args:
            preserve_expressions: 아동 친화적 표현 보존 여부
        """
        self.preserve_expressions = preserve_expressions

        # 보존할 아동 친화적 표현들
        self.preserve_patterns = {
            'laughter': [r'ㅋ+', r'ㅎ+', r'헤+', r'하+'],
            'excitement': [r'\^+', r'!+', r'~+'],
            'sadness': [r'ㅠ+', r'ㅜ+', r'흑+'],
            'heart': [r'♥+', r'❤+', r'💕', r'❣️'],
            'emphasis': [r'\?+', r'\.{2,}']
        }

        # 음식 관련 키워드 사전
        self.food_keywords = {
            'categories': [
                '한식', '중식', '일식', '양식', '치킨', '피자', '햄버거',
                '분식', '카페', '디저트', '아시안', '멕시칸', '인도'
            ],
            'foods': [
                '김치찌개', '된장찌개', '비빔밥', '냉면', '라면', '떡볶이',
                '치킨', '피자', '햄버거', '파스타', '스테이크', '초밥',
                '짜장면', '짬뽕', '탕수육', '마라탕', '쌀국수', '파드타이',
                '카레', '돈까스', '우동', '소바', '규동', '오므라이스'
            ],
            'tastes': [
                '맵다', '달다', '짜다', '시다', '쓰다', '고소하다', '담백하다',
                '진하다', '깔끔하다', '부드럽다', '쫄깃하다', '바삭하다'
            ],
            'cooking_methods': [
                '볶음', '찜', '구이', '튀김', '조림', '탕', '국', '찌개',
                '무침', '절임', '생', '회'
            ]
        }

        # 감정 분석용 키워드
        self.emotion_keywords = {
            EmotionType.POSITIVE: [
                '맛있다', '좋다', '최고', '짱', '굿', '완벽', '만족', '행복',
                '감사', '추천', '다시', '또', '자주', '좋아해', '사랑해'
            ],
            EmotionType.NEGATIVE: [
                '맛없다', '별로', '실망', '후회', '최악', '나쁘다', '싫다',
                '다시는', '안가', '비추', '돈아까워', '짜증'
            ],
            EmotionType.EXCITED: [
                '와', '우와', '대박', '쩐다', '미쳤다', '개맛있어', '존맛',
                '킹왕짱', '레전드', '갓', '혜자', '꿀맛'
            ],
            EmotionType.DISAPPOINTED: [
                '아쉽다', '그냥그냥', '보통', '평범', '기대이하', '뭔가',
                '좀더', '아깝다', '애매하다'
            ]
        }

        # 예산/가격 관련 표현
        self.budget_patterns = [
            r'(\d+)\s*원',
            r'(\d+)\s*천원',
            r'(\d+)\s*만원',
            r'(\d{1,2})\s*천',
            r'(\d{1,3})\s*만',
            r'비싸다?', r'싸다?', r'저렴하다?', r'가성비', r'혜자'
        ]

        # 동반자 패턴
        self.companion_patterns = [
            r'친구', r'가족', r'엄마', r'아빠', r'형', r'누나', r'언니', r'오빠',
            r'동생', r'혼자', r'애인', r'남친', r'여친', r'같이', r'함께'
        ]

    def preprocess(self, text: str) -> PreprocessResult:
        """전체 전처리 파이프라인"""
        if not text or not text.strip():
            return PreprocessResult(
                original_text=text,
                cleaned_text="",
                normalized_text="",
                extracted_keywords=[],
                emotion=EmotionType.NEUTRAL,
                confidence=0.0,
                preserved_expressions=[]
            )

        original_text = text

        # 1. 보존할 표현 추출
        preserved_expressions = self._extract_preserved_expressions(text)

        # 2. 기본 정제
        cleaned_text = self._basic_cleaning(text)

        # 3. 정규화
        normalized_text = self._normalize_text(cleaned_text)

        # 4. 키워드 추출
        keywords = self._extract_keywords(normalized_text)

        # 5. 감정 분석
        emotion, confidence = self._analyze_emotion(normalized_text, preserved_expressions)

        return PreprocessResult(
            original_text=original_text,
            cleaned_text=cleaned_text,
            normalized_text=normalized_text,
            extracted_keywords=keywords,
            emotion=emotion,
            confidence=confidence,
            preserved_expressions=preserved_expressions
        )

    def _extract_preserved_expressions(self, text: str) -> List[str]:
        """보존할 표현들 추출"""
        if not self.preserve_expressions:
            return []

        preserved = []

        for expr_type, patterns in self.preserve_patterns.items():
            for pattern in patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                for match in matches:
                    preserved.append(f"{expr_type}:{match}")

        return preserved

    def _basic_cleaning(self, text: str) -> str:
        """기본 텍스트 정제"""
        # HTML 태그 제거
        text = re.sub(r'<[^>]+>', '', text)

        # URL 제거
        text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)

        # 이메일 제거
        text = re.sub(r'\S+@\S+', '', text)

        # 과도한 공백 정리 (하지만 의미있는 띄어쓰기는 보존)
        text = re.sub(r'\s+', ' ', text)

        # 불필요한 특수문자 제거 (보존할 것들은 제외)
        if self.preserve_expressions:
            # 보존할 특수문자 패턴 생성
            preserve_chars = r'[ㅋㅎㅠㅜ\^!~♥❤💕❣️\?\.]'
            # 보존할 문자가 아닌 특수문자만 제거
            unwanted_chars = r'[^\w\s가-힣ㅋㅎㅠㅜ\^!~♥❤💕❣️\?\.,]'
            text = re.sub(unwanted_chars, ' ', text)
        else:
            # 모든 특수문자 제거
            text = re.sub(r'[^\w\s가-힣]', ' ', text)

        return text.strip()

    def _normalize_text(self, text: str) -> str:
        """텍스트 정규화"""
        # 줄임말 정규화
        normalizations = {
            r'\b넘\b': '너무',
            r'\b짱\b': '정말',
            r'\b개\s*맛있': '정말 맛있',
            r'\b완전\b': '정말',
            r'\b오짜\b': '오징어짜글이',
            r'\b떡볶이\b': '떡볶이',
            r'\b쫄면\b': '쫄면'
        }

        normalized = text
        for pattern, replacement in normalizations.items():
            normalized = re.sub(pattern, replacement, normalized, flags=re.IGNORECASE)

        # 중복 문자 정리 (의미있는 것은 보존)
        if self.preserve_expressions:
            # ㅋㅋㅋ, ^^^ 등은 보존하고 일반 중복만 정리
            normalized = re.sub(r'([가-힣])\1{2,}', r'\1\1', normalized)  # 한글 2글자까지만
        else:
            normalized = re.sub(r'(.)\1{2,}', r'\1', normalized)

        return normalized.strip()

    def _extract_keywords(self, text: str) -> List[str]:
        """키워드 추출"""
        keywords = []
        text_lower = text.lower()

        # 음식 관련 키워드 추출
        for category, words in self.food_keywords.items():
            for word in words:
                if word in text_lower:
                    keywords.append(f"{category}:{word}")

        # 예산 키워드 추출
        budget_matches = []
        for pattern in self.budget_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            budget_matches.extend(matches)

        if budget_matches:
            for match in budget_matches:
                keywords.append(f"budget:{match}")

        # 동반자 키워드 추출
        companion_matches = []
        for pattern in self.companion_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                companion_matches.append(pattern)

        if companion_matches:
            for match in companion_matches:
                keywords.append(f"companion:{match}")

        # 중복 제거
        return list(set(keywords))

    def _analyze_emotion(self, text: str, preserved_expressions: List[str]) -> Tuple[EmotionType, float]:
        """감정 분석"""
        text_lower = text.lower()
        emotion_scores = {emotion: 0 for emotion in EmotionType}

        # 키워드 기반 감정 점수 계산
        for emotion, keywords in self.emotion_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    emotion_scores[emotion] += 1

        # 보존된 표현으로 감정 보정
        for expr in preserved_expressions:
            if expr.startswith('laughter:'):
                emotion_scores[EmotionType.POSITIVE] += 2
                emotion_scores[EmotionType.EXCITED] += 1
            elif expr.startswith('excitement:'):
                emotion_scores[EmotionType.EXCITED] += 2
                emotion_scores[EmotionType.POSITIVE] += 1
            elif expr.startswith('sadness:'):
                emotion_scores[EmotionType.NEGATIVE] += 2
                emotion_scores[EmotionType.DISAPPOINTED] += 1
            elif expr.startswith('heart:'):
                emotion_scores[EmotionType.POSITIVE] += 3

        # 최고 점수 감정 선택
        max_emotion = max(emotion_scores, key=emotion_scores.get)
        max_score = emotion_scores[max_emotion]

        # 신뢰도 계산 (점수 / 총 가능 점수)
        total_score = sum(emotion_scores.values())
        confidence = max_score / max(total_score, 1)

        # 점수가 0이면 중립
        if max_score == 0:
            return EmotionType.NEUTRAL, 0.0

        return max_emotion, min(confidence, 1.0)

    def extract_budget_info(self, text: str) -> Optional[int]:
        """예산 정보 추출 (원 단위)"""
        text = text.replace(',', '').replace(' ', '')

        # 원 단위 직접 표현
        won_pattern = r'(\d+)\s*원'
        won_matches = re.findall(won_pattern, text)
        if won_matches:
            return int(won_matches[0])

        # 천원 단위
        thousand_pattern = r'(\d+)\s*천\s*원?'
        thousand_matches = re.findall(thousand_pattern, text)
        if thousand_matches:
            return int(thousand_matches[0]) * 1000

        # 만원 단위
        man_pattern = r'(\d+)\s*만\s*원?'
        man_matches = re.findall(man_pattern, text)
        if man_matches:
            return int(man_matches[0]) * 10000

        return None

    def extract_companions(self, text: str) -> List[str]:
        """동반자 정보 추출"""
        companions = []
        text_lower = text.lower()

        companion_mapping = {
            '친구': 'friend',
            '가족': 'family',
            '엄마': 'mother',
            '아빠': 'father',
            '부모': 'parents',
            '형': 'brother',
            '누나': 'sister',
            '언니': 'sister',
            '오빠': 'brother',
            '동생': 'sibling',
            '혼자': 'alone',
            '애인': 'partner',
            '남친': 'boyfriend',
            '여친': 'girlfriend'
        }

        for korean, english in companion_mapping.items():
            if korean in text_lower:
                companions.append(english)

        return list(set(companions))

    def clean_for_model_input(self, text: str) -> str:
        """모델 입력용 텍스트 정제"""
        # 기본 전처리
        result = self.preprocess(text)

        # 모델 입력에 적합하게 추가 정제
        cleaned = result.normalized_text

        # 최대 길이 제한
        if len(cleaned) > 200:
            cleaned = cleaned[:200].rsplit(' ', 1)[0]  # 단어 단위로 자르기

        # 빈 문자열 처리
        if not cleaned.strip():
            cleaned = "음식 추천 요청"

        return cleaned

    def is_food_related(self, text: str) -> Tuple[bool, float]:
        """음식 관련 텍스트인지 판단"""
        keywords = self._extract_keywords(text.lower())

        food_keywords = [k for k in keywords if k.startswith(('categories:', 'foods:', 'tastes:', 'cooking_methods:'))]

        # 음식 키워드 비율로 신뢰도 계산
        total_keywords = len(keywords)
        food_keyword_count = len(food_keywords)

        if total_keywords == 0:
            return False, 0.0

        confidence = food_keyword_count / total_keywords
        is_food_related = confidence > 0.3  # 30% 이상이면 음식 관련

        return is_food_related, confidence

    def get_preprocessing_summary(self, result: PreprocessResult) -> str:
        """전처리 결과 요약"""
        return f"""
전처리 결과:
- 원본: {result.original_text[:50]}...
- 정제: {result.cleaned_text[:50]}...
- 키워드: {len(result.extracted_keywords)}개
- 감정: {result.emotion.value} ({result.confidence:.2f})
- 보존표현: {len(result.preserved_expressions)}개
"""


# 편의 함수들
def quick_preprocess(text: str, preserve_expressions: bool = True) -> PreprocessResult:
    """빠른 전처리 (편의 함수)"""
    preprocessor = NaviyamTextPreprocessor(preserve_expressions)
    return preprocessor.preprocess(text)


def extract_food_intent(text: str) -> Dict[str, any]:
    """음식 관련 의도 추출 (편의 함수)"""
    preprocessor = NaviyamTextPreprocessor()
    result = preprocessor.preprocess(text)

    return {
        "is_food_related": preprocessor.is_food_related(text)[0],
        "budget": preprocessor.extract_budget_info(text),
        "companions": preprocessor.extract_companions(text),
        "emotion": result.emotion.value,
        "keywords": result.extracted_keywords
    }