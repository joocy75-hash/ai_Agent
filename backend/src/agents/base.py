"""
에이전트 베이스 클래스 (Agent Base Class)

모든 에이전트의 공통 기능을 정의하는 추상 베이스 클래스
- 상태 관리
- 작업 실행
- 에러 핸들링
- 로깅

관련 문서: AGENT_SYSTEM_WORK_PLAN.md
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional, Set
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


class AgentState(str, Enum):
    """에이전트 상태"""
    IDLE = "idle"  # 유휴 상태
    RUNNING = "running"  # 실행 중
    PAUSED = "paused"  # 일시 정지
    ERROR = "error"  # 에러 발생
    STOPPED = "stopped"  # 중지됨


class TaskPriority(str, Enum):
    """작업 우선순위"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class AgentTask:
    """
    에이전트 작업 (Agent Task)

    에이전트가 처리할 작업 정의
    """
    task_id: str
    task_type: str
    priority: TaskPriority = TaskPriority.NORMAL
    params: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    retry_count: int = 0
    max_retries: int = 3
    timeout: Optional[float] = None  # seconds

    def __post_init__(self):
        """작업 생성 후 검증"""
        if not self.task_id:
            raise ValueError("task_id is required")
        if not self.task_type:
            raise ValueError("task_type is required")

    def can_retry(self) -> bool:
        """재시도 가능 여부"""
        return self.retry_count < self.max_retries

    def increment_retry(self):
        """재시도 횟수 증가"""
        self.retry_count += 1


@dataclass
class AgentMetrics:
    """
    에이전트 메트릭 (Agent Metrics)

    에이전트 성능 및 상태 모니터링용 메트릭
    """
    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    avg_task_duration: float = 0.0
    last_task_at: Optional[datetime] = None
    error_count: int = 0
    last_error_at: Optional[datetime] = None
    uptime_seconds: float = 0.0

    def record_task_completion(self, duration: float, success: bool):
        """작업 완료 기록"""
        self.total_tasks += 1
        if success:
            self.completed_tasks += 1
        else:
            self.failed_tasks += 1

        # 평균 작업 시간 계산 (이동 평균)
        if self.avg_task_duration == 0:
            self.avg_task_duration = duration
        else:
            self.avg_task_duration = (self.avg_task_duration * 0.9) + (duration * 0.1)

        self.last_task_at = datetime.utcnow()

    def record_error(self):
        """에러 기록"""
        self.error_count += 1
        self.last_error_at = datetime.utcnow()

    def get_success_rate(self) -> float:
        """성공률 반환"""
        if self.total_tasks == 0:
            return 0.0
        return (self.completed_tasks / self.total_tasks) * 100


class BaseAgent(ABC):
    """
    에이전트 베이스 클래스 (Base Agent)

    모든 에이전트가 상속받아야 하는 추상 베이스 클래스

    주요 기능:
    - 비동기 작업 실행
    - 상태 관리
    - 에러 핸들링 및 재시도
    - 메트릭 수집
    - Graceful shutdown

    사용 예:
    ```python
    class MyAgent(BaseAgent):
        async def process_task(self, task: AgentTask) -> Any:
            # 작업 처리 로직
            return result
    ```
    """

    def __init__(
        self,
        agent_id: str,
        name: str,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        에이전트 초기화

        Args:
            agent_id: 에이전트 고유 ID
            name: 에이전트 이름
            config: 에이전트 설정
        """
        self.agent_id = agent_id
        self.name = name
        self.config = config or {}

        # 상태 관리
        self.state = AgentState.IDLE
        self._state_lock = asyncio.Lock()

        # 작업 관리
        self.task_queue: asyncio.Queue[AgentTask] = asyncio.Queue()
        self.running_tasks: Set[str] = set()
        self._task_lock = asyncio.Lock()

        # 메트릭
        self.metrics = AgentMetrics()

        # 제어
        self._shutdown_event = asyncio.Event()
        self._main_task: Optional[asyncio.Task] = None
        self._started_at: Optional[datetime] = None

        logger.info(f"Agent '{self.name}' (ID: {self.agent_id}) initialized")

    async def start(self):
        """
        에이전트 시작

        메인 작업 루프를 백그라운드 태스크로 실행
        """
        if self.state != AgentState.IDLE:
            logger.warning(f"Agent '{self.name}' is already running")
            return

        async with self._state_lock:
            self.state = AgentState.RUNNING
            self._started_at = datetime.utcnow()
            self._shutdown_event.clear()

        self._main_task = asyncio.create_task(self._run_loop())
        logger.info(f"✅ Agent '{self.name}' started")

    async def stop(self, timeout: float = 10.0):
        """
        에이전트 중지 (Graceful shutdown)

        Args:
            timeout: 중지 대기 시간 (초)
        """
        if self.state == AgentState.STOPPED:
            logger.warning(f"Agent '{self.name}' is already stopped")
            return

        logger.info(f"Stopping agent '{self.name}'...")

        async with self._state_lock:
            self.state = AgentState.STOPPED
            self._shutdown_event.set()

        # 메인 태스크 종료 대기
        if self._main_task and not self._main_task.done():
            try:
                await asyncio.wait_for(self._main_task, timeout=timeout)
            except asyncio.TimeoutError:
                logger.warning(f"Agent '{self.name}' shutdown timeout, cancelling...")
                self._main_task.cancel()
                try:
                    await self._main_task
                except asyncio.CancelledError:
                    pass

        logger.info(f"✅ Agent '{self.name}' stopped")

    async def pause(self):
        """에이전트 일시 정지"""
        async with self._state_lock:
            if self.state == AgentState.RUNNING:
                self.state = AgentState.PAUSED
                logger.info(f"Agent '{self.name}' paused")

    async def resume(self):
        """에이전트 재개"""
        async with self._state_lock:
            if self.state == AgentState.PAUSED:
                self.state = AgentState.RUNNING
                logger.info(f"Agent '{self.name}' resumed")

    async def submit_task(self, task: AgentTask) -> bool:
        """
        작업 제출

        Args:
            task: 처리할 작업

        Returns:
            성공 여부
        """
        try:
            await self.task_queue.put(task)
            logger.debug(f"Task '{task.task_id}' submitted to agent '{self.name}'")
            return True
        except Exception as e:
            logger.error(f"Failed to submit task '{task.task_id}': {e}")
            return False

    async def _run_loop(self):
        """
        메인 작업 루프

        작업 큐에서 작업을 가져와 처리
        """
        logger.info(f"Agent '{self.name}' main loop started")

        consecutive_errors = 0
        max_consecutive_errors = 10

        try:
            while not self._shutdown_event.is_set():
                # 일시 정지 상태 처리
                while self.state == AgentState.PAUSED:
                    await asyncio.sleep(0.5)

                try:
                    # 작업 가져오기 (타임아웃 1초)
                    try:
                        task = await asyncio.wait_for(
                            self.task_queue.get(),
                            timeout=1.0
                        )
                    except asyncio.TimeoutError:
                        # 타임아웃이면 계속 대기
                        continue

                    # 작업 처리
                    start_time = datetime.utcnow()
                    success = await self._execute_task(task)
                    duration = (datetime.utcnow() - start_time).total_seconds()

                    # 메트릭 기록
                    self.metrics.record_task_completion(duration, success)

                    # 연속 에러 카운터 리셋
                    if success:
                        consecutive_errors = 0

                except Exception as e:
                    consecutive_errors += 1
                    self.metrics.record_error()

                    logger.error(
                        f"Error in agent '{self.name}' loop "
                        f"(consecutive: {consecutive_errors}/{max_consecutive_errors}): {e}",
                        exc_info=True
                    )

                    if consecutive_errors >= max_consecutive_errors:
                        logger.critical(
                            f"Too many consecutive errors in agent '{self.name}'. "
                            f"Entering error state."
                        )
                        async with self._state_lock:
                            self.state = AgentState.ERROR
                        break

                    # 에러 발생 시 잠시 대기
                    await asyncio.sleep(1.0)

        except asyncio.CancelledError:
            logger.info(f"Agent '{self.name}' main loop cancelled")
            raise

        except Exception as e:
            logger.error(f"Fatal error in agent '{self.name}': {e}", exc_info=True)
            async with self._state_lock:
                self.state = AgentState.ERROR

        finally:
            # Uptime 계산
            if self._started_at:
                self.metrics.uptime_seconds = (
                    datetime.utcnow() - self._started_at
                ).total_seconds()

            logger.info(
                f"Agent '{self.name}' main loop ended. "
                f"Metrics: {self.metrics.total_tasks} tasks, "
                f"{self.metrics.completed_tasks} completed, "
                f"{self.metrics.failed_tasks} failed"
            )

    async def _execute_task(self, task: AgentTask) -> bool:
        """
        작업 실행 (내부 메서드)

        Args:
            task: 처리할 작업

        Returns:
            성공 여부
        """
        # 중복 실행 방지
        async with self._task_lock:
            if task.task_id in self.running_tasks:
                logger.warning(f"Task '{task.task_id}' is already running")
                return False
            self.running_tasks.add(task.task_id)

        try:
            logger.info(
                f"Agent '{self.name}' executing task '{task.task_id}' "
                f"(type: {task.task_type}, priority: {task.priority})"
            )

            # 타임아웃 설정
            if task.timeout:
                result = await asyncio.wait_for(
                    self.process_task(task),
                    timeout=task.timeout
                )
            else:
                result = await self.process_task(task)

            logger.info(f"✅ Task '{task.task_id}' completed successfully")
            return True

        except asyncio.TimeoutError:
            logger.error(f"Task '{task.task_id}' timed out after {task.timeout}s")

            # 재시도 가능하면 큐에 다시 추가
            if task.can_retry():
                task.increment_retry()
                logger.info(f"Retrying task '{task.task_id}' ({task.retry_count}/{task.max_retries})")
                await self.task_queue.put(task)

            return False

        except Exception as e:
            logger.error(f"Task '{task.task_id}' failed: {e}", exc_info=True)

            # 재시도 가능하면 큐에 다시 추가
            if task.can_retry():
                task.increment_retry()
                logger.info(f"Retrying task '{task.task_id}' ({task.retry_count}/{task.max_retries})")
                await asyncio.sleep(1.0)  # 재시도 전 대기
                await self.task_queue.put(task)

            return False

        finally:
            # 실행 중인 작업 목록에서 제거
            async with self._task_lock:
                self.running_tasks.discard(task.task_id)

    @abstractmethod
    async def process_task(self, task: AgentTask) -> Any:
        """
        작업 처리 (추상 메서드)

        서브클래스에서 구현 필요

        Args:
            task: 처리할 작업

        Returns:
            작업 결과
        """
        pass

    def get_status(self) -> Dict[str, Any]:
        """
        에이전트 상태 조회

        Returns:
            상태 정보 딕셔너리
        """
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "state": self.state.value,
            "queue_size": self.task_queue.qsize(),
            "running_tasks": len(self.running_tasks),
            "metrics": {
                "total_tasks": self.metrics.total_tasks,
                "completed_tasks": self.metrics.completed_tasks,
                "failed_tasks": self.metrics.failed_tasks,
                "success_rate": round(self.metrics.get_success_rate(), 2),
                "avg_task_duration": round(self.metrics.avg_task_duration, 2),
                "error_count": self.metrics.error_count,
                "uptime_seconds": round(self.metrics.uptime_seconds, 2),
            },
            "config": self.config,
        }

    def __repr__(self) -> str:
        return (
            f"<{self.__class__.__name__} "
            f"id={self.agent_id} "
            f"name='{self.name}' "
            f"state={self.state.value}>"
        )
