# 파티션 테이블의 외래키 참조 문제 상세 분석

## 🚨 친구분이 맞습니다! 

파티션 테이블을 외래키로 참조할 수 없는 문제가 실제로 존재합니다.

---

## 📌 핵심 문제

### 1. PostgreSQL의 제약사항
```sql
-- ❌ 불가능: 파티션 테이블을 외래키로 참조
CREATE TABLE ml_features.user_interactions (
    session_id UUID REFERENCES chatbot.conversations(session_id)  -- 실패!
);
```

**오류 메시지:**
```
ERROR: cannot reference partitioned table "conversations"
```

### 2. 복합키 문제
```sql
-- conversations 테이블의 UNIQUE 제약
CONSTRAINT unique_session_id UNIQUE (session_id, conversation_time)

-- ❌ 외래키 참조 시도
CREATE TABLE other_table (
    session_id UUID,
    -- 단일 컬럼으로는 복합 UNIQUE 참조 불가
    FOREIGN KEY (session_id) REFERENCES conversations(session_id)  -- 실패!
    
    -- 복합키 전체를 참조해야 함
    FOREIGN KEY (session_id, conversation_time) 
        REFERENCES conversations(session_id, conversation_time)  -- 하지만 파티션이라 실패!
);
```

---

## 🔍 실제 코드 분석

### yumai.sql (원본 - 오류 발생)
```sql
-- conversations 테이블 (파티션)
CREATE TABLE chatbot.conversations (
    session_id UUID NOT NULL UNIQUE,  -- 단독 UNIQUE
    ...
) PARTITION BY RANGE (conversation_time);

-- 다른 테이블에서 참조 시도
CREATE TABLE ml_features.user_interactions (
    session_id UUID REFERENCES chatbot.conversations(session_id)  -- 파티션이라 실패
);
```

### yumai_fixed.sql (수정본 - 외래키 제거)
```sql
-- conversations 테이블 (파티션)
CREATE TABLE chatbot.conversations (
    session_id UUID NOT NULL,  -- UNIQUE 제거
    CONSTRAINT unique_session_id UNIQUE (session_id, conversation_time)  -- 복합키
) PARTITION BY RANGE (conversation_time);

-- 다른 테이블에서 외래키 제약 제거
CREATE TABLE ml_features.user_interactions (
    session_id UUID,  -- 외래키 제약 없음! ✅
    -- 애플리케이션 레벨에서 검증 필요
);

CREATE TABLE analytics.recommendations_log (
    session_id UUID,  -- 외래키 제약 없음! ✅
);

CREATE TABLE analytics.user_feedback (
    session_id UUID,  -- 외래키 제약 없음! ✅
);
```

---

## 💡 해결 방법들

### 방법 1: 외래키 제약 포기 (현재 선택) ✅
```sql
-- 외래키 없이 session_id만 저장
CREATE TABLE ml_features.user_interactions (
    session_id UUID NOT NULL,  -- 외래키 제약 없음
    -- 애플리케이션에서 유효성 검증
);

-- 장점: 간단, 파티션 사용 가능
-- 단점: 참조 무결성 보장 안 됨
```

### 방법 2: 중간 테이블 사용
```sql
-- 세션 마스터 테이블 (파티션 아님)
CREATE TABLE chatbot.session_master (
    session_id UUID PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- conversations는 session_master 참조
CREATE TABLE chatbot.conversations (
    session_id UUID REFERENCES chatbot.session_master(session_id),
    ...
) PARTITION BY RANGE (conversation_time);

-- 다른 테이블도 session_master 참조
CREATE TABLE ml_features.user_interactions (
    session_id UUID REFERENCES chatbot.session_master(session_id)  -- 가능!
);
```

### 방법 3: 트리거로 무결성 검증
```sql
-- 트리거 함수 생성
CREATE OR REPLACE FUNCTION check_session_exists()
RETURNS TRIGGER AS $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM chatbot.conversations 
        WHERE session_id = NEW.session_id
    ) THEN
        RAISE EXCEPTION 'session_id % does not exist', NEW.session_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 트리거 적용
CREATE TRIGGER verify_session
BEFORE INSERT ON ml_features.user_interactions
FOR EACH ROW EXECUTE FUNCTION check_session_exists();
```

---

## 📊 각 방법의 장단점 비교

| 방법 | 참조 무결성 | 성능 | 복잡도 | 파티션 활용 |
|------|------------|------|--------|------------|
| 1. 외래키 없음 (현재) | ❌ | ⭐⭐⭐ | 낮음 | ✅ |
| 2. 중간 테이블 | ✅ | ⭐⭐ | 중간 | ✅ |
| 3. 트리거 검증 | 🔶 | ⭐ | 높음 | ✅ |
| 4. 파티션 포기 | ✅ | ⭐ | 낮음 | ❌ |

---

## 🎯 실제 영향 분석

### 현재 구조의 문제점
```sql
-- 1. 존재하지 않는 session_id 삽입 가능
INSERT INTO ml_features.user_interactions (session_id, user_id)
VALUES ('fake-session-id', 1);  -- 성공함 (문제!)

-- 2. conversations에서 삭제해도 연관 데이터 남음
DELETE FROM chatbot.conversations WHERE session_id = 'xxx';
-- user_interactions의 데이터는 그대로 남음 (고아 데이터)

-- 3. 데이터 정합성 체크 필요
SELECT ui.session_id
FROM ml_features.user_interactions ui
LEFT JOIN chatbot.conversations c ON ui.session_id = c.session_id
WHERE c.session_id IS NULL;  -- 고아 레코드 찾기
```

---

## 🛠️ 권장 해결책

### 개선된 스키마 설계
```sql
-- 1. 세션 마스터 테이블 추가
CREATE TABLE chatbot.session_master (
    session_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id INT REFERENCES chatbot.users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    session_metadata JSONB
);

-- 2. conversations는 파티션 유지
CREATE TABLE chatbot.conversations (
    id BIGINT GENERATED ALWAYS AS IDENTITY,
    session_id UUID NOT NULL REFERENCES chatbot.session_master(session_id),
    conversation_time TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id, conversation_time),
    input_text VARCHAR(1000),
    response_text VARCHAR(700)
) PARTITION BY RANGE (conversation_time);

-- 3. 다른 테이블들도 session_master 참조
CREATE TABLE ml_features.user_interactions (
    session_id UUID REFERENCES chatbot.session_master(session_id) ON DELETE CASCADE,
    ...
);

CREATE TABLE analytics.recommendations_log (
    session_id UUID REFERENCES chatbot.session_master(session_id) ON DELETE CASCADE,
    ...
);
```

### 데이터 플로우
```
1. 새 세션 시작
   → session_master에 INSERT
   → session_id 생성

2. 대화 기록
   → conversations에 INSERT (파티션됨)
   → session_id로 session_master 참조

3. 분석 데이터
   → user_interactions, recommendations_log 등
   → session_id로 session_master 참조

4. CASCADE 삭제
   → session_master에서 삭제 시
   → 모든 연관 데이터 자동 삭제
```

---

## 📝 마이그레이션 스크립트

```sql
-- 기존 데이터를 유지하면서 마이그레이션
BEGIN;

-- 1. session_master 생성
CREATE TABLE chatbot.session_master (
    session_id UUID PRIMARY KEY,
    user_id INT REFERENCES chatbot.users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. 기존 세션 데이터 마이그레이션
INSERT INTO chatbot.session_master (session_id, user_id, created_at)
SELECT DISTINCT session_id, user_id, MIN(conversation_time)
FROM chatbot.conversations
GROUP BY session_id, user_id;

-- 3. 외래키 추가 (새 테이블 생성 시)
-- ALTER TABLE은 파티션 테이블에 외래키 추가 불가
-- 새로 만들거나 애플리케이션 레벨 검증 유지

COMMIT;
```

---

## 🎓 결론

### 친구분의 지적이 맞는 이유:
1. **파티션 테이블은 외래키로 참조 불가** (PostgreSQL 제약)
2. **복합키는 부분 참조 불가** (session_id만으로는 참조 못함)
3. **현재 구조는 참조 무결성 포기** (애플리케이션 검증 필요)

### 실무 권장사항:
1. **중요한 시스템**: session_master 테이블 도입
2. **성능 중심**: 현재 구조 유지 + 정기적 정합성 체크
3. **하이브리드**: 중요 테이블만 session_master 참조

### 트레이드오프:
- **파티션 성능 vs 참조 무결성**
- 대부분의 대용량 시스템은 성능을 선택
- 정기적인 데이터 정합성 체크로 보완