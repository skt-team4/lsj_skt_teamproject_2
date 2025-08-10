#!/bin/bash

echo "Apple Silicon GPU (Metal) 설정 스크립트"
echo "======================================="

# 가상환경 활성화
source ~/naviyam_venv/bin/activate

# PyTorch Metal 버전 설치
echo "1. PyTorch Metal 지원 버전 설치..."
pip uninstall torch torchvision -y
pip install --pre torch torchvision --index-url https://download.pytorch.org/whl/nightly/cpu

# Metal Performance Shaders 확인
echo "2. MPS 지원 확인..."
python3 -c "import torch; print(f'MPS 사용 가능: {torch.backends.mps.is_available()}')"

# CPU 최적화 모델 설치
echo "3. CPU/Metal 최적화 모델 설치..."
pip install llama-cpp-python
pip install ctransformers

echo "완료! 이제 Metal GPU를 사용할 수 있습니다."