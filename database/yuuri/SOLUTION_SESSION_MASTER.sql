-- ===============================================
-- 해결책: Session Master 테이블 도입
-- ===============================================
-- 파티션 테이블의 외래키 문제를 해결하는 실무적 방법

-- 1. Session Master 테이블 생성 (파티션 아님!)
-- ===============================================
CREATE TABLE chatbot.session_master (
    session_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id INT REFERENCES chatbot.users(id) ON DELETE CASCADE,
    session_start TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    session_end TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT TRUE,
    session_metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 인덱스 추가
CREATE INDEX idx_session_master_user ON chatbot.session_master(user_id);
CREATE INDEX idx_session_master_active ON chatbot.session_master(is_active) WHERE is_active = TRUE;
CREATE INDEX idx_session_master_start ON chatbot.session_master(session_start);

-- 2. 기존 conversations 테이블 수정
-- ===============================================
-- 기존 테이블 백업
CREATE TABLE chatbot.conversations_backup AS 
SELECT * FROM chatbot.conversations;

-- 기존 테이블 삭제
DROP TABLE chatbot.conversations CASCADE;

-- 새로운 구조로 재생성
CREATE TABLE chatbot.conversations (
    id BIGINT GENERATED ALWAYS AS IDENTITY,
    session_id UUID NOT NULL REFERENCES chatbot.session_master(session_id) ON DELETE CASCADE,
    user_id INT REFERENCES chatbot.users(id) ON DELETE CASCADE,
    conversation_time TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id, conversation_time),
    
    input_text VARCHAR(1000) NOT NULL,
    response_text VARCHAR(700) NOT NULL,
    
    extracted_intent VARCHAR(50) CHECK (extracted_intent IN (
        'FOOD_REQUEST', 'BUDGET_INQUIRY', 'COUPON_INQUIRY', 
        'LOCATION_INQUIRY', 'TIME_INQUIRY', 'GENERAL_CHAT',
        'MENU_OPTION', 'EMERGENCY_FOOD', 'GROUP_DINING', 
        'BALANCE_CHECK', 'BALANCE_CHARGE', 'UNKNOWN'
    )),
    intent_confidence DECIMAL(4,3) CHECK (intent_confidence >= 0 AND intent_confidence <= 1),
    emotion INT,
    extracted_entities JSONB,
    
    conversation_turn INT NOT NULL DEFAULT 1,
    previous_intent VARCHAR(50), 
    user_strategy VARCHAR(20) CHECK (user_strategy IN ('onboarding_mode', 'data_building_mode', 'normal_mode', 'urgent_mode')),

    processing_time_ms INT,
    nlu_time_ms INT,
    rag_time_ms INT,
    response_time_ms INT,

    response_quality_score DECIMAL(4,3),
    user_satisfaction_inferred DECIMAL(4,3),
    conversation_coherence DECIMAL(4,3),
    
    recommended_shop_ids INT[],
    selected_shop_id INT REFERENCES chatbot.shops(id),
    applied_coupon_ids TEXT[]
) PARTITION BY RANGE (conversation_time);

-- 인덱스 재생성
CREATE INDEX idx_conversations_user_time ON chatbot.conversations(user_id, conversation_time DESC);
CREATE INDEX idx_conversations_session ON chatbot.conversations(session_id);
CREATE INDEX idx_conversations_intent ON chatbot.conversations(extracted_intent);

-- 파티션 재생성
CREATE TABLE chatbot.conversations_2024_08 PARTITION OF chatbot.conversations
  FOR VALUES FROM ('2024-08-01') TO ('2024-09-01');
CREATE TABLE chatbot.conversations_2024_09 PARTITION OF chatbot.conversations
  FOR VALUES FROM ('2024-09-01') TO ('2024-10-01');
CREATE TABLE chatbot.conversations_2024_10 PARTITION OF chatbot.conversations
  FOR VALUES FROM ('2024-10-01') TO ('2024-11-01');
CREATE TABLE chatbot.conversations_2024_11 PARTITION OF chatbot.conversations
  FOR VALUES FROM ('2024-11-01') TO ('2024-12-01');
CREATE TABLE chatbot.conversations_2024_12 PARTITION OF chatbot.conversations
  FOR VALUES FROM ('2024-12-01') TO ('2025-01-01');
CREATE TABLE chatbot.conversations_2025_01 PARTITION OF chatbot.conversations
  FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');
CREATE TABLE chatbot.conversations_2025_02 PARTITION OF chatbot.conversations
  FOR VALUES FROM ('2025-02-01') TO ('2025-03-01');
CREATE TABLE chatbot.conversations_2025_03 PARTITION OF chatbot.conversations
  FOR VALUES FROM ('2025-03-01') TO ('2025-04-01');

-- 3. 다른 테이블들도 session_master 참조하도록 수정
-- ===============================================

-- ml_features.user_interactions 수정
ALTER TABLE ml_features.user_interactions 
ADD CONSTRAINT user_interactions_session_fkey 
FOREIGN KEY (session_id) REFERENCES chatbot.session_master(session_id) ON DELETE CASCADE;

-- analytics.recommendations_log 수정
ALTER TABLE analytics.recommendations_log 
ADD CONSTRAINT recommendations_log_session_fkey 
FOREIGN KEY (session_id) REFERENCES chatbot.session_master(session_id) ON DELETE CASCADE;

-- analytics.user_feedback 수정
ALTER TABLE analytics.user_feedback 
ADD CONSTRAINT user_feedback_session_fkey 
FOREIGN KEY (session_id) REFERENCES chatbot.session_master(session_id) ON DELETE CASCADE;

-- 4. 기존 데이터 마이그레이션
-- ===============================================

-- session_master에 기존 세션 데이터 추가
INSERT INTO chatbot.session_master (session_id, user_id, session_start)
SELECT DISTINCT 
    session_id, 
    user_id,
    MIN(conversation_time) as session_start
FROM chatbot.conversations_backup
GROUP BY session_id, user_id;

-- conversations 테이블에 데이터 복원
INSERT INTO chatbot.conversations 
SELECT * FROM chatbot.conversations_backup;

-- 5. 데이터 정합성 검증
-- ===============================================

-- 고아 데이터 확인 (이제는 불가능해야 함)
SELECT COUNT(*) as orphan_count
FROM ml_features.user_interactions ui
LEFT JOIN chatbot.session_master sm ON ui.session_id = sm.session_id
WHERE sm.session_id IS NULL;

-- 6. 사용 예시: 새로운 대화 시작
-- ===============================================

-- 트랜잭션으로 묶어서 처리
BEGIN;

-- 1) 세션 시작
INSERT INTO chatbot.session_master (user_id, session_metadata)
VALUES (1, '{"device": "mobile", "location": "seoul"}'::jsonb)
RETURNING session_id;

-- 2) 대화 기록 (위에서 받은 session_id 사용)
INSERT INTO chatbot.conversations (
    session_id, 
    user_id, 
    input_text, 
    response_text,
    extracted_intent
) VALUES (
    'returned-session-id', 
    1, 
    '오늘 점심 뭐 먹을까?', 
    '김밥천국 어떠세요?',
    'FOOD_REQUEST'
);

-- 3) 관련 분석 데이터
INSERT INTO ml_features.user_interactions (
    user_id,
    session_id,
    interaction_type,
    food_preference_extracted
) VALUES (
    1,
    'returned-session-id',
    'text_input',
    '한식'
);

COMMIT;

-- 7. 세션 종료 처리
-- ===============================================
UPDATE chatbot.session_master 
SET 
    session_end = CURRENT_TIMESTAMP,
    is_active = FALSE
WHERE session_id = 'some-session-id';

-- 8. CASCADE 삭제 테스트
-- ===============================================
-- session_master에서 삭제하면 모든 연관 데이터 자동 삭제
DELETE FROM chatbot.session_master 
WHERE session_id = 'test-session-id';
-- conversations, user_interactions, recommendations_log 등 모두 자동 삭제됨

-- 9. 정리 함수
-- ===============================================

-- 오래된 세션 정리 (30일 이상)
CREATE OR REPLACE FUNCTION clean_old_sessions()
RETURNS void AS $$
BEGIN
    DELETE FROM chatbot.session_master
    WHERE session_end < CURRENT_TIMESTAMP - INTERVAL '30 days'
    AND is_active = FALSE;
END;
$$ LANGUAGE plpgsql;

-- 비정상 종료 세션 정리 (24시간 이상 활동 없음)
CREATE OR REPLACE FUNCTION clean_inactive_sessions()
RETURNS void AS $$
BEGIN
    UPDATE chatbot.session_master sm
    SET is_active = FALSE, session_end = CURRENT_TIMESTAMP
    WHERE is_active = TRUE
    AND NOT EXISTS (
        SELECT 1 FROM chatbot.conversations c
        WHERE c.session_id = sm.session_id
        AND c.conversation_time > CURRENT_TIMESTAMP - INTERVAL '24 hours'
    );
END;
$$ LANGUAGE plpgsql;