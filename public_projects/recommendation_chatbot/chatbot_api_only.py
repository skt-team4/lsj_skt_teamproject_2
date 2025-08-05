"""
채팅 입출력만 처리하는 간단한 API 서버
UI는 모두 프론트엔드에서 처리
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
import random

app = FastAPI(title="나비얌 채팅 API")

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 요청/응답 모델
class ChatRequest(BaseModel):
    message: str
    user_id: str = "default"

class ChatResponse(BaseModel):
    reply: str
    timestamp: str

# 간단한 응답 로직
def get_chatbot_reply(message: str) -> str:
    """메시지에 따른 응답 생성"""
    message_lower = message.lower()
    
    # 음식 관련 키워드와 응답
    food_responses = {
        "치킨": [
            "BBQ 황금올리브치킨 어때요? 18,000원이에요!",
            "교촌치킨 허니콤보도 맛있어요! 17,000원!",
            "오늘은 치킨이 땡기는 날이네요! 🍗"
        ],
        "피자": [
            "도미노피자 페퍼로니 추천해요! 20,000원부터!",
            "피자헛 치즈크러스트 인기 많아요!",
            "피자 좋은 선택이에요! 🍕"
        ],
        "햄버거": [
            "맘스터치 싸이버거 5,500원에 든든해요!",
            "맥도날드 빅맥세트는 어떠세요?",
            "버거킹 와퍼도 맛있어요!"
        ],
        "한식": [
            "김밥천국에서 김치찌개 6,000원!",
            "백반집 제육볶음 7,000원에 집밥 느낌!",
            "오늘은 든든한 한식이 좋겠네요!"
        ],
        "중식": [
            "홍콩반점 짜장면 6,000원! 든든해요!",
            "중국집 짬뽕 7,000원! 시원하고 매콤해요!",
            "탕수육도 함께 어때요? 🥟"
        ],
        "짜장": [
            "홍콩반점 짜장면 6,000원! 인기 메뉴예요!",
            "중화요리 짜장면 배달 어때요?",
            "짜장면에 탕수육 세트 추천!"
        ],
        "짬뽕": [
            "중국집 짬뽕 7,000원! 해물 가득!",
            "매운 짬뽕으로 속 풀어요!",
            "짬뽕에 군만두 추가 어때요?"
        ],
        "삼겹살": [
            "고기집 삼겹살 1인분 12,000원!",
            "삼겹살에 된장찌개 세트 맛있어요!",
            "오늘은 삼겹살 구이 어때요? 🥓"
        ],
        "고기": [
            "소고기, 돼지고기, 닭고기 뭐가 좋으세요?",
            "고기집 삼겹살 12,000원부터!",
            "구이류 좋아하시면 삼겹살, 갈비 추천!"
        ],
        "구이": [
            "삼겹살구이 12,000원! 인기 메뉴!",
            "닭갈비도 맛있어요! 11,000원!",
            "생선구이 백반 8,000원도 좋아요!"
        ],
        "김밥": [
            "김밥천국 참치김밥 3,500원!",
            "김밥 한 줄에 라면 어때요?",
            "김밥 종류 많아요! 야채, 참치, 김치 다 있어요!"
        ],
        "분식": [
            "떡볶이 3,000원부터! 김밥이랑 세트로!",
            "라면, 김밥, 떡볶이 다 있어요!",
            "분식집 순대도 맛있어요!"
        ],
        "라면": [
            "김밥천국 라면 3,000원!",
            "라면에 김밥 세트 6,000원!",
            "매운 라면? 순한 라면?"
        ]
    }
    
    # 예산 관련
    if "만원" in message_lower or "천원" in message_lower:
        if "5천원" in message_lower or "오천원" in message_lower:
            return "5천원이면 김밥천국 김밥(3,500원), 맘스터치 불고기버거(4,900원) 가능해요!"
        elif "만원" in message_lower:
            return "만원이면 대부분 메뉴 가능해요! 치킨은 조금 더 필요하지만 피자, 햄버거, 한식 다 OK!"
        else:
            return "예산 알려주시면 맞춤 추천해드릴게요!"
    
    # 음식 키워드 찾기
    for food, responses in food_responses.items():
        if food in message_lower:
            return random.choice(responses)
    
    # 인사말
    if any(word in message_lower for word in ["안녕", "하이", "헬로"]):
        return "안녕하세요! 나비얌이에요 🦋 오늘 뭐 드시고 싶으세요?"
    
    # 감사 인사
    if any(word in message_lower for word in ["고마워", "감사", "땡큐"]):
        return "천만에요! 맛있게 드세요! 😊"
    
    # "밥" 키워드 처리
    if "밥" in message_lower:
        return "오늘 식사는 뭘로 할까요? 한식, 중식, 분식, 고기 다 있어요!"
    
    # 기본 응답
    general_responses = [
        "어떤 음식 종류를 좋아하세요? 치킨, 피자, 한식, 중식, 분식 다 있어요!",
        "예산은 얼마정도 생각하세요?",
        "오늘은 뭐가 땡기세요? 🤔",
        "제가 맛있는 거 추천해드릴게요! 어떤 종류 좋아하세요?",
        "한식, 중식, 치킨, 피자, 분식 중에 뭐가 좋으세요?"
    ]
    
    return random.choice(general_responses)

@app.get("/")
async def root():
    return {"message": "나비얌 채팅 API", "version": "1.0"}

@app.post("/chat")
async def chat(request: ChatRequest):
    """채팅 메시지를 받아서 응답 반환"""
    
    # 응답 생성
    reply = get_chatbot_reply(request.message)
    
    # 응답 반환
    return ChatResponse(
        reply=reply,
        timestamp=datetime.now().isoformat()
    )

@app.get("/health")
async def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    import os
    
    # Cloud Run은 PORT 환경변수를 사용
    port = int(os.environ.get("PORT", 8080))
    
    print("🚀 나비얌 채팅 API 서버")
    print(f"📍 http://0.0.0.0:{port}")
    print("💬 POST /chat 로 메시지 전송\n")
    
    uvicorn.run(app, host="0.0.0.0", port=port)