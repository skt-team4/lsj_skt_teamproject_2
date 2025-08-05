#!/usr/bin/env python3
"""
나비얌 챗봇 간단 테스트 스크립트
필수 의존성만으로 기본 기능 테스트
"""

import sys
import os
from pathlib import Path

# 프로젝트 경로 추가
sys.path.append(str(Path(__file__).parent))

def test_imports():
    """필수 모듈 임포트 테스트"""
    print("📦 모듈 임포트 테스트 중...")
    
    try:
        # 기본 모듈들
        import utils.config
        print("✅ utils.config")
        
        import data.data_structure
        print("✅ data.data_structure")
        
        import nlp.nlu
        print("✅ nlp.nlu")
        
        import inference.chatbot
        print("✅ inference.chatbot")
        
        print("\n✅ 모든 모듈 임포트 성공!")
        return True
        
    except ImportError as e:
        print(f"\n❌ 임포트 실패: {e}")
        print("\n필요한 패키지 설치:")
        print("pip install torch transformers pandas numpy")
        return False

def test_data_loading():
    """데이터 로딩 테스트"""
    print("\n📂 데이터 로딩 테스트 중...")
    
    try:
        from data.data_loader import DataLoader
        
        data_path = Path(__file__).parent / "data" / "restaurants_optimized.json"
        if not data_path.exists():
            print(f"❌ 데이터 파일 없음: {data_path}")
            return False
            
        loader = DataLoader(str(data_path))
        knowledge = loader.load_knowledge_base()
        
        print(f"✅ 가게 수: {len(knowledge.shops)}")
        print(f"✅ 메뉴 수: {len(knowledge.menus)}")
        
        if knowledge.shops:
            sample_shop = list(knowledge.shops.values())[0]
            print(f"✅ 샘플 가게: {sample_shop.name}")
            
        return True
        
    except Exception as e:
        print(f"❌ 데이터 로딩 실패: {e}")
        return False

def test_basic_chat():
    """기본 대화 테스트"""
    print("\n💬 기본 대화 테스트 중...")
    
    try:
        from utils.config import parse_config
        from inference.chatbot import create_naviyam_chatbot
        
        # 테스트용 설정
        class TestConfig:
            mode = "chat"
            debug = True
            log_level = "INFO"
            use_4bit = True
            max_length = 512
            
            class ModelConfig:
                use_lora = False
                model_type = "koalpaca"
                
            class DataConfig:
                data_path = str(Path(__file__).parent / "data" / "restaurants_optimized.json")
                output_path = str(Path(__file__).parent / "outputs")
                
            class InferenceConfig:
                save_conversations = False
                
            model = ModelConfig()
            data = DataConfig()
            inference = InferenceConfig()
        
        config = TestConfig()
        
        print("🤖 챗봇 초기화 중...")
        chatbot = create_naviyam_chatbot(config)
        
        # 테스트 대화
        test_inputs = [
            "안녕하세요",
            "치킨 먹고 싶어",
            "만원으로 뭐 먹을까?"
        ]
        
        for user_input in test_inputs:
            print(f"\n👤 사용자: {user_input}")
            response = chatbot.chat(user_input, "test_user")
            print(f"🤖 챗봇: {response}")
            
        return True
        
    except Exception as e:
        print(f"❌ 대화 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """메인 테스트 함수"""
    print("🧪 나비얌 챗봇 테스트 시작\n")
    
    tests = [
        ("모듈 임포트", test_imports),
        ("데이터 로딩", test_data_loading),
        # ("기본 대화", test_basic_chat),  # 모델 로딩이 필요하므로 선택적
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        print(f"🔍 {test_name} 테스트")
        print(f"{'='*50}")
        
        if test_func():
            passed += 1
        else:
            failed += 1
    
    print(f"\n{'='*50}")
    print(f"📊 테스트 결과: {passed} 성공, {failed} 실패")
    print(f"{'='*50}")
    
    if failed == 0:
        print("\n✅ 모든 테스트 통과! main.py를 실행할 준비가 되었습니다.")
        print("\n실행 방법:")
        print("python main.py --mode chat")
    else:
        print("\n❌ 일부 테스트 실패. 위의 오류를 확인하세요.")

if __name__ == "__main__":
    main()