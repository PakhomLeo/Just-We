"""normalize proxy enum and legacy account health status values

Revision ID: 20260416_0005
Revises: 20260416_0004
Create Date: 2026-04-16 17:29:00
"""

from __future__ import annotations

from alembic import op


revision = "20260416_0005"
down_revision = "20260416_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    bind.exec_driver_sql("UPDATE accounts SET health_status = lower(health_status) WHERE health_status <> lower(health_status)")
    bind.exec_driver_sql("ALTER TYPE servicetype RENAME VALUE 'POLLING' TO 'polling'")
    bind.exec_driver_sql("ALTER TYPE servicetype RENAME VALUE 'FETCH' TO 'fetch'")
    bind.exec_driver_sql("ALTER TYPE servicetype RENAME VALUE 'PARSE' TO 'parse'")
    bind.exec_driver_sql("ALTER TYPE servicetype RENAME VALUE 'AI' TO 'ai'")


def downgrade() -> None:
    bind = op.get_bind()
    bind.exec_driver_sql("UPDATE accounts SET health_status = upper(health_status) WHERE health_status <> upper(health_status)")
    bind.exec_driver_sql("ALTER TYPE servicetype RENAME VALUE 'polling' TO 'POLLING'")
    bind.exec_driver_sql("ALTER TYPE servicetype RENAME VALUE 'fetch' TO 'FETCH'")
    bind.exec_driver_sql("ALTER TYPE servicetype RENAME VALUE 'parse' TO 'PARSE'")
    bind.exec_driver_sql("ALTER TYPE servicetype RENAME VALUE 'ai' TO 'AI'")
