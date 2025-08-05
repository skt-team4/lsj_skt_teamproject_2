# Feature Engineering 가이드

*작성일: 2025.07.31*  
*Gemini-Claude 협력 분석 결과*  
*대상: 데이터 엔지니어링 팀*

---

## 🎯 **개요**

나비얌 챗봇 AI 시스템의 3가지 모듈 (챗봇, RAG, Wide&Deep 추천엔진)을 위한 Feature Engineering 상세 가이드입니다.

**기본 원칙**: 
- 아동~청소년 타겟 특성 반영
- 급식카드 사용 패턴 고려
- 학교/학원가 중심 지역 특성 활용

---

## 📊 **Feature 분류 및 매핑**

### **1. 사용자 Features (User Features)**

#### **기본 정보 변환**
```sql
-- A. 연령 그룹화 (핵심 Feature)
CASE 
  WHEN TIMESTAMPDIFF(YEAR, birthday, CURDATE()) BETWEEN 7 AND 12 THEN '초등'
  WHEN TIMESTAMPDIFF(YEAR, birthday, CURDATE()) BETWEEN 13 AND 15 THEN '중등'
  WHEN TIMESTAMPDIFF(YEAR, birthday, CURDATE()) BETWEEN 16 AND 18 THEN '고등'
  ELSE '기타'
END as age_group

-- B. 지역 정보 추출
SUBSTRING(currentAddress, 1, 6) as region,  -- 시군구 단위
CASE 
  WHEN currentAddress LIKE '%강남%' OR currentAddress LIKE '%서초%' THEN '강남권'
  WHEN currentAddress LIKE '%마포%' OR currentAddress LIKE '%서대문%' THEN '홍대권'
  ELSE '기타권'
END as area_cluster

-- C. 가입 기간 및 활성도
DATEDIFF(CURDATE(), created_at) as days_since_join,
CASE 
  WHEN DATEDIFF(CURDATE(), last_login) <= 7 THEN '활성'
  WHEN DATEDIFF(CURDATE(), last_login) <= 30 THEN '보통'
  ELSE '비활성'
END as activity_level
```

#### **행동 기반 파생 변수**
```sql
-- 사용자별 통계 Feature 생성
CREATE VIEW user_behavior_features AS
SELECT 
  user_id,
  -- 주문 패턴
  COUNT(*) as total_orders,
  AVG(point_amount) as avg_order_value,
  STDDEV(point_amount) as order_value_std,
  
  -- 시간 패턴  
  COUNT(CASE WHEN HOUR(used_at) BETWEEN 11 AND 14 THEN 1 END) / COUNT(*) as lunch_ratio,
  COUNT(CASE WHEN WEEKDAY(used_at) BETWEEN 0 AND 4 THEN 1 END) / COUNT(*) as weekday_ratio,
  
  -- 다양성 지표
  COUNT(DISTINCT shop_id) as shop_diversity,
  COUNT(DISTINCT category) as category_diversity,
  
  -- 최신성
  DATEDIFF(CURDATE(), MAX(used_at)) as days_since_last_order,
  
  -- 선호도
  (SELECT category FROM shop s 
   JOIN ticket t2 ON s.id = t2.shop_id 
   WHERE t2.user_id = t1.user_id 
   GROUP BY category ORDER BY COUNT(*) DESC LIMIT 1) as preferred_category
   
FROM ticket t1
JOIN shop ON t1.shop_id = shop.id
GROUP BY user_id;
```

---

### **2. 가게 Features (Item Features)**

#### **기본 정보 변환**
```sql
-- A. 카테고리 표준화
CASE 
  WHEN category IN ('치킨', '닭갈비') THEN '치킨류'
  WHEN category IN ('분식', '떡볶이', '김밥') THEN '분식류'
  WHEN category IN ('한식', '백반', '국밥') THEN '한식류'
  WHEN category IN ('중식', '짜장면', '짬뽕') THEN '중식류'
  WHEN category IN ('일식', '돈까스', '라멘') THEN '일식류'
  WHEN category IN ('양식', '피자', '햄버거') THEN '양식류'
  ELSE '기타'
END as category_grouped

-- B. 가격대 구간화
CASE 
  WHEN avg_menu_price < 5000 THEN '저가'
  WHEN avg_menu_price < 8000 THEN '중저가'  
  WHEN avg_menu_price < 12000 THEN '중가'
  WHEN avg_menu_price < 20000 THEN '중고가'
  ELSE '고가'
END as price_tier

-- C. 위치 특성
CASE 
  WHEN addressName LIKE '%학교%' OR addressName LIKE '%대학%' THEN '학교근처'
  WHEN addressName LIKE '%역%' THEN '역세권'
  WHEN addressName LIKE '%단지%' OR addressName LIKE '%아파트%' THEN '주거지역'
  ELSE '상업지역'
END as location_type

-- D. 운영 특성
CASE 
  WHEN isAroundTheClock = 1 THEN '24시간'
  WHEN HOUR(STR_TO_DATE(closeHour, '%H:%i')) >= 22 THEN '늦은영업'
  ELSE '일반영업'
END as operating_type
```

#### **성과 지표 Features**
```sql
-- 가게별 성과 Feature 생성  
CREATE VIEW shop_performance_features AS
SELECT 
  shop_id,
  -- 인기도 지표
  COUNT(DISTINCT user_id) as unique_customers,
  COUNT(*) as total_orders,
  COUNT(*) / NULLIF(DATEDIFF(CURDATE(), MIN(used_at)), 0) as daily_avg_orders,
  
  -- 평점 지표
  AVG(COALESCE(rating, 3.5)) as avg_rating,
  COUNT(review.id) as review_count,
  STDDEV(rating) as rating_std,
  
  -- 매출 지표  
  AVG(point_amount) as avg_order_value,
  SUM(point_amount) as total_revenue,
  
  -- 시간대별 집중도
  COUNT(CASE WHEN HOUR(used_at) BETWEEN 11 AND 14 THEN 1 END) / COUNT(*) as lunch_concentration,
  COUNT(CASE WHEN HOUR(used_at) BETWEEN 17 AND 20 THEN 1 END) / COUNT(*) as dinner_concentration,
  
  -- 고객 충성도
  AVG(user_visit_count) as avg_visits_per_customer,
  COUNT(CASE WHEN user_visit_count >= 3 THEN 1 END) / COUNT(DISTINCT user_id) as loyalty_ratio
  
FROM shop
LEFT JOIN ticket ON shop.id = ticket.shop_id
LEFT JOIN review ON shop.id = review.store_id  
LEFT JOIN (
  SELECT user_id, shop_id, COUNT(*) as user_visit_count
  FROM ticket GROUP BY user_id, shop_id
) user_visits ON ticket.user_id = user_visits.user_id AND ticket.shop_id = user_visits.shop_id
GROUP BY shop_id;
```

---

### **3. 상황적 Features (Contextual Features)**

#### **시간 기반 Features**
```sql
-- 시간 관련 Feature 추출
SELECT 
  *,
  -- 기본 시간 분류
  CASE 
    WHEN HOUR(used_at) BETWEEN 7 AND 10 THEN '아침'
    WHEN HOUR(used_at) BETWEEN 11 AND 14 THEN '점심'  
    WHEN HOUR(used_at) BETWEEN 15 AND 17 THEN '간식'
    WHEN HOUR(used_at) BETWEEN 18 AND 21 THEN '저녁'
    ELSE '기타'
  END as time_slot,
  
  -- 요일 분류
  CASE 
    WHEN WEEKDAY(used_at) BETWEEN 0 AND 4 THEN '평일'
    WHEN WEEKDAY(used_at) = 5 THEN '금요일'
    ELSE '주말'
  END as day_type,
  
  -- 학기/방학 구분 (대략적)
  CASE 
    WHEN MONTH(used_at) IN (7, 8, 12, 1, 2) THEN '방학'
    ELSE '학기'
  END as school_period,
  
  -- 시험기간 추정 (중간고사: 4월, 10월 / 기말고사: 6월, 12월)
  CASE 
    WHEN MONTH(used_at) IN (4, 6, 10, 12) THEN '시험기간'
    ELSE '평상시'
  END as exam_period

FROM ticket;
```

#### **날씨/계절 Features (선택적)**
```sql
-- 계절별 Feature
CASE 
  WHEN MONTH(used_at) IN (3, 4, 5) THEN '봄'
  WHEN MONTH(used_at) IN (6, 7, 8) THEN '여름'
  WHEN MONTH(used_at) IN (9, 10, 11) THEN '가을'
  ELSE '겨울'
END as season,

-- 온도 구간 (외부 날씨 API 연동 시)
CASE 
  WHEN temperature < 5 THEN '한파'
  WHEN temperature < 15 THEN '추위'  
  WHEN temperature < 25 THEN '적정'
  WHEN temperature < 30 THEN '더위'
  ELSE '폭염'
END as temperature_level
```

---

### **4. 교차 Features (Cross Features) - Wide 모델용**

#### **핵심 교차 조합**
```sql
-- A. 사용자 × 아이템 교차
CONCAT(age_group, '_', category_grouped) as age_category_cross,
CONCAT(region, '_', location_type) as region_location_cross,
CONCAT(activity_level, '_', price_tier) as activity_price_cross,

-- B. 시간 × 아이템 교차  
CONCAT(time_slot, '_', category_grouped) as time_category_cross,
CONCAT(day_type, '_', operating_type) as day_operating_cross,
CONCAT(school_period, '_', location_type) as school_location_cross,

-- C. 사용자 × 시간 교차
CONCAT(age_group, '_', time_slot) as age_time_cross,
CONCAT(preferred_category, '_', day_type) as preference_day_cross,

-- D. 3-way 교차 (선택적)
CONCAT(age_group, '_', time_slot, '_', category_grouped) as age_time_category_cross
```

---

### **5. 임베딩 Features (Deep 모델용)**

#### **ID 기반 임베딩**
```sql
-- 카테고리형 ID들을 임베딩 벡터로 변환 대상
- user_id → user_embedding (64차원)
- shop_id → shop_embedding (64차원)  
- category → category_embedding (16차원)
- region → region_embedding (16차원)
- preferred_category → preference_embedding (16차원)
```

#### **텍스트 임베딩**
```python
# 텍스트 필드들을 sentence-transformers로 벡터화
text_embedding_fields = {
    'shop_name': 'shop.shopName',
    'menu_names': 'GROUP_CONCAT(shop_menu.name)',
    'review_text': 'GROUP_CONCAT(review.comment)',
    'address_text': 'shop.addressName'
}

# 각각을 384차원 벡터로 변환 (multilingual-E5-large 모델 사용)
```

---

## 🔧 **Feature Engineering 파이프라인**

### **단계별 처리 순서**

#### **1단계: 원본 데이터 검증 및 정제**
```sql
-- 결측치 처리
UPDATE user SET currentAddress = '주소미상' WHERE currentAddress IS NULL;
UPDATE shop SET category = '기타' WHERE category IS NULL OR category = '';
UPDATE ticket SET point_amount = 0 WHERE point_amount IS NULL;

-- 이상치 처리  
UPDATE ticket SET point_amount = (
  SELECT AVG(point_amount) FROM ticket t2 WHERE t2.shop_id = ticket.shop_id
) WHERE point_amount > 100000 OR point_amount < 0;

-- 데이터 타입 표준화
ALTER TABLE ticket MODIFY COLUMN used_at DATETIME;
ALTER TABLE user MODIFY COLUMN birthday DATE;
```

#### **2단계: 기본 Feature 생성**
```sql
-- 사용자 기본 Feature
ALTER TABLE user 
ADD COLUMN age_group VARCHAR(10),
ADD COLUMN region VARCHAR(20),
ADD COLUMN area_cluster VARCHAR(20);

-- 가게 기본 Feature  
ALTER TABLE shop
ADD COLUMN category_grouped VARCHAR(20),
ADD COLUMN price_tier VARCHAR(10),
ADD COLUMN location_type VARCHAR(20);

-- 거래 기본 Feature
ALTER TABLE ticket
ADD COLUMN time_slot VARCHAR(10),
ADD COLUMN day_type VARCHAR(10),
ADD COLUMN school_period VARCHAR(10);
```

#### **3단계: 집계 Feature 생성**
```sql
-- 사용자 행동 통계 테이블
CREATE TABLE user_features AS 
SELECT * FROM user_behavior_features;

-- 가게 성과 통계 테이블
CREATE TABLE shop_features AS
SELECT * FROM shop_performance_features;

-- 인덱스 추가
CREATE INDEX idx_user_features_user_id ON user_features(user_id);
CREATE INDEX idx_shop_features_shop_id ON shop_features(shop_id);
```

#### **4단계: 교차 Feature 생성**
```sql
-- Wide 모델용 교차 Feature 테이블
CREATE TABLE cross_features AS
SELECT 
  user_id,
  shop_id,
  CONCAT(u.age_group, '_', s.category_grouped) as age_category_cross,
  CONCAT(t.time_slot, '_', s.category_grouped) as time_category_cross,
  CONCAT(u.region, '_', s.location_type) as region_location_cross
FROM ticket t
JOIN user u ON t.user_id = u.id  
JOIN shop s ON t.shop_id = s.id;
```

#### **5단계: 최종 Feature 테이블 통합**
```sql
-- ML 모델 학습용 최종 Feature 테이블
CREATE TABLE ml_features AS
SELECT 
  t.user_id,
  t.shop_id,
  t.used_at,
  
  -- User Features
  u.age_group, u.gender, u.region,
  uf.total_orders, uf.avg_order_value, uf.preferred_category,
  
  -- Shop Features  
  s.category_grouped, s.price_tier, s.location_type,
  sf.avg_rating, sf.total_orders as shop_popularity,
  
  -- Contextual Features
  t.time_slot, t.day_type, t.school_period,
  
  -- Cross Features
  cf.age_category_cross, cf.time_category_cross,
  
  -- Target Variable (추천 모델 학습용)
  1 as interaction  -- 실제 이용했으므로 긍정적 피드백
  
FROM ticket t
JOIN user u ON t.user_id = u.id
JOIN shop s ON t.shop_id = s.id  
JOIN user_features uf ON t.user_id = uf.user_id
JOIN shop_features sf ON t.shop_id = sf.shop_id
JOIN cross_features cf ON t.user_id = cf.user_id AND t.shop_id = cf.shop_id
WHERE t.used_at IS NOT NULL;
```

---

## 📊 **Feature 검증 및 품질 관리**

### **Feature 분포 확인**
```sql
-- 범주형 Feature 분포
SELECT age_group, COUNT(*) as cnt, 
       COUNT(*) * 100.0 / (SELECT COUNT(*) FROM user) as pct
FROM user GROUP BY age_group ORDER BY cnt DESC;

-- 수치형 Feature 통계
SELECT 
  AVG(avg_order_value) as mean_order,
  STDDEV(avg_order_value) as std_order,
  MIN(avg_order_value) as min_order,
  MAX(avg_order_value) as max_order
FROM user_features;
```

### **Feature 중요도 분석 (예시)**
```python
# Python에서 Feature 중요도 확인
feature_importance = {
    'age_group': 0.15,           # 연령이 음식 선호에 큰 영향
    'time_slot': 0.12,           # 시간대별 음식 선택 패턴 뚜렷
    'category_grouped': 0.11,    # 음식 카테고리 자체의 인기도
    'location_type': 0.09,       # 학교 근처 vs 상업지역 차이
    'price_tier': 0.08,          # 가격대별 선호도
    'preferred_category': 0.07,  # 개인 선호도 
    'day_type': 0.06,           # 평일 vs 주말 패턴
    'avg_rating': 0.05          # 가게 평점의 영향
}
```

---

## ⚠️ **주의사항 및 Best Practices**

### **1. 데이터 품질 관리**
- 결측치 비율 20% 이상 Feature는 제외 고려
- 범주형 Feature의 카디널리티가 너무 높으면 그룹화
- 수치형 Feature의 이상치는 99%ile로 cap 처리

### **2. Feature 선택 기준**
- 비즈니스 의미가 명확한 Feature 우선
- 상관관계 0.9 이상 Feature들은 하나만 선택  
- Target과의 상관관계 0.05 미만은 제외 고려

### **3. 성능 최적화**
- 집계 테이블에는 적절한 인덱스 추가
- 배치 처리로 대용량 데이터 처리
- Feature 계산 결과를 캐시 테이블로 저장

### **4. 모니터링**
- Feature 분포가 시간에 따라 변하는지 모니터링
- 새로운 사용자/가게에 대한 Cold Start 문제 대응
- A/B 테스트를 통한 Feature 효과 검증

---

## 🚀 **다음 단계**

1. **Feature 생성 스크립트 개발** (1주)
2. **ML 파이프라인 통합** (1주)  
3. **성능 테스트 및 최적화** (1주)
4. **프로덕션 배포 및 모니터링** (1주)

이 가이드를 바탕으로 나비얌 AI 시스템의 핵심 Feature들을 체계적으로 구축하여 최고의 추천 성능을 달성할 수 있습니다.