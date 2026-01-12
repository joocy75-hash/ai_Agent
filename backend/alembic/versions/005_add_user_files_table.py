"""Add user_files table for upload quota management

Revision ID: 005
Revises: 004
Create Date: 2026-01-12

This migration adds the user_files table to track user file uploads
for quota management (100MB per user, 50 files per user, 100GB total).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '005'
down_revision: Union[str, None] = '004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create user_files table
    op.create_table(
        'user_files',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('filename', sa.String(255), nullable=False),
        sa.Column('file_size_bytes', sa.Integer(), nullable=False),
        sa.Column('file_path', sa.String(500), nullable=False),
        sa.Column('mime_type', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    # Create indexes for efficient queries
    op.create_index('idx_user_files_user_id', 'user_files', ['user_id'])
    op.create_index('idx_user_files_created_at', 'user_files', ['created_at'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_user_files_created_at', table_name='user_files')
    op.drop_index('idx_user_files_user_id', table_name='user_files')

    # Drop table
    op.drop_table('user_files')
