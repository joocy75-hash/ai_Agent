# 🎯 Remaining Tasks - Complete Frontend & Backend Checklist

> **생성일**: 2025-12-04
> **프로젝트**: Auto Trading Dashboard
> **상태**: 코드베이스 전체 분석 완료

---

## 📋 목차

1. [Frontend 남은 작업](#-frontend-남은-작업)
2. [Backend 남은 작업](#-backend-남은-작업)
3. [우선순위 매트릭스](#-우선순위-매트릭스)
4. [즉시 실행 가능한 작업](#-즉시-실행-가능한-작업)

---

## 🎨 Frontend 남은 작업

### 🔴 높은 우선순위 (Critical)

#### 1. **리스크 설정 API 연동** ⚠️ BLOCKED BY BACKEND
**파일**: `frontend/src/pages/Settings.jsx`
**라인**: 43-59, 217-249

**현재 상태**:
- Mock 데이터 사용 중 (`dailyLossLimit: '500'`, `maxLeverage: '10'`, `maxPositions: '5'`)
- 저장 시 실제 API 호출 없이 성공 메시지만 표시

**필요한 작업**:
```javascript
// 1. API 클라이언트 메서드 추가 (frontend/src/api/account.js)
async getRiskSettings() {
  const response = await apiClient.get('/account/risk-settings');
  return response.data;
}

async saveRiskSettings(data) {
  const response = await apiClient.post('/account/risk-settings', data);
  return response.data;
}

// 2. Settings.jsx에서 실제 API 호출로 교체
const loadRiskSettings = async () => {
  try {
    const data = await accountAPI.getRiskSettings();
    setDailyLossLimit(data.daily_loss_limit || '');
    setMaxLeverage(data.max_leverage || '');
    setMaxPositions(data.max_positions || '');
  } catch (err) {
    console.error('[Settings] Failed to load risk settings:', err);
  }
};

const handleSaveRiskSettings = async (e) => {
  e.preventDefault();
  // ... validation ...

  try {
    await accountAPI.saveRiskSettings({
      daily_loss_limit: dailyLoss,
      max_leverage: leverage,
      max_positions: positions
    });
    setSuccess('✅ 리스크 한도 설정이 저장되었습니다!');
  } catch (err) {
    setError(err.response?.data?.detail || '리스크 설정 저장에 실패했습니다.');
  } finally {
    setRiskLoading(false);
  }
};
```

**백엔드 의존성**:
- ❌ `GET /account/risk-settings`
- ❌ `POST /account/risk-settings`

---

#### 2. **비밀번호 변경 기능 구현** ⚠️ BLOCKED BY BACKEND
**파일**: `frontend/src/pages/Settings.jsx`
**라인**: 156-177

**현재 상태**:
- Placeholder 구현만 존재
- 에러 메시지: "비밀번호 변경 기능은 아직 백엔드에 구현되지 않았습니다."

**필요한 작업**:
```javascript
// 1. API 클라이언트 메서드 추가 (frontend/src/api/auth.js)
export const changePassword = async (currentPassword, newPassword) => {
  const token = localStorage.getItem('token');
  const response = await axios.post(
    `${API_URL}/auth/change-password`,
    { current_password: currentPassword, new_password: newPassword },
    { headers: { Authorization: `Bearer ${token}` } }
  );
  return response.data;
};

// 2. Settings.jsx에서 실제 API 호출로 교체
const handlePasswordChange = async (e) => {
  e.preventDefault();

  // ... validation ...

  setPasswordLoading(true);
  setError('');
  setSuccess('');

  try {
    await changePassword(currentPassword, newPassword);
    setSuccess('✅ 비밀번호가 성공적으로 변경되었습니다!');
    setCurrentPassword('');
    setNewPassword('');
    setConfirmPassword('');
  } catch (err) {
    setError(err.response?.data?.detail || '비밀번호 변경에 실패했습니다.');
  } finally {
    setPasswordLoading(false);
  }
};
```

**백엔드 의존성**:
- ❌ `POST /auth/change-password`

---

#### 3. **Bitget 현재가 조회 재활성화** 🟡 PARTIAL
**파일**: `frontend/src/pages/Dashboard.jsx`
**라인**: 56-62

**현재 상태**:
- 일시적으로 비활성화됨
- 주석: `// loadPrices(); // Temporarily disabled due to Bitget API errors`

**필요한 작업**:
1. **백엔드 에러 처리 개선**:
   - API 키가 없을 때 500 대신 404나 빈 데이터 반환
   - 에러 메시지에 API 키 미설정 안내 포함

2. **프론트엔드 재활성화**:
```javascript
// Dashboard.jsx - useEffect에서 주석 제거
useEffect(() => {
  loadBotStatus();
  loadPrices(); // 주석 제거

  const interval = setInterval(() => {
    loadBotStatus();
    loadPrices(); // 주석 제거
  }, 30000);

  return () => clearInterval(interval);
}, []);
```

3. **에러 처리 개선**:
```javascript
const loadPrices = async () => {
  try {
    const symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT'];
    const prices = {};

    for (const symbol of symbols) {
      try {
        const ticker = await bitgetAPI.getTicker(symbol);
        if (ticker && ticker.last) {
          prices[symbol] = parseFloat(ticker.last);
        }
      } catch (err) {
        // API 키 미설정 시 무시
        if (err.response?.status === 404 || err.response?.status === 401) {
          console.log(`[Dashboard] ℹ️ API key not configured for ${symbol}`);
        } else {
          console.error(`[Dashboard] Error loading price for ${symbol}:`, err);
        }
      }
    }

    setCurrentPrices(prices);
  } catch (error) {
    console.error('[Dashboard] Error loading prices:', error);
    setCurrentPrices({});
  }
};
```

**백엔드 의존성**:
- ⚠️ `GET /bitget/ticker/{symbol}` - 에러 처리 개선 필요

---

### 🟡 중간 우선순위 (Medium)

#### 4. **리스크 지표 정확도 개선** 🟢 BACKEND EXISTS
**파일**: `frontend/src/components/RiskGauge.jsx`
**라인**: 16-38

**현재 상태**:
- 백엔드 API는 존재하지만 실제 데이터 부족 시 에러 발생
- Mock 데이터로 fallback: `{ mdd: -15.5, sharpe_ratio: 1.8, win_rate: 62.5 }`

**필요한 작업**:
1. **백엔드 개선**:
   - 데이터가 부족해도 계산 가능한 지표부터 반환
   - 최소 거래 수 미만일 때 null 대신 부분 데이터 반환

2. **프론트엔드 개선**:
```javascript
const loadRiskMetrics = async () => {
  try {
    setLoading(true);
    const data = await analyticsAPI.getRiskMetrics();

    // 데이터 검증 및 기본값 설정
    setRiskMetrics({
      mdd: data.mdd ?? 0,
      sharpe_ratio: data.sharpe_ratio ?? 0,
      win_rate: data.win_rate ?? 0,
      max_mdd_limit: data.max_mdd_limit ?? -25.0,
      max_leverage: data.max_leverage ?? 10
    });

    // 데이터 부족 경고 표시
    if (data.total_trades < 10) {
      setError(`충분한 거래 데이터가 없습니다 (${data.total_trades}/10 거래)`);
    } else {
      setError('');
    }
  } catch (err) {
    console.log('[RiskGauge] ℹ️ Using default data (insufficient trading history)');
    setError('거래 데이터 부족 - 10건 이상의 거래가 필요합니다');

    // 기본값 설정
    setRiskMetrics({
      mdd: 0,
      sharpe_ratio: 0,
      win_rate: 0,
      max_mdd_limit: -25.0,
      max_leverage: 10
    });
  } finally {
    setLoading(false);
  }
};
```

**백엔드 의존성**:
- ✅ `GET /analytics/risk-metrics` - 이미 구현됨, 개선 필요

---

#### 5. **자산 곡선 차트 활성화** ⚠️ BACKEND ISSUE
**파일**: `frontend/src/components/dashboard/PerformanceChart.jsx`
**라인**: 42-56

**현재 상태**:
- Mock 데이터만 사용 (모든 값이 0)
- 실제 API 호출 주석 처리됨 (lines 49-51)

**필요한 작업**:
1. **백엔드 데이터 확인**:
   - `/analytics/equity-curve` 엔드포인트 테스트
   - 데이터가 없을 때 빈 배열 반환 확인

2. **프론트엔드 활성화**:
```javascript
const loadEquityData = async (selectedPeriod) => {
  try {
    setLoading(true);

    const data = await analyticsAPI.getEquityCurve(selectedPeriod);

    if (!data || data.length === 0) {
      // 데이터 없을 때 초기 자본만 표시
      const initialCapital = 10000;
      setChartData([{
        timestamp: Date.now(),
        equity: initialCapital,
        benchmark: initialCapital
      }]);
      setNoDataMessage('거래 내역이 없습니다. 봇을 시작하면 자산 곡선이 표시됩니다.');
    } else {
      setChartData(data);
      setNoDataMessage('');
    }
  } catch (error) {
    console.error('[PerformanceChart] Error loading equity curve:', error);
    setChartData([]);
    setNoDataMessage('자산 곡선을 불러오는데 실패했습니다.');
  } finally {
    setLoading(false);
  }
};
```

**백엔드 의존성**:
- ✅ `GET /analytics/equity-curve` - 이미 구현됨

---

#### 6. **Rate Limiting 클라이언트 측 구현** 🟢 CAN START
**파일**: `frontend/src/api/account.js`
**라인**: 28 (getMyKeys 호출 시)

**현재 상태**:
- 백엔드에서 시간당 3회 제한
- 프론트엔드에서 제한 확인 없음

**필요한 작업**:
```javascript
// api/account.js
const API_KEY_VIEW_LIMIT = {
  count: 0,
  resetTime: null,
  maxRequests: 3,
  windowMs: 3600000 // 1 hour
};

export const accountAPI = {
  // ...

  async getMyKeys() {
    // 클라이언트 측 rate limit 확인
    const now = Date.now();

    if (API_KEY_VIEW_LIMIT.resetTime && now < API_KEY_VIEW_LIMIT.resetTime) {
      if (API_KEY_VIEW_LIMIT.count >= API_KEY_VIEW_LIMIT.maxRequests) {
        const remainingMs = API_KEY_VIEW_LIMIT.resetTime - now;
        const remainingMinutes = Math.ceil(remainingMs / 60000);
        throw new Error(
          `API 키 조회 한도 초과. ${remainingMinutes}분 후에 다시 시도하세요.`
        );
      }
    } else {
      // Reset window
      API_KEY_VIEW_LIMIT.count = 0;
      API_KEY_VIEW_LIMIT.resetTime = now + API_KEY_VIEW_LIMIT.windowMs;
    }

    try {
      const response = await apiClient.get('/account/my_keys');
      API_KEY_VIEW_LIMIT.count++;
      return response.data;
    } catch (error) {
      if (error.response?.status === 429) {
        // 백엔드에서 rate limit 초과
        const retryAfter = error.response.headers['retry-after'];
        throw new Error(
          `요청 한도 초과. ${retryAfter ? `${retryAfter}초` : '잠시'} 후에 다시 시도하세요.`
        );
      }
      throw error;
    }
  }
};
```

**Settings.jsx에서 에러 처리**:
```javascript
const handleShowKeys = async () => {
  try {
    const data = await accountAPI.getMyKeys();
    // ... show keys ...
  } catch (err) {
    if (err.message.includes('한도 초과')) {
      setError(`⏰ ${err.message}`);
    } else {
      setError('API 키를 불러오는데 실패했습니다.');
    }
  }
};
```

---

### 🟢 낮은 우선순위 (Low)

#### 7. **청산가 계산 고도화** 🟢 OPTIONAL
**파일**: `frontend/src/components/PositionList.jsx`
**라인**: 137-153

**현재 상태**:
- 간단한 공식 사용: `청산가 = 진입가 * (1 ± 1/레버리지)`
- 유지증거금율, 수수료 미반영

**필요한 작업**:
```javascript
// 정확한 청산가 계산
const calculateLiquidationPrice = (position) => {
  const entryPrice = parseFloat(position.entry_price);
  const leverage = parseFloat(position.leverage || 1);
  const side = position.side.toLowerCase();

  if (!entryPrice || leverage <= 0) return null;

  // Bitget 기준: 유지증거금율 0.5%, 수수료 고려
  const maintenanceMarginRate = 0.005; // 0.5%
  const takerFee = 0.0006; // 0.06%

  if (side === 'long' || side === 'buy') {
    // Long 청산가 = 진입가 * (1 - (1/레버리지 - 유지증거금율 - 수수료))
    return entryPrice * (1 - (1 / leverage - maintenanceMarginRate - takerFee));
  } else {
    // Short 청산가 = 진입가 * (1 + (1/레버리지 - 유지증거금율 - 수수료))
    return entryPrice * (1 + (1 / leverage - maintenanceMarginRate - takerFee));
  }
};
```

**참고**: Bitget API에서 청산가를 직접 제공하지 않으므로 프론트엔드 계산 필요

---

#### 8. **성능 최적화** 🟢 OPTIONAL

**React.memo 적용**:
```javascript
// 자주 리렌더링되는 컴포넌트에 React.memo 적용
import { memo } from 'react';

export default memo(function PositionList({ currentPrices, onClosePosition, onPositionClosed }) {
  // ...
}, (prevProps, nextProps) => {
  // 커스텀 비교 함수
  return JSON.stringify(prevProps.currentPrices) === JSON.stringify(nextProps.currentPrices);
});
```

**useMemo로 계산 결과 캐싱**:
```javascript
// Dashboard.jsx
const sortedPositions = useMemo(() => {
  return positions.sort((a, b) => b.pnl - a.pnl);
}, [positions]);
```

**API 요청 중복 제거**:
```javascript
// useEffect 의존성 배열 최적화
useEffect(() => {
  if (!isConnected || !botStatus) return;

  const unsubscribe = subscribe('price_update', handlePriceUpdate);
  return unsubscribe;
}, [isConnected, botStatus?.status]); // 불필요한 재구독 방지
```

---

#### 9. **에러 바운더리 추가** 🟢 OPTIONAL
**위치**: `frontend/src/components/ErrorBoundary.jsx` (신규 생성)

```javascript
import React from 'react';

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('[ErrorBoundary] Caught error:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{
          padding: '2rem',
          textAlign: 'center',
          background: '#fff3e0',
          border: '2px solid #ff9800',
          borderRadius: '8px',
          margin: '2rem'
        }}>
          <h2>⚠️ 문제가 발생했습니다</h2>
          <p>페이지를 새로고침하거나 관리자에게 문의하세요.</p>
          <details style={{ marginTop: '1rem', textAlign: 'left' }}>
            <summary>에러 상세 정보</summary>
            <pre style={{
              background: '#f5f5f5',
              padding: '1rem',
              borderRadius: '4px',
              overflow: 'auto',
              fontSize: '0.875rem'
            }}>
              {this.state.error?.toString()}
            </pre>
          </details>
          <button
            onClick={() => window.location.reload()}
            style={{
              marginTop: '1rem',
              padding: '0.75rem 1.5rem',
              background: '#ff9800',
              color: 'white',
              border: 'none',
              borderRadius: '6px',
              cursor: 'pointer',
              fontWeight: 'bold'
            }}
          >
            🔄 페이지 새로고침
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
```

**App.jsx에서 적용**:
```javascript
import ErrorBoundary from './components/ErrorBoundary';

function App() {
  return (
    <ErrorBoundary>
      <Router>
        {/* ... */}
      </Router>
    </ErrorBoundary>
  );
}
```

---

#### 10. **접근성 개선** 🟢 OPTIONAL

**키보드 네비게이션**:
```javascript
// 버튼에 명확한 aria-label 추가
<button
  onClick={handlePanicClose}
  aria-label="모든 포지션 긴급 청산"
  disabled={panicClosing}
>
  🚨 Panic Close
</button>

// 테이블에 aria-describedby 추가
<table aria-describedby="positions-description">
  <caption id="positions-description">
    현재 활성 포지션 목록 - 총 {positions.length}개
  </caption>
  {/* ... */}
</table>
```

**색각 이상 대응**:
```javascript
// 색상에만 의존하지 않고 아이콘/텍스트도 함께 표시
const getPnLDisplay = (pnl) => {
  if (pnl > 0) {
    return {
      color: '#4caf50',
      icon: '↑',
      label: '수익'
    };
  } else if (pnl < 0) {
    return {
      color: '#f44336',
      icon: '↓',
      label: '손실'
    };
  }
  return {
    color: '#666',
    icon: '→',
    label: '본전'
  };
};
```

---

## ⚙️ Backend 남은 작업

### 🔴 높은 우선순위 (Critical)

#### 1. **리스크 설정 API 구현** ❌ NOT IMPLEMENTED
**파일**: `backend/src/api/account.py` (신규 추가)

**필요한 작업**:

**1) Database Model 추가**:
```python
# backend/src/database/models.py
class RiskSettings(Base):
    __tablename__ = "risk_settings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    daily_loss_limit = Column(Float, nullable=False, default=500.0)  # USDT
    max_leverage = Column(Integer, nullable=False, default=10)  # 1-100배
    max_positions = Column(Integer, nullable=False, default=5)  # 1-50개
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="risk_settings")

    __table_args__ = (
        CheckConstraint('daily_loss_limit > 0', name='check_positive_loss_limit'),
        CheckConstraint('max_leverage >= 1 AND max_leverage <= 100', name='check_leverage_range'),
        CheckConstraint('max_positions >= 1 AND max_positions <= 50', name='check_positions_range'),
    )
```

**User 모델에 관계 추가**:
```python
class User(Base):
    # ... existing fields ...
    risk_settings = relationship("RiskSettings", back_populates="user", uselist=False)
```

**2) API Endpoints 구현**:
```python
# backend/src/api/account.py에 추가

@router.get("/risk-settings")
async def get_risk_settings(
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """
    사용자 리스크 설정 조회

    Returns:
        - daily_loss_limit: 일일 손실 한도 (USDT)
        - max_leverage: 최대 레버리지 (1-100)
        - max_positions: 최대 포지션 개수 (1-50)
    """
    try:
        result = await session.execute(
            select(RiskSettings).where(RiskSettings.user_id == user_id)
        )
        settings = result.scalar_one_or_none()

        if not settings:
            # 기본 설정 반환
            return {
                "daily_loss_limit": 500.0,
                "max_leverage": 10,
                "max_positions": 5,
                "is_default": True
            }

        return {
            "daily_loss_limit": settings.daily_loss_limit,
            "max_leverage": settings.max_leverage,
            "max_positions": settings.max_positions,
            "is_default": False,
            "updated_at": settings.updated_at.isoformat()
        }
    except Exception as e:
        logger.error(f"Error fetching risk settings: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="리스크 설정 조회 실패")


@router.post("/risk-settings")
async def save_risk_settings(
    daily_loss_limit: float = Body(..., gt=0),
    max_leverage: int = Body(..., ge=1, le=100),
    max_positions: int = Body(..., ge=1, le=50),
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """
    리스크 설정 저장/업데이트

    Args:
        daily_loss_limit: 일일 손실 한도 (USDT, > 0)
        max_leverage: 최대 레버리지 (1-100)
        max_positions: 최대 포지션 개수 (1-50)
    """
    try:
        # 기존 설정 조회
        result = await session.execute(
            select(RiskSettings).where(RiskSettings.user_id == user_id)
        )
        settings = result.scalar_one_or_none()

        if settings:
            # 업데이트
            settings.daily_loss_limit = daily_loss_limit
            settings.max_leverage = max_leverage
            settings.max_positions = max_positions
            settings.updated_at = datetime.utcnow()
        else:
            # 신규 생성
            settings = RiskSettings(
                user_id=user_id,
                daily_loss_limit=daily_loss_limit,
                max_leverage=max_leverage,
                max_positions=max_positions
            )
            session.add(settings)

        await session.commit()
        await session.refresh(settings)

        logger.info(f"Risk settings saved for user {user_id}: "
                   f"loss_limit={daily_loss_limit}, leverage={max_leverage}, "
                   f"positions={max_positions}")

        return {
            "message": "리스크 설정이 저장되었습니다",
            "daily_loss_limit": settings.daily_loss_limit,
            "max_leverage": settings.max_leverage,
            "max_positions": settings.max_positions
        }
    except Exception as e:
        await session.rollback()
        logger.error(f"Error saving risk settings: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="리스크 설정 저장 실패")
```

**3) Migration 실행**:
```bash
cd backend
alembic revision --autogenerate -m "Add risk_settings table"
alembic upgrade head
```

---

#### 2. **비밀번호 변경 API 구현** ❌ NOT IMPLEMENTED
**파일**: `backend/src/api/auth.py` (기존 파일에 추가)

**필요한 작업**:
```python
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

@router.post("/change-password")
async def change_password(
    current_password: str = Body(...),
    new_password: str = Body(..., min_length=6),
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """
    비밀번호 변경

    Args:
        current_password: 현재 비밀번호
        new_password: 새 비밀번호 (최소 6자)

    Returns:
        성공 메시지
    """
    try:
        # 사용자 조회
        result = await session.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다")

        # 현재 비밀번호 확인
        if not pwd_context.verify(current_password, user.password_hash):
            raise HTTPException(status_code=400, detail="현재 비밀번호가 일치하지 않습니다")

        # 새 비밀번호와 현재 비밀번호가 같은지 확인
        if current_password == new_password:
            raise HTTPException(status_code=400, detail="새 비밀번호는 현재 비밀번호와 달라야 합니다")

        # 비밀번호 강도 검증 (선택사항)
        if len(new_password) < 6:
            raise HTTPException(status_code=400, detail="비밀번호는 최소 6자 이상이어야 합니다")

        # 새 비밀번호 해시 및 저장
        user.password_hash = pwd_context.hash(new_password)
        await session.commit()

        logger.info(f"Password changed for user {user_id} ({user.email})")

        return {"message": "비밀번호가 성공적으로 변경되었습니다"}

    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        logger.error(f"Error changing password: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="비밀번호 변경 실패")
```

**보안 강화 (선택사항)**:
```python
import re

def validate_password_strength(password: str):
    """
    비밀번호 강도 검증
    - 최소 8자
    - 대문자 1개 이상
    - 소문자 1개 이상
    - 숫자 1개 이상
    """
    if len(password) < 8:
        return False, "비밀번호는 최소 8자 이상이어야 합니다"

    if not re.search(r'[A-Z]', password):
        return False, "대문자를 최소 1개 포함해야 합니다"

    if not re.search(r'[a-z]', password):
        return False, "소문자를 최소 1개 포함해야 합니다"

    if not re.search(r'[0-9]', password):
        return False, "숫자를 최소 1개 포함해야 합니다"

    return True, ""

# change_password 함수에서 사용:
is_valid, error_msg = validate_password_strength(new_password)
if not is_valid:
    raise HTTPException(status_code=400, detail=error_msg)
```

---

#### 3. **Signal Tracking 구현** ⚠️ TODO EXISTS
**파일**: `backend/src/services/bot.py`
**라인**: 208

**현재 상태**:
- `lastSignal`과 `lastSignalTime`이 항상 None 반환
- 주석: `# TODO: 실제 시그널 데이터 연동`

**필요한 작업**:

**1) Database Model 추가**:
```python
# backend/src/database/models.py
class TradingSignal(Base):
    __tablename__ = "trading_signals"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    strategy_id = Column(Integer, ForeignKey("strategies.id"))
    symbol = Column(String(20), nullable=False)
    signal_type = Column(String(10), nullable=False)  # BUY, SELL, HOLD
    timeframe = Column(String(10), nullable=False)
    price = Column(Float)
    indicators = Column(JSON)  # 시그널 생성 시 사용된 지표 값
    confidence = Column(Float)  # 신호 신뢰도 (0-1)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    user = relationship("User")
    strategy = relationship("Strategy")
```

**2) Signal 기록 함수**:
```python
# backend/src/services/signal_tracker.py (신규 생성)
import logging
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.models import TradingSignal

logger = logging.getLogger(__name__)

class SignalTracker:
    """트레이딩 시그널 추적 및 기록"""

    @staticmethod
    async def record_signal(
        session: AsyncSession,
        user_id: int,
        strategy_id: int,
        symbol: str,
        signal_type: str,
        timeframe: str,
        price: float = None,
        indicators: dict = None,
        confidence: float = None
    ):
        """
        시그널 기록

        Args:
            signal_type: BUY, SELL, HOLD
            indicators: {"rsi": 65, "macd": 0.05, ...}
            confidence: 0.0 ~ 1.0
        """
        try:
            signal = TradingSignal(
                user_id=user_id,
                strategy_id=strategy_id,
                symbol=symbol,
                signal_type=signal_type.upper(),
                timeframe=timeframe,
                price=price,
                indicators=indicators,
                confidence=confidence,
                timestamp=datetime.utcnow()
            )

            session.add(signal)
            await session.commit()

            logger.info(f"Signal recorded: {signal_type} {symbol} @ {price} "
                       f"(confidence: {confidence})")

            return signal

        except Exception as e:
            await session.rollback()
            logger.error(f"Error recording signal: {e}", exc_info=True)
            return None

    @staticmethod
    async def get_latest_signal(
        session: AsyncSession,
        user_id: int,
        symbol: str = None
    ):
        """최근 시그널 조회"""
        try:
            query = select(TradingSignal).where(
                TradingSignal.user_id == user_id
            )

            if symbol:
                query = query.where(TradingSignal.symbol == symbol)

            query = query.order_by(TradingSignal.timestamp.desc()).limit(1)

            result = await session.execute(query)
            signal = result.scalar_one_or_none()

            return signal

        except Exception as e:
            logger.error(f"Error fetching latest signal: {e}", exc_info=True)
            return None
```

**3) Bot 서비스에서 사용**:
```python
# backend/src/services/bot.py
from .signal_tracker import SignalTracker

class TradingBot:
    async def execute_strategy(self):
        """전략 실행 및 시그널 생성"""
        try:
            # ... 기존 전략 실행 코드 ...

            # 시그널 생성
            signal_type = self.strategy.generate_signal(data)

            # 시그널 기록
            await SignalTracker.record_signal(
                session=self.session,
                user_id=self.user_id,
                strategy_id=self.strategy_id,
                symbol=self.symbol,
                signal_type=signal_type,
                timeframe=self.timeframe,
                price=current_price,
                indicators={
                    "rsi": data.get("rsi"),
                    "macd": data.get("macd"),
                    # ... other indicators
                },
                confidence=0.75
            )

            # ... 주문 실행 ...

        except Exception as e:
            logger.error(f"Error executing strategy: {e}", exc_info=True)

async def get_bot_status(user_id: int, session: AsyncSession):
    # ... 기존 코드 ...

    # 최근 시그널 조회
    latest_signal = await SignalTracker.get_latest_signal(
        session=session,
        user_id=user_id
    )

    return {
        # ... 기존 필드 ...
        "lastSignal": latest_signal.signal_type if latest_signal else None,
        "lastSignalTime": latest_signal.timestamp.isoformat() if latest_signal else None,
        "lastSignalPrice": latest_signal.price if latest_signal else None,
        "lastSignalConfidence": latest_signal.confidence if latest_signal else None
    }
```

**4) Migration 실행**:
```bash
alembic revision --autogenerate -m "Add trading_signals table"
alembic upgrade head
```

---

### 🟡 중간 우선순위 (Medium)

#### 4. **Rate Limiting JWT 통합** ⚠️ TODO EXISTS
**파일**: `backend/src/middleware/rate_limit.py`
**라인**: 134

**현재 상태**:
- 주석: `# TODO: JWT 토큰 파싱 구현`
- 사용자별 rate limiting이 제대로 작동하지 않을 수 있음

**필요한 작업**:
```python
# backend/src/middleware/rate_limit.py

import jwt
from typing import Optional

def extract_user_id_from_token(authorization: str) -> Optional[int]:
    """
    JWT 토큰에서 user_id 추출

    Args:
        authorization: "Bearer <token>" 형식

    Returns:
        user_id 또는 None
    """
    try:
        if not authorization or not authorization.startswith("Bearer "):
            return None

        token = authorization.split(" ")[1]

        # JWT 디코드 (SECRET_KEY는 환경 변수에서)
        import os
        SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key")
        ALGORITHM = "HS256"

        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("user_id")

        return int(user_id) if user_id else None

    except jwt.ExpiredSignatureError:
        # 토큰 만료
        return None
    except jwt.InvalidTokenError:
        # 유효하지 않은 토큰
        return None
    except Exception as e:
        logger.error(f"Error extracting user_id from token: {e}")
        return None


async def rate_limit_middleware(request: Request, call_next):
    # ... 기존 코드 ...

    # JWT에서 user_id 추출
    authorization = request.headers.get("Authorization", "")
    user_id = extract_user_id_from_token(authorization)

    if user_id:
        # 사용자별 rate limit 적용
        user_key = f"user:{user_id}:{endpoint}"
        user_limit = USER_RATE_LIMITS.get(endpoint, {"requests": 100, "window": 3600})

        if not await check_rate_limit(user_key, user_limit["requests"], user_limit["window"]):
            return JSONResponse(
                status_code=429,
                content={
                    "detail": f"User rate limit exceeded for {endpoint}",
                    "retry_after": user_limit["window"]
                }
            )

    # IP 기반 rate limit (기존 코드)
    # ...
```

---

#### 5. **Bitget API 에러 처리 개선** 🟡 PARTIAL
**파일**: `backend/src/api/bitget.py`

**현재 문제**:
- API 키 없을 때 500 에러 반환
- 프론트엔드에서 콘솔 에러 발생

**필요한 작업**:
```python
# backend/src/api/bitget.py

@router.get("/ticker/{symbol}")
async def get_ticker(
    symbol: str,
    user_id: int = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session)
):
    """현재가 조회"""
    try:
        # API 키 조회
        api_keys = await get_user_api_keys(user_id, session)

        if not api_keys:
            # API 키 없을 때 404 반환 (500 대신)
            raise HTTPException(
                status_code=404,
                detail="API 키가 설정되지 않았습니다. Settings에서 API 키를 등록하세요."
            )

        # Bitget API 호출
        exchange = BitgetExchange(api_keys)
        ticker = await exchange.get_ticker(symbol)

        return ticker

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching ticker for {symbol}: {e}", exc_info=True)

        # 구체적인 에러 메시지
        if "Invalid API-KEY" in str(e):
            raise HTTPException(
                status_code=401,
                detail="유효하지 않은 API 키입니다. Settings에서 API 키를 확인하세요."
            )
        elif "timeout" in str(e).lower():
            raise HTTPException(
                status_code=504,
                detail="Bitget API 연결 시간 초과. 잠시 후 다시 시도하세요."
            )
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Ticker 조회 실패: {str(e)}"
            )


@router.get("/account")
async def get_account(
    user_id: int = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session)
):
    """계정 정보 조회"""
    try:
        api_keys = await get_user_api_keys(user_id, session)

        if not api_keys:
            # 빈 계정 정보 반환 (에러 대신)
            return {
                "total_equity": 0,
                "available_balance": 0,
                "unrealized_pnl": 0,
                "margin_used": 0,
                "api_key_configured": False,
                "message": "API 키가 설정되지 않았습니다"
            }

        exchange = BitgetExchange(api_keys)
        account = await exchange.get_account()

        return {
            **account,
            "api_key_configured": True
        }

    except Exception as e:
        logger.error(f"Error fetching account info: {e}", exc_info=True)

        # 에러 시에도 빈 데이터 반환
        return {
            "total_equity": 0,
            "available_balance": 0,
            "unrealized_pnl": 0,
            "margin_used": 0,
            "api_key_configured": True,
            "error": str(e)
        }
```

---

#### 6. **Analytics API 개선** 🟡 EXISTS BUT NEEDS WORK
**파일**: `backend/src/api/analytics.py`

**필요한 개선사항**:
```python
@router.get("/risk-metrics")
async def get_risk_metrics(
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """
    리스크 지표 계산

    개선사항:
    - 데이터 부족 시에도 부분 지표 반환
    - 최소 거래 수 기준 완화
    """
    try:
        # 거래 내역 조회
        result = await session.execute(
            select(Trade).where(
                Trade.user_id == user_id,
                Trade.exit_price.isnot(None)
            ).order_by(Trade.created_at.desc())
        )
        trades = result.scalars().all()

        total_trades = len(trades)

        # 데이터 부족 시 기본값 반환 (에러 대신)
        if total_trades == 0:
            return {
                "max_drawdown": 0.0,
                "sharpe_ratio": 0.0,
                "win_rate": 0.0,
                "profit_loss_ratio": 0.0,
                "daily_volatility": 0.0,
                "total_trades": 0,
                "message": "거래 데이터가 없습니다",
                "data_sufficient": False
            }

        # 부분 지표 계산 (거래 수가 적어도)
        winning_trades = [t for t in trades if t.pnl and t.pnl > 0]
        losing_trades = [t for t in trades if t.pnl and t.pnl < 0]

        win_rate = (len(winning_trades) / total_trades * 100) if total_trades > 0 else 0

        # MDD, Sharpe Ratio는 최소 10거래 필요
        if total_trades < 10:
            return {
                "max_drawdown": 0.0,
                "sharpe_ratio": 0.0,
                "win_rate": round(win_rate, 2),
                "profit_loss_ratio": 0.0,
                "daily_volatility": 0.0,
                "total_trades": total_trades,
                "message": f"거래 데이터 부족 ({total_trades}/10). 승률만 표시됩니다.",
                "data_sufficient": False
            }

        # ... 기존 MDD, Sharpe Ratio 계산 ...

        return {
            "max_drawdown": mdd,
            "sharpe_ratio": sharpe_ratio,
            "win_rate": round(win_rate, 2),
            "profit_loss_ratio": pl_ratio,
            "daily_volatility": volatility,
            "total_trades": total_trades,
            "data_sufficient": True
        }

    except Exception as e:
        logger.error(f"Error calculating risk metrics: {e}", exc_info=True)
        # 에러 시에도 기본값 반환 (500 에러 대신)
        return {
            "max_drawdown": 0.0,
            "sharpe_ratio": 0.0,
            "win_rate": 0.0,
            "profit_loss_ratio": 0.0,
            "daily_volatility": 0.0,
            "total_trades": 0,
            "error": str(e),
            "data_sufficient": False
        }
```

---

### 🟢 낮은 우선순위 (Low)

#### 7. **Input Validation 강화** 🟢 OPTIONAL

**주문 제출 시 검증 강화**:
```python
# backend/src/api/order.py

from pydantic import BaseModel, Field, validator

class OrderSubmitRequest(BaseModel):
    symbol: str = Field(..., regex=r'^[A-Z]+USDT$')
    side: str = Field(..., regex=r'^(buy|sell)$')
    size: float = Field(..., gt=0, le=1000000)
    price: Optional[float] = Field(None, gt=0)
    leverage: int = Field(default=1, ge=1, le=125)

    @validator('symbol')
    def normalize_symbol(cls, v):
        """심볼 정규화"""
        return v.upper().replace('/', '').replace('-', '')

    @validator('size')
    def validate_size(cls, v, values):
        """최소/최대 수량 검증"""
        symbol = values.get('symbol', '')

        # BTC 최소 0.0001, 최대 100
        if 'BTC' in symbol:
            if v < 0.0001 or v > 100:
                raise ValueError('BTC 수량은 0.0001 ~ 100 사이여야 합니다')

        # ETH 최소 0.001, 최대 1000
        elif 'ETH' in symbol:
            if v < 0.001 or v > 1000:
                raise ValueError('ETH 수량은 0.001 ~ 1000 사이여야 합니다')

        return v


@router.post("/submit")
async def submit_order(
    order: OrderSubmitRequest,
    user_id: int = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session)
):
    """주문 제출 (검증 강화)"""
    # ... 구현 ...
```

---

#### 8. **WebSocket 연결 관리 개선** 🟢 OPTIONAL

**자동 재연결 및 정리**:
```python
# backend/src/services/websocket_manager.py

class WebSocketManager:
    def __init__(self):
        self.active_connections: Dict[int, List[WebSocket]] = {}
        self.heartbeat_task = None

    async def start_heartbeat(self):
        """주기적으로 연결 상태 확인"""
        while True:
            await asyncio.sleep(30)

            for user_id, connections in self.active_connections.items():
                for ws in connections[:]:  # 복사본으로 순회
                    try:
                        await ws.send_json({"type": "ping"})
                    except Exception:
                        # 연결 끊김 - 목록에서 제거
                        connections.remove(ws)
                        logger.info(f"Removed stale connection for user {user_id}")

    async def connect(self, websocket: WebSocket, user_id: int):
        await websocket.accept()

        if user_id not in self.active_connections:
            self.active_connections[user_id] = []

        self.active_connections[user_id].append(websocket)

        # Heartbeat 시작 (첫 연결 시)
        if not self.heartbeat_task:
            self.heartbeat_task = asyncio.create_task(self.start_heartbeat())

        logger.info(f"WebSocket connected for user {user_id}")

    async def disconnect(self, websocket: WebSocket, user_id: int):
        if user_id in self.active_connections:
            self.active_connections[user_id].remove(websocket)

            # 연결이 없으면 user_id 제거
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]

        logger.info(f"WebSocket disconnected for user {user_id}")
```

---

#### 9. **Caching Layer 추가** 🟢 OPTIONAL

**Redis를 활용한 캐싱**:
```python
# backend/src/services/cache.py
import redis.asyncio as redis
import json
from typing import Optional, Any

class CacheService:
    def __init__(self):
        self.redis_client = None

    async def connect(self):
        """Redis 연결"""
        self.redis_client = await redis.from_url(
            "redis://localhost:6379",
            encoding="utf-8",
            decode_responses=True
        )

    async def get(self, key: str) -> Optional[Any]:
        """캐시에서 데이터 조회"""
        try:
            value = await self.redis_client.get(key)
            return json.loads(value) if value else None
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None

    async def set(self, key: str, value: Any, ttl: int = 300):
        """캐시에 데이터 저장 (기본 TTL: 5분)"""
        try:
            await self.redis_client.set(
                key,
                json.dumps(value),
                ex=ttl
            )
        except Exception as e:
            logger.error(f"Cache set error: {e}")

    async def delete(self, key: str):
        """캐시 삭제"""
        try:
            await self.redis_client.delete(key)
        except Exception as e:
            logger.error(f"Cache delete error: {e}")

cache_service = CacheService()

# 사용 예시 (analytics.py):
@router.get("/risk-metrics")
async def get_risk_metrics(
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    # 캐시 확인
    cache_key = f"risk_metrics:{user_id}"
    cached = await cache_service.get(cache_key)

    if cached:
        logger.info(f"Risk metrics cache hit for user {user_id}")
        return cached

    # 캐시 미스 - 계산
    metrics = await calculate_risk_metrics(session, user_id)

    # 캐시 저장 (5분)
    await cache_service.set(cache_key, metrics, ttl=300)

    return metrics
```

---

#### 10. **Logging 개선** 🟢 OPTIONAL

**구조화된 로깅**:
```python
# backend/src/utils/structured_logging.py
import logging
import json
from datetime import datetime

class StructuredLogger:
    """JSON 형식의 구조화된 로그"""

    def __init__(self, name: str):
        self.logger = logging.getLogger(name)

    def log_event(
        self,
        level: str,
        event: str,
        user_id: int = None,
        **kwargs
    ):
        """
        구조화된 이벤트 로깅

        Example:
            logger.log_event(
                "INFO",
                "order_submitted",
                user_id=123,
                symbol="BTCUSDT",
                side="buy",
                size=0.001
            )
        """
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": level,
            "event": event,
            "user_id": user_id,
            **kwargs
        }

        log_method = getattr(self.logger, level.lower())
        log_method(json.dumps(log_data))

# 사용 예시:
from .utils.structured_logging import StructuredLogger

logger = StructuredLogger(__name__)

@router.post("/submit")
async def submit_order(...):
    logger.log_event(
        "INFO",
        "order_submitted",
        user_id=user_id,
        symbol=symbol,
        side=side,
        size=size,
        leverage=leverage
    )
```

---

## 🎯 우선순위 매트릭스

### 즉시 시작 가능 (Frontend Only)

| 작업 | 예상 시간 | 난이도 | 파일 |
|------|----------|--------|------|
| Rate Limiting 클라이언트 구현 | 30분 | 쉬움 | `api/account.js` |
| 청산가 계산 고도화 | 20분 | 쉬움 | `components/PositionList.jsx` |
| 성능 최적화 (React.memo) | 1시간 | 보통 | 여러 컴포넌트 |
| 에러 바운더리 추가 | 30분 | 쉬움 | `components/ErrorBoundary.jsx` |
| 접근성 개선 | 1시간 | 쉬움 | 여러 컴포넌트 |

### 백엔드 필요 (Critical)

| 작업 | 예상 시간 | 난이도 | 우선순위 | 의존성 |
|------|----------|--------|---------|--------|
| **리스크 설정 API** | 2시간 | 보통 | 🔴 최고 | DB Migration |
| **비밀번호 변경 API** | 1시간 | 쉬움 | 🔴 최고 | 없음 |
| **Signal Tracking** | 3시간 | 어려움 | 🔴 최고 | DB Migration |
| **Bitget API 에러 처리** | 1시간 | 쉬움 | 🟡 높음 | 없음 |
| **현재가 조회 재활성화** | 30분 | 쉬움 | 🟡 높음 | Bitget API 개선 |
| **Analytics API 개선** | 2시간 | 보통 | 🟡 중간 | 없음 |
| **Rate Limiting JWT** | 1.5시간 | 보통 | 🟡 중간 | 없음 |

### 선택사항 (Optional)

| 작업 | 예상 시간 | 난이도 | 효과 |
|------|----------|--------|------|
| Input Validation 강화 | 2시간 | 보통 | 보안 향상 |
| WebSocket 관리 개선 | 2시간 | 어려움 | 안정성 향상 |
| Caching Layer (Redis) | 4시간 | 어려움 | 성능 대폭 향상 |
| 구조화된 Logging | 2시간 | 보통 | 디버깅 용이 |

---

## ⚡ 즉시 실행 가능한 작업

### 1단계: 프론트엔드만으로 개선 (총 3시간)
```bash
# 1. Rate Limiting 클라이언트 구현 (30분)
# 파일: frontend/src/api/account.js

# 2. 청산가 계산 고도화 (20분)
# 파일: frontend/src/components/PositionList.jsx

# 3. 에러 바운더리 추가 (30분)
# 파일: frontend/src/components/ErrorBoundary.jsx (신규)

# 4. 성능 최적화 (React.memo) (1시간)
# 파일: 여러 컴포넌트에 적용

# 5. 접근성 개선 (1시간)
# 파일: 여러 컴포넌트에 aria-label 추가
```

### 2단계: Critical 백엔드 작업 (총 7시간)
```bash
# 1. 리스크 설정 API 구현 (2시간)
# - Database model 추가
# - API endpoints 생성
# - Migration 실행
# 파일: backend/src/database/models.py, backend/src/api/account.py

# 2. 비밀번호 변경 API 구현 (1시간)
# 파일: backend/src/api/auth.py

# 3. Signal Tracking 구현 (3시간)
# - Database model 추가
# - Signal tracker 서비스 생성
# - Bot 서비스 통합
# 파일: backend/src/database/models.py, backend/src/services/signal_tracker.py

# 4. Bitget API 에러 처리 개선 (1시간)
# 파일: backend/src/api/bitget.py
```

### 3단계: 프론트엔드 API 연동 (총 2시간)
```bash
# 1. 리스크 설정 API 연동 (40분)
# 파일: frontend/src/api/account.js, frontend/src/pages/Settings.jsx

# 2. 비밀번호 변경 API 연동 (30분)
# 파일: frontend/src/api/auth.js, frontend/src/pages/Settings.jsx

# 3. 현재가 조회 재활성화 (20분)
# 파일: frontend/src/pages/Dashboard.jsx

# 4. 리스크 지표 에러 처리 개선 (30분)
# 파일: frontend/src/components/RiskGauge.jsx
```

---

## 📊 전체 작업 요약

### Frontend
- **🔴 Critical**: 3개 (리스크 설정, 비밀번호, 현재가)
- **🟡 Medium**: 3개 (리스크 지표, 자산 곡선, Rate Limiting)
- **🟢 Low**: 4개 (청산가, 성능, 에러 바운더리, 접근성)
- **총 10개 작업**

### Backend
- **🔴 Critical**: 3개 (리스크 설정, 비밀번호, Signal Tracking)
- **🟡 Medium**: 3개 (Rate Limiting JWT, Bitget 에러, Analytics)
- **🟢 Low**: 4개 (Validation, WebSocket, Caching, Logging)
- **총 10개 작업**

### 예상 소요 시간
- **즉시 시작 가능 (Frontend)**: 3시간
- **Critical 백엔드**: 7시간
- **API 연동**: 2시간
- **Optional 작업**: 12시간+
- **총합 (필수만)**: **12시간**
- **총합 (전체)**: **24시간+**

---

## ✅ 완료 체크리스트

### Phase 1: 즉시 실행 (3시간)
- [x] ✅ **Rate Limiting 클라이언트 구현** (완료 - 2025-12-04)
  - API_KEY_VIEW_LIMIT 객체로 클라이언트 측 rate limit 추적
  - 시간당 3회 제한, 사용자 친화적 에러 메시지
  - 백엔드 429 에러 처리
- [x] ✅ **청산가 계산 고도화** (완료 - 2025-12-04)
  - Bitget 기준: 유지증거금율 0.5%, 수수료 0.06% 반영
  - Long/Short 포지션 별 정확한 공식 적용
  - calculateLiquidationPrice 함수 개선
- [x] ✅ **에러 바운더리 추가** (완료 - 2025-12-04)
  - App.jsx 최상위 레벨 적용
  - LiveTrading.jsx - 4개 컴포넌트 개별 적용
  - Performance.jsx - 4개 컴포넌트 개별 적용
  - Dashboard.jsx - 4개 컴포넌트 개별 적용
- [x] ✅ **React.memo 성능 최적화** (완료 - 2025-12-04)
  - BalanceCard, RiskGauge, OrderActivityLog, PositionList에 memo 적용
  - 불필요한 리렌더링 방지
- [x] ✅ **접근성 개선** (완료 - 2025-12-04)
  - PositionList.jsx에 ARIA 레이블 추가
  - 버튼 aria-label, aria-busy 속성 추가
  - 테이블 role, aria-describedby 추가
  - 시각적으로 숨겨진 caption (screen reader용)
  - 개별 포지션 청산 버튼 접근성 개선
  - 남은 작업: 색각 이상 대응, 다른 페이지 적용 (선택사항)

### Phase 2: Critical Backend (7시간)
- [x] ✅ **리스크 설정 API 구현** (완료 - 2025-12-04)
  - Database model 추가 (RiskSettings)
  - GET /account/risk-settings 구현
  - POST /account/risk-settings 구현
  - Migration 생성 및 적용
- [x] ✅ **비밀번호 변경 API 구현** (완료 - 2025-12-04)
  - ChangePasswordRequest schema 추가
  - POST /auth/change-password 엔드포인트 구현
  - 현재 비밀번호 검증
  - 비밀번호 강도 검증 (최소 8자, 대/소문자, 숫자, 특수문자)
  - 테스트 완료 (에러 케이스 및 정상 케이스)
- [x] ✅ **Signal Tracking 구현** (완료 - 2025-12-04)
  - Database model 추가 (TradingSignal)
  - SignalTracker 서비스 구현 (record_signal, get_latest_signal, get_recent_signals)
  - Bot status API에 시그널 조회 연동 (lastSignal, lastSignalTime)
  - Migration 생성 및 적용
- [x] ✅ **Bitget API 에러 처리 개선** (완료 - 2025-12-04)
  - 커스텀 예외 클래스 구현 (BitgetAPIError, RateLimitError, AuthenticationError 등)
  - Retry 로직 구현 (Exponential backoff with 최대 3회 재시도)
  - 에러 분류 시스템 (classify_bitget_error)
  - 사용자 친화적 에러 메시지 개선
  - Timeout, Network 에러 별도 처리
  - 로깅 강화

### Phase 3: API 연동 (2시간)
- [x] ✅ **리스크 설정 프론트엔드 연동** (완료 - 2025-12-04)
  - accountAPI.getRiskSettings() 추가
  - accountAPI.saveRiskSettings() 추가
  - Settings.jsx 실제 API 호출로 변경
  - 테스트 완료
- [x] ✅ **비밀번호 변경 프론트엔드 연동** (완료 - 2025-12-04)
  - authAPI.changePassword() 메서드 추가
  - Settings.jsx에서 실제 API 호출로 변경
  - 에러 처리 및 성공 메시지 구현
  - 테스트 완료
- [x] ✅ **현재가 조회 재활성화** (완료 - 2025-12-04)
  - Dashboard.jsx의 loadPrices() 주석 제거
  - 30초마다 자동 갱신 재활성화
  - Bitget API 에러 처리 개선으로 안정적 작동
  - Graceful degradation (API 키 없어도 UI 정상 작동)
- [x] ✅ **리스크 지표 에러 처리** (완료 - 2025-12-04)
  - 데이터 검증 및 기본값 설정 (Null coalescing)
  - 거래 데이터 부족 시 경고 메시지 표시
  - 404 에러 별도 처리
  - Graceful degradation (기본값 0으로 표시)
  - 에러 메시지 UI 개선

### Phase 4: Optional (선택)
- [x] ✅ **Input Validation 강화** (완료 - 2025-12-04)
  - BotStartRequest 검증 (strategy_id 양수, 상한선 체크)
  - MarketOrderRequest 검증 (symbol, side, size 엄격 검증)
  - LimitOrderRequest 검증 (price, size 소수점 자리수 제한)
  - ClosePositionRequest 검증
  - SetLeverageRequest 검증 (1-125, 높은 레버리지 경고)
  - CancelOrderRequest 검증 (order_id 형식 체크)
  - RiskSettingsRequest 검증 (daily_loss_limit, max_leverage, max_positions)
  - 모든 API 엔드포인트에 Pydantic 스키마 적용
  - ValueError 에러 핸들링으로 사용자 친화적 에러 메시지 제공
- [x] ✅ **WebSocket 관리 개선** (완료 - 2025-12-04)
  - ConnectionState 클래스로 연결 상태 추적 (connected_at, last_ping, last_pong, message_count, error_count)
  - 자동 heartbeat 메커니즘 (30초마다 서버 -> 클라이언트 ping)
  - connection_health_monitor 백그라운드 태스크 (60초 타임아웃, 최대 5회 에러)
  - 백그라운드 태스크 에러 복구 개선 (재시도 로직, 에러 카운트, 알림 전송)
  - 죽은 연결 자동 정리 및 제거
  - 연결 통계 로깅 (연결 시간, 메시지 수, 에러 수)
  - pong 응답 처리로 양방향 heartbeat 지원
  - 향상된 에러 처리 및 복구 (WebSocketDisconnect, 타임아웃)
- [x] ✅ **Redis Caching Layer** (완료 - 2025-12-04)
  - CacheManager 구현 (Redis와 In-Memory 캐시 자동 전환)
  - InMemoryCache 구현 (LRU eviction, TTL, hit counting)
  - Application startup에서 cache manager 초기화
  - Bot status 캐싱 (30초 TTL)
  - Balance 캐싱 (10초 TTL)
  - Positions 캐싱 (5초 TTL)
  - Risk settings 캐싱 (60초 TTL)
  - Cache invalidation (bot start/stop, API 키 저장, 리스크 설정 저장 시)
  - Graceful degradation (Redis 없어도 In-Memory로 작동)
  - Pattern-based cache deletion 지원
  - make_cache_key helper 함수
  - @cached 데코레이터 (향후 사용 가능)
- [x] ✅ **구조화된 Logging** (완료 - 2025-12-04)
  - StructuredLogger 클래스 구현 (JSON 형식 로깅)
  - JSONFormatter 구현 (표준 logging 모듈 통합)
  - ContextVar 기반 context 관리 (request_id, user_id)
  - RequestContextMiddleware 구현 (UUID 기반 request ID 생성)
  - JWT에서 user_id 자동 추출 및 context 저장
  - X-Request-ID 헤더 자동 추가
  - 주요 엔드포인트에 structured logging 통합:
    - Bot API (start, stop, status) - 봇 실행 추적
    - Account API (save_keys, my_keys) - 보안 감사 로그
    - Market API (market_order, limit_order) - 거래 추적
  - Helper 함수 (get_logger, set_request_id, set_user_id, clear_context)
  - setup_structured_logging (JSON/표준 형식 전환 지원)

---

## 🎓 참고 사항

### Database Migration 가이드
```bash
# 백엔드 디렉토리에서
cd backend

# 새 마이그레이션 생성
alembic revision --autogenerate -m "Add risk_settings and trading_signals tables"

# 마이그레이션 적용
alembic upgrade head

# 롤백 (필요 시)
alembic downgrade -1
```

### 테스트 가이드
```bash
# 프론트엔드
cd frontend
npm run dev

# 백엔드
cd backend
uvicorn src.main:app --reload

# API 테스트
curl -X POST http://localhost:8000/account/risk-settings \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"daily_loss_limit": 500, "max_leverage": 10, "max_positions": 5}'
```

---

> **마지막 업데이트**: 2025-12-04
> **다음 리뷰**: Phase 1 완료 후
