#!/usr/bin/env python3
"""
실제 AI 챗봇을 API 서버로 실행
"""
import os
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(str(Path(__file__).parent))

# GPU 없는 환경 설정
os.environ['USE_GPU'] = 'false'
os.environ['MODEL_TYPE'] = 'template'  # 템플릿 모드
os.environ['CUDA_VISIBLE_DEVICES'] = ''  # GPU 비활성화

if __name__ == "__main__":
    import uvicorn
    
    print("🚀 나비얌 챗봇 API 서버 시작...")
    print("📍 주소: http://0.0.0.0:8000")
    print("📖 API 문서: http://0.0.0.0:8000/docs")
    print("\n⚠️  GPU 없음 - 템플릿 모드로 실행됩니다")
    
    # API 서버 실행
    uvicorn.run(
        "api.server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )