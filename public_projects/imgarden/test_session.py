#\!/usr/bin/env python3
import json
import urllib.request

base_url = "http://34.22.80.119:8000"

# 1. 새 세션 생성
print("1. 새 세션 생성...")
req = urllib.request.Request(f"{base_url}/session/new", method='POST')
with urllib.request.urlopen(req) as response:
    result = json.loads(response.read())
    session_id = result['session_id']
    print(f"Session ID: {session_id}\n")

# 2. 연속 대화 테스트
messages = [
    "안녕하세요\! 제 이름은 철수입니다. 맛있는 음식을 좋아해요.",
    "제 이름이 뭐라고 했죠?",
    "제가 뭘 좋아한다고 했나요?",
    "그럼 뭘 먹으면 좋을까요?"
]

for i, msg in enumerate(messages, 1):
    print(f"\n질문 {i}: {msg}")
    print("-" * 50)
    
    data = json.dumps({
        "message": msg,
        "session_id": session_id,
        "max_history": 5
    }).encode('utf-8')
    
    req = urllib.request.Request(
        f"{base_url}/chat",
        data=data,
        headers={'Content-Type': 'application/json'}
    )
    
    with urllib.request.urlopen(req) as response:
        result = json.loads(response.read())
        print(f"응답: {result['response']}")
        print(f"대화 턴: {result['turn_count']}")

# 3. 대화 기록 조회
print("\n\n=== 전체 대화 기록 ===")
data = json.dumps({"session_id": session_id}).encode('utf-8')
req = urllib.request.Request(
    f"{base_url}/session/history",
    data=data,
    headers={'Content-Type': 'application/json'}
)

with urllib.request.urlopen(req) as response:
    result = json.loads(response.read())
    for turn in result['history']:
        print(f"\n사용자: {turn['user']}")
        print(f"AI: {turn['assistant']}")
