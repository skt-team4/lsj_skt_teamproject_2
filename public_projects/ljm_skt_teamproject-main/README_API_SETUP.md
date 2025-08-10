# 나비얌 앱 API 설정 가이드

## 🔄 OpenAI GPT → Cloud Run 서비스 전환 완료

### 변경 사항
- **이전**: OpenAI GPT API 직접 호출 (비용 발생)
- **현재**: 배포된 Cloud Run 서비스 사용 (자체 AI 모델)

## 📋 설정 방법

### 1. 환경 변수 설정
```bash
# .env.example을 복사하여 .env.local 생성
cp .env.example .env.local
```

### 2. .env.local 파일 수정
```env
# 기본 Cloud Run 서비스 사용
EXPO_PUBLIC_API_URL=https://nabiyam-chatbot-web-816056347823.asia-northeast3.run.app

# 또는 워크스테이션 서버 사용 (ngrok URL)
# EXPO_PUBLIC_API_URL=https://abc123.ngrok.io
```

### 3. 앱 실행
```bash
# 패키지 설치
npm install

# 개발 서버 실행
npx expo start
```

## 🔌 API 엔드포인트

### 현재 사용 가능한 서비스
1. **Primary** (기본): `https://nabiyam-chatbot-web-816056347823.asia-northeast3.run.app`
2. **Secondary**: `https://nabiyam-webapp-v2-816056347823.asia-northeast3.run.app`
3. **Workstation**: 워크스테이션 ngrok URL (선택사항)

### API 호출 예시
```typescript
// services/apiService.ts
const response = await fetch(`${apiUrl}/chat`, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    message: "오늘 점심 추천해줘",
    user_id: 'mobile_user',
    session_id: 'session_123',
  }),
});
```

## 🛠️ 서비스 전환 방법

### 코드에서 직접 전환
```typescript
import { switchApiService } from './services/apiService';

// 워크스테이션 서버로 전환
switchApiService('workstation');

// 다시 기본 서버로 전환
switchApiService('primary');
```

### 환경 변수로 전환
```env
# .env.local
EXPO_PUBLIC_API_SERVICE=workstation
EXPO_PUBLIC_WORKSTATION_URL=https://your-ngrok.ngrok.io
```

## 📊 비용 비교

| 서비스 | 월 비용 | 장점 | 단점 |
|--------|---------|------|------|
| OpenAI GPT | $20-50 | 고품질 응답 | 비용 발생 |
| Cloud Run | 거의 무료 | 자체 모델, 무료 | 성능 제한 |
| 워크스테이션 | 전기료만 | 완전 제어 | 설정 필요 |

## 🔍 디버깅

### 로그 확인
```typescript
// 앱에서 콘솔 로그 확인
console.log('API 호출:', apiUrl);
console.log('API 응답:', data);
```

### 헬스체크
```bash
# 서비스 상태 확인
curl https://nabiyam-chatbot-web-816056347823.asia-northeast3.run.app/health
```

## ⚠️ 주의사항

1. **CORS 설정**: Cloud Run 서비스는 모든 origin 허용하도록 설정됨
2. **타임아웃**: 15초로 설정 (느린 응답 대비)
3. **에러 처리**: 서비스 다운시 자동 폴백 메시지 표시

## 🚀 추가 최적화

### 캐싱 구현 (선택사항)
```typescript
// 자주 묻는 질문 캐싱
const responseCache = new Map();

if (responseCache.has(message)) {
  return responseCache.get(message);
}
```

### 오프라인 모드 (선택사항)
```typescript
// 네트워크 없을 때 기본 응답
if (!navigator.onLine) {
  return {
    success: false,
    message: '오프라인 상태입니다. 인터넷 연결을 확인해주세요.',
  };
}
```

## 📞 문제 해결

### API 호출 실패
1. Cloud Run 서비스 상태 확인
2. 네트워크 연결 확인
3. 환경 변수 설정 확인

### 느린 응답
1. 워크스테이션 서버 사용 고려
2. 타임아웃 값 증가
3. 캐싱 구현

---

**변경 완료!** OpenAI GPT 대신 자체 배포 서비스를 사용합니다.