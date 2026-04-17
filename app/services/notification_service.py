"""Notification service for alerts and notifications."""

import uuid
import asyncio
from collections.abc import Sequence
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
import smtplib
from typing import Any

from sqlalchemy import Select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.collector_account import CollectorAccount, CollectorHealthStatus
from app.models.monitored_account import MonitoredAccount
from app.models.notification import Notification
from app.services.system_config_service import SystemConfigService
from app.repositories.base import BaseRepository


settings = get_settings()


class NotificationService:
    """Service for notification management."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.notification_repo = BaseRepository(Notification, db)

    async def _find_recent_duplicate(
        self,
        owner_user_id: uuid.UUID,
        notification_type: str,
        collector_account_id: int | None = None,
        monitored_account_id: int | None = None,
        article_id: int | None = None,
        within_minutes: int = 30,
    ) -> Notification | None:
        query = (
            Select(Notification)
            .where(
                Notification.owner_user_id == owner_user_id,
                Notification.notification_type == notification_type,
                Notification.created_at >= datetime.now(timezone.utc) - timedelta(minutes=within_minutes),
            )
            .order_by(Notification.created_at.desc())
        )
        if collector_account_id is not None:
            query = query.where(Notification.collector_account_id == collector_account_id)
        if monitored_account_id is not None:
            query = query.where(Notification.monitored_account_id == monitored_account_id)
        if article_id is not None:
            query = query.where(Notification.article_id == article_id)
        result = await self.db.execute(query.limit(1))
        return result.scalar_one_or_none()

    async def _deliver_notification(self, notification: Notification) -> None:
        config = await SystemConfigService(self.db).get_or_create_notification_email_config()
        if not config.enabled or not config.smtp_host or not config.to_emails or not config.from_email:
            return
        message = EmailMessage()
        message["Subject"] = f"[DynamicWePubMonitor] {notification.title}"
        message["From"] = config.from_email
        message["To"] = ", ".join(config.to_emails)
        message.set_content(
            "\n".join(
                [
                    f"通知类型: {notification.notification_type}",
                    f"标题: {notification.title}",
                    f"内容: {notification.content}",
                    f"抓取账号 ID: {notification.collector_account_id or '-'}",
                    f"监测对象 ID: {notification.monitored_account_id or '-'}",
                    f"文章 ID: {notification.article_id or '-'}",
                    f"时间: {notification.created_at.isoformat() if notification.created_at else '-'}",
                ]
            )
        )

        def _send() -> None:
            with smtplib.SMTP(config.smtp_host, config.smtp_port, timeout=10) as server:
                if config.use_tls:
                    server.starttls()
                if config.smtp_username:
                    server.login(config.smtp_username, config.smtp_password)
                server.send_message(message)

        try:
            await asyncio.to_thread(_send)
        except Exception:
            return

    async def create_notification(
        self,
        owner_user_id: uuid.UUID,
        notification_type: str,
        title: str,
        content: str,
        account_id: int | None = None,
        collector_account_id: int | None = None,
        monitored_account_id: int | None = None,
        article_id: int | None = None,
        payload: dict[str, Any] | None = None,
    ) -> Notification:
        """Create a new notification."""
        duplicate = await self._find_recent_duplicate(
            owner_user_id=owner_user_id,
            notification_type=notification_type,
            collector_account_id=collector_account_id,
            monitored_account_id=monitored_account_id,
            article_id=article_id,
        )
        if duplicate is not None:
            return duplicate

        notification = await self.notification_repo.create(
            owner_user_id=owner_user_id,
            notification_type=notification_type,
            title=title,
            content=content,
            account_id=account_id,
            collector_account_id=collector_account_id,
            monitored_account_id=monitored_account_id,
            article_id=article_id,
            is_read=False,
            payload=payload or {},
        )
        await self._deliver_notification(notification)
        return notification

    def _owner_filter(self, owner_user_id: uuid.UUID | None) -> Select:
        query = Select(Notification)
        if owner_user_id is not None:
            query = query.where(Notification.owner_user_id == owner_user_id)
        return query

    async def get_notification(
        self,
        notification_id: int,
        owner_user_id: uuid.UUID | None = None,
    ) -> Notification | None:
        """Get notification by ID."""
        query = self._owner_filter(owner_user_id).where(Notification.id == notification_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_notifications(
        self,
        owner_user_id: uuid.UUID | None,
        skip: int = 0,
        limit: int = 50,
        unread_only: bool = False,
    ) -> list[Notification]:
        """Get notifications with optional unread filter."""
        query = self._owner_filter(owner_user_id).order_by(Notification.created_at.desc()).offset(skip).limit(limit)
        if unread_only:
            query = query.where(Notification.is_read.is_(False))
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_total_count(self, owner_user_id: uuid.UUID | None, unread_only: bool = False) -> int:
        query = Select(func.count()).select_from(Notification)
        if owner_user_id is not None:
            query = query.where(Notification.owner_user_id == owner_user_id)
        if unread_only:
            query = query.where(Notification.is_read.is_(False))
        result = await self.db.execute(query)
        return int(result.scalar_one())

    async def mark_as_read(
        self,
        notification_id: int,
        owner_user_id: uuid.UUID | None = None,
    ) -> Notification | None:
        """Mark a notification as read."""
        notification = await self.get_notification(notification_id, owner_user_id)
        if notification is None:
            return None
        return await self.notification_repo.update(notification, is_read=True)

    async def mark_all_as_read(self, owner_user_id: uuid.UUID | None = None) -> int:
        """Mark all notifications as read."""
        notifications = await self.get_notifications(owner_user_id=owner_user_id, limit=1000, unread_only=True)
        count = 0
        for notification in notifications:
            await self.notification_repo.update(notification, is_read=True)
            count += 1
        return count

    async def delete_notification(self, notification_id: int, owner_user_id: uuid.UUID | None = None) -> bool:
        """Delete a notification."""
        notification = await self.get_notification(notification_id, owner_user_id)
        if notification:
            await self.notification_repo.delete(notification)
            return True
        return False

    async def check_and_notify_high_relevance(
        self,
        owner_user_id: uuid.UUID,
        monitored_account: MonitoredAccount,
        collector_account: CollectorAccount,
        article: Any,
        relevance_ratio: float,
    ) -> Notification | None:
        """Check if article has high relevance and create notification."""
        if relevance_ratio >= settings.high_relevance_threshold:
            return await self.create_notification(
                owner_user_id=owner_user_id,
                notification_type="high_relevance",
                title=f"高相关文章发现 ({relevance_ratio:.0%})",
                content=f"监测对象 {monitored_account.name} 的文章《{article.title}》相关度达到 {relevance_ratio:.0%}",
                collector_account_id=collector_account.id,
                monitored_account_id=monitored_account.id,
                article_id=article.id,
                payload={
                    "relevance_ratio": relevance_ratio,
                    "article_url": article.url,
                    "collector_account_id": collector_account.id,
                },
            )
        return None

    async def check_and_notify_ai_consecutive_low(
        self,
        owner_user_id: uuid.UUID,
        monitored_account: MonitoredAccount,
        consecutive_count: int,
    ) -> Notification | None:
        """Notify when AI analysis shows consecutive low relevance."""
        if consecutive_count >= settings.ai_consecutive_low_threshold:
            return await self.create_notification(
                owner_user_id=owner_user_id,
                notification_type="ai_consecutive_low",
                title="AI 连续低相关警告",
                content=f"监测对象 {monitored_account.name} 已连续 {consecutive_count} 次 AI 分析相关度低于阈值",
                monitored_account_id=monitored_account.id,
                payload={"consecutive_count": consecutive_count},
            )
        return None

    async def check_and_notify_fetch_error(
        self,
        owner_user_id: uuid.UUID,
        monitored_account: MonitoredAccount,
        collector_account: CollectorAccount | None,
        error_message: str,
        category: str = "temporary_failure",
    ) -> Notification:
        """Notify when fetch fails."""
        return await self.create_notification(
            owner_user_id=owner_user_id,
            notification_type="fetch_error" if category == "temporary_failure" else f"fetch_error_{category}",
            title="抓取失败",
            content=f"监测对象 {monitored_account.name} 抓取失败: {error_message}",
            collector_account_id=collector_account.id if collector_account else None,
            monitored_account_id=monitored_account.id,
            payload={"category": category},
        )

    async def check_and_notify_proxy_exhausted(
        self,
        owner_user_id: uuid.UUID,
        service_type: str,
    ) -> Notification:
        """Notify when proxy pool is exhausted for a service type."""
        return await self.create_notification(
            owner_user_id=owner_user_id,
            notification_type="proxy_exhausted",
            title="代理池耗尽",
            content=f"服务类型 {service_type} 的代理池已耗尽",
        )

    async def notify_collector_health_issue(
        self,
        account: CollectorAccount,
        health_status: CollectorHealthStatus,
        reason: str,
    ) -> Notification | None:
        if health_status == CollectorHealthStatus.NORMAL:
            return None
        type_mapping = {
            CollectorHealthStatus.RESTRICTED: "collector_restricted",
            CollectorHealthStatus.EXPIRED: "collector_expired",
            CollectorHealthStatus.INVALID: "collector_invalid",
        }
        title_mapping = {
            CollectorHealthStatus.RESTRICTED: "抓取账号受限",
            CollectorHealthStatus.EXPIRED: "抓取账号已失效",
            CollectorHealthStatus.INVALID: "抓取账号不可用",
        }
        return await self.create_notification(
            owner_user_id=account.owner_user_id,
            notification_type=type_mapping[health_status],
            title=title_mapping[health_status],
            content=f"{account.display_name} 健康检查异常: {reason}",
            collector_account_id=account.id,
            payload={"health_status": health_status.value},
        )

    async def notify_collector_expiring_soon(
        self,
        account: CollectorAccount,
        expires_at: datetime,
    ) -> Notification:
        remaining = expires_at - datetime.now(timezone.utc)
        hours_left = max(int(remaining.total_seconds() // 3600), 0)
        return await self.create_notification(
            owner_user_id=account.owner_user_id,
            notification_type="collector_expiring_soon",
            title="抓取账号即将过期",
            content=f"{account.display_name} 将在约 {hours_left} 小时后过期，请尽快重新登录。",
            collector_account_id=account.id,
            payload={"expires_at": expires_at.isoformat()},
        )

    async def get_unread_count(self, owner_user_id: uuid.UUID | None = None) -> int:
        """Get count of unread notifications."""
        return await self.get_total_count(owner_user_id=owner_user_id, unread_only=True)
