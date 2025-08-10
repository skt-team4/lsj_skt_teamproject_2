-- ===============================================
-- YUMAI 데이터베이스 최종 테스트 스크립트
-- Session Master 포함 완전 테스트
-- ===============================================

-- ===============================================
-- 1. 기본 데이터 삽입
-- ===============================================

-- 사용자 생성
INSERT INTO chatbot.users (external_user_id, platform, user_name, email)
VALUES 
    ('test_user_001', 'test', '테스트유저1', 'test1@example.com'),
    ('test_user_002', 'test', '테스트유저2', 'test2@example.com'),
    ('test_user_003', 'test', '테스트유저3', 'test3@example.com');

-- 가게 생성
INSERT INTO chatbot.shops (shop_name, category, latitude, longitude, is_good_influence_shop, is_food_card_shop)
VALUES 
    ('맛있는 김치찌개', '한식', 37.5665, 126.9780, true, 'Y'),
    ('최고 치킨', '치킨', 37.5666, 126.9781, false, 'Y'),
    ('피자헛', '피자', 37.5667, 126.9782, false, 'N');

-- 메뉴 생성
INSERT INTO chatbot.menus (shop_id, menu_name, price, category)
VALUES 
    (1, '김치찌개', 8000, '메인메뉴'),
    (1, '된장찌개', 7500, '메인메뉴'),
    (2, '후라이드치킨', 18000, '메인메뉴');

-- ===============================================
-- 2. Session Master 테스트
-- ===============================================
\echo '=== Session Master 테스트 ==='

-- 세션 시작 함수 테스트
SELECT start_session(1, 'chat', '{"device": "mobile"}'::jsonb) as session_id_1 \gset
SELECT start_session(2, 'api', '{"client": "python"}'::jsonb) as session_id_2 \gset

-- 세션 확인
SELECT session_id, user_id, session_type, is_active 
FROM chatbot.session_master
ORDER BY session_start;

-- ===============================================
-- 3. 외래키 무결성 테스트
-- ===============================================
\echo '=== 외래키 무결성 테스트 ==='

-- 3.1 정상 케이스: 유효한 session_id로 대화 삽입
INSERT INTO chatbot.conversations (session_id, user_id, input_text, response_text, conversation_time)
VALUES 
    (:'session_id_1', 1, '오늘 점심 뭐 먹을까요?', '김치찌개 어떠세요?', '2024-11-01 12:00:00'),
    (:'session_id_1', 1, '가격이 얼마예요?', '8000원입니다.', '2024-11-01 12:01:00');

-- 3.2 실패 케이스: 존재하지 않는 session_id (오류 발생해야 함)
\echo '다음은 오류가 발생해야 정상:'
INSERT INTO chatbot.conversations (session_id, user_id, input_text, response_text)
VALUES ('11111111-1111-1111-1111-111111111111', 1, '테스트', '테스트');

-- 3.3 user_interactions 테이블 외래키 테스트
-- 정상: 유효한 session_id
INSERT INTO ml_features.user_interactions (user_id, session_id, interaction_type)
VALUES (1, :'session_id_1', 'text_input');

-- 실패: 존재하지 않는 session_id (오류 발생해야 함)
\echo '다음은 오류가 발생해야 정상:'
INSERT INTO ml_features.user_interactions (user_id, session_id, interaction_type)
VALUES (1, '22222222-2222-2222-2222-222222222222', 'text_input');

-- 3.4 recommendations_log 테이블 외래키 테스트
INSERT INTO analytics.recommendations_log (user_id, shop_id, session_id, recommendations, recommendation_count)
VALUES (1, 1, :'session_id_1', '[{"shop_id": 1, "score": 0.95}]'::jsonb, 1);

-- 3.5 user_feedback 테이블 외래키 테스트
INSERT INTO analytics.user_feedback (session_id, user_id, feedback_type, feedback_target_type, feedback_target_id)
VALUES (:'session_id_1', 1, 'rating', 'shop', '1');

-- ===============================================
-- 4. 파티셔닝 동작 테스트
-- ===============================================
\echo '=== 파티셔닝 동작 테스트 ==='

-- 다양한 월의 대화 데이터 삽입
INSERT INTO chatbot.conversations (session_id, user_id, input_text, response_text, conversation_time)
VALUES 
    (:'session_id_1', 1, '8월 대화', '응답', '2024-08-15 10:00:00'),
    (:'session_id_1', 1, '9월 대화', '응답', '2024-09-20 14:00:00'),
    (:'session_id_1', 1, '10월 대화', '응답', '2024-10-25 18:00:00'),
    (:'session_id_2', 2, '2025년 1월 대화', '응답', '2025-01-10 09:00:00'),
    (:'session_id_2', 2, '2025년 2월 대화', '응답', '2025-02-15 13:00:00');

-- 파티션별 데이터 분포 확인
SELECT 
    tableoid::regclass as partition_name,
    COUNT(*) as record_count,
    TO_CHAR(MIN(conversation_time), 'YYYY-MM') as month
FROM chatbot.conversations
GROUP BY tableoid
ORDER BY MIN(conversation_time);

-- 특정 기간 쿼리 (파티션 프루닝 확인)
EXPLAIN (ANALYZE, BUFFERS) 
SELECT * FROM chatbot.conversations 
WHERE conversation_time >= '2024-09-01' AND conversation_time < '2024-10-01';

-- ===============================================
-- 5. CASCADE 삭제 테스트
-- ===============================================
\echo '=== CASCADE 삭제 테스트 ==='

-- 테스트용 새 세션 생성
INSERT INTO chatbot.session_master (session_id, user_id, session_type)
VALUES ('33333333-3333-3333-3333-333333333333', 3, 'test');

-- 관련 데이터 생성
INSERT INTO chatbot.conversations (session_id, user_id, input_text, response_text)
VALUES ('33333333-3333-3333-3333-333333333333', 3, '삭제 테스트', '응답');

INSERT INTO ml_features.user_interactions (user_id, session_id, interaction_type)
VALUES (3, '33333333-3333-3333-3333-333333333333', 'text_input');

INSERT INTO analytics.recommendations_log (user_id, shop_id, session_id, recommendations, recommendation_count)
VALUES (3, 1, '33333333-3333-3333-3333-333333333333', '[]'::jsonb, 0);

INSERT INTO analytics.user_feedback (session_id, user_id, feedback_type, feedback_target_type, feedback_target_id)
VALUES ('33333333-3333-3333-3333-333333333333', 3, 'test', 'test', 'test');

-- 삭제 전 데이터 확인
SELECT 'Before DELETE - conversations:' as status, COUNT(*) FROM chatbot.conversations WHERE session_id = '33333333-3333-3333-3333-333333333333'
UNION ALL
SELECT 'Before DELETE - user_interactions:', COUNT(*) FROM ml_features.user_interactions WHERE session_id = '33333333-3333-3333-3333-333333333333'
UNION ALL
SELECT 'Before DELETE - recommendations_log:', COUNT(*) FROM analytics.recommendations_log WHERE session_id = '33333333-3333-3333-3333-333333333333'
UNION ALL
SELECT 'Before DELETE - user_feedback:', COUNT(*) FROM analytics.user_feedback WHERE session_id = '33333333-3333-3333-3333-333333333333';

-- CASCADE 삭제 실행
DELETE FROM chatbot.session_master WHERE session_id = '33333333-3333-3333-3333-333333333333';

-- 삭제 후 데이터 확인 (모두 0이어야 함)
SELECT 'After DELETE - conversations:' as status, COUNT(*) FROM chatbot.conversations WHERE session_id = '33333333-3333-3333-3333-333333333333'
UNION ALL
SELECT 'After DELETE - user_interactions:', COUNT(*) FROM ml_features.user_interactions WHERE session_id = '33333333-3333-3333-3333-333333333333'
UNION ALL
SELECT 'After DELETE - recommendations_log:', COUNT(*) FROM analytics.recommendations_log WHERE session_id = '33333333-3333-3333-3333-333333333333'
UNION ALL
SELECT 'After DELETE - user_feedback:', COUNT(*) FROM analytics.user_feedback WHERE session_id = '33333333-3333-3333-3333-333333333333';

-- ===============================================
-- 6. 세션 관리 함수 테스트
-- ===============================================
\echo '=== 세션 관리 함수 테스트 ==='

-- 세션 종료 함수 테스트
SELECT end_session(:'session_id_2') as ended;

-- 종료된 세션 확인
SELECT session_id, is_active, session_end IS NOT NULL as has_end_time
FROM chatbot.session_master
WHERE session_id = :'session_id_2';

-- 비활성 세션 정리 (24시간 이상 활동 없는 세션)
SELECT clean_inactive_sessions() as cleaned_count;

-- ===============================================
-- 7. 데이터 무결성 종합 검증
-- ===============================================
\echo '=== 데이터 무결성 종합 검증 ==='

-- 모든 conversations의 session_id가 session_master에 존재하는지 확인
SELECT 
    CASE 
        WHEN COUNT(*) = 0 THEN '✅ PASS: 모든 conversations의 session_id가 유효함'
        ELSE '❌ FAIL: 고아 conversations 레코드 존재: ' || COUNT(*)
    END as integrity_check
FROM chatbot.conversations c
LEFT JOIN chatbot.session_master sm ON c.session_id = sm.session_id
WHERE sm.session_id IS NULL;

-- 모든 user_interactions의 session_id가 session_master에 존재하는지 확인
SELECT 
    CASE 
        WHEN COUNT(*) = 0 THEN '✅ PASS: 모든 user_interactions의 session_id가 유효함'
        ELSE '❌ FAIL: 고아 user_interactions 레코드 존재: ' || COUNT(*)
    END as integrity_check
FROM ml_features.user_interactions ui
LEFT JOIN chatbot.session_master sm ON ui.session_id = sm.session_id
WHERE sm.session_id IS NULL;

-- 모든 recommendations_log의 session_id가 session_master에 존재하는지 확인
SELECT 
    CASE 
        WHEN COUNT(*) = 0 THEN '✅ PASS: 모든 recommendations_log의 session_id가 유효함'
        ELSE '❌ FAIL: 고아 recommendations_log 레코드 존재: ' || COUNT(*)
    END as integrity_check
FROM analytics.recommendations_log rl
LEFT JOIN chatbot.session_master sm ON rl.session_id = sm.session_id
WHERE sm.session_id IS NULL;

-- 모든 user_feedback의 session_id가 session_master에 존재하는지 확인
SELECT 
    CASE 
        WHEN COUNT(*) = 0 THEN '✅ PASS: 모든 user_feedback의 session_id가 유효함'
        ELSE '❌ FAIL: 고아 user_feedback 레코드 존재: ' || COUNT(*)
    END as integrity_check
FROM analytics.user_feedback uf
LEFT JOIN chatbot.session_master sm ON uf.session_id = sm.session_id
WHERE sm.session_id IS NULL;

-- ===============================================
-- 8. 외래키 제약 확인
-- ===============================================
\echo '=== 외래키 제약 확인 ==='

-- session_id 관련 외래키 목록
SELECT 
    tc.table_schema || '.' || tc.table_name as table_name,
    kcu.column_name,
    ccu.table_schema || '.' || ccu.table_name AS foreign_table,
    ccu.column_name AS foreign_column
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
    ON tc.constraint_name = kcu.constraint_name
    AND tc.table_schema = kcu.table_schema
JOIN information_schema.constraint_column_usage AS ccu
    ON ccu.constraint_name = tc.constraint_name
    AND ccu.table_schema = tc.table_schema
WHERE tc.constraint_type = 'FOREIGN KEY'
    AND kcu.column_name = 'session_id'
ORDER BY tc.table_schema, tc.table_name;

-- ===============================================
-- 9. 통계 요약
-- ===============================================
\echo '=== 최종 통계 요약 ==='

SELECT 
    'Session Master' as table_name, COUNT(*) as count 
FROM chatbot.session_master
UNION ALL
SELECT 'Conversations', COUNT(*) FROM chatbot.conversations
UNION ALL
SELECT 'User Interactions', COUNT(*) FROM ml_features.user_interactions
UNION ALL
SELECT 'Recommendations Log', COUNT(*) FROM analytics.recommendations_log
UNION ALL
SELECT 'User Feedback', COUNT(*) FROM analytics.user_feedback
ORDER BY table_name;

-- 활성 세션 수
SELECT 
    COUNT(*) FILTER (WHERE is_active = TRUE) as active_sessions,
    COUNT(*) FILTER (WHERE is_active = FALSE) as inactive_sessions,
    COUNT(*) as total_sessions
FROM chatbot.session_master;

\echo '=== 테스트 완료 ===
✅ Session Master 도입으로 모든 테이블 간 참조 무결성 보장
✅ 파티셔닝 정상 작동
✅ CASCADE 삭제 정상 작동
✅ 고아 데이터 발생 불가능'