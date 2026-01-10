"""
거래소 통합 모듈

지원 거래소:
- Bitget (기본)
- Binance
- OKX
- Bybit
- Gate.io
"""

from .base import BaseExchange
from .bitget import BitgetExchange
from .binance import BinanceExchange
from .okx import OKXExchange
from .bybit import BybitExchange
from .gateio import GateioExchange
from .factory import ExchangeFactory, ExchangeManager, exchange_manager

# WebSocket 클라이언트
from .bitget_ws import BitgetWebSocket
from .binance_ws import BinanceWebSocket
from .okx_ws import OKXWebSocket
from .bybit_ws import BybitWebSocket
from .gateio_ws import GateioWebSocket

__all__ = [
    # REST API 클라이언트
    "BaseExchange",
    "BitgetExchange",
    "BinanceExchange",
    "OKXExchange",
    "BybitExchange",
    "GateioExchange",
    # 팩토리 및 매니저
    "ExchangeFactory",
    "ExchangeManager",
    "exchange_manager",
    # WebSocket 클라이언트
    "BitgetWebSocket",
    "BinanceWebSocket",
    "OKXWebSocket",
    "BybitWebSocket",
    "GateioWebSocket",
]
