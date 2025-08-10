#!/usr/bin/env python3
"""
GPU 서버 챗봇과 대화하기
"""
import json
import urllib.request
import urllib.parse

GPU_SERVER = "http://34.22.80.119:8000"

def send_message(message, user_id="user1"):
    """GPU 서버로 메시지 전송"""
    data = json.dumps({
        "message": message,
        "user_id": user_id
    }).encode('utf-8')
    
    req = urllib.request.Request(
        f"{GPU_SERVER}/chat",
        data=data,
        headers={'Content-Type': 'application/json'}
    )
    
    try:
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read())
            return result.get('response', '응답 없음')
    except Exception as e:
        return f"오류: {str(e)}"

def main():
    print("🤖 GPU 서버 챗봇과 대화하기")
    print("=" * 40)
    print("종료: 'quit' 또는 'exit' 입력")
    print()
    
    while True:
        message = input("👤 나: ")
        
        if message.lower() in ['quit', 'exit', '종료']:
            print("👋 대화를 종료합니다.")
            break
        
        response = send_message(message)
        print(f"🤖 챗봇: {response}")
        print()

if __name__ == "__main__":
    main()