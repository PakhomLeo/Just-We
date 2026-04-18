"""extend proxy service type enum values

Revision ID: 20260417_0011
Revises: 20260417_0010
Create Date: 2026-04-17 21:12:00
"""

from __future__ import annotations

from alembic import op


revision = "20260417_0011"
down_revision = "20260417_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    for value in ("weread_list", "weread_detail", "mp_list", "mp_detail"):
        bind.exec_driver_sql(f"ALTER TYPE servicetype ADD VALUE IF NOT EXISTS '{value}'")


def downgrade() -> None:
    # PostgreSQL cannot drop enum values without recreating the type and rewriting
    # dependent columns. Keep downgrade non-destructive.
    pass
