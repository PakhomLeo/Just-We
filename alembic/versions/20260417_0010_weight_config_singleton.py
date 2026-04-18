"""add weight config singleton

Revision ID: 20260417_0010
Revises: 20260417_0009
Create Date: 2026-04-17 16:20:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260417_0010"
down_revision = "20260417_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "weight_configs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("frequency_ratio", sa.Float(), nullable=False, server_default="0.35"),
        sa.Column("recency_ratio", sa.Float(), nullable=False, server_default="0.25"),
        sa.Column("relevance_ratio", sa.Float(), nullable=False, server_default="0.25"),
        sa.Column("stability_ratio", sa.Float(), nullable=False, server_default="0.15"),
        sa.Column("tier_threshold_tier1", sa.Float(), nullable=False, server_default="80"),
        sa.Column("tier_threshold_tier2", sa.Float(), nullable=False, server_default="65"),
        sa.Column("tier_threshold_tier3", sa.Float(), nullable=False, server_default="50"),
        sa.Column("tier_threshold_tier4", sa.Float(), nullable=False, server_default="35"),
        sa.Column("check_interval_tier1", sa.Integer(), nullable=False, server_default="24"),
        sa.Column("check_interval_tier2", sa.Integer(), nullable=False, server_default="48"),
        sa.Column("check_interval_tier3", sa.Integer(), nullable=False, server_default="72"),
        sa.Column("check_interval_tier4", sa.Integer(), nullable=False, server_default="144"),
        sa.Column("check_interval_tier5", sa.Integer(), nullable=False, server_default="336"),
        sa.Column("high_relevance_threshold", sa.Float(), nullable=False, server_default="0.8"),
        sa.Column("ai_consecutive_low_threshold", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("weight_configs")
