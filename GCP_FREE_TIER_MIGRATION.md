# GCP 무료 크레딧 계정으로 전환 가이드

## 📌 현재 상황
- **현재 계정**: 일반 유료 계정 (내 결제 계정)
- **프로젝트**: rational-autumn-467006-e2
- **문제**: 무료 크레딧이 아닌 실제 과금 발생

## 🆓 GCP 무료 크레딧 옵션

### 옵션 1: 새 Google 계정으로 무료 크레딧 받기 (권장)

#### 장점
- $300 (약 40만원) 무료 크레딧
- 90일간 사용 가능
- 신용카드 필요하지만 자동 과금 안됨

#### 단계별 설정
```bash
# 1. 새 Google 계정 생성 (다른 이메일 사용)
# https://accounts.google.com/signup

# 2. GCP 무료 체험 등록
# https://cloud.google.com/free

# 3. 새 프로젝트 생성
gcloud projects create nabiyam-free-tier --name="나비얌 무료"

# 4. 청구 계정 연결 (무료 크레딧)
gcloud beta billing projects link nabiyam-free-tier \
  --billing-account=NEW_BILLING_ACCOUNT_ID

# 5. 필요한 API 활성화
gcloud services enable run.googleapis.com \
  compute.googleapis.com \
  cloudbuild.googleapis.com \
  --project=nabiyam-free-tier
```

### 옵션 2: Always Free 제품만 사용

#### 무료 한도
- **Cloud Run**: 
  - 월 200만 요청 무료
  - 월 360,000 GB-초 메모리 무료
  - 월 180,000 vCPU-초 무료
- **Cloud Storage**: 5GB 무료
- **Firestore**: 1GB 저장, 일 5만 읽기/2만 쓰기 무료

#### 현재 프로젝트 청구 계정 해제
```bash
# 청구 계정 연결 해제 (과금 중단)
gcloud beta billing projects unlink rational-autumn-467006-e2
```

## 🚀 서비스 마이그레이션 스크립트

### 1. 기존 서비스 백업
```bash
# Cloud Run 서비스 설정 내보내기
gcloud run services describe nabiyam-chatbot-web \
  --region=asia-northeast3 \
  --project=rational-autumn-467006-e2 \
  --export > chatbot-web-config.yaml

gcloud run services describe nabiyam-webapp-v2 \
  --region=asia-northeast3 \
  --project=rational-autumn-467006-e2 \
  --export > webapp-v2-config.yaml
```

### 2. 새 계정에서 서비스 재생성
```bash
# 새 프로젝트로 전환
gcloud config set project nabiyam-free-tier

# Cloud Run 서비스 배포
gcloud run deploy nabiyam-chatbot-web \
  --source . \
  --platform managed \
  --region asia-northeast3 \
  --allow-unauthenticated \
  --memory 512Mi \
  --cpu 1 \
  --min-instances 0 \
  --max-instances 2 \
  --project nabiyam-free-tier

# 웹앱 배포
gcloud run deploy nabiyam-webapp-v2 \
  --source . \
  --platform managed \
  --region asia-northeast3 \
  --allow-unauthenticated \
  --memory 1Gi \
  --cpu 1 \
  --min-instances 0 \
  --max-instances 2 \
  --project nabiyam-free-tier
```

## 💳 무료 크레딧 최대 활용 전략

### 1. 무료 등급 내에서만 운영
```yaml
# Cloud Run 설정 (무료 한도 내)
resources:
  limits:
    cpu: "1"
    memory: "512Mi"
scaling:
  minInstances: 0
  maxInstances: 2
```

### 2. 비용 모니터링
```bash
# 일일 사용량 확인
gcloud billing budgets create \
  --billing-account=BILLING_ACCOUNT_ID \
  --display-name="일일 알림" \
  --budget-amount=3USD \
  --threshold-rule=percent=100
```

### 3. 자동 종료 설정
```bash
# 예산 초과시 프로젝트 자동 비활성화
gcloud alpha billing budgets update BUDGET_ID \
  --disable-default-iam-recipients \
  --pubsub-topic=projects/PROJECT_ID/topics/budget-alerts
```

## 🔄 즉시 실행 가능한 옵션

### 옵션 A: 현재 프로젝트 과금 중단
```bash
# 청구 계정 연결 해제 (서비스는 중단됨)
gcloud beta billing projects unlink rational-autumn-467006-e2

echo "⚠️ 경고: 청구 계정이 해제되면 Cloud Run 서비스가 중단됩니다"
```

### 옵션 B: 새 무료 계정 생성
1. 새 Gmail 계정 생성
2. https://cloud.google.com/free 에서 무료 체험 시작
3. $300 크레딧 받기

### 옵션 C: 워크스테이션 전용 (추천)
```bash
# GCP 없이 완전 로컬 운영
# 워크스테이션에서:
python gpu_server.py

# 로컬 ngrok으로 공개
ngrok http 8000

# React Native 앱에서 직접 연결
```

## 📊 비용 비교

| 옵션 | 초기 크레딧 | 월 비용 | 제한사항 |
|------|------------|---------|----------|
| 새 무료 계정 | $300 | $0 (90일) | 90일 후 재생성 필요 |
| Always Free | $0 | $0 | 제한된 리소스 |
| 워크스테이션 | $0 | 전기료 | 24/7 PC 필요 |
| 현재 계정 | $0 | ~2만원 | 실제 과금 |

## ⚡ 추천 방법

### 1. 단기 (3개월)
→ 새 계정 + $300 무료 크레딧

### 2. 장기
→ 워크스테이션 + ngrok

### 3. 하이브리드
→ Always Free Cloud Run (웹) + 워크스테이션 (AI)

## 🛠️ 다음 단계

1. **즉시**: 현재 청구 계정 해제하여 추가 과금 방지
2. **오늘 중**: 새 무료 계정 생성
3. **내일**: 서비스 마이그레이션

```bash
# 과금 즉시 중단 명령
echo "다음 명령을 실행하면 과금이 중단되지만 서비스도 중단됩니다:"
echo "gcloud beta billing projects unlink rational-autumn-467006-e2"
```

---

**중요**: 청구 계정을 해제하면 Cloud Run 서비스가 중단됩니다.
새 무료 계정을 먼저 준비하고 마이그레이션하는 것을 권장합니다.