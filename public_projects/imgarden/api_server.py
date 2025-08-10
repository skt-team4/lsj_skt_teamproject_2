"""
Naviyam Chatbot API Server
FastAPI 기반 REST API 서버
"""

import os
import sys
import json
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, Header, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import uvicorn

# 프로젝트 경로 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from inference.chatbot import NaviyamChatbot
from models.nlu_factory import NLUFactory
from utils.config import NLUConfig
from data.data_structure import UserProfile

# 환경변수 로드
load_dotenv()

# 로깅 설정
logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 전역 변수
chatbot = None
nlu_model = None

# Request/Response 모델
class ChatRequest(BaseModel):
    """채팅 요청 모델"""
    message: str = Field(..., min_length=1, max_length=1000)
    user_id: str = Field(default="default_user", min_length=1, max_length=100)
    session_id: Optional[str] = Field(default=None, max_length=100)
    context: Optional[List[Dict[str, Any]]] = Field(default=None)

class ChatResponse(BaseModel):
    """채팅 응답 모델"""
    response: str
    user_id: str
    session_id: Optional[str] = None
    timestamp: str
    metadata: Optional[Dict[str, Any]] = None
    recommendations: Optional[List[Dict[str, Any]]] = None
    follow_up_questions: Optional[List[str]] = None

class HealthResponse(BaseModel):
    """헬스체크 응답"""
    status: str
    timestamp: str
    model_loaded: bool
    nlu_type: str
    version: str = "1.0.0"

class ErrorResponse(BaseModel):
    """에러 응답"""
    error: str
    detail: str
    timestamp: str

# API Key 검증
async def verify_api_key(x_api_key: str = Header(default=None)):
    """API 키 검증"""
    api_key = os.getenv("API_KEY", "your-api-key-here")
    if api_key != "your-api-key-here" and x_api_key != api_key:
        raise HTTPException(status_code=403, detail="Invalid API Key")
    return True

# Lifespan 관리
@asynccontextmanager
async def lifespan(app: FastAPI):
    """앱 시작/종료 시 실행"""
    global chatbot, nlu_model
    
    # 시작 시
    logger.info("Initializing Naviyam Chatbot API Server...")
    
    try:
        # NLU 설정
        nlu_type = os.getenv("NLU_TYPE", "ax_encoder")
        use_4bit = os.getenv("USE_4BIT", "true").lower() == "true"
        use_trained = os.getenv("USE_TRAINED", "false").lower() == "true"
        
        nlu_config = NLUConfig(
            use_4bit=use_4bit,
            use_trained=use_trained
        )
        
        # NLU 모델 생성
        logger.info(f"Loading NLU model: {nlu_type}")
        nlu_model = NLUFactory.create_nlu_model(
            nlu_type=nlu_type,
            nlu_config=nlu_config
        )
        
        # 챗봇 초기화
        logger.info("Initializing chatbot...")
        chatbot = NaviyamChatbot(
            use_trained_nlu=use_trained,
            use_4bit=use_4bit,
            nlu_model=nlu_model
        )
        
        logger.info("Chatbot initialized successfully!")
        
    except Exception as e:
        logger.error(f"Failed to initialize chatbot: {e}")
        raise
    
    yield
    
    # 종료 시
    logger.info("Shutting down Naviyam Chatbot API Server...")
    if chatbot:
        del chatbot
    if nlu_model:
        del nlu_model

# FastAPI 앱 생성
app = FastAPI(
    title="Naviyam Chatbot API",
    description="나비얌 챗봇 REST API 서버",
    version="1.0.0",
    lifespan=lifespan
)

# CORS 설정
cors_origins = json.loads(os.getenv("CORS_ORIGINS", '["*"]'))
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우트
@app.get("/", response_model=Dict[str, str])
async def root():
    """루트 엔드포인트"""
    return {
        "service": "Naviyam Chatbot API",
        "version": "1.0.0",
        "status": "running"
    }

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """헬스체크 엔드포인트"""
    global chatbot
    
    return HealthResponse(
        status="healthy" if chatbot else "initializing",
        timestamp=datetime.now().isoformat(),
        model_loaded=chatbot is not None,
        nlu_type=os.getenv("NLU_TYPE", "ax_encoder")
    )

@app.post("/chat", response_model=ChatResponse, dependencies=[Depends(verify_api_key)])
async def chat(request: ChatRequest, background_tasks: BackgroundTasks):
    """채팅 엔드포인트"""
    global chatbot
    
    if not chatbot:
        raise HTTPException(status_code=503, detail="Chatbot is not initialized")
    
    try:
        # 채팅 처리
        logger.info(f"Processing chat request from user: {request.user_id}")
        
        response = chatbot.process_message(
            message=request.message,
            user_id=request.user_id
        )
        
        # 응답이 ChatbotResponse 객체인 경우 처리
        if hasattr(response, 'text'):
            response_text = response.text
            recommendations = response.recommendations if hasattr(response, 'recommendations') else None
            follow_up = response.follow_up_questions if hasattr(response, 'follow_up_questions') else None
            metadata = response.metadata if hasattr(response, 'metadata') else None
        else:
            response_text = str(response)
            recommendations = None
            follow_up = None
            metadata = None
        
        # 백그라운드 태스크 (로깅 등)
        background_tasks.add_task(log_chat_interaction, request.user_id, request.message, response_text)
        
        return ChatResponse(
            response=response_text,
            user_id=request.user_id,
            session_id=request.session_id,
            timestamp=datetime.now().isoformat(),
            metadata=metadata,
            recommendations=recommendations,
            follow_up_questions=follow_up
        )
        
    except Exception as e:
        logger.error(f"Chat processing error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/reset/{user_id}", dependencies=[Depends(verify_api_key)])
async def reset_user_context(user_id: str):
    """사용자 컨텍스트 리셋"""
    global chatbot
    
    if not chatbot:
        raise HTTPException(status_code=503, detail="Chatbot is not initialized")
    
    try:
        # 사용자 컨텍스트 리셋 로직
        logger.info(f"Resetting context for user: {user_id}")
        # chatbot.reset_user_context(user_id)  # 구현 필요 시 추가
        
        return {"message": f"Context reset for user {user_id}", "timestamp": datetime.now().isoformat()}
        
    except Exception as e:
        logger.error(f"Reset context error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/users/{user_id}/history", dependencies=[Depends(verify_api_key)])
async def get_user_history(user_id: str, limit: int = 10):
    """사용자 대화 히스토리 조회"""
    global chatbot
    
    if not chatbot:
        raise HTTPException(status_code=503, detail="Chatbot is not initialized")
    
    try:
        # 히스토리 조회 로직
        logger.info(f"Getting history for user: {user_id}")
        # history = chatbot.get_user_history(user_id, limit)  # 구현 필요 시 추가
        
        return {
            "user_id": user_id,
            "history": [],  # 실제 히스토리 데이터
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Get history error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# 백그라운드 태스크
async def log_chat_interaction(user_id: str, message: str, response: str):
    """채팅 인터랙션 로깅"""
    try:
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "user_id": user_id,
            "message": message,
            "response": response[:200]  # 처음 200자만 로깅
        }
        logger.info(f"Chat interaction: {json.dumps(log_data, ensure_ascii=False)}")
    except Exception as e:
        logger.error(f"Logging error: {e}")

# 에러 핸들러
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """HTTP 예외 핸들러"""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error="HTTP Error",
            detail=exc.detail,
            timestamp=datetime.now().isoformat()
        ).dict()
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """일반 예외 핸들러"""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="Internal Server Error",
            detail=str(exc),
            timestamp=datetime.now().isoformat()
        ).dict()
    )

# 메인 실행
if __name__ == "__main__":
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))
    
    uvicorn.run(
        "api_server:app",
        host=host,
        port=port,
        reload=False,
        log_level=os.getenv("LOG_LEVEL", "info").lower()
    )