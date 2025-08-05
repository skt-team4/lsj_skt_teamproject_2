# 나비얌 챗봇 최종 데이터베이스 스키마

## 개요
나비얌 챗봇의 AI 운영에 필요한 스키마.

### 주요 변경사항
- ✅ 13개 카테고리 시스템 적용
- ✅ foodcard_users 테이블 간소화 (is_verified, monthly_limit 제거)
- ✅ 쿠폰 테이블 제외 (현재 미사용)
- ✅ 중복 테이블 통합 (conversations + nlu_features)

---

## 1. 핵심 데이터 테이블

### shops 테이블 (가게 정보)
```sql
CREATE TABLE shops (
    id INT PRIMARY KEY AUTO_INCREMENT,
    
    -- 🏪 [SAMPLE_DATA] 필드
    shop_name VARCHAR(200) NOT NULL,              -- sample_data.xlsx 제공
    category VARCHAR(100) NOT NULL,               -- sample_data.xlsx 제공 (13개 카테고리)
    address_name TEXT,                            -- sample_data.xlsx 제공
    is_good_influence_shop BOOLEAN DEFAULT FALSE, -- sample_data.xlsx 제공
    is_food_card_shop VARCHAR(10),               -- sample_data.xlsx 제공 ('Y', 'N')
    open_hour VARCHAR(10),                        -- sample_data.xlsx 제공
    close_hour VARCHAR(10),                       -- sample_data.xlsx 제공
    break_start_hour VARCHAR(10),                 -- sample_data.xlsx 제공
    break_end_hour VARCHAR(10),                   -- sample_data.xlsx 제공
    phone VARCHAR(20),                            -- sample_data.xlsx 제공
    owner_message TEXT,                           -- sample_data.xlsx 제공
    latitude DECIMAL(10, 8),                      -- sample_data.xlsx 제공 (추가로 제공)
    longitude DECIMAL(11, 8),                     -- sample_data.xlsx 제공 (추가로 제공)
    
    -- 🔄 [DERIVED] 필드 (기존 데이터에서 계산)
    current_status VARCHAR(20) DEFAULT 'UNKNOWN', -- 운영시간에서 실시간 계산
    
    INDEX idx_category (category),
    INDEX idx_good_influence (is_good_influence_shop),
    INDEX idx_food_card (is_food_card_shop)
);
```

### menus 테이블 (메뉴 정보)
```sql
CREATE TABLE menus (
    id INT PRIMARY KEY AUTO_INCREMENT,
    
    -- 🏪 [SAMPLE_DATA] 필드
    shop_id INT NOT NULL,                         -- sample_data.xlsx 제공
    menu_name VARCHAR(200) NOT NULL,              -- sample_data.xlsx 제공
    price INT NOT NULL,                           -- sample_data.xlsx 제공
    description TEXT,                             -- sample_data.xlsx 제공
    category VARCHAR(100),                        -- sample_data.xlsx 제공 (메인, 사이드 등)
    
    FOREIGN KEY (shop_id) REFERENCES shops(id),
    INDEX idx_shop (shop_id),
    INDEX idx_price (price)
);
```

### users 테이블 (일반 사용자)
```sql
CREATE TABLE users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    
    -- 🏪 [SAMPLE_DATA] 필드
    name VARCHAR(100),                            -- sample_data.xlsx 제공
    nickname VARCHAR(100),                        -- sample_data.xlsx 제공
    birthday DATE,                                -- sample_data.xlsx 제공
    current_address TEXT,                         -- sample_data.xlsx 제공
    
    -- 🔄 [DERIVED] 필드
    age_group VARCHAR(20),                        -- birthday에서 계산 (10대, 20대 등)
    region_code VARCHAR(20)                       -- current_address에서 파생
);
```

### foodcard_users 테이블 (급식카드 사용자 - 간소화)
```sql
CREATE TABLE foodcard_users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    
    -- 🏪 [SAMPLE_DATA] 필드
    user_id INT NOT NULL,                         -- sample_data.xlsx 제공
    card_number VARCHAR(50),                      -- sample_data.xlsx 제공
    balance INT DEFAULT 0,                        -- sample_data.xlsx 제공
    status VARCHAR(20) DEFAULT 'ACTIVE',          -- sample_data.xlsx 제공 (ACTIVE/INACTIVE)
    
    -- 🔄 [DERIVED] 필드
    target_age_group VARCHAR(20),                 -- user의 birthday에서 파생 (청소년/청년 등)
    
    FOREIGN KEY (user_id) REFERENCES users(id),
    INDEX idx_user (user_id),
    INDEX idx_status (status)
);
```

---

## 2. AI 운영 테이블

### conversations 테이블 (대화 및 NLU 통합)
```sql
CREATE TABLE conversations (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    
    -- 🤖 [CHATBOT_GENERATED] 필드
    user_id VARCHAR(100) NOT NULL,                -- 챗봇이 생성
    session_id VARCHAR(200) NOT NULL,             -- 챗봇이 생성
    input_text TEXT NOT NULL,                     -- 사용자 입력 (챗봇이 수집)
    response_text TEXT NOT NULL,                  -- 챗봇이 생성
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- 🤖 [CHATBOT_GENERATED] NLU 추출 정보
    extracted_intent VARCHAR(50),                 -- 챗봇이 분석 (food_request 등)
    intent_confidence DECIMAL(4,3),               -- 챗봇이 계산
    extracted_entities JSON,                      -- 챗봇이 추출 {food_type, budget 등}
    
    -- 🤖 [CHATBOT_GENERATED] 대화 맥락
    user_strategy VARCHAR(30),                    -- 챗봇이 판단 (onboarding_mode 등)
    conversation_turn INT,                        -- 챗봇이 카운트
    
    INDEX idx_user_timestamp (user_id, timestamp),
    INDEX idx_session (session_id)
);
```

### user_interactions 테이블 (상호작용 및 학습 데이터)
```sql
CREATE TABLE user_interactions (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    
    -- 🤖 [CHATBOT_GENERATED] 필드
    user_id VARCHAR(100) NOT NULL,                -- 챗봇이 생성
    session_id VARCHAR(200),                      -- 챗봇이 생성
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    interaction_type VARCHAR(30),                 -- 챗봇이 분류 (text_input, selection 등)
    user_selection JSON,                          -- 챗봇이 기록 {shop_id, menu_ids}
    
    -- 🔄 [DERIVED] 필드 (챗봇+추천엔진)
    recommendations JSON,                         -- 추천엔진 결과 [{shop_id, score}]
    
    -- 🤖 [CHATBOT_GENERATED] 학습용 특징
    food_preference_extracted VARCHAR(100),       -- 대화에서 추출
    budget_pattern_extracted INT,                 -- 대화에서 추출
    companion_pattern_extracted VARCHAR(50),      -- 대화에서 추출
    
    INDEX idx_user_timestamp (user_id, timestamp),
    INDEX idx_interaction_type (interaction_type)
);
```

### recommendations_log 테이블 (추천 로그)
```sql
CREATE TABLE recommendations_log (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    
    -- 🤖 [CHATBOT_GENERATED] 필드
    user_id VARCHAR(100) NOT NULL,                -- 챗봇이 생성
    session_id VARCHAR(200),                      -- 챗봇이 생성
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    request_food_type VARCHAR(100),               -- NLU가 추출
    request_budget INT,                           -- NLU가 추출
    request_location VARCHAR(100),                -- NLU가 추출
    
    -- 🔄 [DERIVED] 필드 (추천엔진 결과)
    recommendations JSON NOT NULL,                -- 추천엔진 계산 [{shop_id, score, reason}]
    recommendation_count INT NOT NULL,            -- 추천엔진 계산
    recommendation_method VARCHAR(50),            -- 추천엔진 방식 (wide_deep, rag, hybrid)
    confidence_score DECIMAL(4,3),                -- 추천엔진 신뢰도
    
    INDEX idx_user_timestamp (user_id, timestamp),
    INDEX idx_method (recommendation_method)
);
```

---

## 3. 선택적 운영 테이블 (2차 구현)

### user_profiles 테이블 (개인화)
```sql
CREATE TABLE user_profiles (
    -- 🤖 [CHATBOT_GENERATED] 필드
    user_id VARCHAR(100) PRIMARY KEY,             -- 챗봇이 생성
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    -- 🤖 [CHATBOT_GENERATED] 개인화 정보 (대화에서 학습)
    preferred_categories JSON,                    -- 대화에서 추출 ["한식", "치킨"]
    average_budget INT,                           -- 대화에서 계산
    good_influence_preference DECIMAL(3,2),       -- 선택 패턴에서 계산 (0.0 ~ 1.0)
    interaction_count INT DEFAULT 0,              -- 대화 횟수 카운트
    
    -- 🔄 [DERIVED] 필드 (sample_data + 챗봇)
    favorite_shops JSON,                          -- 주문 이력에서 계산 [shop_id들]
    recent_orders JSON,                           -- tickets + 대화 결합
    
    INDEX idx_updated (last_updated)
);
```

### performance_logs 테이블 (성능 모니터링)
```sql
CREATE TABLE performance_logs (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    
    -- 🤖 [CHATBOT_GENERATED] 필드
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    response_time_ms INT NOT NULL,                -- 챗봇이 측정
    success BOOLEAN NOT NULL,                     -- 챗봇이 기록
    nlu_processing_time_ms INT,                   -- NLU 모듈이 측정
    rag_search_time_ms INT,                       -- RAG 모듈이 측정
    recommendation_time_ms INT,                   -- 추천엔진이 측정
    
    INDEX idx_timestamp (timestamp),
    INDEX idx_response_time (response_time_ms)
);
```

---

## 구현 우선순위

### Phase 1: 핵심 기능 (필수)
1. **shops, menus** - 🏪 [SAMPLE_DATA] 기본 데이터
2. **users, foodcard_users** - 🏪 [SAMPLE_DATA] 사용자 관리
3. **conversations** - 🤖 [CHATBOT_GENERATED] 대화 로깅

### Phase 2: AI 기능 (중요)
4. **user_interactions** - 🤖 [CHATBOT_GENERATED] + 🔄 [DERIVED] 학습 데이터
5. **recommendations_log** - 🤖 [CHATBOT_GENERATED] + 🔄 [DERIVED] 추천 추적

### Phase 3: 고급 기능 (선택)
6. **user_profiles** - 🤖 [CHATBOT_GENERATED] + 🔄 [DERIVED] 개인화
7. **performance_logs** - 🤖 [CHATBOT_GENERATED] 성능 모니터링

---

## 데이터 소스 요약

### 🏪 [SAMPLE_DATA] - sample_data.xlsx에서 제공
- **shops**: 가게 정보 (이름, 카테고리, 주소, 운영시간, 위도/경도 등)
- **menus**: 메뉴 정보 (이름, 가격, 설명 등)
- **users**: 사용자 기본 정보 (이름, 생일, 주소)
- **foodcard_users**: 급식카드 정보 (카드번호, 잔액, 상태)

### 🤖 [CHATBOT_GENERATED] - 챗봇이 새로 생성
- **conversations**: 대화 내용, NLU 분석 결과
- **user_interactions**: 사용자 선택, 피드백
- **user_profiles**: 학습된 선호도
- **performance_logs**: 성능 측정 데이터

### 🔄 [DERIVED] - 기존 데이터를 가공/결합
- **recommendations**: sample_data의 가게/메뉴 + 챗봇 분석 결합
- **current_status**: 운영시간에서 실시간 계산
- **age_group**: 생일에서 계산
- **target_age_group**: 사용자의 생일에서 계산

---

**핵심 변경사항:**
- 쿠폰 테이블 제외 (미사용)
- foodcard_users 간소화 (is_verified, monthly_limit 제거)
- 13개 카테고리 시스템 반영
- 각 필드의 데이터 소스 명시 (🏪/🤖/🔄)

**중요:** 
- 🏪 표시된 필드는 sample_data.xlsx에서 제공해주셔야 합니다
- 🤖 표시된 필드는 챗봇이 자동으로 생성합니다
- 🔄 표시된 필드는 시스템이 자동으로 계산합니다

---

## 카테고리 정보

현재 시스템에서 사용하는 13개 카테고리:
1. 한식
2. 분식
3. 일식
4. 중식
5. 양식
6. 피자
7. 치킨
8. 패스트푸드
9. 아시안
10. 카페/디저트
11. 베이커리
12. 편의점
13. 마트