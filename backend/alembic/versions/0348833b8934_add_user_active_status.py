"""add_user_active_status

Revision ID: 0348833b8934
Revises: 15c805118f10
Create Date: 2025-12-04 10:47:30.135508

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0348833b8934'
down_revision: Union[str, None] = '15c805118f10'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add is_active column (default True)
    op.add_column('users', sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'))
    # Add suspended_at column
    op.add_column('users', sa.Column('suspended_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    # Remove columns in reverse order
    op.drop_column('users', 'suspended_at')
    op.drop_column('users', 'is_active')
