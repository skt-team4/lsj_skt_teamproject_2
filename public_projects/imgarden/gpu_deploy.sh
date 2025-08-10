#!/bin/bash

# GPU 서버에서 실행할 스크립트
echo "🚀 GPU 서버에 챗봇 배포 중..."

# Docker 이미지 pull (간단한 테스트용 이미지)
echo "Docker 이미지 다운로드..."
sudo docker pull pytorch/pytorch:2.3.0-cuda11.8-cudnn8-runtime

# 챗봇 컨테이너 실행
echo "챗봇 컨테이너 시작..."
sudo docker run -d \
  --name naviyam-gpu-test \
  --gpus all \
  -p 8000:8000 \
  -e CUDA_VISIBLE_DEVICES=0 \
  pytorch/pytorch:2.3.0-cuda11.8-cudnn8-runtime \
  python -c "
import torch
from http.server import HTTPServer, BaseHTTPRequestHandler
import json

class ChatbotHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            # GPU 정보 확인
            gpu_available = torch.cuda.is_available()
            gpu_name = torch.cuda.get_device_name(0) if gpu_available else 'No GPU'
            gpu_memory = f'{torch.cuda.get_device_properties(0).total_memory / 1e9:.2f} GB' if gpu_available else 'N/A'
            
            response = {
                'status': 'healthy',
                'message': 'GPU 서버에서 실행 중!',
                'gpu': {
                    'available': gpu_available,
                    'name': gpu_name,
                    'memory': gpu_memory
                }
            }
            self.wfile.write(json.dumps(response).encode())
    
    def do_POST(self):
        if self.path == '/chat':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data)
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            # GPU에서 간단한 텐서 연산 수행
            if torch.cuda.is_available():
                device = torch.device('cuda')
                tensor = torch.randn(1000, 1000).to(device)
                result = torch.matmul(tensor, tensor)
                gpu_used = True
            else:
                gpu_used = False
            
            response = {
                'response': f'GPU 서버입니다! 메시지 \"{data.get(\"message\", \"\")}\" 받았습니다.',
                'gpu_used': gpu_used,
                'server_type': 'GPU Instance (T4)'
            }
            self.wfile.write(json.dumps(response).encode())

print('🚀 GPU 챗봇 서버 시작 (포트 8000)...')
print(f'GPU 사용 가능: {torch.cuda.is_available()}')
if torch.cuda.is_available():
    print(f'GPU 이름: {torch.cuda.get_device_name(0)}')

server = HTTPServer(('0.0.0.0', 8000), ChatbotHandler)
server.serve_forever()
"

echo "✅ 배포 완료!"
echo "테스트: curl http://localhost:8000/health"