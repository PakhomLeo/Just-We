"""add three stage ai pipeline fields

Revision ID: 20260418_0014
Revises: 20260417_0013
Create Date: 2026-04-18 00:30:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260418_0014"
down_revision = "20260417_0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("ai_analysis_configs", sa.Column("text_api_url", sa.Text(), nullable=False, server_default=""))
    op.add_column("ai_analysis_configs", sa.Column("text_api_key", sa.Text(), nullable=False, server_default=""))
    op.add_column("ai_analysis_configs", sa.Column("text_model", sa.String(length=255), nullable=False, server_default=""))
    op.add_column("ai_analysis_configs", sa.Column("text_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")))
    op.add_column("ai_analysis_configs", sa.Column("image_api_url", sa.Text(), nullable=False, server_default=""))
    op.add_column("ai_analysis_configs", sa.Column("image_api_key", sa.Text(), nullable=False, server_default=""))
    op.add_column("ai_analysis_configs", sa.Column("image_model", sa.String(length=255), nullable=False, server_default=""))
    op.add_column("ai_analysis_configs", sa.Column("image_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")))
    op.add_column("ai_analysis_configs", sa.Column("text_analysis_prompt", sa.Text(), nullable=False, server_default=""))
    op.add_column("ai_analysis_configs", sa.Column("image_analysis_prompt", sa.Text(), nullable=False, server_default=""))
    op.add_column("ai_analysis_configs", sa.Column("type_judgment_prompt", sa.Text(), nullable=False, server_default=""))
    op.add_column("ai_analysis_configs", sa.Column("target_article_type", sa.Text(), nullable=False, server_default=""))
    op.add_column("ai_analysis_configs", sa.Column("timeout_seconds", sa.Integer(), nullable=False, server_default="60"))

    bind = op.get_bind()
    bind.exec_driver_sql(
        """
        UPDATE ai_analysis_configs
        SET
            text_api_url = COALESCE(NULLIF(text_api_url, ''), api_url),
            text_api_key = COALESCE(NULLIF(text_api_key, ''), api_key),
            text_model = COALESCE(NULLIF(text_model, ''), model),
            image_api_url = COALESCE(NULLIF(image_api_url, ''), api_url),
            image_api_key = COALESCE(NULLIF(image_api_key, ''), api_key),
            image_model = COALESCE(NULLIF(image_model, ''), model),
            text_analysis_prompt = COALESCE(NULLIF(text_analysis_prompt, ''), prompt_template)
        """
    )

    for column in [
        "text_api_url",
        "text_api_key",
        "text_model",
        "text_enabled",
        "image_api_url",
        "image_api_key",
        "image_model",
        "image_enabled",
        "text_analysis_prompt",
        "image_analysis_prompt",
        "type_judgment_prompt",
        "target_article_type",
        "timeout_seconds",
    ]:
        op.alter_column("ai_analysis_configs", column, server_default=None)

    op.add_column("articles", sa.Column("ai_text_analysis", sa.JSON(), nullable=True))
    op.add_column("articles", sa.Column("ai_image_analysis", sa.JSON(), nullable=True))
    op.add_column("articles", sa.Column("ai_type_judgment", sa.JSON(), nullable=True))
    op.add_column("articles", sa.Column("ai_combined_analysis", sa.JSON(), nullable=True))
    op.add_column("articles", sa.Column("ai_target_match", sa.String(length=8), nullable=True))
    op.add_column("articles", sa.Column("ai_analysis_status", sa.String(length=32), nullable=True))
    op.add_column("articles", sa.Column("ai_analysis_error", sa.Text(), nullable=True))
    op.create_index("ix_articles_ai_target_match", "articles", ["ai_target_match"], unique=False)
    op.create_index("ix_articles_ai_analysis_status", "articles", ["ai_analysis_status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_articles_ai_analysis_status", table_name="articles")
    op.drop_index("ix_articles_ai_target_match", table_name="articles")
    op.drop_column("articles", "ai_analysis_error")
    op.drop_column("articles", "ai_analysis_status")
    op.drop_column("articles", "ai_target_match")
    op.drop_column("articles", "ai_combined_analysis")
    op.drop_column("articles", "ai_type_judgment")
    op.drop_column("articles", "ai_image_analysis")
    op.drop_column("articles", "ai_text_analysis")

    op.drop_column("ai_analysis_configs", "timeout_seconds")
    op.drop_column("ai_analysis_configs", "target_article_type")
    op.drop_column("ai_analysis_configs", "type_judgment_prompt")
    op.drop_column("ai_analysis_configs", "image_analysis_prompt")
    op.drop_column("ai_analysis_configs", "text_analysis_prompt")
    op.drop_column("ai_analysis_configs", "image_enabled")
    op.drop_column("ai_analysis_configs", "image_model")
    op.drop_column("ai_analysis_configs", "image_api_key")
    op.drop_column("ai_analysis_configs", "image_api_url")
    op.drop_column("ai_analysis_configs", "text_enabled")
    op.drop_column("ai_analysis_configs", "text_model")
    op.drop_column("ai_analysis_configs", "text_api_key")
    op.drop_column("ai_analysis_configs", "text_api_url")
