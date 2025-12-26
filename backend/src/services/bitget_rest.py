"""
Bitget REST API Client
주문 실행, 포지션 관리, 잔고 조회
"""

import time
import hmac
import hashlib
import base64
import json
import logging
import asyncio
from typing import Optional, Dict, Any, List
from enum import Enum
import aiohttp

from ..utils.bitget_exceptions import (
    BitgetAPIError,
    BitgetRateLimitError,
    BitgetAuthenticationError,
    BitgetNetworkError,
    BitgetTimeoutError,
    classify_bitget_error,
)

logger = logging.getLogger(__name__)


class OrderSide(str, Enum):
    """주문 방향"""

    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    """주문 타입"""

    MARKET = "market"
    LIMIT = "limit"


class PositionSide(str, Enum):
    """포지션 방향"""

    LONG = "long"
    SHORT = "short"


class BitgetRestClient:
    """Bitget REST API 클라이언트"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        passphrase: Optional[str] = None,
    ):
        self.api_key = api_key
        self.api_secret = api_secret
        self.passphrase = passphrase

        self.base_url = "https://api.bitget.com"
        self.session: Optional[aiohttp.ClientSession] = None

    def _generate_signature(
        self, timestamp: str, method: str, request_path: str, body: str = ""
    ) -> str:
        """API 서명 생성"""
        message = timestamp + method + request_path + body
        mac = hmac.new(
            bytes(self.api_secret, encoding="utf8"),
            bytes(message, encoding="utf-8"),
            digestmod=hashlib.sha256,
        )
        return base64.b64encode(mac.digest()).decode()

    def _get_headers(
        self, method: str, request_path: str, body: str = ""
    ) -> Dict[str, str]:
        """API 요청 헤더 생성"""
        timestamp = str(int(time.time() * 1000))
        sign = self._generate_signature(timestamp, method, request_path, body)

        return {
            "ACCESS-KEY": self.api_key,
            "ACCESS-SIGN": sign,
            "ACCESS-TIMESTAMP": timestamp,
            "ACCESS-PASSPHRASE": self.passphrase,
            "Content-Type": "application/json",
            "locale": "en-US",
        }

    async def _ensure_session(self):
        """aiohttp 세션 생성 (없거나 다른 루프에 연결된 경우)"""
        import asyncio

        current_loop = asyncio.get_running_loop()

        # 세션이 없거나, 닫혔거나, 다른 루프에 연결된 경우 새로 생성
        needs_new_session = (
            self.session is None
            or self.session.closed
            or getattr(self.session, '_loop', None) is not current_loop
        )

        if needs_new_session:
            # 기존 세션이 있으면 닫기
            if self.session is not None and not self.session.closed:
                try:
                    await self.session.close()
                except Exception:
                    pass  # 다른 루프의 세션은 닫기 실패할 수 있음
            self.session = aiohttp.ClientSession()

    async def close(self):
        """세션 종료"""
        if self.session and not self.session.closed:
            await self.session.close()

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        body: Optional[Dict] = None,
        require_auth: bool = True,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ) -> Dict[str, Any]:
        """
        API 요청 (retry 로직 포함)

        Args:
            method: HTTP 메서드
            endpoint: API 엔드포인트
            params: Query 파라미터
            body: Request body
            require_auth: 인증 필요 여부
            max_retries: 최대 재시도 횟수
            retry_delay: 재시도 간격 (초)

        Returns:
            API 응답 데이터

        Raises:
            BitgetAPIError: Bitget API 에러
            BitgetNetworkError: 네트워크 에러
            BitgetTimeoutError: Timeout 에러
        """
        await self._ensure_session()

        url = self.base_url + endpoint
        request_path = endpoint

        # Query params
        if params:
            query_string = "&".join([f"{k}={v}" for k, v in params.items()])
            url += f"?{query_string}"
            request_path += f"?{query_string}"

        # Body
        body_str = ""
        if body:
            body_str = json.dumps(body)

        # 인증 헤더 생성 (require_auth가 True이고 API 키가 있을 때만)
        if require_auth and self.api_key:
            headers = self._get_headers(method, request_path, body_str)
        else:
            # Public API용 기본 헤더
            headers = {
                "Content-Type": "application/json",
                "locale": "en-US",
            }

        last_exception = None

        for attempt in range(max_retries):
            try:
                async with self.session.request(
                    method=method,
                    url=url,
                    headers=headers,
                    data=body_str if body else None,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as response:
                    # Read response text first to avoid ChunkedIteratorResult issues
                    text = await response.text()
                    result = json.loads(text) if text else {}

                    # Bitget API 응답 형식: {"code": "00000", "msg": "success", "data": {...}}
                    if result.get("code") == "00000":
                        # 성공 시 재시도 중이었다면 로그
                        if attempt > 0:
                            logger.info(
                                f"Request succeeded on attempt {attempt + 1}/{max_retries}"
                            )
                        return result.get("data", {})
                    else:
                        # Bitget API 에러
                        error_code = result.get("code", "unknown")
                        error_msg = result.get("msg", "Unknown error")

                        logger.error(
                            f"Bitget API error: [{error_code}] {error_msg} | Response: {result}"
                        )

                        # 에러 분류
                        exception = classify_bitget_error(error_code, error_msg)

                        # Rate Limit 에러는 재시도
                        if isinstance(exception, BitgetRateLimitError):
                            if attempt < max_retries - 1:
                                wait_time = retry_delay * (
                                    2**attempt
                                )  # Exponential backoff
                                logger.warning(
                                    f"Rate limit hit, retrying in {wait_time}s... (attempt {attempt + 1}/{max_retries})"
                                )
                                await asyncio.sleep(wait_time)
                                continue
                            else:
                                raise exception

                        # 인증 에러는 재시도하지 않음
                        if isinstance(exception, BitgetAuthenticationError):
                            raise exception

                        # 기타 에러는 재시도
                        if attempt < max_retries - 1:
                            logger.warning(
                                f"Request failed, retrying... (attempt {attempt + 1}/{max_retries})"
                            )
                            await asyncio.sleep(retry_delay)
                            continue
                        else:
                            raise exception

            except asyncio.TimeoutError as e:
                logger.error(f"Request timeout: {url}")
                last_exception = BitgetTimeoutError(
                    f"요청 시간이 초과되었습니다: {endpoint}"
                )
                if attempt < max_retries - 1:
                    logger.warning(
                        f"Timeout, retrying... (attempt {attempt + 1}/{max_retries})"
                    )
                    await asyncio.sleep(retry_delay)
                    continue

            except aiohttp.ClientError as e:
                logger.error(f"HTTP request failed: {e}")
                last_exception = BitgetNetworkError(f"네트워크 에러: {str(e)}")
                if attempt < max_retries - 1:
                    logger.warning(
                        f"Network error, retrying... (attempt {attempt + 1}/{max_retries})"
                    )
                    await asyncio.sleep(retry_delay)
                    continue

            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response: {e}")
                last_exception = BitgetAPIError(f"응답 파싱 실패: {str(e)}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                    continue

            except Exception as e:
                logger.error(f"Unexpected error: {e}", exc_info=True)
                last_exception = BitgetAPIError(f"예상치 못한 에러: {str(e)}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                    continue

        # 모든 재시도 실패
        if last_exception:
            raise last_exception
        else:
            raise BitgetAPIError("모든 재시도가 실패했습니다")

    # ==================== 계좌 관리 ====================

    async def get_account_info(
        self, product_type: str = "USDT-FUTURES"
    ) -> Dict[str, Any]:
        """
        계좌 정보 조회

        Args:
            product_type: 상품 타입 (USDT-FUTURES, COIN-FUTURES 등)

        Returns:
            계좌 정보 딕셔너리
        """
        endpoint = "/api/v2/mix/account/accounts"
        params = {"productType": product_type}

        result = await self._request("GET", endpoint, params=params)
        logger.info(f"Account info retrieved: {result}")
        return result

    async def fetch_balance(
        self, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        잔고 조회 (CCXT 호환 형식)

        Args:
            params: 추가 파라미터 (type: 'swap' 등)

        Returns:
            CCXT 스타일의 잔고 딕셔너리
        """
        account_type = params.get("type", "swap") if params else "swap"
        product_type = "USDT-FUTURES" if account_type == "swap" else "COIN-FUTURES"

        account_info = await self.get_account_info(product_type=product_type)

        # CCXT 형식으로 변환
        balance_dict = {}
        # API 응답이 직접 배열이거나 data 키 안에 배열일 수 있음
        accounts = (
            account_info
            if isinstance(account_info, list)
            else account_info.get("data", [])
        )

        if len(accounts) > 0:
            account_data = accounts[0]
            usdt_info = {
                "free": float(account_data.get("available", 0)),
                "used": float(account_data.get("locked", 0)),
                "total": float(account_data.get("accountEquity", 0)),
            }
            balance_dict["USDT"] = usdt_info

        logger.info(f"Fetched balance: {balance_dict}")
        return balance_dict

    async def get_positions(
        self, product_type: str = "USDT-FUTURES", symbol: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        포지션 조회

        Args:
            product_type: 상품 타입
            symbol: 거래쌍 (선택사항, 없으면 전체 조회)

        Returns:
            포지션 리스트
        """
        endpoint = "/api/v2/mix/position/all-position"
        params = {"productType": product_type}

        if symbol:
            params["symbol"] = symbol

        result = await self._request("GET", endpoint, params=params)
        positions = result if isinstance(result, list) else []
        logger.info(f"Positions retrieved: {len(positions)} positions")
        return positions

    async def get_single_position(
        self, symbol: str, margin_coin: str = "USDT"
    ) -> Dict[str, Any]:
        """
        특정 포지션 조회

        Args:
            symbol: 거래쌍 (예: BTCUSDT)
            margin_coin: 마진 코인

        Returns:
            포지션 정보
        """
        endpoint = "/api/v2/mix/position/single-position"
        params = {"symbol": symbol, "marginCoin": margin_coin}

        result = await self._request("GET", endpoint, params=params)
        logger.info(f"Position for {symbol}: {result}")
        return result

    # ==================== 주문 실행 ====================

    async def place_order(
        self,
        symbol: str,
        side: OrderSide,
        order_type: OrderType,
        size: float,
        price: Optional[float] = None,
        margin_coin: str = "USDT",
        client_order_id: Optional[str] = None,
        reduce_only: bool = False,
    ) -> Dict[str, Any]:
        """
        주문 실행

        Args:
            symbol: 거래쌍 (예: BTCUSDT)
            side: 주문 방향 (buy/sell)
            order_type: 주문 타입 (market/limit)
            size: 주문 수량 (계약 수)
            price: 지정가 (limit 주문 시 필수)
            margin_coin: 마진 코인
            client_order_id: 사용자 정의 주문 ID
            reduce_only: 포지션 감소 전용 (청산 시 True)

        Returns:
            주문 응답
        """
        endpoint = "/api/v2/mix/order/place-order"

        # 주문 데이터
        order_data = {
            "symbol": symbol,
            "productType": "USDT-FUTURES",  # REQUIRED by Bitget API v2
            "marginCoin": margin_coin,
            "marginMode": "crossed",  # crossed (교차) 또는 isolated (격리)
            "side": side.value,
            "orderType": order_type.value,
            "size": str(size),
        }

        # 지정가 주문이면 가격 필수
        if order_type == OrderType.LIMIT:
            if price is None:
                raise ValueError("Price is required for limit orders")
            order_data["price"] = str(price)

        # 사용자 정의 주문 ID
        if client_order_id:
            order_data["clientOid"] = client_order_id

        # Reduce only (청산 전용)
        if reduce_only:
            order_data["reduceOnly"] = "YES"

        result = await self._request("POST", endpoint, body=order_data)
        logger.info(f"Order placed: {result}")
        return result

    async def place_market_order(
        self,
        symbol: str,
        side: OrderSide,
        size: float,
        margin_coin: str = "USDT",
        reduce_only: bool = False,
    ) -> Dict[str, Any]:
        """
        시장가 주문

        Args:
            symbol: 거래쌍
            side: 주문 방향
            size: 수량
            margin_coin: 마진 코인
            reduce_only: 포지션 감소 전용

        Returns:
            주문 응답
        """
        return await self.place_order(
            symbol=symbol,
            side=side,
            order_type=OrderType.MARKET,
            size=size,
            margin_coin=margin_coin,
            reduce_only=reduce_only,
        )

    async def place_limit_order(
        self,
        symbol: str,
        side: OrderSide,
        size: float,
        price: float,
        margin_coin: str = "USDT",
        reduce_only: bool = False,
    ) -> Dict[str, Any]:
        """
        지정가 주문

        Args:
            symbol: 거래쌍
            side: 주문 방향
            size: 수량
            price: 가격
            margin_coin: 마진 코인
            reduce_only: 포지션 감소 전용

        Returns:
            주문 응답
        """
        return await self.place_order(
            symbol=symbol,
            side=side,
            order_type=OrderType.LIMIT,
            size=size,
            price=price,
            margin_coin=margin_coin,
            reduce_only=reduce_only,
        )

    async def cancel_order(
        self, symbol: str, order_id: str, margin_coin: str = "USDT"
    ) -> Dict[str, Any]:
        """
        주문 취소

        Args:
            symbol: 거래쌍
            order_id: 주문 ID
            margin_coin: 마진 코인

        Returns:
            취소 응답
        """
        endpoint = "/api/v2/mix/order/cancel-order"
        body = {"symbol": symbol, "orderId": order_id, "marginCoin": margin_coin}

        result = await self._request("POST", endpoint, body=body)
        logger.info(f"Order cancelled: {order_id}")
        return result

    async def cancel_all_orders(
        self, symbol: str, margin_coin: str = "USDT"
    ) -> Dict[str, Any]:
        """
        모든 주문 취소

        Args:
            symbol: 거래쌍
            margin_coin: 마진 코인

        Returns:
            취소 응답
        """
        endpoint = "/api/v2/mix/order/cancel-all-orders"
        body = {"productType": "USDT-FUTURES", "marginCoin": margin_coin}

        if symbol:
            body["symbol"] = symbol

        result = await self._request("POST", endpoint, body=body)
        logger.info(f"All orders cancelled for {symbol}")
        return result

    async def get_open_orders(
        self, symbol: Optional[str] = None, product_type: str = "USDT-FUTURES"
    ) -> List[Dict[str, Any]]:
        """
        미체결 주문 조회

        Args:
            symbol: 거래쌍 (선택사항)
            product_type: 상품 타입

        Returns:
            주문 리스트
        """
        endpoint = "/api/v2/mix/order/orders-pending"
        params = {"productType": product_type}

        if symbol:
            params["symbol"] = symbol

        result = await self._request("GET", endpoint, params=params)
        orders = result.get("entrustedList", []) if isinstance(result, dict) else []
        logger.info(f"Open orders: {len(orders)} orders")
        return orders

    async def get_order_history(
        self,
        symbol: str,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        주문 히스토리 조회

        Args:
            symbol: 거래쌍
            start_time: 시작 시간 (ms)
            end_time: 종료 시간 (ms)
            limit: 조회 개수

        Returns:
            주문 히스토리
        """
        endpoint = "/api/v2/mix/order/history"
        params = {"symbol": symbol, "pageSize": str(limit)}

        if start_time:
            params["startTime"] = str(start_time)
        if end_time:
            params["endTime"] = str(end_time)

        result = await self._request("GET", endpoint, params=params)
        orders = result.get("orderList", []) if isinstance(result, dict) else []
        logger.info(f"Order history: {len(orders)} orders")
        return orders

    # ==================== 포지션 관리 ====================

    async def close_position(
        self,
        symbol: str,
        side: PositionSide,
        size: Optional[float] = None,
        margin_coin: str = "USDT",
    ) -> Dict[str, Any]:
        """
        포지션 청산

        Args:
            symbol: 거래쌍
            side: 포지션 방향 (long/short)
            size: 청산 수량 (None이면 전체 청산)
            margin_coin: 마진 코인

        Returns:
            청산 응답
        """
        # 포지션 조회
        result = await self.get_single_position(symbol, margin_coin)

        # API 응답이 리스트인 경우 처리
        positions = []
        if isinstance(result, list):
            positions = result
        elif isinstance(result, dict):
            if result.get("data"):
                positions = (
                    result["data"]
                    if isinstance(result["data"], list)
                    else [result["data"]]
                )
            else:
                positions = [result]

        # 요청한 방향의 포지션 찾기
        target_side = side.value.lower()  # "long" or "short"
        position = None

        for pos in positions:
            pos_side = (pos.get("holdSide") or pos.get("posSide") or "").lower()
            pos_size = float(pos.get("total") or pos.get("available") or 0)

            # 방향이 일치하고 수량이 있는 포지션
            if pos_side == target_side and pos_size > 0:
                position = pos
                break

        if not position:
            logger.warning(f"No {side.value} position found for {symbol}")
            return {"success": False, "message": f"No {side.value} position to close"}

        # 포지션 수량
        if size is None:
            size = float(position.get("total") or position.get("available") or 0)

        if size == 0:
            logger.warning(f"Position size is 0 for {symbol} {side.value}")
            return {"success": False, "message": "Position size is 0"}

        # 청산 주문 (반대 방향)
        order_side = OrderSide.SELL if side == PositionSide.LONG else OrderSide.BUY

        logger.info(f"Closing {side.value} position for {symbol}: size={size}")

        return await self.place_market_order(
            symbol=symbol,
            side=order_side,
            size=size,
            margin_coin=margin_coin,
            reduce_only=True,
        )

    async def set_leverage(
        self, symbol: str, leverage: int, margin_coin: str = "USDT"
    ) -> Dict[str, Any]:
        """
        레버리지 설정

        Args:
            symbol: 거래쌍
            leverage: 레버리지 배수
            margin_coin: 마진 코인

        Returns:
            설정 응답
        """
        endpoint = "/api/v2/mix/account/set-leverage"
        body = {
            "symbol": symbol,
            "productType": "USDT-FUTURES",  # Bitget API v2 필수 파라미터
            "marginCoin": margin_coin,
            "leverage": str(leverage),
            "holdSide": "long",  # long 또는 short, 교차마진일 경우 long으로 설정
        }

        result = await self._request("POST", endpoint, body=body)
        logger.info(f"Leverage set to {leverage}x for {symbol}")
        return result

    async def set_position_mode(
        self, product_type: str = "USDT-FUTURES", hold_mode: str = "double_hold"
    ) -> Dict[str, Any]:
        """
        포지션 모드 설정

        Args:
            product_type: 상품 타입
            hold_mode: 포지션 모드 (single_hold / double_hold)

        Returns:
            설정 응답
        """
        endpoint = "/api/v2/mix/account/set-position-mode"
        body = {"productType": product_type, "holdMode": hold_mode}

        result = await self._request("POST", endpoint, body=body)
        logger.info(f"Position mode set to {hold_mode}")
        return result

    # ==================== 시장 데이터 ====================

    async def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """
        현재가 조회

        Args:
            symbol: 거래쌍

        Returns:
            Ticker 정보
        """
        endpoint = "/api/v2/mix/market/ticker"
        params = {
            "symbol": symbol,
            "productType": "USDT-FUTURES",  # Bitget v2 API requires productType
        }

        result = await self._request("GET", endpoint, params=params)
        logger.debug(f"Ticker for {symbol}: {result}")
        return result

    async def get_orderbook(self, symbol: str, limit: int = 100) -> Dict[str, Any]:
        """
        호가 조회

        Args:
            symbol: 거래쌍
            limit: 호가 개수

        Returns:
            호가 정보
        """
        endpoint = "/api/v2/mix/market/orderbook"
        params = {"symbol": symbol, "limit": str(limit)}

        result = await self._request("GET", endpoint, params=params)
        return result

    async def get_historical_candles(
        self,
        symbol: str,
        interval: str = "1h",
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        limit: int = 1000,
    ) -> List[Dict[str, Any]]:
        """
        과거 캔들 데이터 조회 (단일 요청)

        Args:
            symbol: 거래쌍 (예: BTCUSDT)
            interval: 캔들 간격 (1m, 5m, 15m, 30m, 1h, 4h, 1D 등)
            start_time: 시작 날짜 (YYYY-MM-DD)
            end_time: 종료 날짜 (YYYY-MM-DD)
            limit: 조회 개수 (최대 1000)

        Returns:
            캔들 데이터 리스트
        """
        from datetime import datetime, timedelta, timezone

        endpoint = "/api/v2/mix/market/candles"

        # UTC 기준 현재 시간
        now_utc = datetime.now(timezone.utc)

        # 종료 시간 (UTC)
        if end_time:
            end_dt = datetime.strptime(end_time, "%Y-%m-%d").replace(
                hour=23, minute=59, second=59, tzinfo=timezone.utc
            )
            # 미래 시간이면 현재로 조정
            if end_dt > now_utc:
                end_dt = now_utc
            end_ts = str(int(end_dt.timestamp() * 1000))
        else:
            end_ts = str(int(now_utc.timestamp() * 1000))

        # Bitget API granularity 형식 변환 (명시적 매핑)
        # Bitget 지원: 1m,3m,5m,15m,30m,1H,4H,6H,12H,1D,1W,1M
        INTERVAL_MAP = {
            "1m": "1m",
            "3m": "3m",
            "5m": "5m",
            "15m": "15m",
            "30m": "30m",
            "1h": "1H",
            "4h": "4H",
            "6h": "6H",
            "12h": "12H",
            "1d": "1D",
            "1D": "1D",
            "1w": "1W",
            "1W": "1W",
        }
        granularity = INTERVAL_MAP.get(
            interval, interval.replace("h", "H").replace("d", "D")
        )

        # Bitget API v2는 endTime 기준으로 이전 데이터를 가져옴
        params = {
            "symbol": symbol,
            "productType": "USDT-FUTURES",
            "granularity": granularity,
            "endTime": end_ts,
            "limit": str(min(limit, 1000)),  # Bitget API v2 최대 1000
        }

        result = await self._request("GET", endpoint, params=params, require_auth=False)

        candles = []
        if isinstance(result, list):
            for candle in result:
                if len(candle) >= 6:
                    candles.append(
                        {
                            "timestamp": int(candle[0]),
                            "open": float(candle[1]),
                            "high": float(candle[2]),
                            "low": float(candle[3]),
                            "close": float(candle[4]),
                            "volume": float(candle[5]),
                        }
                    )

        logger.info(f"Retrieved {len(candles)} candles for {symbol} ({interval})")
        return candles

    async def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str = "1h",
        since: Optional[int] = None,
        limit: int = 200,
        params: Optional[Dict] = None,
    ) -> List[List]:
        """
        CCXT 호환 OHLCV 데이터 조회

        CCXT 스타일의 fetch_ohlcv 메서드를 제공하여 기존 전략과의 호환성 유지

        Args:
            symbol: 거래쌍 (예: BTCUSDT, BTC/USDT)
            timeframe: 캔들 간격 (1m, 5m, 15m, 30m, 1h, 4h, 1d)
            since: 시작 타임스탬프 (ms) - 미사용, 호환성용
            limit: 조회 개수 (최대 1000)
            params: 추가 파라미터 - 미사용, 호환성용

        Returns:
            CCXT 형식의 OHLCV 리스트 [[timestamp, open, high, low, close, volume], ...]
        """
        # 심볼 정규화 (BTC/USDT -> BTCUSDT)
        normalized_symbol = symbol.replace("/", "")

        # 기존 메서드 호출
        candles = await self.get_historical_candles(
            symbol=normalized_symbol,
            interval=timeframe,
            limit=limit,
        )

        # CCXT 형식으로 변환 [[timestamp, open, high, low, close, volume], ...]
        ohlcv = []
        for candle in candles:
            ohlcv.append([
                candle["timestamp"],
                candle["open"],
                candle["high"],
                candle["low"],
                candle["close"],
                candle["volume"],
            ])

        return ohlcv

    async def get_all_historical_candles(
        self,
        symbol: str,
        interval: str = "1h",
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        max_candles: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        전체 과거 캔들 데이터 조회 (페이지네이션, Bitget 오픈 ~ 현재)

        Args:
            symbol: 거래쌍 (예: BTCUSDT)
            interval: 캔들 간격 (1m, 5m, 15m, 30m, 1h, 4h, 1D 등)
            start_time: 시작 날짜 (YYYY-MM-DD), 없으면 Bitget 오픈일(2020-05-01)
            end_time: 종료 날짜 (YYYY-MM-DD), 없으면 현재
            max_candles: 최대 캔들 수 제한 (None이면 무제한)

        Returns:
            캔들 데이터 리스트 (오래된 것부터 최신순)
        """
        from datetime import datetime, timedelta, timezone

        # Bitget Futures 오픈일 (2020년 5월)
        BITGET_FUTURES_LAUNCH = "2020-05-01"

        # 시작/종료 시간 설정
        if not start_time:
            start_time = BITGET_FUTURES_LAUNCH

        if not end_time:
            end_time = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        start_dt = datetime.strptime(start_time, "%Y-%m-%d").replace(
            tzinfo=timezone.utc
        )
        end_dt = datetime.strptime(end_time, "%Y-%m-%d").replace(
            hour=23, minute=59, second=59, tzinfo=timezone.utc
        )

        # 현재 시간보다 미래인 경우 조정
        now_utc = datetime.now(timezone.utc)
        if end_dt > now_utc:
            end_dt = now_utc

        logger.info(f"📊 Fetching ALL historical candles for {symbol} ({interval})")
        logger.info(f"   Period: {start_time} ~ {end_time}")

        # Bitget API granularity 형식 변환
        INTERVAL_MAP = {
            "1m": "1m",
            "3m": "3m",
            "5m": "5m",
            "15m": "15m",
            "30m": "30m",
            "1h": "1H",
            "4h": "4H",
            "6h": "6H",
            "12h": "12H",
            "1d": "1D",
            "1D": "1D",
            "1w": "1W",
            "1W": "1W",
        }
        granularity = INTERVAL_MAP.get(
            interval, interval.replace("h", "H").replace("d", "D")
        )

        all_candles = []
        current_end_ts = int(end_dt.timestamp() * 1000)
        start_ts = int(start_dt.timestamp() * 1000)
        batch_count = 0
        rate_limit_delay = 0.3  # 300ms 딜레이

        endpoint = "/api/v2/mix/market/candles"

        while current_end_ts > start_ts:
            batch_count += 1

            params = {
                "symbol": symbol,
                "productType": "USDT-FUTURES",
                "granularity": granularity,
                "endTime": str(current_end_ts),
                "limit": "1000",
            }

            try:
                result = await self._request(
                    "GET", endpoint, params=params, require_auth=False
                )

                if not result or not isinstance(result, list) or len(result) == 0:
                    logger.info(f"   No more candles available (batch {batch_count})")
                    break

                # 캔들 파싱
                candles = []
                for candle in result:
                    if len(candle) >= 6:
                        candles.append(
                            {
                                "timestamp": int(candle[0]),
                                "open": float(candle[1]),
                                "high": float(candle[2]),
                                "low": float(candle[3]),
                                "close": float(candle[4]),
                                "volume": float(candle[5]),
                            }
                        )

                # 결과 추가 (중복 제거)
                existing_timestamps = {c["timestamp"] for c in all_candles}
                new_candles = [
                    c for c in candles if c["timestamp"] not in existing_timestamps
                ]
                all_candles.extend(new_candles)

                # 진행률 로깅 (10배치마다)
                if batch_count % 10 == 0:
                    logger.info(
                        f"   Batch {batch_count}: {len(all_candles)} candles collected..."
                    )

                # 다음 배치를 위해 가장 오래된 캔들 이전으로 이동
                oldest_timestamp = min(c["timestamp"] for c in candles)

                # 시작 타임스탬프에 도달했으면 종료
                if oldest_timestamp <= start_ts:
                    logger.info(f"   Reached start date {start_time}")
                    break

                current_end_ts = oldest_timestamp - 1

                # 최대 캔들 수 제한 확인
                if max_candles and len(all_candles) >= max_candles:
                    logger.info(f"   Reached max_candles limit: {max_candles}")
                    all_candles = all_candles[:max_candles]
                    break

                # Rate Limit 방지
                await asyncio.sleep(rate_limit_delay)

            except Exception as e:
                logger.error(f"   Error fetching batch {batch_count}: {e}")
                # 에러 발생해도 이미 수집한 데이터는 반환
                break

        # 시간순 정렬 (오래된 것부터)
        all_candles.sort(key=lambda x: x["timestamp"])

        # 지정된 기간 외의 데이터 필터링
        end_ts = int(end_dt.timestamp() * 1000)
        all_candles = [c for c in all_candles if start_ts <= c["timestamp"] <= end_ts]

        logger.info(
            f"✅ Total {len(all_candles)} candles fetched for {symbol} ({interval})"
        )
        logger.info(f"   Period: {start_time} ~ {end_time} ({batch_count} API calls)")

        return all_candles


# 싱글톤 인스턴스 관리
_rest_clients: Dict[str, BitgetRestClient] = {}


def get_bitget_rest(api_key: str, api_secret: str, passphrase: str) -> BitgetRestClient:
    """Bitget REST 클라이언트 인스턴스 반환 (캐싱)"""
    # Issue #2.4: API 키를 해시하여 캐시 키로 사용 (보안 강화)
    client_id = hashlib.sha256(f"{api_key}:{api_secret}".encode()).hexdigest()[:16]

    if client_id not in _rest_clients:
        _rest_clients[client_id] = BitgetRestClient(api_key, api_secret, passphrase)

    return _rest_clients[client_id]


async def close_all_rest_clients():
    """
    모든 REST 클라이언트의 aiohttp 세션을 명시적으로 종료

    Issue #2.2: 장시간 운영 시 TCP 커넥션 누수 방지를 위해
    애플리케이션 종료 시 lifespan에서 호출되어야 함
    """
    global _rest_clients

    if not _rest_clients:
        logger.info("No REST clients to close")
        return

    close_count = 0
    for client_id, client in _rest_clients.items():
        try:
            await client.close()
            close_count += 1
            logger.debug(f"Closed REST client: {client_id[:8]}...")
        except Exception as e:
            logger.warning(f"Error closing REST client {client_id[:8]}...: {e}")

    _rest_clients.clear()
    logger.info(f"✅ Closed {close_count} Bitget REST client(s)")
