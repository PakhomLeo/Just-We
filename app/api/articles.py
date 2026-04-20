"""Article API routes."""

from fastapi import APIRouter, BackgroundTasks, HTTPException, status, Query

from app.core.dependencies import DbSession, CurrentUser
from app.schemas.article import (
    ArticleResponse,
    ArticleListResponse,
    ArticleWithAccountResponse,
)
from app.services.article_service import ArticleService
from app.tasks.ai_task import run_article_ai_analysis


router = APIRouter(prefix="/articles", tags=["Articles"])


def _article_to_response(article) -> ArticleWithAccountResponse:
    """Convert Article model to ArticleWithAccountResponse."""
    return ArticleWithAccountResponse(
        id=article.id,
        monitored_account_id=article.monitored_account_id,
        title=article.title,
        content=article.content,
        content_html=article.content_html,
        content_type=article.content_type,
        raw_content=article.raw_content,
        images=article.images or [],
        original_images=article.original_images or [],
        cover_image=article.cover_image,
        url=article.url,
        author=article.author,
        published_at=article.published_at,
        ai_relevance_ratio=article.ai_relevance_ratio,
        ai_judgment=article.ai_judgment,
        ai_text_analysis=article.ai_text_analysis,
        ai_image_analysis=article.ai_image_analysis,
        ai_type_judgment=article.ai_type_judgment,
        ai_combined_analysis=article.ai_combined_analysis,
        ai_target_match=article.ai_target_match,
        ai_analysis_status=article.ai_analysis_status,
        ai_analysis_error=article.ai_analysis_error,
        fetch_mode=article.fetch_mode,
        source_payload=article.source_payload,
        created_at=article.created_at,
        updated_at=article.updated_at,
        account_name=(
            article.monitored_account.name
            if getattr(article, "monitored_account", None)
            else None
        ),
    )


@router.get("/", response_model=ArticleListResponse)
async def list_articles(
    db: DbSession,
    current_user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    monitored_account_id: int | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    min_relevance: float | None = Query(None, ge=0, le=1),
    max_relevance: float | None = Query(None, ge=0, le=1),
):
    """Get paginated list of articles with filters."""
    article_service = ArticleService(db)

    # Parse dates
    from datetime import datetime

    start_dt = None
    end_dt = None
    if start_date:
        start_dt = datetime.fromisoformat(start_date)
    if end_date:
        end_dt = datetime.fromisoformat(end_date)

    articles, total = await article_service.get_articles_paginated(
        page=page,
        page_size=page_size,
        monitored_account_id=monitored_account_id,
        start_date=start_dt,
        end_date=end_dt,
        current_user=current_user,
    )

    # Filter by relevance if specified
    if min_relevance is not None or max_relevance is not None:
        filtered = []
        for a in articles:
            if a.ai_relevance_ratio is not None:
                if min_relevance is not None and a.ai_relevance_ratio < min_relevance:
                    continue
                if max_relevance is not None and a.ai_relevance_ratio > max_relevance:
                    continue
            filtered.append(a)
        articles = filtered
        total = len(filtered)

    total_pages = (total + page_size - 1) // page_size

    return ArticleListResponse(
        total=total,
        items=[_article_to_response(a) for a in articles],
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/monitored/{monitored_account_id}", response_model=ArticleListResponse)
async def get_monitored_account_articles(
    monitored_account_id: int,
    db: DbSession,
    current_user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
):
    """Get articles for a monitored account."""
    article_service = ArticleService(db)
    articles, total = await article_service.get_articles_paginated(
        page=page,
        page_size=page_size,
        monitored_account_id=monitored_account_id,
        current_user=current_user,
    )
    total_pages = (total + page_size - 1) // page_size
    return ArticleListResponse(
        total=total,
        items=[_article_to_response(a) for a in articles],
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/{article_id}", response_model=ArticleResponse)
async def get_article(
    article_id: int,
    db: DbSession,
    current_user: CurrentUser,
):
    """Get article by ID."""
    article_service = ArticleService(db)

    article = await article_service.get_visible_article(article_id, current_user)
    if article is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Article {article_id} not found",
        )

    return ArticleResponse.model_validate(article)


@router.delete("/{article_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_article(
    article_id: int,
    db: DbSession,
    current_user: CurrentUser,
):
    """Delete a visible article."""
    article_service = ArticleService(db)
    deleted = await article_service.delete_visible_article(article_id, current_user)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Article {article_id} not found",
        )


@router.post("/{article_id}/reanalyze-ai", response_model=ArticleResponse)
async def reanalyze_article_ai(
    article_id: int,
    background_tasks: BackgroundTasks,
    db: DbSession,
    current_user: CurrentUser,
):
    """Queue the three-stage AI pipeline again for a visible article."""
    article_service = ArticleService(db)
    article = await article_service.get_visible_article(article_id, current_user)
    if article is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Article {article_id} not found")
    updated = await article_service.mark_ai_pending(article.id)
    await db.commit()
    background_tasks.add_task(run_article_ai_analysis, article.id)
    return ArticleResponse.model_validate(updated)
