# 나비얌 챗봇 Conversation 데이터 상세 분석

## 📊 전체 대화 처리 파이프라인

```
사용자 입력 → 전처리 → NLU(의도+엔티티) → RAG 검색 → 응답 생성 → 학습 데이터 수집 → DB 저장
```

---

## 🎯 Intent와 Entities 분리 아키텍처

### 1. Intent (의도) - "사용자가 무엇을 하려고 하는가?"

**Intent는 사용자의 전체적인 목적을 나타냅니다:**

```python
# Intent 종류와 의미
IntentType = {
    'food_request': '특정 음식 추천 요청',      # "치킨 먹고 싶어"
    'budget_inquiry': '예산 제약 음식 찾기',    # "5천원으로 뭐 먹지?"
    'coupon_inquiry': '쿠폰 정보 문의',        # "할인 쿠폰 있어?"
    'location_inquiry': '위치 기반 검색',       # "근처 맛집 알려줘"
    'time_inquiry': '영업시간 관련 문의',       # "지금 열린 곳 있어?"
    'general_chat': '일반 대화',              # "안녕하세요"
    'menu_option': '메뉴 옵션 문의'            # "매운거 빼고"
}
```

### 2. Entities (엔티티) - "구체적인 정보는 무엇인가?"

**Entities는 의도를 달성하기 위한 세부 정보입니다:**

```python
@dataclass
class ExtractedEntity:
    food_type: Optional[str] = None        # "치킨", "한식", "피자"
    budget: Optional[int] = None           # 5000, 10000, 15000
    location_preference: Optional[str] = None  # "근처", "강남역", "5분 거리"
    time_preference: Optional[str] = None   # "지금", "점심시간", "저녁"
    taste_preference: Optional[str] = None  # "매운", "순한", "짭짤한"
    companions: Optional[str] = None        # "혼자", "친구", "가족"
    urgency: Optional[str] = None          # "high", "normal", "low"
```

### 3. 왜 Intent와 Entities를 분리하는가?

#### 3.1 유연한 처리 가능
```python
# 같은 intent도 다른 entities로 완전히 다른 처리
"치킨 먹고 싶어" vs "한식 먹고 싶어"
→ 둘 다 intent = 'food_request'
→ 하지만 entities.food_type이 달라서 다른 결과

# 같은 entities도 다른 intent로 다른 우선순위
"5천원으로 뭐 먹지?" vs "5천원 있는데 쿠폰 있어?"
→ 둘 다 entities.budget = 5000
→ 하지만 intent가 달라서 처리 전략이 다름
```

#### 3.2 다중 정보 동시 처리
```python
# 하나의 문장에 여러 정보가 포함된 경우
user_input = "친구랑 강남역에서 만원으로 매운 치킨 먹고 싶어"

extracted_intent = 'food_request'
extracted_entities = {
    "food_type": "치킨",
    "budget": 10000,
    "location_preference": "강남역",
    "taste_preference": "매운",
    "companions": "친구"
}
```

#### 3.3 응답 전략 최적화
```python
def select_response_strategy(intent: str, entities: dict) -> str:
    if intent == 'budget_inquiry':
        if entities.get('budget', 0) < 10000:
            return 'budget_constraint_strategy'  # 예산 제약 중심
        else:
            return 'value_for_money_strategy'    # 가성비 중심
    
    elif intent == 'food_request':
        if entities.get('urgency') == 'high':
            return 'quick_recommendation_strategy'  # 빠른 추천
        else:
            return 'detailed_recommendation_strategy'  # 상세 추천
```

---

## 🔄 대화 데이터 처리 상세 흐름

### Phase 1: 입력 처리 및 전처리

```python
# 1. UserInput 객체 생성
user_input = UserInput(
    text="배고픈데 5천원밖에 없어",
    user_id="user_123",
    timestamp=datetime.now(),
    session_id="session_abc"
)

# 2. 텍스트 전처리
preprocessed = self.preprocessor.preprocess(user_input.text)
# 결과: {
#     "normalized_text": "배고픈데 5천원밖에 없어",
#     "keywords": ["배고프다", "5천원", "없다"],
#     "emotion": EmotionType.URGENT,
#     "detected_patterns": ["budget_constraint", "urgency"]
# }
```

### Phase 2: NLU 처리 (Intent + Entities 추출)

```python
# 3. Smart NLU Processing
extracted_info = self._smart_nlu_processing(user_input, preprocessed)

# 복잡한 입력은 LLM 사용
if self.llm_normalizer.should_use_llm_normalization(user_input.text):
    llm_output = self.llm_normalizer.normalize_user_input(
        text=user_input.text,
        context=recent_conversations,
        user_context=user_profile
    )
    extracted_info = self.nlu.extract_from_llm_normalized(
        text=user_input.text,
        llm_output=llm_output,
        user_id=user_input.user_id
    )
else:
    # 단순한 입력은 규칙 기반
    extracted_info = self.nlu.extract_intent_and_entities(
        preprocessed['normalized_text'],
        user_input.user_id
    )

# 결과:
# ExtractedInfo(
#     intent=IntentType.BUDGET_INQUIRY,
#     entities=ExtractedEntity(
#         budget=5000,
#         urgency="high",
#         food_type=None
#     ),
#     confidence=0.92,
#     confidence_level=ConfidenceLevel.HIGH,
#     raw_text="배고픈데 5천원밖에 없어"
# )
```

### Phase 3: 컨텍스트 구축 및 검색

```python
# 4. 대화 컨텍스트 가져오기
conversation_context = self.conversation_memory.get_recent_conversations(
    user_id=user_input.user_id,
    count=3
)

# 5. RAG 검색 수행
if extracted_info.intent in [IntentType.FOOD_REQUEST, IntentType.BUDGET_INQUIRY]:
    rag_context = self._perform_rag_search(user_input, extracted_info)
    # RAG가 의미적으로 관련된 가게/메뉴 찾기
    # 예: 저렴한 음식점, 5천원 이하 메뉴 등

# 6. 사용자 프로필 조회
user_profile = self.user_manager.get_or_create_user_profile(user_input.user_id)
```

### Phase 4: 응답 생성 전략 결정

```python
# 7. 사용자 전략 결정
user_strategy = self._determine_user_strategy(
    user_id=user_input.user_id,
    extracted_info=extracted_info,
    user_profile=user_profile
)

# 급식카드 잔액 확인
if user_input.user_id in self.knowledge.foodcard_users:
    foodcard_user = self.knowledge.foodcard_users[user_input.user_id]
    if foodcard_user.balance <= 5000:
        user_strategy = "urgent_mode"  # 잔액 부족 긴급 모드
```

### Phase 5: 스마트 응답 생성

```python
# 8. 응답 생성
response = self._smart_response_generation(
    extracted_info=extracted_info,
    user_profile=user_profile,
    user_id=user_input.user_id,
    rag_context=rag_context
)

# 응답 생성 로직
if user_strategy == "urgent_mode":
    # 잔액 부족 시 쿠폰 활용 추천
    affordable_options = self.coupon_recommender.find_affordable_options_with_coupons(
        user_id=int(user_input.user_id),
        max_budget=extracted_info.entities.budget
    )
    response = self.nlg.generate_urgent_budget_response(
        affordable_options=affordable_options,
        budget=extracted_info.entities.budget
    )
elif user_strategy == "onboarding_mode":
    # 신규 사용자 친절 안내
    response = self.nlg.generate_onboarding_response(extracted_info)
```

---

## 💾 ConversationMemory 상세 구조

### 메모리 저장 구조
```python
class ConversationMemory:
    def __init__(self, max_history: int = 10):
        self.max_history = max_history
        self.conversations = {}  # user_id -> conversation_history
        
    def add_conversation(self, user_id: str, user_input: str, 
                        bot_response: str, extracted_info: ExtractedInfo):
        if user_id not in self.conversations:
            self.conversations[user_id] = []
        
        conversation_item = {
            "timestamp": datetime.now().isoformat(),
            "user_input": user_input,
            "bot_response": bot_response,
            "intent": extracted_info.intent.value,
            "confidence": extracted_info.confidence,
            "entities": asdict(extracted_info.entities),
            "turn_number": len(self.conversations[user_id]) + 1
        }
        
        self.conversations[user_id].append(conversation_item)
        
        # 슬라이딩 윈도우 적용
        if len(self.conversations[user_id]) > self.max_history:
            self.conversations[user_id].pop(0)
```

### 컨텍스트 활용 예시
```python
# 이전 대화 기반 컨텍스트 이해
recent_convs = conversation_memory.get_recent_conversations("user_123", 3)

# 예시: 
# Turn 1: "치킨 먹고 싶어" → "치킨집 추천..."
# Turn 2: "너무 비싸" → 예산 제약 인식
# Turn 3: "5천원으로 뭐 먹지?" → 이전 컨텍스트 활용하여 저렴한 옵션 추천
```

---

## 📊 학습 데이터 수집 상세

### 1. 멀티 버퍼 시스템

```python
class LearningDataCollector:
    def __init__(self):
        # 타입별 전용 버퍼
        self.buffers = {
            'nlu': deque(maxlen=100),          # NLU 추출 결과
            'interaction': deque(maxlen=100),   # 사용자 상호작용
            'recommendation': deque(maxlen=100), # 추천 결과
            'feedback': deque(maxlen=100)       # 사용자 피드백
        }
        
    def collect_nlu_data(self, user_id: str, input_text: str, 
                        extracted_info: ExtractedInfo):
        nlu_data = {
            "user_id": user_id,
            "input_text": input_text,
            "extracted_intent": extracted_info.intent.value,
            "extracted_entities": asdict(extracted_info.entities),
            "confidence": extracted_info.confidence,
            "timestamp": datetime.now().isoformat()
        }
        self.buffers['nlu'].append(nlu_data)
```

### 2. 데이터 품질 검증

```python
def validate_learning_data(self, data: Dict) -> Tuple[bool, float]:
    """학습 데이터 품질 점수 계산"""
    score = 0.0
    
    # 필수 필드 체크 (50%)
    required_fields = ['user_id', 'input_text', 'extracted_intent']
    for field in required_fields:
        if field in data and data[field]:
            score += 0.5 / len(required_fields)
    
    # 선택 필드 체크 (30%)
    optional_fields = ['extracted_entities', 'user_selection', 'feedback']
    for field in optional_fields:
        if field in data and data[field]:
            score += 0.3 / len(optional_fields)
    
    # 신뢰도 가중치 (20%)
    if 'confidence' in data:
        score += 0.2 * data['confidence']
    
    is_valid = score >= 0.5  # 50% 이상이면 유효
    return is_valid, score
```

---

## 🗄️ DB 저장 스키마 상세

### conversations 테이블 - 대화 이력 저장

```sql
CREATE TABLE conversations (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    
    -- 기본 식별 정보
    user_id VARCHAR(100) NOT NULL,
    session_id VARCHAR(200) NOT NULL,
    conversation_id VARCHAR(200),  -- 전체 대화 세션 식별자
    
    -- 대화 내용
    input_text TEXT NOT NULL,      -- 사용자 원본 입력
    response_text TEXT NOT NULL,   -- 챗봇 응답
    
    -- NLU 추출 결과 (Intent와 Entities 분리 저장)
    extracted_intent VARCHAR(50),   -- 'food_request', 'budget_inquiry' 등
    intent_confidence DECIMAL(4,3), -- 0.000 ~ 1.000
    
    -- Entities는 JSON으로 저장 (유연성)
    extracted_entities JSON,
    -- 예시: {
    --   "food_type": "치킨",
    --   "budget": 5000,
    --   "location_preference": "강남역",
    --   "urgency": "high",
    --   "companions": "친구"
    -- }
    
    -- 대화 맥락 정보
    user_strategy VARCHAR(30),      -- 'onboarding_mode', 'urgent_mode' 등
    conversation_turn INT,          -- 대화 턴 번호 (세션 내 순서)
    previous_intent VARCHAR(50),    -- 이전 대화의 intent
    
    -- 응답 생성 정보
    response_strategy VARCHAR(50),   -- 사용된 응답 전략
    llm_used BOOLEAN DEFAULT FALSE, -- LLM 사용 여부
    template_used VARCHAR(100),     -- 사용된 템플릿 이름
    
    -- 성능 및 품질 지표
    processing_time_ms INT,         -- 전체 처리 시간
    nlu_time_ms INT,               -- NLU 처리 시간
    response_time_ms INT,          -- 응답 생성 시간
    
    -- 타임스탬프
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- 인덱스
    INDEX idx_user_timestamp (user_id, timestamp),
    INDEX idx_session (session_id),
    INDEX idx_intent (extracted_intent),
    INDEX idx_strategy (user_strategy)
);
```

### user_interactions 테이블 - 상세 상호작용 기록

```sql
CREATE TABLE user_interactions (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    
    -- 기본 정보
    user_id VARCHAR(100) NOT NULL,
    session_id VARCHAR(200),
    conversation_id VARCHAR(200),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- 상호작용 타입
    interaction_type VARCHAR(30),
    -- 'text_input': 텍스트 입력
    -- 'selection': 추천 중 선택
    -- 'feedback': 만족도 피드백
    -- 'coupon_use': 쿠폰 사용
    -- 'view_details': 상세보기
    
    -- Intent와 Entities (대화형 상호작용인 경우)
    intent VARCHAR(50),
    entities JSON,
    
    -- 사용자 선택 정보
    user_selection JSON,
    -- 예시: {
    --   "shop_id": 15,
    --   "menu_ids": [201, 202],
    --   "coupon_id": "FOOD10",
    --   "final_price": 8000,
    --   "selected_from_position": 2  -- 추천 목록에서 2번째 선택
    -- }
    
    -- 추천 컨텍스트
    recommendations_shown JSON,     -- 보여준 추천 목록
    recommendation_count INT,       -- 추천 개수
    
    -- 학습용 특징 추출
    food_preference_extracted VARCHAR(100),
    budget_pattern_extracted INT,
    companion_pattern_extracted VARCHAR(50),
    time_preference_extracted VARCHAR(50),
    
    -- 쿠폰 관련
    coupon_usage JSON,
    -- {
    --   "coupon_id": "FOOD10",
    --   "discount_applied": 2000,
    --   "coupon_type": "fixed_amount"
    -- }
    
    -- 피드백 정보
    satisfaction_score INT,         -- 1-5 점
    feedback_text TEXT,
    
    INDEX idx_user_timestamp (user_id, timestamp),
    INDEX idx_interaction_type (interaction_type),
    INDEX idx_intent (intent)
);
```

### recommendations_log 테이블 - 추천 결과 기록

```sql
CREATE TABLE recommendations_log (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    
    -- 기본 정보
    user_id VARCHAR(100) NOT NULL,
    session_id VARCHAR(200),
    conversation_id VARCHAR(200),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- 요청 정보 (Intent + Entities)
    request_intent VARCHAR(50),     -- 사용자 의도
    request_entities JSON,          -- 추출된 엔티티들
    
    -- 구체적 요청 파라미터
    request_food_type VARCHAR(100),
    request_budget INT,
    request_location VARCHAR(100),
    request_time VARCHAR(50),
    request_companions VARCHAR(50),
    
    -- 추천 결과
    recommendations JSON NOT NULL,
    -- [{
    --   "shop_id": 15,
    --   "shop_name": "김밥천국",
    --   "score": 0.92,
    --   "ranking": 1,
    --   "reason": "예산적합+가까움+인기메뉴",
    --   "distance_km": 0.3,
    --   "menu_recommendations": [...],
    --   "applicable_coupons": ["FOOD10", "TEEN20"],
    --   "final_price_with_coupon": 3000
    -- }]
    
    -- 추천 메타정보
    recommendation_count INT NOT NULL,
    recommendation_method VARCHAR(50),
    -- 'wide_deep': Wide&Deep 모델
    -- 'rag': RAG 검색
    -- 'hybrid': 복합 추천
    -- 'emergency': 잔액 부족 긴급 추천
    -- 'coupon_based': 쿠폰 기반 추천
    
    -- 추천 품질 지표
    confidence_score DECIMAL(4,3),
    diversity_score DECIMAL(4,3),   -- 추천 다양성
    personalization_score DECIMAL(4,3), -- 개인화 정도
    
    -- 쿠폰 정보
    total_discount_available INT,   -- 적용 가능한 총 할인액
    best_coupon_option JSON,       -- 최적 쿠폰 조합
    
    -- 사용자 반응
    user_clicked BOOLEAN DEFAULT FALSE,
    clicked_position INT,          -- 클릭한 추천의 순위
    time_to_click_ms INT,         -- 클릭까지 걸린 시간
    
    INDEX idx_user_timestamp (user_id, timestamp),
    INDEX idx_method (recommendation_method),
    INDEX idx_intent (request_intent)
);
```

---

## 🔍 실제 사용 시나리오

### 시나리오 1: "배고픈데 5천원밖에 없어"

```python
# 1. NLU 처리
intent = 'budget_inquiry'  # 예산이 주요 관심사
entities = {
    "budget": 5000,
    "urgency": "high",
    "emotion": "hungry"
}

# 2. 전략 결정
user_strategy = 'urgent_mode'  # 잔액 부족 + 긴급

# 3. DB 저장
INSERT INTO conversations (
    user_id, input_text, response_text,
    extracted_intent, extracted_entities,
    user_strategy, intent_confidence
) VALUES (
    'user_123',
    '배고픈데 5천원밖에 없어',
    '5천원으로도 맛있게 드실 수 있어요! 쿠폰 사용하면...',
    'budget_inquiry',
    '{"budget": 5000, "urgency": "high"}',
    'urgent_mode',
    0.92
);
```

### 시나리오 2: "아까 그 치킨집 말고 다른 데"

```python
# 1. 컨텍스트 조회
previous_conversations = get_recent_conversations('user_123', 3)
# 이전 대화에서 치킨집 추천 확인

# 2. NLU with Context
intent = 'food_request'
entities = {
    "food_type": "치킨",  # 컨텍스트에서 추론
    "exclude_shop": previous_recommendation  # 이전 추천 제외
}

# 3. 응답 생성
response = "아, 다른 치킨집을 찾으시는군요! 이번엔..."
```

---

## 📈 성능 최적화 전략

### 1. 캐싱 전략
```python
# 자주 접근하는 데이터는 Redis 캐시 활용
cache_key = f"user_profile:{user_id}"
user_profile = redis.get(cache_key) or db.get_user_profile(user_id)

# Intent 분류 결과 캐싱 (유사 입력)
intent_cache = f"intent:{normalized_text_hash}"
```

### 2. 배치 처리
```python
# 5분마다 학습 데이터 배치 저장
async def save_learning_data_batch():
    while True:
        await asyncio.sleep(300)  # 5분
        batch_data = collector.get_and_clear_buffers()
        db.bulk_insert_learning_data(batch_data)
```

### 3. 비동기 처리
```python
# 중요하지 않은 로깅은 비동기로
async def log_interaction_async(interaction_data):
    await async_db.insert_interaction(interaction_data)
    
# 메인 응답은 동기, 로깅은 비동기
response = generate_response_sync(user_input)
asyncio.create_task(log_interaction_async(interaction_data))
return response
```

이러한 상세한 대화 데이터 처리 구조를 통해 나비얌 챗봇은:
1. 사용자 의도를 정확히 파악하고
2. 맥락을 유지하며 개인화된 응답을 제공하고
3. 지속적으로 학습하여 서비스를 개선합니다.