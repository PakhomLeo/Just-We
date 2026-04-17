"""Account API routes."""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import DbSession, CurrentUser, AdminUser
from app.core.exceptions import AccountNotFoundException
from app.models.account import AccountStatus, HealthStatus
from app.schemas.account import (
    AccountCreate,
    AccountUpdate,
    AccountResponse,
    AccountListResponse,
    ManualOverrideRequest,
    AccountHistoryResponse,
)
from app.services.account_service import AccountService
from app.services.health_service import health_check_service


router = APIRouter(prefix="/accounts", tags=["Accounts"])


@router.get("/", response_model=AccountListResponse)
async def list_accounts(
    db: DbSession,
    current_user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: AccountStatus | None = None,
    tier: int | None = Query(None, ge=1, le=5),
):
    """Get paginated list of accounts."""
    account_service = AccountService(db)
    accounts, total = await account_service.get_accounts_paginated(
        page=page,
        page_size=page_size,
        status=status,
        tier=tier,
    )

    total_pages = (total + page_size - 1) // page_size

    return AccountListResponse(
        total=total,
        items=[AccountResponse.model_validate(a) for a in accounts],
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.post("/", response_model=AccountResponse, status_code=status.HTTP_201_CREATED)
async def create_account(
    request: AccountCreate,
    db: DbSession,
    current_user: CurrentUser,
):
    """Create a new account (manual biz input)."""
    account_service = AccountService(db)

    # Check if biz already exists
    existing = await account_service.get_account_by_biz(request.biz)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Account with biz '{request.biz}' already exists",
        )

    account = await account_service.create_account(
        biz=request.biz,
        fakeid=request.fakeid,
        name=request.name,
        account_type=request.account_type.value,
        cookies=request.cookies,
    )

    return AccountResponse.model_validate(account)


@router.get("/{account_id}", response_model=AccountResponse)
async def get_account(
    account_id: int,
    db: DbSession,
    current_user: CurrentUser,
):
    """Get account by ID."""
    account_service = AccountService(db)

    try:
        account = await account_service.get_account(account_id)
        return AccountResponse.model_validate(account)
    except AccountNotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Account {account_id} not found",
        )


@router.put("/{account_id}", response_model=AccountResponse)
async def update_account(
    account_id: int,
    request: AccountUpdate,
    db: DbSession,
    current_user: CurrentUser,
):
    """Update account details."""
    account_service = AccountService(db)

    try:
        # Filter out None values
        update_data = {k: v for k, v in request.model_dump().items() if v is not None}

        account = await account_service.update_account(account_id, **update_data)
        return AccountResponse.model_validate(account)
    except AccountNotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Account {account_id} not found",
        )


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    account_id: int,
    db: DbSession,
    current_user: AdminUser,  # Only admin can delete
):
    """Delete an account."""
    account_service = AccountService(db)

    try:
        await account_service.delete_account(account_id)
    except AccountNotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Account {account_id} not found",
        )


@router.post("/{account_id}/override", response_model=AccountResponse)
async def apply_manual_override(
    account_id: int,
    request: ManualOverrideRequest,
    db: DbSession,
    current_user: AdminUser,  # Only admin can override
):
    """Apply manual tier override to an account."""
    account_service = AccountService(db)

    try:
        account = await account_service.apply_manual_override(
            account_id=account_id,
            target_tier=request.target_tier,
            reason=request.reason,
            expire_at=request.expire_at,
        )
        return AccountResponse.model_validate(account)
    except AccountNotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Account {account_id} not found",
        )


@router.delete("/{account_id}/override", response_model=AccountResponse)
async def clear_manual_override(
    account_id: int,
    db: DbSession,
    current_user: AdminUser,
):
    """Clear manual override from an account."""
    account_service = AccountService(db)

    try:
        account = await account_service.clear_manual_override(account_id)
        return AccountResponse.model_validate(account)
    except AccountNotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Account {account_id} not found",
        )


@router.get("/{account_id}/history", response_model=AccountHistoryResponse)
async def get_account_history(
    account_id: int,
    db: DbSession,
    current_user: CurrentUser,
):
    """Get account history including tier changes and overrides."""
    account_service = AccountService(db)

    try:
        history = await account_service.get_account_history(account_id)
        return AccountHistoryResponse(**history)
    except AccountNotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Account {account_id} not found",
        )


@router.post("/{account_id}/crawl")
async def trigger_account_crawl(
    account_id: int,
    db: DbSession,
    current_user: CurrentUser,
):
    """Trigger a manual crawl for a specific account."""
    from app.tasks.fetch_task import run_single_account

    account_service = AccountService(db)

    try:
        account = await account_service.get_account(account_id)
    except AccountNotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Account {account_id} not found",
        )

    # Run the crawl task (in real implementation, this would be a background task)
    await run_single_account(account_id)

    return {
        "message": f"Crawl triggered for account {account_id}",
        "status": "scheduled",
    }


@router.post("/{account_id}/health-check")
async def check_account_health(
    account_id: int,
    db: DbSession,
    current_user: CurrentUser,
):
    """Check health status for a specific account."""
    account_service = AccountService(db)

    try:
        account = await account_service.get_account(account_id)
    except AccountNotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Account {account_id} not found",
        )

    # Perform health check
    health_status, health_reason = await health_check_service.check_account_health(account)

    # Update account with health check results
    await account_service.update_account(
        account_id,
        health_status=health_status,
        last_health_check=datetime.now(timezone.utc),
        health_reason=health_reason,
    )

    # Get updated account
    updated_account = await account_service.get_account(account_id)

    return {
        "account_id": account_id,
        "health_status": health_status.value,
        "health_reason": health_reason,
        "last_health_check": updated_account.last_health_check,
    }


@router.post("/batch-health-check")
async def batch_health_check(
    db: DbSession,
    current_user: CurrentUser,
    account_type: str | None = Query(None, description="Filter by account type: weread or mp"),
):
    """Batch check health status for all accounts or filtered by type."""
    account_service = AccountService(db)

    # Get all accounts or filtered by type
    if account_type:
        accounts = await account_service.get_accounts_by_type(account_type)
    else:
        accounts = await account_service.get_all_accounts()

    results = []
    for account in accounts:
        # Perform health check
        health_status, health_reason = await health_check_service.check_account_health(account)

        # Update account
        await account_service.update_account(
            account.id,
            health_status=health_status,
            last_health_check=datetime.now(timezone.utc),
            health_reason=health_reason,
        )

        results.append({
            "account_id": account.id,
            "account_name": account.name,
            "health_status": health_status.value,
            "health_reason": health_reason,
        })

    # Calculate summary
    summary = {
        "total": len(results),
        "normal": sum(1 for r in results if r["health_status"] == "normal"),
        "restricted": sum(1 for r in results if r["health_status"] == "restricted"),
        "expired": sum(1 for r in results if r["health_status"] == "expired"),
        "invalid": sum(1 for r in results if r["health_status"] == "invalid"),
    }

    return {
        "results": results,
        "summary": summary,
    }
