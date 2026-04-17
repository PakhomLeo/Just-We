"""Custom exceptions for the application."""

from typing import Any


class AppException(Exception):
    """Base application exception."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class AccountNotFoundException(AppException):
    """Raised when an account is not found."""

    def __init__(self, account_id: int | str):
        super().__init__(
            message=f"Account not found: {account_id}",
            details={"account_id": str(account_id)},
        )


class AccountBlockedException(AppException):
    """Raised when an account is blocked."""

    def __init__(self, account_id: int):
        super().__init__(
            message=f"Account is blocked: {account_id}",
            details={"account_id": account_id},
        )


class ProxyNotAvailableException(AppException):
    """Raised when no proxy is available for the requested service type."""

    def __init__(self, service_type: str):
        super().__init__(
            message=f"No proxy available for service type: {service_type}",
            details={"service_type": service_type},
        )


class FetchFailedException(AppException):
    """Raised when fetching articles fails."""

    def __init__(
        self,
        account_id: int,
        reason: str,
        category: str = "temporary_failure",
        retryable: bool = True,
    ):
        super().__init__(
            message=f"Failed to fetch articles for account {account_id}: {reason}",
            details={
                "account_id": account_id,
                "reason": reason,
                "category": category,
                "retryable": retryable,
            },
        )


class AIAnalysisException(AppException):
    """Raised when AI analysis fails."""

    def __init__(self, article_id: int, reason: str):
        super().__init__(
            message=f"Failed to analyze article {article_id}: {reason}",
            details={"article_id": article_id, "reason": reason},
        )


class QRCodeExpiredException(AppException):
    """Raised when a QR code has expired."""

    def __init__(self, ticket: str):
        super().__init__(
            message=f"QR code has expired: {ticket}",
            details={"ticket": ticket},
        )


class QRCodeNotFoundException(AppException):
    """Raised when a QR code ticket is not found."""

    def __init__(self, ticket: str):
        super().__init__(
            message=f"QR code not found: {ticket}",
            details={"ticket": ticket},
        )


class QRProviderNotConfiguredException(AppException):
    """Raised when a QR login provider is not configured."""

    def __init__(self, provider: str):
        super().__init__(
            message=f"QR login provider is not configured: {provider}",
            details={"provider": provider},
        )


class QRProviderException(AppException):
    """Raised when a QR login provider request fails."""

    def __init__(self, provider: str, reason: str):
        super().__init__(
            message=f"QR login provider '{provider}' failed: {reason}",
            details={"provider": provider, "reason": reason},
        )


class ValidationException(AppException):
    """Raised when validation fails."""

    def __init__(self, message: str, field: str | None = None):
        details = {"field": field} if field else {}
        super().__init__(message=message, details=details)


class UnauthorizedException(AppException):
    """Raised when user is not authorized."""

    def __init__(self, message: str = "Unauthorized"):
        super().__init__(message=message)


class ForbiddenException(AppException):
    """Raised when user does not have permission."""

    def __init__(self, message: str = "Forbidden"):
        super().__init__(message=message)
