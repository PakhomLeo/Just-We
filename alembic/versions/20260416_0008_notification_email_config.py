"""notification email config

Revision ID: 20260416_0008
Revises: 20260416_0007
Create Date: 2026-04-16 23:10:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260416_0008"
down_revision = "20260416_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "notification_email_configs",
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("smtp_host", sa.String(length=255), nullable=False),
        sa.Column("smtp_port", sa.Integer(), nullable=False),
        sa.Column("smtp_username", sa.String(length=255), nullable=False),
        sa.Column("smtp_password", sa.Text(), nullable=False),
        sa.Column("from_email", sa.String(length=320), nullable=False),
        sa.Column("to_emails", sa.JSON(), nullable=False),
        sa.Column("use_tls", sa.Boolean(), nullable=False),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("notification_email_configs")
