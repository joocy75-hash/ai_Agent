# 🔐 OAuth 소셜 로그인 설정 가이드

> 작성일: 2025-12-06

## 📋 목차

1. [개요](#개요)
2. [Google OAuth 설정](#google-oauth-설정)
3. [Kakao OAuth 설정](#kakao-oauth-설정)
4. [환경 변수 설정](#환경-변수-설정)
5. [테스트](#테스트)
6. [프로덕션 배포](#프로덕션-배포)

---

## 개요

Deep Signal은 Google과 Kakao 소셜 로그인을 지원합니다. 이 기능을 사용하려면 각 플랫폼에서 OAuth 자격 증명을 생성하고 환경 변수로 설정해야 합니다.

### 지원 기능

- ✅ Google 로그인/가입
- ✅ Kakao 로그인/가입
- ✅ 기존 계정과 소셜 계정 연결
- ✅ 프로필 이미지 자동 가져오기

---

## Google OAuth 설정

### 1. Google Cloud Console 프로젝트 생성

1. [Google Cloud Console](https://console.cloud.google.com/) 접속
2. 새 프로젝트 생성 또는 기존 프로젝트 선택
3. API 및 서비스 > OAuth 동의 화면 > 외부 선택
4. 앱 정보 입력:
   - 앱 이름: `Deep Signal`
   - 사용자 지원 이메일: 본인 이메일
   - 개발자 연락처: 본인 이메일

### 2. OAuth 자격 증명 생성

1. API 및 서비스 > 사용자 인증 정보 > 사용자 인증 정보 만들기
2. **OAuth 클라이언트 ID** 선택
3. 애플리케이션 유형: **웹 애플리케이션**
4. 이름: `Deep Signal Web`
5. 승인된 JavaScript 원본:

   ```
   http://localhost:5173
   http://localhost:3000
   ```

6. 승인된 리디렉션 URI:

   ```
   http://localhost:8000/auth/google/callback
   ```

7. **만들기** 클릭
8. **클라이언트 ID**와 **클라이언트 보안 비밀번호** 복사

### 3. 환경 변수 설정

```bash
GOOGLE_CLIENT_ID=123456789-abcdefg.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-abcdefghijklmnop
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/google/callback
```

---

## Kakao OAuth 설정

### 1. Kakao Developers 애플리케이션 생성

1. [Kakao Developers](https://developers.kakao.com/) 접속 및 로그인
2. **내 애플리케이션** > **애플리케이션 추가하기**
3. 앱 정보 입력:
   - 앱 이름: `Deep Signal`
   - 사업자명: 본인 이름 또는 회사명

### 2. 앱 키 확인

1. 생성된 앱 선택
2. **앱 키** 탭에서 **REST API 키** 복사

### 3. 카카오 로그인 활성화

1. **제품 설정** > **카카오 로그인** > **활성화 설정** ON
2. **Redirect URI 등록**:

   ```
   http://localhost:8000/auth/kakao/callback
   ```

### 4. 동의 항목 설정

1. **제품 설정** > **카카오 로그인** > **동의항목**
2. 다음 항목 설정:
   - **닉네임**: 필수 동의
   - **프로필 사진**: 선택 동의
   - **카카오계정(이메일)**: 선택 동의 (권장)

### 5. 환경 변수 설정

```bash
KAKAO_CLIENT_ID=abcdef1234567890abcdef12
KAKAO_CLIENT_SECRET=  # 선택사항 (보안 설정 시)
KAKAO_REDIRECT_URI=http://localhost:8000/auth/kakao/callback
```

---

## 환경 변수 설정

### 개발 환경 (.env)

```bash
# 기본 설정
ENVIRONMENT=development
FRONTEND_URL=http://localhost:5173

# Google OAuth
GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/google/callback

# Kakao OAuth
KAKAO_CLIENT_ID=your-kakao-rest-api-key
KAKAO_CLIENT_SECRET=
KAKAO_REDIRECT_URI=http://localhost:8000/auth/kakao/callback
```

### 프로덕션 환경

```bash
# 기본 설정
ENVIRONMENT=production
FRONTEND_URL=https://yourdomain.com

# Google OAuth
GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=https://api.yourdomain.com/auth/google/callback

# Kakao OAuth
KAKAO_CLIENT_ID=your-kakao-rest-api-key
KAKAO_CLIENT_SECRET=your-kakao-client-secret
KAKAO_REDIRECT_URI=https://api.yourdomain.com/auth/kakao/callback
```

---

## 테스트

### 1. 백엔드 서버 시작

```bash
cd backend
uvicorn src.main:app --reload
```

### 2. 프론트엔드 서버 시작

```bash
cd frontend
npm run dev
```

### 3. 소셜 로그인 테스트

1. <http://localhost:5173/login> 접속
2. **회원가입** 탭 또는 **로그인** 탭에서 소셜 로그인 버튼 클릭
3. 해당 플랫폼 로그인 페이지로 이동
4. 로그인 완료 후 대시보드로 자동 이동

### 4. OAuth 상태 확인 API

```bash
curl http://localhost:8000/auth/oauth/status
```

응답 예시:

```json
{
  "google": {
    "enabled": true,
    "login_url": "/auth/google/login"
  },
  "kakao": {
    "enabled": true,
    "login_url": "/auth/kakao/login"
  }
}
```

---

## 프로덕션 배포

### 1. Google Cloud Console 업데이트

1. OAuth 동의 화면 > 앱 게시 (프로덕션)
2. 사용자 인증 정보 > 승인된 리디렉션 URI 추가:

   ```
   https://api.yourdomain.com/auth/google/callback
   ```

### 2. Kakao Developers 업데이트

1. Redirect URI 추가:

   ```
   https://api.yourdomain.com/auth/kakao/callback
   ```

### 3. 환경 변수 업데이트

프로덕션 환경변수에서 모든 `localhost` URL을 실제 도메인으로 변경합니다.

---

## 🔒 보안 고려사항

1. **클라이언트 시크릿 보호**: 절대 프론트엔드 코드나 공개 저장소에 노출하지 마세요.
2. **HTTPS 필수**: 프로덕션에서는 반드시 HTTPS를 사용하세요.
3. **State 파라미터**: CSRF 공격 방지를 위해 state 파라미터가 자동으로 사용됩니다.
4. **리다이렉트 URI 검증**: 등록된 URI만 허용됩니다.

---

## 🐛 문제 해결

### "OAuth가 설정되지 않았습니다" 오류

- 환경 변수가 올바르게 설정되었는지 확인
- 서버 재시작 후 다시 시도

### "invalid_state" 오류

- 브라우저 쿠키/캐시 삭제
- 다시 로그인 시도

### "token_exchange_failed" 오류

- 클라이언트 ID/시크릿 확인
- 리다이렉트 URI가 정확히 일치하는지 확인

### 카카오 이메일이 없는 경우

- 동의 항목에서 이메일 설정 확인
- 이메일 없이도 `kakao_{id}@kakao.local` 형태로 자동 생성됨

---

## 📞 문의

추가 도움이 필요하시면 프로젝트 이슈를 생성하거나 관리자에게 문의하세요.
