"""Add is_active column to strategies table

Revision ID: c94d5c828d83
Revises: 002
Create Date: 2025-12-15 14:19:16.455399

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c94d5c828d83'
down_revision: Union[str, None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add is_active column to strategies table
    op.add_column(
        'strategies',
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='0')
    )


def downgrade() -> None:
    # Remove is_active column from strategies table
    op.drop_column('strategies', 'is_active')
