"""Log API routes."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import DbSession, CurrentUser
from app.repositories.log_repo import LogRepository
from app.models.log import OperationLog


router = APIRouter(prefix="/logs", tags=["Logs"])


@router.get("/")
async def list_logs(
    db: DbSession,
    current_user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    action: str | None = None,
    target_type: str | None = None,
):
    """Get paginated list of operation logs."""
    log_repo = LogRepository(db)
    logs = await log_repo.get_paginated(
        skip=(page - 1) * page_size,
        limit=page_size,
        action=action,
        target_type=target_type,
    )
    total = await log_repo.get_filtered_count(action=action, target_type=target_type)

    total_pages = (total + page_size - 1) // page_size

    return {
        "total": total,
        "items": [_log_to_dict(log) for log in logs],
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


@router.get("/account/{account_id}")
async def get_account_logs(
    account_id: int,
    db: DbSession,
    current_user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
):
    """Get logs for a specific account."""
    log_repo = LogRepository(db)

    logs = await log_repo.get_by_target(
        target_type="account",
        target_id=account_id,
        skip=(page - 1) * page_size,
        limit=page_size,
    )
    total = await log_repo.get_count_by_target("account", account_id)

    return {
        "total": total,
        "items": [_log_to_dict(log) for log in logs],
        "page": page,
        "page_size": page_size,
    }


def _log_to_dict(log: OperationLog) -> dict:
    """Convert OperationLog to dict."""
    # Map to frontend-expected field names
    return {
        "id": log.id,
        "timestamp": log.created_at.isoformat() if log.created_at else None,
        "account": None,  # Frontend expects account name, not user_id
        "event": log.action,
        "result": _infer_result(log.action),
        "duration": None,  # Not tracked in our model
        "detail": log.detail,
        # Raw fields for debugging
        "user_id": str(log.user_id) if log.user_id else None,
        "target_type": log.target_type,
        "target_id": log.target_id,
        "before_state": log.before_state,
        "after_state": log.after_state,
    }


def _infer_result(action: str) -> str:
    """Infer result status from action name."""
    action_lower = action.lower()
    if any(word in action_lower for word in ['delete', 'remove', 'block']):
        return 'failed'
    if any(word in action_lower for word in ['create', 'add', 'update', 'edit', 'login']):
        return 'success'
    return 'pending'
