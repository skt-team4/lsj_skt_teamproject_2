"""
LoRA 어댑터 성능 평가 클래스
어댑터 성능 측정, 응답 품질 평가, 배포 결정을 담당
"""

import logging
from typing import List, Dict, Any, Tuple
from pathlib import Path
import re

from models.koalpaca_model import KoAlpacaModel

logger = logging.getLogger(__name__)


class LoRAEvaluator:
    """LoRA 어댑터 성능 평가 클래스"""
    
    def __init__(self, model: KoAlpacaModel):
        """
        Args:
            model: 평가할 모델
        """
        self.model = model
        
        # 평가용 테스트 케이스
        self.test_cases = [
            {
                "input": "치킨 먹고 싶어",
                "expected_keywords": ["치킨", "추천", "맛있는", "가게"],
                "type": "food_recommendation"
            },
            {
                "input": "2만원으로 뭐 먹을까?",
                "expected_keywords": ["2만원", "예산", "추천", "메뉴"],
                "type": "budget_recommendation"
            },
            {
                "input": "혼밥하기 좋은 곳 있을까?",
                "expected_keywords": ["혼밥", "1인", "좋은", "가게"],
                "type": "dining_style"
            },
            {
                "input": "착한가게가 뭐야?",
                "expected_keywords": ["착한가게", "좋은", "선택", "혜택"],
                "type": "concept_explanation"
            },
            {
                "input": "안녕하세요",
                "expected_keywords": ["안녕", "나비얌", "도움", "추천"],
                "type": "greeting"
            }
        ]
        
        logger.info("LoRAEvaluator 초기화 완료")
    
    def evaluate_adapter_performance(self, adapter_name: str, 
                                   adapter_path: str = None) -> Dict[str, float]:
        """어댑터 성능 평가
        
        Args:
            adapter_name: 평가할 어댑터 이름
            adapter_path: 어댑터 파일 경로 (None이면 자동 추론)
            
        Returns:
            성능 지표 딕셔너리
        """
        logger.info(f"어댑터 성능 평가 시작: {adapter_name}")
        
        try:
            # 어댑터 로드 (실제 구현에서는 LoRA 어댑터 로딩 필요)
            if adapter_path:
                logger.info(f"어댑터 로드: {adapter_path}")
                # TODO: 실제 LoRA 어댑터 로딩 구현
            
            # 테스트 케이스별 평가
            total_score = 0.0
            keyword_scores = []
            quality_scores = []
            response_times = []
            
            for i, test_case in enumerate(self.test_cases):
                logger.debug(f"테스트 케이스 {i+1}/{len(self.test_cases)}: {test_case['input']}")
                
                # 응답 생성 및 시간 측정
                import time
                start_time = time.time()
                response = self.generate_test_response(test_case["input"])
                response_time = time.time() - start_time
                response_times.append(response_time)
                
                # 키워드 매칭 점수
                keyword_score = self.calculate_keyword_score(
                    response, test_case["expected_keywords"]
                )
                keyword_scores.append(keyword_score)
                
                # 응답 품질 점수
                quality_score = self.calculate_response_quality(response)
                quality_scores.append(quality_score)
                
                logger.debug(f"응답: {response[:50]}...")
                logger.debug(f"키워드 점수: {keyword_score:.3f}, 품질 점수: {quality_score:.3f}")
            
            # 전체 성능 지표 계산
            performance = {
                "overall_score": (sum(keyword_scores) + sum(quality_scores)) / (2 * len(self.test_cases)),
                "keyword_score": sum(keyword_scores) / len(keyword_scores),
                "quality_score": sum(quality_scores) / len(quality_scores),
                "avg_response_time": sum(response_times) / len(response_times),
                "max_response_time": max(response_times),
                "test_cases_passed": len([s for s in keyword_scores if s > 0.5]),
                "total_test_cases": len(self.test_cases)
            }
            
            logger.info(f"어댑터 성능 평가 완료: {adapter_name}")
            logger.info(f"전체 점수: {performance['overall_score']:.3f}")
            logger.info(f"키워드 점수: {performance['keyword_score']:.3f}")
            logger.info(f"품질 점수: {performance['quality_score']:.3f}")
            logger.info(f"평균 응답 시간: {performance['avg_response_time']:.3f}초")
            
            return performance
            
        except Exception as e:
            logger.error(f"어댑터 성능 평가 실패: {e}")
            return {
                "overall_score": 0.0,
                "keyword_score": 0.0,
                "quality_score": 0.0,
                "avg_response_time": 999.0,
                "error": str(e)
            }
    
    def generate_test_response(self, input_text: str) -> str:
        """테스트 응답 생성
        
        Args:
            input_text: 입력 텍스트
            
        Returns:
            생성된 응답
        """
        try:
            # 간단한 프롬프트 구성
            prompt = f"""당신은 나비얌, 아동을 위한 착한가게 추천 AI입니다.
친근하고 따뜻한 톤으로 음식을 추천해주세요.

사용자: {input_text}
나비얌: """
            
            # 모델을 통한 응답 생성
            if hasattr(self.model, 'generate_response'):
                response = self.model.generate_response(prompt, max_length=150)
            else:
                # 폴백: 간단한 응답
                response = "안녕하세요! 나비얌이에요. 맛있는 음식을 추천해드릴게요!"
            
            # 프롬프트 부분 제거하여 순수 응답만 추출
            if "나비얌: " in response:
                response = response.split("나비얌: ")[-1].strip()
            
            return response
            
        except Exception as e:
            logger.warning(f"테스트 응답 생성 실패: {e}")
            return "응답 생성에 실패했습니다."
    
    def calculate_keyword_score(self, response: str, expected_keywords: List[str]) -> float:
        """키워드 매칭 점수 계산
        
        Args:
            response: 생성된 응답
            expected_keywords: 기대되는 키워드 리스트
            
        Returns:
            키워드 매칭 점수 (0.0 ~ 1.0)
        """
        if not expected_keywords:
            return 1.0
        
        response_lower = response.lower()
        matched_keywords = 0
        
        for keyword in expected_keywords:
            if keyword.lower() in response_lower:
                matched_keywords += 1
        
        score = matched_keywords / len(expected_keywords)
        return score
    
    def calculate_response_quality(self, response: str) -> float:
        """응답 품질 점수 계산
        
        Args:
            response: 생성된 응답
            
        Returns:
            품질 점수 (0.0 ~ 1.0)
        """
        if not response or len(response.strip()) < 5:
            return 0.0
        
        quality_score = 0.0
        
        # 1. 길이 적절성 (10-200자 권장)
        length = len(response.strip())
        if 10 <= length <= 200:
            quality_score += 0.3
        elif length > 5:
            quality_score += 0.1
        
        # 2. 한국어 비율
        korean_chars = len(re.findall(r'[가-힣]', response))
        korean_ratio = korean_chars / len(response) if response else 0
        if korean_ratio > 0.5:
            quality_score += 0.2
        
        # 3. 긍정적 표현 포함
        positive_patterns = ["추천", "좋은", "맛있는", "도움", "최고", "훌륭", "완벽"]
        positive_count = sum(1 for pattern in positive_patterns if pattern in response)
        if positive_count > 0:
            quality_score += 0.2
        
        # 4. 부정적 표현 제외
        negative_patterns = ["죄송", "모르겠", "실패", "오류", "불가능"]
        negative_count = sum(1 for pattern in negative_patterns if pattern in response)
        if negative_count == 0:
            quality_score += 0.2
        
        # 5. 완전한 문장 형태
        if response.strip().endswith(('.', '!', '?', '요', '다', '네', '죠')):
            quality_score += 0.1
        
        return min(quality_score, 1.0)
    
    def should_deploy_adapter(self, adapter_name: str, performance: Dict[str, float],
                            deployment_threshold: float = 0.7) -> bool:
        """어댑터 배포 여부 결정
        
        Args:
            adapter_name: 어댑터 이름
            performance: 성능 지표
            deployment_threshold: 배포 임계값
            
        Returns:
            배포 여부
        """
        overall_score = performance.get("overall_score", 0.0)
        
        # 기본 점수 확인
        if overall_score < deployment_threshold:
            logger.info(f"배포 거부: {adapter_name} (점수: {overall_score:.3f} < {deployment_threshold})")
            return False
        
        # 응답 시간 확인 (5초 이상이면 거부)
        avg_response_time = performance.get("avg_response_time", 999.0)
        if avg_response_time > 5.0:
            logger.info(f"배포 거부: {adapter_name} (응답시간: {avg_response_time:.3f}초 > 5초)")
            return False
        
        # 테스트 케이스 통과율 확인 (50% 이상)
        test_cases_passed = performance.get("test_cases_passed", 0)
        total_test_cases = performance.get("total_test_cases", 1)
        pass_rate = test_cases_passed / total_test_cases
        
        if pass_rate < 0.5:
            logger.info(f"배포 거부: {adapter_name} (테스트 통과율: {pass_rate:.1%} < 50%)")
            return False
        
        logger.info(f"배포 승인: {adapter_name} (점수: {overall_score:.3f}, 통과율: {pass_rate:.1%})")
        return True
    
    def compare_adapters(self, adapter_performances: Dict[str, Dict[str, float]]) -> str:
        """여러 어댑터 성능 비교
        
        Args:
            adapter_performances: {어댑터명: 성능지표} 딕셔너리
            
        Returns:
            최고 성능 어댑터 이름
        """
        if not adapter_performances:
            return None
        
        best_adapter = None
        best_score = -1.0
        
        for adapter_name, performance in adapter_performances.items():
            overall_score = performance.get("overall_score", 0.0)
            if overall_score > best_score:
                best_score = overall_score
                best_adapter = adapter_name
        
        logger.info(f"최고 성능 어댑터: {best_adapter} (점수: {best_score:.3f})")
        return best_adapter