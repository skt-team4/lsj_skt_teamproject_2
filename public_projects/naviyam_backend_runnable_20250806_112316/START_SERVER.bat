@echo off
echo ========================================
echo   나비얌 챗봇 백엔드 서버
echo ========================================
echo.

REM Python 확인
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python이 설치되어 있지 않습니다!
    echo Python 3.8 이상을 설치해주세요.
    pause
    exit /b 1
)

echo [1/3] 의존성 확인 및 설치...
pip install -q -r requirements.txt

echo [2/3] 서버 시작 중...
echo.
echo ** 첫 실행시 모델 다운로드로 5-10분 소요될 수 있습니다 **
echo.

echo [3/3] API 서버 실행...
python api/server.py

pause
