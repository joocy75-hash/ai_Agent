# Bot Runner 리팩토링 계획

**최종 업데이트**: 2026-01-12
**현재 상태**: 계획 수립
**대상 파일**: `backend/src/services/bot_runner.py` (~2900줄)

---

## 📊 현재 구조 분석

### 파일 크기 문제
- 현재: ~2900줄 (단일 파일)
- 권장: 파일당 300-500줄
- 목표: 6-8개 모듈로 분리

### 주요 책임 영역

| 영역 | 예상 줄 수 | 분리 대상 | 설명 |
|------|-----------|----------|------|
| 봇 생명주기 관리 | ~400줄 | `bot_lifecycle.py` | start/stop, 태스크 관리, 상태 추적 |
| 포지션 관리 | ~500줄 | `position_manager.py` | 포지션 동기화, 추적, 청산 처리 |
| 주문 실행 | ~400줄 | `order_executor.py` | 시장가 주문, 레버리지 설정, 주문 크기 계산 |
| 시장 데이터 처리 | ~300줄 | `market_data_handler.py` | 캔들 버퍼, 가격 히스토리, 데이터 정규화 |
| 전략 실행 | ~400줄 | `strategy_executor.py` | 전략 로드, 신호 생성, 신호 검증 |
| 리스크 관리 | ~350줄 | `risk_manager.py` | 일일 손실 체크, 포지션 한도, 레버리지 제한 |
| AI 에이전트 통합 | ~350줄 | `agent_coordinator.py` | MarketRegime, SignalValidator, RiskMonitor |
| 알림/로깅 | ~200줄 | `notification_handler.py` | 텔레그램, WebSocket 브로드캐스트 |

### 현재 코드 구조 상세 분석

```
BotRunner 클래스 (~2900줄)
├── __init__ (1-120줄)
│   ├── 태스크 딕셔너리 초기화
│   ├── AI 에이전트 초기화 (MarketRegime, SignalValidator, RiskMonitor)
│   └── 캐시/버퍼 초기화
│
├── 리스크 체크 메서드 (121-350줄)
│   ├── check_daily_loss_limit()
│   ├── check_max_positions()
│   ├── check_leverage_limit()
│   └── get_all_risk_checks()
│
├── 봇 생명주기 메서드 (351-550줄)
│   ├── is_running() / is_instance_running()
│   ├── start() / start_instance()
│   ├── stop() / stop_instance()
│   └── stop_all_user_instances()
│
├── 메인 실행 루프 - 다중 봇 (551-1200줄) ⚠️ 가장 큰 메서드
│   └── _run_instance_loop()
│       ├── 에이전트 시작
│       ├── 봇 인스턴스 로드
│       ├── Bitget 클라이언트 초기화
│       ├── 캔들 버퍼 초기화
│       ├── 포지션 동기화
│       └── 트레이딩 루프 (리스크 체크, 전략 실행, 주문)
│
├── 메인 실행 루프 - 레거시 (1501-2500줄) ⚠️ 중복 코드
│   └── _run_loop()
│       └── (다중 봇과 유사한 구조)
│
├── 헬퍼 메서드 (2501-2700줄)
│   ├── _get_user_strategy()
│   ├── _get_bot_instance()
│   ├── _get_strategy_by_id()
│   ├── _init_exchange_client()
│   ├── _init_bitget_client()
│   └── _update_bot_instance_error()
│
├── 거래 기록 메서드 (2701-2800줄)
│   ├── _record_entry_trade()
│   ├── _record_instance_entry_trade()
│   ├── _update_trade_exit()
│   ├── _generate_exit_tag()
│   └── _map_to_exit_reason()
│
├── 포지션 청산 메서드 (2801-2850줄)
│   ├── _close_instance_position()
│   └── _close_position() (레거시)
│
├── 알림 메서드 (2851-2900줄)
│   ├── _send_instance_trade_notification()
│   └── _send_instance_close_notification()
│
└── 주기적 에이전트 태스크 (별도 섹션)
    ├── _start_periodic_agents()
    ├── _periodic_market_regime_analysis()
    └── _periodic_risk_monitoring()
```

### 코드 중복 분석

| 중복 영역 | 위치 | 중복률 |
|----------|------|--------|
| `_run_loop` vs `_run_instance_loop` | 1501-2500줄 vs 551-1200줄 | ~70% |
| 포지션 동기화 로직 | 두 루프 모두 | ~90% |
| 캔들 버퍼 초기화 | 두 루프 모두 | ~95% |
| 주문 실행 로직 | 두 루프 모두 | ~80% |
| 텔레그램 알림 | 여러 위치에 분산 | ~60% |

---

## 🎯 리팩토링 목표

1. **단일 책임 원칙 (SRP)**: 각 모듈이 하나의 책임만 담당
2. **테스트 용이성**: 모듈별 독립 테스트 가능
3. **유지보수성**: 변경 영향 범위 최소화
4. **재사용성**: 공통 로직 추출
5. **코드 중복 제거**: `_run_loop`와 `_run_instance_loop` 통합

---

## 📁 제안 구조

```
backend/src/services/bot/
├── __init__.py              # 패키지 초기화 + BotRunner 재export
├── runner.py                # 메인 봇 러너 (축소된 버전, ~300줄)
├── lifecycle.py             # 봇 시작/중지/재시작 (~200줄)
├── position_manager.py      # 포지션 동기화/관리/청산 (~400줄)
├── order_executor.py        # 주문 생성/실행/취소 (~300줄)
├── market_data.py           # 시장 데이터 수집/처리/캔들 버퍼 (~250줄)
├── strategy_executor.py     # 전략 신호 생성/처리 (~300줄)
├── risk_manager.py          # 리스크 체크/손절/익절/한도 (~300줄)
├── agent_coordinator.py     # AI 에이전트 통합 (~300줄)
├── notification.py          # 텔레그램/WebSocket 알림 (~200줄)
└── trade_recorder.py        # 거래 기록 저장/업데이트 (~200줄)
```

### 모듈별 상세 설계

#### 1. `runner.py` - 메인 봇 러너 (축소)
```python
class BotRunner:
    """메인 봇 러너 - 다른 모듈 조율"""
    def __init__(self, market_queue):
        self.lifecycle = BotLifecycle()
        self.position_mgr = PositionManager()
        self.order_exec = OrderExecutor()
        self.risk_mgr = RiskManager()
        self.agent_coord = AgentCoordinator()
        # ...

    async def start_instance(self, ...):
        """봇 인스턴스 시작 - lifecycle에 위임"""
        return await self.lifecycle.start_instance(...)
```

#### 2. `lifecycle.py` - 봇 생명주기
```python
class BotLifecycle:
    """봇 시작/중지/상태 관리"""
    def __init__(self):
        self.tasks: Dict[int, asyncio.Task] = {}
        self.instance_tasks: Dict[int, asyncio.Task] = {}
        self.user_bots: Dict[int, Set[int]] = {}

    def is_running(self, user_id: int) -> bool: ...
    def is_instance_running(self, bot_instance_id: int) -> bool: ...
    async def start(self, session_factory, user_id: int): ...
    async def start_instance(self, session_factory, bot_instance_id: int, user_id: int): ...
    def stop(self, user_id: int): ...
    def stop_instance(self, bot_instance_id: int, user_id: int): ...
```

#### 3. `position_manager.py` - 포지션 관리
```python
class PositionManager:
    """포지션 동기화, 추적, 청산"""

    async def sync_position_from_exchange(
        self, bitget_client, symbol: str, candle_buffer: deque
    ) -> Optional[dict]: ...

    async def close_position(
        self, session, bitget_client, position: dict, price: float, reason: str
    ) -> tuple[float, float]: ...  # (pnl_usdt, pnl_percent)

    def calculate_pnl(
        self, position: dict, current_price: float
    ) -> tuple[float, float]: ...
```

#### 4. `risk_manager.py` - 리스크 관리
```python
class RiskManager:
    """리스크 체크 및 제한"""

    async def check_daily_loss_limit(
        self, session, user_id: int
    ) -> tuple[bool, Optional[float], Optional[float]]: ...

    async def check_max_positions(
        self, session, user_id: int, bitget_client
    ) -> tuple[bool, int, Optional[int]]: ...

    async def check_leverage_limit(
        self, session, user_id: int, requested_leverage: int
    ) -> tuple[bool, int, Optional[int]]: ...

    async def get_all_risk_checks(
        self, session, user_id: int, bitget_client, requested_leverage: int
    ) -> dict: ...
```

#### 5. `agent_coordinator.py` - AI 에이전트 통합
```python
class AgentCoordinator:
    """AI 에이전트 관리 및 조율"""

    def __init__(self):
        self.market_regime = MarketRegimeAgent(...)
        self.signal_validator = SignalValidatorAgent(...)
        self.risk_monitor = RiskMonitorAgent(...)
        self._periodic_tasks: Dict[str, asyncio.Task] = {}

    async def start_agents(self): ...
    async def stop_agents(self): ...
    async def validate_signal(self, signal_data: dict) -> ValidationResult: ...
    async def get_market_regime(self, symbol: str) -> MarketRegime: ...
    async def monitor_position_risk(self, position: dict) -> list: ...
```

---

## 🔄 마이그레이션 단계

### Phase 1: 준비 (1일)
- [ ] 현재 코드 완전 백업
- [ ] 테스트 커버리지 확인 (현재 ~23%)
- [ ] 의존성 그래프 작성
- [ ] `backend/src/services/bot/` 디렉토리 생성

### Phase 2: 독립 모듈 추출 (3-4일)

#### Day 1: 리스크 관리 추출
- [ ] `risk_manager.py` 생성
- [ ] `check_daily_loss_limit`, `check_max_positions`, `check_leverage_limit` 이동
- [ ] 단위 테스트 작성
- [ ] 기존 코드에서 import 변경

#### Day 2: 포지션 관리 추출
- [ ] `position_manager.py` 생성
- [ ] 포지션 동기화 로직 이동 (627-670줄 주의!)
- [ ] 포지션 청산 로직 이동
- [ ] PnL 계산 로직 이동
- [ ] 단위 테스트 작성

#### Day 3: 주문 실행 추출
- [ ] `order_executor.py` 생성
- [ ] 주문 크기 계산 로직 이동
- [ ] 레버리지 설정 로직 이동
- [ ] 시장가 주문 실행 로직 이동
- [ ] 단위 테스트 작성

#### Day 4: AI 에이전트 추출
- [ ] `agent_coordinator.py` 생성
- [ ] 에이전트 초기화 로직 이동
- [ ] 주기적 태스크 로직 이동
- [ ] 신호 검증 로직 이동
- [ ] 단위 테스트 작성

### Phase 3: 통합 및 정리 (2일)

#### Day 5: 메인 러너 리팩토링
- [ ] `runner.py` 생성 (축소된 버전)
- [ ] `_run_loop`와 `_run_instance_loop` 통합
- [ ] 새 모듈 import 구조 설정
- [ ] `lifecycle.py` 생성

#### Day 6: 보조 모듈 추출
- [ ] `notification.py` 생성
- [ ] `trade_recorder.py` 생성
- [ ] `market_data.py` 생성
- [ ] `__init__.py` 설정 (하위 호환성)

### Phase 4: 검증 (2일)

#### Day 7: 테스트
- [ ] 단위 테스트 실행
- [ ] 통합 테스트 실행
- [ ] 기존 API 호환성 테스트

#### Day 8: 배포
- [ ] 스테이징 환경 테스트
- [ ] 프로덕션 배포
- [ ] 모니터링

---

## ⚠️ 주의사항

### 절대 변경 금지 영역 (Critical Sections)

```python
# 1. 포지션 동기화 로직 (627-670줄 근처)
# ⚠️ 이 로직은 Bitget API 응답 구조에 의존
# 변경 시 실제 포지션과 불일치 발생 가능
positions = await bitget_client.get_positions()
for pos in positions:
    pos_symbol = pos.get("symbol", "").replace("/", "").replace("-", "").upper()
    # ... 동기화 로직 ...

# 2. AI 에이전트 초기화 순서
# ⚠️ MarketRegime → SignalValidator → RiskMonitor 순서 유지
if self.market_regime.state != AgentState.RUNNING:
    await self.market_regime.start()
# ...

# 3. current_position 데이터 구조
# ⚠️ 다른 컴포넌트에서 이 구조에 의존
current_position = {
    "side": "long" | "short",
    "entry_price": float,
    "size": float,
    "symbol": str,
    "trade_id": int,
    "leverage": int,
    "position_value": float,  # 다중 봇 전용
}

# 4. signal_result 데이터 구조
# ⚠️ 전략 코드에서 반환하는 구조
signal_result = {
    "action": "buy" | "sell" | "close" | "hold",
    "confidence": float,
    "reason": str,
    "size": Optional[float],
    "size_metadata": Optional[dict],
    "enter_tag": Optional[str],
}
```

### 호환성 유지 필수 사항

```python
# backend/src/services/bot/__init__.py
from .runner import BotRunner

# 기존 import 경로 유지
# from src.services.bot_runner import BotRunner  # 기존
# from src.services.bot import BotRunner         # 신규 (동일하게 동작)

__all__ = ["BotRunner"]
```

```python
# backend/src/services/bot_runner.py (레거시 호환)
# 기존 파일은 새 모듈로 리다이렉트
from .bot import BotRunner

__all__ = ["BotRunner"]
```

### API 엔드포인트 변경 없음
- `POST /api/bot/start` - 변경 없음
- `POST /api/bot/stop` - 변경 없음
- `GET /api/bot/status` - 변경 없음
- `POST /api/bot/instance/start` - 변경 없음
- `POST /api/bot/instance/stop` - 변경 없음

---

## 📈 예상 효과

| 메트릭 | 현재 | 목표 | 개선율 |
|--------|------|------|--------|
| 파일 크기 | 2900줄 | 200-400줄/파일 | 85%↓ |
| 테스트 커버리지 | ~23% | 70%+ | 200%↑ |
| 코드 중복 | ~30% | <5% | 83%↓ |
| 변경 영향 범위 | 전체 파일 | 모듈 단위 | 90%↓ |
| 새 기능 추가 시간 | 높음 | 낮음 | 50%↓ |

### 구체적 개선 사항

1. **테스트 용이성**
   - 현재: 2900줄 파일 전체를 모킹해야 함
   - 개선: 각 모듈별 독립 테스트 가능

2. **버그 수정 속도**
   - 현재: 관련 코드 찾는데 시간 소요
   - 개선: 모듈별로 명확한 책임 분리

3. **코드 리뷰**
   - 현재: 2900줄 파일 변경 시 리뷰 어려움
   - 개선: 작은 모듈 단위로 리뷰 가능

4. **새 개발자 온보딩**
   - 현재: 전체 파일 이해 필요
   - 개선: 필요한 모듈만 학습

---

## 🚀 실행 우선순위

| 우선순위 | 모듈 | 이유 | 난이도 |
|----------|------|------|--------|
| 1 (높음) | `risk_manager.py` | 가장 독립적, 의존성 없음 | ⭐ |
| 2 (높음) | `position_manager.py` | 명확한 책임, 테스트 중요 | ⭐⭐ |
| 3 (중간) | `order_executor.py` | position_manager 의존 | ⭐⭐ |
| 4 (중간) | `agent_coordinator.py` | AI 에이전트 통합 | ⭐⭐⭐ |
| 5 (중간) | `notification.py` | 여러 곳에서 호출 | ⭐ |
| 6 (낮음) | `trade_recorder.py` | DB 의존성 | ⭐⭐ |
| 7 (낮음) | `market_data.py` | 기존 서비스와 중복 가능 | ⭐ |
| 8 (낮음) | `lifecycle.py` | 마지막에 통합 | ⭐⭐⭐ |

---

## 🔍 의존성 그래프

```
                    ┌─────────────────┐
                    │   BotRunner     │
                    │   (runner.py)   │
                    └────────┬────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│  lifecycle.py │   │ risk_manager  │   │agent_coordin- │
│               │   │     .py       │   │   ator.py     │
└───────┬───────┘   └───────────────┘   └───────────────┘
        │
        ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│position_mana- │◄──│order_executor │   │ notification  │
│   ger.py      │   │     .py       │   │     .py       │
└───────┬───────┘   └───────────────┘   └───────────────┘
        │
        ▼
┌───────────────┐   ┌───────────────┐
│trade_recorder │   │ market_data   │
│     .py       │   │     .py       │
└───────────────┘   └───────────────┘
```

---

## 📝 체크리스트

### 리팩토링 전 확인사항
- [ ] 모든 테스트 통과 확인
- [ ] 프로덕션 봇 상태 확인 (실행 중인 봇 없음)
- [ ] 데이터베이스 백업
- [ ] 롤백 계획 수립

### 리팩토링 후 확인사항
- [ ] 기존 import 경로 동작 확인
- [ ] 봇 시작/중지 정상 동작
- [ ] 포지션 동기화 정상 동작
- [ ] 주문 실행 정상 동작
- [ ] 텔레그램 알림 정상 동작
- [ ] AI 에이전트 정상 동작
- [ ] 리스크 체크 정상 동작

---

**문서 작성자**: Claude Code
**예상 소요 시간**: 1-2주
**위험도**: 중간 (충분한 테스트 필요)
**검토자**: (TBD)
