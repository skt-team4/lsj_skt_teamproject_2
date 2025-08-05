#!/bin/bash

# 나비얌 챗봇 백엔드 빠른 실행 스크립트
# 최소한의 설정으로 서버 실행

echo "🚀 나비얌 챗봇 백엔드 서버 시작 준비..."

# Python 버전 확인
python_cmd=""
if command -v python3 &> /dev/null; then
    python_cmd="python3"
elif command -v python &> /dev/null; then
    python_cmd="python"
else
    echo "❌ Python이 설치되어 있지 않습니다."
    exit 1
fi

echo "✅ Python 버전: $($python_cmd --version)"

# 가상환경 생성 (없으면)
if [ ! -d "venv" ]; then
    echo "📦 가상환경 생성 중..."
    $python_cmd -m venv venv
fi

# 가상환경 활성화
echo "🔄 가상환경 활성화..."
source venv/bin/activate

# 최소 필수 패키지만 설치
echo "📦 필수 패키지 설치 중..."
pip install fastapi uvicorn torch transformers pandas numpy --quiet

# 디렉토리 생성
mkdir -p outputs/logs
mkdir -p outputs/learning_data
mkdir -p outputs/user_profiles
mkdir -p outputs/temp
mkdir -p cache/models

# 환경변수 설정 (GPU 없는 환경용)
export USE_GPU=false
export MODEL_TYPE=mock
export RESPONSE_MODE=template_only

echo "🌐 서버 시작 중..."
echo "📍 주소: http://localhost:8000"
echo "📖 API 문서: http://localhost:8000/docs"
echo ""
echo "🔧 테스트 방법:"
echo "1. 새 터미널에서 프론트엔드 실행"
echo "2. 또는 curl로 테스트:"
echo '   curl -X POST http://localhost:8000/chat -H "Content-Type: application/json" -d "{\"message\": \"치킨 먹고 싶어\", \"user_id\": \"test\"}"'
echo ""
echo "종료: Ctrl+C"
echo ""

# 서버 실행
$python_cmd -m uvicorn api.server:app --reload --host 0.0.0.0 --port 8000