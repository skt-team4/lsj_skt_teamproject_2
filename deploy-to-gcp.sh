#!/bin/bash

# GCP 프로젝트 설정
PROJECT_ID="rational-autumn-467006-e2"
REGION="asia-northeast3"
SERVICE_NAME="openai-compatible-server"
REPOSITORY_NAME="openai-compatible"
IMAGE_NAME="ai-server"

# 색상 코드
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     🚀 GCP Cloud Run 배포 스크립트              ║${NC}"
echo -e "${BLUE}║     OpenAI 호환 AI 서버                         ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════╝${NC}"
echo

# 1. 사전 체크
echo -e "${YELLOW}📋 사전 체크...${NC}"

# gcloud 설치 확인
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}❌ gcloud CLI가 설치되어 있지 않습니다.${NC}"
    echo "설치: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Docker 설치 확인
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker가 설치되어 있지 않습니다.${NC}"
    exit 1
fi

# 인증 확인
CURRENT_ACCOUNT=$(gcloud config get-value account 2>/dev/null)
if [ -z "$CURRENT_ACCOUNT" ]; then
    echo -e "${RED}❌ gcloud 인증이 필요합니다.${NC}"
    echo "실행: gcloud auth login"
    exit 1
fi
echo -e "${GREEN}✅ 인증됨: $CURRENT_ACCOUNT${NC}"

# 2. Artifact Registry 확인/생성
echo -e "${YELLOW}📦 Artifact Registry 설정...${NC}"

# API 활성화
gcloud services enable artifactregistry.googleapis.com --project=$PROJECT_ID 2>/dev/null

# 저장소 존재 확인
if ! gcloud artifacts repositories describe $REPOSITORY_NAME \
    --location=$REGION \
    --project=$PROJECT_ID &>/dev/null; then
    
    echo -e "${BLUE}새 저장소 생성 중...${NC}"
    gcloud artifacts repositories create $REPOSITORY_NAME \
        --repository-format=docker \
        --location=$REGION \
        --description="OpenAI 호환 AI 서버 Docker 이미지" \
        --project=$PROJECT_ID
fi

# Docker 인증
echo -e "${YELLOW}🔐 Docker 인증...${NC}"
gcloud auth configure-docker $REGION-docker.pkg.dev --quiet

# 3. Docker 이미지 빌드
echo -e "${YELLOW}🔨 Docker 이미지 빌드...${NC}"

IMAGE_TAG="$REGION-docker.pkg.dev/$PROJECT_ID/$REPOSITORY_NAME/$IMAGE_NAME:latest"

# openai_compatible_server.py 파일 확인
if [ ! -f "openai_compatible_server.py" ]; then
    echo -e "${RED}❌ openai_compatible_server.py 파일을 찾을 수 없습니다.${NC}"
    echo "현재 디렉토리: $(pwd)"
    exit 1
fi

# Dockerfile 확인
if [ ! -f "Dockerfile.openai-compatible" ]; then
    echo -e "${RED}❌ Dockerfile.openai-compatible 파일을 찾을 수 없습니다.${NC}"
    exit 1
fi

# 빌드
docker build -f Dockerfile.openai-compatible -t $IMAGE_TAG . || {
    echo -e "${RED}❌ Docker 빌드 실패${NC}"
    exit 1
}
echo -e "${GREEN}✅ Docker 이미지 빌드 완료${NC}"

# 4. Container Registry에 푸시
echo -e "${YELLOW}📤 Container Registry에 푸시...${NC}"
docker push $IMAGE_TAG || {
    echo -e "${RED}❌ Docker 푸시 실패${NC}"
    exit 1
}
echo -e "${GREEN}✅ 이미지 푸시 완료${NC}"

# 5. Cloud Run 배포
echo -e "${YELLOW}☁️ Cloud Run 서비스 배포...${NC}"

# Cloud Run API 활성화
gcloud services enable run.googleapis.com --project=$PROJECT_ID 2>/dev/null

# 배포
gcloud run deploy $SERVICE_NAME \
    --image $IMAGE_TAG \
    --platform managed \
    --region $REGION \
    --allow-unauthenticated \
    --port 8000 \
    --memory 2Gi \
    --cpu 2 \
    --min-instances 0 \
    --max-instances 10 \
    --set-env-vars="CUSTOM_API_KEY=sk-workstation-123456789" \
    --project $PROJECT_ID \
    --quiet || {
    echo -e "${RED}❌ Cloud Run 배포 실패${NC}"
    exit 1
}

# 6. 서비스 URL 확인
echo -e "${YELLOW}🔍 서비스 정보 확인...${NC}"

SERVICE_URL=$(gcloud run services describe $SERVICE_NAME \
    --region $REGION \
    --project $PROJECT_ID \
    --format="value(status.url)")

if [ -z "$SERVICE_URL" ]; then
    echo -e "${RED}❌ 서비스 URL을 가져올 수 없습니다.${NC}"
    exit 1
fi

# 7. 결과 출력
echo
echo -e "${GREEN}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║     ✅ 배포 완료!                               ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════╝${NC}"
echo
echo -e "${BLUE}📍 서비스 URL:${NC}"
echo -e "${GREEN}   $SERVICE_URL${NC}"
echo
echo -e "${BLUE}🔑 API 키:${NC}"
echo -e "${GREEN}   sk-workstation-123456789${NC}"
echo
echo -e "${BLUE}📱 React Native 설정 (.env.local):${NC}"
echo -e "${YELLOW}EXPO_PUBLIC_OPENAI_BASE_URL=${SERVICE_URL}/v1/chat/completions${NC}"
echo -e "${YELLOW}EXPO_PUBLIC_OPENAI_API_KEY=sk-workstation-123456789${NC}"
echo
echo -e "${BLUE}🧪 테스트 명령어:${NC}"
echo -e "${YELLOW}curl ${SERVICE_URL}/health${NC}"
echo
echo -e "${BLUE}📊 서비스 상태 확인:${NC}"
echo -e "${YELLOW}gcloud run services list --region=$REGION --project=$PROJECT_ID${NC}"
echo
echo -e "${BLUE}📝 로그 확인:${NC}"
echo -e "${YELLOW}gcloud run services logs read $SERVICE_NAME --region=$REGION --project=$PROJECT_ID${NC}"
echo

# 8. 헬스체크
echo -e "${YELLOW}🏥 헬스체크 실행...${NC}"
sleep 3
if curl -s "${SERVICE_URL}/health" | grep -q "healthy"; then
    echo -e "${GREEN}✅ 서비스가 정상적으로 작동 중입니다!${NC}"
else
    echo -e "${YELLOW}⚠️ 서비스가 아직 시작 중입니다. 잠시 후 다시 확인해주세요.${NC}"
fi

echo
echo -e "${GREEN}🎉 모든 작업이 완료되었습니다!${NC}"