import asyncio
from src.database.models import User
from src.database.db import AsyncSessionLocal
from src.utils.jwt_auth import JWTAuth
from sqlalchemy import select


async def create_admin_user():
    email = "admin@admin.com"
    password = "admin1234"

    async with AsyncSessionLocal() as session:
        # Check if user exists
        result = await session.execute(select(User).where(User.email == email))
        existing_user = result.scalar_one_or_none()

        if existing_user:
            print(f"User {email} already exists. Updating password...")
            existing_user.password_hash = JWTAuth.get_password_hash(password)
            await session.commit()
            print("Password updated.")
        else:
            hashed_password = JWTAuth.get_password_hash(password)
            user = User(email=email, password_hash=hashed_password)
            session.add(user)
            await session.commit()
            print(f"User {email} created.")

    print("\n" + "=" * 60)
    print("✅ Admin Account Ready")
    print(f"Email: {email}")
    print(f"Password: {password}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(create_admin_user())
