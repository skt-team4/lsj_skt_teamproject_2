# 나비얌 챗봇 최종 데이터베이스 스키마 (Feature 활용 상세)

## 개요
나비얌 챗봇의 AI 운영에 필요한 스키마와 각 Feature의 구체적인 활용처를 포함

### 데이터 소스 구분
- 🏪 **[SAMPLE_DATA]**: sample_data.xlsx에서 제공되는 데이터
- 🤖 **[CHATBOT_GENERATED]**: 챗봇이 대화를 통해 생성하는 데이터
- 🔄 **[DERIVED]**: 기존 데이터를 가공하여 파생된 데이터

### Feature 활용처 범례
- 💬 **챗봇 NLU/NLG**: 자연어 이해 및 응답 생성
- 🔍 **RAG 검색**: 벡터 검색 및 의미적 매칭
- 🎯 **Wide&Deep**: 추천 모델의 Wide/Deep 컴포넌트
- ⭐ **나비얌 특화**: 급식카드 관련 특화 기능

---

## 1. 핵심 데이터 테이블

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
    -- 💬 챗봇: "한식 먹고 싶어" → category="한식" 필터링
    -- 🔍 RAG: 카테고리별 임베딩으로 의미적 유사성 검색
    -- 🎯 Wide&Deep: user_age_group × shop_category 교차 특성
    -- ⭐ 나비얌: 청소년 선호 카테고리(패스트푸드, 분식) 우선순위
    
    address_name TEXT,                            
    -- 💬 챗봇: "강남역 근처" 등 지역 기반 질문 처리
    -- 🔍 RAG: 지역 정보 컨텍스트 제공
    -- 🎯 Wide&Deep: 지역별 선호도 학습
    
    is_good_influence_shop BOOLEAN DEFAULT FALSE, 
    -- 💬 챗봇: "착한가게 추천해줘" 요청 시 필터링
    -- 🔍 RAG: 착한가게 키워드 검색 시 가중치 부여
    -- 🎯 Wide&Deep: foodcard_verified × good_influence_shop 교차 특성
    -- ⭐ 나비얌: 급식카드 사용자에게 50% 이상 우선 추천
    
    is_food_card_shop VARCHAR(10),               
    -- 💬 챗봇: 급식카드 사용자 확인 후 필터링
    -- 🔍 RAG: 급식카드 관련 질문 시 필수 조건
    -- 🎯 Wide&Deep: 핵심 필터 조건
    -- ⭐ 나비얌: 급식카드로만 이용 가능한 가게 필터링
    
    open_hour VARCHAR(10),                        
    close_hour VARCHAR(10),
    break_start_hour VARCHAR(10),                 
    break_end_hour VARCHAR(10),
    -- 💬 챗봇: "지금 열려있는 곳" 요청 시 실시간 필터링
    -- 🔍 RAG: 시간 관련 컨텍스트 제공
    -- 🎯 Wide&Deep: time_period × food_type 교차 특성
    -- ⭐ 나비얌: 학교 점심시간에 맞춘 추천
    
    phone VARCHAR(20),                            
    -- 💬 챗봇: 최종 추천 시 "전화: 02-1234-5678" 제공
    
    owner_message TEXT,                           
    -- 💬 챗봇: 가게 소개 메시지로 친근한 응답 생성
    -- 🔍 RAG: 특별 이벤트나 할인 정보 검색
    
    latitude DECIMAL(10, 8),                      
    longitude DECIMAL(11, 8),
    -- 💬 챗봇: "500m 이내" 등 거리 기반 필터링
    -- 🎯 Wide&Deep: distance_km 수치 특성 계산
    -- ⭐ 나비얌: 학교 반경 내 가게 우선 추천
    
    -- 🔄 [DERIVED] 필드
    current_status VARCHAR(20) DEFAULT 'UNKNOWN', 
    -- 💬 챗봇: 즉시 "지금 영업중이에요" 응답
    -- 🔍 RAG: 실시간 상태 필터링
    -- 🎯 Wide&Deep: operating_hours_match 특성
    
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
    shop_id INT NOT NULL,                         
    
    menu_name VARCHAR(200) NOT NULL,              
    -- 💬 챗봇: "매운 음식" → "불닭볶음면", "매운치킨" 구체적 제안
    -- 🔍 RAG: 메뉴명 기반 의미적 검색
    -- 🎯 Wide&Deep: 메뉴별 선호도 학습
    
    price INT NOT NULL,                           
    -- 💬 챗봇: "1만원 이하" 요청 시 즉시 필터링
    -- 🔍 RAG: 가격대별 클러스터링
    -- 🎯 Wide&Deep: budget_range × price_tier 교차 특성
    -- ⭐ 나비얌: 급식카드 잔액 내 메뉴만 추천
    
    description TEXT,                             
    -- 💬 챗봇: "덜 맵게", "양 많이" 등 상세 정보 제공
    -- 🔍 RAG: 메뉴 설명 텍스트 기반 의미적 검색
    
    category VARCHAR(100),                        
    -- 💬 챗봇: "메인메뉴만", "세트메뉴" 등 세분화 요청 처리
    -- 🔍 RAG: 메뉴 타입별 필터링
    
    FOREIGN KEY (shop_id) REFERENCES shops(id),
    INDEX idx_shop (shop_id),
    INDEX idx_price (price)
);
```

### coupons 테이블 (쿠폰 정보) ⭐ 나비얌 특화
```sql
CREATE TABLE coupons (
    id VARCHAR(50) PRIMARY KEY,
    
    -- 🏪 [SAMPLE_DATA] 필드
    coupon_name VARCHAR(200) NOT NULL,            
    -- 💬 챗봇: "급식카드 특별할인 쿠폰이 있어요!" 안내
    -- 🔍 RAG: 쿠폰명 키워드 검색
    -- ⭐ 나비얌: 월말 잔액 부족 시 자동 제안
    
    description TEXT,                             
    -- 💬 챗봇: 쿠폰 사용 조건 상세 설명
    -- 🔍 RAG: 쿠폰 혜택 내용 검색
    
    discount_amount INT,                          
    -- 💬 챗봇: "2,000원 할인받을 수 있어요" 구체적 혜택 안내
    -- 🎯 Wide&Deep: 실제 결제 금액 계산
    -- ⭐ 나비얌: 잔액 부족 시 쿠폰 적용 후 금액 재계산
    
    discount_rate DECIMAL(3,2),                   
    -- 💬 챗봇: "20% 할인" 퍼센트 할인 안내
    -- 🎯 Wide&Deep: 할인율 기반 가격 재계산
    
    min_order_amount INT,                         
    -- 💬 챗봇: "5천원 이상 주문 시" 최소 주문 금액 체크
    -- 🎯 Wide&Deep: 쿠폰 적용 가능 여부 필터링
    
    usage_type VARCHAR(30),                       
    -- ALL: 모든 가게, SHOP: 특정 가게, CATEGORY: 특정 카테고리
    -- 💬 챗봇: 쿠폰 사용 가능 범위 안내
    -- 🔍 RAG: 쿠폰 타입별 필터링
    
    target_categories JSON,                       
    -- ["한식", "분식"] 등 적용 가능 카테고리
    -- 💬 챗봇: "한식, 분식에서 사용 가능해요"
    -- 🎯 Wide&Deep: 카테고리 매칭으로 쿠폰 필터링
    
    applicable_shops JSON,                        
    -- [shop_id 리스트] 사용 가능한 가게들
    -- 💬 챗봇: 특정 가게에서만 사용 가능 안내
    -- 🎯 Wide&Deep: 가게별 쿠폰 적용
    
    -- 🏪 [SAMPLE_DATA] 유효기간
    valid_from DATE,                              
    valid_until DATE,
    -- 💬 챗봇: "이번 달 말까지 사용 가능해요" 기한 안내
    -- 🎯 Wide&Deep: 현재 날짜 기준 유효성 체크
    -- ⭐ 나비얌: 월말 임박 쿠폰 우선 추천
    
    -- 🔄 [DERIVED] 필드
    is_active BOOLEAN DEFAULT TRUE,               
    -- 현재 사용 가능 여부 (유효기간 자동 계산)
    
    priority_score DECIMAL(3,2),                  
    -- 💬 챗봇: 우선순위 높은 쿠폰부터 제안
    -- 🎯 Wide&Deep: 쿠폰 추천 순서 결정
    -- ⭐ 나비얌: 급식카드 전용 쿠폰 우선순위 상향
    
    INDEX idx_usage_type (usage_type),
    INDEX idx_active (is_active),
    INDEX idx_valid_dates (valid_from, valid_until)
);
```

### users 테이블 (일반 사용자)
```sql
CREATE TABLE users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    
    -- 🏪 [SAMPLE_DATA] 필드
    name VARCHAR(100),                            
    -- 💬 챗봇: "민수야, 오늘 뭐 먹을래?" 개인화된 인사
    
    nickname VARCHAR(100),                        
    -- 💬 챗봇: 친근한 호칭으로 대화
    
    birthday DATE,                                
    -- 🎯 Wide&Deep: 연령대별 선호도 학습
    -- ⭐ 나비얌: 청소년/청년 구분하여 메뉴 추천
    
    current_address TEXT,                         
    -- 💬 챗봇: 기본 위치 기반 추천
    -- 🎯 Wide&Deep: 지역별 선호도 패턴
    
    -- 🔄 [DERIVED] 필드
    age_group VARCHAR(20),                        
    -- 💬 챗봇: "10대 친구들이 좋아하는" 연령별 추천
    -- 🎯 Wide&Deep: user_age_group × shop_category 교차 특성
    -- ⭐ 나비얌: 급식카드 대상 연령 확인
    
    region_code VARCHAR(20)                       
    -- 🎯 Wide&Deep: 지역별 인기 가게 학습
);
```

### foodcard_users 테이블 (급식카드 사용자) ⭐ 나비얌 핵심
```sql
CREATE TABLE foodcard_users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    
    -- 🏪 [SAMPLE_DATA] 필드
    user_id INT NOT NULL,                         
    
    card_number VARCHAR(50),                      
    -- 💬 챗봇: "급식카드 등록되어 있네요" 확인
    -- ⭐ 나비얌: 카드 인증으로 전용 서비스 제공
    
    balance INT DEFAULT 0,                        
    -- 💬 챗봇: "잔액 8,000원으로 먹을 수 있는" 실시간 안내
    -- 🔍 RAG: 잔액 범위 내 메뉴만 검색
    -- 🎯 Wide&Deep: budget_constraint 필수 제약조건
    -- ⭐ 나비얌: 잔액 부족 시 쿠폰 자동 제안
    
    status VARCHAR(20) DEFAULT 'ACTIVE',          
    -- 💬 챗봇: INACTIVE 시 "카드를 확인해주세요" 안내
    -- 🎯 Wide&Deep: ACTIVE 카드만 급식카드 혜택 적용
    
    -- 🔄 [DERIVED] 필드
    target_age_group VARCHAR(20),                 
    -- 💬 챗봇: "청소년 급식카드" 맞춤형 응답
    -- 🎯 Wide&Deep: 연령별 메뉴 선호도 적용
    -- ⭐ 나비얌: 초등(간식), 중고등(식사) 구분 추천
    
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
    user_id VARCHAR(100) NOT NULL,                
    session_id VARCHAR(200) NOT NULL,             
    
    input_text TEXT NOT NULL,                     
    -- 💬 챗봇: 원본 입력 저장하여 컨텍스트 유지
    -- 🔍 RAG: 이전 대화 검색하여 맥락 이해
    
    response_text TEXT NOT NULL,                  
    -- 💬 챗봇: 생성된 응답 저장하여 일관성 유지
    
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- 🤖 [CHATBOT_GENERATED] NLU 추출 정보
    extracted_intent VARCHAR(50),                 
    -- food_request, budget_inquiry, coupon_inquiry 등
    -- 💬 챗봇: 의도별 응답 템플릿 선택
    -- 🎯 Wide&Deep: 의도별 추천 전략 변경
    
    intent_confidence DECIMAL(4,3),               
    -- 💬 챗봇: 낮은 신뢰도 시 "혹시 ~하신가요?" 확인
    
    extracted_entities JSON,                      
    -- {food_type: "치킨", budget: 10000, location: "근처"}
    -- 💬 챗봇: 추출된 정보로 구체적 응답 생성
    -- 🔍 RAG: 엔티티 기반 검색 쿼리 구성
    -- 🎯 Wide&Deep: 추천 모델 입력 특성으로 변환
    
    -- 🤖 [CHATBOT_GENERATED] 대화 맥락
    user_strategy VARCHAR(30),                    
    -- onboarding_mode: 첫 사용자 친절 안내
    -- data_building_mode: 선호도 파악 질문
    -- normal_mode: 일반 추천
    -- urgent_mode: 잔액 부족 시 긴급 모드
    
    conversation_turn INT,                        
    -- 💬 챗봇: 대화 길이에 따라 상세도 조절
    
    INDEX idx_user_timestamp (user_id, timestamp),
    INDEX idx_session (session_id)
);
```

### user_interactions 테이블 (상호작용 및 학습 데이터)
```sql
CREATE TABLE user_interactions (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    
    -- 🤖 [CHATBOT_GENERATED] 필드
    user_id VARCHAR(100) NOT NULL,                
    session_id VARCHAR(200),                      
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    interaction_type VARCHAR(30),                 
    -- text_input: 텍스트 입력
    -- selection: 추천 중 선택
    -- feedback: 만족도 피드백
    -- coupon_use: 쿠폰 사용
    
    user_selection JSON,                          
    -- {shop_id: 15, menu_ids: [201, 202], coupon_id: "FOOD10"}
    -- 💬 챗봇: "좋은 선택이에요!" 선택 확인
    -- 🎯 Wide&Deep: 실제 선택으로 모델 학습
    
    -- 🔄 [DERIVED] 필드
    recommendations JSON,                         
    -- [{shop_id: 15, score: 0.92, coupon_applicable: true}]
    -- 🎯 Wide&Deep: 추천 결과와 실제 선택 비교
    
    -- 🤖 [CHATBOT_GENERATED] 학습용 특징
    food_preference_extracted VARCHAR(100),       
    -- 💬 챗봇: 다음 대화에 선호도 반영
    -- 🎯 Wide&Deep: 개인화 특성 업데이트
    
    budget_pattern_extracted INT,                 
    -- 🎯 Wide&Deep: 평균 지출 패턴 학습
    -- ⭐ 나비얌: 월말 예산 관리 조언
    
    companion_pattern_extracted VARCHAR(50),      
    -- 💬 챗봇: "친구랑 갈 만한 곳" 맞춤 추천
    
    coupon_usage JSON,                           
    -- {coupon_id: "FOOD10", discount_applied: 2000}
    -- 💬 챗봇: 쿠폰 사용 이력 기반 추가 제안
    -- ⭐ 나비얌: 쿠폰 사용 패턴 분석
    
    INDEX idx_user_timestamp (user_id, timestamp),
    INDEX idx_interaction_type (interaction_type)
);
```

### recommendations_log 테이블 (추천 로그)
```sql
CREATE TABLE recommendations_log (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    
    -- 🤖 [CHATBOT_GENERATED] 필드
    user_id VARCHAR(100) NOT NULL,                
    session_id VARCHAR(200),                      
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    request_food_type VARCHAR(100),               
    -- 💬 챗봇: 요청된 음식 종류 기록
    -- 🔍 RAG: 해당 카테고리 중심 검색
    
    request_budget INT,                           
    -- 🎯 Wide&Deep: 예산 제약 조건
    -- ⭐ 나비얌: 급식카드 잔액과 비교
    
    request_location VARCHAR(100),                
    -- 🎯 Wide&Deep: 거리 계산 기준점
    
    -- 🔄 [DERIVED] 필드
    recommendations JSON NOT NULL,                
    -- [{
    --   shop_id: 15, 
    --   score: 0.92, 
    --   reason: "착한가게+예산적합+인기메뉴",
    --   applicable_coupons: ["FOOD10", "TEEN20"]
    -- }]
    -- 💬 챗봇: 추천 이유 설명으로 신뢰도 향상
    -- ⭐ 나비얌: 적용 가능한 쿠폰 함께 제시
    
    recommendation_count INT NOT NULL,            
    recommendation_method VARCHAR(50),            
    -- wide_deep: Wide&Deep 모델
    -- rag: RAG 검색
    -- hybrid: 복합 추천
    -- emergency: 잔액 부족 시 긴급 추천
    
    confidence_score DECIMAL(4,3),                
    -- 💬 챗봇: 낮은 점수 시 "다른 옵션도 있어요"
    
    total_discount_available INT,                 
    -- 🔄 적용 가능한 총 할인 금액
    -- 💬 챗봇: "최대 3,000원까지 할인받을 수 있어요"
    -- ⭐ 나비얌: 급식카드 잔액 부족 시 강조
    
    INDEX idx_user_timestamp (user_id, timestamp),
    INDEX idx_method (recommendation_method)
);
```

---

## 3. 선택적 운영 테이블

### user_profiles 테이블 (개인화)
```sql
CREATE TABLE user_profiles (
    -- 🤖 [CHATBOT_GENERATED] 필드
    user_id VARCHAR(100) PRIMARY KEY,             
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    -- 🤖 [CHATBOT_GENERATED] 개인화 정보
    preferred_categories JSON,                    
    -- ["치킨", "한식", "분식"]
    -- 💬 챗봇: "평소 좋아하시는 치킨 어때요?"
    -- 🎯 Wide&Deep: 카테고리 선호도 가중치
    
    average_budget INT,                           
    -- 💬 챗봇: 예산 언급 없을 시 기본값 사용
    -- ⭐ 나비얌: 월평균 사용액 대비 절약 조언
    
    good_influence_preference DECIMAL(3,2),       
    -- 🎯 Wide&Deep: 착한가게 추천 가중치
    -- ⭐ 나비얌: 0.7 이상 시 착한가게 우선 추천
    
    interaction_count INT DEFAULT 0,              
    -- 💬 챗봇: 10회 이상 시 친근한 말투
    
    -- 🔄 [DERIVED] 필드
    favorite_shops JSON,                          
    -- [15, 23, 45] 자주 선택한 가게들
    -- 💬 챗봇: "자주 가시는 굽네치킨 오늘도 어때요?"
    
    recent_orders JSON,                           
    -- 최근 10개 주문 이력
    -- 💬 챗봇: "지난번 드신 불닭 또 드실래요?"
    
    coupon_preference JSON,                       
    -- {usage_rate: 0.8, preferred_types: ["정액할인"]}
    -- 💬 챗봇: 쿠폰 선호도 높으면 적극 제안
    -- ⭐ 나비얌: 쿠폰 사용률 기반 맞춤 제공
    
    monthly_stats JSON,                           
    -- {avg_spending: 150000, shop_diversity: 8}
    -- 💬 챗봇: "이번 달 다양하게 드셨네요!"
    -- ⭐ 나비얌: 월별 사용 패턴 분석
    
    INDEX idx_updated (last_updated)
);
```

### user_coupon_wallet 테이블 (사용자별 쿠폰 보관함) ⭐ 신규
```sql
CREATE TABLE user_coupon_wallet (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    
    -- 🤖 [CHATBOT_GENERATED] 필드
    user_id VARCHAR(100) NOT NULL,                
    coupon_id VARCHAR(50) NOT NULL,               
    
    issued_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    -- 💬 챗봇: "3일 전에 받으신 쿠폰이 있어요"
    
    used_at TIMESTAMP NULL,                       
    -- 💬 챗봇: 사용 완료 시 "쿠폰 사용 완료!"
    
    status VARCHAR(20) DEFAULT 'ACTIVE',          
    -- ACTIVE: 사용 가능
    -- USED: 사용 완료
    -- EXPIRED: 기간 만료
    
    -- 🔄 [DERIVED] 필드
    days_until_expiry INT,                        
    -- 💬 챗봇: "3일 후 만료되는 쿠폰이 있어요!"
    -- ⭐ 나비얌: 만료 임박 쿠폰 우선 추천
    
    reminder_sent BOOLEAN DEFAULT FALSE,          
    -- 💬 챗봇: 만료 3일 전 리마인더
    
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (coupon_id) REFERENCES coupons(id),
    INDEX idx_user_status (user_id, status),
    INDEX idx_expiry (days_until_expiry)
);
```

### performance_logs 테이블 (성능 모니터링)
```sql
CREATE TABLE performance_logs (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    
    -- 🤖 [CHATBOT_GENERATED] 필드
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    response_time_ms INT NOT NULL,                
    success BOOLEAN NOT NULL,                     
    
    nlu_processing_time_ms INT,                   
    -- NLU 의도 분석 시간
    
    rag_search_time_ms INT,                       
    -- RAG 벡터 검색 시간
    
    recommendation_time_ms INT,                   
    -- Wide&Deep 추천 계산 시간
    
    coupon_matching_time_ms INT,                  
    -- 쿠폰 매칭 처리 시간
    
    -- 성능 목표: 전체 응답 < 500ms
    
    INDEX idx_timestamp (timestamp),
    INDEX idx_response_time (response_time_ms)
);
```

---

## 🎯 실제 사용 시나리오별 Feature 활용

### 시나리오 1: "배고픈데 5천원밖에 없어" (급식카드 잔액 부족)

#### 1단계: NLU 처리
```sql
-- conversations 테이블
extracted_intent = 'food_request'
extracted_entities = '{"budget": 5000, "urgency": "high"}'
user_strategy = 'urgent_mode'  -- 잔액 부족 긴급 모드
```

#### 2단계: 급식카드 잔액 확인
```sql
-- foodcard_users 테이블 조회
SELECT balance FROM foodcard_users WHERE user_id = ?
-- 결과: balance = 5000
```

#### 3단계: 쿠폰 매칭
```sql
-- user_coupon_wallet에서 사용 가능한 쿠폰 조회
SELECT c.* FROM coupons c
JOIN user_coupon_wallet w ON c.id = w.coupon_id
WHERE w.user_id = ? 
  AND w.status = 'ACTIVE'
  AND c.min_order_amount <= 5000
ORDER BY c.discount_amount DESC
```

#### 4단계: 가게/메뉴 필터링
```sql
-- 5000원 + 쿠폰 할인으로 먹을 수 있는 메뉴 검색
SELECT s.shop_name, m.menu_name, 
       m.price - COALESCE(c.discount_amount, 0) as final_price
FROM shops s
JOIN menus m ON s.id = m.shop_id
LEFT JOIN applicable_coupons c ON ...
WHERE final_price <= 5000
  AND s.is_food_card_shop = 'Y'
  AND s.current_status = 'OPEN'
```

#### 5단계: 챗봇 응답
```
💬 "잔액이 5천원이네요! 걱정마세요, 쿠폰 써서 먹을 수 있는 곳 찾았어요! 🎫

**김밥천국 건대점** (도보 2분)
- 참치김밥 3,500원
- 🎫 1,000원 할인쿠폰 적용 가능 → 2,500원!

**착한분식** (도보 5분) 
- 떡볶이 4,000원
- 🎫 신규가입 2,000원 쿠폰 → 2,000원!
- 💚 착한가게 인증점

남은 잔액으로도 충분히 맛있게 드실 수 있어요! 😊"
```

### 시나리오 2: "매일 치킨만 먹는 것 같아" (다양성 추천)

#### 1단계: 사용자 프로필 분석
```sql
-- user_profiles 조회
SELECT recent_orders, monthly_stats 
FROM user_profiles WHERE user_id = ?
-- 결과: 최근 10개 중 7개가 치킨
```

#### 2단계: 다양성 점수 계산
```sql
-- Wide&Deep 모델에서 diversity_score 적용
diversity_weight = 0.8  -- 다양성 가중치 상향
```

#### 3단계: 새로운 카테고리 추천
```
💬 "치킨을 정말 좋아하시네요! 🍗 
오늘은 색다른 맛 어떠세요?

**베트남쌀국수** (새로운 맛!)
- 양지쌀국수 8,000원
- 🏷️ 첫 주문 시 20% 할인!

**맛있는두부** (건강한 선택)
- 두부김치 7,000원
- 💚 착한가게 + 건강식

가끔은 새로운 도전도 좋아요! 😊"
```

### 시나리오 3: 월말 쿠폰 만료 알림

```
💬 "민수야! 중요한 알림이 있어 📢

🎫 내일 만료되는 쿠폰 2개:
- 치킨 3,000원 할인 (BBQ)
- 전메뉴 20% 할인 (김밥천국)

잔액 15,000원으로 쿠폰 쓰면:
- BBQ 황금올리브 12,000원 (정가 15,000원)
- 김밥천국 제육덮밥 4,800원 (정가 6,000원)

쿠폰 아깝잖아~ 오늘 저녁은 여기 어때? 🍽️"
```

---

## 구현 우선순위 (Feature 중심)

### Phase 1: 핵심 기능
1. **기본 데이터**: shops, menus, users, foodcard_users
2. **대화 기록**: conversations (NLU 포함)
3. **기본 추천**: recommendations_log

### Phase 2: 쿠폰 시스템 ⭐
4. **쿠폰 마스터**: coupons
5. **쿠폰 지갑**: user_coupon_wallet
6. **쿠폰 활용**: user_interactions에 쿠폰 사용 기록

### Phase 3: 고급 개인화
7. **사용자 프로필**: user_profiles
8. **성능 모니터링**: performance_logs

---

## 쿠폰 기능이 중요한 이유

### 1. 급식카드 사용자 지원
- 월말 잔액 부족 시 추가 할인 제공
- 영양가 있는 식사 지속 가능하도록 지원

### 2. 착한가게 활성화
- 착한가게 전용 쿠폰으로 선순환 구조
- 사회적 가치 실현

### 3. 사용자 만족도 향상
- 실질적인 혜택으로 앱 사용률 증가
- 맞춤형 쿠폰으로 개인화 경험

### 4. 데이터 수집 및 학습
- 쿠폰 사용 패턴으로 선호도 정밀 분석
- A/B 테스트를 통한 추천 알고리즘 개선