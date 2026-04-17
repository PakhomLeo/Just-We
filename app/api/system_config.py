"""System configuration API routes."""

from fastapi import APIRouter

from app.core.dependencies import AdminUser, DbSession
from app.schemas.system_config import AIConfigPayload, FetchPolicyPayload, NotificationEmailConfigPayload
from app.services.system_config_service import SystemConfigService


router = APIRouter(prefix="/system", tags=["System Config"])


@router.get("/ai-config", response_model=AIConfigPayload)
async def get_ai_config(db: DbSession, current_user: AdminUser):
    config = await SystemConfigService(db).get_or_create_ai_config()
    return AIConfigPayload.model_validate(config, from_attributes=True)


@router.put("/ai-config", response_model=AIConfigPayload)
async def update_ai_config(payload: AIConfigPayload, db: DbSession, current_user: AdminUser):
    config = await SystemConfigService(db).update_ai_config(**payload.model_dump())
    return AIConfigPayload.model_validate(config, from_attributes=True)


@router.get("/fetch-policy", response_model=FetchPolicyPayload)
async def get_fetch_policy(db: DbSession, current_user: AdminUser):
    config = await SystemConfigService(db).get_or_create_fetch_policy()
    return FetchPolicyPayload.model_validate(config, from_attributes=True)


@router.put("/fetch-policy", response_model=FetchPolicyPayload)
async def update_fetch_policy(payload: FetchPolicyPayload, db: DbSession, current_user: AdminUser):
    config = await SystemConfigService(db).update_fetch_policy(**payload.model_dump())
    return FetchPolicyPayload.model_validate(config, from_attributes=True)


@router.get("/notification-email", response_model=NotificationEmailConfigPayload)
async def get_notification_email_config(db: DbSession, current_user: AdminUser):
    config = await SystemConfigService(db).get_or_create_notification_email_config()
    return NotificationEmailConfigPayload.model_validate(config, from_attributes=True)


@router.put("/notification-email", response_model=NotificationEmailConfigPayload)
async def update_notification_email_config(payload: NotificationEmailConfigPayload, db: DbSession, current_user: AdminUser):
    config = await SystemConfigService(db).update_notification_email_config(**payload.model_dump())
    return NotificationEmailConfigPayload.model_validate(config, from_attributes=True)
