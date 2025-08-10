#!/usr/bin/env python3
"""
Naviyam API 테스트 스크립트
"""

import requests
import json

# API 엔드포인트
BASE_URL = "http://localhost:8000"

def test_health():
    """헬스체크 테스트"""
    print("1. 헬스체크 테스트...")
    response = requests.get(f"{BASE_URL}/health")
    print(f"   상태: {response.status_code}")
    print(f"   응답: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    print()

def test_chat():
    """채팅 API 테스트"""
    print("2. 채팅 API 테스트...")
    
    # OpenAI 호환 API 테스트
    payload = {
        "model": "naviyam-chat",
        "messages": [
            {"role": "user", "content": "치킨 먹고 싶어!"}
        ],
        "temperature": 0.7,
        "max_tokens": 500
    }
    
    response = requests.post(
        f"{BASE_URL}/v1/chat/completions",
        json=payload,
        headers={"Content-Type": "application/json"}
    )
    
    print(f"   상태: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"   응답: {result['choices'][0]['message']['content']}")
    else:
        print(f"   오류: {response.text}")
    print()

def test_legacy_chat():
    """레거시 채팅 API 테스트"""
    print("3. 레거시 채팅 API 테스트...")
    
    payload = {
        "message": "피자 추천해줘",
        "user_id": "test_user_001",
        "session_id": "test_session"
    }
    
    response = requests.post(
        f"{BASE_URL}/chat",
        json=payload,
        headers={"Content-Type": "application/json"}
    )
    
    print(f"   상태: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"   응답: {result.get('response', 'No response')}")
    else:
        print(f"   오류: {response.text}")
    print()

if __name__ == "__main__":
    print("="*50)
    print("Naviyam API 테스트 시작")
    print("="*50)
    print()
    
    try:
        test_health()
        test_chat()
        test_legacy_chat()
        
        print("="*50)
        print("테스트 완료!")
        print("API 문서: http://localhost:8000/docs")
        print("="*50)
        
    except requests.exceptions.ConnectionError:
        print("❌ 서버에 연결할 수 없습니다.")
        print("   서버가 실행 중인지 확인하세요.")
    except Exception as e:
        print(f"❌ 오류 발생: {e}")