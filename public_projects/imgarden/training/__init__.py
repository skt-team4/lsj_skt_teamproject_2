"""
나비얌 챗봇 학습 모듈
데이터 생성, 트레이닝, 파인튜닝을 담당
"""

from .data_generator import (
    NaviyamDataGenerator,
    generate_training_dataset
)

from .trainer import (
    NaviyamTrainer,
    create_trainer,
    quick_intent_training
)

from .fine_tuner import (
    NaviyamFineTuner,
    create_fine_tuner,
    quick_domain_fine_tuning,
    evaluate_fine_tuning_quality
)

__all__ = [
    # 데이터 생성
    'NaviyamDataGenerator',
    'generate_training_dataset',

    # 기본 트레이닝
    'NaviyamTrainer',
    'create_trainer',
    'quick_intent_training',

    # 파인튜닝
    'NaviyamFineTuner',
    'create_fine_tuner',
    'quick_domain_fine_tuning',
    'evaluate_fine_tuning_quality'
]

# 버전 정보
__version__ = "1.0.0"

# 모듈 정보
__author__ = "NaviYam Team"
__description__ = "나비얌 챗봇 학습 모듈"