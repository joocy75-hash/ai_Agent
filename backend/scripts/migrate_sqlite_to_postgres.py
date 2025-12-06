#!/usr/bin/env python3
"""
SQLite에서 PostgreSQL로 데이터 마이그레이션 스크립트

사용법:
    python3 migrate_sqlite_to_postgres.py

환경 변수:
    SQLITE_URL: SQLite 데이터베이스 경로 (기본: sqlite+aiosqlite:///./trading.db)
    POSTGRES_URL: PostgreSQL 연결 문자열 (필수)
"""

import asyncio
import os
import sys
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker

from src.database.models import Base, User, Strategy, Bot, Trade, Position


async def migrate_data():
    """Migrate data from SQLite to PostgreSQL"""

    # Source: SQLite
    sqlite_url = os.getenv("SQLITE_URL", "sqlite+aiosqlite:///./trading.db")
    # Target: PostgreSQL
    postgres_url = os.getenv("POSTGRES_URL")

    if not postgres_url:
        print("❌ Error: POSTGRES_URL environment variable not set")
        print("Example: POSTGRES_URL=postgresql+asyncpg://user:password@localhost/trading_prod")
        sys.exit(1)

    print(f"📦 Source: {sqlite_url}")
    print(f"🎯 Target: {postgres_url}")
    print()

    # Create engines
    sqlite_engine = create_async_engine(sqlite_url, echo=False)
    postgres_engine = create_async_engine(postgres_url, echo=False)

    # Create tables in PostgreSQL
    print("🔧 Creating tables in PostgreSQL...")
    async with postgres_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Tables created")
    print()

    # Create sessions
    SqliteSession = async_sessionmaker(sqlite_engine, class_=AsyncSession, expire_on_commit=False)
    PostgresSession = async_sessionmaker(postgres_engine, class_=AsyncSession, expire_on_commit=False)

    # Migrate each table
    tables = [
        ("Users", User),
        ("Strategies", Strategy),
        ("Bots", Bot),
        ("Trades", Trade),
        ("Positions", Position),
    ]

    for table_name, model in tables:
        print(f"📋 Migrating {table_name}...")

        async with SqliteSession() as sqlite_session:
            async with PostgresSession() as postgres_session:
                # Fetch all records from SQLite
                result = await sqlite_session.execute(select(model))
                records = result.scalars().all()

                if not records:
                    print(f"   ⚠️  No records found in {table_name}")
                    continue

                # Insert into PostgreSQL
                count = 0
                for record in records:
                    # Create new instance to avoid session conflicts
                    new_record = model(
                        **{
                            column.name: getattr(record, column.name)
                            for column in model.__table__.columns
                            if column.name != 'id' or not column.autoincrement
                        }
                    )

                    # For autoincrement IDs, preserve the original ID
                    if hasattr(record, 'id') and record.id:
                        new_record.id = record.id

                    postgres_session.add(new_record)
                    count += 1

                await postgres_session.commit()
                print(f"   ✅ Migrated {count} records")

        print()

    # Close connections
    await sqlite_engine.dispose()
    await postgres_engine.dispose()

    print("🎉 Migration completed successfully!")
    print()
    print("Next steps:")
    print("1. Update .env with POSTGRES_URL")
    print("2. Restart the application")
    print("3. Backup the old trading.db file")


async def verify_migration():
    """Verify that migration was successful"""

    postgres_url = os.getenv("POSTGRES_URL")
    if not postgres_url:
        print("❌ POSTGRES_URL not set")
        return

    postgres_engine = create_async_engine(postgres_url, echo=False)
    PostgresSession = async_sessionmaker(postgres_engine, class_=AsyncSession)

    print("🔍 Verifying migration...")
    print()

    async with PostgresSession() as session:
        # Count records in each table
        for table_name, model in [
            ("Users", User),
            ("Strategies", Strategy),
            ("Bots", Bot),
            ("Trades", Trade),
            ("Positions", Position),
        ]:
            result = await session.execute(select(model))
            count = len(result.scalars().all())
            print(f"   {table_name}: {count} records")

    await postgres_engine.dispose()
    print()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Migrate data from SQLite to PostgreSQL")
    parser.add_argument("--verify", action="store_true", help="Verify migration only")
    args = parser.parse_args()

    if args.verify:
        asyncio.run(verify_migration())
    else:
        print()
        print("⚠️  WARNING: This will copy all data from SQLite to PostgreSQL")
        print("⚠️  Make sure PostgreSQL database is empty or you may have duplicates")
        print()
        response = input("Continue? (yes/no): ")

        if response.lower() == "yes":
            asyncio.run(migrate_data())
            asyncio.run(verify_migration())
        else:
            print("❌ Migration cancelled")
