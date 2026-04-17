"""QR Code login API routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import DbSession, CurrentUser
from app.core.exceptions import QRCodeNotFoundException
from app.schemas.qr import (
    QRGenerateRequest,
    QRGenerateResponse,
    QRStatusResponse,
)
from app.services.qr_login_service import QRLoginService


router = APIRouter(prefix="/accounts/qr", tags=["QR Login"])


@router.post("/generate", response_model=QRGenerateResponse)
async def generate_qr_code(
    request: QRGenerateRequest,
    db: DbSession,
    current_user: CurrentUser,
):
    """Generate a new QR code for login."""
    qr_service = QRLoginService(db)
    return await qr_service.generate(request, current_user)


@router.get("/status", response_model=QRStatusResponse)
async def get_qr_status(
    ticket: str,
    db: DbSession,
    current_user: CurrentUser,
):
    """Get QR code status (poll this endpoint)."""
    qr_service = QRLoginService(db)

    try:
        return await qr_service.get_status(ticket, current_user)
    except QRCodeNotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="QR code not found or expired",
        )


@router.delete("/{ticket}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_qr_login(
    ticket: str,
    db: DbSession,
    current_user: CurrentUser,
):
    """Cancel a QR login attempt."""
    qr_service = QRLoginService(db)
    await qr_service.cancel(ticket)


# Mock endpoints for testing
@router.post("/simulate/scan", response_model=QRStatusResponse)
async def simulate_scan(
    ticket: str,
    db: DbSession,
    current_user: CurrentUser,
):
    """Simulate QR code scan (for testing only)."""
    qr_service = QRLoginService(db)
    return await qr_service.simulate_scan(ticket)


@router.post("/simulate/confirm", response_model=dict)
async def simulate_confirm(
    ticket: str,
    db: DbSession,
    current_user: CurrentUser,
    name: str = "Mock Account",
):
    """Simulate QR code confirmation (for testing only)."""
    qr_service = QRLoginService(db)
    account = await qr_service.simulate_confirm(ticket, current_user, name)
    return {
        "success": True,
        "account_id": account.id,
        "account_name": account.display_name,
    }
