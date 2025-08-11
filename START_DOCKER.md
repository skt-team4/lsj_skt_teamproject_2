# 🐳 Docker 1분 실행 가이드

## 🚀 즉시 실행 (워크스테이션에서)

### 옵션 1: Docker Compose (가장 간단) ⭐
```bash
# 1. 프로젝트 폴더로 이동
cd /path/to/skt_teamproject

# 2. 실행!
docker-compose -f docker-compose-simple.yml up

# 끝! 이제 http://localhost:8000 에서 작동합니다
```

### 옵션 2: Docker 명령어
```bash
# 1. 이미지 빌드
docker build -f Dockerfile.openai-compatible -t ai-server .

# 2. 컨테이너 실행
docker run -d -p 8000:8000 --name ai-server ai-server

# 끝!
```

## 🌐 외부 접속 설정 (ngrok 포함)

### 방법 1: Docker Compose에 ngrok 포함
```bash
# 1. ngrok 토큰 설정 (.env 파일)
echo "NGROK_AUTHTOKEN=your_ngrok_token" > .env

# 2. 실행
docker-compose -f docker-compose-simple.yml up

# 3. ngrok URL 확인
docker logs ngrok-tunnel | grep "url="
# 또는
open http://localhost:4040  # ngrok 웹 UI
```

### 방법 2: 별도 ngrok 실행
```bash
# Docker는 그대로 두고
ngrok http 8000
```

## ✅ 테스트

### 로컬 테스트
```bash
# 헬스체크
curl http://localhost:8000/health

# API 테스트 (OpenAI 형식)
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-workstation-123456789" \
  -d '{
    "model": "gpt-3.5-turbo",
    "messages": [{"role": "user", "content": "안녕하세요"}]
  }'
```

## 📱 React Native 앱 연동

### .env.local 파일 수정
```env
# 로컬 Docker
EXPO_PUBLIC_OPENAI_BASE_URL=http://localhost:8000/v1/chat/completions
EXPO_PUBLIC_OPENAI_API_KEY=sk-workstation-123456789

# 또는 ngrok URL
EXPO_PUBLIC_OPENAI_BASE_URL=https://abc123.ngrok.io/v1/chat/completions
EXPO_PUBLIC_OPENAI_API_KEY=sk-workstation-123456789
```

## 🔧 Docker 관리 명령어

### 상태 확인
```bash
# 실행 중인 컨테이너
docker ps

# 로그 보기
docker logs -f ai-server
```

### 중지/시작
```bash
# 중지
docker-compose -f docker-compose-simple.yml down

# 재시작
docker-compose -f docker-compose-simple.yml restart
```

### 정리
```bash
# 컨테이너와 이미지 모두 삭제
docker-compose -f docker-compose-simple.yml down --rmi all
```

## 💡 FAQ

### Q: GPU를 사용하고 싶어요
```yaml
# docker-compose-simple.yml에 추가
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          count: 1
          capabilities: [gpu]
```

### Q: 포트를 변경하고 싶어요
```yaml
# docker-compose-simple.yml 수정
ports:
  - "8080:8000"  # 8080으로 변경
```

### Q: 더 큰 모델을 사용하고 싶어요
```python
# openai_compatible_server.py 수정
model_name = "microsoft/DialoGPT-large"  # 또는 다른 모델
```

## 🎯 핵심 정리

**Docker 실행 = 1줄**
```bash
docker-compose -f docker-compose-simple.yml up
```

**React Native 연동 = 2줄**
```env
EXPO_PUBLIC_OPENAI_BASE_URL=http://localhost:8000/v1/chat/completions
EXPO_PUBLIC_OPENAI_API_KEY=sk-workstation-123456789
```

이제 GPT API 대신 무료로 사용 가능합니다! 🎉