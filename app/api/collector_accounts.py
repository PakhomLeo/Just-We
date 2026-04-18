"""Collector account API routes."""

from fastapi import APIRouter, HTTPException, status
from redis.exceptions import RedisError

from app.core.dependencies import CurrentUser, DbSession
from app.core.exceptions import QRProviderNotConfiguredException
from app.schemas.collector_account import (
    CollectorAccountListResponse,
    CollectorAccountResponse,
    CollectorLoginProxyUpdate,
)
from app.schemas.qr import QRGenerateRequest, QRGenerateResponse, QRStatusResponse
from app.services.collector_account_service import CollectorAccountService
from app.services.health_service import health_check_service
from app.services.notification_service import NotificationService
from app.services.qr_login_service import QRLoginService
from app.services.qr_providers import discover_mp_admin_profile


router = APIRouter(prefix="/collector-accounts", tags=["Collector Accounts"])


@router.get("/", response_model=CollectorAccountListResponse)
async def list_collector_accounts(db: DbSession, current_user: CurrentUser):
    service = CollectorAccountService(db)
    items = await service.list_visible(current_user, include_all=True)
    return CollectorAccountListResponse(total=len(items), items=[CollectorAccountResponse.model_validate(item) for item in items])


@router.post("/qr/generate", response_model=QRGenerateResponse)
async def generate_qr_code(request: QRGenerateRequest, db: DbSession, current_user: CurrentUser):
    try:
        return await QRLoginService(db).generate(request, current_user)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except QRProviderNotConfiguredException as exc:
        provider = exc.details.get("provider", "QR provider")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"{provider} 未配置，暂时无法生成二维码",
        ) from exc
    except RedisError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Redis is unavailable; QR login state cannot be stored",
        ) from exc


@router.get("/qr/status", response_model=QRStatusResponse)
async def get_qr_status(ticket: str, db: DbSession, current_user: CurrentUser):
    return await QRLoginService(db).get_status(ticket, current_user)


@router.delete("/qr/{ticket}", status_code=204)
async def cancel_qr(ticket: str, db: DbSession, current_user: CurrentUser):
    await QRLoginService(db).cancel(ticket)


@router.post("/{collector_account_id}/health-check", response_model=CollectorAccountResponse)
async def health_check_collector(collector_account_id: int, db: DbSession, current_user: CurrentUser):
    service = CollectorAccountService(db)
    account = await service.get_visible(collector_account_id, current_user)
    if account is None:
        raise HTTPException(status_code=404, detail="Collector account not found")
    notification_service = NotificationService(db)
    health_status, reason, expires_at = await health_check_service.check_collector_account_health(account)
    updated = await service.mark_health(account, health_status, reason)
    if expires_at and reason == "凭证即将过期":
        await notification_service.notify_collector_expiring_soon(updated, expires_at)
    elif health_status.value != "normal":
        await notification_service.notify_collector_health_issue(updated, health_status, reason)
    return CollectorAccountResponse.model_validate(updated)


@router.post("/{collector_account_id}/discover-fakeid", response_model=CollectorAccountResponse)
async def discover_collector_fakeid(collector_account_id: int, db: DbSession, current_user: CurrentUser):
    service = CollectorAccountService(db)
    account = await service.get_visible(collector_account_id, current_user)
    if account is None:
        raise HTTPException(status_code=404, detail="Collector account not found")
    if account.account_type.value != "mp_admin":
        raise HTTPException(status_code=400, detail="Only mp_admin collector accounts support fakeid discovery")
    profile = await discover_mp_admin_profile(account.credentials or {})
    updated = await service.update_discovered_profile(account, profile)
    return CollectorAccountResponse.model_validate(updated)


@router.put("/{collector_account_id}/login-proxy", response_model=CollectorAccountResponse)
async def update_collector_login_proxy(
    collector_account_id: int,
    request: CollectorLoginProxyUpdate,
    db: DbSession,
    current_user: CurrentUser,
):
    service = CollectorAccountService(db)
    account = await service.get_visible(collector_account_id, current_user)
    if account is None:
        raise HTTPException(status_code=404, detail="Collector account not found")
    if account.account_type.value != "mp_admin":
        raise HTTPException(status_code=400, detail="Only mp_admin collector accounts can bind a login proxy")
    if request.login_proxy_id is not None:
        from app.repositories.proxy_repo import ProxyRepository
        from app.models.proxy import ProxyServiceKey
        from app.services.proxy_service import ProxyService

        proxy = await ProxyRepository(db).get_by_id(request.login_proxy_id)
        if proxy is None:
            raise HTTPException(status_code=404, detail="Proxy not found")
        if ProxyServiceKey.MP_ADMIN_LOGIN not in ProxyService(db).compatible_service_keys(proxy):
            raise HTTPException(status_code=400, detail="所选代理类型不能用于公众号管理员登录")
    updated = await service.update_login_proxy(account, request.login_proxy_id)
    return CollectorAccountResponse.model_validate(updated)


@router.delete("/{collector_account_id}", status_code=204)
async def delete_collector_account(collector_account_id: int, db: DbSession, current_user: CurrentUser):
    service = CollectorAccountService(db)
    account = await service.get_visible(collector_account_id, current_user)
    if account is None:
        raise HTTPException(status_code=404, detail="Collector account not found")
    await service.repo.delete(account)
