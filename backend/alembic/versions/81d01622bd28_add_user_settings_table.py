"""add user_settings table

Revision ID: 81d01622bd28
Revises: a1b2c3d4e5f6
Create Date: 2025-12-06 12:00:01.450881

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "81d01622bd28"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create user_settings table for telegram and other user settings
    op.create_table(
        "user_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("encrypted_telegram_bot_token", sa.Text(), nullable=True),
        sa.Column("encrypted_telegram_chat_id", sa.Text(), nullable=True),
        sa.Column(
            "telegram_notify_trades", sa.Boolean(), nullable=False, server_default="1"
        ),
        sa.Column(
            "telegram_notify_system", sa.Boolean(), nullable=False, server_default="1"
        ),
        sa.Column(
            "telegram_notify_errors", sa.Boolean(), nullable=False, server_default="1"
        ),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_user_settings_id"), "user_settings", ["id"], unique=False)
    op.create_index(
        op.f("ix_user_settings_user_id"), "user_settings", ["user_id"], unique=True
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_user_settings_user_id"), table_name="user_settings")
    op.drop_index(op.f("ix_user_settings_id"), table_name="user_settings")
    op.drop_table("user_settings")
