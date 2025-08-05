# 나비얌 챗봇 & 파일 서버 이용 가이드 🍗

**배포된 서비스**: https://naviyam-chatbot-904447394903.asia-northeast3.run.app

---

## 📋 목차

1. [서비스 개요](#서비스-개요)
2. [기본 정보 확인](#기본-정보-확인)
3. [나비얌 챗봇 사용법](#나비얌-챗봇-사용법)
4. [파일 서버 사용법](#파일-서버-사용법)
5. [API 문서](#api-문서)
6. [예제 코드](#예제-코드)
7. [문제 해결](#문제-해결)

---

## 🌟 서비스 개요

이 서비스는 **두 가지 주요 기능**을 제공합니다:

1. **🍗 나비얌 챗봇**: 어린이를 위한 착한가게 추천 AI 챗봇
2. **📁 파일 서버**: Google Cloud Storage를 활용한 파일 관리 서비스

---

## 🔍 기본 정보 확인

### 서비스 상태 확인

```bash
curl https://naviyam-chatbot-904447394903.asia-northeast3.run.app/health
```

**응답 예시:**
```json
{
  "status": "healthy",
  "message": "나비얌 챗봇 서비스가 정상 동작 중입니다!",
  "version": "1.0.0"
}
```

### 서비스 정보 조회

```bash
curl https://naviyam-chatbot-904447394903.asia-northeast3.run.app/
```

**응답 예시:**
```json
{
  "message": "나비얌 챗봇 서버가 실행 중입니다! 🍗",
  "services": ["파일 서버", "나비얌 챗봇"],
  "endpoints": {
    "chat": "/chat - 챗봇과 대화",
    "health": "/health - 서비스 상태 확인", 
    "files": "/files - 파일 목록 조회",
    "docs": "/docs - API 문서"
  }
}
```

---

## 🍗 나비얌 챗봇 사용법

### 기본 대화

**엔드포인트**: `POST /chat`

**요청 형식:**
```json
{
  "message": "사용자 메시지",
  "user_id": "사용자 ID (선택사항, 기본값: guest)"
}
```

### 💬 대화 예시

#### 1. 인사하기
```bash
curl -X POST "https://naviyam-chatbot-904447394903.asia-northeast3.run.app/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "안녕하세요", "user_id": "test_user"}'
```

**응답:**
```json
{
  "response": "안녕하세요! 👋 나비얌 챗봇입니다. 어떤 음식이 드시고 싶으신가요?",
  "user_id": "test_user",
  "timestamp": "2025-07-31T04:17:43.320542",
  "recommendations": []
}
```

#### 2. 치킨 추천 요청
```bash
curl -X POST "https://naviyam-chatbot-904447394903.asia-northeast3.run.app/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "치킨 먹고 싶어", "user_id": "test_user"}'
```

**응답:**
```json
{
  "response": "🍗 치킨이 먹고 싶으시군요! 근처 착한가게 치킨집을 찾아드릴게요.",
  "user_id": "test_user",
  "timestamp": "2025-07-31T04:17:50.691268",
  "recommendations": [
    "BBQ치킨 (착한가게)",
    "교촌치킨 (할인가게)",
    "네네치킨 (깨끗한가게)"
  ]
}
```

#### 3. 햄버거 추천 (영어 키워드)
```bash
curl -X POST "https://naviyam-chatbot-904447394903.asia-northeast3.run.app/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "hamburger 먹고 싶어", "user_id": "test_user"}'
```

**응답:**
```json
{
  "response": "🍔 햄버거 맛집을 찾아드릴게요! 착한가게 인증받은 곳들이에요.",
  "user_id": "test_user", 
  "timestamp": "2025-07-31T04:17:50.691268",
  "recommendations": [
    "맥도날드 (착한가게)",
    "버거킹 (할인쿠폰)",
    "롯데리아 (세트메뉴)"
  ]
}
```

#### 4. 예산 문의
```bash
curl -X POST "https://naviyam-chatbot-904447394903.asia-northeast3.run.app/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "1만원으로 뭐 먹을까", "user_id": "test_user"}'
```

**응답:**
```json
{
  "response": "💰 예산을 고려한 맛집을 찾아드릴게요! 착한가게 위주로 추천드려요.",
  "user_id": "test_user",
  "timestamp": "2025-07-31T04:17:50.691268", 
  "recommendations": [
    "1만원 이하 맛집",
    "2만원 이하 가성비", 
    "3만원 이하 특별한날"
  ]
}
```

### 🎯 지원하는 키워드

| 키워드 | 설명 | 예시 |
|--------|------|------|
| **치킨** | 치킨 전문점 추천 | "치킨 먹고 싶어" |
| **피자** | 피자 전문점 추천 | "피자 주문하고 싶어" |
| **hamburger, burger, 햄버거** | 햄버거 전문점 추천 | "hamburger 먹고 싶어" |
| **예산, 돈, 만원** | 예산별 맛집 추천 | "2만원으로 먹을 수 있는 곳" |
| **안녕, hello** | 인사 및 서비스 소개 | "안녕하세요" |

---

## 📁 파일 서버 사용법

### 🔐 인증 정보

파일 서버 기능은 **Basic 인증**이 필요합니다:
- **사용자명**: `admin`
- **비밀번호**: `naviyam123`

### 파일 목록 조회

```bash
curl -u admin:naviyam123 \
  "https://naviyam-chatbot-904447394903.asia-northeast3.run.app/files"
```

**응답 예시:**
```json
{
  "files": [
    "cool_cat.Mov",
    "example.html", 
    "hot_dog.jpeg",
    "pixel_dog.gif",
    "sample.json",
    "test.csv",
    "test.txt",
    "한글_데이터_테스트.txt"
  ]
}
```

### 특정 파일 다운로드

```bash
curl -u admin:naviyam123 \
  "https://naviyam-chatbot-904447394903.asia-northeast3.run.app/files/sample.json" \
  -o downloaded_sample.json
```

### 파일 업로드

```bash
curl -u admin:naviyam123 \
  -X POST "https://naviyam-chatbot-904447394903.asia-northeast3.run.app/uploadfile/" \
  -F "file=@/path/to/your/file.txt"
```

**응답 예시:**
```json
{
  "filename": "file.txt",
  "message": "File uploaded successfully to GCS"
}
```

### 웹 브라우저에서 파일 목록 보기

브라우저에서 다음 URL 접속:
```
https://naviyam-chatbot-904447394903.asia-northeast3.run.app/files_html
```

프롬프트가 나타나면:
- **사용자명**: `admin`
- **비밀번호**: `naviyam123`

---

## 📚 API 문서

### Swagger UI 접속

브라우저에서 다음 URL로 접속하면 상세한 API 문서를 확인할 수 있습니다:

```
https://naviyam-chatbot-904447394903.asia-northeast3.run.app/docs
```

### API 엔드포인트 요약

| Method | Endpoint | 설명 | 인증 필요 |
|--------|----------|------|-----------|
| `GET` | `/` | 서비스 정보 조회 | ❌ |
| `GET` | `/health` | 헬스체크 | ❌ |
| `POST` | `/chat` | 챗봇 대화 | ❌ |
| `GET` | `/docs` | API 문서 | ❌ |
| `GET` | `/files` | 파일 목록 조회 | ✅ |
| `GET` | `/files/{filename}` | 파일 다운로드 | ✅ |
| `GET` | `/files_html` | 웹 파일 브라우저 | ❌ |
| `POST` | `/uploadfile/` | 파일 업로드 | ✅ |
| `POST` | `/send` | 메시지 전송 (레거시) | ❌ |
| `GET` | `/info` | 서버 정보 | ❌ |
| `GET` | `/data` | 데이터 조회 | ❌ |
| `POST` | `/data/add` | 데이터 추가 | ✅ |

---

## 💻 예제 코드

### Python 예제

```python
import requests
import json

# 서비스 URL
BASE_URL = "https://naviyam-chatbot-904447394903.asia-northeast3.run.app"

def chat_with_naviyam(message, user_id="python_user"):
    """나비얌 챗봇과 대화"""
    url = f"{BASE_URL}/chat"
    data = {
        "message": message,
        "user_id": user_id
    }
    
    response = requests.post(url, json=data)
    return response.json()

def check_health():
    """서비스 상태 확인"""
    url = f"{BASE_URL}/health"
    response = requests.get(url)
    return response.json()

def get_file_list():
    """파일 목록 조회 (인증 필요)"""
    url = f"{BASE_URL}/files"
    auth = ("admin", "naviyam123")
    
    response = requests.get(url, auth=auth)
    return response.json()

# 사용 예시
if __name__ == "__main__":
    # 헬스체크
    health = check_health()
    print("서비스 상태:", health)
    
    # 챗봇과 대화
    response = chat_with_naviyam("치킨 먹고 싶어")
    print("챗봇 응답:", response["response"])
    print("추천 목록:", response["recommendations"])
    
    # 파일 목록 조회
    files = get_file_list()
    print("사용 가능한 파일:", files["files"])
```

### JavaScript 예제

```javascript
const BASE_URL = "https://naviyam-chatbot-904447394903.asia-northeast3.run.app";

// 챗봇과 대화
async function chatWithNaviyam(message, userId = "js_user") {
    const response = await fetch(`${BASE_URL}/chat`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            message: message,
            user_id: userId
        })
    });
    
    return await response.json();
}

// 서비스 상태 확인
async function checkHealth() {
    const response = await fetch(`${BASE_URL}/health`);
    return await response.json();
}

// 파일 목록 조회 (인증 필요)
async function getFileList() {
    const credentials = btoa('admin:naviyam123');
    const response = await fetch(`${BASE_URL}/files`, {
        headers: {
            'Authorization': `Basic ${credentials}`
        }
    });
    
    return await response.json();
}

// 사용 예시
(async () => {
    // 헬스체크
    const health = await checkHealth();
    console.log("서비스 상태:", health);
    
    // 챗봇과 대화
    const chatResponse = await chatWithNaviyam("피자 먹고 싶어");
    console.log("챗봇 응답:", chatResponse.response);
    console.log("추천 목록:", chatResponse.recommendations);
    
    // 파일 목록 조회
    const files = await getFileList();
    console.log("사용 가능한 파일:", files.files);
})();
```

### HTML 페이지 예제

```html
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>나비얌 챗봇 테스트</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
        .chat-container { border: 1px solid #ddd; padding: 20px; margin: 20px 0; border-radius: 8px; }
        .message { margin: 10px 0; padding: 10px; border-radius: 5px; }
        .user-message { background-color: #e3f2fd; text-align: right; }
        .bot-message { background-color: #f1f8e9; }
        input[type="text"] { width: 70%; padding: 10px; }
        button { padding: 10px 20px; margin-left: 10px; }
        .recommendations { margin-top: 10px; }
        .recommendation-item { 
            display: inline-block; 
            background-color: #fff3e0; 
            padding: 5px 10px; 
            margin: 2px; 
            border-radius: 15px; 
            border: 1px solid #ffcc02;
        }
    </style>
</head>
<body>
    <h1>🍗 나비얌 챗봇 테스트</h1>
    
    <div class="chat-container">
        <div id="chatMessages"></div>
        <div>
            <input type="text" id="messageInput" placeholder="메시지를 입력하세요..." onkeypress="handleKeyPress(event)">
            <button onclick="sendMessage()">전송</button>
        </div>
    </div>

    <script>
        const BASE_URL = "https://naviyam-chatbot-904447394903.asia-northeast3.run.app";
        
        async function sendMessage() {
            const input = document.getElementById('messageInput');
            const message = input.value.trim();
            
            if (!message) return;
            
            // 사용자 메시지 표시
            addMessage(message, 'user');
            input.value = '';
            
            try {
                // 챗봇에 메시지 전송
                const response = await fetch(`${BASE_URL}/chat`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        message: message,
                        user_id: "web_user"
                    })
                });
                
                const data = await response.json();
                
                // 챗봇 응답 표시
                addMessage(data.response, 'bot', data.recommendations);
                
            } catch (error) {
                addMessage('죄송합니다. 오류가 발생했습니다.', 'bot');
                console.error('Error:', error);
            }
        }
        
        function addMessage(text, sender, recommendations = []) {
            const messagesDiv = document.getElementById('chatMessages');
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${sender}-message`;
            
            let content = `<strong>${sender === 'user' ? '나' : '나비얌'}:</strong> ${text}`;
            
            if (recommendations && recommendations.length > 0) {
                content += '<div class="recommendations">';
                recommendations.forEach(rec => {
                    content += `<span class="recommendation-item">${rec}</span>`;
                });
                content += '</div>';
            }
            
            messageDiv.innerHTML = content;
            messagesDiv.appendChild(messageDiv);
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        }
        
        function handleKeyPress(event) {
            if (event.key === 'Enter') {
                sendMessage();
            }
        }
        
        // 초기 인사 메시지
        window.onload = function() {
            addMessage('안녕하세요! 나비얌 챗봇입니다. 어떤 음식이 드시고 싶으신가요? 🍗', 'bot');
        };
    </script>
</body>
</html>
```

---

## 🔧 문제 해결

### 일반적인 문제

#### 1. 403 Forbidden 오류
**문제**: API 호출 시 403 오류 발생  
**해결**: 파일 관련 엔드포인트는 Basic 인증이 필요합니다.
```bash
curl -u admin:naviyam123 "https://naviyam-chatbot-904447394903.asia-northeast3.run.app/files"
```

#### 2. 챗봇이 응답하지 않음
**문제**: `/chat` 엔드포인트에 POST 요청을 했지만 응답이 없음  
**해결**: 
1. Content-Type 헤더 확인: `Content-Type: application/json`
2. 요청 본문 형식 확인: `{"message": "메시지", "user_id": "사용자ID"}`

#### 3. 파일 업로드 실패
**문제**: 파일 업로드 시 오류 발생  
**해결**:
1. 인증 정보 확인 (admin:naviyam123)
2. multipart/form-data 형식으로 전송
3. 'file' 필드명 사용

### 서비스 상태 확인

서비스에 문제가 있다고 생각되면 헬스체크를 먼저 수행해보세요:

```bash
curl https://naviyam-chatbot-904447394903.asia-northeast3.run.app/health
```

정상적인 응답:
```json
{"status": "healthy", "message": "나비얌 챗봇 서비스가 정상 동작 중입니다!", "version": "1.0.0"}
```

### 로그 확인

Cloud Run 서비스의 로그를 확인하려면:
```bash
gcloud logs read --service=naviyam-chatbot --region=asia-northeast3 --limit=50
```

---

## 📞 지원 및 문의

- **서비스 URL**: https://naviyam-chatbot-904447394903.asia-northeast3.run.app
- **API 문서**: https://naviyam-chatbot-904447394903.asia-northeast3.run.app/docs
- **프로젝트**: aimovietalk (Google Cloud)
- **지역**: asia-northeast3 (Seoul)

---

**마지막 업데이트**: 2025년 7월 31일  
**버전**: 1.0.0

Made with ❤️ by Naviyam Team 🍗