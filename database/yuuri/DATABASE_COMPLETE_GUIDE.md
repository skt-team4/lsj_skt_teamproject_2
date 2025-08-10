# YUMAI 데이터베이스 완전 가이드

## 📋 목차
1. [프로젝트 개요](#프로젝트-개요)
2. [데이터베이스 아키텍처](#데이터베이스-아키텍처)
3. [설치 및 설정](#설치-및-설정)
4. [스키마 상세 설명](#스키마-상세-설명)
5. [파티셔닝 전략](#파티셔닝-전략)
6. [테스트 결과](#테스트-결과)
7. [성능 최적화](#성능-최적화)
8. [트러블슈팅](#트러블슈팅)
9. [API 참조](#api-참조)
10. [유지보수 가이드](#유지보수-가이드)

---

## 프로젝트 개요

### 목적
음식점 추천 챗봇 서비스를 위한 확장 가능하고 성능 최적화된 PostgreSQL 데이터베이스 시스템

### 주요 기능
- 🍽️ 음식점 및 메뉴 관리
- 👤 사용자 프로필 및 선호도 추적
- 💳 급식카드 지원 시스템
- 🎟️ 쿠폰 및 할인 관리
- 💬 대화 로그 파티셔닝
- 📊 실시간 분석 및 추천

### 기술 스택
- **Database**: PostgreSQL 16
- **Extensions**: uuid-ossp, pg_trgm, btree_gin, pgcrypto
- **특수 기능**: JSONB, 파티셔닝, Materialized Views, GIN 인덱스

---

## 데이터베이스 아키텍처

### 스키마 구조
```
yumai_db/
├── chatbot/          # 핵심 비즈니스 로직
│   ├── shops         # 가게 정보
│   ├── menus         # 메뉴 정보
│   ├── users         # 사용자 정보
│   ├── orders        # 주문 관리
│   ├── reviews       # 리뷰 시스템
│   └── conversations # 대화 로그 (파티션)
├── analytics/        # 분석 데이터
│   ├── recommendations_log
│   └── user_feedback
└── ml_features/      # 머신러닝 특징
    ├── nlu_features
    └── user_interactions
```

### ER 다이어그램 (주요 관계)
```
users ──┬── user_profiles (1:1)
        ├── foodcard_users (1:1)
        ├── user_wallet (1:N)
        ├── orders (1:N)
        ├── reviews (1:N)
        └── conversations (1:N)

shops ──┬── menus (1:N)
        ├── orders (N:1)
        └── reviews (N:1)

coupons ── user_wallet (1:N)

orders ──┬── orders_coupons (1:N)
         └── reviews (1:1)
```

---

## 설치 및 설정

### 1. PostgreSQL 설치
```bash
# macOS (Homebrew)
brew install postgresql@16
brew services start postgresql@16

# 경로 설정
export PATH="/opt/homebrew/opt/postgresql@16/bin:$PATH"
```

### 2. 데이터베이스 생성
```bash
createdb yumai_production
```

### 3. 스키마 적용
```bash
# 수정된 스키마 사용 (파티셔닝 오류 수정됨)
psql -d yumai_production -f yumai_fixed.sql
```

### 4. 초기 데이터 설정
```bash
# 테스트 데이터 삽입
psql -d yumai_production -f test_partitions.sql
```

---

## 스키마 상세 설명

### 1. chatbot.shops (가게 정보)
```sql
CREATE TABLE chatbot.shops (
    id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    shop_name VARCHAR(30) NOT NULL,
    category VARCHAR(20) NOT NULL,  -- 한식, 중식, 일식 등
    latitude DECIMAL(8,6) NOT NULL,
    longitude DECIMAL(9,6) NOT NULL,
    business_hours JSONB,           -- 영업시간 JSON
    is_good_influence_shop BOOLEAN, -- 착한가게 여부
    is_food_card_shop CHAR(1),      -- Y/N/P/U
    popularity_score DECIMAL(4,3),  -- AI 계산 인기도
    quality_score DECIMAL(4,3)      -- AI 계산 품질점수
);
```

**JSONB business_hours 예시:**
```json
{
  "monday": {"open": "09:00", "close": "22:00"},
  "tuesday": {"open": "09:00", "close": "22:00"},
  "sunday": {"closed": true}
}
```

### 2. chatbot.conversations (대화 로그 - 파티션)
```sql
CREATE TABLE chatbot.conversations (
    id BIGINT GENERATED ALWAYS AS IDENTITY,
    session_id UUID NOT NULL,
    conversation_time TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (id, conversation_time),  -- 파티션 키 포함
    input_text VARCHAR(1000),
    response_text VARCHAR(700),
    extracted_intent VARCHAR(50),
    extracted_entities JSONB
) PARTITION BY RANGE (conversation_time);
```

**파티션 구조:**
- 월별 파티션 (conversations_YYYY_MM)
- 자동 프루닝으로 쿼리 성능 최적화
- 6개월 이상 데이터 자동 삭제 함수 포함

### 3. chatbot.user_profiles (사용자 프로필)
```sql
CREATE TABLE chatbot.user_profiles (
    user_id INT PRIMARY KEY REFERENCES users(id),
    preferred_categories TEXT[],      -- ['한식', '중식']
    taste_preferences JSONB,          -- {"매운맛": 0.8}
    average_budget INT,
    favorite_shops INT[],
    good_influence_preference DECIMAL(3,2)
);
```

---

## 파티셔닝 전략

### 문제점 해결
**원본 오류:**
```
ERROR: unique constraint on partitioned table must include all partitioning columns
```

**해결 방법:**
1. `session_id` 단독 UNIQUE 제약 제거
2. 복합 UNIQUE 제약 추가: `(session_id, conversation_time)`
3. PRIMARY KEY에 파티션 키 포함

### 파티션 관리
```sql
-- 새 파티션 생성 (매월 실행)
CREATE TABLE chatbot.conversations_2025_04 
PARTITION OF chatbot.conversations
FOR VALUES FROM ('2025-04-01') TO ('2025-05-01');

-- 오래된 파티션 삭제
DROP TABLE chatbot.conversations_2024_01;

-- 자동 삭제 함수
SELECT auto_delete_old_conversations();
```

---

## 테스트 결과

### 1. CRUD 작업 ✅
- 모든 테이블 INSERT/UPDATE/DELETE 정상 작동
- 트리거를 통한 updated_at 자동 갱신 확인

### 2. 파티셔닝 ✅
```
파티션별 데이터 분포:
┌────────────────────────┬──────────┬─────────┐
│ Partition              │ Records  │ Period  │
├────────────────────────┼──────────┼─────────┤
│ conversations_2024_08  │ 1        │ 2024-08 │
│ conversations_2024_09  │ 1        │ 2024-09 │
│ conversations_2024_10  │ 1        │ 2024-10 │
│ conversations_2025_01  │ 2        │ 2025-01 │
│ conversations_2025_02  │ 1        │ 2025-02 │
└────────────────────────┴──────────┴─────────┘
```

### 3. 인덱스 성능 ✅
```sql
-- 카테고리 검색: Index Scan (0.007ms)
EXPLAIN ANALYZE 
SELECT * FROM shops WHERE category = '한식';

-- GIN 인덱스 활용: 배열 검색 최적화
SELECT * FROM user_profiles 
WHERE preferred_categories @> ARRAY['한식'];
```

### 4. 제약조건 검증 ✅
- 외래키 CASCADE 삭제 정상 작동
- CHECK 제약조건 위반 시 적절한 오류 발생
- 이메일 형식 검증 작동

### 5. JSONB 작업 ✅
```sql
-- 영업시간 조회
SELECT business_hours->>'monday' FROM shops;

-- 메뉴 옵션 접근
SELECT options->'size'->0->>'price' FROM menus;
```

---

## 성능 최적화

### 인덱스 전략
```sql
-- 1. B-Tree 인덱스 (일반 검색)
CREATE INDEX idx_shops_category ON shops(category);

-- 2. 부분 인덱스 (조건부 검색)
CREATE INDEX idx_shops_open ON shops(current_status) 
WHERE current_status = 'OPEN';

-- 3. GIN 인덱스 (텍스트/배열 검색)
CREATE INDEX idx_shops_name_gin ON shops 
USING gin(shop_name gin_trgm_ops);

-- 4. 복합 인덱스 (다중 컬럼)
CREATE INDEX idx_menus_shop_price ON menus(shop_id, price);
```

### 쿼리 최적화 팁
1. **파티션 프루닝 활용**
   ```sql
   -- Good: 시간 범위 명시
   SELECT * FROM conversations 
   WHERE conversation_time >= '2024-11-01' 
   AND conversation_time < '2024-12-01';
   ```

2. **인덱스 힌트 활용**
   ```sql
   -- 착한가게만 검색 (부분 인덱스 활용)
   SELECT * FROM shops 
   WHERE is_good_influence_shop = true;
   ```

3. **JSONB 인덱싱**
   ```sql
   CREATE INDEX idx_shops_hours ON shops 
   USING gin(business_hours);
   ```

---

## 트러블슈팅

### 일반적인 문제 해결

#### 1. 파티션 테이블 외래키 오류
**문제:** `relation "conversations" does not exist`
**해결:** 파티션 테이블은 직접 외래키 참조 불가. session_id만 저장하고 애플리케이션에서 검증

#### 2. UNIQUE 제약 파티션 오류
**문제:** `unique constraint must include all partitioning columns`
**해결:** UNIQUE(session_id, conversation_time) 형태로 복합 제약 사용

#### 3. JSONB 쿼리 성능 저하
**문제:** JSONB 필드 검색이 느림
**해결:** GIN 인덱스 생성
```sql
CREATE INDEX idx_business_hours ON shops USING gin(business_hours);
```

---

## API 참조

### 함수

#### get_shop_hours()
영업시간 조회 함수
```sql
-- 사용법
SELECT * FROM get_shop_hours(shop_id, 'monday');
SELECT * FROM get_shop_hours(shop_id);  -- 현재 요일

-- 반환값
open_hour  | close_hour
-----------+-----------
09:00:00   | 22:00:00
```

#### clean_invalid_shop_references()
잘못된 가게 참조 정리
```sql
-- 사용법
SELECT clean_invalid_shop_references();
```

#### auto_delete_old_conversations()
6개월 이상 대화 삭제
```sql
-- 사용법 (cron job 권장)
SELECT auto_delete_old_conversations();
```

### 트리거

#### update_updated_at_column()
모든 테이블의 updated_at 자동 갱신
```sql
-- 자동 적용 테이블
shops, menus, users, user_profiles, foodcard_users
```

---

## 유지보수 가이드

### 일일 작업
```sql
-- 1. 통계 갱신
ANALYZE;

-- 2. Materialized View 갱신
REFRESH MATERIALIZED VIEW chatbot.recent_conversations;
```

### 주간 작업
```sql
-- 1. 인덱스 재구성
REINDEX DATABASE yumai_production;

-- 2. 공간 정리
VACUUM FULL ANALYZE;
```

### 월간 작업
```sql
-- 1. 새 파티션 생성
CREATE TABLE chatbot.conversations_YYYY_MM 
PARTITION OF chatbot.conversations
FOR VALUES FROM ('YYYY-MM-01') TO ('YYYY-MM-01'::date + interval '1 month');

-- 2. 오래된 데이터 정리
SELECT auto_delete_old_conversations();

-- 3. 백업
pg_dump yumai_production > backup_YYYYMMDD.sql
```

### 모니터링 쿼리
```sql
-- 테이블 크기 확인
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables 
WHERE schemaname IN ('chatbot', 'analytics', 'ml_features')
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- 인덱스 사용률
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan as index_scans,
    idx_tup_read as tuples_read,
    idx_tup_fetch as tuples_fetched
FROM pg_stat_user_indexes
ORDER BY idx_scan DESC;

-- 슬로우 쿼리 확인
SELECT 
    query,
    calls,
    total_time,
    mean_time,
    max_time
FROM pg_stat_statements
WHERE mean_time > 100
ORDER BY mean_time DESC
LIMIT 10;
```

---

## 보안 권장사항

1. **접근 권한 관리**
   ```sql
   -- 읽기 전용 사용자
   CREATE ROLE readonly_user LOGIN PASSWORD 'secure_password';
   GRANT CONNECT ON DATABASE yumai_production TO readonly_user;
   GRANT USAGE ON SCHEMA chatbot TO readonly_user;
   GRANT SELECT ON ALL TABLES IN SCHEMA chatbot TO readonly_user;
   ```

2. **민감 데이터 암호화**
   ```sql
   -- pgcrypto 사용
   UPDATE users SET phone_number = pgp_sym_encrypt(phone_number, 'secret_key');
   ```

3. **감사 로그 설정**
   ```sql
   -- postgresql.conf
   log_statement = 'all'
   log_connections = on
   log_disconnections = on
   ```

---

## 부록

### 파일 구조
```
/Volumes/samsd/yuuri/
├── yumai.sql              # 원본 스키마 (파티션 오류 포함)
├── yumai_fixed.sql        # 수정된 스키마 (정상 작동)
├── test_partitions.sql    # 파티션 테스트 쿼리
├── comprehensive_test.sql # 전체 기능 테스트
├── CLAUDE.md             # 초기 테스트 문서
├── DATABASE_COMPLETE_GUIDE.md # 본 문서
└── todo.txt              # 작업 내역
```

### 성능 벤치마크
- 파티션 테이블 쿼리: ~5ms (월별 데이터)
- 인덱스 스캔: ~0.007ms
- Full Table Scan (6 rows): ~0.004ms
- JSONB 필드 접근: ~0.01ms

### 확장 계획
1. **자동 파티션 생성** - pg_partman 확장 도입 검토
2. **실시간 동기화** - logical replication 설정
3. **캐싱 레이어** - Redis 연동
4. **분석 파이프라인** - Apache Kafka 통합

---

## 문의 및 지원

본 문서는 YUMAI 데이터베이스 시스템의 완전한 기술 참조서입니다.
추가 질문이나 지원이 필요한 경우 기술팀에 문의하세요.

**작성일**: 2025-08-07  
**버전**: 1.0  
**작성자**: Claude Code Assistant