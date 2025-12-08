"""
Check current Bitget positions from database
"""
import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from sqlalchemy import select
from database.db import AsyncSessionLocal
from database.models import ApiKey
from utils.encryption import decrypt_secret


async def check_positions():
    """Check Bitget positions for user 1 (admin)"""
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

        print(f"✅ Found API keys for user 1")
        print(f"   Exchange: {api_key_obj.exchange_name}")
        print()

        # Use CCXT to fetch positions
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
            positions = await exchange.fetch_positions()

            print(f"📊 Total positions: {len(positions)}")
            print()

            # Filter open positions
            open_positions = [p for p in positions if float(p.get('contracts', 0)) > 0]

            if not open_positions:
                print("✅ No open positions found")
            else:
                print(f"⚠️  Found {len(open_positions)} open position(s):")
                print()

                for pos in open_positions:
                    symbol = pos.get('symbol', 'Unknown')
                    contracts = float(pos.get('contracts', 0))
                    side = pos.get('side', 'Unknown')
                    entry_price = float(pos.get('entryPrice', 0))
                    mark_price = float(pos.get('markPrice', 0))
                    unrealized_pnl = float(pos.get('unrealizedPnl', 0))
                    liquidation_price = float(pos.get('liquidationPrice', 0))

                    print(f"  Symbol: {symbol}")
                    print(f"  Side: {side.upper()}")
                    print(f"  Contracts: {contracts}")
                    print(f"  Entry Price: ${entry_price:,.2f}")
                    print(f"  Mark Price: ${mark_price:,.2f}")
                    print(f"  Unrealized PnL: ${unrealized_pnl:,.2f}")
                    print(f"  Liquidation Price: ${liquidation_price:,.2f}")
                    print()

            # Fetch balance
            balance = await exchange.fetch_balance()
            total = float(balance.get('total', {}).get('USDT', 0))
            free = float(balance.get('free', {}).get('USDT', 0))
            used = float(balance.get('used', {}).get('USDT', 0))

            print(f"💰 Account Balance:")
            print(f"   Total: ${total:,.2f} USDT")
            print(f"   Free: ${free:,.2f} USDT")
            print(f"   Used (in positions): ${used:,.2f} USDT")

        except Exception as e:
            print(f"❌ Error fetching positions: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await exchange.close()


if __name__ == "__main__":
    try:
        asyncio.run(check_positions())
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
