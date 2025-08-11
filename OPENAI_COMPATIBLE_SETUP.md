# 🔄 OpenAI API 완벽 대체 가이드

## 🎯 핵심: GPT API 키처럼 간단하게!

### 현재 상황
- **이전**: OpenAI API 키 필요 (유료)
- **현재**: 워크스테이션 AI 서버 (무료, OpenAI 호환)

## 🚀 즉시 실행 방법

### 1️⃣ 워크스테이션에서 서버 실행
```bash
# OpenAI 호환 서버 실행
python openai_compatible_server.py

# 출력:
# ╔══════════════════════════════════════════════════════╗
# ║     OpenAI Compatible AI Server                      ║
# ║     GPT API를 완벽하게 대체합니다!                    ║
# ╠══════════════════════════════════════════════════════╣
# ║  기본 API 키: sk-workstation-123456789               ║
# ║  엔드포인트: http://localhost:8000/v1/chat/completions║
# ╚══════════════════════════════════════════════════════╝
```

### 2️⃣ ngrok으로 공개
```bash
ngrok http 8000

# URL 복사: https://abc123.ngrok.io
```

### 3️⃣ React Native 앱 설정 (2가지 방법)

#### 방법 A: 환경변수만 변경 (가장 간단) ✅
```bash
# .env.local 파일 생성
cd public_projects/ljm_skt_teamproject-main

cat > .env.local << EOF
# OpenAI 대신 워크스테이션 서버 사용
EXPO_PUBLIC_OPENAI_BASE_URL=https://abc123.ngrok.io/v1/chat/completions
EXPO_PUBLIC_OPENAI_API_KEY=sk-workstation-123456789
EOF
```

#### 방법 B: 코드에서 직접 변경
```typescript
// services/apiService.ts
const API_CONFIG = {
  openai: {
    // OpenAI를 워크스테이션으로 변경
    baseUrl: 'https://abc123.ngrok.io/v1/chat/completions',
    apiKey: 'sk-workstation-123456789',
    model: 'gpt-3.5-turbo',
  },
};
```

## 🔑 API 키 시스템

### 기본 제공 키
```
sk-workstation-123456789
```

### 커스텀 키 추가
```python
# openai_compatible_server.py에서
API_KEYS = {
    "sk-workstation-123456789": "default_user",
    "sk-custom-your-key-here": "custom_user",  # 추가
}
```

또는 환경변수로:
```bash
CUSTOM_API_KEY=sk-my-secret-key python openai_compatible_server.py
```

## ✅ 100% OpenAI 호환 엔드포인트

| OpenAI 엔드포인트 | 워크스테이션 엔드포인트 | 상태 |
|------------------|------------------------|------|
| `/v1/chat/completions` | `/v1/chat/completions` | ✅ |
| `/v1/models` | `/v1/models` | ✅ |
| `/v1/completions` | `/v1/completions` | ✅ |
| Authorization: Bearer | Authorization: Bearer | ✅ |

## 🧪 테스트

### curl로 테스트 (OpenAI와 동일한 형식)
```bash
curl https://abc123.ngrok.io/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-workstation-123456789" \
  -d '{
    "model": "gpt-3.5-turbo",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

### Python으로 테스트 (OpenAI 라이브러리 사용 가능!)
```python
import openai

# 워크스테이션 서버로 설정
openai.api_base = "https://abc123.ngrok.io/v1"
openai.api_key = "sk-workstation-123456789"

response = openai.ChatCompletion.create(
    model="gpt-3.5-turbo",
    messages=[{"role": "user", "content": "Hello!"}]
)
print(response.choices[0].message.content)
```

### JavaScript/TypeScript (기존 코드 그대로)
```javascript
const response = await fetch('https://abc123.ngrok.io/v1/chat/completions', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer sk-workstation-123456789',
  },
  body: JSON.stringify({
    model: 'gpt-3.5-turbo',
    messages: [{ role: 'user', content: 'Hello!' }]
  })
});
```

## 🔄 전환 가이드

### OpenAI에서 워크스테이션으로
```diff
- baseUrl: 'https://api.openai.com/v1/chat/completions'
- apiKey: 'sk-your-openai-key'
+ baseUrl: 'https://your-workstation.ngrok.io/v1/chat/completions'
+ apiKey: 'sk-workstation-123456789'
```

### 워크스테이션에서 OpenAI로 (필요시)
```diff
- baseUrl: 'https://your-workstation.ngrok.io/v1/chat/completions'
- apiKey: 'sk-workstation-123456789'
+ baseUrl: 'https://api.openai.com/v1/chat/completions'
+ apiKey: 'sk-your-openai-key'
```

## 🐳 Docker로 실행

```dockerfile
# Dockerfile.openai-compatible
FROM python:3.10-slim

WORKDIR /app

RUN pip install fastapi uvicorn transformers torch

COPY openai_compatible_server.py .

ENV API_KEY=sk-workstation-123456789

EXPOSE 8000

CMD ["python", "openai_compatible_server.py"]
```

```bash
# 빌드 및 실행
docker build -f Dockerfile.openai-compatible -t openai-compatible .
docker run -p 8000:8000 openai-compatible
```

## 💡 장점

### vs OpenAI
- ✅ **무료** (월 $20 → $0)
- ✅ **무제한** 요청
- ✅ **데이터 프라이버시** (로컬 실행)
- ✅ **커스터마이징 가능**

### vs 복잡한 설정
- ✅ **API 키만 변경** (코드 수정 최소화)
- ✅ **OpenAI 라이브러리 호환**
- ✅ **동일한 응답 형식**
- ✅ **기존 코드 그대로 사용**

## 📊 비교표

| 항목 | OpenAI GPT | 워크스테이션 AI |
|------|-----------|----------------|
| 월 비용 | $20+ | $0 |
| API 키 | 필요 | 필요 (무료) |
| 응답 형식 | JSON | JSON (동일) |
| 엔드포인트 | /v1/chat/completions | /v1/chat/completions (동일) |
| 코드 변경 | - | URL만 변경 |
| 제한 | 분당 요청 제한 | 무제한 |

## 🎯 결론

**GPT API 키를 워크스테이션 키로 바꾸기만 하면 됩니다!**

1. `openai_compatible_server.py` 실행
2. ngrok으로 공개
3. API 키와 URL만 변경
4. 완료!

기존 OpenAI 사용 코드를 **전혀 수정하지 않고** 사용 가능합니다.