"""
Unit tests for ExchangeFactory and multi-exchange support.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from decimal import Decimal

from src.services.exchanges.factory import ExchangeFactory, ExchangeManager
from src.services.exchanges.base import BaseExchange
from src.services.exchanges.binance import BinanceExchange
from src.services.exchanges.okx import OKXExchange
from src.services.exchanges.bybit import BybitExchange
from src.services.exchanges.gateio import GateioExchange
from src.services.exchanges.bitget import BitgetExchange
from src.config import ExchangeConfig


@pytest.mark.unit
class TestExchangeConfig:
    """Tests for ExchangeConfig."""

    def test_supported_exchanges(self):
        """Test all expected exchanges are supported."""
        expected = ["bitget", "binance", "okx", "bybit", "gateio"]
        assert set(ExchangeConfig.SUPPORTED_EXCHANGES) == set(expected)

    def test_passphrase_required_exchanges(self):
        """Test passphrase required exchanges."""
        assert "bitget" in ExchangeConfig.PASSPHRASE_REQUIRED
        assert "okx" in ExchangeConfig.PASSPHRASE_REQUIRED
        assert "binance" not in ExchangeConfig.PASSPHRASE_REQUIRED
        assert "bybit" not in ExchangeConfig.PASSPHRASE_REQUIRED
        assert "gateio" not in ExchangeConfig.PASSPHRASE_REQUIRED

    def test_symbol_formats(self):
        """Test symbol format mappings."""
        assert ExchangeConfig.SYMBOL_FORMATS["bitget"] == "ETHUSDT"
        assert ExchangeConfig.SYMBOL_FORMATS["binance"] == "ETH/USDT"
        assert ExchangeConfig.SYMBOL_FORMATS["okx"] == "ETH/USDT:USDT"
        assert ExchangeConfig.SYMBOL_FORMATS["bybit"] == "ETHUSDT"
        assert ExchangeConfig.SYMBOL_FORMATS["gateio"] == "ETH/USDT:USDT"


@pytest.mark.unit
class TestExchangeFactory:
    """Tests for ExchangeFactory."""

    def test_get_supported_exchanges(self):
        """Test get_supported_exchanges returns all exchanges."""
        supported = ExchangeFactory.get_supported_exchanges()
        assert "bitget" in supported
        assert "binance" in supported
        assert "okx" in supported
        assert "bybit" in supported
        assert "gateio" in supported

    def test_create_bitget_requires_passphrase(self):
        """Test Bitget requires passphrase."""
        with pytest.raises(ValueError) as exc_info:
            ExchangeFactory.create(
                exchange_name="bitget",
                api_key="test-key",
                secret_key="test-secret",
                passphrase=None,
            )
        assert "requires passphrase" in str(exc_info.value)

    def test_create_okx_requires_passphrase(self):
        """Test OKX requires passphrase."""
        with pytest.raises(ValueError) as exc_info:
            ExchangeFactory.create(
                exchange_name="okx",
                api_key="test-key",
                secret_key="test-secret",
                passphrase=None,
            )
        assert "requires passphrase" in str(exc_info.value)

    @patch("src.services.exchanges.binance.ccxt.binance")
    def test_create_binance_no_passphrase_required(self, mock_ccxt):
        """Test Binance doesn't require passphrase."""
        mock_ccxt.return_value = MagicMock()

        client = ExchangeFactory.create(
            exchange_name="binance",
            api_key="test-key",
            secret_key="test-secret",
        )

        assert isinstance(client, BinanceExchange)

    @patch("src.services.exchanges.bybit.ccxt.bybit")
    def test_create_bybit_no_passphrase_required(self, mock_ccxt):
        """Test Bybit doesn't require passphrase."""
        mock_ccxt.return_value = MagicMock()

        client = ExchangeFactory.create(
            exchange_name="bybit",
            api_key="test-key",
            secret_key="test-secret",
        )

        assert isinstance(client, BybitExchange)

    @patch("src.services.exchanges.gateio.ccxt.gateio")
    def test_create_gateio_no_passphrase_required(self, mock_ccxt):
        """Test Gate.io doesn't require passphrase."""
        mock_ccxt.return_value = MagicMock()

        client = ExchangeFactory.create(
            exchange_name="gateio",
            api_key="test-key",
            secret_key="test-secret",
        )

        assert isinstance(client, GateioExchange)

    def test_create_unsupported_exchange_raises_error(self):
        """Test unsupported exchange raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            ExchangeFactory.create(
                exchange_name="unsupported",
                api_key="test-key",
                secret_key="test-secret",
            )
        assert "Unsupported exchange" in str(exc_info.value)

    def test_exchange_name_case_insensitive(self):
        """Test exchange name is case insensitive."""
        # Should normalize to lowercase
        with pytest.raises(ValueError) as exc_info:
            ExchangeFactory.create(
                exchange_name="BITGET",
                api_key="test-key",
                secret_key="test-secret",
            )
        # Error message shows it was normalized (requires passphrase)
        assert "bitget requires passphrase" in str(exc_info.value)


@pytest.mark.unit
class TestExchangeManager:
    """Tests for ExchangeManager."""

    def test_init(self):
        """Test ExchangeManager initialization."""
        manager = ExchangeManager()
        assert manager._clients == {}

    @patch("src.services.exchanges.factory.ExchangeFactory.create")
    def test_get_client_creates_new_client(self, mock_create):
        """Test get_client creates new client when not cached."""
        mock_client = MagicMock()
        mock_create.return_value = mock_client

        manager = ExchangeManager()
        client = manager.get_client(
            user_id=1,
            exchange_name="binance",
            api_key="test-key",
            secret_key="test-secret",
        )

        assert client == mock_client
        mock_create.assert_called_once()

    @patch("src.services.exchanges.factory.ExchangeFactory.create")
    def test_get_client_returns_cached_client(self, mock_create):
        """Test get_client returns cached client."""
        mock_client = MagicMock()
        mock_create.return_value = mock_client

        manager = ExchangeManager()

        # First call
        client1 = manager.get_client(
            user_id=1,
            exchange_name="binance",
            api_key="test-key",
            secret_key="test-secret",
        )

        # Second call should return cached
        client2 = manager.get_client(
            user_id=1,
            exchange_name="binance",
            api_key="test-key",
            secret_key="test-secret",
        )

        assert client1 == client2
        assert mock_create.call_count == 1  # Only called once

    @patch("src.services.exchanges.factory.ExchangeFactory.create")
    def test_get_client_force_new(self, mock_create):
        """Test get_client with force_new creates new client."""
        mock_client1 = MagicMock()
        mock_client2 = MagicMock()
        mock_create.side_effect = [mock_client1, mock_client2]

        manager = ExchangeManager()

        # First call
        client1 = manager.get_client(
            user_id=1,
            exchange_name="binance",
            api_key="test-key",
            secret_key="test-secret",
        )

        # Second call with force_new
        client2 = manager.get_client(
            user_id=1,
            exchange_name="binance",
            api_key="test-key",
            secret_key="test-secret",
            force_new=True,
        )

        assert client2 == mock_client2
        assert mock_create.call_count == 2

    @patch("src.services.exchanges.factory.ExchangeFactory.create")
    def test_get_client_different_users(self, mock_create):
        """Test get_client creates separate clients for different users."""
        mock_client1 = MagicMock()
        mock_client2 = MagicMock()
        mock_create.side_effect = [mock_client1, mock_client2]

        manager = ExchangeManager()

        client1 = manager.get_client(
            user_id=1,
            exchange_name="binance",
            api_key="key1",
            secret_key="secret1",
        )

        client2 = manager.get_client(
            user_id=2,
            exchange_name="binance",
            api_key="key2",
            secret_key="secret2",
        )

        assert client1 == mock_client1
        assert client2 == mock_client2
        assert mock_create.call_count == 2

    @pytest.mark.asyncio
    async def test_close_client(self):
        """Test close_client removes and closes client."""
        mock_client = AsyncMock()

        manager = ExchangeManager()
        manager._clients["1:binance"] = mock_client

        await manager.close_client(user_id=1, exchange_name="binance")

        assert "1:binance" not in manager._clients
        mock_client.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_close_all(self):
        """Test close_all closes all clients."""
        mock_client1 = AsyncMock()
        mock_client2 = AsyncMock()

        manager = ExchangeManager()
        manager._clients["1:binance"] = mock_client1
        manager._clients["2:okx"] = mock_client2

        await manager.close_all()

        assert manager._clients == {}
        mock_client1.close.assert_awaited_once()
        mock_client2.close.assert_awaited_once()

    @patch("src.services.exchanges.factory.ExchangeFactory.create")
    def test_get_active_exchanges(self, mock_create):
        """Test get_active_exchanges returns correct counts."""
        manager = ExchangeManager()
        manager._clients = {
            "1:binance": MagicMock(),
            "2:binance": MagicMock(),
            "3:okx": MagicMock(),
        }

        result = manager.get_active_exchanges()

        assert result["binance"] == 2
        assert result["okx"] == 1


@pytest.mark.unit
class TestBaseExchangeInterface:
    """Tests for BaseExchange interface compliance."""

    def test_base_exchange_is_abstract(self):
        """Test BaseExchange cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseExchange("key", "secret")

    @patch("src.services.exchanges.binance.ccxt.binance")
    def test_binance_implements_interface(self, mock_ccxt):
        """Test BinanceExchange implements all required methods."""
        mock_ccxt.return_value = MagicMock()
        client = BinanceExchange("key", "secret")

        # Check required methods exist
        assert hasattr(client, "get_balance")
        assert hasattr(client, "get_futures_balance")
        assert hasattr(client, "create_order")
        assert hasattr(client, "cancel_order")
        assert hasattr(client, "get_order")
        assert hasattr(client, "get_open_orders")
        assert hasattr(client, "get_positions")
        assert hasattr(client, "close_position")
        assert hasattr(client, "get_ticker")
        assert hasattr(client, "get_candles")
        assert hasattr(client, "set_leverage")
        assert hasattr(client, "get_funding_rate")
        assert hasattr(client, "close")

    @patch("src.services.exchanges.okx.ccxt.okx")
    def test_okx_implements_interface(self, mock_ccxt):
        """Test OKXExchange implements all required methods."""
        mock_ccxt.return_value = MagicMock()
        client = OKXExchange("key", "secret", "passphrase")

        assert hasattr(client, "get_balance")
        assert hasattr(client, "get_futures_balance")
        assert hasattr(client, "create_order")
        assert hasattr(client, "get_positions")
        assert hasattr(client, "close")

    @patch("src.services.exchanges.bybit.ccxt.bybit")
    def test_bybit_implements_interface(self, mock_ccxt):
        """Test BybitExchange implements all required methods."""
        mock_ccxt.return_value = MagicMock()
        client = BybitExchange("key", "secret")

        assert hasattr(client, "get_balance")
        assert hasattr(client, "get_futures_balance")
        assert hasattr(client, "create_order")
        assert hasattr(client, "get_positions")
        assert hasattr(client, "close")

    @patch("src.services.exchanges.gateio.ccxt.gateio")
    def test_gateio_implements_interface(self, mock_ccxt):
        """Test GateioExchange implements all required methods."""
        mock_ccxt.return_value = MagicMock()
        client = GateioExchange("key", "secret")

        assert hasattr(client, "get_balance")
        assert hasattr(client, "get_futures_balance")
        assert hasattr(client, "create_order")
        assert hasattr(client, "get_positions")
        assert hasattr(client, "close")
