#!/usr/bin/env python3
"""MPS 테스트 및 간단한 모델 실행"""

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

print("=" * 50)
print("Apple Silicon GPU (MPS) 테스트")
print("=" * 50)

# MPS 확인
print(f"\n1. MPS 상태:")
print(f"   - PyTorch 버전: {torch.__version__}")
print(f"   - MPS 사용 가능: {torch.backends.mps.is_available()}")
print(f"   - MPS 빌드됨: {torch.backends.mps.is_built()}")

# 디바이스 설정
if torch.backends.mps.is_available():
    device = torch.device("mps")
    print(f"   - 사용 디바이스: MPS (Metal GPU)")
else:
    device = torch.device("cpu")
    print(f"   - 사용 디바이스: CPU")

# 간단한 텐서 연산 테스트
print(f"\n2. 텐서 연산 테스트:")
x = torch.randn(1000, 1000).to(device)
y = torch.randn(1000, 1000).to(device)

import time
start = time.time()
z = torch.matmul(x, y)
end = time.time()

print(f"   - 1000x1000 행렬곱 시간: {end-start:.4f}초")
print(f"   - 결과 shape: {z.shape}")
print(f"   - 디바이스: {z.device}")

# 간단한 모델 테스트 (선택사항)
print(f"\n3. 작은 모델 로드 테스트:")
try:
    # 매우 작은 GPT2 모델 사용
    model_name = "gpt2"
    print(f"   - 모델: {model_name}")
    
    # bitsandbytes 없이 일반 로드
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        torch_dtype=torch.float16 if device.type == "mps" else torch.float32,
        low_cpu_mem_usage=True
    ).to(device)
    
    print(f"   - 모델 로드 성공!")
    print(f"   - 모델 디바이스: {next(model.parameters()).device}")
    
    # 간단한 추론
    text = "Hello, my name is"
    inputs = tokenizer(text, return_tensors="pt").to(device)
    
    with torch.no_grad():
        outputs = model.generate(**inputs, max_length=20)
    
    result = tokenizer.decode(outputs[0], skip_special_tokens=True)
    print(f"   - 입력: '{text}'")
    print(f"   - 출력: '{result}'")
    
except Exception as e:
    print(f"   - 모델 로드 실패: {e}")

print("\n" + "=" * 50)
print("테스트 완료!")
print("=" * 50)