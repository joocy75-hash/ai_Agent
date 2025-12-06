"""add_user_name_and_phone_fields

Revision ID: a1b2c3d4e5f6
Revises: 0348833b8934
Create Date: 2025-12-06

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "0348833b8934"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add name, phone, and OAuth columns to users table."""
    # Add name column
    op.add_column("users", sa.Column("name", sa.String(100), nullable=True))

    # Add phone column
    op.add_column("users", sa.Column("phone", sa.String(20), nullable=True))

    # Add OAuth columns for social login
    op.add_column("users", sa.Column("oauth_provider", sa.String(20), nullable=True))

    op.add_column(
        "users", sa.Column("oauth_id", sa.String(255), nullable=True, index=True)
    )

    op.add_column("users", sa.Column("profile_image", sa.String(500), nullable=True))

    # Create index for oauth_id
    op.create_index("ix_users_oauth_id", "users", ["oauth_id"])


def downgrade() -> None:
    """Remove name, phone, and OAuth columns from users table."""
    op.drop_index("ix_users_oauth_id", "users")
    op.drop_column("users", "profile_image")
    op.drop_column("users", "oauth_id")
    op.drop_column("users", "oauth_provider")
    op.drop_column("users", "phone")
    op.drop_column("users", "name")
