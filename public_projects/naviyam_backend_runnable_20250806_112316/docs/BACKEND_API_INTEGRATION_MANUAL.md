# 백엔드 API 통합 매뉴얼

## 📌 개요
이 문서는 백엔드 개발팀이 나비얌 챗봇 API를 프론트엔드와 연동하기 위한 완전한 가이드입니다.

---

## 🎯 문제 상황 및 해결 방안

### 기존 문제
- **프론트엔드**: OpenAI GPT API 형식으로 요청 전송
- **나비얌 백엔드**: 독자적인 API 형식 사용
- **결과**: 형식 불일치로 연동 실패

### 해결 방안
OpenAI API와 호환되는 어댑터 레이어를 추가하여 자동 변환

---

## 📁 프로젝트 구조

```
aiyam_chatbot_v2/
├── api/
│   ├── server.py              # 메인 API 서버
│   ├── openai_adapter.py      # ⭐ OpenAI 호환 어댑터 (새로 추가)
│   └── README.md
├── inference/                  # 챗봇 핵심 로직
│   └── chatbot.py
├── test_backend_integration.py # ⭐ 통합 테스트 스크립트
└── docs/
    └── BACKEND_API_INTEGRATION_MANUAL.md  # 이 문서
```

---

## 🚀 빠른 시작 가이드

### 1단계: 환경 준비

```bash
# 1. 프로젝트 디렉토리로 이동
cd aiyam_chatbot_v2

# 2. 가상환경 활성화 (선택사항)
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# 3. 의존성 설치 확인
pip install -r requirements.txt
```

### 2단계: API 서버 실행

```bash
# 터미널 1에서 실행
python api/server.py
```

**예상 출력:**
```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     나비얌 챗봇 API 서버 시작...
INFO:     챗봇 초기화 중...
INFO:     나비얌 챗봇 API 서버 초기화 완료
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

⚠️ **주의**: 첫 실행 시 모델 로딩으로 5-10초 소요

### 3단계: API 테스트

```bash
# 터미널 2에서 실행
python test_backend_integration.py
```

**성공 시 출력:**
```
✅ 서버 정상 실행 중
✅ GPT API 형식: 성공 - 프론트엔드 연동 가능!
✅ 나비얌 네이티브: 성공 - 백엔드 로직 정상
```

---

## 🔌 API 엔드포인트 명세

### 1. OpenAI 호환 엔드포인트 (프론트엔드용)

#### `POST /v1/chat/completions`

**요청 형식:**
```json
{
  "model": "gpt-3.5-turbo",  // 무시됨, 호환성을 위해 포함
  "messages": [
    {
      "role": "user",
      "content": "치킨 추천해줘"
    }
  ],
  "temperature": 0.7,  // 선택사항
  "max_tokens": null,   // 선택사항
  "stream": false       // 현재 미지원
}
```

**응답 형식:**
```json
{
  "id": "chatcmpl-abc123",
  "object": "chat.completion",
  "created": 1234567890,
  "model": "naviyam-chatbot",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "치킨 좋죠! 근처 급식카드 사용 가능한 치킨집을 찾아봤어요..."
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 10,
    "completion_tokens": 20,
    "total_tokens": 30
  }
}
```

### 2. 나비얌 네이티브 엔드포인트 (내부용)

#### `POST /chat`

**요청 형식:**
```json
{
  "message": "치킨 추천해줘",
  "user_id": "user123",
  "session_id": "session456"
}
```

**응답 형식:**
```json
{
  "response": "치킨 좋죠! 근처 급식카드 사용 가능한 치킨집을 찾아봤어요...",
  "user_id": "user123",
  "session_id": "session456",
  "timestamp": "2024-01-01T12:00:00",
  "recommendations": [
    {
      "name": "굽네치킨",
      "category": "치킨",
      "average_price": 20000,
      "card_available": true
    }
  ],
  "intent": "search_restaurant",
  "confidence": 0.95,
  "emotion": "excited",
  "metadata": {}
}
```

### 3. 헬스체크 엔드포인트

#### `GET /health`

**응답 예시:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00",
  "version": "1.0.0",
  "components": {
    "chatbot": "healthy",
    "knowledge_base": "healthy",
    "model": "healthy"
  }
}
```

---

## 🔧 구현 상세

### OpenAI 어댑터 동작 원리

```python
# api/openai_adapter.py 핵심 로직

1. GPT 형식 요청 수신
   messages = [{"role": "user", "content": "안녕"}]
   ↓
2. 메시지 추출
   user_message = "안녕"
   ↓
3. 나비얌 형식 변환
   UserInput(text="안녕", user_id="...", ...)
   ↓
4. 챗봇 처리
   chatbot.process_user_input(...)
   ↓
5. 응답 재포장
   choices = [{"message": {"content": "안녕하세요!"}}]
   ↓
6. GPT 형식 응답 반환
```

### 주요 파일 설명

#### `api/server.py`
- FastAPI 메인 서버
- 모든 엔드포인트 정의
- OpenAI 어댑터 통합

#### `api/openai_adapter.py`
- OpenAI API 형식 처리
- 형식 변환 로직
- `/v1/chat/completions` 엔드포인트

---

## 🧪 테스트 방법

### 1. cURL 테스트

```bash
# OpenAI 형식 테스트
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-3.5-turbo",
    "messages": [{"role": "user", "content": "안녕하세요"}]
  }'

# 나비얌 형식 테스트
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "안녕하세요",
    "user_id": "test_user",
    "session_id": "test_session"
  }'
```

### 2. Python 테스트

```python
import requests

# OpenAI 형식
response = requests.post(
    "http://localhost:8000/v1/chat/completions",
    json={
        "model": "gpt-3.5-turbo",
        "messages": [{"role": "user", "content": "치킨 추천"}]
    }
)
print(response.json()["choices"][0]["message"]["content"])
```

### 3. Postman 테스트

1. 새 요청 생성
2. Method: `POST`
3. URL: `http://localhost:8000/v1/chat/completions`
4. Headers: `Content-Type: application/json`
5. Body (raw JSON):
```json
{
  "model": "gpt-3.5-turbo",
  "messages": [{"role": "user", "content": "테스트"}]
}
```

---

## ❗ 트러블슈팅

### 문제 1: ModuleNotFoundError
```
ModuleNotFoundError: No module named 'api.openai_adapter'
```
**해결:** `api/openai_adapter.py` 파일이 있는지 확인

### 문제 2: 서버 시작 실패
```
ERROR: [Errno 10048] 이미 사용 중인 포트
```
**해결:** 
```bash
# Windows
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# 또는 다른 포트 사용
python api/server.py --port 8001
```

### 문제 3: 응답 시간 초과
```
TimeoutError: Request timeout
```
**해결:**
- 첫 요청은 모델 로딩으로 오래 걸림
- 타임아웃을 30초 이상으로 설정
- 두 번째 요청부터는 빨라짐

### 문제 4: 메모리 부족
```
RuntimeError: CUDA out of memory
```
**해결:**
```bash
# CPU 모드로 실행
python api/server.py --device cpu

# 또는 4bit 양자화
python api/server.py --use_4bit
```

---

## 📊 성능 최적화

### 1. 모델 로딩 속도 개선
```python
# config.yaml 수정
model:
  cache_dir: "./cache/models"  # 로컬 캐시 사용
  load_in_4bit: true           # 4bit 양자화
```

### 2. 응답 캐싱
```python
# 자주 사용되는 질문 캐싱
cache:
  enabled: true
  ttl: 3600  # 1시간
```

### 3. 동시 요청 처리
```bash
# Gunicorn으로 실행 (프로덕션)
gunicorn api.server:app -w 4 -k uvicorn.workers.UvicornWorker
```

---

## 🚢 배포 준비

### 1. 환경 변수 설정
```bash
# .env 파일 생성
API_HOST=0.0.0.0
API_PORT=8000
MODEL_CACHE_DIR=./cache
LOG_LEVEL=INFO
```

### 2. Docker 컨테이너화
```dockerfile
# Dockerfile
FROM python:3.10
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "api/server.py"]
```

### 3. 프로덕션 체크리스트
- [ ] CORS 설정 (특정 도메인만 허용)
- [ ] HTTPS 설정
- [ ] 로그 수집 시스템 구축
- [ ] 모니터링 대시보드 설정
- [ ] 부하 테스트 완료
- [ ] 백업 및 복구 계획

---

## 📞 지원

### 문제 발생 시
1. 로그 확인: `outputs/naviyam_chatbot.log`
2. 서버 상태: `GET /health`
3. API 문서: `http://localhost:8000/docs`

### 추가 자료
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- 소스 코드: `api/` 디렉토리

---

## 📝 요약

1. **문제**: 프론트엔드(GPT 형식) ↔ 백엔드(나비얌 형식) 불일치
2. **해결**: OpenAI 호환 어댑터 추가 (`/v1/chat/completions`)
3. **테스트**: `python test_backend_integration.py`
4. **결과**: 프론트엔드 수정 없이 연동 가능

이제 백엔드 API가 GPT 형식과 나비얌 형식 모두 지원합니다! 🎉