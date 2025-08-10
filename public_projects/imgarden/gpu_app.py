from fastapi import FastAPI
from pydantic import BaseModel
import torch
import datetime
import uvicorn

app = FastAPI(title="GPU 챗봇 서버")

class ChatRequest(BaseModel):
    message: str
    user_id: str = "guest"

@app.get("/")
def root():
    return {"service": "GPU 챗봇 서버", "status": "running"}

@app.get("/health")
def health():
    gpu_info = {}
    if torch.cuda.is_available():
        gpu_info = {
            "available": True,
            "device_name": torch.cuda.get_device_name(0),
            "memory_total": f"{torch.cuda.get_device_properties(0).total_memory / 1e9:.2f} GB",
            "cuda_version": torch.version.cuda
        }
    else:
        gpu_info = {"available": False}
        
    return {
        "status": "healthy",
        "message": "GPU 서버가 정상 작동 중입니다!",
        "gpu": gpu_info,
        "pytorch_version": torch.__version__
    }

@app.post("/chat")
async def chat(request: ChatRequest):
    # GPU에서 간단한 연산 수행
    if torch.cuda.is_available():
        device = torch.device("cuda")
        # GPU 테스트 연산
        tensor = torch.randn(1000, 1000).to(device)
        result = torch.matmul(tensor, tensor)
        gpu_status = f"GPU 사용 중 ({torch.cuda.get_device_name(0)})"
    else:
        gpu_status = "CPU 모드"
    
    responses = {
        "안녕": "안녕하세요! NVIDIA L4 GPU로 구동되는 챗봇입니다! 🚀",
        "점심": "GPU가 추천하는 오늘의 메뉴는 김치찌개입니다!",
        "한식": "비빔밥, 불고기, 된장찌개를 추천합니다!",
        "gpu": f"현재 {gpu_status}로 작동 중입니다!",
    }
    
    response_text = "GPU 서버입니다. 무엇을 도와드릴까요?"
    for keyword, response in responses.items():
        if keyword in request.message.lower():
            response_text = response
            break
    
    return {
        "response": response_text,
        "user_id": request.user_id,
        "gpu_status": gpu_status,
        "timestamp": datetime.datetime.now().isoformat()
    }

if __name__ == "__main__":
    print("🚀 GPU 챗봇 서버 시작...")
    print(f"PyTorch 버전: {torch.__version__}")
    print(f"CUDA 사용 가능: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"GPU: {torch.cuda.get_device_name(0)}")
        print(f"CUDA 버전: {torch.version.cuda}")
    uvicorn.run(app, host="0.0.0.0", port=8000)