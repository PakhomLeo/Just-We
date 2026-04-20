"""System configuration API routes."""

from time import perf_counter
from types import SimpleNamespace

from fastapi import APIRouter

from app.core.dependencies import AdminUser, DbSession
from app.core.config import get_settings
from app.models.user import UserRole
from app.schemas.system_config import (
    AIConfigPayload,
    AIConfigTestPayload,
    AIConfigTestResponse,
    DefaultAdminPayload,
    DefaultAdminUpdatePayload,
    FetchPolicyPayload,
    NotificationEmailConfigPayload,
    NotificationPolicyPayload,
    ProxyPolicyPayload,
    RateLimitPolicyPayload,
)
from app.services.ai_service import AIService
from app.services.auth_service import AuthService
from app.services.system_config_service import SystemConfigService


router = APIRouter(prefix="/system", tags=["System Config"])
settings = get_settings()


@router.get("/ai-config", response_model=AIConfigPayload)
async def get_ai_config(db: DbSession, current_user: AdminUser):
    config = await SystemConfigService(db).get_or_create_ai_config()
    return AIConfigPayload.model_validate(config, from_attributes=True)


@router.put("/ai-config", response_model=AIConfigPayload)
async def update_ai_config(payload: AIConfigPayload, db: DbSession, current_user: AdminUser):
    config = await SystemConfigService(db).update_ai_config(**payload.model_dump())
    return AIConfigPayload.model_validate(config, from_attributes=True)


@router.post("/ai-config/test", response_model=AIConfigTestResponse)
async def test_ai_config(payload: AIConfigTestPayload, db: DbSession, current_user: AdminUser):
    """Test the supplied AI config with a dedicated connectivity payload."""
    started_at = perf_counter()
    service = AIService()
    service.config = SimpleNamespace(**payload.config.model_dump())
    if payload.stage == "text":
        api_config = service._text_api_config()
        prompt = (
            'Just-We AI connectivity test. Return exactly one JSON object like '
            '{"ok":true,"service":"text","message":"pong"}. Do not analyze any article.'
        )
        image_paths = None
    else:
        api_config = service._image_api_config()
        prompt = (
            'Just-We image AI connectivity test. The attached 16x16 PNG is a synthetic test fixture. '
            'Return exactly one JSON object like {"ok":true,"service":"image","message":"pong"}.'
        )
        image_paths = [
            "data:image/png;base64,"
            "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAIAAACQkWg2AAAAFElEQVR4nGP4TyJgGNUwqmH4agAAr639H708R/EAAAAASUVORK5CYII="
        ]
    endpoint = service._normalize_chat_completions_url(str(api_config.get("api_url") or ""), str(api_config.get("model") or ""))
    try:
        result = await service._call_json_stage(
            api_config=api_config,
            prompt=prompt,
            image_paths=image_paths,
        )
        return AIConfigTestResponse(
            success=True,
            stage=payload.stage,
            status="success",
            model=str(api_config.get("model") or ""),
            endpoint=endpoint,
            duration_ms=int((perf_counter() - started_at) * 1000),
            result=result,
        )
    except Exception as exc:
        return AIConfigTestResponse(
            success=False,
            stage=payload.stage,
            status="failed",
            model=str(api_config.get("model") or ""),
            endpoint=endpoint,
            duration_ms=int((perf_counter() - started_at) * 1000),
            error=str(exc),
        )


@router.get("/fetch-policy", response_model=FetchPolicyPayload)
async def get_fetch_policy(db: DbSession, current_user: AdminUser):
    config = await SystemConfigService(db).get_or_create_fetch_policy()
    return FetchPolicyPayload.model_validate(config, from_attributes=True)


@router.put("/fetch-policy", response_model=FetchPolicyPayload)
async def update_fetch_policy(payload: FetchPolicyPayload, db: DbSession, current_user: AdminUser):
    config = await SystemConfigService(db).update_fetch_policy(**payload.model_dump())
    return FetchPolicyPayload.model_validate(config, from_attributes=True)


@router.get("/rate-limit-policy", response_model=RateLimitPolicyPayload)
async def get_rate_limit_policy(db: DbSession, current_user: AdminUser):
    payload = await SystemConfigService(db).get_rate_limit_policy()
    return RateLimitPolicyPayload(**payload)


@router.put("/rate-limit-policy", response_model=RateLimitPolicyPayload)
async def update_rate_limit_policy(payload: RateLimitPolicyPayload, db: DbSession, current_user: AdminUser):
    config = await SystemConfigService(db).update_rate_limit_policy(**payload.model_dump())
    return RateLimitPolicyPayload(**(config.rate_limit_policy or {}))


@router.get("/proxy-policy", response_model=ProxyPolicyPayload)
async def get_proxy_policy(db: DbSession, current_user: AdminUser):
    payload = await SystemConfigService(db).get_proxy_policy()
    return ProxyPolicyPayload(**payload)


@router.put("/proxy-policy", response_model=ProxyPolicyPayload)
async def update_proxy_policy(payload: ProxyPolicyPayload, db: DbSession, current_user: AdminUser):
    result = await SystemConfigService(db).update_proxy_policy(**payload.model_dump())
    return ProxyPolicyPayload(**result)


@router.get("/notification-email", response_model=NotificationEmailConfigPayload)
async def get_notification_email_config(db: DbSession, current_user: AdminUser):
    config = await SystemConfigService(db).get_or_create_notification_email_config()
    return NotificationEmailConfigPayload.model_validate(config, from_attributes=True)


@router.put("/notification-email", response_model=NotificationEmailConfigPayload)
async def update_notification_email_config(payload: NotificationEmailConfigPayload, db: DbSession, current_user: AdminUser):
    config = await SystemConfigService(db).update_notification_email_config(**payload.model_dump())
    return NotificationEmailConfigPayload.model_validate(config, from_attributes=True)


@router.get("/notification-policy", response_model=NotificationPolicyPayload)
async def get_notification_policy(db: DbSession, current_user: AdminUser):
    payload = await SystemConfigService(db).get_notification_policy()
    return NotificationPolicyPayload(**payload)


@router.put("/notification-policy", response_model=NotificationPolicyPayload)
async def update_notification_policy(payload: NotificationPolicyPayload, db: DbSession, current_user: AdminUser):
    result = await SystemConfigService(db).update_notification_policy(**payload.model_dump())
    return NotificationPolicyPayload(**result)


@router.get("/default-admin", response_model=DefaultAdminPayload)
async def get_default_admin(db: DbSession, current_user: AdminUser):
    auth = AuthService(db)
    user = await auth.user_repo.get_by_email(settings.default_admin_email)
    user = user or await auth.user_repo.get_first_admin()
    return DefaultAdminPayload(
        email=user.email if user else settings.default_admin_email,
        alias=settings.default_admin_alias,
        password="",
    )


@router.put("/default-admin", response_model=DefaultAdminPayload)
async def update_default_admin(payload: DefaultAdminUpdatePayload, db: DbSession, current_user: AdminUser):
    auth = AuthService(db)
    user = await auth.user_repo.get_by_email(settings.default_admin_email)
    user = user or await auth.user_repo.get_first_admin()
    if user is None:
        user = await auth.user_repo.create(
            email=str(payload.email),
            username=settings.default_admin_alias,
            hashed_password=auth.hash_password(payload.password or settings.default_admin_password),
            role=UserRole.ADMIN,
            is_active=True,
            is_superuser=True,
        )
    else:
        user.email = str(payload.email)
        user.username = user.username or settings.default_admin_alias
        user.role = UserRole.ADMIN
        user.is_active = True
        user.is_superuser = True
        if payload.password:
            user.hashed_password = auth.hash_password(payload.password)
        await db.flush()
        await db.refresh(user)
    return DefaultAdminPayload(email=user.email, alias=settings.default_admin_alias, password="")
