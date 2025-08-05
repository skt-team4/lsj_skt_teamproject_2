# 나비얌 챗봇 데이터베이스 구현 가이드

## 목차
1. [데이터베이스 초기 설정](#1-데이터베이스-초기-설정)
2. [데이터 저장 정책](#2-데이터-저장-정책)
3. [핵심 테이블 DDL](#3-핵심-테이블-ddl)
4. [데이터 타입 상세 명세](#4-데이터-타입-상세-명세)
5. [시스템 플로우 문서](#5-시스템-플로우-문서)
6. [API 엔드포인트 및 데이터 흐름](#6-api-엔드포인트-및-데이터-흐름)
7. [데이터 마이그레이션 가이드](#7-데이터-마이그레이션-가이드)

---

## 1. 데이터베이스 초기 설정

### PostgreSQL 설정
```sql
-- 데이터베이스 생성
CREATE DATABASE naviyam_chatbot
    WITH 
    OWNER = postgres
    ENCODING = 'UTF8'
    LC_COLLATE = 'ko_KR.UTF-8'
    LC_CTYPE = 'ko_KR.UTF-8'
    TABLESPACE = pg_default
    CONNECTION LIMIT = -1;

-- 확장 기능 활성화
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";      -- UUID 생성
CREATE EXTENSION IF NOT EXISTS "pg_trgm";        -- 텍스트 유사도 검색
CREATE EXTENSION IF NOT EXISTS "btree_gin";      -- GIN 인덱스 성능 향상
CREATE EXTENSION IF NOT EXISTS "pgcrypto";       -- 암호화 기능

-- 스키마 생성
CREATE SCHEMA IF NOT EXISTS chatbot;
CREATE SCHEMA IF NOT EXISTS analytics;
CREATE SCHEMA IF NOT EXISTS ml_features;

-- 기본 스키마 설정
SET search_path TO chatbot, public;
```

### 사용자 권한 설정
```sql
-- 읽기 전용 사용자
CREATE USER data_analyst WITH PASSWORD 'secure_password';
GRANT CONNECT ON DATABASE naviyam_chatbot TO data_analyst;
GRANT USAGE ON SCHEMA chatbot, analytics, ml_features TO data_analyst;
GRANT SELECT ON ALL TABLES IN SCHEMA chatbot, analytics, ml_features TO data_analyst;

-- 애플리케이션 사용자
CREATE USER app_user WITH PASSWORD 'secure_password';
GRANT CONNECT ON DATABASE naviyam_chatbot TO app_user;
GRANT USAGE ON SCHEMA chatbot TO app_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA chatbot TO app_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA chatbot TO app_user;

-- ML 사용자
CREATE USER ml_user WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON SCHEMA ml_features TO ml_user;
```

---

## 2. 데이터 저장 정책

### 2.1 챗봇이 생성하는 데이터 분류

#### 🗄️ DB에 반드시 저장하는 데이터

| 데이터 종류 | 저장 테이블 | 데이터 타입 | 저장 이유 |
|------------|------------|-----------|----------|
| **대화 기록** | conversations | input_text: TEXT<br>response_text: TEXT<br>timestamp: TIMESTAMP WITH TIME ZONE | 법적 요구사항, 학습 데이터, 감사 추적 |
| **NLU 결과** | conversations | extracted_intent: VARCHAR(50)<br>intent_confidence: DECIMAL(4,3)<br>extracted_entities: JSONB | 모델 개선, 정확도 추적 |
| **추천 결과** | recommendations_log | recommendations: JSONB<br>recommendation_method: VARCHAR(50)<br>confidence_score: DECIMAL(4,3) | A/B 테스트, 성능 평가 |
| **사용자 선택** | recommendations_log | user_final_selection: INTEGER<br>time_to_decision_ms: INTEGER | 선호도 학습, CTR 계산 |
| **사용자 프로필** | user_profiles | preferred_categories: JSONB<br>average_budget: INTEGER<br>personality_type: VARCHAR(50) | 장기 개인화 |
| **급식카드 잔액** | foodcard_users | balance: INTEGER<br>status: VARCHAR(20)<br>last_sync_at: TIMESTAMP | 예산 내 추천 |
| **성능 메트릭** | performance_logs | processing_time_ms: INTEGER<br>error_type: VARCHAR(100)<br>bottleneck_component: VARCHAR(50) | 성능 최적화 |
| **학습 데이터** | nlu_training_data | input_text: TEXT<br>predicted_intent: VARCHAR(50)<br>true_intent: VARCHAR(50) | 모델 재학습 |
| **세션 컨텍스트** | conversation_contexts | context_data: JSONB<br>user_state: JSONB<br>extracted_patterns: JSONB | 대화 연속성 |

#### 💾 메모리/캐시에만 저장하는 데이터

| 데이터 종류 | 저장 위치 | TTL | 저장하지 않는 이유 |
|------------|----------|-----|------------------|
| **현재 대화 상태** | Redis | 24시간 | 임시 데이터, 세션 종료 시 불필요 |
| **실시간 추천 점수** | 메모리 | 세션 동안 | 실시간 계산, 재현 가능 |
| **임시 NLU 결과** | 메모리 | 5분 | 단기 캐시, 최종 결과만 DB 저장 |
| **중간 계산 결과** | Redis | 1시간 | 재계산 가능, 저장 비용 높음 |
| **디버그 정보** | 로그 파일 | 7일 | 개발/디버깅용, 프로덕션 불필요 |
| **UI 상태 정보** | 클라이언트 | 세션 동안 | 프론트엔드 관련, 백엔드 불필요 |
| **임시 토큰** | 메모리 | 1시간 | 보안상 영구 저장 금지 |

#### ❌ 절대 저장하지 않는 데이터

| 데이터 종류 | 이유 | 대체 방안 |
|------------|------|----------|
| **비밀번호 평문** | 보안 위반 | bcrypt 해시만 저장 |
| **결제 카드 정보** | PCI DSS 규정 | 토큰화 또는 외부 서비스 |
| **민감 개인정보** | 개인정보보호법 | 암호화 또는 익명화 |
| **임시 계산값** | 저장 공간 낭비 | 필요시 재계산 |
| **외부 API 응답 전체** | 저작권/용량 문제 | 필요한 부분만 추출 |
| **모델 가중치** | 용량 문제 | S3/파일 시스템 |

### 2.2 데이터 타입 선택 기준

#### 텍스트 데이터
```sql
-- 짧은 고정 텍스트 (최대 길이 확실)
VARCHAR(n)  -- 예: user_id VARCHAR(100), intent VARCHAR(50)

-- 가변 길이 텍스트
TEXT        -- 예: input_text TEXT, response_text TEXT

-- JSON 구조화 데이터
JSONB       -- 예: extracted_entities JSONB, recommendations JSONB
```

#### 숫자 데이터
```sql
-- 정수 (ID, 카운트, 금액)
INTEGER     -- 예: shop_id INTEGER, price INTEGER (-2,147,483,648 ~ 2,147,483,647)
BIGINT      -- 예: id BIGINT (매우 큰 테이블용)

-- 소수 (비율, 점수)
DECIMAL(p,s) -- 예: confidence DECIMAL(4,3) → 0.000~1.000
             -- p: 전체 자릿수, s: 소수점 자릿수

-- 부동소수점 (과학계산, 정밀도 낮아도 됨)
REAL        -- 예: cpu_usage REAL
```

#### 시간 데이터
```sql
-- 날짜만
DATE        -- 예: birth_date DATE

-- 시간만  
TIME        -- 예: open_hour TIME

-- 날짜+시간+시간대
TIMESTAMP WITH TIME ZONE -- 예: created_at TIMESTAMP WITH TIME ZONE
```

#### 불린 데이터
```sql
BOOLEAN     -- 예: is_active BOOLEAN, is_verified BOOLEAN
```

#### 배열/리스트 데이터
```sql
TYPE[]      -- 예: target_categories TEXT[], shop_ids INTEGER[]
```

---

## 3. 핵심 테이블 DDL

### 3.1 가게 정보 테이블 (shops)
```sql
CREATE TABLE chatbot.shops (
    id SERIAL PRIMARY KEY,
    
    -- 기본 정보 (NOT NULL 필수 필드)
    shop_name VARCHAR(200) NOT NULL,  -- [SAMPLE_DATA] 가게명, Excel에서 가져옴
    category VARCHAR(100) NOT NULL CHECK (category IN (
        '한식', '중식', '일식', '양식', '치킨', '피자', '패스트푸드',
        '분식', '카페/디저트', '도시락/죽', '프랜차이즈', '기타음식', '편의점'
    )),  -- [SAMPLE_DATA] 13개 고정 카테고리
    
    -- 주소 정보
    address_name TEXT NOT NULL,  -- [SAMPLE_DATA] 지번 주소
    road_address_name TEXT,      -- [CRAWLED] 도로명 주소
    
    -- 착한가게/급식카드 정보
    is_good_influence_shop BOOLEAN NOT NULL DEFAULT FALSE,  -- [SAMPLE_DATA] 착한가게 여부
    is_food_card_shop CHAR(1) NOT NULL DEFAULT 'U' CHECK (is_food_card_shop IN ('Y', 'N', 'P', 'U')),
    -- Y: 사용가능, N: 사용불가, P: 부분사용가능, U: 미확인
    -- [SAMPLE_DATA + VERIFIED] 급식카드 사용 가능 여부
    
    -- 영업시간 (NULL 허용 - 정보 없을 수 있음)
    business_hours JSONB,  -- [CRAWLED/MANUAL] 영업시간 정보
    /* 예시:
    {
      "monday": {"open": "09:00", "close": "22:00", "break_start": "15:00", "break_end": "17:00"},
      "tuesday": {"open": "09:00", "close": "22:00"},
      "wednesday": {"open": "09:00", "close": "22:00"},
      "thursday": {"open": "09:00", "close": "22:00"},
      "friday": {"open": "09:00", "close": "23:00"},
      "saturday": {"open": "11:00", "close": "23:00"},
      "sunday": {"open": "11:00", "close": "22:00"},
      "holiday": {"closed": true}
    }
    */
    
    -- 연락처 정보
    phone VARCHAR(20),        -- [SAMPLE_DATA/CRAWLED] 전화번호
    owner_message TEXT,       -- [SAMPLE_DATA] 사장님 메시지
    
    -- 위치 정보 (소수점 8자리 정밀도 = 약 1.1mm)
    latitude DECIMAL(10, 8) NOT NULL,   -- [SAMPLE_DATA] 위도
    longitude DECIMAL(11, 8) NOT NULL,  -- [SAMPLE_DATA] 경도
    
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
    
    recommendation_count INTEGER DEFAULT 0 CHECK (recommendation_count >= 0),  
    -- [CHATBOT_GENERATED] 추천 횟수 - 실시간 업데이트
    
    -- 필수 메타데이터
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,  -- [SYSTEM] 생성 시간 (필수)
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,  -- [SYSTEM] 수정 시간 (필수)
    data_source VARCHAR(50) DEFAULT 'manual', -- [SYSTEM] 데이터 출처: 'manual', 'crawled', 'api', 'user_generated'
    
    -- 인덱스 정의는 테이블 생성 후
    CONSTRAINT shops_location_check CHECK (
        latitude >= -90 AND latitude <= 90 AND
        longitude >= -180 AND longitude <= 180
    )
);

-- 인덱스 생성
CREATE INDEX idx_shops_category ON chatbot.shops(category);  -- 카테고리별 필터링
CREATE INDEX idx_shops_good_influence ON chatbot.shops(is_good_influence_shop) WHERE is_good_influence_shop = TRUE;  -- 착한가게만
CREATE INDEX idx_shops_food_card ON chatbot.shops(is_food_card_shop) WHERE is_food_card_shop != 'N';  -- 급식카드 가능
CREATE INDEX idx_shops_location ON chatbot.shops(latitude, longitude);  -- 거리 기반 검색용
CREATE INDEX idx_shops_popularity ON chatbot.shops(popularity_score DESC);  -- 인기순 정렬
CREATE INDEX idx_shops_status ON chatbot.shops(current_status) WHERE current_status = 'OPEN';  -- 영업중인 가게만

-- GIN 인덱스 (사용 예정)
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
```

### 3.2 메뉴 정보 테이블 (menus)
```sql
CREATE TABLE chatbot.menus (
    id SERIAL PRIMARY KEY,
    shop_id INTEGER NOT NULL REFERENCES chatbot.shops(id) ON DELETE CASCADE,
    
    -- 메뉴 기본 정보
    menu_name VARCHAR(200) NOT NULL,     -- [SAMPLE_DATA/CRAWLED] 메뉴명
    price INTEGER NOT NULL CHECK (price >= 0),  -- [SAMPLE_DATA/CRAWLED] 가격 (원)
    description TEXT,                    -- [CRAWLED/MANUAL] 메뉴 설명
    category VARCHAR(100) CHECK (category IN (
        '메인메뉴', '세트메뉴', '사이드메뉴', '음료', '디저트', '기타'
    )),  -- [MANUAL] 메뉴 카테고리
    
    -- 메뉴 상태
    is_available BOOLEAN NOT NULL DEFAULT TRUE,   -- [SYSTEM] 판매 가능 여부
    is_popular BOOLEAN DEFAULT FALSE,              -- [AI_COMPUTED] 인기 메뉴
    
    -- 옵션 정보
    options JSONB,  -- [CRAWLED/MANUAL] 메뉴 옵션
    /* 예시:
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
    }
    */
    
    -- AI 특징
    recommendation_frequency INTEGER DEFAULT 0 CHECK (recommendation_frequency >= 0),  -- [CHATBOT_GENERATED] 추천 횟수
    
    -- 식이 정보 (단순 문자열로 저장)
    dietary_info VARCHAR(200),  -- [MANUAL] 식이 정보 예: '채식,할랄' 또는 '글루텐프리'
    
    -- 메타데이터
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT menus_shop_name_unique UNIQUE (shop_id, menu_name)
);

-- 인덱스
CREATE INDEX idx_menus_shop ON chatbot.menus(shop_id);
CREATE INDEX idx_menus_price ON chatbot.menus(price);
CREATE INDEX idx_menus_available ON chatbot.menus(is_available) WHERE is_available = TRUE;
CREATE INDEX idx_menus_popular ON chatbot.menus(is_popular) WHERE is_popular = TRUE;
-- dietary_tags 인덱스 제거 (단순 문자열로 변경됨)

-- 트리거
CREATE TRIGGER update_menus_updated_at BEFORE UPDATE ON chatbot.menus
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

### 3.3 사용자 테이블 (users)
```sql
CREATE TABLE chatbot.users (
    id SERIAL PRIMARY KEY,
    
    -- 사용자 식별 (플랫폼별 다양한 ID 형식 지원)
    external_user_id VARCHAR(200) NOT NULL UNIQUE,  -- [CLIENT] 외부 사용자 ID
    platform VARCHAR(50) NOT NULL DEFAULT 'web' CHECK (platform IN (
        'web', 'mobile_app', 'kakao', 'line', 'facebook', 'test'
    )),  -- [CLIENT] 접속 플랫폼
    
    -- 기본 정보 (NULL 허용 - 선택적 정보)
    name VARCHAR(100),               -- [USER_PROVIDED] 실명 (선택)
    nickname VARCHAR(100),           -- [USER_PROVIDED] 닉네임
    email VARCHAR(255) UNIQUE,       -- [USER_PROVIDED] 이메일
    phone_number VARCHAR(20),        -- [USER_PROVIDED] 전화번호
    
    -- 인구통계 정보
    birth_date DATE,                 -- [USER_PROVIDED] 생년월일
    
    -- 주소 정보 (단순화)
    current_address TEXT,            -- [USER_PROVIDED] 현재 주소
    preferred_location VARCHAR(100), -- [USER_PROVIDED] 선호 지역 (ex: '강남구', '건국대 근처')
    
    -- 사용자 상태
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE' CHECK (status IN (
        'ACTIVE', 'INACTIVE', 'SUSPENDED', 'DELETED'
    )),
    
    -- 개인정보 동의
    terms_agreed_at TIMESTAMP WITH TIME ZONE,
    privacy_agreed_at TIMESTAMP WITH TIME ZONE,
    marketing_agreed_at TIMESTAMP WITH TIME ZONE,
    
    -- 메타데이터
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMP WITH TIME ZONE,
    
    CONSTRAINT users_email_format CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}$')
);

-- 인덱스
CREATE INDEX idx_users_external_id ON chatbot.users(external_user_id);
CREATE INDEX idx_users_platform ON chatbot.users(platform);
CREATE INDEX idx_users_status ON chatbot.users(status) WHERE status = 'ACTIVE';
-- age_group 인덱스 제거 (필드 삭제됨)

-- 트리거
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON chatbot.users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

### 3.4 급식카드 사용자 테이블 (foodcard_users)
```sql
CREATE TABLE chatbot.foodcard_users (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES chatbot.users(id) ON DELETE CASCADE,
    
    -- 카드 정보
    card_number VARCHAR(50) UNIQUE,
    card_type VARCHAR(30) NOT NULL CHECK (card_type IN (
        '아동급식카드', '청소년급식카드', '취약계층지원카드', '기타'
    )),
    
    -- 잔액 정보 (추천을 위한 읽기 전용)
    balance INTEGER NOT NULL DEFAULT 0 CHECK (balance >= 0),  -- [EXTERNAL_SYNC] 외부 시스템에서 동기화
    
    -- 대상 정보
    target_age_group VARCHAR(20) NOT NULL CHECK (target_age_group IN (
        '초등학생', '중학생', '고등학생', '대학생', '청년', '기타'
    )),
    
    -- 카드 상태
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE' CHECK (status IN (
        'ACTIVE', 'INACTIVE', 'SUSPENDED', 'EXPIRED', 'LOST'
    )),
    
    -- 알림 설정 (추천 시 활용)
    balance_alert_threshold INTEGER DEFAULT 5000,  -- 저잔액 알림 기준 (원)
    balance_alert_sent BOOLEAN DEFAULT FALSE,      -- 알림 발송 여부 (24시간 단위 초기화)
    
    -- 메타데이터
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_sync_at TIMESTAMP WITH TIME ZONE,  -- [SYSTEM] 외부 시스템과 마지막 동기화 시간
    
    CONSTRAINT foodcard_users_unique_user UNIQUE (user_id)
);

-- 인덱스
CREATE INDEX idx_foodcard_user ON chatbot.foodcard_users(user_id);  -- 사용자별 빠른 조회
CREATE INDEX idx_foodcard_status ON chatbot.foodcard_users(status) WHERE status = 'ACTIVE';  -- 활성 카드만
CREATE INDEX idx_foodcard_balance ON chatbot.foodcard_users(balance) WHERE balance < 5000;  -- 저잔액 사용자 타겟팅

-- 테이블 주석
COMMENT ON TABLE chatbot.foodcard_users IS '급식카드 사용자 정보. 외부 시스템과 5분마다 동기화';
COMMENT ON COLUMN chatbot.foodcard_users.balance IS '현재 잔액 (읽기 전용, 외부 시스템에서 관리)';
COMMENT ON COLUMN chatbot.foodcard_users.last_sync_at IS '외부 시스템과 마지막 동기화 시간';

-- 트리거
CREATE TRIGGER update_foodcard_users_updated_at BEFORE UPDATE ON chatbot.foodcard_users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

### 3.5 사용자 프로필 테이블 (user_profiles)
```sql
CREATE TABLE chatbot.user_profiles (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES chatbot.users(id) ON DELETE CASCADE,
    
    -- 선호도 정보 (실제 data_structure.py UserProfile 클래스 기반)
    preferred_categories TEXT[] DEFAULT '{}',  -- [CHATBOT_LEARNED] 선호 음식 카테고리 ['한식', '중식']
    average_budget INTEGER,                    -- [CHATBOT_COMPUTED] 평균 예산 (원)
    favorite_shops INTEGER[] DEFAULT '{}',     -- [USER_BEHAVIOR] 즐겨찾는 가게 ID 배열
    conversation_style VARCHAR(20) DEFAULT 'friendly' CHECK (conversation_style IN (
        'friendly', 'formal', 'casual', 'brief'
    )),                                       -- [CHATBOT_INFERRED] 대화 스타일
    
    -- 학습된 패턴들
    taste_preferences JSONB DEFAULT '{}',      -- [CHATBOT_LEARNED] 맛 선호도 {"매운맛": 0.8, "단맛": 0.3}
    companion_patterns TEXT[] DEFAULT '{}',    -- [CHATBOT_LEARNED] 동반자 패턴 ['혼자', '친구', '가족']
    location_preferences TEXT[] DEFAULT '{}',  -- [CHATBOT_LEARNED] 위치 선호도 ['건국대', '강남']
    
    -- 개인화 관련 설정
    good_influence_preference DECIMAL(3,2) DEFAULT 0.50 CHECK (
        good_influence_preference >= 0 AND good_influence_preference <= 1
    ),                                        -- [USER_BEHAVIOR] 착한가게 선호도 (0.0~1.0)
    interaction_count INTEGER DEFAULT 0,      -- [SYSTEM] 총 상호작용 횟수
    data_completeness DECIMAL(3,2) DEFAULT 0.00 CHECK (
        data_completeness >= 0 AND data_completeness <= 1
    ),                                        -- [SYSTEM] 데이터 완성도 (0.0~1.0)
    
    -- 최근 주문 이력 (JSON 형태로 저장)
    recent_orders JSONB DEFAULT '[]',          -- [USER_BEHAVIOR] 최근 10개 주문 이력
    /*
    예시:
    [
        {
            "shop_id": 15,
            "menu_name": "김치찌개",
            "price": 7000,
            "order_date": "2024-01-15T12:30:00Z",
            "satisfaction": 4.5
        }
    ]
    */
    
    -- 메타데이터
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,  -- UserProfile 클래스와 일치
    
    CONSTRAINT user_profiles_unique_user UNIQUE (user_id)
);

-- 인덱스
CREATE INDEX idx_user_profiles_user ON chatbot.user_profiles(user_id);
CREATE INDEX idx_user_profiles_categories ON chatbot.user_profiles USING GIN(preferred_categories);
CREATE INDEX idx_user_profiles_favorites ON chatbot.user_profiles USING GIN(favorite_shops);
CREATE INDEX idx_user_profiles_completeness ON chatbot.user_profiles(data_completeness DESC)
    WHERE data_completeness > 0.5;

-- 트리거
CREATE TRIGGER update_user_profiles_updated_at BEFORE UPDATE ON chatbot.user_profiles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

COMMENT ON TABLE chatbot.user_profiles IS '사용자 개인화 프로필. data_structure.py UserProfile 클래스와 매핑';
COMMENT ON COLUMN chatbot.user_profiles.data_completeness IS '프로필 완성도. 온보딩 단계별로 증가 (0.0~1.0)';
COMMENT ON COLUMN chatbot.user_profiles.recent_orders IS '최근 10개 주문 이력. 개인화 학습에 사용';
```

### 3.6 쿠폰 테이블 (coupons)
```sql
CREATE TABLE chatbot.coupons (
    id VARCHAR(50) PRIMARY KEY, -- 'WELCOME10', 'FOODCARD20' 등
    
    -- 쿠폰 기본 정보
    coupon_name VARCHAR(200) NOT NULL,
    description TEXT NOT NULL,
    coupon_type VARCHAR(30) NOT NULL CHECK (coupon_type IN (
        'FIXED_AMOUNT', 'PERCENTAGE', 'FREEBIE', 'BOGO'
    )),
    
    -- 할인 정보
    discount_amount INTEGER CHECK (discount_amount > 0), -- 정액 할인 (원)
    discount_rate DECIMAL(3,2) CHECK (discount_rate > 0 AND discount_rate <= 1), -- 정률 할인 (0.00~1.00)
    max_discount_amount INTEGER, -- 정률 할인 시 최대 할인액
    
    -- 사용 조건
    min_order_amount INTEGER DEFAULT 0,
    usage_type VARCHAR(30) NOT NULL CHECK (usage_type IN (
        'ALL', 'SHOP', 'CATEGORY', 'FOODCARD', 'NEW_USER', 'LOYALTY'
    )),
    
    -- 적용 대상
    target_categories TEXT[], -- ARRAY['한식', '중식']
    applicable_shop_ids INTEGER[], -- ARRAY[1, 2, 3]
    target_user_types TEXT[], -- ARRAY['foodcard', 'new', 'vip']
    
    -- 유효 기간
    valid_from DATE NOT NULL DEFAULT CURRENT_DATE,
    valid_until DATE NOT NULL,
    
    -- 발급 제한
    max_issue_count INTEGER, -- NULL이면 무제한
    max_use_per_user INTEGER DEFAULT 1,
    total_issued INTEGER DEFAULT 0,
    total_used INTEGER DEFAULT 0,
    
    -- 상태 관리
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    priority_score DECIMAL(3,2) DEFAULT 0.50 CHECK (priority_score >= 0 AND priority_score <= 1),
    
    -- 메타데이터
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100),
    
    CONSTRAINT coupons_discount_check CHECK (
        (discount_amount IS NOT NULL AND discount_rate IS NULL) OR
        (discount_amount IS NULL AND discount_rate IS NOT NULL)
    ),
    CONSTRAINT coupons_valid_period CHECK (valid_until >= valid_from)
);

-- 인덱스
CREATE INDEX idx_coupons_type ON chatbot.coupons(usage_type);
CREATE INDEX idx_coupons_active ON chatbot.coupons(is_active, valid_from, valid_until);
CREATE INDEX idx_coupons_categories ON chatbot.coupons USING GIN(target_categories);
CREATE INDEX idx_coupons_shops ON chatbot.coupons USING GIN(applicable_shop_ids);
```

### 3.7 사용자 쿠폰 지갑 테이블 (user_coupon_wallet)
```sql
CREATE TABLE chatbot.user_coupon_wallet (
    id BIGSERIAL PRIMARY KEY,
    
    -- 관계
    user_id INTEGER NOT NULL REFERENCES chatbot.users(id) ON DELETE CASCADE,
    coupon_id VARCHAR(50) NOT NULL REFERENCES chatbot.coupons(id),
    
    -- 쿠폰 상태
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE' CHECK (status IN (
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
    
    -- 사용 정보
    used_at TIMESTAMP WITH TIME ZONE,
    used_shop_id INTEGER REFERENCES chatbot.shops(id),
    used_order_amount INTEGER,
    discount_applied INTEGER,
    
    -- 만료 관리
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    expiry_notified BOOLEAN DEFAULT FALSE,
    
    -- AI 예측
    usage_probability DECIMAL(4,3) DEFAULT 0.500 CHECK (usage_probability >= 0 AND usage_probability <= 1),
    recommended_usage_date DATE,
    
    -- 제약조건
    CONSTRAINT user_coupon_unique_active UNIQUE (user_id, coupon_id, status) 
        DEFERRABLE INITIALLY DEFERRED,
    CONSTRAINT user_coupon_status_check CHECK (
        (status = 'USED' AND used_at IS NOT NULL) OR
        (status != 'USED' AND used_at IS NULL)
    )
);

-- 인덱스
CREATE INDEX idx_user_coupon_user_status ON chatbot.user_coupon_wallet(user_id, status);
CREATE INDEX idx_user_coupon_expires ON chatbot.user_coupon_wallet(expires_at) WHERE status = 'ACTIVE';
CREATE INDEX idx_user_coupon_usage_prob ON chatbot.user_coupon_wallet(usage_probability DESC) WHERE status = 'ACTIVE';
```

### 3.8 대화 기록 테이블 (conversations)
```sql
CREATE TABLE chatbot.conversations (
    id BIGSERIAL PRIMARY KEY,
    
    -- 세션 정보
    user_id INTEGER REFERENCES chatbot.users(id),
    session_id UUID NOT NULL DEFAULT uuid_generate_v4(),
    conversation_id UUID NOT NULL DEFAULT uuid_generate_v4(),
    
    -- 대화 내용
    input_text TEXT NOT NULL,        -- [USER_INPUT] 사용자 입력 원문
    response_text TEXT NOT NULL,     -- [CHATBOT_GENERATED] 챗봇 응답
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,  -- [SYSTEM] 발생 시간
    
    -- NLU 결과
    extracted_intent VARCHAR(50) CHECK (extracted_intent IN (
        'FOOD_REQUEST', 'BUDGET_INQUIRY', 'COUPON_INQUIRY', 
        'LOCATION_INQUIRY', 'TIME_INQUIRY', 'GENERAL_CHAT',
        'MENU_OPTION', 'EMERGENCY_FOOD', 'GROUP_DINING', 
        'BALANCE_CHECK', 'BALANCE_CHARGE', 'UNKNOWN'
    )),  -- [AI_COMPUTED] NLU가 추출한 의도
    intent_confidence DECIMAL(4,3) CHECK (intent_confidence >= 0 AND intent_confidence <= 1),  -- [AI_COMPUTED] 의도 신뢰도
    extracted_entities JSONB,  -- [AI_COMPUTED] 추출된 엔티티
    /* 예시:
    {
      "food_type": "치킨",         // 음식 종류
      "budget": 10000,           // 예산 (원)
      "location": "건대입구",      // 위치 선호
      "companions": ["친구"],    // 동반자
      "time_preference": "저녁", // 시간 선호
      "menu_options": ["순살", "매운맛"], // 메뉴 옵션
      "urgency": "normal"       // 긴급도
    }
    */
    
    -- 대화 컨텍스트
    conversation_turn INTEGER NOT NULL DEFAULT 1,  -- [SYSTEM] 대화 턴 번호
    previous_intent VARCHAR(50),                   -- [SYSTEM] 이전 의도
    user_strategy VARCHAR(30) CHECK (user_strategy IN (
        'ONBOARDING', 'DATA_BUILDING', 'NORMAL', 'URGENT'
    )),  -- [AI_COMPUTED] 사용자 전략
    
    -- 성능 메트릭
    processing_time_ms INTEGER,  -- [SYSTEM] 전체 처리 시간
    nlu_time_ms INTEGER,        -- [SYSTEM] NLU 처리 시간
    rag_time_ms INTEGER,        -- [SYSTEM] RAG 검색 시간
    response_time_ms INTEGER,   -- [SYSTEM] 응답 생성 시간
    
    -- 품질 지표
    response_quality_score DECIMAL(4,3),      -- [AI_COMPUTED] 응답 품질
    user_satisfaction_inferred DECIMAL(4,3),  -- [AI_COMPUTED] 추론된 만족도
    conversation_coherence DECIMAL(4,3),      -- [AI_COMPUTED] 대화 일관성
    
    -- 추천 결과
    recommended_shop_ids INTEGER[],           -- [CHATBOT_GENERATED] 추천된 가게 ID 리스트
    selected_shop_id INTEGER REFERENCES chatbot.shops(id),  -- [USER_ACTION] 사용자가 선택한 가게
    applied_coupon_ids TEXT[],               -- [CHATBOT_GENERATED] 적용된 쿠폰 ID
    
    CONSTRAINT conversations_metrics_check CHECK (
        processing_time_ms >= 0 AND
        nlu_time_ms >= 0 AND
        rag_time_ms >= 0 AND
        response_time_ms >= 0
    )
);

-- 인덱스
CREATE INDEX idx_conversations_user_time ON chatbot.conversations(user_id, timestamp DESC);
CREATE INDEX idx_conversations_session ON chatbot.conversations(session_id);
CREATE INDEX idx_conversations_intent ON chatbot.conversations(extracted_intent);
CREATE INDEX idx_conversations_timestamp ON chatbot.conversations(timestamp) 
    WHERE timestamp > CURRENT_TIMESTAMP - INTERVAL '7 days';

-- 파티셔닝 (월별)
CREATE TABLE chatbot.conversations_2024_01 PARTITION OF chatbot.conversations
    FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');
```

### 3.9 추천 로그 테이블 (recommendations_log)
```sql
CREATE TABLE chatbot.recommendations_log (
    id BIGSERIAL PRIMARY KEY,
    
    -- 요청 정보
    user_id INTEGER REFERENCES chatbot.users(id),
    session_id UUID NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- 요청 컨텍스트
    request_intent VARCHAR(50) NOT NULL,      -- [CHATBOT_GENERATED] 요청 의도
    request_entities JSONB NOT NULL,          -- [CHATBOT_GENERATED] 요청 엔티티
    user_location GEOGRAPHY(POINT, 4326),     -- [CLIENT] 사용자 위치
    
    -- 추천 결과
    recommendations JSONB NOT NULL,  -- [CHATBOT_GENERATED] 추천 결과 상세
    /* 예시:
    [{
      "shop_id": 15,
      "shop_name": "김밥천국",
      "score": 0.92,               // 추천 점수 (0.0~1.0)
      "ranking": 1,                // 순위
      "distance_meters": 250,      // 거리 (미터)
      "reason_codes": ["BUDGET_FIT", "NEARBY", "POPULAR", "FOODCARD_OK"],  // 추천 이유
      "menus": [                   // 추천 메뉴
        {"name": "참치김밥", "price": 3500, "is_available": true},
        {"name": "돈까스", "price": 5000, "is_available": true}
      ],
      "final_price": 3500,         // 최종 가격 (할인 적용 후)
      "foodcard_usable": true      // 급식카드 사용 가능 여부
    }]
    */
    
    -- 추천 메타데이터
    recommendation_count INTEGER NOT NULL,    -- [SYSTEM] 추천 개수
    recommendation_method VARCHAR(50) NOT NULL CHECK (recommendation_method IN (
        'WIDE_DEEP', 'RAG', 'HYBRID', 'EMERGENCY', 'COUPON_BASED', 'FALLBACK'
    )),  -- [SYSTEM] 추천 방법
    confidence_score DECIMAL(4,3),           -- [AI_COMPUTED] 추천 신뢰도
    total_candidates INTEGER,                -- [SYSTEM] 후보 개수
    filtering_steps JSONB,                   -- [SYSTEM] 필터링 단계
    
    -- 사용자 반응
    user_viewed_details INTEGER[],           -- [USER_ACTION] 상세 조회한 가게
    user_final_selection INTEGER REFERENCES chatbot.shops(id),  -- [USER_ACTION] 최종 선택
    time_to_decision_ms INTEGER,             -- [SYSTEM] 결정 시간
    feedback_rating INTEGER CHECK (feedback_rating >= 1 AND feedback_rating <= 5),  -- [USER_PROVIDED] 평점
    
    -- 추천 품질 메트릭
    diversity_score DECIMAL(4,3),            -- [AI_COMPUTED] 다양성 점수
    personalization_score DECIMAL(4,3),      -- [AI_COMPUTED] 개인화 점수
    relevance_score DECIMAL(4,3),            -- [AI_COMPUTED] 관련성 점수
    novelty_score DECIMAL(4,3)               -- [AI_COMPUTED] 새로움 점수
);

-- 인덱스
CREATE INDEX idx_recommendations_user_time ON chatbot.recommendations_log(user_id, timestamp DESC);
CREATE INDEX idx_recommendations_method ON chatbot.recommendations_log(recommendation_method);
CREATE INDEX idx_recommendations_selection ON chatbot.recommendations_log(user_final_selection) 
    WHERE user_final_selection IS NOT NULL;
```

---

## 4. 데이터 타입 상세 명세

### 4.1 PostgreSQL 데이터 타입 선택 가이드

| 용도 | PostgreSQL 타입 | 범위/제약 | 사용 예시 |
|------|----------------|-----------|-----------|
| **ID (Primary Key)** | SERIAL / BIGSERIAL | 4byte: ~21억 / 8byte: ~922경 | 테이블 크기에 따라 선택 |
| **UUID** | UUID | 128-bit | 세션ID, 고유 식별자 |
| **짧은 문자열** | VARCHAR(n) | 최대 n 글자 | 이름, 카테고리 |
| **긴 문자열** | TEXT | 무제한 | 설명, 메시지 |
| **정수** | INTEGER | -2,147,483,648 ~ 2,147,483,647 | 가격, 수량 |
| **큰 정수** | BIGINT | -9,223,372,036,854,775,808 ~ 9,223,372,036,854,775,807 | 조회수, 누적값 |
| **소수** | DECIMAL(p,s) | p: 전체자리수, s: 소수자리수 | 비율, 점수 |
| **부동소수점** | REAL / DOUBLE PRECISION | 6자리 / 15자리 정밀도 | 과학 계산 |
| **불린** | BOOLEAN | TRUE/FALSE/NULL | 상태 플래그 |
| **날짜** | DATE | 4713 BC ~ 5874897 AD | 생년월일 |
| **시간** | TIME | 00:00:00 ~ 24:00:00 | 영업시간 |
| **타임스탬프** | TIMESTAMP WITH TIME ZONE | 4713 BC ~ 294276 AD | 이벤트 시각 |
| **JSON** | JSONB | 바이너리 JSON | 구조화된 데이터 |
| **배열** | TYPE[] | 1차원/다차원 배열 | 카테고리 목록 |
| **지리정보** | GEOGRAPHY(POINT, 4326) | WGS84 좌표계 | 위치 정보 |

### 4.2 명명 규칙

```sql
-- 테이블명: 복수형, snake_case
CREATE TABLE users (...);
CREATE TABLE product_orders (...);

-- 컬럼명: snake_case
user_id INTEGER
created_at TIMESTAMP
is_active BOOLEAN

-- 인덱스명: idx_테이블명_컬럼명
CREATE INDEX idx_users_email ON users(email);

-- 제약조건명: 테이블명_제약유형_설명
CONSTRAINT users_email_unique UNIQUE (email)
CONSTRAINT orders_amount_positive CHECK (amount > 0)

-- 외래키명: fk_자식테이블_부모테이블
CONSTRAINT fk_orders_users FOREIGN KEY (user_id) REFERENCES users(id)
```

### 4.3 JSONB 스키마 정의

```javascript
// 영업시간 (business_hours)
{
  "type": "object",
  "properties": {
    "monday": {
      "type": "object",
      "properties": {
        "open": {"type": "string", "pattern": "^\\d{2}:\\d{2}$"},
        "close": {"type": "string", "pattern": "^\\d{2}:\\d{2}$"},
        "break_start": {"type": "string", "pattern": "^\\d{2}:\\d{2}$"},
        "break_end": {"type": "string", "pattern": "^\\d{2}:\\d{2}$"},
        "closed": {"type": "boolean"}
      }
    }
    // tuesday ~ sunday 동일
  }
}

// 추출된 엔티티 (extracted_entities)
{
  "type": "object",
  "properties": {
    "food_type": {"type": "string", "description": "음식 종류 (치킨, 피자 등)"},
    "budget": {"type": "integer", "minimum": 0, "maximum": 100000},
    "location": {"type": "string", "description": "위치 선호"},
    "companions": {"type": "array", "items": {"type": "string"}},
    "time_preference": {"type": "string", "enum": ["아침", "점심", "저녁", "야식"]},
    "menu_options": {"type": "array", "items": {"type": "string"}},
    "urgency": {"type": "string", "enum": ["high", "normal", "low"]}
  },
  "additionalProperties": true
}

// 추천 결과 (recommendations)
{
  "type": "array",
  "items": {
    "type": "object",
    "required": ["shop_id", "shop_name", "score", "ranking"],
    "properties": {
      "shop_id": {"type": "integer"},
      "shop_name": {"type": "string"},
      "score": {"type": "number", "minimum": 0, "maximum": 1},
      "ranking": {"type": "integer", "minimum": 1},
      "distance_meters": {"type": "integer"},
      "reason_codes": {
        "type": "array",
        "items": {"type": "string", "enum": ["BUDGET_FIT", "NEARBY", "POPULAR", "FOODCARD_OK", "HIGH_QUALITY", "USER_PREFERENCE"]}
      },
      "menus": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "name": {"type": "string"},
            "price": {"type": "integer"},
            "is_available": {"type": "boolean"}
          }
        }
      },
      "final_price": {"type": "integer"},
      "foodcard_usable": {"type": "boolean"}
    }
  }
}

// 메뉴 옵션 (options)
{
  "type": "object",
  "properties": {
    "size": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "name": {"type": "string"},
          "price": {"type": "integer", "minimum": 0}
        },
        "required": ["name", "price"]
      }
    },
    "spicy": {"type": "array", "items": {"$ref": "#/properties/size/items"}},
    "extras": {"type": "array", "items": {"$ref": "#/properties/size/items"}}
  }
}
```

---

## 5. 시스템 플로우 문서

### 5.1 전체 시스템 아키텍처 플로우

#### 시스템 구성 요소
1. **클라이언트 레이어**
   - 웹 프론트엔드 (React/Vue.js)
   - 모바일 앱 (Flutter/React Native)
   - 메신저 봇 (카카오톡, 라인)

2. **API 게이트웨이**
   - FastAPI 기반 REST API
   - WebSocket 실시간 통신
   - 인증/인가 처리

3. **비즈니스 로직 레이어**
   - NLU 엔진 (자연어 이해)
   - 추천 엔진 (Wide&Deep)
   - RAG 시스템 (검색 증강 생성)
   - 쿠폰 관리자

4. **데이터 레이어**
   - PostgreSQL (주 데이터베이스)
   - Redis (캐시/세션)
   - FAISS (벡터 검색)
   - S3 (파일 스토리지)

### 5.2 사용자 요청 처리 플로우

#### Step 1: 요청 수신 및 인증 (0-50ms)
```
1. 클라이언트 → API Gateway
   - HTTP POST /api/v1/chat
   - Headers: Authorization: Bearer {token}
   - Body: {
       "message": "5천원으로 점심 뭐 먹지?",
       "session_id": "uuid-xxxx",
       "location": {"lat": 37.5665, "lng": 126.9780}
     }

2. API Gateway 처리
   - JWT 토큰 검증
   - Rate limiting 체크 (분당 60회)
   - Request ID 생성
   - 로깅 시작
```

#### Step 2: 사용자 컨텍스트 로드 (50-100ms)
```
3. 사용자 정보 조회
   - Redis 캐시 확인
     KEY: user:{user_id}:profile
     TTL: 3600초
   
   - 캐시 미스 시 DB 조회
     SELECT * FROM users WHERE id = ?
     SELECT * FROM foodcard_users WHERE user_id = ?
     SELECT * FROM user_profiles WHERE user_id = ?

4. 세션 컨텍스트 로드
   - Redis에서 대화 히스토리
     KEY: session:{session_id}:context
     데이터: 최근 10턴 대화 내역
```

#### Step 3: NLU 처리 (100-200ms)
```
5. 텍스트 전처리
   - 정규화: "５천원" → "5천원"
   - 토큰화: ["5천원", "으로", "점심", "뭐", "먹지"]
   - 형태소 분석: Mecab/Komoran

6. 의도 분류 (Intent Classification)
   - 입력: 전처리된 텍스트 + 컨텍스트
   - 모델: KoAlpaca 기반 분류기
   - 출력: {
       "intent": "BUDGET_INQUIRY",
       "confidence": 0.92
     }

7. 엔티티 추출 (Entity Extraction)
   - 규칙 기반 + ML 하이브리드
   - 추출 결과: {
       "budget": 5000,
       "meal_time": "lunch",
       "urgency": "normal"
     }

8. NLU 결과 캐싱
   - DB 저장: INSERT INTO nlu_training_data ...
   - 캐시 저장: SET nlu:{text_hash} = {result}
```

#### Step 4: 추천 후보 생성 (200-400ms)
```
9. 필터링 조건 생성
   - 예산: price <= 5000
   - 시간: 현재 영업 중
   - 위치: 반경 1km 이내
   - 급식카드: 사용 가능 매장

10. RAG 검색 수행
    - 쿼리 임베딩 생성
      모델: sentence-transformers/xlm-r-bert
      차원: 768
    
    - FAISS 벡터 검색
      인덱스: IVF1024,Flat
      검색 개수: 100
    
    - 시맨틱 매칭 점수 계산

11. 데이터베이스 필터링
    SELECT s.*, m.*
    FROM shops s
    JOIN menus m ON s.id = m.shop_id
    WHERE s.current_status = 'OPEN'
      AND m.price <= 5000
      AND ST_DWithin(s.geom, user_location, 1000)
      AND s.is_food_card_shop IN ('Y', 'P')
    ORDER BY s.popularity_score DESC
    LIMIT 50;
```

#### Step 5: 추천 스코어링 (400-500ms)
```
12. 특징 추출 (Feature Engineering)
    사용자 특징:
    - category_preferences: [0.7, 0.3, 0.5, ...]
    - avg_budget_norm: 0.45
    - meal_time_patterns: {"lunch": 0.8, "dinner": 0.2}
    
    가게 특징:
    - popularity_score: 0.85
    - distance_penalty: 0.92
    - price_match_score: 0.95
    
    교차 특징:
    - user_shop_affinity: 0.73
    - time_appropriateness: 0.90

13. Wide&Deep 모델 예측
    - Wide 부분: 선형 특징 조합
    - Deep 부분: 신경망 (3층, 128-64-32)
    - 최종 점수: 0.0 ~ 1.0

14. 쿠폰 매칭
    SELECT c.*, ucw.*
    FROM coupons c
    JOIN user_coupon_wallet ucw ON c.id = ucw.coupon_id
    WHERE ucw.user_id = ? 
      AND ucw.status = 'ACTIVE'
      AND c.min_order_amount <= ?
      AND (c.applicable_shop_ids && ARRAY[?] OR c.usage_type = 'ALL')
```

#### Step 6: 응답 생성 (500-600ms)
```
15. 추천 순위 결정
    - Wide&Deep 점수로 정렬
    - 다양성 보장 (MMR 알고리즘)
    - 상위 5개 선택

16. 응답 텍스트 생성
    - 템플릿 선택
    - 개인화 요소 삽입
    - 이모지 추가 (선택적)
    
    예시: "5천원으로 즐길 수 있는 점심 추천드려요! 🍱
           1. 김밥천국 (도보 5분) - 참치김밥 3,500원
           2. 봉구스밥버거 (도보 7분) - 불고기버거 4,500원"

17. 추가 정보 포함
    - 영업시간
    - 쿠폰 적용 가격
    - 급식카드 사용 가능 여부
    - 리뷰 요약
```

#### Step 7: 로깅 및 학습 (비동기, 600ms+)
```
18. 대화 기록 저장
    INSERT INTO conversations (
        user_id, session_id, input_text, response_text,
        extracted_intent, extracted_entities, processing_time_ms
    ) VALUES (?, ?, ?, ?, ?, ?, ?);

19. 추천 로그 저장
    INSERT INTO recommendations_log (
        user_id, session_id, recommendations,
        recommendation_method, confidence_score
    ) VALUES (?, ?, ?, ?, ?);

20. 성능 메트릭 기록
    INSERT INTO performance_logs (
        operation_type, total_time_ms, 
        nlu_time_ms, rag_time_ms, recommendation_time_ms
    ) VALUES (?, ?, ?, ?, ?);

21. 학습 데이터 수집 (비동기)
    - 사용자 피드백 대기
    - 선택 결과 추적
    - 만족도 추론
```

### 5.3 특수 시나리오 플로우

#### 시나리오 1: 급식카드 잔액 부족
```
잔액 확인 → 긴급 쿠폰 자격 검사 → 쿠폰 자동 발급 → 알림 전송

1. 잔액 체크
   SELECT balance FROM foodcard_users WHERE user_id = ?
   
2. 임계값 비교 (balance < 5000)

3. 긴급 쿠폰 발급
   - 쿠폰 생성: 'EMERGENCY_FOOD_AID'
   - 지갑에 추가
   - 24시간 만료 설정

4. 푸시 알림
   "잔액이 부족해요! 긴급 식사 쿠폰을 발급해드렸습니다."
```

#### 시나리오 2: 신규 사용자 온보딩
```
최초 접속 → 환영 메시지 → 선호도 수집 → 프로필 생성 → 환영 쿠폰

1. 신규 사용자 감지
   SELECT COUNT(*) FROM users WHERE external_user_id = ?
   
2. 온보딩 전략 활성화
   SET user_strategy = 'ONBOARDING'
   
3. 데이터 수집 대화
   - "어떤 음식을 좋아하시나요?"
   - "평소 식사 예산은 어느 정도인가요?"
   - "매운 음식은 괜찮으신가요?"

4. 프로필 초기화
   INSERT INTO user_profiles ...
   
5. 환영 혜택
   - 3,000원 할인 쿠폰
   - 첫 주문 10% 추가 할인
```

#### 시나리오 3: 그룹 주문 처리
```
단체 식사 요청 → 인원 파악 → 적합 매장 필터링 → 예약 가능 확인

1. 그룹 컨텍스트 추출
   entities: {
     "companion_count": 10,
     "occasion": "회식"
   }

2. 그룹 적합 매장 쿼리
   - 좌석 수 >= 10
   - 단체 예약 가능
   - 룸/홀 보유

3. 예약 API 연동
   - 실시간 예약 가능 여부
   - 예약 링크 제공
```

### 5.4 데이터 동기화 플로우

#### 실시간 동기화
```
1. 영업 상태 업데이트 (1분 주기)
   - 현재 시간 vs 영업시간 비교
   - current_status 필드 업데이트
   - 캐시 무효화

2. 인기도 점수 계산 (5분 주기)
   - 최근 추천/선택 집계
   - 지수 이동 평균 적용
   - popularity_score 업데이트

3. 사용자 프로필 갱신 (세션 종료 시)
   - 선호도 재계산
   - 패턴 분석
   - 다음 예측 갱신
```

#### 배치 동기화
```
1. 일일 배치 (새벽 2시)
   - 전일 로그 집계
   - 특징 벡터 재계산
   - 오래된 캐시 정리
   - 통계 리포트 생성

2. 주간 배치 (일요일 새벽)
   - 모델 재학습 데이터 준비
   - A/B 테스트 결과 분석
   - 쿠폰 효과성 분석

3. 월간 배치 (월초)
   - 사용자 세그먼테이션
   - 장기 트렌드 분석
   - 데이터 아카이빙
```

---

## 6. API 엔드포인트 및 데이터 흐름

### 6.1 주요 API 엔드포인트

#### 채팅 API
```
POST /api/v1/chat
Request:
{
  "message": "string",
  "session_id": "uuid",
  "location": {
    "latitude": "number",
    "longitude": "number"
  },
  "context": {
    "time_of_day": "string",
    "weather": "string",
    "companion_count": "number"
  }
}

Response:
{
  "response": "string",
  "recommendations": [{
    "shop_id": "number",
    "shop_name": "string",
    "menus": [{
      "menu_id": "number",
      "menu_name": "string",
      "price": "number",
      "final_price": "number"
    }],
    "applicable_coupons": ["string"],
    "distance": "number",
    "estimated_time": "number"
  }],
  "session_info": {
    "intent": "string",
    "confidence": "number",
    "conversation_turn": "number"
  }
}
```

#### 사용자 API
```
GET /api/v1/users/{user_id}/profile
Response:
{
  "user_id": "number",
  "preferences": {
    "categories": ["string"],
    "budget_range": {
      "min": "number",
      "max": "number"
    },
    "dietary_restrictions": ["string"]
  },
  "statistics": {
    "total_orders": "number",
    "favorite_shops": ["number"],
    "avg_spending": "number"
  }
}

PUT /api/v1/users/{user_id}/preferences
Request:
{
  "categories": ["string"],
  "budget": "number",
  "dietary_restrictions": ["string"]
}
```

#### 쿠폰 API
```
GET /api/v1/users/{user_id}/coupons
Response:
{
  "active_coupons": [{
    "coupon_id": "string",
    "name": "string",
    "discount_amount": "number",
    "discount_rate": "number",
    "expires_at": "datetime",
    "applicable_shops": ["number"]
  }],
  "expired_coupons": [],
  "used_coupons": []
}

POST /api/v1/coupons/apply
Request:
{
  "user_id": "number",
  "coupon_id": "string",
  "shop_id": "number",
  "order_amount": "number"
}
```

### 6.2 데이터 흐름 다이어그램 (텍스트)

```
[클라이언트]
    ↓ HTTPS
[API Gateway / Load Balancer]
    ↓ Internal Network
[FastAPI Application Server]
    ↓ ↓ ↓
[NLU Service] [Recommendation Service] [Coupon Service]
    ↓ ↓ ↓
[Redis Cache Layer]
    ↓ (Cache Miss)
[PostgreSQL Primary DB]
    ↓ (Replication)
[PostgreSQL Read Replicas]

병렬 처리:
- NLU: KoAlpaca 모델 서버
- Vector Search: FAISS 인덱스 서버
- Session: Redis 세션 스토어
```

### 6.3 데이터 일관성 보장

#### 트랜잭션 범위
```python
# 주문 처리 트랜잭션
async def process_order(user_id, shop_id, items, coupon_id):
    async with db.transaction():
        # 1. 주문 생성
        order = await create_order(user_id, shop_id, items)
        
        # 2. 쿠폰 사용 처리
        if coupon_id:
            await use_coupon(user_id, coupon_id, order.id)
        
        # 3. 급식카드 잔액 차감
        await deduct_foodcard_balance(user_id, order.total_amount)
        
        # 4. 통계 업데이트
        await update_shop_statistics(shop_id)
        await update_user_statistics(user_id)
        
        # 5. 캐시 무효화
        await invalidate_caches(user_id, shop_id)
        
    return order
```

#### 캐시 일관성
```python
# 캐시 무효화 전략
CACHE_INVALIDATION_RULES = {
    'user_profile_update': [
        'user:{user_id}:profile',
        'user:{user_id}:preferences',
        'recommendations:{user_id}:*'
    ],
    'shop_update': [
        'shop:{shop_id}:info',
        'shop:{shop_id}:menus',
        'search:category:{category}:*'
    ],
    'order_complete': [
        'user:{user_id}:recent_orders',
        'shop:{shop_id}:popularity',
        'stats:daily:*'
    ]
}
```

---

## 7. 데이터 마이그레이션 가이드

### 7.1 초기 데이터 로드

#### Excel 데이터 임포트
```python
import pandas as pd
import psycopg2
from datetime import datetime

def import_shops_from_excel(file_path, db_conn):
    """sample_data.xlsx에서 가게 정보 임포트"""
    
    # Excel 읽기
    df = pd.read_excel(file_path, sheet_name='shops')
    
    # 데이터 정제
    df['is_good_influence_shop'] = df['is_good_influence_shop'].fillna(False)
    df['is_food_card_shop'] = df['is_food_card_shop'].fillna('U')
    df['created_at'] = datetime.now()
    df['updated_at'] = datetime.now()
    
    # NULL 처리
    df['phone'] = df['phone'].replace('', None)
    df['owner_message'] = df['owner_message'].replace('', None)
    
    # 영업시간 JSON 변환
    df['business_hours'] = df.apply(convert_business_hours, axis=1)
    
    # DB 삽입
    cursor = db_conn.cursor()
    insert_query = """
        INSERT INTO chatbot.shops (
            shop_name, category, address_name, 
            is_good_influence_shop, is_food_card_shop,
            business_hours, phone, owner_message,
            latitude, longitude, created_at, updated_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (shop_name, address_name) DO UPDATE SET
            updated_at = EXCLUDED.updated_at
    """
    
    for _, row in df.iterrows():
        cursor.execute(insert_query, tuple(row[columns]))
    
    db_conn.commit()
    print(f"Imported {len(df)} shops")

def convert_business_hours(row):
    """영업시간을 JSON 형식으로 변환"""
    hours = {}
    days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
    
    for day in days:
        hours[day] = {
            'open': row.get(f'{day}_open', '09:00'),
            'close': row.get(f'{day}_close', '22:00')
        }
        
        if row.get(f'{day}_break_start'):
            hours[day]['break_start'] = row[f'{day}_break_start']
            hours[day]['break_end'] = row[f'{day}_break_end']
    
    return json.dumps(hours, ensure_ascii=False)
```

### 7.2 데이터 검증

```sql
-- 데이터 무결성 검증 쿼리
-- 1. 고아 레코드 확인
SELECT m.* FROM chatbot.menus m
LEFT JOIN chatbot.shops s ON m.shop_id = s.id
WHERE s.id IS NULL;

-- 2. 중복 데이터 확인
SELECT shop_name, address_name, COUNT(*) 
FROM chatbot.shops 
GROUP BY shop_name, address_name 
HAVING COUNT(*) > 1;

-- 3. 필수 필드 NULL 체크
SELECT * FROM chatbot.shops 
WHERE shop_name IS NULL 
   OR category IS NULL 
   OR latitude IS NULL 
   OR longitude IS NULL;

-- 4. 데이터 범위 검증
SELECT * FROM chatbot.menus WHERE price < 0 OR price > 1000000;
SELECT * FROM chatbot.shops WHERE latitude NOT BETWEEN -90 AND 90;
SELECT * FROM chatbot.user_coupon_wallet WHERE expires_at < issued_at;

-- 5. 참조 무결성 검증
SELECT ucw.* FROM chatbot.user_coupon_wallet ucw
LEFT JOIN chatbot.users u ON ucw.user_id = u.id
LEFT JOIN chatbot.coupons c ON ucw.coupon_id = c.id
WHERE u.id IS NULL OR c.id IS NULL;
```

### 7.3 성능 최적화 체크리스트

```sql
-- 1. 테이블 통계 업데이트
ANALYZE chatbot.shops;
ANALYZE chatbot.menus;
ANALYZE chatbot.users;

-- 2. 인덱스 사용률 확인
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
WHERE schemaname = 'chatbot'
ORDER BY idx_scan DESC;

-- 3. 느린 쿼리 확인
SELECT 
    query,
    calls,
    mean_time,
    total_time,
    min_time,
    max_time
FROM pg_stat_statements
WHERE mean_time > 100  -- 100ms 이상
ORDER BY mean_time DESC
LIMIT 20;

-- 4. 테이블 크기 확인
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'chatbot'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- 5. 파티션 상태 확인
SELECT 
    parent.relname AS parent_table,
    child.relname AS partition_name,
    pg_size_pretty(pg_relation_size(child.oid)) AS partition_size
FROM pg_inherits
JOIN pg_class parent ON pg_inherits.inhparent = parent.oid
JOIN pg_class child ON pg_inherits.inhrelid = child.oid
WHERE parent.relname = 'conversations';
```

### 7.4 백업 및 복구 전략

```bash
# 일일 백업 스크립트
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backup/postgresql"
DB_NAME="naviyam_chatbot"

# 전체 백업
pg_dump -h localhost -U postgres -d $DB_NAME -F custom -f $BACKUP_DIR/full_backup_$DATE.dump

# 스키마별 백업
pg_dump -h localhost -U postgres -d $DB_NAME -n chatbot -F custom -f $BACKUP_DIR/chatbot_schema_$DATE.dump
pg_dump -h localhost -U postgres -d $DB_NAME -n analytics -F custom -f $BACKUP_DIR/analytics_schema_$DATE.dump

# 중요 테이블 개별 백업
pg_dump -h localhost -U postgres -d $DB_NAME -t chatbot.users -F custom -f $BACKUP_DIR/users_$DATE.dump
pg_dump -h localhost -U postgres -d $DB_NAME -t chatbot.foodcard_users -F custom -f $BACKUP_DIR/foodcard_users_$DATE.dump

# 7일 이상 된 백업 삭제
find $BACKUP_DIR -name "*.dump" -mtime +7 -delete

# S3 업로드 (선택사항)
aws s3 cp $BACKUP_DIR/full_backup_$DATE.dump s3://naviyam-backups/postgresql/
```

---

## 8. 학습 데이터 처리 상세 설계

### 8.1 학습 데이터 수집 아키텍처

#### 데이터 수집 시스템 구조
```
[LearningDataCollector]
    ├── 4개의 데이터 버퍼 (deque)
    │   ├── NLU 버퍼: NLU 처리 결과
    │   ├── 상호작용 버퍼: 대화 내용
    │   ├── 추천 버퍼: 추천 결과
    │   └── 피드백 버퍼: 사용자 반응
    │
    ├── 세션 관리
    │   ├── active_sessions: Dict[str, CollectionSession]
    │   └── session_timeout: 2시간
    │
    └── 자동 저장
        ├── auto_save_interval: 300초
        └── 백그라운드 스레드로 처리
```

#### 데이터 수집 플로우
```
[사용자 입력] → [NLU 처리] → [응답 생성]
      ↓             ↓             ↓
[상호작용 버퍼] [NLU 버퍼]  [추천 버퍼]
      ↓             ↓             ↓
        [세션별 데이터 포인트 추가]
                    ↓
            [품질 메트릭 업데이트]
                    ↓
        [자동 저장 (5분마다) 또는 세션 종료 시]
                    ↓
            [JSONL 파일로 저장]
```

#### 데이터 구조 정의

##### CollectionSession 데이터클래스
```python
@dataclass
class CollectionSession:
    """데이터 수집 세션"""
    session_id: str                      # 세션 고유 ID
    user_id: str                         # 사용자 ID
    start_time: datetime                 # 세션 시작 시간
    data_points: List[Dict[str, Any]]    # 수집된 데이터 포인트들
    status: str = "active"               # active, completed, error
```

##### DataQualityMetrics 데이터클래스
```python
@dataclass
class DataQualityMetrics:
    """데이터 품질 지표"""
    total_collected: int = 0                        # 총 수집 개수
    valid_samples: int = 0                          # 유효 샘플 수
    invalid_samples: int = 0                        # 무효 샘플 수
    missing_fields: Dict[str, int] = field(default_factory=dict)      # 누락 필드 통계
    confidence_distribution: Dict[str, int] = field(default_factory=dict)  # 신뢰도 분포
```

##### LearningData 데이터클래스 (기존)
```python
@dataclass
class LearningData:
    """구조화된 학습 데이터"""
    user_id: str                                    # 사용자 ID
    timestamp: datetime = field(default_factory=datetime.now)
    
    # 기본 추출 데이터
    extracted_entities: Dict[str, Any] = field(default_factory=dict)   # 추출된 엔티티
    intent_confidence: float = 0.0                  # 의도 분류 신뢰도
    
    # 학습용 Feature들
    food_preferences: List[str] = field(default_factory=list)         # 선호 음식 ["치킨", "피자"]
    budget_patterns: List[int] = field(default_factory=list)          # 예산 패턴 [5000, 8000, 10000]
    companion_patterns: List[str] = field(default_factory=list)       # 동반자 패턴 ["혼자", "친구"]
    taste_preferences: Dict[str, float] = field(default_factory=dict) # 맛 선호도 {"매운맛": 0.8}
    
    # 선택/피드백 데이터
    recommendations_provided: List[Dict] = field(default_factory=list) # 제공된 추천
    user_selection: Optional[Dict] = None           # 사용자 선택
    user_feedback: Optional[str] = None             # 피드백 ("positive", "negative")
    satisfaction_score: Optional[float] = None      # 만족도 점수 (0.0 ~ 1.0)
```

### 8.2 파일 기반 저장 구조 (실제 구현)

#### 저장 디렉토리 구조
```
output/learning_data/
├── raw/                           # 원시 데이터 (JSONL 형식)
│   ├── nlu_features_20240315.jsonl
│   ├── interactions_20240315.jsonl
│   ├── recommendations_20240315.jsonl
│   └── feedback_20240315.jsonl
├── processed/                     # 처리된 데이터
│   └── processed_data_20240315.jsonl
└── sessions/                      # 세션별 데이터 (JSON)
    └── user123_20240315.json
```

#### 데이터 파일 형식

**1. NLU Features 파일 (nlu_features_YYYYMMDD.jsonl)**
```json
{
  "timestamp": "2024-03-15T14:30:00",
  "user_id": "user123",
  "data_type": "nlu_features",
  "features": {
    "nlu_intent": "음식추천",
    "nlu_confidence": 0.92,
    "food_category_mentioned": "한식",
    "budget_mentioned": 15000,
    "companion_mentioned": "가족",
    "entities": {
      "cuisine_type": ["한식"],
      "price_range": 15000,
      "group_size": 4
    }
  }
}
```

**2. Interactions 파일 (interactions_YYYYMMDD.jsonl)**
```json
{
  "timestamp": "2024-03-15T14:30:05",
  "user_id": "user123",
  "data_type": "interaction",
  "interaction": {
    "input_text": "가족과 함께 먹을 한식당 추천해줘",
    "intent": "음식추천",
    "confidence": 0.92,
    "entities": {
      "cuisine": ["한식"],
      "companion": ["가족"]
    },
    "response_text": "가족과 함께 즐기기 좋은 한식당을 추천해드릴게요.",
    "response_time_ms": 245,
    "conversation_turn": 1
  }
}
```

**3. Recommendations 파일 (recommendations_YYYYMMDD.jsonl)**
```json
{
  "timestamp": "2024-03-15T14:30:10",
  "user_id": "user123",
  "data_type": "recommendation",
  "recommendations": [
    {
      "shop_id": 1234,
      "shop_name": "전통한정식",
      "score": 0.95,
      "price": 20000,
      "cuisine_type": "한식",
      "rating": 4.5
    }
  ],
  "user_selection": {
    "shop_id": 1234,
    "selected_at": "2024-03-15T14:31:00"
  },
  "recommendation_count": 3
}
```

**4. Feedback 파일 (feedback_YYYYMMDD.jsonl)**
```json
{
  "timestamp": "2024-03-15T14:32:00",
  "user_id": "user123",
  "data_type": "feedback",
  "feedback_type": "rating",
  "feedback_content": 5,
  "context": {
    "shop_id": 1234,
    "session_id": "user123_20240315",
    "recommendation_satisfied": true
  }
}
```

**5. Session 파일 (sessions/user123_20240315.json)**
```json
{
  "session_id": "user123_20240315",
  "user_id": "user123",
  "start_time": "2024-03-15T14:30:00",
  "end_time": "2024-03-15T14:35:00",
  "data_points_count": 12,
  "status": "completed",
  "data_points": [
    // 세션 동안 수집된 모든 데이터 포인트
  ]
}
```

#### 품질 점수 계산 (0.0 ~ 1.0)
```python
quality_score = (
    nlu_confidence * 0.3 +           # NLU 신뢰도 (30%)
    response_time_score * 0.2 +      # 응답 속도 (20%)
    has_recommendations * 0.3 +      # 추천 존재 (30%)
    response_length_score * 0.2      # 응답 길이 (20%)
)
```

#### 세션 가치 평가 기준
- 최소 2턴 이상의 대화
- 평균 품질 점수 0.5 이상
- 하나 이상의 추천 포함
- 정상 종료된 세션

### 8.3 데이터 수집 메소드 상세

#### 1. NLU Feature 수집
```python
def collect_nlu_features(self, user_id: str, features: Dict[str, Any]):
    """
    NLU 처리 결과를 수집
    
    Args:
        user_id: 사용자 ID
        features: {
            "nlu_intent": str,           # 추출된 의도
            "nlu_confidence": float,     # 신뢰도 (0.0~1.0)
            "food_category_mentioned": str,
            "budget_mentioned": int,
            "companion_mentioned": str,
            "entities": Dict[str, Any]
        }
    """
```

#### 2. 상호작용 데이터 수집
```python
def collect_interaction_data(self, user_id: str, interaction_data: Dict[str, Any]):
    """
    대화 상호작용 데이터 수집
    
    Args:
        user_id: 사용자 ID
        interaction_data: {
            "input_text": str,           # 사용자 입력
            "intent": str,               # 분류된 의도
            "confidence": float,         # 의도 신뢰도
            "entities": Dict,            # 추출된 엔티티
            "response_text": str,        # 챗봇 응답
            "response_time_ms": int,     # 응답 시간
            "conversation_turn": int     # 대화 턴
        }
    """
```

#### 3. 추천 데이터 수집
```python
def collect_recommendation_data(self, user_id: str, recommendations: List[Dict], 
                               user_selection: Optional[Dict] = None):
    """
    추천 결과 및 사용자 선택 수집
    
    Args:
        user_id: 사용자 ID
        recommendations: [{
            "shop_id": int,
            "shop_name": str,
            "score": float,
            "price": int,
            "cuisine_type": str,
            "rating": float
        }]
        user_selection: {
            "shop_id": int,
            "selected_at": str
        }
    """
```

#### 4. 피드백 데이터 수집
```python
def collect_feedback_data(self, user_id: str, feedback_type: str, 
                         feedback_content: Any, context: Dict[str, Any] = None):
    """
    사용자 피드백 수집
    
    Args:
        user_id: 사용자 ID
        feedback_type: "selection" | "rating" | "text" | "implicit"
        feedback_content: 피드백 내용 (타입에 따라 다름)
        context: {
            "shop_id": int,
            "session_id": str,
            "recommendation_satisfied": bool
        }
    """
```

### 8.4 세션 관리 및 자동 저장

#### 세션 생명주기
```python
# 세션 생성 (자동)
session_id = f"{user_id}_{datetime.now().strftime('%Y%m%d')}"

# 세션 타임아웃 설정
session_timeout = timedelta(hours=2)  # 2시간 무활동 시 만료

# 자동 저장 간격
auto_save_interval = 300  # 5분마다 버퍼 저장
```

#### 자동 저장 시스템 (백그라운드 스레드)
```python
def _auto_save_worker(self):
    """
    5분마다 실행되는 자동 저장 워커
    1. 모든 버퍼 데이터를 JSONL 파일로 저장
    2. 만료된 세션을 세션 파일로 저장 후 제거
    3. 품질 메트릭 업데이트
    """
    while self.is_running:
        time.sleep(self.auto_save_interval)  # 300초 대기
        self._flush_all_buffers()            # 버퍼 저장
        self._cleanup_old_sessions()         # 세션 정리
```

#### 세션 종료 처리
```python
def _save_session(self, session: CollectionSession):
    """
    세션 데이터를 JSON 파일로 저장
    
    저장 구조:
    {
        "session_id": "user123_20240315",
        "user_id": "user123", 
        "start_time": "2024-03-15T14:30:00",
        "end_time": "2024-03-15T14:35:00",
        "data_points_count": 12,
        "status": "completed",
        "data_points": [
            // 세션의 모든 데이터 포인트들
        ]
    }
    """
```

#### 데이터 완성도 점수 계산
```python
def get_data_completeness_score(self, user_id: str) -> float:
    """
    사용자 데이터 완성도 계산 (0.0 ~ 1.0)
    
    평가 기준:
    - NLU Features: 최소 5개 필요 (25%)
    - Interactions: 최소 3개 필요 (25%) 
    - Recommendations: 최소 2개 필요 (25%)
    - Feedback: 최소 1개 필요 (25%)
    
    각 항목별로 요구사항 대비 비율을 계산하여 평균
    """
```

### 8.5 학습 파이프라인 연동 (scripts/train_from_collected_data.py)

#### 실제 구현된 파이프라인
```bash
# 학습 파이프라인 실행
python scripts/train_from_collected_data.py --data-dir output/learning_data

# 평가만 실행 (학습 스킵)
python scripts/train_from_collected_data.py --skip-training

# 품질 임계값 설정
python scripts/train_from_collected_data.py --min-quality 0.7
```

#### 파이프라인 처리 단계
```python
class TrainingPipeline:
    def run_pipeline(self, skip_training: bool = False) -> Dict[str, Any]:
        """
        1. 데이터 준비: LearningDataCollector에서 데이터 내보내기
        2. 품질 필터링: min_quality_score 이상만 선별
        3. 데이터 분할: Stratified sampling (70:20:10)
        4. 현재 모델 평가: NLU 정확도 및 신뢰도 측정
        5. 새 모델 학습: 패턴 업데이트 및 키워드 추출
        6. 성능 비교: 개선도 계산
        """
```

#### 데이터 익스포트 기능
```python
def export_training_data(self, output_path: str, format: str = "jsonl", days: int = 30) -> bool:
    """
    학습용 데이터 익스포트
    
    지원 형식:
    - JSONL: 각 데이터 포인트를 한 줄씩 JSON으로
    - JSON: 전체 데이터를 하나의 JSON 배열로
    - CSV: 플랫한 구조로 변환하여 CSV로
    
    필터링:
    - 최근 N일간 데이터만
    - 품질 점수 기준 필터링
    - 데이터 타입별 분류
    """
```

#### 성능 추적 (파일 기반)
```json
// pipeline_results_20240315_143000.json
{
  "timestamp": "20240315_143000",
  "results": {
    "status": "completed",
    "current_performance": {
      "accuracy": 0.85,
      "avg_confidence": 0.78,
      "total_samples": 150,
      "correct_predictions": 128
    },
    "new_performance": {
      "accuracy": 0.87,
      "avg_confidence": 0.81,
      "total_samples": 150, 
      "correct_predictions": 130
    },
    "improvement": 0.02,
    "data_stats": {
      "train": 105,
      "val": 30,
      "test": 15
    }
  }
}
```

### 8.6 데이터 프라이버시

#### 자동 익명화
- 정규식 기반 개인정보 마스킹
- 이름: [NAME]
- 전화번호: [PHONE]
- 주소: [ADDRESS]
- 카드번호: [CARD]

---

## 9. 자가 학습 시스템 데이터베이스 설계

### 9.1 개요
나비얌 챗봇은 사용자와의 상호작용을 통해 생성된 데이터로 자기 자신을 개선합니다. NLU(자연어 이해), RAG(검색 증강 생성), 추천 엔진 세 가지 핵심 컴포넌트가 각각 학습 데이터를 활용하여 성능을 향상시킵니다.

### 9.2 자가 학습 스키마 생성
```sql
-- 머신러닝 학습 데이터 전용 스키마
CREATE SCHEMA IF NOT EXISTS ml_training;
COMMENT ON SCHEMA ml_training IS '자가 학습 시스템을 위한 데이터 저장 및 관리';

-- 권한 설정
GRANT ALL PRIVILEGES ON SCHEMA ml_training TO ml_user;
GRANT USAGE ON SCHEMA ml_training TO app_user;
```

### 9.3 학습 데이터 큐 테이블 (ml_training.data_queue)
```sql
CREATE TABLE ml_training.data_queue (
    id BIGSERIAL PRIMARY KEY,
    
    -- 모델 분류
    model_type VARCHAR(50) NOT NULL CHECK (model_type IN (
        'nlu',           -- 자연어 이해 모델
        'rag',           -- RAG 검색 모델
        'recommendation' -- 추천 엔진 모델
    )),
    
    -- 데이터
    raw_data JSONB NOT NULL,        -- 원본 데이터 (처리 전)
    processed_data JSONB,            -- 전처리된 데이터 (학습 준비 완료)
    
    -- 품질 관리
    quality_score DECIMAL(4,3) CHECK (quality_score >= 0 AND quality_score <= 1),
    -- 0.000 ~ 1.000 범위의 품질 점수
    -- NLU: 신뢰도 기반 (0.8 이상 고품질)
    -- RAG: 검색 정확도 기반
    -- Recommendation: 사용자 선택 여부 기반
    
    validation_errors JSONB,         -- 검증 오류 상세 정보
    /* 예시:
    {
        "missing_fields": ["intent", "entities"],
        "invalid_format": ["timestamp"],
        "quality_issues": ["low_confidence"]
    }
    */
    
    -- 상태 관리
    status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (status IN (
        'pending',      -- 대기 중
        'processing',   -- 처리 중
        'ready',        -- 학습 준비 완료
        'training',     -- 학습 중
        'completed',    -- 완료
        'rejected',     -- 품질 미달로 거부
        'error'         -- 오류 발생
    )),
    
    error_message TEXT,              -- 오류 발생 시 상세 메시지
    retry_count INTEGER DEFAULT 0,   -- 재시도 횟수
    
    -- 메타데이터
    source_table VARCHAR(100),       -- 데이터 출처 테이블 (conversations, recommendations_log 등)
    source_id BIGINT,                -- 원본 레코드 ID
    user_id INTEGER REFERENCES chatbot.users(id),  -- 데이터 생성 사용자
    session_id UUID,                 -- 세션 식별자
    
    -- 시간 정보
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP WITH TIME ZONE,  -- 전처리 완료 시간
    trained_at TIMESTAMP WITH TIME ZONE,    -- 학습 완료 시간
    
    -- 우선순위 (높을수록 먼저 처리)
    priority INTEGER DEFAULT 0 CHECK (priority >= 0 AND priority <= 100),
    
    CONSTRAINT data_queue_raw_data_not_empty CHECK (jsonb_array_length(raw_data) > 0 OR jsonb_typeof(raw_data) = 'object')
);

-- 인덱스
CREATE INDEX idx_ml_queue_status_priority ON ml_training.data_queue(status, priority DESC) 
    WHERE status IN ('pending', 'ready');
CREATE INDEX idx_ml_queue_model_type ON ml_training.data_queue(model_type, status);
CREATE INDEX idx_ml_queue_created_at ON ml_training.data_queue(created_at DESC);
CREATE INDEX idx_ml_queue_quality ON ml_training.data_queue(quality_score DESC) 
    WHERE quality_score > 0.5;

-- 트리거: processed_at 자동 업데이트
CREATE TRIGGER update_ml_queue_processed_at 
    BEFORE UPDATE ON ml_training.data_queue
    FOR EACH ROW 
    WHEN (OLD.status != 'ready' AND NEW.status = 'ready')
    EXECUTE FUNCTION update_updated_at_column();

COMMENT ON TABLE ml_training.data_queue IS '모든 자가 학습 데이터의 대기열. 품질 검증 후 각 모델별 학습에 사용';
```

### 9.4 학습 작업 관리 테이블 (ml_training.training_jobs)
```sql
CREATE TABLE ml_training.training_jobs (
    id SERIAL PRIMARY KEY,
    
    -- 작업 정보
    job_name VARCHAR(200) NOT NULL,  -- 작업명 (예: 'nlu_daily_training_20240315')
    model_type VARCHAR(50) NOT NULL CHECK (model_type IN ('nlu', 'rag', 'recommendation')),
    model_version VARCHAR(50),        -- 학습할 모델 버전 (예: 'v1.2.3')
    
    -- 학습 설정
    training_config JSONB NOT NULL,   -- 학습 하이퍼파라미터 및 설정
    /* 예시:
    {
        "epochs": 10,
        "batch_size": 32,
        "learning_rate": 0.001,
        "validation_split": 0.2,
        "early_stopping": true,
        "max_samples": 10000
    }
    */
    
    -- 데이터 정보
    data_count INTEGER NOT NULL,      -- 총 학습 데이터 개수
    train_count INTEGER,              -- 훈련 세트 크기
    validation_count INTEGER,         -- 검증 세트 크기
    test_count INTEGER,               -- 테스트 세트 크기
    
    -- 시간 정보
    scheduled_at TIMESTAMP WITH TIME ZONE,   -- 예약 시간
    start_time TIMESTAMP WITH TIME ZONE,     -- 실제 시작 시간
    end_time TIMESTAMP WITH TIME ZONE,       -- 종료 시간
    duration_seconds INTEGER GENERATED ALWAYS AS (
        EXTRACT(EPOCH FROM (end_time - start_time))
    ) STORED,  -- 소요 시간 (초)
    
    -- 상태
    status VARCHAR(20) NOT NULL DEFAULT 'scheduled' CHECK (status IN (
        'scheduled',    -- 예약됨
        'queued',       -- 대기열
        'preparing',    -- 데이터 준비 중
        'training',     -- 학습 중
        'evaluating',   -- 평가 중
        'completed',    -- 완료
        'failed',       -- 실패
        'cancelled'     -- 취소됨
    )),
    
    -- 학습 결과
    metrics JSONB,                    -- 학습 메트릭
    /* 예시:
    {
        "accuracy": 0.92,
        "precision": 0.89,
        "recall": 0.91,
        "f1_score": 0.90,
        "loss": 0.23,
        "val_accuracy": 0.88,
        "val_loss": 0.31,
        "confusion_matrix": [[...], [...]],
        "per_class_metrics": {...}
    }
    */
    
    improvement_rate DECIMAL(5,4),    -- 이전 모델 대비 개선율 (-1.0000 ~ 1.0000)
    
    -- 모델 저장 정보
    model_path TEXT,                  -- 학습된 모델 파일 경로 (S3/로컬)
    model_size_mb DECIMAL(10,2),      -- 모델 파일 크기 (MB)
    checkpoint_path TEXT,             -- 체크포인트 경로
    
    -- 로그 및 오류
    log_path TEXT,                    -- 학습 로그 파일 경로
    error_message TEXT,               -- 오류 메시지
    warnings JSONB,                   -- 경고 메시지 목록
    
    -- 메타데이터
    created_by VARCHAR(100) DEFAULT 'system',  -- 작업 생성자
    triggered_by VARCHAR(50) CHECK (triggered_by IN (
        'scheduled',    -- 정기 스케줄
        'manual',       -- 수동 실행
        'threshold',    -- 데이터량 임계값 도달
        'performance'   -- 성능 저하 감지
    )),
    
    CONSTRAINT training_jobs_data_counts CHECK (
        train_count + validation_count + test_count <= data_count
    )
);

-- 인덱스
CREATE INDEX idx_training_jobs_status ON ml_training.training_jobs(status, scheduled_at);
CREATE INDEX idx_training_jobs_model_type ON ml_training.training_jobs(model_type, start_time DESC);
CREATE INDEX idx_training_jobs_metrics ON ml_training.training_jobs USING GIN(metrics);

COMMENT ON TABLE ml_training.training_jobs IS '모델 학습 작업 관리. 각 학습의 설정, 진행 상황, 결과를 추적';
```

### 9.5 모델 버전 관리 테이블 (ml_training.model_versions)
```sql
CREATE TABLE ml_training.model_versions (
    id SERIAL PRIMARY KEY,
    
    -- 모델 식별
    model_type VARCHAR(50) NOT NULL CHECK (model_type IN ('nlu', 'rag', 'recommendation')),
    version VARCHAR(20) NOT NULL,     -- Semantic Versioning (예: '1.2.3')
    version_name VARCHAR(100),        -- 버전 별칭 (예: 'spring_2024_update')
    
    -- 모델 정보
    base_model VARCHAR(100),          -- 기반 모델 (예: 'koalpaca-5.8b', 'sentence-bert')
    architecture JSONB,               -- 모델 아키텍처 상세
    /* 예시:
    {
        "type": "transformer",
        "layers": 12,
        "hidden_size": 768,
        "attention_heads": 12,
        "vocab_size": 32000,
        "custom_layers": ["intent_classifier", "entity_extractor"]
    }
    */
    
    -- 학습 정보
    training_job_id INTEGER REFERENCES ml_training.training_jobs(id),
    training_data_stats JSONB,        -- 학습 데이터 통계
    /* 예시:
    {
        "total_samples": 50000,
        "intent_distribution": {
            "FOOD_REQUEST": 15000,
            "BUDGET_INQUIRY": 8000,
            "LOCATION_INQUIRY": 7000
        },
        "avg_text_length": 45.3,
        "vocabulary_size": 8500
    }
    */
    
    -- 성능 메트릭
    performance_metrics JSONB NOT NULL,  -- 성능 지표
    /* 예시:
    {
        "test_accuracy": 0.92,
        "test_f1_score": 0.90,
        "inference_time_ms": 45,
        "memory_usage_mb": 512,
        "daily_request_capacity": 100000
    }
    */
    
    benchmark_results JSONB,          -- 벤치마크 결과
    /* 예시:
    {
        "standard_benchmarks": {
            "klue_nli": 0.87,
            "klue_ner": 0.91
        },
        "custom_benchmarks": {
            "food_intent_accuracy": 0.94,
            "budget_extraction_accuracy": 0.89
        }
    }
    */
    
    -- 배포 정보
    is_active BOOLEAN DEFAULT FALSE,  -- 현재 운영 중인 모델인지
    deployment_status VARCHAR(20) CHECK (deployment_status IN (
        'development',  -- 개발 중
        'testing',      -- 테스트 중
        'staging',      -- 스테이징
        'production',   -- 운영 중
        'deprecated',   -- 사용 중단
        'archived'      -- 보관
    )),
    
    -- 파일 정보
    model_path TEXT NOT NULL,         -- 모델 파일 경로
    model_size_mb DECIMAL(10,2),      -- 모델 크기 (MB)
    checksum VARCHAR(64),             -- 파일 체크섬 (SHA256)
    
    -- A/B 테스트
    ab_test_group VARCHAR(10),        -- A/B 테스트 그룹 (A, B, C...)
    traffic_percentage DECIMAL(5,2) DEFAULT 0.00,  -- 트래픽 할당 비율 (0.00 ~ 100.00)
    
    -- 메타데이터
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100) DEFAULT 'system',
    deployed_at TIMESTAMP WITH TIME ZONE,  -- 운영 배포 시간
    retired_at TIMESTAMP WITH TIME ZONE,   -- 사용 중단 시간
    
    notes TEXT,                       -- 버전 설명 및 주요 변경사항
    
    CONSTRAINT model_versions_unique_version UNIQUE (model_type, version),
    CONSTRAINT model_versions_traffic_check CHECK (
        traffic_percentage >= 0 AND traffic_percentage <= 100
    )
);

-- 인덱스
CREATE INDEX idx_model_versions_active ON ml_training.model_versions(model_type, is_active) 
    WHERE is_active = TRUE;
CREATE INDEX idx_model_versions_deployment ON ml_training.model_versions(deployment_status);
CREATE INDEX idx_model_versions_performance ON ml_training.model_versions 
    USING GIN(performance_metrics);

-- 트리거: 활성 모델은 model_type별로 하나만
CREATE OR REPLACE FUNCTION ensure_single_active_model()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.is_active = TRUE THEN
        UPDATE ml_training.model_versions 
        SET is_active = FALSE 
        WHERE model_type = NEW.model_type 
          AND id != NEW.id 
          AND is_active = TRUE;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER ensure_single_active_model_trigger
    BEFORE INSERT OR UPDATE ON ml_training.model_versions
    FOR EACH ROW
    WHEN (NEW.is_active = TRUE)
    EXECUTE FUNCTION ensure_single_active_model();

COMMENT ON TABLE ml_training.model_versions IS '모든 모델의 버전 관리. 성능, 배포 상태, A/B 테스트 정보 포함';
```

### 9.6 성능 추적 테이블 (ml_training.performance_metrics)
```sql
CREATE TABLE ml_training.performance_metrics (
    id BIGSERIAL PRIMARY KEY,
    
    -- 모델 정보
    model_type VARCHAR(50) NOT NULL,
    model_version_id INTEGER REFERENCES ml_training.model_versions(id),
    
    -- 측정 시점
    measured_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    measurement_window_minutes INTEGER DEFAULT 60,  -- 측정 시간 범위 (분)
    
    -- 실시간 성능 지표
    request_count BIGINT NOT NULL,    -- 총 요청 수
    success_count BIGINT NOT NULL,    -- 성공 처리 수
    error_count BIGINT NOT NULL DEFAULT 0,  -- 오류 수
    
    success_rate DECIMAL(5,4) GENERATED ALWAYS AS (
        CASE WHEN request_count > 0 
        THEN success_count::DECIMAL / request_count 
        ELSE 0 END
    ) STORED,  -- 성공률 (0.0000 ~ 1.0000)
    
    -- 응답 시간 통계 (밀리초)
    avg_response_time_ms DECIMAL(10,2),
    min_response_time_ms INTEGER,
    max_response_time_ms INTEGER,
    p50_response_time_ms INTEGER,     -- 중위수
    p95_response_time_ms INTEGER,     -- 95 백분위수
    p99_response_time_ms INTEGER,     -- 99 백분위수
    
    -- 모델별 특화 지표
    model_specific_metrics JSONB,
    /* NLU 예시:
    {
        "intent_accuracy": 0.91,
        "entity_f1_score": 0.88,
        "avg_confidence": 0.85,
        "low_confidence_ratio": 0.12,
        "unknown_intent_ratio": 0.08
    }
    
    RAG 예시:
    {
        "retrieval_accuracy": 0.87,
        "avg_relevance_score": 0.82,
        "cache_hit_rate": 0.65,
        "avg_documents_retrieved": 5.2,
        "embedding_time_ms": 23
    }
    
    Recommendation 예시:
    {
        "click_through_rate": 0.24,
        "conversion_rate": 0.18,
        "avg_recommendations": 4.5,
        "diversity_score": 0.73,
        "personalization_score": 0.81
    }
    */
    
    -- 리소스 사용량
    cpu_usage_percent DECIMAL(5,2),   -- CPU 사용률 (0.00 ~ 100.00)
    memory_usage_mb DECIMAL(10,2),    -- 메모리 사용량 (MB)
    gpu_usage_percent DECIMAL(5,2),   -- GPU 사용률 (선택적)
    
    -- 비즈니스 영향도
    user_satisfaction_score DECIMAL(3,2),  -- 사용자 만족도 (0.00 ~ 5.00)
    business_value_score DECIMAL(10,2),    -- 비즈니스 가치 점수
    
    CONSTRAINT performance_metrics_counts CHECK (
        success_count <= request_count AND
        error_count <= request_count
    )
);

-- 인덱스
CREATE INDEX idx_performance_metrics_model ON ml_training.performance_metrics(
    model_type, model_version_id, measured_at DESC
);
CREATE INDEX idx_performance_metrics_time ON ml_training.performance_metrics(measured_at DESC);
CREATE INDEX idx_performance_metrics_performance ON ml_training.performance_metrics(
    success_rate DESC, avg_response_time_ms
);

-- 파티셔닝 (월별)
CREATE TABLE ml_training.performance_metrics_2024_01 
    PARTITION OF ml_training.performance_metrics
    FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');

COMMENT ON TABLE ml_training.performance_metrics IS '모델별 실시간 성능 추적. 운영 중인 모델의 품질 모니터링';
```

### 9.7 NLU 학습 데이터 테이블 (ml_training.nlu_training_data)
```sql
CREATE TABLE ml_training.nlu_training_data (
    id BIGSERIAL PRIMARY KEY,
    
    -- 원본 참조
    conversation_id BIGINT REFERENCES chatbot.conversations(id),
    data_queue_id BIGINT REFERENCES ml_training.data_queue(id),
    
    -- 입력 데이터
    input_text TEXT NOT NULL,         -- 사용자 입력 원문
    normalized_text TEXT,             -- 정규화된 텍스트
    
    -- 레이블 (정답)
    true_intent VARCHAR(50) NOT NULL CHECK (true_intent IN (
        'FOOD_REQUEST', 'BUDGET_INQUIRY', 'COUPON_INQUIRY', 
        'LOCATION_INQUIRY', 'TIME_INQUIRY', 'GENERAL_CHAT',
        'MENU_OPTION', 'EMERGENCY_FOOD', 'GROUP_DINING', 
        'BALANCE_CHECK', 'BALANCE_CHARGE', 'UNKNOWN'
    )),
    
    true_entities JSONB,              -- 정답 엔티티
    /* 예시:
    {
        "food_type": ["치킨", "피자"],
        "budget": 10000,
        "location": "강남역",
        "companions": ["친구", "2명"],
        "time": "저녁"
    }
    */
    
    -- 모델 예측 (학습 시점)
    predicted_intent VARCHAR(50),
    predicted_entities JSONB,
    prediction_confidence DECIMAL(4,3),
    
    -- 레이블 출처
    label_source VARCHAR(50) CHECK (label_source IN (
        'auto',         -- 자동 레이블링
        'manual',       -- 수동 레이블링
        'verified',     -- 검증됨
        'corrected',    -- 수정됨
        'weak'          -- 약한 레이블 (신뢰도 낮음)
    )),
    
    labeler_id VARCHAR(100),          -- 레이블링한 사람/시스템
    
    -- 품질 지표
    text_quality_score DECIMAL(4,3),  -- 텍스트 품질 (0.000 ~ 1.000)
    label_confidence DECIMAL(4,3),    -- 레이블 신뢰도 (0.000 ~ 1.000)
    
    -- 특징 (Features)
    text_features JSONB,              -- 추출된 텍스트 특징
    /* 예시:
    {
        "length": 45,
        "word_count": 8,
        "has_question": true,
        "has_price": true,
        "sentiment": "positive",
        "formality": 0.3
    }
    */
    
    -- 학습 상태
    is_used_for_training BOOLEAN DEFAULT FALSE,  -- 학습에 사용되었는지
    training_job_ids INTEGER[],       -- 사용된 학습 작업 ID들
    
    -- 메타데이터
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- 데이터 증강
    is_augmented BOOLEAN DEFAULT FALSE,  -- 증강된 데이터인지
    augmentation_method VARCHAR(50),     -- 증강 방법 (synonym, paraphrase, noise)
    original_data_id BIGINT REFERENCES ml_training.nlu_training_data(id)  -- 원본 데이터 ID
);

-- 인덱스
CREATE INDEX idx_nlu_training_intent ON ml_training.nlu_training_data(true_intent);
CREATE INDEX idx_nlu_training_quality ON ml_training.nlu_training_data(
    text_quality_score DESC, label_confidence DESC
) WHERE text_quality_score > 0.5;
CREATE INDEX idx_nlu_training_unused ON ml_training.nlu_training_data(is_used_for_training) 
    WHERE is_used_for_training = FALSE;
CREATE INDEX idx_nlu_training_entities ON ml_training.nlu_training_data USING GIN(true_entities);

-- 트리거
CREATE TRIGGER update_nlu_training_updated_at 
    BEFORE UPDATE ON ml_training.nlu_training_data
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

COMMENT ON TABLE ml_training.nlu_training_data IS 'NLU 모델 학습용 데이터. 의도 분류와 엔티티 추출 학습에 사용';
```

### 9.8 RAG 임베딩 학습 테이블 (ml_training.rag_embeddings_queue)
```sql
CREATE TABLE ml_training.rag_embeddings_queue (
    id BIGSERIAL PRIMARY KEY,
    
    -- 문서 정보
    document_id VARCHAR(100) NOT NULL,  -- 문서 고유 ID (shop_123, menu_456)
    document_type VARCHAR(50) NOT NULL CHECK (document_type IN (
        'shop',         -- 가게 정보
        'menu',         -- 메뉴 정보
        'review',       -- 리뷰
        'faq',          -- 자주 묻는 질문
        'notice'        -- 공지사항
    )),
    
    -- 콘텐츠
    title VARCHAR(500),               -- 문서 제목
    content TEXT NOT NULL,            -- 문서 내용
    metadata JSONB,                   -- 추가 메타데이터
    /* 예시:
    {
        "shop_id": 123,
        "category": "한식",
        "tags": ["김치찌개", "된장찌개", "가성비"],
        "last_updated": "2024-03-15",
        "popularity_score": 0.85
    }
    */
    
    -- 임베딩 정보
    embedding_model VARCHAR(100),     -- 사용된 임베딩 모델
    embedding_vector REAL[],          -- 임베딩 벡터 (차원은 모델에 따라 다름)
    embedding_dimension INTEGER,      -- 벡터 차원 수
    
    -- 검색 성능 추적
    search_count INTEGER DEFAULT 0,   -- 검색된 횟수
    click_count INTEGER DEFAULT 0,    -- 클릭된 횟수
    relevance_score DECIMAL(4,3),    -- 평균 관련성 점수 (0.000 ~ 1.000)
    
    -- 피드백 기반 품질
    positive_feedback INTEGER DEFAULT 0,  -- 긍정 피드백 수
    negative_feedback INTEGER DEFAULT 0,  -- 부정 피드백 수
    quality_score DECIMAL(4,3) GENERATED ALWAYS AS (
        CASE 
            WHEN (positive_feedback + negative_feedback) > 0
            THEN positive_feedback::DECIMAL / (positive_feedback + negative_feedback)
            ELSE 0.5
        END
    ) STORED,  -- 품질 점수 (0.000 ~ 1.000)
    
    -- 재학습 필요성
    needs_reembedding BOOLEAN DEFAULT FALSE,  -- 재임베딩 필요 여부
    reembedding_reason VARCHAR(100),          -- 재임베딩 이유
    last_embedded_at TIMESTAMP WITH TIME ZONE,  -- 마지막 임베딩 시간
    
    -- 상태
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN (
        'active',       -- 활성
        'pending',      -- 임베딩 대기
        'processing',   -- 처리 중
        'inactive',     -- 비활성
        'error'         -- 오류
    )),
    
    -- 메타데이터
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT rag_embeddings_vector_dimension CHECK (
        array_length(embedding_vector, 1) = embedding_dimension
    )
);

-- 인덱스
CREATE INDEX idx_rag_embeddings_document ON ml_training.rag_embeddings_queue(
    document_type, document_id
);
CREATE INDEX idx_rag_embeddings_quality ON ml_training.rag_embeddings_queue(
    quality_score DESC
) WHERE status = 'active';
CREATE INDEX idx_rag_embeddings_reembedding ON ml_training.rag_embeddings_queue(
    needs_reembedding
) WHERE needs_reembedding = TRUE;

-- 벡터 검색을 위한 인덱스 (pgvector extension 필요)
-- CREATE INDEX idx_rag_embeddings_vector ON ml_training.rag_embeddings_queue 
-- USING ivfflat (embedding_vector vector_cosine_ops);

-- 트리거
CREATE TRIGGER update_rag_embeddings_updated_at 
    BEFORE UPDATE ON ml_training.rag_embeddings_queue
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

COMMENT ON TABLE ml_training.rag_embeddings_queue IS 'RAG 시스템의 문서 임베딩 관리. 검색 품질 향상을 위한 재학습 큐';
```

### 9.9 추천 엔진 학습 데이터 테이블 (ml_training.recommendation_feedback)
```sql
CREATE TABLE ml_training.recommendation_feedback (
    id BIGSERIAL PRIMARY KEY,
    
    -- 추천 컨텍스트
    recommendation_log_id BIGINT REFERENCES chatbot.recommendations_log(id),
    user_id INTEGER NOT NULL REFERENCES chatbot.users(id),
    session_id UUID NOT NULL,
    
    -- 추천된 항목들
    recommended_shops JSONB NOT NULL,  -- 추천된 가게 목록
    /* 예시:
    [{
        "shop_id": 123,
        "rank": 1,
        "score": 0.95,
        "reason_codes": ["BUDGET_FIT", "NEARBY", "POPULAR"]
    }, {
        "shop_id": 456,
        "rank": 2,
        "score": 0.87,
        "reason_codes": ["USER_PREFERENCE", "HIGH_QUALITY"]
    }]
    */
    
    -- 사용자 행동
    user_action VARCHAR(50) NOT NULL CHECK (user_action IN (
        'viewed',       -- 조회만 함
        'clicked',      -- 클릭함
        'selected',     -- 선택함
        'ignored',      -- 무시함
        'scrolled_past' -- 스크롤해서 지나감
    )),
    
    selected_shop_id INTEGER REFERENCES chatbot.shops(id),  -- 최종 선택한 가게
    action_timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    time_to_action_ms INTEGER,        -- 추천 후 행동까지 시간 (밀리초)
    
    -- 상호작용 상세
    interaction_details JSONB,        -- 상세 상호작용 정보
    /* 예시:
    {
        "viewed_shops": [123, 456],
        "view_duration_ms": {
            "123": 5000,
            "456": 3000
        },
        "scroll_depth": 0.75,
        "clicks": [{
            "shop_id": 123,
            "element": "menu_button",
            "timestamp": "2024-03-15T14:30:00Z"
        }]
    }
    */
    
    -- 컨텍스트 특징
    context_features JSONB NOT NULL,   -- 추천 시점의 컨텍스트
    /* 예시:
    {
        "time_of_day": "lunch",
        "day_of_week": "friday",
        "weather": "sunny",
        "location": {"lat": 37.5665, "lng": 126.9780},
        "user_state": "hungry",
        "budget": 10000,
        "companions": 2
    }
    */
    
    -- 사용자 특징 (추천 시점)
    user_features JSONB NOT NULL,      -- 사용자 프로필 특징
    /* 예시:
    {
        "preferred_categories": ["한식", "중식"],
        "avg_budget": 12000,
        "total_orders": 45,
        "loyalty_score": 0.73,
        "price_sensitivity": 0.6
    }
    */
    
    -- 피드백
    explicit_rating INTEGER CHECK (explicit_rating >= 1 AND explicit_rating <= 5),  -- 명시적 평점
    implicit_satisfaction DECIMAL(4,3),  -- 암묵적 만족도 (0.000 ~ 1.000)
    -- 계산 방법: 선택 여부, 조회 시간, 재방문 등을 종합
    
    -- 학습 가치
    learning_value DECIMAL(4,3),      -- 학습 가치 점수 (0.000 ~ 1.000)
    -- 높을수록 모델 개선에 도움이 되는 데이터
    
    is_outlier BOOLEAN DEFAULT FALSE,  -- 이상치 여부
    
    -- 메타데이터
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    device_type VARCHAR(50),          -- 기기 유형 (mobile, desktop, app)
    app_version VARCHAR(20),          -- 앱 버전
    
    CONSTRAINT recommendation_feedback_action_consistency CHECK (
        (user_action = 'selected' AND selected_shop_id IS NOT NULL) OR
        (user_action != 'selected' AND selected_shop_id IS NULL)
    )
);

-- 인덱스
CREATE INDEX idx_recommendation_feedback_user ON ml_training.recommendation_feedback(
    user_id, created_at DESC
);
CREATE INDEX idx_recommendation_feedback_action ON ml_training.recommendation_feedback(
    user_action, selected_shop_id
);
CREATE INDEX idx_recommendation_feedback_learning ON ml_training.recommendation_feedback(
    learning_value DESC
) WHERE learning_value > 0.5;
CREATE INDEX idx_recommendation_feedback_features ON ml_training.recommendation_feedback 
    USING GIN(context_features, user_features);

COMMENT ON TABLE ml_training.recommendation_feedback IS '추천 엔진 학습을 위한 사용자 피드백 데이터. Wide&Deep 모델 개선에 사용';
```

### 9.10 자동 학습 데이터 수집 트리거
```sql
-- 1. NLU 학습 데이터 자동 수집
CREATE OR REPLACE FUNCTION collect_nlu_training_data()
RETURNS TRIGGER AS $$
BEGIN
    -- 높은 신뢰도의 대화만 수집
    IF NEW.intent_confidence > 0.7 THEN
        INSERT INTO ml_training.data_queue (
            model_type, 
            raw_data, 
            quality_score,
            source_table,
            source_id,
            user_id,
            session_id
        ) VALUES (
            'nlu',
            jsonb_build_object(
                'input_text', NEW.input_text,
                'intent', NEW.extracted_intent,
                'entities', NEW.extracted_entities,
                'confidence', NEW.intent_confidence
            ),
            NEW.intent_confidence,
            'conversations',
            NEW.id,
            NEW.user_id,
            NEW.session_id
        );
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_collect_nlu_data
    AFTER INSERT ON chatbot.conversations
    FOR EACH ROW
    EXECUTE FUNCTION collect_nlu_training_data();

-- 2. 추천 피드백 자동 수집
CREATE OR REPLACE FUNCTION collect_recommendation_feedback()
RETURNS TRIGGER AS $$
BEGIN
    -- 사용자가 최종 선택을 한 경우만 수집
    IF NEW.user_final_selection IS NOT NULL AND OLD.user_final_selection IS NULL THEN
        INSERT INTO ml_training.data_queue (
            model_type,
            raw_data,
            quality_score,
            source_table,
            source_id,
            user_id,
            session_id
        ) VALUES (
            'recommendation',
            jsonb_build_object(
                'recommendations', NEW.recommendations,
                'user_selection', NEW.user_final_selection,
                'time_to_decision', NEW.time_to_decision_ms,
                'context', NEW.request_entities
            ),
            CASE 
                WHEN NEW.time_to_decision_ms < 5000 THEN 0.9
                WHEN NEW.time_to_decision_ms < 30000 THEN 0.7
                ELSE 0.5
            END,
            'recommendations_log',
            NEW.id,
            NEW.user_id,
            NEW.session_id
        );
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_collect_recommendation_feedback
    AFTER UPDATE ON chatbot.recommendations_log
    FOR EACH ROW
    WHEN (OLD.user_final_selection IS NULL AND NEW.user_final_selection IS NOT NULL)
    EXECUTE FUNCTION collect_recommendation_feedback();
```

### 9.11 학습 데이터 처리 뷰
```sql
-- 1. NLU 학습 준비 데이터 뷰
CREATE VIEW ml_training.v_nlu_ready_for_training AS
SELECT 
    ntd.id,
    ntd.input_text,
    ntd.true_intent,
    ntd.true_entities,
    ntd.text_quality_score * ntd.label_confidence AS overall_quality,
    COUNT(*) OVER (PARTITION BY ntd.true_intent) AS intent_count
FROM ml_training.nlu_training_data ntd
WHERE ntd.is_used_for_training = FALSE
  AND ntd.text_quality_score > 0.6
  AND ntd.label_confidence > 0.7
  AND ntd.label_source IN ('verified', 'corrected', 'manual')
ORDER BY overall_quality DESC;

-- 2. 추천 모델 학습 데이터 뷰
CREATE VIEW ml_training.v_recommendation_training_data AS
SELECT 
    rf.id,
    rf.user_id,
    rf.recommended_shops,
    rf.selected_shop_id,
    rf.user_action,
    rf.context_features,
    rf.user_features,
    rf.implicit_satisfaction,
    rf.learning_value,
    CASE 
        WHEN rf.user_action = 'selected' THEN 1.0
        WHEN rf.user_action = 'clicked' THEN 0.5
        ELSE 0.0
    END AS reward
FROM ml_training.recommendation_feedback rf
WHERE rf.is_outlier = FALSE
  AND rf.learning_value > 0.5
ORDER BY rf.created_at DESC;

-- 3. 모델 성능 대시보드 뷰
CREATE VIEW ml_training.v_model_performance_dashboard AS
SELECT 
    mv.model_type,
    mv.version,
    mv.is_active,
    pm.measured_at,
    pm.request_count,
    pm.success_rate,
    pm.avg_response_time_ms,
    pm.model_specific_metrics,
    mv.traffic_percentage
FROM ml_training.model_versions mv
LEFT JOIN ml_training.performance_metrics pm 
    ON mv.id = pm.model_version_id
WHERE pm.measured_at > CURRENT_TIMESTAMP - INTERVAL '24 hours'
ORDER BY mv.model_type, pm.measured_at DESC;
```

### 9.12 자동 학습 스케줄링 함수
```sql
-- 일일 자동 학습 데이터 준비
CREATE OR REPLACE FUNCTION ml_training.prepare_daily_training_data()
RETURNS TABLE(model_type VARCHAR, data_count INTEGER, avg_quality DECIMAL) AS $$
BEGIN
    -- NLU 데이터 준비
    UPDATE ml_training.data_queue
    SET status = 'ready',
        processed_at = CURRENT_TIMESTAMP
    WHERE model_type = 'nlu'
      AND status = 'pending'
      AND quality_score > 0.6
      AND created_at > CURRENT_TIMESTAMP - INTERVAL '1 day';
    
    -- 추천 데이터 준비
    UPDATE ml_training.data_queue
    SET status = 'ready',
        processed_at = CURRENT_TIMESTAMP
    WHERE model_type = 'recommendation'
      AND status = 'pending'
      AND quality_score > 0.5
      AND created_at > CURRENT_TIMESTAMP - INTERVAL '1 day';
    
    -- 결과 반환
    RETURN QUERY
    SELECT 
        dq.model_type,
        COUNT(*)::INTEGER as data_count,
        AVG(dq.quality_score)::DECIMAL(4,3) as avg_quality
    FROM ml_training.data_queue dq
    WHERE dq.status = 'ready'
      AND dq.processed_at > CURRENT_TIMESTAMP - INTERVAL '1 hour'
    GROUP BY dq.model_type;
END;
$$ LANGUAGE plpgsql;

-- 학습 작업 생성 함수
CREATE OR REPLACE FUNCTION ml_training.create_training_job(
    p_model_type VARCHAR,
    p_training_config JSONB
) RETURNS INTEGER AS $$
DECLARE
    v_job_id INTEGER;
    v_data_count INTEGER;
BEGIN
    -- 준비된 데이터 개수 확인
    SELECT COUNT(*) INTO v_data_count
    FROM ml_training.data_queue
    WHERE model_type = p_model_type
      AND status = 'ready';
    
    -- 최소 데이터 개수 확인 (모델별로 다름)
    IF (p_model_type = 'nlu' AND v_data_count < 100) OR
       (p_model_type = 'recommendation' AND v_data_count < 500) OR
       (p_model_type = 'rag' AND v_data_count < 50) THEN
        RAISE EXCEPTION '학습 데이터가 부족합니다: % (현재: %개)', p_model_type, v_data_count;
    END IF;
    
    -- 학습 작업 생성
    INSERT INTO ml_training.training_jobs (
        job_name,
        model_type,
        training_config,
        data_count,
        status,
        scheduled_at,
        triggered_by
    ) VALUES (
        format('%s_training_%s', p_model_type, to_char(CURRENT_TIMESTAMP, 'YYYYMMDD_HH24MI')),
        p_model_type,
        p_training_config,
        v_data_count,
        'scheduled',
        CURRENT_TIMESTAMP + INTERVAL '10 minutes',
        'scheduled'
    ) RETURNING id INTO v_job_id;
    
    -- 데이터 상태 업데이트
    UPDATE ml_training.data_queue
    SET status = 'training'
    WHERE model_type = p_model_type
      AND status = 'ready';
    
    RETURN v_job_id;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION ml_training.prepare_daily_training_data IS '일일 학습 데이터 준비. 품질 기준을 충족하는 데이터를 ready 상태로 변경';
COMMENT ON FUNCTION ml_training.create_training_job IS '학습 작업 생성. 충분한 데이터가 있을 때만 작업 생성';
```

---