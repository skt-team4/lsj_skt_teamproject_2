# 🚀 워크스테이션 AI를 GCP로 배포하기

## 🎯 목표: 네트워크 분리 문제 해결
워크스테이션과 테스트 환경이 다른 네트워크에 있어도 GCP를 통해 접근 가능하게 만들기

## 📝 전체 흐름
1. 워크스테이션에서 Docker 이미지 빌드
2. GCP Container Registry에 푸시
3. Cloud Run으로 배포
4. 퍼블릭 URL로 어디서나 접근 가능

## 1️⃣ GCP Container Registry 설정

### Artifact Registry 생성 (최초 1회)
```bash
# Artifact Registry 활성화
gcloud services enable artifactregistry.googleapis.com --project=rational-autumn-467006-e2

# Docker 저장소 생성
gcloud artifacts repositories create openai-compatible \
  --repository-format=docker \
  --location=asia-northeast3 \
  --description="OpenAI 호환 AI 서버" \
  --project=rational-autumn-467006-e2
```

### Docker 인증 설정
```bash
# gcloud 인증
gcloud auth configure-docker asia-northeast3-docker.pkg.dev
```

## 2️⃣ Docker 이미지 빌드 및 푸시

### 워크스테이션에서 실행
```bash
# 1. 프로젝트 폴더로 이동
cd /Volumes/samsd/skt_teamproject

# 2. Docker 이미지 빌드 (태그 포함)
docker build -f Dockerfile.openai-compatible \
  -t asia-northeast3-docker.pkg.dev/rational-autumn-467006-e2/openai-compatible/ai-server:latest .

# 3. GCP Container Registry에 푸시
docker push asia-northeast3-docker.pkg.dev/rational-autumn-467006-e2/openai-compatible/ai-server:latest
```

## 3️⃣ Cloud Run 배포

### 배포 명령어
```bash
gcloud run deploy openai-compatible-server \
  --image asia-northeast3-docker.pkg.dev/rational-autumn-467006-e2/openai-compatible/ai-server:latest \
  --platform managed \
  --region asia-northeast3 \
  --allow-unauthenticated \
  --port 8000 \
  --memory 2Gi \
  --cpu 2 \
  --min-instances 0 \
  --max-instances 10 \
  --set-env-vars="CUSTOM_API_KEY=sk-workstation-123456789" \
  --project rational-autumn-467006-e2
```

### 서비스 URL 확인
```bash
# URL 가져오기
gcloud run services describe openai-compatible-server \
  --region asia-northeast3 \
  --project rational-autumn-467006-e2 \
  --format="value(status.url)"

# 예상 출력: https://openai-compatible-server-816056347823.asia-northeast3.run.app
```

## 4️⃣ React Native 앱 설정

### .env.local 파일 수정
```env
# GCP Cloud Run URL 사용
EXPO_PUBLIC_OPENAI_BASE_URL=https://openai-compatible-server-816056347823.asia-northeast3.run.app/v1/chat/completions
EXPO_PUBLIC_OPENAI_API_KEY=sk-workstation-123456789
```

### 또는 apiService.ts에서 직접 수정
```typescript
const API_CONFIG = {
  openai: {
    baseUrl: 'https://openai-compatible-server-816056347823.asia-northeast3.run.app/v1/chat/completions',
    apiKey: 'sk-workstation-123456789',
    model: 'gpt-3.5-turbo',
  },
};
```

## 5️⃣ 테스트

### Cloud Run 서비스 테스트
```bash
# 헬스체크
curl https://openai-compatible-server-816056347823.asia-northeast3.run.app/health

# API 테스트
curl https://openai-compatible-server-816056347823.asia-northeast3.run.app/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-workstation-123456789" \
  -d '{
    "model": "gpt-3.5-turbo",
    "messages": [{"role": "user", "content": "안녕하세요"}]
  }'
```

## 6️⃣ 업데이트 자동화 스크립트

### deploy-to-gcp.sh
```bash
#!/bin/bash

# 색상 코드
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 GCP 배포 시작...${NC}"

# 1. Docker 이미지 빌드
echo -e "${GREEN}1. Docker 이미지 빌드 중...${NC}"
docker build -f Dockerfile.openai-compatible \
  -t asia-northeast3-docker.pkg.dev/rational-autumn-467006-e2/openai-compatible/ai-server:latest .

# 2. Container Registry에 푸시
echo -e "${GREEN}2. Container Registry에 푸시 중...${NC}"
docker push asia-northeast3-docker.pkg.dev/rational-autumn-467006-e2/openai-compatible/ai-server:latest

# 3. Cloud Run 업데이트
echo -e "${GREEN}3. Cloud Run 서비스 업데이트 중...${NC}"
gcloud run deploy openai-compatible-server \
  --image asia-northeast3-docker.pkg.dev/rational-autumn-467006-e2/openai-compatible/ai-server:latest \
  --region asia-northeast3 \
  --project rational-autumn-467006-e2

# 4. URL 확인
echo -e "${GREEN}4. 배포 완료!${NC}"
SERVICE_URL=$(gcloud run services describe openai-compatible-server \
  --region asia-northeast3 \
  --project rational-autumn-467006-e2 \
  --format="value(status.url)")

echo -e "${BLUE}✅ 서비스 URL: ${SERVICE_URL}${NC}"
echo -e "${BLUE}📝 React Native .env.local에 추가:${NC}"
echo "EXPO_PUBLIC_OPENAI_BASE_URL=${SERVICE_URL}/v1/chat/completions"
echo "EXPO_PUBLIC_OPENAI_API_KEY=sk-workstation-123456789"
```

실행 권한 부여:
```bash
chmod +x deploy-to-gcp.sh
```

## 7️⃣ 비용 관리

### 비용 최적화 설정
```bash
# 최소 인스턴스 0으로 설정 (요청 없으면 비용 0)
gcloud run services update openai-compatible-server \
  --min-instances 0 \
  --region asia-northeast3 \
  --project rational-autumn-467006-e2

# CPU 할당 설정 (요청 시에만 CPU 사용)
gcloud run services update openai-compatible-server \
  --cpu-throttling \
  --region asia-northeast3 \
  --project rational-autumn-467006-e2
```

### 서비스 삭제 (필요시)
```bash
# Cloud Run 서비스 삭제
gcloud run services delete openai-compatible-server \
  --region asia-northeast3 \
  --project rational-autumn-467006-e2

# Container Registry 이미지 삭제
gcloud artifacts docker images delete \
  asia-northeast3-docker.pkg.dev/rational-autumn-467006-e2/openai-compatible/ai-server:latest
```

## 📊 장점

### vs ngrok
- ✅ **안정적**: 터널 끊김 없음
- ✅ **고정 URL**: 항상 같은 주소
- ✅ **확장 가능**: 자동 스케일링
- ✅ **HTTPS**: 자동 SSL 인증서

### vs GPU 인스턴스
- ✅ **저렴**: min-instances=0으로 요청 없으면 무료
- ✅ **관리 불필요**: 서버리스
- ✅ **자동 업데이트**: 이미지 푸시만 하면 자동 배포

## 🔧 문제 해결

### "Permission denied" 오류
```bash
# 권한 확인
gcloud auth list

# 재인증
gcloud auth login
```

### Docker push 실패
```bash
# Docker 재인증
gcloud auth configure-docker asia-northeast3-docker.pkg.dev

# 또는 직접 로그인
docker login asia-northeast3-docker.pkg.dev
```

### Cloud Run 503 오류
```bash
# 로그 확인
gcloud run services logs read openai-compatible-server \
  --region asia-northeast3 \
  --project rational-autumn-467006-e2

# 메모리 증가
gcloud run services update openai-compatible-server \
  --memory 4Gi \
  --region asia-northeast3 \
  --project rational-autumn-467006-e2
```

## 🎯 요약

**워크스테이션에서 한 번만 실행:**
```bash
./deploy-to-gcp.sh
```

**React Native에서 URL/API키 변경:**
```env
EXPO_PUBLIC_OPENAI_BASE_URL=https://[자동생성된URL]/v1/chat/completions
EXPO_PUBLIC_OPENAI_API_KEY=sk-workstation-123456789
```

이제 네트워크가 분리되어 있어도 어디서나 워크스테이션 AI를 사용할 수 있습니다! 🎉