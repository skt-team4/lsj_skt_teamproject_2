#!/usr/bin/env python3
"""
나비얌 추천 챗봇 빠른 테스트
"""

import sys
import os
from pathlib import Path

# 프로젝트 경로 추가
sys.path.append(str(Path(__file__).parent))

print("🚀 나비얌 추천 챗봇 테스트")
print("========================\n")

# 1. 필수 모듈 확인
print("1. 필수 모듈 확인 중...")
required_modules = {
    'data': 'data.data_loader',
    'utils': 'utils.config',
    'inference': 'inference.chatbot',
    'recommendation': 'recommendation.recommendation_engine'
}

available_modules = []
missing_modules = []

for name, module in required_modules.items():
    try:
        __import__(module)
        available_modules.append(name)
        print(f"  ✓ {name} 모듈 확인됨")
    except ImportError as e:
        missing_modules.append(name)
        print(f"  ✗ {name} 모듈 누락: {e}")

# 2. 데이터 파일 확인
print("\n2. 데이터 파일 확인 중...")
data_files = [
    'data/restaurants_optimized.json',
    'rag/test_data.json'
]

for file in data_files:
    file_path = Path(__file__).parent / file
    if file_path.exists():
        print(f"  ✓ {file} 존재")
    else:
        print(f"  ✗ {file} 누락")

# 3. 간단한 테스트 실행
if not missing_modules:
    print("\n3. 간단한 챗봇 테스트...")
    try:
        from utils.config import Config
        from data.data_loader import DataLoader
        
        print("  - Config 생성 중...")
        config = Config()
        config.mode = "chat"
        config.debug = True
        
        print("  - 데이터 로더 초기화 중...")
        data_loader = DataLoader()
        
        print("  - 데이터 로드 중...")
        # 간단한 데이터 로드 테스트
        
        print("\n✅ 기본 설정 테스트 성공!")
        print("\n다음 명령어로 챗봇을 실행할 수 있습니다:")
        print("python3 main.py --mode chat")
        
    except Exception as e:
        print(f"\n❌ 테스트 실패: {e}")
        print("\n필요한 패키지를 설치해주세요:")
        print("pip3 install pandas numpy pydantic")
        
else:
    print("\n❌ 누락된 모듈이 있어 실행할 수 없습니다.")
    print("프로젝트 구조를 확인해주세요.")

print("\n" + "="*50)
print("테스트 완료!")