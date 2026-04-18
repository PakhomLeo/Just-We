"""add reusable proxy service bindings and login proxy locks

Revision ID: 20260418_0015
Revises: 20260418_0014
Create Date: 2026-04-18 02:00:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "20260418_0015"
down_revision = "20260418_0014"
branch_labels = None
depends_on = None


proxy_kind = postgresql.ENUM(
    "datacenter",
    "isp_static",
    "residential_static",
    "residential_rotating",
    "mobile_static",
    "mobile_rotating",
    "custom_gateway",
    name="proxykind",
    create_type=False,
)
proxy_rotation_mode = postgresql.ENUM(
    "fixed",
    "sticky",
    "round_robin",
    "per_request",
    "provider_auto",
    name="proxyrotationmode",
    create_type=False,
)
proxy_service_key = postgresql.ENUM(
    "mp_admin_login",
    "mp_list",
    "mp_detail",
    "weread_login",
    "weread_list",
    "weread_detail",
    "image_proxy",
    "ai",
    name="proxyservicekey",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    proxy_kind.create(bind, checkfirst=True)
    proxy_rotation_mode.create(bind, checkfirst=True)
    proxy_service_key.create(bind, checkfirst=True)

    op.add_column("proxies", sa.Column("proxy_kind", proxy_kind, nullable=False, server_default="residential_rotating"))
    op.add_column("proxies", sa.Column("rotation_mode", proxy_rotation_mode, nullable=False, server_default="round_robin"))
    op.add_column("proxies", sa.Column("sticky_ttl_seconds", sa.Integer(), nullable=True))
    op.add_column("proxies", sa.Column("provider_name", sa.String(length=128), nullable=True))
    op.add_column("proxies", sa.Column("notes", sa.Text(), nullable=True))

    bind.exec_driver_sql(
        """
        UPDATE proxies
        SET
            proxy_kind = CASE
                WHEN service_type IN ('mp_list', 'weread_list') THEN 'isp_static'::proxykind
                WHEN service_type = 'ai' THEN 'datacenter'::proxykind
                ELSE proxy_kind
            END,
            rotation_mode = CASE
                WHEN service_type IN ('mp_list', 'weread_list') THEN 'sticky'::proxyrotationmode
                ELSE rotation_mode
            END,
            sticky_ttl_seconds = CASE
                WHEN service_type IN ('mp_list', 'weread_list') THEN COALESCE(sticky_ttl_seconds, 1800)
                ELSE sticky_ttl_seconds
            END
        """
    )

    for column in ["proxy_kind", "rotation_mode"]:
        op.alter_column("proxies", column, server_default=None)

    op.create_table(
        "proxy_service_bindings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("proxy_id", sa.Integer(), nullable=False),
        sa.Column("service_key", proxy_service_key, nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["proxy_id"], ["proxies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("proxy_id", "service_key", name="uq_proxy_service_binding_proxy_service"),
    )
    op.create_index("ix_proxy_service_bindings_proxy_id", "proxy_service_bindings", ["proxy_id"], unique=False)
    op.create_index("ix_proxy_service_bindings_service_key", "proxy_service_bindings", ["service_key"], unique=False)

    bind.exec_driver_sql(
        """
        INSERT INTO proxy_service_bindings (proxy_id, service_key, is_enabled, priority, created_at)
        SELECT
            id,
            CASE service_type
                WHEN 'ai' THEN 'ai'::proxyservicekey
                WHEN 'weread_list' THEN 'weread_list'::proxyservicekey
                WHEN 'weread_detail' THEN 'weread_detail'::proxyservicekey
                WHEN 'mp_list' THEN 'mp_list'::proxyservicekey
                WHEN 'mp_detail' THEN 'mp_detail'::proxyservicekey
                WHEN 'parse' THEN 'image_proxy'::proxyservicekey
                WHEN 'polling' THEN 'weread_list'::proxyservicekey
                ELSE 'mp_detail'::proxyservicekey
            END,
            true,
            100,
            NOW()
        FROM proxies
        ON CONFLICT DO NOTHING
        """
    )

    op.add_column("collector_accounts", sa.Column("login_proxy_id", sa.Integer(), nullable=True))
    op.add_column("collector_accounts", sa.Column("login_proxy_locked", sa.Boolean(), nullable=False, server_default=sa.text("true")))
    op.add_column("collector_accounts", sa.Column("last_login_proxy_ip", sa.String(length=128), nullable=True))
    op.add_column("collector_accounts", sa.Column("login_proxy_changed_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_collector_accounts_login_proxy_id", "collector_accounts", ["login_proxy_id"], unique=False)
    op.create_foreign_key(
        "fk_collector_accounts_login_proxy_id_proxies",
        "collector_accounts",
        "proxies",
        ["login_proxy_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.alter_column("collector_accounts", "login_proxy_locked", server_default=None)

    op.add_column("fetch_policies", sa.Column("proxy_policy", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")))
    op.execute(
        """
        UPDATE fetch_policies
        SET proxy_policy = '{"disable_direct_wechat_fetch": true, "min_success_rate": 50.0, "proxy_failure_cooldown_seconds": 120, "detail_rotation_strategy": "round_robin", "list_sticky_ttl_seconds": 1800}'::json
        WHERE proxy_policy::text = '{}'::text
        """
    )
    op.alter_column("fetch_policies", "proxy_policy", server_default=None)


def downgrade() -> None:
    op.drop_column("fetch_policies", "proxy_policy")

    op.drop_constraint("fk_collector_accounts_login_proxy_id_proxies", "collector_accounts", type_="foreignkey")
    op.drop_index("ix_collector_accounts_login_proxy_id", table_name="collector_accounts")
    op.drop_column("collector_accounts", "login_proxy_changed_at")
    op.drop_column("collector_accounts", "last_login_proxy_ip")
    op.drop_column("collector_accounts", "login_proxy_locked")
    op.drop_column("collector_accounts", "login_proxy_id")

    op.drop_index("ix_proxy_service_bindings_service_key", table_name="proxy_service_bindings")
    op.drop_index("ix_proxy_service_bindings_proxy_id", table_name="proxy_service_bindings")
    op.drop_table("proxy_service_bindings")

    op.drop_column("proxies", "notes")
    op.drop_column("proxies", "provider_name")
    op.drop_column("proxies", "sticky_ttl_seconds")
    op.drop_column("proxies", "rotation_mode")
    op.drop_column("proxies", "proxy_kind")

    bind = op.get_bind()
    proxy_service_key.drop(bind, checkfirst=True)
    proxy_rotation_mode.drop(bind, checkfirst=True)
    proxy_kind.drop(bind, checkfirst=True)
