# 🐳 Docker로 AI 서버 실행 가이드

## 📦 Docker 설치

### Windows
```powershell
# Docker Desktop 다운로드
# https://www.docker.com/products/docker-desktop/
```

### Mac
```bash
brew install --cask docker
```

### Linux
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install docker.io docker-compose
sudo usermod -aG docker $USER
```

## 🚀 빠른 시작 (3가지 옵션)

### 옵션 1: GPU 있는 워크스테이션
```bash
# NVIDIA Docker 런타임 설치 (처음 한 번)
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list
sudo apt update && sudo apt install -y nvidia-docker2
sudo systemctl restart docker

# GPU 서버 실행
docker-compose up ai-server-gpu
```

### 옵션 2: CPU만 있는 워크스테이션
```bash
# CPU 버전 실행
docker-compose --profile cpu-only up ai-server-cpu
```

### 옵션 3: ngrok 터널링 포함
```bash
# .env 파일에 ngrok 토큰 설정
echo "NGROK_AUTHTOKEN=your_token_here" > .env

# GPU + ngrok 실행
docker-compose --profile with-ngrok up
```

## 🎯 단계별 설정

### Step 1: 이미지 빌드
```bash
cd /path/to/skt_teamproject

# GPU 버전 빌드
docker build -f Dockerfile.ai-server -t naviyam-ai-gpu .

# CPU 버전 빌드
docker build -f Dockerfile.cpu-only -t naviyam-ai-cpu .
```

### Step 2: 컨테이너 실행

#### GPU 버전
```bash
docker run -d \
  --name naviyam-ai \
  --gpus all \
  -p 8000:8000 \
  -v $(pwd)/cache:/app/cache \
  -v $(pwd)/models:/app/models \
  naviyam-ai-gpu
```

#### CPU 버전
```bash
docker run -d \
  --name naviyam-ai \
  -p 8000:8000 \
  -v $(pwd)/cache:/app/cache \
  naviyam-ai-cpu
```

### Step 3: 헬스체크
```bash
# 컨테이너 상태 확인
docker ps

# 로그 확인
docker logs naviyam-ai

# API 테스트
curl http://localhost:8000/health
```

## 🔗 ngrok 통합 (외부 접속)

### Docker Compose로 자동 실행
```yaml
# docker-compose.yml에 이미 포함됨
services:
  ngrok:
    image: ngrok/ngrok:latest
    command: http ai-server-gpu:8000
    environment:
      - NGROK_AUTHTOKEN=${NGROK_AUTHTOKEN}
```

### ngrok URL 확인
```bash
# ngrok 웹 인터페이스
open http://localhost:4040

# 또는 로그에서 확인
docker logs naviyam-ngrok | grep "url="
```

## 📊 모니터링 (선택사항)

### Prometheus + Grafana 실행
```bash
# 모니터링 스택 실행
docker-compose --profile monitoring up -d

# Grafana 접속
open http://localhost:3000
# 로그인: admin/admin
```

## 🌐 Cloud Run 배포

### 1. 이미지 빌드 및 푸시
```bash
# GCP Artifact Registry에 푸시
docker tag naviyam-ai-cpu gcr.io/rational-autumn-467006-e2/naviyam-ai:latest
docker push gcr.io/rational-autumn-467006-e2/naviyam-ai:latest

# Cloud Run 배포
gcloud run deploy naviyam-ai \
  --image gcr.io/rational-autumn-467006-e2/naviyam-ai:latest \
  --platform managed \
  --region asia-northeast3 \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --min-instances 0 \
  --max-instances 2
```

### 2. 기존 Cloud Run 서비스 업데이트
```bash
gcloud run services update nabiyam-chatbot-web \
  --image gcr.io/rational-autumn-467006-e2/naviyam-ai:latest \
  --region asia-northeast3
```

## 🛠️ 유용한 Docker 명령어

### 기본 명령어
```bash
# 컨테이너 목록
docker ps -a

# 로그 보기
docker logs -f naviyam-ai

# 컨테이너 접속
docker exec -it naviyam-ai bash

# 중지/시작
docker stop naviyam-ai
docker start naviyam-ai

# 삭제
docker rm naviyam-ai
docker rmi naviyam-ai-gpu
```

### Docker Compose 명령어
```bash
# 시작
docker-compose up -d

# 중지
docker-compose down

# 로그
docker-compose logs -f

# 재시작
docker-compose restart

# 전체 정리
docker-compose down -v --rmi all
```

## 🔧 환경 변수 설정

### .env 파일 생성
```env
# AI 모델 설정
MODEL_NAME=microsoft/DialoGPT-medium
DEVICE=cuda
MAX_MEMORY=8GB

# ngrok 설정
NGROK_AUTHTOKEN=your_auth_token

# API 설정
PORT=8000
DEBUG=true
```

## 📱 React Native 앱 연동

### Docker 컨테이너 URL 설정
```javascript
// .env.local
EXPO_PUBLIC_API_URL=http://localhost:8000

// 또는 ngrok URL
EXPO_PUBLIC_API_URL=https://abc123.ngrok.io
```

## ⚡ 성능 최적화

### 1. 모델 캐싱
```dockerfile
# Dockerfile에 추가
RUN python -c "from transformers import AutoModel; AutoModel.from_pretrained('microsoft/DialoGPT-medium')"
```

### 2. 멀티스테이지 빌드
```dockerfile
# 빌드 스테이지
FROM python:3.10 AS builder
RUN pip install --user -r requirements.txt

# 실행 스테이지
FROM python:3.10-slim
COPY --from=builder /root/.local /root/.local
```

### 3. 리소스 제한
```yaml
# docker-compose.yml
deploy:
  resources:
    limits:
      cpus: '2'
      memory: 4G
    reservations:
      cpus: '1'
      memory: 2G
```

## 🚨 트러블슈팅

### GPU를 인식하지 못함
```bash
# NVIDIA 런타임 확인
docker run --rm --gpus all nvidia/cuda:11.8.0-base nvidia-smi

# Docker 데몬 설정
sudo nano /etc/docker/daemon.json
{
  "default-runtime": "nvidia",
  "runtimes": {
    "nvidia": {
      "path": "nvidia-container-runtime",
      "runtimeArgs": []
    }
  }
}
sudo systemctl restart docker
```

### 메모리 부족
```bash
# 스왑 메모리 추가
sudo fallocate -l 8G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

### 포트 충돌
```bash
# 다른 포트 사용
docker run -p 8080:8000 naviyam-ai-gpu
```

## 💰 비용 효과

| 배포 방식 | 초기 비용 | 월 비용 | 장점 | 단점 |
|----------|-----------|---------|------|------|
| Docker (로컬) | 0원 | 전기료 | 완전 제어 | 24/7 PC 필요 |
| Cloud Run + Docker | 0원 | 2만원 | 자동 스케일링 | 콜드 스타트 |
| GCP VM + Docker | 0원 | 20만원 | 항상 가동 | 비용 높음 |

## 🎉 완료!

이제 Docker로 AI 서버를 쉽게 실행할 수 있습니다:
- 개발: `docker-compose up`
- 프로덕션: Cloud Run 배포
- 테스트: 로컬 Docker

---

**팁**: Docker를 사용하면 환경 설정 걱정 없이 어디서든 동일하게 실행됩니다!