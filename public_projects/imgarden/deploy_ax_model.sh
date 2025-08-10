#!/bin/bash

# A.X-3.1-Light 모델 배포 스크립트
echo "🚀 A.X-3.1-Light 모델 GPU 배포 시작..."

SERVER_IP="34.22.80.119"

# 1. 프로젝트 파일 압축
echo "📦 프로젝트 파일 압축 중..."
tar -czf naviyam_ax_deploy.tar.gz \
    --exclude='*.pyc' \
    --exclude='__pycache__' \
    --exclude='.git' \
    --exclude='cache/models/*' \
    ../naviyam_backend_runnable_20250806_112316/

# 2. GPU 서버로 전송
echo "📤 GPU 서버로 파일 전송 중..."
scp naviyam_ax_deploy.tar.gz isangjae@${SERVER_IP}:/home/isangjae/

# 3. GPU 서버에서 실행할 스크립트 생성
cat > setup_ax_model.sh << 'SETUP_SCRIPT'
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
cat > /home/isangjae/naviyam_backend/Dockerfile << 'DOCKERFILE'
FROM nvidia/cuda:12.2.0-runtime-ubuntu22.04

# Python 3.10 설치
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3.10-dev \
    python3-pip \
    git \
    wget \
    && rm -rf /var/lib/apt/lists/*

# 작업 디렉토리 설정
WORKDIR /app

# 프로젝트 파일 복사
COPY . /app/

# Python 패키지 설치 (4bit 양자화 포함)
RUN pip3 install --no-cache-dir \
    torch==2.8.0 \
    transformers==4.48.0 \
    accelerate==1.2.1 \
    bitsandbytes==0.45.1 \
    fastapi==0.115.6 \
    uvicorn==0.34.0 \
    faiss-cpu==1.9.0.post1 \
    numpy==1.26.4 \
    scikit-learn==1.6.1 \
    pandas==2.2.3 \
    sentencepiece==0.2.0 \
    protobuf==5.29.3 \
    peft==0.14.0 \
    GPUtil==1.4.0

# 환경 변수 설정
ENV PYTHONPATH=/app
ENV USE_4BIT=true
ENV MODEL_NAME=skt/A.X-3.1-Light
ENV CUDA_VISIBLE_DEVICES=0

# 포트 설정
EXPOSE 8000

# 모델 사전 다운로드 및 서버 시작 스크립트
RUN echo '#!/bin/bash' > /app/start.sh && \
    echo 'echo "🔄 모델 다운로드 시작..."' >> /app/start.sh && \
    echo 'python3 -c "from transformers import AutoModelForCausalLM, AutoTokenizer; import torch; print(\"Downloading model...\"); tokenizer = AutoTokenizer.from_pretrained(\"skt/A.X-3.1-Light\"); model = AutoModelForCausalLM.from_pretrained(\"skt/A.X-3.1-Light\", load_in_4bit=True, device_map=\"auto\", torch_dtype=torch.float16); print(\"Model loaded successfully!\")"' >> /app/start.sh && \
    echo 'echo "✅ 모델 로드 완료! 서버 시작..."' >> /app/start.sh && \
    echo 'python3 -m uvicorn api.server:app --host 0.0.0.0 --port 8000' >> /app/start.sh && \
    chmod +x /app/start.sh

CMD ["/app/start.sh"]
DOCKERFILE

# models_config.py 수정 (4bit 양자화 강제 활성화)
cat > /home/isangjae/naviyam_backend/models/models_config.py << 'PYTHON_CONFIG'
import os
import torch

# 모델 설정
MODEL_CONFIGS = {
    "ax": {
        "model_name": "skt/A.X-3.1-Light",
        "model_class": "AXModel",
        "max_length": 2048,
        "temperature": 0.7,
        "top_p": 0.9,
        "use_4bit": True,  # 4bit 양자화 강제 활성화
        "device_map": "auto",
        "torch_dtype": torch.float16,
        "load_in_4bit": True,
        "bnb_4bit_compute_dtype": torch.float16,
        "bnb_4bit_use_double_quant": True,
        "bnb_4bit_quant_type": "nf4"
    }
}

# 기본 모델 설정
DEFAULT_MODEL = "ax"

# GPU 설정
USE_CUDA = torch.cuda.is_available()
DEVICE = torch.device("cuda:0" if USE_CUDA else "cpu")

print(f"🔧 Models Config Loaded")
print(f"  - USE_CUDA: {USE_CUDA}")
print(f"  - DEVICE: {DEVICE}")
print(f"  - 4bit Quantization: ENABLED")
print(f"  - Model: {MODEL_CONFIGS['ax']['model_name']}")
PYTHON_CONFIG

# ax_model.py 수정 (4bit 양자화 보장)
cat > /home/isangjae/naviyam_backend/models/ax_model.py << 'PYTHON_MODEL'
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
import logging

logger = logging.getLogger(__name__)

class AXModel:
    def __init__(self, model_config):
        self.config = model_config
        self.model = None
        self.tokenizer = None
        self.device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
        
        logger.info(f"Initializing A.X-3.1-Light with 4bit quantization")
        logger.info(f"Device: {self.device}")
        
    def load(self):
        """모델 로드 (4bit 양자화)"""
        try:
            model_name = self.config.get("model_name", "skt/A.X-3.1-Light")
            
            # 4bit 양자화 설정
            bnb_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_use_double_quant=True,
                bnb_4bit_quant_type="nf4"
            )
            
            logger.info(f"Loading tokenizer from {model_name}")
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
            
            logger.info(f"Loading model with 4bit quantization...")
            self.model = AutoModelForCausalLM.from_pretrained(
                model_name,
                quantization_config=bnb_config,
                device_map="auto",
                torch_dtype=torch.float16,
                trust_remote_code=True
            )
            
            # GPU 메모리 정보 출력
            if torch.cuda.is_available():
                allocated = torch.cuda.memory_allocated(0) / 1024**3
                reserved = torch.cuda.memory_reserved(0) / 1024**3
                logger.info(f"GPU Memory - Allocated: {allocated:.2f}GB, Reserved: {reserved:.2f}GB")
            
            logger.info("✅ Model loaded successfully with 4bit quantization!")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load model: {str(e)}")
            raise
    
    def generate(self, prompt, max_length=512, temperature=0.7, top_p=0.9):
        """텍스트 생성"""
        try:
            # 입력 토큰화
            inputs = self.tokenizer(
                prompt,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=1024
            )
            
            # GPU로 이동
            input_ids = inputs["input_ids"].to(self.model.device)
            attention_mask = inputs["attention_mask"].to(self.model.device)
            
            # 생성
            with torch.no_grad():
                outputs = self.model.generate(
                    input_ids=input_ids,
                    attention_mask=attention_mask,
                    max_new_tokens=max_length,
                    temperature=temperature,
                    top_p=top_p,
                    do_sample=True,
                    pad_token_id=self.tokenizer.pad_token_id,
                    eos_token_id=self.tokenizer.eos_token_id
                )
            
            # 디코딩
            response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            
            # 프롬프트 제거
            if prompt in response:
                response = response.replace(prompt, "").strip()
            
            return response
            
        except Exception as e:
            logger.error(f"Generation error: {str(e)}")
            return "죄송합니다. 응답 생성 중 오류가 발생했습니다."
    
    def unload(self):
        """모델 언로드"""
        if self.model is not None:
            del self.model
            self.model = None
        if self.tokenizer is not None:
            del self.tokenizer
            self.tokenizer = None
        torch.cuda.empty_cache()
        logger.info("Model unloaded and GPU memory cleared")
PYTHON_MODEL

# Docker 이미지 빌드
echo "🔨 Docker 이미지 빌드 중..."
cd /home/isangjae/naviyam_backend
docker build -t ax-chatbot:latest .

# 컨테이너 실행 (충분한 시간 제공)
echo "🚀 컨테이너 시작 (모델 다운로드 포함)..."
docker run -d \
    --name ax-chatbot \
    --gpus all \
    -p 8000:8000 \
    -e USE_4BIT=true \
    -e MODEL_NAME="skt/A.X-3.1-Light" \
    -e CUDA_VISIBLE_DEVICES=0 \
    -v /home/isangjae/model_cache:/root/.cache/huggingface \
    ax-chatbot:latest

echo "⏳ 모델 다운로드 및 로딩 대기 중 (약 5-10분)..."
sleep 30

# 로그 확인
echo "📋 컨테이너 로그:"
docker logs --tail 50 ax-chatbot

echo "✅ 배포 완료!"
echo "테스트: curl http://localhost:8000/health"
SETUP_SCRIPT

# 4. 설정 스크립트 전송 및 실행
echo "📤 설정 스크립트 전송 중..."
scp setup_ax_model.sh isangjae@${SERVER_IP}:/home/isangjae/

echo "🔧 GPU 서버에서 설정 실행 중..."
ssh isangjae@${SERVER_IP} "chmod +x /home/isangjae/setup_ax_model.sh && /home/isangjae/setup_ax_model.sh"

echo "✅ 배포 완료!"
echo "테스트 명령어:"
echo "  curl http://${SERVER_IP}:8000/health"
echo "  python3 gpu_chat.py"