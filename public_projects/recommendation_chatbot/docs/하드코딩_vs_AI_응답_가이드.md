# 나비얌 챗봇 응답 유형 가이드 (GPU 없는 환경용)

## 📋 개요
나비얌 챗봇은 두 가지 방식으로 응답을 생성합니다:
1. **하드코딩된 템플릿 응답** - GPU 없이 작동
2. **AI 모델 생성 응답** - GPU 필요 (A.X 3.1 Lite)

백엔드 담당자가 GPU 없는 로컬 환경에서 테스트할 때 참고하세요.

---

## 1. 🤖 하드코딩된 응답 (GPU 불필요)

### 1.1 템플릿 기반 응답
**위치**: `nlp/nlg.py` (42-200라인)

#### 음식 추천 요청 (IntentType.FOOD_REQUEST)
```python
입력 예시: "치킨 먹고 싶어", "피자 추천해줘", "한식 뭐 먹을까?"

응답 템플릿:
- "{food_type} 좋은 선택이에요! {shop_name}에서 {menu_name}({price}원) 어떠세요?"
- "{shop_name}의 {menu_name} 추천드려요! {price}원이고 정말 맛있어요!"
- "오! {food_type} 드시고 싶으시군요. {shop_name} 가보세요!"

실제 응답 예시:
"치킨 좋은 선택이에요! BBQ에서 황금올리브치킨(18,000원) 어떠세요? 🍗"
```

#### 예산 관련 질문 (IntentType.BUDGET_INQUIRY)
```python
입력 예시: "5천원으로 뭐 먹지?", "만원 있는데 추천해줘"

응답 템플릿:
- "{budget}원이면 {menu_list} 드실 수 있어요!"
- "{budget}원 예산으로 {menu_count}개 메뉴 중에 고르실 수 있어요!"

실제 응답 예시:
"5,000원이면 김밥천국 참치김밥, 신선설농탕 육개장 드실 수 있어요! 💰"
```

#### 위치 관련 질문 (IntentType.LOCATION_INQUIRY)
```python
입력 예시: "근처 맛집", "주변에 뭐 있어?", "가까운 곳"

응답 템플릿:
- "근처에 {shop_count}개 맛집이 있어요! {shop_list} 어떠세요?"
- "{distance}에 {shop_name}이 있어요! {menu_name} 맛있어요!"

실제 응답 예시:
"도보 5분에 김밥천국이 있어요! 참치김밥 맛있어요! 📍"
```

#### 시간 관련 질문 (IntentType.TIME_INQUIRY)
```python
입력 예시: "지금 열린 곳", "영업시간", "밤에도 하는 곳"

응답 템플릿:
- "지금 영업 중인 곳은 {shop_list}예요!"
- "{shop_name}은 {close_hour}까지 영업해요!"

실제 응답 예시:
"지금 영업 중인 곳은 김밥천국, BBQ, 맥도날드예요! 🕐"
```

#### 쿠폰 관련 질문 (IntentType.COUPON_INQUIRY)
```python
입력 예시: "쿠폰", "할인", "싸게 먹을 수 있는 곳"

응답 템플릿:
- "{coupon_name} 쿠폰으로 {shop_name}에서 {discount}원 할인받을 수 있어요!"
- "쿠폰 사용하면 {final_price}원에 드실 수 있어요!"

실제 응답 예시:
"신규가입 쿠폰으로 BBQ에서 3,000원 할인받을 수 있어요! 🎫"
```

#### 급식카드 잔액 확인 (IntentType.BALANCE_CHECK)
```python
입력 예시: "잔액", "급식카드 얼마 남았어?", "잔액 확인"

응답 템플릿:
- "현재 급식카드 잔액은 {balance}원이에요!"
- "잔액이 {balance}원 남았네요. {suggestion}"

실제 응답 예시:
"현재 급식카드 잔액은 15,000원이에요! 💳"
```

### 1.2 폴백 응답 (신뢰도 낮을 때)
**위치**: `inference/response_generator.py` (688-709라인)

```python
신뢰도 < 0.3일 때 자동 선택되는 응답:

fallback_messages = [
    "죄송해요! 잘 이해하지 못했어요. 다시 말씀해주시겠어요?",
    "음.. 무슨 말씀인지 잘 모르겠어요. 음식 관련해서 도와드릴까요?",
    "헷갈리네요! 간단하게 말씀해주시면 더 잘 도와드릴 수 있어요!",
    "이해하기 어려워요 ㅠㅠ 예를 들어 '치킨 추천해줘' 이런 식으로 말씀해주세요!"
]
```

### 1.3 특수 상황 응답
**위치**: `nlp/nlg.py` (250-400라인)

#### 급식카드 잔액 부족
```python
조건: balance < 5000

응답:
"급식카드 잔액이 {balance}원 남았어요. 저렴한 메뉴 추천드릴게요!"
"잔액이 부족하네요 😢 {coupon_name} 쿠폰 사용하시면 {menu_name} 드실 수 있어요!"
```

#### 시간대별 인사
```python
06:00-11:00: "좋은 아침이에요! 아침 식사 추천드릴까요? 🌅"
11:00-14:00: "점심시간이네요! 든든한 메뉴 추천드려요! 🍱"
14:00-17:00: "오후 간식 시간! 가벼운 메뉴 어떠세요? ☕"
17:00-21:00: "저녁 시간이에요! 맛있는 저녁 추천드려요! 🌆"
21:00-24:00: "야식 시간! 부담없는 메뉴 추천드릴게요! 🌙"
```

---

## 2. 🧠 AI 모델 생성 응답 (GPU 필요)

### 2.1 모델 기반 응답이 필요한 경우
- 복잡한 대화 맥락 이해
- 개인화된 추천 설명
- 창의적인 응답 생성
- 다중 조건 처리

### 2.2 GPU 없이 테스트하는 방법

#### 방법 1: Mock 응답 사용
```python
# models/ax_model.py의 generate 메서드를 수정
def generate(self, prompt, **kwargs):
    if not torch.cuda.is_available():
        # GPU 없을 때 미리 정의된 응답 반환
        return {
            "generated_text": "맛있는 음식 추천드려요! (Mock 응답)",
            "tokens_generated": 10,
            "tokens_per_second": 100
        }
    # 원래 코드...
```

#### 방법 2: 템플릿 전용 모드
```python
# main.py 실행 시 --no-llm 옵션 추가
python main.py --mode chat --no-llm

# response_generator.py에서 처리
if self.model is None or self.no_llm_mode:
    return self._generate_template_response(...)
```

---

## 3. 📊 응답 유형별 통계

| 응답 유형 | GPU 필요 | 평균 응답 시간 | 품질 |
|---------|----------|--------------|------|
| 템플릿 응답 | ❌ | 10-50ms | 보통 |
| 폴백 응답 | ❌ | 5-10ms | 낮음 |
| 특수 상황 응답 | ❌ | 10-30ms | 높음 |
| AI 모델 응답 | ✅ | 1-3초 | 매우 높음 |

---

## 4. 🛠️ GPU 없는 환경 설정

### 4.1 환경 변수 설정
```bash
# .env 파일
USE_GPU=false
FALLBACK_MODE=true
MODEL_TYPE=mock
```

### 4.2 테스트용 간단 실행
```python
# test_no_gpu.py
from inference.chatbot import NaviyamChatbot

# GPU 없는 환경용 설정
config = {
    "use_gpu": False,
    "model_type": "mock",
    "response_mode": "template_only"
}

chatbot = NaviyamChatbot(config)

# 테스트
test_inputs = [
    "치킨 먹고 싶어",
    "5천원으로 뭐 먹지?",
    "근처 맛집",
    "쿠폰",
    "잔액"
]

for input_text in test_inputs:
    response = chatbot.process(input_text)
    print(f"입력: {input_text}")
    print(f"응답: {response.text}")
    print("-" * 50)
```

---

## 5. 📌 주의사항

1. **GPU 없는 환경의 제한사항**
   - 개인화 추천 설명 불가
   - 복잡한 대화 맥락 처리 제한
   - 창의적 응답 생성 불가

2. **테스트 가능한 기능**
   - 의도 분류 (NLU)
   - 엔티티 추출
   - 템플릿 기반 응답
   - 추천 로직
   - 쿠폰 시스템
   - 급식카드 관리

3. **성능 차이**
   - GPU 있음: 전체 기능, 1-3초 응답
   - GPU 없음: 제한된 기능, 10-50ms 응답

---

## 6. 🚀 빠른 시작 (GPU 없는 환경)

```bash
# 1. 의존성 설치 (torch-cpu 버전)
pip install torch==2.0.1+cpu -f https://download.pytorch.org/whl/torch_stable.html
pip install -r requirements_no_gpu.txt

# 2. 환경 설정
echo "USE_GPU=false" >> .env

# 3. 템플릿 전용 모드로 실행
python main.py --mode chat --template-only

# 4. 테스트
# "치킨 추천해줘" → 템플릿 응답 출력
# "잔액" → 급식카드 잔액 확인
# "쿠폰" → 쿠폰 목록 표시
```

이 가이드를 참고하여 GPU 없는 환경에서도 나비얌 챗봇의 핵심 기능을 테스트할 수 있습니다!