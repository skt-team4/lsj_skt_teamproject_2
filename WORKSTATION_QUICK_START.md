# 🚀 워크스테이션 AI 서버 - 5분 설정 가이드

## 즉시 실행 (3단계)

### 1️⃣ 워크스테이션에서 서버 실행
```bash
# 터미널 1
cd /path/to/skt_teamproject
./quick_workstation_setup.sh

# 또는 수동 실행
python3 -m venv naviyam_gpu_env
source naviyam_gpu_env/bin/activate
pip install fastapi uvicorn transformers torch
python gpu_server.py
```

서버가 시작되면:
- http://localhost:8000 접속 확인
- http://localhost:8000/health 에서 GPU 상태 확인

### 2️⃣ 외부 접속 설정 (ngrok)
```bash
# 터미널 2
# ngrok 설치 (처음 한 번만)
brew install ngrok  # Mac
# 또는
snap install ngrok  # Ubuntu

# ngrok 실행
ngrok http 8000
```

출력 예시:
```
Forwarding  https://abc123xyz.ngrok.io -> http://localhost:8000
```
이 URL을 복사하세요!

### 3️⃣ Cloud Run 연동
```bash
# 옵션 A: 환경변수로 설정
gcloud run services update nabiyam-chatbot-web \
  --set-env-vars GPU_SERVER_URL=https://abc123xyz.ngrok.io \
  --region asia-northeast3 \
  --project rational-autumn-467006-e2

# 옵션 B: 직접 테스트
curl -X POST https://abc123xyz.ngrok.io/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "안녕하세요"}'
```

## 📝 체크리스트

✅ **워크스테이션 준비**
- [ ] Python 3.8+ 설치됨
- [ ] GPU 있으면 좋고, 없어도 됨
- [ ] 인터넷 연결

✅ **서버 실행 확인**
- [ ] http://localhost:8000 접속 성공
- [ ] /health 엔드포인트 응답 확인

✅ **외부 접속**
- [ ] ngrok URL 생성됨
- [ ] 외부에서 접속 가능

## 🔥 바로 테스트

### 로컬 테스트
```python
# test_local.py
import requests

response = requests.post(
    "http://localhost:8000/chat",
    json={"message": "오늘 점심 추천해줘"}
)
print(response.json())
```

### 외부 테스트
```bash
# ngrok URL로 테스트
curl https://your-ngrok-url.ngrok.io/health
```

## ⚡ 성능 팁

### GPU 있는 경우
```python
# gpu_server.py 수정
# 더 큰 모델 사용
model_name = "beomi/KoAlpaca-Polyglot-5.8B"  # 한국어 특화
```

### GPU 없는 경우
```python
# CPU 최적화 모델
model_name = "microsoft/DialoGPT-small"  # 117M
# 또는
model_name = "skt/kogpt2-base-v2"  # 한국어 125M
```

## 🛠️ 트러블슈팅

### "GPU를 찾을 수 없습니다"
→ 정상입니다. CPU로 작동합니다.

### "포트 8000이 이미 사용 중"
```bash
# 다른 포트 사용
PORT=8001 python gpu_server.py
ngrok http 8001
```

### ngrok 세션 만료 (2시간)
→ 무료 계정 가입하면 더 긴 세션
→ 또는 Cloudflare Tunnel 사용

## 💰 비용 절감 효과

| 항목 | GCP GPU | 워크스테이션 |
|-----|---------|------------|
| 초기비용 | 0원 | 0원 (이미 있음) |
| 월 비용 | 20만원 | 전기료 3만원 |
| 성능 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| 관리 | 쉬움 | 중간 |

## 📞 다음 단계

1. **모델 업그레이드**
   - 한국어 특화 모델로 변경
   - 나비얌 데이터로 파인튜닝

2. **안정성 개선**
   - systemd 서비스 등록
   - 자동 재시작 설정

3. **보안 강화**
   - API 키 인증
   - HTTPS 인증서

---

**즉시 지원**: 문제가 있으면 바로 물어보세요!