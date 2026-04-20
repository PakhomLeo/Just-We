"""Background AI analysis tasks."""

from app.core.database import get_db_context
from app.services.article_ai_analysis_service import ArticleAIAnalysisService


async def run_article_ai_analysis(article_id: int) -> dict:
    """Run AI analysis for a saved article in a fresh DB session."""
    async with get_db_context() as db:
        return await ArticleAIAnalysisService(db).run_article(article_id)
