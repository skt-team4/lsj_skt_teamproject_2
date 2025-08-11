# 🚀 워크스테이션 최종 설정 단계

## Step 1: 서버 실행 확인

### 워크스테이션 터미널 1에서:
```bash
# 서버가 실행 중인지 확인
curl http://localhost:8000/health

# 응답 예시:
{
  "status": "healthy",
  "gpu_available": true,  # 또는 false (CPU만 있어도 OK)
  "model_loaded": true
}
```

서버가 안 떠있다면:
```bash
# Python 가상환경 활성화
source naviyam_env/bin/activate  # Linux/Mac
# 또는
naviyam_env\Scripts\activate  # Windows

# 서버 실행
python gpu_server.py
```

## Step 2: ngrok 터널링 설정

### 워크스테이션 터미널 2에서:
```bash
# ngrok 실행
ngrok http 8000

# 출력에서 URL 복사:
# Forwarding https://abc123xyz.ngrok-free.app -> http://localhost:8000
#            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ 이 URL을 복사!
```

### ngrok URL 테스트:
```bash
# 로컬에서 테스트 (Mac에서)
curl https://abc123xyz.ngrok-free.app/health
```

## Step 3: React Native 앱 연동

### 옵션 A: 환경변수 파일 수정
```bash
cd /Volumes/samsd/skt_teamproject/public_projects/ljm_skt_teamproject-main

# .env.local 파일 생성/수정
cat > .env.local << EOF
# 워크스테이션 서버 URL (ngrok URL로 변경)
EXPO_PUBLIC_API_URL=https://abc123xyz.ngrok-free.app
EXPO_PUBLIC_API_SERVICE=workstation
EXPO_PUBLIC_ENV=development
EXPO_PUBLIC_DEBUG=true
EOF
```

### 옵션 B: 코드에서 직접 수정
```typescript
// services/apiService.ts 파일 수정
const API_CONFIG = {
  nabiyam: {
    services: {
      // ngrok URL로 직접 변경
      primary: 'https://abc123xyz.ngrok-free.app',
      // ...
    },
    activeService: 'primary',
  },
  // ...
};
```

## Step 4: 앱 실행 및 테스트

### React Native 앱 실행:
```bash
cd public_projects/ljm_skt_teamproject-main

# 패키지 설치 (처음 한 번)
npm install

# 개발 서버 실행
npx expo start

# QR 코드 스캔 또는:
# i - iOS 시뮬레이터
# a - Android 에뮬레이터
# w - 웹 브라우저
```

## Step 5: 테스트 체크리스트

### ✅ 워크스테이션에서 확인:
```bash
# 1. 서버 로그 확인
# gpu_server.py 실행 터미널에서 요청 로그 확인

# 2. GPU/CPU 사용률 확인
nvidia-smi  # GPU 있는 경우
top         # CPU 사용률
```

### ✅ React Native 앱에서 테스트:
1. 앱 실행
2. 채팅 화면으로 이동
3. "안녕하세요" 메시지 전송
4. 응답 확인

### ✅ 연결 확인:
```bash
# Mac에서 직접 API 테스트
curl -X POST https://abc123xyz.ngrok-free.app/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "오늘 점심 추천해줘", "user_id": "test"}'
```

## 🛠️ 트러블슈팅

### "연결 실패" 에러
1. ngrok URL이 정확한지 확인
2. 워크스테이션 방화벽 확인
3. 서버가 실행 중인지 확인

### "CORS 에러"
```python
# gpu_server.py에 이미 설정되어 있음
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 모든 출처 허용
    # ...
)
```

### ngrok 세션 만료 (2시간)
```bash
# 무료 계정 가입 후
ngrok config add-authtoken YOUR_TOKEN
ngrok http 8000  # 더 긴 세션
```

## 📊 성능 모니터링

### 워크스테이션에서:
```python
# 간단한 모니터링 스크립트
import psutil
import GPUtil

# CPU 사용률
print(f"CPU: {psutil.cpu_percent()}%")

# RAM 사용률
print(f"RAM: {psutil.virtual_memory().percent}%")

# GPU 사용률 (있는 경우)
gpus = GPUtil.getGPUs()
if gpus:
    print(f"GPU: {gpus[0].load * 100}%")
```

## 🎯 최종 확인

### 모든 것이 작동한다면:
1. ✅ 워크스테이션 서버 실행 중
2. ✅ ngrok 터널 활성화
3. ✅ React Native 앱 연결됨
4. ✅ 채팅 응답 정상

### 비용 절감 효과:
- **이전**: GCP GPU 월 20만원
- **현재**: 전기료만 (월 3-5만원)
- **절감**: 월 15만원+

## 🔄 일일 운영 방법

### 시작할 때:
```bash
# 터미널 1
cd ~/naviyam_project
source naviyam_env/bin/activate
python gpu_server.py

# 터미널 2
ngrok http 8000
# URL 복사

# React Native 앱 .env.local 업데이트
EXPO_PUBLIC_API_URL=https://new-ngrok-url.ngrok-free.app
```

### 종료할 때:
- Ctrl+C로 서버 종료
- ngrok 종료

## 💡 추가 최적화 (선택사항)

### 1. 자동 시작 설정
```bash
# systemd 서비스 생성 (Linux)
# 또는 작업 스케줄러 (Windows)
```

### 2. 고정 URL 사용
- Cloudflare Tunnel (무료)
- 고정 IP + 포트포워딩
- DuckDNS 등 DDNS 서비스

### 3. 모델 업그레이드
```python
# 더 좋은 한국어 모델 사용
model_name = "beomi/KoAlpaca-Polyglot-5.8B"
```

---

**축하합니다! 🎉**
이제 완전 무료로 AI 챗봇을 운영할 수 있습니다!