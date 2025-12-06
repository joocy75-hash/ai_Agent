"""add_performance_indexes

Revision ID: 42e3c0f7e90a
Revises: 8e946c90dc5b
Create Date: 2025-12-02 11:30:16.282710

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '42e3c0f7e90a'
down_revision: Union[str, None] = '8e946c90dc5b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """성능 최적화를 위한 인덱스 추가"""

    # Trade 테이블 인덱스
    op.create_index('idx_trade_user_created', 'trades', ['user_id', 'created_at'])
    op.create_index('idx_trade_symbol', 'trades', ['symbol'])
    op.create_index('idx_trade_strategy', 'trades', ['strategy_id'])

    # Equity 테이블 인덱스
    op.create_index('idx_equity_user_time', 'equities', ['user_id', 'timestamp'])

    # BacktestResult 테이블 인덱스
    op.create_index('idx_backtest_user_created', 'backtest_results', ['user_id', 'created_at'])
    op.create_index('idx_backtest_status', 'backtest_results', ['status'])

    # BotLog 테이블 인덱스
    op.create_index('idx_botlog_user_created', 'bot_logs', ['user_id', 'created_at'])
    op.create_index('idx_botlog_event_type', 'bot_logs', ['event_type'])

    # OpenOrder 테이블 인덱스
    op.create_index('idx_openorder_user_status', 'open_orders', ['user_id', 'status'])
    op.create_index('idx_openorder_symbol', 'open_orders', ['symbol'])


def downgrade() -> None:
    """인덱스 제거 (롤백용)"""

    # OpenOrder 테이블 인덱스 제거
    op.drop_index('idx_openorder_symbol', 'open_orders')
    op.drop_index('idx_openorder_user_status', 'open_orders')

    # BotLog 테이블 인덱스 제거
    op.drop_index('idx_botlog_event_type', 'bot_logs')
    op.drop_index('idx_botlog_user_created', 'bot_logs')

    # BacktestResult 테이블 인덱스 제거
    op.drop_index('idx_backtest_status', 'backtest_results')
    op.drop_index('idx_backtest_user_created', 'backtest_results')

    # Equity 테이블 인덱스 제거
    op.drop_index('idx_equity_user_time', 'equities')

    # Trade 테이블 인덱스 제거
    op.drop_index('idx_trade_strategy', 'trades')
    op.drop_index('idx_trade_symbol', 'trades')
    op.drop_index('idx_trade_user_created', 'trades')
