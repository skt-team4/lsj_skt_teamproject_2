@echo off
echo ========================================
echo   ����� ê�� �鿣�� ����
echo ========================================
echo.

REM Python Ȯ��
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python�� ��ġ�Ǿ� ���� �ʽ��ϴ�!
    echo Python 3.8 �̻��� ��ġ���ּ���.
    pause
    exit /b 1
)

echo [1/3] ������ Ȯ�� �� ��ġ...
pip install -q -r requirements.txt

echo [2/3] ���� ���� ��...
echo.
echo ** ù ����� �� �ٿ�ε�� 5-10�� �ҿ�� �� �ֽ��ϴ� **
echo.

echo [3/3] API ���� ����...
python api/server.py

pause
