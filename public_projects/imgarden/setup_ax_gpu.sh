#!/bin/bash

echo "🔧 A.X-3.1-Light 모델 설정 시작..."

# 기존 컨테이너 정리
docker stop ax-chatbot 2>/dev/null
docker rm ax-chatbot 2>/dev/null

# 프로젝트 압축 해제
cd /home/isangjae
rm -rf naviyam_backend
tar -xzf naviyam_ax_deploy.tar.gz
mv naviyam_backend_runnable_20250806_112316 naviyam_backend

# Dockerfile 생성
cat > /home/isangjae/naviyam_backend/Dockerfile << 'EOF'
FROM nvidia/cuda:12.2.0-runtime-ubuntu22.04

RUN apt-get update && apt-get install -y \
    python3.10 \
    python3.10-dev \
    python3-pip \
    git \
    wget \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . /app/

RUN pip3 install --no-cache-dir \
    torch \
    transformers \
    accelerate \
    bitsandbytes \
    fastapi \
    uvicorn \
    faiss-cpu \
    numpy \
    scikit-learn \
    pandas \
    sentencepiece \
    protobuf \
    peft \
    GPUtil

ENV PYTHONPATH=/app
ENV USE_4BIT=true
ENV MODEL_NAME=skt/A.X-3.1-Light
ENV CUDA_VISIBLE_DEVICES=0

EXPOSE 8000

CMD ["python3", "-m", "uvicorn", "api.server:app", "--host", "0.0.0.0", "--port", "8000"]
EOF

# Docker 이미지 빌드
echo "🔨 Docker 이미지 빌드 중..."
cd /home/isangjae/naviyam_backend
docker build -t ax-chatbot:latest .

# 컨테이너 실행
echo "🚀 컨테이너 시작..."
docker run -d \
    --name ax-chatbot \
    --gpus all \
    -p 8000:8000 \
    -e USE_4BIT=true \
    -e MODEL_NAME="skt/A.X-3.1-Light" \
    -e CUDA_VISIBLE_DEVICES=0 \
    -v /home/isangjae/model_cache:/root/.cache/huggingface \
    ax-chatbot:latest

echo "⏳ 서버 시작 대기 중..."
sleep 30

echo "📋 컨테이너 상태:"
docker ps -a | grep ax-chatbot

echo "📋 컨테이너 로그:"
docker logs --tail 50 ax-chatbot

echo "✅ 배포 완료!"