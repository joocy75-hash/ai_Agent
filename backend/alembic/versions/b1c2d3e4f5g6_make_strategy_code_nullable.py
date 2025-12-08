"""Make strategy code column nullable

Revision ID: b1c2d3e4f5g6
Revises: a1b2c3d4e5f6
Create Date: 2024-12-08

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b1c2d3e4f5g6"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Make strategies.code column nullable for simple strategy creation."""
    # PostgreSQL에서 컬럼을 nullable로 변경
    op.alter_column("strategies", "code", existing_type=sa.Text(), nullable=True)


def downgrade() -> None:
    """Revert strategies.code column to non-nullable."""
    # 먼저 NULL 값을 빈 문자열로 업데이트
    op.execute("UPDATE strategies SET code = '' WHERE code IS NULL")
    # 그 다음 non-nullable로 변경
    op.alter_column("strategies", "code", existing_type=sa.Text(), nullable=False)
