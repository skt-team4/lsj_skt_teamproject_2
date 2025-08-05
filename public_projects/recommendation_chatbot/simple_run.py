#!/usr/bin/env python3
"""
나비얌 추천 챗봇 간단 실행
"""

import sys
import os

# 현재 디렉토리를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("🚀 나비얌 추천 챗봇 실행")
print("========================\n")

try:
    # main.py의 main 함수 import
    from main import main
    
    # 명령줄 인자 설정 (chat 모드)
    sys.argv = ['main.py', '--mode', 'chat']
    
    # 실행
    exit_code = main()
    sys.exit(exit_code)
    
except ImportError as e:
    print(f"❌ Import 오류: {e}")
    print("\n필요한 패키지가 설치되지 않았을 수 있습니다.")
    print("다음 패키지들을 설치해주세요:")
    print("\npip3 install fastapi uvicorn pandas numpy pydantic")
    
except Exception as e:
    print(f"❌ 실행 오류: {e}")
    print("\n자세한 오류 내용을 확인하려면 다음 명령어를 실행하세요:")
    print("python3 main.py --mode chat --debug")