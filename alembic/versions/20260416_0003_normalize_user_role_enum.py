"""normalize user role enum labels

Revision ID: 20260416_0003
Revises: 20260416_0002
Create Date: 2026-04-16 17:25:00
"""

from __future__ import annotations

from alembic import op


revision = "20260416_0003"
down_revision = "20260416_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    bind.exec_driver_sql("ALTER TYPE userrole RENAME VALUE 'ADMIN' TO 'admin'")
    bind.exec_driver_sql("ALTER TYPE userrole RENAME VALUE 'OPERATOR' TO 'operator'")
    bind.exec_driver_sql("ALTER TYPE userrole RENAME VALUE 'VIEWER' TO 'viewer'")


def downgrade() -> None:
    bind = op.get_bind()
    bind.exec_driver_sql("ALTER TYPE userrole RENAME VALUE 'admin' TO 'ADMIN'")
    bind.exec_driver_sql("ALTER TYPE userrole RENAME VALUE 'operator' TO 'OPERATOR'")
    bind.exec_driver_sql("ALTER TYPE userrole RENAME VALUE 'viewer' TO 'VIEWER'")
