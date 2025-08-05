#!/bin/bash

# 간단한 배포 스크립트
echo "🚀 나비얌 챗봇 API 배포 (간단 버전)"

# 1. 배포용 디렉토리 생성
echo "1️⃣ 배포 파일 준비..."
mkdir -p deploy-files
cp chatbot_api_only.py deploy-files/
cp requirements_simple.txt deploy-files/
cp Dockerfile deploy-files/

# 2. 배포 디렉토리로 이동
cd deploy-files

# 3. Cloud Run 소스 배포
echo "2️⃣ Cloud Run 배포 시작..."
gcloud run deploy nabiyam-chatbot-api \
    --source . \
    --region asia-northeast3 \
    --allow-unauthenticated \
    --port 8080 \
    --memory 512Mi \
    --project rational-autumn-467006-e2

echo "✅ 배포 완료!"