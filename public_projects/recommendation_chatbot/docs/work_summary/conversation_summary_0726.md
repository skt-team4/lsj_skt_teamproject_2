# 나비얌 챗봇 개발 대화 요약 - 2025.07.26

## 🔍 대화 시작점
사용자가 어제(0725) 작업 내용을 바탕으로 전체 시스템 아키텍처를 이해하고 개선 방향을 논의하며 시작

## 🛠️ 주요 분석 및 개선 사항

### 1. 어제 작업 내용 분석 (Gemini 협력)
- **현재 시스템 완성도**: 85% 신뢰도의 LoRA 학습 시스템 완전 구축
- **완성된 MLOps 파이프라인**: 데이터 수집 → 품질 필터링 → LoRA 훈련 → 성능 평가 → 자동 배포
- **검증 완료**: 모의 훈련 성공률 100%, 에러 복구율 100%
- **데이터 현황**: sample_data.xlsx에서 11개 가게 정보, 1,600-2,400개 대화 쌍 생성 가능

### 2. 전체 코드베이스 구조 분석
#### **장점**
- 명확한 모듈 분리 (training/, inference/, nlp/, data/, utils/)
- 자동화된 MLOps 파이프라인
- 개인화 최적화 설계

#### **기술 부채**
- `lora_trainer.py` 731줄 복잡성 (God Object 패턴)
- 파일 기반 데이터 관리의 확장성 한계
- CLI 종속성

## 🎯 핵심 시스템 아키텍처 개선안

### 사용자 원래 계획 vs Gemini 개선 제안

#### **사용자 원안 (LoRA Fine-tuning 중심)**
```
DB 데이터 → LoRA 학습 → 챗봇이 모든 정보 '암기'
새 정보 추가 → 다시 LoRA 학습 → 암기 업데이트
```

#### **Gemini 개선안 (RAG 패턴 도입)**
```
챗봇: '대화 방법'만 학습 (LoRA)
실제 정보: '암기하지 않고' 실시간 DB 검색 (RAG)
사용자 질문 → DB 검색 → 검색 결과 보고 답변 생성
```

### RAG vs 기존 방식 비교

| 항목 | 기존 LoRA 방식 | RAG 개선안 |
|------|----------------|------------|
| **최신 정보 반영** | 전체 재학습 필요 (시간/비용 소모) | DB 추가만으로 즉시 반영 |
| **정확성** | 환각 현상 가능 | DB 기반 정확한 정보 |
| **확장성** | 데이터 증가시 모델 무거워짐 | 모델 크기 영향 없음 |
| **유지보수** | 대화+지식 혼재로 복잡 | 대화/지식 분리로 단순 |

## 🗃️ RAG의 핵심: Vector DB 저장 방식

### 일반 DB vs Vector DB
- **일반 DB**: 정확한 키워드 매칭 (`SELECT * WHERE name = '치킨마요덮밥'`)
- **Vector DB**: 의미 기반 매칭 (텍스트 → 수치 좌표 → 유사도 검색)

### Vector DB 동작 원리
```python
# 1. 저장 시
store_info = "멕시칸 치킨닭은 양식을 파는 가게입니다. 치킨마요덮밥 8900원"
vector = embedding_model.encode(store_info)  # → [0.12, -0.78, 0.45...]
vector_db.store(vector, store_info, metadata={"price": 8900})

# 2. 검색 시  
user_query = "치킨 먹고 싶은데 만원 이하로"
query_vector = embedding_model.encode(user_query)  # → [0.15, -0.65, 0.41...]
results = vector_db.similarity_search(query_vector, filters={"price": {"$lte": 10000}})
```

## 🤖 개인화 챗봇 구현 전략

### RAG + 개인화 결합 구조
```
사용자 입력
    ↓
챗봇 NLU (개인 프로필 반영)
    ↓
구조화 쿼리 생성
    ↓
추천시스템 API + RAG 검색
    ↓
개인화된 자연어 응답 생성
```

### 개인화 데이터 수집 및 활용
#### **취향 추출 과정**
```python
# 대화에서 실시간 추출
사용자: "매운 거 별로..."
→ 추출: {"category": "taste", "value": "spicy", "sentiment": "negative"}
→ 저장: taste_preferences["매운맛"] = -0.8
```

#### **프로필 기반 추천**
```python
# 프로필 → 구조화 쿼리
user_profile = {"taste_preferences": {"매운맛": -0.8}, "budget": 10000}
structured_query = {
    "exclude_taste": ["spicy"],
    "max_price": 10000
}
```

## 🌊 전체 추천 시스템 End-to-End 플로우

### Phase 1: 초기 시스템 구축 (오프라인)
```
회사 DB
    ↓ [ETL]
    ├─ LoRA 학습용 대화 데이터 (.jsonl)
    ├─ Vector DB용 상세 설명 텍스트
    └─ 추천엔진용 Item-Feature Matrix
    ↓
각 시스템 초기화 (챗봇, Vector DB, 추천엔진)
```

### Phase 2: 첫 사용자 대화 (실시간)
```
신규 사용자 → 온보딩 → 기본 취향 수집
    ↓
사용자 질문: "강남역 근처 파스타"
    ↓
[1] 추천엔진: 콘텐츠 기반 필터링 → 후보군 생성
[2] Vector DB: RAG 검색 → 상세 정보 보강  
[3] 챗봇: 결합하여 개인화 응답 생성
    ↓
프로필 저장 → 다음 대화 시 활용
```

### Phase 3: 지속적 학습 (순환)
```
사용자 피드백 수집 → 프로필 업데이트
    ↓ [주기적]
실제 대화 로그 → LoRA 재학습 → 성능 개선
    ↓
협업 필터링 도입 → "비슷한 취향 사용자들이 좋아한 가게"
```

### Phase 4: 시스템 업데이트 (유지보수)
```
회사 DB 신규 데이터 → Vector DB + 추천엔진 업데이트
알고리즘 개선 → A/B 테스트 → 배포
```

## 🔧 현재 나비얌 코드 구현 현황

### ✅ 이미 구현된 기능들
- **LoRA 학습 시스템**: `training/lora_trainer.py` (731줄, 자동 스케줄링)
- **사용자 프로필 관리**: `inference/user_manager.py`, `outputs/user_profiles/`
- **학습 데이터 수집**: `inference/data_collector.py`, `outputs/learning_data/`
- **임시 추천엔진**: `inference/response_generator.py` - `RecommendationEngine` 클래스
- **개인화 데이터 구조**: `data/data_structure.py` - `UserProfile` 클래스
- **배치 스케줄러**: `training/batch_scheduler.py`
- **테스트 시스템**: `tests/` (85% 신뢰도 검증 완료)

### 🔄 추가 구현 필요
- **Vector DB 연동**: RAG 시스템 구축
- **추천시스템 API 인터페이스**: 외부 추천엔진 연동 준비
- **실시간 취향 추출**: 대화에서 자동 프로필 업데이트
- **Tool/Function Calling**: LLM의 API 호출 결정 시스템

### 📊 현재 추천엔진 현황
```python
# inference/response_generator.py
class RecommendationEngine:
    """간단한 추천 엔진 (Matrix Factorization 전까지의 임시)"""
    
    def recommend_by_food_type()     # 카테고리별 추천
    def recommend_by_budget()        # 예산별 추천
    def recommend_coupons()          # 쿠폰 추천
```

**현재 방식**: 규칙 기반 필터링 + 착한가게 우선순위
**미래 계획**: 협업 필터링 → 하이브리드 → 딥러닝 추천

## 📋 다음 단계 우선순위

### 🥇 1순위: 기술 부채 해소
- `lora_trainer.py` 리팩토링 (`DataLoader`, `Trainer`, `Evaluator`, `Deployer` 분리)
- 의존성 주입(Dependency Injection) 도입
- 데이터 구조 강제 (Pydantic 활용)

### 🥈 2순위: RAG 시스템 구축  
- Vector DB 연동 (Chroma, Pinecone, 또는 PostgreSQL pgvector)
- Embedding 모델 도입 (OpenAI embedding, SentenceTransformers)
- 의미 기반 검색 로직 구현

### 🥉 3순위: 확장성 개선
- SQLite 도입으로 파일 기반 → DB 기반 전환
- 추천시스템 표준 인터페이스 설계
- 평가 및 모니터링 시스템 구축

### 🏅 4순위: 서비스화 준비
- FastAPI 기반 REST API 서버 구축  
- A/B 테스트 및 Canary 배포 시스템
- 성능 최적화 (모델 양자화, 캐싱)

## 🎯 핵심 개선안 요약

### 기존 아키텍처
```
사용자 질문 → 챗봇(암기 기반) → 응답
```

### 개선된 아키텍처  
```
사용자 질문 
    ↓
챗봇 NLU (프로필 반영)
    ↓
추천엔진 (알고리즘) + Vector DB (RAG)
    ↓
챗봇 NLG (개인화 응답)
    ↓
사용자 + 프로필 업데이트
```

## 🔮 향후 발전 방향

### 단기 (1-3개월)
- RAG 시스템 완성
- 현재 임시 추천엔진 개선  
- 사용자 피드백 수집 체계 구축

### 중기 (3-6개월)  
- 협업 필터링 도입
- 실시간 개인화 점수 계산
- 외부 추천엔진과의 연동

### 장기 (6개월+)
- Neural Collaborative Filtering
- 실시간 임베딩 업데이트
- 멀티모달 추천 (이미지, 위치 등)

---

## 📊 최종 상태

**현재 시스템**: 85% 신뢰도의 완전한 LoRA 학습 파이프라인 + 임시 추천엔진
**개선 방향**: RAG 패턴 도입 + 개인화 강화 + 확장성 개선
**다음 작업**: 기술 부채 해소 → RAG 구축 → 서비스화

*대화 요약 생성일: 2025.07.26*  
*상태: 시스템 아키텍처 개선 방향 확정, RAG 도입 계획 수립 완료*