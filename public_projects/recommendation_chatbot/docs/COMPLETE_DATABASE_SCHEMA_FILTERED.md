# 나비얌 챗봇 완전한 데이터베이스 스키마 (실제 사용 Feature만)

## 개요
나비얌 챗봇이 실제로 수집하고 저장하는 모든 데이터의 완전한 스키마.
sample_data.xlsx의 31개 테이블 중 **챗봇/RAG/추천엔진이 실제로 사용하는 16개 테이블**만 포함하고, 
챗봇이 새로 생성하는 데이터와 명확히 구분.

### 데이터 소스 구분
- 🏪 **[SAMPLE_DATA]**: 기존 sample_data.xlsx에서 제공되는 데이터 (실제 사용하는 16개 테이블만)
- 🤖 **[CHATBOT_GENERATED]**: 챗봇이 사용자와의 대화를 통해 새로 생성/수집하는 데이터
- 🔄 **[DERIVED]**: 기존 데이터를 가공/분석하여 파생된 데이터

---

## 1. 🏪 [SAMPLE_DATA] 핵심 가게/메뉴 정보

### shops 테이블 (sample_data.xlsx의 shop 테이블)
```sql
CREATE TABLE shops (
    id INT PRIMARY KEY AUTO_INCREMENT,
    
    -- 🏪 [SAMPLE_DATA] 가게 기본 정보
    shop_name VARCHAR(200) NOT NULL,              
    -- 사용 이유: 추천 결과를 사용자에게 표시할 때 필수
    -- 챗봇 활용: "맛있는 치킨집" → "굽네치킨 건국대점"으로 구체적 응답
    -- RAG 검색: 가게명에서 키워드 추출하여 벡터 검색 인덱스 구성
    -- Wide&Deep: Deep 모델에서 shop_id 임베딩으로 활용
    
    category VARCHAR(100) NOT NULL,               
    -- 사용 이유: 사용자 요청과 가게 매칭의 핵심 필터
    -- 챗봇 활용: NLU가 "한식 먹고 싶어"에서 추출한 카테고리와 직접 매칭
    -- RAG 검색: 카테고리별 임베딩 벡터로 의미적 유사성 검색
    -- Wide&Deep: Wide 모델의 "user_age_group × shop_category" 교차 특성
    -- 나비얌 특화: 아동/청소년 선호 카테고리 우선 순위 (패스트푸드, 분식 등)
    
    address_name TEXT,                            
    -- 사용 이유: 위치 기반 추천의 기초 정보
    -- 챗봇 활용: "강남역 근처" 등 지역 기반 질문 처리
    -- RAG 검색: 지역 정보 컨텍스트 제공
    
    address_point POINT,                          
    -- 사용 이유: 위치 기반 추천의 핵심 (거리 계산)
    -- 챗봇 활용: "근처 맛집" 요청 시 사용자 위치와 거리 계산
    -- RAG 검색: 지리적 클러스터링으로 지역별 추천 개선
    -- Wide&Deep: numerical_features의 "distance_km"으로 활용
    -- 실제 시나리오: 급식카드 사용자 → 학교 반경 500m 내 가게 우선 추천
    
    contact VARCHAR(20),                          
    -- 사용 이유: 추천 후 연락처 제공으로 사용자 편의성 향상
    -- 챗봇 활용: 최종 추천 시 "전화: 02-1234-5678" 정보 제공
    
    -- 🏪 [SAMPLE_DATA] 나비얌 핵심 특화 기능
    is_good_influence_shop BOOLEAN DEFAULT FALSE, 
    -- 사용 이유: 나비얌의 핵심 차별화 기능 (사회적 가치 실현)
    -- 챗봇 활용: 착한가게 우선 추천으로 브랜드 가치 강화
    -- RAG 검색: 착한가게 관련 키워드 검색 시 가중치 부여
    -- Wide&Deep: "foodcard_status × good_influence_shop" 교차 특성
    -- 나비얌 특화: 급식카드 사용자에게 착한가게 50% 이상 추천
    
    is_food_card_shop VARCHAR(10),               
    -- 사용 이유: 급식카드 사용 가능 여부 필터링
    -- 챗봇 활용: 급식카드 사용자에게만 해당 가게 추천
    -- RAG 검색: 급식카드 관련 질문 시 필터링 조건
    -- Wide&Deep: Wide 모델의 핵심 교차 특성
    -- 실제 시나리오: "급식카드로 먹을 수 있는 곳" → is_food_card_shop = 'Y' 필터링
    
    -- 🏪 [SAMPLE_DATA] 운영 정보
    open_hour VARCHAR(10),                        
    close_hour VARCHAR(10),
    break_start_hour VARCHAR(10),                 
    break_end_hour VARCHAR(10),
    -- 사용 이유: 실시간 영업 상태 확인으로 사용자 실망 방지
    -- 챗봇 활용: "지금 열려있는 곳" 요청 시 실시간 필터링
    -- RAG 검색: 시간 관련 질문 시 컨텍스트 제공
    -- Wide&Deep: "time_period × food_type" 교차 특성의 시간 요소
    -- 실제 시나리오: 오후 3시 "간식 먹고 싶어" → 브레이크타임이 아닌 가게만 추천
    
    -- 🔄 [DERIVED] 실시간 계산 결과
    current_status VARCHAR(20) DEFAULT 'UNKNOWN', 
    -- 사용 이유: 운영시간 계산 결과를 캐싱하여 성능 향상
    -- 챗봇 활용: 즉시 영업 상태 확인 (OPEN/CLOSED/BREAK)
    -- RAG 검색: 실시간 상태 필터링
    -- Wide&Deep: operating_hours_match 수치 특성 계산 기준
    
    extracted_tags JSON,                          
    -- 사용 이유: RAG 검색 성능 향상을 위한 전처리된 키워드
    -- 챗봇 활용: 자연어 질문과 빠른 매칭
    -- RAG 검색: 임베딩 전 키워드 기반 1차 필터링
    -- 실제 예시: "굽네치킨" → ["치킨", "닭", "프라이드", "양념"]
    
    INDEX idx_category (category),
    INDEX idx_good_influence (is_good_influence_shop),
    INDEX idx_food_card (is_food_card_shop),
    SPATIAL INDEX idx_location (address_point)
);
```

### menus 테이블 (sample_data.xlsx의 shop_menu 테이블)
```sql
CREATE TABLE menus (
    id INT PRIMARY KEY AUTO_INCREMENT,
    shop_id INT NOT NULL,
    
    -- 🏪 [SAMPLE_DATA] 메뉴 기본 정보
    menu_name VARCHAR(200) NOT NULL,              
    -- 사용 이유: 구체적인 메뉴 추천으로 선택 도움
    -- 챗봇 활용: "매운 음식" → "불닭볶음면", "매운치킨" 등 구체적 제안
    -- RAG 검색: 메뉴명 기반 의미적 검색
    -- Wide&Deep: 메뉴별 선호도 학습
    
    price INT NOT NULL,                           
    -- 사용 이유: 예산 기반 필터링의 핵심
    -- 챗봇 활용: "1만원 이하" 요청 시 즉시 필터링
    -- RAG 검색: 가격대별 클러스터링
    -- Wide&Deep: "budget_range × price_tier" 교차 특성
    -- 급식카드 특화: 급식카드 한도 내 메뉴만 추천
    
    description TEXT,                             
    -- 사용 이유: 메뉴 상세 정보로 정확한 추천
    -- 챗봇 활용: "매운 정도", "양", "재료" 등 상세 정보 제공
    -- RAG 검색: 메뉴 설명 텍스트 기반 의미적 검색
    
    is_best BOOLEAN DEFAULT FALSE,                
    -- 사용 이유: 인기메뉴 우선 추천으로 만족도 향상
    -- 챗봇 활용: "추천해줘" 요청 시 베스트 메뉴 우선 제안
    -- Wide&Deep: 인기도 가중치 적용
    -- 실제 시나리오: 첫 방문 고객에게 베스트 메뉴 우선 제안
    
    category VARCHAR(100),                        
    -- 사용 이유: 메뉴 카테고리별 세분화된 추천
    -- 챗봇 활용: "메인메뉴", "사이드", "음료" 등 카테고리별 제안
    -- RAG 검색: 카테고리 기반 필터링
    
    -- 🔄 [DERIVED] 추천 시스템용 전처리
    normalized_price DECIMAL(5,2),                
    -- 사용 이유: Wide&Deep 모델 입력을 위한 정규화
    -- Wide&Deep: numerical_features로 직접 입력
    -- 계산 방식: (price - mean_price) / std_price
    -- 성능 향상: 실시간 정규화 계산 없이 사전 계산된 값 사용
    
    menu_embedding_vector JSON,                   
    -- 사용 이유: RAG 검색을 위한 사전 계산된 임베딩
    -- RAG 검색: 벡터 유사도 검색으로 의미적으로 유사한 메뉴 발견
    -- 성능 향상: 실시간 임베딩 계산 대신 사전 계산된 벡터 사용
    -- 실제 예시: "매운 음식" 검색 시 spicy 관련 임베딩 벡터와 유사도 계산
    
    FOREIGN KEY (shop_id) REFERENCES shops(id),
    INDEX idx_shop (shop_id),
    INDEX idx_price (price),
    INDEX idx_best (is_best)
);
```

---

## 2. 🏪 [SAMPLE_DATA] 사용자 기본 정보

### users 테이블 (sample_data.xlsx의 user 테이블)
```sql
CREATE TABLE users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    
    -- 🏪 [SAMPLE_DATA] 사용자 기본 정보
    name VARCHAR(100),                            -- [user.name] 개인화된 응답용
    nickname VARCHAR(100),                        -- [user.nickname] 친근한 응답용
    birthday DATE,                                -- [user.birthday] 연령별 메뉴 추천
    current_address TEXT,                         -- [user.currentAddress] 위치 기반 추천
    
    -- 🔄 [DERIVED] 추천 시스템용 계산값
    age_group VARCHAR(20),                        -- birthday에서 계산된 연령대
    region_code VARCHAR(20),                      -- 주소에서 추출한 지역 코드
    
    INDEX idx_age_group (age_group),
    INDEX idx_region (region_code)
);
```

### user_favorites 테이블 (sample_data.xlsx의 userfavorite 테이블)  
```sql
CREATE TABLE user_favorites (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    shop_id INT NOT NULL,
    
    -- 🏪 [SAMPLE_DATA] 찜 정보
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- [userfavorite.createdAt]
    
    -- 🔄 [DERIVED] 협업 필터링용
    preference_score DECIMAL(3,2) DEFAULT 1.0,    -- 선호도 점수 (1.0 = 찜)
    
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (shop_id) REFERENCES shops(id),
    UNIQUE KEY unique_user_shop (user_id, shop_id),
    INDEX idx_user (user_id)
);
```

---

## 3. 🏪 [SAMPLE_DATA] 급식카드 시스템 (나비얌 핵심!)

### foodcard_users 테이블 (sample_data.xlsx의 foodcard 테이블) ⭐ 나비얌 핵심!
```sql
CREATE TABLE foodcard_users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    
    -- 🏪 [SAMPLE_DATA] 급식카드 정보  
    card_number VARCHAR(50),                      
    -- 사용 이유: 급식카드 인증 및 개인 식별
    -- 챗봇 활용: "카드 등록하셨나요?" 등 인증 상태 확인
    -- 보안: 마스킹 처리하여 개인정보 보호
    
    status VARCHAR(20) DEFAULT 'ACTIVE',          
    -- 사용 이유: 카드 유효성 확인으로 서비스 제한
    -- 챗봇 활용: INACTIVE 카드 시 "카드를 확인해주세요" 안내
    -- 추천엔진: ACTIVE 카드만 급식카드 혜택 적용
    
    balance INT DEFAULT 0,                        
    -- 사용 이유: **나비얌 핵심 기능** - 예산 범위 내 추천으로 실용성 극대화
    -- 챗봇 활용: "5천원 남았어" → 잔액 내 메뉴만 추천
    -- Wide&Deep: budget_constraint 특성으로 활용
    -- 실제 시나리오: 월말 잔액 부족 시 저렴한 메뉴 위주 추천
    -- 사회적 가치: 예산 관리 교육 효과
    
    monthly_limit INT,                            
    -- 사용 이유: 월 사용 한도 관리로 과소비 방지
    -- 챗봇 활용: "이번 달 한도의 80% 사용했어요" 알림
    -- 교육적 효과: 아동/청소년 예산 관리 습관 형성
    
    -- 🔄 [DERIVED] 추천 시스템 필터링용
    is_verified BOOLEAN DEFAULT FALSE,            
    -- 사용 이유: **나비얌 차별화** - 인증된 급식카드 사용자 확인
    -- Wide&Deep: "foodcard_status × good_influence_shop" 교차 특성
    -- 나비얌 특화: 인증 사용자에게 착한가게 우선 추천 (50% 이상)
    -- 신뢰성: 검증된 대상에게만 특화 서비스 제공
    
    target_age_group VARCHAR(20),                 
    -- 사용 이유: 급식카드 종류별 차별화 서비스
    -- 예시: 
    --   초등급식카드 (7-12세) → 키즈메뉴, 교육적 가게 우선
    --   청소년급식카드 (13-18세) → 다양한 선택지, 영양 고려
    -- 챗봇 활용: 연령대별 맞춤 언어와 추천 방식
    -- Wide&Deep: age_specific_preference 특성
    
    FOREIGN KEY (user_id) REFERENCES users(id),
    INDEX idx_user (user_id),
    INDEX idx_status (status),
    INDEX idx_verified (is_verified)
);
```

---

## 4. 🏪 [SAMPLE_DATA] 실제 이용 이력 (협업 필터링용)

### tickets 테이블 (sample_data.xlsx의 ticket 테이블)
```sql
CREATE TABLE tickets (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    shop_id INT NOT NULL,
    
    -- 🏪 [SAMPLE_DATA] 이용권 정보
    created_at TIMESTAMP,                         -- [ticket.createdAt] 방문 시간
    status VARCHAR(20),                           -- [ticket.status] 이용 상태
    amount INT,                                   -- [ticket.amount] 이용 금액
    
    -- 🔄 [DERIVED] 협업 필터링 feature
    visit_frequency_score DECIMAL(3,2),          -- 방문 빈도 점수
    spending_pattern VARCHAR(20),                 -- 지출 패턴 (low/medium/high)
    
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (shop_id) REFERENCES shops(id),
    INDEX idx_user_time (user_id, created_at),
    INDEX idx_shop (shop_id)
);
```

### product_orders 테이블 (sample_data.xlsx의 product_order 테이블)
```sql
CREATE TABLE product_orders (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    
    -- 🏪 [SAMPLE_DATA] 주문 정보
    product_id INT,                               -- [product_order.product_id] 주문 상품
    created_at TIMESTAMP,                         -- [product_order.createdAt] 주문 시간
    quantity INT,                                 -- [product_order.quantity] 주문 수량
    price INT,                                    -- [product_order.price] 주문 금액
    
    -- 🔄 [DERIVED] 선호도 학습용
    order_pattern_score DECIMAL(3,2),            -- 주문 패턴 점수
    preference_weight DECIMAL(3,2),              -- 선호도 가중치
    
    FOREIGN KEY (user_id) REFERENCES users(id),
    INDEX idx_user_time (user_id, created_at),
    INDEX idx_product (product_id)
);
```

---

## 5. 🏪 [SAMPLE_DATA] 리뷰 및 평점 (품질 보장)

### reviews 테이블 (sample_data.xlsx의 review 테이블)
```sql
CREATE TABLE reviews (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    shop_id INT NOT NULL,
    
    -- 🏪 [SAMPLE_DATA] 리뷰 정보
    rating DECIMAL(2,1) NOT NULL,                 -- [review.rating] 평점 (1.0~5.0)
    comment TEXT,                                 -- [review.comment] 리뷰 텍스트
    created_at TIMESTAMP,                         -- [review.createdAt] 작성 시간
    
    -- 🔄 [DERIVED] 감정 분석 및 품질 지표
    sentiment VARCHAR(20),                        -- 감정 분석 결과 (positive/negative/neutral)
    quality_score DECIMAL(3,2),                  -- 리뷰 품질 점수
    helpful_count INT DEFAULT 0,                 -- 도움이 된 횟수
    
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (shop_id) REFERENCES shops(id),
    INDEX idx_shop_rating (shop_id, rating),
    INDEX idx_user (user_id)
);
```

---

## 6. 🤖 [CHATBOT_GENERATED] 대화 및 상호작용 데이터

### conversations 테이블
```sql
CREATE TABLE conversations (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id VARCHAR(100) NOT NULL,               -- 🤖 [CHATBOT_GENERATED]
    session_id VARCHAR(200) NOT NULL,            -- 🤖 [CHATBOT_GENERATED]
    input_text TEXT NOT NULL,                    -- 🤖 [CHATBOT_GENERATED]
    response_text TEXT NOT NULL,                 -- 🤖 [CHATBOT_GENERATED]
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- 🤖 [CHATBOT_GENERATED] NLU 추출 정보
    extracted_intent VARCHAR(50),
    intent_confidence DECIMAL(4,3),
    
    -- 🤖 [CHATBOT_GENERATED] 추출된 엔티티 (JSON 형태)
    extracted_entities JSON,                     -- food_type, budget, location, companions 등
    
    -- 🤖 [CHATBOT_GENERATED] 감정 및 키워드
    emotion VARCHAR(20),
    extracted_keywords JSON,
    
    -- 🤖 [CHATBOT_GENERATED] 사용자 전략 및 대화 맥락
    user_strategy VARCHAR(30),                   -- onboarding_mode, data_building_mode, normal_mode
    conversation_turn INT,
    
    INDEX idx_user_timestamp (user_id, timestamp),
    INDEX idx_session (session_id),
    INDEX idx_intent (extracted_intent)
);
```

### nlu_features 테이블
```sql
CREATE TABLE nlu_features (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id VARCHAR(100) NOT NULL,               -- 🤖 [CHATBOT_GENERATED]
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- 🤖 [CHATBOT_GENERATED] NLU 핵심 결과
    nlu_intent VARCHAR(50),                      -- food_request, budget_inquiry 등
    nlu_confidence DECIMAL(4,3),
    
    -- 🤖 [CHATBOT_GENERATED] 추출된 특징들
    food_category_mentioned VARCHAR(100),        -- "치킨", "한식", "일식" 등
    budget_mentioned INT,                        -- 예산 금액
    location_mentioned VARCHAR(100),             -- "근처", "강남" 등
    companions_mentioned JSON,                   -- ["친구", "가족"] 등
    time_preference VARCHAR(50),                 -- "지금", "저녁" 등
    menu_options JSON,                           -- ["맵게", "곱배기"] 등
    special_requirements JSON,                   -- 특별 요구사항
    
    -- 🤖 [CHATBOT_GENERATED] 처리 메타데이터
    processing_time_ms INT,
    model_version VARCHAR(20),
    
    INDEX idx_user_timestamp (user_id, timestamp),
    INDEX idx_intent (nlu_intent),
    INDEX idx_food_category (food_category_mentioned)
);
```

---

## 7. 🤖 [CHATBOT_GENERATED] 사용자 상호작용 데이터

### user_interactions 테이블
```sql
CREATE TABLE user_interactions (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id VARCHAR(100) NOT NULL,               -- 🤖 [CHATBOT_GENERATED]
    session_id VARCHAR(200),                     -- 🤖 [CHATBOT_GENERATED]
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- 🤖 [CHATBOT_GENERATED] 상호작용 세부사항
    interaction_type VARCHAR(30),                -- "text_input", "selection", "feedback"
    input_text TEXT,
    response_generated TEXT,
    
    -- 🤖 [CHATBOT_GENERATED] 학습 데이터 추출 결과
    food_preference_extracted VARCHAR(100),      -- 대화에서 추출한 음식 선호도
    budget_pattern_extracted INT,                -- 대화에서 추출한 예산 패턴
    companion_pattern_extracted JSON,            -- 대화에서 추출한 동반자 패턴
    location_preference_extracted VARCHAR(100),  -- 대화에서 추출한 위치 선호도
    
    -- 🔄 [DERIVED] 추천 관련 데이터 (shops 테이블과 연결)
    recommendation_provided BOOLEAN DEFAULT FALSE,
    recommendation_count INT DEFAULT 0,
    recommendations JSON,                        -- 추천된 shop_id들과 점수
    
    -- 🤖 [CHATBOT_GENERATED] 사용자 상태
    user_strategy VARCHAR(30),
    conversation_turn INT,
    
    INDEX idx_user_timestamp (user_id, timestamp),
    INDEX idx_session (session_id),
    INDEX idx_interaction_type (interaction_type)
);
```

---

## 8. 🔄 [DERIVED] 추천 시스템 데이터 (sample_data + chatbot 결합)

### recommendations_log 테이블
```sql
CREATE TABLE recommendations_log (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id VARCHAR(100) NOT NULL,               -- 🤖 [CHATBOT_GENERATED]
    session_id VARCHAR(200),                     -- 🤖 [CHATBOT_GENERATED]
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- 🤖 [CHATBOT_GENERATED] 추천 입력 조건
    request_food_type VARCHAR(100),              -- NLU에서 추출한 음식 종류
    request_budget INT,                          -- NLU에서 추출한 예산
    request_location VARCHAR(100),               -- NLU에서 추출한 위치 선호
    request_companions JSON,                     -- NLU에서 추출한 동반자
    
    -- 🔄 [DERIVED] 추천 결과 (shops 테이블의 shop_id 참조)
    recommendations JSON NOT NULL,               -- [{shop_id, score, reason}] 배열
    recommendation_count INT NOT NULL,
    top_recommendation_shop_id INT,              -- shops.id 참조
    
    -- 🤖 [CHATBOT_GENERATED] 사용자 선택 (나중에 업데이트)
    user_selection JSON,                         -- 사용자가 선택한 가게 정보
    selection_timestamp TIMESTAMP NULL,
    
    -- 🤖 [CHATBOT_GENERATED] 추천 시스템 메타데이터
    recommendation_method VARCHAR(50),           -- "wide_deep", "rag", "hybrid"
    confidence_score DECIMAL(4,3),
    wide_score DECIMAL(4,3),                    -- Wide 모델 점수
    deep_score DECIMAL(4,3),                    -- Deep 모델 점수
    rag_score DECIMAL(4,3),                     -- RAG 검색 점수
    
    INDEX idx_user_timestamp (user_id, timestamp),
    INDEX idx_session (session_id),
    INDEX idx_shop (top_recommendation_shop_id),
    FOREIGN KEY (top_recommendation_shop_id) REFERENCES shops(id)
);
```

---

## 9. 🤖 [CHATBOT_GENERATED] 사용자 피드백 데이터

### user_feedback 테이블
```sql
CREATE TABLE user_feedback (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id VARCHAR(100) NOT NULL,               -- 🤖 [CHATBOT_GENERATED]
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- 🤖 [CHATBOT_GENERATED] 피드백 기본 정보
    feedback_type VARCHAR(30) NOT NULL,          -- "selection", "rating", "text", "implicit"
    feedback_content JSON,                       -- 피드백 내용 (점수, 텍스트, 선택 등)
    
    -- 🤖 [CHATBOT_GENERATED] 피드백 맥락
    context JSON,                                -- 피드백이 발생한 상황 정보
    related_recommendation_id BIGINT,            -- recommendations_log.id 참조
    related_session_id VARCHAR(200),
    
    -- 🔄 [DERIVED] 피드백 분석 결과
    sentiment VARCHAR(20),                       -- "positive", "negative", "neutral"
    satisfaction_score DECIMAL(3,2),            -- 0.00 ~ 1.00
    feedback_quality DECIMAL(3,2),              -- 피드백 품질 점수
    
    INDEX idx_user_timestamp (user_id, timestamp),
    INDEX idx_feedback_type (feedback_type),
    INDEX idx_recommendation (related_recommendation_id),
    FOREIGN KEY (related_recommendation_id) REFERENCES recommendations_log(id)
);
```

---

## 10. 🤖 [CHATBOT_GENERATED] 구조화된 학습 데이터

### structured_learning_data 테이블
```sql
CREATE TABLE structured_learning_data (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id VARCHAR(100) NOT NULL,               -- 🤖 [CHATBOT_GENERATED]
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- 🤖 [CHATBOT_GENERATED] 기본 추출 데이터
    extracted_entities JSON NOT NULL,           -- NLU 추출 엔티티
    intent_confidence DECIMAL(4,3) NOT NULL,
    
    -- 🤖 [CHATBOT_GENERATED] 학습용 특징들
    food_preferences JSON,                       -- ["치킨", "한식", "양식"] 
    budget_patterns JSON,                        -- [15000, 20000, 18000]
    companion_patterns JSON,                     -- ["친구", "혼자", "가족"]
    taste_preferences JSON,                      -- {"매운맛": 0.3, "짠맛": 0.8}
    
    -- 🤖 [CHATBOT_GENERATED] 선택/피드백 데이터
    recommendations_provided JSON,               -- 제공된 추천 목록
    user_selection JSON,                         -- 사용자 최종 선택
    user_feedback TEXT,                          -- 사용자 피드백 텍스트
    satisfaction_score DECIMAL(3,2),            -- 만족도 점수
    
    -- 🔄 [DERIVED] 데이터 품질 지표
    quality_score DECIMAL(4,3) NOT NULL,        -- 데이터 품질 점수 (0.0~1.0)
    is_valid BOOLEAN NOT NULL,                   -- 유효성 여부 (quality_score >= 0.5)
    
    INDEX idx_user_timestamp (user_id, timestamp),
    INDEX idx_quality (quality_score),
    INDEX idx_valid (is_valid)
);
```

---

## 11. 🤖 [CHATBOT_GENERATED] 사용자 프로필 (동적 업데이트)

### user_profiles 테이블
```sql
CREATE TABLE user_profiles (
    user_id VARCHAR(100) PRIMARY KEY,            -- 🤖 [CHATBOT_GENERATED]
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    -- 🔄 [DERIVED] 기본 선호도 (sample_data + 대화 학습)
    preferred_categories JSON,                   -- ["치킨", "한식", "중식"] (대화에서 학습)
    average_budget INT,                          -- 대화에서 학습한 평균 예산
    favorite_shops JSON,                         -- [1, 5, 12, 23] (sample_data + 대화 결합)
    
    -- 🤖 [CHATBOT_GENERATED] 고급 개인화 특징
    taste_preferences JSON,                      -- {"매운맛": 0.3, "짠맛": 0.8} (대화에서 학습)
    companion_patterns JSON,                     -- ["친구", "혼자", "가족"] (대화 패턴)
    location_preferences JSON,                   -- ["건국대", "강남"] (대화 + sample_data)
    good_influence_preference DECIMAL(3,2) DEFAULT 0.50, -- 착한가게 선호도
    
    -- 🤖 [CHATBOT_GENERATED] 사용자 상태
    interaction_count INT DEFAULT 0,             -- 총 상호작용 횟수
    data_completeness DECIMAL(3,2) DEFAULT 0.00, -- 데이터 완성도 (0.00 ~ 1.00)
    conversation_style VARCHAR(20) DEFAULT 'friendly',
    
    -- 🔄 [DERIVED] 최근 활동 (sample_data + 대화 결합)
    recent_orders JSON,                          -- 최근 10개 주문 이력 (ticket + 대화)
    
    INDEX idx_updated (last_updated),
    INDEX idx_completeness (data_completeness),
    INDEX idx_interaction_count (interaction_count)
);
```

---

## 12. 시스템 관리 테이블들

### collection_sessions 테이블 (데이터 수집 관리)
```sql
CREATE TABLE collection_sessions (
    session_id VARCHAR(200) PRIMARY KEY,         -- 🤖 [CHATBOT_GENERATED]
    user_id VARCHAR(100) NOT NULL,               -- 🤖 [CHATBOT_GENERATED]
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP,
    status VARCHAR(20) DEFAULT 'active',         -- 'active', 'completed', 'error'
    
    -- 🤖 [CHATBOT_GENERATED] 세션 통계
    data_points_count INT DEFAULT 0,
    nlu_features_count INT DEFAULT 0,
    interactions_count INT DEFAULT 0,
    recommendations_count INT DEFAULT 0,
    feedback_count INT DEFAULT 0,
    
    -- 🔄 [DERIVED] 세션 품질 지표
    avg_confidence DECIMAL(4,3),
    valid_data_ratio DECIMAL(3,2),
    
    INDEX idx_user (user_id),
    INDEX idx_start_time (start_time),
    INDEX idx_status (status)
);
```

### performance_logs 테이블 (성능 모니터링)
```sql
CREATE TABLE performance_logs (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- 🤖 [CHATBOT_GENERATED] 응답 성능
    response_time_ms INT NOT NULL,
    success BOOLEAN NOT NULL,
    
    -- 🤖 [CHATBOT_GENERATED] 세부 성능 지표
    nlu_processing_time_ms INT,
    rag_search_time_ms INT,
    recommendation_time_ms INT,
    response_generation_time_ms INT,
    
    -- 🤖 [CHATBOT_GENERATED] 시스템 리소스
    memory_usage_mb INT,
    gpu_memory_mb INT,
    
    INDEX idx_timestamp (timestamp),
    INDEX idx_response_time (response_time_ms),
    INDEX idx_success (success)
);
```

---

## 데이터 처리 및 백업 전략

### 1. 실시간 버퍼링
- 각 데이터 타입별로 메모리 버퍼 운용 (기본 100개)
- 5분마다 자동 저장 (auto_save_interval: 300초)
- 버퍼 가득참 시 즉시 저장

### 2. 파일 저장 구조
```
data/
├── raw/
│   ├── nlu_features_20250802.jsonl
│   ├── interactions_20250802.jsonl
│   ├── recommendations_20250802.jsonl
│   └── feedback_20250802.jsonl
├── processed/
│   └── training_data_20250802.json
└── sessions/
    ├── user1_20250802_142301.json
    └── user2_20250802_143015.json
```

### 3. Wide&Deep 모델 Feature 매핑

#### Wide Component (교차 특성)
```python
wide_features = [
    "user_age_group × shop_category",           # users.age_group × shops.category
    "user_region × shop_category",              # users.region_code × shops.category  
    "time_period × food_type",                  # 현재시간 × shops.category
    "foodcard_status × good_influence_shop",    # foodcard_users.is_verified × shops.is_good_influence_shop
    "budget_range × price_tier"                 # NLU 예산 × menus.normalized_price
]
```

#### Deep Component (임베딩 특성)
```python
deep_features = {
    "categorical_features": [
        "user_id",           # 사용자 고유 임베딩
        "shop_id",           # 가게 고유 임베딩
        "category_id",       # 카테고리 임베딩
        "age_group",         # 연령대 임베딩
        "region_code"        # 지역 임베딩
    ],
    "numerical_features": [
        "normalized_price",          # menus.normalized_price
        "distance_km",               # 계산된 거리
        "operating_hours_match",     # 운영시간 매칭도
        "good_influence_score",      # 착한가게 가중치
        "user_preference_score",     # 사용자 선호도 점수
        "review_rating_avg"          # 평균 리뷰 점수
    ]
}
```

---

## 🎯 실제 사용 시나리오별 Feature 종합 활용

### 시나리오 1: "치킨 먹고 싶어" (급식카드 사용자)

#### 1단계: NLU 처리
```sql
-- conversations 테이블에 저장
INSERT INTO conversations (user_id, input_text, extracted_intent, extracted_entities)
VALUES ('student123', '치킨 먹고 싶어', 'food_request', '{"food_type": "치킨"}');

-- nlu_features 테이블에 저장  
INSERT INTO nlu_features (user_id, food_category_mentioned, nlu_confidence)
VALUES ('student123', '치킨', 0.95);
```

#### 2단계: 급식카드 확인 및 필터링
```sql
-- foodcard_users에서 사용자 상태 확인
SELECT balance, is_verified FROM foodcard_users WHERE user_id = 'student123';
-- 결과: balance=8000, is_verified=TRUE

-- 예산 내 치킨집 필터링
SELECT s.shop_name, m.menu_name, m.price 
FROM shops s 
JOIN menus m ON s.id = m.shop_id
WHERE s.category = '치킨' 
  AND s.is_food_card_shop = 'Y'
  AND m.price <= 8000  -- 급식카드 잔액 내
  AND s.current_status = 'OPEN';
```

#### 3단계: RAG 검색
```sql  
-- extracted_tags를 이용한 키워드 매칭
SELECT shop_name FROM shops 
WHERE JSON_CONTAINS(extracted_tags, '"치킨"')
   OR JSON_CONTAINS(extracted_tags, '"닭"')
   OR JSON_CONTAINS(extracted_tags, '"프라이드"');

-- menu_embedding_vector를 이용한 의미적 검색
-- "치킨" 임베딩과 유사도 계산하여 상위 N개 반환
```

#### 4단계: Wide&Deep 추천 점수 계산
```sql
-- Wide Component 교차 특성
- user_age_group × shop_category = "teen × 치킨" → 높은 가중치
- foodcard_verified × good_influence_shop = "TRUE × TRUE" → 추가 가산점

-- Deep Component 수치 특성  
- normalized_price: 0.3 (8000원 → 정규화)
- distance_km: 0.5 (500m)
- operating_hours_match: 1.0 (영업중)
- good_influence_score: 0.8 (착한가게)
```

#### 5단계: 최종 추천 및 응답
```sql
-- recommendations_log에 추천 결과 저장
INSERT INTO recommendations_log (
    user_id, recommendations, recommendation_method, confidence_score
) VALUES (
    'student123',
    '[{"shop_id": 15, "score": 0.92, "reason": "착한가게+예산적합"}]',
    'hybrid', 0.92
);
```

**챗봇 최종 응답**: 
> "안녕 민수야! 잔액 8천원으로 먹을 수 있는 착한 치킨집을 찾았어! 🍗
> 
> **굽네치킨 건국대점** (도보 3분)
> - 순살치킨 7,000원 ⭐ 베스트메뉴
> - 착한가게 인증 💚 급식카드 OK
> - 지금 영업중 (21:00까지)
> 
> 전화: 02-456-7890"

### 시나리오 2: 월말 잔액 부족 상황 (balance < 5000원)

#### 급식카드 잔액 기반 추천 로직
```sql
-- 잔액 확인 및 경고
SELECT balance, monthly_limit FROM foodcard_users WHERE user_id = 'student456';
-- 결과: balance=3500, monthly_limit=60000

-- 잔액 내 메뉴만 필터링 + 가성비 우선
SELECT s.shop_name, m.menu_name, m.price,
       (m.is_best * 0.3 + s.is_good_influence_shop * 0.2) as priority_score
FROM shops s JOIN menus m ON s.id = m.shop_id
WHERE m.price <= 3500
  AND s.is_food_card_shop = 'Y'
ORDER BY priority_score DESC, m.price ASC;
```

**챗봇 응답**:
> "잔액이 3,500원 남았네! 알뜰하게 먹을 수 있는 곳들을 찾아봤어 😊
> 
> **착한분식 건대점** - 떡볶이 3,000원 💚착한가게
> **대학생김밥** - 참치김밥 2,500원  
> **할머니국수** - 잔치국수 3,000원
> 
> 다음 달까지 6일 남았어. 계획적으로 써보자! 💪"

### 시나리오 3: 첫 방문 사용자 온보딩

#### 사용자 프로필 구축 과정
```sql
-- 1. 기본 정보 수집
UPDATE user_profiles SET 
    interaction_count = 1,
    conversation_style = 'onboarding_mode'
WHERE user_id = 'newbie789';

-- 2. 선호도 학습
INSERT INTO structured_learning_data (
    user_id, food_preferences, budget_patterns, companion_patterns
) VALUES (
    'newbie789', 
    '["한식", "분식"]',
    '[8000, 12000]', 
    '["혼자", "친구"]'
);

-- 3. 데이터 완성도 계산
UPDATE user_profiles SET 
    data_completeness = 0.7,  -- 70% 완성
    user_strategy = 'data_building_mode'
WHERE user_id = 'newbie789';
```

---

## 🔧 시스템별 Feature 활용 매트릭스

| Feature | 챗봇 NLU/NLG | RAG 검색 | Wide&Deep | 나비얌 특화 |
|---------|-------------|----------|-----------|------------|
| **shop_name** | 추천 표시 | 키워드 추출 | 임베딩 | - |
| **category** | 의도 매칭 | 의미적 검색 | 교차 특성 | 연령별 선호 |
| **is_good_influence_shop** | 브랜드 강화 | 가중치 부여 | 핵심 교차 특성 | ⭐ 50% 우선 추천 |
| **is_food_card_shop** | 필터링 | 조건 검색 | 필수 조건 | ⭐ 급식카드 전용 |
| **foodcard.balance** | 예산 안내 | - | 제약 조건 | ⭐ 실시간 잔액 관리 |
| **foodcard.is_verified** | 인증 확인 | - | 교차 특성 | ⭐ 차별화 서비스 |
| **menu.price** | 예산 필터링 | 가격대 검색 | 수치 특성 | 급식카드 한도 |
| **review.rating** | 품질 보장 | 평점 필터 | 신뢰도 특성 | 안전한 가게 |

---

### 🎯 핵심 포인트:

1. **sample_data.xlsx 활용**: 31개 테이블 중 **실제 사용하는 16개 테이블**만 선별
   - **핵심**: shop, shop_menu, user, userfavorite, foodcard, review, ticket, product_order

2. **급식카드 특화**: `foodcard` 테이블을 통한 **나비얌만의 차별화 기능**

3. **3-tier 데이터 구조**:
   - 🏪 [SAMPLE_DATA]: 기존 데이터 16개 테이블
   - 🤖 [CHATBOT_GENERATED]: 대화로 새로 생성되는 8개 테이블  
   - 🔄 [DERIVED]: 두 데이터를 결합한 파생 데이터

4. **Wide&Deep 추천엔진**: sample_data의 가게/메뉴/사용자 정보 + 챗봇 대화 데이터 결합

### 🚀 구현 우선순위:
**Phase 1**: shops, menus, users, conversations, recommendations_log  
**Phase 2**: foodcard_users, reviews, user_feedback, structured_learning_data  
**Phase 3**: 성능 모니터링 및 고도화 테이블들