"""Public feed endpoints."""

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Request, Response

from app.core.dependencies import DbSession
from app.services.feed_service import FeedService
from app.tasks.fetch_task import run_single_account


router = APIRouter(prefix="/feeds", tags=["Public Feeds"])


def _public_base_url(request: Request) -> str:
    return str(request.base_url).rstrip("/")


@router.get("/all/{token}.{feed_type}")
async def aggregate_feed(
    token: str,
    feed_type: str,
    request: Request,
    db: DbSession,
    limit: int = Query(50, ge=1, le=200),
    page: int = Query(1, ge=1),
    mode: str = Query("summary", pattern="^(summary|fulltext)$"),
    title_include: str | None = None,
    title_exclude: str | None = None,
):
    service = FeedService(db, public_base_url=_public_base_url(request))
    user = await service.get_user_by_aggregate_token(token)
    if user is None:
        raise HTTPException(status_code=404, detail="Feed not found")
    try:
        body, media_type = await service.generate_aggregate(
            user,
            feed_type,
            limit=limit,
            page=page,
            mode=mode,
            title_include=title_include,
            title_exclude=title_exclude,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return Response(content=body, media_type=media_type)


@router.get("/{token}.{feed_type}")
async def single_feed(
    token: str,
    feed_type: str,
    request: Request,
    background_tasks: BackgroundTasks,
    db: DbSession,
    limit: int = Query(50, ge=1, le=200),
    page: int = Query(1, ge=1),
    mode: str = Query("summary", pattern="^(summary|fulltext)$"),
    title_include: str | None = None,
    title_exclude: str | None = None,
    update: bool = False,
):
    service = FeedService(db, public_base_url=_public_base_url(request))
    account = await service.get_account_by_token(token)
    if account is None:
        raise HTTPException(status_code=404, detail="Feed not found")
    if update:
        background_tasks.add_task(run_single_account, account.id)
    try:
        body, media_type = await service.generate_for_account(
            account,
            feed_type,
            limit=limit,
            page=page,
            mode=mode,
            title_include=title_include,
            title_exclude=title_exclude,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return Response(content=body, media_type=media_type)
