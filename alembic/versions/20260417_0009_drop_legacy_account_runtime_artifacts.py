"""drop legacy account runtime artifacts

Revision ID: 20260417_0009
Revises: 20260416_0008
Create Date: 2026-04-17 10:30:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260417_0009"
down_revision = "20260416_0008"
branch_labels = None
depends_on = None


def _drop_column_artifacts(table_name: str, column_name: str) -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns(table_name)}
    if column_name not in columns:
        return

    foreign_keys = [
        foreign_key["name"]
        for foreign_key in inspector.get_foreign_keys(table_name)
        if foreign_key["name"] and foreign_key.get("constrained_columns") == [column_name]
    ]
    indexes = [
        index["name"]
        for index in inspector.get_indexes(table_name)
        if index["name"] and index.get("column_names") == [column_name]
    ]

    with op.batch_alter_table(table_name) as batch_op:
        for foreign_key_name in foreign_keys:
            batch_op.drop_constraint(foreign_key_name, type_="foreignkey")
        for index_name in indexes:
            batch_op.drop_index(index_name)
        batch_op.drop_column(column_name)


def upgrade() -> None:
    _drop_column_artifacts("articles", "account_id")
    _drop_column_artifacts("notifications", "account_id")

    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table("accounts"):
        op.drop_table("accounts")


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("accounts"):
        op.create_table(
            "accounts",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("biz", sa.String(length=64), nullable=False),
            sa.Column("fakeid", sa.String(length=64), nullable=False),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("account_type", sa.String(length=32), nullable=False),
            sa.Column("current_tier", sa.Integer(), nullable=False, server_default="3"),
            sa.Column("composite_score", sa.Float(), nullable=False, server_default="50"),
            sa.Column("last_checked", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_updated", sa.DateTime(timezone=True), nullable=True),
            sa.Column("update_history", sa.JSON(), nullable=True),
            sa.Column("ai_relevance_history", sa.JSON(), nullable=True),
            sa.Column("manual_override", sa.JSON(), nullable=True),
            sa.Column("cookies", sa.JSON(), nullable=True),
            sa.Column("cookies_expire_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
            sa.Column("health_status", sa.String(length=32), nullable=False, server_default="normal"),
            sa.Column("last_health_check", sa.DateTime(timezone=True), nullable=True),
            sa.Column("health_reason", sa.String(length=200), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("biz"),
        )
        op.create_index("ix_accounts_biz", "accounts", ["biz"])

    article_columns = {column["name"] for column in inspector.get_columns("articles")}
    if "account_id" not in article_columns:
        with op.batch_alter_table("articles") as batch_op:
            batch_op.add_column(sa.Column("account_id", sa.Integer(), nullable=True))
            batch_op.create_index("ix_articles_account_id", ["account_id"])
            batch_op.create_foreign_key("fk_articles_account_id", "accounts", ["account_id"], ["id"], ondelete="SET NULL")

    notification_columns = {column["name"] for column in inspector.get_columns("notifications")}
    if "account_id" not in notification_columns:
        with op.batch_alter_table("notifications") as batch_op:
            batch_op.add_column(sa.Column("account_id", sa.Integer(), nullable=True))
            batch_op.create_index("ix_notifications_account_id", ["account_id"])
            batch_op.create_foreign_key("fk_notifications_account_id", "accounts", ["account_id"], ["id"], ondelete="SET NULL")
