"""
컨텍스트 기반 응답 생성기
"""
import random
from typing import Dict, List, Optional, Any
from core.session_manager import Session, ConversationState

class ContextualResponseGenerator:
    """세션 컨텍스트를 고려한 응답 생성"""
    
    def __init__(self, knowledge_base: Dict):
        self.knowledge_base = knowledge_base
        
        # 상태별 응답 템플릿
        self.templates = {
            'request_budget': [
                "예산이 얼마나 되시나요? 💰",
                "얼마 정도로 생각하고 계신가요?",
                "예산을 알려주시면 더 정확히 추천해드릴게요!",
                "가격대는 어느 정도로 생각하세요?"
            ],
            'request_location': [
                "어느 지역에서 찾으시나요? 📍",
                "위치를 알려주시면 근처 맛집을 추천해드릴게요!",
                "어디 근처가 좋으신가요?",
                "지역을 알려주세요!"
            ],
            'request_time': [
                "몇 시쯤 가실 예정이신가요? 🕐",
                "언제 방문하실 예정이신가요?",
                "시간대를 알려주시면 영업 중인 곳을 추천해드릴게요!"
            ],
            'food_recommendation': [
                "{shop_name}의 {menu_name}({price}원) 어떠세요? {reason}",
                "{shop_name}에서 {menu_name} 추천드려요! {price}원이에요. {reason}",
                "오! {food_type} 좋은 선택이에요! {shop_name}의 {menu_name}이 유명해요! 💝"
            ],
            'no_results_with_context': [
                "죄송해요, '{query}' 관련 식당을 찾지 못했어요. 😢 다른 메뉴는 어떠세요?",
                "'{query}'로 검색했는데 결과가 없네요. 비슷한 다른 음식을 추천해드릴까요?",
                "앗, '{query}' 데이터가 없어서 추천이 어려워요. 다른 종류는 어떠세요?"
            ],
            'budget_over': [
                "예산 {budget}원으로는 선택지가 제한적이에요. 조금 더 여유를 두시면 어떨까요?",
                "{budget}원 예산으로 드실 수 있는 메뉴가 많지 않네요. 😅",
                "예산이 조금 부족해 보여요. 쿠폰을 사용하시면 어떨까요?"
            ],
            'greeting': [
                "안녕하세요! 맛있는 식사 찾아드릴게요! 🍽️",
                "반가워요! 오늘 뭐 드시고 싶으세요?",
                "어서오세요! 맛집 추천 도와드릴게요!"
            ],
            'clarification': [
                "잘 이해하지 못했어요. 어떤 음식을 찾으시는지 다시 말씀해주시겠어요?",
                "음.. 무슨 말씀인지 잘 모르겠어요. 예를 들어 '치킨 추천해줘' 이런 식으로 말씀해주세요!",
                "헷갈리네요! 간단하게 음식 종류나 예산을 말씀해주세요!"
            ],
            'confirmation': [
                "{location} 근처 {food_type}을 찾아드릴까요? 예산은 {budget}원이 맞으신가요?",
                "확인해드릴게요. {food_type} 맛집, {budget}원 예산으로 찾아드릴까요?",
                "{food_type}을 원하시고 예산은 {budget}원이시군요! 맞나요?"
            ]
        }
    
    def generate_response(self, session: Session, search_results: List[Dict], 
                         query: str, intent: Optional[str] = None) -> str:
        """세션 상태를 고려한 응답 생성"""
        state = session.state_tracker
        
        # 0. 복합 정보 확인 (의도 변경 시)
        confirmation = self._generate_confirmation_if_needed(state)
        if confirmation:
            return confirmation
        
        # 1. 필수 정보 확인 및 요청
        missing_info = state.get_missing_info()
        if missing_info and not search_results:
            return self._request_missing_info(missing_info, state)
        
        # 2. 검색 결과가 있는 경우
        if search_results:
            return self._generate_recommendation_response(
                search_results, state, session.get_conversation_context()
            )
        
        # 3. 검색 결과가 없는 경우 - 컨텍스트 포함
        if state.intent == 'food_request' and query:
            # 사용자가 원했던 음식 종류 추출
            food_type = state.entities.get('food_type', query)
            return self._generate_no_results_response(food_type)
        
        # 4. 인사말
        if intent == 'greeting':
            return random.choice(self.templates['greeting'])
        
        # 5. 기본 응답
        return random.choice(self.templates['clarification'])
    
    def _generate_confirmation_if_needed(self, state: ConversationState) -> Optional[str]:
        """복합 정보가 있을 때 확인 메시지 생성"""
        # 여러 정보가 한 번에 제공된 경우
        if len(state.entities) >= 2 and state.is_intent_changed:
            template = random.choice(self.templates['confirmation'])
            
            # 기본값 설정
            food_type = state.entities.get('food_type', '음식')
            budget = state.entities.get('budget', '예산')
            location = state.entities.get('location', '현재 위치')
            
            try:
                return template.format(
                    food_type=food_type,
                    budget=budget,
                    location=location
                )
            except:
                return None
        return None
    
    def _request_missing_info(self, missing_info: List[str], 
                             state: ConversationState) -> str:
        """부족한 정보 요청"""
        # 우선순위: 예산 > 위치 > 시간
        if 'budget' in missing_info:
            # 이미 음식 종류를 언급했다면 컨텍스트 포함
            if 'food_type' in state.entities:
                food_type = state.entities['food_type']
                return f"{food_type} 좋은 선택이에요! 예산은 얼마나 되시나요? 💰"
            return random.choice(self.templates['request_budget'])
        
        elif 'location' in missing_info:
            return random.choice(self.templates['request_location'])
        
        elif 'time' in missing_info:
            return random.choice(self.templates['request_time'])
        
        return "추가 정보를 알려주시면 더 정확한 추천을 해드릴 수 있어요!"
    
    def _generate_recommendation_response(self, results: List[Dict], 
                                        state: ConversationState,
                                        context: str) -> str:
        """추천 응답 생성"""
        if not results:
            return self._generate_no_results_response(
                state.entities.get('food_type', '음식')
            )
        
        # 최고 점수 결과 선택
        best_result = results[0]
        
        # 응답 변수 준비
        food_type = state.entities.get('food_type', best_result['category'])
        shop_name = best_result['shop_name']
        
        # 예산에 맞는 메뉴 선택
        budget = state.entities.get('budget')
        if budget and 'affordable_menus' in best_result:
            menu = random.choice(best_result['affordable_menus'])
        elif best_result['menus']:
            menu = random.choice(best_result['menus'])
        else:
            menu = {'name': '추천메뉴', 'price': 0}
        
        # 추천 이유 생성
        reasons = []
        if best_result.get('keyword_score', 0) > 0.8:
            reasons.append(f"{food_type} 전문점이에요")
        if budget and menu.get('price', 0) <= int(budget) * 0.7:
            reasons.append("가성비가 좋아요")
        if best_result.get('tags') and '인기' in best_result.get('tags', []):
            reasons.append("인기가 많아요")
        
        reason = " ".join(reasons) if reasons else "맛있어요"
        
        # 템플릿 선택 및 포맷팅
        template = random.choice(self.templates['food_recommendation'])
        response = template.format(
            shop_name=shop_name,
            menu_name=menu.get('name', '추천메뉴'),
            price=menu.get('price', 0),
            food_type=food_type,
            reason=reason
        )
        
        # 추가 옵션 제공
        if len(results) > 1:
            response += f"\n다른 옵션도 있어요! {results[1]['shop_name']}도 괜찮아요."
        
        return response
    
    def _generate_no_results_response(self, query: str) -> str:
        """검색 결과 없음 응답 - 컨텍스트 포함"""
        template = random.choice(self.templates['no_results_with_context'])
        return template.format(query=query)
    
    def generate_error_response(self, error_type: str = 'general') -> str:
        """에러 응답 생성"""
        error_responses = {
            'general': "죄송해요, 일시적인 오류가 발생했어요. 다시 시도해주세요! 🙏",
            'timeout': "응답 시간이 초과되었어요. 잠시 후 다시 시도해주세요.",
            'invalid_input': "입력을 이해하지 못했어요. 다시 말씀해주시겠어요?"
        }
        return error_responses.get(error_type, error_responses['general'])