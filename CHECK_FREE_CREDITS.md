# 🎁 GCP 무료 크레딧 확인 방법

## 📊 무료 크레딧 잔액 확인

### 웹 콘솔에서 확인 (가장 정확)

1. **청구 대시보드 접속**
   ```
   https://console.cloud.google.com/billing/015A93-2FA814-C6BCC8/reports
   ```

2. **크레딧 섹션 확인**
   ```
   https://console.cloud.google.com/billing/015A93-2FA814-C6BCC8/credits
   ```

3. **확인 사항**:
   - 프로모션 크레딧 잔액
   - 크레딧 만료일
   - 사용한 크레딧 금액

## 🔍 무료 크레딧 상태 체크

### 일반적인 GCP 무료 크레딧 유형

#### 1. 신규 가입 크레딧
- **금액**: $300 (약 40만원)
- **기간**: 90일
- **상태**: 계정 생성일로부터 확인 필요

#### 2. Always Free 한도
- **Cloud Run**: 월 200만 요청
- **Storage**: 5GB
- **네트워크**: 월 1GB
- **상태**: 영구 무료 (크레딧과 별개)

## 💻 명령어로 사용량 확인

```bash
# 이번 달 예상 비용 확인
gcloud billing accounts get-iam-policy 015A93-2FA814-C6BCC8

# 프로젝트별 비용 확인 (웹이 더 정확)
gcloud beta billing projects describe rational-autumn-467006-e2
```

## 📱 모바일 앱에서 확인

Google Cloud 모바일 앱:
1. Billing 섹션
2. Credits & promotions
3. 잔액 확인

## ⚠️ 중요 정보

### 현재 계정 상태
- **계정명**: 내 결제 계정
- **결제 연결**: 해제됨 (billingEnabled: false)
- **크레딧 확인**: 웹 콘솔 접속 필요

### 무료 크레딧이 있다면
- 결제 수단 없어도 크레딧 소진까지 사용 가능
- 크레딧 소진 후 서비스 중단

### 무료 크레딧이 없다면
- Always Free 한도만 사용 가능
- 현재 webapp-v2만 작동하는 이유

## 🎯 빠른 확인 링크

**바로 확인하기:**
https://console.cloud.google.com/billing/015A93-2FA814-C6BCC8/credits

이 페이지에서:
- "프로모션" 섹션 확인
- "크레딧 잔액" 확인
- "만료일" 확인

---

**참고**: gcloud CLI로는 크레딧 잔액을 직접 확인할 수 없어서 웹 콘솔 접속이 필요합니다.