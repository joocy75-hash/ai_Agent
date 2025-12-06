"""
데이터베이스에 직접 사용자를 생성하는 스크립트
bcrypt 문제를 우회하여 간단한 해싱 사용
"""
import asyncio
import hashlib
from src.database.models import User
from src.database.db import AsyncSessionLocal


async def create_user_simple():
    """간단한 해싱으로 테스트 사용자 생성"""
    email = "test@example.com"
    password = "test1234"

    # 간단한 SHA256 해싱 (테스트용)
    # 실제 운영에서는 bcrypt 사용 권장
    password_hash = hashlib.sha256(password.encode()).hexdigest()

    async with AsyncSessionLocal() as session:
        # 기존 사용자 확인
        from sqlalchemy import select
        result = await session.execute(select(User).where(User.email == email))
        existing = result.scalars().first()

        if existing:
            print(f"\n⚠️  사용자가 이미 존재합니다: {email}")
            print("기존 사용자 정보를 사용하세요.")
            return

        # 새 사용자 생성
        user = User(
            email=email,
            password_hash=f"sha256${password_hash}"  # 접두사로 해싱 방법 표시
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        print("\n" + "=" * 60)
        print("✅ 테스트 계정이 생성되었습니다!")
        print("=" * 60)
        print(f"📧 이메일: {email}")
        print(f"🔑 비밀번호: {password}")
        print(f"🆔 사용자 ID: {user.id}")
        print("=" * 60)
        print("\n⚠️  주의: 이 계정은 테스트용입니다.")
        print("운영 환경에서는 프론트엔드 회원가입을 사용하세요.")
        print("=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(create_user_simple())
