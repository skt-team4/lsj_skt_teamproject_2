#!/usr/bin/env python3
"""
A.X-3.1-Light 4bit 양자화 테스트 서버
"""
from fastapi import FastAPI
from pydantic import BaseModel
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
import datetime
import uvicorn
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="A.X-3.1-Light 4bit Server")

# 전역 변수
model = None
tokenizer = None

class ChatRequest(BaseModel):
    message: str
    user_id: str = "guest"

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

@app.get("/")
def root():
    return {
        "service": "A.X-3.1-Light 4bit Server",
        "status": "running",
        "model_loaded": model is not None
    }

@app.get("/health")
def health():
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
        "quantization": "4bit (nf4)"
    }

@app.post("/chat")
async def chat(request: ChatRequest):
    """채팅 응답 생성"""
    if model is None or tokenizer is None:
        return {
            "response": "모델이 아직 로드되지 않았습니다. 잠시 후 다시 시도해주세요.",
            "error": True
        }
    
    try:
        # 프롬프트 생성
        prompt = f"""다음은 사용자와 AI 어시스턴트의 대화입니다.

사용자: {request.message}
어시스턴트:"""
        
        # 토큰화
        inputs = tokenizer(
            prompt,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=512
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
        response = tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        # 프롬프트 제거
        if "어시스턴트:" in response:
            response = response.split("어시스턴트:")[-1].strip()
        
        # GPU 상태
        gpu_status = "4bit 양자화 GPU 모드"
        if torch.cuda.is_available():
            allocated = torch.cuda.memory_allocated(0) / 1024**3
            gpu_status = f"4bit GPU ({allocated:.1f}GB 사용)"
        
        return {
            "response": response,
            "user_id": request.user_id,
            "gpu_status": gpu_status,
            "quantization": "4bit",
            "timestamp": datetime.datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"생성 오류: {str(e)}")
        return {
            "response": "죄송합니다. 응답 생성 중 오류가 발생했습니다.",
            "error": str(e)
        }

if __name__ == "__main__":
    print("🚀 A.X-3.1-Light 4bit 서버 시작...")
    print(f"PyTorch 버전: {torch.__version__}")
    print(f"CUDA 사용 가능: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"GPU: {torch.cuda.get_device_name(0)}")
        print(f"CUDA 버전: {torch.version.cuda}")
    uvicorn.run(app, host="0.0.0.0", port=8000)