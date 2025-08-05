# Python 3.11 이미지 사용 (3.13은 아직 일부 패키지 호환성 문제)
FROM python:3.11-slim

# 작업 디렉토리 설정
WORKDIR /app

# 필수 패키지만 설치
COPY requirements_simple.txt .
RUN pip install --no-cache-dir -r requirements_simple.txt

# 앱 파일 복사
COPY chatbot_api_only.py .

# 포트 설정
EXPOSE 8080

# 앱 실행
CMD ["python", "chatbot_api_only.py"]