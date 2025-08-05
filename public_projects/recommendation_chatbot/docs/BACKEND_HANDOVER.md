# 백엔드 담당자 인수인계 가이드

## 📋 프로젝트 개요
**나비얌 챗봇** - 아동 대상 착한가게 추천 AI 챗봇 백엔드 시스템

## 🎯 현재 완성된 작업

### ✅ 1. API 서버 기본 구조 (완료)
- **파일**: `api/server.py`
- **설명**: FastAPI 기반 REST API 서버 틀
- **포함 기능**:
  - 기본 엔드포인트 (/chat, /health, /users 등)
  - 요청/응답 모델 정의 (Pydantic)
  - 에러 핸들링 구조
  - CORS 설정
  - API 문서화 (Swagger)

### ✅ 2. 데이터 구조 정의 (완료)
- **파일**: `data/data_structure.py`
- **설명**: 모든 데이터 모델과 Enum 정의
- **포함 내용**:
  - 사용자 입력/출력 모델
  - 가게/메뉴 정보 구조
  - 대화 및 추천 데이터 구조
  - 사용자 프로필 구조

### ✅ 3. 챗봇 로직 (완료)
- **파일**: `inference/chatbot.py`
- **설명**: 핵심 챗봇 처리 로직
- **기능**: 사용자 입력 → 의도 분석 → 응답 생성

## 🚀 백엔드 담당자가 해야 할 작업

### 📊 1. 데이터베이스 설계 및 구축 (최우선)

#### 필요한 참고 파일:
```
data/data_structure.py    # 데이터 모델 참고
api/server.py            # API 명세 참고  
sample_data.xlsx         # 실제 데이터 구조 참고
```

#### 작업 내용:
1. **ERD 설계**
   - 사용자, 가게, 메뉴, 대화기록, 추천기록 테이블
   - 관계 설정 (1:N, N:M)
   
2. **데이터베이스 선택**
   - PostgreSQL/MySQL 추천 (정형 데이터)
   - MongoDB 대안 (JSON 데이터 많음)

3. **ORM 설정**
   - SQLAlchemy 추천
   - Alembic 마이그레이션 설정

#### 예상 주요 테이블:
- `users` - 사용자 기본정보
- `user_profiles` - 사용자 개인화 데이터
- `shops` - 가게 정보
- `menus` - 메뉴 정보
- `conversations` - 대화 기록
- `recommendations` - 추천 기록
- `feedback` - 사용자 피드백

### 🔗 2. API 엔드포인트 실제 구현

#### 현재 상태:
- **완료**: API 명세, 요청/응답 모델
- **필요**: 실제 비즈니스 로직 구현

#### 우선순위 엔드포인트:
1. `POST /chat` - 메인 채팅 API
2. `GET /users/{user_id}/profile` - 사용자 프로필
3. `GET /users/{user_id}/history` - 대화 기록
4. `GET /health` - 헬스체크

#### 연동 포인트:
```python
# api/server.py의 이 부분을 실제 DB 로직으로 교체
@app.post("/chat")
async def chat(request: ChatRequest):
    # 현재: 챗봇 로직만 호출
    # 추가 필요: DB 저장, 사용자 관리, 세션 관리
```

### 🗄️ 3. 데이터베이스 연동

#### 설정 파일 생성:
```
database/
├── __init__.py
├── connection.py     # DB 연결 설정
├── models.py        # SQLAlchemy 모델
├── schemas.py       # Pydantic 스키마
└── crud.py          # CRUD 작업
```

#### 환경 설정:
```bash
# .env 파일
# 보안상 데이터베이스 연결 정보는 .env 파일에서 관리합니다.
# .env.example 파일을 .env로 복사하고 실제 값으로 변경하세요.
# DATABASE_URL="postgresql://your_user:your_password@your_host/your_database"
REDIS_URL=redis://localhost:6379  # 캐싱용 (선택)
```

### 🔐 4. 인증/인가 시스템 (선택)

#### 고려사항:
- 아동 대상이므로 간단한 세션 기반 추천
- JWT 토큰 (확장 시)
- 사용자 식별자만으로 시작 가능

### 📈 5. 성능 최적화

#### 우선순위:
1. **DB 쿼리 최적화**
   - 인덱스 설정
   - N+1 쿼리 방지
   
2. **캐싱 전략**
   - Redis 활용
   - 가게 정보 캐싱
   - 추천 결과 캐싱

3. **비동기 처리**
   - 백그라운드 작업
   - 로그 처리

## 📁 인수인계 파일 목록

### 🔥 핵심 파일 (필수 검토)
```
api/server.py                 # API 서버 메인
api/README.md                # API 사용 가이드
data/data_structure.py       # 데이터 모델 정의
inference/chatbot.py         # 챗봇 로직 (참고용)
requirements.txt             # 기본 의존성
sample_data.xlsx            # 실제 데이터 구조
```

### 📚 참고 파일
```
utils/config.py              # 설정 관리
utils/logging_utils.py       # 로깅 설정
rag/test_data.json          # 현재 사용 중인 데이터
main.py                     # CLI 실행 (참고)
```

### 📝 문서 파일
```
api/README.md               # API 문서
work_summary/               # 프로젝트 진행사항
CLAUDE.md                   # 프로젝트 가이드
```

## 🛠 개발 환경 설정

### 1. 의존성 설치
```bash
pip install fastapi uvicorn sqlalchemy alembic psycopg2-binary
```

### 2. 서버 실행 테스트
```bash
python api/server.py
# 또는
uvicorn api.server:app --reload
```

### 3. API 문서 확인
```
http://localhost:8000/docs
```

## 🔄 작업 순서 제안

1. **1주차**: 데이터베이스 설계 및 구축
2. **2주차**: 핵심 API 엔드포인트 구현
3. **3주차**: 챗봇 로직과 DB 연동
4. **4주차**: 성능 최적화 및 테스트

## 🚨 주의사항

### ⚠️ 기존 코드와의 연동
- `inference/chatbot.py`의 기존 로직 활용
- `data/data_structure.py`의 모델 구조 준수
- API 명세 변경 시 프론트엔드와 협의

### 📊 데이터 처리
- `sample_data.xlsx` 파일이 실제 데이터 구조
- 현재 `rag/test_data.json`은 테스트용 (38개→7개 컬럼 축소됨)
- 실제 데이터 확장 시 AI 성능 향상 예상

### 🔒 보안 고려사항
- 아동 데이터 처리 주의
- 개인정보 최소 수집
- 로그에 민감정보 노출 방지

## 📞 연락 및 지원

### 기술 지원:
- AI 로직 관련: `inference/` 담당자
- 프론트엔드 연동: 추후 협의
- 데이터 구조: `data/data_structure.py` 참고

### 테스트 방법:
```bash
# 기본 헬스체크
curl http://localhost:8000/health

# 채팅 테스트  
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "치킨 먹고 싶어", "user_id": "test_user"}'
```

## 🎯 목표
백엔드 담당자가 이 가이드를 통해 **즉시 작업을 시작**할 수 있도록 하며, 기존 AI 로직과 **매끄럽게 연동**되는 견고한 백엔드 시스템 구축

---
**마지막 업데이트**: 2025.07.29  
**작성자**: Claude (AI 로직 담당)  
**인수자**: [백엔드 담당자명]