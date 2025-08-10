# 워크스테이션 AI 서버 구축 가이드

## 📋 사전 요구사항 체크리스트

### 하드웨어 최소 사양
- [ ] GPU: NVIDIA RTX 3060 (12GB) 이상
- [ ] RAM: 32GB 이상
- [ ] 저장공간: 100GB 이상 여유
- [ ] 네트워크: 안정적인 인터넷 연결

### 소프트웨어 요구사항
- [ ] Ubuntu 20.04+ 또는 Windows 10/11
- [ ] NVIDIA 드라이버 (525.x 이상)
- [ ] CUDA 11.8 또는 12.1
- [ ] Python 3.8-3.10
- [ ] Docker (선택사항)

## 🚀 Step 1: 워크스테이션 환경 설정

### 1.1 GPU 환경 확인
```bash
# NVIDIA 드라이버 확인
nvidia-smi

# CUDA 버전 확인
nvcc --version

# PyTorch GPU 지원 확인
python -c "import torch; print(torch.cuda.is_available())"
```

### 1.2 Python 환경 구성
```bash
# 가상환경 생성
python -m venv naviyam_gpu_env
source naviyam_gpu_env/bin/activate  # Linux/Mac
# 또는
naviyam_gpu_env\Scripts\activate  # Windows

# 필수 패키지 설치
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
pip install fastapi uvicorn transformers accelerate bitsandbytes
```

## 🖥️ Step 2: AI 서버 로컬 실행

### 2.1 나비얌 백엔드 복사
```bash
# 워크스테이션에 프로젝트 복사
scp -r public_projects/naviyam_backend_runnable_20250806_112316 workstation:/home/user/
```

### 2.2 GPU 최적화 서버 파일 생성
```python
# gpu_server.py
import torch
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from transformers import AutoModelForCausalLM, AutoTokenizer
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Naviyam GPU Server")

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str
    user_id: str = "default"
    session_id: str = "default"

class ChatResponse(BaseModel):
    response: str
    recommendations: list = []

# 전역 모델 변수
model = None
tokenizer = None

@app.on_event("startup")
async def load_model():
    global model, tokenizer
    
    # GPU 메모리 확인
    if torch.cuda.is_available():
        gpu_mem = torch.cuda.get_device_properties(0).total_memory / 1024**3
        logger.info(f"GPU 메모리: {gpu_mem:.1f}GB")
    
    # 모델 로드 (4bit 양자화)
    model_name = "maywell/EXAONE-3.0-7.8B-Instruct"  # 또는 더 작은 모델
    
    from transformers import BitsAndBytesConfig
    quantization_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_use_double_quant=True,
    )
    
    try:
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModelForCausalLM.from_pretrained(
            model_name,
            quantization_config=quantization_config,
            device_map="auto",
            torch_dtype=torch.float16,
        )
        logger.info("모델 로드 완료")
    except Exception as e:
        logger.error(f"모델 로드 실패: {e}")
        # 폴백: 더 작은 모델 사용
        model_name = "microsoft/DialoGPT-medium"
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModelForCausalLM.from_pretrained(model_name).cuda()

@app.get("/")
def root():
    return {"status": "Naviyam GPU Server Running", "gpu": torch.cuda.is_available()}

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "gpu_available": torch.cuda.is_available(),
        "model_loaded": model is not None
    }

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    try:
        # 입력 토큰화
        inputs = tokenizer.encode(request.message, return_tensors="pt").cuda()
        
        # 생성
        with torch.no_grad():
            outputs = model.generate(
                inputs,
                max_length=200,
                temperature=0.7,
                do_sample=True,
                pad_token_id=tokenizer.eos_token_id
            )
        
        # 디코딩
        response = tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        return ChatResponse(
            response=response,
            recommendations=[]
        )
    
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### 2.3 서버 실행 스크립트
```bash
# run_gpu_server.sh
#!/bin/bash

# GPU 메모리 정리
nvidia-smi
echo "GPU 메모리 정리 중..."
sudo fuser -k /dev/nvidia*

# 환경 변수 설정
export CUDA_VISIBLE_DEVICES=0
export PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512

# 서버 실행
source naviyam_gpu_env/bin/activate
python gpu_server.py
```

## 🌐 Step 3: 외부 접속 설정

### 옵션 A: ngrok (가장 간단)
```bash
# ngrok 설치
curl -s https://ngrok-agent.s3.amazonaws.com/ngrok.asc | sudo tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null
echo "deb https://ngrok-agent.s3.amazonaws.com buster main" | sudo tee /etc/apt/sources.list.d/ngrok.list
sudo apt update && sudo apt install ngrok

# 계정 설정 (무료 가입 후)
ngrok config add-authtoken YOUR_AUTH_TOKEN

# 터널 실행
ngrok http 8000

# 출력 예시:
# Forwarding https://abc123.ngrok.io -> http://localhost:8000
```

### 옵션 B: Cloudflare Tunnel (더 안정적)
```bash
# cloudflared 설치
wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared-linux-amd64.deb

# 터널 생성
cloudflared tunnel create naviyam-gpu

# 설정 파일 생성
cat > ~/.cloudflared/config.yml << EOF
tunnel: naviyam-gpu
credentials-file: /home/user/.cloudflared/[TUNNEL_ID].json

ingress:
  - hostname: naviyam-gpu.yourdomain.com
    service: http://localhost:8000
  - service: http_status:404
EOF

# 터널 실행
cloudflared tunnel run naviyam-gpu
```

### 옵션 C: 포트 포워딩 (고정 IP 필요)
```bash
# 라우터 설정에서 포트 포워딩
# 외부 포트 8000 -> 내부 IP:8000

# 방화벽 설정
sudo ufw allow 8000/tcp

# DDNS 설정 (동적 IP인 경우)
# DuckDNS, No-IP 등 사용
```

## 🔗 Step 4: Cloud Run과 연동

### 4.1 Cloud Run 서비스 수정
```python
# public_projects/naviyam_backend_runnable_20250806_112316/api/server.py 수정

import os
import requests
from fastapi import FastAPI, HTTPException

# 워크스테이션 GPU 서버 URL
GPU_SERVER_URL = os.getenv("GPU_SERVER_URL", "https://your-tunnel.ngrok.io")

@app.post("/chat")
async def chat(request: ChatRequest):
    try:
        # GPU 서버로 전달
        response = requests.post(
            f"{GPU_SERVER_URL}/chat",
            json=request.dict(),
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            # 폴백: 간단한 응답
            return {
                "response": "GPU 서버 연결 실패. 기본 응답입니다.",
                "recommendations": []
            }
    
    except requests.exceptions.RequestException as e:
        logger.error(f"GPU server error: {e}")
        # 폴백 처리
        return {
            "response": "현재 서비스가 원활하지 않습니다. 잠시 후 다시 시도해주세요.",
            "recommendations": []
        }
```

### 4.2 Cloud Run 재배포
```bash
# 환경 변수와 함께 배포
gcloud run deploy nabiyam-chatbot-web \
  --source . \
  --set-env-vars GPU_SERVER_URL=https://your-tunnel.ngrok.io \
  --region asia-northeast3 \
  --project rational-autumn-467006-e2
```

## 🔒 Step 5: 보안 및 모니터링

### 5.1 API 키 인증 추가
```python
# gpu_server.py에 추가
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Depends

security = HTTPBearer()

API_KEY = os.getenv("API_KEY", "your-secret-key")

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if credentials.credentials != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API Key")
    return credentials.credentials

@app.post("/chat", dependencies=[Depends(verify_token)])
async def chat(request: ChatRequest):
    # 기존 코드
```

### 5.2 모니터링 설정
```python
# monitoring.py
import psutil
import GPUtil
from datetime import datetime

def log_system_status():
    # CPU 사용률
    cpu_percent = psutil.cpu_percent(interval=1)
    
    # RAM 사용률
    ram = psutil.virtual_memory()
    
    # GPU 상태
    gpus = GPUtil.getGPUs()
    
    status = {
        "timestamp": datetime.now().isoformat(),
        "cpu_percent": cpu_percent,
        "ram_percent": ram.percent,
        "gpu_memory": gpus[0].memoryUsed if gpus else 0,
        "gpu_util": gpus[0].load * 100 if gpus else 0
    }
    
    # 로그 파일에 저장
    with open("system_monitor.log", "a") as f:
        f.write(f"{status}\n")
    
    return status
```

### 5.3 자동 재시작 설정
```bash
# systemd 서비스 생성
sudo nano /etc/systemd/system/naviyam-gpu.service

[Unit]
Description=Naviyam GPU Server
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/home/user/naviyam
ExecStart=/home/user/naviyam_gpu_env/bin/python gpu_server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target

# 서비스 활성화
sudo systemctl enable naviyam-gpu
sudo systemctl start naviyam-gpu
```

## 📊 성능 최적화 팁

### 1. 모델 캐싱
```python
# 모델을 메모리에 유지
from functools import lru_cache

@lru_cache(maxsize=1)
def get_model():
    return load_model()
```

### 2. 배치 처리
```python
# 여러 요청을 모아서 처리
from asyncio import Queue
batch_queue = Queue(maxsize=10)

async def batch_inference():
    batch = []
    while len(batch) < 5:
        request = await batch_queue.get()
        batch.append(request)
    
    # 배치 처리
    results = model.generate_batch(batch)
    return results
```

### 3. GPU 메모리 관리
```python
# 주기적으로 메모리 정리
import gc
torch.cuda.empty_cache()
gc.collect()
```

## 🎯 최종 체크리스트

- [ ] GPU 서버 정상 실행 확인
- [ ] 외부 접속 URL 생성 완료
- [ ] Cloud Run 환경변수 설정
- [ ] API 키 설정
- [ ] 모니터링 설정
- [ ] 자동 재시작 설정
- [ ] 테스트 완료

## 문제 해결

### GPU 메모리 부족
```bash
# 더 작은 모델 사용
model_name = "microsoft/DialoGPT-medium"  # 345M

# 또는 8bit 양자화
load_in_8bit=True
```

### 네트워크 불안정
```bash
# 재시도 로직 추가
max_retries = 3
retry_delay = 5
```

### 전원 관리
```bash
# GPU 절전 모드 비활성화
sudo nvidia-smi -pm 1
```