"""Tests for database models."""

from datetime import datetime, timezone
import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.article import Article
from app.models.collector_account import CollectorAccountType
from app.models.monitored_account import MonitoredAccount, MonitoredAccountStatus
from app.models.user import User, UserRole
from app.models.proxy import Proxy, ServiceType
from app.models.notification import Notification


class TestMonitoredAccountModel:
    """Test cases for monitored account model."""

    @pytest.mark.asyncio
    async def test_create_account(self, test_db: AsyncSession):
        """Test creating a monitored account."""
        account = MonitoredAccount(
            owner_user_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
            biz="model_test_biz",
            fakeid="model_test_fakeid",
            name="Model Test Account",
            source_url="https://mp.weixin.qq.com/s?__biz=model_test_biz",
            current_tier=3,
            composite_score=50.0,
            primary_fetch_mode=CollectorAccountType.MP_ADMIN,
            fallback_fetch_mode=CollectorAccountType.WEREAD,
            status=MonitoredAccountStatus.MONITORING,
            strategy_config={},
        )

        test_db.add(account)
        await test_db.commit()
        await test_db.refresh(account)

        assert account.id is not None
        assert account.biz == "model_test_biz"
        assert account.created_at is not None

    @pytest.mark.asyncio
    async def test_account_update_history(self, test_db: AsyncSession, mock_account: MonitoredAccount):
        """Test updating account history."""
        mock_account.update_history = {
            datetime.now(timezone.utc).isoformat(): 5
        }
        mock_account.ai_relevance_history = {
            datetime.now(timezone.utc).isoformat(): {"ratio": 0.8, "reason": "Good"}
        }

        await test_db.commit()

        assert len(mock_account.update_history) == 1
        assert len(mock_account.ai_relevance_history) == 1

    @pytest.mark.asyncio
    async def test_account_manual_override(self, test_db: AsyncSession, mock_account: MonitoredAccount):
        """Test account manual override."""
        mock_account.manual_override = {
            "target_tier": 1,
            "reason": "VIP",
            "expire_at": datetime.now(timezone.utc).isoformat(),
        }

        await test_db.commit()
        await test_db.refresh(mock_account)

        assert mock_account.manual_override is not None
        assert mock_account.manual_override["target_tier"] == 1


class TestArticleModel:
    """Test cases for Article model."""

    @pytest.mark.asyncio
    async def test_create_article(self, test_db: AsyncSession, mock_account: MonitoredAccount):
        """Test creating an article."""
        article = Article(
            monitored_account_id=mock_account.id,
            title="Model Test Article",
            content="Test content for model article",
            url="https://example.com/model_test",
            published_at=datetime.now(timezone.utc),
        )

        test_db.add(article)
        await test_db.commit()
        await test_db.refresh(article)

        assert article.id is not None
        assert article.title == "Model Test Article"
        assert article.ai_judgment is None

    @pytest.mark.asyncio
    async def test_article_with_ai_judgment(self, test_db: AsyncSession, mock_account: MonitoredAccount):
        """Test article with AI judgment."""
        article = Article(
            monitored_account_id=mock_account.id,
            title="Article with AI",
            content="Test content",
            url="https://example.com/ai_test",
            ai_relevance_ratio=0.85,
            ai_judgment={
                "ratio": 0.85,
                "reason": "High sports content",
                "keywords": ["basketball", "championship"],
            },
        )

        test_db.add(article)
        await test_db.commit()
        await test_db.refresh(article)

        assert article.ai_relevance_ratio == 0.85
        assert article.ai_judgment["ratio"] == 0.85


class TestProxyModel:
    """Test cases for Proxy model."""

    @pytest.mark.asyncio
    async def test_create_proxy(self, test_db: AsyncSession):
        """Test creating a proxy."""
        proxy = Proxy(
            host="10.0.0.1",
            port=8080,
            service_type=ServiceType.PARSE,
            success_rate=90.0,
            is_active=True,
        )

        test_db.add(proxy)
        await test_db.commit()
        await test_db.refresh(proxy)

        assert proxy.id is not None
        assert proxy.proxy_url == "http://10.0.0.1:8080"

    @pytest.mark.asyncio
    async def test_proxy_with_auth(self, test_db: AsyncSession):
        """Test proxy with authentication."""
        proxy = Proxy(
            host="10.0.0.2",
            port=8080,
            username="user",
            password="pass",
            service_type=ServiceType.AI,
            success_rate=85.0,
            is_active=True,
        )

        test_db.add(proxy)
        await test_db.commit()
        await test_db.refresh(proxy)

        assert proxy.proxy_url == "http://user:pass@10.0.0.2:8080"

    @pytest.mark.asyncio
    async def test_proxy_url_preserves_explicit_scheme(self, test_db: AsyncSession):
        """Test proxy URLs can be configured with non-HTTP schemes."""
        proxy = Proxy(
            host="socks5://10.0.0.3",
            port=1080,
            service_type=ServiceType.MP_DETAIL,
            success_rate=85.0,
            is_active=True,
        )

        test_db.add(proxy)
        await test_db.commit()
        await test_db.refresh(proxy)

        assert proxy.proxy_url == "socks5://10.0.0.3:1080"


class TestUserModel:
    """Test cases for User model."""

    @pytest.mark.asyncio
    async def test_create_user(self, test_db: AsyncSession):
        """Test creating a user."""
        user = User(
            email="model_test@example.com",
            hashed_password="hashed_password_here",
            role=UserRole.OPERATOR,
            is_active=True,
        )

        test_db.add(user)
        await test_db.commit()
        await test_db.refresh(user)

        assert user.id is not None
        assert user.email == "model_test@example.com"
        assert user.role == UserRole.OPERATOR


class TestNotificationModel:
    """Test cases for Notification model."""

    @pytest.mark.asyncio
    async def test_create_notification(
        self, test_db: AsyncSession, mock_account: MonitoredAccount, mock_user: User
    ):
        """Test creating a notification."""
        notification = Notification(
            owner_user_id=mock_user.id,
            monitored_account_id=mock_account.id,
            notification_type="high_relevance",
            title="High Relevance Alert",
            content="Article has 90% relevance",
            is_read=False,
        )

        test_db.add(notification)
        await test_db.commit()
        await test_db.refresh(notification)

        assert notification.id is not None
        assert notification.is_read is False

    @pytest.mark.asyncio
    async def test_mark_notification_read(
        self, test_db: AsyncSession, mock_account: MonitoredAccount, mock_user: User
    ):
        """Test marking notification as read."""
        notification = Notification(
            owner_user_id=mock_user.id,
            monitored_account_id=mock_account.id,
            notification_type="alert",
            title="Test Alert",
            content="Test content",
            is_read=False,
        )

        test_db.add(notification)
        await test_db.commit()
        await test_db.refresh(notification)

        notification.is_read = True
        await test_db.commit()
        await test_db.refresh(notification)

        assert notification.is_read is True
