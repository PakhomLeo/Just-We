"""Database models."""

from app.models.base import Base, TimestampMixin
from app.models.user import User, UserRole
from app.models.article import Article
from app.models.article_export import ArticleExportRecord, ArticleExportStatus
from app.models.collector_account import (
    CollectorAccount,
    CollectorAccountStatus,
    CollectorAccountType,
    CollectorHealthStatus,
    RiskStatus,
)
from app.models.fetch_job import FetchJob, FetchJobStatus, FetchJobType
from app.models.proxy import (
    Proxy,
    ProxyKind,
    ProxyRotationMode,
    ProxyServiceBinding,
    ProxyServiceKey,
    ServiceType,
)
from app.models.monitored_account import MonitoredAccount, MonitoredAccountStatus
from app.models.system_config import AIAnalysisConfig, FetchPolicy, NotificationEmailConfig
from app.models.weight_config import WeightConfig
from app.models.log import OperationLog
from app.models.notification import Notification

__all__ = [
    "Base",
    "TimestampMixin",
    "User",
    "UserRole",
    "Article",
    "ArticleExportRecord",
    "ArticleExportStatus",
    "CollectorAccount",
    "CollectorAccountStatus",
    "CollectorAccountType",
    "CollectorHealthStatus",
    "RiskStatus",
    "FetchJob",
    "FetchJobStatus",
    "FetchJobType",
    "Proxy",
    "ProxyKind",
    "ProxyRotationMode",
    "ProxyServiceBinding",
    "ProxyServiceKey",
    "ServiceType",
    "MonitoredAccount",
    "MonitoredAccountStatus",
    "AIAnalysisConfig",
    "FetchPolicy",
    "NotificationEmailConfig",
    "WeightConfig",
    "OperationLog",
    "Notification",
]
