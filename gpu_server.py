"""
Naviyam GPU Server - 워크스테이션용 AI 서버
간소화된 버전으로 즉시 실행 가능
"""

import torch
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Naviyam GPU Server")

# CORS 설정 (모든 출처 허용)
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
    """서버 시작 시 모델 로드"""
    global model, tokenizer
    
    # GPU 체크
    if torch.cuda.is_available():
        device = "cuda"
        gpu_name = torch.cuda.get_device_name(0)
        gpu_mem = torch.cuda.get_device_properties(0).total_memory / 1024**3
        logger.info(f"GPU 감지: {gpu_name} ({gpu_mem:.1f}GB)")
    else:
        device = "cpu"
        logger.warning("GPU를 찾을 수 없습니다. CPU 모드로 실행됩니다.")
    
    # 간단한 모델로 시작 (테스트용)
    try:
        from transformers import AutoModelForCausalLM, AutoTokenizer
        
        # 경량 모델 사용 (빠른 테스트를 위해)
        model_name = "microsoft/DialoGPT-small"  # 117M 파라미터
        
        logger.info(f"모델 로딩 중: {model_name}")
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        tokenizer.pad_token = tokenizer.eos_token
        
        model = AutoModelForCausalLM.from_pretrained(model_name)
        model = model.to(device)
        model.eval()
        
        logger.info(f"✅ 모델 로드 완료 (Device: {device})")
        
    except Exception as e:
        logger.error(f"❌ 모델 로드 실패: {e}")
        logger.info("폴백: 더미 응답 모드로 실행")

@app.get("/")
def root():
    """루트 엔드포인트"""
    return {
        "service": "Naviyam GPU Server",
        "status": "running",
        "gpu_available": torch.cuda.is_available(),
        "model_loaded": model is not None
    }

@app.get("/health")
def health_check():
    """헬스 체크"""
    gpu_info = {}
    if torch.cuda.is_available():
        gpu_info = {
            "gpu_name": torch.cuda.get_device_name(0),
            "gpu_memory_allocated": f"{torch.cuda.memory_allocated(0) / 1024**3:.2f}GB",
            "gpu_memory_cached": f"{torch.cuda.memory_reserved(0) / 1024**3:.2f}GB"
        }
    
    return {
        "status": "healthy",
        "gpu_available": torch.cuda.is_available(),
        "model_loaded": model is not None,
        **gpu_info
    }

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """챗봇 대화 처리"""
    
    # 모델이 없으면 더미 응답
    if model is None or tokenizer is None:
        logger.warning("모델이 로드되지 않았습니다. 더미 응답 반환")
        return ChatResponse(
            response=f"[테스트 응답] 입력하신 메시지: '{request.message}'",
            recommendations=["테스트 추천 1", "테스트 추천 2"]
        )
    
    try:
        # 대화 컨텍스트 구성
        input_text = f"User: {request.message}\nBot:"
        
        # 토큰화
        inputs = tokenizer.encode(input_text, return_tensors="pt")
        if torch.cuda.is_available():
            inputs = inputs.cuda()
        
        # 응답 생성
        with torch.no_grad():
            outputs = model.generate(
                inputs,
                max_length=inputs.shape[1] + 100,
                temperature=0.8,
                do_sample=True,
                top_p=0.9,
                pad_token_id=tokenizer.eos_token_id,
                eos_token_id=tokenizer.eos_token_id
            )
        
        # 디코딩
        full_response = tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        # 봇 응답 부분만 추출
        if "Bot:" in full_response:
            bot_response = full_response.split("Bot:")[-1].strip()
        else:
            bot_response = full_response[len(input_text):].strip()
        
        # 간단한 음식 추천 로직 (하드코딩)
        recommendations = []
        food_keywords = ["배고파", "먹고싶", "음식", "추천", "메뉴"]
        if any(keyword in request.message for keyword in food_keywords):
            recommendations = ["김밥", "떡볶이", "라면"]
        
        return ChatResponse(
            response=bot_response if bot_response else "무엇을 도와드릴까요?",
            recommendations=recommendations
        )
    
    except Exception as e:
        logger.error(f"대화 처리 중 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/inference")
async def inference(request: dict):
    """Cloud Run에서 호출하는 추론 엔드포인트"""
    # /chat과 동일한 로직이지만 다른 형식 지원
    chat_request = ChatRequest(
        message=request.get("message", ""),
        user_id=request.get("user_id", "default"),
        session_id=request.get("session_id", "default")
    )
    return await chat(chat_request)

if __name__ == "__main__":
    # 서버 실행
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    
    print(f"""
    ╔══════════════════════════════════════╗
    ║   Naviyam GPU Server Starting...     ║
    ║   Host: {host:29} ║
    ║   Port: {port:29} ║
    ╚══════════════════════════════════════╝
    """)
    
    uvicorn.run(app, host=host, port=port, reload=False)