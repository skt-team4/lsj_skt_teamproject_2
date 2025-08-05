# 🚀 나비얌 챗봇 빠른 연동 테스트 가이드

프론트엔드와 백엔드가 제대로 연결되는지 빠르게 확인하는 방법입니다.

## 1️⃣ 백엔드 서버 실행

### 터미널 1에서:
```bash
cd /Volumes/samsd/skt_teamproject/public_projects/recommendation_chatbot

# 빠른 실행 스크립트 사용
./quick_start.sh

# 또는 수동으로
python3 -m venv venv
source venv/bin/activate
pip install fastapi uvicorn
python -m uvicorn api.server:app --reload --host 0.0.0.0 --port 8000
```

서버가 실행되면:
- API 주소: http://localhost:8000
- API 문서: http://localhost:8000/docs

## 2️⃣ 프론트엔드 실행

### 터미널 2에서:
```bash
cd /Volumes/samsd/skt_teamproject/public_projects/ljm_skt_teamproject-main

# chat.tsx를 chat_fixed.tsx로 교체
cp app/chat_fixed.tsx app/chat.tsx

# 의존성 설치 (처음 한 번만)
npm install

# Expo 실행
npx expo start
```

실행 후:
- `w` 키를 눌러 웹 브라우저에서 실행
- 또는 Expo Go 앱으로 QR 코드 스캔

## 3️⃣ 테스트 방법

### 웹/앱에서:
1. 하단 탭에서 챗 아이콘 클릭
2. 채팅 화면에서 메시지 입력:
   - "치킨 먹고 싶어"
   - "만원으로 뭐 먹을까?"
   - "근처 맛집 추천해줘"

### 백엔드만 테스트 (curl):
```bash
# 새 터미널에서
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "치킨 먹고 싶어",
    "user_id": "test_user"
  }'
```

## 4️⃣ 예상 결과

### 성공 시:
- 프론트엔드에서 메시지 전송 → 백엔드 응답 표시
- 콘솔에 API 호출/응답 로그 출력

### 실패 시 확인사항:
1. **CORS 에러**: 백엔드 서버가 실행 중인지 확인
2. **Connection refused**: 포트 8000이 사용 중인지 확인
3. **Module not found**: 필수 패키지 설치 확인

## 5️⃣ 최소 작동 확인

프론트엔드 콘솔에서 다음과 같은 로그가 보이면 성공:
```
API 호출 시작: { message: '치킨 먹고 싶어', userId: 'test_user' }
응답 상태: 200
API 응답: { response: '...', recommendations: [...] }
```

## 🛠️ 문제 해결

### 백엔드 에러 시:
```bash
# 최소 모드로 실행 (AI 모델 없이)
export USE_GPU=false
export MODEL_TYPE=mock
python -m uvicorn api.server:app --reload
```

### 프론트엔드 연결 안 될 때:
```javascript
// app/chat.tsx에서 API 주소 확인
const API_CONFIG = {
  baseUrl: 'http://localhost:8000', // 맞는지 확인
  // baseUrl: 'http://192.168.x.x:8000', // 실제 IP로 변경
};
```

## ✅ 연동 확인 완료!

위 과정을 통해 프론트엔드와 백엔드가 기본적으로 연결되는지 확인할 수 있습니다.
- 메시지 전송 → 응답 수신 성공하면 기본 연동 완료
- 이후 세부 기능은 점진적으로 개선