-- ===============================================
-- YUMAI 데이터베이스 전체 기능 테스트 스크립트
-- ===============================================

-- 1. 기본 CRUD 테스트
-- ===============================================

-- 1.1 사용자 관리 테스트
-- 사용자 생성
INSERT INTO chatbot.users (external_user_id, platform, user_name, nickname, email, phone_number, birthday)
VALUES 
    ('kakao_user_123', 'kakao', '김철수', '철수', 'chulsoo@example.com', '010-1234-5678', '1990-05-15'),
    ('line_user_456', 'line', '이영희', '영희', 'younghee@example.com', '010-2345-6789', '1995-08-20'),
    ('web_user_789', 'web', '박민수', '민수', 'minsoo@example.com', '010-3456-7890', '1988-12-10');

-- 사용자 조회
SELECT id, user_name, platform, user_status FROM chatbot.users;

-- 사용자 업데이트 (updated_at 트리거 테스트)
UPDATE chatbot.users 
SET preferred_location = '강남구', last_login_at = CURRENT_TIMESTAMP 
WHERE external_user_id = 'kakao_user_123';

-- updated_at 자동 업데이트 확인
SELECT user_name, created_at, updated_at, last_login_at 
FROM chatbot.users WHERE external_user_id = 'kakao_user_123';

-- 1.2 가게 정보 관리
-- 가게 추가 (JSONB 필드 포함)
INSERT INTO chatbot.shops (shop_name, category, latitude, longitude, is_good_influence_shop, is_food_card_shop, business_hours, contact)
VALUES 
    ('김밥천국', '분식', 37.5665, 126.9780, true, 'Y', 
     '{"monday": {"open": "08:00", "close": "22:00"}, "tuesday": {"open": "08:00", "close": "22:00"}, "sunday": {"closed": true}}'::jsonb,
     '02-1234-5678'),
    ('스타벅스', '카페/디저트', 37.5666, 126.9781, false, 'N',
     '{"monday": {"open": "07:00", "close": "22:00"}, "saturday": {"open": "08:00", "close": "23:00"}}'::jsonb,
     '02-2345-6789'),
    ('맥도날드', '패스트푸드', 37.5667, 126.9782, false, 'P',
     '{"monday": {"open": "00:00", "close": "23:59"}}'::jsonb,
     '02-3456-7890');

-- 가게 영업시간 함수 테스트
SELECT * FROM get_shop_hours(4, 'monday');

-- 1.3 메뉴 관리 (JSONB 옵션 포함)
INSERT INTO chatbot.menus (shop_id, menu_name, price, category, options, is_best)
VALUES 
    (4, '참치김밥', 3500, '메인메뉴', 
     '{"size": [{"name": "보통", "price": 0}, {"name": "곱빼기", "price": 1000}]}'::jsonb, true),
    (4, '라면', 4000, '메인메뉴', 
     '{"spicy": [{"name": "순한맛", "price": 0}, {"name": "매운맛", "price": 0}]}'::jsonb, false),
    (5, '아메리카노', 4500, '음료', 
     '{"size": [{"name": "Tall", "price": 0}, {"name": "Grande", "price": 500}, {"name": "Venti", "price": 1000}]}'::jsonb, true);

-- 메뉴 옵션 조회
SELECT menu_name, price, options->>'size' as size_options 
FROM chatbot.menus WHERE shop_id = 4;

-- 2. 트리거 및 함수 테스트
-- ===============================================

-- 2.1 updated_at 트리거 테스트
SELECT shop_name, created_at, updated_at FROM chatbot.shops WHERE id = 4;
UPDATE chatbot.shops SET popularity_score = 0.75 WHERE id = 4;
SELECT shop_name, created_at, updated_at, popularity_score FROM chatbot.shops WHERE id = 4;

-- 2.2 영업시간 조회 함수 테스트
SELECT * FROM get_shop_hours(4, 'monday');
SELECT * FROM get_shop_hours(4, 'sunday');
SELECT * FROM get_shop_hours(4); -- 현재 요일

-- 3. 복잡한 관계 테스트
-- ===============================================

-- 3.1 사용자 프로필 생성
INSERT INTO chatbot.user_profiles (user_id, preferred_categories, average_budget, taste_preferences, good_influence_preference)
VALUES 
    (1, ARRAY['한식', '중식'], 10000, 
     '{"매운맛": 0.8, "단맛": 0.3, "짠맛": 0.5}'::jsonb, 0.75),
    (2, ARRAY['일식', '양식'], 20000,
     '{"매운맛": 0.2, "단맛": 0.7}'::jsonb, 0.30);

-- 3.2 급식카드 사용자 등록
INSERT INTO chatbot.foodcard_users (user_id, card_number, card_type, card_status, balance, target_age_group)
VALUES 
    (1, 'CARD-2024-001', '청소년급식카드', 'ACTIVE', 50000, '고등학생'),
    (2, 'CARD-2024-002', '아동급식카드', 'ACTIVE', 30000, '중학생');

-- 3.3 쿠폰 생성 및 발급
INSERT INTO chatbot.coupons (coupon_name, coupon_code, coupon_type, discount_rate, usage_type, valid_from, valid_until, target_categories)
VALUES 
    ('신규가입 할인', 'WELCOME2024', 'PERCENTAGE', 0.20, 'NEW_USER', '2024-01-01', '2024-12-31', ARRAY['한식', '중식']),
    ('급식카드 할인', 'FOODCARD10', 'FIXED_AMOUNT', NULL, 'FOODCARD', '2024-01-01', '2024-12-31', NULL);

UPDATE chatbot.coupons SET discount_amount = 3000 WHERE coupon_code = 'FOODCARD10';

-- 사용자 지갑에 쿠폰 발급
INSERT INTO chatbot.user_wallet (user_id, coupon_id, acquisition_source, expires_at)
VALUES 
    (1, 1, 'WELCOME_BONUS', '2024-12-31'),
    (1, 2, 'LOYALTY_REWARD', '2024-12-31'),
    (2, 1, 'WELCOME_BONUS', '2024-12-31');

-- 4. 주문 및 리뷰 플로우 테스트
-- ===============================================

-- 4.1 주문 생성
INSERT INTO chatbot.orders (user_id, shop_id, menu_id, order_status, order_time, quantity, price, discount_applied)
VALUES 
    (1, 4, 1, 'confirmed', '2024-11-20 12:30:00+09', 2, 7000, 1000),
    (2, 5, 3, 'prepared', '2024-11-20 13:00:00+09', 1, 4500, 0);

-- 4.2 쿠폰 사용 기록
INSERT INTO chatbot.orders_coupons (order_id, user_wallet_id, applied_discount)
VALUES (1, 1, 1000);

-- 쿠폰 상태 업데이트
UPDATE chatbot.user_wallet SET coupon_status = 'USED' WHERE id = 1;

-- 4.3 리뷰 작성
INSERT INTO chatbot.reviews (user_id, shop_id, order_id, rating, comment)
VALUES 
    (1, 4, 1, 4.5, '맛있고 양도 많아요! 급식카드 사용 가능해서 좋습니다.'),
    (2, 5, 2, 3.0, '평범한 맛이었어요.');

-- 5. 파티션 테이블 테스트
-- ===============================================

-- 5.1 다양한 시간대 대화 데이터 삽입
INSERT INTO chatbot.conversations (session_id, user_id, conversation_time, input_text, response_text, extracted_intent, extracted_entities)
VALUES 
    (uuid_generate_v4(), 1, '2024-11-15 10:00:00+09', '오늘 점심 추천해주세요', '김밥천국 어떠세요?', 'FOOD_REQUEST', '{"meal_type": "lunch"}'::jsonb),
    (uuid_generate_v4(), 1, '2024-12-01 18:00:00+09', '급식카드 사용 가능한 곳', '급식카드 사용 가능 가게입니다', 'COUPON_INQUIRY', '{"card_type": "foodcard"}'::jsonb),
    (uuid_generate_v4(), 2, '2025-01-10 12:00:00+09', '1만원 이하 메뉴', '예산에 맞는 메뉴입니다', 'BUDGET_INQUIRY', '{"budget": 10000}'::jsonb);

-- 파티션별 데이터 분포 확인
SELECT 
    tableoid::regclass as partition_name,
    COUNT(*) as record_count,
    TO_CHAR(MIN(conversation_time), 'YYYY-MM') as month
FROM chatbot.conversations
GROUP BY tableoid
ORDER BY MIN(conversation_time);

-- 6. 인덱스 활용 테스트
-- ===============================================

-- 6.1 카테고리별 가게 검색
EXPLAIN ANALYZE
SELECT shop_name, category FROM chatbot.shops WHERE category = '한식';

-- 6.2 착한가게 필터링
EXPLAIN ANALYZE
SELECT shop_name FROM chatbot.shops WHERE is_good_influence_shop = true;

-- 6.3 가게명 검색 (GIN 인덱스)
EXPLAIN ANALYZE
SELECT shop_name FROM chatbot.shops WHERE shop_name ILIKE '%김밥%';

-- 6.4 사용자 선호 카테고리 검색 (GIN 인덱스)
EXPLAIN ANALYZE
SELECT user_id FROM chatbot.user_profiles WHERE preferred_categories @> ARRAY['한식'];

-- 7. 외래키 제약조건 테스트
-- ===============================================

-- 7.1 존재하지 않는 가게에 메뉴 추가 시도 (실패해야 함)
-- INSERT INTO chatbot.menus (shop_id, menu_name, price) VALUES (999, '테스트메뉴', 5000);

-- 7.2 CASCADE 삭제 테스트용 임시 데이터
INSERT INTO chatbot.shops (shop_name, category, latitude, longitude) 
VALUES ('임시가게', '기타음식', 37.5, 127.0);

INSERT INTO chatbot.menus (shop_id, menu_name, price) 
VALUES (currval('chatbot.shops_id_seq'), '임시메뉴', 5000);

-- 가게 삭제 시 메뉴도 함께 삭제되는지 확인
DELETE FROM chatbot.shops WHERE shop_name = '임시가게';

-- 8. CHECK 제약조건 테스트
-- ===============================================

-- 8.1 잘못된 이메일 형식 (실패해야 함)
-- INSERT INTO chatbot.users (external_user_id, email) VALUES ('test_user', 'invalid-email');

-- 8.2 범위 밖의 점수 (실패해야 함)
-- UPDATE chatbot.shops SET popularity_score = 1.5 WHERE id = 4;

-- 8.3 잘못된 위도/경도 (실패해야 함)
-- INSERT INTO chatbot.shops (shop_name, category, latitude, longitude) 
-- VALUES ('잘못된가게', '한식', 91, 181);

-- 9. Materialized View 테스트
-- ===============================================

-- 9.1 최근 대화 조회
SELECT COUNT(*) as total_recent FROM chatbot.recent_conversations;

-- 9.2 새 대화 추가 후 갱신
INSERT INTO chatbot.conversations (session_id, user_id, conversation_time, input_text, response_text)
VALUES (uuid_generate_v4(), 1, CURRENT_TIMESTAMP, '테스트 입력', '테스트 응답');

REFRESH MATERIALIZED VIEW chatbot.recent_conversations;
SELECT COUNT(*) as updated_count FROM chatbot.recent_conversations;

-- 10. 분석 테이블 테스트
-- ===============================================

-- 10.1 추천 로그 기록
INSERT INTO analytics.recommendations_log (user_id, shop_id, session_id, request_food_type, request_budget, recommendations, recommendation_count, top_recommendation_shop_id)
VALUES 
    (1, 4, uuid_generate_v4(), '한식', 10000, 
     '[{"shop_id": 4, "score": 0.95, "reason": "선호 카테고리 일치"}]'::jsonb, 1, 4);

-- 10.2 사용자 피드백 기록
INSERT INTO analytics.user_feedback (session_id, related_recommendation_id, user_id, feedback_type, feedback_target_type, feedback_target_id, feedback_content)
VALUES 
    (uuid_generate_v4(), 1, 1, 'rating', 'shop', '4', '{"rating": 5}'::jsonb);

-- 11. 통계 쿼리
-- ===============================================

-- 11.1 카테고리별 가게 수
SELECT category, COUNT(*) as shop_count 
FROM chatbot.shops 
GROUP BY category 
ORDER BY shop_count DESC;

-- 11.2 사용자별 주문 횟수
SELECT u.user_name, COUNT(o.id) as order_count
FROM chatbot.users u
LEFT JOIN chatbot.orders o ON u.id = o.user_id
GROUP BY u.id, u.user_name;

-- 11.3 평균 리뷰 점수별 가게
SELECT s.shop_name, AVG(r.rating) as avg_rating, COUNT(r.id) as review_count
FROM chatbot.shops s
LEFT JOIN chatbot.reviews r ON s.id = r.shop_id
GROUP BY s.id, s.shop_name
HAVING COUNT(r.id) > 0
ORDER BY avg_rating DESC;

-- 11.4 월별 대화 수
SELECT 
    TO_CHAR(conversation_time, 'YYYY-MM') as month,
    COUNT(*) as conversation_count
FROM chatbot.conversations
GROUP BY TO_CHAR(conversation_time, 'YYYY-MM')
ORDER BY month;

-- 12. 정리 함수 테스트
-- ===============================================

-- 12.1 잘못된 가게 참조 정리
UPDATE chatbot.user_profiles 
SET favorite_shops = ARRAY[4, 999, 5] 
WHERE user_id = 1;

SELECT clean_invalid_shop_references();

SELECT favorite_shops FROM chatbot.user_profiles WHERE user_id = 1;

-- 12.2 오래된 대화 삭제 함수 (6개월 이상)
SELECT auto_delete_old_conversations();

-- 최종 상태 확인
-- ===============================================
SELECT 
    'Users' as table_name, COUNT(*) as count FROM chatbot.users
UNION ALL
SELECT 'Shops', COUNT(*) FROM chatbot.shops
UNION ALL
SELECT 'Menus', COUNT(*) FROM chatbot.menus
UNION ALL
SELECT 'Orders', COUNT(*) FROM chatbot.orders
UNION ALL
SELECT 'Reviews', COUNT(*) FROM chatbot.reviews
UNION ALL
SELECT 'Conversations', COUNT(*) FROM chatbot.conversations
UNION ALL
SELECT 'Coupons', COUNT(*) FROM chatbot.coupons
UNION ALL
SELECT 'User Wallets', COUNT(*) FROM chatbot.user_wallet;