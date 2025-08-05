# 나비얌 챗봇 데이터베이스 스키마 헷갈리는 부분 정리

## 🧠 Gemini 분석 기반 주요 혼동 요소 정리

---

## 1. 🔄 유사한 이름의 필드들 구분

### age_group vs target_age_group 차이점

#### **users.age_group** (일반 사용자 연령대)
```sql
-- 사용자의 실제 나이를 기반으로 한 분류
age_group VARCHAR(20)  -- '10대', '20대', '30대' 등

-- 계산 방법:
CASE 
    WHEN YEAR(CURDATE()) - YEAR(birthday) < 20 THEN '10대'
    WHEN YEAR(CURDATE()) - YEAR(birthday) < 30 THEN '20대'
    -- ...
END
```

#### **foodcard_users.target_age_group** (급식카드 대상 구분)
```sql
-- 급식카드 지원 대상 구분
target_age_group VARCHAR(20)  -- '초등학생', '중고등학생', '청년' 등

-- 사용 예시:
-- 초등학생: 간식류 위주 추천
-- 중고등학생: 한 끼 식사 추천
-- 청년: 가성비 좋은 식사 추천
```

**💡 사용 구분:**
```python
# 일반 추천 시
if user.age_group == '10대':
    # 10대가 좋아하는 메뉴 추천
    
# 급식카드 추천 시
if foodcard_user.target_age_group == '초등학생':
    # 5,000원 이하 간식 위주 추천
```

### category 필드들의 구분

#### **shops.category** (가게 업종)
```sql
-- 13개 표준 카테고리
category VARCHAR(100)  -- '한식', '중식', '일식', '양식', '분식', '치킨', '피자', 
                      -- '패스트푸드', '아시안', '카페/디저트', '베이커리', '편의점', '마트'
```

#### **menus.category** (메뉴 구분)
```sql
-- 메뉴 타입 분류
category VARCHAR(100)  -- '메인메뉴', '세트메뉴', '사이드메뉴', '음료', '디저트' 등
```

**💡 계층 구조:**
```
가게(한식) → 메뉴들
  ├─ 김치찌개 (메인메뉴)
  ├─ 김치찌개정식 (세트메뉴)
  └─ 공기밥 (사이드메뉴)
```

---

## 2. 📋 JSON 필드 구조 명확화

### extracted_entities (대화에서 추출된 정보)
```json
{
    "food_type": "치킨",          // 음식 종류 (선택)
    "budget": 10000,              // 예산 (선택, 정수)
    "location": "강남역",          // 위치 (선택)
    "companions": "친구",          // 동반자 (선택)
    "taste_preference": "매운",     // 맛 선호 (선택)
    "urgency": "high",            // 긴급도 (선택: high/normal/low)
    "time_preference": "저녁"       // 시간 선호 (선택)
}
```

**⚠️ 주의사항:**
- 모든 필드는 선택사항 (null 가능)
- food_type은 shops.category와 일치하지 않아도 됨 (의미적 매칭)
- budget은 항상 정수값

### recommendations (추천 결과)
```json
[{
    "shop_id": 15,                        // shops.id 참조 (필수)
    "shop_name": "김밥천국",               // 가게명 (필수)
    "score": 0.92,                        // 추천 점수 0.0~1.0 (필수)
    "ranking": 1,                         // 추천 순위 (필수)
    "reason": "예산적합+가까움+인기메뉴",     // 추천 이유 (필수)
    "reason_detail": {                    // 상세 이유 (선택)
        "budget_fit": true,
        "distance_score": 0.9,
        "popularity_score": 0.85
    },
    "distance_km": 0.3,                   // 거리 (선택)
    "menu_recommendations": [              // 추천 메뉴 (선택)
        {"menu_id": 201, "menu_name": "참치김밥", "price": 3500}
    ],
    "applicable_coupons": ["FOOD10", "TEEN20"],  // 쿠폰 ID 리스트 (선택)
    "final_price_with_coupon": 3000       // 쿠폰 적용 최종가 (선택)
}]
```

### user_selection (사용자 선택 기록)
```json
{
    "shop_id": 15,                  // 선택한 가게 ID (필수)
    "menu_ids": [201, 202],         // 선택한 메뉴 ID들 (필수)
    "coupon_id": "FOOD10",          // 사용한 쿠폰 ID (선택)
    "final_price": 8000,            // 최종 결제 금액 (필수)
    "selected_from_position": 2,     // 추천 목록에서 몇 번째 선택 (필수)
    "time_to_selection_ms": 3500    // 선택까지 걸린 시간 (선택)
}
```

---

## 3. 🔗 테이블 간 관계 명확화

### 사용자 식별자 혼동 해결

```sql
-- users 테이블
id INT PRIMARY KEY  -- 숫자형 사용자 ID (예: 1, 2, 3)

-- conversations 테이블  
user_id VARCHAR(100)  -- 문자형 사용자 ID (예: "user_123", "kakao_456", "1")

-- foodcard_users 테이블
user_id INT  -- users.id 참조
```

**💡 이유:**
- conversations는 다양한 플랫폼 ID 수용 (카카오톡, 웹, 앱 등)
- 실제 서비스에서는 플랫폼 ID → users.id 매핑 테이블 필요

```python
# 사용 예시
def get_numeric_user_id(platform_user_id: str) -> Optional[int]:
    if platform_user_id.isdigit():
        return int(platform_user_id)
    
    # 플랫폼 ID 매핑 조회
    mapping = db.query("SELECT user_id FROM user_mappings WHERE platform_id = ?", platform_user_id)
    return mapping.user_id if mapping else None
```

### 쿠폰 적용 로직 우선순위

```sql
-- coupons 테이블의 3가지 적용 범위
usage_type VARCHAR(30)      -- 'ALL', 'SHOP', 'CATEGORY'
target_categories JSON      -- ["한식", "분식"]
applicable_shops JSON       -- [1, 2, 3]
```

**💡 적용 우선순위:**
1. **usage_type = 'SHOP'**: applicable_shops에 있는 가게만
2. **usage_type = 'CATEGORY'**: target_categories에 있는 카테고리 가게만
3. **usage_type = 'ALL'**: 모든 가게 (단, min_amount 조건은 확인)

```python
def is_coupon_applicable(coupon, shop, order_amount):
    # 1. 최소 주문 금액 확인
    if order_amount < coupon.min_amount:
        return False
    
    # 2. usage_type에 따른 확인
    if coupon.usage_type == 'SHOP':
        return shop.id in coupon.applicable_shops
    elif coupon.usage_type == 'CATEGORY':
        return shop.category in coupon.target_categories
    elif coupon.usage_type == 'ALL':
        return True
    
    return False
```

---

## 4. 🔄 파생 필드 vs 원본 필드

### current_status (현재 영업 상태)
```python
# 계산 방법
def calculate_current_status(shop, current_time):
    if not shop.open_hour or not shop.close_hour:
        return 'UNKNOWN'
    
    # 현재 시간이 영업시간 내인지 확인
    if shop.open_hour <= current_time <= shop.close_hour:
        # 브레이크 타임 확인
        if shop.break_start_hour and shop.break_end_hour:
            if shop.break_start_hour <= current_time <= shop.break_end_hour:
                return 'BREAK_TIME'
        return 'OPEN'
    
    return 'CLOSED'
```

### priority_score (쿠폰 우선순위 점수)
```python
# 계산 요소
def calculate_coupon_priority(coupon, user):
    score = 0.5  # 기본 점수
    
    # 만료일 임박 (+0.3)
    days_left = (coupon.valid_until - date.today()).days
    if days_left <= 3:
        score += 0.3
    elif days_left <= 7:
        score += 0.2
    
    # 할인액 크기 (+0.2)
    if coupon.amount > 3000 or coupon.discount_rate > 0.2:
        score += 0.2
    
    # 급식카드 전용 쿠폰 (+0.1)
    if user.is_foodcard_user and coupon.usage_type == 'FOODCARD':
        score += 0.1
    
    return min(score, 1.0)  # 최대 1.0
```

---

## 5. 📊 상태(Status) 필드 전체 목록

### foodcard_users.status
```python
STATUS_VALUES = {
    'ACTIVE': '정상 사용 가능',
    'INACTIVE': '일시 정지',
    'SUSPENDED': '이용 정지 (규정 위반)',
    'EXPIRED': '기간 만료',
    'PENDING': '승인 대기중'
}
```

### user_coupon_wallet.status
```python
COUPON_STATUS = {
    'ACTIVE': '사용 가능',
    'USED': '사용 완료',
    'EXPIRED': '기간 만료',
    'CANCELLED': '취소됨',
    'PENDING': '발급 대기중'
}

# 상태 전이 규칙
TRANSITIONS = {
    'ACTIVE': ['USED', 'EXPIRED', 'CANCELLED'],
    'PENDING': ['ACTIVE', 'CANCELLED'],
    'USED': [],  # 최종 상태
    'EXPIRED': [],  # 최종 상태
    'CANCELLED': []  # 최종 상태
}
```

### user_strategy (사용자 대화 전략)
```python
USER_STRATEGIES = {
    'onboarding_mode': '신규 사용자 온보딩 (1-3회 대화)',
    'data_building_mode': '선호도 파악 중 (4-10회 대화)',
    'normal_mode': '일반 추천 모드 (10회 이상)',
    'urgent_mode': '긴급 모드 (잔액 부족, 시간 촉박)',
    'vip_mode': '단골 사용자 모드 (50회 이상)',
    'dormant_mode': '휴면 사용자 재활성화'
}
```

---

## 6. ⏰ 시간 관련 필드 형식

### 영업시간 형식
```sql
open_hour VARCHAR(10)    -- "09:00" (24시간 형식)
close_hour VARCHAR(10)   -- "22:00"
break_start_hour VARCHAR(10)  -- "15:00"
break_end_hour VARCHAR(10)    -- "17:00"
```

**특수 케이스:**
```python
# 24시간 영업
open_hour = "00:00"
close_hour = "23:59"

# 새벽 영업 (자정 넘김)
open_hour = "18:00"
close_hour = "02:00"  # 다음날 새벽 2시
# → 별도 처리 로직 필요

# 브레이크타임 없음
break_start_hour = NULL
break_end_hour = NULL
```

### 쿠폰 유효기간
```sql
valid_from DATE   -- '2025-08-01' (날짜만)
valid_until DATE  -- '2025-08-31'
```

**시간 포함이 필요한 경우:**
```python
# 자정 기준 처리
def is_coupon_valid(coupon, current_datetime):
    # valid_from은 00:00:00부터
    # valid_until은 23:59:59까지
    valid_from = datetime.combine(coupon.valid_from, time.min)
    valid_until = datetime.combine(coupon.valid_until, time.max)
    
    return valid_from <= current_datetime <= valid_until
```

---

## 7. 📈 점수/신뢰도 필드 범위

### 신뢰도 점수들
```python
# intent_confidence (의도 분류 신뢰도)
CONFIDENCE_RANGES = {
    'HIGH': (0.8, 1.0),      # 확실함
    'MEDIUM': (0.5, 0.8),    # 보통
    'LOW': (0.0, 0.5)        # 불확실 (확인 필요)
}

# 사용 예시
if intent_confidence < 0.5:
    response = "혹시 {} 찾으시는 건가요?".format(predicted_intent)
```

### 추천 점수
```python
# recommendation score (0.0 ~ 1.0)
SCORE_COMPONENTS = {
    'location_score': 0.3,      # 거리 가중치
    'preference_score': 0.3,    # 선호도 가중치  
    'price_score': 0.2,         # 가격 적합도
    'popularity_score': 0.2     # 인기도
}

# good_influence_preference (0.0 ~ 1.0)
if user.good_influence_preference >= 0.7:
    # 착한가게 가중치 2배 적용
    score *= 2 if shop.is_good_influence_shop else 1
```

---

## 8. 🤔 기타 헷갈리는 개념들

### is_food_card_shop 값
```python
# VARCHAR(10)이지만 실제로는 Y/N만 사용
IS_FOOD_CARD_VALUES = {
    'Y': '급식카드 사용 가능',
    'N': '급식카드 사용 불가',
    'P': '부분 가능 (일부 메뉴만)',  # 향후 확장용
    'U': '확인 필요'                # 미확인 상태
}
```

### interaction_type 전체 목록
```python
INTERACTION_TYPES = {
    # 입력 관련
    'text_input': '텍스트 대화 입력',
    'voice_input': '음성 입력',
    
    # 선택 관련
    'selection': '추천 목록에서 선택',
    'detail_view': '상세 정보 조회',
    'comparison': '가게/메뉴 비교',
    
    # 피드백 관련
    'positive_feedback': '긍정 피드백',
    'negative_feedback': '부정 피드백',
    'rating': '별점 평가',
    
    # 쿠폰 관련
    'coupon_view': '쿠폰 조회',
    'coupon_use': '쿠폰 사용',
    'coupon_save': '쿠폰 저장',
    
    # 기타
    'share': '공유하기',
    'bookmark': '즐겨찾기 추가',
    'report': '문제 신고'
}
```

### 할인 계산 우선순위
```python
def calculate_final_price(original_price, coupon):
    # 정액 할인과 정률 할인이 모두 있는 경우
    if coupon.amount > 0 and coupon.discount_rate > 0:
        # 더 큰 할인 적용
        fixed_discount = coupon.amount
        rate_discount = original_price * coupon.discount_rate
        return original_price - max(fixed_discount, rate_discount)
    
    # 정액 할인만
    elif coupon.amount > 0:
        return original_price - coupon.amount
    
    # 정률 할인만
    elif coupon.discount_rate > 0:
        return original_price * (1 - coupon.discount_rate)
    
    return original_price
```

---

## 💡 실무 활용 팁

### 1. 복잡한 쿼리 예시
```sql
-- 급식카드 사용자의 쿠폰 포함 추천 가능 메뉴 찾기
SELECT 
    s.shop_name,
    m.menu_name,
    m.price,
    c.coupon_name,
    CASE 
        WHEN c.amount > 0 THEN m.price - c.amount
        ELSE m.price * (1 - c.discount_rate)
    END as final_price
FROM shops s
JOIN menus m ON s.id = m.shop_id
LEFT JOIN coupons c ON (
    c.usage_type = 'ALL' 
    OR (c.usage_type = 'SHOP' AND s.id IN (SELECT value FROM JSON_TABLE(c.applicable_shops, '$[*]' COLUMNS(value INT PATH '$'))))
    OR (c.usage_type = 'CATEGORY' AND s.category IN (SELECT value FROM JSON_TABLE(c.target_categories, '$[*]' COLUMNS(value VARCHAR(100) PATH '$'))))
)
WHERE s.is_food_card_shop = 'Y'
    AND s.current_status = 'OPEN'
    AND m.price <= 10000  -- 예산 제약
    AND (c.id IS NULL OR m.price >= c.min_amount)  -- 쿠폰 최소 금액
ORDER BY final_price ASC;
```

### 2. 데이터 일관성 체크
```python
# 정기적으로 실행할 데이터 검증
def validate_data_consistency():
    issues = []
    
    # 1. 쿠폰의 가게가 실제 존재하는지
    for coupon in coupons:
        if coupon.usage_type == 'SHOP':
            for shop_id in coupon.applicable_shops:
                if shop_id not in shops:
                    issues.append(f"Coupon {coupon.id} references non-existent shop {shop_id}")
    
    # 2. foodcard_user의 user_id가 users에 존재하는지
    for fc_user in foodcard_users:
        if fc_user.user_id not in users:
            issues.append(f"Foodcard user {fc_user.id} references non-existent user {fc_user.user_id}")
    
    return issues
```

이러한 명확한 정의와 예시를 통해 개발자들이 스키마를 정확히 이해하고 구현할 수 있습니다.