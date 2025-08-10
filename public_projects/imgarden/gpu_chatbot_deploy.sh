#!/bin/bash

# GPU 서버 배포 스크립트
echo "🚀 GPU 챗봇 배포 시작..."

# 1. Python 환경 설정
sudo apt-get update
sudo apt-get install -y python3-pip python3-venv git

# 2. 가상환경 생성
python3 -m venv /home/isangjae/chatbot_env
source /home/isangjae/chatbot_env/bin/activate

# 3. 필수 패키지 설치
pip install --upgrade pip
pip install fastapi uvicorn torch transformers accelerate

# 4. 간단한 GPU 챗봇 생성
cat > /home/isangjae/gpu_chatbot.py << 'PYTHON_CODE'
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import torch
import datetime
import os

app = FastAPI(title="GPU 챗봇 서버")

class ChatRequest(BaseModel):
    message: str
    user_id: str = "guest"

@app.get("/")
def root():
    return {
        "service": "나비얌 GPU 챗봇",
        "status": "running",
        "server": "Google Cloud GPU Instance"
    }

@app.get("/health")
def health():
    gpu_info = {}
    if torch.cuda.is_available():
        gpu_info = {
            "available": True,
            "device_count": torch.cuda.device_count(),
            "device_name": torch.cuda.get_device_name(0),
            "memory_allocated": f"{torch.cuda.memory_allocated(0) / 1e9:.2f} GB",
            "memory_total": f"{torch.cuda.get_device_properties(0).total_memory / 1e9:.2f} GB"
        }
    else:
        gpu_info = {"available": False, "message": "GPU not detected"}
    
    return {
        "status": "healthy",
        "message": "GPU 서버가 정상 작동 중입니다!",
        "timestamp": datetime.datetime.now().isoformat(),
        "gpu": gpu_info,
        "pytorch_version": torch.__version__
    }

@app.post("/chat")
async def chat(request: ChatRequest):
    message = request.message.lower()
    
    # GPU 테스트 연산
    if torch.cuda.is_available():
        device = torch.device("cuda")
        # 간단한 행렬 연산으로 GPU 사용 테스트
        test_tensor = torch.randn(1000, 1000).to(device)
        result = torch.matmul(test_tensor, test_tensor)
        gpu_status = "GPU 사용 중 (NVIDIA Tesla T4)"
    else:
        gpu_status = "CPU 모드"
    
    # 간단한 응답 로직
    responses = {
        "안녕": "안녕하세요! GPU 서버에서 실행 중인 나비얌 챗봇입니다! 🚀",
        "점심": "오늘 점심은 김치찌개 어떠세요? GPU가 빠르게 추천해드립니다!",
        "한식": "비빔밥, 불고기, 된장찌개를 추천합니다! GPU 파워로 선택했어요!",
        "gpu": f"현재 {gpu_status}로 작동 중입니다!",
    }
    
    response_text = "무엇을 도와드릴까요?"
    for keyword, response in responses.items():
        if keyword in message:
            response_text = response
            break
    
    return {
        "response": response_text,
        "user_id": request.user_id,
        "timestamp": datetime.datetime.now().isoformat(),
        "server_info": {
            "type": "GPU Instance",
            "location": "asia-northeast3-b",
            "gpu_status": gpu_status
        }
    }

if __name__ == "__main__":
    import uvicorn
    print("🚀 GPU 챗봇 서버 시작...")
    print(f"PyTorch 버전: {torch.__version__}")
    print(f"CUDA 사용 가능: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"GPU: {torch.cuda.get_device_name(0)}")
    uvicorn.run(app, host="0.0.0.0", port=8000)
PYTHON_CODE

# 5. 서비스 파일 생성
sudo tee /etc/systemd/system/gpu-chatbot.service << 'SERVICE'
[Unit]
Description=GPU Chatbot Service
After=network.target

[Service]
Type=simple
User=isangjae
WorkingDirectory=/home/isangjae
Environment="PATH=/home/isangjae/chatbot_env/bin"
ExecStart=/home/isangjae/chatbot_env/bin/python /home/isangjae/gpu_chatbot.py
Restart=always

[Install]
WantedBy=multi-user.target
SERVICE

# 6. 서비스 시작
sudo systemctl daemon-reload
sudo systemctl enable gpu-chatbot
sudo systemctl start gpu-chatbot

echo "✅ GPU 챗봇 배포 완료!"
echo "테스트: curl http://34.22.80.119:8000/health"