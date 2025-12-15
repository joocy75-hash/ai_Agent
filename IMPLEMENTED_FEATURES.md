# Auto-Dashboard 구현 기능 상세 문서

> 트레이딩 자동화 플랫폼의 전체 구현 사항을 상세히 설명합니다.
>
> **작성일**: 2024-12-15
> **버전**: 1.0
> **목적**: 누구든 이 문서를 읽고 시스템이 어떻게 구현되었는지 정확히 이해할 수 있도록

---

## 📋 목차

1. [시스템 개요](#시스템-개요)
2. [백엔드 아키텍처](#백엔드-아키텍처)
3. [프론트엔드 아키텍처](#프론트엔드-아키텍처)
4. [핵심 기능 구현](#핵심-기능-구현)
5. [데이터베이스 설계](#데이터베이스-설계)
6. [인프라 및 배포](#인프라-및-배포)
7. [보안 기능](#보안-기능)
8. [성능 최적화](#성능-최적화)

---

## 시스템 개요

### 🎯 프로젝트 목표
암호화폐 선물 거래를 자동화하는 엔터프라이즈급 플랫폼으로, 다음을 지원합니다:
- **다중 봇 시스템**: 사용자당 최대 10개의 독립적인 트레이딩 봇 운영
- **그리드 트레이딩**: 레인지 시장에서 수익을 내는 자동화 전략
- **백테스팅**: 과거 데이터로 전략 검증
- **AI 전략 생성**: DeepSeek AI를 활용한 자동 전략 코드 생성
- **실시간 모니터링**: WebSocket 기반 실시간 데이터 및 알림

### 🛠 기술 스택

**백엔드**
- FastAPI (Python 3.11+) - 비동기 웹 프레임워크
- PostgreSQL 15 - 메인 데이터베이스
- Redis 7 - 캐싱 및 세션 관리
- SQLAlchemy (Async) - ORM
- CCXT - 거래소 API 통합
- WebSocket - 실시간 통신

**프론트엔드**
- React 18 + Vite - UI 프레임워크
- Ant Design - UI 컴포넌트 라이브러리
- Recharts - 차트 시각화
- Axios - HTTP 클라이언트
- Tailwind CSS - 스타일링

**거래소 연동**
- Bitget (주력)
- Binance
- OKX

**외부 서비스**
- DeepSeek API - AI 전략 생성
- Google OAuth - 소셜 로그인
- Kakao OAuth - 소셜 로그인
- Telegram Bot - 알림

---

## 백엔드 아키텍처

### 📂 프로젝트 구조

```
backend/
├── src/
│   ├── main.py                 # FastAPI 앱 진입점
│   ├── config.py               # 환경 설정
│   │
│   ├── api/                    # API 엔드포인트 (50+ 파일)
│   │   ├── auth.py            # 인증 (로그인, 회원가입)
│   │   ├── bot.py             # 봇 제어
│   │   ├── bot_instances.py   # 다중 봇 관리
│   │   ├── grid_bot.py        # 그리드 봇
│   │   ├── strategy.py        # 전략 관리
│   │   ├── backtest.py        # 백테스팅
│   │   ├── order.py           # 주문 실행
│   │   ├── trades.py          # 거래 내역
│   │   ├── alerts.py          # 알림 설정
│   │   └── admin_*.py         # 관리자 기능
│   │
│   ├── database/
│   │   └── models.py          # SQLAlchemy 모델 정의
│   │
│   ├── services/              # 비즈니스 로직
│   │   ├── bot_runner.py      # 봇 실행 엔진
│   │   ├── grid_bot_runner.py # 그리드 봇 실행
│   │   ├── backtest_engine.py # 백테스팅 엔진
│   │   ├── trade_executor.py  # 거래 실행
│   │   ├── risk_engine.py     # 리스크 관리
│   │   ├── deepseek_service.py # AI 전략 생성
│   │   ├── exchanges/         # 거래소 API 래퍼
│   │   │   ├── base_exchange.py
│   │   │   ├── bitget_exchange.py
│   │   │   └── bitget_ws.py
│   │   └── ...
│   │
│   ├── agents/                # 다단계 AI 에이전트
│   │   ├── market_regime/     # 시장 상황 분석
│   │   ├── signal_validator/  # 신호 검증
│   │   └── risk_monitor/      # 리스크 모니터링
│   │
│   ├── strategies/            # 트레이딩 전략들
│   │   ├── proven_*.py        # 검증된 전략들
│   │   └── dynamic_strategy_executor.py
│   │
│   ├── websockets/
│   │   └── ws_server.py       # WebSocket 서버
│   │
│   ├── workers/
│   │   └── manager.py         # 봇 매니저 (부트스트랩)
│   │
│   ├── middleware/            # 미들웨어
│   │   ├── cors.py
│   │   ├── rate_limit.py
│   │   └── error_handler.py
│   │
│   └── utils/                 # 유틸리티
│       ├── jwt_auth.py        # JWT 토큰
│       ├── crypto_secrets.py  # API 키 암호화
│       ├── totp_service.py    # 2FA TOTP
│       └── login_security.py  # 브루트포스 방어
```

### 🔌 API 엔드포인트 (50+ 개)

#### 1. 인증 (`/api/v1/auth`)
| 메서드 | 경로 | 설명 | 주요 기능 |
|--------|------|------|-----------|
| POST | `/register` | 회원가입 | - 이메일/비밀번호 검증<br>- bcrypt 해싱<br>- 비밀번호 정책 (8자+, 대소문자+숫자+특수문자) |
| POST | `/login` | 로그인 | - JWT + Refresh 토큰 발급<br>- 브루트포스 방어 (5회 실패 시 15분 잠금)<br>- 2FA 지원 |
| POST | `/refresh` | 토큰 갱신 | - Refresh 토큰으로 새 Access 토큰 발급 |
| POST | `/change-password` | 비밀번호 변경 | - 기존 비밀번호 검증 필수 |

**구현 세부사항**:
```python
# 로그인 플로우 (backend/src/api/auth.py)
1. 이메일/비밀번호 검증
2. LoginSecurity.check_failed_attempts() - 브루트포스 체크
3. bcrypt.checkpw() - 비밀번호 검증
4. is_2fa_enabled == True면:
   - return {"requires_2fa": True, "user_id": user.id}
   - 클라이언트는 별도로 POST /verify-2fa 호출
5. JWT 토큰 생성:
   - access_token (1시간 유효)
   - refresh_token (7일 유효)
6. return {"access_token": ..., "refresh_token": ...}
```

#### 2. OAuth (`/api/v1/oauth`)
| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/google/callback` | Google OAuth 콜백 |
| GET | `/kakao/callback` | Kakao OAuth 콜백 |

**OAuth 플로우**:
```
1. 프론트엔드 → Google/Kakao 인증 페이지 리다이렉트
2. 사용자 로그인 완료 → /oauth/callback?code=XXX
3. 백엔드가 code로 프로필 정보 요청
4. 기존 사용자면 로그인, 신규면 회원가입
5. JWT 토큰 발급 후 프론트엔드로 리다이렉트
```

#### 3. 봇 관리 (`/api/v1/bot`, `/api/v1/bot-instances`)

**단일 봇 (레거시)**:
| 메서드 | 경로 | 설명 |
|--------|------|------|
| POST | `/bot/start` | 봇 시작 (user_id 기준) |
| POST | `/bot/stop` | 봇 중지 |
| GET | `/bot/status` | 봇 상태 조회 |

**다중 봇 시스템 (신규)**:
| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/bot-instances` | 사용자의 모든 봇 인스턴스 조회 |
| POST | `/bot-instances` | 새 봇 인스턴스 생성 |
| GET | `/bot-instances/{id}` | 특정 봇 상세 조회 |
| PUT | `/bot-instances/{id}` | 봇 설정 수정 |
| DELETE | `/bot-instances/{id}` | 봇 삭제 |
| POST | `/bot-instances/{id}/start` | 특정 봇 시작 |
| POST | `/bot-instances/{id}/stop` | 특정 봇 중지 |

**다중 봇 구현**:
```python
# BotInstance 테이블 구조
{
  "id": 1,
  "user_id": 123,
  "name": "BTC 급등 봇",
  "bot_type": "STRATEGY",  # or "GRID"
  "symbol": "BTCUSDT",
  "allocation_percent": 30,  # 전체 잔고의 30%만 사용
  "strategy_id": 5,
  "max_leverage": 10,
  "max_positions": 3,
  "stop_loss_percent": 5.0,
  "take_profit_percent": 10.0,
  "is_running": true,
  "total_trades": 45,
  "winning_trades": 32,
  "total_pnl": 234.56
}
```

**봇 실행 엔진** (`backend/src/services/bot_runner.py`):
```python
async def run_bot(bot_instance_id: int):
    while True:
        # 1. 캔들 데이터 가져오기
        candles = await fetch_candles(symbol, timeframe='5m')

        # 2. 전략 실행
        signal = strategy.calculate(candles)  # 'buy', 'sell', None

        # 3. AI 에이전트 검증
        validated = await SignalValidator.validate(signal)

        # 4. 리스크 체크
        risk_ok = await RiskMonitor.check(bot_instance)

        # 5. 주문 실행
        if validated and risk_ok and signal == 'buy':
            await execute_trade(bot_instance, 'buy')

        # 6. WebSocket으로 상태 브로드캐스트
        await ws_manager.broadcast(user_id, {
            "type": "bot_update",
            "bot_id": bot_instance_id,
            "status": "running"
        })

        # 7. Telegram 알림
        if telegram_enabled:
            await send_telegram_notification(...)

        await asyncio.sleep(300)  # 5분 대기
```

#### 4. 그리드 봇 (`/api/v1/grid-bot`)

| 메서드 | 경로 | 설명 |
|--------|------|------|
| POST | `/grid-bot` | 그리드 봇 생성 |
| GET | `/grid-bot/{bot_id}/config` | 그리드 설정 조회 |
| POST | `/grid-bot/{bot_id}/config` | 그리드 설정 저장 |
| GET | `/grid-bot/{bot_id}/orders` | 그리드 주문 목록 |
| GET | `/grid-bot/{bot_id}/stats` | 그리드 통계 |
| POST | `/grid-bot/preview` | 그리드 미리보기 (주문 배치 계산) |

**그리드 봇 원리**:
```
가격 범위: $30,000 ~ $35,000
그리드 개수: 10개

[Geometric 모드]
각 그리드 간격이 일정 비율 (예: 1%)

그리드 0: $30,000 (매수)
그리드 1: $30,300 (매수)
그리드 2: $30,603 (매수)
...
그리드 9: $34,700 (매수)

동작:
1. 각 그리드 가격에 매수 주문 배치
2. 그리드 3에서 매수 체결 → 즉시 그리드 4 가격에 매도 주문
3. 매도 체결 → 실현 손익 기록 + 다시 그리드 3에 매수 주문
4. 가격이 범위 내에서 오르락내리락할 때마다 수익 발생
```

**그리드 주문 생명주기**:
```python
# GridOrder 상태 변화
PENDING → BUY_PLACED → BUY_FILLED
        → SELL_PLACED → SELL_FILLED
        → COMPLETED (profit 기록)
        → BUY_PLACED (사이클 반복)
```

**그리드 봇 실행기** (`backend/src/services/grid_bot_runner.py`):
```python
async def run_grid_bot(bot_instance_id: int):
    config = await get_grid_config(bot_instance_id)

    # 그리드 가격 계산
    grid_prices = calculate_grid_prices(
        lower=config.lower_price,
        upper=config.upper_price,
        count=config.grid_count,
        mode=config.grid_mode  # 'arithmetic' or 'geometric'
    )

    # 초기 매수 주문 배치
    for price in grid_prices:
        order = await place_limit_order(
            symbol=config.symbol,
            side='buy',
            price=price,
            quantity=config.per_grid_amount
        )
        await save_grid_order(order)

    # 주문 모니터링
    while True:
        filled_orders = await check_filled_orders()

        for order in filled_orders:
            if order.side == 'buy':
                # 매수 체결 → 매도 주문 생성
                sell_price = get_next_grid_price(order.price)
                await place_sell_order(sell_price)

            elif order.side == 'sell':
                # 매도 체결 → 실현 손익 기록
                profit = (order.sell_price - order.buy_price) * order.quantity
                await update_realized_profit(profit)

                # 다시 매수 주문
                await place_buy_order(order.grid_price)

        await asyncio.sleep(10)  # 10초마다 체크
```

#### 5. 전략 관리 (`/api/v1/strategy`)

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/strategy` | 사용자 전략 목록 |
| POST | `/strategy` | 새 전략 생성 |
| GET | `/strategy/{id}` | 전략 상세 조회 |
| PUT | `/strategy/{id}` | 전략 수정 |
| DELETE | `/strategy/{id}` | 전략 삭제 |

**전략 타입**:
1. **내장 전략**: RSI, EMA Crossover, MACD
2. **커스텀 전략**: 사용자가 Python 코드 작성
3. **AI 생성 전략**: DeepSeek API로 자동 생성

**커스텀 전략 예시**:
```python
# 사용자가 작성하는 전략 코드
class MyStrategy:
    def __init__(self):
        self.rsi_period = 14
        self.ema_fast = 9
        self.ema_slow = 21

    def on_candle(self, candle, position):
        """
        candle: {'open': 30000, 'high': 30500, 'low': 29800, 'close': 30200}
        position: {'side': 'long', 'size': 0.1} or None

        return: 'buy', 'sell', or None
        """
        # RSI 계산
        rsi = calculate_rsi(self.rsi_period)

        # EMA 계산
        ema_fast = calculate_ema(self.ema_fast)
        ema_slow = calculate_ema(self.ema_slow)

        # 진입 조건
        if rsi < 30 and ema_fast > ema_slow and not position:
            return 'buy'

        # 청산 조건
        if position and (rsi > 70 or ema_fast < ema_slow):
            return 'sell'

        return None
```

#### 6. 백테스팅 (`/api/v1/backtest`, `/api/v1/user-backtest`)

| 메서드 | 경로 | 설명 |
|--------|------|------|
| POST | `/backtest` | 백테스트 실행 (관리자용, 캐시 시스템) |
| GET | `/backtest-history` | 백테스트 결과 히스토리 |
| POST | `/user-backtest` | 사용자 백테스트 (캐시된 결과 사용) |

**백테스팅 엔진** (`backend/src/services/backtest_engine.py`):
```python
async def run_backtest(strategy, candles, initial_balance=1000):
    balance = initial_balance
    position = None
    trades = []
    equity_curve = []

    for candle in candles:
        # 전략 신호 생성
        signal = strategy.on_candle(candle, position)

        if signal == 'buy' and not position:
            # 롱 포지션 진입
            entry_price = candle['close'] * (1 + SLIPPAGE)
            size = balance * 0.95 / entry_price  # 95% 사용
            fee = entry_price * size * FEE_RATE

            position = {
                'side': 'long',
                'entry_price': entry_price,
                'size': size,
                'entry_time': candle['timestamp']
            }
            balance -= fee

        elif signal == 'sell' and position:
            # 포지션 청산
            exit_price = candle['close'] * (1 - SLIPPAGE)
            pnl = (exit_price - position['entry_price']) * position['size']
            fee = exit_price * position['size'] * FEE_RATE

            balance += pnl - fee

            trades.append({
                'entry': position['entry_price'],
                'exit': exit_price,
                'pnl': pnl - fee,
                'pnl_percent': (pnl - fee) / (position['entry_price'] * position['size']) * 100
            })

            position = None

        # 에퀴티 곡선 기록
        current_equity = balance
        if position:
            unrealized_pnl = (candle['close'] - position['entry_price']) * position['size']
            current_equity += unrealized_pnl

        equity_curve.append({
            'timestamp': candle['timestamp'],
            'equity': current_equity
        })

    # 메트릭 계산
    metrics = calculate_metrics(trades, equity_curve)

    return {
        'final_balance': balance,
        'total_return': (balance - initial_balance) / initial_balance * 100,
        'trades': trades,
        'equity_curve': equity_curve,
        'metrics': {
            'total_trades': len(trades),
            'winning_trades': sum(1 for t in trades if t['pnl'] > 0),
            'win_rate': winning_trades / total_trades * 100,
            'max_drawdown': calculate_max_drawdown(equity_curve),
            'sharpe_ratio': calculate_sharpe(equity_curve)
        }
    }
```

**백테스트 결과 예시**:
```json
{
  "final_balance": 1234.56,
  "total_return": 23.45,
  "trades": [
    {
      "entry": 30000,
      "exit": 31000,
      "pnl": 95.0,
      "pnl_percent": 9.5,
      "timestamp": "2024-01-15T10:30:00Z"
    }
  ],
  "metrics": {
    "total_trades": 15,
    "winning_trades": 10,
    "win_rate": 66.7,
    "max_drawdown": -8.5,
    "sharpe_ratio": 1.2,
    "avg_win": 120.5,
    "avg_loss": -45.2
  }
}
```

#### 7. 거래 실행 (`/api/v1/order`, `/api/v1/trades`, `/api/v1/positions`)

| 메서드 | 경로 | 설명 |
|--------|------|------|
| POST | `/order` | 주문 실행 (시장가/지정가) |
| GET | `/trades` | 거래 내역 (페이지네이션) |
| GET | `/positions` | 열린 포지션 목록 |
| GET | `/account` | 계좌 정보 (잔고, 에퀴티) |

**거래 실행기** (`backend/src/services/trade_executor.py`):
```python
async def execute_trade(
    user_id: int,
    bot_instance_id: int,
    symbol: str,
    side: str,  # 'buy' or 'sell'
    quantity: float,
    leverage: int = 1,
    order_type: str = 'market'
):
    # 1. API 키 복호화
    api_keys = await get_user_api_keys(user_id)
    exchange = BitgetExchange(api_keys)

    # 2. 주문 실행
    order = await exchange.create_order(
        symbol=symbol,
        side=side,
        type=order_type,
        amount=quantity,
        leverage=leverage
    )

    # 3. DB에 거래 기록
    trade = Trade(
        user_id=user_id,
        bot_instance_id=bot_instance_id,
        symbol=symbol,
        side=side,
        qty=quantity,
        entry_price=order['price'],
        leverage=leverage,
        trade_source='AI_BOT',  # or 'GRID_BOT', 'MANUAL'
        created_at=datetime.utcnow()
    )
    await db.add(trade)

    # 4. 포지션 업데이트
    if side == 'buy':
        await create_position(trade)
    else:
        await close_position(trade)

    # 5. WebSocket 알림
    await ws_manager.broadcast(user_id, {
        'type': 'trade_alert',
        'trade': trade.to_dict()
    })

    # 6. Telegram 알림
    if bot_instance.telegram_notify:
        await send_telegram(
            f"✅ {side.upper()} {symbol}\n"
            f"수량: {quantity}\n"
            f"가격: {order['price']}"
        )

    return order
```

#### 8. AI 전략 생성 (`/api/v1/ai-strategy`)

| 메서드 | 경로 | 설명 |
|--------|------|------|
| POST | `/ai-strategy/generate` | AI로 전략 코드 생성 |

**AI 전략 생성 플로우**:
```python
# backend/src/services/deepseek_service.py
async def generate_strategy(user_prompt: str):
    # 1. Rate limit 체크 (2/min, 20/hour, 100/day)
    await check_rate_limit(user_id)

    # 2. DeepSeek API 호출
    response = await deepseek_client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": STRATEGY_SYSTEM_PROMPT},
            {"role": "user", "content": f"""
사용자 요청: {user_prompt}

다음 형식으로 Python 전략 코드를 생성하세요:
- on_candle(candle, position) 메서드 구현
- RSI, EMA, MACD 등 지표 활용
- 명확한 진입/청산 조건
            """}
        ]
    )

    # 3. 생성된 코드 검증
    code = response.choices[0].message.content
    validated = validate_strategy_code(code)

    # 4. 전략 저장
    strategy = Strategy(
        user_id=user_id,
        name=f"AI Strategy - {datetime.now().strftime('%Y%m%d_%H%M')}",
        code=code,
        description=user_prompt,
        is_active=True
    )
    await db.add(strategy)

    return strategy
```

**생성 예시**:
```
사용자 입력: "RSI가 30 이하일 때 매수하고 70 이상일 때 매도하는 전략"

AI 생성 결과:
```python
class RSIStrategy:
    def __init__(self):
        self.rsi_period = 14
        self.oversold = 30
        self.overbought = 70

    def on_candle(self, candle, position):
        rsi = calculate_rsi(self.rsi_period)

        if rsi < self.oversold and not position:
            return 'buy'

        if rsi > self.overbought and position:
            return 'sell'

        return None
```
```

#### 9. 관리자 기능 (`/api/v1/admin-*`)

**그리드 템플릿 관리** (`/api/v1/admin/grid-templates`):
| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/admin/grid-templates` | 템플릿 목록 (비활성 포함) |
| POST | `/admin/grid-templates` | 템플릿 생성 |
| PUT | `/admin/grid-templates/{id}` | 템플릿 수정 |
| DELETE | `/admin/grid-templates/{id}` | 템플릿 삭제 |
| POST | `/admin/grid-templates/{id}/toggle` | 활성/비활성 전환 |
| POST | `/admin/grid-templates/{id}/backtest` | 템플릿 백테스트 실행 |

**템플릿 구조**:
```python
{
  "id": 1,
  "name": "BTC 보수형 그리드",
  "symbol": "BTCUSDT",
  "direction": "long",
  "leverage": 5,
  "lower_price": 28000,
  "upper_price": 35000,
  "grid_count": 20,
  "grid_mode": "geometric",
  "min_investment": 100,
  "recommended_investment": 500,

  # 백테스트 결과
  "backtest_roi_30d": 15.6,
  "backtest_max_drawdown": -4.2,
  "backtest_total_trades": 156,
  "backtest_win_rate": 78.5,
  "backtest_roi_history": [
    {"date": "2024-01-01", "roi": 2.3},
    {"date": "2024-01-02", "roi": 3.1}
  ],

  # 사용 통계
  "active_users": 12,
  "total_users": 45,
  "total_funds_in_use": 25600.00,

  "is_active": true,
  "is_featured": true,
  "created_by": 1,  # admin user_id
  "created_at": "2024-01-01T00:00:00Z"
}
```

**사용자 관리** (`/api/v1/admin/users`):
- 전체 사용자 목록
- 계정 활성화/비활성화
- 사용자별 거래 통계

**시스템 모니터링** (`/api/v1/admin/analytics`):
- 플랫폼 전체 P&L
- 활성 봇 개수
- 인기 전략/템플릿
- 에러 로그

#### 10. 알림 (`/api/v1/alerts`, `/api/v1/telegram`)

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/alerts` | 알림 목록 |
| POST | `/alerts` | 알림 생성 (가격, 이벤트) |
| DELETE | `/alerts/{id}` | 알림 삭제 |
| POST | `/telegram/setup` | Telegram 연동 설정 |

**알림 타입**:
1. **가격 알림**: BTC가 $30,000 도달 시
2. **이벤트 알림**: 포지션 청산 시
3. **리스크 알림**: 일일 손실 5% 초과 시

### 🌐 WebSocket 구현

**서버** (`backend/src/websockets/ws_server.py`):
```python
class WebSocketManager:
    def __init__(self):
        self.active_connections: Dict[int, WebSocket] = {}  # user_id → WebSocket

    async def connect(self, user_id: int, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[user_id] = websocket

        # 핑/퐁 keepalive 시작
        asyncio.create_task(self.keepalive(user_id, websocket))

    async def disconnect(self, user_id: int):
        if user_id in self.active_connections:
            await self.active_connections[user_id].close()
            del self.active_connections[user_id]

    async def broadcast(self, user_id: int, message: dict):
        """특정 사용자에게 메시지 전송"""
        if user_id in self.active_connections:
            websocket = self.active_connections[user_id]
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Failed to send message: {e}")
                await self.disconnect(user_id)

    async def keepalive(self, user_id: int, websocket: WebSocket):
        """30초마다 핑 전송, 응답 없으면 연결 종료"""
        while user_id in self.active_connections:
            try:
                await websocket.send_json({"type": "ping"})
                await asyncio.sleep(30)
            except:
                await self.disconnect(user_id)
                break

# 엔드포인트
@app.websocket("/ws/user/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int, token: str):
    # JWT 검증
    user = await verify_jwt_token(token)
    if not user or user.id != user_id:
        await websocket.close(code=4001)
        return

    await ws_manager.connect(user_id, websocket)

    try:
        while True:
            data = await websocket.receive_json()

            # 클라이언트 → 서버 메시지 처리
            if data['type'] == 'pong':
                # keepalive 응답
                pass
            elif data['type'] == 'subscribe':
                # 특정 채널 구독
                await subscribe_channel(user_id, data['channel'])

    except WebSocketDisconnect:
        await ws_manager.disconnect(user_id)
```

**메시지 타입**:
```python
# 1. 가격 업데이트
{
  "type": "price_update",
  "symbol": "BTCUSDT",
  "price": 30250.50,
  "timestamp": "2024-01-15T10:30:00Z"
}

# 2. 포지션 업데이트
{
  "type": "position_update",
  "position": {
    "id": 123,
    "symbol": "BTCUSDT",
    "side": "long",
    "size": 0.1,
    "entry_price": 30000,
    "current_price": 30250,
    "unrealized_pnl": 25.0
  }
}

# 3. 주문 업데이트
{
  "type": "order_update",
  "order": {
    "id": "abc123",
    "status": "filled",
    "symbol": "BTCUSDT",
    "side": "buy",
    "price": 30250
  }
}

# 4. 거래 알림
{
  "type": "trade_alert",
  "trade": {
    "symbol": "BTCUSDT",
    "side": "buy",
    "qty": 0.1,
    "price": 30250,
    "bot_name": "BTC 급등 봇"
  }
}

# 5. 시스템 알림
{
  "type": "system_alert",
  "level": "warning",  # info, warning, error
  "message": "일일 손실이 5%를 초과했습니다."
}
```

### 🤖 AI 에이전트 시스템

**3단계 오케스트레이션**:

1. **Market Regime Agent** (`backend/src/agents/market_regime/`)
   - 시장 상황 분석 (추세, 레인지, 변동성)
   - 매크로 지표 고려
   - 출력: "bullish_trend", "bearish_trend", "ranging", "high_volatility"

2. **Signal Validator Agent** (`backend/src/agents/signal_validator/`)
   - 전략에서 생성된 신호 검증
   - 허위 신호 필터링
   - 여러 지표 종합 판단
   - 출력: signal_quality (0.0 ~ 1.0)

3. **Risk Monitor Agent** (`backend/src/agents/risk_monitor/`)
   - 실시간 리스크 모니터링
   - 일일 손실 한도 체크
   - 포지션 크기 검증
   - 청산 리스크 계산
   - 출력: risk_level ("safe", "moderate", "high", "critical")

**에이전트 통합**:
```python
# bot_runner.py 내부
async def execute_with_agents(bot_instance, signal):
    # 1. 시장 상황 분석
    market_regime = await MarketRegimeAgent.analyze(symbol)

    # 2. 신호 검증
    signal_quality = await SignalValidatorAgent.validate(
        signal=signal,
        market_regime=market_regime
    )

    if signal_quality < 0.6:
        logger.info("Signal rejected: low quality")
        return

    # 3. 리스크 체크
    risk_level = await RiskMonitorAgent.check(bot_instance)

    if risk_level in ['high', 'critical']:
        logger.warning("Trade blocked: high risk")
        return

    # 4. 거래 실행
    await execute_trade(bot_instance, signal)
```

---

## 프론트엔드 아키텍처

### 📂 프로젝트 구조

```
frontend/
├── src/
│   ├── main.jsx              # 엔트리 포인트
│   ├── App.jsx               # 루트 컴포넌트
│   │
│   ├── pages/                # 16개 페이지
│   │   ├── Login.jsx
│   │   ├── Dashboard.jsx    # 메인 대시보드
│   │   ├── Strategy.jsx     # 전략 관리
│   │   ├── Trading.jsx      # 실시간 거래
│   │   ├── History.jsx      # 거래 내역
│   │   ├── Backtesting.jsx  # 백테스팅
│   │   ├── Bots.jsx         # 다중 봇 관리 (신규)
│   │   ├── Alerts.jsx       # 알림 설정
│   │   ├── Settings.jsx     # 사용자 설정
│   │   └── admin/           # 관리자 페이지들
│   │
│   ├── components/          # 50+ 컴포넌트
│   │   ├── bot/
│   │   │   ├── BotCard.jsx
│   │   │   ├── AddBotCard.jsx
│   │   │   ├── EditBotModal.jsx
│   │   │   └── AllocationBar.jsx
│   │   ├── grid/
│   │   │   ├── GridBotCard.jsx
│   │   │   ├── GridVisualizer.jsx
│   │   │   └── TemplateList.jsx
│   │   ├── strategy/
│   │   │   ├── StrategyEditor.jsx
│   │   │   └── BacktestRunner.jsx
│   │   └── ...
│   │
│   ├── context/             # 상태 관리
│   │   ├── AuthContext.jsx
│   │   ├── WebSocketContext.jsx
│   │   ├── ThemeContext.jsx
│   │   └── StrategyContext.jsx
│   │
│   ├── api/                 # 20+ API 모듈
│   │   ├── client.js        # Axios 인스턴스
│   │   ├── auth.js
│   │   ├── bot.js
│   │   ├── botInstances.js
│   │   ├── strategy.js
│   │   └── ...
│   │
│   ├── hooks/               # 커스텀 훅
│   │   ├── useAuth.js
│   │   ├── useWebSocket.js
│   │   └── useRealTimePrice.js
│   │
│   └── utils/
│       ├── formatters.js    # 숫자/날짜 포맷팅
│       └── constants.js
```

### 🔐 인증 플로우 (프론트엔드)

**AuthContext** (`frontend/src/context/AuthContext.jsx`):
```jsx
export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  // 토큰 자동 갱신 (4분마다)
  useEffect(() => {
    const interval = setInterval(async () => {
      const token = localStorage.getItem('access_token');
      const decoded = jwtDecode(token);
      const expiresIn = decoded.exp - Date.now() / 1000;

      // 5분 이하 남으면 갱신
      if (expiresIn < 300) {
        await refreshToken();
      }
    }, 240000);  // 4분

    return () => clearInterval(interval);
  }, []);

  const login = async (email, password, totpCode = null) => {
    const response = await authAPI.login(email, password, totpCode);

    if (response.requires_2fa) {
      // 2FA 입력 화면으로 이동
      return { requires_2fa: true, user_id: response.user_id };
    }

    // 토큰 저장
    localStorage.setItem('access_token', response.access_token);
    localStorage.setItem('refresh_token', response.refresh_token);

    // 사용자 정보 디코딩
    const decoded = jwtDecode(response.access_token);
    setUser({
      id: decoded.user_id,
      email: decoded.email,
      role: decoded.role
    });

    return { success: true };
  };

  const refreshToken = async () => {
    const refreshToken = localStorage.getItem('refresh_token');
    const response = await authAPI.refresh(refreshToken);

    localStorage.setItem('access_token', response.access_token);

    // Refresh 토큰도 1일 미만 남으면 재발급
    if (response.refresh_token) {
      localStorage.setItem('refresh_token', response.refresh_token);
    }
  };

  const logout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    setUser(null);
    navigate('/login');
  };

  return (
    <AuthContext.Provider value={{ user, login, logout, refreshToken }}>
      {children}
    </AuthContext.Provider>
  );
};
```

**로그인 페이지** (`frontend/src/pages/Login.jsx`):
```jsx
const Login = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [totpCode, setTotpCode] = useState('');
  const [show2FA, setShow2FA] = useState(false);
  const [userId, setUserId] = useState(null);
  const { login } = useAuth();

  const handleSubmit = async (e) => {
    e.preventDefault();

    const result = await login(email, password, totpCode);

    if (result.requires_2fa) {
      setShow2FA(true);
      setUserId(result.user_id);
      message.info('2FA 코드를 입력하세요');
    } else if (result.success) {
      message.success('로그인 성공!');
      navigate('/dashboard');
    }
  };

  return (
    <div className="login-container">
      <Form onSubmit={handleSubmit}>
        <Input
          type="email"
          value={email}
          onChange={e => setEmail(e.target.value)}
          placeholder="이메일"
        />
        <Input
          type="password"
          value={password}
          onChange={e => setPassword(e.target.value)}
          placeholder="비밀번호"
        />

        {show2FA && (
          <Input
            value={totpCode}
            onChange={e => setTotpCode(e.target.value)}
            placeholder="2FA 코드 (6자리)"
          />
        )}

        <Button type="primary" htmlType="submit">
          로그인
        </Button>

        <Divider>OR</Divider>

        <Button
          icon={<GoogleOutlined />}
          onClick={() => window.location.href = '/api/v1/oauth/google'}
        >
          Google로 로그인
        </Button>

        <Button
          onClick={() => window.location.href = '/api/v1/oauth/kakao'}
        >
          Kakao로 로그인
        </Button>
      </Form>
    </div>
  );
};
```

### 🌐 WebSocket 연결 (프론트엔드)

**WebSocketContext** (`frontend/src/context/WebSocketContext.jsx`):
```jsx
export const WebSocketProvider = ({ children }) => {
  const [ws, setWs] = useState(null);
  const [connected, setConnected] = useState(false);
  const [reconnectAttempts, setReconnectAttempts] = useState(0);
  const { user } = useAuth();

  const connect = useCallback(() => {
    if (!user) return;

    const token = localStorage.getItem('access_token');
    const wsUrl = `ws://localhost:8000/ws/user/${user.id}?token=${token}`;

    const socket = new WebSocket(wsUrl);

    socket.onopen = () => {
      console.log('WebSocket connected');
      setConnected(true);
      setReconnectAttempts(0);

      // 핑/퐁 핸들러
      const pingInterval = setInterval(() => {
        if (socket.readyState === WebSocket.OPEN) {
          socket.send(JSON.stringify({ type: 'ping' }));
        }
      }, 30000);

      socket.pingInterval = pingInterval;
    };

    socket.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data.type === 'ping') {
        socket.send(JSON.stringify({ type: 'pong' }));
        return;
      }

      // 이벤트 리스너 호출
      eventListeners[data.type]?.forEach(callback => callback(data));
    };

    socket.onclose = () => {
      console.log('WebSocket disconnected');
      setConnected(false);
      clearInterval(socket.pingInterval);

      // 지수 백오프 재연결
      const delay = Math.min(30000, 1000 * Math.pow(2, reconnectAttempts));
      setTimeout(() => {
        if (reconnectAttempts < 10) {
          setReconnectAttempts(prev => prev + 1);
          connect();
        }
      }, delay);
    };

    socket.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    setWs(socket);
  }, [user, reconnectAttempts]);

  const eventListeners = useRef({});

  const on = (eventType, callback) => {
    if (!eventListeners.current[eventType]) {
      eventListeners.current[eventType] = [];
    }
    eventListeners.current[eventType].push(callback);
  };

  const off = (eventType, callback) => {
    if (eventListeners.current[eventType]) {
      eventListeners.current[eventType] =
        eventListeners.current[eventType].filter(cb => cb !== callback);
    }
  };

  useEffect(() => {
    if (user) {
      connect();
    }

    return () => {
      if (ws) {
        ws.close();
      }
    };
  }, [user]);

  return (
    <WebSocketContext.Provider value={{ ws, connected, on, off }}>
      {children}
    </WebSocketContext.Provider>
  );
};
```

**WebSocket 사용 예시**:
```jsx
const Dashboard = () => {
  const { on, off } = useWebSocket();
  const [positions, setPositions] = useState([]);

  useEffect(() => {
    // 포지션 업데이트 리스너
    const handlePositionUpdate = (data) => {
      setPositions(prev => {
        const index = prev.findIndex(p => p.id === data.position.id);
        if (index >= 0) {
          const updated = [...prev];
          updated[index] = data.position;
          return updated;
        }
        return [...prev, data.position];
      });
    };

    on('position_update', handlePositionUpdate);

    return () => off('position_update', handlePositionUpdate);
  }, []);

  return (
    <div>
      <h2>열린 포지션</h2>
      {positions.map(pos => (
        <PositionCard key={pos.id} position={pos} />
      ))}
    </div>
  );
};
```

### 📊 주요 페이지 구현

#### 1. 대시보드 (`frontend/src/pages/Dashboard.jsx`)
```jsx
const Dashboard = () => {
  const [stats, setStats] = useState({
    totalEquity: 0,
    dailyPnL: 0,
    activeBots: 0,
    totalTrades: 0
  });
  const [recentTrades, setRecentTrades] = useState([]);
  const [equityCurve, setEquityCurve] = useState([]);

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    const [account, trades, equity] = await Promise.all([
      accountAPI.getAccountInfo(),
      tradesAPI.getRecentTrades(5),
      accountAPI.getEquityCurve(30)  // 30일
    ]);

    setStats({
      totalEquity: account.equity,
      dailyPnL: account.daily_pnl,
      activeBots: account.active_bots,
      totalTrades: account.total_trades
    });
    setRecentTrades(trades);
    setEquityCurve(equity);
  };

  return (
    <div className="dashboard">
      <Row gutter={16}>
        <Col span={6}>
          <StatCard
            title="총 에퀴티"
            value={`$${stats.totalEquity.toFixed(2)}`}
            trend={stats.dailyPnL > 0 ? 'up' : 'down'}
          />
        </Col>
        <Col span={6}>
          <StatCard
            title="일일 P&L"
            value={`$${stats.dailyPnL.toFixed(2)}`}
            color={stats.dailyPnL > 0 ? 'green' : 'red'}
          />
        </Col>
        <Col span={6}>
          <StatCard title="활성 봇" value={stats.activeBots} />
        </Col>
        <Col span={6}>
          <StatCard title="총 거래" value={stats.totalTrades} />
        </Col>
      </Row>

      <Row gutter={16} style={{ marginTop: 24 }}>
        <Col span={16}>
          <Card title="에퀴티 곡선 (30일)">
            <PerformanceChart data={equityCurve} />
          </Card>
        </Col>
        <Col span={8}>
          <Card title="최근 거래">
            <RecentTrades trades={recentTrades} />
          </Card>
        </Col>
      </Row>

      <Row style={{ marginTop: 24 }}>
        <Col span={24}>
          <RiskMetrics />
        </Col>
      </Row>
    </div>
  );
};
```

#### 2. 다중 봇 관리 (`frontend/src/pages/Bots.jsx`)
```jsx
const Bots = () => {
  const [bots, setBots] = useState([]);
  const [showAddModal, setShowAddModal] = useState(false);
  const [totalAllocation, setTotalAllocation] = useState(0);

  useEffect(() => {
    fetchBots();
  }, []);

  const fetchBots = async () => {
    const data = await botInstancesAPI.getBotInstances();
    setBots(data);

    const total = data.reduce((sum, bot) => sum + bot.allocation_percent, 0);
    setTotalAllocation(total);
  };

  const handleStartBot = async (botId) => {
    await botInstancesAPI.startBot(botId);
    message.success('봇이 시작되었습니다!');
    fetchBots();
  };

  const handleStopBot = async (botId) => {
    await botInstancesAPI.stopBot(botId);
    message.success('봇이 중지되었습니다!');
    fetchBots();
  };

  return (
    <div className="bots-page">
      <PageHeader
        title="나의 봇"
        extra={
          <Button
            type="primary"
            onClick={() => setShowAddModal(true)}
            disabled={bots.length >= 10}
          >
            + 새 봇 추가
          </Button>
        }
      />

      <AllocationBar
        used={totalAllocation}
        max={100}
        label={`자본 할당: ${totalAllocation}% / 100%`}
      />

      <Row gutter={16} style={{ marginTop: 24 }}>
        {bots.map(bot => (
          <Col key={bot.id} span={8}>
            <BotCard
              bot={bot}
              onStart={() => handleStartBot(bot.id)}
              onStop={() => handleStopBot(bot.id)}
              onEdit={() => showEditModal(bot)}
            />
          </Col>
        ))}

        {bots.length < 10 && (
          <Col span={8}>
            <AddBotCard onClick={() => setShowAddModal(true)} />
          </Col>
        )}
      </Row>

      <CreateBotModal
        visible={showAddModal}
        onClose={() => setShowAddModal(false)}
        onSuccess={fetchBots}
      />
    </div>
  );
};
```

**BotCard 컴포넌트**:
```jsx
const BotCard = ({ bot, onStart, onStop, onEdit }) => {
  const winRate = (bot.winning_trades / bot.total_trades * 100).toFixed(1);

  return (
    <Card
      title={bot.name}
      extra={
        <Tag color={bot.is_running ? 'green' : 'default'}>
          {bot.is_running ? '실행 중' : '중지됨'}
        </Tag>
      }
    >
      <Descriptions column={1} size="small">
        <Descriptions.Item label="심볼">{bot.symbol}</Descriptions.Item>
        <Descriptions.Item label="전략">
          {bot.bot_type === 'STRATEGY' ? bot.strategy_name : 'Grid Bot'}
        </Descriptions.Item>
        <Descriptions.Item label="할당">
          {bot.allocation_percent}%
        </Descriptions.Item>
        <Descriptions.Item label="레버리지">
          {bot.max_leverage}x
        </Descriptions.Item>
      </Descriptions>

      <Divider />

      <Statistic
        title="총 P&L"
        value={bot.total_pnl}
        precision={2}
        prefix="$"
        valueStyle={{ color: bot.total_pnl > 0 ? '#3f8600' : '#cf1322' }}
      />

      <Row gutter={8} style={{ marginTop: 8 }}>
        <Col span={12}>
          <Statistic title="거래" value={bot.total_trades} />
        </Col>
        <Col span={12}>
          <Statistic title="승률" value={winRate} suffix="%" />
        </Col>
      </Row>

      <Divider />

      <Space>
        {bot.is_running ? (
          <Button danger onClick={onStop}>중지</Button>
        ) : (
          <Button type="primary" onClick={onStart}>시작</Button>
        )}
        <Button onClick={onEdit}>설정</Button>
      </Space>
    </Card>
  );
};
```

#### 3. 백테스팅 페이지 (`frontend/src/pages/Backtesting.jsx`)
```jsx
const Backtesting = () => {
  const [strategies, setStrategies] = useState([]);
  const [selectedStrategy, setSelectedStrategy] = useState(null);
  const [backtestConfig, setBacktestConfig] = useState({
    initial_balance: 1000,
    start_date: '2024-01-01',
    end_date: '2024-12-31',
    fee_rate: 0.1,
    slippage: 0.05
  });
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);

  const runBacktest = async () => {
    setLoading(true);

    try {
      const result = await backtestAPI.runBacktest({
        strategy_id: selectedStrategy,
        ...backtestConfig
      });

      setResults(result);
      message.success('백테스트 완료!');
    } catch (error) {
      message.error('백테스트 실패: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="backtesting-page">
      <Row gutter={24}>
        <Col span={8}>
          <Card title="백테스트 설정">
            <Form layout="vertical">
              <Form.Item label="전략 선택">
                <Select
                  value={selectedStrategy}
                  onChange={setSelectedStrategy}
                >
                  {strategies.map(s => (
                    <Select.Option key={s.id} value={s.id}>
                      {s.name}
                    </Select.Option>
                  ))}
                </Select>
              </Form.Item>

              <Form.Item label="초기 잔고">
                <InputNumber
                  value={backtestConfig.initial_balance}
                  onChange={val => setBacktestConfig(prev => ({
                    ...prev,
                    initial_balance: val
                  }))}
                  prefix="$"
                />
              </Form.Item>

              <Form.Item label="기간">
                <DatePicker.RangePicker
                  value={[
                    moment(backtestConfig.start_date),
                    moment(backtestConfig.end_date)
                  ]}
                  onChange={dates => setBacktestConfig(prev => ({
                    ...prev,
                    start_date: dates[0].format('YYYY-MM-DD'),
                    end_date: dates[1].format('YYYY-MM-DD')
                  }))}
                />
              </Form.Item>

              <Button
                type="primary"
                block
                onClick={runBacktest}
                loading={loading}
              >
                백테스트 실행
              </Button>
            </Form>
          </Card>
        </Col>

        <Col span={16}>
          {results ? (
            <BacktestResults results={results} />
          ) : (
            <Card>
              <Empty description="백테스트를 실행하세요" />
            </Card>
          )}
        </Col>
      </Row>
    </div>
  );
};
```

**백테스트 결과 컴포넌트**:
```jsx
const BacktestResults = ({ results }) => {
  return (
    <div>
      <Card title="백테스트 결과">
        <Row gutter={16}>
          <Col span={8}>
            <Statistic
              title="최종 잔고"
              value={results.final_balance}
              precision={2}
              prefix="$"
            />
          </Col>
          <Col span={8}>
            <Statistic
              title="총 수익률"
              value={results.total_return}
              precision={2}
              suffix="%"
              valueStyle={{
                color: results.total_return > 0 ? '#3f8600' : '#cf1322'
              }}
            />
          </Col>
          <Col span={8}>
            <Statistic
              title="샤프 비율"
              value={results.metrics.sharpe_ratio}
              precision={2}
            />
          </Col>
        </Row>

        <Divider />

        <Row gutter={16}>
          <Col span={6}>
            <Statistic
              title="총 거래"
              value={results.metrics.total_trades}
            />
          </Col>
          <Col span={6}>
            <Statistic
              title="승률"
              value={results.metrics.win_rate}
              precision={1}
              suffix="%"
            />
          </Col>
          <Col span={6}>
            <Statistic
              title="최대 손실"
              value={results.metrics.max_drawdown}
              precision={2}
              suffix="%"
              valueStyle={{ color: '#cf1322' }}
            />
          </Col>
          <Col span={6}>
            <Statistic
              title="평균 수익"
              value={results.metrics.avg_win}
              precision={2}
              prefix="$"
            />
          </Col>
        </Row>
      </Card>

      <Card title="에퀴티 곡선" style={{ marginTop: 16 }}>
        <EquityCurveChart data={results.equity_curve} />
      </Card>

      <Card title="거래 내역" style={{ marginTop: 16 }}>
        <Table
          dataSource={results.trades}
          columns={[
            { title: '시간', dataIndex: 'timestamp', render: formatDate },
            { title: '진입', dataIndex: 'entry', render: price => `$${price}` },
            { title: '청산', dataIndex: 'exit', render: price => `$${price}` },
            {
              title: 'P&L',
              dataIndex: 'pnl',
              render: (pnl) => (
                <span style={{ color: pnl > 0 ? 'green' : 'red' }}>
                  ${pnl.toFixed(2)}
                </span>
              )
            },
            {
              title: 'P&L %',
              dataIndex: 'pnl_percent',
              render: (pct) => `${pct.toFixed(2)}%`
            }
          ]}
          pagination={{ pageSize: 10 }}
        />
      </Card>
    </div>
  );
};
```

### 🎨 컴포넌트 디자인 패턴

**1. API 통합 패턴**:
```jsx
// hooks/useAsyncData.js
const useAsyncData = (fetchFn, deps = []) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;

    const fetch = async () => {
      setLoading(true);
      try {
        const result = await fetchFn();
        if (!cancelled) {
          setData(result);
          setError(null);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    fetch();

    return () => {
      cancelled = true;
    };
  }, deps);

  return { data, loading, error, refetch: fetchFn };
};

// 사용 예시
const MyComponent = () => {
  const { data, loading, error, refetch } = useAsyncData(
    () => botInstancesAPI.getBotInstances(),
    []
  );

  if (loading) return <Spin />;
  if (error) return <Alert type="error" message={error.message} />;

  return <BotList bots={data} onRefresh={refetch} />;
};
```

**2. 실시간 데이터 패턴**:
```jsx
// hooks/useRealTimePrice.js
const useRealTimePrice = (symbol) => {
  const [price, setPrice] = useState(null);
  const { on, off } = useWebSocket();

  useEffect(() => {
    const handlePriceUpdate = (data) => {
      if (data.symbol === symbol) {
        setPrice(data.price);
      }
    };

    on('price_update', handlePriceUpdate);

    // 심볼 구독
    ws.send(JSON.stringify({
      type: 'subscribe',
      channel: `price:${symbol}`
    }));

    return () => {
      off('price_update', handlePriceUpdate);
      ws.send(JSON.stringify({
        type: 'unsubscribe',
        channel: `price:${symbol}`
      }));
    };
  }, [symbol]);

  return price;
};

// 사용
const PriceDisplay = ({ symbol }) => {
  const price = useRealTimePrice(symbol);

  return <div>${price?.toFixed(2)}</div>;
};
```

---

## 핵심 기능 구현

### 1. 다중 봇 시스템 (Multi-Bot)

**개념**:
- 사용자당 최대 10개의 독립적인 봇 인스턴스
- 각 봇은 전체 잔고의 일부만 사용 (allocation_percent)
- 봇별로 다른 심볼, 전략, 레버리지 설정 가능

**할당 관리** (`backend/src/services/allocation_manager.py`):
```python
class AllocationManager:
    @staticmethod
    async def get_available_balance(user_id: int) -> float:
        """사용자의 사용 가능한 잔고 계산"""
        # 1. 전체 잔고 조회
        account = await get_account_info(user_id)
        total_balance = account.balance

        # 2. 모든 봇의 할당 합계
        bots = await db.query(BotInstance).filter(
            BotInstance.user_id == user_id,
            BotInstance.is_active == True
        ).all()

        allocated = sum(
            total_balance * (bot.allocation_percent / 100)
            for bot in bots
        )

        return total_balance - allocated

    @staticmethod
    async def validate_allocation(user_id: int, allocation_percent: float) -> bool:
        """새 봇의 할당이 가능한지 검증"""
        available = await AllocationManager.get_available_balance(user_id)
        account = await get_account_info(user_id)

        requested = account.balance * (allocation_percent / 100)

        return requested <= available

    @staticmethod
    async def get_bot_trading_limit(bot_instance_id: int) -> float:
        """봇의 거래 한도 계산"""
        bot = await db.get(BotInstance, bot_instance_id)
        account = await get_account_info(bot.user_id)

        allocated_balance = account.balance * (bot.allocation_percent / 100)

        # 레버리지 적용
        max_position_value = allocated_balance * bot.max_leverage

        # 포지션 개수로 나눔
        per_position_limit = max_position_value / bot.max_positions

        return per_position_limit
```

**봇 생성 검증**:
```python
@router.post("/bot-instances")
async def create_bot_instance(
    bot_data: BotInstanceCreate,
    user_id: int = Depends(get_current_user)
):
    # 1. 최대 개수 체크
    bot_count = await db.query(BotInstance).filter(
        BotInstance.user_id == user_id,
        BotInstance.is_active == True
    ).count()

    if bot_count >= 10:
        raise HTTPException(400, "최대 10개의 봇만 생성 가능합니다")

    # 2. 할당 검증
    valid = await AllocationManager.validate_allocation(
        user_id,
        bot_data.allocation_percent
    )

    if not valid:
        raise HTTPException(400, "잔고가 부족합니다")

    # 3. 봇 생성
    bot = BotInstance(
        user_id=user_id,
        name=bot_data.name,
        symbol=bot_data.symbol,
        allocation_percent=bot_data.allocation_percent,
        max_leverage=bot_data.max_leverage,
        max_positions=bot_data.max_positions,
        strategy_id=bot_data.strategy_id
    )

    await db.add(bot)
    await db.commit()

    return bot
```

### 2. 그리드 트레이딩

**가격 계산** (`backend/src/utils/grid_calculator.py`):
```python
def calculate_grid_prices(
    lower_price: float,
    upper_price: float,
    grid_count: int,
    mode: str = 'arithmetic'
) -> List[float]:
    """그리드 가격 배열 계산"""

    if mode == 'arithmetic':
        # 등차: 일정한 가격 간격
        step = (upper_price - lower_price) / (grid_count - 1)
        return [lower_price + i * step for i in range(grid_count)]

    elif mode == 'geometric':
        # 등비: 일정한 비율 간격
        ratio = (upper_price / lower_price) ** (1 / (grid_count - 1))
        return [lower_price * (ratio ** i) for i in range(grid_count)]

    else:
        raise ValueError(f"Unknown mode: {mode}")

# 예시
# arithmetic: [30000, 30500, 31000, 31500, 32000]
# geometric:  [30000, 30300, 30609, 30927, 31254] (1% 증가)
```

**그리드 봇 실행** (`backend/src/services/grid_bot_runner.py`):
```python
class GridBotRunner:
    def __init__(self, bot_instance_id: int):
        self.bot_instance_id = bot_instance_id
        self.config = None
        self.exchange = None

    async def initialize(self):
        """초기화: 설정 로드 + 거래소 연결"""
        self.config = await db.query(GridBotConfig).filter(
            GridBotConfig.bot_instance_id == self.bot_instance_id
        ).first()

        bot = await db.get(BotInstance, self.bot_instance_id)
        api_keys = await get_user_api_keys(bot.user_id)
        self.exchange = BitgetExchange(api_keys)

    async def setup_grid(self):
        """초기 그리드 주문 배치"""
        grid_prices = calculate_grid_prices(
            lower_price=self.config.lower_price,
            upper_price=self.config.upper_price,
            grid_count=self.config.grid_count,
            mode=self.config.grid_mode
        )

        per_grid_amount = self.config.per_grid_amount

        for index, price in enumerate(grid_prices):
            # 매수 주문 배치
            order = await self.exchange.create_limit_order(
                symbol=self.config.symbol,
                side='buy',
                price=price,
                amount=per_grid_amount
            )

            # DB에 GridOrder 생성
            grid_order = GridOrder(
                grid_config_id=self.config.id,
                grid_index=index,
                grid_price=price,
                buy_order_id=order['id'],
                status='BUY_PLACED'
            )
            await db.add(grid_order)

        await db.commit()

    async def monitor_orders(self):
        """주문 모니터링 및 사이클 관리"""
        while True:
            # 모든 그리드 주문 조회
            grid_orders = await db.query(GridOrder).filter(
                GridOrder.grid_config_id == self.config.id,
                GridOrder.status.in_(['BUY_PLACED', 'SELL_PLACED'])
            ).all()

            for order in grid_orders:
                # 주문 상태 확인
                if order.status == 'BUY_PLACED':
                    buy_order = await self.exchange.fetch_order(
                        order.buy_order_id
                    )

                    if buy_order['status'] == 'closed':
                        # 매수 체결 → 매도 주문 생성
                        await self.handle_buy_filled(order, buy_order)

                elif order.status == 'SELL_PLACED':
                    sell_order = await self.exchange.fetch_order(
                        order.sell_order_id
                    )

                    if sell_order['status'] == 'closed':
                        # 매도 체결 → 사이클 완료
                        await self.handle_sell_filled(order, sell_order)

            await asyncio.sleep(10)  # 10초마다 체크

    async def handle_buy_filled(self, grid_order: GridOrder, buy_order: dict):
        """매수 체결 처리"""
        # 1. GridOrder 업데이트
        grid_order.status = 'BUY_FILLED'
        grid_order.buy_filled_price = buy_order['average']
        grid_order.buy_filled_qty = buy_order['filled']
        grid_order.buy_filled_at = datetime.utcnow()

        # 2. 다음 그리드 가격 계산 (한 칸 위)
        next_index = grid_order.grid_index + 1
        if next_index < self.config.grid_count:
            grid_prices = calculate_grid_prices(
                self.config.lower_price,
                self.config.upper_price,
                self.config.grid_count,
                self.config.grid_mode
            )
            sell_price = grid_prices[next_index]
        else:
            sell_price = grid_order.grid_price * 1.01  # 1% 위

        # 3. 매도 주문 생성
        sell_order = await self.exchange.create_limit_order(
            symbol=self.config.symbol,
            side='sell',
            price=sell_price,
            amount=grid_order.buy_filled_qty
        )

        grid_order.sell_order_id = sell_order['id']
        grid_order.status = 'SELL_PLACED'

        await db.commit()

    async def handle_sell_filled(self, grid_order: GridOrder, sell_order: dict):
        """매도 체결 처리"""
        # 1. 실현 손익 계산
        profit = (
            (sell_order['average'] - grid_order.buy_filled_price)
            * sell_order['filled']
        )

        grid_order.status = 'SELL_FILLED'
        grid_order.sell_filled_price = sell_order['average']
        grid_order.sell_filled_qty = sell_order['filled']
        grid_order.sell_filled_at = datetime.utcnow()
        grid_order.profit = profit

        # 2. 총 실현 손익 업데이트
        self.config.realized_profit += profit

        # 3. 다시 매수 주문 배치 (사이클 반복)
        new_buy_order = await self.exchange.create_limit_order(
            symbol=self.config.symbol,
            side='buy',
            price=grid_order.grid_price,
            amount=self.config.per_grid_amount
        )

        # 4. 새 GridOrder 생성
        new_grid_order = GridOrder(
            grid_config_id=self.config.id,
            grid_index=grid_order.grid_index,
            grid_price=grid_order.grid_price,
            buy_order_id=new_buy_order['id'],
            status='BUY_PLACED'
        )
        await db.add(new_grid_order)

        await db.commit()

        # 5. WebSocket 알림
        await ws_manager.broadcast(self.user_id, {
            'type': 'grid_profit',
            'profit': profit,
            'total_profit': self.config.realized_profit
        })

    async def run(self):
        """그리드 봇 실행"""
        await self.initialize()
        await self.setup_grid()
        await self.monitor_orders()
```

### 3. 리스크 관리

**리스크 엔진** (`backend/src/services/risk_engine.py`):
```python
class RiskEngine:
    @staticmethod
    async def check_daily_loss_limit(user_id: int) -> bool:
        """일일 손실 한도 체크"""
        # 오늘의 거래 조회
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0)

        trades = await db.query(Trade).filter(
            Trade.user_id == user_id,
            Trade.created_at >= today_start
        ).all()

        daily_pnl = sum(t.pnl for t in trades if t.pnl is not None)

        # 일일 손실이 -5% 초과하면 거래 중지
        account = await get_account_info(user_id)
        loss_limit = account.balance * 0.05

        if daily_pnl < -loss_limit:
            logger.warning(f"Daily loss limit exceeded: {daily_pnl}")
            return False

        return True

    @staticmethod
    async def check_position_limit(bot_instance_id: int) -> bool:
        """포지션 개수 한도 체크"""
        bot = await db.get(BotInstance, bot_instance_id)

        open_positions = await db.query(Position).filter(
            Position.bot_instance_id == bot_instance_id
        ).count()

        if open_positions >= bot.max_positions:
            logger.warning(f"Position limit reached: {open_positions}/{bot.max_positions}")
            return False

        return True

    @staticmethod
    async def check_leverage_risk(
        bot_instance_id: int,
        leverage: int
    ) -> bool:
        """레버리지 리스크 체크"""
        bot = await db.get(BotInstance, bot_instance_id)

        if leverage > bot.max_leverage:
            logger.warning(f"Leverage too high: {leverage} > {bot.max_leverage}")
            return False

        # 청산 가격 계산
        account = await get_account_info(bot.user_id)
        current_price = await get_current_price(bot.symbol)

        liquidation_distance = 100 / leverage  # %

        if liquidation_distance < 5:
            logger.warning(f"Liquidation risk too high: {liquidation_distance}%")
            return False

        return True

    @staticmethod
    async def apply_stop_loss(position_id: int):
        """스탑로스 적용"""
        position = await db.get(Position, position_id)
        bot = await db.get(BotInstance, position.bot_instance_id)

        current_price = await get_current_price(position.symbol)

        # 손실률 계산
        if position.side == 'long':
            loss_percent = (
                (position.entry_price - current_price)
                / position.entry_price * 100
            )
        else:
            loss_percent = (
                (current_price - position.entry_price)
                / position.entry_price * 100
            )

        # 스탑로스 조건
        if loss_percent >= bot.stop_loss_percent:
            logger.info(f"Stop loss triggered: {loss_percent}%")
            await close_position(position_id, reason='stop_loss')

            # 알림
            await ws_manager.broadcast(bot.user_id, {
                'type': 'system_alert',
                'level': 'warning',
                'message': f"스탑로스 발동: {position.symbol}"
            })
```

**거래 전 리스크 체크**:
```python
async def execute_trade_with_risk_check(bot_instance_id: int, signal: str):
    # 1. 일일 손실 한도
    if not await RiskEngine.check_daily_loss_limit(user_id):
        logger.warning("Daily loss limit exceeded, skipping trade")
        return

    # 2. 포지션 개수
    if not await RiskEngine.check_position_limit(bot_instance_id):
        logger.warning("Position limit reached, skipping trade")
        return

    # 3. 레버리지 리스크
    if not await RiskEngine.check_leverage_risk(bot_instance_id, leverage):
        logger.warning("Leverage risk too high, skipping trade")
        return

    # 4. 거래 실행
    await execute_trade(bot_instance_id, signal)
```

---

## 데이터베이스 설계

### ERD (주요 테이블 관계)

```
users
  ├─ has many → bot_instances
  ├─ has many → strategies
  ├─ has many → trades
  ├─ has many → positions
  └─ has many → equities

bot_instances
  ├─ belongs to → users
  ├─ belongs to → strategies (optional)
  ├─ belongs to → grid_bot_templates (optional)
  ├─ has one → grid_bot_configs
  ├─ has many → trades
  └─ has many → positions

grid_bot_configs
  ├─ belongs to → bot_instances
  └─ has many → grid_orders

grid_bot_templates (admin-created)
  └─ has many → bot_instances (users applying template)
```

### 테이블 상세

#### 1. users
```sql
CREATE TABLE users (
  id SERIAL PRIMARY KEY,
  email VARCHAR(255) UNIQUE NOT NULL,
  password_hash VARCHAR(255),  -- OAuth 사용자는 NULL
  name VARCHAR(100),
  phone VARCHAR(20),
  role VARCHAR(20) DEFAULT 'user',  -- 'user' or 'admin'
  exchange VARCHAR(50) DEFAULT 'bitget',
  is_active BOOLEAN DEFAULT true,

  -- OAuth
  oauth_provider VARCHAR(50),  -- 'google' or 'kakao'
  oauth_id VARCHAR(255),
  profile_image TEXT,

  -- 2FA
  totp_secret TEXT,  -- AES 암호화됨
  is_2fa_enabled BOOLEAN DEFAULT false,

  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_user_email ON users(email);
CREATE INDEX idx_user_oauth ON users(oauth_provider, oauth_id);
```

#### 2. api_keys
```sql
CREATE TABLE api_keys (
  id SERIAL PRIMARY KEY,
  user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
  encrypted_api_key TEXT NOT NULL,
  encrypted_secret_key TEXT NOT NULL,
  encrypted_passphrase TEXT,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),

  UNIQUE(user_id)  -- 사용자당 1개
);
```

#### 3. bot_instances
```sql
CREATE TABLE bot_instances (
  id SERIAL PRIMARY KEY,
  user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
  strategy_id INTEGER REFERENCES strategies(id) ON DELETE SET NULL,
  template_id INTEGER REFERENCES grid_bot_templates(id) ON DELETE SET NULL,

  name VARCHAR(100) NOT NULL,
  description TEXT,
  bot_type VARCHAR(20) NOT NULL,  -- 'STRATEGY' or 'GRID'

  -- 자본 할당
  allocation_percent DECIMAL(5,2) NOT NULL CHECK (allocation_percent > 0 AND allocation_percent <= 100),

  -- 거래 설정
  symbol VARCHAR(20) NOT NULL,  -- 'BTCUSDT'
  max_leverage INTEGER DEFAULT 1 CHECK (max_leverage >= 1 AND max_leverage <= 100),
  max_positions INTEGER DEFAULT 1 CHECK (max_positions >= 1 AND max_positions <= 20),

  -- 리스크 관리
  stop_loss_percent DECIMAL(5,2) DEFAULT 5.0,
  take_profit_percent DECIMAL(5,2) DEFAULT 10.0,

  -- 상태
  is_running BOOLEAN DEFAULT false,
  is_active BOOLEAN DEFAULT true,

  -- 알림
  telegram_notify BOOLEAN DEFAULT false,

  -- 통계
  last_started_at TIMESTAMP,
  last_stopped_at TIMESTAMP,
  last_error TEXT,
  total_trades INTEGER DEFAULT 0,
  winning_trades INTEGER DEFAULT 0,
  total_pnl DECIMAL(15,2) DEFAULT 0.00,

  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_bot_instances_user_id ON bot_instances(user_id);
CREATE INDEX idx_bot_instances_user_running ON bot_instances(user_id, is_running);
```

#### 4. grid_bot_templates
```sql
CREATE TABLE grid_bot_templates (
  id SERIAL PRIMARY KEY,
  name VARCHAR(100) NOT NULL,
  symbol VARCHAR(20) NOT NULL,
  direction VARCHAR(10) NOT NULL,  -- 'long' or 'short'
  leverage INTEGER DEFAULT 1,

  -- 그리드 설정
  lower_price DECIMAL(20,8) NOT NULL,
  upper_price DECIMAL(20,8) NOT NULL,
  grid_count INTEGER NOT NULL CHECK (grid_count >= 2 AND grid_count <= 100),
  grid_mode VARCHAR(20) DEFAULT 'geometric',  -- 'arithmetic' or 'geometric'

  -- 투자 금액
  min_investment DECIMAL(15,2) DEFAULT 100.00,
  recommended_investment DECIMAL(15,2) DEFAULT 500.00,

  -- 백테스트 결과
  backtest_roi_30d DECIMAL(10,2),
  backtest_max_drawdown DECIMAL(10,2),
  backtest_total_trades INTEGER,
  backtest_win_rate DECIMAL(5,2),
  backtest_roi_history JSONB,  -- [{"date": "2024-01-01", "roi": 2.3}]

  -- 설명
  description TEXT,
  tags TEXT[],  -- ['conservative', 'btc', 'ranging']

  -- 사용 통계
  active_users INTEGER DEFAULT 0,
  total_users INTEGER DEFAULT 0,
  total_funds_in_use DECIMAL(20,2) DEFAULT 0.00,

  -- 상태
  is_active BOOLEAN DEFAULT true,
  is_featured BOOLEAN DEFAULT false,

  created_by INTEGER REFERENCES users(id),
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_grid_templates_active ON grid_bot_templates(is_active, is_featured);
CREATE INDEX idx_grid_templates_symbol ON grid_bot_templates(symbol);
```

#### 5. grid_bot_configs
```sql
CREATE TABLE grid_bot_configs (
  id SERIAL PRIMARY KEY,
  bot_instance_id INTEGER REFERENCES bot_instances(id) ON DELETE CASCADE UNIQUE,

  lower_price DECIMAL(20,8) NOT NULL,
  upper_price DECIMAL(20,8) NOT NULL,
  grid_count INTEGER NOT NULL,
  grid_mode VARCHAR(20) DEFAULT 'geometric',

  total_investment DECIMAL(15,2) NOT NULL,
  per_grid_amount DECIMAL(15,8) NOT NULL,

  -- 현재 상태
  trigger_price DECIMAL(20,8),
  stop_upper DECIMAL(20,8),
  stop_lower DECIMAL(20,8),
  current_price DECIMAL(20,8),

  active_buy_orders INTEGER DEFAULT 0,
  active_sell_orders INTEGER DEFAULT 0,
  filled_buy_count INTEGER DEFAULT 0,
  filled_sell_count INTEGER DEFAULT 0,

  realized_profit DECIMAL(15,2) DEFAULT 0.00,

  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_grid_config_bot ON grid_bot_configs(bot_instance_id);
```

#### 6. grid_orders
```sql
CREATE TABLE grid_orders (
  id SERIAL PRIMARY KEY,
  grid_config_id INTEGER REFERENCES grid_bot_configs(id) ON DELETE CASCADE,

  grid_index INTEGER NOT NULL,
  grid_price DECIMAL(20,8) NOT NULL,

  buy_order_id VARCHAR(100),
  sell_order_id VARCHAR(100),

  status VARCHAR(20) NOT NULL,
  -- 'PENDING', 'BUY_PLACED', 'BUY_FILLED',
  -- 'SELL_PLACED', 'SELL_FILLED', 'COMPLETED'

  -- 매수 정보
  buy_filled_price DECIMAL(20,8),
  buy_filled_qty DECIMAL(20,8),
  buy_filled_at TIMESTAMP,

  -- 매도 정보
  sell_filled_price DECIMAL(20,8),
  sell_filled_qty DECIMAL(20,8),
  sell_filled_at TIMESTAMP,

  profit DECIMAL(15,2),

  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_grid_orders_config ON grid_orders(grid_config_id);
CREATE INDEX idx_grid_orders_status ON grid_orders(status);
```

#### 7. strategies
```sql
CREATE TABLE strategies (
  id SERIAL PRIMARY KEY,
  user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,

  name VARCHAR(100) NOT NULL,
  description TEXT,
  code TEXT NOT NULL,  -- Python code
  params JSONB,  -- {"rsi_period": 14, "ema_fast": 9}

  is_active BOOLEAN DEFAULT true,

  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_strategy_user ON strategies(user_id, is_active);
```

#### 8. trades
```sql
CREATE TABLE trades (
  id SERIAL PRIMARY KEY,
  user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
  bot_instance_id INTEGER REFERENCES bot_instances(id) ON DELETE SET NULL,
  strategy_id INTEGER REFERENCES strategies(id) ON DELETE SET NULL,

  symbol VARCHAR(20) NOT NULL,
  side VARCHAR(10) NOT NULL,  -- 'buy' or 'sell'
  qty DECIMAL(20,8) NOT NULL,

  entry_price DECIMAL(20,8) NOT NULL,
  exit_price DECIMAL(20,8),

  pnl DECIMAL(15,2),
  pnl_percent DECIMAL(10,2),

  leverage INTEGER DEFAULT 1,
  exit_reason VARCHAR(50),  -- 'strategy', 'stop_loss', 'take_profit', 'manual'

  enter_tag VARCHAR(50),
  exit_tag VARCHAR(50),
  order_tag VARCHAR(50),

  trade_source VARCHAR(20) DEFAULT 'MANUAL',
  -- 'AI_BOT', 'GRID_BOT', 'MANUAL'

  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_trade_user_created ON trades(user_id, created_at DESC);
CREATE INDEX idx_trade_bot_instance ON trades(bot_instance_id);
```

#### 9. positions
```sql
CREATE TABLE positions (
  id SERIAL PRIMARY KEY,
  user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
  bot_instance_id INTEGER REFERENCES bot_instances(id) ON DELETE SET NULL,

  symbol VARCHAR(20) NOT NULL,
  entry_price DECIMAL(20,8) NOT NULL,
  size DECIMAL(20,8) NOT NULL,
  side VARCHAR(10) NOT NULL,  -- 'long' or 'short'

  pnl DECIMAL(15,2) DEFAULT 0.00,

  exchange_order_id VARCHAR(100),

  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_position_user ON positions(user_id);
CREATE INDEX idx_position_bot_instance ON positions(bot_instance_id);
```

#### 10. equities
```sql
CREATE TABLE equities (
  id SERIAL PRIMARY KEY,
  user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,

  value DECIMAL(15,2) NOT NULL,
  timestamp TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_equity_user_time ON equities(user_id, timestamp DESC);
```

### 데이터 무결성 규칙

1. **할당 검증**: 모든 bot_instances의 allocation_percent 합 ≤ 100%
2. **포지션 제한**: 봇당 열린 포지션 개수 ≤ bot.max_positions
3. **레버리지 제한**: 거래 시 leverage ≤ bot.max_leverage
4. **캐스케이드 삭제**: 사용자 삭제 시 모든 관련 데이터 삭제

---

## 인프라 및 배포

### Docker Compose 구성

```yaml
# docker-compose.yml
version: '3.8'

services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: trading
      POSTGRES_USER: trader
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U trader"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    command: redis-server --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s

  backend:
    build: ./backend
    environment:
      DATABASE_URL: postgresql+asyncpg://trader:${POSTGRES_PASSWORD}@postgres:5432/trading
      REDIS_URL: redis://:${REDIS_PASSWORD}@redis:6379/0
      JWT_SECRET: ${JWT_SECRET}
      ENCRYPTION_KEY: ${ENCRYPTION_KEY}
      ENVIRONMENT: production
      CORS_ORIGINS: ${FRONTEND_URL}
      GOOGLE_CLIENT_ID: ${GOOGLE_CLIENT_ID}
      GOOGLE_CLIENT_SECRET: ${GOOGLE_CLIENT_SECRET}
      KAKAO_CLIENT_ID: ${KAKAO_CLIENT_ID}
      KAKAO_CLIENT_SECRET: ${KAKAO_CLIENT_SECRET}
      TELEGRAM_BOT_TOKEN: ${TELEGRAM_BOT_TOKEN}
      DEEPSEEK_API_KEY: ${DEEPSEEK_API_KEY}
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    command: uvicorn src.main:app --host 0.0.0.0 --port 8000
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      VITE_API_URL: ${API_URL}
    depends_on:
      - backend

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./nginx/ssl:/etc/nginx/ssl
    depends_on:
      - frontend
      - backend

volumes:
  postgres_data:
  redis_data:
```

### 환경 변수 (.env)

```bash
# 데이터베이스
POSTGRES_PASSWORD=strong_password_here
DATABASE_URL=postgresql+asyncpg://trader:strong_password@postgres:5432/trading

# Redis
REDIS_PASSWORD=redis_password_here

# JWT (반드시 변경!)
JWT_SECRET=your-super-secret-jwt-key-change-this-in-production

# API 키 암호화 (32바이트 base64)
ENCRYPTION_KEY=Dz9w_blEMa-tMD5hqK6V7yiaYecQBdsTaO0PJR3ESn8=

# 환경
ENVIRONMENT=production

# CORS
CORS_ORIGINS=https://yourdomain.com
FRONTEND_URL=https://yourdomain.com
API_URL=https://api.yourdomain.com

# OAuth
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
KAKAO_CLIENT_ID=your-kakao-client-id
KAKAO_CLIENT_SECRET=your-kakao-client-secret

# Telegram
TELEGRAM_BOT_TOKEN=your-telegram-bot-token
TELEGRAM_CHAT_ID=your-chat-id

# DeepSeek AI
DEEPSEEK_API_KEY=your-deepseek-api-key
```

### Nginx 설정

```nginx
# nginx/nginx.conf
upstream backend {
    server backend:8000;
}

upstream frontend {
    server frontend:3000;
}

server {
    listen 80;
    server_name yourdomain.com;

    # HTTPS로 리다이렉트
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    # SSL 인증서
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;

    # SSL 설정
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # 프론트엔드
    location / {
        proxy_pass http://frontend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    # API
    location /api/ {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket
    location /ws/ {
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 86400;  # 24시간
    }
}
```

---

## 보안 기능

### 1. JWT 인증
- Access 토큰: 1시간 유효
- Refresh 토큰: 7일 유효
- HS256 알고리즘
- 페이로드: user_id, email, role, exp

### 2. 2FA (TOTP)
- pyotp 라이브러리
- 30초 간격 코드 생성
- 비밀키 AES-256 암호화 저장

### 3. API 키 암호화
- AES-256-GCM
- 환경 변수로 관리되는 ENCRYPTION_KEY
- 데이터베이스에 암호문만 저장

### 4. 브루트포스 방어
- 5회 로그인 실패 시 15분 잠금
- IP 기반 추적
- Redis 캐시 활용

### 5. Rate Limiting
- IP 기반: 60 req/min
- 사용자 기반: 100 req/min
- 관리자 API: IP 화이트리스트 (프로덕션)

### 6. CORS
- 개발: localhost 허용
- 프로덕션: 환경 변수로 지정된 도메인만

### 7. 비밀번호 정책
- 최소 8자
- 대문자 + 소문자 + 숫자 + 특수문자
- bcrypt 해싱 (cost factor: 12)

---

## 성능 최적화

### 1. 비동기 I/O
- FastAPI async/await
- SQLAlchemy AsyncSession
- aiohttp for external APIs

### 2. 데이터베이스 최적화
- 전략적 인덱스 (user_id, created_at, bot_instance_id)
- 페이지네이션 (LIMIT/OFFSET)
- Connection pooling

### 3. 캐싱
- Redis: 세션, 캔들 데이터
- 백테스트 결과 캐싱
- Rate limit 카운터

### 4. WebSocket
- Connection pooling
- 자동 재연결 (지수 백오프)
- Dead connection cleanup

### 5. 프론트엔드
- React.lazy (코드 스플리팅)
- 메모이제이션 (useMemo, useCallback)
- 이미지 최적화

---

## 📊 요약

이 플랫폼은 **엔터프라이즈급 암호화폐 트레이딩 자동화 시스템**으로:

✅ **다중 봇 시스템**: 사용자당 10개 봇, 독립적 자본 할당
✅ **그리드 트레이딩**: 레인지 시장 수익화
✅ **AI 전략 생성**: DeepSeek API 활용
✅ **백테스팅**: 과거 데이터 검증
✅ **실시간 모니터링**: WebSocket 기반
✅ **리스크 관리**: 일일 손실 한도, 스탑로스
✅ **보안**: JWT, 2FA, API 키 암호화
✅ **확장 가능**: Docker Compose, 마이크로서비스 아키텍처

**기술 스택**: FastAPI + React + PostgreSQL + Redis + WebSocket
**거래소**: Bitget, Binance, OKX
**배포**: Docker Compose + Nginx

---

**이 문서를 읽은 사람은 시스템의 모든 구현 세부사항을 이해하고, 필요한 부분을 수정하거나 확장할 수 있습니다.**
