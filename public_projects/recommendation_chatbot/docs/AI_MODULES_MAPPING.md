# AI 모듈별 Feature 매핑 가이드

*작성일: 2025.07.31*  
*Gemini-Claude 협력 분석*  
*대상: AI 개발팀, 데이터 사이언스팀*

---

## 🎯 **개요**

나비얌 챗봇의 3가지 AI 모듈 (SKT A.X 3.1 Lite, RAG, Wide&Deep 추천엔진)이 sample_data.xlsx의 31개 테이블을 어떻게 활용하는지 상세 매핑 가이드입니다.

**시스템 아키텍처**:
```
사용자 질문 → A.X 3.1 Lite(NLU) → RAG 검색 → Wide&Deep 추천 → A.X 3.1 Lite(NLG)
```

---

## 🤖 **모듈 1: SKT A.X 3.1 Lite 시스템 (+ LoRA 선택적)**

**현재 상태**: ✅ 기본 모델 설치 완료, 선택적 도메인 특화 파인튜닝

### **목적 및 역할**
- 사용자의 자연어 질문을 이해하고 적절한 응답 생성
- 아동~청소년의 언어 패턴 학습 (은어, 줄임말, 급식카드 표현)
- 의도 파악 및 엔티티 추출

### **활용 테이블 및 Feature 매핑**

#### **학습 데이터 생성용 테이블**
```sql
-- 1. 도메인 지식 학습 (shop 테이블)
SELECT 
  shopName,                    -- 가게명 학습
  category,                    -- 음식 카테고리 이해
  addressName,                 -- 지역명 학습  
  isGoodInfluenceShop,        -- 착한가게 개념 학습
  openHour, closeHour,        -- 영업시간 이해
  offDay                      -- 휴무일 정보
FROM shop;

-- 2. 메뉴 정보 학습 (shop_menu 테이블)  
SELECT 
  name,                       -- 메뉴명 학습
  description,                -- 메뉴 설명 이해
  price,                      -- 가격 정보 학습
  is_best,                    -- 인기 메뉴 개념
  is_sold_out               -- 품절 상태 이해
FROM shop_menu;

-- 3. 실제 사용자 표현 학습 (review 테이블)
SELECT 
  comment,                    -- 실제 사용자 리뷰 언어
  img_static,                -- 이미지 설명 (선택적)
  createdAt                  -- 최신 표현 트렌드
FROM review
WHERE comment IS NOT NULL;

-- 4. 사용자 프로필 기반 페르소나 (user 테이블)
SELECT 
  CASE 
    WHEN TIMESTAMPDIFF(YEAR, birthday, CURDATE()) BETWEEN 7 AND 12 THEN '초등학생'
    WHEN TIMESTAMPDIFF(YEAR, birthday, CURDATE()) BETWEEN 13 AND 15 THEN '중학생'  
    WHEN TIMESTAMPDIFF(YEAR, birthday, CURDATE()) BETWEEN 16 AND 18 THEN '고등학생'
  END as age_group,           -- 연령대별 말투 차이 학습
  currentAddress             -- 지역별 표현 차이
FROM user;
```

#### **LoRA 파인튜닝 데이터셋 구조**
```json
{
  "instruction": "청소년 대상 음식 추천 챗봇으로 답변해주세요. 친근하고 이해하기 쉽게 설명해주세요.",
  "input": "급식카드 되는 치킨집 있어? 학교 근처로",
  "output": "네! 급식카드 사용 가능한 치킨집을 찾아드릴게요 🍗 학교가 어느 지역인지 알려주시면 더 정확한 추천을 해드릴 수 있어요. 혹시 매운맛 괜찮으신가요?"
}
```

#### **학습 시나리오 예시**
```python
training_scenarios = {
    "급식카드_문의": [
        "급식카드 되는 곳 있어?",
        "아동급식카드 사용 가능한 가게 알려줘",
        "급식카드로 먹을 수 있는 곳은?"
    ],
    "청소년_은어": [
        "JMT 맛집 추천해줘",
        "존맛탱인 치킨집 어디야?", 
        "레게노 맛있는 피자집은?"
    ],
    "상황별_추천": [
        "시험 스트레스 받을 때 먹을만한 거",
        "친구들이랑 같이 먹기 좋은 곳",
        "혼밥하기 좋은 가게 있어?"
    ]
}
```

---

## 🔍 **모듈 2: RAG 시스템 (sentence-transformers + FAISS)**

**현재 상태**: ✅ 사전 훈련된 모델 사용 가능, 벡터 인덱스만 구축하면 됨

### **목적 및 역할**
- 사용자 질문과 의미적으로 유사한 가게/메뉴 정보 검색
- 벡터 임베딩 기반 의미 검색으로 키워드 매칭의 한계 극복
- 검색된 정보를 챗봇 응답 생성에 컨텍스트로 제공

### **활용 테이블 및 Feature 매핑**

#### **벡터화 대상 문서 생성**
```sql
-- 가게별 통합 정보 문서 생성
CREATE VIEW rag_shop_documents AS
SELECT 
  shop.id as shop_id,
  CONCAT(
    '[가게명: ', shop.shopName, '] ',
    '[카테고리: ', shop.category, '] ',
    '[위치: ', shop.addressName, '] ',
    '[착한가게: ', IF(shop.isGoodInfluenceShop = 1, 'O', 'X'), '] ',
    '[영업시간: ', COALESCE(shop.openHour, '정보없음'), ' ~ ', COALESCE(shop.closeHour, '정보없음'), '] ',
    '[휴무일: ', COALESCE(shop.offDay, '연중무휴'), '] ',
    '[급식카드: ', IF(shop.isFoodCardShop = 1, '사용가능', '사용불가'), '] ',
    '[대표메뉴: ', menu_info.popular_menus, '] ',
    '[가격대: ', menu_info.price_range, '] ',
    '[고객리뷰: ', review_info.review_summary, ']'
  ) as document_text,
  
  -- 메타데이터
  shop.shopName as title,
  shop.category as category,
  shop.addressName as address,
  shop.isGoodInfluenceShop as is_good_shop
  
FROM shop
LEFT JOIN (
  SELECT 
    shop_id,
    GROUP_CONCAT(
      CASE WHEN is_best = 1 THEN CONCAT(name, '★') ELSE name END 
      ORDER BY is_best DESC, priority ASC 
      LIMIT 5
    ) as popular_menus,
    CONCAT(MIN(price), '원~', MAX(price), '원') as price_range
  FROM shop_menu 
  WHERE is_sold_out = 0
  GROUP BY shop_id
) menu_info ON shop.id = menu_info.shop_id
LEFT JOIN (
  SELECT 
    store_id,
    GROUP_CONCAT(
      comment 
      ORDER BY createdAt DESC 
      SEPARATOR ' / '
      LIMIT 3
    ) as review_summary
  FROM review 
  WHERE comment IS NOT NULL AND comment != ''
  GROUP BY store_id
) review_info ON shop.id = review_info.store_id;

-- 메뉴별 상세 문서 생성 (선택적)
CREATE VIEW rag_menu_documents AS
SELECT 
  menu.id as menu_id,
  CONCAT(
    '[메뉴: ', menu.name, '] ',
    '[가게: ', shop.shopName, '] ',
    '[설명: ', COALESCE(menu.description, '설명없음'), '] ',
    '[가격: ', menu.price, '원] ',
    '[카테고리: ', shop.category, '] ',
    IF(menu.is_best = 1, '[베스트메뉴] ', ''),
    IF(shop.isGoodInfluenceShop = 1, '[착한가게] ', ''),
    IF(shop.isFoodCardShop = 1, '[급식카드가능] ', '')
  ) as document_text,
  
  menu.name as title,
  shop.category as category,
  menu.price as price
  
FROM shop_menu menu
JOIN shop ON menu.shop_id = shop.id
WHERE menu.is_sold_out = 0;
```

#### **임베딩 생성 프로세스**
```python
# sentence-transformers를 이용한 벡터화
from sentence_transformers import SentenceTransformer

model = SentenceTransformer('sentence-transformers/xlm-r-100langs-bert-base-nli-stsb-mean-tokens')

# 문서 벡터화
documents = [
    "[가게명: 엄마손치킨] [카테고리: 치킨] [위치: 서울시 강남구] [착한가게: O] [급식카드: 사용가능] [대표메뉴: 후라이드치킨★, 양념치킨] [가격대: 15000원~18000원] [고객리뷰: 바삭하고 맛있어요 / 급식카드도 돼서 좋아요 / 양이 많아서 나눠먹기 좋아요]"
]

embeddings = model.encode(documents)  # 768차원 벡터로 변환
```

#### **검색 대상 필드**
```python
searchable_fields = {
    'primary': [
        'shop.shopName',      # 가게명 직접 검색
        'shop.category',      # 카테고리 매칭
        'menu.name',         # 메뉴명 검색
        'review.comment'     # 리뷰 내용 의미 검색
    ],
    'metadata': [
        'shop.addressName',   # 위치 필터링
        'shop.isGoodInfluenceShop',  # 착한가게 필터
        'shop.isFoodCardShop',       # 급식카드 필터
        'menu.price',        # 가격 범위 필터
        'shop.openHour'      # 영업시간 필터
    ]
}
```

---

## 📊 **모듈 3: Wide&Deep 추천엔진** 🔥 **최우선**

**현재 상태**: ✅ **코드 완전 구현 완료!** (3,800+ 줄의 완성된 시스템)
  - ✅ `ranking_model.py` (453줄) - Wide&Deep 신경망 구현
  - ✅ `model_trainer.py` (502줄) - 학습 시스템 구현  
  - ✅ `recommendation_engine.py` (914줄) - 전체 추천 엔진
  - ✅ `feature_engineering.py` (464줄) - Feature 처리 시스템
  - ✅ 4-Funnel 시스템 (Popularity, Content, Collaborative, Contextual)

**필요 작업**: 데이터로 학습만 하면 됨 (최소 1000개 상호작용 데이터)

### **목적 및 역할**
- 개인화된 가게 추천 (개인 취향 + 일반적 인기도)
- Wide: 명시적 규칙 기반 추천 (연령×카테고리, 시간×음식 등)
- Deep: 잠재 요인 기반 추천 (사용자-가게 임베딩)

### **Wide Component Feature 매핑**

#### **사용자 기반 Features**
```sql
-- Wide 모델용 사용자 Feature
SELECT 
  user.id,
  -- 기본 정보
  CASE 
    WHEN TIMESTAMPDIFF(YEAR, birthday, CURDATE()) BETWEEN 7 AND 12 THEN 'elementary'
    WHEN TIMESTAMPDIFF(YEAR, birthday, CURDATE()) BETWEEN 13 AND 15 THEN 'middle'
    WHEN TIMESTAMPDIFF(YEAR, birthday, CURDATE()) BETWEEN 16 AND 18 THEN 'high'
  END as age_group,
  
  gender,
  SUBSTRING(currentAddress, 1, 6) as region,
  
  -- 활동 패턴
  activity_stats.avg_order_value,
  activity_stats.visit_frequency,
  activity_stats.preferred_time_slot,
  activity_stats.preferred_category
  
FROM user
LEFT JOIN (
  SELECT 
    user_id,
    AVG(point_amount) as avg_order_value,
    COUNT(*) as visit_frequency,
    (SELECT CASE 
       WHEN HOUR(used_at) BETWEEN 11 AND 14 THEN 'lunch'
       WHEN HOUR(used_at) BETWEEN 17 AND 20 THEN 'dinner'
       ELSE 'other'
     END
     FROM ticket t2 WHERE t2.user_id = t1.user_id
     GROUP BY CASE 
       WHEN HOUR(used_at) BETWEEN 11 AND 14 THEN 'lunch'
       WHEN HOUR(used_at) BETWEEN 17 AND 20 THEN 'dinner'
       ELSE 'other'
     END
     ORDER BY COUNT(*) DESC LIMIT 1) as preferred_time_slot,
    (SELECT category FROM shop s 
     JOIN ticket t3 ON s.id = t3.shop_id 
     WHERE t3.user_id = t1.user_id 
     GROUP BY category ORDER BY COUNT(*) DESC LIMIT 1) as preferred_category
  FROM ticket t1
  GROUP BY user_id
) activity_stats ON user.id = activity_stats.user_id;
```

#### **가게 기반 Features**
```sql
-- Wide 모델용 가게 Feature
SELECT 
  shop.id,
  -- 기본 속성
  category,
  CASE 
    WHEN avg_price < 7000 THEN 'budget'
    WHEN avg_price < 15000 THEN 'mid'
    ELSE 'premium'
  END as price_tier,
  
  isGoodInfluenceShop as is_good_shop,
  isFoodCardShop as accepts_meal_card,
  
  CASE 
    WHEN addressName LIKE '%학교%' OR distance_to_school < 0.5 THEN 'school_area'
    WHEN addressName LIKE '%역%' THEN 'station_area'  
    ELSE 'other_area'
  END as location_type,
  
  -- 성과 지표
  performance_stats.popularity_score,
  performance_stats.avg_rating,
  performance_stats.peak_hour
  
FROM shop
LEFT JOIN (
  SELECT shop_id, AVG(price) as avg_price
  FROM shop_menu GROUP BY shop_id
) price_info ON shop.id = price_info.shop_id
LEFT JOIN (
  SELECT 
    shop_id,
    COUNT(DISTINCT user_id) as popularity_score,
    AVG(COALESCE(rating, 3.5)) as avg_rating,
    (SELECT HOUR(used_at) FROM ticket t2 WHERE t2.shop_id = t1.shop_id
     GROUP BY HOUR(used_at) ORDER BY COUNT(*) DESC LIMIT 1) as peak_hour
  FROM ticket t1
  LEFT JOIN review ON t1.shop_id = review.store_id
  GROUP BY shop_id
) performance_stats ON shop.id = performance_stats.shop_id;
```

#### **상황적 Features**
```sql
-- 상황적 Feature (추론 시점에 동적 생성)
SELECT 
  CASE 
    WHEN HOUR(NOW()) BETWEEN 7 AND 10 THEN 'breakfast'
    WHEN HOUR(NOW()) BETWEEN 11 AND 14 THEN 'lunch'
    WHEN HOUR(NOW()) BETWEEN 17 AND 20 THEN 'dinner'
    ELSE 'snack'
  END as current_time_slot,
  
  CASE 
    WHEN WEEKDAY(NOW()) BETWEEN 0 AND 4 THEN 'weekday'
    ELSE 'weekend'
  END as current_day_type,
  
  CASE 
    WHEN MONTH(NOW()) IN (7, 8, 12, 1, 2) THEN 'vacation'
    ELSE 'school_term' 
  END as school_period;
```

#### **교차 Features (Cross Product)**
```sql
-- Wide 모델의 핵심: Feature 교차
SELECT 
  user_id,
  shop_id,
  -- 2-way 교차
  CONCAT(age_group, '_', category) as age_category,
  CONCAT(time_slot, '_', category) as time_category,
  CONCAT(region, '_', location_type) as region_location,
  CONCAT(preferred_category, '_', category) as preference_match,
  
  -- 3-way 교차 (선택적)
  CONCAT(age_group, '_', time_slot, '_', category) as age_time_category,
  CONCAT(day_type, '_', price_tier, '_', is_good_shop) as context_price_shop,
  
  -- 조건부 교차
  CASE 
    WHEN is_good_shop = 1 AND accepts_meal_card = 1 THEN 'ideal_for_students'
    WHEN price_tier = 'budget' AND location_type = 'school_area' THEN 'budget_school'
    ELSE 'regular'
  END as special_combination

FROM user_shop_interactions;
```

### **Deep Component Feature 매핑**

#### **임베딩 Features**
```python
# Deep 모델용 임베딩 Feature
embedding_features = {
    # 카테고리형 ID → 임베딩 벡터
    'user_id': {'vocab_size': user_count, 'embedding_dim': 64},
    'shop_id': {'vocab_size': shop_count, 'embedding_dim': 64},
    'category_id': {'vocab_size': category_count, 'embedding_dim': 16},
    'region_id': {'vocab_size': region_count, 'embedding_dim': 16},
    
    # 다중값 임베딩 (사용자 이력 기반)
    'user_visited_categories': {'max_len': 10, 'embedding_dim': 16},
    'user_visited_shops': {'max_len': 20, 'embedding_dim': 32}
}
```

#### **수치형 Features**
```sql
-- Deep 모델용 수치형 Feature
SELECT 
  user_id,
  shop_id,
  
  -- 사용자 수치 특성
  user_stats.total_orders,
  user_stats.avg_order_value,
  user_stats.days_since_last_order,
  user_stats.category_diversity,  -- 방문한 카테고리 다양성
  
  -- 가게 수치 특성  
  shop_stats.avg_rating,
  shop_stats.total_customers,
  shop_stats.avg_order_value as shop_avg_order,
  
  -- 유사도 특성
  user_shop_similarity.cosine_similarity,
  category_preference_score.preference_score,
  
  -- 시간 기반 특성
  TIMESTAMPDIFF(DAY, user_stats.join_date, NOW()) as user_tenure,
  TIMESTAMPDIFF(DAY, shop_stats.open_date, NOW()) as shop_age

FROM interactions
JOIN user_stats ON interactions.user_id = user_stats.user_id
JOIN shop_stats ON interactions.shop_id = shop_stats.shop_id;
```

### **학습 데이터 구성**

#### **긍정적 상호작용 (Positive Interactions)**
```sql
-- 실제 이용 기록 = 긍정적 피드백
SELECT 
  user_id,
  shop_id,
  1 as label,  -- 긍정적 상호작용
  used_at as timestamp,
  point_amount as engagement_value
FROM ticket
WHERE used_at IS NOT NULL;

-- 즐겨찾기 = 강한 긍정적 피드백  
SELECT 
  userId as user_id,
  shopId as shop_id,
  2 as label,  -- 매우 긍정적 상호작용 (가중치 높음)
  createdAt as timestamp,
  NULL as engagement_value
FROM userfavorite;
```

#### **부정적 상호작용 생성 (Negative Sampling)**
```sql
-- 명시적 부정적 피드백이 없으므로 negative sampling
-- 방법 1: 같은 카테고리에서 선택하지 않은 가게들
-- 방법 2: 지역은 같지만 방문하지 않은 가게들  
-- 방법 3: 무작위 샘플링 (전체 가게에서)

WITH user_visited AS (
  SELECT DISTINCT user_id, shop_id FROM ticket
),
negative_candidates AS (
  SELECT u.id as user_id, s.id as shop_id
  FROM user u CROSS JOIN shop s
  WHERE NOT EXISTS (
    SELECT 1 FROM user_visited uv 
    WHERE uv.user_id = u.id AND uv.shop_id = s.id
  )
)
SELECT 
  user_id, 
  shop_id, 
  0 as label,  -- 부정적 상호작용
  NOW() as timestamp
FROM negative_candidates 
ORDER BY RAND() 
LIMIT (SELECT COUNT(*) FROM ticket);  -- positive와 1:1 비율
```

---

## 🔄 **모듈 간 데이터 플로우**

### **추론 시나리오**
```python
# 사용자 질문: "학교 끝나고 친구들이랑 먹을 치킨집 추천해줘"

# Step 1: 챗봇 NLU
extracted_info = {
    'intent': 'food_recommendation',
    'entities': {
        'food_category': '치킨',
        'context': '친구들과',
        'time': '방과후',
        'location': '학교 근처'
    },
    'user_id': 'user_123'
}

# Step 2: RAG 검색
rag_query = "치킨 친구들과 학교 근처"
retrieved_shops = rag_system.search(rag_query, top_k=20)

# Step 3: Wide&Deep 추천
user_features = get_user_features('user_123')
context_features = {
    'current_time_slot': 'after_school',
    'day_type': 'weekday',
    'group_size': 'friends'
}

recommendations = wide_deep_model.predict(
    user_features=user_features,
    candidate_shops=retrieved_shops,
    context_features=context_features
)

# Step 4: 최종 응답 생성
final_response = nlg_system.generate_response(
    recommendations=recommendations[:3],  # 상위 3개
    user_query=original_query,
    shop_details=shop_info
)
```

### **학습 데이터 플로우**
```python
# 배치 학습 프로세스
def daily_training_pipeline():
    # 1. 새로운 상호작용 데이터 수집
    new_interactions = get_new_interactions(yesterday)
    
    # 2. 챗봇 학습 데이터 업데이트
    new_conversations = extract_conversations(new_interactions)
    update_lora_training_data(new_conversations)
    
    # 3. RAG 문서 업데이트
    updated_shops = get_updated_shops(yesterday)
    update_rag_documents(updated_shops)
    rebuild_faiss_index()
    
    # 4. 추천 모델 재학습
    feature_table = rebuild_feature_table()
    retrain_wide_deep_model(feature_table)
    
    # 5. 성능 평가 및 모니터링
    evaluate_model_performance()
```

---

## 📊 **성능 모니터링 지표**

### **모듈별 KPI**
```python
model_kpis = {
    'chatbot': {
        'intent_accuracy': 0.95,      # 의도 파악 정확도
        'entity_precision': 0.90,     # 엔티티 추출 정확도
        'response_relevance': 0.88    # 응답 관련성
    },
    'rag': {
        'retrieval_precision@5': 0.85,  # 상위 5개 검색 정확도
        'semantic_similarity': 0.82,    # 의미적 유사도
        'coverage': 0.90               # 검색 커버리지
    },
    'recommendation': {
        'precision@5': 0.75,           # 상위 5개 추천 정확도
        'recall@10': 0.65,            # 상위 10개 재현율
        'ndcg@5': 0.70,               # 순위 품질
        'diversity': 0.60             # 추천 다양성
    }
}
```

### **A/B 테스트 설계**
```python
ab_test_scenarios = {
    'feature_importance': {
        'control': 'current_features',
        'variant': 'with_temporal_features',
        'metric': 'click_through_rate'
    },
    'cross_features': {
        'control': 'basic_cross_features',
        'variant': 'advanced_cross_features',  
        'metric': 'recommendation_accuracy'
    },
    'embedding_dimension': {
        'control': 'embedding_dim_64',
        'variant': 'embedding_dim_128',
        'metric': 'model_performance'
    }
}
```

---

## 🚀 **수정된 구현 우선순위** (SKT A.X 3.1 Lite 기준)

### **⚡ Phase 1: 핵심 시스템 (1-2주)**
- [ ] **🔥 Wide&Deep 추천엔진 데이터 학습** (최우선, 1-2주)
  - ✅ **코드 완성**: 모든 구현체 준비 완료!
  - [ ] sample_data.xlsx → 학습 데이터 변환
  - [ ] 기존 ModelTrainer로 모델 학습
  - [ ] 모델 검증 및 저장
- [ ] **RAG 문서 생성 및 FAISS 인덱싱** (1주)
  - [ ] sentence-transformers 벡터 인덱스 구축
  - [ ] 가게별 통합 문서 생성

### **Phase 2: 성능 향상 (2-3주, 선택적)**  
- [ ] **A.X 3.1 Lite LoRA 파인튜닝** (선택적)
  - [ ] 청소년 언어 패턴 학습 데이터 수집
  - [ ] 도메인 특화 파인튜닝
- [ ] 고급 Feature 최적화
- [ ] 하이퍼파라미터 튜닝

### **Phase 3: 프로덕션 (2주)**
- [ ] 실시간 추론 최적화
- [ ] A/B 테스트 프레임워크
- [ ] 자동 재학습 파이프라인
- [ ] 성능 대시보드

### **📊 실제 현황 (코드베이스 재확인 결과)**
```
✅ A.X 3.1 Lite: 이미 준비됨, 바로 사용 가능
✅ sentence-transformers: 사전 훈련된 모델 활용
✅ Wide&Deep: 코드 완전 구현 완료! (3,800+ 줄) <- 데이터 학습만!
✅ 전체 시스템: 92% 완성도 (conversation_summary 확인)

🎯 실제 필요 작업: 코드 구현(❌) → 데이터 학습(✅)
```

이 매핑 가이드를 통해 나비얌 AI 시스템의 각 모듈이 데이터를 효과적으로 활용하여 최고의 추천 성능을 달성할 수 있습니다.