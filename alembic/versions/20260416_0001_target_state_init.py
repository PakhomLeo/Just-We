"""target state init

Revision ID: 20260416_0001
Revises:
Create Date: 2026-04-16 17:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260416_0001"
down_revision = None
branch_labels = None
depends_on = None


collector_account_type = postgresql.ENUM("weread", "mp_admin", name="collectoraccounttype", create_type=False)
collector_account_status = postgresql.ENUM("active", "disabled", "expired", "error", name="collectoraccountstatus", create_type=False)
collector_health_status = postgresql.ENUM("normal", "restricted", "expired", "invalid", name="collectorhealthstatus", create_type=False)
risk_status = postgresql.ENUM("normal", "cooling", "blocked", name="riskstatus", create_type=False)
monitored_account_status = postgresql.ENUM("monitoring", "paused", "risk_observed", "invalid", name="monitoredaccountstatus", create_type=False)
fetch_job_type = postgresql.ENUM("update_list", "article_detail", "full_sync", name="fetchjobtype", create_type=False)
fetch_job_status = postgresql.ENUM("pending", "running", "success", "failed", name="fetchjobstatus", create_type=False)


def upgrade() -> None:
    bind = op.get_bind()
    collector_account_type.create(bind, checkfirst=True)
    collector_account_status.create(bind, checkfirst=True)
    collector_health_status.create(bind, checkfirst=True)
    risk_status.create(bind, checkfirst=True)
    monitored_account_status.create(bind, checkfirst=True)
    fetch_job_type.create(bind, checkfirst=True)
    fetch_job_status.create(bind, checkfirst=True)

    op.create_table(
        "collector_accounts",
        sa.Column("owner_user_id", sa.Uuid(), nullable=False),
        sa.Column("account_type", collector_account_type, nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=True),
        sa.Column("credentials", sa.JSON(), nullable=False),
        sa.Column("status", collector_account_status, nullable=False),
        sa.Column("health_status", collector_health_status, nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_health_check", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_failure_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("risk_status", risk_status, nullable=False),
        sa.Column("risk_reason", sa.String(length=500), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_collector_accounts_owner_user_id", "collector_accounts", ["owner_user_id"])
    op.create_index("ix_collector_accounts_account_type", "collector_accounts", ["account_type"])
    op.create_index("ix_collector_accounts_external_id", "collector_accounts", ["external_id"])

    op.create_table(
        "monitored_accounts",
        sa.Column("owner_user_id", sa.Uuid(), nullable=False),
        sa.Column("biz", sa.String(length=128), nullable=False),
        sa.Column("fakeid", sa.String(length=128), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("avatar_url", sa.Text(), nullable=True),
        sa.Column("current_tier", sa.Integer(), nullable=False),
        sa.Column("composite_score", sa.Float(), nullable=False),
        sa.Column("primary_fetch_mode", collector_account_type, nullable=False),
        sa.Column("fallback_fetch_mode", collector_account_type, nullable=True),
        sa.Column("status", monitored_account_status, nullable=False),
        sa.Column("last_polled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("update_history", sa.JSON(), nullable=False),
        sa.Column("ai_relevance_history", sa.JSON(), nullable=False),
        sa.Column("manual_override", sa.JSON(), nullable=True),
        sa.Column("strategy_config", sa.JSON(), nullable=False),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("biz"),
    )
    op.create_index("ix_monitored_accounts_owner_user_id", "monitored_accounts", ["owner_user_id"])
    op.create_index("ix_monitored_accounts_biz", "monitored_accounts", ["biz"])
    op.create_index("ix_monitored_accounts_fakeid", "monitored_accounts", ["fakeid"])

    op.create_table(
        "fetch_jobs",
        sa.Column("job_type", fetch_job_type, nullable=False),
        sa.Column("status", fetch_job_status, nullable=False),
        sa.Column("monitored_account_id", sa.Integer(), nullable=False),
        sa.Column("collector_account_id", sa.Integer(), nullable=True),
        sa.Column("proxy_id", sa.Integer(), nullable=True),
        sa.Column("fetch_mode", collector_account_type, nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["collector_account_id"], ["collector_accounts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["monitored_account_id"], ["monitored_accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["proxy_id"], ["proxies.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_fetch_jobs_monitored_account_id", "fetch_jobs", ["monitored_account_id"])
    op.create_index("ix_fetch_jobs_collector_account_id", "fetch_jobs", ["collector_account_id"])

    op.create_table(
        "ai_analysis_configs",
        sa.Column("api_url", sa.Text(), nullable=False),
        sa.Column("api_key", sa.Text(), nullable=False),
        sa.Column("model", sa.String(length=255), nullable=False),
        sa.Column("prompt_template", sa.Text(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "fetch_policies",
        sa.Column("tier_thresholds", sa.JSON(), nullable=False),
        sa.Column("check_intervals", sa.JSON(), nullable=False),
        sa.Column("primary_modes", sa.JSON(), nullable=False),
        sa.Column("retry_limit", sa.Integer(), nullable=False),
        sa.Column("retry_backoff_seconds", sa.Integer(), nullable=False),
        sa.Column("random_delay_min_ms", sa.Integer(), nullable=False),
        sa.Column("random_delay_max_ms", sa.Integer(), nullable=False),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    with op.batch_alter_table("articles") as batch_op:
        batch_op.add_column(sa.Column("monitored_account_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("cover_image", sa.String(length=1000), nullable=True))
        batch_op.add_column(sa.Column("author", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("fetch_mode", sa.String(length=32), nullable=True))
        batch_op.add_column(sa.Column("content_fingerprint", sa.String(length=128), nullable=True))
        batch_op.add_column(sa.Column("source_payload", sa.JSON(), nullable=True))
        batch_op.create_index("ix_articles_monitored_account_id", ["monitored_account_id"])
        batch_op.create_index("ix_articles_content_fingerprint", ["content_fingerprint"])
        batch_op.create_foreign_key("fk_articles_monitored_account_id", "monitored_accounts", ["monitored_account_id"], ["id"], ondelete="CASCADE")


def downgrade() -> None:
    with op.batch_alter_table("articles") as batch_op:
        batch_op.drop_constraint("fk_articles_monitored_account_id", type_="foreignkey")
        batch_op.drop_index("ix_articles_content_fingerprint")
        batch_op.drop_index("ix_articles_monitored_account_id")
        batch_op.drop_column("source_payload")
        batch_op.drop_column("content_fingerprint")
        batch_op.drop_column("fetch_mode")
        batch_op.drop_column("author")
        batch_op.drop_column("cover_image")
        batch_op.drop_column("monitored_account_id")

    op.drop_table("fetch_policies")
    op.drop_table("ai_analysis_configs")
    op.drop_index("ix_fetch_jobs_collector_account_id", table_name="fetch_jobs")
    op.drop_index("ix_fetch_jobs_monitored_account_id", table_name="fetch_jobs")
    op.drop_table("fetch_jobs")
    op.drop_index("ix_monitored_accounts_fakeid", table_name="monitored_accounts")
    op.drop_index("ix_monitored_accounts_biz", table_name="monitored_accounts")
    op.drop_index("ix_monitored_accounts_owner_user_id", table_name="monitored_accounts")
    op.drop_table("monitored_accounts")
    op.drop_index("ix_collector_accounts_external_id", table_name="collector_accounts")
    op.drop_index("ix_collector_accounts_account_type", table_name="collector_accounts")
    op.drop_index("ix_collector_accounts_owner_user_id", table_name="collector_accounts")
    op.drop_table("collector_accounts")

    bind = op.get_bind()
    fetch_job_status.drop(bind, checkfirst=True)
    fetch_job_type.drop(bind, checkfirst=True)
    monitored_account_status.drop(bind, checkfirst=True)
    risk_status.drop(bind, checkfirst=True)
    collector_health_status.drop(bind, checkfirst=True)
    collector_account_status.drop(bind, checkfirst=True)
    collector_account_type.drop(bind, checkfirst=True)
