# 🚀 나비얌 챗봇 Docker 배포 가이드

## 📌 개요
이 문서는 **나비얌 챗봇**을 Docker 환경에서 배포하는 완전한 가이드입니다.
서버 담당자분이 이 문서만 보고도 성공적으로 배포할 수 있도록 모든 단계를 상세히 설명합니다.

## 📋 목차
1. [사전 준비사항](#사전-준비사항)
2. [빠른 시작](#빠른-시작)
3. [상세 설정](#상세-설정)
4. [배포 및 실행](#배포-및-실행)
5. [테스트](#테스트)
6. [문제 해결](#문제-해결)
7. [프로덕션 최적화](#프로덕션-최적화)

---

## 사전 준비사항

### 필수 소프트웨어
- **Docker**: 20.10 이상
- **Docker Compose**: 2.0 이상
- **NVIDIA Driver**: 470 이상 (GPU 사용 시)
- **NVIDIA Container Toolkit** (GPU 사용 시)

### 시스템 요구사항
- **RAM**: 최소 16GB (권장 32GB)
- **Storage**: 50GB 이상 여유 공간
- **GPU**: NVIDIA GPU (CUDA 11.8+ 지원)
- **CPU**: 4코어 이상

### GPU 설정 확인
```bash
# NVIDIA 드라이버 확인
nvidia-smi

# Docker GPU 지원 확인
docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi
```

---

## 빠른 시작

### 1단계: 환경 변수 설정
```bash
# .env 파일 생성
cp .env.example .env

# .env 파일 편집 (비밀번호 등 설정)
nano .env
```

### 2단계: 모델 파일 준비
```bash
# 모델 캐시 디렉토리 생성
mkdir -p model_cache

# 모델 다운로드 (필요한 경우)
# A.X 3.1 Lite 모델을 model_cache 디렉토리에 배치
```

### 3단계: Docker 실행
```bash
# 이미지 빌드 및 컨테이너 실행
docker-compose up --build -d

# 로그 확인
docker-compose logs -f app
```

### 4단계: 상태 확인
```bash
# 컨테이너 상태 확인
docker-compose ps

# 헬스체크
curl http://localhost:8000/health
```

---

## 상세 설정

### 환경 변수 설명

#### 데이터베이스 설정
```env
POSTGRES_DB=aiyam_db          # 데이터베이스 이름
POSTGRES_USER=aiyam_user      # DB 사용자명
POSTGRES_PASSWORD=secure_pwd   # DB 비밀번호 (변경 필수!)
```

#### 모델 설정
```env
MODEL_PATH=/app/model_cache   # 모델 파일 경로
USE_4BIT=true                  # 4비트 양자화 사용
MAX_LENGTH=2048                # 최대 토큰 길이
TEMPERATURE=0.7                # 생성 온도
```

#### API 설정
```env
API_PORT=8000                  # API 서버 포트
API_WORKERS=1                  # 워커 프로세스 수
LOG_LEVEL=INFO                 # 로그 레벨
```

### Docker Compose 프로파일

#### 개발 환경 (pgAdmin 포함)
```bash
docker-compose --profile dev up -d
```

#### 프로덕션 환경 (최소 구성)
```bash
docker-compose up -d
```

---

## 배포 및 실행

### 개발 환경 배포
```bash
# 1. 전체 스택 실행
docker-compose --profile dev up --build

# 2. pgAdmin 접속
# http://localhost:5050
# 로그인: admin@aiyam.com / admin

# 3. API 문서 확인
# http://localhost:8000/docs
```

### 프로덕션 환경 배포
```bash
# 1. 프로덕션 이미지 빌드
docker build -t aiyam-chatbot:prod -f Dockerfile .

# 2. 환경 변수 설정
export POSTGRES_PASSWORD=$(openssl rand -base64 32)
export SECRET_KEY=$(openssl rand -base64 32)

# 3. 실행
docker-compose up -d

# 4. 로그 모니터링
docker-compose logs -f --tail=100
```

### 스케일링
```bash
# API 서버 스케일 아웃 (3개 인스턴스)
docker-compose up -d --scale app=3
```

---

## 테스트

### 자동화 테스트 실행
```bash
# 테스트 스크립트 실행
python test_docker.py

# 특정 서버 테스트
python test_docker.py http://your-server:8000
```

### 수동 테스트

#### 헬스체크
```bash
curl http://localhost:8000/health
```

#### 채팅 API 테스트
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "안녕하세요",
    "user_id": "test_user"
  }'
```

#### OpenAI 호환 API 테스트
```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "naviyam-v1",
    "messages": [
      {"role": "user", "content": "치킨 추천해줘"}
    ]
  }'
```

### 성능 테스트
```bash
# Apache Bench 사용
ab -n 100 -c 10 -p request.json -T application/json \
   http://localhost:8000/chat
```

---

## 문제 해결

### 일반적인 문제

#### 1. 모델 로딩 실패
```bash
# 모델 파일 확인
ls -la model_cache/

# 권한 설정
chmod -R 755 model_cache/

# 볼륨 재마운트
docker-compose down
docker-compose up -d
```

#### 2. GPU를 인식하지 못함
```bash
# NVIDIA Container Toolkit 재설치
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | \
  sudo tee /etc/apt/sources.list.d/nvidia-docker.list

sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit
sudo systemctl restart docker
```

#### 3. 메모리 부족
```bash
# Docker 메모리 제한 확인
docker system df

# 불필요한 이미지 정리
docker system prune -a

# swap 메모리 추가 (Linux)
sudo fallocate -l 8G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

#### 4. 데이터베이스 연결 실패
```bash
# PostgreSQL 컨테이너 로그 확인
docker-compose logs db

# 데이터베이스 초기화
docker-compose down -v
docker-compose up -d db
docker-compose exec db psql -U aiyam_user -d aiyam_db
```

### 로그 확인
```bash
# 전체 로그
docker-compose logs

# 특정 서비스 로그
docker-compose logs app
docker-compose logs db

# 실시간 로그
docker-compose logs -f --tail=50

# 로그 파일 위치
ls -la logs/
```

---

## 프로덕션 최적화

### 1. 이미지 최적화
```dockerfile
# Dockerfile에서 모델 파일 포함 (Volume 대신)
COPY model_cache /app/model_cache

# 멀티스테이지 빌드로 이미지 크기 감소
FROM python:3.10-slim as builder
# ... 빌드 단계

FROM pytorch/pytorch:2.3.0-cuda12.1-cudnn8-runtime
# ... 실행 단계
```

### 2. 보안 강화
```yaml
# docker-compose.yml
services:
  app:
    # 읽기 전용 루트 파일시스템
    read_only: true
    # 임시 디렉토리 마운트
    tmpfs:
      - /tmp
    # 보안 옵션
    security_opt:
      - no-new-privileges:true
    # 사용자 변경
    user: "1000:1000"
```

### 3. 네트워크 최적화
```yaml
# 내부 네트워크만 사용
networks:
  aiyam_net:
    internal: true
  
  external_net:
    external: true
```

### 4. 리소스 제한
```yaml
deploy:
  resources:
    limits:
      memory: 12G
      cpus: '4'
    reservations:
      memory: 10G
      cpus: '2'
```

### 5. 모니터링 추가
```yaml
# Prometheus + Grafana 추가
prometheus:
  image: prom/prometheus:latest
  volumes:
    - ./prometheus.yml:/etc/prometheus/prometheus.yml
  ports:
    - "9090:9090"

grafana:
  image: grafana/grafana:latest
  ports:
    - "3000:3000"
```

---

## 백업 및 복구

### 데이터베이스 백업
```bash
# 백업
docker-compose exec db pg_dump -U aiyam_user aiyam_db > backup.sql

# 복구
docker-compose exec -T db psql -U aiyam_user aiyam_db < backup.sql
```

### 전체 볼륨 백업
```bash
# 백업
docker run --rm -v aiyam_chatbot_v2_postgres_data:/data \
  -v $(pwd):/backup alpine tar czf /backup/postgres_backup.tar.gz /data

# 복구
docker run --rm -v aiyam_chatbot_v2_postgres_data:/data \
  -v $(pwd):/backup alpine tar xzf /backup/postgres_backup.tar.gz
```

---

## CI/CD 통합

### GitHub Actions 예제
```yaml
name: Deploy
on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Build and push Docker image
        run: |
          docker build -t ghcr.io/${{ github.repository }}:latest .
          docker push ghcr.io/${{ github.repository }}:latest
      
      - name: Deploy to server
        run: |
          ssh user@server "docker-compose pull && docker-compose up -d"
```

---

## 유용한 명령어

```bash
# 컨테이너 쉘 접속
docker-compose exec app bash

# 데이터베이스 접속
docker-compose exec db psql -U aiyam_user -d aiyam_db

# Redis CLI
docker-compose exec redis redis-cli

# 리소스 사용량 확인
docker stats

# 네트워크 확인
docker network ls

# 볼륨 확인
docker volume ls

# 전체 정리 (주의!)
docker-compose down -v --remove-orphans
```

---

## 지원 및 문의

- **이슈 트래커**: [GitHub Issues](https://github.com/your-repo/issues)
- **문서**: [API Documentation](http://localhost:8000/docs)
- **이메일**: support@aiyam.com

---

*작성일: 2025-08-07*  
*버전: 1.0.0*