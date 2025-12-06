# 🎨 Deep Signal - UI/UX 디자인 가이드

> **최종 업데이트**: 2025-12-05  
> **상태**: 프로덕션 확정

---

## ⚠️ 중요: 변경 금지 영역

### 🔒 좌측 사이드바 (Sidebar) - **절대 변경 금지**

현재 디자인이 **최종 확정** 되었습니다. 다음 요소들은 변경하지 마세요:

| 요소 | 값 | 파일 위치 |
|------|-----|----------|
| **배경색** | `#000000` (순수 블랙) | `MainLayout.jsx` line 284, 306 |
| **메뉴 텍스트 색상** | `#ffffff` (쨍한 화이트) | `index.css` line 165 |
| **아이콘 색상** | `#ffffff` (쨍한 화이트) | `index.css` line 185 |
| **로고 배경** | `#ffffff` (흰색) | `MainLayout.jsx` line 164 |
| **로고 아이콘** | 🚀 | `MainLayout.jsx` line 172 |
| **로고 텍스트** | "Deep Signal" (흰색) | `MainLayout.jsx` line 179 |
| **사이드바 너비** | `260px` | `MainLayout.jsx` line 298 |

---

### 🚫 알록달록 그라데이션 카드 - **절대 사용 금지**

다음과 같은 **화려한 그라데이션 카드 배경색은 사용하지 마세요**:

```css
/* ❌ 금지된 색상 예시 - 절대 사용 금지 */
background: linear-gradient(135deg, #667eea, #764ba2);  /* 보라색 */
background: linear-gradient(135deg, #11998e, #38ef7d);  /* 녹색 */
background: linear-gradient(135deg, #ee0979, #ff6a00);  /* 핑크-오렌지 */
background: linear-gradient(135deg, #4facfe, #00f2fe);  /* 파란색 */
background: linear-gradient(135deg, #fa709a, #fee140);  /* 핑크-노랑 */
```

**올바른 카드 스타일:**

```css
/* ✅ 허용된 카드 스타일 */
background: #ffffff;                    /* 흰색 배경 */
background: #f8fafc;                    /* 밝은 회색 배경 */
border: 1px solid #e5e7eb;              /* 회색 테두리 */
box-shadow: 0 1px 3px rgba(0,0,0,0.1);  /* 미세한 그림자 */
```

**카드 디자인 원칙:**

- ✅ 깔끔한 흰색/회색 배경
- ✅ 미니멀한 테두리와 그림자
- ✅ 텍스트와 아이콘으로 정보 전달
- ❌ 화려한 그라데이션 배경
- ❌ 알록달록한 색상 조합
- ❌ 네온/형광 색상

---

## 📁 디자인 관련 주요 파일

```
frontend/src/
├── components/layout/
│   └── MainLayout.jsx       # 메인 레이아웃 (사이드바, 헤더)
├── index.css                # 글로벌 스타일, Ant Design 오버라이드
└── pages/
    ├── Dashboard.jsx        # 대시보드 페이지
    ├── Trading.jsx          # 트레이딩 페이지
    ├── Settings.jsx         # 설정 페이지
    └── ...
```

---

## 🎨 색상 팔레트

### 사이드바 (고정)

```css
--sidebar-bg: #000000;           /* 순수 블랙 */
--sidebar-text: #ffffff;         /* 쨍한 화이트 */
--sidebar-icon: #ffffff;         /* 쨍한 화이트 */
--sidebar-hover: rgba(255, 255, 255, 0.1);
--sidebar-selected: rgba(255, 255, 255, 0.15);
```

### 메인 콘텐츠 (애플 스타일)

```css
--content-bg: #f5f5f7;           /* 애플 웜 그레이 */
--header-bg: #ffffff;            /* 흰색 */
--header-border: #f5f5f7;        /* 헤더 경계선 */
--card-bg: #ffffff;              /* 흰색 */
--card-border: #e5e7eb;          /* 미세한 테두리 */
```

### 프라이머리 컬러 (Apple Blue)

```css
--primary-500: #0071e3;          /* Apple Blue */
--primary-600: #0066cc;          /* Hover Blue */
--primary-700: #0055b3;          /* Active Blue */
```

### 시맨틱 컬러

```css
--success: #10b981;              /* 그린 (수익) */
--danger: #ef4444;               /* 레드 (손실) */
--warning: #f59e0b;              /* 오렌지 (경고) */
```

---

## 📐 레이아웃 규격

### 사이드바

- **너비 (펼침)**: 260px
- **너비 (접힘)**: 80px
- **로고 영역 높이**: 72px
- **메뉴 아이템 높이**: 44px (모바일 터치 최적화)

### 헤더

- **높이**: 64px
- **좌우 패딩**: 32px (데스크톱), 16px (모바일)

### 콘텐츠

- **패딩**: 28px (데스크톱), 16px (모바일)
- **최대 너비**: 1400px

---

## 🌓 다크 모드 (향후 추가 예정)

다크 모드는 향후 추가될 예정입니다. 추가 시 다음 사항을 고려하세요:

1. **사이드바는 변경 없음** - 이미 블랙이므로 그대로 유지
2. **콘텐츠 영역만 변경**:
   - 배경: `#0f172a` → `#1e293b`
   - 카드: `#1e293b`
   - 텍스트: `#f1f5f9`
3. **CSS 변수 활용** - `:root`에 정의된 변수 사용

---

## 🔧 Ant Design 오버라이드

`index.css`에서 Ant Design 컴포넌트 스타일을 오버라이드합니다:

```css
/* 카드 */
.ant-card { border-radius: 12px; }

/* 버튼 */
.ant-btn-primary { 
  background: linear-gradient(135deg, #3b82f6, #2563eb);
}

/* 메뉴 (사이드바) - ⚠️ 변경 금지 */
.ant-menu-dark .ant-menu-item { color: #ffffff; }
.ant-menu-dark .ant-menu-item .anticon { color: #ffffff; }
```

---

## 📱 반응형 브레이크포인트

```css
/* 모바일 */
@media (max-width: 768px) { ... }

/* 소형 모바일 */
@media (max-width: 480px) { ... }

/* 태블릿/소형 데스크톱 */
@media (max-width: 992px) { ... }
```

---

## ✅ 디자인 체크리스트

### 사이드바 (변경 금지)

- [x] 배경: 순수 블랙 (#000000)
- [x] 텍스트: 쨍한 화이트 (#ffffff)
- [x] 아이콘: 쨍한 화이트 (#ffffff)
- [x] 로고: 흰색 배경 + 🚀
- [x] 너비: 260px

### 헤더

- [x] 배경: 흰색
- [x] 텍스트: 진한 회색
- [x] 그림자: 미세한 그림자

### 콘텐츠

- [x] 배경: 밝은 회색 (#f8fafc)
- [x] 카드: 흰색 + 라운드 코너

---

## 📋 인수인계 시 주의사항

1. **사이드바 디자인은 절대 변경하지 마세요** - 클라이언트 최종 확정 디자인입니다
2. 색상 변경 시 `index.css`의 CSS 변수를 활용하세요
3. Ant Design 컴포넌트 수정 시 `!important` 사용이 필요할 수 있습니다
4. 모바일 최적화는 항상 테스트하세요 (최소 터치 타겟: 44px)

---

## 🔗 관련 문서

- [DEVELOPMENT_GUIDE.md](./DEVELOPMENT_GUIDE.md) - 개발 가이드
- [ENVIRONMENT_SETUP.md](./ENVIRONMENT_SETUP.md) - 환경 설정
- [SESSION_HANDOVER.md](./SESSION_HANDOVER.md) - 세션 인수인계
