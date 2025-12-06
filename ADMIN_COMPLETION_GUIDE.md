# 🛡️ 관리자 페이지 완성 가이드

> **작성일**: 2025-12-05  
> **목적**: 관리자 페이지의 미완성 부분을 완벽하게 구현하기 위한 상세 가이드

---

## 📋 현재 상태 요약

### ✅ 완료된 기능

| 탭 | 기능 | 상태 |
|---|------|------|
| **전체 개요** | 전체 사용자 수, 활성 봇, 총 AUM, 총 P&L 통계 카드 | ✅ |
| **전체 개요** | 위험 사용자 (손실 Top 5) 테이블 | ✅ |
| **전체 개요** | 고빈도 거래자 테이블 | ✅ |
| **전체 개요** | 거래량 통계 (최근 7일) | ✅ |
| **봇 관리** | 활성 봇 목록 | ✅ |
| **봇 관리** | 개별 봇 정지/재시작 | ✅ |
| **봇 관리** | 전체 봇 긴급 정지 | ✅ |
| **사용자 관리** | 사용자 목록 (검색, 필터링) | ✅ |
| **사용자 관리** | 계정 정지/활성화 | ✅ |
| **사용자 관리** | 강제 로그아웃 | ✅ |
| **사용자 관리** | UserDetailModal (상세보기) | ✅ |
| **로그 조회** | 시스템/봇/거래 로그 조회 | ✅ |

### ❌ 미완료 기능

| 탭 | 기능 | 우선순위 |
|---|------|----------|
| **사용자 관리** | 사용자 생성 | 🔴 높음 |
| **사용자 관리** | 비밀번호 초기화 UI | 🔴 높음 |
| **사용자 관리** | 역할 변경 UI | 🔴 높음 |
| **사용자 관리** | API 키 관리 UI | 🟡 중간 |
| **사용자 관리** | 2FA 해제 | 🟡 중간 |
| **시스템 설정** | 설정 페이지 전체 | 🟡 중간 |
| **보안 설정** | IP 화이트리스트 | 🔴 높음 |

---

## 🔴 즉시 구현해야 할 기능

### 1. 사용자 생성 기능

#### 1.1 백엔드 API 추가 (`backend/src/api/admin_users.py`)

```python
from ..schemas.admin_schema import UserCreate

@router.post("")
async def create_user(
    payload: UserCreate,
    session: AsyncSession = Depends(get_session),
    admin_id: int = Depends(require_admin),
):
    """
    관리자 전용: 새 사용자 생성
    """
    from passlib.context import CryptContext
    
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    
    # 이메일 중복 확인
    existing = await session.execute(
        select(User).where(User.email == payload.email)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="이미 사용 중인 이메일입니다")
    
    # 사용자 생성
    new_user = User(
        email=payload.email,
        password_hash=pwd_context.hash(payload.password),
        role=payload.role or "user",
        is_active=True,
    )
    
    session.add(new_user)
    await session.commit()
    await session.refresh(new_user)
    
    return {
        "success": True,
        "message": "사용자가 생성되었습니다",
        "user": {
            "id": new_user.id,
            "email": new_user.email,
            "role": new_user.role,
        }
    }
```

#### 1.2 스키마 추가 (`backend/src/schemas/admin_schema.py`)

```python
class UserCreate(BaseModel):
    email: str
    password: str
    role: str = "user"  # "user" 또는 "admin"
```

#### 1.3 프론트엔드 UI (`admin-frontend/src/pages/AdminDashboard.jsx`)

Users 탭에 "사용자 추가" 버튼과 모달 추가:

```jsx
// State 추가
const [showCreateUserModal, setShowCreateUserModal] = useState(false);
const [newUserEmail, setNewUserEmail] = useState('');
const [newUserPassword, setNewUserPassword] = useState('');
const [newUserRole, setNewUserRole] = useState('user');

// 사용자 생성 핸들러
const handleCreateUser = async () => {
  if (!newUserEmail || !newUserPassword) {
    alert('이메일과 비밀번호를 입력하세요');
    return;
  }
  
  try {
    await api.post('/admin/users', {
      email: newUserEmail,
      password: newUserPassword,
      role: newUserRole
    });
    alert('사용자가 생성되었습니다');
    setShowCreateUserModal(false);
    setNewUserEmail('');
    setNewUserPassword('');
    setNewUserRole('user');
    fetchUsers();
  } catch (error) {
    alert('사용자 생성 실패: ' + (error.response?.data?.detail || error.message));
  }
};

// Users 탭 헤더에 버튼 추가
<button
  onClick={() => setShowCreateUserModal(true)}
  style={{
    padding: '0.5rem 1rem',
    background: '#2563eb',
    color: 'white',
    border: 'none',
    borderRadius: '0.5rem',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    gap: '0.5rem'
  }}
>
  <Users style={{ width: '1rem', height: '1rem' }} />
  사용자 추가
</button>

// 모달 컴포넌트
{showCreateUserModal && (
  <div className="modal-overlay">
    <div className="modal-content">
      <h2>새 사용자 생성</h2>
      <div style={{ marginBottom: '1rem' }}>
        <label>이메일</label>
        <input
          type="email"
          value={newUserEmail}
          onChange={(e) => setNewUserEmail(e.target.value)}
          placeholder="user@example.com"
        />
      </div>
      <div style={{ marginBottom: '1rem' }}>
        <label>비밀번호</label>
        <input
          type="password"
          value={newUserPassword}
          onChange={(e) => setNewUserPassword(e.target.value)}
          placeholder="최소 8자"
        />
      </div>
      <div style={{ marginBottom: '1rem' }}>
        <label>역할</label>
        <select value={newUserRole} onChange={(e) => setNewUserRole(e.target.value)}>
          <option value="user">일반 사용자</option>
          <option value="admin">관리자</option>
        </select>
      </div>
      <div style={{ display: 'flex', gap: '1rem', justifyContent: 'flex-end' }}>
        <button onClick={() => setShowCreateUserModal(false)}>취소</button>
        <button onClick={handleCreateUser} style={{ background: '#2563eb', color: 'white' }}>
          생성
        </button>
      </div>
    </div>
  </div>
)}
```

---

### 2. 비밀번호 초기화 UI

#### 2.1 UserDetailModal에 버튼 추가 (`admin-frontend/src/components/UserDetailModal.jsx`)

```jsx
// 비밀번호 초기화 핸들러
const handleResetPassword = async () => {
  if (!window.confirm(`${user.email}의 비밀번호를 초기화하시겠습니까?`)) return;
  
  try {
    const response = await api.post(`/admin/users/${user.id}/reset-password`);
    
    // 새 비밀번호 표시 (보안상 주의 필요)
    alert(`비밀번호가 초기화되었습니다.\n\n새 비밀번호: ${response.data.new_password}\n\n이 비밀번호를 사용자에게 안전하게 전달하세요.`);
  } catch (error) {
    alert('비밀번호 초기화 실패: ' + error.message);
  }
};

// 버튼 추가
<button
  onClick={handleResetPassword}
  style={{
    padding: '0.5rem 1rem',
    background: '#f59e0b',
    color: 'white',
    border: 'none',
    borderRadius: '0.5rem',
    cursor: 'pointer'
  }}
>
  비밀번호 초기화
</button>
```

---

### 3. 역할 변경 UI

#### 3.1 UserDetailModal에 역할 변경 드롭다운 추가

```jsx
// State
const [selectedRole, setSelectedRole] = useState(user?.role || 'user');

// 역할 변경 핸들러
const handleChangeRole = async () => {
  if (selectedRole === user.role) return;
  
  if (!window.confirm(`${user.email}의 역할을 "${selectedRole}"로 변경하시겠습니까?`)) return;
  
  try {
    await api.put(`/admin/users/${user.id}/role?role=${selectedRole}`);
    alert('역할이 변경되었습니다');
    // 사용자 정보 다시 로드
    fetchUserDetail();
  } catch (error) {
    alert('역할 변경 실패: ' + error.message);
  }
};

// UI
<div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginTop: '1rem' }}>
  <label>역할:</label>
  <select
    value={selectedRole}
    onChange={(e) => setSelectedRole(e.target.value)}
    style={{ padding: '0.5rem', borderRadius: '0.375rem', border: '1px solid #d1d5db' }}
  >
    <option value="user">일반 사용자</option>
    <option value="admin">관리자</option>
  </select>
  <button
    onClick={handleChangeRole}
    disabled={selectedRole === user.role}
    style={{
      padding: '0.5rem 1rem',
      background: selectedRole === user.role ? '#9ca3af' : '#8b5cf6',
      color: 'white',
      border: 'none',
      borderRadius: '0.5rem',
      cursor: selectedRole === user.role ? 'not-allowed' : 'pointer'
    }}
  >
    역할 변경
  </button>
</div>
```

---

### 4. API 키 관리 UI

#### 4.1 UserDetailModal에 API 키 섹션 추가

```jsx
// 섹션 컴포넌트
{user?.has_api_keys && (
  <div style={{ marginTop: '2rem', padding: '1rem', background: '#f9fafb', borderRadius: '0.5rem' }}>
    <h3 style={{ fontSize: '1rem', fontWeight: '600', marginBottom: '1rem' }}>
      🔑 API 키 정보
    </h3>
    <div style={{ display: 'grid', gap: '0.5rem' }}>
      <p><strong>등록일:</strong> {user.api_key_created_at || 'N/A'}</p>
      <p><strong>마지막 사용:</strong> {user.api_key_last_used || 'N/A'}</p>
    </div>
    <div style={{ marginTop: '1rem', display: 'flex', gap: '0.5rem' }}>
      <button
        onClick={() => fetchApiKeys(user.id)}
        style={{
          padding: '0.5rem 1rem',
          background: '#dbeafe',
          color: '#1e40af',
          border: '1px solid #bfdbfe',
          borderRadius: '0.375rem',
          cursor: 'pointer'
        }}
      >
        API 키 조회
      </button>
      <button
        onClick={() => handleDeleteApiKey(user.id)}
        style={{
          padding: '0.5rem 1rem',
          background: '#fee2e2',
          color: '#991b1b',
          border: '1px solid #fecaca',
          borderRadius: '0.375rem',
          cursor: 'pointer'
        }}
      >
        API 키 삭제
      </button>
    </div>
  </div>
)}
```

---

### 5. 관리자 IP 화이트리스트

#### 5.1 백엔드 미들웨어 추가 (`backend/src/middleware/admin_ip_whitelist.py`)

```python
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
import os

class AdminIPWhitelistMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, whitelist: list = None):
        super().__init__(app)
        # 환경변수에서 읽기: 쉼표로 구분된 IP 목록
        whitelist_env = os.getenv("ADMIN_IP_WHITELIST", "")
        self.whitelist = whitelist or [ip.strip() for ip in whitelist_env.split(",") if ip.strip()]
        
    async def dispatch(self, request: Request, call_next):
        # /admin 경로에 대해서만 체크
        if request.url.path.startswith("/admin"):
            client_ip = request.client.host
            
            # X-Forwarded-For 헤더 체크 (프록시 뒤에 있는 경우)
            forwarded = request.headers.get("X-Forwarded-For")
            if forwarded:
                client_ip = forwarded.split(",")[0].strip()
            
            # 화이트리스트가 비어있으면 모든 IP 허용 (개발 환경)
            if self.whitelist and client_ip not in self.whitelist:
                raise HTTPException(
                    status_code=403,
                    detail=f"Access denied: IP {client_ip} is not whitelisted"
                )
        
        return await call_next(request)
```

#### 5.2 main.py에 미들웨어 등록

```python
from .middleware.admin_ip_whitelist import AdminIPWhitelistMiddleware

# 관리자 IP 화이트리스트 (프로덕션에서만 활성화)
if not RateLimitConfig.IS_DEVELOPMENT:
    app.add_middleware(AdminIPWhitelistMiddleware)
```

#### 5.3 환경변수 설정

```bash
# .env
ADMIN_IP_WHITELIST=123.45.67.89,111.222.333.444
```

---

## 🟡 중간 우선순위 구현

### 6. 시스템 설정 페이지

새 파일 생성: `admin-frontend/src/pages/SystemSettings.jsx`

```jsx
import React, { useState, useEffect } from 'react';
import { Settings, Save, RefreshCw } from 'lucide-react';
import api from '../api/client';

export default function SystemSettings() {
  const [settings, setSettings] = useState({
    maxUsersPerBot: 10,
    defaultLeverage: 10,
    maxDailyLoss: 500,
    maintenanceMode: false,
  });
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchSettings();
  }, []);

  const fetchSettings = async () => {
    try {
      setLoading(true);
      const response = await api.get('/admin/settings');
      setSettings(response.data);
    } catch (error) {
      console.error('Failed to fetch settings:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    try {
      await api.put('/admin/settings', settings);
      alert('설정이 저장되었습니다');
    } catch (error) {
      alert('설정 저장 실패: ' + error.message);
    }
  };

  return (
    <div style={{ padding: '2rem' }}>
      <h1 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '2rem' }}>
        <Settings style={{ width: '1.5rem', height: '1.5rem' }} />
        시스템 설정
      </h1>

      <div style={{ display: 'grid', gap: '1.5rem', maxWidth: '600px' }}>
        <div>
          <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '500' }}>
            기본 레버리지
          </label>
          <input
            type="number"
            value={settings.defaultLeverage}
            onChange={(e) => setSettings({ ...settings, defaultLeverage: parseInt(e.target.value) })}
            style={{ padding: '0.5rem', border: '1px solid #d1d5db', borderRadius: '0.375rem', width: '100%' }}
          />
        </div>

        <div>
          <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '500' }}>
            일일 최대 손실 한도 (USDT)
          </label>
          <input
            type="number"
            value={settings.maxDailyLoss}
            onChange={(e) => setSettings({ ...settings, maxDailyLoss: parseInt(e.target.value) })}
            style={{ padding: '0.5rem', border: '1px solid #d1d5db', borderRadius: '0.375rem', width: '100%' }}
          />
        </div>

        <div>
          <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <input
              type="checkbox"
              checked={settings.maintenanceMode}
              onChange={(e) => setSettings({ ...settings, maintenanceMode: e.target.checked })}
            />
            <span style={{ fontWeight: '500' }}>점검 모드</span>
          </label>
          <p style={{ color: '#6b7280', fontSize: '0.875rem', marginTop: '0.25rem' }}>
            점검 모드 활성화 시 일반 사용자의 거래가 중지됩니다
          </p>
        </div>

        <div style={{ display: 'flex', gap: '1rem', marginTop: '1rem' }}>
          <button
            onClick={handleSave}
            style={{
              padding: '0.75rem 1.5rem',
              background: '#2563eb',
              color: 'white',
              border: 'none',
              borderRadius: '0.5rem',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem'
            }}
          >
            <Save style={{ width: '1rem', height: '1rem' }} />
            저장
          </button>
          <button
            onClick={fetchSettings}
            style={{
              padding: '0.75rem 1.5rem',
              background: '#f3f4f6',
              border: '1px solid #d1d5db',
              borderRadius: '0.5rem',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem'
            }}
          >
            <RefreshCw style={{ width: '1rem', height: '1rem' }} />
            새로고침
          </button>
        </div>
      </div>
    </div>
  );
}
```

---

## 📊 필요한 백엔드 API 요약

| 메서드 | 경로 | 설명 | 구현 상태 |
|--------|------|------|----------|
| `POST` | `/admin/users` | 사용자 생성 | ❌ 필요 |
| `DELETE` | `/admin/users/{id}` | 사용자 삭제 | ❌ 필요 |
| `PUT` | `/admin/users/{id}/2fa/disable` | 2FA 해제 | ❌ 필요 |
| `GET` | `/admin/settings` | 시스템 설정 조회 | ❌ 필요 |
| `PUT` | `/admin/settings` | 시스템 설정 변경 | ❌ 필요 |
| `GET` | `/admin/ip-whitelist` | IP 화이트리스트 조회 | ❌ 필요 |
| `POST` | `/admin/ip-whitelist` | IP 추가 | ❌ 필요 |
| `DELETE` | `/admin/ip-whitelist/{ip}` | IP 삭제 | ❌ 필요 |
| `GET` | `/admin/audit-log` | 감사 로그 조회 | ❌ 필요 |

---

## 🎨 CSS 추가 필요

`admin-frontend/src/pages/AdminDashboard.css`에 모달 스타일 추가:

```css
/* Modal Overlay */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

/* Modal Content */
.modal-content {
  background: white;
  padding: 2rem;
  border-radius: 0.75rem;
  width: 100%;
  max-width: 500px;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
}

.modal-content h2 {
  font-size: 1.25rem;
  font-weight: 600;
  margin-bottom: 1.5rem;
}

.modal-content label {
  display: block;
  font-size: 0.875rem;
  font-weight: 500;
  color: #374151;
  margin-bottom: 0.5rem;
}

.modal-content input,
.modal-content select {
  width: 100%;
  padding: 0.5rem 0.75rem;
  border: 1px solid #d1d5db;
  border-radius: 0.375rem;
  font-size: 0.875rem;
}

.modal-content input:focus,
.modal-content select:focus {
  outline: none;
  border-color: #2563eb;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
}

.modal-content button {
  padding: 0.5rem 1rem;
  border-radius: 0.375rem;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
}
```

---

## ✅ 구현 완료 체크리스트

다음 개발자가 구현해야 할 항목을 순서대로 정리:

```markdown
## Phase 1: 긴급 (배포 전)
- [ ] 관리자 IP 화이트리스트 미들웨어 구현
- [ ] 환경변수 설정 문서화

## Phase 2: 높음 (1주일 내)
- [ ] POST /admin/users API 추가
- [ ] 사용자 생성 UI 구현
- [ ] 비밀번호 초기화 UI 구현
- [ ] 역할 변경 UI 구현

## Phase 3: 중간 (2주 내)
- [ ] API 키 관리 UI 구현
- [ ] 2FA 해제 API 및 UI
- [ ] 시스템 설정 페이지
- [ ] 감사 로그 API 및 UI

## Phase 4: 낮음 (1개월 내)
- [ ] 관리자 대시보드 차트 시각화
- [ ] 데이터 내보내기 기능
- [ ] 관리자 페이지 모바일 반응형
```

---

이 가이드를 따라 구현하면 관리자 페이지가 완성됩니다. 궁금한 점이 있으면 코드베이스의 기존 구현을 참고하세요.
