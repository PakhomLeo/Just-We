"""Article JSON export API routes."""

from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import FileResponse

from app.core.config import get_settings
from app.core.dependencies import CurrentUser, DbSession
from app.schemas.article_export import (
    ArticleExportCreate,
    ArticleExportListResponse,
    ArticleExportRecordResponse,
)
from app.repositories.log_repo import LogRepository
from app.services.article_export_service import ArticleExportService


router = APIRouter(prefix="/article-exports", tags=["Article Exports"])


def _record_response(record) -> ArticleExportRecordResponse:
    return ArticleExportRecordResponse(
        id=record.id,
        scope=record.scope,
        target_match=record.target_match,
        include_exported=record.include_exported,
        filters=record.filters or {},
        article_count=record.article_count,
        file_name=record.file_name,
        status=getattr(record.status, "value", record.status),
        error=record.error,
        created_at=record.created_at,
        updated_at=record.updated_at,
        download_url=f"/api/article-exports/{record.id}/download",
    )


@router.get("/", response_model=ArticleExportListResponse)
async def list_article_exports(
    db: DbSession,
    current_user: CurrentUser,
    limit: int = Query(20, ge=1, le=100),
):
    records, total = await ArticleExportService(db).list_records(current_user, limit=limit)
    return ArticleExportListResponse(total=total, items=[_record_response(record) for record in records])


@router.post("/", response_model=ArticleExportRecordResponse)
async def create_article_export(
    payload: ArticleExportCreate,
    db: DbSession,
    current_user: CurrentUser,
):
    record = await ArticleExportService(db).create_export(payload, current_user)
    if payload.scope == "account" and payload.monitored_account_id is not None:
        await LogRepository(db).create_log(
            user_id=current_user.id,
            action="create_article_export",
            target_type="monitored_account",
            target_id=payload.monitored_account_id,
            after_state={
                "export_id": record.id,
                "article_count": record.article_count,
                "file_name": record.file_name,
                "target_match": record.target_match,
            },
            detail=f"按监测对象导出 JSON：{record.file_name}",
        )
    await LogRepository(db).create_log(
        user_id=current_user.id,
        action="create_article_export",
        target_type="article_export",
        target_id=record.id,
        after_state={
            "scope": record.scope,
            "monitored_account_id": payload.monitored_account_id,
            "article_count": record.article_count,
            "file_name": record.file_name,
            "status": getattr(record.status, "value", record.status),
        },
        detail=f"生成文章 JSON 导出：{record.file_name}",
    )
    return _record_response(record)


@router.get("/{record_id}/download")
async def download_article_export(
    record_id: int,
    db: DbSession,
    current_user: CurrentUser,
):
    service = ArticleExportService(db)
    record = await service.get_record(record_id, current_user)
    if record is None:
        raise HTTPException(status_code=404, detail="导出记录不存在")
    path = Path(get_settings().media_root) / record.file_path
    if not path.exists():
        raise HTTPException(status_code=404, detail="导出文件不存在，请重新导出")
    return FileResponse(
        path,
        media_type="application/json; charset=utf-8",
        filename=record.file_name,
    )


@router.delete("/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_article_export(
    record_id: int,
    db: DbSession,
    current_user: CurrentUser,
):
    service = ArticleExportService(db)
    record = await service.get_record(record_id, current_user)
    if record is None:
        raise HTTPException(status_code=404, detail="导出记录不存在")
    await service.delete_record(record)
