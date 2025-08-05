"""
간단한 테스트용 API 서버
실제 챗봇 로직 없이 하드코딩된 응답만 반환
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
import random

app = FastAPI(title="나비얌 챗봇 Simple API")

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
    user_id: str

class ChatResponse(BaseModel):
    response: str
    user_id: str
    session_id: str
    timestamp: str
    recommendations: list
    follow_up_questions: list
    intent: str
    confidence: float
    metadata: dict

# 하드코딩된 응답들
RESPONSES = {
    "치킨": {
        "response": "치킨 좋은 선택이에요! 🍗",
        "recommendations": [
            {"shop_name": "BBQ", "menu_name": "황금올리브치킨", "price": 18000},
            {"shop_name": "교촌치킨", "menu_name": "허니콤보", "price": 17000},
        ],
        "intent": "FOOD_REQUEST"
    },
    "피자": {
        "response": "피자 먹고 싶으시군요! 🍕",
        "recommendations": [
            {"shop_name": "도미노피자", "menu_name": "슈퍼슈프림", "price": 25000},
            {"shop_name": "피자헛", "menu_name": "치즈바이트", "price": 23000},
        ],
        "intent": "FOOD_REQUEST"
    },
    "default": {
        "response": "맛있는 음식 추천해드릴게요! 😊",
        "recommendations": [
            {"shop_name": "김밥천국", "menu_name": "참치김밥", "price": 3500},
            {"shop_name": "맘스터치", "menu_name": "싸이버거", "price": 5000},
        ],
        "intent": "GENERAL_CHAT"
    }
}

@app.get("/")
async def root():
    return {"message": "나비얌 챗봇 Simple API"}

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }

@app.post("/chat")
async def chat(request: ChatRequest):
    # 메시지에서 키워드 찾기
    message = request.message.lower()
    
    response_data = RESPONSES["default"]
    for keyword, data in RESPONSES.items():
        if keyword in message:
            response_data = data
            break
    
    return ChatResponse(
        response=response_data["response"],
        user_id=request.user_id,
        session_id=f"session_{random.randint(1000, 9999)}",
        timestamp=datetime.now().isoformat(),
        recommendations=response_data["recommendations"],
        follow_up_questions=["다른 메뉴도 볼래?", "가격대는 어떻게 원해?"],
        intent=response_data["intent"],
        confidence=0.95,
        metadata={}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)