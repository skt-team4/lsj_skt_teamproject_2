# 실무적 해결 방법 가이드

## 🎯 핵심 해결책: Session Master 테이블 도입

### 문제점
- 파티션 테이블은 외래키로 참조 불가
- session_id로 테이블 간 연결 불가능
- 데이터 무결성 보장 안 됨

### 해결 방법
**중간 마스터 테이블을 만들어서 모든 테이블이 이것을 참조**

```
┌─────────────────┐
│ session_master  │ ← 중심 테이블 (파티션 아님!)
│   (마스터)      │
└────────┬────────┘
         │
    ┌────┴────┬──────────┬──────────┐
    ↓         ↓          ↓          ↓
conversations  user_interactions  recommendations_log  user_feedback
(파티션 O)     (파티션 X)        (파티션 X)          (파티션 X)
```

---

## 📝 구현 방법

### 1단계: Session Master 테이블 생성
```sql
CREATE TABLE chatbot.session_master (
    session_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id INT REFERENCES chatbot.users(id),
    session_start TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    session_end TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);
```

### 2단계: 모든 테이블이 session_master 참조
```sql
-- conversations (파티션 테이블도 가능!)
FOREIGN KEY (session_id) REFERENCES session_master(session_id)

-- user_interactions
FOREIGN KEY (session_id) REFERENCES session_master(session_id)

-- recommendations_log
FOREIGN KEY (session_id) REFERENCES session_master(session_id)
```

### 3단계: CASCADE 설정으로 자동 삭제
```sql
ON DELETE CASCADE
-- session_master에서 삭제 시 연관 데이터 모두 자동 삭제
```

---

## 🔄 데이터 플로우

### 새 세션 시작
```sql
-- 1. 세션 생성
INSERT INTO session_master (user_id) 
VALUES (1) 
RETURNING session_id;  -- 'abc-123' 반환

-- 2. 대화 기록
INSERT INTO conversations (session_id, ...) 
VALUES ('abc-123', ...);

-- 3. 분석 데이터
INSERT INTO user_interactions (session_id, ...) 
VALUES ('abc-123', ...);
```

### 세션 종료
```sql
UPDATE session_master 
SET session_end = NOW(), is_active = FALSE 
WHERE session_id = 'abc-123';
```

---

## 🚀 실제 적용 스크립트

### 옵션 1: 완전 재구축 (권장)
```bash
# 백업
pg_dump yumai_test > backup.sql

# 새 구조 적용
psql -d yumai_test -f SOLUTION_SESSION_MASTER.sql
```

### 옵션 2: 점진적 마이그레이션
```sql
-- 1. session_master만 먼저 추가
CREATE TABLE chatbot.session_master (...);

-- 2. 기존 세션 데이터 마이그레이션
INSERT INTO session_master 
SELECT DISTINCT session_id, user_id, MIN(time) 
FROM conversations GROUP BY session_id, user_id;

-- 3. 새 데이터부터 session_master 사용
-- 4. 나중에 외래키 추가
```

---

## ✅ 장점

1. **데이터 무결성 보장**
   - 존재하지 않는 session_id 삽입 불가
   - CASCADE로 자동 정리

2. **파티션 성능 유지**
   - conversations는 여전히 파티션
   - 쿼리 성능 그대로

3. **관리 용이**
   - 세션 메타데이터 중앙 관리
   - 세션 생명주기 추적

4. **확장 가능**
   - session_master에 추가 정보 저장 가능
   - 세션 분석, 통계 용이

---

## ⚠️ 주의사항

### 마이그레이션 시
1. **반드시 백업 먼저**
2. **기존 session_id 모두 session_master에 등록**
3. **고아 데이터 정리 후 외래키 추가**

### 운영 시
1. **세션 시작 시 반드시 session_master에 먼저 등록**
2. **정기적으로 비활성 세션 정리**
3. **CASCADE 삭제 주의 (연관 데이터 모두 삭제됨)**

---

## 🤔 다른 옵션들

### 옵션 A: 외래키 포기 (현재 상태)
- 장점: 간단
- 단점: 무결성 보장 안 됨
- 적합: 프로토타입, MVP

### 옵션 B: 파티션 포기
- 장점: 외래키 사용 가능
- 단점: 대용량 데이터 성능 저하
- 적합: 소규모 시스템

### 옵션 C: 애플리케이션 레벨 검증
- 장점: 유연함
- 단점: 복잡, 버그 가능성
- 적합: 특수한 요구사항

### 📍 권장: Session Master (옵션 D)
- **무결성 + 성능 둘 다 확보**
- **실무에서 가장 많이 사용**
- **확장성 좋음**

---

## 📊 적용 후 효과

### Before (현재)
```sql
-- 가짜 session_id 삽입 가능
INSERT INTO user_interactions (session_id) 
VALUES ('fake-uuid');  -- 성공 😱
```

### After (개선 후)
```sql
-- 가짜 session_id 삽입 불가
INSERT INTO user_interactions (session_id) 
VALUES ('fake-uuid');  -- 실패! ✅
-- ERROR: violates foreign key constraint
```

---

## 🎯 결론

**Session Master 테이블 도입이 최선의 해결책**

1. 즉시 적용 가능
2. 기존 파티션 구조 유지
3. 완벽한 참조 무결성
4. 실무 검증된 패턴

SOLUTION_SESSION_MASTER.sql 파일에 전체 구현 코드가 있습니다.