"""notification ownership and targets

Revision ID: 20260416_0007
Revises: 20260416_0006
Create Date: 2026-04-16 22:30:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260416_0007"
down_revision = "20260416_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("notifications") as batch_op:
        batch_op.add_column(sa.Column("owner_user_id", sa.Uuid(), nullable=True))
        batch_op.add_column(sa.Column("collector_account_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("monitored_account_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("payload", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")))
        batch_op.create_index("ix_notifications_owner_user_id", ["owner_user_id"])
        batch_op.create_index("ix_notifications_collector_account_id", ["collector_account_id"])
        batch_op.create_index("ix_notifications_monitored_account_id", ["monitored_account_id"])
        batch_op.create_foreign_key(
            "fk_notifications_owner_user_id",
            "users",
            ["owner_user_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch_op.create_foreign_key(
            "fk_notifications_collector_account_id",
            "collector_accounts",
            ["collector_account_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch_op.create_foreign_key(
            "fk_notifications_monitored_account_id",
            "monitored_accounts",
            ["monitored_account_id"],
            ["id"],
            ondelete="CASCADE",
        )

    op.execute(
        """
        UPDATE notifications AS n
        SET monitored_account_id = a.monitored_account_id,
            owner_user_id = m.owner_user_id
        FROM articles AS a
        JOIN monitored_accounts AS m ON m.id = a.monitored_account_id
        WHERE n.article_id = a.id
          AND a.monitored_account_id IS NOT NULL
        """
    )

    with op.batch_alter_table("notifications") as batch_op:
        batch_op.alter_column("payload", server_default=None)


def downgrade() -> None:
    with op.batch_alter_table("notifications") as batch_op:
        batch_op.drop_constraint("fk_notifications_monitored_account_id", type_="foreignkey")
        batch_op.drop_constraint("fk_notifications_collector_account_id", type_="foreignkey")
        batch_op.drop_constraint("fk_notifications_owner_user_id", type_="foreignkey")
        batch_op.drop_index("ix_notifications_monitored_account_id")
        batch_op.drop_index("ix_notifications_collector_account_id")
        batch_op.drop_index("ix_notifications_owner_user_id")
        batch_op.drop_column("payload")
        batch_op.drop_column("monitored_account_id")
        batch_op.drop_column("collector_account_id")
        batch_op.drop_column("owner_user_id")
