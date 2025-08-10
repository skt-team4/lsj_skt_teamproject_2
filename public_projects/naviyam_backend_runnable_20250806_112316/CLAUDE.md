# Naviyam Backend 설정 및 실행 가이드

## 프로젝트 상태
- 위치: `/Volumes/samsd/naviyam_backend_runnable_20250806_112316`
- 상태: ✅ **정상 실행 중**
- 서버 포트: 8000

## 해결된 문제들
1. ✅ **Python 가상환경**: ~/naviyam_venv 생성 및 설정 완료
2. ✅ **패키지 설치**: 필수 패키지 모두 설치 완료
3. ✅ **Windows 경로 문제**: macOS 경로로 수정 완료
4. ✅ **RAG 데이터**: test_data.json 생성 완료
5. ✅ **MeCab**: 한국어 형태소 분석기 설치 완료
6. ✅ **서버 실행**: uvicorn으로 정상 실행 중

## 실행 방법
```bash
# 1. 가상환경 활성화
source ~/naviyam_venv/bin/activate

# 2. 서버 실행
PYTHONPATH=/Volumes/samsd/naviyam_backend_runnable_20250806_112316 \
python3 -m uvicorn api.server:app --host 0.0.0.0 --port 8000
```

## API 접속 정보
- **헬스체크**: http://localhost:8000/health ✅
- **API 문서**: http://localhost:8000/docs ✅
- **채팅 API**: POST http://localhost:8000/chat ✅
- **OpenAI 호환**: POST http://localhost:8000/v1/chat/completions ⚠️ (500 에러)

## 현재 제한사항
1. **LLM 미작동**: GPU 없어서 bitsandbytes 기반 모델 로드 불가
   - 템플릿 기반 응답으로 작동 중
2. **OpenAI API 오류**: UserInput 클래스 인자 문제
   - 레거시 /chat 엔드포인트는 정상 작동

## 테스트
```bash
# API 테스트 실행
python3 test_api.py
```

## 프론트엔드 연동
- **상태**: ✅ 연동 가능
- **추천 엔드포인트**: `/chat` (레거시 API)
- **응답 형식**: JSON

## 서버 로그 확인
```bash
# 실시간 로그 확인
tail -f server_improved.log
```

## 참고사항
- macOS ARM64 (M1/M2) 환경에서 실행 중
- CPU 모드로 작동 (GPU 미사용)
- 기본 채팅 기능은 정상 작동