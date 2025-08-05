#!/usr/bin/env python3
"""
간단한 챗봇 테스트 - 최소 의존성
"""

import json
import random
from datetime import datetime

# 음식점 데이터 (하드코딩)
RESTAURANTS = {
    "치킨": [
        {"name": "BBQ", "menu": "황금올리브치킨", "price": 18000},
        {"name": "교촌치킨", "menu": "허니콤보", "price": 17000},
        {"name": "굽네치킨", "menu": "볼케이노", "price": 19000}
    ],
    "피자": [
        {"name": "도미노피자", "menu": "슈퍼슈프림", "price": 25000},
        {"name": "피자헛", "menu": "치즈바이트", "price": 23000}
    ],
    "한식": [
        {"name": "김밥천국", "menu": "김치찌개", "price": 6000},
        {"name": "새마을식당", "menu": "7분돼지김치", "price": 8000}
    ],
    "분식": [
        {"name": "엽기떡볶이", "menu": "엽기떡볶이", "price": 14000},
        {"name": "신전떡볶이", "menu": "신전떡볶이", "price": 13000}
    ]
}

def simple_chatbot(user_input):
    """간단한 규칙 기반 챗봇"""
    user_input = user_input.lower()
    
    # 음식 카테고리 찾기
    category = None
    for cat in RESTAURANTS.keys():
        if cat in user_input:
            category = cat
            break
    
    # 가격 관련 키워드
    if any(word in user_input for word in ["만원", "천원", "원", "싸", "저렴"]):
        # 가격대별 추천
        if "만원" in user_input:
            budget = 10000
            recommendations = []
            for cat, restaurants in RESTAURANTS.items():
                for r in restaurants:
                    if r["price"] <= budget:
                        recommendations.append(f"{r['name']}의 {r['menu']} ({r['price']:,}원)")
            
            if recommendations:
                return f"{budget:,}원 이하 메뉴: " + ", ".join(recommendations[:3])
            else:
                return "만원 이하 메뉴를 찾기 어려워요 ㅠㅠ"
    
    # 카테고리별 추천
    if category:
        restaurants = RESTAURANTS[category]
        r = random.choice(restaurants)
        return f"{category} 추천! {r['name']}의 {r['menu']} 어때요? ({r['price']:,}원)"
    
    # 일반 추천
    if any(word in user_input for word in ["뭐", "추천", "먹", "배고파"]):
        all_restaurants = []
        for restaurants in RESTAURANTS.values():
            all_restaurants.extend(restaurants)
        r = random.choice(all_restaurants)
        return f"오늘은 {r['name']}의 {r['menu']} 어떠세요? ({r['price']:,}원)"
    
    # 인사
    if any(word in user_input for word in ["안녕", "하이", "헬로"]):
        return "안녕하세요! 나비얌이에요 🦋 오늘 뭐 드시고 싶으세요?"
    
    # 기본 응답
    return "무엇을 도와드릴까요? 음식 종류나 예산을 알려주세요!"

def main():
    print("=" * 50)
    print("🦋 나비얌 챗봇 (간단 버전)")
    print("=" * 50)
    print("종료하려면 'quit' 또는 'exit'를 입력하세요\n")
    
    while True:
        user_input = input("👤 사용자: ").strip()
        
        if user_input.lower() in ['quit', 'exit', '종료']:
            print("\n👋 안녕히 가세요!")
            break
        
        if not user_input:
            continue
        
        response = simple_chatbot(user_input)
        print(f"🤖 나비얌: {response}\n")

if __name__ == "__main__":
    main()