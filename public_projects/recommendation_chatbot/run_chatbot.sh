#!/bin/bash

echo "🚀 나비얌 추천 챗봇 실행"
echo "========================"

# 색상 코드
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# 프로젝트 디렉토리
PROJECT_DIR="/Volumes/samsd/skt_teamproject/public_projects/recommendation_chatbot"
cd "$PROJECT_DIR"

echo -e "${YELLOW}1. Python 환경 확인...${NC}"
python3 --version

echo -e "\n${YELLOW}2. 필수 패키지 확인...${NC}"
# 최소한의 필수 패키지만 확인
packages=("fastapi" "uvicorn" "pandas" "pydantic")
missing_packages=()

for pkg in "${packages[@]}"; do
    if python3 -c "import $pkg" 2>/dev/null; then
        echo "  ✓ $pkg 설치됨"
    else
        echo "  ✗ $pkg 누락"
        missing_packages+=($pkg)
    fi
done

if [ ${#missing_packages[@]} -gt 0 ]; then
    echo -e "\n${RED}누락된 패키지가 있습니다: ${missing_packages[*]}${NC}"
    echo "다음 명령어로 설치하세요:"
    echo "pip3 install ${missing_packages[*]}"
    exit 1
fi

echo -e "\n${YELLOW}3. 챗봇 실행 옵션:${NC}"
echo "  1) 대화형 모드 (chat) - 기본"
echo "  2) 추론 모드 (inference) - API 테스트"
echo "  3) 평가 모드 (evaluation) - 성능 평가"

read -p "모드 선택 (1/2/3, 기본값 1): " mode_choice

case $mode_choice in
    2)
        MODE="inference"
        ;;
    3)
        MODE="evaluation"
        ;;
    *)
        MODE="chat"
        ;;
esac

echo -e "\n${GREEN}4. 챗봇 실행 중... (모드: $MODE)${NC}"
echo "=================================="

# 환경 변수 설정
export PYTHONPATH="$PROJECT_DIR:$PYTHONPATH"
export TOKENIZERS_PARALLELISM=false

# 챗봇 실행
python3 main.py --mode $MODE

echo -e "\n${GREEN}챗봇이 종료되었습니다.${NC}"