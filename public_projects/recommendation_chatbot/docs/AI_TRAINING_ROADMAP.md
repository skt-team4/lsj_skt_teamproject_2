# AI 모델 학습 로드맵

*작성일: 2025.07.31*  
*Gemini-Claude 협력 분석 결과*  
*대상: AI 개발팀*

---

## 🎯 **현재 상황**

### **실제 사용 중인 AI 모델들**
- **SKT A.X 3.1 Lite**: 실제 설치해서 사용 중 ✅
- **KoAlpaca**: 실험용으로만 사용 (프로덕션 아님)
- **상용 API (GPT, HyperCLOVA)**: 사용하지 않음

### **⚡ 수정된 모델별 학습 상태** (실제 코드베이스 재확인 결과)
- ✅ **sentence-transformers**: 사전 훈련된 모델 그대로 사용 가능
- ✅ **FAISS**: 알고리즘 자체는 학습 불필요, 벡터 인덱스만 구축
- ✅ **SKT A.X 3.1 Lite**: 기본 한국어 처리 가능
- ✅ **Wide&Deep 추천엔진**: **이미 구현 완료!** (ranking_model.py 453줄 + 전체 시스템)
  - 📁 구현된 파일들:
    - `ranking_model.py` (453줄) - Wide&Deep 신경망
    - `model_trainer.py` (502줄) - 학습 시스템  
    - `recommendation_engine.py` (914줄) - 전체 추천 엔진
    - `feature_engineering.py` (464줄) - Feature 처리
    - 4-Funnel 시스템 완벽 구현
- 🔧 **A.X 3.1 Lite LoRA**: 선택적 도메인 특화 파인튜닝

---

## 🚀 **실용적 3단계 학습 전략**

### **Phase 1: 기본 시스템 구축 (1주)**

#### **목표**: SKT A.X 3.1 Lite + RAG 시스템 동작 확인

```python
# 1. A.X 3.1 Lite 모델 로딩
from models.ax_model import AXModel
ax_model = AXModel.from_pretrained("skt/A.X-3.1-Light")

# 2. RAG 시스템 구축
from sentence_transformers import SentenceTransformer
sentence_model = SentenceTransformer('multilingual-E5-large')
faiss_index = build_shop_index(shop_data)

# 3. 기본 동작 테스트
user_input = "급식카드 되는 치킨집 추천해줘"
response = ax_model.generate(user_input)
print(f"A.X 응답: {response}")
```

#### **완료 조건**
- [ ] A.X 3.1 Lite 모델 정상 로딩
- [ ] RAG 벡터 검색 동작 확인
- [ ] 기본 질문-응답 테스트 통과

---

### **Phase 2: Wide&Deep 추천엔진 데이터 학습 (1-2주) 🔥 최우선**

#### **목표**: 구현된 추천 시스템에 실제 데이터로 학습

#### **✅ 이미 구현된 것들**
```python
# 모든 코드가 이미 완성되어 있음!
from recommendation.ranking_model import WideAndDeepRankingModel  # ✅ 완성
from recommendation.model_trainer import ModelTrainer             # ✅ 완성
from recommendation.feature_engineering import FeatureEngineer   # ✅ 완성
from recommendation.recommendation_engine import RecommendationEngine  # ✅ 완성
```

#### **필요한 작업 (데이터 준비만)**
```python
# 1. 실제 데이터 연결
user_shop_data = load_from_sample_data_xlsx()  # sample_data.xlsx 활용

# 2. 기존 구현된 시스템으로 학습
trainer = ModelTrainer()  # 이미 구현됨
trainer.train(user_shop_data)  # 바로 실행 가능

# 3. 학습된 모델 저장
trainer.save_model("outputs/recommendation_models/trained_model.pth")
```

#### **최소 데이터 요구사항**
```python
minimum_data = {
    "user_shop_interactions": 1000,  # ticket 테이블 데이터
    "users": 100,                    # user 테이블 데이터  
    "shops": 50,                     # shop 테이블 데이터
    "time_span": "1개월"             # 최소 데이터 기간
}
```

#### **완료 조건**
- [ ] 1000개 이상 상호작용 데이터 수집
- [ ] Wide&Deep 모델 학습 완료
- [ ] 추천 정확도 70% 이상 달성
- [ ] A/B 테스트로 성능 검증

---

### **Phase 3: A.X 모델 도메인 특화 (선택적, 2-3주)**

#### **목표**: 음식 추천 도메인 특화 성능 향상

#### **LoRA 파인튜닝 설정**
```python
# LoRA 설정
from peft import LoraConfig, get_peft_model

lora_config = LoraConfig(
    r=16,                                    # LoRA rank
    lora_alpha=32,                          # scaling parameter
    target_modules=["q_proj", "v_proj", "k_proj", "o_proj"],
    lora_dropout=0.1,
    bias="none",
    task_type="CAUSAL_LM"
)

# A.X 모델에 LoRA 적용
peft_model = get_peft_model(ax_model.model, lora_config)
```

#### **파인튜닝 데이터**
```python
# 도메인 특화 학습 데이터
training_scenarios = {
    "급식카드_문의": [
        {"input": "급식카드 되는 곳 있어?", "output": "급식카드 사용 가능한 가게를 찾아드릴게요!"},
        {"input": "아동급식카드 쓸 수 있는 치킨집은?", "output": "네! 급식카드로 이용 가능한 치킨집 추천드려요"}
    ],
    "청소년_언어": [
        {"input": "JMT 맛집 추천해줘", "output": "존맛탱 맛집 추천드릴게요! 🔥"},
        {"input": "레게노 맛있는 피자집은?", "output": "정말 맛있는 피자집 찾아드릴게요!"}
    ]
}
```

#### **완료 조건**
- [ ] 500개 이상 도메인 특화 대화 데이터 수집
- [ ] LoRA 파인튜닝 완료
- [ ] 청소년 언어 패턴 이해도 향상 확인
- [ ] NLU 정확도 90% 이상 달성

---

## 📊 **우선순위 및 일정**

### **핵심 우선순위**
1. **🔥 Wide&Deep 추천엔진 학습** (가장 중요)
   - 현재 A.X 3.1 Lite는 이미 사용 가능
   - 추천 시스템만 없으면 개인화 불가능

2. **🔧 RAG 시스템 구축** (비교적 쉬움)
   - 사전 훈련된 모델 활용
   - 벡터 인덱스만 구축하면 됨

3. **⭐ A.X LoRA 파인튜닝** (선택적)
   - 성능 향상 목적
   - 기본 모델도 충분히 사용 가능

### **예상 일정**
```
Week 1: Phase 1 (기본 시스템)
Week 2-4: Phase 2 (Wide&Deep 학습) <- 핵심
Week 5-7: Phase 3 (LoRA 파인튜닝, 선택적)
```

---

## ⚠️ **주의사항**

### **데이터 요구사항**
- **Wide&Deep**: 최소 1000개 실제 사용자-가게 상호작용 데이터 필수
- **LoRA**: 최소 500개 음식 추천 대화 데이터 권장

### **하드웨어 요구사항**
- **Wide&Deep**: GPU 불필요 (CPU로도 학습 가능)
- **A.X LoRA**: RTX 3060 Ti 이상 권장

### **성공 지표**
- **추천 정확도**: 70% 이상
- **응답 관련성**: 85% 이상
- **청소년 언어 이해도**: 90% 이상

---

## 🎯 **수정된 결론**

**🎉 대부분의 AI 모듈이 이미 완성되어 있습니다!**

#### **실제 상황 정리:**
- ✅ **SKT A.X 3.1 Lite**: 설치 완료, 바로 사용 가능
- ✅ **Wide&Deep 추천엔진**: **코드 완전 구현 완료** (3,800+ 줄)
- ✅ **sentence-transformers + FAISS**: 사전 훈련된 모델 활용 가능
- ✅ **전체 시스템**: 92% 완성도 (conversation_summary 확인)

#### **실제 필요한 작업:**
**코드 구현 ❌** → **데이터 학습 ✅**

### **실행 순서**
1. ✅ A.X 3.1 Lite + RAG 기본 동작 확인
2. 🔥 Wide&Deep 모델 학습 (핵심)
3. ⭐ 필요시 LoRA 파인튜닝으로 성능 향상

이 로드맵을 따르면 **4-7주 내에 완전한 개인화 음식 추천 챗봇**을 구축할 수 있습니다.