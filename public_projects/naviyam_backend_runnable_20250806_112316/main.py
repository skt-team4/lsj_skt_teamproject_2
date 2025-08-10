#!/usr/bin/env python3
"""
나비얌 챗봇 메인 실행 파일
대화형 인터페이스 및 추론 모드 지원
"""

import sys
import os
import logging
import time
from datetime import datetime
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(str(Path(__file__).parent))

from utils.config import parse_config, get_config_summary
from utils.logging_utils import setup_logger
from utils.welcome_message import create_welcome_generator
from inference.chatbot import NaviyamChatbot, create_naviyam_chatbot
from inference.data_collector import LearningDataCollector
from data.data_structure import UserInput
from utils.coupon_manager import CouponManager
from recommendation.coupon_recommender import CouponRecommender


def setup_logging(config):
    """로깅 설정"""
    log_level = getattr(logging, config.log_level.upper())

    # 기본 로깅 설정
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(
                Path(config.data.output_path) / 'naviyam_chatbot.log',
                encoding='utf-8'
            )
        ]
    )

    # 외부 라이브러리 로그 레벨 조정
    logging.getLogger('transformers').setLevel(logging.WARNING)
    logging.getLogger('torch').setLevel(logging.WARNING)

    return logging.getLogger(__name__)


def run_chat_mode(config, logger):
    """대화형 모드 실행"""
    logger.info("대화형 모드 시작")

    try:
        # 챗봇 초기화
        print("나비얌 챗봇을 초기화하고 있습니다...")
        chatbot = create_naviyam_chatbot(config)
        
        # 쿠폰 기능 추가 (config에서 활성화된 경우)
        if getattr(config, 'enable_coupon', True):
            if hasattr(chatbot, 'knowledge'):
                chatbot.coupon_manager = CouponManager(chatbot.knowledge)
                chatbot.coupon_recommender = CouponRecommender(chatbot.knowledge)
                print("쿠폰 기능이 활성화되었습니다.")

        # 데이터 수집기 초기화 및 연결 (새로 추가)
        data_collector = LearningDataCollector(
            save_path=f"{config.data.output_path}/learning_data",
            buffer_size=100,
            auto_save_interval=300
        )
        chatbot.data_collector = data_collector

        # NLU에도 연결
        if hasattr(chatbot, 'nlu') and chatbot.nlu:
            chatbot.nlu.set_learning_data_collector(data_collector)

        print("초기화 완료!")
        print(get_config_summary(config))

        # 성능 지표 출력
        if config.debug:
            metrics = chatbot.get_performance_metrics()
            print(f"지식베이스: 가게 {metrics['knowledge_base_size']['shops']}개, "
                  f"메뉴 {metrics['knowledge_base_size']['menus']}개")

        # 다양한 환영 메시지 생성
        welcome_generator = create_welcome_generator()
        
        print("\n" + "=" * 60)
        
        # 사용자 ID 설정
        # TODO: 실제 서비스에서는 플랫폼(카카오톡, 웹, 앱)에서 자동으로 user_id 제공
        # 테스트를 위한 임시 구현
        print("\n[TIP] 실제 서비스에서는 로그인이나 플랫폼 인증으로 자동 식별됩니다.")
        if getattr(config, 'enable_coupon', True):
            user_id = input("테스트 사용자 선택 (1: 잔액 25,000원, 2: 잔액 5,000원, 3: 잔액 15,000원, 기타: 일반): ").strip()
        else:
            user_id = input("사용자 이름을 입력해주세요 (기본값: guest): ").strip()
        if not user_id:
            user_id = "guest"
        
        # 쿠폰 기능이 활성화된 경우 급식카드 정보 표시
        if getattr(config, 'enable_coupon', True) and hasattr(chatbot, 'knowledge'):
            foodcard_user = chatbot.knowledge.foodcard_users.get(user_id)
            if foodcard_user:
                print(f"\n[급식카드 사용자 정보]")
                print(f"   - 잔액: {foodcard_user.balance:,}원")
                print(f"   - 대상: {foodcard_user.target_age_group}")
                print(f"   - 상태: {foodcard_user.status}")
        
        # 기존 사용자 프로필 확인하여 개인화 환영 메시지 생성
        try:
            user_profile = chatbot.get_user_profile(user_id)
            if user_profile and user_profile.preferred_categories:
                welcome_message = welcome_generator.generate_custom_welcome(
                    user_name=user_id, 
                    preferences=user_profile.preferred_categories
                )
            else:
                welcome_message = welcome_generator.generate_simple_welcome()
        except:
            # 프로필 로드 실패시 기본 메시지
            welcome_message = welcome_generator.generate_simple_welcome()
        
        print(welcome_message)
        print("\n[TIP] 도움말: 'quit', 'exit', '종료' 입력시 종료 | '/help'로 명령어 확인")
        if getattr(config, 'enable_coupon', True):
            print("   '쿠폰'으로 사용 가능한 쿠폰 확인 | '잔액'으로 급식카드 잔액 확인")
        print("=" * 60 + "\n")

        # 대화 루프
        conversation_count = 0
        start_time = time.time()

        while True:
            try:
                # 사용자 입력 받기
                user_message = input(f"{user_id}: ").strip()

                # 종료 명령 확인
                if user_message.lower() in ['quit', 'exit', '종료', '나가기', '끝']:
                    break

                if not user_message:
                    print("챗봇: 무엇을 도와드릴까요? 😊\n")
                    continue

                # 특별 명령 처리
                if user_message.startswith('/'):
                    handle_special_commands(user_message, chatbot, user_id, config)
                    continue
                
                # 쿠폰 관련 명령어 처리
                if getattr(config, 'enable_coupon', True) and user_message in ['쿠폰', '잔액']:
                    if user_message == '쿠폰' and hasattr(chatbot, 'knowledge'):
                        print("\n🎫 사용 가능한 쿠폰:")
                        # 사용자 ID가 숫자가 아니면 None으로 처리하여 모든 쿠폰 표시
                        user_id_int = int(user_id) if user_id.isdigit() else None
                        coupons = chatbot.knowledge.get_applicable_coupons(user_id=user_id_int)
                        if coupons:
                            for coupon in coupons:
                                print(f"   - {coupon.name}")
                                if coupon.amount > 0:
                                    print(f"     {coupon.amount:,}원 할인")
                                else:
                                    print(f"     {int(coupon.discount_rate * 100)}% 할인")
                        else:
                            print("   사용 가능한 쿠폰이 없습니다.")
                    elif user_message == '잔액' and hasattr(chatbot, 'knowledge'):
                        foodcard_user = chatbot.knowledge.foodcard_users.get(user_id)
                        if foodcard_user:
                            print(f"\n💳 현재 잔액: {foodcard_user.balance:,}원")
                        else:
                            print("\n급식카드 정보가 없습니다.")
                    continue

                # 챗봇 응답 생성
                print("챗봇: ", end="", flush=True)

                response_start = time.time()
                response = chatbot.chat(user_message, user_id)
                response_time = time.time() - response_start

                print(response)

                # 디버그 정보 출력
                if config.debug:
                    print(f"   (응답시간: {response_time:.2f}초)")

                print()  # 빈 줄
                conversation_count += 1


            except KeyboardInterrupt:

                print("\n\n👋 대화를 종료합니다...")

                # 데이터 저장 (새로 추가)

                if hasattr(chatbot, 'data_collector') and chatbot.data_collector:
                    print("📊 학습 데이터 저장 중...")

                    chatbot.data_collector.force_save()

                    print("✅ 데이터 저장 완료!")

                break

            except Exception as e:
                logger.error(f"대화 처리 중 오류: {e}")
                print(f"챗봇: 죄송해요! 오류가 발생했습니다: {e}\n")

        # 대화 종료 정보
        total_time = time.time() - start_time
        print(f"\n📊 대화 통계:")
        print(f"   총 대화 수: {conversation_count}")
        print(f"   총 시간: {total_time:.1f}초")
        if conversation_count > 0:
            print(f"   평균 대화 시간: {total_time / conversation_count:.1f}초")

        # 최종 성능 지표
        final_metrics = chatbot.get_performance_metrics()
        print(f"   총 응답 수: {final_metrics['total_conversations']}")
        print(f"   평균 응답 시간: {final_metrics['avg_response_time']:.2f}초")
        print(f"   성공률: {final_metrics.get('success_rate', 0):.1%}")

        if hasattr(chatbot, 'data_collector') and chatbot.data_collector:
            collection_stats = chatbot.data_collector.get_collection_statistics()
            print(f"   수집된 학습 데이터: {collection_stats['quality_stats']['total_collected']}개")
            print(f"   데이터 품질: {collection_stats['quality_stats']['validity_rate']:.1f}%")
            print(f"   LLM 응답 비율: {final_metrics.get('llm_child_response_rate', 0) * 100:.1f}%")
        # 상태 저장
        if config.inference.save_conversations:
            state_file = Path(
                config.data.output_path) / f"chatbot_state_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            chatbot.save_state(str(state_file))
            print(f"   대화 기록 저장: {state_file}")

            if hasattr(chatbot, 'data_collector') and chatbot.data_collector:
                learning_data_file = Path(
                    config.data.output_path) / f"learning_data_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
                success = chatbot.data_collector.export_training_data(str(learning_data_file), format="jsonl", days=1)
                if success:
                    print(f"   학습 데이터 저장: {learning_data_file}")
                else:
                    print("   학습 데이터 저장 실패")
        print("\n👋 나비얌 챗봇을 이용해주셔서 감사합니다!")

    except Exception as e:
        logger.error(f"챗봇 실행 실패: {e}")
        print(f"챗봇 실행에 실패했습니다: {e}")
        return 1

    return 0


def handle_special_commands(command, chatbot, user_id, config):
    """특별 명령 처리"""

    if command == '/help':
        print("""
        📖 사용 가능한 명령어:
           /help        - 도움말 표시
           /welcome     - 새로운 환영 메시지 보기
           /profile     - 내 프로필 보기
           /history     - 대화 기록 보기
           /stats       - 성능 통계 보기
           /data        - 학습 데이터 통계 보기    (새로 추가)
           /export      - 학습 데이터 내보내기      (새로 추가)
           /reset       - 대화 기록 리셋
           /debug       - 디버그 모드 토글
           /clear       - 화면 지우기
           /clearcache  - 캐시 초기화            (새로 추가)
           /coupon      - 쿠폰 기능 토글          (쿠폰 기능)
                """)

    elif command == '/welcome':
        # 새로운 환영 메시지 생성
        welcome_generator = create_welcome_generator()
        try:
            user_profile = chatbot.get_user_profile(user_id)
            if user_profile and user_profile.preferred_categories:
                welcome_message = welcome_generator.generate_custom_welcome(
                    user_name=user_id, 
                    preferences=user_profile.preferred_categories
                )
            else:
                welcome_message = welcome_generator.generate_simple_welcome()
        except:
            welcome_message = welcome_generator.generate_simple_welcome()
        
        print("\n" + "=" * 60)
        print(welcome_message)
        print("=" * 60 + "\n")

    elif command == '/profile':
        profile = chatbot.get_user_profile(user_id)
        if profile:
            print(f"""
👤 {user_id}님의 프로필:
   선호 음식: {', '.join(profile.preferred_categories) if profile.preferred_categories else '없음'}
   평균 예산: {profile.average_budget}원 (설정됨: {'예' if profile.average_budget else '아니오'})
   즐겨찾기: {len(profile.favorite_shops)}개
   대화 스타일: {profile.conversation_style}
   마지막 활동: {profile.last_updated.strftime('%Y-%m-%d %H:%M:%S')}
            """)
        else:
            print("프로필 정보가 없습니다.")

    elif command == '/history':
        history = chatbot.get_conversation_history(user_id, 5)
        if history:
            print("\n📜 최근 대화 기록 (최대 5개):")
            for i, conv in enumerate(history, 1):
                print(f"   {i}. {conv['user_input'][:50]}..." if len(
                    conv['user_input']) > 50 else f"   {i}. {conv['user_input']}")
                print(f"      → {conv['bot_response'][:50]}..." if len(
                    conv['bot_response']) > 50 else f"      → {conv['bot_response']}")
        else:
            print("대화 기록이 없습니다.")

    elif command == '/stats':
        metrics = chatbot.get_performance_metrics()
        print(f"""
📊 성능 통계:
   총 대화 수: {metrics['total_conversations']}
   평균 응답 시간: {metrics['avg_response_time']:.2f}초
   성공률: {metrics.get('success_rate', 0):.1%}
   지식베이스: 가게 {metrics['knowledge_base_size']['shops']}개, 메뉴 {metrics['knowledge_base_size']['menus']}개
        """)

    elif command == '/reset':
        chatbot.reset_conversation(user_id)
        print("✅ 대화 기록이 리셋되었습니다.")

    elif command == '/debug':
        config.debug = not config.debug
        print(f"🐛 디버그 모드: {'ON' if config.debug else 'OFF'}")

    elif command == '/clear':
        os.system('cls' if os.name == 'nt' else 'clear')
    
    elif command == '/clearcache':
        # 캐시 초기화
        try:
            from utils.cache import get_query_cache
            cache = get_query_cache()
            cache.clear()
            print("✅ 캐시가 초기화되었습니다.")
        except Exception as e:
            print(f"❌ 캐시 초기화 실패: {e}")
    
    elif command == '/coupon':
        config.enable_coupon = not getattr(config, 'enable_coupon', True)
        print(f"🎫 쿠폰 기능: {'ON' if config.enable_coupon else 'OFF'}")

    elif command == '/data':
        if hasattr(chatbot, 'data_collector') and chatbot.data_collector:
            stats = chatbot.data_collector.get_collection_statistics()
            print(f"""
    📊 학습 데이터 통계:
       총 수집된 데이터: {stats['quality_stats']['total_collected']}개
       유효 샘플: {stats['quality_stats']['valid_samples']}개
       데이터 품질: {stats['quality_stats']['validity_rate']:.1f}%
       활성 세션: {stats['session_stats']['active_sessions']}개
       버퍼 상태: {stats['buffer_stats']['total_buffer_size']}개 대기중
       저장 경로: {stats['save_path']}
            """)
        else:
            print("데이터 수집기가 초기화되지 않았습니다.")

    elif command == '/export':
        if hasattr(chatbot, 'data_collector') and chatbot.data_collector:
            export_file = f"./exported_learning_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
            print("📤 학습 데이터 내보내는 중...")
            success = chatbot.data_collector.export_training_data(export_file, format="jsonl", days=7)
            if success:
                print(f"✅ 학습 데이터 내보내기 완료: {export_file}")
            else:
                print("❌ 학습 데이터 내보내기 실패")
        else:
            print("데이터 수집기가 초기화되지 않았습니다.")


    else:

        print(f"❌ 알 수 없는 명령어: {command}")

        print("   /help를 입력하여 사용 가능한 명령어를 확인하세요.")

def run_inference_mode(config, logger):
    """추론 모드 실행 (API 형태)"""
    logger.info("추론 모드 시작")

    try:
        # 챗봇 초기화
        chatbot = create_naviyam_chatbot(config)

        print("🚀 나비얌 챗봇 추론 모드 실행 중...")
        print("   API 서버가 시작되었습니다 (예시)")

        # 실제로는 FastAPI나 Flask 서버 시작
        # 여기서는 간단한 테스트 케이스 실행
        test_cases = [
            "치킨 먹고 싶어",
            "만원으로 뭐 먹을까?",
            "근처 착한가게 알려줘",
            "할인 쿠폰 있어?",
            "지금 열린 곳 있나?"
        ]

        print("\n📝 테스트 케이스 실행:")
        for i, test_input in enumerate(test_cases, 1):
            print(f"\n{i}. 테스트: {test_input}")

            user_input = UserInput(
                text=test_input,
                user_id="test_user",
                timestamp=datetime.now()
            )

            start_time = time.time()
            output = chatbot.process_user_input(user_input)
            response_time = time.time() - start_time

            print(f"   응답: {output.response.text}")
            print(f"   의도: {output.extracted_info.intent.value}")
            print(f"   신뢰도: {output.extracted_info.confidence:.2f}")
            print(f"   추천 수: {len(output.response.recommendations)}")
            print(f"   응답 시간: {response_time:.3f}초")

        # 최종 통계
        metrics = chatbot.get_performance_metrics()
        print(f"\n📊 테스트 완료:")
        print(f"   총 처리: {metrics['total_conversations']}")
        print(f"   평균 응답 시간: {metrics['avg_response_time']:.3f}초")
        print(f"   성공률: {metrics.get('success_rate', 0):.1%}")

        return 0

    except Exception as e:
        logger.error(f"추론 모드 실행 실패: {e}")
        print(f"❌ 추론 모드 실행에 실패했습니다: {e}")
        return 1


def run_evaluation_mode(config, logger):
    """평가 모드 실행"""
    logger.info("평가 모드 시작")

    try:
        chatbot = create_naviyam_chatbot(config)

        print("🔍 나비얌 챗봇 평가 모드")

        # 평가용 데이터셋
        evaluation_dataset = [
            {"input": "치킨 먹고 싶어", "expected_intent": "FOOD_REQUEST", "expected_food": "치킨"},
            {"input": "5천원으로 뭐 먹을까", "expected_intent": "BUDGET_INQUIRY", "expected_budget": 5000},
            {"input": "근처 맛집 추천해줘", "expected_intent": "LOCATION_INQUIRY"},
            {"input": "지금 열린 곳 있어?", "expected_intent": "TIME_INQUIRY"},
            {"input": "할인 쿠폰 있나요?", "expected_intent": "COUPON_INQUIRY"},
            {"input": "안녕하세요", "expected_intent": "GENERAL_CHAT"},
        ]

        correct_predictions = 0
        total_predictions = len(evaluation_dataset)

        print(f"\n📋 {total_predictions}개 테스트 케이스 평가 중...\n")

        for i, test_case in enumerate(evaluation_dataset, 1):
            user_input = UserInput(
                text=test_case["input"],
                user_id="eval_user",
                timestamp=datetime.now()
            )

            output = chatbot.process_user_input(user_input)
            predicted_intent = output.extracted_info.intent.value
            expected_intent = test_case["expected_intent"]

            is_correct = predicted_intent == expected_intent
            if is_correct:
                correct_predictions += 1

            status = "✅" if is_correct else "❌"
            print(f"{status} {i:2d}. '{test_case['input']}'")
            print(f"      예상: {expected_intent}, 예측: {predicted_intent}")
            print(f"      신뢰도: {output.extracted_info.confidence:.2f}")

            # 추가 검증
            if "expected_food" in test_case:
                predicted_food = output.extracted_info.entities.food_type if output.extracted_info.entities else None
                expected_food = test_case["expected_food"]
                food_match = predicted_food == expected_food
                print(f"      음식: 예상={expected_food}, 예측={predicted_food} {'✅' if food_match else '❌'}")

            if "expected_budget" in test_case:
                predicted_budget = output.extracted_info.entities.budget if output.extracted_info.entities else None
                expected_budget = test_case["expected_budget"]
                budget_match = predicted_budget == expected_budget
                print(f"      예산: 예상={expected_budget}, 예측={predicted_budget} {'✅' if budget_match else '❌'}")

            print()

        # 결과 요약
        accuracy = correct_predictions / total_predictions
        print("=" * 50)
        print(f"📊 평가 결과:")
        print(f"   정확도: {accuracy:.1%} ({correct_predictions}/{total_predictions})")
        print(f"   의도 분류 성능: {'우수' if accuracy > 0.8 else '보통' if accuracy > 0.6 else '개선 필요'}")

        # 성능 지표
        metrics = chatbot.get_performance_metrics()
        print(f"   평균 응답 시간: {metrics['avg_response_time']:.3f}초")
        print(
            f"   처리 속도: {'빠름' if metrics['avg_response_time'] < 1.0 else '보통' if metrics['avg_response_time'] < 2.0 else '느림'}")

        return 0 if accuracy > 0.7 else 1  # 70% 이상이면 성공

    except Exception as e:
        logger.error(f"평가 모드 실행 실패: {e}")
        print(f"❌ 평가 모드 실행에 실패했습니다: {e}")
        return 1


def main():
    """메인 함수"""
    try:
        # 설정 파싱
        config = parse_config()

        # 로깅 설정
        logger = setup_logging(config)

        # 시작 메시지
        logger.info("나비얌 챗봇 시작")
        logger.info(f"실행 모드: {config.mode}")
        logger.info(f"디버그 모드: {config.debug}")

        # 모드별 실행
        if config.mode == "chat":
            return run_chat_mode(config, logger)
        elif config.mode == "inference":
            return run_inference_mode(config, logger)
        elif config.mode == "evaluation":
            return run_evaluation_mode(config, logger)
        else:
            logger.error(f"지원하지 않는 모드: {config.mode}")
            print(f"❌ 지원하지 않는 모드: {config.mode}")
            print("사용 가능한 모드: chat, inference, training, evaluation")
            return 1

    except KeyboardInterrupt:
        print("\n\n👋 프로그램을 종료합니다...")
        return 0
    except Exception as e:
        print(f"❌ 예상치 못한 오류: {e}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)