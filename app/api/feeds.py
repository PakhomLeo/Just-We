"""Authenticated feed utility endpoints."""

from fastapi import APIRouter, HTTPException, Query, Request, Response

from app.core.dependencies import CurrentUser, DbSession
from app.services.feed_service import FeedService


router = APIRouter(prefix="/feeds", tags=["Feeds"])


@router.get("/export")
async def export_feeds(
    request: Request,
    db: DbSession,
    current_user: CurrentUser,
    format: str = Query("opml", pattern="^(opml|csv)$"),
):
    service = FeedService(db, public_base_url=str(request.base_url).rstrip("/"))
    try:
        body, media_type, filename = await service.export_visible(current_user, format)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return Response(
        content=body,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
