#!/bin/bash

echo "🤖 나비얌 챗봇 대화 테스트"
echo "=================================="

# 색상 코드
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# API 엔드포인트
API_URL="http://localhost:8000/chat"

# 대화 함수
send_message() {
    local message="$1"
    echo -e "\n${BLUE}👤 사용자:${NC} $message"
    
    # JSON 데이터 생성 (한글 처리를 위해 echo와 파이프 사용)
    response=$(echo "{\"message\": \"$message\", \"user_id\": \"test_user\"}" | \
               curl -s -X POST "$API_URL" \
               -H "Content-Type: application/json; charset=utf-8" \
               -d @-)
    
    # 응답 파싱 및 출력
    if [ ! -z "$response" ]; then
        echo -e "${GREEN}🤖 챗봇:${NC}"
        echo "$response" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if 'response' in data:
        print(data['response'])
    if 'recommendations' in data and data['recommendations']:
        print('\\n📋 추천 메뉴:')
        for rec in data['recommendations'][:3]:
            print(f\"  - {rec.get('name', 'Unknown')} ({rec.get('category', '')})\")
            if 'reason' in rec:
                print(f\"    💡 {rec['reason']}\")
except:
    print('응답을 파싱할 수 없습니다.')
    print(sys.stdin.read())
"
    else
        echo "응답 없음"
    fi
    echo "----------------------------------"
}

# 테스트 대화
send_message "안녕하세요"
sleep 1

send_message "오늘 점심 추천해주세요"
sleep 1

send_message "아이가 먹기 좋은 한식 메뉴 알려주세요"
sleep 1

send_message "매운 음식 말고 순한 음식으로"

echo -e "\n✅ 테스트 완료!"