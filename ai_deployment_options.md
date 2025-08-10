# AI 서비스 배포 옵션 가이드

## 🎯 핵심 질문: GPU가 정말 필요한가?

### 1. AI 모델 실행 단계별 요구사항

#### 🔴 학습(Training) - GPU 필수
- 대량의 행렬 연산
- 수 시간~수 일 소요
- GPU 없으면 현실적으로 불가능

#### 🟡 추론(Inference) - 상황에 따라 다름
- **대형 모델(7B+ 파라미터)**: GPU 권장
- **경량 모델(~3B)**: CPU 가능
- **양자화 모델(4bit/8bit)**: CPU 가능
- **API 호출**: GPU 불필요

## 💡 실용적인 솔루션 비교

### 옵션 1: Preemptible GPU 인스턴스
```bash
# 80% 할인된 가격 (시간당 280원)
gcloud compute instances create ai-server \
  --machine-type=g2-standard-4 \
  --accelerator=type=nvidia-l4,count=1 \
  --preemptible \  # 24시간 내 중단 가능
  --zone=asia-northeast3-b
```

**장점:**
- 일반 GPU의 20% 가격
- 실제 GPU 성능 100%

**단점:**
- 최대 24시간 후 강제 종료
- 재시작 보장 없음
- 프로덕션 서비스 부적합

**적합한 경우:**
- 배치 처리
- 개발/테스트
- 단기 실험

### 옵션 2: 고사양 워크스테이션 활용

#### 필요 사양 확인
```python
# 최소 요구사항
- GPU: RTX 3060 (12GB) 이상
- RAM: 32GB 이상
- 인터넷: 고정 IP 또는 DDNS
```

**장점:**
- 초기 비용만 발생
- 완전한 제어권
- 24/7 운영 가능

**단점:**
- 전기료 (월 3-5만원)
- 네트워크 설정 복잡
- 보안 위험
- 유지보수 필요

### 옵션 3: 하이브리드 아키텍처 (권장) ⭐

```
[사용자] → [Cloud Run 웹서버] → [선택적 백엔드]
                                    ├── 가벼운 요청 → CPU 처리
                                    ├── 무거운 요청 → 워크스테이션
                                    └── 대량 처리 → Preemptible GPU
```

## 🏗️ 나비얌 챗봇에 최적화된 구성

### 현재 코드 분석 결과
- A.X-3.1-Light 모델 사용 (3.1B 파라미터)
- 4bit 양자화 지원
- MPS(Apple Silicon) 지원

### 권장 아키텍처

#### 1단계: 경량화 (즉시 적용 가능)
```python
# 1. 모델을 양자화하여 CPU에서 실행
from transformers import AutoModelForCausalLM, BitsAndBytesConfig

quantization_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_compute_dtype=torch.float16
)

# 2. 또는 더 작은 모델 사용
model = "microsoft/phi-2"  # 2.7B, CPU 가능
```

#### 2단계: 워크스테이션 API 서버
```bash
# 워크스테이션에서 실행
ngrok http 8000  # 임시 공개 URL 생성

# 또는 Cloudflare Tunnel (무료)
cloudflared tunnel --url http://localhost:8000
```

#### 3단계: Cloud Run + 워크스테이션
```python
# Cloud Run 서버 (api/server.py)
import requests

@app.post("/chat")
async def chat(request):
    if is_heavy_request(request):
        # 워크스테이션으로 전달
        response = requests.post(
            "https://your-workstation.ngrok.io/inference",
            json=request
        )
    else:
        # 경량 처리
        response = simple_response(request)
    return response
```

## 📊 비용 비교

| 옵션 | 초기비용 | 월 운영비 | 안정성 | 성능 |
|------|---------|----------|--------|------|
| GPU VM 상시 | 0원 | 20만원 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| Preemptible | 0원 | 4만원 | ⭐⭐ | ⭐⭐⭐⭐ |
| 워크스테이션 | 200만원 | 5만원 | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| 하이브리드 | 0원 | 2만원 | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| API Only | 0원 | 3만원 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |

## 🚀 즉시 실행 가능한 솔루션

### 1. Preemptible로 테스트
```bash
# 인스턴스 생성 (시간당 280원)
gcloud compute instances create ai-test \
  --machine-type=g2-standard-4 \
  --accelerator=type=nvidia-l4,count=1 \
  --preemptible \
  --boot-disk-size=30GB \
  --zone=asia-northeast3-b

# 사용 후 즉시 삭제
gcloud compute instances delete ai-test --zone=asia-northeast3-b
```

### 2. 워크스테이션 테스트
```bash
# 로컬에서 서버 실행
cd naviyam_backend_runnable_20250806_112316
python -m uvicorn api.server:app --host 0.0.0.0 --port 8000

# ngrok으로 임시 공개
ngrok http 8000
# 생성된 URL을 Cloud Run에서 호출
```

### 3. 경량 모델로 전환
```python
# models/model_factory.py 수정
class ModelFactory:
    @staticmethod
    def create_model(model_type: str):
        if model_type == "ax":
            # 경량 모델로 변경
            return AutoModelForCausalLM.from_pretrained(
                "microsoft/DialoGPT-medium",  # 345M, CPU 가능
                torch_dtype=torch.float32
            )
```

## 📌 결론

**즉시 적용:** Preemptible 인스턴스로 테스트
**중기 계획:** 워크스테이션 + Cloud Run 하이브리드
**장기 계획:** 모델 경량화 + 완전 서버리스

워크스테이션이 있다면 충분히 활용 가능합니다!
중요한 건 24/7 서비스가 필요한지, 아니면 특정 시간만 필요한지입니다.