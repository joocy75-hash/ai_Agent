#!/usr/bin/env python3
"""
긴급 정지 스크립트 - 모든 봇 정지 및 포지션 청산

사용법:
    python3 emergency_stop_all.py [OPTIONS]

옵션:
    --user-id <ID>        특정 사용자만 정지 (선택사항)
    --close-positions     포지션도 함께 청산 (위험!)
    --dry-run             실제 실행 없이 시뮬레이션만
"""

import asyncio
import os
import sys
import argparse
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from src.database.models import Bot, User, Position
from src.config import settings


async def emergency_stop(user_id: int = None, close_positions: bool = False, dry_run: bool = False):
    """
    긴급 정지 실행

    Args:
        user_id: 특정 사용자 ID (None이면 모든 사용자)
        close_positions: True면 포지션도 청산
        dry_run: True면 실제 실행 없이 출력만
    """

    # Create engine
    engine = create_async_engine(settings.database_url, echo=False)
    SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    print()
    print("=" * 60)
    print("🚨 EMERGENCY STOP SCRIPT")
    print("=" * 60)
    print()

    if dry_run:
        print("⚠️  DRY RUN MODE - No actual changes will be made")
        print()

    async with SessionLocal() as session:
        # Find running bots
        query = select(Bot).where(Bot.status == "running")
        if user_id:
            query = query.where(Bot.user_id == user_id)

        result = await session.execute(query)
        bots = result.scalars().all()

        if not bots:
            print("ℹ️  No running bots found")
            await engine.dispose()
            return

        print(f"📋 Found {len(bots)} running bot(s):")
        print()

        for bot in bots:
            # Get user info
            user_result = await session.execute(
                select(User).where(User.id == bot.user_id)
            )
            user = user_result.scalar_one_or_none()

            print(f"  Bot ID: {bot.id}")
            print(f"  User: {user.email if user else 'Unknown'} (ID: {bot.user_id})")
            print(f"  Strategy: {bot.strategy_code}")
            print(f"  Symbol: {bot.symbol}")
            print(f"  Status: {bot.status}")
            print()

            if not dry_run:
                # Stop bot
                bot.status = "stopped"
                bot.stopped_at = datetime.utcnow()
                session.add(bot)
                print(f"  ✅ Bot {bot.id} stopped")

        if not dry_run:
            await session.commit()
            print()
            print(f"✅ Stopped {len(bots)} bot(s)")

        # Handle positions
        if close_positions:
            print()
            print("=" * 60)
            print("💰 CLOSING POSITIONS")
            print("=" * 60)
            print()

            query = select(Position).where(Position.status == "open")
            if user_id:
                query = query.where(Position.user_id == user_id)

            result = await session.execute(query)
            positions = result.scalars().all()

            if not positions:
                print("ℹ️  No open positions found")
            else:
                print(f"📋 Found {len(positions)} open position(s):")
                print()

                for pos in positions:
                    print(f"  Position ID: {pos.id}")
                    print(f"  User ID: {pos.user_id}")
                    print(f"  Symbol: {pos.symbol}")
                    print(f"  Side: {pos.side}")
                    print(f"  Size: {pos.size}")
                    print(f"  Entry: ${pos.entry_price:,.2f}")
                    print()

                    if not dry_run:
                        # TODO: Call Bitget API to close position
                        # This requires API credentials which are encrypted in DB
                        # For now, just mark as closed in DB
                        print(f"  ⚠️  Position {pos.id} - Manual closure required!")
                        print(f"     Use Bitget web interface to close manually")

                print()
                print("⚠️  WARNING: Positions must be closed manually through Bitget!")
                print("⚠️  This script only stops the bot, not close positions automatically")

    await engine.dispose()

    print()
    print("=" * 60)
    print("✅ Emergency stop completed")
    print("=" * 60)
    print()

    if not dry_run:
        print("Next steps:")
        print("1. Check Bitget account for any open positions")
        print("2. Close positions manually if needed")
        print("3. Check logs for any errors")
        print("4. Investigate root cause before restarting bots")


async def list_status():
    """List current bot status"""

    engine = create_async_engine(settings.database_url, echo=False)
    SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    print()
    print("📊 Current Bot Status")
    print("=" * 60)
    print()

    async with SessionLocal() as session:
        result = await session.execute(select(Bot))
        bots = result.scalars().all()

        if not bots:
            print("ℹ️  No bots found")
            await engine.dispose()
            return

        for bot in bots:
            user_result = await session.execute(
                select(User).where(User.id == bot.user_id)
            )
            user = user_result.scalar_one_or_none()

            status_emoji = "🟢" if bot.status == "running" else "🔴"

            print(f"{status_emoji} Bot ID: {bot.id}")
            print(f"   User: {user.email if user else 'Unknown'}")
            print(f"   Status: {bot.status}")
            print(f"   Strategy: {bot.strategy_code}")
            print(f"   Symbol: {bot.symbol}")
            print()

    await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Emergency stop script for trading bots",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--user-id",
        type=int,
        help="Stop bots for specific user ID only"
    )

    parser.add_argument(
        "--close-positions",
        action="store_true",
        help="Also attempt to close positions (WARNING: Use with caution!)"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate without making actual changes"
    )

    parser.add_argument(
        "--status",
        action="store_true",
        help="Show current bot status only"
    )

    args = parser.parse_args()

    if args.status:
        asyncio.run(list_status())
    else:
        # Confirmation
        if not args.dry_run:
            print()
            print("⚠️  WARNING: This will stop all running bots!")
            if args.close_positions:
                print("⚠️  WARNING: This will also attempt to close positions!")
            print()
            response = input("Continue? (type 'EMERGENCY STOP' to confirm): ")

            if response != "EMERGENCY STOP":
                print("❌ Cancelled")
                sys.exit(0)

        asyncio.run(emergency_stop(
            user_id=args.user_id,
            close_positions=args.close_positions,
            dry_run=args.dry_run
        ))
