# 나비얌 챗봇 데이터베이스 종합 가이드 v2 (완전판)

## 목차
1. [개요](#1-개요)
2. [시스템 아키텍처](#2-시스템-아키텍처)
3. [대화 처리 파이프라인](#3-대화-처리-파이프라인)
4. [핵심 데이터 테이블](#4-핵심-데이터-테이블)
5. [AI 운영 테이블](#5-ai-운영-테이블)
6. [성능 최적화 테이블](#6-성능-최적화-테이블)
7. [ML 특징 및 학습 테이블](#7-ml-특징-및-학습-테이블)
8. [분석 및 모니터링 테이블](#8-분석-및-모니터링-테이블)
9. [Intent와 Entities 분리 설계](#9-intent와-entities-분리-설계)
10. [데이터 저장 전략](#10-데이터-저장-전략)
11. [파생 필드 및 특징 엔지니어링](#11-파생-필드-및-특징-엔지니어링)
12. [실제 사용 시나리오](#12-실제-사용-시나리오)
13. [구현 가이드](#13-구현-가이드)

---

## 1. 개요

나비얌 챗봇은 **급식카드 사용자를 위한 AI 기반 맛집 추천 서비스**입니다. LLM + RAG + 추천 시스템을 결합한 하이브리드 아키텍처로 구성되어 있습니다.

### 데이터 소스 구분
- 🏪 **[SAMPLE_DATA]**: sample_data.xlsx에서 제공되는 기본 데이터
- 🤖 **[CHATBOT_GENERATED]**: 챗봇이 대화를 통해 생성하는 데이터
- 🔄 **[DERIVED]**: 기존 데이터를 가공하여 파생된 데이터
- 🚀 **[AI_COMPUTED]**: AI 모델이 계산한 특징 및 점수

### Feature 활용처 범례
- 💬 **챗봇 NLU/NLG**: 자연어 이해 및 응답 생성
- 🔍 **RAG 검색**: 벡터 검색 및 의미적 매칭
- 🎯 **Wide&Deep**: 추천 모델의 Wide/Deep 컴포넌트
- ⭐ **나비얌 특화**: 급식카드 관련 특화 기능
- 📊 **분석/모니터링**: 성능 추적 및 개선

---

## 2. 시스템 아키텍처

### 전체 데이터 흐름
```
사용자 입력 → 전처리 → NLU(의도+엔티티) → RAG 검색 → 추천 모델 → 응답 생성 → 학습 데이터 수집 → DB 저장
                            ↓                    ↓           ↓
                      NLU 캐시/학습        벡터 캐시    특징 저장
```

### 주요 컴포넌트
1. **NLU (자연어 이해)**: Intent 분류 + Entity 추출 + 신뢰도 평가
2. **RAG (검색 증강 생성)**: 의미적 유사도 기반 가게/메뉴 검색 + 캐싱
3. **Wide&Deep 추천**: 개인화된 추천 순위 결정 + 특징 엔지니어링
4. **쿠폰 시스템**: 급식카드 잔액 부족 시 할인 매칭 + 지갑 관리
5. **성능 모니터링**: 실시간 성능 추적 + 병목 지점 파악
6. **학습 시스템**: LoRA 파인튜닝 + 지속적 개선

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

# 3. 컨텍스트 로드 (conversation_contexts 테이블)
context = db.get_conversation_context(session_id, user_id)
```

### Phase 2: NLU 처리 (Intent + Entities 추출)
```python
# 4. NLU 캐시 확인 (nlu_training_data 테이블)
cached_nlu = check_nlu_cache(preprocessed.normalized_text)

if not cached_nlu:
    # 5. Smart NLU Processing
    extracted_info = self._smart_nlu_processing(user_input, preprocessed)
    
    # 6. NLU 결과 저장 (학습용)
    save_nlu_training_data(user_input.text, extracted_info)
```

### Phase 3: RAG 검색 및 특징 추출
```python
# 7. RAG 캐시 확인 (rag_query_cache 테이블)
query_hash = hash_query(extracted_info)
cached_results = get_rag_cache(query_hash)

if not cached_results:
    # 8. 임베딩 생성/조회 (embedding_cache 테이블)
    query_embedding = get_or_create_embedding(user_input.text)
    
    # 9. 벡터 검색 수행
    rag_results = perform_vector_search(query_embedding)
    save_rag_cache(query_hash, rag_results)

# 10. 특징 추출 (feature_vectors 테이블)
features = extract_features(user_id, rag_results, extracted_info)
```

### Phase 4: 추천 및 응답 생성
```python
# 11. 추천 특징 계산 (recommendation_features 테이블)
rec_features = calculate_recommendation_features(user_id, candidate_shops)

# 12. Wide&Deep 모델 스코어링
final_scores = wide_deep_model.predict(rec_features)

# 13. 쿠폰 적용 (user_coupon_wallet 테이블)
apply_coupons(recommendations, user_id)

# 14. 응답 생성 및 성능 기록 (performance_logs 테이블)
response = generate_response(recommendations)
log_performance(start_time, response_time, component_times)
```

---

## 4. 핵심 데이터 테이블

### shops 테이블 (가게 정보) - 확장 버전
```sql
CREATE TABLE shops (
    id INT PRIMARY KEY AUTO_INCREMENT,
    
    -- 🏪 [SAMPLE_DATA] 기본 필드
    shop_name VARCHAR(200) NOT NULL,              
    category VARCHAR(100) NOT NULL,               -- 13개 카테고리
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
    
    -- 🔄 [DERIVED] 실시간 상태
    current_status VARCHAR(20) DEFAULT 'UNKNOWN', -- OPEN/CLOSED/BREAK_TIME/UNKNOWN
    
    -- 🚀 [AI_COMPUTED] 성능 지표
    recommendation_count INT DEFAULT 0,           -- 총 추천 횟수
    click_through_rate DECIMAL(5,4) DEFAULT 0.0,  -- 클릭률 (0.0000~1.0000)
    conversion_rate DECIMAL(5,4) DEFAULT 0.0,     -- 전환율 (실제 방문/주문)
    
    -- 🚀 [AI_COMPUTED] AI 파생 특징
    popularity_score DECIMAL(4,3) DEFAULT 0.0,    -- 인기도 점수 (0.000~1.000)
    quality_score DECIMAL(4,3) DEFAULT 0.0,       -- 품질 점수 (리뷰 기반)
    user_satisfaction_avg DECIMAL(3,2) DEFAULT 0.0, -- 평균 만족도 (0.00~5.00)
    
    -- 🚀 [AI_COMPUTED] 운영 지표
    last_recommended TIMESTAMP,                   -- 마지막 추천 시각
    total_orders_served INT DEFAULT 0,            -- 총 주문 처리 수
    avg_order_value DECIMAL(8,2) DEFAULT 0.0,    -- 평균 주문 금액
    
    -- 🔍 [AI_COMPUTED] 벡터 검색용
    description_embedding JSON,                   -- 가게 설명 임베딩 벡터
    menu_summary_embedding JSON,                  -- 메뉴 요약 임베딩
    
    INDEX idx_category (category),
    INDEX idx_good_influence (is_good_influence_shop),
    INDEX idx_food_card (is_food_card_shop),
    INDEX idx_popularity (popularity_score),
    INDEX idx_quality (quality_score),
    INDEX idx_last_recommended (last_recommended)
);
```

### menus 테이블 (메뉴 정보) - 확장 버전
```sql
CREATE TABLE menus (
    id INT PRIMARY KEY AUTO_INCREMENT,
    shop_id INT NOT NULL,                         
    
    -- 🏪 [SAMPLE_DATA] 기본 정보
    menu_name VARCHAR(200) NOT NULL,              
    price INT NOT NULL,                           
    description TEXT,                             
    category VARCHAR(100),                        -- 메인메뉴/세트메뉴/사이드메뉴/음료/디저트
    
    -- 🚀 [AI_COMPUTED] ML 특징
    recommendation_frequency INT DEFAULT 0,       -- 추천된 횟수
    user_preference_score DECIMAL(4,3) DEFAULT 0.0, -- 사용자 선호도 점수
    seasonal_popularity JSON,                     -- {"1월": 0.8, "2월": 0.6, ...}
    
    -- 🚀 [AI_COMPUTED] 영양 AI 특징
    estimated_calories INT,                       -- 추정 칼로리
    healthiness_score DECIMAL(3,2),              -- 건강도 점수 (0.00~5.00)
    dietary_tags JSON,                           -- ["vegetarian", "spicy", "low-sodium"]
    
    -- 🔍 [AI_COMPUTED] 벡터 검색용
    description_embedding JSON,                   -- 메뉴 설명 임베딩
    ingredient_embedding JSON,                    -- 재료 기반 임베딩
    
    FOREIGN KEY (shop_id) REFERENCES shops(id),
    INDEX idx_shop (shop_id),
    INDEX idx_price (price),
    INDEX idx_preference_score (user_preference_score),
    INDEX idx_calories (estimated_calories)
);
```

### coupons 테이블 (쿠폰 정보) ⭐ 나비얌 특화
```sql
CREATE TABLE coupons (
    id VARCHAR(50) PRIMARY KEY,
    
    coupon_name VARCHAR(200) NOT NULL,            
    description TEXT,                             
    
    discount_amount INT,                          -- 정액 할인 (원)
    discount_rate DECIMAL(3,2),                   -- 정률 할인 (0.00~1.00)
    min_order_amount INT,                         -- 최소 주문 금액
    
    usage_type VARCHAR(30),                       -- 'ALL', 'SHOP', 'CATEGORY', 'FOODCARD'
    target_categories JSON,                       -- ["한식", "분식"]
    applicable_shops JSON,                        -- [1, 2, 3] shop_id 리스트
    
    valid_from DATE,                              
    valid_until DATE,
    
    -- 🔄 [DERIVED] 필드
    is_active BOOLEAN DEFAULT TRUE,               
    priority_score DECIMAL(3,2),                  -- 0.00~1.00 우선순위
    
    -- 🚀 [AI_COMPUTED] 사용 분석
    total_issued INT DEFAULT 0,                   -- 총 발급 수
    total_used INT DEFAULT 0,                     -- 총 사용 수
    avg_order_increase DECIMAL(8,2),              -- 평균 주문액 증가
    user_satisfaction_impact DECIMAL(3,2),        -- 만족도 영향 (0.00~5.00)
    
    INDEX idx_usage_type (usage_type),
    INDEX idx_active (is_active),
    INDEX idx_valid_dates (valid_from, valid_until)
);
```

### users 테이블 (일반 사용자) - 확장 버전
```sql
CREATE TABLE users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    
    -- 🏪 [SAMPLE_DATA] 기본 정보
    name VARCHAR(100),                            
    nickname VARCHAR(100),                        
    birthday DATE,                                
    current_address TEXT,                         
    
    -- 🔄 [DERIVED] 필드
    age_group VARCHAR(20),                        -- '10대', '20대', '30대' 등
    region_code VARCHAR(20),                      
    
    -- 🚀 [AI_COMPUTED] AI 학습 특징
    interaction_patterns JSON,                    -- 상호작용 패턴 분석
    -- {
    --   "peak_hours": [12, 18, 19],
    --   "preferred_days": ["Friday", "Saturday"],
    --   "avg_session_length": 180,
    --   "interaction_style": "quick_decision"
    -- }
    
    preference_evolution JSON,                    -- 선호도 변화 추적
    -- {
    --   "2024-01": {"한식": 0.7, "중식": 0.3},
    --   "2024-02": {"한식": 0.5, "치킨": 0.5}
    -- }
    
    context_preferences JSON,                     -- 상황별 선호도
    -- {
    --   "lunch": {"categories": ["한식", "분식"], "budget": 8000},
    --   "dinner_with_friends": {"categories": ["치킨", "피자"], "budget": 15000}
    -- }
    
    -- 🚀 [AI_COMPUTED] 참여 지표
    session_frequency DECIMAL(4,2) DEFAULT 0.0,   -- 주간 평균 세션 수
    avg_session_duration INT DEFAULT 0,           -- 평균 세션 시간(초)
    churn_probability DECIMAL(4,3) DEFAULT 0.0,   -- 이탈 확률 (0.000~1.000)
    lifetime_value_score DECIMAL(6,2) DEFAULT 0.0, -- LTV 점수
    
    -- 🚀 [AI_COMPUTED] 개인화 수준
    personalization_completeness DECIMAL(3,2) DEFAULT 0.0, -- 프로필 완성도
    model_confidence DECIMAL(4,3) DEFAULT 0.0,    -- 모델 신뢰도
    
    INDEX idx_age_group (age_group),
    INDEX idx_churn_prob (churn_probability)
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
    
    -- 🚀 [AI_COMPUTED] 사용 패턴
    monthly_usage_pattern JSON,                   -- 월별 사용 패턴
    -- {
    --   "week1": {"amount": 35000, "count": 7},
    --   "week2": {"amount": 30000, "count": 6},
    --   "week3": {"amount": 25000, "count": 5},
    --   "week4": {"amount": 10000, "count": 2}  -- 월말 잔액 부족
    -- }
    
    balance_alert_sent BOOLEAN DEFAULT FALSE,     -- 잔액 부족 알림 발송 여부
    emergency_coupon_eligible BOOLEAN DEFAULT TRUE, -- 긴급 쿠폰 자격
    
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
    
    -- 🚀 [AI_COMPUTED] 추가 분석
    time_since_last_order INT,                    -- 이전 주문과의 간격(일)
    is_reorder BOOLEAN DEFAULT FALSE,             -- 재주문 여부
    order_context VARCHAR(50),                    -- 'regular', 'exploration', 'emergency'
    
    FOREIGN KEY (user_id) REFERENCES users(id),
    INDEX idx_user_time (user_id, created_at),
    INDEX idx_product (product_id),
    INDEX idx_pattern_score (order_pattern_score)
);
```

### user_coupon_wallet 테이블 (사용자 쿠폰 지갑) ⭐ 신규
```sql
CREATE TABLE user_coupon_wallet (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    
    user_id INT NOT NULL,
    coupon_id VARCHAR(50) NOT NULL,
    
    -- 지갑 관리
    acquired_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expiry_date TIMESTAMP,
    usage_date TIMESTAMP NULL,
    status VARCHAR(20) DEFAULT 'ACTIVE',          -- 'ACTIVE', 'USED', 'EXPIRED'
    
    -- 사용 컨텍스트
    used_shop_id INT,
    used_menu_id INT,
    used_order_amount INT,
    discount_applied INT,
    
    -- 획득 경로
    acquisition_source VARCHAR(50),               -- 'welcome_bonus', 'loyalty_reward', 'emergency_assist'
    acquisition_context JSON,                     -- 획득 상황 상세 정보
    
    -- 🚀 [AI_COMPUTED] 사용 예측
    usage_probability DECIMAL(4,3),               -- 사용 가능성 (0.000~1.000)
    recommended_usage_date DATE,                  -- AI 추천 사용일
    
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (coupon_id) REFERENCES coupons(id),
    UNIQUE KEY unique_user_coupon_active (user_id, coupon_id, status),
    INDEX idx_user_status (user_id, status),
    INDEX idx_expiry (expiry_date),
    INDEX idx_usage_prob (usage_probability)
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
    
    -- 🚀 [AI_COMPUTED] 품질 지표
    response_quality_score DECIMAL(4,3),          -- 응답 품질 점수
    user_satisfaction_inferred DECIMAL(4,3),      -- 추론된 만족도
    conversation_coherence DECIMAL(4,3),          -- 대화 일관성
    
    INDEX idx_user_timestamp (user_id, timestamp),
    INDEX idx_session (session_id),
    INDEX idx_intent (extracted_intent)
);
```

### conversation_contexts 테이블 (세션 컨텍스트 관리) 🆕
```sql
CREATE TABLE conversation_contexts (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    
    -- 컨텍스트 식별
    session_id VARCHAR(200) NOT NULL,
    user_id VARCHAR(100) NOT NULL,
    conversation_turn INT NOT NULL,
    
    -- 컨텍스트 데이터
    context_data JSON NOT NULL,                   -- 전체 대화 컨텍스트
    -- {
    --   "mentioned_shops": [1, 15, 23],
    --   "mentioned_categories": ["치킨", "한식"],
    --   "budget_constraints": [5000, 10000],
    --   "time_constraints": ["lunch", "now"],
    --   "dietary_restrictions": ["no_spicy"],
    --   "companion_info": "friends"
    -- }
    
    user_state JSON,                              -- 현재 사용자 상태
    -- {
    --   "strategy": "data_building_mode",
    --   "completeness": 0.65,
    --   "engagement_level": "high",
    --   "frustration_score": 0.2
    -- }
    
    extracted_patterns JSON,                      -- 추출된 대화 패턴
    -- {
    --   "decision_style": "exploratory",
    --   "price_sensitivity": "high",
    --   "brand_loyalty": "low"
    -- }
    
    -- 컨텍스트 메타데이터
    context_type VARCHAR(50),                     -- 'onboarding', 'data_building', 'normal', 'urgent'
    importance_score DECIMAL(3,2),                -- 중요도 점수 (0.00~1.00)
    
    -- 시간 관리
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,                         -- 컨텍스트 만료 시간
    
    INDEX idx_session_turn (session_id, conversation_turn),
    INDEX idx_user_timestamp (user_id, timestamp),
    INDEX idx_context_type (context_type)
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
    -- 'scroll', 'hover', 'copy_info', 'share', 'bookmark'
    
    intent VARCHAR(50),                           
    entities JSON,                                
    
    user_selection JSON,                          
    -- {
    --   "shop_id": 15,
    --   "menu_ids": [201, 202],
    --   "coupon_id": "FOOD10",
    --   "final_price": 8000,
    --   "selection_time_ms": 3500,
    --   "alternatives_viewed": [14, 16]
    -- }
    
    -- 🤖 [CHATBOT_GENERATED] 학습용 특징
    food_preference_extracted VARCHAR(100),       
    budget_pattern_extracted INT,                 
    companion_pattern_extracted VARCHAR(50),      
    
    coupon_usage JSON,                           
    satisfaction_score INT,                      -- 1-5점
    
    -- 🚀 [AI_COMPUTED] 행동 분석
    interaction_sequence_pattern VARCHAR(100),    -- 상호작용 순서 패턴
    decision_confidence DECIMAL(4,3),             -- 결정 확신도
    exploration_score DECIMAL(4,3),               -- 탐색 성향 점수
    
    INDEX idx_user_timestamp (user_id, timestamp),
    INDEX idx_interaction_type (interaction_type),
    INDEX idx_decision_confidence (decision_confidence)
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
    --   "reason_breakdown": {
    --     "budget_fit": 0.95,
    --     "distance_score": 0.88,
    --     "popularity": 0.91,
    --     "personal_preference": 0.85
    --   },
    --   "applicable_coupons": ["FOOD10", "TEEN20"],
    --   "final_price_with_coupon": 3000
    -- }]
    
    recommendation_count INT NOT NULL,            
    recommendation_method VARCHAR(50),            -- wide_deep/rag/hybrid/emergency/coupon_based
    
    confidence_score DECIMAL(4,3),                
    total_discount_available INT,                 
    
    -- 🚀 [AI_COMPUTED] 추천 품질
    diversity_score DECIMAL(4,3),                 -- 다양성 점수
    personalization_score DECIMAL(4,3),           -- 개인화 점수
    relevance_score DECIMAL(4,3),                 -- 관련성 점수
    novelty_score DECIMAL(4,3),                   -- 새로움 점수
    
    -- 사용자 반응
    user_viewed_details JSON,                     -- 상세 조회한 추천 ID들
    user_final_selection INT,                     -- 최종 선택한 shop_id
    time_to_decision_ms INT,                      -- 결정까지 걸린 시간
    
    INDEX idx_user_timestamp (user_id, timestamp),
    INDEX idx_method (recommendation_method),
    INDEX idx_personalization (personalization_score)
);
```

---

## 6. 성능 최적화 테이블

### performance_logs 테이블 (시스템 성능 추적) 🆕
```sql
CREATE TABLE performance_logs (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    
    -- 성능 메트릭
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    operation_type VARCHAR(50) NOT NULL,          -- 'nlu_processing', 'rag_search', 'recommendation', 'response_generation'
    
    -- 시간 측정 (밀리초)
    processing_time_ms INT,
    nlu_time_ms INT,
    rag_time_ms INT,
    recommendation_time_ms INT,
    response_generation_time_ms INT,
    total_time_ms INT,
    
    -- 리소스 사용량
    memory_usage_mb FLOAT,
    cpu_usage_percent FLOAT,
    gpu_usage_percent FLOAT,
    cache_hit_rate DECIMAL(4,3),                  -- 캐시 히트율 (0.000~1.000)
    
    -- 품질 메트릭
    confidence_score DECIMAL(4,3),
    success BOOLEAN DEFAULT TRUE,
    error_type VARCHAR(100),
    error_message TEXT,
    
    -- 컨텍스트
    user_id VARCHAR(100),
    session_id VARCHAR(200),
    request_complexity VARCHAR(20),               -- 'simple', 'moderate', 'complex'
    
    -- 병목 지점 분석
    bottleneck_component VARCHAR(50),             -- 가장 느린 컴포넌트
    optimization_suggestions JSON,                -- AI가 제안하는 최적화 방법
    
    INDEX idx_timestamp (timestamp),
    INDEX idx_operation_type (operation_type),
    INDEX idx_user_session (user_id, session_id),
    INDEX idx_total_time (total_time_ms)
);
```

### rag_query_cache 테이블 (RAG 성능 최적화) 🆕
```sql
CREATE TABLE rag_query_cache (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    
    -- 쿼리 정보
    query_hash VARCHAR(64) NOT NULL UNIQUE,       -- SHA-256 of normalized query
    original_query TEXT NOT NULL,
    normalized_query TEXT NOT NULL,
    
    -- RAG 결과
    retrieved_documents JSON,                     -- 문서 ID와 점수
    -- [{
    --   "doc_id": "shop_15_desc",
    --   "score": 0.89,
    --   "type": "shop_description"
    -- }]
    
    vector_search_results JSON,                   -- 벡터 검색 결과
    semantic_similarity_scores JSON,              -- 의미적 유사도 점수
    
    -- 성능 데이터
    search_time_ms INT,
    total_documents_searched INT,
    cache_hit_count INT DEFAULT 0,
    avg_response_time_ms INT,                     -- 평균 응답 시간
    
    -- 캐시 관리
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    access_count INT DEFAULT 1,
    ttl_seconds INT DEFAULT 3600,                 -- Time To Live
    
    -- 품질 지표
    result_quality_score DECIMAL(4,3),            -- 결과 품질 점수
    user_satisfaction_rate DECIMAL(4,3),          -- 사용자 만족률
    
    INDEX idx_query_hash (query_hash),
    INDEX idx_created (created_at),
    INDEX idx_last_accessed (last_accessed),
    INDEX idx_access_count (access_count)
);
```

### embedding_cache 테이블 (벡터 캐싱) 🆕
```sql
CREATE TABLE embedding_cache (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    
    -- 컨텐츠 식별
    content_hash VARCHAR(64) NOT NULL UNIQUE,     -- SHA-256 해시
    content_type VARCHAR(50) NOT NULL,            -- 'query', 'shop_description', 'menu_description', 'user_review'
    original_content TEXT NOT NULL,
    
    -- 임베딩 데이터
    embedding_vector JSON NOT NULL,               -- 임베딩 벡터 (예: 768차원)
    embedding_model VARCHAR(100),                 -- 'sentence-transformers/xlm-r-100langs-bert-base-nli-stsb-mean-tokens'
    embedding_dimension INT,                      -- 벡터 차원
    
    -- 캐시 관리
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    access_count INT DEFAULT 1,
    computation_time_ms INT,                      -- 생성 시간
    
    -- 품질 관리
    vector_norm FLOAT,                           -- 벡터 노름 (품질 체크용)
    is_valid BOOLEAN DEFAULT TRUE,               -- 유효성 검증
    
    INDEX idx_content_hash (content_hash),
    INDEX idx_content_type (content_type),
    INDEX idx_last_accessed (last_accessed),
    INDEX idx_model (embedding_model)
);
```

---

## 7. ML 특징 및 학습 테이블

### feature_vectors 테이블 (ML 특징 저장) 🆕
```sql
CREATE TABLE feature_vectors (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    
    -- 엔티티 정보
    entity_type VARCHAR(50) NOT NULL,             -- 'user', 'shop', 'menu', 'interaction'
    entity_id VARCHAR(100) NOT NULL,
    
    -- 벡터 데이터
    feature_vector_dense JSON,                    -- Dense features for Wide&Deep
    -- {
    --   "avg_order_value": 0.65,
    --   "visit_frequency": 0.82,
    --   "price_sensitivity": 0.91,
    --   "category_diversity": 0.45
    -- }
    
    feature_vector_sparse JSON,                   -- Sparse categorical features
    -- {
    --   "preferred_categories": ["한식", "중식"],
    --   "preferred_time_slots": ["lunch", "dinner"],
    --   "dietary_restrictions": ["no_spicy"]
    -- }
    
    embedding_vector JSON,                        -- Learned embeddings (예: 128차원)
    
    -- 특징 엔지니어링 컨텍스트
    feature_extraction_method VARCHAR(100),       -- 'rule_based', 'ml_derived', 'hybrid'
    feature_version VARCHAR(20),                  -- 버전 관리
    confidence_score DECIMAL(4,3),               
    
    -- 시간 정보
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    valid_until TIMESTAMP,                        -- 유효 기간
    
    -- 특징 중요도
    feature_importance JSON,                      -- 각 특징의 중요도
    -- {
    --   "avg_order_value": 0.85,
    --   "visit_frequency": 0.72,
    --   "price_sensitivity": 0.93
    -- }
    
    INDEX idx_entity (entity_type, entity_id),
    INDEX idx_version (feature_version),
    INDEX idx_created (created_at),
    INDEX idx_valid_until (valid_until)
);
```

### recommendation_features 테이블 (추천 특징 상세) 🆕
```sql
CREATE TABLE recommendation_features (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    
    -- 추천 컨텍스트
    user_id VARCHAR(100) NOT NULL,
    shop_id INT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Layer 1 Features (Funnel Scores)
    collaborative_score DECIMAL(4,3),             -- 협업 필터링 점수
    content_score DECIMAL(4,3),                   -- 콘텐츠 기반 점수
    contextual_score DECIMAL(4,3),                -- 컨텍스트 점수
    popularity_score DECIMAL(4,3),                -- 인기도 점수
    
    -- Wide Features (Engineered)
    category_preference_match DECIMAL(4,3),       -- 카테고리 선호도 매칭
    budget_compatibility DECIMAL(4,3),            -- 예산 적합도
    distance_penalty DECIMAL(4,3),                -- 거리 페널티
    time_preference_match DECIMAL(4,3),           -- 시간대 선호도 매칭
    visited_before BOOLEAN,                       -- 이전 방문 여부
    similar_user_liked DECIMAL(4,3),              -- 유사 사용자 선호도
    
    -- Deep Features (Numerical)
    user_avg_budget_normalized DECIMAL(4,3),      -- 정규화된 평균 예산
    user_favorite_count_normalized DECIMAL(4,3),  -- 정규화된 즐겨찾기 수
    shop_rating_normalized DECIMAL(4,3),          -- 정규화된 가게 평점
    shop_review_count_normalized DECIMAL(4,3),    -- 정규화된 리뷰 수
    distance_normalized DECIMAL(4,3),             -- 정규화된 거리
    
    -- Cross Features (교차 특징)
    user_category_interaction DECIMAL(4,3),       -- user × category 상호작용
    budget_time_interaction DECIMAL(4,3),         -- budget × time 상호작용
    location_category_interaction DECIMAL(4,3),   -- location × category 상호작용
    
    -- 최종 예측
    predicted_score DECIMAL(4,3),                 -- Wide&Deep 모델 예측 점수
    ranking_position INT,                         -- 최종 순위
    
    -- 설명 가능성
    feature_contributions JSON,                   -- 각 특징의 기여도
    -- {
    --   "category_preference_match": 0.25,
    --   "budget_compatibility": 0.18,
    --   "distance_penalty": -0.12,
    --   "popularity_score": 0.15
    -- }
    
    FOREIGN KEY (shop_id) REFERENCES shops(id),
    INDEX idx_user_timestamp (user_id, timestamp),
    INDEX idx_shop_score (shop_id, predicted_score),
    INDEX idx_ranking (ranking_position)
);
```

### nlu_training_data 테이블 (NLU 학습 데이터) 🆕
```sql
CREATE TABLE nlu_training_data (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    
    -- 입력 데이터
    input_text TEXT NOT NULL,
    normalized_text TEXT,
    
    -- NLU 출력
    predicted_intent VARCHAR(50),
    intent_confidence DECIMAL(4,3),
    extracted_entities JSON,
    
    -- Ground Truth (학습용)
    true_intent VARCHAR(50),
    true_entities JSON,
    
    -- 품질 메트릭
    prediction_accuracy DECIMAL(4,3),             -- 예측 정확도
    entity_extraction_f1 DECIMAL(4,3),            -- 엔티티 추출 F1 점수
    
    -- 학습 컨텍스트
    user_id VARCHAR(100),
    feedback_provided BOOLEAN DEFAULT FALSE,      -- 사용자 피드백 여부
    correction_applied BOOLEAN DEFAULT FALSE,     -- 수정 적용 여부
    
    -- 데이터 관리
    data_source VARCHAR(50),                      -- 'user_interaction', 'synthetic', 'corrected', 'augmented'
    quality_score DECIMAL(3,2),                   -- 데이터 품질 점수
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- 학습 상태
    used_for_training BOOLEAN DEFAULT FALSE,      -- 학습에 사용됨
    training_batch_id VARCHAR(100),               -- 학습 배치 ID
    model_version VARCHAR(20),                    -- 사용된 모델 버전
    
    INDEX idx_intent (predicted_intent),
    INDEX idx_quality (quality_score),
    INDEX idx_created (created_at),
    INDEX idx_training_status (used_for_training)
);
```

### model_training_logs 테이블 (LoRA 훈련 관리) 🆕
```sql
CREATE TABLE model_training_logs (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    
    -- 훈련 세션 정보
    training_session_id VARCHAR(200) NOT NULL,
    model_type VARCHAR(50),                       -- 'lora_adapter', 'base_model', 'embeddings'
    training_start_time TIMESTAMP,
    training_end_time TIMESTAMP,
    
    -- 훈련 설정
    model_name VARCHAR(200),                      -- 'beomi/KoAlpaca-Polyglot-5.8B'
    lora_rank INT,                               -- 8, 16, 32
    lora_alpha INT,                              -- 16, 32
    lora_dropout DECIMAL(3,2),                   -- 0.05
    learning_rate DECIMAL(10,8),                 -- 0.0001
    batch_size INT,                              -- 4, 8, 16
    epochs INT,                                  -- 3, 5, 10
    
    -- 훈련 진행
    current_epoch INT,
    current_step INT,
    total_steps INT,
    training_loss DECIMAL(10,6),
    validation_loss DECIMAL(10,6),
    best_validation_loss DECIMAL(10,6),
    
    -- 데이터 품질
    training_samples_count INT,
    validation_samples_count INT,
    data_quality_score DECIMAL(3,2),
    class_balance JSON,                          -- 클래스별 샘플 수
    
    -- 모델 성능
    final_model_path VARCHAR(500),
    checkpoint_paths JSON,                       -- 체크포인트 경로들
    evaluation_metrics JSON,                     -- 평가 지표
    -- {
    --   "accuracy": 0.92,
    --   "f1_score": 0.89,
    --   "precision": 0.91,
    --   "recall": 0.87
    -- }
    
    deployment_status VARCHAR(50),               -- 'training', 'completed', 'deployed', 'failed'
    deployment_timestamp TIMESTAMP,
    
    -- 리소스 사용
    gpu_hours DECIMAL(10,2),
    peak_memory_gb FLOAT,
    
    INDEX idx_session (training_session_id),
    INDEX idx_status (deployment_status),
    INDEX idx_model_type (model_type)
);
```

---

## 8. 분석 및 모니터링 테이블

### user_journey_analytics 테이블 (사용자 여정 분석) 🆕
```sql
CREATE TABLE user_journey_analytics (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    
    -- 여정 식별
    user_id VARCHAR(100) NOT NULL,
    journey_session_id VARCHAR(200),
    journey_start TIMESTAMP,
    journey_end TIMESTAMP,
    
    -- 여정 단계
    onboarding_completed BOOLEAN DEFAULT FALSE,
    first_recommendation_received BOOLEAN DEFAULT FALSE,
    first_selection_made BOOLEAN DEFAULT FALSE,
    personalization_achieved BOOLEAN DEFAULT FALSE,
    
    -- 여정 메트릭
    total_interactions INT DEFAULT 0,
    successful_recommendations INT DEFAULT 0,
    recommendation_acceptance_rate DECIMAL(4,3),
    average_session_duration INT,                 -- 초 단위
    
    -- 전환 퍼널
    funnel_stage VARCHAR(50),                     -- 'awareness', 'interest', 'consideration', 'conversion', 'retention'
    conversion_probability DECIMAL(4,3),
    drop_off_point VARCHAR(100),                 -- 이탈 지점
    
    -- 사용자 만족도
    satisfaction_signals JSON,                    -- 만족도 신호
    -- {
    --   "positive_feedback_count": 5,
    --   "negative_feedback_count": 1,
    --   "avg_response_time": 2.3,
    --   "reengagement_rate": 0.8
    -- }
    
    -- 개인화 진행도
    personalization_milestones JSON,              -- 개인화 마일스톤
    -- {
    --   "preferences_identified": true,
    --   "budget_pattern_learned": true,
    --   "time_preference_detected": false,
    --   "companion_patterns_found": true
    -- }
    
    INDEX idx_user_journey (user_id, journey_session_id),
    INDEX idx_funnel_stage (funnel_stage),
    INDEX idx_journey_start (journey_start)
);
```

### user_profiles 테이블 (종합 프로필) 🆕
```sql
CREATE TABLE user_profiles (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    
    -- 🤖 [CHATBOT_GENERATED] 필드
    user_id VARCHAR(100) PRIMARY KEY,             
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    -- 🤖 [CHATBOT_GENERATED] 개인화 정보
    preferred_categories JSON,                    -- ["치킨", "한식", "분식"]
    average_budget INT,                           
    good_influence_preference DECIMAL(3,2),       -- 착한가게 선호도
    interaction_count INT DEFAULT 0,              
    
    -- 🔄 [DERIVED] 필드
    favorite_shops JSON,                          -- [15, 23, 45]
    recent_orders JSON,                           -- 최근 10개 주문
    coupon_preference JSON,                       -- 쿠폰 사용 패턴
    monthly_stats JSON,                           -- 월별 통계
    
    -- 🚀 [AI_COMPUTED] 고급 프로필
    personality_type VARCHAR(50),                 -- 'explorer', 'loyalist', 'deal_seeker', 'convenience_first'
    decision_making_speed VARCHAR(20),            -- 'quick', 'moderate', 'deliberate'
    price_elasticity DECIMAL(4,3),               -- 가격 민감도
    brand_loyalty_score DECIMAL(4,3),            -- 브랜드 충성도
    
    -- 🚀 [AI_COMPUTED] 예측 모델
    next_order_prediction JSON,                   -- 다음 주문 예측
    -- {
    --   "predicted_date": "2024-02-15",
    --   "predicted_category": "치킨",
    --   "predicted_budget": 15000,
    --   "confidence": 0.78
    -- }
    
    churn_risk_factors JSON,                      -- 이탈 위험 요인
    -- {
    --   "last_order_days_ago": 15,
    --   "satisfaction_declining": true,
    --   "budget_constraints_increasing": true
    -- }
    
    INDEX idx_updated (last_updated),
    INDEX idx_personality (personality_type)
);
```

---

## 9. Intent와 Entities 분리 설계

### Intent (의도) - "사용자가 무엇을 하려고 하는가?"
```python
IntentType = {
    'food_request': '특정 음식 추천 요청',      # "치킨 먹고 싶어"
    'budget_inquiry': '예산 제약 음식 찾기',    # "5천원으로 뭐 먹지?"
    'coupon_inquiry': '쿠폰 정보 문의',        # "할인 쿠폰 있어?"
    'location_inquiry': '위치 기반 검색',       # "근처 맛집 알려줘"
    'time_inquiry': '영업시간 관련 문의',       # "지금 열린 곳 있어?"
    'general_chat': '일반 대화',              # "안녕하세요"
    'menu_option': '메뉴 옵션 문의',           # "매운거 빼고"
    'emergency_food': '긴급 식사 필요',        # "지금 당장 먹을 수 있는"
    'group_dining': '단체 식사 문의',          # "10명이 먹을 수 있는"
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
    dietary_restrictions: Optional[List[str]] = None  # ["vegetarian", "halal", "no_pork"]
    portion_size: Optional[str] = None     # "large", "normal", "small"
```

---

## 10. 데이터 저장 전략

### 🗄️ DB에 반드시 저장해야 하는 데이터

#### 핵심 비즈니스 데이터
1. **대화 기록** (conversations) - 법적 요구사항, 학습 데이터
2. **사용자 프로필** (user_profiles) - 장기 개인화
3. **추천 로그** (recommendations_log) - A/B 테스트, 성능 평가
4. **주문 이력** (product_orders) - 매출 분석, 패턴 학습
5. **쿠폰 사용** (user_coupon_wallet) - 재무 추적, 마케팅 분석

#### ML/AI 필수 데이터
1. **학습 데이터** (nlu_training_data) - 모델 개선
2. **특징 벡터** (feature_vectors) - 재학습 시 필요
3. **모델 훈련 로그** (model_training_logs) - 버전 관리
4. **사용자 여정** (user_journey_analytics) - 장기 행동 분석

### 💾 메모리/캐시에 보관 가능한 데이터

#### 실시간 계산 데이터
1. **현재 대화 컨텍스트** - Redis, TTL 24시간
2. **실시간 추천 점수** - 메모리, 세션 종료 시 삭제
3. **임시 NLU 결과** - 메모리, 5분 TTL

#### 자주 접근하는 캐시 데이터
1. **임베딩 벡터** (embedding_cache) - Redis, TTL 7일
2. **RAG 검색 결과** (rag_query_cache) - Redis, TTL 1시간
3. **인기 가게 목록** - 메모리, 10분 갱신

### 🔄 하이브리드 접근 방식

```python
# 캐시 계층 구조
CACHE_HIERARCHY = {
    'L1_Memory': {
        'conversation_context': 300,      # 5분
        'active_recommendations': 600,    # 10분
        'user_state': 1800               # 30분
    },
    'L2_Redis': {
        'user_profile': 3600,            # 1시간
        'shop_embeddings': 86400,        # 24시간
        'popular_queries': 7200          # 2시간
    },
    'L3_Database': {
        'conversations': None,           # 영구 저장
        'recommendations_log': None,     # 영구 저장
        'user_interactions': None        # 영구 저장
    }
}
```

---

## 11. 파생 필드 및 특징 엔지니어링

### 사용자 레벨 특징
```python
def extract_user_features(user_id):
    return {
        # 기본 통계
        'total_orders': count_user_orders(user_id),
        'avg_order_value': calculate_avg_order_value(user_id),
        'order_frequency': calculate_order_frequency(user_id),
        
        # 시간 패턴
        'preferred_meal_times': extract_meal_time_preference(user_id),
        'weekend_vs_weekday': calculate_weekend_ratio(user_id),
        'time_consistency': measure_order_time_consistency(user_id),
        
        # 다양성 지표
        'category_diversity': calculate_category_entropy(user_id),
        'shop_loyalty': measure_shop_repeat_rate(user_id),
        'exploration_tendency': calculate_new_shop_ratio(user_id),
        
        # 가격 민감도
        'price_elasticity': measure_price_sensitivity(user_id),
        'discount_responsiveness': calculate_coupon_usage_rate(user_id),
        'budget_variability': measure_budget_std(user_id)
    }
```

### 가게 레벨 특징
```python
def extract_shop_features(shop_id):
    return {
        # 인기도 지표
        'overall_popularity': calculate_order_count_percentile(shop_id),
        'recent_popularity_trend': measure_recent_growth(shop_id),
        'repeat_customer_rate': calculate_repeat_rate(shop_id),
        
        # 품질 지표
        'avg_rating': calculate_weighted_rating(shop_id),
        'rating_consistency': measure_rating_variance(shop_id),
        'complaint_rate': calculate_negative_feedback_rate(shop_id),
        
        # 운영 효율성
        'order_fulfillment_rate': measure_success_rate(shop_id),
        'peak_hour_performance': analyze_rush_hour_metrics(shop_id),
        'menu_availability': calculate_menu_stockout_rate(shop_id)
    }
```

### 상호작용 레벨 특징
```python
def extract_interaction_features(user_id, shop_id, context):
    return {
        # 매칭 점수
        'category_preference_match': match_user_shop_category(user_id, shop_id),
        'price_range_compatibility': check_budget_fit(user_id, shop_id),
        'distance_feasibility': calculate_distance_score(user_id, shop_id),
        
        # 컨텍스트 특징
        'time_appropriateness': match_current_time_with_preference(context.time),
        'weather_menu_match': correlate_weather_with_menu(context.weather),
        'companion_suitability': evaluate_group_dining_fit(context.companions),
        
        # 이력 기반
        'previous_satisfaction': get_historical_rating(user_id, shop_id),
        'reorder_probability': calculate_reorder_likelihood(user_id, shop_id),
        'time_since_last_order': days_since_last_order(user_id, shop_id)
    }
```

---

## 12. 실제 사용 시나리오

### 시나리오 1: "배고픈데 5천원밖에 없어" (긴급 + 예산 제약)

#### 1단계: NLU 처리 및 캐싱
```python
# nlu_training_data 테이블 조회
cached = db.query("""
    SELECT predicted_intent, extracted_entities 
    FROM nlu_training_data 
    WHERE normalized_text = ? AND quality_score > 0.8
""", normalized_input)

if not cached:
    # 새로운 NLU 처리
    intent = 'budget_inquiry'
    entities = {"budget": 5000, "urgency": "high"}
    
    # 학습 데이터 저장
    save_nlu_training_data(input_text, intent, entities)
```

#### 2단계: 특징 추출 및 추천
```python
# feature_vectors 테이블에서 사용자 특징 로드
user_features = load_user_features(user_id)

# recommendation_features 계산
for shop in candidate_shops:
    features = calculate_recommendation_features(user_id, shop.id)
    
    # 긴급 모드 가중치 적용
    if user_strategy == 'urgent_mode':
        features.distance_penalty *= 2  # 거리 더 중요
        features.budget_compatibility *= 1.5  # 예산 적합성 중요

# 쿠폰 적용 (user_coupon_wallet)
apply_emergency_coupons(recommendations, user_id)
```

#### 3단계: 성능 로깅
```python
# performance_logs 테이블에 기록
log_performance({
    'operation_type': 'emergency_recommendation',
    'total_time_ms': 245,
    'nlu_time_ms': 32,
    'rag_time_ms': 78,
    'recommendation_time_ms': 89,
    'bottleneck_component': 'rag_search'
})
```

### 시나리오 2: 개인화 추천 진화 과정

#### Phase 1: 온보딩 (1-3회 대화)
```python
# user_journey_analytics 추적
update_journey_stage(user_id, 'onboarding')

# 기본 선호도 수집
if interaction_count < 3:
    response = "어떤 종류의 음식을 좋아하세요?"
    strategy = 'data_building_mode'
```

#### Phase 2: 프로필 구축 (4-10회)
```python
# user_profiles 업데이트
update_user_profile({
    'preferred_categories': extract_category_preferences(),
    'average_budget': calculate_typical_budget(),
    'personality_type': infer_personality_type()
})

# feature_vectors 생성
create_initial_feature_vectors(user_id)
```

#### Phase 3: 고급 개인화 (10회 이상)
```python
# recommendation_features 정교화
enhanced_features = {
    'time_based_preferences': learn_temporal_patterns(),
    'companion_based_preferences': analyze_group_dynamics(),
    'mood_based_selections': correlate_with_context()
}

# 예측 모델 활성화
next_order = predict_next_order(user_id)
churn_risk = assess_churn_probability(user_id)
```

### 시나리오 3: A/B 테스트 및 모델 개선

#### 실험 설정
```python
# A그룹: 기존 Wide&Deep 모델
# B그룹: LoRA 파인튜닝된 모델

if user_id in ab_test_group_b:
    model = load_lora_adapted_model()
    recommendations = model.predict(features)
    
    # 실험 결과 추적
    track_ab_test_metrics(user_id, 'lora_model', recommendations)
```

#### 모델 재훈련
```python
# model_training_logs에 새 세션 시작
training_session = start_training_session({
    'model_type': 'lora_adapter',
    'training_data': prepare_training_data(),
    'hyperparameters': {
        'lora_rank': 16,
        'learning_rate': 0.0001,
        'epochs': 5
    }
})

# 훈련 진행 상황 추적
update_training_progress(training_session.id, epoch, loss)
```

---

## 13. 구현 가이드

### 구현 우선순위

#### Phase 1: 핵심 기능 (2주)
1. **기본 테이블**: shops, menus, users, foodcard_users, product_orders
2. **대화 시스템**: conversations, conversation_contexts
3. **기본 추천**: recommendations_log
4. **쿠폰 시스템**: coupons, user_coupon_wallet

#### Phase 2: 성능 최적화 (1주)
5. **캐싱 시스템**: rag_query_cache, embedding_cache
6. **성능 모니터링**: performance_logs
7. **특징 저장**: feature_vectors

#### Phase 3: ML/AI 고도화 (2주)
8. **추천 고도화**: recommendation_features
9. **학습 시스템**: nlu_training_data, model_training_logs
10. **사용자 분석**: user_profiles, user_journey_analytics

### 성능 최적화 전략

#### 1. 인덱스 설계
```sql
-- 복합 인덱스 (자주 함께 조회되는 필드)
CREATE INDEX idx_shop_status_category ON shops(current_status, category, is_food_card_shop);
CREATE INDEX idx_user_time_intent ON conversations(user_id, timestamp, extracted_intent);
CREATE INDEX idx_rec_user_score ON recommendation_features(user_id, predicted_score DESC);

-- 부분 인덱스 (특정 조건만)
CREATE INDEX idx_active_coupons ON user_coupon_wallet(user_id, status) WHERE status = 'ACTIVE';
CREATE INDEX idx_recent_logs ON performance_logs(timestamp) WHERE timestamp > DATE_SUB(NOW(), INTERVAL 1 DAY);
```

#### 2. 파티셔닝 전략
```sql
-- 시간 기반 파티셔닝 (대용량 로그 테이블)
ALTER TABLE conversations PARTITION BY RANGE (YEAR(timestamp)) (
    PARTITION p2024 VALUES LESS THAN (2025),
    PARTITION p2025 VALUES LESS THAN (2026),
    PARTITION p_future VALUES LESS THAN MAXVALUE
);

-- 해시 파티셔닝 (균등 분산)
ALTER TABLE feature_vectors PARTITION BY HASH(entity_id) PARTITIONS 16;
```

#### 3. 배치 처리 및 집계
```python
# 5분마다 배치 처리
async def batch_process_logs():
    # 1. 성능 로그 집계
    aggregate_performance_metrics()
    
    # 2. 특징 벡터 업데이트
    update_feature_vectors_batch()
    
    # 3. 캐시 정리
    cleanup_expired_cache()
    
    # 4. 학습 데이터 준비
    prepare_training_batch()
```

### 모니터링 및 알림

#### 주요 모니터링 지표
```python
MONITORING_METRICS = {
    'response_time': {
        'threshold': 500,  # ms
        'alert': 'Response time > 500ms'
    },
    'cache_hit_rate': {
        'threshold': 0.7,
        'alert': 'Cache hit rate < 70%'
    },
    'nlu_accuracy': {
        'threshold': 0.85,
        'alert': 'NLU accuracy < 85%'
    },
    'recommendation_ctr': {
        'threshold': 0.25,
        'alert': 'CTR < 25%'
    }
}
```

### 데이터 보존 정책
```sql
-- 테이블별 보존 기간
DATA_RETENTION_POLICY = {
    -- 영구 보존
    'users': None,
    'product_orders': None,
    'user_profiles': None,
    
    -- 장기 보존 (1년)
    'conversations': 365,
    'recommendations_log': 365,
    'user_interactions': 365,
    
    -- 중기 보존 (3개월)
    'performance_logs': 90,
    'nlu_training_data': 90,
    
    -- 단기 보존 (1개월)
    'rag_query_cache': 30,
    'embedding_cache': 30,
    
    -- 매우 단기 (7일)
    'conversation_contexts': 7
}
```

---

## 🎯 핵심 포인트 요약

### 1. 데이터 아키텍처
- **3층 캐시 구조**: 메모리 → Redis → Database
- **실시간 + 배치 하이브리드**: 즉시 처리와 배치 최적화 병행
- **특징 중심 설계**: ML 모델을 위한 특징 사전 계산 및 저장

### 2. AI/ML 최적화
- **임베딩 캐싱**: 반복 계산 방지
- **RAG 결과 캐싱**: 유사 쿼리 빠른 응답
- **특징 버전 관리**: 모델 업데이트 시 호환성 유지

### 3. 개인화 전략
- **점진적 프로필 구축**: 온보딩 → 기본 → 고급 개인화
- **다차원 선호도**: 시간, 상황, 동반자별 선호도
- **예측 모델**: 다음 주문, 이탈 위험 예측

### 4. 성능 모니터링
- **병목 지점 자동 감지**: 구간별 시간 측정
- **품질 지표 추적**: NLU 정확도, 추천 CTR
- **자동 최적화 제안**: AI 기반 성능 개선 제안

### 5. 급식카드 특화
- **잔액 기반 추천**: 실시간 잔액 확인 및 최적화
- **긴급 쿠폰 시스템**: 월말 잔액 부족 시 자동 지원
- **사용 패턴 분석**: 월별 사용 패턴으로 예산 관리 조언

이 종합 가이드 v2는 나비얌 챗봇의 모든 데이터베이스 요구사항을 포함하며, 개발부터 운영까지 전체 라이프사이클을 지원합니다.