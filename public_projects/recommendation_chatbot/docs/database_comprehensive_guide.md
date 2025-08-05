# 나비얌 챗봇 데이터베이스 종합 가이드

## 목차
1. [개요](#1-개요)
2. [시스템 아키텍처](#2-시스템-아키텍처)
3. [대화 처리 파이프라인](#3-대화-처리-파이프라인)
4. [핵심 데이터 테이블](#4-핵심-데이터-테이블)
5. [AI 운영 테이블](#5-ai-운영-테이블)
6. [Intent와 Entities 분리 설계](#6-intent와-entities-분리-설계)
7. [데이터 저장 전략](#7-데이터-저장-전략)
8. [헷갈리는 부분 정리](#8-헷갈리는-부분-정리)
9. [실제 사용 시나리오](#9-실제-사용-시나리오)
10. [구현 가이드](#10-구현-가이드)

---

## 1. 개요

나비얌 챗봇은 **급식카드 사용자를 위한 AI 기반 맛집 추천 서비스**입니다. LLM + RAG + 추천 시스템을 결합한 하이브리드 아키텍처로 구성되어 있습니다.

### 데이터 소스 구분
- 🏪 **[SAMPLE_DATA]**: sample_data.xlsx에서 제공되는 기본 데이터
- 🤖 **[CHATBOT_GENERATED]**: 챗봇이 대화를 통해 생성하는 데이터
- 🔄 **[DERIVED]**: 기존 데이터를 가공하여 파생된 데이터

### Feature 활용처 범례
- 💬 **챗봇 NLU/NLG**: 자연어 이해 및 응답 생성
- 🔍 **RAG 검색**: 벡터 검색 및 의미적 매칭
- 🎯 **Wide&Deep**: 추천 모델의 Wide/Deep 컴포넌트
- ⭐ **나비얌 특화**: 급식카드 관련 특화 기능

---

## 2. 시스템 아키텍처

### 전체 데이터 흐름
```
사용자 입력 → 전처리 → NLU(의도+엔티티) → RAG 검색 → 응답 생성 → 학습 데이터 수집 → DB 저장
```

### 주요 컴포넌트
1. **NLU (자연어 이해)**: Intent 분류 + Entity 추출
2. **RAG (검색 증강 생성)**: 의미적 유사도 기반 가게/메뉴 검색
3. **Wide&Deep 추천**: 개인화된 추천 순위 결정
4. **쿠폰 시스템**: 급식카드 잔액 부족 시 할인 매칭

---

## 3. 대화 처리 파이프라인

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

# ExtractedInfo 결과:
# intent: IntentType.BUDGET_INQUIRY (예산 제약이 주요 관심사)
# entities: {
#     "budget": 5000,
#     "urgency": "high",
#     "emotion": "hungry"
# }
# confidence: 0.92
```

### Phase 3: 컨텍스트 구축 및 검색
```python
# 4. 대화 컨텍스트 가져오기
conversation_context = self.conversation_memory.get_recent_conversations(
    user_id=user_input.user_id,
    count=3  # 최근 3개 대화
)

# 5. RAG 검색 수행
if extracted_info.intent in [IntentType.FOOD_REQUEST, IntentType.BUDGET_INQUIRY]:
    rag_context = self._perform_rag_search(user_input, extracted_info)

# 6. 사용자 프로필 조회
user_profile = self.user_manager.get_or_create_user_profile(user_input.user_id)
```

### Phase 4: 응답 생성
```python
# 7. 사용자 전략 결정
if foodcard_user.balance <= 5000:
    user_strategy = "urgent_mode"  # 잔액 부족 긴급 모드

# 8. 응답 생성
response = self._smart_response_generation(
    extracted_info=extracted_info,
    user_profile=user_profile,
    rag_context=rag_context
)
```

---

## 4. 핵심 데이터 테이블

### shops 테이블 (가게 정보)
```sql
CREATE TABLE shops (
    id INT PRIMARY KEY AUTO_INCREMENT,
    
    -- 🏪 [SAMPLE_DATA] 필드
    shop_name VARCHAR(200) NOT NULL,              
    -- 💬 챗봇: "굽네치킨 건대점"으로 구체적 응답 생성
    -- 🔍 RAG: 가게명 키워드 추출하여 벡터 인덱스 구성
    -- 🎯 Wide&Deep: shop_id 임베딩으로 Deep 모델 입력
    
    category VARCHAR(100) NOT NULL,               
    -- 13개 카테고리: 한식, 중식, 일식, 양식, 분식, 치킨, 피자, 
    --              패스트푸드, 아시안, 카페/디저트, 베이커리, 편의점, 마트
    
    address_name TEXT,                            
    is_good_influence_shop BOOLEAN DEFAULT FALSE, 
    is_food_card_shop VARCHAR(10),               -- 'Y', 'N', 'P'(부분), 'U'(미확인)
    
    open_hour VARCHAR(10),                        -- "09:00" (24시간 형식)
    close_hour VARCHAR(10),                       -- "22:00"
    break_start_hour VARCHAR(10),                 
    break_end_hour VARCHAR(10),
    
    phone VARCHAR(20),                            
    owner_message TEXT,                           
    
    latitude DECIMAL(10, 8),                      
    longitude DECIMAL(11, 8),
    
    -- 🔄 [DERIVED] 필드
    current_status VARCHAR(20) DEFAULT 'UNKNOWN', -- OPEN/CLOSED/BREAK_TIME/UNKNOWN
    
    INDEX idx_category (category),
    INDEX idx_good_influence (is_good_influence_shop),
    INDEX idx_food_card (is_food_card_shop)
);
```

### menus 테이블 (메뉴 정보)
```sql
CREATE TABLE menus (
    id INT PRIMARY KEY AUTO_INCREMENT,
    shop_id INT NOT NULL,                         
    
    menu_name VARCHAR(200) NOT NULL,              
    price INT NOT NULL,                           
    description TEXT,                             
    category VARCHAR(100),                        -- 메인메뉴/세트메뉴/사이드메뉴/음료/디저트
    
    FOREIGN KEY (shop_id) REFERENCES shops(id),
    INDEX idx_shop (shop_id),
    INDEX idx_price (price)
);
```

### coupons 테이블 (쿠폰 정보) ⭐ 나비얌 특화
```sql
CREATE TABLE coupons (
    id VARCHAR(50) PRIMARY KEY,
    
    coupon_name VARCHAR(200) NOT NULL,            
    description TEXT,                             
    
    discount_amount INT,                          -- 정액 할인 (원)
    discount_rate DECIMAL(3,2),                   -- 정률 할인 (0.0~1.0)
    min_order_amount INT,                         -- 최소 주문 금액
    
    usage_type VARCHAR(30),                       -- 'ALL', 'SHOP', 'CATEGORY'
    target_categories JSON,                       -- ["한식", "분식"]
    applicable_shops JSON,                        -- [1, 2, 3] shop_id 리스트
    
    valid_from DATE,                              
    valid_until DATE,
    
    -- 🔄 [DERIVED] 필드
    is_active BOOLEAN DEFAULT TRUE,               
    priority_score DECIMAL(3,2),                  -- 0.0~1.0 우선순위
    
    INDEX idx_usage_type (usage_type),
    INDEX idx_active (is_active),
    INDEX idx_valid_dates (valid_from, valid_until)
);
```

### users 테이블 (일반 사용자)
```sql
CREATE TABLE users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    
    name VARCHAR(100),                            
    nickname VARCHAR(100),                        
    birthday DATE,                                
    current_address TEXT,                         
    
    -- 🔄 [DERIVED] 필드
    age_group VARCHAR(20),                        -- '10대', '20대', '30대' 등
    region_code VARCHAR(20)                       
);
```

### foodcard_users 테이블 (급식카드 사용자) ⭐ 나비얌 핵심
```sql
CREATE TABLE foodcard_users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    
    user_id INT NOT NULL,                         
    card_number VARCHAR(50),                      
    balance INT DEFAULT 0,                        -- 현재 잔액
    status VARCHAR(20) DEFAULT 'ACTIVE',          -- ACTIVE/INACTIVE/SUSPENDED/EXPIRED
    
    -- 🔄 [DERIVED] 필드
    target_age_group VARCHAR(20),                 -- '초등학생', '중고등학생', '청년'
    
    FOREIGN KEY (user_id) REFERENCES users(id),
    INDEX idx_user (user_id),
    INDEX idx_status (status)
);
```

### product_orders 테이블 (주문 이력)
```sql
CREATE TABLE product_orders (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    
    -- 🏪 [SAMPLE_DATA] 주문 정보
    product_id INT,                               -- 주문 상품 (메뉴 ID)
    created_at TIMESTAMP,                         -- 주문 시간
    quantity INT,                                 -- 주문 수량
    price INT,                                    -- 주문 금액
    
    -- 🔄 [DERIVED] 선호도 학습용
    order_pattern_score DECIMAL(3,2),             -- 주문 패턴 점수 (0.00~1.00)
    preference_weight DECIMAL(3,2),               -- 선호도 가중치 (0.00~1.00)
    
    FOREIGN KEY (user_id) REFERENCES users(id),
    INDEX idx_user_time (user_id, created_at),
    INDEX idx_product (product_id)
);
```

---

## 5. AI 운영 테이블

### conversations 테이블 (대화 이력)
```sql
CREATE TABLE conversations (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    
    -- 🤖 [CHATBOT_GENERATED] 기본 정보
    user_id VARCHAR(100) NOT NULL,                -- 플랫폼별 다양한 ID 수용
    session_id VARCHAR(200) NOT NULL,             
    conversation_id VARCHAR(200),                 
    
    input_text TEXT NOT NULL,                     
    response_text TEXT NOT NULL,                  
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- 🤖 [CHATBOT_GENERATED] NLU 추출 정보
    extracted_intent VARCHAR(50),                 -- 'food_request', 'budget_inquiry' 등
    intent_confidence DECIMAL(4,3),               -- 0.000~1.000
    extracted_entities JSON,                      -- {"food_type": "치킨", "budget": 5000}
    
    -- 🤖 [CHATBOT_GENERATED] 대화 맥락
    user_strategy VARCHAR(30),                    -- onboarding/data_building/normal/urgent
    conversation_turn INT,                        
    previous_intent VARCHAR(50),                  
    
    -- 성능 지표
    processing_time_ms INT,                       
    nlu_time_ms INT,                             
    response_time_ms INT,                        
    
    INDEX idx_user_timestamp (user_id, timestamp),
    INDEX idx_session (session_id),
    INDEX idx_intent (extracted_intent)
);
```

### user_interactions 테이블 (상세 상호작용)
```sql
CREATE TABLE user_interactions (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    
    -- 🤖 [CHATBOT_GENERATED] 기본 정보
    user_id VARCHAR(100) NOT NULL,                
    session_id VARCHAR(200),                      
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    interaction_type VARCHAR(30),                 
    -- 'text_input', 'selection', 'feedback', 'coupon_use', 'detail_view'
    
    intent VARCHAR(50),                           
    entities JSON,                                
    
    user_selection JSON,                          
    -- {
    --   "shop_id": 15,
    --   "menu_ids": [201, 202],
    --   "coupon_id": "FOOD10",
    --   "final_price": 8000
    -- }
    
    -- 🤖 [CHATBOT_GENERATED] 학습용 특징
    food_preference_extracted VARCHAR(100),       
    budget_pattern_extracted INT,                 
    companion_pattern_extracted VARCHAR(50),      
    
    coupon_usage JSON,                           
    satisfaction_score INT,                      -- 1-5점
    
    INDEX idx_user_timestamp (user_id, timestamp),
    INDEX idx_interaction_type (interaction_type)
);
```

### recommendations_log 테이블 (추천 로그)
```sql
CREATE TABLE recommendations_log (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    
    -- 🤖 [CHATBOT_GENERATED] 기본 정보
    user_id VARCHAR(100) NOT NULL,                
    session_id VARCHAR(200),                      
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- 요청 정보
    request_intent VARCHAR(50),                   
    request_entities JSON,                        
    
    -- 🔄 [DERIVED] 추천 결과
    recommendations JSON NOT NULL,                
    -- [{
    --   "shop_id": 15,
    --   "shop_name": "김밥천국",
    --   "score": 0.92,
    --   "ranking": 1,
    --   "reason": "예산적합+가까움+인기메뉴",
    --   "applicable_coupons": ["FOOD10", "TEEN20"],
    --   "final_price_with_coupon": 3000
    -- }]
    
    recommendation_count INT NOT NULL,            
    recommendation_method VARCHAR(50),            -- wide_deep/rag/hybrid/emergency
    
    confidence_score DECIMAL(4,3),                
    total_discount_available INT,                 
    
    INDEX idx_user_timestamp (user_id, timestamp),
    INDEX idx_method (recommendation_method)
);
```

---

## 6. Intent와 Entities 분리 설계

### Intent (의도) - "사용자가 무엇을 하려고 하는가?"
```python
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

### Entities (엔티티) - "구체적인 정보는 무엇인가?"
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

### 분리의 이점
1. **유연성**: 같은 intent도 다른 entities로 다른 처리
2. **확장성**: 새로운 entity 추가가 쉬움
3. **정확성**: 의도와 정보를 명확히 구분
4. **개인화**: 사용자별 intent/entity 패턴 학습 가능

### 실제 예시
```python
# "친구랑 강남역에서 만원으로 매운 치킨 먹고 싶어"
extracted_intent = 'food_request'
extracted_entities = {
    "food_type": "치킨",
    "budget": 10000,
    "location_preference": "강남역",
    "taste_preference": "매운",
    "companions": "친구"
}
```

---

## 7. 데이터 저장 전략

### 🗄️ DB에 반드시 저장해야 하는 데이터

#### 1. 대화 기록 및 NLU 정보 (conversations)
- `input_text`, `response_text` - 대화 연속성 보장
- `extracted_intent`, `extracted_entities` - 학습 데이터
- `user_strategy`, `conversation_turn` - 개인화된 대화 흐름

**저장 이유**: 컨텍스트 기반 대화, 지속적 학습, 패턴 분석

#### 2. 사용자 상호작용 (user_interactions)
- `user_selection` - 실제 선택 (추천 모델 학습)
- `food_preference_extracted` - 장기적 개인화
- `coupon_usage` - 쿠폰 전략 최적화

**저장 이유**: ML 모델 훈련, 장기적 개인화

#### 3. 추천 로그 (recommendations_log)
- `recommendations` - 추천 결과 및 이유
- `confidence_score` - 추천 신뢰도
- `total_discount_available` - 할인 정보

**저장 이유**: A/B 테스트, 모델 성능 평가

#### 4. 사용자 프로필 (user_profiles)
- `preferred_categories` - 선호 카테고리
- `average_budget` - 평균 예산
- `monthly_stats` - 월별 사용 통계

**저장 이유**: 세션 간 지속되는 개인화

### 💾 메모리/캐시에 보관 가능한 데이터

#### 1. 실시간 계산 결과
- 현재 대화 컨텍스트 (최근 3-5개)
- 실시간 추천 점수 계산
- 현재 세션의 상호작용 패턴

#### 2. 파생 필드
- `current_status` (영업 중/마감 상태)
- `days_until_expiry` (쿠폰 만료일 계산)
- 쿠폰 적용 후 실시간 잔액 계산

### 🔄 하이브리드 접근 방식

#### 캐싱 전략
```python
# 캐시 TTL 설정
CACHE_TTL = {
    'user_profile': 3600,      # 1시간
    'shop_status': 300,        # 5분
    'recommendations': 1800,    # 30분
    'conversation': 86400      # 24시간
}
```

#### 쓰기 패턴
- **즉시 DB 저장**: 사용자 선택, 쿠폰 사용
- **배치 저장**: 성능 로그, 대화 요약
- **비동기 저장**: 상세 분석 데이터

---

## 8. 헷갈리는 부분 정리

### 🔄 유사한 이름의 필드들

#### age_group vs target_age_group
- **users.age_group**: 사용자 실제 나이 기반 ('10대', '20대')
- **foodcard_users.target_age_group**: 급식카드 대상 ('초등학생', '중고등학생')

```python
# 사용 구분
if user.age_group == '10대':           # 일반 추천
    recommend_teen_favorites()
    
if foodcard_user.target_age_group == '초등학생':  # 급식카드 추천
    recommend_snacks_under_5000()
```

#### category 필드들의 계층
- **shops.category**: 가게 업종 (한식, 중식 등 13개)
- **menus.category**: 메뉴 타입 (메인메뉴, 세트메뉴 등)

### 📋 JSON 필드 상세 구조

#### extracted_entities
```json
{
    "food_type": "치킨",          // 선택, shops.category와 다를 수 있음
    "budget": 10000,              // 선택, 항상 정수
    "location": "강남역",          // 선택
    "companions": "친구",          // 선택
    "taste_preference": "매운",     // 선택
    "urgency": "high"             // 선택: high/normal/low
}
```

#### recommendations
```json
[{
    "shop_id": 15,                        // 필수
    "score": 0.92,                        // 필수, 0.0~1.0
    "ranking": 1,                         // 필수
    "reason": "예산적합+가까움+인기메뉴",     // 필수
    "applicable_coupons": ["FOOD10"],      // 선택
    "final_price_with_coupon": 3000       // 선택
}]
```

### 🔗 사용자 ID 타입 차이
```sql
users.id INT                    -- 숫자형 (1, 2, 3)
conversations.user_id VARCHAR   -- 문자형 ("user_123", "kakao_456")
foodcard_users.user_id INT      -- users.id 참조
```

**이유**: conversations는 다양한 플랫폼 ID 수용

### 📊 점수/신뢰도 범위

#### 신뢰도 점수
```python
# intent_confidence: 0.0~1.0
if intent_confidence < 0.5:
    response = "혹시 {} 찾으시는 건가요?"  # 확인 필요

# recommendation_score: 0.0~1.0
score = 0.3 * location_score + 0.3 * preference_score + 
        0.2 * price_score + 0.2 * popularity_score
```

### ⏰ 시간 형식 표준
```sql
open_hour VARCHAR(10)    -- "09:00" (24시간 형식)
close_hour VARCHAR(10)   -- "22:00"

-- 특수 케이스
-- 24시간: open="00:00", close="23:59"
-- 새벽 영업: open="18:00", close="02:00" (다음날)
```

### 🎯 쿠폰 적용 우선순위
```python
def is_coupon_applicable(coupon, shop, order_amount):
    # 1. 최소 금액 확인
    if order_amount < coupon.min_amount:
        return False
    
    # 2. usage_type 확인
    if coupon.usage_type == 'SHOP':
        return shop.id in coupon.applicable_shops
    elif coupon.usage_type == 'CATEGORY':
        return shop.category in coupon.target_categories
    elif coupon.usage_type == 'ALL':
        return True
```

### 📊 주문 패턴 점수와 선호도 가중치

#### order_pattern_score (주문 패턴 점수)
```python
def calculate_order_pattern_score(user_orders):
    """사용자의 주문 패턴을 분석하여 점수화 (0.00~1.00)"""
    
    # 1. 주문 빈도 (40%)
    frequency_score = min(order_count / 30, 1.0) * 0.4  # 월 30회 기준
    
    # 2. 주문 규칙성 (30%)
    # 같은 요일, 같은 시간대 주문 비율
    regularity_score = calculate_time_regularity() * 0.3
    
    # 3. 재주문률 (30%)
    reorder_rate = repeat_orders / total_orders
    reorder_score = reorder_rate * 0.3
    
    return frequency_score + regularity_score + reorder_score
```

**활용:**
- 0.8 이상: 충성 고객, 정기적 패턴 → "매주 금요일 저녁 메뉴"
- 0.5~0.8: 일반 고객 → 표준 추천
- 0.5 미만: 비정기 고객 → 새로운 메뉴 탐색 유도

#### preference_weight (선호도 가중치)
```python
def calculate_preference_weight(product_id, user_id):
    """특정 상품에 대한 사용자의 선호도 가중치 (0.00~1.00)"""
    
    # 1. 구매 횟수 (30%)
    purchase_count = get_purchase_count(user_id, product_id)
    count_weight = min(purchase_count / 5, 1.0) * 0.3  # 5회 이상 만점
    
    # 2. 최근성 (30%)
    days_since_last = get_days_since_last_purchase(user_id, product_id)
    recency_weight = max(1 - (days_since_last / 30), 0) * 0.3
    
    # 3. 구매 금액 비중 (20%)
    total_spent = get_total_spent_on_product(user_id, product_id)
    amount_weight = min(total_spent / user_avg_spending, 1.0) * 0.2
    
    # 4. 카테고리 선호도 (20%)
    category_preference = get_category_preference(user_id, product.category)
    category_weight = category_preference * 0.2
    
    return count_weight + recency_weight + amount_weight + category_weight
```

**Wide&Deep 모델 활용:**
```python
# 추천 점수 계산 시 선호도 가중치 적용
final_score = base_score * (1 + preference_weight * 0.5)
```

### 📋 상태(Status) 값들

#### foodcard_users.status
- `ACTIVE`: 정상 사용 가능
- `INACTIVE`: 일시 정지
- `SUSPENDED`: 이용 정지
- `EXPIRED`: 기간 만료

#### user_strategy
- `onboarding_mode`: 신규 사용자 (1-3회)
- `data_building_mode`: 선호도 파악 중 (4-10회)
- `normal_mode`: 일반 추천 (10회 이상)
- `urgent_mode`: 긴급 모드 (잔액 부족)

---

## 9. 실제 사용 시나리오

### 시나리오 1: "배고픈데 5천원밖에 없어"

#### 1단계: NLU 처리
```python
intent = 'budget_inquiry'
entities = {"budget": 5000, "urgency": "high"}
user_strategy = 'urgent_mode'
```

#### 2단계: 급식카드 확인
```sql
SELECT balance FROM foodcard_users WHERE user_id = ?
-- 결과: balance = 5000
```

#### 3단계: 쿠폰 매칭
```sql
SELECT c.* FROM coupons c
JOIN user_coupon_wallet w ON c.id = w.coupon_id
WHERE w.user_id = ? 
  AND w.status = 'ACTIVE'
  AND c.min_order_amount <= 5000
```

#### 4단계: 응답 생성
```
💬 "잔액이 5천원이네요! 쿠폰 써서 먹을 수 있는 곳 찾았어요! 🎫

**김밥천국** (도보 2분)
- 참치김밥 3,500원
- 🎫 1,000원 할인쿠폰 → 2,500원!

남은 잔액으로도 충분히 맛있게 드실 수 있어요! 😊"
```

### 시나리오 2: "아까 그 치킨집 말고 다른 데"

#### 컨텍스트 활용
```python
# 이전 대화 조회
previous_conversations = get_recent_conversations(user_id, 3)
# → 이전에 '굽네치킨' 추천 확인

# 제외하고 추천
intent = 'food_request'
entities = {
    "food_type": "치킨",
    "exclude_shop": "굽네치킨"
}
```

### 시나리오 3: 월말 쿠폰 만료 알림

```python
# 만료 임박 쿠폰 확인
expiring_coupons = get_expiring_coupons(user_id, days=3)

# 자동 알림
response = """
📢 중요한 알림!

🎫 내일 만료되는 쿠폰:
- 치킨 3,000원 할인 (BBQ)
- 전메뉴 20% 할인 (김밥천국)

잔액 15,000원으로 쿠폰 쓰면 더 저렴해요!
"""
```

---

## 10. 구현 가이드

### 구현 우선순위

#### Phase 1: 핵심 기능 (1-2주)
1. **기본 테이블**: shops, menus, users, foodcard_users
2. **대화 기록**: conversations (NLU 포함)
3. **기본 추천**: recommendations_log

#### Phase 2: 쿠폰 시스템 (1주)
4. **쿠폰 마스터**: coupons
5. **쿠폰 지갑**: user_coupon_wallet
6. **쿠폰 활용**: user_interactions에 쿠폰 사용 기록

#### Phase 3: 고급 개인화 (1주)
7. **사용자 프로필**: user_profiles
8. **성능 모니터링**: performance_logs

### 성능 최적화 전략

#### 1. 인덱스 설계
```sql
-- 자주 사용되는 쿼리용 복합 인덱스
CREATE INDEX idx_shop_food_card_status ON shops(is_food_card_shop, current_status);
CREATE INDEX idx_menu_shop_price ON menus(shop_id, price);
CREATE INDEX idx_conversation_user_intent ON conversations(user_id, extracted_intent);
```

#### 2. 캐싱 전략
```python
# Redis 캐시 활용
@cache(ttl=3600)
def get_user_profile(user_id):
    return db.query("SELECT * FROM user_profiles WHERE user_id = ?", user_id)
```

#### 3. 배치 처리
```python
# 5분마다 학습 데이터 배치 저장
async def save_learning_data_batch():
    while True:
        await asyncio.sleep(300)
        batch_data = collector.get_and_clear_buffers()
        db.bulk_insert_learning_data(batch_data)
```

### 데이터 보존 정책
```sql
-- 보존 규칙
conversations: 활성 사용자 6개월, 비활성 3개월
performance_logs: 상세 30일, 집계 1년
recommendations_log: 무기한 (ML 학습용)
user_interactions: 무기한 (핵심 학습 데이터)
```

### 실무 체크리스트

#### 데이터 일관성 검증
```python
def validate_data_consistency():
    issues = []
    
    # 쿠폰의 가게 존재 여부
    for coupon in coupons:
        if coupon.usage_type == 'SHOP':
            for shop_id in coupon.applicable_shops:
                if shop_id not in shops:
                    issues.append(f"Invalid shop_id {shop_id}")
    
    # foodcard_user의 user 존재 여부
    for fc_user in foodcard_users:
        if fc_user.user_id not in users:
            issues.append(f"Invalid user_id {fc_user.user_id}")
    
    return issues
```

### 모니터링 지표
- 평균 응답 시간: < 500ms 목표
- NLU 정확도: > 85%
- 추천 클릭률: > 30%
- 쿠폰 사용률: > 50%

---

## 🎯 핵심 포인트 요약

1. **Intent와 Entities 분리**: 유연하고 확장 가능한 NLU 설계
2. **하이브리드 저장 전략**: DB와 캐시의 적절한 활용
3. **급식카드 특화**: 잔액 관리와 쿠폰 시스템 통합
4. **개인화 추천**: 사용자 프로필과 대화 컨텍스트 활용
5. **실시간 성능**: 캐싱과 배치 처리로 응답 속도 최적화

이 종합 가이드를 통해 나비얌 챗봇의 데이터베이스 설계부터 구현까지 전체 과정을 이해하고 개발할 수 있습니다.