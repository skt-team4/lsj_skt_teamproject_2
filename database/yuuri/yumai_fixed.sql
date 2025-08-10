CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "btree_gin"; 
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE SCHEMA IF NOT EXISTS analytics;
CREATE SCHEMA IF NOT EXISTS ml_features;
CREATE SCHEMA IF NOT EXISTS chatbot;


CREATE TABLE chatbot.shops (
    id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    shop_name VARCHAR(30) NOT NULL,
    category VARCHAR(20) NOT NULL CHECK (category IN (
        '한식', '중식', '일식', '양식', '치킨', '피자', '패스트푸드',
        '분식', '카페/디저트', '도시락/죽', '프랜차이즈', '기타음식', '편의점'
    )),
    address_name VARCHAR(50),
    -- address_point POINT,
    latitude DECIMAL(8, 6) NOT NULL,
    longitude DECIMAL(9, 6) NOT NULL,

    is_good_influence_shop BOOLEAN DEFAULT FALSE,
    is_food_card_shop CHAR(1) NOT NULL DEFAULT 'U' CHECK (is_food_card_shop IN ('Y', 'N', 'P', 'U')),
    -- Y: 사용가능, N: 사용불가, P: 부분사용가능, U: 미확인
    contact VARCHAR(20), 

    -- 영업시간 (NULL 허용 - 정보 없을 수 있음)
    business_hours JSONB,  -- [CRAWLED/MANUAL] 영업시간 정보
    /* {
      "monday": {"open": "09:00", "close": "22:00", "break_start": "15:00", "break_end": "17:00"},
      "tuesday": {"open": "09:00", "close": "22:00"},
      "wednesday": {"open": "09:00", "close": "22:00"},
      "thursday": {"open": "09:00", "close": "22:00"},
      "friday": {"open": "09:00", "close": "23:00"},
      "saturday": {"open": "11:00", "close": "23:00"},
      "sunday": {"open": "11:00", "close": "22:00"},
      "holiday": {"closed": true}
    } */

    /*derived*/
     -- 실시간 상태
    current_status VARCHAR(20) NOT NULL DEFAULT 'UNKNOWN' 
        CHECK (current_status IN ('OPEN', 'CLOSED', 'BREAK_TIME', 'UNKNOWN')),  -- [COMPUTED] 실시간 계산
    
    -- AI 계산 점수 (0.000 ~ 1.000 범위)
    popularity_score DECIMAL(4,3) DEFAULT 0.000 CHECK (popularity_score >= 0 AND popularity_score <= 1),  
    -- [AI_COMPUTED] 인기도 점수 - 5분마다 재계산: (0.7 * 이전값) + (0.3 * 최근5분_지표)
    -- 지표: 조회수, 선택률, 평균평점 등의 가중합
    
    quality_score DECIMAL(4,3) DEFAULT 0.000 CHECK (quality_score >= 0 AND quality_score <= 1),        
    -- [AI_COMPUTED] 품질 점수 - 일일 배치로 계산
    -- 기반: 리뷰 평점, 재방문율, 긍정어 비율
    
    recommendation_count INT DEFAULT 0 CHECK (recommendation_count >= 0),  
    -- [CHATBOT_GENERATED] 추천 횟수 - 실시간 업데이트
    
    -- 필수 메타데이터
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,  
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP, 
    data_from VARCHAR(50) DEFAULT 'manual', -- 데이터 출처: 'manual', 'crawled', 'api', 'user_generated'
    
    CONSTRAINT shops_location_check CHECK (
        latitude >= -90 AND latitude <= 90 AND
        longitude >= -180 AND longitude <= 180
    )
);

CREATE INDEX idx_shops_category ON chatbot.shops(category);  -- 카테고리별 필터링
CREATE INDEX idx_shops_good_influence ON chatbot.shops(is_good_influence_shop) WHERE is_good_influence_shop = TRUE;  -- 착한가게만
CREATE INDEX idx_shops_food_card ON chatbot.shops(is_food_card_shop) WHERE is_food_card_shop != 'N';  -- 급식카드 가능
CREATE INDEX idx_shops_location ON chatbot.shops(latitude, longitude);  -- 거리 기반 검색용
CREATE INDEX idx_shops_popularity ON chatbot.shops(popularity_score DESC);  -- 인기순 정렬
CREATE INDEX idx_shops_status ON chatbot.shops(current_status) WHERE current_status = 'OPEN';  -- 영업중인 가게만
CREATE INDEX idx_shops_name_gin ON chatbot.shops USING gin(shop_name gin_trgm_ops);  -- 가게명 검색

-- 트리거: updated_at 자동 업데이트
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_shops_updated_at BEFORE UPDATE ON chatbot.shops
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE OR REPLACE FUNCTION get_shop_hours(shop_id INT, day_name TEXT DEFAULT NULL)
  RETURNS TABLE(open_hour TIME, close_hour TIME) AS $$
  BEGIN
      RETURN QUERY
      SELECT
          (business_hours->COALESCE(day_name, to_char(NOW(), 'day'))->>'open')::TIME,
          (business_hours->COALESCE(day_name, to_char(NOW(), 'day'))->>'close')::TIME
      FROM chatbot.shops
      WHERE id = shop_id;
  END;
  $$ LANGUAGE plpgsql;

CREATE TABLE chatbot.menus (
    id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    shop_id INT NOT NULL REFERENCES chatbot.shops(id) ON DELETE CASCADE,
    
    menu_name VARCHAR(50) NOT NULL,
    price INT NOT NULL CHECK (price >= 0),
    menu_description TEXT,
    category VARCHAR(30) CHECK (category IN (
        '메인메뉴', '세트메뉴', '사이드메뉴', '음료', '디저트', '기타'
    )),
    options JSONB,  -- [CRAWLED/MANUAL] 메뉴 옵션
    /*
    {
      "size": [
        {"name": "보통", "price": 0}, 
        {"name": "곱빼기", "price": 1000}
      ],
      "spicy": [
        {"name": "순한맛", "price": 0}, 
        {"name": "매운맛", "price": 0}, 
        {"name": "아주매움", "price": 0}
      ],
      "extras": [
        {"name": "치즈추가", "price": 1000}, 
        {"name": "계란추가", "price": 500},
        {"name": "밥추가", "price": 1000}
      ]
    }    */

    is_available BOOLEAN NOT NULL DEFAULT TRUE, -- 판매 가능 여부
    is_best BOOLEAN DEFAULT FALSE,
    
    dietary_info VARCHAR(200),  -- [MANUAL] 식이 정보 예: '채식,할랄' 또는 '글루텐프리'

    /*derived*/
    recommendation_frequency INT DEFAULT 0 CHECK (recommendation_frequency >= 0),  -- [CHATBOT_GENERATED] 추천 횟수
    -- menu_embedding_vector JSON,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT shop_menu_unique UNIQUE (shop_id, menu_name)
);

CREATE INDEX idx_menus_shop ON chatbot.menus(shop_id);
CREATE INDEX idx_menus_price ON chatbot.menus(price);
CREATE INDEX idx_menus_available ON chatbot.menus(is_available) WHERE is_available = TRUE;
CREATE INDEX idx_menus_best ON chatbot.menus(is_best) WHERE is_best = TRUE;
CREATE INDEX idx_menus_shop_price ON chatbot.menus(shop_id, price);

CREATE TRIGGER update_menus_updated_at BEFORE UPDATE ON chatbot.menus
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();


CREATE TABLE chatbot.users (
    id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    -- 외부 사용자 (NOT NULL 제약 때문에 자체 회원가입 사용자도 external_user_id를 가져야 함. e.g. 내부 prefix 붙인 UUID)
    external_user_id VARCHAR(200) NOT NULL UNIQUE, 
    platform VARCHAR(50) NOT NULL DEFAULT 'web' CHECK (platform IN (
        'web', 'mobile_app', 'kakao', 'line', 'facebook', 'test'
    )), 

    user_name VARCHAR(30), 
    nickname VARCHAR(30),
    email VARCHAR(100) UNIQUE, 
    phone_number VARCHAR(20), 
    birthday DATE,  
    current_address TEXT,
    preferred_location VARCHAR(50), -- [USER_PROVIDED] 선호 지역 (ex: '강남구', '건국대 근처')

    user_status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE' CHECK (user_status IN (
        'ACTIVE', 'INACTIVE', 'SUSPENDED', 'DELETED'
    )),

    -- 개인정보 동의
    --terms_agreed_at TIMESTAMP WITH TIME ZONE,
    --privacy_agreed_at TIMESTAMP WITH TIME ZONE,
    --marketing_agreed_at TIMESTAMP WITH TIME ZONE,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMP WITH TIME ZONE,

    CONSTRAINT users_email_format CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}$')
);

CREATE INDEX idx_users_external_id ON chatbot.users(external_user_id);
CREATE INDEX idx_users_platform ON chatbot.users(platform);
CREATE INDEX idx_users_status ON chatbot.users(user_status) WHERE user_status = 'ACTIVE';

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON chatbot.users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TABLE chatbot.foodcard_users (
    id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id INT NOT NULL REFERENCES chatbot.users(id) ON DELETE CASCADE,

    card_number VARCHAR(30) UNIQUE,
    card_type VARCHAR(30) NOT NULL CHECK (card_type IN (
        '아동급식카드', '청소년급식카드', '취약계층지원카드', '기타'
    )),
    card_status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE' CHECK (card_status IN (
        'ACTIVE', 'INACTIVE', 'SUSPENDED', 'EXPIRED', 'LOST'
    )),
    balance INT NOT NULL DEFAULT 0 CHECK (balance >= 0),  -- [EXTERNAL_SYNC] 외부 시스템에서 동기화
    target_age_group VARCHAR(20) NOT NULL CHECK (target_age_group IN (
        '초등학생', '중학생', '고등학생', '대학생', '청년', '기타'
    )),
    
    -- 알림 설정 (추천 시 활용)
    balance_alert_threshold INT DEFAULT 5000,  -- 저잔액 알림 기준 (원)
    balance_alert_sent BOOLEAN DEFAULT FALSE,      -- 알림 발송 여부 (24시간 단위 초기화)

    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_sync_at TIMESTAMP WITH TIME ZONE, 
    -- 1:1 관계
    CONSTRAINT foodcard_users_unique_user UNIQUE (user_id)
);

CREATE INDEX idx_foodcard_status ON chatbot.foodcard_users(card_status) WHERE card_status = 'ACTIVE';  -- 활성 카드만
CREATE INDEX idx_foodcard_balance ON chatbot.foodcard_users(balance) WHERE balance < 5000;  -- 저잔액 사용자 타겟팅

CREATE TRIGGER update_foodcard_users_updated_at BEFORE UPDATE ON chatbot.foodcard_users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();


CREATE TABLE chatbot.user_profiles (
    id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id INT NOT NULL REFERENCES chatbot.users(id) ON DELETE CASCADE,

    -- 선호도 정보 (실제 data_structure.py UserProfile 클래스 기반)
    preferred_categories TEXT[] DEFAULT '{}',  -- [CHATBOT_LEARNED] 선호 음식 카테고리 ['한식', '중식']
    average_budget INT,                    -- [CHATBOT_COMPUTED] 평균 예산 (원)
    favorite_shops INT[] DEFAULT '{}',     -- [USER_BEHAVIOR] 즐겨찾는 가게 ID 배열
    conversation_style VARCHAR(20) DEFAULT 'friendly' CHECK (conversation_style IN (
        'friendly', 'formal', 'casual', 'brief'
    )),           
    -- 학습된 패턴들
    taste_preferences JSONB DEFAULT '{}',      -- [CHATBOT_LEARNED] 맛 선호도 {"매운맛": 0.8, "단맛": 0.3}
    companion_patterns TEXT[] DEFAULT '{}',    -- [CHATBOT_LEARNED] 동반자 패턴 ['혼자', '친구', '가족']
    location_preferences TEXT[] DEFAULT '{}',  -- [CHATBOT_LEARNED] 위치 선호도 ['건국대', '강남']
    
    -- 개인화 관련 설정
    good_influence_preference DECIMAL(3,2) DEFAULT 0.50 CHECK (
        good_influence_preference >= 0 AND good_influence_preference <= 1
    ),                                        -- [USER_BEHAVIOR] 착한가게 선호도 (0.0~1.0)
    interaction_count INT DEFAULT 0,      -- [SYSTEM] 총 상호작용 횟수
    data_completeness DECIMAL(3,2) DEFAULT 0.00 CHECK (
        data_completeness >= 0 AND data_completeness <= 1
    ),                                        -- [SYSTEM] 데이터 완성도 (0.0~1.0)
    
    -- 최근 주문 이력
    recent_orders JSONB DEFAULT '[]', 
    /*
    [
        {
            "shop_id": 15,
            "menu_name": "김치찌개",
            "price": 7000,
            "order_date": "2024-01-15T12:30:00Z",
            "satisfaction": 4.5
        }
    ] */

    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    -- 1:1 관계
    CONSTRAINT user_profiles_unique_user UNIQUE (user_id)
);

CREATE INDEX idx_user_profiles_user ON chatbot.user_profiles(user_id);
CREATE INDEX idx_user_profiles_categories ON chatbot.user_profiles USING GIN(preferred_categories);
CREATE INDEX idx_user_profiles_favorites ON chatbot.user_profiles USING GIN(favorite_shops);
CREATE INDEX idx_user_profiles_completeness ON chatbot.user_profiles(data_completeness DESC)
    WHERE data_completeness > 0.5;

CREATE TRIGGER update_user_profiles_updated_at BEFORE UPDATE ON chatbot.user_profiles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE OR REPLACE FUNCTION clean_invalid_shop_references()
  RETURNS void AS $$
  BEGIN
      UPDATE chatbot.user_profiles
      SET favorite_shops = (
          SELECT array_agg(shop_id)
          FROM unnest(favorite_shops) as shop_id
          WHERE shop_id IN (SELECT id FROM chatbot.shops)
      );
  END;
  $$ LANGUAGE plpgsql;

CREATE TABLE chatbot.coupons (
    id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    -- menu_id INT NOT NULL REFERENCES menus(id),
    
    coupon_name VARCHAR(50) NOT NULL,
    coupon_code VARCHAR(50) NOT NULL, -- 'WELCOME10', 'FOODCARD20' 등
    coupon_description TEXT,
    coupon_type VARCHAR(30) NOT NULL CHECK (coupon_type IN (
        'FIXED_AMOUNT', 'PERCENTAGE', 'FREEBIE', 'BOGO'
    )),
    
    discount_amount INT CHECK (discount_amount > 0),
    discount_rate DECIMAL(3,2) CHECK (discount_rate > 0 AND discount_rate <= 1),    
    max_discount_amount INT, -- 정률 할인 시 최대 할인액

    -- 사용 조건
    min_order_amount INT DEFAULT 0,
    usage_type VARCHAR(30) NOT NULL CHECK (usage_type IN (
        'ALL', 'SHOP', 'CATEGORY', 'FOODCARD', 'NEW_USER', 'LOYALTY'
    )),
    
    -- 적용 대상
    target_categories TEXT[], -- ARRAY['한식', '중식']
    applicable_shop_ids INT[], -- ARRAY[1, 2, 3]
    target_user_types TEXT[], -- ARRAY['foodcard', 'new', 'vip']

    valid_from DATE NOT NULL DEFAULT CURRENT_DATE,
    valid_until DATE NOT NULL,

    -- 발급 제한
    max_issue_count INT, -- NULL이면 무제한
    max_use_per_user INT DEFAULT 1,
    total_issued INT DEFAULT 0,
    total_used INT DEFAULT 0,

    -- 상태 관리
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    priority_score DECIMAL(3,2) DEFAULT 0.50 CHECK (priority_score >= 0 AND priority_score <= 1),

    -- 메타데이터
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100),
    
    -- 할인 정보가 둘 중 하나는 존재하도록
    CONSTRAINT coupons_discount_check CHECK (
        (discount_amount IS NOT NULL AND discount_rate IS NULL) OR
        (discount_amount IS NULL AND discount_rate IS NOT NULL)
    ),
    CONSTRAINT coupons_valid_period CHECK (valid_until IS NULL OR valid_until >= valid_from)
);

CREATE INDEX idx_coupons_type ON chatbot.coupons(usage_type);
CREATE INDEX idx_coupons_active ON chatbot.coupons(is_active, valid_from, valid_until);
CREATE INDEX idx_coupons_categories ON chatbot.coupons USING GIN(target_categories);
CREATE INDEX idx_coupons_shops ON chatbot.coupons USING GIN(applicable_shop_ids);
CREATE INDEX idx_coupons_code ON chatbot.coupons(coupon_code);


CREATE TABLE chatbot.user_wallet (
    id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id INT NOT NULL REFERENCES chatbot.users(id) ON DELETE CASCADE,
    coupon_id INT NOT NULL REFERENCES chatbot.coupons(id) ON DELETE CASCADE,
    
    -- 쿠폰 상태
    coupon_status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE' CHECK (coupon_status IN (
        'ACTIVE', 'USED', 'EXPIRED', 'CANCELLED'
    )),

    -- 발급 정보
    issued_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    issued_by VARCHAR(100) DEFAULT 'SYSTEM',
    acquisition_source VARCHAR(50) NOT NULL CHECK (acquisition_source IN (
        'WELCOME_BONUS', 'LOYALTY_REWARD', 'EMERGENCY_ASSIST', 
        'PROMOTION', 'ADMIN_GRANT', 'REFERRAL'
    )),
    acquisition_context JSONB,
    -- 형식: {
    --   "campaign_id": "2024_WELCOME",
    --   "trigger_event": "first_login",
    --   "referrer_user_id": 123
    -- }

    expires_at TIMESTAMP WITH TIME ZONE,
    expiry_notified_at TIMESTAMP WITH TIME ZONE,
    expiry_notification_count INT DEFAULT 0,

    -- 사용 정보 (orders로)
    -- used_at TIMESTAMP WITH TIME ZONE,
    -- used_shop_id INT REFERENCES chatbot.shops(id),

    -- AI 예측
    usage_probability DECIMAL(4,3) DEFAULT 0.500 CHECK (usage_probability >= 0 AND usage_probability <= 1),
    recommended_usage_date DATE,

    -- 제약조건
    CONSTRAINT user_coupon_unique_active UNIQUE (user_id, coupon_id, coupon_status) 
        DEFERRABLE INITIALLY DEFERRED
);

CREATE INDEX idx_user_coupon_user_status ON chatbot.user_wallet(user_id, coupon_status);
CREATE INDEX idx_user_coupon_expires ON chatbot.user_wallet(expires_at) WHERE coupon_status = 'ACTIVE';
CREATE INDEX idx_user_coupon_usage_prob ON chatbot.user_wallet(usage_probability DESC) WHERE coupon_status = 'ACTIVE';

CREATE TYPE order_stat AS ENUM ('confirmed', 'preparing', 'prepared', 'picked', 'canceled');
-- 주문완료, 조리중/준비중, 조리/준비완료, 픽업/배송 완료

CREATE TABLE chatbot.orders (
    id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id INT NOT NULL REFERENCES chatbot.users(id),
    shop_id INT NOT NULL REFERENCES chatbot.shops(id),
    menu_id INT NOT NULL REFERENCES chatbot.menus(id),

    order_status order_stat,   
    order_time TIMESTAMP WITH TIME ZONE, -- 쿠폰 사용 시간 동일
    quantity INT,  
    price INT,  
    discount_applied INT
);
CREATE INDEX idx_orders_userid ON chatbot.orders(user_id);


-- 주문 없이 쿠폰 사용이 기록되는 걸 방지
CREATE TABLE chatbot.orders_coupons (
    order_id INT NOT NULL REFERENCES chatbot.orders(id) ON DELETE CASCADE,
    user_wallet_id INT NOT NULL REFERENCES chatbot.user_wallet(id) ON DELETE CASCADE,
    applied_discount INT NOT NULL,  -- 실제 적용된 할인 금액
    PRIMARY KEY (order_id, user_wallet_id)
);

CREATE TABLE chatbot.reviews (
    id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id INT NOT NULL REFERENCES chatbot.users(id),
    shop_id INT NOT NULL REFERENCES chatbot.shops(id) ON DELETE CASCADE,
    order_id INT NOT NULL REFERENCES chatbot.orders(id) ON DELETE CASCADE,
    
    rating DECIMAL(2,1) NOT NULL,
    comment TEXT, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,   
    
    /*derived*/
    sentiment VARCHAR(20), 
    quality_score DECIMAL(3,2), 
    helpful_count INT DEFAULT 0,
    
    -- 주문:리뷰 1:1
    CONSTRAINT unique_user_order_review UNIQUE (user_id, order_id)
);
CREATE INDEX idx_reviews_order_rating ON chatbot.reviews(order_id, rating);
CREATE INDEX idx_reviews_user ON chatbot.reviews(user_id);


-- FIXED: session_id UNIQUE 제약 제거하고 파티션 키를 PRIMARY KEY에 포함
CREATE TABLE chatbot.conversations (
    id BIGINT GENERATED ALWAYS AS IDENTITY,
    session_id UUID NOT NULL DEFAULT uuid_generate_v4(),  -- UNIQUE 제거
    user_id INT REFERENCES chatbot.users(id) ON DELETE CASCADE,
    conversation_time TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id, conversation_time),  -- 파티션 키 포함

    input_text VARCHAR(1000) NOT NULL, -- input token: 312
    response_text VARCHAR(700) NOT NULL, --response token: 200
	
    -- NLU 추출 정보
    extracted_intent VARCHAR(50) CHECK (extracted_intent IN (
        'FOOD_REQUEST', 'BUDGET_INQUIRY', 'COUPON_INQUIRY', 
        'LOCATION_INQUIRY', 'TIME_INQUIRY', 'GENERAL_CHAT',
        'MENU_OPTION', 'EMERGENCY_FOOD', 'GROUP_DINING', 
        'BALANCE_CHECK', 'BALANCE_CHARGE', 'UNKNOWN'
    )),  -- [AI_COMPUTED] NLU가 추출한 의도,
    intent_confidence DECIMAL(4,3) CHECK (intent_confidence >= 0 AND intent_confidence <= 1),  -- [AI_COMPUTED] 의도 신뢰도
    emotion INT,  -- 감정별 카테고리 매핑 (약 6종류)
    -- 추출된 엔티티
    extracted_entities JSONB,   -- {food_type: "치킨", budget: 10000, location: "근처" ,...}
    
    -- 대화 컨텍스트
    conversation_turn INT NOT NULL DEFAULT 1,  -- [SYSTEM] 대화 턴 번호
    previous_intent VARCHAR(50), 
    user_strategy VARCHAR(20) CHECK (user_strategy IN ('onboarding_mode', 'data_building_mode', 'normal_mode', 'urgent_mode')),

    -- 성능 메트릭
    processing_time_ms INT,  -- [SYSTEM] 전체 처리 시간
    nlu_time_ms INT,        -- [SYSTEM] NLU 처리 시간
    rag_time_ms INT,        -- [SYSTEM] RAG 검색 시간
    response_time_ms INT,   -- [SYSTEM] 응답 생성 시간

    -- 품질 지표
    response_quality_score DECIMAL(4,3),      -- [AI_COMPUTED] 응답 품질
    user_satisfaction_inferred DECIMAL(4,3),  -- [AI_COMPUTED] 추론된 만족도
    conversation_coherence DECIMAL(4,3),      -- [AI_COMPUTED] 대화 일관성
    
    -- 추천 결과
    recommended_shop_ids INT[],           -- [CHATBOT_GENERATED] 추천된 가게 ID 리스트
    selected_shop_id INT REFERENCES chatbot.shops(id),  -- [USER_ACTION] 사용자가 선택한 가게
    applied_coupon_ids TEXT[],             -- [CHATBOT_GENERATED] 적용된 쿠폰 ID
    
    -- session_id에 대한 UNIQUE 제약을 별도로 추가
    CONSTRAINT unique_session_id UNIQUE (session_id, conversation_time)
) PARTITION BY RANGE (conversation_time);

CREATE INDEX idx_conversations_user_time ON chatbot.conversations(user_id, conversation_time DESC);
CREATE INDEX idx_conversations_session ON chatbot.conversations(session_id);
CREATE INDEX idx_conversations_intent ON chatbot.conversations(extracted_intent);

-- 파티션 테이블 생성 (2024년 8월~12월, 2025년 1월~3월)
CREATE TABLE chatbot.conversations_2024_08 PARTITION OF chatbot.conversations
  FOR VALUES FROM ('2024-08-01') TO ('2024-09-01');
CREATE TABLE chatbot.conversations_2024_09 PARTITION OF chatbot.conversations
  FOR VALUES FROM ('2024-09-01') TO ('2024-10-01');
CREATE TABLE chatbot.conversations_2024_10 PARTITION OF chatbot.conversations
  FOR VALUES FROM ('2024-10-01') TO ('2024-11-01');
CREATE TABLE chatbot.conversations_2024_11 PARTITION OF chatbot.conversations
  FOR VALUES FROM ('2024-11-01') TO ('2024-12-01');
CREATE TABLE chatbot.conversations_2024_12 PARTITION OF chatbot.conversations
  FOR VALUES FROM ('2024-12-01') TO ('2025-01-01');
CREATE TABLE chatbot.conversations_2025_01 PARTITION OF chatbot.conversations
  FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');
CREATE TABLE chatbot.conversations_2025_02 PARTITION OF chatbot.conversations
  FOR VALUES FROM ('2025-02-01') TO ('2025-03-01');
CREATE TABLE chatbot.conversations_2025_03 PARTITION OF chatbot.conversations
  FOR VALUES FROM ('2025-03-01') TO ('2025-04-01');

CREATE MATERIALIZED VIEW chatbot.recent_conversations AS
SELECT *
FROM chatbot.conversations
WHERE conversation_time > CURRENT_TIMESTAMP - INTERVAL '7 days';
CREATE INDEX idx_recent_conversations_time ON chatbot.recent_conversations(conversation_time);

CREATE OR REPLACE FUNCTION auto_delete_old_conversations()
RETURNS void AS $$
BEGIN
    DELETE FROM chatbot.conversations
    WHERE conversation_time < NOW() - INTERVAL '6 months';
END;
$$ LANGUAGE plpgsql;

CREATE TABLE ml_features.nlu_features (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- NLU 핵심 결과
    nlu_intent VARCHAR(50),  -- food_request, budget_inquiry 등
    nlu_confidence DECIMAL(4,3),
    
    -- 추출된 특징들
    food_category_mentioned VARCHAR(100),        -- "치킨", "한식", "일식" 등
    budget_mentioned INT,                        -- 예산 금액
    location_mentioned VARCHAR(100),             -- "근처", "강남" 등
    companions_mentioned JSON,                   -- ["친구", "가족"] 등
    time_preference VARCHAR(50),                 -- "지금", "저녁" 등
    menu_options JSON,                           -- ["맵게", "곱배기"] 등
    special_requirements JSON,                   -- 특별 요구사항
    
    -- 처리 메타데이터
    processing_time_ms INT,
    model_version VARCHAR(20)
);

CREATE INDEX idx_user_timestamp ON ml_features.nlu_features(user_id, created_at);
CREATE INDEX idx_intent ON ml_features.nlu_features(nlu_intent);
CREATE INDEX idx_food_category ON ml_features.nlu_features(food_category_mentioned);

CREATE TYPE interaction AS ENUM ('text_input', 'selection', 'feedback', 'coupon_use');
CREATE TABLE ml_features.user_interactions (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id INT NOT NULL REFERENCES chatbot.users(id),
    session_id UUID,  -- 외래키 제약 제거 (파티션 테이블이라 직접 참조 불가)
    time_stamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- [CHATBOT_GENERATED] 상호작용 세부사항
    interaction_type interaction,
    
    -- [CHATBOT_GENERATED] 학습 데이터 추출 결과
    food_preference_extracted VARCHAR(100),      
    budget_pattern_extracted INT, 
    companion_pattern_extracted JSON, 
    location_preference_extracted VARCHAR(100), 
    
    -- [DERIVED] 추천 관련 데이터 (shops 테이블과 연결)
    recommendation_provided BOOLEAN DEFAULT FALSE,
    recommendation_count INT DEFAULT 0,
    recommendations JSONB,                        -- 추천된 shop_id들과 점수
    
    -- [CHATBOT_GENERATED] 사용자 상태
    user_strategy VARCHAR(30),
    conversation_turn INT
);
CREATE INDEX idx_interaction_timestamp ON ml_features.user_interactions(user_id, time_stamp);
CREATE INDEX idx_session ON ml_features.user_interactions(session_id);

CREATE TABLE analytics.recommendations_log (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id INT NOT NULL, 
    shop_id INT NOT NULL REFERENCES chatbot.shops(id),
    session_id UUID,  -- 외래키 제약 제거
    time_stamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- 추천 입력 조건
    request_food_type VARCHAR(100),              -- NLU에서 추출한 음식 종류
    request_budget INT,                          -- NLU에서 추출한 예산
    request_location VARCHAR(100),               -- NLU에서 추출한 위치 선호
    
    -- [DERIVED] 추천 결과 (shops 테이블의 shop_id 참조)
    recommendations JSONB NOT NULL,               -- [{shop_id, score, reason}] 배열
    recommendation_count INT NOT NULL,
    top_recommendation_shop_id INT,              -- shops.id 참조
    
    -- 사용자 선택 (나중에 업데이트)
    user_selection JSON,                         -- 사용자가 선택한 가게 정보
    selection_timestamp TIMESTAMP NULL,
    
    -- 추천 시스템 메타데이터
    recommendation_method VARCHAR(50),           -- "wide_deep", "rag", "hybrid"
    confidence_score DECIMAL(4,3),
    wide_score DECIMAL(4,3),                    -- Wide 모델 점수
    deep_score DECIMAL(4,3),                    -- Deep 모델 점수
    rag_score DECIMAL(4,3)                     -- RAG 검색 점수
);

CREATE INDEX idx_recommendation_timestamp ON analytics.recommendations_log(user_id, time_stamp);
CREATE INDEX idx_session_rmd ON analytics.recommendations_log(session_id);
CREATE INDEX idx_shop_rmd ON analytics.recommendations_log(top_recommendation_shop_id);


CREATE TABLE analytics.user_feedback (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,    
    session_id UUID,  -- 외래키 제약 제거
    related_recommendation_id BIGINT REFERENCES analytics.recommendations_log(id),
    user_id INT NOT NULL REFERENCES chatbot.users(id),  
    time_stamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- 피드백 기본 정보
    feedback_type VARCHAR(30) NOT NULL,          -- "selection", "rating", "text", "implicit"
    feedback_target_type VARCHAR(30) NOT NULL,
    feedback_target_id VARCHAR(30) NOT NULL,         
    feedback_content JSONB,                       -- 피드백 내용 (점수, 텍스트, 선택 등)
    context JSONB                                -- 피드백이 발생한 상황 정보
    -- 마지막 컬럼에 쉼표 제거

    -- [DERIVED] 피드백 분석 결과 (별도 컬럼 추가 가능)
    -- sentiment VARCHAR(20),                       -- "positive", "negative", "neutral"
    -- satisfaction_score DECIMAL(3,2),            -- 0.00 ~ 1.00
    -- feedback_quality DECIMAL(3,2)              -- 피드백 품질 점수
);
CREATE INDEX idx_user_timestamp ON analytics.user_feedback(user_id, time_stamp);
CREATE INDEX idx_feedback_type ON analytics.user_feedback(feedback_type);
CREATE INDEX idx_recommendation ON analytics.user_feedback(related_recommendation_id);