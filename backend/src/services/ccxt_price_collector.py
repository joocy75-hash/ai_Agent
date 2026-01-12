"""
CCXT Pro를 사용한 실시간 가격 수집기
Bitget WebSocket 문제 해결을 위한 안정적인 대체 방안
"""

import asyncio
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


async def ccxt_price_collector(market_queue: asyncio.Queue, chart_queue: asyncio.Queue = None):
    """
    CCXT를 사용한 실시간 가격 수집 (WebSocket 대체)

    Bitget WebSocket 직접 연결이 실패하는 경우 CCXT를 사용하여
    안정적으로 시장 데이터를 수집합니다.

    Args:
        market_queue: 봇 실행을 위한 큐
        chart_queue: 차트 서비스를 위한 별도 큐 (선택사항)
    """
    try:
        import ccxt.async_support as ccxt
    except ImportError:
        logger.error("ccxt library not installed. Install with: pip install ccxt")
        return

    exchange = None

    try:
        # Bitget exchange 초기화
        exchange = ccxt.bitget({
            'enableRateLimit': True,
            'options': {
                'defaultType': 'swap',  # USDT-M futures
            }
        })

        # 주요 심볼 목록 (프론트엔드의 Trading.jsx와 일치)
        symbols = [
            'BTC/USDT:USDT',
            'ETH/USDT:USDT',
            'BNB/USDT:USDT',
            'SOL/USDT:USDT',
            'ADA/USDT:USDT',
        ]

        logger.info("🚀 CCXT price collector started")
        logger.info(f"📡 Watching symbols: {symbols}")

        iteration = 0

        while True:
            try:
                for symbol in symbols:
                    try:
                        # Fetch ticker (REST API, but reliable)
                        ticker = await exchange.fetch_ticker(symbol)

                        # Convert symbol: BTC/USDT:USDT -> BTCUSDT
                        simple_symbol = symbol.split('/')[0] + 'USDT'

                        # Current timestamp
                        now = datetime.now(timezone.utc).timestamp()

                        market_data = {
                            "symbol": simple_symbol,
                            "price": float(ticker.get('last', 0)),
                            "volume": float(ticker.get('baseVolume', 0)),
                            "timestamp": now,
                            "high": float(ticker.get('high', ticker.get('last', 0))),
                            "low": float(ticker.get('low', ticker.get('last', 0))),
                            "open": float(ticker.get('open', ticker.get('last', 0))),
                            "close": float(ticker.get('last', 0)),  # current price as close
                            "time": int(now),
                        }

                        # Put to market queue (for bot)
                        try:
                            market_queue.put_nowait(market_data)
                        except asyncio.QueueFull:
                            # Queue full - remove old data and add new
                            try:
                                market_queue.get_nowait()
                                market_queue.put_nowait(market_data)
                            except Exception:
                                pass

                        # Put to chart queue (for chart service) if provided
                        if chart_queue:
                            try:
                                chart_queue.put_nowait(market_data)
                            except asyncio.QueueFull:
                                try:
                                    chart_queue.get_nowait()
                                    chart_queue.put_nowait(market_data)
                                except Exception:
                                    pass

                        # Update price alert service for annotation alerts
                        try:
                            from .price_alert_service import price_alert_service
                            await price_alert_service.update_price(
                                simple_symbol, market_data['price']
                            )
                        except Exception:
                            # Non-critical - don't break the collector
                            pass

                        # Log every 10th iteration to reduce noise
                        if iteration % 10 == 0:
                            logger.info(
                                f"✅ Market data: {simple_symbol} @ ${market_data['price']:,.2f}"
                            )

                    except Exception as e:
                        logger.warning(f"Error fetching ticker for {symbol}: {e}")
                        continue

                iteration += 1

                # Fetch every 5 seconds (reasonable for trading bot)
                await asyncio.sleep(5)

            except Exception as e:
                logger.error(f"CCXT collector loop error: {e}")
                await asyncio.sleep(10)

    except Exception as e:
        logger.error(f"CCXT price collector initialization error: {e}", exc_info=True)

    finally:
        if exchange:
            try:
                await exchange.close()
                logger.info("CCXT exchange connection closed")
            except Exception:
                pass
