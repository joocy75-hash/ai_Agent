# 📝 작업 로그 - 자동매매 플랫폼

**최종 업데이트**: 2025-12-03 (세션 5 계속 - 백테스트 구현 완료)
**플랫폼 유형**: **일반 사용자용 암호화폐 선물 자동매매 플랫폼**
**중요 사항**: 관리자 전용 시스템이 아닙니다. 일반 사용자가 회원가입, 로그인, 전략 생성, 백테스트, 실전 자동매매를 수행합니다.

---

## ⚠️ 중요: 다음 AI 에이전트를 위한 지침

**중요 - 먼저 읽으세요:**

이 플랫폼은 **일반 사용자**를 위한 것입니다:
1. 자신의 계정으로 회원가입 및 로그인
2. 맞춤형 거래 전략 생성
3. 실제 과거 데이터로 전략 백테스트
4. 실제 자금으로 실전 자동매매 실행

**따라서:**
- **절대 금지**: 시스템의 다른 부분을 망가뜨리는 빠른 수정
- **절대 금지**: 기능이 작동한다고 가정 - 항상 전체 사용자 워크플로우 검증 필요
- **절대 금지**: 모든 사용자에게 미치는 영향을 이해하지 않고 핵심 로직 수정
- **반드시 수행**: 전체 흐름 테스트 - 회원가입 → 로그인 → 전략 생성 → 백테스트 → 실전 거래
- **반드시 수행**: 모든 작업 완료 후 WORK_LOG.md 업데이트

**항상 이 지침 포함:**
WORK_LOG.md 업데이트 시, 향후 AI 에이전트를 위한 연속성을 보장하기 위해 항상 이 "중요: 다음 AI 에이전트를 위한 지침" 섹션 전체를 포함하세요.

---

## 🚦 현재 시스템 상태 (2025-12-03)

### ✅ 실행 중인 서비스
- **백엔드**: http://localhost:8000
- **프론트엔드**: http://localhost:3001
- **데이터베이스**: `/Users/mr.joo/Desktop/auto-dashboard/backend/trading.db`
- **로그 파일**: `/tmp/backend.log`

### 🔐 환경 변수 (필수)
```bash
export DATABASE_URL="sqlite+aiosqlite:///./trading.db"
export ENCRYPTION_KEY="Dz9w_blEMa-tMD5hqK6V7yiaYecQBdsTaO0PJR3ESn8="
```

### 👤 테스트 계정
- **이메일**: admin@admin.com
- **비밀번호**: admin
- **사용자 ID**: 6

---

## ✅ 완료됨 - 세션 5 계속: 백테스트 워크플로우 구현

### 달성한 내용

**완전한 CSV 없는 백테스트 워크플로우** - 사용자가 CSV 파일을 수동으로 업로드하지 않고도 전략을 백테스트할 수 있습니다. 과거 데이터는 Bitget API에서 자동으로 가져옵니다.

### 수정된 파일

1. **[bitget_rest.py](backend/src/services/bitget_rest.py)**
   - `get_historical_candles()` 메서드 추가 (517-589줄)
   - 공개 엔드포인트를 위해 API 자격 증명을 선택 사항으로 변경
   - 공개/비공개 API 요청 처리 추가
   - 심볼 형식: "BTCUSDT", 간격 형식: "1H" (대문자)
   - 제품 타입: "USDT-FUTURES" 필수

2. **[backtest.py](backend/src/api/backtest.py)**
   - 106-160줄: csv_path가 None일 때 과거 데이터 자동 가져오기
   - 심볼 변환: "BTC/USDT" → "BTCUSDT"
   - 동기/비동기 세션 사용 수정 (sync session.execute에서 `await` 제거)
   - 전략 코드 매핑: DB `code` 대신 params의 `strategy_type` 사용
   - 백그라운드 태스크가 Bitget에서 200개 캔들 가져와 CSV 저장 후 백테스트 실행

3. **[backtest_result.py](backend/src/api/backtest_result.py)**
   - 91-92줄: 응답에 `status` 및 `error_message` 필드 추가

4. **[backtest_response_schema.py](backend/src/schemas/backtest_response_schema.py)**
   - 51-52줄: Pydantic 스키마에 `status` 및 `error_message` 추가

5. **[BacktestRunner.jsx](frontend/src/components/strategy/BacktestRunner.jsx)**
   - CSV 업로드 UI 제거 (Dragger 컴포넌트)
   - 날짜 선택을 위한 DatePicker와 RangePicker 추가
   - 요청 형식: `{strategy_id, initial_balance, start_date, end_date}`
   - 자동 데이터 다운로드에 대한 정보 알림 추가

6. **[backtest.js](frontend/src/api/backtest.js)** - 새 파일
   - 백테스트 작업을 위한 API 클라이언트 생성
   - 메서드: `start()`, `getResult()`, `getHistory()`

### 주요 기술 솔루션

| 문제 | 해결 방법 |
|------|----------|
| 심볼 형식 불일치 | API 호출 전 "BTC/USDT" → "BTCUSDT" 변환 |
| 간격 형식 오류 | "1h" → "1H" 변환 (Bitget은 대문자 필요) |
| productType 누락 | 모든 캔들 요청에 "USDT-FUTURES" 추가 |
| 동기/비동기 혼동 | 동기 세션에는 `session.execute()` 사용 (await 없이) |
| 전략 코드 불일치 | `strategy.code` 대신 `strategy_params['type']` 사용 |
| 상태 필드 누락 | 응답 dict와 Pydantic 스키마 모두에 추가 |

### 테스트 결과 ✅

**테스트 스크립트**: [test_backtest_workflow.sh](test_backtest_workflow.sh)

```
전략: RSI Strategy (ID: 3)
초기 잔고: 10,000 USDT
최종 잔고: 10,857 USDT
수익률: +8.57%
거래 수: 2
상태: completed ✅
과거 데이터: Bitget API에서 자동 가져오기 ✅
```

### 설치된 종속성
```bash
pip3 install python-multipart  # 파일 업로드 엔드포인트에 필요
```

---

## 🔴 주의가 필요한 중요 문제

### 1. 백테스트 지표 계산 안 됨 (우선순위 🔴)

**문제**:
- 백테스트가 성공적으로 완료됨
- `final_balance`가 올바르게 계산됨
- 하지만 `metrics` 필드가 비어 있음: `{}`
- 요약 통계가 total_return, win_rate, sharpe_ratio 등에 대해 "null" 표시

**중요한 이유**:
사용자는 전략을 평가하기 위해 백테스트 성능 지표를 확인해야 합니다. 지표 없이는 정보에 근거한 결정을 내릴 수 없습니다.

**근본 원인**:
백테스트 엔진([backtest.py](backend/src/api/backtest.py))이 결과를 저장하지만 지표를 계산하거나 저장하지 않습니다.

**필요한 해결 방법**:
1. [backtest.py](backend/src/api/backtest.py:80-180)의 `_run_backtest_background()` 함수 확인
2. 백테스트 완료 후 다음 계산:
   - 총 수익률 %
   - 총 거래 수
   - 승률 %
   - 손익비
   - 샤프 비율
   - 최대 낙폭 %
3. `BacktestResult.metrics`에 JSON 문자열로 저장
4. 계산 예시:
```python
import json

# 백테스트 실행 후
total_return = ((final_balance - initial_balance) / initial_balance) * 100
total_trades = len(all_trades)
winning_trades = [t for t in all_trades if t['pnl'] > 0]
win_rate = (len(winning_trades) / total_trades * 100) if total_trades > 0 else 0

metrics = {
    "total_return": round(total_return, 2),
    "total_trades": total_trades,
    "win_rate": round(win_rate, 2),
    "profit_factor": calculate_profit_factor(all_trades),
    "sharpe_ratio": calculate_sharpe_ratio(equity_curve),
    "max_drawdown": calculate_max_drawdown(equity_curve)
}

result.metrics = json.dumps(metrics)
session.commit()
```

**수정할 파일**:
- [backtest.py](backend/src/api/backtest.py:80-180) - 지표 계산 추가

---

### 2. 실전 거래를 위한 단일 캔들 문제 (우선순위 🔴)

**문제**:
- 실전 거래 봇이 전략에 1개의 캔들만 전달
- RSI, EMA 및 기타 지표는 정확한 계산을 위해 50-100개의 캔들 필요
- 전략 시그널이 신뢰할 수 없거나 무작위

**중요한 이유**:
사용자의 실전 거래가 잘못된 결정을 내려 금전적 손실로 이어집니다.

**필요한 해결 방법**:

**파일**: [bot_runner.py](backend/src/services/bot_runner.py:44-110) - `_run_loop()` 메서드

봇 루프 시작 시 과거 캔들 로딩 추가:

```python
from collections import deque

async def _run_loop(self, session_factory, user_id):
    # ... 기존 전략 로드 코드 ...

    # 🆕 과거 캔들 로드
    candle_buffer = deque(maxlen=100)

    # 전략 params에서 심볼과 타임프레임 가져오기
    strategy_params = json.loads(strategy.params) if strategy.params else {}
    symbol = strategy_params.get('symbol', 'BTC/USDT').replace('/', '')  # "BTCUSDT"
    timeframe = strategy_params.get('timeframe', '1h')

    try:
        # BitgetRestClient를 사용하여 과거 100개 캔들 가져오기
        from ..services.bitget_rest import BitgetRestClient

        # 사용자 계정에서 API 키 가져오기
        account = session.query(UserAccount).filter_by(user_id=user_id).first()
        if account:
            bitget_rest = BitgetRestClient(
                api_key=decrypt(account.api_key),
                api_secret=decrypt(account.secret_key),
                passphrase=decrypt(account.passphrase) if account.passphrase else ""
            )

            historical = await bitget_rest.get_historical_candles(
                symbol=symbol,
                interval=timeframe,
                limit=100
            )

            for candle in historical:
                candle_buffer.append({
                    "open": candle["open"],
                    "high": candle["high"],
                    "low": candle["low"],
                    "close": candle["close"],
                    "volume": candle["volume"],
                    "time": candle["timestamp"]
                })

            logger.info(f"✅ {symbol} {timeframe}에 대한 과거 캔들 {len(candle_buffer)}개 로드됨")
    except Exception as e:
        logger.error(f"❌ 과거 캔들 로드 실패: {e}")
        # 빈 버퍼로 계속 - 봇이 시간이 지남에 따라 캔들을 축적할 것임

    # 메인 루프
    while True:
        market = await self.market_queue.get()
        price = float(market.get("price", 0))

        # 버퍼에 새 캔들 추가
        new_candle = {
            "open": market.get("open", price),
            "high": market.get("high", price),
            "low": market.get("low", price),
            "close": market.get("close", price),
            "volume": market.get("volume", 0),
            "time": market.get("time", 0)
        }
        candle_buffer.append(new_candle)

        # 전략에 모든 캔들 전달 (1개만 아님!)
        candles = list(candle_buffer)  # deque를 리스트로 변환

        # 전체 캔들 히스토리로 시그널 생성
        signal_result = generate_signal_with_strategy(
            strategy_code=strategy_code,
            current_price=price,
            candles=candles,  # 🔑 이것이 핵심 변경 사항!
            params_json=strategy.params,
            current_position=current_position
        )

        # ... 나머지 거래 로직 ...
```

**테스트**:
구현 후 로그 확인으로 검증:
```bash
tail -f /tmp/backend.log | grep "과거 캔들"
# 다음이 보여야 함: "✅ BTCUSDT 1h에 대한 과거 캔들 100개 로드됨"
```

---

### 3. Mock 가격 생성기 여전히 활성 (우선순위 🟡)

**문제**:
- 실전 거래가 **모의/가짜 가격**을 사용, 실제 Bitget 데이터 아님
- 파일: [db.py:51](backend/src/database/db.py#L51)

**중요한 이유**:
사용자가 실제 시장 데이터로 거래한다고 생각하지만 그렇지 않습니다.

**해결 방법**:

**파일**: [db.py:51-56](backend/src/database/db.py#L51-L56)

```python
# mock 생성기 주석 처리
# asyncio.create_task(mock_price_generator(market_queue))
# logger.info("✅ Mock price generator started")

# 실제 Bitget WebSocket 주석 해제
asyncio.create_task(bitget_ws_collector(market_queue))
logger.info("✅ Bitget WebSocket collector started")
```

**⚠️ 먼저 mock 데이터로 테스트한 후에만 실행하세요!**

---

### 4. 백테스트에서 전략 목록이 표시되지 않음 (우선순위 🟡)

**문제**:
- 사용자 보고: "백테스트에 전략 선택 드롭다운이 비어있음"
- BacktestRunner가 StrategyList에서 전략을 받지 못함

**상태**: ✅ **해결됨** - 이번 세션에서

**적용된 해결 방법**:
1. [Strategy.jsx](frontend/src/pages/Strategy.jsx) 수정하여 콜백 추가
2. [StrategyList.jsx](frontend/src/components/strategy/StrategyList.jsx) 수정하여 `onStrategiesLoaded()` 호출
3. 전략 흐름: StrategyList → Strategy (부모) → BacktestRunner

**수정된 파일**:
- [Strategy.jsx](frontend/src/pages/Strategy.jsx): `handleStrategiesLoaded` 콜백 추가
- [StrategyList.jsx](frontend/src/components/strategy/StrategyList.jsx): 로드된 전략으로 부모 콜백 호출
- [BacktestRunner.jsx](frontend/src/components/strategy/BacktestRunner.jsx): 전략을 prop으로 받음

---

### 5. 비활성 전략이 UI에 나타남 (우선순위 🟢)

**문제**:
- `is_active = 0`인 전략이 드롭다운에 나타남
- Test Always Buy (ID: 5)가 비활성 상태임에도 표시됨

**상태**: ✅ **해결됨** - 이전 세션에서

**적용된 해결 방법**:
- [strategy.py](backend/src/api/strategy.py): `.where(Strategy.is_active == True)` 추가
- [ai_strategy.py](backend/src/api/ai_strategy.py): `.where(Strategy.is_active == True)` 추가

---

## 🎯 다음 우선순위 작업

### 우선순위 1: 백테스트 지표 계산 및 저장 🔴
- **파일**: [backtest.py](backend/src/api/backtest.py)
- **영향**: 높음 - 사용자가 지표 없이 전략 성능을 평가할 수 없음
- **예상 시간**: 1시간
- **참조**: "주의가 필요한 중요 문제" → 문제 #1

### 우선순위 2: 실전 거래를 위한 과거 캔들 로드 🔴
- **파일**: [bot_runner.py](backend/src/services/bot_runner.py)
- **영향**: 중요 - 실전 거래 정확도 및 사용자 수익/손실에 영향
- **예상 시간**: 2시간
- **참조**: "주의가 필요한 중요 문제" → 문제 #2

### 우선순위 3: Mock에서 실제 Bitget 데이터로 전환 🟡
- **파일**: [db.py](backend/src/database/db.py)
- **영향**: 중간 - 현재 가짜 데이터 사용
- **예상 시간**: 5분
- **전제 조건**: 우선순위 1 & 2를 먼저 완료하고 철저히 테스트

### 우선순위 4: 전략 성능 지표 표시 추가 🟢
- **파일**: 프론트엔드 전략 페이지
- **영향**: 낮음 - 사용자 경험을 위한 좋은 기능
- **예상 시간**: 1시간

---

## 🏗️ 전체 사용자 워크플로우 (END-TO-END 작동 필수)

### 1. 사용자 등록 및 로그인 ✅
- **프론트엔드**: [Login.jsx](frontend/src/pages/Login.jsx), [Register.jsx](frontend/src/pages/Register.jsx)
- **백엔드**: [auth.py](backend/src/api/auth.py)
- **상태**: 작동 중
- **테스트**: 계정 생성 → 로그인 → JWT 토큰 수신

### 2. 전략 생성 ✅
- **프론트엔드**: [Strategy.jsx](frontend/src/pages/Strategy.jsx), [StrategyForm.jsx](frontend/src/components/strategy/StrategyForm.jsx)
- **백엔드**: [ai_strategy.py](backend/src/api/ai_strategy.py)
- **상태**: 작동 중
- **테스트**: RSI 전략 생성 → 저장 → 목록에 나타남

### 3. 백테스트 ✅
- **프론트엔드**: [BacktestRunner.jsx](frontend/src/components/strategy/BacktestRunner.jsx)
- **백엔드**: [backtest.py](backend/src/api/backtest.py)
- **상태**: 작동 중 (지표 계산 누락 - 우선순위 1 참조)
- **테스트**: 전략 선택 → 날짜 범위 선택 → 실행 → 결과 확인

### 4. API 키 관리 ✅
- **프론트엔드**: [Settings.jsx](frontend/src/pages/Settings.jsx)
- **백엔드**: [account.py](backend/src/api/account.py)
- **상태**: 작동 중
- **테스트**: Bitget API 키 입력 → 저장 → 데이터베이스에 암호화됨

### 5. 실전 자동매매 ⚠️
- **프론트엔드**: [BotControl.jsx](frontend/src/pages/BotControl.jsx)
- **백엔드**: [bot.py](backend/src/api/bot.py), [bot_runner.py](backend/src/services/bot_runner.py)
- **상태**: 부분적으로 작동 (정확도를 위해 우선순위 2 수정 필요)
- **테스트**: 전략 선택 → 봇 시작 → 거래 모니터링

---

## 🐛 일반적인 오류 및 해결 방법

### 오류 1: `KeyError: 'close'`
**원인**: 시장 데이터가 캔들 형식으로 변환되지 않음
**파일**: [bot_runner.py:130-139](backend/src/services/bot_runner.py#L130-L139)
**해결 방법**: 항상 OHLCV 필드로 캔들 객체 생성
**예방**: 캔들 생성 로직을 절대 수정하지 말 것

### 오류 2: `The margin mode cannot be empty`
**원인**: Bitget API v2 주문에서 `marginMode` 필드 누락
**파일**: [bitget_rest.py:222](backend/src/services/bitget_rest.py#L222)
**해결 방법**: 주문 데이터에 항상 `"marginMode": "crossed"` 포함
**예방**: 이 필드를 제거하지 말 것

### 오류 3: `Parameter verification failed` (Bitget API)
**원인**: Bitget API에 대한 잘못된 매개변수 형식
**일반적인 문제**:
- 심볼 형식: "BTC/USDT"가 아닌 "BTCUSDT" 사용
- 간격 형식: "1h"가 아닌 "1H" (대문자) 사용
- productType 누락: "USDT-FUTURES" 추가

**해결 방법**: 올바른 형식은 [bitget_rest.py:525-589](backend/src/services/bitget_rest.py#L525-L589) 참조

### 오류 4: `SSL: CERTIFICATE_VERIFY_FAILED`
**원인**: macOS Python SSL 인증서가 설치되지 않음
**해결 방법**:
```bash
bash "/Applications/Python 3.11/Install Certificates.command"
```
**재발**: Python 재설치 또는 virtualenv 변경 후

### 오류 5: `object ChunkedIteratorResult can't be used in 'await' expression`
**원인**: 동기 session.execute()에 `await` 사용
**해결 방법**: 세션이 동기인지 비동기인지 확인
- 동기 세션: `session.execute(query)`
- 비동기 세션: `await session.execute(query)`

**파일**: [backtest.py](backend/src/api/backtest.py)는 `get_session()`의 **동기** 세션 사용

### 오류 6: 백테스트에서 전략 드롭다운 비어 있음
**원인**: StrategyList가 BacktestRunner와 데이터를 공유하지 않음
**상태**: ✅ 수정됨 (중요 문제의 문제 #4 참조)

---

## 🔒 보안 고려 사항

### 1. API 키 암호화
- **저장소**: 데이터베이스 `user_accounts` 테이블
- **암호화**: `ENCRYPTION_KEY` 환경 변수를 사용한 AES
- **⚠️ 위험**: `ENCRYPTION_KEY`가 노출되면 모든 API 키가 손상됨
- **권장 사항**:
  - `.env` 파일 사용 (`.gitignore`에 추가)
  - 프로덕션: AWS Secrets Manager 또는 HashiCorp Vault 사용

### 2. JWT 토큰 만료
- **위치**: [jwt_auth.py](backend/src/utils/jwt_auth.py)
- **현재 만료**: 토큰 설정 확인
- **권장 사항**: 합리적인 만료 설정 (1-7일)

### 3. 사용자 데이터 격리
- **중요**: 모든 엔드포인트는 반드시 `user_id`로 필터링해야 함
- **예시**: `session.query(Strategy).filter_by(user_id=user_id)`
- **⚠️ 절대 금지**: user_id 확인 없이 데이터 반환 (데이터 유출!)

### 4. 환경 변수
```bash
# 백엔드 시작 전 항상 설정
export DATABASE_URL="sqlite+aiosqlite:///./trading.db"
export ENCRYPTION_KEY="Dz9w_blEMa-tMD5hqK6V7yiaYecQBdsTaO0PJR3ESn8="
```

---

## 📂 중요 파일 참조

### 백엔드 핵심
| 파일 | 목적 | 주요 함수 |
|------|---------|---------------|
| [bot_runner.py](backend/src/services/bot_runner.py) | 실전 거래 봇 메인 루프 | `_run_loop()`, `_get_user_strategy()` |
| [backtest.py](backend/src/api/backtest.py) | 백테스트 실행 | `start_backtest()`, `_run_backtest_background()` |
| [bitget_rest.py](backend/src/services/bitget_rest.py) | Bitget REST API 클라이언트 | `place_order()`, `get_historical_candles()` |
| [strategy_loader.py](backend/src/services/strategy_loader.py) | DB에서 전략 로드 | `load_strategy()`, `generate_signal_with_strategy()` |
| [db.py](backend/src/database/db.py) | 데이터베이스 및 수명 이벤트 | Mock/실제 데이터 전환 |

### 프론트엔드 핵심
| 파일 | 목적 | 주요 컴포넌트 |
|------|---------|----------------|
| [BotControl.jsx](frontend/src/pages/BotControl.jsx) | 봇 시작/중지 제어 | 전략 선택, 상태 표시 |
| [Strategy.jsx](frontend/src/pages/Strategy.jsx) | 전략 관리 | 목록/폼/백테스트용 탭 컨테이너 |
| [BacktestRunner.jsx](frontend/src/components/strategy/BacktestRunner.jsx) | 백테스트 실행 UI | 날짜 선택기, 결과 표시 |
| [Settings.jsx](frontend/src/pages/Settings.jsx) | API 키 관리 | 키 암호화, 저장 |

### 데이터베이스 스키마
| 테이블 | 목적 | 주요 컬럼 |
|-------|---------|-------------|
| users | 사용자 계정 | id, email, password_hash |
| user_accounts | Bitget API 키 | user_id, api_key (암호화), secret_key (암호화) |
| strategies | 거래 전략 | id, user_id, code, params, is_active |
| bot_status | 봇 실행 상태 | user_id, strategy_id, is_running |
| trades | 거래 내역 | user_id, side, price, quantity, pnl |
| backtest_results | 백테스트 결과 | user_id, strategy_id, final_balance, metrics, status |
| backtest_trades | 백테스트 거래 내역 | result_id, side, entry_price, exit_price, pnl |

---

## 🔧 필수 명령어

### 백엔드 재시작
```bash
# 기존 종료
lsof -ti:8000 | xargs kill -9

# 시작
cd /Users/mr.joo/Desktop/auto-dashboard/backend
export DATABASE_URL="sqlite+aiosqlite:///./trading.db"
export ENCRYPTION_KEY="Dz9w_blEMa-tMD5hqK6V7yiaYecQBdsTaO0PJR3ESn8="
uvicorn src.main:app --reload --port 8000 > /tmp/backend.log 2>&1 &
```

### 프론트엔드 재시작
```bash
# 기존 종료
lsof -ti:3001 | xargs kill -9

# 시작
cd /Users/mr.joo/Desktop/auto-dashboard/frontend
npm start &
```

### 로그 모니터링
```bash
# 백엔드 로그
tail -f /tmp/backend.log

# 오류만 필터링
tail -f /tmp/backend.log | grep -i "error\|exception"

# 백테스트 필터링
tail -f /tmp/backend.log | grep -i "backtest"

# 거래 시그널 필터링
tail -f /tmp/backend.log | grep -i "signal\|buy\|sell"
```

### 데이터베이스 쿼리
```bash
cd /Users/mr.joo/Desktop/auto-dashboard/backend

# 활성 전략 목록
sqlite3 trading.db "SELECT id, name, code, is_active FROM strategies WHERE is_active = 1;"

# 사용자 API 키 확인 (암호화됨)
sqlite3 trading.db "SELECT user_id, api_key, secret_key FROM user_accounts WHERE user_id = 6;"

# 최근 거래 확인
sqlite3 trading.db "SELECT * FROM trades WHERE user_id = 6 ORDER BY created_at DESC LIMIT 10;"

# 봇 상태 확인
sqlite3 trading.db "SELECT user_id, strategy_id, is_running FROM bot_status WHERE user_id = 6;"

# 백테스트 결과 확인
sqlite3 trading.db "SELECT id, pair, timeframe, initial_balance, final_balance, status FROM backtest_results ORDER BY created_at DESC LIMIT 5;"
```

### 백테스트 워크플로우 테스트
```bash
cd /Users/mr.joo/Desktop/auto-dashboard
bash test_backtest_workflow.sh
```

---

## ⛔ 절대 하지 말아야 할 것

### 1. 환경 변수 제거 금지
```bash
# ❌ 잘못됨 - 암호화 오류 발생
uvicorn src.main:app --reload

# ✅ 올바름
export DATABASE_URL="sqlite+aiosqlite:///./trading.db"
export ENCRYPTION_KEY="Dz9w_blEMa-tMD5hqK6V7yiaYecQBdsTaO0PJR3ESn8="
uvicorn src.main:app --reload
```

### 2. 캔들 생성 로직 수정 금지
```python
# ❌ 잘못됨 - KeyError: 'close' 발생
candles = [market]  # OHLCV 구조 누락

# ✅ 올바름
candle = {
    "open": market.get("open", price),
    "high": market.get("high", price),
    "low": market.get("low", price),
    "close": market.get("close", price),
    "volume": market.get("volume", 0),
    "time": market.get("time", 0)
}
candles = [candle]
```

### 3. 주문에서 marginMode 제거 금지
```python
# ❌ 잘못됨 - Bitget API가 거부함
order_data = {
    "symbol": symbol,
    "side": side.value,
    "orderType": order_type.value,
    "size": str(size),
}

# ✅ 올바름
order_data = {
    "symbol": symbol,
    "marginCoin": margin_coin,
    "marginMode": "crossed",  # 필수!
    "side": side.value,
    "orderType": order_type.value,
    "size": str(size),
}
```

### 4. 백업 없이 데이터베이스 삭제 금지
```bash
# ❌ 잘못됨 - 모든 사용자 데이터 손실
rm backend/trading.db

# ✅ 올바름 - 먼저 백업
cp backend/trading.db backend/trading.db.backup.$(date +%Y%m%d)
```

### 5. user_id 필터링 건너뛰기 금지
```python
# ❌ 잘못됨 - 모든 사용자 데이터 반환 (보안 위반!)
strategies = session.query(Strategy).all()

# ✅ 올바름 - 사용자 자신의 데이터만
strategies = session.query(Strategy).filter_by(user_id=user_id).all()
```

### 6. 동기 세션에 await 사용 금지
```python
# ❌ 잘못됨
result = await session.execute(query)  # 세션이 동기인 경우

# ✅ 올바름
result = session.execute(query)  # 동기 세션용
# 또는
result = await session.execute(query)  # 비동기 세션용
```

---

## 📝 다음 AI 에이전트를 위해

**작업 시작 전**:
1. ✅ 이 WORK_LOG.md를 완전히 읽기
2. ✅ "현재 시스템 상태" 확인
3. ✅ "주의가 필요한 중요 문제" 검토
4. ✅ "전체 사용자 워크플로우" 이해
5. ✅ 변경 사항이 영향을 미칠 워크플로우 테스트

**작업 중**:
1. ✅ 점진적으로 변경
2. ✅ 각 변경 후 테스트
3. ✅ 시스템의 다른 부분에 미치는 영향 확인
4. ✅ 백엔드 로그에서 오류 모니터링

**작업 완료 후**:
1. ✅ "현재 시스템 상태" 섹션 업데이트
2. ✅ "다음 우선순위 작업"에서 완료된 항목을 "완료됨" 섹션으로 이동
3. ✅ 새로운 문제를 "중요 문제" 또는 "일반적인 오류"에 추가
4. ✅ 변경 사항의 영향을 받는 전체 사용자 워크플로우 테스트
5. ✅ 이 WORK_LOG.md 업데이트
6. ✅ "중요: 다음 AI 에이전트를 위한 지침" 섹션 유지

**새로운 문제 발견 시**:
1. ✅ 우선순위와 함께 "주의가 필요한 중요 문제"에 추가
2. ✅ 사용자에게 왜 중요한지 설명
3. ✅ 해결 방법 제공
4. ✅ 수정이 필요한 파일 나열

---

**기억하세요**: 이것은 **실제 사용자 자금**을 처리하는 **프로덕션 플랫폼**입니다. 모든 변경 사항은 다음과 같아야 합니다:
- ✅ 철저히 테스트됨
- ✅ 사용자 데이터 격리됨 (보안)
- ✅ 이 로그에 문서화됨
- ✅ End-to-end 검증됨

**최종 업데이트**: 2025-12-03
**최종 수정자**: Claude Sonnet 4.5
**세션**: 5 계속 - 백테스트 구현 완료

---
