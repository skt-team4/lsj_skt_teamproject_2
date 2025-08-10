# Naviyam Chatbot Docker Deployment Guide

## 📋 Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+
- NVIDIA Docker (for GPU support, optional)
- 최소 8GB RAM
- 20GB 이상의 디스크 공간

## 🚀 Quick Start

### 1. 환경 설정

```bash
# .env 파일 생성
cp .env.example .env

# .env 파일 편집하여 설정 수정
# API_KEY, DATABASE_URL 등 필요한 값 설정
```

### 2. Docker 이미지 빌드 및 실행

#### Linux/Mac:
```bash
chmod +x docker-build.sh
./docker-build.sh
```

#### Windows:
```cmd
docker-build.bat
```

### 3. 서비스 확인

- API Server: http://localhost:8000
- API Documentation: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

## 📦 Docker Compose 서비스

### 메인 서비스
- **naviyam-chatbot**: 챗봇 API 서버
- **postgres**: PostgreSQL 데이터베이스
- **redis**: Redis 캐시 서버

## 🔧 환경 변수

| 변수명 | 설명 | 기본값 |
|--------|------|--------|
| `NLU_TYPE` | NLU 모델 타입 | `ax_encoder` |
| `USE_4BIT` | 4-bit 양자화 사용 | `true` |
| `API_KEY` | API 인증 키 | `your-api-key-here` |
| `DATABASE_URL` | PostgreSQL 연결 문자열 | - |
| `REDIS_URL` | Redis 연결 문자열 | - |

## 📝 사용법

### API 테스트

```bash
# 채팅 요청
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key-here" \
  -d '{"message": "안녕하세요", "user_id": "test"}'
```

### 로그 확인

```bash
# 실시간 로그 확인
docker-compose logs -f naviyam-chatbot

# 특정 서비스 로그
docker-compose logs postgres
```

### 컨테이너 관리

```bash
# 서비스 중지
docker-compose down

# 서비스 재시작
docker-compose restart

# 컨테이너 쉘 접속
docker exec -it naviyam-chatbot bash
```

## 🔍 문제 해결

### GPU 사용 관련

GPU를 사용하려면:
1. NVIDIA Docker 설치
2. `docker-compose.yml`에서 GPU 설정 확인
3. `CUDA_VISIBLE_DEVICES` 환경변수 설정

### 메모리 부족

메모리가 부족한 경우:
1. `USE_4BIT=true` 설정으로 메모리 사용량 감소
2. Docker Desktop 메모리 할당 증가
3. 불필요한 서비스 제거

### 포트 충돌

포트가 이미 사용 중인 경우:
1. `.env` 파일에서 `API_PORT` 변경
2. `docker-compose.yml`에서 포트 매핑 수정

## 📊 모니터링

### Health Check

```bash
# API 헬스체크
curl http://localhost:8000/health

# Docker 헬스체크
docker-compose ps
```

### 리소스 사용량

```bash
# 컨테이너 리소스 확인
docker stats

# 상세 정보
docker-compose top
```

## 🔄 업데이트

### 코드 업데이트

```bash
# 코드 변경 후 재빌드
docker-compose build --no-cache
docker-compose up -d
```

### 모델 업데이트

모델 파일은 볼륨으로 마운트되므로:
1. 호스트의 `models/` 디렉토리에 새 모델 복사
2. 컨테이너 재시작

## 🛡️ 보안 권장사항

1. **API Key 설정**: 프로덕션 환경에서는 반드시 강력한 API 키 사용
2. **데이터베이스 비밀번호**: 기본 비밀번호 변경
3. **네트워크 격리**: 필요한 포트만 노출
4. **SSL/TLS**: 프로덕션 환경에서는 HTTPS 사용 권장

## 📁 디렉토리 구조

```
aiyam_chatbot_v2/
├── Dockerfile           # Docker 이미지 정의
├── docker-compose.yml   # 서비스 구성
├── .env                # 환경 변수
├── api_server.py       # FastAPI 서버
├── requirements.txt    # Python 의존성
├── data/              # 데이터 파일
├── models/            # 모델 파일
├── logs/              # 로그 파일
└── temp_naviyam/      # FAISS 인덱스
```

## 🆘 지원

문제가 발생하면:
1. 로그 확인: `docker-compose logs`
2. 컨테이너 상태 확인: `docker-compose ps`
3. 환경 변수 확인: `.env` 파일
4. GitHub Issues 또는 팀 채널로 문의