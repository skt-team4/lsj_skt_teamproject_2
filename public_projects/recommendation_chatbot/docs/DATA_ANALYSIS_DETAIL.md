# 나비얌 챗봇 데이터 상세 분석 및 구축 전략

*최종 업데이트: 2025.07.31*  
*관련 문서: [DATA_STATUS.md](DATA_STATUS.md)*

## 📊 **sample_data.xlsx 전체 분석 결과**

### **🔍 완전 분석 개요**
- **총 시트 수**: 31개
- **총 데이터 건수**: 각 시트별 10-12개 샘플 데이터
- **총 컬럼 수**: 500+ 개 (모든 시트 합계)
- **데이터 구성**: 실제 서비스 구조를 반영한 완전한 스키마

---

## 🗂️ **카테고리별 테이블 분석**

### **🏪 1. 가게 관련 데이터 (보유 가능)**

#### **`shop` (11개 행, 38개 컬럼)**
**핵심 컬럼:**
- **기본 정보**: id, shopName, addressName, addressPoint, contact
- **운영 정보**: openHour, closeHour, breakStartHour, breakEndHour, offDay
- **카테고리**: category, sales_type, open_status
- **특성**: isGoodInfluenceShop, isFoodCardShop, isAroundTheClock
- **관리**: managerId, approved, joined, deleted_at, brand_id

#### **`shop_menu` (11개 행, 15개 컬럼)**
**핵심 컬럼:**
- **메뉴 정보**: name, description, price, img
- **상태**: is_sold_out, is_best, deleted_at
- **관계**: shop_id, category_id
- **관리**: discount_value, priority, type

#### **`shop_menu_category` (11개 행, 6개 컬럼)**
- id, name, priority, shop_id, created_at, updated_at

#### **`shop_menu_option` (10개 행, 8개 컬럼)**
- **옵션 정보**: name, price, is_sold_out
- **관계**: option_category_id
- **관리**: priority, created_at, updated_at

#### **`brand` (8개 행, 15개 컬럼)**
**핵심 컬럼:**
- **브랜드 정보**: name, logo, description, site_url
- **소셜**: instagram_link, facebook_link, youtube_link
- **관리**: brand_manager_id, primary_color, is_active

---

### **👤 2. 사용자 관련 데이터 (생성 필요)**

#### **`user` (11개 행, 25개 컬럼)**
**핵심 컬럼:**
- **인증**: loginId, email, password, phone
- **프로필**: name, nickname, birthday, imageUrl
- **상태**: role, isApproved, isBanned, useYN
- **설정**: marketingOn, deviceToken, currentAddress
- **관리**: snsType, reportCnt, stopDuration, deleted_at

#### **`user_location` (11개 행, 4개 컬럼)**
- id, user_id, state, city

#### **`userfavorite` (11개 행, 5개 컬럼)**
- id, userId, shopId, createdAt, updatedAt

---

### **🎫 3. 거래/티켓 데이터 (생성 필요)**

#### **`ticket` (11개 행, 19개 컬럼)**
**핵심 컬럼:**
- **기본 정보**: user_id, shop_id, ticket_number
- **상태**: expired_at, paid_at, used_at, canceled_at
- **포인트**: point_amount, bbugiddogi_point_amount, bongridangil_point_amount
- **메타**: shop_name, shop_thumbnail, cancel_reason

#### **`product_order` (11개 행, 27개 컬럼)**
**핵심 컬럼:**
- **주문 정보**: user_id, product_id, quantity, amount
- **배송**: delivery_address, delivery_status, tracking_number
- **상태**: order_status, delivered_at, canceled_at, refunded_at
- **결제**: point_amount, giftcard_usage_amount
- **관리**: admin_id, user_coupon_id, courier_id

---

### **🎁 4. 쿠폰/프로모션 데이터 (생성 필요)**

#### **`coupon` (10개 행, 30개 컬럼)**
**핵심 컬럼:**
- **쿠폰 정보**: name, description, type, amount
- **제한**: quantity, min_amount_available, max_discount_value
- **기간**: expiry_datetime, published_at, finished_at
- **관리**: payer_type, usage_type, sponsor_id, publisher_id

#### **`coop_coupon` (11개 행, 30개 컬럼)**
**협력업체 쿠폰 - 외부 제휴 쿠폰 시스템**

#### **매핑 테이블들:**
- `coupon_menu_map`, `coupon_shop_map`, `coupon_product_map`, `coupon_user_map`

---

### **💳 5. 기프트카드 시스템 (생성 필요)**

#### **`giftcard` (11개 행, 19개 컬럼)**
- **카드 정보**: name, image_url, pub_amt, pub_quantity
- **제한**: usage_list, targets, min_available_amt, max_applicable_val
- **관리**: published_at, expired_at, paused_at

#### **`giftcard_wallet` (11개 행, 9개 컬럼)**
- user_id, giftcard_id, balance, hidden_at, paused_at

#### **`giftcard_wallet_transaction` (11개 행, 9개 컬럼)**
- **거래 정보**: wallet_id, type, usage_type, amount, content

---

### **⭐ 6. 리뷰/평가 데이터 (생성 필요)**

#### **`review` (11개 행, 9개 컬럼)**
**핵심 컬럼:**
- **리뷰 정보**: user_id, store_id, subject_id, comment
- **메타**: img_static, subject_type
- **관리**: createdAt, updatedAt

---

### **🏢 7. 협력업체 데이터 (생성 필요)**

#### **`coop_brand` (11개 행, 10개 컬럼)**
- **브랜드**: name, image_url, category_id, category_name

#### **`coop_company` (11개 행, 8개 컬럼)**
- **업체**: name, code, brand_id, category_name

#### **`coop_category` (10개 행, 5개 컬럼)**
- **카테고리**: name

---

### **🏪 8. 상품 관련 (생성 필요)**

#### **`products` (11개 행, 16개 컬럼)**
**핵심 컬럼:**
- **상품 정보**: name, origin_price, discounted_price, thumbnail
- **분류**: category, type, company, number
- **관리**: quantity, delivery_fee, product_company_id

---

### **💰 9. 포인트/결제 (생성 필요)**

#### **`point_transaction` (11개 행, 12개 컬럼)**
**핵심 컬럼:**
- **거래**: user_id, type_cat, type, amount, balance
- **메타**: content, expired_at, remark, ord_service

#### **`foodcard` (11개 행, 21개 컬럼)**
**아동급식카드 관련:**
- **카드 정보**: card_number, owner_name, owner_birthday, company
- **지역**: region_do, region_si, region_dong
- **상태**: status, verified_at, expired_at, rejected_at

---

## 🎯 **Gemini 전문가 데이터 구축 전략**

### **📋 1. 최소 필수 데이터 (MVP)**
```markdown
✅ 즉시 활용 가능:
- shop (11개 가게, 38개 컬럼)
- shop_menu (메뉴 정보)

🔧 추가 필요:
- popularity_score (0~1): 가상 인기도
- simulated_rating (1~5): 가상 평점
```

### **📈 2. 우선순위별 구축 전략**

#### **🥇 1순위: MVP 핵심 (1개월)**
**목표**: 비개인화 추천 챗봇
```bash
필수 데이터:
- shop, shop_menu + 가상 인기도/평점

구현 기능:
- 키워드 기반 검색 ("치킨 먹고 싶어")
- 위치 기반 추천 ("강남역 맛집")  
- 인기 기반 추천 ("오늘 뭐 먹지?")
```

#### **🥈 2순위: 기본 개인화 (2-3개월)**
**목표**: 사용자 취향 반영
```bash
생성 필요 데이터:
- user (사용자 프로필)
- review (별점 중심)
- userfavorite (찜 기능)

구현 기능:
- 사용자 찜 기능
- "찜한 가게와 비슷한 곳 추천"
- 별점 기반 추천
```

#### **🥉 3순위: 고급 개인화 (4-6개월)**
**목표**: 구매 패턴 기반 추천
```bash
생성 필요 데이터:
- product_order, ticket (거래 내역)
- 실제 데이터 확보 시작

구현 기능:
- 협업 필터링 ("이걸 산 다른 사람들은...")
- 시간/상황 인지 추천
- 쿠폰/프로모션 추천
```

### **🤖 3. 데이터 생성 전략**

#### **사용자 데이터 생성**
```python
# 주요 상권 중심 클러스터링
주요_상권 = ["강남역", "홍대입구", "명동", "신촌", "이태원"]
사용자_분포 = {
    "20대 대학생": 40%,  # 홍대, 신촌 중심
    "30대 직장인": 35%,  # 강남, 명동 중심  
    "40대 가족": 25%     # 주거지 중심
}
```

#### **거래 패턴 생성**
```python
페르소나별_패턴 = {
    "20대 대학생": {
        "시간": "평일 12-1시 (점심)",
        "장소": "학교 근처",
        "가격": "5000-15000원",
        "카테고리": ["분식", "돈까스", "치킨"]
    },
    "30대 직장인": {
        "시간": "평일 12-1시, 18-20시",
        "장소": "회사 근처, 역세권",
        "가격": "10000-30000원", 
        "카테고리": ["한식", "중식", "일식"]
    }
}
```

#### **리뷰 생성 전략**
```python
리뷰_분포 = {
    "긍정 (4-5점)": 80%,
    "부정 (1-2점)": 20%
}

템플릿_예시 = {
    "긍정": ["맛있어요!", "직장인 점심으로 딱!", "가성비 좋아요"],
    "부정": ["별로에요", "가격에 비해 아쉬워요", "기대했는데 실망"]
}
```

### **🔄 4. 하이브리드 데이터 전략**

#### **초기 (MVP)**: 100% 생성 데이터
- **장점**: 빠른 개발, 원하는 분포 제어 가능
- **용도**: 추천 로직 개발 및 테스트

#### **중장기**: 실제 데이터로 점진적 교체  
```markdown
실제 데이터 확보 방안:
1. 크롤링: 네이버 플레이스, 망고플레이트 (약관 준수)
2. 공공 데이터: 정부 착한가게 데이터
3. 제휴: 소상공인 가게와 직접 제휴
```

---

## 🚀 **즉시 실행 가능한 첫 단계**

### **1. 가상 점수 추가 스크립트**
```python
# scripts/add_virtual_scores.py
import pandas as pd

# shop 테이블에 가상 점수 추가
def add_virtual_scores():
    # 착한가게에 가중치 부여
    # 카테고리별 인기도 차등 적용
    # 위치별 점수 조정 (역세권 가중치)
```

### **2. 기존 데이터 처리 파이프라인 분석**
- `data/data_loader.py` 확인
- `analyze_data.py` 기능 파악
- 확장 방안 설계

---

## 📚 **관련 문서**

- [DATA_STATUS.md](DATA_STATUS.md) - 전체 데이터 현황 요약
- [conversation_summary_0731_v1.md](work_summary/conversation_summary_0731_v1.md) - 프로젝트 전체 현황
- `sample_data.xlsx` - 원본 데이터 파일

**🎯 결론: 31개 테이블의 완전한 분석을 바탕으로 3단계 점진적 구축 전략 수립 완료!**