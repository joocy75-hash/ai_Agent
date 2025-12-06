# Refine 프론트엔드 설정 가이드

**작성일**: 2025-11-30
**프론트엔드**: Refine + Vite + React + TypeScript + Ant Design
**백엔드**: FastAPI + JWT + WebSocket

---

## 📁 프로젝트 구조

```
auto-dashboard/
├── backend/                    # FastAPI 백엔드 (완료)
│   ├── src/                   # API, 서비스, 모델
│   ├── tests/                 # 테스트
│   ├── docs/                  # 문서
│   └── docker-compose.yml     # PostgreSQL
│
└── frontend/                   # Refine 프론트엔드 (신규)
    ├── src/
    │   ├── App.tsx            # 메인 앱 설정
    │   ├── authProvider.tsx   # JWT 인증
    │   ├── pages/             # 페이지들
    │   │   ├── dashboard/     # 대시보드
    │   │   ├── login/         # 로그인
    │   │   ├── bot/           # 봇 제어
    │   │   └── strategies/    # 전략 관리
    │   └── components/        # 재사용 컴포넌트
    ├── package.json
    └── vite.config.ts
```

---

## 🚀 빠른 시작 (5단계)

### 1단계: 프로젝트 확인
```bash
cd /Users/mr.joo/Desktop/auto-dashboard/frontend
ls -la
```

**설치된 패키지**:
- ✅ `@refinedev/core` - Refine 코어
- ✅ `@refinedev/antd` - Ant Design 통합
- ✅ `@refinedev/simple-rest` - REST API 연동
- ✅ `@refinedev/react-router` - 라우팅
- ✅ `antd` - UI 컴포넌트
- ✅ `recharts` - 차트 라이브러리

---

### 2단계: Auth Provider 생성

**파일**: `frontend/src/authProvider.tsx`

```typescript
import { AuthProvider } from "@refinedev/core";

const API_URL = "http://localhost:8000";

export const authProvider: AuthProvider = {
  // 로그인
  login: async ({ email, password }) => {
    const response = await fetch(`${API_URL}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });

    if (!response.ok) {
      return {
        success: false,
        error: {
          name: "LoginError",
          message: "이메일 또는 비밀번호가 올바르지 않습니다.",
        },
      };
    }

    const data = await response.json();
    localStorage.setItem("token", data.access_token);

    // JWT에서 user_id 추출
    const payload = JSON.parse(atob(data.access_token.split(".")[1]));
    localStorage.setItem("user_id", String(payload.user_id));
    localStorage.setItem("email", payload.email);

    return { success: true, redirectTo: "/" };
  },

  // 로그아웃
  logout: async () => {
    localStorage.removeItem("token");
    localStorage.removeItem("user_id");
    localStorage.removeItem("email");
    return { success: true, redirectTo: "/login" };
  },

  // 인증 확인
  check: async () => {
    const token = localStorage.getItem("token");
    if (!token) {
      return {
        authenticated: false,
        redirectTo: "/login",
      };
    }

    // TODO: JWT 만료 확인 (옵션)
    return { authenticated: true };
  },

  // 에러 처리
  onError: async (error) => {
    if (error?.statusCode === 401) {
      return {
        logout: true,
        redirectTo: "/login",
        error,
      };
    }
    return {};
  },

  // 사용자 정보
  getIdentity: async () => {
    const userId = localStorage.getItem("user_id");
    const email = localStorage.getItem("email");

    if (!userId || !email) {
      return null;
    }

    return {
      id: userId,
      name: email,
      avatar: `https://ui-avatars.com/api/?name=${encodeURIComponent(email)}`,
    };
  },
};
```

---

### 3단계: Data Provider 설정 (JWT 헤더 추가)

**파일**: `frontend/src/dataProvider.ts`

```typescript
import { DataProvider } from "@refinedev/core";
import dataProviderSimpleRest from "@refinedev/simple-rest";

const API_URL = "http://localhost:8000";

// JWT 토큰을 모든 요청에 자동 추가
const customDataProvider: DataProvider = {
  ...dataProviderSimpleRest(API_URL),

  // 커스텀 헤더 추가
  getList: async ({ resource, pagination, filters, sorters, meta }) => {
    const token = localStorage.getItem("token");
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    };

    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    const url = `${API_URL}${meta?.path || `/${resource}/list`}`;
    const response = await fetch(url, { headers });
    const data = await response.json();

    return {
      data: Array.isArray(data) ? data : [],
      total: Array.isArray(data) ? data.length : 0,
    };
  },

  getOne: async ({ resource, id, meta }) => {
    const token = localStorage.getItem("token");
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    };

    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    const url = `${API_URL}${meta?.path || `/${resource}/${id}`}`;
    const response = await fetch(url, { headers });
    const data = await response.json();

    return { data };
  },

  create: async ({ resource, variables, meta }) => {
    const token = localStorage.getItem("token");
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    };

    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    const url = `${API_URL}${meta?.path || `/${resource}/create`}`;
    const response = await fetch(url, {
      method: "POST",
      headers,
      body: JSON.stringify(variables),
    });
    const data = await response.json();

    return { data };
  },

  update: async ({ resource, id, variables, meta }) => {
    const token = localStorage.getItem("token");
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    };

    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    const url = `${API_URL}${meta?.path || `/${resource}/update/${id}`}`;
    const response = await fetch(url, {
      method: "POST",
      headers,
      body: JSON.stringify(variables),
    });
    const data = await response.json();

    return { data };
  },
};

export default customDataProvider;
```

---

### 4단계: App.tsx 설정

**파일**: `frontend/src/App.tsx`

```typescript
import { Refine } from "@refinedev/core";
import { RefineKbar, RefineKbarProvider } from "@refinedev/kbar";
import {
  ErrorComponent,
  ThemedLayoutV2,
  ThemedSiderV2,
  useNotificationProvider,
} from "@refinedev/antd";
import routerBindings, {
  CatchAllNavigate,
  DocumentTitleHandler,
  NavigateToResource,
  UnsavedChangesNotifier,
} from "@refinedev/react-router";
import { BrowserRouter, Outlet, Route, Routes } from "react-router-dom";
import { ConfigProvider, App as AntdApp } from "antd";
import { authProvider } from "./authProvider";
import dataProvider from "./dataProvider";

// 페이지 임포트 (TODO: 생성 필요)
// import { DashboardPage } from "./pages/dashboard";
// import { LoginPage } from "./pages/login";
// import { BotListPage, BotControlPage } from "./pages/bot";
// import { StrategyListPage, StrategyCreatePage } from "./pages/strategies";

import "@refinedev/antd/dist/reset.css";

function App() {
  return (
    <BrowserRouter>
      <ConfigProvider
        theme={{
          token: {
            colorPrimary: "#10b981", // Emerald color
          },
        }}
      >
        <AntdApp>
          <RefineKbarProvider>
            <Refine
              dataProvider={dataProvider}
              authProvider={authProvider}
              routerProvider={routerBindings}
              notificationProvider={useNotificationProvider}
              resources={[
                {
                  name: "dashboard",
                  list: "/",
                  meta: {
                    label: "대시보드",
                    icon: "📊",
                  },
                },
                {
                  name: "bot",
                  list: "/bot",
                  meta: {
                    label: "봇 제어",
                    icon: "🤖",
                    path: "/bot/status",
                  },
                },
                {
                  name: "strategies",
                  list: "/strategies",
                  create: "/strategies/create",
                  edit: "/strategies/edit/:id",
                  meta: {
                    label: "전략 관리",
                    icon: "📈",
                    path: "/strategy/list",
                  },
                },
                {
                  name: "trades",
                  list: "/trades",
                  meta: {
                    label: "거래 내역",
                    icon: "💰",
                    path: "/order/history",
                  },
                },
              ]}
              options={{
                syncWithLocation: true,
                warnWhenUnsavedChanges: true,
                useNewQueryKeys: true,
              }}
            >
              <Routes>
                <Route
                  element={
                    <ThemedLayoutV2
                      Sider={() => <ThemedSiderV2 Title={() => <div>트레이딩 봇</div>} />}
                    >
                      <Outlet />
                    </ThemedLayoutV2>
                  }
                >
                  <Route index element={<div>대시보드 (TODO)</div>} />
                  <Route path="/bot" element={<div>봇 제어 (TODO)</div>} />
                  <Route path="/strategies" element={<div>전략 목록 (TODO)</div>} />
                  <Route path="/strategies/create" element={<div>전략 생성 (TODO)</div>} />
                  <Route path="/trades" element={<div>거래 내역 (TODO)</div>} />
                  <Route path="*" element={<ErrorComponent />} />
                </Route>
                <Route
                  element={
                    <AntdApp>
                      <Outlet />
                    </AntdApp>
                  }
                >
                  <Route path="/login" element={<div>로그인 페이지 (TODO)</div>} />
                </Route>
              </Routes>
              <RefineKbar />
              <UnsavedChangesNotifier />
              <DocumentTitleHandler />
            </Refine>
          </RefineKbarProvider>
        </AntdApp>
      </ConfigProvider>
    </BrowserRouter>
  );
}

export default App;
```

---

### 5단계: 프론트엔드 실행

```bash
cd /Users/mr.joo/Desktop/auto-dashboard/frontend
npm run dev
```

**URL**: http://localhost:5173

---

## 📱 페이지 구현 가이드

### 1. 로그인 페이지

**파일**: `frontend/src/pages/login/index.tsx`

```typescript
import { useLogin } from "@refinedev/core";
import { Form, Input, Button, Card, Typography } from "antd";

const { Title } = Typography;

export const LoginPage = () => {
  const { mutate: login, isLoading } = useLogin();

  return (
    <div style={{
      display: "flex",
      justifyContent: "center",
      alignItems: "center",
      minHeight: "100vh",
      background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)"
    }}>
      <Card style={{ width: 400 }}>
        <Title level={2} style={{ textAlign: "center" }}>
          트레이딩 봇 로그인
        </Title>
        <Form
          layout="vertical"
          onFinish={(values) => login(values)}
        >
          <Form.Item
            label="이메일"
            name="email"
            rules={[{ required: true, type: "email" }]}
          >
            <Input placeholder="your@email.com" />
          </Form.Item>
          <Form.Item
            label="비밀번호"
            name="password"
            rules={[{ required: true }]}
          >
            <Input.Password placeholder="••••••••" />
          </Form.Item>
          <Button type="primary" htmlType="submit" block loading={isLoading}>
            로그인
          </Button>
        </Form>
      </Card>
    </div>
  );
};
```

---

### 2. 대시보드 페이지 (봇 상태 + 차트)

**파일**: `frontend/src/pages/dashboard/index.tsx`

```typescript
import { useCustom } from "@refinedev/core";
import { Card, Col, Row, Statistic, Button } from "antd";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";

export const DashboardPage = () => {
  const { data: botStatus } = useCustom({
    url: "http://localhost:8000/bot/status",
    method: "get",
  });

  const { data: equityHistory } = useCustom({
    url: "http://localhost:8000/order/equity_history",
    method: "get",
  });

  const handleStartBot = async () => {
    // TODO: 봇 시작 API 호출
  };

  return (
    <div style={{ padding: 24 }}>
      <Row gutter={[16, 16]}>
        <Col xs={24} md={8}>
          <Card>
            <Statistic
              title="봇 상태"
              value={botStatus?.data?.is_running ? "실행 중" : "중지"}
              valueStyle={{ color: botStatus?.data?.is_running ? "#3f8600" : "#cf1322" }}
            />
            <Button
              type="primary"
              style={{ marginTop: 16 }}
              onClick={handleStartBot}
            >
              {botStatus?.data?.is_running ? "중지" : "시작"}
            </Button>
          </Card>
        </Col>

        <Col xs={24} md={16}>
          <Card title="자산 변화">
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={equityHistory?.data || []}>
                <XAxis dataKey="time" />
                <YAxis />
                <Tooltip />
                <Line type="monotone" dataKey="value" stroke="#10b981" />
              </LineChart>
            </ResponsiveContainer>
          </Card>
        </Col>
      </Row>
    </div>
  );
};
```

---

### 3. 전략 관리 페이지

**파일**: `frontend/src/pages/strategies/list.tsx`

```typescript
import { useList } from "@refinedev/core";
import { List, Table, Space, Button } from "@refinedev/antd";

export const StrategyListPage = () => {
  const { data, isLoading } = useList({
    resource: "strategies",
    meta: {
      path: "/strategy/list",
    },
  });

  return (
    <List>
      <Table dataSource={data?.data} loading={isLoading} rowKey="id">
        <Table.Column title="ID" dataKey="id" />
        <Table.Column title="이름" dataKey="name" />
        <Table.Column title="설명" dataKey="description" />
        <Table.Column
          title="작업"
          render={(_, record: any) => (
            <Space>
              <Button type="link">편집</Button>
              <Button type="link" danger>삭제</Button>
            </Space>
          )}
        />
      </Table>
    </List>
  );
};
```

---

## 🔌 백엔드 API 매핑

| 프론트엔드 | 백엔드 API | 설명 |
|-----------|------------|------|
| `authProvider.login()` | `POST /auth/login` | 로그인 |
| `authProvider.check()` | JWT 토큰 검증 (클라이언트) | 인증 확인 |
| `/bot` 페이지 | `GET /bot/status` | 봇 상태 조회 |
| 봇 시작 버튼 | `POST /bot/start` | 봇 시작 |
| 봇 중지 버튼 | `POST /bot/stop` | 봇 중지 |
| `/strategies` 페이지 | `GET /strategy/list` | 전략 목록 |
| 전략 생성 폼 | `POST /strategy/create` | 전략 생성 |
| `/trades` 페이지 | `GET /order/history` | 거래 내역 |
| 차트 데이터 | `GET /order/equity_history` | 자산 변화 |

---

## 📱 모바일 최적화

### Ant Design 반응형 Grid

```tsx
import { Row, Col } from "antd";

<Row gutter={[16, 16]}>
  <Col xs={24} sm={12} md={8} lg={6}>
    {/* 모바일: 100%, 태블릿: 50%, 데스크탑: 33%, 큰 화면: 25% */}
  </Col>
</Row>
```

### 모바일 메뉴

```tsx
import { ThemedLayoutV2, ThemedSiderV2 } from "@refinedev/antd";

<ThemedLayoutV2
  Sider={() => (
    <ThemedSiderV2
      Title={() => <div>트레이딩 봇</div>}
      render={({ items, logout }) => (
        <>
          {items}
          {logout}
        </>
      )}
    />
  )}
/>
```

---

## 🎨 다크 모드 설정

```typescript
import { ConfigProvider, theme } from "antd";
import { useState } from "react";

function App() {
  const [isDark, setIsDark] = useState(false);

  return (
    <ConfigProvider
      theme={{
        algorithm: isDark ? theme.darkAlgorithm : theme.defaultAlgorithm,
        token: {
          colorPrimary: "#10b981",
        },
      }}
    >
      {/* ... */}
    </ConfigProvider>
  );
}
```

---

## 🧪 테스트 방법

### 1. 백엔드 실행 확인
```bash
# 터미널 1
cd /Users/mr.joo/Desktop/auto-dashboard/backend
docker-compose up -d
export ENCRYPTION_KEY="Dz9w_blEMa-tMD5hqK6V7yiaYecQBdsTaO0PJR3ESn8="
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. 프론트엔드 실행
```bash
# 터미널 2
cd /Users/mr.joo/Desktop/auto-dashboard/frontend
npm run dev
```

### 3. 테스트 시나리오
1. http://localhost:5173 접속
2. 로그인 페이지 확인
3. 회원가입: `test@example.com` / `password123`
4. 대시보드 자동 이동 확인
5. 봇 상태 조회 확인
6. 전략 목록 확인

---

## 📚 다음 단계

### 우선순위 높음
1. ⭐ 로그인 페이지 완성
2. ⭐ 대시보드 페이지 완성 (봇 상태 + 차트)
3. ⭐ 봇 제어 페이지
4. ⭐ 전략 관리 CRUD

### 우선순위 중간
5. WebSocket 실시간 업데이트
6. 차트 고도화 (TradingView Lightweight Charts)
7. 알림 시스템

### 우선순위 낮음
8. PWA 설정
9. 다국어 지원
10. 테마 커스터마이징

---

## 🔗 유용한 링크

- **Refine 공식 문서**: https://refine.dev/docs
- **Ant Design**: https://ant.design/components/overview
- **Recharts**: https://recharts.org
- **React Router**: https://reactrouter.com

---

**작성자**: Claude Code
**최종 업데이트**: 2025-11-30 19:30
**버전**: v1.0 (Initial Setup)

**다음 작업자에게**:
- ✅ Refine 프로젝트 생성 완료
- ✅ 필수 패키지 설치 완료 (Refine, Ant Design, Recharts)
- 📋 Auth Provider, Data Provider 구현 필요
- 📋 페이지 컴포넌트 구현 필요
- 🚀 백엔드 API와 100% 호환되는 구조!
