"""add feed, rich content, and proxy cooldown fields

Revision ID: 20260417_0012
Revises: 20260417_0011
Create Date: 2026-04-17 22:30:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260417_0012"
down_revision = "20260417_0011"
branch_labels = None
depends_on = None


def _fill_token(table_name: str, column_name: str, id_column: str = "id") -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        bind.exec_driver_sql(
            f"""
            UPDATE {table_name}
            SET {column_name} = md5(random()::text || clock_timestamp()::text || {id_column}::text)
            WHERE {column_name} IS NULL
            """
        )
    else:
        rows = bind.exec_driver_sql(f"SELECT {id_column} FROM {table_name} WHERE {column_name} IS NULL").fetchall()
        for index, row in enumerate(rows):
            token = f"legacy_{table_name}_{row[0]}_{index}"
            bind.exec_driver_sql(
                f"UPDATE {table_name} SET {column_name} = :token WHERE {id_column} = :id",
                {"token": token, "id": row[0]},
            )


def upgrade() -> None:
    bind = op.get_bind()

    op.add_column("users", sa.Column("aggregate_feed_token", sa.String(length=64), nullable=True))
    _fill_token("users", "aggregate_feed_token")
    op.alter_column("users", "aggregate_feed_token", nullable=False)
    op.create_index("ix_users_aggregate_feed_token", "users", ["aggregate_feed_token"], unique=True)

    op.add_column("monitored_accounts", sa.Column("feed_token", sa.String(length=64), nullable=True))
    op.add_column("monitored_accounts", sa.Column("mp_intro", sa.Text(), nullable=True))
    op.add_column("monitored_accounts", sa.Column("metadata_json", sa.JSON(), nullable=True))
    _fill_token("monitored_accounts", "feed_token")
    op.alter_column("monitored_accounts", "feed_token", nullable=False)
    op.create_index("ix_monitored_accounts_feed_token", "monitored_accounts", ["feed_token"], unique=True)

    op.add_column("articles", sa.Column("content_html", sa.Text(), nullable=True))
    op.add_column("articles", sa.Column("content_type", sa.String(length=64), nullable=True))
    op.add_column("articles", sa.Column("original_images", sa.JSON(), nullable=True))

    op.add_column("proxies", sa.Column("fail_until", sa.DateTime(timezone=True), nullable=True))
    op.add_column("proxies", sa.Column("last_error", sa.Text(), nullable=True))
    op.add_column("proxies", sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_proxies_fail_until", "proxies", ["fail_until"], unique=False)

    if bind.dialect.name == "postgresql":
        bind.exec_driver_sql("ALTER TYPE fetchjobtype ADD VALUE IF NOT EXISTS 'history_backfill'")


def downgrade() -> None:
    op.drop_index("ix_proxies_fail_until", table_name="proxies")
    op.drop_column("proxies", "last_checked_at")
    op.drop_column("proxies", "last_error")
    op.drop_column("proxies", "fail_until")

    op.drop_column("articles", "original_images")
    op.drop_column("articles", "content_type")
    op.drop_column("articles", "content_html")

    op.drop_index("ix_monitored_accounts_feed_token", table_name="monitored_accounts")
    op.drop_column("monitored_accounts", "metadata_json")
    op.drop_column("monitored_accounts", "mp_intro")
    op.drop_column("monitored_accounts", "feed_token")

    op.drop_index("ix_users_aggregate_feed_token", table_name="users")
    op.drop_column("users", "aggregate_feed_token")
