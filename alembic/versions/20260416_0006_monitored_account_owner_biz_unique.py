"""scope monitored account uniqueness by owner

Revision ID: 20260416_0006
Revises: 20260416_0005
Create Date: 2026-04-16 19:15:00
"""

from __future__ import annotations

from alembic import op


revision = "20260416_0006"
down_revision = "20260416_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "postgresql":
        bind.exec_driver_sql("ALTER TABLE monitored_accounts DROP CONSTRAINT IF EXISTS monitored_accounts_biz_key")
        bind.exec_driver_sql(
            "ALTER TABLE monitored_accounts "
            "ADD CONSTRAINT uq_monitored_accounts_owner_biz UNIQUE (owner_user_id, biz)"
        )
        return

    with op.batch_alter_table("monitored_accounts") as batch_op:
        batch_op.create_unique_constraint("uq_monitored_accounts_owner_biz", ["owner_user_id", "biz"])


def downgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "postgresql":
        bind.exec_driver_sql("ALTER TABLE monitored_accounts DROP CONSTRAINT IF EXISTS uq_monitored_accounts_owner_biz")
        bind.exec_driver_sql("ALTER TABLE monitored_accounts ADD CONSTRAINT monitored_accounts_biz_key UNIQUE (biz)")
        return

    with op.batch_alter_table("monitored_accounts") as batch_op:
        batch_op.drop_constraint("uq_monitored_accounts_owner_biz", type_="unique")
        batch_op.create_unique_constraint("monitored_accounts_biz_key", ["biz"])
