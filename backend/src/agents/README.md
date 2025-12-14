# 에이전트 시스템 (Agent System)

자율 실행 에이전트를 위한 비동기 프레임워크입니다.

## 📁 디렉토리 구조

```
backend/src/agents/
├── __init__.py          # 모듈 진입점
├── base.py              # 에이전트 베이스 클래스
├── config.py            # 에이전트 설정
├── models.py            # 데이터베이스 모델
├── redis_client.py      # Redis 클라이언트
├── example.py           # 사용 예제
└── README.md            # 문서 (이 파일)
```

## 🚀 주요 기능

### 1. BaseAgent - 에이전트 베이스 클래스

모든 에이전트가 상속받아야 하는 추상 베이스 클래스입니다.

**주요 기능:**
- ✅ 비동기 작업 실행 (asyncio 기반)
- ✅ 상태 관리 (IDLE → RUNNING → PAUSED/ERROR → STOPPED)
- ✅ 작업 큐 관리 (asyncio.Queue)
- ✅ 에러 핸들링 및 자동 재시도
- ✅ 성능 메트릭 수집
- ✅ Graceful shutdown

**사용 예:**

```python
from agents import BaseAgent, AgentTask, TaskPriority

class MyAgent(BaseAgent):
    async def process_task(self, task: AgentTask):
        # 작업 처리 로직 구현
        result = await do_something(task.params)
        return result

# 에이전트 생성 및 시작
agent = MyAgent(agent_id="my_agent_1", name="My Agent")
await agent.start()

# 작업 제출
task = AgentTask(
    task_id="task_1",
    task_type="analyze",
    priority=TaskPriority.HIGH,
    params={"symbol": "BTCUSDT"}
)
await agent.submit_task(task)

# 상태 확인
status = agent.get_status()
print(status)

# 에이전트 중지
await agent.stop()
```

### 2. AgentTask - 작업 정의

에이전트가 처리할 작업을 정의합니다.

**필드:**
- `task_id`: 작업 고유 ID
- `task_type`: 작업 타입 (예: "analyze", "generate_signal")
- `priority`: 우선순위 (LOW, NORMAL, HIGH, CRITICAL)
- `params`: 작업 파라미터 (dict)
- `retry_count`: 재시도 횟수
- `max_retries`: 최대 재시도 횟수 (기본: 3)
- `timeout`: 작업 타임아웃 (초)

### 3. AgentState - 상태 관리

에이전트의 현재 상태를 나타냅니다.

**상태:**
- `IDLE`: 유휴 상태 (작업 대기 중)
- `RUNNING`: 실행 중
- `PAUSED`: 일시 정지
- `ERROR`: 에러 발생
- `STOPPED`: 중지됨

### 4. RedisClient - 에이전트 간 통신

에이전트 간 데이터 공유 및 메시징을 위한 Redis 클라이언트입니다.

**주요 기능:**
- ✅ 키-값 저장/조회 (자동 JSON 직렬화)
- ✅ 해시맵 관리
- ✅ Pub/Sub 메시징
- ✅ TTL 관리

**사용 예:**

```python
from agents.redis_client import get_redis_client

# Redis 클라이언트 가져오기
redis = await get_redis_client()

# 데이터 저장 (TTL 60초)
await redis.set("key", {"value": 123}, ttl=60)

# 데이터 조회
value = await redis.get("key")

# Pub/Sub 메시징
await redis.publish("market_updates", {"symbol": "BTCUSDT", "price": 50000})
```

### 5. 데이터베이스 모델

에이전트 시스템의 데이터베이스 모델입니다.

**모델:**
- `AgentInstance`: 에이전트 인스턴스 정보
- `AgentTaskLog`: 작업 실행 로그
- `AgentEvent`: 시스템 이벤트 로그
- `AgentMetric`: 성능 메트릭 (시계열)
- `AgentCommunication`: 에이전트 간 통신 로그
- `AgentSchedule`: 주기적 작업 스케줄

## 📝 예제 실행

```bash
# 백엔드 디렉토리로 이동
cd /Users/mr.joo/Desktop/auto-dashboard/backend

# 예제 실행
python -m src.agents.example
```

## 🔧 환경 변수 설정

에이전트 시스템은 다음 환경 변수를 통해 설정할 수 있습니다:

```bash
# 에이전트 시스템 활성화 여부
AGENT_ENABLED=true

# 최대 워커 수
AGENT_MAX_WORKERS=4

# 작업 타임아웃 (초)
AGENT_TASK_TIMEOUT=300

# 큐 최대 크기
AGENT_QUEUE_SIZE=1000

# Redis 설정
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=your_password

# 로깅 설정
AGENT_LOG_LEVEL=INFO
AGENT_LOG_TO_FILE=false
AGENT_LOG_FILE=logs/agents.log
```

## 🏗️ 에이전트 구현 가이드

### 1. 에이전트 클래스 생성

```python
from agents import BaseAgent, AgentTask
import logging

logger = logging.getLogger(__name__)

class MarketAnalyzerAgent(BaseAgent):
    """시장 분석 에이전트"""

    async def process_task(self, task: AgentTask):
        """
        작업 처리 (반드시 구현 필요)

        Args:
            task: 처리할 작업

        Returns:
            작업 결과
        """
        task_type = task.task_type
        params = task.params

        if task_type == "analyze_price":
            return await self._analyze_price(params)
        elif task_type == "analyze_volume":
            return await self._analyze_volume(params)
        else:
            raise ValueError(f"Unknown task type: {task_type}")

    async def _analyze_price(self, params: dict) -> dict:
        """가격 분석 로직"""
        symbol = params.get("symbol")
        # 분석 로직 구현
        return {"symbol": symbol, "signal": "buy"}

    async def _analyze_volume(self, params: dict) -> dict:
        """거래량 분석 로직"""
        # 분석 로직 구현
        return {"volume_trend": "increasing"}
```

### 2. 에이전트 시작 및 작업 제출

```python
import asyncio
from agents import AgentTask, TaskPriority

async def main():
    # 에이전트 생성
    agent = MarketAnalyzerAgent(
        agent_id="analyzer_1",
        name="Market Analyzer",
        config={"interval": 60}
    )

    # 에이전트 시작
    await agent.start()

    # 작업 제출
    task = AgentTask(
        task_id="task_1",
        task_type="analyze_price",
        priority=TaskPriority.HIGH,
        params={"symbol": "BTCUSDT", "price": 50000}
    )
    await agent.submit_task(task)

    # 작업 처리 대기
    await asyncio.sleep(5)

    # 상태 확인
    status = agent.get_status()
    print(f"Completed tasks: {status['metrics']['completed_tasks']}")

    # 에이전트 중지
    await agent.stop()

if __name__ == "__main__":
    asyncio.run(main())
```

## 🔄 에이전트 생명주기

```
1. 초기화 (IDLE)
   ↓
2. start() 호출
   ↓
3. 실행 중 (RUNNING)
   - 작업 큐에서 작업 가져오기
   - process_task() 호출
   - 메트릭 수집
   ↓
4. pause() / resume() (PAUSED ↔ RUNNING)
   ↓
5. stop() 호출 또는 에러 발생
   ↓
6. 중지됨 (STOPPED / ERROR)
```

## 📊 메트릭 모니터링

에이전트는 자동으로 다음 메트릭을 수집합니다:

- `total_tasks`: 총 작업 수
- `completed_tasks`: 완료된 작업 수
- `failed_tasks`: 실패한 작업 수
- `success_rate`: 성공률 (%)
- `avg_task_duration`: 평균 작업 시간 (초)
- `error_count`: 에러 발생 횟수
- `uptime_seconds`: 가동 시간 (초)

```python
status = agent.get_status()
metrics = status['metrics']

print(f"Success Rate: {metrics['success_rate']:.2f}%")
print(f"Avg Duration: {metrics['avg_task_duration']:.2f}s")
```

## 🐛 에러 핸들링

에이전트는 다음과 같은 에러 핸들링 기능을 제공합니다:

1. **자동 재시도**: 작업 실패 시 최대 3번까지 자동 재시도
2. **타임아웃 처리**: 작업이 지정된 시간 내에 완료되지 않으면 취소
3. **연속 에러 감지**: 10회 연속 에러 발생 시 에이전트 ERROR 상태로 전환
4. **Graceful Shutdown**: stop() 호출 시 실행 중인 작업 완료 후 종료

## 📚 추가 리소스

- [AGENT_SYSTEM_WORK_PLAN.md](../../../AGENT_SYSTEM_WORK_PLAN.md) - 전체 시스템 계획
- [example.py](./example.py) - 실제 사용 예제
- [bot_runner.py](../services/bot_runner.py) - 기존 봇 러너 참고

## 🤝 기여 가이드

새로운 에이전트 타입을 추가하려면:

1. `BaseAgent`를 상속받는 클래스 생성
2. `process_task()` 메서드 구현
3. `config.py`의 `AgentType` enum에 타입 추가
4. `DEFAULT_AGENT_CONFIGS`에 기본 설정 추가
5. 테스트 작성 및 문서 업데이트

## 📄 라이선스

이 프로젝트의 라이선스를 따릅니다.
