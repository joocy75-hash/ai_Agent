import asyncio
from sqlalchemy import select
from src.database.models import User
from src.database.db import AsyncSessionLocal


async def check_users():
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User))
        users = result.scalars().all()
        print(f"\n총 사용자 수: {len(users)}")
        print("-" * 50)
        if len(users) == 0:
            print("등록된 사용자가 없습니다.")
            print("\n회원가입이 필요합니다:")
            print("1. 프론트엔드에서 /register 페이지로 이동")
            print("2. 이메일과 비밀번호를 입력하여 계정 생성")
        else:
            for u in users:
                print(f"ID: {u.id} | Email: {u.email} | 생성일: {u.created_at}")
        print("-" * 50)


if __name__ == "__main__":
    asyncio.run(check_users())
