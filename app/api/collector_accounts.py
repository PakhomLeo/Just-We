"""Collector account API routes."""

from fastapi import APIRouter, HTTPException

from app.core.dependencies import CurrentUser, DbSession
from app.schemas.collector_account import CollectorAccountListResponse, CollectorAccountResponse
from app.schemas.qr import QRGenerateRequest, QRGenerateResponse, QRStatusResponse
from app.services.collector_account_service import CollectorAccountService
from app.services.health_service import health_check_service
from app.services.notification_service import NotificationService
from app.services.qr_login_service import QRLoginService


router = APIRouter(prefix="/collector-accounts", tags=["Collector Accounts"])


@router.get("/", response_model=CollectorAccountListResponse)
async def list_collector_accounts(db: DbSession, current_user: CurrentUser):
    service = CollectorAccountService(db)
    items = await service.list_visible(current_user, include_all=True)
    return CollectorAccountListResponse(total=len(items), items=[CollectorAccountResponse.model_validate(item) for item in items])


@router.post("/qr/generate", response_model=QRGenerateResponse)
async def generate_qr_code(request: QRGenerateRequest, db: DbSession, current_user: CurrentUser):
    return await QRLoginService(db).generate(request, current_user)


@router.get("/qr/status", response_model=QRStatusResponse)
async def get_qr_status(ticket: str, db: DbSession, current_user: CurrentUser):
    return await QRLoginService(db).get_status(ticket, current_user)


@router.delete("/qr/{ticket}", status_code=204)
async def cancel_qr(ticket: str, db: DbSession, current_user: CurrentUser):
    await QRLoginService(db).cancel(ticket)


@router.post("/qr/confirm", response_model=CollectorAccountResponse)
async def confirm_qr(ticket: str, db: DbSession, current_user: CurrentUser, display_name: str = "已绑定抓取账号"):
    account = await QRLoginService(db).confirm(ticket=ticket, current_user=current_user, display_name=display_name)
    return CollectorAccountResponse.model_validate(account)


@router.post("/qr/simulate-scan", response_model=QRStatusResponse)
async def simulate_scan(ticket: str, db: DbSession, current_user: CurrentUser):
    return await QRLoginService(db).simulate_scan(ticket)


@router.post("/qr/simulate-confirm", response_model=CollectorAccountResponse)
async def simulate_confirm(ticket: str, db: DbSession, current_user: CurrentUser, display_name: str = "Mock Collector Account"):
    account = await QRLoginService(db).simulate_confirm(ticket=ticket, current_user=current_user, display_name=display_name)
    return CollectorAccountResponse.model_validate(account)


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


@router.delete("/{collector_account_id}", status_code=204)
async def delete_collector_account(collector_account_id: int, db: DbSession, current_user: CurrentUser):
    service = CollectorAccountService(db)
    account = await service.get_visible(collector_account_id, current_user)
    if account is None:
        raise HTTPException(status_code=404, detail="Collector account not found")
    await service.repo.delete(account)
