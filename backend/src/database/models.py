from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Enum as SQLEnum,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=True)  # 소셜 로그인 사용자는 비밀번호 없음
    name = Column(String(100), nullable=True)  # 사용자 이름
    phone = Column(String(20), nullable=True)  # 전화번호
    role = Column(String, default="user", nullable=False)  # 'user' or 'admin'
    exchange = Column(
        String, default="bitget", nullable=False
    )  # 'bitget', 'binance', 'okx'
    is_active = Column(Boolean, default=True, nullable=False)  # 계정 활성화 상태
    suspended_at = Column(DateTime, nullable=True)  # 계정 정지 시각

    # 소셜 로그인 정보
    oauth_provider = Column(String(20), nullable=True)  # 'google', 'kakao', None(일반)
    oauth_id = Column(String(255), nullable=True, index=True)  # 소셜 계정 고유 ID
    profile_image = Column(String(500), nullable=True)  # 프로필 이미지 URL

    # 2FA (Two-Factor Authentication) 설정
    totp_secret = Column(String, nullable=True)  # 암호화된 TOTP 시크릿 키
    is_2fa_enabled = Column(Boolean, default=False, nullable=False)  # 2FA 활성화 여부

    created_at = Column(DateTime, default=datetime.utcnow)

    api_keys = relationship(
        "ApiKey", back_populates="user", cascade="all, delete-orphan"
    )
    strategies = relationship(
        "Strategy", back_populates="user", cascade="all, delete-orphan"
    )
    trades = relationship("Trade", back_populates="user", cascade="all, delete-orphan")
    positions = relationship(
        "Position", back_populates="user", cascade="all, delete-orphan"
    )
    equities = relationship(
        "Equity", back_populates="user", cascade="all, delete-orphan"
    )


class ApiKey(Base):
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    encrypted_api_key = Column(Text, nullable=False)
    encrypted_secret_key = Column(Text, nullable=False)
    encrypted_passphrase = Column(Text, nullable=True)

    user = relationship("User", back_populates="api_keys")


class Strategy(Base):
    __tablename__ = "strategies"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    code = Column(Text, nullable=False)
    params = Column(Text, nullable=True)
    is_active = Column(Boolean, default=False, nullable=False)

    user = relationship("User", back_populates="strategies")


class BotStatus(Base):
    __tablename__ = "bot_status"

    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    strategy_id = Column(Integer, ForeignKey("strategies.id"))
    is_running = Column(Boolean, default=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ExitReason(str, Enum):
    take_profit = "take_profit"
    stop_loss = "stop_loss"
    signal_reverse = "signal_reverse"
    manual = "manual"
    liquidation = "liquidation"


class Trade(Base):
    __tablename__ = "trades"

    # 성능 최적화를 위한 인덱스 정의
    __table_args__ = (
        # 사용자별 거래 내역 조회용 (ORDER BY created_at DESC)
        Index("idx_trade_user_created", "user_id", "created_at"),
        # 심볼별 거래 조회용
        Index("idx_trade_symbol", "symbol"),
        # 전략별 거래 조회용
        Index("idx_trade_strategy", "strategy_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    symbol = Column(String, nullable=False)
    side = Column(String, nullable=False)
    qty = Column(Float, nullable=False)
    entry_price = Column(Numeric(18, 8), nullable=False)
    exit_price = Column(Numeric(18, 8), nullable=True)
    pnl = Column(Numeric(18, 8), default=0)
    pnl_percent = Column(Float, default=0)
    strategy_id = Column(Integer, ForeignKey("strategies.id"), nullable=True)
    leverage = Column(Integer, default=1)
    exit_reason = Column(SQLEnum(ExitReason), default=ExitReason.manual)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="trades")


class Position(Base):
    __tablename__ = "positions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    symbol = Column(String, nullable=False)
    entry_price = Column(Numeric(18, 8), nullable=False)
    size = Column(Float, nullable=False)
    side = Column(String, nullable=False)
    pnl = Column(Numeric(18, 8), default=0)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="positions")


class Equity(Base):
    __tablename__ = "equities"

    # 성능 최적화를 위한 인덱스 정의
    __table_args__ = (
        # 사용자별 자산 기록 조회용 (시간순 정렬)
        Index("idx_equity_user_time", "user_id", "timestamp"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    value = Column(Numeric(18, 8), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="equities")


class BotLog(Base):
    __tablename__ = "bot_logs"

    # 성능 최적화를 위한 인덱스 정의
    __table_args__ = (
        # 사용자별 로그 조회용 (최신순 정렬)
        Index("idx_botlog_user_created", "user_id", "created_at"),
        # 이벤트 타입별 조회용
        Index("idx_botlog_event_type", "event_type"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    event_type = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class BotConfig(Base):
    __tablename__ = "bot_config"

    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    max_risk_percent = Column(Float, default=1.0)
    leverage = Column(Integer, default=5)
    auto_tp = Column(Float, default=3.0)
    auto_sl = Column(Float, default=1.5)


class OpenOrder(Base):
    __tablename__ = "open_orders"

    # 성능 최적화를 위한 인덱스 정의
    __table_args__ = (
        # 사용자별 미체결 주문 조회용
        Index("idx_openorder_user_status", "user_id", "status"),
        # 심볼별 주문 조회용
        Index("idx_openorder_symbol", "symbol"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    symbol = Column(String, nullable=False)
    side = Column(String, nullable=False)
    qty = Column(Float, nullable=False)
    status = Column(String, default="open")
    created_at = Column(DateTime, default=datetime.utcnow)


class BacktestResult(Base):
    __tablename__ = "backtest_results"

    # 성능 최적화를 위한 인덱스 정의
    __table_args__ = (
        # 사용자별 백테스트 결과 조회용 (최신순 정렬)
        Index("idx_backtest_user_created", "user_id", "created_at"),
        # 실행 중인 백테스트 조회용
        Index("idx_backtest_status", "status"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    pair = Column(String, nullable=True)
    timeframe = Column(String, nullable=True)
    initial_balance = Column(Float, nullable=False)
    final_balance = Column(Float, nullable=False)
    metrics = Column(Text, nullable=True)
    equity_curve = Column(Text, nullable=True)
    params = Column(Text, nullable=True)
    status = Column(String, default="queued")  # queued, running, completed, failed
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", backref="backtest_results")
    trades = relationship(
        "BacktestTrade", back_populates="result", cascade="all, delete-orphan"
    )


class BacktestTrade(Base):
    __tablename__ = "backtest_trades"

    id = Column(Integer, primary_key=True, index=True)
    result_id = Column(Integer, ForeignKey("backtest_results.id"), nullable=False)
    timestamp = Column(String, nullable=True)
    side = Column(String, nullable=False)
    direction = Column(String, nullable=False)
    entry_price = Column(Float, nullable=True)
    exit_price = Column(Float, nullable=True)
    qty = Column(Float, nullable=True, default=1.0)
    fee = Column(Float, nullable=True, default=0.0)
    pnl = Column(Float, nullable=True, default=0.0)

    result = relationship("BacktestResult", back_populates="trades")


class SystemAlert(Base):
    """시스템 알림 모델"""

    __tablename__ = "system_alerts"

    __table_args__ = (
        Index("idx_alert_user_level", "user_id", "level"),
        Index("idx_alert_resolved", "is_resolved"),
        Index("idx_alert_created", "created_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    level = Column(String, nullable=False)  # ERROR, WARNING, INFO
    message = Column(Text, nullable=False)
    is_resolved = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    resolved_at = Column(DateTime, nullable=True)

    user = relationship("User", backref="alerts")


class RiskSettings(Base):
    """리스크 관리 설정 모델"""

    __tablename__ = "risk_settings"

    __table_args__ = (
        CheckConstraint("daily_loss_limit > 0", name="check_positive_loss_limit"),
        CheckConstraint(
            "max_leverage >= 1 AND max_leverage <= 100", name="check_leverage_range"
        ),
        CheckConstraint(
            "max_positions >= 1 AND max_positions <= 50", name="check_positions_range"
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    daily_loss_limit = Column(Float, nullable=False, default=500.0)  # USDT
    max_leverage = Column(Integer, nullable=False, default=10)  # 1-100배
    max_positions = Column(Integer, nullable=False, default=5)  # 1-50개
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", backref="risk_settings")


class UserSettings(Base):
    """사용자 설정 모델 (텔레그램, 알림 등)"""

    __tablename__ = "user_settings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)

    # 텔레그램 설정 (암호화 저장)
    encrypted_telegram_bot_token = Column(Text, nullable=True)
    encrypted_telegram_chat_id = Column(Text, nullable=True)
    telegram_notify_trades = Column(Boolean, default=True, nullable=False)
    telegram_notify_system = Column(Boolean, default=True, nullable=False)
    telegram_notify_errors = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", backref="settings")


class TradingSignal(Base):
    """트레이딩 시그널 추적 모델"""

    __tablename__ = "trading_signals"

    __table_args__ = (
        # 사용자별 시그널 조회용 (최신순 정렬)
        Index("idx_signal_user_timestamp", "user_id", "timestamp"),
        # 심볼별 시그널 조회용
        Index("idx_signal_symbol", "symbol"),
        # 전략별 시그널 조회용
        Index("idx_signal_strategy", "strategy_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    strategy_id = Column(Integer, ForeignKey("strategies.id"), nullable=True)
    symbol = Column(String(20), nullable=False)
    signal_type = Column(String(10), nullable=False)  # BUY, SELL, HOLD
    timeframe = Column(String(10), nullable=False)  # 1m, 5m, 15m, 1h, 4h, 1d
    price = Column(Float, nullable=True)  # 시그널 발생 시점의 가격
    indicators = Column(JSON, nullable=True)  # 시그널 생성 시 사용된 지표 값
    confidence = Column(Float, nullable=True)  # 신호 신뢰도 (0-1)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True, nullable=False)

    user = relationship("User", backref="trading_signals")
    strategy = relationship("Strategy", backref="signals")
