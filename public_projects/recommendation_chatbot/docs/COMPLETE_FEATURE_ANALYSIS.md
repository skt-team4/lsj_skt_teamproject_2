# 나비얌 챗봇 완전한 Feature 분석 보고서

*작성일: 2025.08.02*  
*sample_data.xlsx 31개 시트 + 기존 문서 분석 결과*  

---

## 📊 **분석 개요**

### **데이터 소스**
- **sample_data.xlsx**: 31개 시트, 500+ 컬럼
- **기존 문서**: DATA_STATUS.md, DATA_ANALYSIS_DETAIL.md, CHATBOT_WORKFLOW_COMPLETE.md
- **현재 스키마**: COMPLETE_DATABASE_SCHEMA.md

### **분석 결과 요약**
- **총 Feature 카테고리**: 9개 주요 영역
- **실제 사용 테이블**: 31개 전체 시트 활용 가능
- **챗봇 활용도**: 기존 가게/메뉴 외 7개 추가 영역 발견

---

## 🏪 **1. 가게/브랜드 관련 Features (4개 테이블)**

### **shop (11개 데이터, 38개 컬럼)**
**챗봇 활용:**
- 🎯 **추천 기본 정보**: shopName, category, addressName
- 🍽️ **착한가게 필터링**: isGoodInfluenceShop (중요!)
- 💳 **급식카드 대응**: isFoodCardShop (핵심 Feature!)
- ⏰ **운영시간 체크**: openHour, closeHour, breakStartHour, breakEndHour
- 📞 **연락처 제공**: contact
- 🚨 **현재 운영상태**: open_status ("운영중", "휴업중", "폐업")

```python
# 챗봇 사용 예시
def filter_good_influence_shops(query_results):
    """착한가게만 필터링 (급식카드 사용자용)"""
    return [shop for shop in query_results 
            if shop['isGoodInfluenceShop'] == True 
            and shop['isFoodCardShop'] in ['Y', 'yes']]
```

### **shop_menu (11개 데이터, 15개 컬럼)**
**챗봇 활용:**
- 🍜 **메뉴 추천**: name, description, price
- 💰 **가격 범위 필터**: price (8,000원~25,000원 범위)
- 🔥 **인기메뉴 우선**: is_best (인기메뉴 우선 추천)
- ❌ **품절 제외**: is_sold_out (주문 불가 메뉴 제외)
- 🎁 **할인 정보**: discount_value

### **brand (8개 데이터, 15개 컬럼)**
**챗봇 활용:**
- 🏢 **브랜드 추천**: name, description
- 📱 **소셜 정보**: instagram_link, facebook_link
- 🎨 **브랜드 컬러**: primary_color (UI 개인화)
- ✅ **운영 상태**: is_active

### **shop_menu_category (11개 데이터, 6개 컬럼)**
**챗봇 활용:**
- 📂 **카테고리 분류**: name (메뉴 그룹핑)
- 📊 **우선순위**: priority (중요도 순 표시)

---

## 👤 **2. 사용자 관련 Features (3개 테이블)**

### **user (11개 데이터, 25개 컬럼)**
**챗봇 활용:**
- 👨‍🎓 **개인화 기본**: name, nickname, birthday
- 📧 **연락처**: email, phone
- 🎯 **사용자 역할**: role (학생, 일반 등)
- 📍 **현재 위치**: currentAddress (위치 기반 추천)
- 📱 **푸시 알림**: deviceToken, marketingOn
- 🚫 **계정 상태**: isBanned, useYN

```python
# 챗봇 사용 예시
def personalize_recommendations(user_id, recommendations):
    """사용자 정보 기반 개인화"""
    user = get_user_profile(user_id)
    
    # 나이 기반 메뉴 필터링
    age = calculate_age(user['birthday'])
    if age < 18:  # 청소년
        return filter_youth_friendly_menus(recommendations)
    
    return recommendations
```

### **user_location (11개 데이터, 4개 컬럼)**
**챗봇 활용:**
- 🏠 **지역 기반 추천**: state, city
- 📍 **근처 가게 찾기**: 사용자 지역과 가게 위치 매칭

### **userfavorite (11개 데이터, 5개 컬럼)**
**챗봇 활용:**
- ❤️ **찜한 가게**: shopId (개인화 추천 핵심)
- 🔄 **반복 방문**: 찜한 가게 우선 추천
- 📈 **취향 학습**: 찜 패턴 분석

---

## 🎫 **3. 거래/주문 관련 Features (4개 테이블)**

### **ticket (11개 데이터, 19개 컬럼)**
**챗봇 활용:**
- 🎟️ **이용권 현황**: ticket_number, expired_at
- 💰 **포인트 사용**: point_amount, bbugiddogi_point_amount
- 📊 **주문 이력**: paid_at, used_at (선호도 학습)
- 🏪 **방문 가게**: shop_id (재방문 추천)

### **product_order (11개 데이터, 27개 컬럼)**
**챗봇 활용:**
- 🛒 **주문 이력**: product_id, quantity, amount
- 🚚 **배송 상태**: delivery_status, order_status
- 💳 **결제 수단**: point_amount, giftcard_usage_amount
- 📦 **주문 패턴**: 주문 시간, 금액 분석

```python
# 챗봇 사용 예시
def recommend_based_on_order_history(user_id):
    """주문 이력 기반 추천"""
    orders = get_user_orders(user_id)
    
    # 자주 주문하는 가격대 분석
    avg_amount = sum(order['amount'] for order in orders) / len(orders)
    
    # 비슷한 가격대 메뉴 추천
    return find_similar_price_menus(avg_amount)
```

### **ticket_menu & ticket_menu_option**
**챗봇 활용:**
- 🍽️ **메뉴 선택 패턴**: menu_name, quantity
- 🧾 **옵션 선호도**: option preferences 학습

---

## 🎁 **4. 쿠폰/프로모션 Features (7개 테이블)**

### **coupon (10개 데이터, 30개 컬럼)**
**챗봇 활용:**
- 🎫 **쿠폰 정보**: name, description, amount
- 💰 **할인 조건**: min_amount_available, max_discount_value
- ⏰ **유효기간**: expiry_datetime, published_at
- 🎯 **대상 조건**: target, usage_type

### **coop_coupon (11개 데이터, 30개 컬럼)**
**챗봇 활용:**
- 🤝 **제휴 쿠폰**: 외부 업체 쿠폰 추천
- 🏢 **협력업체**: company_id, comp_name

### **쿠폰 매핑 테이블들**
- **coupon_shop_map**: 쿠폰 사용 가능 가게
- **coupon_menu_map**: 쿠폰 적용 메뉴
- **coupon_user_map**: 사용자 보유 쿠폰

```python
# 챗봇 사용 예시
def recommend_with_coupons(user_id, shop_recommendations):
    """쿠폰 적용 가능한 추천 우선"""
    user_coupons = get_user_coupons(user_id)
    
    enhanced_recommendations = []
    for shop in shop_recommendations:
        applicable_coupons = find_applicable_coupons(shop['id'], user_coupons)
        if applicable_coupons:
            shop['available_coupons'] = applicable_coupons
            shop['discount_available'] = True
            enhanced_recommendations.insert(0, shop)  # 쿠폰 있는 가게 우선
        else:
            enhanced_recommendations.append(shop)
    
    return enhanced_recommendations
```

---

## 💳 **5. 기프트카드 Features (3개 테이블)**

### **giftcard (11개 데이터, 19개 컬럼)**
**챗봇 활용:**
- 💎 **기프트카드 정보**: name, image_url, pub_amt
- 🎯 **사용 조건**: usage_list, targets, min_available_amt
- ⏰ **유효기간**: published_at, expired_at

### **giftcard_wallet (11개 데이터, 9개 컬럼)**
**챗봇 활용:**
- 💰 **잔액 확인**: balance
- 💳 **보유 카드**: 사용자가 보유한 기프트카드 목록

### **giftcard_wallet_transaction (11개 데이터, 9개 컬럼)**
**챗봇 활용:**
- 📊 **사용 이력**: type, usage_type, amount
- 💸 **결제 패턴**: 기프트카드 사용 패턴 분석

---

## ⭐ **6. 리뷰/평가 Features (1개 테이블)**

### **review (11개 데이터, 9개 컬럼)**
**챗봇 활용:**
- ⭐ **평점 정보**: rating (별점 기반 추천)
- 💬 **리뷰 내용**: comment (감정 분석)
- 📸 **리뷰 이미지**: img_static
- 🏪 **리뷰 대상**: store_id, subject_id

```python
# 챗봇 사용 예시
def recommend_by_ratings(shop_list):
    """평점 기반 가게 순위 조정"""
    for shop in shop_list:
        reviews = get_shop_reviews(shop['id'])
        if reviews:
            avg_rating = sum(r['rating'] for r in reviews) / len(reviews)
            shop['avg_rating'] = avg_rating
            shop['review_count'] = len(reviews)
    
    # 평점 높은 순으로 정렬
    return sorted(shop_list, key=lambda x: x.get('avg_rating', 0), reverse=True)
```

---

## 💳 **7. 급식카드 Features (1개 테이블)**

### **foodcard (11개 데이터, 21개 컬럼)**
**챗봇 활용 (핵심 Feature!):**
- 💳 **카드 정보**: card_number, owner_name
- 📍 **지역 정보**: region_do, region_si, region_dong
- ✅ **인증 상태**: status, verified_at
- 🏢 **카드 회사**: company

```python
# 챗봇 사용 예시 (매우 중요!)
def filter_for_meal_card_users(user_id, recommendations):
    """급식카드 사용자 전용 필터링"""
    user_foodcard = get_user_foodcard(user_id)
    
    if user_foodcard and user_foodcard['status'] == 'verified':
        # 착한가게만 필터링
        valid_shops = []
        for shop in recommendations:
            if (shop['isGoodInfluenceShop'] == True and 
                shop['isFoodCardShop'] in ['Y', 'yes']):
                shop['meal_card_available'] = True
                shop['card_company'] = user_foodcard['company']
                valid_shops.append(shop)
        
        return valid_shops
    
    return recommendations
```

---

## 💰 **8. 포인트/결제 Features (1개 테이블)**

### **point_transaction (11개 데이터, 12개 컬럼)**
**챗봇 활용:**
- 💰 **포인트 이력**: type, amount, balance
- 📊 **사용 패턴**: content, type_cat (적립/사용 패턴)
- ⏰ **포인트 만료**: expired_at

```python
# 챗봇 사용 예시
def suggest_point_usage(user_id, order_amount):
    """포인트 사용 제안"""
    point_balance = get_user_point_balance(user_id)
    
    if point_balance >= order_amount * 0.1:  # 10% 이상 포인트 보유
        return {
            'suggest_point_use': True,
            'available_points': point_balance,
            'suggested_amount': min(point_balance, order_amount * 0.5)
        }
    
    return {'suggest_point_use': False}
```

---

## 🏢 **9. 협력업체 Features (3개 테이블)**

### **coop_brand, coop_company, coop_category**
**챗봇 활용:**
- 🤝 **제휴 브랜드**: 제휴업체 상품 추천
- 🏪 **협력업체**: 제휴 쿠폰/이벤트 연동
- 📂 **제휴 카테고리**: 카테고리별 제휴 혜택

---

## 🎯 **챗봇 Feature 활용 시나리오**

### **시나리오 1: "급식카드로 치킨 먹고 싶어"**
```python
def process_meal_card_chicken_request(user_id, user_input):
    # 1. NLU: 의도(음식추천) + 엔티티(급식카드, 치킨) 추출
    entities = extract_entities(user_input)
    
    # 2. 사용자 급식카드 확인
    foodcard = get_user_foodcard(user_id)
    
    # 3. 착한가게 중 치킨 카테고리 필터링
    chicken_shops = filter_shops({
        'category': '치킨',
        'isGoodInfluenceShop': True,
        'isFoodCardShop': 'Y'
    })
    
    # 4. 사용자 위치 기반 정렬
    user_location = get_user_location(user_id)
    nearby_shops = sort_by_distance(chicken_shops, user_location)
    
    # 5. 과거 주문 이력 반영
    user_orders = get_user_order_history(user_id)
    personalized_shops = apply_preference_scoring(nearby_shops, user_orders)
    
    # 6. 쿠폰 적용 가능 가게 우선
    final_recommendations = prioritize_with_coupons(user_id, personalized_shops)
    
    return generate_response(final_recommendations, entities)
```

### **시나리오 2: "1만원 이하로 맛있는 곳"**
```python
def process_budget_request(user_id, budget_limit):
    # 1. 예산 내 메뉴 필터링
    affordable_menus = filter_menus({'price': {'$lte': budget_limit}})
    
    # 2. 리뷰 평점 높은 가게 우선
    high_rated_shops = get_shops_by_menu_ids(affordable_menus)
    rated_shops = add_rating_scores(high_rated_shops)
    
    # 3. 사용자 과거 선호도 반영
    user_favorites = get_user_favorites(user_id)
    preference_matched = apply_favorite_patterns(rated_shops, user_favorites)
    
    # 4. 현재 운영중인 가게만
    open_shops = filter_by_operating_hours(preference_matched)
    
    return generate_budget_response(open_shops, budget_limit)
```

---

## 📊 **Feature 우선순위 및 활용도**

### **🥇 최고 우선순위 (핵심 Features)**
1. **shop** - 기본 추천 정보
2. **foodcard** - 급식카드 사용자 필터링 (타겟 핵심!)
3. **userfavorite** - 개인화 추천
4. **user** - 사용자 개인화

### **🥈 높은 우선순위**
5. **shop_menu** - 메뉴 상세 추천
6. **review** - 평점 기반 품질 보장
7. **ticket & product_order** - 주문 이력 학습
8. **point_transaction** - 결제 패턴 분석

### **🥉 보조 Features**
9. **coupon 관련** - 할인 혜택 제공
10. **giftcard 관련** - 결제 수단 다양화
11. **coop 관련** - 제휴 혜택 확장

---

## 🚀 **실제 구현 로드맵**

### **Phase 1: MVP (1-2주)**
```python
# 필수 Features만 활용
essential_features = [
    'shop',           # 기본 가게 정보
    'shop_menu',      # 메뉴 정보  
    'foodcard',       # 급식카드 필터링
    'user',           # 기본 개인화
    'userfavorite'    # 찜 기능
]
```

### **Phase 2: 고도화 (3-4주)**
```python
# 학습 및 개인화 강화
advanced_features = [
    'ticket',         # 주문 이력
    'product_order',  # 구매 패턴
    'review',         # 평점 시스템
    'point_transaction' # 포인트 사용 패턴
]
```

### **Phase 3: 완전체 (5-6주)**
```python
# 모든 혜택 연동
complete_features = [
    'coupon_*',       # 쿠폰 시스템
    'giftcard_*',     # 기프트카드
    'coop_*'          # 제휴 혜택
]
```

---

## 🎯 **결론: 발견된 새로운 Features**

### **기존 인식 (COMPLETE_DATABASE_SCHEMA.md)**
- 가게/메뉴 정보만 주로 언급
- 대화 로그 중심 설계

### **실제 발견된 추가 Features (sample_data.xlsx 분석 결과)**

1. **💳 급식카드 시스템** (foodcard 테이블)
   - 나비얌 챗봇의 핵심 타겟 사용자층
   - 착한가게 필터링 필수

2. **🎫 쿠폰/프로모션 시스템** (coupon 관련 7개 테이블)
   - 할인 혜택 제공
   - 사용자 유치 및 재방문 유도

3. **💳 기프트카드 시스템** (giftcard 관련 3개 테이블)
   - 다양한 결제 수단
   - 선물하기 기능

4. **🎟️ 티켓/주문 시스템** (ticket, product_order)
   - 실제 거래 데이터
   - 학습용 선호도 데이터

5. **⭐ 리뷰/평가 시스템** (review)
   - 품질 보장
   - 사용자 만족도 기반 추천

6. **🏢 협력업체 시스템** (coop 관련 3개 테이블)
   - 제휴 혜택 확장
   - 다양한 선택지 제공

7. **💰 포인트 시스템** (point_transaction)
   - 결제 패턴 학습
   - 사용자 유지

**총 31개 테이블의 모든 feature가 챗봇에서 실제 활용 가능하며, 기존 예상보다 훨씬 더 풍부한 개인화 및 혜택 제공이 가능함을 확인했습니다.**

---

## 📞 **관련 문서**

- [sample_data.xlsx](sample_data.xlsx) - 원본 데이터 (31개 시트)
- [DATA_STATUS.md](DATA_STATUS.md) - 데이터 현황
- [DATA_ANALYSIS_DETAIL.md](DATA_ANALYSIS_DETAIL.md) - 상세 분석
- [CHATBOT_WORKFLOW_COMPLETE.md](CHATBOT_WORKFLOW_COMPLETE.md) - 워크플로우
- [COMPLETE_DATABASE_SCHEMA.md](COMPLETE_DATABASE_SCHEMA.md) - 기존 스키마

**🎯 이제 31개 테이블의 모든 feature를 활용한 완전한 나비얌 챗봇 구현이 가능합니다!**