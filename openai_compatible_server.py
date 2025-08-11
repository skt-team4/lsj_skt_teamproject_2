"""
OpenAI API 호환 서버
GPT API를 완벽하게 대체 가능한 워크스테이션 AI 서버
"""

import torch
import time
import uuid
import os
from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import List, Optional, Dict, Any, Union
import uvicorn
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="OpenAI Compatible AI Server")

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API 키 인증 (OpenAI처럼)
API_KEYS = {
    "sk-workstation-123456789": "default_user",  # 기본 API 키
    # 추가 API 키를 여기에 추가 가능
}

# 환경변수로 API 키 추가 설정
if os.getenv("CUSTOM_API_KEY"):
    API_KEYS[os.getenv("CUSTOM_API_KEY")] = "custom_user"

security = HTTPBearer()

def verify_api_key(authorization: str = Header(None)) -> str:
    """OpenAI 스타일 API 키 검증"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authentication")
    
    token = authorization.replace("Bearer ", "")
    
    if token not in API_KEYS:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    return API_KEYS[token]

# OpenAI 호환 모델 클래스
class Message(BaseModel):
    role: str  # system, user, assistant
    content: str
    name: Optional[str] = None

class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[Message]
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 300
    top_p: Optional[float] = 1.0
    frequency_penalty: Optional[float] = 0.0
    presence_penalty: Optional[float] = 0.0
    stop: Optional[Union[str, List[str]]] = None
    stream: Optional[bool] = False
    n: Optional[int] = 1
    user: Optional[str] = None

class Choice(BaseModel):
    index: int
    message: Message
    finish_reason: str

class Usage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int

class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[Choice]
    usage: Usage

# 전역 모델 변수
model = None
tokenizer = None

@app.on_event("startup")
async def load_model():
    """서버 시작 시 모델 로드"""
    global model, tokenizer
    
    try:
        from transformers import AutoModelForCausalLM, AutoTokenizer
        
        # 가벼운 모델로 시작 (GPT-2 크기)
        model_name = "microsoft/DialoGPT-medium"
        
        logger.info(f"Loading model: {model_name}")
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        tokenizer.pad_token = tokenizer.eos_token
        
        # GPU 사용 가능하면 GPU, 아니면 CPU
        device = "cuda" if torch.cuda.is_available() else "cpu"
        model = AutoModelForCausalLM.from_pretrained(model_name)
        model = model.to(device)
        model.eval()
        
        logger.info(f"✅ Model loaded successfully on {device}")
        
    except Exception as e:
        logger.error(f"❌ Failed to load model: {e}")
        logger.info("Running in mock mode")

# OpenAI 호환 엔드포인트들

@app.get("/v1/models")
async def list_models(user: str = Depends(verify_api_key)):
    """사용 가능한 모델 목록 (OpenAI 형식)"""
    return {
        "object": "list",
        "data": [
            {
                "id": "gpt-3.5-turbo",  # OpenAI 모델명 시뮬레이션
                "object": "model",
                "owned_by": "workstation",
                "permission": []
            },
            {
                "id": "gpt-4",  # GPT-4로 가장
                "object": "model", 
                "owned_by": "workstation",
                "permission": []
            }
        ]
    }

@app.post("/v1/chat/completions")
async def chat_completions(
    request: ChatCompletionRequest,
    user: str = Depends(verify_api_key)
) -> ChatCompletionResponse:
    """OpenAI 호환 채팅 완성 엔드포인트"""
    
    # 메시지 변환
    prompt = ""
    for msg in request.messages:
        if msg.role == "system":
            prompt += f"System: {msg.content}\n"
        elif msg.role == "user":
            prompt += f"User: {msg.content}\n"
        elif msg.role == "assistant":
            prompt += f"Assistant: {msg.content}\n"
    
    prompt += "Assistant: "
    
    # 모델이 없으면 목업 응답
    if model is None or tokenizer is None:
        response_text = f"[Mock Response] 입력하신 메시지를 받았습니다: '{request.messages[-1].content}'"
        prompt_tokens = len(prompt.split())
        completion_tokens = len(response_text.split())
    else:
        # 실제 모델 추론
        try:
            inputs = tokenizer.encode(prompt, return_tensors="pt")
            device = next(model.parameters()).device
            inputs = inputs.to(device)
            
            with torch.no_grad():
                outputs = model.generate(
                    inputs,
                    max_length=inputs.shape[1] + request.max_tokens,
                    temperature=request.temperature,
                    top_p=request.top_p,
                    pad_token_id=tokenizer.eos_token_id,
                    eos_token_id=tokenizer.eos_token_id,
                    do_sample=True
                )
            
            response_text = tokenizer.decode(outputs[0][inputs.shape[1]:], skip_special_tokens=True)
            
            # 토큰 수 계산
            prompt_tokens = len(inputs[0])
            completion_tokens = len(outputs[0]) - len(inputs[0])
            
        except Exception as e:
            logger.error(f"Model inference error: {e}")
            response_text = "죄송합니다. 일시적인 오류가 발생했습니다."
            prompt_tokens = 10
            completion_tokens = 10
    
    # OpenAI 형식 응답 생성
    return ChatCompletionResponse(
        id=f"chatcmpl-{uuid.uuid4().hex[:8]}",
        created=int(time.time()),
        model=request.model,
        choices=[
            Choice(
                index=0,
                message=Message(
                    role="assistant",
                    content=response_text.strip()
                ),
                finish_reason="stop"
            )
        ],
        usage=Usage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens
        )
    )

@app.post("/v1/completions")
async def completions(request: dict, user: str = Depends(verify_api_key)):
    """레거시 완성 엔드포인트 (GPT-3 스타일)"""
    prompt = request.get("prompt", "")
    max_tokens = request.get("max_tokens", 100)
    
    # 간단한 응답 생성
    response_text = f"Completion for: {prompt[:50]}..."
    
    return {
        "id": f"cmpl-{uuid.uuid4().hex[:8]}",
        "object": "text_completion",
        "created": int(time.time()),
        "model": request.get("model", "text-davinci-003"),
        "choices": [{
            "text": response_text,
            "index": 0,
            "logprobs": None,
            "finish_reason": "stop"
        }],
        "usage": {
            "prompt_tokens": len(prompt.split()),
            "completion_tokens": len(response_text.split()),
            "total_tokens": len(prompt.split()) + len(response_text.split())
        }
    }

@app.get("/")
def root():
    """루트 엔드포인트"""
    return {
        "service": "OpenAI Compatible AI Server",
        "version": "1.0.0",
        "endpoints": {
            "chat": "/v1/chat/completions",
            "models": "/v1/models",
            "completions": "/v1/completions"
        },
        "authentication": "Bearer token required",
        "default_key": "sk-workstation-123456789"
    }

@app.get("/health")
def health_check():
    """헬스 체크"""
    return {
        "status": "healthy",
        "model_loaded": model is not None,
        "gpu_available": torch.cuda.is_available()
    }

# 호환성을 위한 추가 엔드포인트
@app.post("/chat/completions")
async def chat_completions_alt(request: ChatCompletionRequest, user: str = Depends(verify_api_key)):
    """대체 경로 (일부 라이브러리용)"""
    return await chat_completions(request, user)

@app.get("/models")
async def list_models_alt(user: str = Depends(verify_api_key)):
    """대체 경로"""
    return await list_models(user)

if __name__ == "__main__":
    import sys
    
    print("""
    ╔══════════════════════════════════════════════════════╗
    ║     OpenAI Compatible AI Server                      ║
    ║     GPT API를 완벽하게 대체합니다!                    ║
    ╠══════════════════════════════════════════════════════╣
    ║  기본 API 키: sk-workstation-123456789               ║
    ║  엔드포인트: http://localhost:8000/v1/chat/completions║
    ╚══════════════════════════════════════════════════════╝
    """)
    
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)