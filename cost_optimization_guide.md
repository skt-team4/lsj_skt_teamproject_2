# GCP 비용 최적화 가이드

## 즉시 실행 명령어

### 1. 불필요한 디스크 삭제 (약 월 13,000원 절감)
```bash
# GPU 서버의 디스크 삭제 (인스턴스가 TERMINATED 상태이므로 안전)
gcloud compute disks delete naviyam-gpu-server \
  --project=rational-autumn-467006-e2 \
  --zone=asia-northeast3-b
```

### 2. Cloud Run 최소 인스턴스 0으로 설정 (대기 비용 제거)
```bash
# nabiyam-chatbot-web 서비스
gcloud run services update nabiyam-chatbot-web \
  --project=rational-autumn-467006-e2 \
  --region=asia-northeast3 \
  --min-instances=0 \
  --max-instances=3

# nabiyam-webapp-v2 서비스  
gcloud run services update nabiyam-webapp-v2 \
  --project=rational-autumn-467006-e2 \
  --region=asia-northeast3 \
  --min-instances=0 \
  --max-instances=3
```

### 3. GPU 대신 CPU 인스턴스 사용 고려
```bash
# GPU가 필요한 경우에만 Spot 인스턴스 사용
gcloud compute instances create naviyam-cpu-server \
  --project=rational-autumn-467006-e2 \
  --zone=asia-northeast3-a \
  --machine-type=e2-medium \  # 시간당 약 40원
  --preemptible \
  --boot-disk-size=20GB \
  --boot-disk-type=pd-standard
```

## 권장 아키텍처 변경

### 현재 문제점
- GPU 인스턴스 사용 (시간당 1,400원)
- 100GB 디스크 (월 13,000원)
- Cloud Run 상시 대기

### 개선안
1. **개발/테스트**: Cloud Run만 사용 (요청 시에만 비용 발생)
2. **추론 필요 시**: 
   - Spot/Preemptible CPU 인스턴스 (80% 할인)
   - 작은 디스크 (20-30GB)
3. **GPU 필요 시**: 
   - 사용 직전에만 생성
   - 사용 후 즉시 삭제 (디스크 포함)

## 예상 비용 절감
- 현재: 월 20만원
- 개선 후: 월 2-3만원 (90% 절감)

## 추가 팁
1. 예산 알림 설정
```bash
gcloud billing budgets create \
  --billing-account=YOUR_BILLING_ACCOUNT \
  --display-name="월 예산" \
  --budget-amount=30000KRW \
  --threshold-rule=percent=50,basis=current-spend \
  --threshold-rule=percent=90,basis=current-spend
```

2. 자동 종료 스크립트 설정
3. Cloud Scheduler로 야간/주말 자동 중지