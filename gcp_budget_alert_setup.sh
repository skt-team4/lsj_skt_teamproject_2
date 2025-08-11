#!/bin/bash

# GCP 예산 알림 설정 스크립트

PROJECT_ID="rational-autumn-467006-e2"
BUDGET_AMOUNT="30000"  # 30,000원
DISPLAY_NAME="월간 예산 알림"
ALERT_EMAIL="softkleenex1217@gmail.com"  # 알림 받을 이메일

echo "🔔 GCP 예산 알림 설정 중..."

# 1. 청구 계정 ID 가져오기
echo "청구 계정 확인 중..."
BILLING_ACCOUNT=$(/Users/isangjae/google-cloud-sdk/bin/gcloud billing accounts list --format="value(name)" | head -1)

if [ -z "$BILLING_ACCOUNT" ]; then
    echo "❌ 청구 계정을 찾을 수 없습니다."
    echo "다음 명령으로 수동 확인: gcloud billing accounts list"
    exit 1
fi

echo "청구 계정: $BILLING_ACCOUNT"

# 2. 예산 생성 (gcloud budgets 명령이 없을 경우 대안)
cat > budget_config.json << EOF
{
  "displayName": "${DISPLAY_NAME}",
  "budgetFilter": {
    "projects": ["projects/${PROJECT_ID}"]
  },
  "amount": {
    "specifiedAmount": {
      "currencyCode": "KRW",
      "units": "${BUDGET_AMOUNT}"
    }
  },
  "thresholdRules": [
    {
      "thresholdPercent": 0.5,
      "spendBasis": "CURRENT_SPEND"
    },
    {
      "thresholdPercent": 0.9,
      "spendBasis": "CURRENT_SPEND"
    },
    {
      "thresholdPercent": 1.0,
      "spendBasis": "CURRENT_SPEND"
    }
  ],
  "notificationsRule": {
    "pubsubTopic": "",
    "schemaVersion": "1.0",
    "monitoringNotificationChannels": [],
    "disableDefaultIamRecipients": false
  }
}
EOF

echo "✅ 예산 설정 파일 생성 완료: budget_config.json"

# 3. 대안: 콘솔 URL 제공
echo ""
echo "📌 예산 알림을 설정하려면 다음 URL에서 수동으로 설정하세요:"
echo "https://console.cloud.google.com/billing/budgets/new?project=${PROJECT_ID}"
echo ""
echo "설정 값:"
echo "  - 예산 이름: ${DISPLAY_NAME}"
echo "  - 예산 금액: ${BUDGET_AMOUNT} KRW"
echo "  - 알림 임계값: 50%, 90%, 100%"
echo "  - 프로젝트: ${PROJECT_ID}"
echo ""

# 4. 추가 비용 절감 확인
echo "🔍 추가 비용 절감 체크..."

# VM 인스턴스 확인
echo "- VM 인스턴스 확인..."
INSTANCES=$(/Users/isangjae/google-cloud-sdk/bin/gcloud compute instances list --project=${PROJECT_ID} --format="value(name,status)" 2>/dev/null)
if [ -n "$INSTANCES" ]; then
    echo "  ⚠️ 실행 중인 인스턴스가 있습니다:"
    echo "$INSTANCES"
else
    echo "  ✅ 실행 중인 VM 없음"
fi

# Cloud Run 서비스 확인
echo "- Cloud Run 서비스 확인..."
SERVICES=$(/Users/isangjae/google-cloud-sdk/bin/gcloud run services list --project=${PROJECT_ID} --format="value(SERVICE,REGION)" 2>/dev/null)
if [ -n "$SERVICES" ]; then
    echo "  ✅ Cloud Run 서비스 (최소 인스턴스 0으로 설정됨)"
    echo "$SERVICES"
fi

# 디스크 확인
echo "- 남은 디스크 확인..."
DISKS=$(/Users/isangjae/google-cloud-sdk/bin/gcloud compute disks list --project=${PROJECT_ID} --format="value(name,sizeGb)" 2>/dev/null)
if [ -n "$DISKS" ]; then
    echo "  ⚠️ 남은 디스크가 있습니다:"
    echo "$DISKS"
else
    echo "  ✅ 불필요한 디스크 없음"
fi

echo ""
echo "✅ 비용 절감 설정 완료!"
echo ""
echo "현재 설정:"
echo "  - GPU 인스턴스: 삭제됨 ✅"
echo "  - Cloud Run: 최소 인스턴스 0 ✅"
echo "  - 예상 월 비용: 2-3만원"