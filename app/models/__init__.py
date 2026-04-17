"""Database models."""

from app.models.base import Base, TimestampMixin
from app.models.user import User, UserRole
from app.models.account import Account, AccountType, AccountStatus
from app.models.article import Article
from app.models.collector_account import (
    CollectorAccount,
    CollectorAccountStatus,
    CollectorAccountType,
    CollectorHealthStatus,
    RiskStatus,
)
from app.models.fetch_job import FetchJob, FetchJobStatus, FetchJobType
from app.models.proxy import Proxy, ServiceType
from app.models.monitored_account import MonitoredAccount, MonitoredAccountStatus
from app.models.system_config import AIAnalysisConfig, FetchPolicy, NotificationEmailConfig
from app.models.log import OperationLog
from app.models.notification import Notification

__all__ = [
    "Base",
    "TimestampMixin",
    "User",
    "UserRole",
    "Account",
    "AccountType",
    "AccountStatus",
    "Article",
    "CollectorAccount",
    "CollectorAccountStatus",
    "CollectorAccountType",
    "CollectorHealthStatus",
    "RiskStatus",
    "FetchJob",
    "FetchJobStatus",
    "FetchJobType",
    "Proxy",
    "ServiceType",
    "MonitoredAccount",
    "MonitoredAccountStatus",
    "AIAnalysisConfig",
    "FetchPolicy",
    "NotificationEmailConfig",
    "OperationLog",
    "Notification",
]
