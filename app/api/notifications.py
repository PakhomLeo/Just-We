"""Notification API routes."""

from fastapi import APIRouter, HTTPException, Query

from app.core.dependencies import DbSession, CurrentUser
from app.services.notification_service import NotificationService


router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("/")
async def list_notifications(
    db: DbSession,
    current_user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    unread_only: bool = False,
):
    """Get paginated list of notifications."""
    notification_service = NotificationService(db)

    notifications = await notification_service.get_notifications(
        owner_user_id=None if current_user.role.value == "admin" else current_user.id,
        skip=(page - 1) * page_size,
        limit=page_size,
        unread_only=unread_only,
    )
    owner_user_id = None if current_user.role.value == "admin" else current_user.id
    total = await notification_service.get_total_count(owner_user_id=owner_user_id, unread_only=unread_only)
    unread_count = await notification_service.get_unread_count(owner_user_id=owner_user_id)

    return {
        "total": total,
        "unread_count": unread_count,
        "items": [_notification_to_dict(n) for n in notifications],
        "page": page,
        "page_size": page_size,
    }


@router.put("/{notification_id}/read")
async def mark_notification_read(
    notification_id: int,
    db: DbSession,
    current_user: CurrentUser,
):
    """Mark a notification as read."""
    notification_service = NotificationService(db)

    notification = await notification_service.mark_as_read(
        notification_id,
        owner_user_id=None if current_user.role.value == "admin" else current_user.id,
    )
    if notification is None:
        raise HTTPException(
            status_code=404,
            detail=f"Notification {notification_id} not found",
        )

    return _notification_to_dict(notification)


@router.put("/read-all")
async def mark_all_read(
    db: DbSession,
    current_user: CurrentUser,
):
    """Mark all notifications as read."""
    notification_service = NotificationService(db)
    count = await notification_service.mark_all_as_read(
        owner_user_id=None if current_user.role.value == "admin" else current_user.id
    )

    return {"marked_count": count}


@router.delete("/{notification_id}", status_code=204)
async def delete_notification(
    notification_id: int,
    db: DbSession,
    current_user: CurrentUser,
):
    """Delete a notification."""
    notification_service = NotificationService(db)
    deleted = await notification_service.delete_notification(
        notification_id,
        owner_user_id=None if current_user.role.value == "admin" else current_user.id,
    )
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Notification {notification_id} not found")


def _notification_to_dict(notification) -> dict:
    """Convert Notification to dict."""
    return {
        "id": notification.id,
        "owner_user_id": str(notification.owner_user_id) if notification.owner_user_id else None,
        "collector_account_id": notification.collector_account_id,
        "monitored_account_id": notification.monitored_account_id,
        "article_id": notification.article_id,
        "notification_type": notification.notification_type,
        "title": notification.title,
        "content": notification.content,
        "is_read": notification.is_read,
        "payload": notification.payload,
        "created_at": notification.created_at.isoformat() if notification.created_at else None,
    }
