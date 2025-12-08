# Bitget Futures Grid Bot AI 구현 계획서

## 📋 프로젝트 개요

### 목표
비트겟의 Futures Grid Bot AI 기능을 참고하여 **초보자도 쉽게 사용할 수 있는 AI 자동매매 시스템** 구축

### 핵심 기능
1. **AI 기반 전략 추천**: 현재 시장 상황에 맞는 최적의 그리드 봇 전략 제안 (DeepSeek API 활용)
2. **간단한 설정**: 투자 금액 비율만 입력하면 자동으로 봇 실행
3. **다중 봇 관리**: 여러 개의 봇을 동시에 쉽게 관리
4. **실시간 ROI 표시**: 각 봇의 수익률을 실시간으로 확인
5. **리스크 관리**: 손실 한도, 최대 포지션 수, 레버리지 제한 등

---

## 🔍 현재 시스템 분석

### ✅ 이미 구현된 기능

#### 1. 백엔드 인프라
- ✅ FastAPI 기반 REST API
- ✅ SQLAlchemy ORM (비동기)
- ✅ JWT 인증 시스템
- ✅ WebSocket 실시간 통신
- ✅ Bitget REST API 클라이언트 (`bitget_rest.py`)
  - 주문 실행, 포지션 관리, 계좌 조회
  - 시장가/지정가 주문
  - 레버리지 설정
- ✅ Bitget WebSocket 마켓 데이터 수집 (`bitget_ws_collector.py`)

#### 2. 봇 실행 시스템
- ✅ BotRunner (`bot_runner.py`)
  - 비동기 봇 실행 루프
  - 전략 로딩 및 시그널 생성
  - Bitget 주문 실행
  - 포지션 추적
- ✅ BotManager (`workers/manager.py`)
  - 다중 사용자 봇 관리
  - 봇 시작/정지
- ✅ Strategy Engine
  - 전략 코드 실행
  - 캔들 데이터 분석
  - 매매 시그널 생성

#### 3. 리스크 관리
- ✅ 일일 손실 한도 체크
- ✅ 최대 포지션 개수 제한
- ✅ 레버리지 제한
- ✅ RiskSettings 모델

#### 4. AI 전략 생성
- ✅ DeepSeek API 연동 (`deepseek_service.py`)
- ✅ AI 전략 생성 엔드포인트 (`/ai/strategies/generate`)
- ✅ 전략 목록 조회/삭제

#### 5. 데이터베이스 모델
- ✅ User, ApiKey, Strategy, BotStatus
- ✅ Trade, Position, Equity
- ✅ RiskSettings, SystemAlert

#### 6. 프론트엔드
- ✅ React + Ant Design
- ✅ 전략 관리 페이지
- ✅ 대시보드
- ✅ 실시간 차트 및 거래 내역

---

## 🎯 추가 구현이 필요한 기능

### 1. Grid Bot 전용 모델 추가 ⭐⭐⭐
**현재 문제**: 기존 전략 시스템은 단일 포지션 기반이며, 그리드 봇의 다중 포지션 관리에 최적화되어 있지 않음

**필요한 작업**:
```python
# backend/src/database/models.py

class GridBot(Base):
    """그리드 봇 설정 및 상태 관리"""
    __tablename__ = "grid_bots"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    name = Column(String, nullable=False)  # 봇 이름
    symbol = Column(String, nullable=False)  # BTCUSDT 등

    # 그리드 설정
    grid_type = Column(String, default="arithmetic")  # arithmetic, geometric
    price_range_lower = Column(Float, nullable=False)  # 하단 가격
    price_range_upper = Column(Float, nullable=False)  # 상단 가격
    grid_count = Column(Integer, nullable=False)  # 그리드 개수
    investment_amount = Column(Float, nullable=False)  # 투자 금액 (USDT)
    investment_ratio = Column(Float, nullable=True)  # 계좌 잔고 대비 비율 (%)

    # 레버리지 및 리스크
    leverage = Column(Integer, default=1)
    stop_loss_percent = Column(Float, nullable=True)
    take_profit_percent = Column(Float, nullable=True)

    # 봇 상태
    status = Column(String, default="stopped")  # running, stopped, paused, error
    is_ai_recommended = Column(Boolean, default=False)  # AI 추천 전략 여부

    # 성과 지표
    total_profit = Column(Float, default=0.0)  # 총 수익 (USDT)
    total_profit_percent = Column(Float, default=0.0)  # 총 수익률 (%)
    total_trades = Column(Integer, default=0)  # 총 거래 횟수
    win_rate = Column(Float, default=0.0)  # 승률

    # 타임스탬프
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    stopped_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class GridPosition(Base):
    """그리드 봇의 개별 포지션 관리"""
    __tablename__ = "grid_positions"

    id = Column(Integer, primary_key=True)
    grid_bot_id = Column(Integer, ForeignKey("grid_bots.id"))

    grid_level = Column(Integer, nullable=False)  # 그리드 레벨 (0부터 시작)
    target_price = Column(Float, nullable=False)  # 목표 가격
    order_size = Column(Float, nullable=False)  # 주문 수량

    # 포지션 상태
    status = Column(String, default="pending")  # pending, filled, closed

    # 주문 정보
    buy_order_id = Column(String, nullable=True)  # 매수 주문 ID
    sell_order_id = Column(String, nullable=True)  # 매도 주문 ID
    entry_price = Column(Float, nullable=True)  # 진입 가격
    exit_price = Column(Float, nullable=True)  # 청산 가격

    # 수익
    profit = Column(Float, default=0.0)  # 실현 수익

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

**작업 규모**: 중간 (신규 모델 2개 추가, 마이그레이션 파일 생성)

---

### 2. AI 그리드 전략 추천 시스템 ⭐⭐⭐⭐⭐
**현재 상태**: DeepSeek API 연동은 되어 있으나, 그리드 봇 전용 추천 로직 없음

**필요한 작업**:
```python
# backend/src/services/grid_ai_service.py (신규 파일)

class GridAIService:
    """AI 기반 그리드 봇 전략 추천"""

    async def analyze_market_for_grid(
        self,
        symbol: str,
        timeframe: str = "1h"
    ) -> Dict[str, Any]:
        """
        시장 분석 및 그리드 전략 추천

        Returns:
        {
            "symbol": "BTCUSDT",
            "recommended_strategies": [
                {
                    "name": "BTC Conservative Grid",
                    "price_range_lower": 95000,
                    "price_range_upper": 105000,
                    "grid_count": 20,
                    "leverage": 3,
                    "expected_roi_30d": 12.5,  # 30일 예상 ROI
                    "risk_level": "low",  # low, medium, high
                    "min_investment": 100,  # USDT
                    "description": "현재 시장은 횡보 중입니다. 레버리지 3배로 안정적인 수익을 노립니다."
                },
                {
                    "name": "BTC Aggressive Grid",
                    "price_range_lower": 92000,
                    "price_range_upper": 108000,
                    "grid_count": 50,
                    "leverage": 10,
                    "expected_roi_30d": 45.8,
                    "risk_level": "high",
                    "min_investment": 200,
                    "description": "변동성이 큰 시장에서 높은 수익을 노립니다."
                }
            ],
            "market_analysis": {
                "trend": "sideways",  # uptrend, downtrend, sideways
                "volatility": 0.23,  # 24시간 변동성
                "support_level": 94000,
                "resistance_level": 106000
            }
        }
        """
        pass

    async def calculate_grid_parameters(
        self,
        symbol: str,
        investment_amount: float,
        price_range_lower: float,
        price_range_upper: float,
        grid_count: int,
        leverage: int = 1
    ) -> Dict[str, Any]:
        """
        그리드 파라미터 계산

        Returns:
        {
            "grid_levels": [
                {"level": 0, "price": 95000, "size": 0.01},
                {"level": 1, "price": 95500, "size": 0.01},
                ...
            ],
            "total_required_margin": 150.5,  # USDT
            "estimated_profit_per_grid": 5.2,  # USDT
            "risk_metrics": {
                "max_drawdown": -8.5,  # %
                "liquidation_price": 85000
            }
        }
        """
        pass
```

**DeepSeek 프롬프트 최적화**:
```python
# backend/src/services/deepseek_service.py

def generate_grid_strategies(self, symbol: str, market_data: dict) -> List[dict]:
    """
    그리드 봇 전략 생성 (AI)

    프롬프트:
    "You are a cryptocurrency grid trading expert. Analyze the following market data
    and recommend 3 grid bot strategies (conservative, moderate, aggressive).

    Market Data:
    - Symbol: {symbol}
    - Current Price: {current_price}
    - 24h High: {high_24h}
    - 24h Low: {low_24h}
    - Volatility: {volatility}
    - Trend: {trend}

    For each strategy, provide:
    1. Price range (lower, upper)
    2. Number of grids (10-100)
    3. Leverage (1-20x)
    4. Expected 30-day ROI
    5. Risk level (low/medium/high)
    6. Minimum investment (USDT)
    7. Brief description

    Return as JSON array."
    """
    pass
```

**작업 규모**: 큰 규모 (AI 로직 설계, 시장 분석 알고리즘, DeepSeek 프롬프트 최적화)

---

### 3. Grid Bot 실행 엔진 ⭐⭐⭐⭐⭐
**현재 문제**: 기존 BotRunner는 단일 포지션 기반이며, 그리드 봇의 다중 주문 관리 로직 없음

**필요한 작업**:
```python
# backend/src/services/grid_bot_runner.py (신규 파일)

class GridBotRunner:
    """그리드 봇 실행 엔진"""

    async def start_grid_bot(
        self,
        user_id: int,
        grid_bot_id: int,
        session: AsyncSession
    ):
        """
        그리드 봇 시작

        1. 그리드 레벨 계산
        2. 각 레벨에 매수/매도 지정가 주문 배치
        3. 주문 체결 모니터링
        4. 체결된 주문의 반대 주문 생성 (매수 체결 -> 매도 주문, 매도 체결 -> 매수 주문)
        5. 수익 실현 시 포지션 기록
        """
        pass

    async def _place_grid_orders(
        self,
        grid_bot: GridBot,
        bitget_client: BitgetRestClient
    ):
        """
        모든 그리드 레벨에 초기 주문 배치

        - 현재가 이하: 매수 지정가 주문
        - 현재가 이상: 매도 지정가 주문 (이미 포지션 보유 가정)
        """
        pass

    async def _monitor_and_update(
        self,
        grid_bot: GridBot,
        bitget_client: BitgetRestClient,
        session: AsyncSession
    ):
        """
        주문 체결 모니터링 및 재주문

        - WebSocket으로 주문 체결 이벤트 수신
        - 체결된 주문의 반대 주문 생성
        - 수익 계산 및 기록
        """
        pass

    async def calculate_roi(self, grid_bot_id: int) -> float:
        """30일 APY 계산"""
        pass
```

**작업 규모**: 매우 큰 규모 (핵심 로직, 복잡한 주문 관리, 에러 처리)

---

### 4. 투자 금액 비율 기반 자동 계산 ⭐⭐
**현재 문제**: 사용자가 수동으로 투자 금액을 입력해야 함

**필요한 작업**:
```python
# backend/src/services/account_helper.py (신규 파일)

async def calculate_investment_from_ratio(
    user_id: int,
    ratio_percent: float,
    bitget_client: BitgetRestClient
) -> float:
    """
    계좌 잔고 대비 투자 금액 계산

    Args:
        ratio_percent: 투자 비율 (예: 10 = 잔고의 10%)

    Returns:
        투자 금액 (USDT)
    """
    account_info = await bitget_client.get_account_info()
    available_balance = float(account_info.get("available", 0))
    investment_amount = available_balance * (ratio_percent / 100)
    return investment_amount
```

**작업 규모**: 작은 규모 (간단한 계산 로직)

---

### 5. 다중 봇 관리 UI ⭐⭐⭐⭐
**현재 상태**: 전략 관리 UI는 있으나, 그리드 봇 전용 UI 없음

**필요한 작업**:
```jsx
// frontend/src/pages/FuturesGridBot.jsx (신규 파일)

export default function FuturesGridBot() {
  return (
    <div>
      {/* 상단: AI 추천 전략 카드 (이미지처럼) */}
      <div className="ai-recommendations">
        <Tabs defaultActiveKey="ai">
          <TabPane tab="AI" key="ai">
            {/* AI 추천 전략 목록 */}
            {strategies.map(strategy => (
              <Card>
                <div className="strategy-header">
                  <h3>{strategy.symbol}</h3>
                  <Tag color={strategy.risk === 'low' ? 'green' : 'red'}>
                    {strategy.leverage}X
                  </Tag>
                </div>

                {/* ROI 차트 */}
                <div className="roi-display">
                  <span className="roi-value">{strategy.expected_roi}%</span>
                  <span className="period">30-day APY</span>
                  <LineChart data={strategy.roi_curve} />
                </div>

                {/* 투자 정보 */}
                <div className="investment-info">
                  <p>Min investment: {strategy.min_investment} USDT</p>
                  <p>Recommended duration: {strategy.duration}</p>
                  <p>Users: {strategy.users}</p>
                </div>

                {/* 사용 버튼 */}
                <Button type="primary" onClick={() => handleUse(strategy)}>
                  Use
                </Button>
              </Card>
            ))}
          </TabPane>

          <TabPane tab="Manual" key="manual">
            {/* 수동 설정 폼 */}
          </TabPane>
        </Tabs>
      </div>

      {/* 하단: 실행 중인 봇 목록 */}
      <div className="running-bots">
        <h2>My Grid Bots</h2>
        <Table dataSource={runningBots} columns={[
          { title: 'Symbol', dataIndex: 'symbol' },
          { title: 'ROI', dataIndex: 'roi', render: (roi) => <span className="roi-green">+{roi}%</span> },
          { title: 'Investment', dataIndex: 'investment' },
          { title: 'Status', dataIndex: 'status' },
          { title: 'Actions', render: (bot) => (
            <>
              <Button onClick={() => handleStop(bot)}>Stop</Button>
              <Button onClick={() => handleEdit(bot)}>Edit</Button>
            </>
          )}
        ]} />
      </div>
    </div>
  );
}
```

**작업 규모**: 큰 규모 (UI 디자인, API 연동, 실시간 데이터 업데이트)

---

### 6. API 엔드포인트 추가 ⭐⭐⭐
```python
# backend/src/api/grid_bot.py (신규 파일)

router = APIRouter(prefix="/grid-bot", tags=["grid-bot"])

@router.post("/analyze")
async def analyze_market_for_grid(
    symbol: str,
    user_id: int = Depends(get_current_user_id)
):
    """AI 기반 그리드 전략 추천"""
    pass

@router.post("/create")
async def create_grid_bot(
    payload: GridBotCreate,
    user_id: int = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session)
):
    """그리드 봇 생성 (투자 비율 기반)"""
    pass

@router.post("/{bot_id}/start")
async def start_grid_bot(
    bot_id: int,
    user_id: int = Depends(get_current_user_id)
):
    """그리드 봇 시작"""
    pass

@router.post("/{bot_id}/stop")
async def stop_grid_bot(
    bot_id: int,
    user_id: int = Depends(get_current_user_id)
):
    """그리드 봇 정지"""
    pass

@router.get("/list")
async def list_grid_bots(
    user_id: int = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session)
):
    """사용자의 모든 그리드 봇 조회"""
    pass

@router.get("/{bot_id}/performance")
async def get_grid_bot_performance(
    bot_id: int,
    user_id: int = Depends(get_current_user_id)
):
    """그리드 봇 성과 조회 (ROI, 거래 내역 등)"""
    pass
```

**작업 규모**: 중간 (6개 엔드포인트 추가, 인증/권한 검증)

---

## 💰 AI API 비용 최적화

### 현재 DeepSeek API 사용량
- **모델**: `deepseek-chat`
- **가격**: 매우 저렴 (GPT-4 대비 1/10 이하)
- **Rate Limit**: 현재 시간당 5회로 제한됨

### 비용 절감 전략
1. **캐싱**: 동일 심볼/타임프레임의 전략 추천은 1시간 동안 캐싱
2. **배치 처리**: 한 번의 API 호출로 3개 전략 생성
3. **사전 생성**: 인기 코인(BTC, ETH 등)의 전략은 매 1시간마다 자동 생성하여 DB 저장
4. **Rate Limit 유지**: 시간당 5회 제한으로 충분 (대부분 사용자는 캐시된 전략 사용)

**예상 월간 API 비용**: $5 이하 (사용자 100명 기준)

---

## 📊 작업 규모 평가

### 총 작업 항목: 6개

| 번호 | 작업 항목 | 규모 | 예상 시간 | 우선순위 |
|------|----------|------|-----------|----------|
| 1 | Grid Bot 모델 추가 | 중간 | 4시간 | ⭐⭐⭐ |
| 2 | AI 그리드 전략 추천 | 큰 | 12시간 | ⭐⭐⭐⭐⭐ |
| 3 | Grid Bot 실행 엔진 | 매우 큰 | 20시간 | ⭐⭐⭐⭐⭐ |
| 4 | 투자 비율 계산 | 작은 | 2시간 | ⭐⭐ |
| 5 | 다중 봇 관리 UI | 큰 | 16시간 | ⭐⭐⭐⭐ |
| 6 | API 엔드포인트 | 중간 | 6시간 | ⭐⭐⭐ |

**총 예상 시간**: 약 60시간 (1-2주 풀타임 작업)

---

## 🚦 구현 가능 여부 판단

### ✅ 구현 가능
현재 백엔드 구조는 **그리드 봇 기능을 추가하기에 매우 적합**합니다:

1. **Bitget API 클라이언트 완비**: 주문, 포지션 관리, 계좌 조회 모두 지원
2. **비동기 처리**: 다중 봇 동시 실행 가능
3. **AI 연동 준비**: DeepSeek API 이미 연동됨
4. **리스크 관리 시스템**: 손실 한도, 레버리지 제한 이미 구현
5. **WebSocket**: 실시간 데이터 수집 및 브로드캐스팅 가능

### ⚠️ 주의사항
1. **복잡도 증가**: 그리드 봇 로직은 기존 단일 포지션 전략보다 복잡
2. **테스트 필요**: 실제 거래 전 충분한 백테스트 및 모의 거래 필요
3. **에러 처리**: 주문 실패, 네트워크 오류 등 다양한 예외 상황 처리 필요
4. **성능 최적화**: 수십 개의 주문을 동시에 관리하므로 DB 쿼리 최적화 필요

---

## 📝 단계별 구현 계획

### Phase 1: 기본 인프라 (4-6시간)
1. Grid Bot 모델 추가 (`GridBot`, `GridPosition`)
2. Alembic 마이그레이션 생성 및 실행
3. 투자 비율 계산 헬퍼 함수

### Phase 2: AI 추천 시스템 (10-12시간)
1. 시장 분석 로직 (변동성, 트렌드 계산)
2. DeepSeek 프롬프트 최적화
3. 그리드 파라미터 계산 알고리즘
4. 캐싱 시스템 구축

### Phase 3: Grid Bot 엔진 (18-20시간)
1. GridBotRunner 기본 구조
2. 그리드 주문 배치 로직
3. 주문 체결 모니터링
4. 자동 재주문 시스템
5. 수익 계산 및 기록

### Phase 4: API 및 UI (12-16시간)
1. API 엔드포인트 6개 구현
2. 프론트엔드 페이지 제작
3. 실시간 ROI 업데이트
4. 다중 봇 관리 UI

### Phase 5: 테스트 및 최적화 (6-8시간)
1. 단위 테스트
2. 통합 테스트
3. 모의 거래 테스트
4. 성능 최적화

---

## 🎯 최종 결론

### ✅ 구현 가능: 예
현재 백엔드 구조는 그리드 봇 기능을 추가하기에 **매우 적합**하며, 대부분의 인프라가 이미 갖춰져 있습니다.

### 📈 작업 규모: 중대형 (60시간)
새로운 모델, 복잡한 주문 관리 로직, AI 통합, UI 제작 등이 필요하지만, 기존 코드베이스를 최대한 활용하여 **효율적으로 구현 가능**합니다.

### 💡 추천 접근 방식
1. **단계별 개발**: Phase 1부터 순차적으로 진행
2. **MVP 먼저**: 핵심 기능(AI 추천, 봇 실행)을 먼저 구현하고 점진적으로 개선
3. **기존 코드 재사용**: BotRunner, BitgetRestClient 등을 최대한 활용
4. **테스트 우선**: 실제 거래 전 충분한 백테스트

### 🚀 다음 단계
작업을 진행하시겠습니까? 원하시면 Phase 1부터 단계별로 구현을 시작할 수 있습니다.
