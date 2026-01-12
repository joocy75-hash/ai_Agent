"""
Script to create admin user for deployment
Usage: python -m src.scripts.create_admin_user
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from passlib.context import CryptContext
from sqlalchemy import select
from src.database.db import AsyncSessionLocal, engine
from src.database.models import Base, User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def create_admin():
    """Create admin user if not exists"""
    print("🔧 Initializing database...")

    # Create tables if they don't exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    print("✅ Database initialized")

    async with AsyncSessionLocal() as db:
        # Check if admin already exists
        result = await db.execute(
            select(User).where(User.email == "admin@admin.com")
        )
        existing_user = result.scalar_one_or_none()

        if existing_user:
            print("⚠️  Admin user already exists!")
            print(f"   Email: {existing_user.email}")
            print(f"   Name: {existing_user.name}")
            print(f"   Role: {existing_user.role}")
            return

        # Create admin user
        print("👤 Creating admin user...")
        admin_user = User(
            email="admin@admin.com",
            name="Admin User",
            phone="010-0000-0000",
            password_hash=pwd_context.hash("Admin123!"),
            role="admin",
            is_active=True
        )

        db.add(admin_user)
        await db.commit()
        await db.refresh(admin_user)

        print("✅ Admin user created successfully!")
        print(f"   Email: {admin_user.email}")
        print("   Password: Admin123!")
        print(f"   Role: {admin_user.role}")
        print("")
        print("🔐 Please change the password after first login!")


if __name__ == "__main__":
    try:
        asyncio.run(create_admin())
    except Exception as e:
        print(f"❌ Error creating admin user: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
