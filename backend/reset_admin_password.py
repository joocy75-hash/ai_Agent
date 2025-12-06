import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import select
from passlib.context import CryptContext
from src.database.db import get_session
from src.database.models import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def reset_admin_password():
    """Reset admin password to 'admin123'"""
    async for session in get_session():
        try:
            # Find admin user
            result = await session.execute(
                select(User).where(User.email == "admin@admin.com")
            )
            user = result.scalars().first()

            if not user:
                print("❌ Admin user not found!")
                return

            # Hash new password
            new_password = "admin123"
            hashed_password = pwd_context.hash(new_password)

            # Update password
            user.password_hash = hashed_password
            await session.commit()

            print(f"✅ Admin password reset successfully!")
            print(f"   Email: {user.email}")
            print(f"   Password: {new_password}")
            print(f"   Hash: {hashed_password[:50]}...")

        except Exception as e:
            print(f"❌ Error: {e}")
            await session.rollback()

if __name__ == "__main__":
    asyncio.run(reset_admin_password())
