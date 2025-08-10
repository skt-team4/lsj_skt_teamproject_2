from fastapi import FastAPI
from fastapi.responses import JSONResponse
import torch
import uvicorn
import datetime

app = FastAPI()

@app.get("/")
def root():
    return {"message": "GPU 챗봇 서버입니다"}

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "message": "GPU 서버에서 실행 중!",
        "server": "Google Cloud GPU Instance (T4)",
        "pytorch_version": torch.__version__,
        "cuda_available": torch.cuda.is_available(),
        "timestamp": datetime.datetime.now().isoformat()
    }

@app.post("/chat")
async def chat(request: dict):
    message = request.get("message", "")
    user_id = request.get("user_id", "guest")
    
    # GPU에서 간단한 연산 수행 (데모용)
    if torch.cuda.is_available():
        device = torch.device("cuda")
        tensor = torch.randn(100, 100).to(device)
        result = torch.matmul(tensor, tensor)
        gpu_used = "NVIDIA Tesla T4 GPU 사용"
    else:
        gpu_used = "CPU 사용 (GPU 미감지)"
    
    responses = {
        "안녕": "안녕하세요! GPU 서버에서 인사드립니다! 🚀",
        "점심": "GPU 서버가 추천하는 오늘의 메뉴는 김치찌개입니다!",
        "한식": "비빔밥, 불고기, 된장찌개를 추천합니다!",
    }
    
    # 키워드 매칭
    response_text = "GPU 서버입니다. 무엇을 도와드릴까요?"
    for keyword, response in responses.items():
        if keyword in message:
            response_text = response
            break
    
    return {
        "response": response_text,
        "user_id": user_id,
        "server_type": "GCP GPU Instance",
        "gpu_info": gpu_used,
        "timestamp": datetime.datetime.now().isoformat()
    }

if __name__ == "__main__":
    print("🚀 GPU 챗봇 서버 시작...")
    print(f"PyTorch 버전: {torch.__version__}")
    print(f"CUDA 사용 가능: {torch.cuda.is_available()}")
    uvicorn.run(app, host="0.0.0.0", port=8000)