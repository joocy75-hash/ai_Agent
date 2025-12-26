"""
Dashboard Snapshot Worker

Background worker that calculates and caches dashboard statistics for all active users.
Updates every 60 seconds and stores results in Redis with 300s TTL.

Purpose:
- Pre-calculate expensive dashboard queries (trades, positions, statistics)
- Reduce database load during user requests
- Provide fast dashboard loading experience

Cache Key Pattern: dashboard_snapshot:{user_id}
TTL: 300 seconds (5 minutes)
Update Interval: 60 seconds
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from decimal import Decimal
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..utils.cache_manager import cache_manager
from ..database.db import AsyncSessionLocal
from ..database.models import User, Trade, BotInstance, Position

logger = logging.getLogger(__name__)


def calculate_trade_stats(trades: List[Trade]) -> Dict[str, Any]:
    """
    Calculate trading statistics from trade list.

    Args:
        trades: List of Trade objects

    Returns:
        Dictionary with trade statistics:
        - totalTrades: Total number of trades
        - winningTrades: Number of profitable trades
        - losingTrades: Number of losing trades
        - winRate: Win rate percentage (0-100)
        - avgPnl: Average PnL per trade (USDT)
        - totalReturn: Total cumulative PnL (USDT)
        - bestTrade: Highest single trade PnL (USDT)
        - worstTrade: Lowest single trade PnL (USDT)
    """
    if not trades:
        return {
            "totalTrades": 0,
            "winningTrades": 0,
            "losingTrades": 0,
            "winRate": 0.0,
            "avgPnl": 0.0,
            "totalReturn": 0.0,
            "bestTrade": 0.0,
            "worstTrade": 0.0,
        }

    # Filter only closed trades (with exit_price)
    closed_trades = [t for t in trades if t.exit_price is not None]

    if not closed_trades:
        return {
            "totalTrades": len(trades),
            "winningTrades": 0,
            "losingTrades": 0,
            "winRate": 0.0,
            "avgPnl": 0.0,
            "totalReturn": 0.0,
            "bestTrade": 0.0,
            "worstTrade": 0.0,
        }

    # Calculate statistics
    pnl_values = [float(t.pnl) for t in closed_trades]
    winning_trades = [pnl for pnl in pnl_values if pnl > 0]
    losing_trades = [pnl for pnl in pnl_values if pnl <= 0]

    total_trades = len(closed_trades)
    winning_count = len(winning_trades)
    losing_count = len(losing_trades)
    win_rate = (winning_count / total_trades * 100) if total_trades > 0 else 0.0
    avg_pnl = sum(pnl_values) / total_trades if total_trades > 0 else 0.0
    total_return = sum(pnl_values)
    best_trade = max(pnl_values) if pnl_values else 0.0
    worst_trade = min(pnl_values) if pnl_values else 0.0

    return {
        "totalTrades": total_trades,
        "winningTrades": winning_count,
        "losingTrades": losing_count,
        "winRate": round(win_rate, 2),
        "avgPnl": round(avg_pnl, 2),
        "totalReturn": round(total_return, 2),
        "bestTrade": round(best_trade, 2),
        "worstTrade": round(worst_trade, 2),
    }


def calculate_period_profits(trades: List[Trade]) -> Dict[str, float]:
    """
    Calculate profits for different time periods.

    Args:
        trades: List of Trade objects

    Returns:
        Dictionary with period profits (USDT):
        - daily: Last 24 hours
        - weekly: Last 7 days
        - monthly: Last 30 days
        - allTime: All time
    """
    now = datetime.utcnow()
    daily_cutoff = now - timedelta(days=1)
    weekly_cutoff = now - timedelta(days=7)
    monthly_cutoff = now - timedelta(days=30)

    # Filter only closed trades
    closed_trades = [t for t in trades if t.exit_price is not None]

    if not closed_trades:
        return {
            "daily": 0.0,
            "weekly": 0.0,
            "monthly": 0.0,
            "allTime": 0.0,
        }

    # Calculate period profits
    daily_pnl = sum(
        float(t.pnl)
        for t in closed_trades
        if t.created_at and t.created_at >= daily_cutoff
    )
    weekly_pnl = sum(
        float(t.pnl)
        for t in closed_trades
        if t.created_at and t.created_at >= weekly_cutoff
    )
    monthly_pnl = sum(
        float(t.pnl)
        for t in closed_trades
        if t.created_at and t.created_at >= monthly_cutoff
    )
    all_time_pnl = sum(float(t.pnl) for t in closed_trades)

    return {
        "daily": round(daily_pnl, 2),
        "weekly": round(weekly_pnl, 2),
        "monthly": round(monthly_pnl, 2),
        "allTime": round(all_time_pnl, 2),
    }


async def update_user_snapshot(user_id: int) -> bool:
    """
    Update dashboard snapshot for a specific user.

    Queries:
    1. All trades for the user
    2. Active bot instances
    3. Current positions

    Calculates:
    - Trade statistics (win rate, avg PnL, etc.)
    - Period profits (daily, weekly, monthly)
    - Bot status
    - Position summary

    Stores result in Redis with key: dashboard_snapshot:{user_id}

    Args:
        user_id: User ID to update snapshot for

    Returns:
        True if snapshot updated successfully, False otherwise
    """
    try:
        async with AsyncSessionLocal() as session:
            # Query trades
            trades_stmt = (
                select(Trade)
                .where(Trade.user_id == user_id)
                .order_by(Trade.created_at.desc())
                .limit(1000)  # Limit to last 1000 trades for performance
            )
            trades_result = await session.execute(trades_stmt)
            trades = list(trades_result.scalars().all())

            # Query bot instances
            bots_stmt = select(BotInstance).where(
                BotInstance.user_id == user_id, BotInstance.is_active == True
            )
            bots_result = await session.execute(bots_stmt)
            bot_instances = list(bots_result.scalars().all())

            # Query positions
            positions_stmt = select(Position).where(Position.user_id == user_id)
            positions_result = await session.execute(positions_stmt)
            positions = list(positions_result.scalars().all())

        # Calculate trade statistics
        trade_stats = calculate_trade_stats(trades)

        # Calculate period profits
        period_profits = calculate_period_profits(trades)

        # Bot status
        running_bots = [b for b in bot_instances if b.is_running]
        total_bots = len(bot_instances)
        running_bots_count = len(running_bots)

        # Position summary
        total_positions = len(positions)
        total_position_pnl = sum(float(p.pnl) for p in positions)

        # Build snapshot
        snapshot = {
            # Trade statistics
            "stats": trade_stats,
            # Period profits
            "profits": period_profits,
            # Bot status
            "bots": {
                "total": total_bots,
                "running": running_bots_count,
                "stopped": total_bots - running_bots_count,
            },
            # Position summary
            "positions": {
                "total": total_positions,
                "totalPnl": round(total_position_pnl, 2),
            },
            # Metadata
            "updatedAt": datetime.utcnow().isoformat(),
            "userId": user_id,
        }

        # Store in cache (Redis or in-memory fallback)
        cache_key = f"dashboard_snapshot:{user_id}"
        success = await cache_manager.set(cache_key, snapshot, ttl=300)

        if success:
            logger.debug(
                f"✅ Dashboard snapshot updated for user {user_id} "
                f"(trades: {trade_stats['totalTrades']}, bots: {running_bots_count}/{total_bots})"
            )
        else:
            logger.warning(f"⚠️ Failed to cache dashboard snapshot for user {user_id}")

        return success

    except Exception as e:
        logger.error(
            f"❌ Error updating dashboard snapshot for user {user_id}: {e}",
            exc_info=True,
        )
        return False


async def get_all_active_users() -> List[int]:
    """
    Get list of all active user IDs.

    Returns:
        List of user IDs with is_active=True
    """
    try:
        async with AsyncSessionLocal() as session:
            stmt = select(User.id).where(User.is_active == True)
            result = await session.execute(stmt)
            user_ids = [row[0] for row in result.all()]
            return user_ids
    except Exception as e:
        logger.error(f"❌ Error fetching active users: {e}", exc_info=True)
        return []


async def snapshot_worker_loop():
    """
    Main snapshot worker loop.

    Runs continuously and updates snapshots for all active users every 60 seconds.

    Workflow:
    1. Wait 60 seconds
    2. Get all active users
    3. Update snapshot for each user (sequentially to avoid DB overload)
    4. Log summary statistics
    5. Repeat

    Note:
    - Runs in background (do not await directly)
    - Handles errors gracefully (continues on failure)
    - Can be stopped by canceling the task
    """
    logger.info("🚀 Dashboard snapshot worker started")

    while True:
        try:
            # Wait before next update cycle
            await asyncio.sleep(60)

            # Get all active users
            user_ids = await get_all_active_users()

            if not user_ids:
                logger.debug("⏭️ No active users found, skipping snapshot update")
                continue

            logger.info(f"🔄 Updating snapshots for {len(user_ids)} active users...")

            # Update snapshots for each user
            success_count = 0
            fail_count = 0

            for user_id in user_ids:
                success = await update_user_snapshot(user_id)
                if success:
                    success_count += 1
                else:
                    fail_count += 1

                # Small delay to avoid overwhelming the database
                await asyncio.sleep(0.1)

            # Log summary
            logger.info(
                f"✅ Snapshot update complete: {success_count} succeeded, {fail_count} failed"
            )

        except asyncio.CancelledError:
            logger.info("🛑 Dashboard snapshot worker stopped")
            break
        except Exception as e:
            logger.error(
                f"❌ Error in snapshot worker loop: {e}",
                exc_info=True,
            )
            # Continue running despite errors
            await asyncio.sleep(10)


# Utility function to manually trigger snapshot update for a user
async def refresh_user_snapshot(user_id: int) -> Optional[Dict[str, Any]]:
    """
    Manually refresh and return snapshot for a specific user.

    This can be called from API endpoints when immediate refresh is needed.

    Args:
        user_id: User ID to refresh snapshot for

    Returns:
        Snapshot data if successful, None otherwise
    """
    success = await update_user_snapshot(user_id)
    if success:
        cache_key = f"dashboard_snapshot:{user_id}"
        return await cache_manager.get(cache_key)
    return None


# Utility function to get cached snapshot
async def get_user_snapshot(user_id: int) -> Optional[Dict[str, Any]]:
    """
    Get cached snapshot for a user.

    Args:
        user_id: User ID to get snapshot for

    Returns:
        Cached snapshot data if available, None otherwise
    """
    cache_key = f"dashboard_snapshot:{user_id}"
    return await cache_manager.get(cache_key)


# Alias for lifespan startup
async def start_snapshot_worker():
    """
    Start the snapshot worker loop.

    This is an alias for snapshot_worker_loop() for cleaner import in lifespan.
    """
    await snapshot_worker_loop()
