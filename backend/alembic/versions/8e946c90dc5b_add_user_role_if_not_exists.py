"""add_user_role_if_not_exists

Revision ID: 8e946c90dc5b
Revises: 92c2304a947f
Create Date: 2025-12-02 10:29:01.386790

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8e946c90dc5b'
down_revision: Union[str, None] = '92c2304a947f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # SQLite에서는 컬럼 존재 여부를 먼저 확인
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    columns = [col['name'] for col in inspector.get_columns('users')]

    # role 컬럼이 없는 경우에만 추가
    if 'role' not in columns:
        op.add_column('users', sa.Column('role', sa.String(), nullable=True))
        # 기존 사용자들을 모두 'user' 역할로 설정
        op.execute("UPDATE users SET role = 'user' WHERE role IS NULL")
        # role을 NOT NULL로 변경
        with op.batch_alter_table('users') as batch_op:
            batch_op.alter_column('role', nullable=False)


def downgrade() -> None:
    # role 컬럼 삭제
    with op.batch_alter_table('users') as batch_op:
        batch_op.drop_column('role')
