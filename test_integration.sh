#!/bin/bash

echo "=== 나비얌 챗봇 통합 테스트 ==="
echo ""

API_URL="http://34.146.37.35:8000"

echo "1. 헬스체크 테스트..."
curl -s ${API_URL}/health | python3 -m json.tool
echo ""

echo "2. 인사 메시지 테스트..."
curl -s -X POST ${API_URL}/chat \
    -H "Content-Type: application/json" \
    -d '{"message": "안녕하세요!", "user_id": "test_user"}' \
    | python3 -m json.tool
echo ""

echo "3. 오늘 메뉴 추천 테스트..."
curl -s -X POST ${API_URL}/chat \
    -H "Content-Type: application/json" \
    -d '{"message": "오늘 추천 메뉴 뭐야?", "user_id": "test_user"}' \
    | python3 -m json.tool
echo ""

echo "4. 건강 메뉴 추천 테스트..."
curl -s -X POST ${API_URL}/chat \
    -H "Content-Type: application/json" \
    -d '{"message": "건강한 메뉴 추천해줘", "user_id": "test_user"}' \
    | python3 -m json.tool
echo ""

echo "5. 도시락 메뉴 추천 테스트..."
curl -s -X POST ${API_URL}/chat \
    -H "Content-Type: application/json" \
    -d '{"message": "도시락 메뉴 추천", "user_id": "test_user"}' \
    | python3 -m json.tool
echo ""

echo "=== 테스트 완료 ==="
echo ""
echo "서버 상태:"
echo "- 챗봇 API: ${API_URL}"
echo "- 웹앱: http://34.146.37.35:8080/naviyam-webapp.html"
echo ""
echo "접속 방법:"
echo "1. 웹 브라우저에서: http://34.146.37.35:8080/naviyam-webapp.html"
echo "2. 로컬 파일 열기: open /Volumes/samsd/skt_teamproject/publicproject/naviyam-webapp.html"