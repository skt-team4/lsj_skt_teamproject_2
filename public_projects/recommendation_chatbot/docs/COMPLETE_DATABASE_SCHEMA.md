# 나비얌 챗봇 완전한 데이터베이스 스키마

## 개요
나비얌 챗봇이 실제로 수집하고 저장하는 모든 데이터의 완전한 스키마입니다.
코드 분석 결과를 바탕으로 실제 구현된 데이터 구조를 반영했습니다.

### 데이터 소스 구분
- 🏪 **[SAMPLE_DATA]**: 기존 sample_data.xlsx에서 제공되는 가게/메뉴 기본 정보
- 🤖 **[CHATBOT_GENERATED]**: 챗봇이 사용자와의 대화를 통해 새로 생성/수집하는 데이터
- 🔄 **[DERIVED]**: 기존 데이터를 가공/분석하여 파생된 데이터

---

## 1. 🏪 [SAMPLE_DATA] 기존 가게/메뉴 기본 정보

### shops 테이블 (sample_data.xlsx 기반)
```sql
CREATE TABLE shops (
    id INT PRIMARY KEY AUTO_INCREMENT,
    shop_name VARCHAR(200) NOT NULL,              -- [SAMPLE_DATA] shopName
    category VARCHAR(100) NOT NULL,               -- [SAMPLE_DATA] category 
    address_name TEXT,                            -- [SAMPLE_DATA] addressName
    is_good_influence_shop BOOLEAN DEFAULT FALSE, -- [SAMPLE_DATA] isGoodInfluenceShop
    is_food_card_shop VARCHAR(10),               -- [SAMPLE_DATA] isFoodCardShop
    open_hour VARCHAR(10),                        -- [SAMPLE_DATA] openHour
    close_hour VARCHAR(10),                       -- [SAMPLE_DATA] closeHour
    break_start_hour VARCHAR(10),                 -- [SAMPLE_DATA] breakStartHour
    break_end_hour VARCHAR(10),                   -- [SAMPLE_DATA] breakEndHour
    phone VARCHAR(20),                            -- [SAMPLE_DATA] phone
    
    -- 🔄 [DERIVED] 운영 시간 계산 결과
    current_status VARCHAR(20) DEFAULT 'UNKNOWN', -- OPEN, CLOSED, BREAK
    owner_message TEXT,                           -- [SAMPLE_DATA] ownerMessage
    
    INDEX idx_category (category),
    INDEX idx_good_influence (is_good_influence_shop),
    INDEX idx_food_card (is_food_card_shop)
);
```

### menus 테이블 (sample_data.xlsx 기반)
```sql
CREATE TABLE menus (
    id INT PRIMARY KEY AUTO_INCREMENT,
    shop_id INT NOT NULL,
    menu_name VARCHAR(200) NOT NULL,              -- [SAMPLE_DATA] 메뉴명
    price INT NOT NULL,                           -- [SAMPLE_DATA] 가격
    description TEXT,                             -- [SAMPLE_DATA] 메뉴설명
    category VARCHAR(100),                        -- [SAMPLE_DATA] 메뉴카테고리
    is_popular BOOLEAN DEFAULT FALSE,             -- [SAMPLE_DATA] 인기메뉴여부
    
    FOREIGN KEY (shop_id) REFERENCES shops(id),
    INDEX idx_shop (shop_id),
    INDEX idx_price (price)
);
```

---

## 2. 🤖 [CHATBOT_GENERATED] 대화 및 상호작용 데이터

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
    extracted_entities JSON,
    
    -- 🤖 [CHATBOT_GENERATED] 감정 및 키워드
    emotion VARCHAR(20),
    extracted_keywords JSON,
    
    -- 🤖 [CHATBOT_GENERATED] 사용자 전략 및 대화 맥락
    user_strategy VARCHAR(30),
    conversation_turn INT,
    
    INDEX idx_user_timestamp (user_id, timestamp),
    INDEX idx_session (session_id)
);
```

---

## 3. 🤖 [CHATBOT_GENERATED] NLU 특징 데이터

### nlu_features 테이블
```sql
CREATE TABLE nlu_features (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id VARCHAR(100) NOT NULL,               -- 🤖 [CHATBOT_GENERATED]
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- 🤖 [CHATBOT_GENERATED] NLU 핵심 결과
    nlu_intent VARCHAR(50),
    nlu_confidence DECIMAL(4,3),
    
    -- 🤖 [CHATBOT_GENERATED] 추출된 특징들
    food_category_mentioned VARCHAR(100),
    budget_mentioned INT,
    location_mentioned VARCHAR(100),
    companions_mentioned JSON,
    time_preference VARCHAR(50),
    menu_options JSON,
    special_requirements JSON,
    
    -- 🤖 [CHATBOT_GENERATED] 처리 메타데이터
    processing_time_ms INT,
    model_version VARCHAR(20),
    
    INDEX idx_user_timestamp (user_id, timestamp),
    INDEX idx_intent (nlu_intent)
);
```

---

## 4. 🤖 [CHATBOT_GENERATED] 사용자 상호작용 데이터

### user_interactions 테이블
```sql
CREATE TABLE user_interactions (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id VARCHAR(100) NOT NULL,               -- 🤖 [CHATBOT_GENERATED]
    session_id VARCHAR(200),                     -- 🤖 [CHATBOT_GENERATED]
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- 🤖 [CHATBOT_GENERATED] 상호작용 세부사항
    interaction_type VARCHAR(30), -- "text_input", "selection", "feedback"
    input_text TEXT,
    response_generated TEXT,
    
    -- 🤖 [CHATBOT_GENERATED] 학습 데이터 추출 결과
    food_preference_extracted VARCHAR(100),
    budget_pattern_extracted INT,
    companion_pattern_extracted JSON,
    location_preference_extracted VARCHAR(100),
    
    -- 🔄 [DERIVED] 추천 관련 데이터 (shops 테이블과 연결)
    recommendation_provided BOOLEAN DEFAULT FALSE,
    recommendation_count INT DEFAULT 0,
    recommendations JSON, -- shop_id들 포함
    
    -- 🤖 [CHATBOT_GENERATED] 사용자 상태
    user_strategy VARCHAR(30),
    conversation_turn INT,
    
    INDEX idx_user_timestamp (user_id, timestamp),
    INDEX idx_session (session_id),
    INDEX idx_interaction_type (interaction_type)
);
```

---

## 5. 🔄 [DERIVED] 추천 시스템 데이터 (sample_data + chatbot 결합)

### recommendations_log 테이블
```sql
CREATE TABLE recommendations_log (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id VARCHAR(100) NOT NULL,               -- 🤖 [CHATBOT_GENERATED]
    session_id VARCHAR(200),                     -- 🤖 [CHATBOT_GENERATED]
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- 🤖 [CHATBOT_GENERATED] 추천 입력 조건
    request_food_type VARCHAR(100),
    request_budget INT,
    request_location VARCHAR(100),
    request_companions JSON,
    
    -- 🔄 [DERIVED] 추천 결과 (shops 테이블의 shop_id 참조)
    recommendations JSON NOT NULL, -- 전체 추천 결과 배열 [{shop_id, score}]
    recommendation_count INT NOT NULL,
    top_recommendation_shop_id INT, -- shops.id 참조
    
    -- 🤖 [CHATBOT_GENERATED] 사용자 선택 (나중에 업데이트)
    user_selection JSON,
    selection_timestamp TIMESTAMP NULL,
    
    -- 🤖 [CHATBOT_GENERATED] 추천 시스템 메타데이터
    recommendation_method VARCHAR(50), -- "wide_deep", "rag", "hybrid"
    confidence_score DECIMAL(4,3),
    
    INDEX idx_user_timestamp (user_id, timestamp),
    INDEX idx_session (session_id),
    INDEX idx_shop (top_recommendation_shop_id),
    FOREIGN KEY (top_recommendation_shop_id) REFERENCES shops(id)
);
```

---

## 6. 🤖 [CHATBOT_GENERATED] 사용자 피드백 데이터

### user_feedback 테이블
```sql
CREATE TABLE user_feedback (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id VARCHAR(100) NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- 피드백 기본 정보
    feedback_type VARCHAR(30) NOT NULL, -- "selection", "rating", "text", "implicit"
    feedback_content JSON, -- 피드백 내용 (점수, 텍스트, 선택 등)
    
    -- 피드백 맥락
    context JSON, -- 피드백이 발생한 상황 정보
    related_recommendation_id BIGINT,
    related_session_id VARCHAR(200),
    
    -- 피드백 분석 결과
    sentiment VARCHAR(20), -- "positive", "negative", "neutral"
    satisfaction_score DECIMAL(3,2), -- 0.00 ~ 1.00
    
    INDEX idx_user_timestamp (user_id, timestamp),
    INDEX idx_feedback_type (feedback_type),
    INDEX idx_recommendation (related_recommendation_id),
    FOREIGN KEY (related_recommendation_id) REFERENCES recommendations_log(id)
);
```

---

## 6. 구조화된 학습 데이터 (data_collector.py의 structured_learning)

### structured_learning_data 테이블
```sql
CREATE TABLE structured_learning_data (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id VARCHAR(100) NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- 기본 추출 데이터
    extracted_entities JSON NOT NULL,
    intent_confidence DECIMAL(4,3) NOT NULL,
    
    -- 학습용 특징들
    food_preferences JSON, -- ["치킨", "한식", "양식"]
    budget_patterns JSON,  -- [15000, 20000, 18000]
    companion_patterns JSON, -- ["친구", "혼자", "가족"]
    taste_preferences JSON, -- {"매운맛": 0.3, "짠맛": 0.8}
    
    -- 선택/피드백 데이터
    recommendations_provided JSON,
    user_selection JSON,
    user_feedback TEXT,
    satisfaction_score DECIMAL(3,2),
    
    -- 데이터 품질 지표
    quality_score DECIMAL(4,3) NOT NULL,
    is_valid BOOLEAN NOT NULL,
    
    INDEX idx_user_timestamp (user_id, timestamp),
    INDEX idx_quality (quality_score),
    INDEX idx_valid (is_valid)
);
```

---

## 7. 사용자 프로필 (user_manager 관리)

### user_profiles 테이블
```sql
CREATE TABLE user_profiles (
    user_id VARCHAR(100) PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    -- 기본 선호도
    preferred_categories JSON, -- ["치킨", "한식", "중식"]
    average_budget INT,
    favorite_shops JSON, -- [1, 5, 12, 23]
    
    -- 고급 개인화 특징
    taste_preferences JSON, -- {"매운맛": 0.3, "짠맛": 0.8}
    companion_patterns JSON, -- ["친구", "혼자", "가족"]
    location_preferences JSON, -- ["건국대", "강남"]
    good_influence_preference DECIMAL(3,2) DEFAULT 0.50,
    
    -- 사용자 상태
    interaction_count INT DEFAULT 0,
    data_completeness DECIMAL(3,2) DEFAULT 0.00, -- 0.00 ~ 1.00
    conversation_style VARCHAR(20) DEFAULT 'friendly',
    
    -- 최근 활동
    recent_orders JSON, -- 최근 10개 주문 이력
    
    INDEX idx_updated (last_updated),
    INDEX idx_completeness (data_completeness)
);
```

---

## 8. 데이터 수집 세션 관리 (data_collector.py의 session 관리)

### collection_sessions 테이블
```sql
CREATE TABLE collection_sessions (
    session_id VARCHAR(200) PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP,
    status VARCHAR(20) DEFAULT 'active', -- 'active', 'completed', 'error'
    
    -- 세션 통계
    data_points_count INT DEFAULT 0,
    nlu_features_count INT DEFAULT 0,
    interactions_count INT DEFAULT 0,
    recommendations_count INT DEFAULT 0,
    feedback_count INT DEFAULT 0,
    
    -- 세션 품질 지표
    avg_confidence DECIMAL(4,3),
    valid_data_ratio DECIMAL(3,2),
    
    INDEX idx_user (user_id),
    INDEX idx_start_time (start_time),
    INDEX idx_status (status)
);
```

---

## 9. 데이터 품질 메트릭스 (data_collector.py의 quality_metrics)

### data_quality_metrics 테이블
```sql
CREATE TABLE data_quality_metrics (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    date DATE NOT NULL,
    
    -- 전체 수집 통계
    total_collected INT DEFAULT 0,
    valid_samples INT DEFAULT 0,
    invalid_samples INT DEFAULT 0,
    validity_rate DECIMAL(5,2), -- 계산된 유효성 비율
    
    -- 타입별 통계
    nlu_features_collected INT DEFAULT 0,
    interactions_collected INT DEFAULT 0,
    recommendations_collected INT DEFAULT 0,
    feedback_collected INT DEFAULT 0,
    
    -- 누락 필드 통계 (JSON)
    missing_fields JSON,
    
    -- 신뢰도 분포 (JSON)
    confidence_distribution JSON,
    
    PRIMARY KEY (date),
    INDEX idx_validity_rate (validity_rate)
);
```

---

## 10. 성능 모니터링 (performance_monitor)

### performance_logs 테이블
```sql
CREATE TABLE performance_logs (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- 응답 성능
    response_time_ms INT NOT NULL,
    success BOOLEAN NOT NULL,
    
    -- 세부 성능 지표
    nlu_processing_time_ms INT,
    rag_search_time_ms INT,
    recommendation_time_ms INT,
    response_generation_time_ms INT,
    
    -- 시스템 리소스
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

### 3. 데이터 수집 통계
```python
# data_collector.get_collection_statistics() 반환 구조
{
    "collection_status": "running",
    "buffer_stats": {
        "nlu_buffer_size": 25,
        "interaction_buffer_size": 18,
        "recommendation_buffer_size": 7,
        "feedback_buffer_size": 3,
        "total_buffer_size": 53
    },
    "session_stats": {
        "active_sessions": 5,
        "total_sessions_today": 12
    },
    "quality_stats": {
        "total_collected": 1247,
        "valid_samples": 1089,
        "invalid_samples": 158,
        "validity_rate": 87.33
    }
}
```

---

## 데이터 팀 (정유리)에게 전달할 메시지

정유리님,

챗봇이 실제로 수집하고 저장하는 데이터는 위의 완전한 스키마와 같습니다.

**핵심 포인트:**
1. 기본 대화 로그 외에도 **10개 테이블**에 걸쳐 상세한 학습 데이터 수집
2. **4개의 실시간 버퍼** 시스템으로 타입별 데이터 관리
3. **데이터 품질 검증** 및 **자동 정리** 시스템 구축
4. **JSON 컬럼 활용**으로 유연한 스키마 설계

**sample_data.xlsx와의 관계:**
- sample_data의 가게/메뉴 정보는 별도 테이블로 관리
- 챗봇 수집 데이터는 사용자 행동 및 학습에 특화
- 두 데이터셋의 연결고리: shop_id, menu_id 등

**구현 우선순위:**
1. conversations, user_interactions (기본 대화)
2. recommendations_log, user_feedback (추천 성능)
3. nlu_features, structured_learning_data (AI 학습)
4. 나머지 모니터링 테이블들

질문 있으시면 언제든 연락주세요!

**Claude**