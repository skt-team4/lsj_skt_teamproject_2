#!/bin/bash

# Naviyam Chatbot Docker Build Script

echo "========================================"
echo "Naviyam Chatbot Docker Build"
echo "========================================"

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 함수: 성공 메시지
success() {
    echo -e "${GREEN}✓${NC} $1"
}

# 함수: 에러 메시지
error() {
    echo -e "${RED}✗${NC} $1"
    exit 1
}

# 함수: 정보 메시지
info() {
    echo -e "${YELLOW}ℹ${NC} $1"
}

# 1. Docker 설치 확인
info "Checking Docker installation..."
if ! command -v docker &> /dev/null; then
    error "Docker is not installed. Please install Docker first."
fi
success "Docker is installed"

# 2. Docker Compose 설치 확인
info "Checking Docker Compose installation..."
if ! command -v docker-compose &> /dev/null; then
    error "Docker Compose is not installed. Please install Docker Compose first."
fi
success "Docker Compose is installed"

# 3. NVIDIA Docker 지원 확인 (옵션)
info "Checking NVIDIA Docker support..."
if command -v nvidia-smi &> /dev/null; then
    success "NVIDIA GPU detected"
    GPU_SUPPORT="--gpus all"
else
    info "No NVIDIA GPU detected. Using CPU mode."
    GPU_SUPPORT=""
fi

# 4. 환경 변수 파일 생성
if [ ! -f .env ]; then
    info "Creating .env file from .env.example..."
    cp .env.example .env
    success "Created .env file. Please update it with your settings."
fi

# 5. 필요한 디렉토리 생성
info "Creating necessary directories..."
mkdir -p data outputs logs preprocessed_data models/ax_encoder_base temp_naviyam
success "Directories created"

# 6. Docker 이미지 빌드
info "Building Docker image..."
docker build -t naviyam-chatbot:latest . || error "Docker build failed"
success "Docker image built successfully"

# 7. 기존 컨테이너 정리 (있는 경우)
info "Cleaning up old containers..."
docker-compose down 2>/dev/null
success "Cleanup completed"

# 8. Docker Compose로 서비스 시작
info "Starting services with Docker Compose..."
docker-compose up -d || error "Failed to start services"
success "Services started"

# 9. 헬스체크
info "Waiting for services to be ready..."
sleep 10

# API 헬스체크
MAX_RETRIES=30
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -f http://localhost:8000/health 2>/dev/null; then
        echo ""
        success "API server is healthy"
        break
    else
        echo -n "."
        sleep 2
        RETRY_COUNT=$((RETRY_COUNT + 1))
    fi
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    error "API server health check failed"
fi

# 10. 서비스 정보 출력
echo ""
echo "========================================"
echo "Naviyam Chatbot is running!"
echo "========================================"
echo ""
echo "Services:"
echo "  - API Server: http://localhost:8000"
echo "  - API Docs: http://localhost:8000/docs"
echo "  - PostgreSQL: localhost:5432"
echo "  - Redis: localhost:6379"
echo ""
echo "Useful commands:"
echo "  - View logs: docker-compose logs -f naviyam-chatbot"
echo "  - Stop services: docker-compose down"
echo "  - Restart services: docker-compose restart"
echo "  - Shell access: docker exec -it naviyam-chatbot bash"
echo ""
echo "API Test:"
echo '  curl -X POST "http://localhost:8000/chat" \'
echo '    -H "Content-Type: application/json" \'
echo '    -H "X-API-Key: your-api-key-here" \'
echo '    -d '"'"'{"message": "안녕하세요", "user_id": "test"}'"'"
echo ""
success "Setup complete!"