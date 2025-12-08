"""
Update admin password to Admin123!
"""
import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.database.db import AsyncSessionLocal
from src.database.models import User
from passlib.context import CryptContext
from sqlalchemy import select

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def update_admin_password():
    """Update admin password"""
    print("🔧 Updating admin password...")

    async with AsyncSessionLocal() as db:
        # Find admin user
        result = await db.execute(
            select(User).where(User.email == "admin@admin.com")
        )
        admin_user = result.scalar_one_or_none()

        if not admin_user:
            print("❌ Admin user not found!")
            return

        # Update password
        new_password = "Admin123!"
        admin_user.hashed_password = pwd_context.hash(new_password)
        admin_user.name = "Admin User"  # Also update name

        await db.commit()

        print("✅ Admin password updated successfully!")
        print(f"   Email: {admin_user.email}")
        print(f"   New Password: {new_password}")
        print(f"   Name: {admin_user.name}")


if __name__ == "__main__":
    try:
        asyncio.run(update_admin_password())
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
