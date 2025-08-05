"""
쿠폰 기능이 통합된 나비얌 챗봇 메인
"""

import os
import sys
from pathlib import Path
import logging
from datetime import datetime
import json

# 프로젝트 루트 경로 추가
project_root = Path(__file__).parent
sys.path.append(str(project_root))

from config import get_config
from data.data_structure import UserInput, NaviyamKnowledge
from data.data_loader import load_naviyam_data
from nlp.nlu import NaviyamNLU
from nlp.nlg import NaviyamNLG
from recommendation.ranking_model import PersonalizedRanker
from recommendation.coupon_recommender import CouponRecommender
from rag.rag_main import RAGSearchEngine
from user_management.profile_manager import UserProfileManager
from utils.coupon_manager import CouponManager

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('chatbot.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class NaviyamChatbotWithCoupons:
    """쿠폰 기능이 통합된 나비얌 챗봇"""
    
    def __init__(self, config):
        logger.info("쿠폰 기능 통합 나비얌 챗봇 초기화 시작...")
        
        # 데이터 로드
        self.knowledge = load_naviyam_data(config.data)
        logger.info(f"지식베이스 로드 완료 - 쿠폰 {len(self.knowledge.coupons)}개 포함")
        
        # 컴포넌트 초기화
        self.nlu = NaviyamNLU(self.knowledge)
        self.nlg = NaviyamNLG(self.knowledge)
        self.ranker = PersonalizedRanker(knowledge_base=self.knowledge, model_type='rule_based')
        self.rag_engine = RAGSearchEngine(self.knowledge)
        self.profile_manager = UserProfileManager()
        
        # 쿠폰 관련 컴포넌트
        self.coupon_manager = CouponManager(self.knowledge)
        self.coupon_recommender = CouponRecommender(self.knowledge)
        
        logger.info("챗봇 초기화 완료!")
        
    def process_message(self, user_input: UserInput):
        """사용자 메시지 처리"""
        try:
            # 1. 자연어 이해
            extracted_info = self.nlu.extract_info(user_input)
            logger.info(f"추출된 의도: {extracted_info.intent.value} (신뢰도: {extracted_info.confidence:.2f})")
            
            # 2. 사용자 프로필 조회
            user_profile = self.profile_manager.get_profile(user_input.user_id)
            
            # 3. 급식카드 사용자 확인
            foodcard_user = self.knowledge.foodcard_users.get(str(user_input.user_id))
            
            # 4. RAG 검색 (필요한 경우)
            search_results = []
            if extracted_info.entities.food_type:
                search_results = self.rag_engine.search(
                    extracted_info.entities.food_type,
                    top_k=10
                )
            
            # 5. 추천 생성
            recommendations = self.ranker.rank_items(
                user_id=user_input.user_id,
                candidate_items=search_results,
                context={
                    'intent': extracted_info.intent.value,
                    'entities': extracted_info.entities.__dict__,
                    'confidence': extracted_info.confidence
                }
            )
            
            # 6. 쿠폰 정보 추가
            if recommendations:
                user_id = int(user_input.user_id) if user_input.user_id.isdigit() else None
                recommendations = self.coupon_recommender.enhance_recommendations_with_coupons(
                    recommendations, user_id
                )
            
            # 7. 급식카드 잔액 부족 시 특별 처리
            if foodcard_user and foodcard_user.is_low_balance():
                affordable_options = self.coupon_recommender.find_affordable_options_with_coupons(
                    int(user_input.user_id)
                )
                if affordable_options:
                    # 쿠폰으로 구매 가능한 옵션을 상위에 추가
                    for option in affordable_options[:2]:
                        recommendation = {
                            'shop_id': option['shop_id'],
                            'score': 0.95,
                            'reason': f"잔액 {foodcard_user.balance:,}원으로 쿠폰 사용 시 구매 가능",
                            'coupon_available': True,
                            'coupon_id': option['coupon_id'],
                            'coupon_name': option['coupon_name'],
                            'menu_name': option['menu_name'],
                            'menu_price': option['original_price'],
                            'discount_amount': option['discount_amount'],
                            'final_price': option['final_price']
                        }
                        recommendations.insert(0, recommendation)
            
            # 8. 응답 생성
            response = self.nlg.generate(
                extracted_info=extracted_info,
                recommendations=recommendations[:5],
                user_profile=user_profile,
                conversation_context={'has_coupon': bool(recommendations and any(r.get('coupon_available') for r in recommendations))}
            )
            
            # 쿠폰 정보를 응답에 추가
            if recommendations and any(r.get('coupon_available') for r in recommendations):
                response_parts = [response.text]
                
                if foodcard_user:
                    response_parts.insert(0, f"\n💳 현재 잔액: {foodcard_user.balance:,}원\n")
                
                # 쿠폰 정보 추가
                for i, rec in enumerate(recommendations[:3]):
                    if rec.get('coupon_available'):
                        shop = self.knowledge.shops.get(rec['shop_id'])
                        if shop and i == 0:  # 첫 번째 추천에만 상세 정보
                            response_parts.append(f"\n🎫 쿠폰 적용 시:")
                            response_parts.append(f"   {rec['menu_name']} {rec['menu_price']:,}원")
                            response_parts.append(f"   -{rec['discount_amount']:,}원 ({rec['coupon_name']})")
                            response_parts.append(f"   = {rec['final_price']:,}원")
                
                response.text = '\n'.join(response_parts)
            
            # 9. 프로필 업데이트
            if user_profile:
                self.profile_manager.update_from_interaction(
                    user_profile,
                    extracted_info,
                    recommendations[:3] if recommendations else []
                )
            
            return response
            
        except Exception as e:
            logger.error(f"메시지 처리 중 오류: {e}", exc_info=True)
            return self.nlg.generate_error_response(str(e))


def main():
    """메인 실행 함수"""
    print("\n🤖 나비얌 챗봇 (쿠폰 기능 포함)")
    print("=" * 50)
    
    # 설정 로드
    config = get_config()
    
    # 챗봇 초기화
    chatbot = NaviyamChatbotWithCoupons(config)
    
    # 사용자 ID 입력
    user_id = input("\n사용자 ID를 입력하세요 (1~3 중 선택, 기본값 2): ").strip() or "2"
    
    # 급식카드 사용자 정보 표시
    foodcard_user = chatbot.knowledge.foodcard_users.get(user_id)
    if foodcard_user:
        print(f"\n💳 급식카드 사용자 정보:")
        print(f"   - 잔액: {foodcard_user.balance:,}원")
        print(f"   - 대상: {foodcard_user.target_age_group}")
        print(f"   - 상태: {foodcard_user.status}")
    
    print("\n사용 가능한 명령어:")
    print("  - '종료' 또는 'quit': 대화 종료")
    print("  - '쿠폰': 사용 가능한 쿠폰 보기")
    print("  - '잔액': 급식카드 잔액 확인")
    print("\n무엇을 도와드릴까요?")
    print("-" * 50)
    
    # 대화 루프
    while True:
        try:
            # 사용자 입력
            user_text = input("\n👤 You: ").strip()
            
            if not user_text:
                continue
                
            if user_text.lower() in ['종료', 'quit', 'exit']:
                print("\n👋 안녕히 가세요! 맛있는 하루 보내세요~")
                break
            
            # 특별 명령어 처리
            if user_text == '쿠폰':
                print("\n🎫 사용 가능한 쿠폰:")
                coupons = chatbot.knowledge.get_applicable_coupons(user_id=int(user_id))
                for coupon in coupons:
                    print(f"   - {coupon.name}")
                    if coupon.amount > 0:
                        print(f"     {coupon.amount:,}원 할인")
                    else:
                        print(f"     {int(coupon.discount_rate * 100)}% 할인")
                continue
                
            if user_text == '잔액':
                if foodcard_user:
                    print(f"\n💳 현재 잔액: {foodcard_user.balance:,}원")
                else:
                    print("\n급식카드 정보가 없습니다.")
                continue
            
            # 사용자 입력 객체 생성
            user_input = UserInput(
                text=user_text,
                user_id=user_id,
                timestamp=datetime.now()
            )
            
            # 챗봇 응답 생성
            response = chatbot.process_message(user_input)
            
            # 응답 출력
            print(f"\n🤖 나비얌: {response.text}")
            
            # 추천 결과가 있으면 표시
            if hasattr(response, 'recommendations') and response.recommendations:
                print("\n📍 추천 결과:")
                for i, rec in enumerate(response.recommendations[:3]):
                    shop = chatbot.knowledge.shops.get(rec.get('shop_id'))
                    if shop:
                        print(f"\n{i+1}. {shop.name}")
                        if rec.get('coupon_available'):
                            print(f"   🎫 쿠폰 적용 가능!")
            
            # 후속 질문이 있으면 표시
            if hasattr(response, 'follow_up_questions') and response.follow_up_questions:
                print("\n💡 이런 것도 물어보실 수 있어요:")
                for q in response.follow_up_questions[:3]:
                    print(f"   - {q}")
                    
        except KeyboardInterrupt:
            print("\n\n👋 안녕히 가세요!")
            break
        except Exception as e:
            logger.error(f"대화 처리 중 오류: {e}", exc_info=True)
            print(f"\n❌ 오류가 발생했습니다: {e}")
            print("다시 시도해주세요.")


if __name__ == "__main__":
    main()