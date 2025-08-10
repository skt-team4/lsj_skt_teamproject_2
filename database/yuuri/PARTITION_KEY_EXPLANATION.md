# PostgreSQL 파티션 테이블의 UNIQUE 제약조건 이해하기

## 🔍 문제 상황

### 원본 코드 (오류 발생)
```sql
CREATE TABLE chatbot.conversations (
    id BIGINT GENERATED ALWAYS AS IDENTITY,
    session_id UUID NOT NULL UNIQUE,  -- ❌ 문제: 단독 UNIQUE
    user_id INT,
    conversation_time TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (id, conversation_time),
    ...
) PARTITION BY RANGE (conversation_time);  -- 파티션 키: conversation_time
```

### 오류 메시지
```
ERROR: unique constraint on partitioned table must include all partitioning columns
```

---

## 📚 이론적 배경

### 파티션 테이블의 제약사항
PostgreSQL에서 파티션 테이블을 사용할 때, **모든 UNIQUE 제약조건은 반드시 파티션 키를 포함해야 합니다.**

**이유:**
- 각 파티션은 독립적인 물리적 테이블
- UNIQUE 제약은 전체 테이블에 걸쳐 유일성을 보장해야 함
- 파티션 키 없이는 모든 파티션을 검색해야 함 (성능 저하)

### 그림으로 이해하기

```
❌ 잘못된 구조 (session_id만 UNIQUE)
┌─────────────────────────────────────┐
│         전체 테이블 (논리적)          │
│  session_id는 전체에서 유일해야 함    │
└─────────────────────────────────────┘
           ↓ 파티셔닝 ↓
┌──────────┐ ┌──────────┐ ┌──────────┐
│2024년8월 │ │2024년9월 │ │2024년10월│
├──────────┤ ├──────────┤ ├──────────┤
│session_A │ │session_B │ │session_C │
└──────────┘ └──────────┘ └──────────┘
문제: session_A의 유일성 검증 시 모든 파티션 검색 필요!

✅ 올바른 구조 (session_id + conversation_time)
┌─────────────────────────────────────┐
│         전체 테이블 (논리적)          │
│  (session_id, time) 조합이 유일      │
└─────────────────────────────────────┘
           ↓ 파티셔닝 ↓
┌──────────┐ ┌──────────┐ ┌──────────┐
│2024년8월 │ │2024년9월 │ │2024년10월│
├──────────┤ ├──────────┤ ├──────────┤
│session_A │ │session_B │ │session_C │
│+ 시간정보│ │+ 시간정보│ │+ 시간정보│
└──────────┘ └──────────┘ └──────────┘
해결: conversation_time으로 해당 파티션만 검색!
```

---

## 💡 해결 방법

### 수정된 코드
```sql
CREATE TABLE chatbot.conversations (
    id BIGINT GENERATED ALWAYS AS IDENTITY,
    session_id UUID NOT NULL DEFAULT uuid_generate_v4(),  -- UNIQUE 제거
    user_id INT,
    conversation_time TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (id, conversation_time),  -- 파티션 키 포함
    ...
    -- 복합 UNIQUE 제약 추가 (파티션 키 포함)
    CONSTRAINT unique_session_id UNIQUE (session_id, conversation_time)
) PARTITION BY RANGE (conversation_time);
```

### 핵심 변경사항
1. **단독 UNIQUE 제거**: `session_id UUID NOT NULL UNIQUE` → `session_id UUID NOT NULL`
2. **복합 UNIQUE 추가**: `UNIQUE (session_id, conversation_time)`
3. **PRIMARY KEY 수정**: `(id, conversation_time)` - 파티션 키 포함

---

## 🤔 실제 의미

### Q: session_id가 정말로 유일한가?
**A: 실질적으로는 YES!**

- `session_id`는 UUID (`uuid_generate_v4()`)로 생성
- UUID는 사실상 중복 가능성이 없음 (340,282,366,920,938,463,463,374,607,431,768,211,456 가지)
- 같은 session_id가 다른 시간에 나타날 가능성은 거의 0

### Q: 그럼 왜 복합키로 만들었나?
**A: PostgreSQL 파티션 규칙 때문**

```sql
-- 실제 데이터 예시
session_id                            | conversation_time
--------------------------------------+------------------------
f1982e25-5040-4235-b0db-6adde79e95c6 | 2024-09-20 12:00:00+09
a7b3c4d5-6789-4321-bcde-f0123456789a | 2024-10-15 14:30:00+09

-- 각 session_id는 사실상 유일하지만,
-- PostgreSQL은 (session_id, conversation_time) 조합으로 체크
```

---

## 🚀 성능 영향

### 장점
1. **파티션 프루닝**: 시간 기반 쿼리 시 해당 파티션만 검색
2. **인덱스 효율성**: 각 파티션별 작은 인덱스
3. **유지보수**: 오래된 파티션 통째로 삭제 가능

### 쿼리 예시
```sql
-- ✅ 효율적: 특정 시간 범위 명시
SELECT * FROM conversations 
WHERE session_id = 'f1982e25-5040-4235-b0db-6adde79e95c6'
AND conversation_time >= '2024-09-01' 
AND conversation_time < '2024-10-01';
-- 결과: 2024년 9월 파티션만 검색

-- ⚠️ 비효율적: 시간 조건 없음
SELECT * FROM conversations 
WHERE session_id = 'f1982e25-5040-4235-b0db-6adde79e95c6';
-- 결과: 모든 파티션 검색 (느림)
```

---

## 📊 실제 적용 결과

### 테스트 데이터
```sql
-- 파티션별 데이터 분포
SELECT 
    tableoid::regclass as partition_name,
    COUNT(*) as records
FROM chatbot.conversations
GROUP BY tableoid;

-- 결과:
partition_name                | records
------------------------------+---------
chatbot.conversations_2024_08 | 1
chatbot.conversations_2024_09 | 1  
chatbot.conversations_2024_10 | 1
chatbot.conversations_2025_01 | 2
chatbot.conversations_2025_02 | 1
```

### 유일성 검증
```sql
-- session_id 중복 체크
SELECT session_id, COUNT(*) 
FROM chatbot.conversations 
GROUP BY session_id 
HAVING COUNT(*) > 1;
-- 결과: 0 rows (중복 없음)

-- 복합키 중복 체크
SELECT session_id, conversation_time, COUNT(*) 
FROM chatbot.conversations 
GROUP BY session_id, conversation_time 
HAVING COUNT(*) > 1;
-- 결과: 0 rows (당연히 중복 없음)
```

---

## 🎯 핵심 요약

### 변경 전후 비교
| 항목 | 변경 전 (오류) | 변경 후 (정상) |
|------|---------------|---------------|
| UNIQUE 제약 | `session_id` | `(session_id, conversation_time)` |
| PRIMARY KEY | `id` | `(id, conversation_time)` |
| 파티션 키 | `conversation_time` | `conversation_time` |
| 실제 중복 가능성 | 없음 | 없음 |
| PostgreSQL 규칙 | ❌ 위반 | ✅ 준수 |

### 기억할 점
1. **기술적 제약**: PostgreSQL 파티션 테이블의 규칙
2. **실용적 영향**: session_id는 여전히 사실상 유일함
3. **성능 이점**: 파티션 프루닝으로 쿼리 최적화
4. **베스트 프랙티스**: 쿼리 시 항상 시간 조건 포함

---

## 💭 추가 고려사항

### 대안 1: 파티션 사용 안 함
```sql
-- 파티션 없이 일반 테이블 사용
CREATE TABLE conversations (
    session_id UUID PRIMARY KEY,
    ...
);
-- 장점: 제약 없음
-- 단점: 대용량 데이터 시 성능 저하
```

### 대안 2: 다른 파티션 전략
```sql
-- session_id 해시 파티션 (PostgreSQL 11+)
CREATE TABLE conversations (...)
PARTITION BY HASH (session_id);
-- 장점: session_id만으로 UNIQUE 가능
-- 단점: 시간 기반 데이터 관리 어려움
```

### 권장사항
현재 구조(시간 기반 RANGE 파티션 + 복합 UNIQUE)가 챗봇 대화 로그에 가장 적합:
- ✅ 시간순 데이터 관리 용이
- ✅ 오래된 데이터 쉽게 삭제
- ✅ 대부분의 쿼리가 시간 기반
- ✅ session_id 실질적 유일성 유지