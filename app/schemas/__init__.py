"""Pydantic schemas for API request/response validation."""

from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    Token,
    TokenPayload,
    UserResponse,
    UserUpdate,
)
from app.schemas.article import (
    ArticleResponse,
    ArticleListResponse,
    ArticleCreate,
    ArticleFilter,
)
from app.schemas.proxy import (
    ProxyCreate,
    ProxyUpdate,
    ProxyResponse,
    ProxyTestResult,
    ProxyListResponse,
)
from app.schemas.qr import (
    QRGenerateRequest,
    QRGenerateResponse,
    QRStatusResponse,
    QRData,
)
from app.schemas.weight import (
    WeightConfig,
    WeightConfigUpdate,
    WeightSimulateInput,
    WeightSimulateResult,
    WeightUpdateEvent,
)

__all__ = [
    "LoginRequest",
    "RegisterRequest",
    "Token",
    "TokenPayload",
    "UserResponse",
    "UserUpdate",
    "ArticleResponse",
    "ArticleListResponse",
    "ArticleCreate",
    "ArticleFilter",
    "ProxyCreate",
    "ProxyUpdate",
    "ProxyResponse",
    "ProxyTestResult",
    "ProxyListResponse",
    "QRGenerateRequest",
    "QRGenerateResponse",
    "QRStatusResponse",
    "QRData",
    "WeightConfig",
    "WeightConfigUpdate",
    "WeightSimulateInput",
    "WeightSimulateResult",
    "WeightUpdateEvent",
]
