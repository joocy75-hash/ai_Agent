"""Add risk_settings table

Revision ID: 89337a4e9d2b
Revises: 42e3c0f7e90a
Create Date: 2025-12-04 01:36:44.407756

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '89337a4e9d2b'
down_revision: Union[str, None] = '42e3c0f7e90a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create risk_settings table
    op.create_table(
        'risk_settings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('daily_loss_limit', sa.Float(), nullable=False, server_default='500.0'),
        sa.Column('max_leverage', sa.Integer(), nullable=False, server_default='10'),
        sa.Column('max_positions', sa.Integer(), nullable=False, server_default='5'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.CheckConstraint('daily_loss_limit > 0', name='check_positive_loss_limit'),
        sa.CheckConstraint('max_leverage >= 1 AND max_leverage <= 100', name='check_leverage_range'),
        sa.CheckConstraint('max_positions >= 1 AND max_positions <= 50', name='check_positions_range'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id')
    )
    op.create_index(op.f('ix_risk_settings_id'), 'risk_settings', ['id'], unique=False)


def downgrade() -> None:
    # Drop risk_settings table
    op.drop_index(op.f('ix_risk_settings_id'), table_name='risk_settings')
    op.drop_table('risk_settings')
