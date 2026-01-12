"""
Signal Tracker Service
트레이딩 시그널 추적 및 기록
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.models import TradingSignal
from ..utils.structured_logging import get_logger

logger = logging.getLogger(__name__)
structured_logger = get_logger(__name__)


class SignalTracker:
    """트레이딩 시그널 추적 및 기록"""

    @staticmethod
    async def record_signal(
        session: AsyncSession,
        user_id: int,
        symbol: str,
        signal_type: str,
        timeframe: str,
        strategy_id: Optional[int] = None,
        price: Optional[float] = None,
        indicators: Optional[dict] = None,
        confidence: Optional[float] = None,
    ) -> Optional[TradingSignal]:
        """
        시그널 기록

        Args:
            session: Database session
            user_id: 사용자 ID
            symbol: 거래 심볼 (예: BTCUSDT)
            signal_type: 시그널 타입 (BUY, SELL, HOLD)
            timeframe: 타임프레임 (1m, 5m, 15m, 1h, 4h, 1d)
            strategy_id: 전략 ID (optional)
            price: 시그널 발생 시점의 가격
            indicators: 시그널 생성 시 사용된 지표 값 (예: {"rsi": 65, "macd": 0.05})
            confidence: 신호 신뢰도 (0.0 ~ 1.0)

        Returns:
            생성된 TradingSignal 객체 또는 None (에러 발생 시)
        """
        try:
            # 입력 검증
            valid_signal_types = ['BUY', 'SELL', 'HOLD']
            signal_type_upper = signal_type.upper()

            if signal_type_upper not in valid_signal_types:
                structured_logger.warning(
                    "signal_invalid_type",
                    f"Invalid signal type: {signal_type}",
                    user_id=user_id,
                    signal_type=signal_type,
                    symbol=symbol
                )
                return None

            # Confidence 검증 (0.0 ~ 1.0)
            if confidence is not None and (confidence < 0.0 or confidence > 1.0):
                structured_logger.warning(
                    "signal_invalid_confidence",
                    f"Invalid confidence value: {confidence}",
                    user_id=user_id,
                    confidence=confidence,
                    symbol=symbol
                )
                confidence = max(0.0, min(1.0, confidence))  # Clamp to valid range

            # Price 검증
            if price is not None and price <= 0:
                structured_logger.warning(
                    "signal_invalid_price",
                    f"Invalid price value: {price}",
                    user_id=user_id,
                    price=price,
                    symbol=symbol
                )
                price = None

            signal = TradingSignal(
                user_id=user_id,
                strategy_id=strategy_id,
                symbol=symbol,
                signal_type=signal_type_upper,
                timeframe=timeframe,
                price=price,
                indicators=indicators,
                confidence=confidence,
                timestamp=datetime.utcnow(),
            )

            session.add(signal)
            await session.commit()
            await session.refresh(signal)

            structured_logger.info(
                "signal_recorded",
                f"Signal recorded: {signal_type_upper} {symbol} @ {price}",
                user_id=user_id,
                signal_type=signal_type_upper,
                symbol=symbol,
                price=price,
                confidence=confidence,
                timeframe=timeframe,
                strategy_id=strategy_id
            )

            return signal

        except Exception as e:
            await session.rollback()
            structured_logger.error(
                "signal_record_failed",
                "Failed to record signal",
                user_id=user_id,
                signal_type=signal_type,
                symbol=symbol,
                error=str(e)
            )
            return None

    @staticmethod
    async def get_latest_signal(
        session: AsyncSession, user_id: int, symbol: Optional[str] = None
    ) -> Optional[TradingSignal]:
        """
        최근 시그널 조회

        Args:
            session: Database session
            user_id: 사용자 ID
            symbol: 거래 심볼 (optional, 지정하면 해당 심볼의 최근 시그널만 조회)

        Returns:
            최근 TradingSignal 객체 또는 None
        """
        try:
            query = select(TradingSignal).where(TradingSignal.user_id == user_id)

            if symbol:
                query = query.where(TradingSignal.symbol == symbol)

            query = query.order_by(TradingSignal.timestamp.desc()).limit(1)

            result = await session.execute(query)
            signal = result.scalar_one_or_none()

            if signal:
                logger.debug(
                    f"[SignalTracker] Latest signal for user {user_id}"
                    + (f" (symbol: {symbol})" if symbol else "")
                    + f": {signal.signal_type} at {signal.timestamp}"
                )

            return signal

        except Exception as e:
            logger.error(
                f"[SignalTracker] Error fetching latest signal: {e}", exc_info=True
            )
            return None

    @staticmethod
    async def get_recent_signals(
        session: AsyncSession,
        user_id: int,
        limit: int = 10,
        symbol: Optional[str] = None,
    ) -> list[TradingSignal]:
        """
        최근 시그널 목록 조회

        Args:
            session: Database session
            user_id: 사용자 ID
            limit: 조회할 시그널 개수 (기본: 10)
            symbol: 거래 심볼 (optional)

        Returns:
            TradingSignal 리스트
        """
        try:
            query = select(TradingSignal).where(TradingSignal.user_id == user_id)

            if symbol:
                query = query.where(TradingSignal.symbol == symbol)

            query = query.order_by(TradingSignal.timestamp.desc()).limit(limit)

            result = await session.execute(query)
            signals = result.scalars().all()

            logger.debug(
                f"[SignalTracker] Retrieved {len(signals)} recent signals for user {user_id}"
            )

            return list(signals)

        except Exception as e:
            logger.error(
                f"[SignalTracker] Error fetching recent signals: {e}", exc_info=True
            )
            return []

    @staticmethod
    async def get_signal_statistics(
        session: AsyncSession,
        user_id: int,
        days: int = 30,
        symbol: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        시그널 통계 조회

        Args:
            session: Database session
            user_id: 사용자 ID
            days: 조회 기간 (일 단위, 기본: 30일)
            symbol: 거래 심볼 (optional)

        Returns:
            시그널 통계 딕셔너리
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)

            query = select(TradingSignal).where(
                TradingSignal.user_id == user_id,
                TradingSignal.timestamp >= cutoff_date
            )

            if symbol:
                query = query.where(TradingSignal.symbol == symbol)

            result = await session.execute(query)
            signals = result.scalars().all()

            if not signals:
                return {
                    "total_signals": 0,
                    "buy_signals": 0,
                    "sell_signals": 0,
                    "hold_signals": 0,
                    "avg_confidence": 0.0,
                    "symbols_tracked": 0,
                    "period_days": days,
                }

            # 시그널 타입별 카운트
            buy_count = sum(1 for s in signals if s.signal_type == 'BUY')
            sell_count = sum(1 for s in signals if s.signal_type == 'SELL')
            hold_count = sum(1 for s in signals if s.signal_type == 'HOLD')

            # 평균 신뢰도 계산
            confidences = [s.confidence for s in signals if s.confidence is not None]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

            # 추적된 심볼 수
            unique_symbols = len(set(s.symbol for s in signals))

            # 시그널 빈도 (일평균)
            signals_per_day = len(signals) / days if days > 0 else 0

            structured_logger.info(
                "signal_statistics_calculated",
                f"Signal statistics for {days} days",
                user_id=user_id,
                total_signals=len(signals),
                buy_signals=buy_count,
                sell_signals=sell_count,
                period_days=days,
                symbol=symbol
            )

            return {
                "total_signals": len(signals),
                "buy_signals": buy_count,
                "sell_signals": sell_count,
                "hold_signals": hold_count,
                "avg_confidence": round(avg_confidence, 3),
                "symbols_tracked": unique_symbols,
                "period_days": days,
                "signals_per_day": round(signals_per_day, 2),
            }

        except Exception as e:
            structured_logger.error(
                "signal_statistics_failed",
                "Failed to calculate signal statistics",
                user_id=user_id,
                period_days=days,
                symbol=symbol,
                error=str(e)
            )
            return {
                "total_signals": 0,
                "buy_signals": 0,
                "sell_signals": 0,
                "hold_signals": 0,
                "avg_confidence": 0.0,
                "symbols_tracked": 0,
                "period_days": days,
                "signals_per_day": 0.0,
            }

    @staticmethod
    async def get_signal_accuracy(
        session: AsyncSession,
        user_id: int,
        days: int = 30,
        min_confidence: float = 0.5,
    ) -> Dict[str, Any]:
        """
        시그널 정확도 분석
        (추후 실제 거래 결과와 비교하여 정확도 계산 가능)

        Args:
            session: Database session
            user_id: 사용자 ID
            days: 조회 기간 (일 단위)
            min_confidence: 최소 신뢰도 임계값

        Returns:
            시그널 정확도 분석 결과
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)

            query = select(TradingSignal).where(
                TradingSignal.user_id == user_id,
                TradingSignal.timestamp >= cutoff_date,
                TradingSignal.confidence.isnot(None)
            )

            result = await session.execute(query)
            signals = result.scalars().all()

            if not signals:
                return {
                    "total_analyzed": 0,
                    "high_confidence_signals": 0,
                    "low_confidence_signals": 0,
                    "avg_confidence": 0.0,
                    "min_confidence_threshold": min_confidence,
                }

            # 신뢰도 기준 분류
            high_conf = [s for s in signals if s.confidence >= min_confidence]
            low_conf = [s for s in signals if s.confidence < min_confidence]

            avg_confidence = sum(s.confidence for s in signals) / len(signals)

            # 신뢰도 분포
            confidence_distribution = {
                "0.0-0.3": sum(1 for s in signals if s.confidence < 0.3),
                "0.3-0.5": sum(1 for s in signals if 0.3 <= s.confidence < 0.5),
                "0.5-0.7": sum(1 for s in signals if 0.5 <= s.confidence < 0.7),
                "0.7-0.9": sum(1 for s in signals if 0.7 <= s.confidence < 0.9),
                "0.9-1.0": sum(1 for s in signals if s.confidence >= 0.9),
            }

            structured_logger.info(
                "signal_accuracy_analyzed",
                f"Signal accuracy analysis for {days} days",
                user_id=user_id,
                total_analyzed=len(signals),
                high_confidence_count=len(high_conf),
                avg_confidence=round(avg_confidence, 3)
            )

            return {
                "total_analyzed": len(signals),
                "high_confidence_signals": len(high_conf),
                "low_confidence_signals": len(low_conf),
                "avg_confidence": round(avg_confidence, 3),
                "min_confidence_threshold": min_confidence,
                "confidence_distribution": confidence_distribution,
            }

        except Exception as e:
            structured_logger.error(
                "signal_accuracy_analysis_failed",
                "Failed to analyze signal accuracy",
                user_id=user_id,
                period_days=days,
                error=str(e)
            )
            return {
                "total_analyzed": 0,
                "high_confidence_signals": 0,
                "low_confidence_signals": 0,
                "avg_confidence": 0.0,
                "min_confidence_threshold": min_confidence,
            }
