# GCP 비용 분석 - 정확한 구조

## 🏗️ 현재 아키텍처

### 1. Cloud Run 서비스 (서버리스, GPU 없음)
```
nabiyam-chatbot-web (CPU only)
├── CPU: 1 vCPU
├── Memory: 512Mi
├── Min Instances: 0 (요청 없으면 비용 0)
└── 비용: 요청당 과금 (거의 무료 수준)

nabiyam-webapp-v2 (CPU only)  
├── CPU: 1 vCPU
├── Memory: 1Gi
├── Min Instances: 미설정 (확인 필요)
└── 비용: 요청당 과금
```

### 2. Compute Engine VM (별도 가상머신)
```
naviyam-gpu-server (현재 TERMINATED)
├── Machine Type: g2-standard-4
├── GPU: NVIDIA L4 x1
├── Disk: 100GB pd-balanced (아직 존재!)
├── 상태: TERMINATED (중지됨)
└── 비용: 
    - 실행 시: 시간당 1,400원
    - 디스크: 월 13,000원 (중지해도 계속 과금)
```

## 💸 20만원 비용의 실제 원인

### 주요 원인: Compute Engine GPU 인스턴스
1. **GPU 인스턴스 실행 시간**
   - g2-standard-4 + NVIDIA L4: 시간당 약 1,400원
   - 6일(144시간) 실행 = 201,600원

2. **100GB 디스크 유지**
   - 인스턴스는 중지했지만 디스크는 남아있음
   - 월 13,000원 계속 과금 중

### Cloud Run은 거의 무료
- Min Instances = 0 설정되어 있음
- 요청이 없으면 비용 0
- 월 몇 천원 수준

## 🎯 핵심 포인트

**Cloud Run ≠ GPU 인스턴스**
- Cloud Run: 서버리스 컨테이너 서비스 (GPU 지원 안함)
- Compute Engine: 전통적인 가상머신 (GPU 옵션 있음)
- 두 서비스는 완전히 독립적

## 🔧 즉시 해야 할 일

1. **남아있는 100GB 디스크 삭제**
```bash
gcloud compute disks delete naviyam-gpu-server \
  --project=rational-autumn-467006-e2 \
  --zone=asia-northeast3-b
```

2. **앞으로 GPU가 필요한 경우**
- AI 모델 학습/추론이 필요하면 임시로만 생성
- 사용 후 인스턴스와 디스크 모두 삭제
- 또는 Cloud Run + 외부 AI API 사용 고려

## 💡 권장 아키텍처

### 옵션 1: Cloud Run Only (권장)
- 프론트엔드: Cloud Run 웹앱
- 백엔드: Cloud Run API (CPU만 사용)
- AI: OpenAI API 또는 Google Vertex AI API 호출
- 비용: 월 1-2만원

### 옵션 2: 필요시만 GPU
- 평소: Cloud Run만 운영
- AI 학습 필요시: 임시 GPU 인스턴스 생성 → 사용 → 즉시 삭제
- 비용: 사용한 시간만큼만 과금

### 옵션 3: Colab Pro 활용
- 개발/테스트: Google Colab Pro (월 $10)
- 프로덕션: Cloud Run only
- 비용: 월 2-3만원