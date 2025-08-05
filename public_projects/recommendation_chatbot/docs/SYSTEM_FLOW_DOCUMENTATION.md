# 나비얌 챗봇 시스템 플로우 상세 문서

## 목차
1. [시스템 개요](#1-시스템-개요)
2. [데이터 저장 정책 및 타입](#2-데이터-저장-정책-및-타입)
3. [핵심 비즈니스 플로우](#3-핵심-비즈니스-플로우)
4. [데이터 처리 플로우](#4-데이터-처리-플로우)
5. [AI/ML 파이프라인 플로우](#5-aiml-파이프라인-플로우)
6. [실시간 처리 플로우](#6-실시간-처리-플로우)
7. [배치 처리 플로우](#7-배치-처리-플로우)
8. [장애 처리 및 복구 플로우](#8-장애-처리-및-복구-플로우)

---

## 1. 시스템 개요

### 1.1 시스템 목표
나비얌 챗봇은 급식카드 사용자를 위한 AI 기반 맛집 추천 서비스로, 다음 목표를 달성합니다:

1. **응답 시간**: 95%의 요청을 2초 이내 처리
2. **정확도**: NLU 의도 분류 정확도 90% 이상
3. **개인화**: 10회 이상 사용자에게 80% 이상 개인화된 추천
4. **가용성**: 99.9% 이상의 서비스 가용성

**핵심**: 추천에만 집중합니다. 결제/거래는 외부 시스템의 역할입니다.

### 1.2 시스템 구성 요소

#### 프론트엔드 계층

#### 백엔드 계층
#### AI/ML 계층
- **NLU 엔진**: SKT A.X 3.1 Lite
- **추천 엔진**: Wide&Deep TensorFlow
- **RAG 시스템**: Sentence-BERT + FAISS

#### 데이터 계층
- **주 데이터베이스**: PostgreSQL 15
- **캐시**: Redis 7.0
- **벡터 DB**: FAISS
- **메시지 큐**: RabbitMQ
- **객체 스토리지**: MinIO/S3

### 1.3 시스템 특성

#### 확장성 (Scalability)
- 수평 확장 가능한 마이크로서비스 아키텍처
- 독립적인 서비스 배포 및 스케일링
- 로드 밸런서를 통한 트래픽 분산

#### 신뢰성 (Reliability)
- 서킷 브레이커 패턴 구현
- 재시도 및 백오프 전략
- 우아한 성능 저하 (Graceful Degradation)

---

## 2. 데이터 저장 정책 및 타입

### 2.1 챗봇이 생성하는 모든 데이터 분류

#### 💾 DB에 반드시 저장하는 데이터

| 데이터 카테고리 | 데이터 예시 | 저장 테이블 | 데이터 타입 | 저장 이유 |
|--------------|------------|------------|-----------|----------|
| **사용자 입력** | "치킨 먹고 싶어" | conversations | input_text: TEXT | 학습 데이터, 감사 로그 |
| **챗봇 응답** | "치킨 추천드려요!" | conversations | response_text: TEXT | 품질 추적, A/B 테스트 |
| **NLU 추출 결과** | intent: FOOD_REQUEST | conversations | extracted_intent: VARCHAR(50)<br>extracted_entities: JSONB | 모델 개선 |
| **추천 결과** | [가게1, 가게2] | recommendations_log | recommendations: JSONB | 성과 분석 |
| **사용자 선택** | 가게1 선택 | recommendations_log | user_final_selection: INTEGER | 선호도 학습 |
| **성능 메트릭** | 처리시간 245ms | performance_logs | processing_time_ms: INTEGER | 성능 최적화 |
| **사용자 프로필** | 치킨 선호 | user_profiles | preferred_categories: JSONB | 개인화 |
| **급식카드 잔액** | 5000원 | foodcard_users | balance: INTEGER<br>last_sync_at: TIMESTAMP | 예산 내 추천 (읽기 전용) |
| **세션 컨텍스트** | 이전 대화 내용 | conversation_contexts | context_data: JSONB | 대화 연속성 |
| **학습 데이터** | NLU 학습용 | nlu_training_data | input_text: TEXT<br>true_intent: VARCHAR(50) | 모델 재학습 |
| **특징 벡터** | 사용자/가게 특징 | feature_vectors | feature_vector_dense: JSONB | ML 훈련 |

#### 📝 임시 저장 후 필요시 DB 저장

| 데이터 카테고리 | 초기 저장 | DB 저장 조건 | TTL |
|--------------|----------|--------------|-----|
| **임베딩 벡터** | Redis | 자주 사용되는 경우 | 7일 |
| **RAG 검색 결과** | Redis | 인기 쿼리인 경우 | 1시간 |
| **실시간 추천 점수** | 메모리 | 세션 종료 시 집계 | 세션 |
| **중간 계산 결과** | Redis | 최종 결과만 DB | 5분 |

#### ❌ 절대 DB에 저장하지 않는 데이터

| 데이터 카테고리 | 이유 | 대체 방안 |
|--------------|------|----------|
| **비밀번호** | 보안 위험 | bcrypt 해시만 저장 |
| **결제 카드 정보** | PCI DSS | 토큰화/외부 서비스 |
| **민감 개인정보** | GDPR/개인정보보호법 | 암호화/가명화 |
| **임시 토큰** | 보안 | 메모리만 |
| **디버그 로그** | 개발용 | 로그 파일만 |
| **모델 가중치** | 용량 | S3/파일 시스템 |

### 2.2 데이터 타입 사용 가이드

#### 텍스트 데이터
```sql
-- 고정 길이 문자열 (최대 길이 예측 가능)
user_id VARCHAR(100)         -- 최대 100자
intent VARCHAR(50)           -- 최대 50자
status VARCHAR(20)           -- 최대 20자

-- 가변 길이 텍스트 (긴 문자열)
input_text TEXT              -- 사용자 입력 (무제한)
response_text TEXT           -- 챗봇 응답 (무제한)
description TEXT             -- 설명 필드

-- JSON 데이터 (구조화된 데이터)
extracted_entities JSONB     -- {"food_type": "치킨", "budget": 5000}
recommendations JSONB        -- [{"shop_id": 1, "score": 0.95}]
context_data JSONB          -- 복잡한 구조체
```

#### 숫자 데이터
```sql
-- 정수 (32비트)
shop_id INTEGER              -- -2,147,483,648 ~ 2,147,483,647
price INTEGER                -- 가격, 금액
processing_time_ms INTEGER   -- 밀리초 단위 시간

-- 큰 정수 (64비트)  
id BIGSERIAL                 -- 자동 증가, 큰 테이블
user_interaction_id BIGINT   -- 대량 로그 테이블

-- 소수 (고정 소수점)
confidence DECIMAL(4,3)      -- 0.000 ~ 1.000 (신뢰도, 확률)
score DECIMAL(6,4)           -- 0.0000 ~ 99.9999 (점수)
amount DECIMAL(10,2)         -- 금액 (억 단위까지)
```

#### 시간 데이터
```sql
-- 날짜만
birth_date DATE              -- 'YYYY-MM-DD'
valid_until DATE            -- 유효기간

-- 시간만
open_hour TIME              -- 'HH:MM:SS'
processing_duration INTERVAL -- '2 hours 30 minutes'

-- 타임스탬프 (시간대 포함)
created_at TIMESTAMP WITH TIME ZONE      -- '2024-01-15 14:30:00+09'
last_accessed TIMESTAMP WITH TIME ZONE   -- UTC 변환 자동
```

#### 배열 데이터
```sql
-- 단순 배열
categories TEXT[]            -- ['한식', '중식', '일식']
shop_ids INTEGER[]          -- [1, 5, 10, 23]

-- 복합 배열 (사용 지양, JSONB 사용)
options JSONB               -- 대신 JSONB 사용 권장
```

### 2.3 데이터 저장 시 체크리스트

#### 저장 전 확인사항
- [ ] 개인정보 포함 여부 확인
- [ ] 데이터 타입 적절성 검토
- [ ] NULL 허용 여부 결정
- [ ] 인덱스 필요성 검토
- [ ] 파티셔닝 필요성 검토

#### 저장 후 확인사항
- [ ] 데이터 무결성 검증
- [ ] 트리거 작동 확인
- [ ] 캐시 무효화 수행
- [ ] 백업 정상 작동

---

## 3. 핵심 비즈니스 플로우

### 3.1 사용자 대화 처리 플로우

#### 2.1.1 대화 시작
```
[단계 1] 사용자 인증 및 세션 생성
시작: 사용자가 챗봇에 접속
↓
1.1 플랫폼 식별 (웹/앱/메신저)
1.2 사용자 인증 토큰 검증
    - JWT 토큰 유효성 검증
    - 토큰 만료 시간 확인
    - Refresh token 자동 갱신
1.3 세션 생성 또는 복원
    - 신규 세션: UUID 생성
    - 기존 세션: Redis에서 컨텍스트 로드
1.4 사용자 프로필 로드
    - 기본 정보: users 테이블
    - 급식카드 정보: foodcard_users 테이블
    - 선호도: user_profiles 테이블
↓
결과: 인증된 세션 컨텍스트 생성
```

#### 2.1.2 메시지 처리
```
[단계 2] 사용자 입력 처리
시작: "5천원으로 점심 먹을만한 곳 추천해줘"
↓
2.1 입력 검증 및 전처리
    - XSS/SQL Injection 방어
    - 텍스트 길이 검증 (최대 500자)
    - 유니코드 정규화
    - 이모지 처리
    
2.2 언어 감지 및 처리
    - 한국어/영어 감지
    - 비속어 필터링
    - 오타 교정 (선택적)
    
2.3 컨텍스트 병합
    - 이전 대화 내용 (최근 10턴)
    - 시간대 정보 (아침/점심/저녁)
    - 위치 정보 (GPS 또는 주소)
    - 날씨 정보 (선택적)
↓
결과: 정규화된 입력 + 풍부한 컨텍스트
```

#### 2.1.3 의도 분류 및 엔티티 추출
```
[단계 3] NLU 처리
시작: 전처리된 텍스트와 컨텍스트
↓
3.1 토큰화 및 임베딩
    - Mecab 형태소 분석
    - WordPiece 토큰화
    - 위치 인코딩 추가
    
3.2 의도 분류 (Intent Classification)
    - 모델: Fine-tuned A.X 3.1 Lite
    - 입력: [CLS] + 토큰 + [SEP] + 컨텍스트
    - 출력: Softmax 확률 분포
    - 임계값: 0.7 이상만 채택
    
3.3 엔티티 추출 (Entity Extraction)
    - 규칙 기반:
        * 금액: 정규식 /\d+[천만]?원/
        * 시간: "점심", "저녁" 등 키워드
    - ML 기반:
        * 음식 종류: NER 모델
        * 감정/긴급도: 감성 분석
        
3.4 신뢰도 평가
    - 의도 신뢰도 < 0.7: 재질문 생성
    - 엔티티 모호성: 명확화 요청
↓
결과: {intent: "BUDGET_INQUIRY", entities: {budget: 5000, meal_time: "lunch"}, confidence: 0.92}
```

#### 2.1.4 추천 생성
```
[단계 4] 추천 후보 생성 및 순위 결정
시작: NLU 결과 + 사용자 프로필
↓
4.1 필터링 조건 생성
    - Hard Filters:
        * 예산: menus.price <= 5000
        * 영업: shops.current_status = 'OPEN'
        * 거리: ST_Distance(location) <= 1000m
        * 급식카드: is_food_card_shop IN ('Y', 'P')
    - Soft Filters:
        * 선호 카테고리 우선
        * 이전 방문 이력 고려
        
4.2 후보 검색 (Multi-Source)
    - DB 쿼리: PostgreSQL FTS + PostGIS
    - 벡터 검색: FAISS 시맨틱 매칭
    - 캐시 조회: Redis 인기 가게
    
4.3 특징 추출 (Feature Engineering)
    - User Features (32차원):
        * 카테고리 선호도 벡터
        * 평균 예산 정규화
        * 시간대별 패턴
        * 급식카드 잔액 상태
    - Shop Features (24차원):
        * 인기도 점수
        * 리뷰 평점
        * 가격 적합도
        * 급식카드 사용 가능 여부
    - Cross Features (16차원):
        * User-Shop 친화도
        * 시간-메뉴 적합성
        * 예산-가격 매칭도
        
4.4 Wide&Deep 스코어링
    - Wide: 범주형 특징의 선형 결합
    - Deep: 3층 신경망 (128→64→32→1)
    - 최종 점수: Sigmoid(Wide + Deep)
    - 급식카드 사용 가능 시 추가 점수 +0.2
↓
결과: [(shop_id: 15, score: 0.92), (shop_id: 23, score: 0.87), ...]
```

#### 2.1.5 응답 생성
```
[단계 5] 자연어 응답 생성
시작: 정렬된 추천 목록
↓
5.1 추천 다양성 보장
    - MMR(Maximal Marginal Relevance) 적용
    - 카테고리 다양성 체크
    - 가격대 분산
    
5.2 쿠폰 매칭
    - 사용 가능 쿠폰 조회
    - 최적 할인 조합 계산
    - 최종 가격 재계산
    
5.3 템플릿 선택
    - 상황별 템플릿 풀
    - 개인화 요소 삽입
    - 어투 일관성 유지
    
5.4 추가 정보 포함
    - 영업시간 및 브레이크타임
    - 도보 시간 (거리 ÷ 80m/분)
    - 인기 메뉴 Top 3
    - 급식카드 사용 가능 여부
    
5.5 응답 후처리
    - 문법 검사
    - 이모지 추가 (선택적)
    - 길이 조절 (최대 500자)
↓
결과: "5천원으로 맛있는 점심 드실 수 있는 곳 추천드려요! 🍱\n1. 김밥천국 (도보 5분)..."
```

### 3.2 급식카드 특화 플로우

#### 2.2.1 잔액 관리 플로우
```
[단계 1] 실시간 잔액 확인
시작: 추천 요청 시 자동 확인
↓
1.1 현재 잔액 조회
    SELECT balance, daily_limit, monthly_limit 
    FROM foodcard_users 
    WHERE user_id = ? AND status = 'ACTIVE'
    
1.2 사용 가능액 계산
    - 일일 한도 확인
    - 월 한도 확인
    - 실제 사용 가능액 = MIN(잔액, 일일한도, 월한도)
    
1.3 잔액 부족 감지
    IF 사용가능액 < 5000:
        - 긴급 지원 자격 확인
        - 알림 발송 여부 확인
↓
결과: 실제 사용 가능한 예산 확정
```

#### 2.2.2 저잔액 알림 플로우
```
[단계 2] 저잔액 알림 및 예산 내 추천
시작: 잔액 < 5000원 감지
↓
2.1 알림 조건 확인
    - balance < balance_alert_threshold
    - balance_alert_sent = FALSE
    - 마지막 알림으로부터 24시간 경과
    
2.2 저잔액 알림
    - 메시지: "급식카드 잔액이 {balance}원 남았습니다"
    - 충전 안내 메시지 포함
    
2.3 추천 조정
    - 잔액 내 메뉴만 필터링
    - 저렴한 메뉴 우선 추천
    - "잘 생각해보면 {price}원으로도 맛있게 드실 수 있어요!"
    
2.4 상태 업데이트
    UPDATE foodcard_users 
    SET balance_alert_sent = TRUE
    WHERE user_id = ?
↓
결과: 사용자에게 저잔액 알림 및 예산 내 맛집 추천
```

### 3.3 개인화 진화 플로우

#### 2.3.1 온보딩 플로우 (1-3회차)
```
[단계 1] 신규 사용자 감지 및 데이터 수집
시작: interaction_count < 3
↓
1.1 환영 및 안내
    "안녕하세요! 맛있는 추천을 위해 몇 가지 여쭤볼게요 😊"
    
1.2 선호도 수집 대화
    Q1: "평소 어떤 음식을 좋아하시나요?"
    → 카테고리 선호도 초기화
    
    Q2: "보통 한 끼에 얼마정도 쓰시나요?"
    → 예산 범위 설정
    
    Q3: "못 드시는 음식이나 알레르기가 있나요?"
    → 제약사항 기록
    
1.3 초기 프로필 생성
    INSERT INTO user_profiles (
        user_id, preferred_categories, average_budget,
        dietary_restrictions, personality_type
    ) VALUES (?, ?, ?, ?, 'EXPLORER')
↓
결과: 기본 개인화 프로필 생성
```

#### 2.3.2 프로필 강화 플로우 (4-10회차)
```
[단계 2] 패턴 학습 및 프로필 정교화
시작: 4 <= interaction_count <= 10
↓
2.1 행동 패턴 분석
    - 시간대별 주문 패턴
    - 요일별 선호 변화
    - 날씨별 메뉴 선택
    
2.2 선호도 가중치 조정
    - 명시적 피드백: weight = 1.0
    - 선택 행동: weight = 0.8  
    - 조회만: weight = 0.3
    
2.3 성격 유형 판별
    IF 다양한 카테고리 시도: personality = 'EXPLORER'
    ELIF 같은 가게 반복: personality = 'LOYALIST'
    ELIF 할인 쿠폰 선호: personality = 'DEAL_SEEKER'
    ELSE: personality = 'BALANCED'
↓
결과: 정교화된 개인화 프로필
```

#### 2.3.3 고급 개인화 플로우 (10회차 이상)
```
[단계 3] 예측 모델 활성화
시작: interaction_count > 10
↓
3.1 다차원 선호도 모델링
    - 시간 × 카테고리 매트릭스
    - 동반자 × 예산 매트릭스
    - 날씨 × 메뉴 상관관계
    
3.2 다음 주문 예측
    - LSTM 기반 시퀀스 예측
    - 입력: 최근 20개 주문 이력
    - 출력: 다음 주문 확률 분포
    
3.3 이상 탐지 및 알림
    - 평소와 다른 패턴 감지
    - 예산 초과 경향 경고
    - 영양 불균형 조언
↓
결과: 완전 개인화된 예측적 추천
```

---

## 4. 데이터 처리 플로우

### 4.1 실시간 데이터 스트림 처리

#### 3.1.1 이벤트 수집 플로우
```
[이벤트 소스]
- 사용자 입력 이벤트
- 클릭/스크롤 이벤트  
- 시스템 상태 변경
- 외부 API 응답

↓ [이벤트 버스: Apache Kafka]

[Topic 구조]
- user.interactions: 사용자 상호작용
- system.performance: 성능 메트릭
- shop.updates: 가게 정보 변경
- order.events: 주문 관련 이벤트

↓ [스트림 프로세싱: Kafka Streams]

[처리 로직]
1. 필터링: 유효한 이벤트만 통과
2. 변환: 정규화 및 보강
3. 집계: 시간 윈도우별 집계
4. 조인: 여러 스트림 결합

↓ [저장 및 액션]

[실시간 저장]
- Redis: 핫 데이터 (TTL 설정)
- PostgreSQL: 영구 저장
- Elasticsearch: 검색용 인덱싱

[실시간 액션]
- 알림 발송
- 캐시 무효화
- 모델 업데이트 트리거
```

#### 3.1.2 실시간 집계 플로우
```
[5분 윈도우 집계]
시작: 매 5분마다
↓
1. 인기도 점수 업데이트
   - 최근 5분간 조회수 (40%)
   - 최근 5분간 선택률 (40%)
   - 평균 평점 (20%)
   - 지수 이동 평균 적용
   UPDATE shops SET 
     popularity_score = 0.7 * popularity_score + 0.3 * new_score
   WHERE updated_at < NOW() - INTERVAL '5 minutes'
   
2. 실시간 재고 상태
   - 품절 메뉴 감지
   - 자동 상태 변경
   
3. 트래픽 패턴 분석
   - 피크 시간 감지
   - 자동 스케일링 트리거

[1시간 윈도우 집계]
- 시간대별 통계
- 캐시 히트율 계산
- 에러율 모니터링

3. 급식카드 잔액 동기화
   - 5분마다 외부 API 호출
   - 변경된 잔액만 업데이트
   ```sql
   UPDATE foodcard_users 
   SET balance = ?, last_sync_at = NOW()
   WHERE user_id = ? AND balance != ?
   ```
```

### 4.2 벡터 검색 플로우

#### 3.2.1 임베딩 생성 플로우
```
[텍스트 → 벡터 변환]
시작: 새로운 텍스트 입력
↓
1. 텍스트 전처리
   - HTML 태그 제거
   - 특수문자 정규화
   - 최대 512 토큰 제한
   
2. 임베딩 캐시 확인
   cache_key = SHA256(normalized_text)
   cached = cache.get(query, filters)  # 실제 코드의 QueryCache 클래스 사용
   
3. 임베딩 생성 (캐시 미스)
   - 모델: sentence-transformers/xlm-r-100langs-bert
   - 차원: 768
   - 정규화: L2 norm = 1
   
4. 캐시 저장
   cache.set(query, result, filters)  # 실제 코드의 QueryCache.set 메소드 사용
   
5. DB 저장 (배치)
   - 5분마다 배치 처리
   - 중복 제거
   - 압축 저장
```

#### 3.2.2 유사도 검색 플로우
```
[벡터 검색 실행]
시작: 쿼리 벡터 준비됨
↓
1. FAISS 인덱스 선택
   - shops_index: 가게 설명
   - menus_index: 메뉴 설명
   - reviews_index: 리뷰 텍스트
   
2. 검색 파라미터 설정
   - k: 100 (초기 후보)
   - nprobe: 32 (정확도)
   
3. 다단계 검색
   Stage 1: Coarse quantizer
   - IVF 클러스터 선택
   - 상위 32개 클러스터
   
   Stage 2: Fine search
   - PQ 코드 거리 계산
   - 상위 100개 선택
   
   Stage 3: Reranking
   - 원본 벡터로 재계산
   - 최종 20개 선택
   
4. 후처리
   - 거리 → 유사도 변환
   - 메타데이터 조인
   - 필터 조건 적용
```

### 4.3 트랜잭션 처리 플로우

#### 3.3.1 추천 선택 트랜잭션 플로우
```
[추천 선택 기록 ACID 보장]
시작: 사용자가 최종 선택
↓
BEGIN TRANSACTION;

1. 추천 선택 기록
   UPDATE recommendations_log 
   SET user_final_selection = ?, 
       time_to_decision_ms = ?,
       selected_at = NOW()
   WHERE user_id = ? AND session_id = ?;
   
2. 가게 추천 횟수 업데이트
   UPDATE shops 
   SET recommendation_count = recommendation_count + 1
   WHERE id = ?;
   
3. 사용자 프로필 업데이트
   -- 선호 카테고리 강화
   UPDATE user_profiles
   SET interaction_count = interaction_count + 1,
       last_category_selected = ?
   WHERE user_id = ?;
   
4. 급식카드 잔액 확인 (읽기 전용)
   SELECT balance FROM foodcard_users
   WHERE user_id = ? AND status = 'ACTIVE';
   
   -- 잔액 부족 시 알림만 발송
   -- 실제 결제는 외부 시스템에서 처리
   
5. 인기도 점수 계산 트리거
   -- 5분 후 배치로 처리됨
   
COMMIT;

6. 후속 처리 (트랜잭션 외부)
   - 캐시 무효화
   - 로그 기록
   - 학습 데이터 큐잉
```

---

## 5. AI/ML 파이프라인 플로우

### 5.1 모델 서빙 플로우

#### 4.1.1 모델 로딩 및 웜업
```
[서비스 시작 시]
1. 모델 체크포인트 확인
   - S3에서 최신 버전 확인
   - 로컬 캐시와 비교
   - 필요시 다운로드
   
2. 모델 로딩
   - SKT A.X 3.1 Lite: 4bit 양자화 버전
   - Wide&Deep: TensorFlow SavedModel
   - Sentence-BERT: ONNX 형식
   
3. 웜업 요청
   - 각 모델에 더미 입력
   - JIT 컴파일 트리거
   - 메모리 사전 할당
   
4. 헬스체크
   - 응답 시간 측정
   - 메모리 사용량 확인
   - 준비 상태 보고
```

#### 4.1.2 추론 요청 처리
```
[모델 추론 파이프라인]
시작: API 요청 수신
↓
1. 요청 큐잉
   - Priority Queue 사용
   - 긴급 요청 우선 처리
   - 배치 크기: 8
   
2. 전처리
   - 토큰화 (병렬 처리)
   - 패딩/트런케이션
   - 어텐션 마스크 생성
   
3. 추론 실행
   - GPU 배치 처리
   - Mixed precision (FP16)
   - Dynamic batching
   
4. 후처리
   - Softmax/Sigmoid 적용
   - 임계값 필터링
   - 결과 디코딩
   
5. 응답 캐싱
   - 결과 캐싱 (TTL 300초)
   - 메트릭 기록
```

### 5.2 학습 파이프라인 플로우

#### 4.2.1 데이터 수집 및 전처리
```
[학습 데이터 준비]
매일 02:00 시작
↓
1. 데이터 추출
   - 전일 대화 로그
   - 사용자 피드백
   - 선택/미선택 결과
   
2. 데이터 검증
   - 품질 점수 > 0.7
   - 개인정보 마스킹
   - 이상치 제거
   
3. 레이블링
   - 자동 레이블: 규칙 기반
   - 수동 검토: 애매한 케이스
   - 능동 학습: 불확실한 샘플
   
4. 증강 (Augmentation)
   - 동의어 치환
   - 문장 순서 변경
   - 노이즈 추가
   
5. 분할
   - Train: 80%
   - Validation: 10%
   - Test: 10%
```

#### 4.2.2 LoRA 파인튜닝 플로우
```
[LoRA 학습 프로세스]
주 1회 실행
↓
1. 베이스 모델 준비
   - SKT A.X 3.1 Lite
   - 4bit 양자화 버전
   - LoRA 설정:
     * r=16 (rank)
     * alpha=32
     * dropout=0.05
     
2. 학습 설정
   - Learning rate: 2e-4
   - Batch size: 4
   - Gradient accumulation: 4
   - Epochs: 3
   
3. 학습 실행
   for epoch in range(3):
     for batch in dataloader:
       # Forward pass
       outputs = model(batch)
       loss = compute_loss(outputs, labels)
       
       # Backward pass
       loss.backward()
       
       # Gradient clipping
       clip_grad_norm_(model.parameters(), 1.0)
       
       # Optimizer step
       if step % grad_accum == 0:
         optimizer.step()
         optimizer.zero_grad()
       
       # Logging
       wandb.log({"loss": loss, "lr": scheduler.get_lr()})
       
4. 검증 및 평가
   - Validation loss 모니터링
   - Early stopping
   - Best checkpoint 저장
   
5. A/B 테스트 배포
   - 10% 트래픽 할당
   - 성능 지표 비교
   - 점진적 롤아웃
```

### 5.3 특징 엔지니어링 플로우

#### 4.3.1 실시간 특징 계산
```
[온라인 특징 생성]
요청마다 실행
↓
1. 사용자 컨텍스트 특징
   - 현재 시간 인코딩
   - 요일 원-핫 인코딩
   - 날씨 상태 벡터
   - 위치 그리드 인덱스
   
2. 상호작용 특징
   - 최근 N개 조회 이력
   - 시간 간격 통계
   - 카테고리 전환 패턴
   - 스크롤 깊이
   
3. 실시간 집계 특징
   - 5분간 인기도
   - 현재 대기 시간
   - 실시간 재고 상태
```

#### 4.3.2 배치 특징 계산
```
[오프라인 특징 생성]
매 시간 실행
↓
1. 사용자 장기 특징
   - 30일 이동 평균
   - 선호도 엔트로피
   - 생애 가치 (LTV)
   - 이탈 확률
   
2. 가게 통계 특징
   - 시간대별 매출
   - 재방문율
   - 평균 주문 금액
   - 리뷰 감성 점수
   
3. 협업 필터링 특징
   - User-Item 매트릭스
   - SVD 잠재 요인
   - 유사 사용자 클러스터
   
4. 그래프 특징
   - 사용자-가게 네트워크
   - PageRank 점수
   - 커뮤니티 탐지
```

---

## 6. 실시간 처리 플로우

### 6.1 웹소켓 통신 플로우

#### 5.1.1 연결 관리
```
[WebSocket 생명주기]
1. 연결 수립
   Client → WS://api.naviyam.com/ws
   → 핸드셰이크
   → JWT 검증
   → 세션 등록
   
2. 하트비트
   - 30초마다 PING
   - PONG 응답 확인
   - 타임아웃: 60초
   
3. 메시지 처리
   수신 → 검증 → 라우팅 → 처리 → 응답
   
4. 연결 종료
   - 정상 종료: Close frame
   - 비정상 종료: 타임아웃
   - 재연결: 지수 백오프
```

#### 5.1.2 실시간 알림 플로우
```
[푸시 알림 시스템]
이벤트 발생 → 알림 생성 → 전송
↓
1. 알림 트리거
   - 잔액 부족 감지
   - 쿠폰 만료 임박
   - 추천 가게 할인
   
2. 알림 생성
   - 템플릿 선택
   - 개인화 변수 치환
   - 다국어 처리
   
3. 채널별 전송
   - FCM: Android/iOS
   - Web Push: 브라우저
   - 카카오 알림톡
   
4. 전송 추적
   - 전송 성공/실패
   - 열람 여부
   - 클릭 액션
```

### 6.2 캐시 관리 플로우

#### 5.2.1 캐시 계층 구조
```
[멀티 레벨 캐시]
L1: Application Memory (1ms)
  ├─ 자주 사용하는 설정값
  ├─ 인기 가게 Top 100
  └─ 활성 세션 정보
  
L2: Redis Cluster (10ms)
  ├─ 사용자 프로필
  ├─ 임베딩 벡터
  ├─ API 응답 캐시
  └─ 세션 컨텍스트
  
L3: CDN Edge (50ms)
  ├─ 정적 리소스
  ├─ 이미지/썸네일
  └─ 자주 변하지 않는 데이터
```

#### 5.2.2 캐시 무효화 전략
```
[캐시 일관성 유지]
1. TTL 기반
   - 짧은 TTL: 실시간 데이터 (60초)
   - 중간 TTL: 사용자 데이터 (5분)
   - 긴 TTL: 정적 데이터 (1시간)
   
2. 이벤트 기반
   - 데이터 변경 시 즉시 무효화
   - Pub/Sub 패턴 사용
   - 관련 캐시 연쇄 무효화
   
3. 버전 기반
   - 캐시 키에 버전 포함
   - 배포 시 버전 증가
   - 점진적 마이그레이션
```

### 6.3 모니터링 플로우

#### 5.3.1 메트릭 수집
```
[실시간 모니터링]
매 초마다 수집
↓
1. 애플리케이션 메트릭
   - 요청 처리 시간
   - 에러율
   - 처리량 (TPS)
   - 동시 접속자 수
   
2. 인프라 메트릭
   - CPU/메모리 사용률
   - 디스크 I/O
   - 네트워크 대역폭
   - JVM 힙 사용량
   
3. 비즈니스 메트릭
   - 추천 클릭률
   - 전환율
   - 평균 주문 금액
   - 사용자 만족도
```

#### 5.3.2 알람 및 대응
```
[장애 감지 및 대응]
1. 임계값 기반 알람
   - P1: 서비스 다운 (즉시)
   - P2: 성능 저하 (5분)
   - P3: 경고 수준 (30분)
   
2. 이상 탐지
   - 시계열 예측 모델
   - 정상 범위 벗어남 감지
   - 계절성 고려
   
3. 자동 대응
   - 자동 스케일링
   - 서킷 브레이커 작동
   - 트래픽 우회
   - 장애 격리
```

---

## 7. 배치 처리 플로우

### 7.1 일일 배치 작업

#### 6.1.1 데이터 집계 배치
```
[Daily Aggregation - 02:00 AM]
1. 일일 통계 계산
   - 가게별 매출 집계
   - 사용자별 활동 요약
   - 카테고리별 트렌드
   
   INSERT INTO daily_stats
   SELECT 
     date_trunc('day', created_at) as date,
     shop_id,
     COUNT(*) as order_count,
     SUM(amount) as total_revenue,
     AVG(amount) as avg_order_value
   FROM orders
   WHERE created_at >= CURRENT_DATE - INTERVAL '1 day'
   GROUP BY date, shop_id;
   
2. 인기도 재계산
   - 전일 데이터 기반
   - 가중 평균 적용
   - 시간 감쇠 팩터
   
3. 사용자 세그먼트 갱신
   - RFM 분석
   - 클러스터링 재실행
   - 세그먼트 이동 추적
```

#### 6.1.2 데이터 정리 배치
```
[Data Cleanup - 03:00 AM]
1. 로그 아카이빙
   - 7일 이상 로그 → S3
   - 압축 및 암호화
   - 로컬 삭제
   
2. 임시 데이터 정리
   - 만료된 세션
   - 사용된 쿠폰
   - 오래된 캐시
   
3. 인덱스 재구성
   - 단편화된 인덱스 재구성
   - 통계 업데이트
   - 쿼리 플랜 캐시 정리
```

### 7.2 주간 배치 작업

#### 6.2.1 모델 재학습
```
[Weekly Model Training - Sunday 00:00]
1. 학습 데이터 준비
   - 지난 주 상호작용 로그
   - 피드백 데이터 수집
   - 품질 검증
   
2. 특징 재계산
   - 사용자 임베딩 갱신
   - 아이템 임베딩 갱신
   - 상호작용 행렬 재구성
   
3. 모델 학습
   - Wide&Deep 재학습
   - 하이퍼파라미터 튜닝
   - 교차 검증
   
4. A/B 테스트 설정
   - 새 모델 배포
   - 트래픽 분할 설정
   - 성능 모니터링 시작
```

#### 6.2.2 리포트 생성
```
[Weekly Reports - Monday 06:00]
1. 성능 리포트
   - 주간 KPI 요약
   - 전주 대비 변화
   - 목표 달성률
   
2. 사용자 행동 리포트
   - 신규/재방문 분석
   - 이탈률 분석
   - 코호트 분석
   
3. 추천 품질 리포트
   - 클릭률 (CTR)
   - 전환율 (CVR)
   - 다양성 지표
   - 개인화 수준
```

### 7.3 월간 배치 작업

#### 6.3.1 데이터 마이그레이션
```
[Monthly Migration - 1st Day]
1. 콜드 스토리지 이동
   - 3개월 이상 데이터
   - 파티션 단위 이동
   - 메타데이터 유지
   
2. 집계 테이블 재구성
   - 월간 요약 생성
   - 연간 트렌드 갱신
   - 계절성 패턴 분석
   
3. 마스터 데이터 동기화
   - 외부 시스템과 동기화
   - 데이터 정합성 검증
   - 불일치 리포트
```

---

## 8. 장애 처리 및 복구 플로우

### 8.1 장애 감지 및 분류

#### 7.1.1 장애 감지 메커니즘
```
[다층 감지 시스템]
1. 헬스체크 (1초 간격)
   - HTTP GET /health
   - TCP 포트 체크
   - 프로세스 상태
   
2. 메트릭 기반 (5초 간격)
   - 응답 시간 > 2초
   - 에러율 > 5%
   - CPU > 80%
   
3. 로그 기반 (실시간)
   - ERROR 레벨 로그
   - Exception 스택트레이스
   - 특정 패턴 매칭
   
4. 사용자 리포트
   - 피드백 채널
   - 자동 이슈 생성
```

#### 7.1.2 장애 분류 및 우선순위
```
[장애 등급]
P1 - Critical (즉시 대응)
  - 전체 서비스 다운
  - 데이터 손실 위험
  - 보안 침해
  
P2 - Major (15분 내)
  - 주요 기능 장애
  - 성능 심각 저하
  - 일부 사용자 영향
  
P3 - Minor (1시간 내)
  - 부가 기능 장애
  - 간헐적 오류
  - UX 저하
  
P4 - Low (업무시간 내)
  - 개선 사항
  - 성능 최적화
```

### 8.2 자동 복구 플로우

#### 7.2.1 서비스 레벨 복구
```
[자동 복구 단계]
1. 1차 시도: 재시작
   - 프로세스 재시작
   - 연결 재설정
   - 캐시 초기화
   
2. 2차 시도: 격리
   - 문제 인스턴스 제외
   - 트래픽 재라우팅
   - 새 인스턴스 시작
   
3. 3차 시도: 롤백
   - 이전 버전 배포
   - 설정 롤백
   - 데이터 복구
   
4. 4차 시도: 대체
   - 대체 서비스 활성화
   - 기능 제한 모드
   - 수동 개입 요청
```

#### 7.2.2 데이터 복구
```
[데이터 복구 절차]
1. 손상 범위 파악
   - 영향받은 테이블 식별
   - 시간 범위 확인
   - 데이터 검증
   
2. 복구 소스 선택
   - 실시간 복제본
   - 정기 백업
   - 트랜잭션 로그
   
3. 복구 실행
   BEGIN;
   -- 손상 데이터 격리
   CREATE TABLE corrupted_data AS 
   SELECT * FROM affected_table 
   WHERE created_at BETWEEN ? AND ?;
   
   -- 백업에서 복구
   INSERT INTO affected_table
   SELECT * FROM backup.affected_table
   WHERE created_at BETWEEN ? AND ?
   ON CONFLICT DO NOTHING;
   
   -- 정합성 검증
   SELECT COUNT(*) FROM affected_table;
   COMMIT;
   
4. 사후 검증
   - 데이터 무결성 체크
   - 애플리케이션 테스트
   - 모니터링 강화
```

### 8.3 재해 복구 (DR) 플로우

#### 7.3.1 RTO/RPO 목표
```
[복구 목표]
RPO (Recovery Point Objective): 5분
- 최대 5분의 데이터 손실 허용

RTO (Recovery Time Objective): 30분  
- 30분 내 서비스 정상화

[달성 방법]
- 실시간 복제 (1분 지연)
- 5분마다 스냅샷
- 핫 스탠바이 유지
```

#### 7.3.2 DR 시나리오별 대응
```
[시나리오 1: 데이터센터 장애]
1. 장애 감지 (1분)
   - 모니터링 알람
   - 자동 페일오버 시작
   
2. DNS 전환 (5분)
   - Route53 헬스체크
   - DR 사이트로 전환
   
3. 서비스 활성화 (10분)
   - 스탠바이 → 액티브
   - 캐시 워밍업
   - 부하 분산 조정
   
4. 데이터 동기화 (15분)
   - 누락 데이터 확인
   - 복제 재개
   - 일관성 검증

[시나리오 2: 랜섬웨어 공격]
1. 격리 (즉시)
   - 네트워크 차단
   - 쓰기 작업 중단
   - 스냅샷 생성
   
2. 평가 (30분)
   - 감염 범위 파악
   - 클린 백업 확인
   - 복구 계획 수립
   
3. 복구 (2시간)
   - 클린 환경 구축
   - 데이터 복원
   - 보안 패치 적용
   
4. 서비스 재개 (4시간)
   - 단계적 오픈
   - 모니터링 강화
   - 사용자 공지
```

### 8.4 사후 분석 플로우

#### 7.4.1 근본 원인 분석 (RCA)
```
[5 Whys 분석]
문제: 오후 2시 서비스 응답 지연

Why 1: DB 쿼리 타임아웃 발생
→ Why 2: 특정 쿼리가 전체 테이블 스캔
→ Why 3: 인덱스가 삭제됨
→ Why 4: 마이그레이션 스크립트 오류
→ Why 5: 코드 리뷰 프로세스 미준수

근본 원인: 프로세스 미준수
개선 방안: 
- 자동화된 스키마 검증
- 필수 리뷰어 지정
- 스테이징 환경 테스트 의무화
```

#### 7.4.2 개선 액션 아이템
```
[Post-Mortem Action Items]
1. 단기 조치 (1주 내)
   - 누락된 인덱스 복구
   - 알람 임계값 조정
   - 런북 업데이트
   
2. 중기 개선 (1개월 내)
   - CI/CD 파이프라인 강화
   - 카나리 배포 도입
   - 자동 롤백 구현
   
3. 장기 개선 (3개월 내)
   - 아키텍처 개선
   - 모니터링 고도화
   - DR 훈련 정례화
```

---

## 9. 학습 데이터 처리 플로우

### 9.1 실시간 데이터 수집

#### 데이터 수집 포인트
```
[수집 시점]
1. 사용자 입력 직후
2. NLU 처리 완료 후
3. 응답 생성 완료 후
4. 사용자 피드백 수신 시
5. 세션 종료 시

[수집 데이터]
- 원본 입력 텍스트
- NLU 예측 결과 (의도, 엔티티, 신뢰도)
- 생성된 응답
- 추천 결과
- 응답 시간
- 사용자 피드백 (선택, 평점 등)
```

#### 품질 평가 로직
```python
def calculate_quality_score(interaction):
    """학습 데이터 품질 점수 계산"""
    score = 0.0
    
    # NLU 신뢰도 (30%)
    score += interaction.nlu_confidence * 0.3
    
    # 응답 속도 (20%) - 2초 이내 만점
    time_score = max(0, 1 - (interaction.response_time_ms / 2000))
    score += time_score * 0.2
    
    # 추천 존재 여부 (30%)
    if interaction.has_recommendations:
        score += 0.3
    
    # 응답 길이 적절성 (20%)
    length = len(interaction.response_text)
    if 50 <= length <= 300:
        score += 0.2
    elif 30 <= length <= 500:
        score += 0.1
    
    return min(1.0, score)
```

### 9.2 세션 종료 처리

#### 세션 종료 트리거
```
1. 명시적 종료
   - 사용자가 대화 종료 버튼 클릭
   - "안녕", "고마워" 등 종료 인사
   
2. 타임아웃 (30분)
   - 마지막 상호작용 후 30분 경과
   - 백그라운드 타이머로 감지
   
3. 새 세션 시작
   - 동일 사용자가 새로운 대화 시작
   - 이전 세션 자동 마감
```

#### 종료 시 처리 절차
```python
async def handle_session_end(session_id: str):
    """세션 종료 시 학습 데이터 처리"""
    
    # 1. 세션 데이터 수집
    session_data = await get_session_data(session_id)
    
    # 2. 통계 계산
    stats = {
        "total_turns": len(session_data.conversations),
        "avg_quality_score": calculate_avg_quality(session_data),
        "has_recommendations": check_recommendations(session_data),
        "duration_seconds": calculate_duration(session_data)
    }
    
    # 3. 학습 가치 평가
    is_valuable = (
        stats["total_turns"] >= 2 and
        stats["avg_quality_score"] >= 0.5 and
        stats["has_recommendations"]
    )
    
    # 4. 데이터 저장
    if is_valuable:
        # 파일 시스템에 저장 (프로토타입)
        save_to_file(f"training_data/processed/{date}_sessions.jsonl", {
            "session_id": session_id,
            "stats": stats,
            "entries": session_data.conversations
        })
    
    # 5. 메모리 정리
    await cleanup_session_memory(session_id)
    
    return {
        "session_id": session_id,
        "is_valuable": is_valuable,
        "stats": stats
    }
```

### 9.3 학습 파이프라인

#### 일일 배치 처리
```bash
#!/bin/bash
# daily_training.sh - 매일 새벽 2시 실행

# 1. 전날 데이터 수집
echo "Collecting yesterday's data..."
python scripts/collect_daily_data.py \
    --date $(date -d "yesterday" +%Y%m%d)

# 2. 품질 필터링
echo "Filtering quality data..."
python scripts/filter_quality_data.py \
    --min-score 0.6 \
    --input training_data/raw \
    --output training_data/filtered

# 3. 학습 데이터셋 생성
echo "Creating training dataset..."
python scripts/prepare_dataset.py \
    --split "70:20:10" \
    --stratify intent

# 4. 모델 학습
echo "Training model..."
python scripts/train_from_collected_data.py \
    --epochs 10 \
    --batch-size 32 \
    --learning-rate 0.001

# 5. 성능 평가
echo "Evaluating performance..."
python scripts/evaluate_model.py \
    --test-set training_data/test.json \
    --metrics "accuracy,f1,confusion_matrix"

# 6. A/B 테스트 준비
echo "Preparing A/B test..."
if [ "$IMPROVEMENT" -gt "0.02" ]; then
    echo "Deploying to 10% traffic for A/B test"
    python scripts/deploy_canary.py --percentage 10
fi
```

#### 실시간 모니터링
```python
class TrainingMonitor:
    """학습 데이터 실시간 모니터링"""
    
    def __init__(self):
        self.metrics = {
            "daily_conversations": 0,
            "valuable_sessions": 0,
            "avg_quality_score": 0.0,
            "intent_distribution": {}
        }
    
    async def update_metrics(self, session_data):
        """메트릭 업데이트"""
        self.metrics["daily_conversations"] += 1
        
        if session_data["is_valuable"]:
            self.metrics["valuable_sessions"] += 1
        
        # 의도 분포 업데이트
        for conv in session_data["conversations"]:
            intent = conv["predicted_intent"]
            self.metrics["intent_distribution"][intent] = \
                self.metrics["intent_distribution"].get(intent, 0) + 1
    
    def get_dashboard_data(self):
        """대시보드용 데이터 반환"""
        return {
            "timestamp": datetime.now().isoformat(),
            "metrics": self.metrics,
            "alerts": self.check_anomalies()
        }
    
    def check_anomalies(self):
        """이상 패턴 감지"""
        alerts = []
        
        # 품질 점수 급락
        if self.metrics["avg_quality_score"] < 0.4:
            alerts.append("Quality score below threshold")
        
        # 특정 의도 급증
        total = sum(self.metrics["intent_distribution"].values())
        for intent, count in self.metrics["intent_distribution"].items():
            if total > 0 and count / total > 0.5:
                alerts.append(f"Intent {intent} dominating ({count/total:.1%})")
        
        return alerts
```

### 9.4 프라이버시 보호

#### 개인정보 자동 마스킹
```python
import re

class PrivacyProtector:
    """개인정보 자동 마스킹"""
    
    def __init__(self):
        self.patterns = {
            "name": r"(김|이|박|최|정|강|조|윤|장|임)[가-힣]{1,2}",
            "phone": r"\d{3}-?\d{3,4}-?\d{4}",
            "email": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
            "card": r"\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}",
            "address": r"(서울|부산|대구|인천|광주|대전|울산|세종|경기|강원|충북|충남|전북|전남|경북|경남|제주).*?(구|군|시).*?[0-9-]+"
        }
    
    def mask_text(self, text: str) -> str:
        """텍스트에서 개인정보 마스킹"""
        masked_text = text
        
        for info_type, pattern in self.patterns.items():
            masked_text = re.sub(
                pattern,
                f"[{info_type.upper()}]",
                masked_text,
                flags=re.IGNORECASE
            )
        
        return masked_text
    
    def process_training_data(self, data: dict) -> dict:
        """학습 데이터 익명화"""
        processed = data.copy()
        
        # 텍스트 필드 마스킹
        if "input_text" in processed:
            processed["input_text"] = self.mask_text(processed["input_text"])
        
        if "response_text" in processed:
            processed["response_text"] = self.mask_text(processed["response_text"])
        
        # 사용자 ID 해싱
        if "user_id" in processed:
            processed["user_id"] = hashlib.sha256(
                processed["user_id"].encode()
            ).hexdigest()[:16]
        
        return processed
```

#### 데이터 보관 정책
```yaml
data_retention_policy:
  # 원시 데이터 (개인정보 포함)
  raw_conversations:
    retention_days: 7
    storage: "encrypted_filesystem"
    access: "restricted"
  
  # 익명화된 학습 데이터
  anonymized_training_data:
    retention_days: 365
    storage: "object_storage"
    access: "ml_team_only"
  
  # 집계 통계
  aggregated_statistics:
    retention_days: -1  # 무기한
    storage: "data_warehouse"
    access: "read_only"
  
  # 모델 체크포인트
  model_checkpoints:
    retention_count: 10  # 최근 10개 버전
    storage: "model_registry"
    access: "deployment_pipeline"
```

---

## 부록: 주요 설정값 및 임계값

### 성능 임계값
```yaml
performance_thresholds:
  api_response_time:
    p50: 200ms
    p95: 500ms
    p99: 2000ms
  
  database_query:
    simple_select: 10ms
    complex_join: 100ms
    write_operation: 50ms
  
  cache_hit_rate:
    l1_memory: 0.95
    l2_redis: 0.80
    overall: 0.85
  
  error_rate:
    client_error_4xx: 0.05
    server_error_5xx: 0.01
    timeout_error: 0.001
```

### 리소스 제한
```yaml
resource_limits:
  api_server:
    cpu_limit: 4000m
    memory_limit: 8Gi
    max_connections: 10000
    request_timeout: 30s
  
  ml_server:
    gpu_memory: 16Gi
    model_cache_size: 32Gi
    batch_size: 32
    inference_timeout: 5s
  
  database:
    max_connections: 500
    connection_timeout: 10s
    statement_timeout: 30s
    work_mem: 256MB
```

### 보안 설정
```yaml
security_settings:
  rate_limiting:
    anonymous: 10/min
    authenticated: 60/min
    premium: 300/min
  
  jwt_token:
    access_token_ttl: 1h
    refresh_token_ttl: 30d
    algorithm: RS256
  
  encryption:
    at_rest: AES-256-GCM
    in_transit: TLS 1.3
    key_rotation: 90d
```
