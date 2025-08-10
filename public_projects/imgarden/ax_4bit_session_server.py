#!/usr/bin/env python3
"""
A.X-3.1-Light 4bit 양자화 서버 - 세션 지원 버전
대화 컨텍스트를 유지하여 연속적인 대화 가능
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
import datetime
import uvicorn
import logging
from collections import defaultdict
import uuid

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="A.X-3.1-Light 4bit Server with Session",
    description="세션 기반 대화 지원 - Swagger UI에서 연속 대화 테스트 가능",
    version="1.0.0"
)

# CORS 설정 (웹 UI 접근용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 전역 변수
model = None
tokenizer = None
conversation_history = defaultdict(list)  # 세션별 대화 기록

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    max_history: Optional[int] = 5  # 유지할 대화 턴 수

class SessionRequest(BaseModel):
    session_id: str

class ChatResponse(BaseModel):
    response: str
    session_id: str
    turn_count: int
    gpu_status: str
    quantization: str
    timestamp: str

@app.on_event("startup")
async def startup_event():
    """서버 시작 시 모델 로드"""
    global model, tokenizer
    
    logger.info("🚀 A.X-3.1-Light 모델 로딩 시작...")
    
    try:
        # 4bit 양자화 설정
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4"
        )
        
        model_name = "skt/A.X-3.1-Light"
        
        # 토크나이저 로드
        logger.info(f"토크나이저 로드: {model_name}")
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token
        
        # 모델 로드 (4bit 양자화)
        logger.info("모델 로드 중... (시간이 걸릴 수 있습니다)")
        model = AutoModelForCausalLM.from_pretrained(
            model_name,
            quantization_config=bnb_config,
            device_map="auto",
            torch_dtype=torch.float16,
            trust_remote_code=True
        )
        
        # GPU 메모리 정보
        if torch.cuda.is_available():
            allocated = torch.cuda.memory_allocated(0) / 1024**3
            reserved = torch.cuda.memory_reserved(0) / 1024**3
            logger.info(f"✅ GPU 메모리 - 할당: {allocated:.2f}GB, 예약: {reserved:.2f}GB")
        
        logger.info("✅ 모델 로드 완료! 4bit 양자화 활성화됨")
        
    except Exception as e:
        logger.error(f"❌ 모델 로드 실패: {str(e)}")
        raise

@app.get("/", tags=["Info"])
def root():
    """서비스 정보"""
    return {
        "service": "A.X-3.1-Light 4bit Server with Session",
        "status": "running",
        "model_loaded": model is not None,
        "active_sessions": len(conversation_history),
        "endpoints": {
            "/docs": "Swagger UI - 대화 테스트",
            "/chat": "대화 API (세션 지원)",
            "/session/new": "새 세션 생성",
            "/session/history": "세션 대화 기록 조회",
            "/session/clear": "세션 초기화"
        }
    }

@app.get("/health", tags=["Info"])
def health():
    """헬스체크"""
    gpu_info = {}
    if torch.cuda.is_available():
        gpu_info = {
            "available": True,
            "device_name": torch.cuda.get_device_name(0),
            "memory_allocated": f"{torch.cuda.memory_allocated(0) / 1e9:.2f} GB",
            "memory_reserved": f"{torch.cuda.memory_reserved(0) / 1e9:.2f} GB",
            "memory_total": f"{torch.cuda.get_device_properties(0).total_memory / 1e9:.2f} GB",
            "cuda_version": torch.version.cuda
        }
    else:
        gpu_info = {"available": False}
    
    return {
        "status": "healthy",
        "message": "4bit 양자화 서버가 정상 작동 중입니다!",
        "gpu": gpu_info,
        "pytorch_version": torch.__version__,
        "model_loaded": model is not None,
        "quantization": "4bit (nf4)",
        "active_sessions": len(conversation_history)
    }

@app.post("/session/new", tags=["Session"], response_model=dict)
async def create_session():
    """새 세션 생성"""
    session_id = str(uuid.uuid4())
    conversation_history[session_id] = []
    return {
        "session_id": session_id,
        "message": "새 세션이 생성되었습니다. 이 session_id를 사용하여 연속 대화가 가능합니다.",
        "created_at": datetime.datetime.now().isoformat()
    }

@app.post("/session/history", tags=["Session"])
async def get_history(request: SessionRequest):
    """세션 대화 기록 조회"""
    if request.session_id not in conversation_history:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다")
    
    history = conversation_history[request.session_id]
    return {
        "session_id": request.session_id,
        "turn_count": len(history),
        "history": history
    }

@app.post("/session/clear", tags=["Session"])
async def clear_session(request: SessionRequest):
    """세션 초기화"""
    if request.session_id in conversation_history:
        conversation_history[request.session_id] = []
        return {"message": "세션이 초기화되었습니다", "session_id": request.session_id}
    else:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다")

@app.post("/chat", tags=["Chat"], response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    대화 API - 세션을 통한 연속 대화 지원
    
    사용 방법:
    1. /session/new로 session_id 생성
    2. session_id를 포함하여 대화 요청
    3. 대화 컨텍스트가 자동으로 유지됩니다
    """
    if model is None or tokenizer is None:
        raise HTTPException(status_code=503, detail="모델이 아직 로드되지 않았습니다")
    
    try:
        # 세션 ID 처리
        if not request.session_id:
            request.session_id = str(uuid.uuid4())
        
        # 대화 기록 가져오기
        history = conversation_history[request.session_id]
        
        # 프롬프트 생성 (대화 기록 포함)
        prompt_parts = ["다음은 사용자와 AI 어시스턴트의 대화입니다.\n"]
        
        # 최근 대화 기록 추가
        for turn in history[-request.max_history:]:
            prompt_parts.append(f"사용자: {turn['user']}")
            prompt_parts.append(f"어시스턴트: {turn['assistant']}")
        
        # 현재 메시지 추가
        prompt_parts.append(f"사용자: {request.message}")
        prompt_parts.append("어시스턴트:")
        
        prompt = "\n".join(prompt_parts)
        
        # 토큰화
        inputs = tokenizer(
            prompt,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=1024
        )
        
        # GPU로 이동
        input_ids = inputs["input_ids"].to(model.device)
        attention_mask = inputs["attention_mask"].to(model.device)
        
        # 생성
        with torch.no_grad():
            outputs = model.generate(
                input_ids=input_ids,
                attention_mask=attention_mask,
                max_new_tokens=256,
                temperature=0.7,
                top_p=0.9,
                do_sample=True,
                pad_token_id=tokenizer.pad_token_id,
                eos_token_id=tokenizer.eos_token_id
            )
        
        # 디코딩
        full_response = tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        # 응답 추출
        if "어시스턴트:" in full_response:
            response = full_response.split("어시스턴트:")[-1].strip()
        else:
            response = full_response[len(prompt):].strip()
        
        # 대화 기록 저장
        history.append({
            "user": request.message,
            "assistant": response,
            "timestamp": datetime.datetime.now().isoformat()
        })
        
        # GPU 상태
        gpu_status = "4bit 양자화 GPU 모드"
        if torch.cuda.is_available():
            allocated = torch.cuda.memory_allocated(0) / 1024**3
            gpu_status = f"4bit GPU ({allocated:.1f}GB 사용)"
        
        return ChatResponse(
            response=response,
            session_id=request.session_id,
            turn_count=len(history),
            gpu_status=gpu_status,
            quantization="4bit",
            timestamp=datetime.datetime.now().isoformat()
        )
        
    except Exception as e:
        logger.error(f"생성 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"응답 생성 중 오류: {str(e)}")

@app.get("/session/list", tags=["Session"])
async def list_sessions():
    """활성 세션 목록"""
    sessions = []
    for session_id, history in conversation_history.items():
        sessions.append({
            "session_id": session_id,
            "turn_count": len(history),
            "last_activity": history[-1]["timestamp"] if history else None
        })
    return {"active_sessions": len(sessions), "sessions": sessions}

if __name__ == "__main__":
    print("🚀 A.X-3.1-Light 4bit 세션 서버 시작...")
    print(f"PyTorch 버전: {torch.__version__}")
    print(f"CUDA 사용 가능: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"GPU: {torch.cuda.get_device_name(0)}")
        print(f"CUDA 버전: {torch.version.cuda}")
    print("\n📚 Swagger UI: http://localhost:8000/docs")
    print("💡 /session/new로 세션을 생성한 후 대화를 시작하세요!")
    uvicorn.run(app, host="0.0.0.0", port=8000)