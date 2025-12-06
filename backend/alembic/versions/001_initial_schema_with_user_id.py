"""initial schema with user_id

Revision ID: 001
Revises:
Create Date: 2025-11-30

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    전체 스키마 생성.

    모든 테이블을 초기 상태로 생성.
    BacktestResult는 user_id, status, error_message 포함.
    """
    # users 테이블
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('password_hash', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)

    # api_keys 테이블
    op.create_table(
        'api_keys',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('encrypted_api_key', sa.Text(), nullable=False),
        sa.Column('encrypted_secret_key', sa.Text(), nullable=False),
        sa.Column('encrypted_passphrase', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_api_keys_id'), 'api_keys', ['id'], unique=False)

    # strategies 테이블
    op.create_table(
        'strategies',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('code', sa.Text(), nullable=False),
        sa.Column('params', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_strategies_id'), 'strategies', ['id'], unique=False)

    # bot_status 테이블
    op.create_table(
        'bot_status',
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('strategy_id', sa.Integer(), nullable=True),
        sa.Column('is_running', sa.Boolean(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['strategy_id'], ['strategies.id'], ),
        sa.PrimaryKeyConstraint('user_id')
    )

    # bot_config 테이블
    op.create_table(
        'bot_config',
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('max_risk_percent', sa.Float(), nullable=True),
        sa.Column('leverage', sa.Integer(), nullable=True),
        sa.Column('auto_tp', sa.Float(), nullable=True),
        sa.Column('auto_sl', sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('user_id')
    )

    # trades 테이블
    op.create_table(
        'trades',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('symbol', sa.String(), nullable=False),
        sa.Column('side', sa.String(), nullable=False),
        sa.Column('qty', sa.Float(), nullable=False),
        sa.Column('entry_price', sa.Numeric(precision=18, scale=8), nullable=False),
        sa.Column('exit_price', sa.Numeric(precision=18, scale=8), nullable=True),
        sa.Column('pnl', sa.Numeric(precision=18, scale=8), nullable=True),
        sa.Column('pnl_percent', sa.Float(), nullable=True),
        sa.Column('strategy_id', sa.Integer(), nullable=True),
        sa.Column('leverage', sa.Integer(), nullable=True),
        sa.Column('exit_reason', sa.Enum('take_profit', 'stop_loss', 'signal_reverse', 'manual', 'liquidation', name='exitreason'), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['strategy_id'], ['strategies.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_trades_id'), 'trades', ['id'], unique=False)

    # positions 테이블
    op.create_table(
        'positions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('symbol', sa.String(), nullable=False),
        sa.Column('entry_price', sa.Numeric(precision=18, scale=8), nullable=False),
        sa.Column('size', sa.Float(), nullable=False),
        sa.Column('side', sa.String(), nullable=False),
        sa.Column('pnl', sa.Numeric(precision=18, scale=8), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_positions_id'), 'positions', ['id'], unique=False)

    # equities 테이블
    op.create_table(
        'equities',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('value', sa.Numeric(precision=18, scale=8), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_equities_id'), 'equities', ['id'], unique=False)

    # bot_logs 테이블
    op.create_table(
        'bot_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('event_type', sa.String(), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_bot_logs_id'), 'bot_logs', ['id'], unique=False)

    # open_orders 테이블
    op.create_table(
        'open_orders',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('symbol', sa.String(), nullable=False),
        sa.Column('side', sa.String(), nullable=False),
        sa.Column('qty', sa.Float(), nullable=False),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_open_orders_id'), 'open_orders', ['id'], unique=False)

    # backtest_results 테이블 (user_id, status, error_message 포함)
    op.create_table(
        'backtest_results',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('pair', sa.String(), nullable=True),
        sa.Column('timeframe', sa.String(), nullable=True),
        sa.Column('initial_balance', sa.Float(), nullable=False),
        sa.Column('final_balance', sa.Float(), nullable=False),
        sa.Column('metrics', sa.Text(), nullable=True),
        sa.Column('equity_curve', sa.Text(), nullable=True),
        sa.Column('params', sa.Text(), nullable=True),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_backtest_results_id'), 'backtest_results', ['id'], unique=False)
    op.create_index(op.f('ix_backtest_results_user_id'), 'backtest_results', ['user_id'], unique=False)

    # backtest_trades 테이블
    op.create_table(
        'backtest_trades',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('result_id', sa.Integer(), nullable=False),
        sa.Column('timestamp', sa.String(), nullable=True),
        sa.Column('side', sa.String(), nullable=False),
        sa.Column('direction', sa.String(), nullable=False),
        sa.Column('entry_price', sa.Float(), nullable=True),
        sa.Column('exit_price', sa.Float(), nullable=True),
        sa.Column('qty', sa.Float(), nullable=True),
        sa.Column('fee', sa.Float(), nullable=True),
        sa.Column('pnl', sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(['result_id'], ['backtest_results.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_backtest_trades_id'), 'backtest_trades', ['id'], unique=False)


def downgrade() -> None:
    """
    전체 스키마 삭제 (롤백).
    """
    op.drop_index(op.f('ix_backtest_trades_id'), table_name='backtest_trades')
    op.drop_table('backtest_trades')

    op.drop_index(op.f('ix_backtest_results_user_id'), table_name='backtest_results')
    op.drop_index(op.f('ix_backtest_results_id'), table_name='backtest_results')
    op.drop_table('backtest_results')

    op.drop_index(op.f('ix_open_orders_id'), table_name='open_orders')
    op.drop_table('open_orders')

    op.drop_index(op.f('ix_bot_logs_id'), table_name='bot_logs')
    op.drop_table('bot_logs')

    op.drop_index(op.f('ix_equities_id'), table_name='equities')
    op.drop_table('equities')

    op.drop_index(op.f('ix_positions_id'), table_name='positions')
    op.drop_table('positions')

    op.drop_index(op.f('ix_trades_id'), table_name='trades')
    op.drop_table('trades')

    op.drop_table('bot_config')
    op.drop_table('bot_status')

    op.drop_index(op.f('ix_strategies_id'), table_name='strategies')
    op.drop_table('strategies')

    op.drop_index(op.f('ix_api_keys_id'), table_name='api_keys')
    op.drop_table('api_keys')

    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
