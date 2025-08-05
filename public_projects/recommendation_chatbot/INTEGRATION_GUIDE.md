# 나비얌 챗봇 프론트엔드-백엔드 연동 가이드

## 현재 상태 분석

### ✅ 완성된 부분
1. **백엔드 (recommendation_chatbot)**
   - FastAPI 서버 구현 완료 (`api/server.py`)
   - 챗봇 엔진 구현 완료 (AI 모델 + 템플릿 하이브리드)
   - RESTful API 엔드포인트 구현 완료

2. **프론트엔드 (ljm_skt_teamproject-main)**
   - React Native Expo 앱 구조 완성
   - UI/UX 디자인 구현
   - API 호출 함수 구조 준비

### ❌ 아직 연결되지 않은 부분
1. API URL이 하드코딩된 더미 값
2. 응답 데이터 형식 불일치 가능성
3. CORS 설정 확인 필요
4. 인증/세션 관리 미구현

## 연동을 위한 필수 작업

### 1. 백엔드 서버 실행
```bash
cd /Volumes/samsd/skt_teamproject/public_projects/recommendation_chatbot

# 가상환경 생성 및 활성화
python3 -m venv venv
source venv/bin/activate

# 의존성 설치
pip install -r archive/requirements.txt

# FastAPI 서버 실행
python -m api.server
# 또는
uvicorn api.server:app --reload --host 0.0.0.0 --port 8000
```

서버가 실행되면 다음 주소에서 확인:
- API 문서: http://localhost:8000/docs
- 헬스체크: http://localhost:8000/health

### 2. 프론트엔드 API 설정 수정

**파일**: `ljm_skt_teamproject-main/app/chat.tsx`

```typescript
// 기존 코드 (36-44줄)
const API_CONFIG = {
  baseUrl: 'https://your-api-domain.com/api', // 실제 API URL로 변경 필요
  endpoints: {
    chat: '/chat',
    recommend: '/recommend',
  },
  timeout: 10000,
};

// 수정 후
const API_CONFIG = {
  baseUrl: 'http://localhost:8000', // 로컬 테스트용
  // baseUrl: 'https://your-production-api.com', // 프로덕션용
  endpoints: {
    chat: '/chat',
    recommend: '/chat', // 백엔드에 /recommend 엔드포인트가 없음
  },
  timeout: 10000,
};
```

### 3. API 응답 형식 맞추기

백엔드 응답 형식:
```json
{
  "response": "맛있는 치킨 추천드려요!",
  "user_id": "child_001",
  "session_id": "uuid-string",
  "timestamp": "2024-01-01T12:00:00",
  "recommendations": [
    {
      "shop_name": "BBQ",
      "menu_name": "황금올리브치킨",
      "price": 18000,
      "distance": 500
    }
  ],
  "follow_up_questions": ["매운 거 좋아해?", "다른 메뉴도 볼래?"],
  "intent": "FOOD_REQUEST",
  "confidence": 0.95,
  "metadata": {}
}
```

프론트엔드에서 이를 처리하도록 수정 필요.

### 4. CORS 설정 확인

백엔드는 이미 모든 origin을 허용하도록 설정되어 있음:
```python
allow_origins=["*"]  # 프로덕션에서는 특정 도메인으로 제한
```

프로덕션에서는 다음과 같이 수정:
```python
allow_origins=[
    "http://localhost:19006",  # Expo 웹
    "http://localhost:8081",   # Expo 개발 서버
    "https://your-app-domain.com"  # 프로덕션 도메인
]
```

### 5. 프론트엔드 실행 및 테스트

```bash
cd ljm_skt_teamproject-main

# 의존성 설치
npm install

# Expo 개발 서버 실행
npx expo start

# 웹에서 테스트
# w 키를 눌러 웹 브라우저에서 실행
```

### 6. 추가 필요 작업

#### 6.1 에러 처리 개선
프론트엔드 `sendChatMessage` 함수에 백엔드 에러 형식 대응:
```typescript
if (!response.ok) {
  const errorData = await response.json();
  throw new Error(errorData.message || `HTTP error! status: ${response.status}`);
}
```

#### 6.2 로딩 상태 관리
```typescript
const [isLoading, setIsLoading] = useState(false);

const handleSendMessage = async () => {
  setIsLoading(true);
  try {
    const response = await sendChatMessage(message);
    // 처리
  } finally {
    setIsLoading(false);
  }
};
```

#### 6.3 세션 관리
```typescript
// 세션 ID를 AsyncStorage에 저장
import AsyncStorage from '@react-native-async-storage/async-storage';

const getOrCreateSessionId = async () => {
  let sessionId = await AsyncStorage.getItem('sessionId');
  if (!sessionId) {
    sessionId = generateUUID();
    await AsyncStorage.setItem('sessionId', sessionId);
  }
  return sessionId;
};
```

## 테스트 시나리오

### 1. 기본 대화 테스트
```bash
# 백엔드 테스트 (curl)
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "치킨 먹고 싶어",
    "user_id": "test_user"
  }'
```

### 2. 프론트엔드 통합 테스트
1. 백엔드 서버 실행
2. 프론트엔드 앱 실행
3. 채팅 화면에서 메시지 전송
4. 응답 확인

## 배포 고려사항

### 1. 백엔드 배포
- GPU 서버 필요 (AI 모델용)
- 또는 CPU 전용 모드로 실행 (템플릿 응답만)
- Docker 컨테이너화 권장

### 2. 프론트엔드 배포
- Expo EAS Build 사용
- 앱스토어/플레이스토어 배포

### 3. 프로덕션 체크리스트
- [ ] HTTPS 설정
- [ ] 환경변수 분리 (.env)
- [ ] 에러 로깅 시스템
- [ ] 사용자 인증 구현
- [ ] API 레이트 리미팅
- [ ] 모니터링 설정

## 결론

현재 백엔드와 프론트엔드 모두 기본 구조는 완성되어 있으며, **API URL 설정만 변경하면 기본적인 연동은 가능**합니다. 

하지만 프로덕션 레벨로 가려면:
1. 에러 처리 강화
2. 인증/보안 구현
3. 성능 최적화
4. 모니터링 설정

등의 추가 작업이 필요합니다.