"""add_user_role_field

Revision ID: 92c2304a947f
Revises: ad9472a74882
Create Date: 2025-12-02 09:33:03.297162

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '92c2304a947f'
down_revision: Union[str, None] = 'ad9472a74882'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # SQLite doesn't support ALTER COLUMN, so we add it with a default value
    # Add role column with default value 'user'
    op.add_column('users', sa.Column('role', sa.String(), nullable=False, server_default='user'))

    # Update existing rows (if any) to ensure they have 'user' role
    op.execute("UPDATE users SET role = 'user' WHERE role IS NULL OR role = ''")


def downgrade() -> None:
    op.drop_column('users', 'role')
