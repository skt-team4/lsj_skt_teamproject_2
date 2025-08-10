# 프론트엔드 통합 가이드

## 개요
나비얌 챗봇 API는 이제 **OpenAI API와 호환되는 엔드포인트**를 제공합니다. 
기존 GPT API를 사용하던 코드를 최소한의 수정으로 나비얌 챗봇과 연동할 수 있습니다.

---

## 빠른 시작

### 1. API 서버 실행
```bash
# 나비얌 챗봇 서버 실행
python api/server.py

# 서버가 http://localhost:8000 에서 실행됩니다
```

### 2. 엔드포인트 변경
```javascript
// 기존 GPT API
const OPENAI_API_URL = 'https://api.openai.com/v1/chat/completions';

// 나비얌 챗봇 API로 변경
const NAVIYAM_API_URL = 'http://localhost:8000/v1/chat/completions';
```

### 3. API 키 제거
```javascript
// 기존: Authorization 헤더 필요
headers: {
  'Authorization': `Bearer ${OPENAI_API_KEY}`,
  'Content-Type': 'application/json'
}

// 나비얌: API 키 불필요
headers: {
  'Content-Type': 'application/json'
}
```

---

## 상세 통합 방법

### 방법 1: OpenAI 호환 모드 (권장) ✅

기존 GPT API 코드를 거의 수정하지 않고 사용할 수 있습니다.

```javascript
// React 예시
async function sendMessage(message) {
  try {
    const response = await fetch('http://localhost:8000/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        model: 'naviyam-chatbot',  // 모델명 (무시됨)
        messages: [
          { role: 'user', content: message }
        ],
        temperature: 0.7
      })
    });

    const data = await response.json();
    
    // GPT와 동일한 응답 구조
    const botResponse = data.choices[0].message.content;
    return botResponse;
    
  } catch (error) {
    console.error('Error:', error);
    return '죄송합니다. 오류가 발생했습니다.';
  }
}
```

### 방법 2: 나비얌 네이티브 API 사용

더 많은 기능을 활용하려면 나비얌 전용 엔드포인트를 사용하세요.

```javascript
async function sendMessageNative(message, userId) {
  try {
    const response = await fetch('http://localhost:8000/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        message: message,
        user_id: userId || 'default_user',
        session_id: sessionStorage.getItem('session_id')
      })
    });

    const data = await response.json();
    
    // 나비얌 고유 기능 활용
    return {
      text: data.response,
      recommendations: data.recommendations,  // 추천 음식점
      emotion: data.emotion,  // 감정 상태
      quickReplies: data.quick_replies  // 빠른 답변 버튼
    };
    
  } catch (error) {
    console.error('Error:', error);
    return { text: '죄송합니다. 오류가 발생했습니다.' };
  }
}
```

---

## API 응답 형식 비교

### OpenAI 호환 모드 (/v1/chat/completions)
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
        "content": "치킨 좋죠! 근처에 맛있는 치킨집을 찾아봤어요..."
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

### 나비얌 네이티브 (/chat)
```json
{
  "response": "치킨 좋죠! 근처에 맛있는 치킨집을 찾아봤어요...",
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
  "emotion": "excited",
  "quick_replies": ["다른 추천", "자세히 보기", "쿠폰 확인"],
  "intent": "search_restaurant",
  "confidence": 0.95
}
```

---

## 주요 차이점 및 주의사항

### 1. 응답 시간
- **GPT API**: 1-3초
- **나비얌 (첫 요청)**: 5-10초 (모델 로딩)
- **나비얌 (이후)**: 2-5초

**해결책**: 로딩 인디케이터 표시
```javascript
setLoading(true);
const response = await sendMessage(message);
setLoading(false);
```

### 2. 스트리밍 미지원
나비얌은 현재 스트리밍을 지원하지 않습니다.
```javascript
// ❌ 지원 안 됨
stream: true

// ✅ 일반 응답만 사용
stream: false  // 또는 생략
```

### 3. CORS 설정
개발 환경에서는 CORS가 허용되어 있지만, 프로덕션에서는 설정이 필요합니다.

```javascript
// 개발 환경 프록시 설정 (React)
// package.json
"proxy": "http://localhost:8000"

// 또는 setupProxy.js
const { createProxyMiddleware } = require('http-proxy-middleware');

module.exports = function(app) {
  app.use(
    '/v1',
    createProxyMiddleware({
      target: 'http://localhost:8000',
      changeOrigin: true,
    })
  );
};
```

---

## 테스트 방법

### 1. 서버 상태 확인
```bash
curl http://localhost:8000/health
```

### 2. 간단한 대화 테스트
```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "naviyam-chatbot",
    "messages": [{"role": "user", "content": "안녕하세요"}]
  }'
```

### 3. 브라우저 콘솔 테스트
```javascript
fetch('http://localhost:8000/v1/chat/completions', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    model: 'naviyam-chatbot',
    messages: [{role: 'user', content: '치킨 추천해줘'}]
  })
})
.then(r => r.json())
.then(console.log);
```

---

## 트러블슈팅

### 문제: 연결 거부 (Connection Refused)
**해결**: API 서버가 실행 중인지 확인
```bash
python api/server.py
```

### 문제: CORS 에러
**해결**: 프론트엔드 프록시 설정 또는 서버 CORS 설정 확인

### 문제: 응답 시간 초과
**해결**: 타임아웃 시간 증가
```javascript
const controller = new AbortController();
const timeoutId = setTimeout(() => controller.abort(), 30000); // 30초

fetch(url, {
  signal: controller.signal,
  // ...
});
```

### 문제: 메모리 부족
**해결**: 서버 실행 시 4bit 양자화 모드 사용
```bash
python api/server.py --use_4bit
```

---

## 지원 및 문의

- **백엔드 팀**: 나비얌 챗봇 API 관련
- **이슈 리포트**: GitHub Issues
- **API 문서**: http://localhost:8000/docs (Swagger UI)

---

## 체크리스트

프론트엔드 통합 전 확인사항:

- [ ] API 서버 실행 확인 (`http://localhost:8000/health`)
- [ ] 엔드포인트 URL 변경 (`/v1/chat/completions`)
- [ ] Authorization 헤더 제거
- [ ] 응답 처리 로직 확인 (`data.choices[0].message.content`)
- [ ] 에러 처리 추가
- [ ] 로딩 상태 UI 구현
- [ ] CORS 프록시 설정 (필요시)

모든 항목을 확인했다면 통합 준비가 완료된 것입니다! 🎉