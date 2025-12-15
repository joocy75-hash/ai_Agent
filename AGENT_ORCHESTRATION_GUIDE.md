# AI Agent Orchestration System - 통합 가이드

> 완벽한 AI 에이전트 오케스트레이션 시스템 구축 완료!
>
> **작성일**: 2024-12-15
> **버전**: 1.0

---

## 📋 목차

1. [시스템 개요](#시스템-개요)
2. [에이전트 구조](#에이전트-구조)
3. [통합 방법](#통합-방법)
4. [사용 예시](#사용-예시)
5. [커스터마이징](#커스터마이징)
6. [테스트](#테스트)

---

## 시스템 개요

### 🎯 구현된 에이전트

1. **Anomaly Detection Agent** (이상 징후 감지)
   - 봇 동작 이상 감지 (과도한 거래, 연속 손실, 높은 슬리피지, API 오류)
   - 시장 이상 감지 (급등락, 거래량 급증, 펀딩 비율 이상)
   - 서킷 브레이커 (일일 손실 한도)

2. **Portfolio Optimization Agent** (포트폴리오 최적화)
   - 마코위츠 포트폴리오 이론 적용
   - 상관관계 분석 및 분산 효과 측정
   - 자동 리밸런싱 제안

3. **Agent Orchestrator** (에이전트 조율)
   - 이벤트 기반 협업
   - 규칙 엔진
   - Redis Pub/Sub 실시간 통신

### 🏗 아키텍처

```
┌─────────────────────────────────────────────────────────┐
│                  Agent Orchestrator                      │
│  (이벤트 기반 조율 + 규칙 엔진 + 헬스 체크)                 │
└──────────────────┬──────────────────────────────────────┘
                   │
       ┌───────────┼───────────┬─────────────┐
       │           │           │             │
   ┌───▼───┐  ┌───▼────┐  ┌───▼──────┐  ┌──▼──────────┐
   │Market │  │Signal  │  │Risk      │  │Anomaly      │
   │Regime │  │Validator│  │Monitor   │  │Detector     │
   └───────┘  └────────┘  └──────────┘  └─────────────┘

                           ┌──────────────────┐
                           │Portfolio         │
                           │Optimizer         │
                           └──────────────────┘
```

### 🔄 이벤트 플로우

**예시 1: 신호 검증 파이프라인**
```
1. Strategy → SIGNAL_GENERATED 이벤트
2. Orchestrator → SignalValidator 호출
3. Orchestrator → RiskMonitor 호출
4. Orchestrator → 최종 결정 (allow/block)
5. 거래 실행 or 차단
```

**예시 2: 이상 징후 대응**
```
1. AnomalyDetector → ANOMALY_DETECTED 이벤트 (severity=high)
2. Orchestrator → RiskMonitor에게 알림
3. RiskMonitor → 포지션 축소 or 봇 중지
4. Telegram/Email 알림
```

**예시 3: 자동 리밸런싱**
```
1. Scheduler → REBALANCING_DUE 이벤트 (주간)
2. Orchestrator → PortfolioOptimizer 호출
3. PortfolioOptimizer → 최적 할당 계산
4. Orchestrator → SignalValidator 검증
5. DB 업데이트 (allocation_percent)
6. 사용자 알림
```

---

## 에이전트 구조

### 디렉토리 구조

```
backend/src/agents/
├── base.py                           # BaseAgent 클래스
├── models.py                         # 공통 모델
├── redis_client.py                   # Redis 클라이언트
│
├── market_regime/                    # [기존] 시장 환경 분석
│   ├── agent.py
│   └── models.py
│
├── signal_validator/                 # [기존] 신호 검증
│   ├── agent.py
│   └── models.py
│
├── risk_monitor/                     # [기존] 리스크 모니터링
│   ├── agent.py
│   └── models.py
│
├── anomaly_detector/                 # [NEW] 이상 징후 감지
│   ├── __init__.py
│   ├── agent.py
│   └── models.py
│
├── portfolio_optimizer/              # [NEW] 포트폴리오 최적화
│   ├── __init__.py
│   ├── agent.py
│   └── models.py
│
└── orchestrator/                     # [NEW] 오케스트레이터
    ├── __init__.py
    ├── orchestrator.py
    ├── models.py
    └── decision_logic.py             # ⭐ 비즈니스 로직 커스터마이징
```

---

## 통합 방법

### Step 1: 의존성 설치

```bash
# scipy 필요 (마코위츠 최적화)
pip install scipy numpy
```

### Step 2: 에이전트 초기화 (main.py or startup.py)

```python
# backend/src/main.py

from fastapi import FastAPI
from contextlib import asynccontextmanager

# Agent imports
from .agents.market_regime import MarketRegimeAgent
from .agents.signal_validator import SignalValidatorAgent
from .agents.risk_monitor import RiskMonitorAgent
from .agents.anomaly_detector import AnomalyDetectionAgent
from .agents.portfolio_optimizer import PortfolioOptimizationAgent
from .agents.orchestrator import AgentOrchestrator

# Redis client
from .agents.redis_client import get_redis_client

# Global orchestrator instance
orchestrator = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """앱 시작/종료 시 실행"""
    global orchestrator

    # Redis 클라이언트 초기화
    redis_client = await get_redis_client()

    # Orchestrator 초기화
    orchestrator = AgentOrchestrator(redis_client=redis_client)

    # 에이전트 등록
    market_regime = MarketRegimeAgent(
        agent_id="market_regime",
        name="Market Regime Agent",
        config={},
        redis_client=redis_client,
    )
    orchestrator.register_agent("market_regime", market_regime)

    signal_validator = SignalValidatorAgent(
        agent_id="signal_validator",
        name="Signal Validator Agent",
        config={},
        redis_client=redis_client,
    )
    orchestrator.register_agent("signal_validator", signal_validator)

    risk_monitor = RiskMonitorAgent(
        agent_id="risk_monitor",
        name="Risk Monitor Agent",
        config={},
    )
    orchestrator.register_agent("risk_monitor", risk_monitor)

    anomaly_detector = AnomalyDetectionAgent(
        agent_id="anomaly_detector",
        name="Anomaly Detection Agent",
        config={
            "max_trades_per_10min": 20,
            "losing_streak_threshold": 7,
            "max_daily_loss_percent": 10.0,
        },
        redis_client=redis_client,
    )
    orchestrator.register_agent("anomaly_detector", anomaly_detector)

    portfolio_optimizer = PortfolioOptimizationAgent(
        agent_id="portfolio_optimizer",
        name="Portfolio Optimization Agent",
        config={
            "min_allocation_percent": 5.0,
            "max_allocation_percent": 40.0,
        },
        redis_client=redis_client,
    )
    orchestrator.register_agent("portfolio_optimizer", portfolio_optimizer)

    # 백그라운드에서 이벤트 구독 시작
    import asyncio
    asyncio.create_task(orchestrator.subscribe_to_events())

    logger.info("Agent orchestration system initialized")

    yield

    # Cleanup
    logger.info("Shutting down agent orchestration system")


app = FastAPI(lifespan=lifespan)


# Orchestrator 접근용 헬퍼
def get_orchestrator() -> AgentOrchestrator:
    return orchestrator
```

### Step 3: API 라우터 등록

```python
# backend/src/main.py (continued)

from .api import agent_orchestration

app.include_router(agent_orchestration.router)
```

### Step 4: 봇 러너에서 이벤트 발행

```python
# backend/src/services/bot_runner.py

from ..agents.orchestrator.models import OrchestrationEvent, EventType
from ..main import get_orchestrator
import uuid


async def execute_trade_with_validation(bot_instance, signal):
    """신호 검증 파이프라인을 거쳐 거래 실행"""

    orchestrator = get_orchestrator()

    # 이벤트 생성
    event = OrchestrationEvent(
        event_id=f"evt_{uuid.uuid4().hex[:12]}",
        event_type=EventType.SIGNAL_GENERATED,
        source_agent="strategy",
        user_id=bot_instance.user_id,
        bot_instance_id=bot_instance.id,
        data={
            "signal": signal,  # "LONG" or "SHORT"
            "confidence": 0.85,
            "strategy_id": bot_instance.strategy_id,
        },
        priority=3,
    )

    # 이벤트 발행 및 처리
    await orchestrator.publish_event(event)
    result = await orchestrator.handle_event(event)

    # 최종 결정에 따라 거래 실행
    if result.final_decision == "allow":
        logger.info(f"Signal approved, executing trade for bot {bot_instance.id}")
        await trade_executor.execute(bot_instance, signal)

    elif result.final_decision == "adjust_size_50":
        logger.info(f"Signal approved with 50% size reduction")
        await trade_executor.execute(bot_instance, signal, size_multiplier=0.5)

    else:
        logger.info(f"Signal blocked: {result.final_decision}")
```

### Step 5: 주기적 태스크 (이상 징후 감지, 리밸런싱)

```python
# backend/src/services/scheduled_tasks.py

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from ..main import get_orchestrator
from ..agents.orchestrator.models import OrchestrationEvent, EventType
import uuid


scheduler = AsyncIOScheduler()


async def check_anomalies_task():
    """5분마다 모든 봇의 이상 징후 체크"""
    orchestrator = get_orchestrator()
    anomaly_detector = orchestrator._agents.get("anomaly_detector")

    # TODO: DB에서 활성 봇 목록 가져오기
    active_bots = await get_active_bots()

    for bot in active_bots:
        # 봇 메트릭 수집
        metrics = await collect_bot_metrics(bot.id)

        # 이상 징후 감지
        from ..agents.base import AgentTask

        task = AgentTask(
            task_id=f"anomaly_check_{bot.id}",
            task_type="monitor_bot_behavior",
            params={
                "bot_instance_id": bot.id,
                "metrics": metrics,
                "auto_execute": True,
            },
        )

        alerts = await anomaly_detector.process_task(task)

        # 알림이 있으면 이벤트 발행
        for alert in alerts:
            event = OrchestrationEvent(
                event_id=f"evt_{uuid.uuid4().hex[:12]}",
                event_type=EventType.ANOMALY_DETECTED,
                source_agent="anomaly_detector",
                user_id=bot.user_id,
                bot_instance_id=bot.id,
                data={
                    "anomaly_type": alert.anomaly_type.value,
                    "severity": alert.severity.value,
                    "message": alert.message,
                },
                priority=4 if alert.severity.value == "high" else 2,
            )
            await orchestrator.publish_event(event)
            await orchestrator.handle_event(event)


async def weekly_rebalancing_task():
    """주간 리밸런싱 체크"""
    orchestrator = get_orchestrator()

    # TODO: 리밸런싱이 필요한 사용자 조회
    users = await get_users_with_active_bots()

    for user in users:
        event = OrchestrationEvent(
            event_id=f"evt_{uuid.uuid4().hex[:12]}",
            event_type=EventType.REBALANCING_DUE,
            source_agent="scheduler",
            user_id=user.id,
            data={"reason": "weekly_schedule"},
            priority=2,
        )

        await orchestrator.publish_event(event)
        await orchestrator.handle_event(event)


# 스케줄 등록
scheduler.add_job(check_anomalies_task, "interval", minutes=5)
scheduler.add_job(weekly_rebalancing_task, "cron", day_of_week="sun", hour=0)

scheduler.start()
```

---

## 사용 예시

### 예시 1: 프론트엔드에서 포트폴리오 분석 조회

```javascript
// frontend/src/api/agent.js

export const getPortfolioAnalysis = async () => {
  const response = await client.get('/agent/portfolio/analysis');
  return response.data;
};

export const suggestRebalancing = async (riskLevel = 'moderate') => {
  const response = await client.post('/agent/portfolio/rebalancing/suggest', {
    risk_level: riskLevel,
  });
  return response.data;
};

export const applyRebalancing = async () => {
  const response = await client.post('/agent/portfolio/rebalancing/apply');
  return response.data;
};
```

```jsx
// frontend/src/pages/Portfolio.jsx

import { getPortfolioAnalysis, suggestRebalancing, applyRebalancing } from '../api/agent';

const PortfolioPage = () => {
  const [analysis, setAnalysis] = useState(null);
  const [suggestion, setSuggestion] = useState(null);

  useEffect(() => {
    loadAnalysis();
  }, []);

  const loadAnalysis = async () => {
    const data = await getPortfolioAnalysis();
    setAnalysis(data);
  };

  const handleSuggestRebalancing = async (riskLevel) => {
    const data = await suggestRebalancing(riskLevel);
    setSuggestion(data);
  };

  const handleApplyRebalancing = async () => {
    await applyRebalancing();
    message.success('리밸런싱이 적용되었습니다!');
    loadAnalysis();
  };

  return (
    <div>
      <Card title="포트폴리오 분석">
        <Statistic title="샤프 비율" value={analysis?.portfolio_sharpe} />
        <Statistic title="분산 효과" value={analysis?.diversification_ratio} suffix="x" />
      </Card>

      <Card title="리밸런싱 제안">
        <Select onChange={handleSuggestRebalancing}>
          <Option value="conservative">보수적</Option>
          <Option value="moderate">중립적</Option>
          <Option value="aggressive">공격적</Option>
        </Select>

        {suggestion && (
          <>
            <Alert message={`예상 샤프 개선: +${suggestion.expected_sharpe_improvement}%`} />
            <Button onClick={handleApplyRebalancing}>리밸런싱 적용</Button>
          </>
        )}
      </Card>
    </div>
  );
};
```

### 예시 2: 이상 징후 모니터링 대시보드

```jsx
// frontend/src/components/AnomalyMonitor.jsx

import { getAnomalyAlerts } from '../api/agent';
import { useWebSocket } from '../context/WebSocketContext';

const AnomalyMonitor = () => {
  const [alerts, setAlerts] = useState([]);
  const { on } = useWebSocket();

  useEffect(() => {
    loadAlerts();

    // WebSocket으로 실시간 알림 구독
    on('anomaly_alert', (newAlert) => {
      setAlerts(prev => [newAlert, ...prev]);

      // 심각도에 따라 알림
      if (newAlert.severity === 'critical') {
        notification.error({
          message: '긴급 알림',
          description: newAlert.message,
          duration: 0,
        });
      }
    });
  }, []);

  const loadAlerts = async () => {
    const data = await getAnomalyAlerts({ limit: 50 });
    setAlerts(data);
  };

  return (
    <Timeline>
      {alerts.map(alert => (
        <Timeline.Item color={getSeverityColor(alert.severity)}>
          <Tag>{alert.anomaly_type}</Tag>
          <span>{alert.message}</span>
          <div>{alert.recommended_action}</div>
        </Timeline.Item>
      ))}
    </Timeline>
  );
};
```

---

## 커스터마이징

### ⭐ 중요: 비즈니스 로직 커스터마이징

**`backend/src/agents/orchestrator/decision_logic.py`** 파일을 열어서 다음 함수들을 프로젝트 요구사항에 맞게 수정하세요:

1. **`decide_signal_validation()`**
   - 신호 검증 시 최종 승인/거부 결정
   - 임계값: 신뢰도, 리스크 레벨
   - 질문: "신뢰도가 0.7 미만일 때 포지션 크기를 50%로 줄일까요?"

2. **`decide_anomaly_response()`**
   - 이상 징후 타입 및 심각도별 대응 전략
   - 질문: "API 오류율 30% 이상이면 봇을 자동 중지할까요?"

3. **`decide_circuit_breaker()`**
   - 서킷 브레이커 발동 시 대응
   - 질문: "일일 손실 10% 도달 시 모든 포지션을 청산할까요, 아니면 봇만 중지할까요?"

4. **`decide_rebalancing()`**
   - 리밸런싱 적용 조건
   - 질문: "샤프 비율이 5% 미만 개선되면 리밸런싱을 건너뛸까요?"

**예시**:

```python
# decision_logic.py

def decide_signal_validation(self, event, action_results):
    validator_result = action_results.get("signal_validator", {})
    risk_result = action_results.get("risk_monitor", {})

    confidence = validator_result.get("confidence", 0.0)
    risk_level = risk_result.get("risk_level", "safe")

    # 🔧 커스터마이징: 여기서 임계값 조정
    if confidence < 0.60:  # 60% 미만이면 차단
        return "block_low_confidence"

    if risk_level in ["high", "critical"]:  # 리스크 높으면 차단
        return "block_risk"

    if confidence < 0.75:  # 75% 미만이면 절반만 진입
        return "adjust_size_50"

    return "allow"
```

---

## 테스트

### Unit Test

```python
# tests/test_agents/test_anomaly_detector.py

import pytest
from backend.src.agents.anomaly_detector import AnomalyDetectionAgent
from backend.src.agents.base import AgentTask


@pytest.mark.asyncio
async def test_excessive_trading_detection():
    agent = AnomalyDetectionAgent(
        agent_id="test_anomaly",
        name="Test Agent",
        config={"max_trades_per_10min": 20},
    )

    task = AgentTask(
        task_id="test_1",
        task_type="monitor_bot_behavior",
        params={
            "bot_instance_id": 1,
            "metrics": {
                "trades_last_10min": 25,  # 임계값 초과
                "recent_trades_count": 10,
                "losing_trades_count": 3,
                "avg_slippage_percent": 0.1,
                "api_calls_last_5min": 100,
                "api_errors_last_5min": 5,
                "api_error_rate": 0.05,
                "seconds_since_last_activity": 60,
            },
            "auto_execute": False,
        },
    )

    alerts = await agent.process_task(task)

    assert len(alerts) == 1
    assert alerts[0].anomaly_type.value == "excessive_trading"
    assert alerts[0].severity.value == "high"
```

### Integration Test

```python
# tests/test_integration/test_orchestration.py

import pytest
from backend.src.agents.orchestrator import AgentOrchestrator
from backend.src.agents.orchestrator.models import OrchestrationEvent, EventType


@pytest.mark.asyncio
async def test_signal_validation_pipeline():
    orchestrator = AgentOrchestrator()

    # 에이전트 등록 (모의 객체)
    orchestrator.register_agent("signal_validator", MockSignalValidator())
    orchestrator.register_agent("risk_monitor", MockRiskMonitor())

    # 이벤트 생성
    event = OrchestrationEvent(
        event_id="test_evt_1",
        event_type=EventType.SIGNAL_GENERATED,
        source_agent="strategy",
        bot_instance_id=1,
        data={"signal": "LONG", "confidence": 0.85},
        priority=3,
    )

    # 처리
    result = await orchestrator.handle_event(event)

    # 검증
    assert result.success == True
    assert result.final_decision == "allow"
    assert len(result.actions_executed) == 2
```

---

## 다음 단계

1. ✅ **비즈니스 로직 커스터마이징**
   - `decision_logic.py` 수정

2. ✅ **통합 테스트**
   - 각 에이전트 단위 테스트
   - 오케스트레이션 통합 테스트

3. ✅ **프론트엔드 대시보드 추가**
   - 포트폴리오 분석 페이지
   - 이상 징후 모니터 위젯
   - 오케스트레이션 상태 페이지

4. ✅ **프로덕션 배포**
   - 환경 변수 설정
   - Redis 연결 확인
   - 로그 모니터링 설정

---

## 문의

이 시스템에 대한 질문이나 커스터마이징이 필요하시면 언제든 물어보세요!
