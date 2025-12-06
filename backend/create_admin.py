"""
관리자 계정 생성 스크립트

첫 관리자 계정을 생성합니다.

사용법:
    python create_admin.py

또는 인자를 전달:
    python create_admin.py admin@example.com your-password
"""

import asyncio
import sys
from sqlalchemy import select

from src.database.db import AsyncSessionLocal
from src.database.models import User
from src.utils.jwt_auth import JWTAuth


async def create_admin_user(email: str, password: str):
    """관리자 계정 생성"""
    async with AsyncSessionLocal() as session:
        # 이미 존재하는지 확인
        result = await session.execute(select(User).where(User.email == email))
        existing = result.scalars().first()

        if existing:
            print(f"❌ User {email} already exists")
            if existing.role == "admin":
                print(f"✅ User is already an admin")
            else:
                # 기존 사용자를 관리자로 승격
                existing.role = "admin"
                await session.commit()
                print(f"✅ Upgraded {email} to admin role")
            return

        # 관리자 생성
        admin = User(
            email=email,
            password_hash=JWTAuth.get_password_hash(password),
            role="admin",  # 관리자 역할
            exchange="bitget"
        )

        session.add(admin)
        await session.commit()
        await session.refresh(admin)

        print(f"\n✅ Admin user created successfully!")
        print(f"   Email: {email}")
        print(f"   Role: {admin.role}")
        print(f"   ID: {admin.id}")
        print(f"\n🔐 You can now login with this account at the frontend.")


async def main():
    """메인 함수"""
    if len(sys.argv) >= 3:
        # 인자로 받은 경우
        email = sys.argv[1]
        password = sys.argv[2]
    else:
        # 기본값 사용
        email = "admin@admin.com"
        password = "admin123"  # 실제 사용 시 변경 필요!
        print(f"⚠️  Using default credentials:")
        print(f"   Email: {email}")
        print(f"   Password: {password}")
        print(f"   (Change the password after first login!)\n")

    await create_admin_user(email, password)


if __name__ == "__main__":
    print("=" * 60)
    print("관리자 계정 생성 스크립트")
    print("=" * 60 + "\n")

    asyncio.run(main())
