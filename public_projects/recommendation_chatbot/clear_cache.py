#!/usr/bin/env python3
"""캐시 완전 초기화 스크립트"""

import shutil
from pathlib import Path

# 캐시 디렉토리 삭제
cache_dirs = [
    "outputs/cache",
    "outputs/cache/query_cache",
    "outputs/cache/embedding_cache"
]

for cache_dir in cache_dirs:
    cache_path = Path(cache_dir)
    if cache_path.exists():
        shutil.rmtree(cache_path, ignore_errors=True)
        print(f"삭제됨: {cache_dir}")
    cache_path.mkdir(parents=True, exist_ok=True)
    print(f"생성됨: {cache_dir}")

print("\n✅ 캐시 초기화 완료!")
print("이제 챗봇을 다시 시작하세요.")