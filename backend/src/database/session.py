from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from ..config import settings


_sync_engine = None
_SyncSessionLocal = None


def _get_sync_engine():
    """Lazy initialization of synchronous database engine."""
    global _sync_engine, _SyncSessionLocal
    if _sync_engine is None:
        # Convert async database URL to sync version
        sync_database_url = settings.database_url.replace("+asyncpg", "").replace("+aiosqlite", "")

        # 동기 엔진 - 커넥션 풀 설정 (백테스트용)
        _sync_engine = create_engine(
            sync_database_url,
            echo=settings.debug,
            pool_size=10,           # 기본 커넥션 10개
            max_overflow=15,        # 추가로 최대 15개
            pool_timeout=30,
            pool_recycle=3600,
            pool_pre_ping=True,
        )
        _SyncSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_sync_engine)
    return _SyncSessionLocal


def get_session() -> Generator[Session, None, None]:
    """
    Dependency for getting a synchronous database session.
    Used by backtest endpoints that are not async.
    """
    SessionLocal = _get_sync_engine()
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
