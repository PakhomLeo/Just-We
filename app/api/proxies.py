"""Proxy API routes."""

from fastapi import APIRouter, HTTPException, status, Query

from app.core.dependencies import DbSession, CurrentUser, AdminUser, OperatorUser
from app.models.proxy import ProxyServiceKey, ServiceType
from app.schemas.proxy import (
    ProxyCreate,
    ProxyUpdate,
    ProxyResponse,
    ProxyTestResult,
    ProxyListResponse,
    ProxyBulkCreate,
    ProxyBulkCreateResponse,
    ProxyServicesResponse,
    ProxyServicesUpdate,
)
from app.services.proxy_service import ProxyService


router = APIRouter(prefix="/proxies", tags=["Proxies"])


def _proxy_response(proxy) -> ProxyResponse:
    return ProxyResponse.model_validate(proxy)


@router.get("/", response_model=ProxyListResponse)
async def list_proxies(
    db: DbSession,
    current_user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    service_type: ServiceType | None = None,
    service_key: ProxyServiceKey | None = None,
    active_only: bool = True,
):
    """Get paginated list of proxies."""
    proxy_service = ProxyService(db)

    if service_key:
        proxies = await proxy_service.get_proxies_by_service_key(service_key, active_only)
        total = len(proxies)
        proxies = proxies[(page - 1) * page_size : page * page_size]
    elif service_type:
        proxies = await proxy_service.get_proxies_by_service_type(service_type, active_only)
        total = len(proxies)
        proxies = proxies[(page - 1) * page_size : page * page_size]
    else:
        proxies = await proxy_service.get_all_proxies(
            skip=(page - 1) * page_size,
            limit=page_size,
        )
        total = await proxy_service.get_proxy_count()

    total_pages = (total + page_size - 1) // page_size

    return ProxyListResponse(
        total=total,
        items=[_proxy_response(p) for p in proxies],
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/stats")
async def get_proxy_stats(
    db: DbSession,
    current_user: CurrentUser,
):
    """Get proxy statistics."""
    proxy_service = ProxyService(db)
    return await proxy_service.get_proxy_stats()


@router.post("/", response_model=ProxyResponse, status_code=status.HTTP_201_CREATED)
async def create_proxy(
    request: ProxyCreate,
    db: DbSession,
    current_user: OperatorUser,
):
    """Create a new proxy."""
    proxy_service = ProxyService(db)

    try:
        proxy = await proxy_service.create_proxy(
            host=request.host,
            port=request.port,
            service_type=request.service_type,
            username=request.username,
            password=request.password,
            proxy_kind=request.proxy_kind,
            rotation_mode=request.rotation_mode,
            sticky_ttl_seconds=request.sticky_ttl_seconds,
            provider_name=request.provider_name,
            notes=request.notes,
            service_keys=request.service_keys,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return _proxy_response(proxy)


@router.post("/bulk", response_model=ProxyBulkCreateResponse, status_code=status.HTTP_201_CREATED)
async def bulk_create_proxies(
    request: ProxyBulkCreate,
    db: DbSession,
    current_user: OperatorUser,
):
    proxy_service = ProxyService(db)
    try:
        proxies = await proxy_service.bulk_create([item.model_dump() for item in request.proxies])
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ProxyBulkCreateResponse(
        created=len(proxies),
        items=[_proxy_response(proxy) for proxy in proxies],
    )


@router.put("/{proxy_id}", response_model=ProxyResponse)
async def update_proxy(
    proxy_id: int,
    request: ProxyUpdate,
    db: DbSession,
    current_user: OperatorUser,
):
    """Update a proxy."""
    proxy_service = ProxyService(db)

    update_data = {k: v for k, v in request.model_dump().items() if v is not None}
    try:
        proxy = await proxy_service.update_proxy(proxy_id, **update_data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return _proxy_response(proxy)


@router.get("/{proxy_id}/services", response_model=ProxyServicesResponse)
async def get_proxy_services(
    proxy_id: int,
    db: DbSession,
    current_user: CurrentUser,
):
    proxy_service = ProxyService(db)
    from app.repositories.proxy_repo import ProxyRepository

    proxy = await ProxyRepository(db).get_by_id(proxy_id)
    if proxy is None:
        raise HTTPException(status_code=404, detail=f"Proxy {proxy_id} not found")
    return ProxyServicesResponse(
        proxy_id=proxy.id,
        service_keys=proxy.service_keys,
        compatible_service_keys=proxy_service.compatible_service_keys(proxy),
        incompatible_reasons=proxy_service.incompatible_reasons(proxy),
    )


@router.put("/{proxy_id}/services", response_model=ProxyServicesResponse)
async def update_proxy_services(
    proxy_id: int,
    request: ProxyServicesUpdate,
    db: DbSession,
    current_user: OperatorUser,
):
    proxy_service = ProxyService(db)
    from app.repositories.proxy_repo import ProxyRepository

    proxy = await ProxyRepository(db).get_by_id(proxy_id)
    if proxy is None:
        raise HTTPException(status_code=404, detail=f"Proxy {proxy_id} not found")
    try:
        service_keys = await proxy_service.replace_service_bindings(proxy, request.service_keys)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ProxyServicesResponse(
        proxy_id=proxy.id,
        service_keys=service_keys,
        compatible_service_keys=proxy_service.compatible_service_keys(proxy),
        incompatible_reasons=proxy_service.incompatible_reasons(proxy),
    )


@router.delete("/{proxy_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_proxy(
    proxy_id: int,
    db: DbSession,
    current_user: AdminUser,
):
    """Delete a proxy."""
    proxy_service = ProxyService(db)
    await proxy_service.delete_proxy(proxy_id)


@router.post("/{proxy_id}/test", response_model=ProxyTestResult)
async def test_proxy(
    proxy_id: int,
    db: DbSession,
    current_user: OperatorUser,
):
    """Test a proxy connection."""
    proxy_service = ProxyService(db)

    from app.repositories.proxy_repo import ProxyRepository
    proxy_repo = ProxyRepository(db)
    proxy = await proxy_repo.get_by_id(proxy_id)

    if proxy is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Proxy {proxy_id} not found",
        )

    result = await proxy_service.test_proxy(proxy)
    return ProxyTestResult(**result)
