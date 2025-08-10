-- ===============================================
-- YUMAI 데이터베이스 최종 스키마 (Session Master 포함)
-- 버전: 2.0
-- 작성일: 2025-08-07
-- 주요 변경: Session Master 테이블 도입으로 참조 무결성 완벽 보장
-- ===============================================

-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "btree_gin"; 
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Schemas
CREATE SCHEMA IF NOT EXISTS analytics;
CREATE SCHEMA IF NOT EXISTS ml_features;
CREATE SCHEMA IF NOT EXISTS chatbot;

-- ===============================================
-- 핵심: Session Master 테이블 (NEW!)
-- 모든 세션의 중앙 관리 테이블
-- ===============================================
CREATE TABLE chatbot.session_master (
    session_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id INT REFERENCES chatbot.users(id) ON DELETE CASCADE,
    session_start TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    session_end TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT TRUE,
    session_type VARCHAR(50) DEFAULT 'chat' CHECK (session_type IN (
        'chat', 'voice', 'api', 'test', 'admin'
    )),
    session_metadata JSONB DEFAULT '{}'::jsonb,  -- 추가 세션 정보
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Session Master 인덱스
CREATE INDEX idx_session_master_user ON chatbot.session_master(user_id);
CREATE INDEX idx_session_master_active ON chatbot.session_master(is_active) WHERE is_active = TRUE;
CREATE INDEX idx_session_master_start ON chatbot.session_master(session_start DESC);
CREATE INDEX idx_session_master_type ON chatbot.session_master(session_type);

-- Session Master 트리거
CREATE TRIGGER update_session_master_updated_at BEFORE UPDATE ON chatbot.session_master
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ===============================================
-- 기본 테이블들
-- ===============================================

CREATE TABLE chatbot.shops (
    id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    shop_name VARCHAR(30) NOT NULL,
    category VARCHAR(20) NOT NULL CHECK (category IN (
        '한식', '중식', '일식', '양식', '치킨', '피자', '패스트푸드',
        '분식', '카페/디저트', '도시락/죽', '프랜차이즈', '기타음식', '편의점'
    )),
    address_name VARCHAR(50),
    latitude DECIMAL(8, 6) NOT NULL,
    longitude DECIMAL(9, 6) NOT NULL,
    is_good_influence_shop BOOLEAN DEFAULT FALSE,
    is_food_card_shop CHAR(1) NOT NULL DEFAULT 'U' CHECK (is_food_card_shop IN ('Y', 'N', 'P', 'U')),
    contact VARCHAR(20), 
    business_hours JSONB,
    current_status VARCHAR(20) NOT NULL DEFAULT 'UNKNOWN' 
        CHECK (current_status IN ('OPEN', 'CLOSED', 'BREAK_TIME', 'UNKNOWN')),
    popularity_score DECIMAL(4,3) DEFAULT 0.000 CHECK (popularity_score >= 0 AND popularity_score <= 1),  
    quality_score DECIMAL(4,3) DEFAULT 0.000 CHECK (quality_score >= 0 AND quality_score <= 1),        
    recommendation_count INT DEFAULT 0 CHECK (recommendation_count >= 0),  
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,  
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP, 
    data_from VARCHAR(50) DEFAULT 'manual',
    
    CONSTRAINT shops_location_check CHECK (
        latitude >= -90 AND latitude <= 90 AND
        longitude >= -180 AND longitude <= 180
    )
);

CREATE INDEX idx_shops_category ON chatbot.shops(category);
CREATE INDEX idx_shops_good_influence ON chatbot.shops(is_good_influence_shop) WHERE is_good_influence_shop = TRUE;
CREATE INDEX idx_shops_food_card ON chatbot.shops(is_food_card_shop) WHERE is_food_card_shop != 'N';
CREATE INDEX idx_shops_location ON chatbot.shops(latitude, longitude);
CREATE INDEX idx_shops_popularity ON chatbot.shops(popularity_score DESC);
CREATE INDEX idx_shops_status ON chatbot.shops(current_status) WHERE current_status = 'OPEN';
CREATE INDEX idx_shops_name_gin ON chatbot.shops USING gin(shop_name gin_trgm_ops);

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
    options JSONB,
    is_available BOOLEAN NOT NULL DEFAULT TRUE,
    is_best BOOLEAN DEFAULT FALSE,
    dietary_info VARCHAR(200),
    recommendation_frequency INT DEFAULT 0 CHECK (recommendation_frequency >= 0),
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
    preferred_location VARCHAR(50),
    user_status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE' CHECK (user_status IN (
        'ACTIVE', 'INACTIVE', 'SUSPENDED', 'DELETED'
    )),
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
    balance INT NOT NULL DEFAULT 0 CHECK (balance >= 0),
    target_age_group VARCHAR(20) NOT NULL CHECK (target_age_group IN (
        '초등학생', '중학생', '고등학생', '대학생', '청년', '기타'
    )),
    balance_alert_threshold INT DEFAULT 5000,
    balance_alert_sent BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_sync_at TIMESTAMP WITH TIME ZONE, 
    CONSTRAINT foodcard_users_unique_user UNIQUE (user_id)
);

CREATE INDEX idx_foodcard_status ON chatbot.foodcard_users(card_status) WHERE card_status = 'ACTIVE';
CREATE INDEX idx_foodcard_balance ON chatbot.foodcard_users(balance) WHERE balance < 5000;

CREATE TRIGGER update_foodcard_users_updated_at BEFORE UPDATE ON chatbot.foodcard_users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TABLE chatbot.user_profiles (
    id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id INT NOT NULL REFERENCES chatbot.users(id) ON DELETE CASCADE,
    preferred_categories TEXT[] DEFAULT '{}',
    average_budget INT,
    favorite_shops INT[] DEFAULT '{}',
    conversation_style VARCHAR(20) DEFAULT 'friendly' CHECK (conversation_style IN (
        'friendly', 'formal', 'casual', 'brief'
    )),           
    taste_preferences JSONB DEFAULT '{}',
    companion_patterns TEXT[] DEFAULT '{}',
    location_preferences TEXT[] DEFAULT '{}',
    good_influence_preference DECIMAL(3,2) DEFAULT 0.50 CHECK (
        good_influence_preference >= 0 AND good_influence_preference <= 1
    ),
    interaction_count INT DEFAULT 0,
    data_completeness DECIMAL(3,2) DEFAULT 0.00 CHECK (
        data_completeness >= 0 AND data_completeness <= 1
    ),
    recent_orders JSONB DEFAULT '[]', 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
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
    coupon_name VARCHAR(50) NOT NULL,
    coupon_code VARCHAR(50) NOT NULL,
    coupon_description TEXT,
    coupon_type VARCHAR(30) NOT NULL CHECK (coupon_type IN (
        'FIXED_AMOUNT', 'PERCENTAGE', 'FREEBIE', 'BOGO'
    )),
    discount_amount INT CHECK (discount_amount > 0),
    discount_rate DECIMAL(3,2) CHECK (discount_rate > 0 AND discount_rate <= 1),    
    max_discount_amount INT,
    min_order_amount INT DEFAULT 0,
    usage_type VARCHAR(30) NOT NULL CHECK (usage_type IN (
        'ALL', 'SHOP', 'CATEGORY', 'FOODCARD', 'NEW_USER', 'LOYALTY'
    )),
    target_categories TEXT[],
    applicable_shop_ids INT[],
    target_user_types TEXT[],
    valid_from DATE NOT NULL DEFAULT CURRENT_DATE,
    valid_until DATE NOT NULL,
    max_issue_count INT,
    max_use_per_user INT DEFAULT 1,
    total_issued INT DEFAULT 0,
    total_used INT DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    priority_score DECIMAL(3,2) DEFAULT 0.50 CHECK (priority_score >= 0 AND priority_score <= 1),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100),
    
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
    coupon_status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE' CHECK (coupon_status IN (
        'ACTIVE', 'USED', 'EXPIRED', 'CANCELLED'
    )),
    issued_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    issued_by VARCHAR(100) DEFAULT 'SYSTEM',
    acquisition_source VARCHAR(50) NOT NULL CHECK (acquisition_source IN (
        'WELCOME_BONUS', 'LOYALTY_REWARD', 'EMERGENCY_ASSIST', 
        'PROMOTION', 'ADMIN_GRANT', 'REFERRAL'
    )),
    acquisition_context JSONB,
    expires_at TIMESTAMP WITH TIME ZONE,
    expiry_notified_at TIMESTAMP WITH TIME ZONE,
    expiry_notification_count INT DEFAULT 0,
    usage_probability DECIMAL(4,3) DEFAULT 0.500 CHECK (usage_probability >= 0 AND usage_probability <= 1),
    recommended_usage_date DATE,
    
    CONSTRAINT user_coupon_unique_active UNIQUE (user_id, coupon_id, coupon_status) 
        DEFERRABLE INITIALLY DEFERRED
);

CREATE INDEX idx_user_coupon_user_status ON chatbot.user_wallet(user_id, coupon_status);
CREATE INDEX idx_user_coupon_expires ON chatbot.user_wallet(expires_at) WHERE coupon_status = 'ACTIVE';
CREATE INDEX idx_user_coupon_usage_prob ON chatbot.user_wallet(usage_probability DESC) WHERE coupon_status = 'ACTIVE';

CREATE TYPE order_stat AS ENUM ('confirmed', 'preparing', 'prepared', 'picked', 'canceled');

CREATE TABLE chatbot.orders (
    id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id INT NOT NULL REFERENCES chatbot.users(id),
    shop_id INT NOT NULL REFERENCES chatbot.shops(id),
    menu_id INT NOT NULL REFERENCES chatbot.menus(id),
    order_status order_stat,   
    order_time TIMESTAMP WITH TIME ZONE,
    quantity INT,  
    price INT,  
    discount_applied INT
);
CREATE INDEX idx_orders_userid ON chatbot.orders(user_id);

CREATE TABLE chatbot.orders_coupons (
    order_id INT NOT NULL REFERENCES chatbot.orders(id) ON DELETE CASCADE,
    user_wallet_id INT NOT NULL REFERENCES chatbot.user_wallet(id) ON DELETE CASCADE,
    applied_discount INT NOT NULL,
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
    sentiment VARCHAR(20), 
    quality_score DECIMAL(3,2), 
    helpful_count INT DEFAULT 0,
    CONSTRAINT unique_user_order_review UNIQUE (user_id, order_id)
);
CREATE INDEX idx_reviews_order_rating ON chatbot.reviews(order_id, rating);
CREATE INDEX idx_reviews_user ON chatbot.reviews(user_id);

-- ===============================================
-- Conversations 테이블 (Session Master 참조!)
-- ===============================================
CREATE TABLE chatbot.conversations (
    id BIGINT GENERATED ALWAYS AS IDENTITY,
    session_id UUID NOT NULL REFERENCES chatbot.session_master(session_id) ON DELETE CASCADE,  -- Session Master 참조!
    user_id INT REFERENCES chatbot.users(id) ON DELETE CASCADE,
    conversation_time TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id, conversation_time),

    input_text VARCHAR(1000) NOT NULL,
    response_text VARCHAR(700) NOT NULL,
	
    extracted_intent VARCHAR(50) CHECK (extracted_intent IN (
        'FOOD_REQUEST', 'BUDGET_INQUIRY', 'COUPON_INQUIRY', 
        'LOCATION_INQUIRY', 'TIME_INQUIRY', 'GENERAL_CHAT',
        'MENU_OPTION', 'EMERGENCY_FOOD', 'GROUP_DINING', 
        'BALANCE_CHECK', 'BALANCE_CHARGE', 'UNKNOWN'
    )),
    intent_confidence DECIMAL(4,3) CHECK (intent_confidence >= 0 AND intent_confidence <= 1),
    emotion INT,
    extracted_entities JSONB,
    
    conversation_turn INT NOT NULL DEFAULT 1,
    previous_intent VARCHAR(50), 
    user_strategy VARCHAR(20) CHECK (user_strategy IN ('onboarding_mode', 'data_building_mode', 'normal_mode', 'urgent_mode')),

    processing_time_ms INT,
    nlu_time_ms INT,
    rag_time_ms INT,
    response_time_ms INT,

    response_quality_score DECIMAL(4,3),
    user_satisfaction_inferred DECIMAL(4,3),
    conversation_coherence DECIMAL(4,3),
    
    recommended_shop_ids INT[],
    selected_shop_id INT REFERENCES chatbot.shops(id),
    applied_coupon_ids TEXT[]
) PARTITION BY RANGE (conversation_time);

CREATE INDEX idx_conversations_user_time ON chatbot.conversations(user_id, conversation_time DESC);
CREATE INDEX idx_conversations_session ON chatbot.conversations(session_id);
CREATE INDEX idx_conversations_intent ON chatbot.conversations(extracted_intent);

-- 파티션 테이블 생성
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

-- ===============================================
-- ML Features 테이블들 (Session Master 참조!)
-- ===============================================
CREATE TABLE ml_features.nlu_features (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    nlu_intent VARCHAR(50),
    nlu_confidence DECIMAL(4,3),
    food_category_mentioned VARCHAR(100),
    budget_mentioned INT,
    location_mentioned VARCHAR(100),
    companions_mentioned JSON,
    time_preference VARCHAR(50),
    menu_options JSON,
    special_requirements JSON,
    processing_time_ms INT,
    model_version VARCHAR(20)
);

CREATE INDEX idx_user_timestamp ON ml_features.nlu_features(user_id, created_at);
CREATE INDEX idx_intent ON ml_features.nlu_features(nlu_intent);
CREATE INDEX idx_food_category ON ml_features.nlu_features(food_category_mentioned);

CREATE TYPE interaction AS ENUM ('text_input', 'selection', 'feedback', 'coupon_use');
CREATE TABLE ml_features.user_interactions (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id INT NOT NULL REFERENCES chatbot.users(id) ON DELETE CASCADE,
    session_id UUID NOT NULL REFERENCES chatbot.session_master(session_id) ON DELETE CASCADE,  -- Session Master 참조!
    time_stamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    interaction_type interaction,
    food_preference_extracted VARCHAR(100),      
    budget_pattern_extracted INT, 
    companion_pattern_extracted JSON, 
    location_preference_extracted VARCHAR(100), 
    recommendation_provided BOOLEAN DEFAULT FALSE,
    recommendation_count INT DEFAULT 0,
    recommendations JSONB,
    user_strategy VARCHAR(30),
    conversation_turn INT
);
CREATE INDEX idx_interaction_timestamp ON ml_features.user_interactions(user_id, time_stamp);
CREATE INDEX idx_session ON ml_features.user_interactions(session_id);

-- ===============================================
-- Analytics 테이블들 (Session Master 참조!)
-- ===============================================
CREATE TABLE analytics.recommendations_log (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id INT NOT NULL, 
    shop_id INT NOT NULL REFERENCES chatbot.shops(id),
    session_id UUID NOT NULL REFERENCES chatbot.session_master(session_id) ON DELETE CASCADE,  -- Session Master 참조!
    time_stamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    request_food_type VARCHAR(100),
    request_budget INT,
    request_location VARCHAR(100),
    recommendations JSONB NOT NULL,
    recommendation_count INT NOT NULL,
    top_recommendation_shop_id INT,
    user_selection JSON,
    selection_timestamp TIMESTAMP NULL,
    recommendation_method VARCHAR(50),
    confidence_score DECIMAL(4,3),
    wide_score DECIMAL(4,3),
    deep_score DECIMAL(4,3),
    rag_score DECIMAL(4,3)
);

CREATE INDEX idx_recommendation_timestamp ON analytics.recommendations_log(user_id, time_stamp);
CREATE INDEX idx_session_rmd ON analytics.recommendations_log(session_id);
CREATE INDEX idx_shop_rmd ON analytics.recommendations_log(top_recommendation_shop_id);

CREATE TABLE analytics.user_feedback (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,    
    session_id UUID NOT NULL REFERENCES chatbot.session_master(session_id) ON DELETE CASCADE,  -- Session Master 참조!
    related_recommendation_id BIGINT REFERENCES analytics.recommendations_log(id),
    user_id INT NOT NULL REFERENCES chatbot.users(id),  
    time_stamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    feedback_type VARCHAR(30) NOT NULL,
    feedback_target_type VARCHAR(30) NOT NULL,
    feedback_target_id VARCHAR(30) NOT NULL,         
    feedback_content JSONB,
    context JSONB
);
CREATE INDEX idx_user_timestamp ON analytics.user_feedback(user_id, time_stamp);
CREATE INDEX idx_feedback_type ON analytics.user_feedback(feedback_type);
CREATE INDEX idx_recommendation ON analytics.user_feedback(related_recommendation_id);

-- ===============================================
-- Session 관리 함수들 (NEW!)
-- ===============================================

-- 세션 시작 함수
CREATE OR REPLACE FUNCTION start_session(
    p_user_id INT,
    p_session_type VARCHAR(50) DEFAULT 'chat',
    p_metadata JSONB DEFAULT '{}'::jsonb
)
RETURNS UUID AS $$
DECLARE
    v_session_id UUID;
BEGIN
    INSERT INTO chatbot.session_master (user_id, session_type, session_metadata)
    VALUES (p_user_id, p_session_type, p_metadata)
    RETURNING session_id INTO v_session_id;
    
    RETURN v_session_id;
END;
$$ LANGUAGE plpgsql;

-- 세션 종료 함수
CREATE OR REPLACE FUNCTION end_session(p_session_id UUID)
RETURNS BOOLEAN AS $$
BEGIN
    UPDATE chatbot.session_master
    SET session_end = CURRENT_TIMESTAMP,
        is_active = FALSE
    WHERE session_id = p_session_id
    AND is_active = TRUE;
    
    RETURN FOUND;
END;
$$ LANGUAGE plpgsql;

-- 비활성 세션 정리 함수
CREATE OR REPLACE FUNCTION clean_inactive_sessions()
RETURNS INTEGER AS $$
DECLARE
    v_count INTEGER;
BEGIN
    WITH updated AS (
        UPDATE chatbot.session_master sm
        SET is_active = FALSE, 
            session_end = CURRENT_TIMESTAMP
        WHERE is_active = TRUE
        AND NOT EXISTS (
            SELECT 1 FROM chatbot.conversations c
            WHERE c.session_id = sm.session_id
            AND c.conversation_time > CURRENT_TIMESTAMP - INTERVAL '24 hours'
        )
        RETURNING 1
    )
    SELECT COUNT(*) INTO v_count FROM updated;
    
    RETURN v_count;
END;
$$ LANGUAGE plpgsql;

-- 오래된 세션 삭제 함수
CREATE OR REPLACE FUNCTION delete_old_sessions(p_days INTEGER DEFAULT 30)
RETURNS INTEGER AS $$
DECLARE
    v_count INTEGER;
BEGIN
    WITH deleted AS (
        DELETE FROM chatbot.session_master
        WHERE session_end < CURRENT_TIMESTAMP - (p_days || ' days')::INTERVAL
        AND is_active = FALSE
        RETURNING 1
    )
    SELECT COUNT(*) INTO v_count FROM deleted;
    
    RETURN v_count;
END;
$$ LANGUAGE plpgsql;