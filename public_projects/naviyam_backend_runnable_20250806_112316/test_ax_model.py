#!/usr/bin/env python3
"""A.X 3.1 Lite 모델 로드 테스트 - MPS 사용"""

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
import os

print("=" * 60)
print("SKT A.X 3.1 Lite 모델 로드 테스트")
print("=" * 60)

# MPS 확인
device = "mps" if torch.backends.mps.is_available() else "cpu"
print(f"\n사용 디바이스: {device}")
print(f"MPS 사용 가능: {torch.backends.mps.is_available()}")

# 모델 정보
model_name = "skt/ax-llm-3.1-8b"  # 또는 실제 경로
print(f"\n모델: {model_name}")

try:
    print("\n1. 토크나이저 로드 중...")
    tokenizer = AutoTokenizer.from_pretrained(
        model_name,
        trust_remote_code=True
    )
    print("   ✓ 토크나이저 로드 성공")
    
    print("\n2. 모델 로드 중 (시간이 걸릴 수 있습니다)...")
    print("   - bitsandbytes 없이 float16으로 로드 시도")
    
    # MPS용 설정 (bitsandbytes 없이)
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        torch_dtype=torch.float16,  # MPS는 float16 지원
        device_map={"": device},     # 직접 MPS로 매핑
        trust_remote_code=True,
        low_cpu_mem_usage=True,
    )
    
    print("   ✓ 모델 로드 성공!")
    print(f"   - 모델 크기: {sum(p.numel() for p in model.parameters()) / 1e9:.2f}B 파라미터")
    
    # 간단한 추론 테스트
    print("\n3. 추론 테스트...")
    text = "안녕하세요, 오늘 날씨가"
    inputs = tokenizer(text, return_tensors="pt").to(device)
    
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=30,
            temperature=0.7,
            do_sample=True,
            pad_token_id=tokenizer.eos_token_id
        )
    
    result = tokenizer.decode(outputs[0], skip_special_tokens=True)
    print(f"   입력: {text}")
    print(f"   출력: {result}")
    
except Exception as e:
    print(f"\n❌ 오류 발생: {e}")
    print("\n대안:")
    print("1. 모델이 너무 큼 → 더 작은 모델 사용")
    print("2. 메모리 부족 → Google Colab 사용")
    print("3. 로컬 모델 파일 → GGUF 형식으로 변환")

print("\n" + "=" * 60)