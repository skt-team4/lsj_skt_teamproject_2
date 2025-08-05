#!/bin/bash

# Google Cloud 배포 스크립트
# 사전 준비: gcloud CLI 설치 및 로그인 필요

PROJECT_ID="rational-autumn-467006-e2"  # 기존 프로젝트 ID
SERVICE_NAME="nabiyam-chatbot-api"
REGION="asia-northeast3"  # 서울

echo "🚀 나비얌 챗봇 API Google Cloud Run 배포"
echo "=================================="

# 1. 프로젝트 설정
echo "1️⃣ 프로젝트 설정..."
gcloud config set project $PROJECT_ID

# 2. Cloud Build를 사용한 이미지 빌드 및 푸시
echo "2️⃣ Docker 이미지 빌드 중..."
gcloud builds submit --tag gcr.io/$PROJECT_ID/$SERVICE_NAME

# 3. Cloud Run에 배포
echo "3️⃣ Cloud Run 배포 중..."
gcloud run deploy $SERVICE_NAME \
  --image gcr.io/$PROJECT_ID/$SERVICE_NAME \
  --region $REGION \
  --platform managed \
  --allow-unauthenticated \
  --port 8080 \
  --memory 512Mi \
  --max-instances 10

# 4. 서비스 URL 가져오기
echo "4️⃣ 배포 완료!"
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region $REGION --format 'value(status.url)')
echo "✅ API URL: $SERVICE_URL"
echo "📖 API 문서: $SERVICE_URL/docs"
echo ""
echo "테스트:"
echo "curl -X POST $SERVICE_URL/chat \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{\"message\": \"안녕\", \"user_id\": \"test\"}'"