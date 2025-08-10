"""
컨텍스트 인식 나비얌 챗봇
"""
import os
import sys
import logging
from pathlib import Path
from typing import Optional, Dict

# 프로젝트 루트 경로 추가
project_root = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_root))

from config import Config
from data.data_loader import load_naviyam_data
from nlp.nlu import NaviyamNLU
from nlp.nlg import NaviyamNLG
from rag.retriever import RAGSearchEngine
from rag.enhanced_retriever import EnhancedRetriever
from recommendation.ranker import PersonalizedRanker
from core.session_manager import SessionManager
from inference.contextual_response_generator import ContextualResponseGenerator
from inference.response_generator import NaviyamResponseGenerator

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('context_aware_chatbot.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

class ContextAwareNaviyamChatbot:
    """컨텍스트를 인식하는 나비얌 챗봇"""
    
    def __init__(self, config: Config):
        logger.info("컨텍스트 인식 챗봇 초기화 시작...")
        
        self.config = config
        self.knowledge = load_naviyam_data(config.data)
        
        # 기본 컴포넌트
        self.nlu = NaviyamNLU(self.knowledge)
        self.nlg = NaviyamNLG(self.knowledge)
        self.ranker = PersonalizedRanker(
            knowledge_base=self.knowledge,
            model_type='rule_based'
        )
        
        # RAG 엔진
        self.rag_engine = RAGSearchEngine(self.knowledge)
        
        # 새로운 컴포넌트들
        self.session_manager = SessionManager(session_timeout_minutes=30)
        self.enhanced_retriever = EnhancedRetriever(
            knowledge_base=self.knowledge,
            vector_retriever=self.rag_engine
        )
        self.contextual_generator = ContextualResponseGenerator(self.knowledge)
        
        # 기존 응답 생성기 (폴백용)
        self.response_generator = NaviyamResponseGenerator(
            knowledge_base=self.knowledge,
            model=None  # GPU 없을 때를 위해
        )
        
        # 현재 세션
        self.current_session = None
        
        logger.info("컨텍스트 인식 챗봇 초기화 완료!")
    
    def start_session(self, user_id: Optional[str] = None) -> str:
        """새 세션 시작"""
        session = self.session_manager.create_session(user_id)
        self.current_session = session
        logger.info(f"새 세션 시작: {session.session_id}")
        return session.session_id
    
    def process_message(self, user_input: str, session_id: Optional[str] = None) -> str:
        """사용자 메시지 처리"""
        try:
            # 세션 확인
            if session_id:
                self.current_session = self.session_manager.get_session(session_id)
            
            if not self.current_session:
                self.start_session()
            
            # 대화 기록에 사용자 입력 추가
            self.current_session.add_message('user', user_input)
            
            # NLU 처리
            nlu_result = self.nlu.process(user_input)
            intent = nlu_result.get('intent', {}).get('intent_type')
            entities = nlu_result.get('entities', {})
            
            logger.info(f"NLU 결과 - Intent: {intent}, Entities: {entities}")
            
            # 세션 상태 업데이트
            self._update_session_state(intent, entities, user_input)
            
            # 응답 생성
            response = self._generate_contextual_response(user_input, intent)
            
            # 대화 기록에 봇 응답 추가
            self.current_session.add_message('bot', response)
            
            return response
            
        except Exception as e:
            logger.error(f"메시지 처리 중 오류: {str(e)}")
            return self.contextual_generator.generate_error_response()
    
    def _update_session_state(self, intent: str, entities: Dict, user_input: str):
        """세션 상태 업데이트"""
        state_updates = {'intent': intent}
        
        # 엔티티 매핑
        entity_mapping = {
            'food_type': entities.get('food_type'),
            'budget': entities.get('price') or entities.get('budget'),
            'location': entities.get('location'),
            'time': entities.get('time')
        }
        
        # None이 아닌 엔티티만 업데이트
        valid_entities = {k: v for k, v in entity_mapping.items() if v}
        state_updates['entities'] = valid_entities
        
        # 의도 변경 감지 - 새로운 food_type이 들어오면 의도 변경으로 간주
        current_state = self.current_session.state_tracker
        if 'food_type' in valid_entities and current_state.entities.get('food_type'):
            if valid_entities['food_type'] != current_state.entities['food_type']:
                state_updates['reset_entities'] = True
                logger.info(f"의도 변경 감지: {current_state.entities['food_type']} -> {valid_entities['food_type']}")
        
        # 의도별 필수 정보 설정
        if intent == 'food_request':
            state_updates['required_info'] = ['budget']
        elif intent == 'budget_inquiry':
            state_updates['required_info'] = ['food_type']
        
        self.session_manager.update_session_state(
            self.current_session.session_id,
            **state_updates
        )
    
    def _generate_contextual_response(self, query: str, intent: str) -> str:
        """컨텍스트 기반 응답 생성"""
        state = self.current_session.state_tracker
        
        # 검색이 필요한 경우
        if state.entities.get('food_type') or '추천' in query:
            # 컨텍스트 기반 검색
            search_query = state.entities.get('food_type', query)
            
            # 향상된 검색 수행
            search_results = self.enhanced_retriever.search_by_context(
                search_query,
                state.entities,
                top_k=5
            )
            
            logger.info(f"검색 완료: {len(search_results)}개 결과")
            
            # 컨텍스트 응답 생성
            response = self.contextual_generator.generate_response(
                self.current_session,
                search_results,
                search_query,
                intent
            )
            
            return response
        
        # 인사말이나 기타 의도
        return self.contextual_generator.generate_response(
            self.current_session,
            [],
            query,
            intent
        )
    
    def get_session_history(self) -> Dict:
        """현재 세션 기록 반환"""
        if self.current_session:
            return self.session_manager.export_session(self.current_session.session_id)
        return {}

def main():
    """테스트용 메인 함수"""
    # 설정 로드
    config = Config()
    
    # 챗봇 초기화
    chatbot = ContextAwareNaviyamChatbot(config)
    
    print("=" * 50)
    print("컨텍스트 인식 나비얌 챗봇")
    print("종료하려면 'exit' 또는 '종료'를 입력하세요.")
    print("=" * 50)
    
    # 세션 시작
    session_id = chatbot.start_session()
    print(f"세션 ID: {session_id}")
    print()
    
    while True:
        try:
            user_input = input("사용자: ").strip()
            
            if user_input.lower() in ['exit', '종료', 'quit']:
                print("챗봇을 종료합니다. 감사합니다!")
                break
            
            # 응답 생성
            response = chatbot.process_message(user_input, session_id)
            print(f"챗봇: {response}")
            print()
            
        except KeyboardInterrupt:
            print("\n챗봇을 종료합니다.")
            break
        except Exception as e:
            print(f"오류 발생: {str(e)}")
            logger.error(f"대화 중 오류: {str(e)}", exc_info=True)

if __name__ == "__main__":
    main()