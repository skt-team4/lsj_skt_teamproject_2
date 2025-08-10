"""
LoRA 학습 데이터 관리
데이터 수집, 품질 검사, 전처리를 담당하는 클래스
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass

from inference.data_collector import LearningDataCollector

logger = logging.getLogger(__name__)


@dataclass
class DataQualityConfig:
    """데이터 품질 검사 설정"""
    min_input_length: int = 3
    min_response_length: int = 5
    quality_threshold: float = 0.7
    max_samples_per_batch: int = 200
    exclude_error_patterns: List[str] = None
    
    def __post_init__(self):
        if self.exclude_error_patterns is None:
            self.exclude_error_patterns = ["오류", "실패", "죄송", "모르겠"]


class LoRADataManager:
    """LoRA 학습용 데이터 관리 클래스"""
    
    def __init__(self, data_collector: LearningDataCollector, 
                 quality_config: DataQualityConfig = None):
        """
        Args:
            data_collector: 학습 데이터 수집기
            quality_config: 데이터 품질 검사 설정
        """
        self.data_collector = data_collector
        self.quality_config = quality_config or DataQualityConfig()
        
        logger.info("LoRADataManager 초기화 완료")
    
    def collect_training_data(self, days: int = 7) -> List[Dict]:
        """훈련용 데이터 수집
        
        Args:
            days: 수집할 데이터의 일수
            
        Returns:
            품질 검사를 통과한 훈련 데이터 리스트
        """
        logger.info(f"훈련 데이터 수집 시작 (최근 {days}일)")
        
        # 1. 원시 데이터 수집
        all_data = self.data_collector.get_recent_data(days=days)
        logger.info(f"원시 데이터 수집: {len(all_data)}개")
        
        # 2. 품질 필터링
        quality_data = []
        for data in all_data:
            if self.is_high_quality_data(data):
                quality_data.append(data)
        
        logger.info(f"품질 필터링 후: {len(quality_data)}개")
        
        # 3. 샘플 수 제한 (최신 데이터 우선)
        if len(quality_data) > self.quality_config.max_samples_per_batch:
            quality_data = sorted(
                quality_data, 
                key=lambda x: x.get('timestamp', datetime.min), 
                reverse=True
            )
            quality_data = quality_data[:self.quality_config.max_samples_per_batch]
            logger.info(f"샘플 수 제한: {len(quality_data)}개")
        
        return quality_data
    
    def is_high_quality_data(self, data: Dict) -> bool:
        """데이터 품질 검사
        
        Args:
            data: 검사할 데이터
            
        Returns:
            품질 검사 통과 여부
        """
        # 1. 기본 필드 확인
        if not data.get('user_input') or not data.get('bot_response'):
            return False
        
        # 2. 길이 확인
        if (len(data['user_input']) < self.quality_config.min_input_length or 
            len(data['bot_response']) < self.quality_config.min_response_length):
            return False
        
        # 3. 품질 점수 확인
        quality_score = data.get('quality_score', 0.0)
        if quality_score < self.quality_config.quality_threshold:
            return False
        
        # 4. 에러 패턴 제외
        bot_response = data['bot_response'].lower()
        if any(pattern in bot_response for pattern in self.quality_config.exclude_error_patterns):
            return False
        
        return True
    
    def convert_to_training_samples(self, data_list: List[Dict], 
                                  tokenizer, max_length: int = 512) -> List[Dict]:
        """데이터를 훈련 샘플로 변환
        
        Args:
            data_list: 변환할 데이터 리스트
            tokenizer: 토크나이저
            max_length: 최대 토큰 길이
            
        Returns:
            토크나이징된 훈련 샘플 리스트
        """
        training_samples = []
        
        for data in data_list:
            sample = self._convert_single_sample(data, tokenizer, max_length)
            if sample:
                training_samples.append(sample)
        
        logger.info(f"훈련 샘플 변환 완료: {len(training_samples)}개")
        return training_samples
    
    def _convert_single_sample(self, data: Dict, tokenizer, max_length: int) -> Optional[Dict]:
        """단일 데이터를 훈련 샘플로 변환"""
        try:
            user_input = data['user_input']
            bot_response = data['bot_response']
            
            # 나비얌 프롬프트 형식
            prompt_template = """당신은 나비얌, 아동을 위한 착한가게 추천 AI입니다.
친근하고 따뜻한 톤으로 음식을 추천해주세요.

사용자: {user_input}
나비얌: {bot_response}"""
            
            formatted_text = prompt_template.format(
                user_input=user_input,
                bot_response=bot_response
            )
            
            # 토크나이징
            tokens = tokenizer(
                formatted_text,
                truncation=True,
                padding=False,
                max_length=max_length,
                return_tensors=None
            )
            
            return {
                "input_ids": tokens["input_ids"],
                "attention_mask": tokens["attention_mask"],
                "labels": tokens["input_ids"].copy()  # Causal LM에서는 input과 label이 동일
            }
            
        except Exception as e:
            logger.warning(f"훈련 샘플 변환 실패: {e}")
            return None
    
    def get_data_statistics(self, data_list: List[Dict]) -> Dict[str, Any]:
        """데이터 통계 정보 반환"""
        if not data_list:
            return {"count": 0}
        
        # 기본 통계
        stats = {
            "count": len(data_list),
            "avg_input_length": sum(len(d.get('user_input', '')) for d in data_list) / len(data_list),
            "avg_response_length": sum(len(d.get('bot_response', '')) for d in data_list) / len(data_list),
        }
        
        # 품질 점수 통계
        quality_scores = [d.get('quality_score', 0.0) for d in data_list if 'quality_score' in d]
        if quality_scores:
            stats["avg_quality_score"] = sum(quality_scores) / len(quality_scores)
            stats["min_quality_score"] = min(quality_scores)
            stats["max_quality_score"] = max(quality_scores)
        
        return stats