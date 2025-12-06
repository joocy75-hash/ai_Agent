"""
pytest 설정 및 공통 픽스처
"""
import pytest
import asyncio
import os
from typing import AsyncGenerator, Generator
from httpx import AsyncClient

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from src.database.models import Base
from src.config import settings
from src.main import create_app


# 테스트용 DB URL (SQLite - 인메모리 DB 사용)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
TEST_SYNC_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """
    세션 스코프의 이벤트 루프.
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def async_engine():
    """
    테스트용 비동기 엔진 (각 테스트마다 새로 생성).
    """
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture(scope="function")
async def async_session(async_engine) -> AsyncGenerator[AsyncSession, None]:
    """
    테스트용 비동기 세션.
    """
    AsyncSessionLocal = async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    async with AsyncSessionLocal() as session:
        yield session


@pytest.fixture(scope="function")
def sync_engine():
    """
    테스트용 동기 엔진.
    """
    engine = create_engine(TEST_SYNC_DATABASE_URL, echo=False)
    Base.metadata.create_all(engine)

    yield engine

    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture(scope="function")
def sync_session(sync_engine) -> Generator[Session, None, None]:
    """
    테스트용 동기 세션.
    """
    SyncSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)

    session = SyncSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="function")
async def async_client(async_engine) -> AsyncGenerator[AsyncClient, None]:
    """
    테스트용 HTTP 클라이언트 (FastAPI TestClient 대신 httpx AsyncClient 사용).
    """
    from src.database.db import get_session

    app = create_app()

    # DB 세션 오버라이드
    async def override_get_session():
        AsyncSessionLocal = async_sessionmaker(
            async_engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        async with AsyncSessionLocal() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session

    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture(scope="session")
def sample_csv_path() -> str:
    """
    테스트용 샘플 CSV 파일 경로.
    """
    csv_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "test_data",
        "sample_btc_1h.csv"
    )

    # CSV 파일이 존재하는지 확인
    if not os.path.exists(csv_path):
        pytest.skip(f"Sample CSV file not found: {csv_path}")

    return csv_path
