#!/bin/bash

echo "🚀 A.X-3.1-Light 4bit 양자화 모델 실행"

# 기존 컨테이너 정리
sudo docker stop ax-4bit 2>/dev/null
sudo docker rm ax-4bit 2>/dev/null

# Docker 이미지 빌드
echo "🔨 Docker 이미지 빌드..."
cd /home/isangjae/imgarden

# Dockerfile 수정 (4bit 양자화 설정)
cat > Dockerfile.ax4bit << 'EOF'
FROM nvidia/cuda:12.2.0-runtime-ubuntu22.04

RUN apt-get update && apt-get install -y \
    python3.10 \
    python3-pip \
    git \
    wget \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 프로젝트 파일 복사
COPY api /app/api
COPY core /app/core
COPY data /app/data
COPY inference /app/inference
COPY models /app/models
COPY nlp /app/nlp
COPY rag /app/rag
COPY recommendation /app/recommendation
COPY training /app/training
COPY utils /app/utils
COPY *.py /app/

# Python 패키지 설치
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

# 4bit 양자화 설정 파일 생성
RUN echo 'import torch' > /app/models/models_config.py && \
    echo 'MODEL_CONFIGS = {' >> /app/models/models_config.py && \
    echo '    "ax": {' >> /app/models/models_config.py && \
    echo '        "model_name": "skt/A.X-3.1-Light",' >> /app/models/models_config.py && \
    echo '        "model_class": "AXModel",' >> /app/models/models_config.py && \
    echo '        "use_4bit": True,' >> /app/models/models_config.py && \
    echo '        "load_in_4bit": True,' >> /app/models/models_config.py && \
    echo '        "device_map": "auto",' >> /app/models/models_config.py && \
    echo '        "torch_dtype": torch.float16' >> /app/models/models_config.py && \
    echo '    }' >> /app/models/models_config.py && \
    echo '}' >> /app/models/models_config.py && \
    echo 'DEFAULT_MODEL = "ax"' >> /app/models/models_config.py

ENV PYTHONPATH=/app
ENV USE_4BIT=true
ENV CUDA_VISIBLE_DEVICES=0

EXPOSE 8000

CMD ["python3", "-m", "uvicorn", "api.server:app", "--host", "0.0.0.0", "--port", "8000"]
EOF

# Docker 이미지 빌드
sudo docker build -f Dockerfile.ax4bit -t ax-4bit:latest .

# 컨테이너 실행
echo "🚀 컨테이너 실행..."
sudo docker run -d \
    --name ax-4bit \
    --gpus all \
    -p 8000:8000 \
    -e USE_4BIT=true \
    -e MODEL_NAME="skt/A.X-3.1-Light" \
    -v /home/isangjae/model_cache:/root/.cache/huggingface \
    ax-4bit:latest

echo "⏳ 서버 시작 대기 중..."
sleep 20

# 상태 확인
echo "📋 컨테이너 상태:"
sudo docker ps | grep ax-4bit

echo "📋 컨테이너 로그:"
sudo docker logs --tail 50 ax-4bit

echo "✅ 완료!"
echo "테스트: curl http://localhost:8000/health"