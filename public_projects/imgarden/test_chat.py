#\!/usr/bin/env python3
import json
import urllib.request
import urllib.parse

url = "http://34.22.80.119:8000/chat"
messages = [
    "안녕하세요\! 오늘 점심 메뉴 추천해주세요.",
    "아이가 좋아할만한 한식 메뉴 알려주세요",
    "김치찌개 맛있게 만드는 방법은?"
]

for msg in messages:
    print(f"\n질문: {msg}")
    print("-" * 50)
    
    data = json.dumps({
        "message": msg,
        "user_id": "test_user"
    }).encode('utf-8')
    
    req = urllib.request.Request(
        url,
        data=data,
        headers={'Content-Type': 'application/json'}
    )
    
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read())
            
            print(f"응답: {result.get('response', 'No response')}")
            print(f"GPU 상태: {result.get('gpu_status', 'Unknown')}")
            print(f"양자화: {result.get('quantization', 'Unknown')}")
            
    except Exception as e:
        print(f"오류: {str(e)}")
