-- 테스트 사용자 생성
INSERT INTO chatbot.users (external_user_id, platform, user_name, email)
VALUES 
    ('test_user_001', 'test', '테스트유저1', 'test1@example.com'),
    ('test_user_002', 'test', '테스트유저2', 'test2@example.com');

-- 테스트 가게 생성
INSERT INTO chatbot.shops (shop_name, category, latitude, longitude, is_good_influence_shop, is_food_card_shop)
VALUES 
    ('맛있는 김치찌개', '한식', 37.5665, 126.9780, true, 'Y'),
    ('최고 치킨', '치킨', 37.5666, 126.9781, false, 'Y'),
    ('피자헛', '피자', 37.5667, 126.9782, false, 'N');

-- 파티션별 대화 데이터 삽입 테스트
-- 2024년 8월 데이터
INSERT INTO chatbot.conversations (
    session_id, user_id, conversation_time,
    input_text, response_text,
    extracted_intent, intent_confidence
) VALUES (
    uuid_generate_v4(), 1, '2024-08-15 10:30:00+09',
    '오늘 점심 뭐 먹을까요?', '김치찌개 어떠세요?',
    'FOOD_REQUEST', 0.95
);

-- 2024년 9월 데이터
INSERT INTO chatbot.conversations (
    session_id, user_id, conversation_time,
    input_text, response_text,
    extracted_intent, intent_confidence
) VALUES (
    uuid_generate_v4(), 1, '2024-09-20 12:00:00+09',
    '치킨 먹고 싶어요', '최고 치킨을 추천드립니다!',
    'FOOD_REQUEST', 0.98
);

-- 2024년 10월 데이터
INSERT INTO chatbot.conversations (
    session_id, user_id, conversation_time,
    input_text, response_text,
    extracted_intent, intent_confidence
) VALUES (
    uuid_generate_v4(), 2, '2024-10-10 18:30:00+09',
    '저녁 추천해주세요', '피자는 어떠신가요?',
    'FOOD_REQUEST', 0.92
);

-- 2025년 1월 데이터 (현재 시점 기준 미래)
INSERT INTO chatbot.conversations (
    session_id, user_id, conversation_time,
    input_text, response_text,
    extracted_intent, intent_confidence,
    recommended_shop_ids
) VALUES (
    uuid_generate_v4(), 2, '2025-01-15 13:00:00+09',
    '급식카드 사용 가능한 곳 알려주세요', '급식카드 사용 가능한 가게를 알려드릴게요.',
    'COUPON_INQUIRY', 0.89,
    ARRAY[1, 2]
);

-- 2025년 2월 데이터
INSERT INTO chatbot.conversations (
    session_id, user_id, conversation_time,
    input_text, response_text,
    extracted_intent, intent_confidence,
    extracted_entities
) VALUES (
    uuid_generate_v4(), 1, '2025-02-20 14:30:00+09',
    '1만원 이하 점심 추천', '예산에 맞는 메뉴를 찾아드릴게요.',
    'BUDGET_INQUIRY', 0.93,
    '{"budget": 10000, "meal_type": "lunch"}'::jsonb
);

-- 파티션별 데이터 확인
SELECT 
    tableoid::regclass as partition_name,
    COUNT(*) as record_count,
    MIN(conversation_time) as min_time,
    MAX(conversation_time) as max_time
FROM chatbot.conversations
GROUP BY tableoid
ORDER BY MIN(conversation_time);

-- 특정 기간 데이터 조회 (파티션 프루닝 테스트)
SELECT 
    id, session_id, conversation_time, extracted_intent
FROM chatbot.conversations
WHERE conversation_time >= '2024-09-01' AND conversation_time < '2024-10-01'
ORDER BY conversation_time;

-- Materialized View 새로고침 및 확인
REFRESH MATERIALIZED VIEW chatbot.recent_conversations;

SELECT COUNT(*) as recent_count FROM chatbot.recent_conversations;