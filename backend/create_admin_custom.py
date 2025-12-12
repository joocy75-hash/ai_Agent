"""
커스텀 관리자 계정 생성 스크립트

사용법: python create_admin_custom.py
"""

import asyncio
from sqlalchemy import select
from passlib.context import CryptContext

from src.database.db import AsyncSessionLocal
from src.database.models import User


# 비밀번호 해싱 컨텍스트
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def create_admin_user(email: str, password: str, name: str = "Admin"):
    """관리자 계정 생성 (비밀번호 검증 우회)"""
    async with AsyncSessionLocal() as session:
        # 이미 존재하는지 확인
        result = await session.execute(select(User).where(User.email == email))
        existing = result.scalars().first()

        if existing:
            print(f"⚠️  User {email} already exists. Updating password...")
            existing.password_hash = pwd_context.hash(password)
            existing.role = "admin"
            existing.name = name
            await session.commit()
            print(f"✅ Password updated and role set to admin")
            return existing

        # 관리자 생성
        admin = User(
            email=email,
            password_hash=pwd_context.hash(password),
            role="admin",
            name=name,
            exchange="bitget",
        )

        session.add(admin)
        await session.commit()
        await session.refresh(admin)

        print(f"\n✅ Admin user created successfully!")
        print(f"   Email: {email}")
        print(f"   Name: {name}")
        print(f"   Role: {admin.role}")
        print(f"   ID: {admin.id}")

        return admin


async def main():
    """메인 함수"""
    # 요청된 관리자 계정 정보
    email = "admin"
    password = "1004"
    name = "Administrator"

    print("=" * 60)
    print("커스텀 관리자 계정 생성")
    print("=" * 60)
    print(f"Email: {email}")
    print(f"Password: {password}")
    print("=" * 60 + "\n")

    await create_admin_user(email, password, name)

    print("\n🔐 You can now login with this account.")


if __name__ == "__main__":
    asyncio.run(main())
