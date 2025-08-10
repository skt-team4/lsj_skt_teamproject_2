#!/bin/bash

# Naviyam 워크스테이션 빠른 설정 스크립트

echo "🚀 Naviyam 워크스테이션 AI 서버 설정 시작"

# 1. Python 환경 확인
echo "📦 Python 환경 체크..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3가 설치되어 있지 않습니다."
    exit 1
fi

# 2. 가상환경 생성
echo "🔧 가상환경 생성..."
python3 -m venv naviyam_gpu_env
source naviyam_gpu_env/bin/activate

# 3. 필수 패키지 설치
echo "📚 필수 패키지 설치 중..."
pip install --upgrade pip

# GPU가 있으면 CUDA 버전 설치, 없으면 CPU 버전
if command -v nvidia-smi &> /dev/null; then
    echo "✅ GPU 감지됨 - CUDA 버전 설치"
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
else
    echo "⚠️ GPU 없음 - CPU 버전 설치"
    pip install torch torchvision torchaudio
fi

# FastAPI 및 기타 패키지
pip install fastapi uvicorn transformers accelerate pydantic

# 4. 서버 실행
echo "🎯 서버 시작..."
echo "서버가 http://localhost:8000 에서 실행됩니다"
echo ""
echo "다음 단계:"
echo "1. 다른 터미널에서: ngrok http 8000"
echo "2. ngrok URL을 Cloud Run 환경변수에 설정"
echo ""

python gpu_server.py