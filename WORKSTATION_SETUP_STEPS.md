# 🖥️ 워크스테이션 세팅 가이드

## Step 1: 기본 환경 확인 및 설치

### Windows 워크스테이션
```powershell
# 1. Python 설치 (3.8~3.10 권장)
# https://www.python.org/downloads/ 에서 다운로드
# ✅ "Add Python to PATH" 체크 필수!

# 2. 설치 확인
python --version
pip --version

# 3. GPU 있는 경우 - NVIDIA 드라이버 확인
nvidia-smi
# 출력되면 GPU 사용 가능
```

### Linux/Ubuntu 워크스테이션
```bash
# 1. Python 설치
sudo apt update
sudo apt install python3 python3-pip python3-venv

# 2. GPU 있는 경우 - NVIDIA 드라이버 설치
sudo apt install nvidia-driver-525
sudo reboot
nvidia-smi  # 재부팅 후 확인
```

### Mac 워크스테이션
```bash
# 1. Homebrew 설치 (없는 경우)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 2. Python 설치
brew install python@3.10

# 3. 확인
python3 --version
```

---

## Step 2: 프로젝트 파일 가져오기

### 방법 A: Git Clone (권장)
```bash
# 워크스테이션 터미널에서
cd ~
git clone https://github.com/your-repo/skt_teamproject.git
cd skt_teamproject
```

### 방법 B: 파일 직접 복사
```bash
# 필요한 파일만 복사
# 1. gpu_server.py 파일을 워크스테이션에 생성
# 2. 아래 내용 복사
```

**gpu_server.py 내용:**
```python
import torch
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Naviyam GPU Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str
    user_id: str = "default"
    session_id: str = "default"

class ChatResponse(BaseModel):
    response: str
    recommendations: list = []

@app.get("/")
def root():
    return {
        "service": "Naviyam GPU Server",
        "gpu": torch.cuda.is_available()
    }

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "gpu_available": torch.cuda.is_available()
    }

@app.post("/chat")
async def chat(request: ChatRequest):
    # 간단한 응답 (모델 없이)
    return ChatResponse(
        response=f"[서버 응답] {request.message}에 대한 답변입니다.",
        recommendations=["김밥", "떡볶이", "라면"]
    )

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

---

## Step 3: Python 환경 설정

### Windows
```powershell
# PowerShell 또는 CMD에서
cd C:\Users\YourName\skt_teamproject

# 가상환경 생성
python -m venv naviyam_env

# 가상환경 활성화
naviyam_env\Scripts\activate

# 패키지 설치
pip install fastapi uvicorn torch transformers
```

### Linux/Mac
```bash
cd ~/skt_teamproject

# 가상환경 생성
python3 -m venv naviyam_env

# 가상환경 활성화
source naviyam_env/bin/activate

# 패키지 설치
pip install fastapi uvicorn torch transformers
```

---

## Step 4: AI 서버 실행

```bash
# 가상환경 활성화 상태에서
python gpu_server.py
```

성공하면 이렇게 출력됩니다:
```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### 브라우저에서 확인
1. http://localhost:8000 접속
2. 다음과 같은 JSON 응답 확인:
```json
{
  "service": "Naviyam GPU Server",
  "gpu": true  // 또는 false
}
```

---

## Step 5: 외부 접속 설정 (ngrok)

### ngrok 설치

#### Windows
```powershell
# 1. https://ngrok.com/download 에서 다운로드
# 2. ngrok.exe를 C:\ngrok\ 폴더에 저장
# 3. 환경변수 PATH에 C:\ngrok 추가

# 또는 Chocolatey 사용
choco install ngrok
```

#### Linux
```bash
# Snap 사용
sudo snap install ngrok

# 또는 직접 다운로드
wget https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-amd64.tgz
tar xvzf ngrok-v3-stable-linux-amd64.tgz
sudo mv ngrok /usr/local/bin/
```

#### Mac
```bash
brew install ngrok
```

### ngrok 실행
```bash
# 새 터미널 창에서
ngrok http 8000
```

출력 예시:
```
Session Status                online
Account                       your-email@example.com (Plan: Free)
Version                       3.3.0
Region                        United States (us)
Latency                       32ms
Web Interface                 http://127.0.0.1:4040
Forwarding                    https://abc123xyz.ngrok-free.app -> http://localhost:8000
```

**중요: `https://abc123xyz.ngrok-free.app` 이 URL을 복사하세요!**

---

## Step 6: 테스트

### 로컬 테스트
```bash
# 새 터미널에서
curl http://localhost:8000/health
```

### 외부 접속 테스트
```bash
# ngrok URL 사용
curl https://abc123xyz.ngrok-free.app/health
```

### Python으로 테스트
```python
# test.py
import requests

# 로컬 테스트
response = requests.post(
    "http://localhost:8000/chat",
    json={"message": "안녕하세요"}
)
print("로컬:", response.json())

# ngrok 테스트
response = requests.post(
    "https://abc123xyz.ngrok-free.app/chat",
    json={"message": "안녕하세요"}
)
print("외부:", response.json())
```

---

## Step 7: Cloud Run 연동

ngrok URL을 받았으면, Cloud Run 서비스에 설정:

```bash
gcloud run services update nabiyam-chatbot-web \
  --set-env-vars GPU_SERVER_URL=https://abc123xyz.ngrok-free.app \
  --region asia-northeast3 \
  --project rational-autumn-467006-e2
```

---

## 🔧 트러블슈팅

### "python이 인식되지 않습니다" (Windows)
```powershell
# Python 경로 직접 사용
C:\Users\YourName\AppData\Local\Programs\Python\Python310\python.exe gpu_server.py
```

### "포트 8000이 이미 사용 중"
```bash
# 다른 포트 사용
python gpu_server.py --port 8001
ngrok http 8001
```

### "CUDA not available" 
→ GPU 없거나 드라이버 미설치. CPU로 작동합니다.

### ngrok 세션 종료 (2시간)
→ https://ngrok.com 무료 가입 후 인증 토큰 설정:
```bash
ngrok config add-authtoken YOUR_AUTH_TOKEN
```

---

## ✅ 최종 체크리스트

- [ ] Python 3.8+ 설치됨
- [ ] gpu_server.py 파일 생성됨
- [ ] 가상환경 생성 및 활성화됨
- [ ] 패키지 설치 완료 (fastapi, uvicorn, torch)
- [ ] 서버 실행됨 (http://localhost:8000)
- [ ] ngrok 설치 및 실행됨
- [ ] 외부 URL 획득 (https://xxx.ngrok-free.app)
- [ ] Cloud Run에 URL 설정됨

---

## 📌 서버 유지 관리

### 서버 시작 (매번)
```bash
# 터미널 1
cd ~/skt_teamproject
source naviyam_env/bin/activate  # Linux/Mac
# 또는
naviyam_env\Scripts\activate  # Windows
python gpu_server.py

# 터미널 2
ngrok http 8000
```

### 자동 시작 설정 (선택사항)
Windows: 작업 스케줄러 사용
Linux: systemd 서비스 생성
Mac: launchd 사용