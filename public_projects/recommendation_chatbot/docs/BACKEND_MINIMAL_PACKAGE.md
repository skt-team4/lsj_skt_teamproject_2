# 백엔드 담당자 최소 필수 패키지

## 🎯 꼭 넘겨야 하는 파일만 정리

### 📋 필수 파일 (총 7개)

```
📁 백엔드_필수_파일/
├── BACKEND_HANDOVER.md          # 인수인계 가이드
├── api/
│   ├── __init__.py
│   ├── server.py                # FastAPI 서버 틀
│   └── README.md                # API 사용법
├── data/
│   └── data_structure.py        # 데이터 모델 정의
├── requirements.txt             # 기본 의존성
└── sample_data.xlsx            # 실제 데이터 구조 참고
```

### ❌ 넘기지 않아도 되는 파일들

```
cache/                    # AI 모델 캐시 (용량 큼)
outputs/                  # 실행 결과물
models/                   # AI 모델 코드
nlp/                      # NLP 처리 로직
rag/                      # RAG 시스템
training/                 # 모델 학습
inference/                # AI 추론 로직 (참고만)
nutrition/                # 영양 정보 API
tests/                    # 테스트 파일
work_summary/             # 작업 요약
mcp-servers/              # 빈 폴더
utils/                    # 유틸리티 (선택)
```

## 🚀 실제 전달 방법

### 1단계: 새 폴더 생성
```
나비얌_백엔드_패키지/
```

### 2단계: 필수 파일만 복사
- `BACKEND_HANDOVER.md`
- `api/` 폴더 전체
- `data/data_structure.py`
- `requirements.txt`
- `sample_data.xlsx`

### 3단계: 백엔드 담당자에게 전달
"이 5개 파일/폴더만 있으면 백엔드 작업 시작할 수 있습니다!"

## 📊 용량 비교
- **전체 프로젝트**: ~2GB (AI 모델 캐시 포함)
- **백엔드 필수 패키지**: ~10MB

## 💡 추가 설명

### 왜 inference/chatbot.py는 안 넘기나요?
- 백엔드 담당자는 **API 서버만** 구축
- AI 로직은 **별도 서비스**로 분리된 상태
- `api/server.py`에서 챗봇을 import해서 사용하는 구조

### 나중에 필요하면?
```python
# api/server.py에서 이미 import 되어 있음
from inference.chatbot import NaviyamChatbot
```
실제 배포할 때만 AI 코드와 연동하면 됩니다.

## 🎯 결론
**최소 5개 파일/폴더만** 넘기면 백엔드 담당자는 즉시 작업 시작 가능!