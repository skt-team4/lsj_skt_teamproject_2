
import secrets
import os
from pydantic import BaseModel
from fastapi import Depends, FastAPI, HTTPException, status, UploadFile, File
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse
import shutil
import aiofiles
from google.cloud import storage

app = FastAPI(
    title="나비얌 챗봇 & 파일 서버 API",
    description="어린이를 위한 착한가게 추천 AI 챗봇과 파일 관리 서비스",
    version="1.0.0",
)

security = HTTPBasic()

class Message(BaseModel):
    text: str
    
class ChatRequest(BaseModel):
    message: str
    user_id: str = "guest"

class ChatResponse(BaseModel):
    response: str
    user_id: str
    timestamp: str
    recommendations: list = []

# --- Configuration ---
# WARNING: In a real application, use a more secure way to handle credentials
# (e.g., environment variables, a secrets management system).
USERNAME = os.environ.get("SERVER_USERNAME", "admin")
PASSWORD = os.environ.get("SERVER_PASSWORD", "password")

# Directory where your files are served from
STATIC_DIR = "publicdata"

# GCS Bucket for file storage
GCS_BUCKET_NAME = "rational-autumn-467006-e2-lsj-files"

my_data = ["initial_item_1", "initial_item_2"]

# --- Helper Function ---
def get_current_username(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = secrets.compare_digest(credentials.username, USERNAME)
    correct_password = secrets.compare_digest(credentials.password, PASSWORD)
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

# --- API Endpoints ---

@app.get("/files/{filename}", summary="Get a specific file")
async def get_file(filename: str, username: str = Depends(get_current_username)):
    """
    Retrieves a specific file from Google Cloud Storage after successful authentication.

    - **filename**: The name of the file to retrieve (e.g., `hot_dog.jpeg`).
    """
    client = storage.Client()
    bucket = client.get_bucket(GCS_BUCKET_NAME)
    blob = bucket.blob(filename)

    if not blob.exists():
        raise HTTPException(status_code=404, detail="File not found in GCS")

    # Download the file to a temporary location or directly stream it
    # For simplicity, we'll download to a temporary file and then return FileResponse
    # In a real application, consider streaming directly for large files
    temp_file_path = f"/tmp/{filename}"
    try:
        blob.download_to_filename(temp_file_path)
        return FileResponse(temp_file_path, media_type=blob.content_type)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not retrieve file from GCS: {e}")

@app.get("/files", summary="List all available files")
async def list_files(username: str = Depends(get_current_username)):
    """
    Lists all the files available in the Google Cloud Storage bucket.
    """
    client = storage.Client()
    bucket = client.get_bucket(GCS_BUCKET_NAME)
    blobs = bucket.list_blobs()
    files = [blob.name for blob in blobs]
    return JSONResponse(content={"files": files}, media_type="application/json; charset=utf-8")

@app.get("/files_html", summary="View files in HTML")
async def view_files_html():
    """
    Provides an HTML page to view the list of files.
    """
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>File List</title>
        <style>
            body { font-family: sans-serif; margin: 20px; }
            h1 { color: #333; }
            ul { list-style-type: none; padding: 0; }
            li { margin-bottom: 5px; }
            a { text-decoration: none; color: #007bff; }
            a:hover { text-decoration: underline; }
            #error { color: red; }
        </style>
    </head>
    <body>
        <h1>Files in GCS Bucket</h1>
        <p id="loading">Loading files...</p>
        <p id="error" style="display:none;"></p>
        <ul id="fileList"></ul>

        <script>
            async function fetchFiles() {
                const username = prompt("Enter username:");
                const password = prompt("Enter password:");

                if (!username || !password) {
                    document.getElementById('error').innerText = "Username and password are required.";
                    document.getElementById('error').style.display = 'block';
                    document.getElementById('loading').style.display = 'none';
                    return;
                }

                const headers = new Headers();
                headers.set('Authorization', 'Basic ' + btoa(username + ':' + password));

                try {
                    const response = await fetch('/files', { headers: headers });
                    document.getElementById('loading').style.display = 'none';

                    if (response.ok) {
                        const data = await response.json();
                        const fileList = document.getElementById('fileList');
                        if (data.files && data.files.length > 0) {
                            data.files.forEach(file => {
                                const listItem = document.createElement('li');
                                const link = document.createElement('a');
                                link.href = `/files/${file}`; // Link to download the file
                                link.textContent = file;
                                listItem.appendChild(link);
                                fileList.appendChild(listItem);
                            });
                        } else {
                            fileList.innerHTML = '<li>No files found in the bucket.</li>';
                        }
                    } else if (response.status === 401) {
                        document.getElementById('error').innerText = "Authentication failed. Please refresh and try again.";
                        document.getElementById('error').style.display = 'block';
                    } else {
                        document.getElementById('error').innerText = `Error: ${response.status} ${response.statusText}`;
                        document.getElementById('error').style.display = 'block';
                    }
                } catch (error) {
                    document.getElementById('loading').style.display = 'none';
                    document.getElementById('error').innerText = `Network error: ${error.message}`;
                    document.getElementById('error').style.display = 'block';
                }
            }
            fetchFiles();
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content, status_code=200)

# Mount the static directory to serve files directly (optional, but useful)
# This part is not protected by the authentication middleware.
# To protect it, you would need to implement a custom middleware.
# app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/")
def read_root():
    return JSONResponse(
        content={
            "message": "나비얌 챗봇 서버가 실행 중입니다! 🍗", 
            "services": ["파일 서버", "나비얌 챗봇"],
            "endpoints": {
                "chat": "/chat - 챗봇과 대화",
                "health": "/health - 서비스 상태 확인",
                "files": "/files - 파일 목록 조회",
                "docs": "/docs - API 문서"
            }
        },
        media_type="application/json; charset=utf-8"
    )

@app.post("/send")
def send_message(message: Message):
    return JSONResponse(
        content={"lsj received_message": message.text},
        media_type="application/json; charset=utf-8"
    )

@app.post("/uploadfile/", summary="Upload a file")
async def create_upload_file(
    file: UploadFile = File(...), username: str = Depends(get_current_username)
):
    """
    Uploads a file to Google Cloud Storage after successful authentication.

    - **file**: The file to upload.
    """
    client = storage.Client()
    bucket = client.get_bucket(GCS_BUCKET_NAME)
    blob = bucket.blob(file.filename)

    try:
        # Upload the file directly to GCS
        await blob.upload_from_file(file.file, content_type=file.content_type)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not upload file to GCS: {e}")
    finally:
        await file.close()
    return {"filename": file.filename, "message": "File uploaded successfully to GCS"}

@app.get("/info", summary="Get server information")
def get_info():
    """
    Returns a simple information message.
    """
    return {"info": "This is a functional endpoint on the LSJ server."}

@app.get("/data", summary="Get current data")
def get_data():
    """
    Returns the current in-memory data list.
    """
    return {"data": my_data}

@app.post("/data/add", summary="Add data to the list")
def add_data(item: str, username: str = Depends(get_current_username)):
    """
    Adds a new item to the in-memory data list. Requires authentication.

    - **item**: The string item to add.
    """
    my_data.append(item)
    return {"message": f"'{item}' added to data", "current_data": my_data}

@app.post("/chat", response_model=ChatResponse, summary="Chat with Naviyam Bot")
async def chat_with_bot(request: ChatRequest):
    """
    나비얌 챗봇과 대화합니다. 어린이를 위한 착한가게 추천 AI입니다.
    
    - **message**: 사용자 메시지
    - **user_id**: 사용자 ID (선택사항, 기본값: guest)
    """
    from datetime import datetime
    
    # 간단한 키워드 기반 응답
    message = request.message.lower()
    
    if "치킨" in message:
        response = "🍗 치킨이 먹고 싶으시군요! 근처 착한가게 치킨집을 찾아드릴게요."
        recommendations = ["BBQ치킨 (착한가게)", "교촌치킨 (할인가게)", "네네치킨 (깨끗한가게)"]
    elif "피자" in message:
        response = "🍕 피자가 땡기시는군요! 맛있는 피자집을 추천해드려요."
        recommendations = ["도미노피자 (할인중)", "피자헛 (가족세트)", "파파존스 (신선한재료)"]
    elif "안녕" in message or "hello" in message:
        response = "안녕하세요! 👋 나비얌 챗봇입니다. 어떤 음식이 드시고 싶으신가요?"
        recommendations = []
    elif "예산" in message or "돈" in message or "만원" in message:
        response = "💰 예산을 고려한 맛집을 찾아드릴게요! 착한가게 위주로 추천드려요."
        recommendations = ["1만원 이하 맛집", "2만원 이하 가성비", "3만원 이하 특별한날"]
    elif "hamburger" in message or "burger" in message or "햄버거" in message:
        response = "🍔 햄버거 맛집을 찾아드릴게요! 착한가게 인증받은 곳들이에요."
        recommendations = ["맥도날드 (착한가게)", "버거킹 (할인쿠폰)", "롯데리아 (세트메뉴)"]
    else:
        response = f"'{request.message}' 에 대해 검색 중이에요... 🔍 조금만 기다려주세요!"
        recommendations = ["추천 준비중"]
    
    return JSONResponse(
        content={
            "response": response,
            "user_id": request.user_id,
            "timestamp": datetime.now().isoformat(),
            "recommendations": recommendations
        },
        media_type="application/json; charset=utf-8"
    )

@app.get("/health", summary="Health Check")
def health_check():
    """
    서비스 상태를 확인합니다.
    """
    return JSONResponse(
        content={
            "status": "healthy", 
            "message": "나비얌 챗봇 서비스가 정상 동작 중입니다!", 
            "version": "1.0.0"
        },
        media_type="application/json; charset=utf-8"
    )

if __name__ == "__main__":
    import uvicorn
    print(f"Starting server. Access the API docs at http://127.0.0.1:8000/docs")
    print(f"Username: {USERNAME}")
    print(f"Password: {PASSWORD}")
    uvicorn.run(app, host="0.0.0.0", port=8080)
