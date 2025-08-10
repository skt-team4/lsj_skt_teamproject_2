# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is the SKT Team Project repository containing multiple subprojects related to the "나비얌 (NabiYam)" food recommendation system for children. The project consists of a React Native mobile app, Python backend services with AI chatbot capabilities, and Google Cloud Platform deployment configurations.

## Key Components

### 1. Frontend - React Native Expo App
**Location**: `public_projects/ljm_skt_teamproject-main/`
- Mobile app built with React Native 0.79.5 and Expo ~53.0.20
- TypeScript-based with file-based routing using Expo Router
- Main chatbot interface in `app/chat.tsx`

### 2. Backend - Python AI Chatbot Service  
**Location**: `public_projects/naviyam_backend_runnable_20250806_112316/`
- FastAPI-based API server
- Integrates multiple AI models (A.X-3.1-Light, KoAlpaca)
- RAG (Retrieval Augmented Generation) system for restaurant recommendations
- Session management and user profiling
- Nutrition API integration

### 3. Cloud Services
- Google Cloud Platform deployment with Cloud Run
- Google Cloud Storage for file management
- Service URL: `https://naviyam-chatbot-904447394903.asia-northeast3.run.app`

## Common Development Commands

### Frontend (React Native App)
```bash
# Navigate to frontend directory
cd public_projects/ljm_skt_teamproject-main

# Install dependencies
npm install

# Run development server
npx expo start

# Platform-specific runs
npm run ios       # iOS simulator
npm run android   # Android emulator  
npm run web       # Web browser

# Code quality
npm run lint
```

### Backend (Python Services)
```bash
# Navigate to backend directory
cd public_projects/naviyam_backend_runnable_20250806_112316

# Install dependencies with minimal requirements
pip install -r requirements_minimal.txt

# Run the API server
PYTHONPATH=. python -m uvicorn api.server:app --host 0.0.0.0 --port 8000

# Test the API
python test_api.py
```

### Google Cloud Deployment
```bash
# Deploy to Cloud Run
gcloud run deploy nabiyam-main-app \
  --source . \
  --platform managed \
  --region asia-northeast3 \
  --allow-unauthenticated \
  --port 8080 \
  --memory 2Gi \
  --cpu 1 \
  --project rational-autumn-467006-e2

# View service status
gcloud run services list --project=rational-autumn-467006-e2

# Check VM instances
gcloud compute instances list --project=rational-autumn-467006-e2
```

## Architecture & Key Files

### Backend Architecture
- **API Layer**: `api/server.py` - FastAPI endpoints for chat and file operations
- **Core Logic**: `inference/chatbot.py` - Main chatbot orchestration
- **RAG System**: `rag/` - Document retrieval and vector store management
- **Models**: `models/` - AI model factories and configurations
- **Data**: `data/restaurants_optimized.json` - Restaurant database
- **Session Management**: `core/session_manager.py` - User session handling

### Frontend Architecture  
- **Navigation**: File-based routing in `app/` directory
- **Chat Interface**: `app/chat.tsx` - Main chatbot UI component
- **Tab Navigation**: `app/(tabs)/` - Bottom tab screens
- **Theme System**: `constants/Colors.ts` and themed components

### Data Flow
1. User input → Frontend chat interface
2. API request to `/chat` endpoint
3. Backend processes with NLU → Model inference → Response generation
4. RAG retrieval for restaurant recommendations
5. Response with recommendations → Frontend display

## API Endpoints

### Main Service Endpoints
- `GET /` - Service info
- `GET /health` - Health check
- `POST /chat` - Main chatbot interaction
- `GET /files` - List files (requires auth)
- `GET /files/{filename}` - Download file (requires auth)
- `POST /uploadfile/` - Upload file (requires auth)
- `GET /docs` - Swagger API documentation

### Authentication
File operations require Basic auth:
- Username: `admin`  
- Password: Set via environment variable or default

## Testing

### Backend Testing
```bash
# Run API tests
python test_api.py

# Test specific models
python test_ax_model.py
python test_mps.py
```

### Frontend Testing
```bash
# Lint checks
npm run lint

# Run on Expo Go (physical device)
# Scan QR code from expo start output
```

## Environment Variables

### Backend
- `SERVER_USERNAME` - Basic auth username
- `SERVER_PASSWORD` - Basic auth password
- `PYTHONPATH` - Set to project root for module imports

### Frontend
- Configure in `.env` file for API endpoints
- Use `react-native-dotenv` for environment management

## Important Notes

- Backend requires Python 3.8+ with PyTorch and transformers
- Frontend requires Node.js 18+ and npm/yarn
- Google Cloud SDK (`gcloud`) required for deployments
- Models are cached in `cache/models/` directory
- User profiles stored in `outputs/user_profiles/`
- Conversation logs in `outputs/conversation_logs/`

## GCP Resources
- **Project ID**: `rational-autumn-467006-e2`
- **Region**: `asia-northeast3` (Seoul)
- **Services**: Cloud Run, Cloud Storage, Compute Engine
- **Storage Bucket**: `rational-autumn-467006-e2-lsj-files`