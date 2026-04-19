"""add optional usernames for application users

Revision ID: 20260419_0016
Revises: 20260418_0015
Create Date: 2026-04-19 18:00:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260419_0016"
down_revision = "20260418_0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("username", sa.String(length=80), nullable=True))
    op.create_index("ix_users_username", "users", ["username"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_users_username", table_name="users")
    op.drop_column("users", "username")
