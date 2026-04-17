"""normalize legacy account enum labels

Revision ID: 20260416_0004
Revises: 20260416_0003
Create Date: 2026-04-16 17:27:00
"""

from __future__ import annotations

from alembic import op


revision = "20260416_0004"
down_revision = "20260416_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    bind.exec_driver_sql("ALTER TYPE accounttype RENAME VALUE 'WEREAD' TO 'weread'")
    bind.exec_driver_sql("ALTER TYPE accounttype RENAME VALUE 'MP' TO 'mp'")
    bind.exec_driver_sql("ALTER TYPE accountstatus RENAME VALUE 'ACTIVE' TO 'active'")
    bind.exec_driver_sql("ALTER TYPE accountstatus RENAME VALUE 'INACTIVE' TO 'inactive'")
    bind.exec_driver_sql("ALTER TYPE accountstatus RENAME VALUE 'BLOCKED' TO 'blocked'")
    bind.exec_driver_sql("ALTER TYPE healthstatus RENAME VALUE 'NORMAL' TO 'normal'")
    bind.exec_driver_sql("ALTER TYPE healthstatus RENAME VALUE 'RESTRICTED' TO 'restricted'")
    bind.exec_driver_sql("ALTER TYPE healthstatus RENAME VALUE 'EXPIRED' TO 'expired'")
    bind.exec_driver_sql("ALTER TYPE healthstatus RENAME VALUE 'INVALID' TO 'invalid'")


def downgrade() -> None:
    bind = op.get_bind()
    bind.exec_driver_sql("ALTER TYPE accounttype RENAME VALUE 'weread' TO 'WEREAD'")
    bind.exec_driver_sql("ALTER TYPE accounttype RENAME VALUE 'mp' TO 'MP'")
    bind.exec_driver_sql("ALTER TYPE accountstatus RENAME VALUE 'active' TO 'ACTIVE'")
    bind.exec_driver_sql("ALTER TYPE accountstatus RENAME VALUE 'inactive' TO 'INACTIVE'")
    bind.exec_driver_sql("ALTER TYPE accountstatus RENAME VALUE 'blocked' TO 'BLOCKED'")
    bind.exec_driver_sql("ALTER TYPE healthstatus RENAME VALUE 'normal' TO 'NORMAL'")
    bind.exec_driver_sql("ALTER TYPE healthstatus RENAME VALUE 'restricted' TO 'RESTRICTED'")
    bind.exec_driver_sql("ALTER TYPE healthstatus RENAME VALUE 'expired' TO 'EXPIRED'")
    bind.exec_driver_sql("ALTER TYPE healthstatus RENAME VALUE 'invalid' TO 'INVALID'")
