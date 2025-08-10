#!/bin/bash

# GPU 서버 챗봇과 대화하기
GPU_SERVER="http://34.22.80.119:8000"

echo "🤖 GPU 서버 챗봇과 대화하기"
echo "================================"
echo "종료하려면 'quit' 또는 'exit' 입력"
echo ""

while true; do
    echo -n "👤 나: "
    read message
    
    # 종료 명령 확인
    if [ "$message" = "quit" ] || [ "$message" = "exit" ]; then
        echo "👋 대화를 종료합니다."
        break
    fi
    
    # GPU 서버로 메시지 전송
    response=$(echo "{\"message\": \"$message\", \"user_id\": \"user1\"}" | \
               curl -s -X POST "$GPU_SERVER/chat" \
               -H "Content-Type: application/json" -d @- | \
               python3 -c "import sys, json; print(json.load(sys.stdin)['response'])" 2>/dev/null)
    
    echo "🤖 챗봇: $response"
    echo ""
done