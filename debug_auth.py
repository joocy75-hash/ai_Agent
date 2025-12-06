import asyncio
import os
import sys
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Add src to path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from src.database.models import User, Base
from src.utils.jwt_auth import JWTAuth

# Setup DB
DATABASE_URL = "sqlite+aiosqlite:///./backend/trading.db"
engine = create_async_engine(DATABASE_URL)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def check_user():
    async with AsyncSessionLocal() as session:
        # Check if table exists
        try:
            # Try to select from User
            result = await session.execute(
                select(User).where(User.email == "admin@admin.com")
            )
            user = result.scalars().first()

            if user:
                print(f"User found: {user.email}")
                print(f"Role: {user.role}")
                print(f"Password Hash: {user.password_hash}")

                # Verify password
                is_valid = JWTAuth.verify_password(
                    "admin123", user.password_hash
                )  # Assuming default password
                print(f"Password 'admin123' valid: {is_valid}")

                if not is_valid:
                    # Try another common password
                    is_valid_2 = JWTAuth.verify_password("password", user.password_hash)
                    print(f"Password 'password' valid: {is_valid_2}")

            else:
                print("User 'admin@admin.com' not found.")

                # List all users
                result = await session.execute(select(User))
                users = result.scalars().all()
                print(f"Total users found: {len(users)}")
                for u in users:
                    print(f" - {u.email} ({u.role})")

        except Exception as e:
            print(f"Error accessing database: {e}")
            import traceback

            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(check_user())
