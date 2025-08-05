# 나비얌 챗봇 테스트 가이드

## 1. 환경 설정

### 가상환경 생성 및 활성화
```bash
# Python 3.8+ 필요
python3 -m venv venv
source venv/bin/activate  # Mac/Linux
# 또는
# venv\Scripts\activate  # Windows
```

### 의존성 설치
```bash
cd /Volumes/samsd/skt_teamproject/public_projects/recommendation_chatbot
pip install -r archive/requirements.txt
```

## 2. 간단한 테스트 실행

### 기본 대화 모드 실행
```bash
python main.py --mode chat
```

### 디버그 모드로 실행
```bash
python main.py --mode chat --debug
```

### 평가 모드 실행 (빠른 테스트)
```bash
python main.py --mode evaluation
```

## 3. 주요 실행 옵션

```bash
# 도움말 보기
python main.py --help

# 다양한 모드
python main.py --mode chat        # 대화형 모드
python main.py --mode inference   # 추론 테스트 모드
python main.py --mode evaluation  # 평가 모드

# 추가 옵션
python main.py --mode chat --debug              # 디버그 정보 출력
python main.py --mode chat --log_level DEBUG    # 상세 로그
python main.py --mode chat --use_4bit           # 4bit 양자화 (메모리 절약)
```

## 4. 테스트 시나리오

### 대화 모드에서 테스트할 수 있는 명령어들:

1. **음식 추천 요청**
   - "치킨 먹고 싶어"
   - "만원으로 뭐 먹을까?"
   - "근처 착한가게 알려줘"

2. **쿠폰 관련**
   - "쿠폰"
   - "잔액"
   - "할인 쿠폰 있어?"

3. **특수 명령어**
   - `/help` - 도움말
   - `/stats` - 통계 정보
   - `/profile` - 사용자 프로필
   - `/history` - 대화 기록
   - `/reset` - 대화 초기화

## 5. 빠른 테스트 (Quick Test)

만약 전체 환경 설정이 어렵다면, quick_test.py 파일을 확인해보세요:
```bash
python quick_test.py
```

## 6. 문제 해결

### 메모리 부족 시
```bash
python main.py --mode chat --use_4bit --max_length 512
```

### 모델 로딩 오류 시
```bash
# 캐시 삭제
python clear_cache.py

# 다시 실행
python main.py --mode chat
```

### 의존성 문제 시
```bash
# 최소 의존성만 설치
pip install torch transformers pandas
```

## 7. 테스트 사용자 정보

대화 모드에서 테스트 사용자 선택 시:
- `1`: 잔액 25,000원 사용자
- `2`: 잔액 5,000원 사용자  
- `3`: 잔액 15,000원 사용자
- 기타: 일반 사용자

## 8. 로그 확인

실행 로그는 다음 위치에 저장됩니다:
```
outputs/logs/naviyam_chatbot.log
```