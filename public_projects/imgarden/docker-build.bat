@echo off
REM Naviyam Chatbot Docker Build Script for Windows

echo ========================================
echo Naviyam Chatbot Docker Build (Windows)
echo ========================================
echo.

REM 1. Docker 설치 확인
echo Checking Docker installation...
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Docker is not installed or not in PATH.
    echo Please install Docker Desktop for Windows.
    pause
    exit /b 1
)
echo [OK] Docker is installed
echo.

REM 2. Docker Compose 설치 확인
echo Checking Docker Compose installation...
docker-compose --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Docker Compose is not installed.
    pause
    exit /b 1
)
echo [OK] Docker Compose is installed
echo.

REM 3. NVIDIA GPU 확인
echo Checking GPU support...
nvidia-smi >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] NVIDIA GPU detected
    set GPU_SUPPORT=--gpus all
) else (
    echo [INFO] No NVIDIA GPU detected. Using CPU mode.
    set GPU_SUPPORT=
)
echo.

REM 4. 환경 변수 파일 생성
if not exist .env (
    echo Creating .env file from .env.example...
    copy .env.example .env >nul
    echo [OK] Created .env file. Please update it with your settings.
) else (
    echo [OK] .env file already exists
)
echo.

REM 5. 필요한 디렉토리 생성
echo Creating necessary directories...
if not exist data mkdir data
if not exist outputs mkdir outputs
if not exist logs mkdir logs
if not exist preprocessed_data mkdir preprocessed_data
if not exist models\ax_encoder_base mkdir models\ax_encoder_base
if not exist temp_naviyam mkdir temp_naviyam
echo [OK] Directories created
echo.

REM 6. Docker 이미지 빌드
echo Building Docker image...
docker build -t naviyam-chatbot:latest .
if %errorlevel% neq 0 (
    echo [ERROR] Docker build failed
    pause
    exit /b 1
)
echo [OK] Docker image built successfully
echo.

REM 7. 기존 컨테이너 정리
echo Cleaning up old containers...
docker-compose down >nul 2>&1
echo [OK] Cleanup completed
echo.

REM 8. Docker Compose로 서비스 시작
echo Starting services with Docker Compose...
docker-compose up -d
if %errorlevel% neq 0 (
    echo [ERROR] Failed to start services
    pause
    exit /b 1
)
echo [OK] Services started
echo.

REM 9. 헬스체크
echo Waiting for services to be ready...
timeout /t 10 /nobreak >nul

set MAX_RETRIES=30
set RETRY_COUNT=0

:health_check_loop
if %RETRY_COUNT% geq %MAX_RETRIES% (
    echo [ERROR] API server health check failed
    pause
    exit /b 1
)

curl -f http://localhost:8000/health >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] API server is healthy
    goto :health_check_done
)

timeout /t 2 /nobreak >nul
set /a RETRY_COUNT=%RETRY_COUNT%+1
goto :health_check_loop

:health_check_done
echo.

REM 10. 서비스 정보 출력
echo ========================================
echo Naviyam Chatbot is running!
echo ========================================
echo.
echo Services:
echo   - API Server: http://localhost:8000
echo   - API Docs: http://localhost:8000/docs
echo   - PostgreSQL: localhost:5432
echo   - Redis: localhost:6379
echo.
echo Useful commands:
echo   - View logs: docker-compose logs -f naviyam-chatbot
echo   - Stop services: docker-compose down
echo   - Restart services: docker-compose restart
echo   - Shell access: docker exec -it naviyam-chatbot bash
echo.
echo API Test:
echo   curl -X POST "http://localhost:8000/chat" ^
echo     -H "Content-Type: application/json" ^
echo     -H "X-API-Key: your-api-key-here" ^
echo     -d "{\"message\": \"안녕하세요\", \"user_id\": \"test\"}"
echo.
echo [OK] Setup complete!
echo.
pause