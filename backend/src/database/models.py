from datetime import datetime
from enum import Enum

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy import (
    Enum as SQLEnum,
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
    code = Column(Text, nullable=True)  # 간단 전략 생성 시 code가 없을 수 있음
    params = Column(Text, nullable=True)
    is_active = Column(Boolean, default=False, nullable=False)

    user = relationship("User", back_populates="strategies")


class BotStatus(Base):
    __tablename__ = "bot_status"

    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    strategy_id = Column(Integer, ForeignKey("strategies.id"))
    is_running = Column(Boolean, default=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Bot auto-restart tracking (Issue #5)
    restart_attempts = Column(Integer, default=0, nullable=False)
    last_restart_attempt = Column(DateTime, nullable=True)


class ExitReason(str, Enum):
    take_profit = "take_profit"
    stop_loss = "stop_loss"
    signal_reverse = "signal_reverse"
    manual = "manual"
    liquidation = "liquidation"


# ============================================================
# 다중 봇 시스템 모델 (Multi-Bot System)
# 문서: docs/MULTI_BOT_IMPLEMENTATION_PLAN.md
# 목적: 사용자당 여러 봇 인스턴스 운영 지원 (최대 5개)
# ============================================================


class BotType(str, Enum):
    """봇 유형"""

    AI_TREND = "ai_trend"  # AI 추세 추종 봇 (기존 봇 로직)
    GRID = "grid"  # 그리드 봇 (신규)


class GridMode(str, Enum):
    """그리드 간격 모드"""

    ARITHMETIC = "arithmetic"  # 균등 간격 (가격 차이 동일)
    GEOMETRIC = "geometric"  # 기하 간격 (% 비율 동일)


class PositionDirection(str, Enum):
    """포지션 방향 (그리드봇 템플릿용)"""

    LONG = "long"
    SHORT = "short"


class GridOrderStatus(str, Enum):
    """그리드 주문 상태"""

    PENDING = "pending"  # 주문 대기
    BUY_PLACED = "buy_placed"  # 매수 주문 설정됨
    BUY_FILLED = "buy_filled"  # 매수 체결 (보유 중)
    SELL_PLACED = "sell_placed"  # 매도 주문 설정됨
    SELL_FILLED = "sell_filled"  # 매도 체결 (수익 실현)


class TradeSource(str, Enum):
    """거래 출처 - Values match PostgreSQL enum (lowercase)

    NOTE: Member names MUST be lowercase to match PostgreSQL enum values.
    SQLAlchemy uses .name (not .value) when inserting into DB.
    """

    manual = "manual"  # 수동 거래
    ai_bot = "ai_bot"  # AI 봇 거래
    grid_bot = "grid_bot"  # 그리드 봇 거래
    bot_instance = "bot_instance"  # 봇 인스턴스 거래


class BotInstance(Base):
    """
    봇 인스턴스 테이블

    - 사용자당 최대 5개 봇 생성 가능
    - 각 봇은 독립적인 전략, 심볼, 투자금액을 가짐
    - allocated_amount: 사용자가 입력한 투자금액 (USDT)
    """

    __tablename__ = "bot_instances"

    __table_args__ = (
        CheckConstraint(
            "allocation_percent > 0 AND allocation_percent <= 100",
            name="check_allocation_range",
        ),
        CheckConstraint(
            "max_leverage >= 1 AND max_leverage <= 100", name="check_bot_leverage_range"
        ),
        CheckConstraint(
            "max_positions >= 1 AND max_positions <= 20",
            name="check_bot_positions_range",
        ),
        CheckConstraint(
            "allocated_amount >= 0",
            name="check_allocated_amount_positive",
        ),
        Index("idx_bot_instances_user_id", "user_id"),
        Index("idx_bot_instances_user_running", "user_id", "is_running"),
        Index("idx_bot_instances_type", "bot_type"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    strategy_id = Column(
        Integer, ForeignKey("strategies.id", ondelete="SET NULL"), nullable=True
    )

    # 봇 정보
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    bot_type = Column(SQLEnum(BotType), default=BotType.AI_TREND, nullable=False)

    # 잔고 할당 (사용자 전체 잔고의 %) - 기존 호환성 유지
    allocation_percent = Column(Numeric(5, 2), nullable=False, default=10.0)

    # 투자금액 (USDT) - 멀티봇 시스템에서 사용
    allocated_amount = Column(Numeric(15, 2), nullable=True, default=0)

    # 심볼 설정
    symbol = Column(String(20), nullable=False, default="BTCUSDT")

    # 리스크 설정 (봇별로 다르게 설정 가능)
    max_leverage = Column(Integer, nullable=False, default=10)
    max_positions = Column(Integer, nullable=False, default=3)
    stop_loss_percent = Column(Numeric(5, 2), nullable=True, default=5.0)
    take_profit_percent = Column(Numeric(5, 2), nullable=True, default=10.0)

    # 알림 설정
    telegram_notify = Column(Boolean, default=True, nullable=False)

    # 상태
    is_running = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)  # soft delete용

    # 실행 추적
    last_started_at = Column(DateTime, nullable=True)
    last_stopped_at = Column(DateTime, nullable=True)
    last_trade_at = Column(DateTime, nullable=True)
    last_error = Column(Text, nullable=True)
    last_signal_at = Column(DateTime, nullable=True)  # 마지막 시그널 시간

    # 통계 (실시간 업데이트)
    total_trades = Column(Integer, default=0, nullable=False)
    winning_trades = Column(Integer, default=0, nullable=False)
    total_pnl = Column(Numeric(20, 8), default=0, nullable=False)
    current_pnl_percent = Column(Numeric(10, 4), nullable=True, default=0)  # 현재 수익률 %

    # 타임스탬프
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # 템플릿 참조 (그리드봇이 템플릿에서 생성된 경우)
    template_id = Column(
        Integer, ForeignKey("grid_bot_templates.id", ondelete="SET NULL"), nullable=True
    )

    # 트렌드봇 템플릿 참조 (AI 트렌드봇이 템플릿에서 생성된 경우)
    trend_template_id = Column(
        Integer, ForeignKey("trend_bot_templates.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    user = relationship("User", backref="bot_instances")
    strategy = relationship("Strategy", backref="bot_instances")
    template = relationship("GridBotTemplate", back_populates="instances")
    trend_template = relationship("TrendBotTemplate", back_populates="instances")
    grid_config = relationship(
        "GridBotConfig",
        back_populates="bot_instance",
        uselist=False,
        cascade="all, delete-orphan",
    )
    # trades relationship은 Trade 모델에서 정의


class GridBotTemplate(Base):
    """
    관리자가 생성한 그리드봇 템플릿

    - 백테스트 결과와 함께 저장
    - 일반 사용자가 "Use" 버튼으로 복사하여 사용
    - Bitget AI 탭과 유사한 기능
    """

    __tablename__ = "grid_bot_templates"

    __table_args__ = (
        CheckConstraint("upper_price > lower_price", name="check_template_price_range"),
        CheckConstraint(
            "grid_count >= 2 AND grid_count <= 200", name="check_template_grid_count"
        ),
        CheckConstraint("min_investment > 0", name="check_template_min_investment"),
        Index("ix_grid_bot_templates_symbol", "symbol"),
        Index("ix_grid_bot_templates_is_active", "is_active"),
        Index("ix_grid_bot_templates_is_featured", "is_featured"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)

    # ===== 기본 정보 =====
    name = Column(String(100), nullable=False)  # 템플릿 이름
    symbol = Column(String(20), nullable=False)  # "SOLUSDT", "BTCUSDT"
    direction = Column(
        SQLEnum(PositionDirection, values_callable=lambda e: [x.value for x in e]),
        nullable=False,
    )  # LONG, SHORT
    leverage = Column(Integer, default=5, nullable=False)  # 기본 레버리지

    # ===== 그리드 설정 =====
    lower_price = Column(Numeric(20, 8), nullable=False)  # 하단 가격
    upper_price = Column(Numeric(20, 8), nullable=False)  # 상단 가격
    grid_count = Column(Integer, nullable=False)  # 그리드 개수 (2-200)
    grid_mode = Column(
        SQLEnum(GridMode, values_callable=lambda e: [x.value for x in e]),
        default=GridMode.ARITHMETIC,
        nullable=False,
    )

    # ===== 투자 제한 =====
    min_investment = Column(Numeric(20, 8), nullable=False)  # 최소 투자금액 (USDT)
    recommended_investment = Column(Numeric(20, 8), nullable=True)  # 권장 투자금액

    # ===== 백테스트 결과 =====
    backtest_roi_30d = Column(Numeric(10, 4), nullable=True)  # 30일 ROI (%)
    backtest_max_drawdown = Column(Numeric(10, 4), nullable=True)  # 최대 낙폭 (%)
    backtest_total_trades = Column(Integer, nullable=True)  # 총 거래 수
    backtest_win_rate = Column(Numeric(10, 4), nullable=True)  # 승률 (%)
    backtest_roi_history = Column(JSON, nullable=True)  # 일별 ROI 배열 (차트용)
    backtest_updated_at = Column(DateTime, nullable=True)  # 백테스트 실행 시각

    # ===== 추천 정보 =====
    recommended_period = Column(String(50), nullable=True)  # "7-30 days"
    description = Column(Text, nullable=True)  # 봇 설명
    tags = Column(JSON, nullable=True)  # ["stable", "high-risk"] 등

    # ===== 사용 통계 =====
    active_users = Column(Integer, default=0, nullable=False)  # 현재 사용 중인 유저 수
    total_users = Column(Integer, default=0, nullable=False)  # 누적 사용자 수
    total_funds_in_use = Column(
        Numeric(20, 8), default=0, nullable=False
    )  # 총 운용 자금 (USDT)

    # ===== 상태 =====
    is_active = Column(Boolean, default=True, nullable=False)  # 공개 여부
    is_featured = Column(
        Boolean, default=False, nullable=False
    )  # 추천 표시 (상단 노출)
    sort_order = Column(Integer, default=0, nullable=False)  # 정렬 순서

    # ===== 관리 =====
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # ===== 관계 =====
    creator = relationship(
        "User", foreign_keys=[created_by], backref="created_templates"
    )
    instances = relationship("BotInstance", back_populates="template")

    def __repr__(self):
        return (
            f"<GridBotTemplate {self.symbol} {self.direction.value} {self.leverage}x>"
        )


class GridBotConfig(Base):
    """
    그리드 봇 설정 테이블

    - bot_instances와 1:1 관계 (bot_type='grid'인 경우만)
    - 가격 범위, 그리드 수, 투자금 설정
    """

    __tablename__ = "grid_bot_configs"

    __table_args__ = (
        CheckConstraint("upper_price > lower_price", name="check_price_range"),
        CheckConstraint(
            "grid_count >= 2 AND grid_count <= 100", name="check_grid_count_range"
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    bot_instance_id = Column(
        Integer,
        ForeignKey("bot_instances.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    # 그리드 설정
    lower_price = Column(Numeric(20, 8), nullable=False)  # 하한가
    upper_price = Column(Numeric(20, 8), nullable=False)  # 상한가
    grid_count = Column(Integer, nullable=False, default=10)
    grid_mode = Column(SQLEnum(GridMode), default=GridMode.ARITHMETIC, nullable=False)

    # 투자 설정
    total_investment = Column(Numeric(20, 8), nullable=False)  # 총 투자금 (USDT)
    per_grid_amount = Column(
        Numeric(20, 8), nullable=True
    )  # 그리드당 투자금 (자동 계산)

    # 트리거 설정
    trigger_price = Column(Numeric(20, 8), nullable=True)  # 특정 가격에 시작 (선택)
    stop_upper = Column(Numeric(20, 8), nullable=True)  # 상한 돌파 시 중지
    stop_lower = Column(Numeric(20, 8), nullable=True)  # 하한 돌파 시 중지

    # 상태 추적
    current_price = Column(Numeric(20, 8), nullable=True)
    active_buy_orders = Column(Integer, default=0, nullable=False)
    active_sell_orders = Column(Integer, default=0, nullable=False)
    filled_buy_count = Column(Integer, default=0, nullable=False)
    filled_sell_count = Column(Integer, default=0, nullable=False)
    realized_profit = Column(Numeric(20, 8), default=0, nullable=False)

    # 타임스탬프
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    bot_instance = relationship("BotInstance", back_populates="grid_config")
    orders = relationship(
        "GridOrder", back_populates="grid_config", cascade="all, delete-orphan"
    )


class GridOrder(Base):
    """
    그리드 주문 테이블

    - 각 그리드 라인의 주문 상태 추적
    - 매수 체결 → 매도 주문 자동 설정
    - 매도 체결 → 매수 주문 재설정 (사이클 반복)
    """

    __tablename__ = "grid_orders"

    __table_args__ = (
        Index("idx_grid_orders_config", "grid_config_id"),
        Index("idx_grid_orders_status", "status"),
    )

    id = Column(Integer, primary_key=True, index=True)
    grid_config_id = Column(
        Integer, ForeignKey("grid_bot_configs.id", ondelete="CASCADE"), nullable=False
    )

    # 그리드 정보
    grid_index = Column(Integer, nullable=False)  # 0 ~ (grid_count-1)
    grid_price = Column(Numeric(20, 8), nullable=False)  # 이 그리드의 가격

    # 주문 상태
    buy_order_id = Column(String(100), nullable=True)  # Bitget 매수 주문 ID
    sell_order_id = Column(String(100), nullable=True)  # Bitget 매도 주문 ID
    status = Column(
        SQLEnum(GridOrderStatus), default=GridOrderStatus.PENDING, nullable=False
    )

    # 체결 정보
    buy_filled_price = Column(Numeric(20, 8), nullable=True)
    buy_filled_qty = Column(Numeric(20, 8), nullable=True)
    buy_filled_at = Column(DateTime, nullable=True)
    sell_filled_price = Column(Numeric(20, 8), nullable=True)
    sell_filled_qty = Column(Numeric(20, 8), nullable=True)
    sell_filled_at = Column(DateTime, nullable=True)

    # 수익
    profit = Column(Numeric(20, 8), default=0, nullable=False)

    # 타임스탬프
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    grid_config = relationship("GridBotConfig", back_populates="orders")


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
        # 봇 인스턴스별 거래 조회용 (다중 봇 시스템)
        Index("idx_trade_bot_instance", "bot_instance_id"),
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

    # 시그널 태그 (차트 마커용)
    enter_tag = Column(
        String(100), nullable=True
    )  # 진입 시그널 태그 (예: "rsi_oversold", "macd_cross")
    exit_tag = Column(
        String(100), nullable=True
    )  # 청산 시그널 태그 (예: "tp_hit", "sl_triggered")
    order_tag = Column(
        String(100), nullable=True
    )  # 주문 태그 (예: "main_entry", "dca_1")

    # 다중 봇 시스템 지원 (추가)
    bot_instance_id = Column(
        Integer, ForeignKey("bot_instances.id", ondelete="SET NULL"), nullable=True
    )
    trade_source = Column(
        SQLEnum(TradeSource, name="tradesource", create_type=False),
        default=TradeSource.manual,
        nullable=False,
    )

    user = relationship("User", back_populates="trades")
    bot_instance = relationship("BotInstance", backref="trades")


class Position(Base):
    __tablename__ = "positions"

    # 봇 인스턴스별 포지션 조회를 위한 인덱스
    __table_args__ = (
        Index("idx_position_bot_instance", "bot_instance_id"),
        Index("idx_position_user_symbol", "user_id", "symbol"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    symbol = Column(String, nullable=False)
    entry_price = Column(Numeric(18, 8), nullable=False)
    size = Column(Float, nullable=False)
    side = Column(String, nullable=False)
    pnl = Column(Numeric(18, 8), default=0)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 다중 봇 시스템 지원 (추가)
    bot_instance_id = Column(
        Integer,
        ForeignKey("bot_instances.id", ondelete="SET NULL"),
        nullable=True,  # 기존 포지션과의 호환성을 위해 nullable
    )
    # 거래소 주문 ID (격리 추적용)
    exchange_order_id = Column(String(100), nullable=True)

    user = relationship("User", back_populates="positions")
    bot_instance = relationship("BotInstance", backref="positions")


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


# ============================================================
# 차트 어노테이션 시스템 (Chart Annotations)
# 목적: 차트에 사용자 메모, 지지/저항선, 트렌드라인 등 표시
# ============================================================


class AnnotationType(str, Enum):
    """어노테이션 유형"""

    NOTE = "note"  # 텍스트 메모
    HORIZONTAL_LINE = "hline"  # 수평선 (지지/저항선)
    VERTICAL_LINE = "vline"  # 수직선 (이벤트 마커)
    TRENDLINE = "trendline"  # 추세선 (두 점 연결)
    RECTANGLE = "rectangle"  # 사각형 영역
    PRICE_LEVEL = "price_level"  # 가격 수준 (알림 설정 가능)


class ChartAnnotation(Base):
    """
    차트 어노테이션 모델

    - 사용자가 차트에 추가하는 메모, 선, 도형 등
    - 심볼별로 저장되어 해당 심볼 차트에 표시
    - 타임프레임과 독립적으로 표시 (가격/시간 기준)
    """

    __tablename__ = "chart_annotations"

    __table_args__ = (
        # 사용자별 + 심볼별 어노테이션 조회용
        Index("idx_annotation_user_symbol", "user_id", "symbol"),
        # 활성 어노테이션 조회용
        Index("idx_annotation_active", "user_id", "is_active"),
        # 생성 시간순 정렬용
        Index("idx_annotation_created", "created_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    # 기본 정보
    symbol = Column(String(20), nullable=False)  # BTCUSDT, ETHUSDT 등
    annotation_type = Column(SQLEnum(AnnotationType), nullable=False)
    label = Column(String(100), nullable=True)  # 어노테이션 라벨 (선택)
    text = Column(Text, nullable=True)  # 메모 내용 (NOTE 타입의 경우)

    # 위치 정보 (시간 기준)
    timestamp = Column(DateTime, nullable=True)  # NOTE, VLINE의 시간 위치
    start_timestamp = Column(DateTime, nullable=True)  # TRENDLINE, RECTANGLE 시작점
    end_timestamp = Column(DateTime, nullable=True)  # TRENDLINE, RECTANGLE 끝점

    # 위치 정보 (가격 기준)
    price = Column(Numeric(20, 8), nullable=True)  # HLINE, NOTE의 가격 위치
    start_price = Column(
        Numeric(20, 8), nullable=True
    )  # TRENDLINE, RECTANGLE 시작 가격
    end_price = Column(Numeric(20, 8), nullable=True)  # TRENDLINE, RECTANGLE 끝 가격

    # 스타일 설정 (JSON)
    style = Column(JSON, nullable=True, default=dict)
    # 예: {"color": "#ff0000", "lineWidth": 2, "lineDash": [5, 5], "fontSize": 12}

    # 알림 설정 (PRICE_LEVEL 타입용)
    alert_enabled = Column(Boolean, default=False, nullable=False)
    alert_triggered = Column(Boolean, default=False, nullable=False)
    alert_direction = Column(String(10), nullable=True)  # "above" 또는 "below"

    # 상태
    is_active = Column(Boolean, default=True, nullable=False)  # 표시 여부
    is_locked = Column(Boolean, default=False, nullable=False)  # 편집 잠금

    # 타임스탬프
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    user = relationship("User", backref="annotations")


# ============================================================
# AI 추세 봇 템플릿 시스템 (Trend Bot Templates)
# 목적: 관리자가 생성한 AI 추세 봇 템플릿을 사용자에게 제공
# ============================================================


class TrendDirection(str, Enum):
    """추세 방향"""

    LONG = "long"
    SHORT = "short"
    BOTH = "both"  # 양방향


class TrendBotTemplate(Base):
    """
    AI 추세 봇 템플릿

    - 관리자가 생성한 AI 추세 봇 설정
    - 백테스트 결과와 함께 저장
    - 일반 사용자가 "Use" 버튼으로 봇 생성
    """

    __tablename__ = "trend_bot_templates"

    __table_args__ = (
        CheckConstraint("min_investment > 0", name="check_trend_min_investment"),
        Index("ix_trend_bot_templates_symbol", "symbol"),
        Index("ix_trend_bot_templates_is_active", "is_active"),
        Index("ix_trend_bot_templates_is_featured", "is_featured"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)

    # ===== 기본 정보 =====
    name = Column(String(100), nullable=False)  # 템플릿 이름
    symbol = Column(String(20), nullable=False)  # "BTCUSDT", "ETHUSDT"
    description = Column(Text, nullable=True)  # 봇 설명

    # ===== 전략 설정 =====
    strategy_type = Column(String(50), default="ema_crossover")  # 전략 타입
    direction = Column(
        SQLEnum(TrendDirection, values_callable=lambda e: [x.value for x in e]),
        default=TrendDirection.LONG,
        nullable=False,
    )
    leverage = Column(Integer, default=5, nullable=False)  # 기본 레버리지

    # ===== 리스크 설정 =====
    stop_loss_percent = Column(Float, default=2.0, nullable=False)  # 손절 %
    take_profit_percent = Column(Float, default=4.0, nullable=False)  # 익절 %

    # ===== 투자 제한 =====
    min_investment = Column(
        Numeric(20, 8), nullable=False, default=50.0
    )  # 최소 투자금액 (USDT)
    recommended_investment = Column(Numeric(20, 8), nullable=True)  # 권장 투자금액

    # ===== 백테스트 결과 =====
    backtest_roi_30d = Column(Numeric(10, 4), nullable=True)  # 30일 ROI (%)
    backtest_win_rate = Column(Numeric(10, 4), nullable=True)  # 승률 (%)
    backtest_max_drawdown = Column(Numeric(10, 4), nullable=True)  # 최대 낙폭 (%)
    backtest_total_trades = Column(Integer, nullable=True)  # 총 거래 수
    backtest_updated_at = Column(DateTime, nullable=True)  # 백테스트 실행 시각

    # ===== 추천 정보 =====
    recommended_period = Column(String(50), nullable=True)  # "7-30 days"
    risk_level = Column(String(20), default="medium")  # low, medium, high
    tags = Column(JSON, nullable=True)  # ["trending", "btc", "stable"] 등

    # ===== 사용 통계 =====
    active_users = Column(Integer, default=0, nullable=False)  # 현재 사용 중인 유저 수
    total_users = Column(Integer, default=0, nullable=False)  # 누적 사용자 수

    # ===== 상태 =====
    is_active = Column(Boolean, default=True, nullable=False)  # 공개 여부
    is_featured = Column(Boolean, default=False, nullable=False)  # 추천 표시
    sort_order = Column(Integer, default=0, nullable=False)  # 정렬 순서

    # ===== 관리 =====
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # ===== 관계 =====
    creator = relationship(
        "User", foreign_keys=[created_by], backref="created_trend_templates"
    )
    instances = relationship("BotInstance", back_populates="trend_template")

    def __repr__(self):
        return (
            f"<TrendBotTemplate {self.symbol} {self.direction.value} {self.leverage}x>"
        )


# ============================================================
# 사용자 마진 사용량 캐시 (User Margin Usage Cache)
# 목적: 실시간 마진 사용량 추적 및 빠른 조회
# ============================================================


class UserMarginUsage(Base):
    """
    사용자별 마진 사용량 캐시

    - 실시간으로 업데이트되는 마진 사용량
    - 봇 시작/정지 시 자동 갱신
    - 잔고 조회 결과를 캐싱하여 성능 최적화
    """

    __tablename__ = "user_margin_usage"

    __table_args__ = (
        Index("idx_user_margin_usage_user_id", "user_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True
    )

    # 잔고 정보 (캐시)
    total_balance = Column(Numeric(15, 2), default=0, nullable=False)  # 총 잔고 (USDT)
    used_margin = Column(Numeric(15, 2), default=0, nullable=False)  # 사용 중인 마진 (USDT)
    available_margin = Column(Numeric(15, 2), default=0, nullable=False)  # 사용 가능한 마진 (USDT)

    # 봇 정보
    active_bot_count = Column(Integer, default=0, nullable=False)  # 활성 봇 개수

    # 타임스탬프
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    user = relationship("User", backref="margin_usage")


# ============================================================
# 사용자 파일 업로드 추적 (User File Upload Tracking)
# 목적: 업로드 쿼터 관리를 위한 파일 추적
# ============================================================


class UserFile(Base):
    """
    사용자 파일 업로드 추적 모델

    - 사용자별 업로드 파일 추적
    - 쿼터 관리를 위한 파일 크기 및 개수 추적
    - 100MB/사용자, 50개 파일/사용자 제한
    """

    __tablename__ = "user_files"

    __table_args__ = (
        Index("idx_user_files_user_id", "user_id"),
        Index("idx_user_files_created_at", "created_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    # 파일 정보
    filename = Column(String(255), nullable=False)  # 원본 파일명
    file_size_bytes = Column(Integer, nullable=False)  # 파일 크기 (바이트)
    file_path = Column(String(500), nullable=False)  # 저장 경로
    mime_type = Column(String(100), nullable=True)  # MIME 타입

    # 타임스탬프
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", backref="uploaded_files")
