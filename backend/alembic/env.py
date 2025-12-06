"""
Alembic 마이그레이션 환경 설정
"""
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config, pool

from alembic import context

# 프로젝트 루트를 sys.path에 추가
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

# 설정과 모델 임포트
from src.config import settings
from src.database.models import Base

# Alembic Config 객체
config = context.config

# Python logging 설정
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# autogenerate를 위한 MetaData
target_metadata = Base.metadata

# DB URL 설정 (async 드라이버를 sync 드라이버로 변경)
database_url = settings.database_url
# asyncpg -> psycopg2 (PostgreSQL)
database_url = database_url.replace("+asyncpg", "").replace("postgresql://", "postgresql+psycopg2://")
# aiosqlite -> pysqlite (SQLite)
database_url = database_url.replace("+aiosqlite", "")
config.set_main_option("sqlalchemy.url", database_url)


def run_migrations_offline() -> None:
    """
    오프라인 모드로 마이그레이션 실행.

    DB 연결 없이 SQL 스크립트만 생성.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,  # 타입 변경 감지
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    온라인 모드로 마이그레이션 실행.

    실제 DB 연결을 생성하여 마이그레이션 적용.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,  # 타입 변경 감지
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
