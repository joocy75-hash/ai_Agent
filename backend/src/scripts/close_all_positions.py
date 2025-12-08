"""
Close all open Bitget positions for admin user
Usage: python -m src.scripts.close_all_positions

WARNING: This will close ALL open positions at market price!
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import select
from src.database.db import AsyncSessionLocal
from src.database.models import ApiKey
from src.utils.crypto_secrets import decrypt_secret


async def close_all_positions():
    """Close all open Bitget positions"""
    print("⚠️  WARNING: This will close ALL open positions at market price!")
    print("   Press Ctrl+C within 5 seconds to cancel...")
    print()

    try:
        await asyncio.sleep(5)
    except KeyboardInterrupt:
        print("\n❌ Cancelled by user")
        return

    print("🔍 Starting position closure process...\n")

    async with AsyncSessionLocal() as session:
        # Get API keys for user 1
        result = await session.execute(
            select(ApiKey).where(ApiKey.user_id == 1)
        )
        api_key_obj = result.scalars().first()

        if not api_key_obj:
            print("❌ No API keys found for user 1")
            return

        # Decrypt API keys
        api_key = decrypt_secret(api_key_obj.encrypted_api_key)
        api_secret = decrypt_secret(api_key_obj.encrypted_secret_key)
        passphrase = decrypt_secret(api_key_obj.encrypted_passphrase) if api_key_obj.encrypted_passphrase else ""

        print(f"✅ Using API keys for Bitget")
        print()

        # Use CCXT to close positions
        import ccxt.async_support as ccxt

        exchange = ccxt.bitget({
            'apiKey': api_key,
            'secret': api_secret,
            'password': passphrase,
            'options': {
                'defaultType': 'swap',
            }
        })

        try:
            # Fetch positions
            print("📡 Fetching current positions...")
            positions = await exchange.fetch_positions()
            open_positions = [p for p in positions if float(p.get('contracts', 0)) > 0]

            if not open_positions:
                print("✅ No open positions to close")
                return

            print(f"Found {len(open_positions)} open position(s)")
            print()

            # Close each position
            closed_count = 0
            failed_count = 0

            for pos in open_positions:
                symbol = pos.get('symbol', 'Unknown')
                contracts = float(pos.get('contracts', 0))
                side = pos.get('side', 'Unknown')

                print(f"🔄 Closing {symbol} {side.upper()} position ({contracts} contracts)...")

                try:
                    # Close position by creating opposite market order
                    close_side = 'sell' if side == 'long' else 'buy'

                    # Using reduceOnly flag to ensure it's a position close
                    order = await exchange.create_order(
                        symbol=symbol,
                        type='market',
                        side=close_side,
                        amount=contracts,
                        params={'reduceOnly': True}
                    )

                    print(f"   ✅ Closed successfully - Order ID: {order.get('id', 'N/A')}")
                    closed_count += 1

                except Exception as e:
                    print(f"   ❌ Failed to close: {e}")
                    failed_count += 1

                print()

            # Summary
            print("=" * 50)
            print(f"📊 Summary:")
            print(f"   ✅ Successfully closed: {closed_count}")
            print(f"   ❌ Failed: {failed_count}")
            print("=" * 50)
            print()

            # Check final balance
            print("💰 Fetching final balance...")
            balance = await exchange.fetch_balance()
            total = float(balance.get('total', {}).get('USDT', 0))
            free = float(balance.get('free', {}).get('USDT', 0))
            used = float(balance.get('used', {}).get('USDT', 0))

            print(f"   Total: ${total:,.4f} USDT")
            print(f"   Free: ${free:,.4f} USDT")
            print(f"   Used: ${used:,.4f} USDT")
            print()

            if used > 0.01:  # Small threshold for rounding errors
                print("⚠️  Warning: Still have margin in use. Some positions may not have closed.")
            else:
                print("✅ All positions closed successfully!")

        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await exchange.close()


if __name__ == "__main__":
    try:
        asyncio.run(close_all_positions())
    except KeyboardInterrupt:
        print("\n❌ Cancelled by user")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
