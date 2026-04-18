"""Test configuration and fixtures."""

import asyncio
from collections.abc import AsyncGenerator, Generator
from datetime import datetime, timedelta, timezone
from typing import Any

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.config import Settings
from app.core.dependencies import get_db
from app.models.base import Base
from app.models.article import Article
from app.models.collector_account import (
    CollectorAccount,
    CollectorAccountStatus,
    CollectorAccountType,
    CollectorHealthStatus,
    RiskStatus,
)
from app.models.monitored_account import MonitoredAccount, MonitoredAccountStatus
from app.models.user import User, UserRole
from app.models.proxy import Proxy, ServiceType
from app.services.rate_limit_service import rate_limit_service


# Test database URL (SQLite in-memory for tests)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def test_db() -> AsyncGenerator[AsyncSession, None]:
    """Create test database session."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture(autouse=True)
async def override_app_db(test_db: AsyncSession) -> AsyncGenerator[None, None]:
    """Ensure API tests use the in-memory test database."""

    async def _get_test_db():
        yield test_db

    app.dependency_overrides[get_db] = _get_test_db
    yield
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture(autouse=True)
def reset_rate_limit_service(monkeypatch) -> Generator[None, None, None]:
    """Keep the process-local limiter and optional Redis state isolated per test."""

    async def _no_redis():
        return None

    rate_limit_service.reset()
    monkeypatch.setattr(rate_limit_service, "_redis_ready", _no_redis)
    yield
    rate_limit_service.reset()


@pytest_asyncio.fixture
async def mock_user(test_db: AsyncSession) -> User:
    """Create a test user."""
    user = User(
        email="test@example.com",
        hashed_password="$2b$12$test_hash",
        role=UserRole.ADMIN,
        is_active=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest_asyncio.fixture
async def other_user(test_db: AsyncSession) -> User:
    """Create a second test user."""
    user = User(
        email="other@example.com",
        hashed_password="$2b$12$other_hash",
        role=UserRole.VIEWER,
        is_active=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest_asyncio.fixture
async def mock_account(test_db: AsyncSession, mock_user: User) -> MonitoredAccount:
    """Create a test monitored account."""
    account = MonitoredAccount(
        owner_user_id=mock_user.id,
        biz="test_biz_123",
        fakeid="test_fakeid",
        name="Test Account",
        source_url="https://mp.weixin.qq.com/s?__biz=test_biz_123",
        current_tier=3,
        composite_score=50.0,
        primary_fetch_mode=CollectorAccountType.MP_ADMIN,
        fallback_fetch_mode=CollectorAccountType.WEREAD,
        status=MonitoredAccountStatus.MONITORING,
        update_history={},
        ai_relevance_history={},
        strategy_config={},
    )
    test_db.add(account)
    await test_db.commit()
    await test_db.refresh(account)
    return account


@pytest_asyncio.fixture
async def mock_account_with_history(test_db: AsyncSession, mock_user: User) -> MonitoredAccount:
    """Create a test monitored account with update history."""
    now = datetime.now(timezone.utc)

    # Create 90 days of history
    update_history = {}
    ai_relevance_history = {}

    for i in range(90):
        day = now - timedelta(days=i)
        timestamp = day.isoformat()
        update_history[timestamp] = i % 5 + 1  # 1-5 articles per day
        ai_relevance_history[timestamp] = {
            "ratio": 0.5 + (i % 3) * 0.15,  # Varying relevance
            "reason": f"Analysis day {i}",
        }

    account = MonitoredAccount(
        owner_user_id=mock_user.id,
        biz="test_biz_history",
        fakeid="test_fakeid_history",
        name="Test Account with History",
        source_url="https://mp.weixin.qq.com/s?__biz=test_biz_history",
        current_tier=2,
        composite_score=65.0,
        last_polled_at=now - timedelta(hours=12),
        last_published_at=now - timedelta(hours=6),
        primary_fetch_mode=CollectorAccountType.WEREAD,
        fallback_fetch_mode=CollectorAccountType.MP_ADMIN,
        status=MonitoredAccountStatus.MONITORING,
        update_history=update_history,
        ai_relevance_history=ai_relevance_history,
        strategy_config={},
    )
    test_db.add(account)
    await test_db.commit()
    await test_db.refresh(account)
    return account


@pytest_asyncio.fixture
async def mock_proxy(test_db: AsyncSession) -> Proxy:
    """Create a test proxy."""
    proxy = Proxy(
        host="127.0.0.1",
        port=8080,
        service_type=ServiceType.FETCH,
        success_rate=95.0,
        is_active=True,
    )
    test_db.add(proxy)
    await test_db.commit()
    await test_db.refresh(proxy)
    return proxy


@pytest_asyncio.fixture
async def mock_article(test_db: AsyncSession, mock_account: MonitoredAccount) -> Article:
    """Create a test article."""
    article = Article(
        monitored_account_id=mock_account.id,
        title="Test Article",
        content="This is test content about sports and games.",
        url="https://mp.weixin.qq.com/s/test_article",
        published_at=datetime.now(timezone.utc),
        ai_relevance_ratio=0.75,
        ai_judgment={"ratio": 0.75, "reason": "Sports content"},
        images=[],
    )
    test_db.add(article)
    await test_db.commit()
    await test_db.refresh(article)
    return article


@pytest_asyncio.fixture
async def mock_monitored_account(test_db: AsyncSession, mock_user: User) -> MonitoredAccount:
    """Create a monitored account owned by the primary test user."""
    monitored = MonitoredAccount(
        owner_user_id=mock_user.id,
        biz="monitored_biz_123",
        fakeid="fakeid_123",
        name="Monitored Account",
        source_url="https://mp.weixin.qq.com/s?__biz=monitored_biz_123",
        current_tier=3,
        composite_score=50.0,
        primary_fetch_mode=CollectorAccountType.MP_ADMIN,
        fallback_fetch_mode=CollectorAccountType.WEREAD,
        status=MonitoredAccountStatus.MONITORING,
        update_history={},
        ai_relevance_history={},
        strategy_config={},
    )
    test_db.add(monitored)
    await test_db.commit()
    await test_db.refresh(monitored)
    return monitored


@pytest_asyncio.fixture
async def other_monitored_account(test_db: AsyncSession, other_user: User) -> MonitoredAccount:
    """Create a monitored account owned by another user."""
    monitored = MonitoredAccount(
        owner_user_id=other_user.id,
        biz="other_monitored_biz_123",
        fakeid="other_fakeid_123",
        name="Other Monitored Account",
        source_url="https://mp.weixin.qq.com/s?__biz=other_monitored_biz_123",
        current_tier=3,
        composite_score=50.0,
        primary_fetch_mode=CollectorAccountType.MP_ADMIN,
        fallback_fetch_mode=CollectorAccountType.WEREAD,
        status=MonitoredAccountStatus.MONITORING,
        update_history={},
        ai_relevance_history={},
        strategy_config={},
    )
    test_db.add(monitored)
    await test_db.commit()
    await test_db.refresh(monitored)
    return monitored


@pytest_asyncio.fixture
async def mock_monitored_article(test_db: AsyncSession, mock_monitored_account: MonitoredAccount) -> Article:
    """Create an article bound to a monitored account."""
    article = Article(
        monitored_account_id=mock_monitored_account.id,
        title="Monitored Test Article",
        content="Monitored content",
        url="https://mp.weixin.qq.com/s/monitored_test_article",
        published_at=datetime.now(timezone.utc),
        ai_relevance_ratio=0.6,
        ai_judgment={"ratio": 0.6, "reason": "monitor"},
        images=[],
    )
    test_db.add(article)
    await test_db.commit()
    await test_db.refresh(article)
    return article


@pytest_asyncio.fixture
async def other_monitored_article(test_db: AsyncSession, other_monitored_account: MonitoredAccount) -> Article:
    """Create an article owned by another user's monitored account."""
    article = Article(
        monitored_account_id=other_monitored_account.id,
        title="Other Monitored Test Article",
        content="Other monitored content",
        url="https://mp.weixin.qq.com/s/other_monitored_test_article",
        published_at=datetime.now(timezone.utc),
        ai_relevance_ratio=0.4,
        ai_judgment={"ratio": 0.4, "reason": "other-monitor"},
        images=[],
    )
    test_db.add(article)
    await test_db.commit()
    await test_db.refresh(article)
    return article


@pytest_asyncio.fixture
async def mock_collector_account(test_db: AsyncSession, mock_user: User) -> CollectorAccount:
    """Create a collector account owned by the primary user."""
    account = CollectorAccount(
        owner_user_id=mock_user.id,
        account_type=CollectorAccountType.MP_ADMIN,
        display_name="Primary Collector",
        external_id="primary_collector",
        credentials={"token": "primary-token", "cookies": {}},
        status=CollectorAccountStatus.ACTIVE,
        health_status=CollectorHealthStatus.NORMAL,
        risk_status=RiskStatus.NORMAL,
        metadata_json={},
    )
    test_db.add(account)
    await test_db.commit()
    await test_db.refresh(account)
    return account


@pytest_asyncio.fixture
async def other_collector_account(test_db: AsyncSession, other_user: User) -> CollectorAccount:
    """Create a collector account owned by another user."""
    account = CollectorAccount(
        owner_user_id=other_user.id,
        account_type=CollectorAccountType.MP_ADMIN,
        display_name="Other Collector",
        external_id="other_collector",
        credentials={"token": "other-token", "cookies": {}},
        status=CollectorAccountStatus.ACTIVE,
        health_status=CollectorHealthStatus.NORMAL,
        risk_status=RiskStatus.NORMAL,
        metadata_json={},
    )
    test_db.add(account)
    await test_db.commit()
    await test_db.refresh(account)
    return account


@pytest.fixture
def mock_settings() -> Settings:
    """Create mock settings for testing."""
    return Settings(
        database_url=TEST_DATABASE_URL,
        redis_url="redis://localhost:6379/1",
        jwt_secret_key="test-secret-key",
        jwt_algorithm="HS256",
        jwt_access_token_expire_minutes=30,
        weight_frequency_ratio=0.35,
        weight_recency_ratio=0.25,
        weight_relevance_ratio=0.25,
        weight_stability_ratio=0.15,
        tier_threshold_tier1=80.0,
        tier_threshold_tier2=65.0,
        tier_threshold_tier3=50.0,
        tier_threshold_tier4=35.0,
        check_interval_tier1=24,
        check_interval_tier2=48,
        check_interval_tier3=72,
        check_interval_tier4=144,
        check_interval_tier5=336,
        high_relevance_threshold=0.8,
        ai_consecutive_low_threshold=3,
        qr_code_expire_seconds=180,
        debug=True,
    )


@pytest.fixture
def sample_articles_data() -> list[dict[str, Any]]:
    """Sample articles data for testing."""
    return [
        {
            "title": "NBA Finals Preview",
            "url": "https://mp.weixin.qq.com/s/nba_preview",
            "published_at": datetime.now(timezone.utc).isoformat(),
            "raw_content": "<html><body><h1>NBA Finals Preview</h1><p>Exciting basketball action...</p></body></html>",
        },
        {
            "title": "World Cup Update",
            "url": "https://mp.weixin.qq.com/s/world_cup",
            "published_at": (datetime.now(timezone.utc) - timedelta(hours=5)).isoformat(),
            "raw_content": "<html><body><h1>World Cup Update</h1><p>Soccer tournament news...</p></body></html>",
        },
    ]


@pytest.fixture
def sample_ai_result() -> dict[str, Any]:
    """Sample AI analysis result."""
    return {
        "ratio": 0.85,
        "reason": "High sports relevance based on keyword analysis",
        "keywords": ["basketball", "tournament", "championship"],
        "json_data": {"category": "sports", "sentiment": "positive"},
    }
