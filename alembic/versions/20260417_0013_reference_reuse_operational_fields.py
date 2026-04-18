"""add reference reuse operational fields

Revision ID: 20260417_0013
Revises: 20260417_0012
Create Date: 2026-04-17 23:10:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260417_0013"
down_revision = "20260417_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    json_default = sa.text("'{}'::json") if bind.dialect.name == "postgresql" else sa.text("'{}'")
    op.add_column("collector_accounts", sa.Column("cool_until", sa.DateTime(timezone=True), nullable=True))
    op.add_column("collector_accounts", sa.Column("last_error_category", sa.String(length=100), nullable=True))
    op.create_index("ix_collector_accounts_cool_until", "collector_accounts", ["cool_until"], unique=False)

    op.add_column("fetch_policies", sa.Column("rate_limit_policy", sa.JSON(), nullable=False, server_default=json_default))
    op.add_column("fetch_policies", sa.Column("history_backfill_policy", sa.JSON(), nullable=False, server_default=json_default))
    op.add_column("fetch_policies", sa.Column("notification_policy", sa.JSON(), nullable=False, server_default=json_default))
    op.alter_column("fetch_policies", "rate_limit_policy", server_default=None)
    op.alter_column("fetch_policies", "history_backfill_policy", server_default=None)
    op.alter_column("fetch_policies", "notification_policy", server_default=None)

    op.add_column("notification_email_configs", sa.Column("webhook_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("notification_email_configs", sa.Column("webhook_url", sa.Text(), nullable=False, server_default=""))
    op.alter_column("notification_email_configs", "webhook_enabled", server_default=None)
    op.alter_column("notification_email_configs", "webhook_url", server_default=None)


def downgrade() -> None:
    op.drop_column("notification_email_configs", "webhook_url")
    op.drop_column("notification_email_configs", "webhook_enabled")

    op.drop_column("fetch_policies", "notification_policy")
    op.drop_column("fetch_policies", "history_backfill_policy")
    op.drop_column("fetch_policies", "rate_limit_policy")

    op.drop_index("ix_collector_accounts_cool_until", table_name="collector_accounts")
    op.drop_column("collector_accounts", "last_error_category")
    op.drop_column("collector_accounts", "cool_until")
