# AI 데이터 요구사항 - 데이터 담당자용 가이드

*작성일: 2025.07.31*  
*작성자: AI 담당자 (Gemini-Claude 협력 분석)*  
*대상: 데이터 엔지니어링 팀*

---

## 📋 **요약**

나비얌 챗봇의 3가지 AI 모듈 (SKT A.X 3.1 Lite, RAG, Wide&Deep 추천엔진) 학습 및 추론을 위해 sample_data.xlsx 기반 데이터 전처리가 필요합니다.

**🎯 대상 사용자**: 아동~청소년 (초/중/고등학생 + 취약계층)  
**🏪 핵심 데이터**: 31개 테이블 중 user, shop, shop_menu, ticket, review 중심

---

## 🤖 **AI 모듈별 데이터 요구사항**

### **1️⃣ SKT A.X 3.1 Lite (LoRA 파인튜닝)**

**목적**: 청소년 대상 자연어 대화 이해/생성 능력 향상
**현재 상태**: ✅ 기본 모델 설치 완료, 선택적 도메인 특화 파인튜닝

**필요 데이터 구조**:
```json
{
  "instruction": "청소년 대상 음식 추천 챗봇으로 답변해주세요",
  "input": "급식카드 되는 치킨집 있어?",
  "output": "네! 급식카드 사용 가능한 치킨집을 찾아드릴게요. 학교 근처나 선호 맛이 있나요?"
}
```

**활용 테이블**:
- `user`: 연령대별 표현 방식 학습
- `shop`: 도메인 지식 (착한가게, 카테고리)
- `review`: 실제 사용자 표현 및 은어 학습

**전처리 요청**:
- 청소년 표현 패턴 분석 (급식카드, JMT, 존맛탱 등)
- instruction-input-output 형태 대화 데이터셋 구성

---

### **2️⃣ RAG 벡터 검색**

**목적**: 사용자 질문과 관련 가게 정보 의미적 매칭
**현재 상태**: ✅ sentence-transformers 사전 훈련된 모델 사용 가능

**필요 데이터**: 가게별 통합 텍스트 문서

**문서 생성 SQL**:
```sql
SELECT shop.id,
       CONCAT('[가게: ', shop.shopName, '] ',
              '[카테고리: ', shop.category, '] ',
              '[주소: ', shop.addressName, '] ',
              '[착한가게: ', IF(shop.isGoodInfluenceShop, 'O', 'X'), '] ',
              '[메뉴: ', GROUP_CONCAT(menu.name, ' ', menu.price, '원'), '] ',
              '[리뷰: ', GROUP_CONCAT(review.comment LIMIT 3), ']'
       ) as rag_document
FROM shop 
LEFT JOIN shop_menu menu ON shop.id = menu.shop_id
LEFT JOIN review ON shop.id = review.store_id
GROUP BY shop.id;
```

**출력 예시**:
```
[가게: 엄마손치킨] [카테고리: 치킨] [주소: 서울시 강남구] [착한가게: O] 
[메뉴: 후라이드치킨 15000원, 양념치킨 16000원] 
[리뷰: 바삭하고 맛있어요, 급식카드도 돼서 좋아요, 양이 많아서 친구들과 나눠먹기 좋아요]
```

---

### **3️⃣ Wide&Deep 추천엔진** 🔥 **최우선**

**목적**: 개인화된 가게 추천
**현재 상태**: ✅ **코드 완전 구현 완료!** 데이터로 학습만 하면 됨
  - `ranking_model.py` (453줄) - Wide&Deep 신경망 완성
  - `model_trainer.py` (502줄) - 학습 시스템 완성
  - `recommendation_engine.py` (914줄) - 전체 엔진 완성
  - `feature_engineering.py` (464줄) - Feature 처리 완성

#### **Wide Component (명시적 특성)**
```sql
-- User Features
SELECT user_id,
       CASE 
         WHEN TIMESTAMPDIFF(YEAR, birthday, CURDATE()) BETWEEN 7 AND 12 THEN '초등'
         WHEN TIMESTAMPDIFF(YEAR, birthday, CURDATE()) BETWEEN 13 AND 15 THEN '중등'
         WHEN TIMESTAMPDIFF(YEAR, birthday, CURDATE()) BETWEEN 16 AND 18 THEN '고등'
       END as age_group,
       gender,
       SUBSTRING(currentAddress, 1, 6) as region
FROM user;

-- Item Features  
SELECT shop_id,
       category,
       CASE 
         WHEN avg_price < 5000 THEN '저가'
         WHEN avg_price < 10000 THEN '중가'
         ELSE '고가'
       END as price_range,
       isGoodInfluenceShop
FROM shop 
LEFT JOIN (
  SELECT shop_id, AVG(price) as avg_price 
  FROM shop_menu 
  GROUP BY shop_id
) menu_avg ON shop.id = menu_avg.shop_id;

-- Cross Features (교차 특성)
-- age_group × category, time_slot × category 조합
```

#### **Deep Component (임베딩 특성)**
```sql
-- 사용자별 통계
SELECT user_id, 
       AVG(point_amount) as avg_order_price,
       COUNT(*) as visit_frequency,
       (SELECT category FROM shop WHERE id = 
         (SELECT shop_id FROM ticket t2 WHERE t2.user_id = t1.user_id 
          GROUP BY shop_id ORDER BY COUNT(*) DESC LIMIT 1)
       ) as favorite_category
FROM ticket t1
GROUP BY user_id;

-- 가게별 통계  
SELECT shop_id,
       COUNT(ticket.id) as popularity_score,
       AVG(CASE WHEN review.rating IS NOT NULL THEN review.rating ELSE 3.5 END) as avg_rating,
       COUNT(review.id) as review_count
FROM shop 
LEFT JOIN ticket ON shop.id = ticket.shop_id
LEFT JOIN review ON shop.id = review.store_id
GROUP BY shop_id;
```

---

## 🔧 **즉시 필요한 전처리 작업** 

### **⚡ 수정된 우선순위** (SKT A.X 3.1 Lite 사용 기준)

### **우선순위 1: Wide&Deep 추천엔진 데이터 학습 (최우선, 1-2주)**
- ✅ **코드 이미 완성**: 모든 구현체 준비 완료
- 🔥 **필요 작업**: sample_data.xlsx → 학습 데이터 변환
- 📊 **목표**: 1000개 이상 user-shop 상호작용 데이터로 모델 학습

### **우선순위 2: RAG 문서 생성 (1주)**  
- 가게별 통합 텍스트 문서 생성
- FAISS 벡터 인덱스 구축

### **우선순위 3: A.X 파인튜닝 데이터 (선택적, 2주)**
- 청소년 대화 데이터셋 구축
- LoRA 학습용 instruction 데이터

### **우선순위 4: 기본 변환 (1주)**

```sql
-- 1. 연령 그룹화
ALTER TABLE user ADD COLUMN age_group VARCHAR(10);
UPDATE user SET age_group = 
  CASE 
    WHEN TIMESTAMPDIFF(YEAR, birthday, CURDATE()) BETWEEN 7 AND 12 THEN '초등'
    WHEN TIMESTAMPDIFF(YEAR, birthday, CURDATE()) BETWEEN 13 AND 15 THEN '중등'  
    WHEN TIMESTAMPDIFF(YEAR, birthday, CURDATE()) BETWEEN 16 AND 18 THEN '고등'
  END;

-- 2. 가격대 구간화
ALTER TABLE shop ADD COLUMN price_range VARCHAR(10);
UPDATE shop SET price_range = (
  SELECT CASE 
    WHEN AVG(price) < 5000 THEN '저가'
    WHEN AVG(price) < 10000 THEN '중가'
    ELSE '고가'
  END
  FROM shop_menu WHERE shop_id = shop.id
);

-- 3. 시간 특성 추출
ALTER TABLE ticket ADD COLUMN time_slot VARCHAR(10);
ALTER TABLE ticket ADD COLUMN day_type VARCHAR(10);
UPDATE ticket SET 
  time_slot = CASE 
    WHEN HOUR(used_at) BETWEEN 6 AND 10 THEN '아침'
    WHEN HOUR(used_at) BETWEEN 11 AND 14 THEN '점심'
    WHEN HOUR(used_at) BETWEEN 17 AND 20 THEN '저녁'
    ELSE '기타'
  END,
  day_type = CASE 
    WHEN WEEKDAY(used_at) BETWEEN 0 AND 4 THEN '평일'
    ELSE '주말'
  END;
```

### **우선순위 2: 집계 변수 생성 (2주일)**

```sql
-- 사용자 통계 테이블 생성
CREATE TABLE user_stats AS
SELECT user_id,
       AVG(point_amount) as avg_order_price,
       COUNT(*) as visit_frequency,
       COUNT(DISTINCT shop_id) as shop_diversity,
       MAX(used_at) as last_visit_date
FROM ticket
WHERE used_at IS NOT NULL
GROUP BY user_id;

-- 가게 통계 테이블 생성  
CREATE TABLE shop_stats AS
SELECT shop.id as shop_id,
       shop.shopName,
       COUNT(ticket.id) as popularity_score,
       AVG(COALESCE(review.rating, 3.5)) as avg_rating,
       COUNT(review.id) as review_count,
       COUNT(DISTINCT ticket.user_id) as unique_customers
FROM shop
LEFT JOIN ticket ON shop.id = ticket.shop_id
LEFT JOIN review ON shop.id = review.store_id
GROUP BY shop.id;
```

### **우선순위 3: RAG 문서 생성 (1주일)**

```sql
-- RAG용 통합 문서 테이블 생성
CREATE TABLE rag_documents AS
SELECT 
  shop.id as shop_id,
  CONCAT(
    '[가게: ', shop.shopName, '] ',
    '[카테고리: ', shop.category, '] ',
    '[주소: ', shop.addressName, '] ',
    '[착한가게: ', IF(shop.isGoodInfluenceShop = 1, 'O', 'X'), '] ',
    '[영업시간: ', COALESCE(shop.openHour, '정보없음'), '-', COALESCE(shop.closeHour, '정보없음'), '] ',
    '[메뉴: ', COALESCE(menu_info.menu_list, '메뉴정보없음'), '] ',
    '[리뷰: ', COALESCE(review_info.review_summary, '리뷰없음'), ']'
  ) as document_text
FROM shop
LEFT JOIN (
  SELECT shop_id, 
         GROUP_CONCAT(CONCAT(name, ' ', price, '원') SEPARATOR ', ') as menu_list
  FROM shop_menu 
  GROUP BY shop_id
) menu_info ON shop.id = menu_info.shop_id
LEFT JOIN (
  SELECT store_id,
         GROUP_CONCAT(comment SEPARATOR ' / ') as review_summary
  FROM (
    SELECT store_id, comment, 
           ROW_NUMBER() OVER (PARTITION BY store_id ORDER BY createdAt DESC) as rn
    FROM review 
    WHERE comment IS NOT NULL
  ) ranked_reviews
  WHERE rn <= 3
  GROUP BY store_id
) review_info ON shop.id = review_info.store_id;
```

---

## 📊 **데이터 품질 체크리스트**

### **필수 검증 항목**
- [ ] user 테이블 age_group NULL 값 확인
- [ ] shop 테이블 좌표 정보 완성도 확인  
- [ ] ticket 테이블 used_at 시간 형식 통일
- [ ] review 테이블 comment 텍스트 품질 확인
- [ ] 외래키 관계 무결성 검증

### **데이터 분포 확인**
```sql
-- 연령대별 분포
SELECT age_group, COUNT(*) FROM user GROUP BY age_group;

-- 카테고리별 가게 수
SELECT category, COUNT(*) FROM shop GROUP BY category;

-- 시간대별 이용 패턴
SELECT time_slot, COUNT(*) FROM ticket GROUP BY time_slot;

-- 가격대별 분포
SELECT price_range, COUNT(*) FROM shop GROUP BY price_range;
```

---

## 🚨 **주의사항**

1. **개인정보 보호**: 사용자 실명, 전화번호 등 개인정보는 해시화 또는 마스킹 처리
2. **데이터 일관성**: 외래키 관계 유지, NULL 값 처리 방안 사전 협의  
3. **성능 최적화**: 집계 테이블에 인덱스 추가, 배치 처리 고려
4. **청소년 특성**: 은어, 줄임말, 급식카드 관련 표현 보존

---

## 📞 **문의 및 협업**

**AI 담당자**: 전처리 결과 검토 및 피드백
**데이터 담당자**: 기술적 구현 및 스케줄 조율

**다음 단계**: 전처리 완료 후 AI 모델 학습 데이터 검증 및 성능 테스트

---

**🎯 목표**: 이 요구사항에 따라 전처리된 데이터로 나비얌 AI 챗봇의 학습 성능을 최적화하여 아동~청소년에게 최고의 음식 추천 서비스를 제공합니다.