"""
데이터베이스 초기화 및 테스트 사용자 생성
"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from src.database.models import Base, User
from src.database.db import AsyncSessionLocal
from passlib.context import CryptContext

# 비밀번호 해싱
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def init_db():
    """데이터베이스 테이블 생성"""
    print("데이터베이스 초기화 중...")

    # SQLite용 비동기 엔진 생성
    engine = create_async_engine(
        "sqlite+aiosqlite:///./trading.db",
        echo=True
    )

    # 모든 테이블 생성
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)  # 기존 테이블 삭제
        await conn.run_sync(Base.metadata.create_all)  # 새로 생성

    print("✅ 데이터베이스 테이블 생성 완료!")

    # 테스트 사용자 생성
    print("\n테스트 사용자 생성 중...")
    async with AsyncSessionLocal() as session:
        # 비밀번호 해싱
        hashed_password = pwd_context.hash("test1234")

        # 사용자 생성
        user = User(
            email="test@example.com",
            password_hash=hashed_password
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        print("\n" + "=" * 60)
        print("✅ 테스트 계정이 생성되었습니다!")
        print("=" * 60)
        print(f"📧 이메일: test@example.com")
        print(f"🔑 비밀번호: test1234")
        print(f"🆔 사용자 ID: {user.id}")
        print("=" * 60)
        print("\n로그인 방법:")
        print("1. http://localhost:3000 접속")
        print("2. 위 이메일과 비밀번호로 로그인")
        print("=" * 60 + "\n")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(init_db())
