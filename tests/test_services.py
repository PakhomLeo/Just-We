"""Tests for service layer."""

from datetime import datetime, timedelta, timezone
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import Select
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.auth_service import AuthService
from app.services.bootstrap_service import BootstrapService
from app.services.proxy_service import ProxyService
from app.services.article_service import ArticleService
from app.services.parser_service import ParserService, ParsedArticle
from app.services.ai_service import AIService
from app.services.fetch_pipeline_service import FetchPipelineService
from app.services.fetcher_service import DetailDocumentResponse, FetcherService
from app.services.monitoring_source_service import MonitoringSourceService
from app.services.notification_service import NotificationService
from app.services.qr_login_service import QRLoginService
from app.services.rate_limit_service import rate_limit_service
from app.services.scheduler_service import SchedulerService, stop_scheduler
from app.models.article import Article
from app.models.collector_account import (
    CollectorAccount,
    CollectorAccountStatus,
    CollectorAccountType,
    CollectorHealthStatus,
    RiskStatus,
)
from app.models.monitored_account import MonitoredAccount, MonitoredAccountStatus
from app.models.notification import Notification
from app.models.proxy import Proxy, ProxyKind, ProxyRotationMode, ProxyServiceKey, ServiceType
from app.models.system_config import NotificationEmailConfig
from app.models.user import User
from app.core.exceptions import FetchFailedException
from app.services.health_service import HealthCheckService


class TestAuthService:
    """Test cases for AuthService."""

    def test_hash_password(self, test_db: AsyncSession):
        """Test password hashing."""
        auth_service = AuthService(test_db)
        password = "test_password123"
        hashed = auth_service.hash_password(password)

        assert hashed != password
        assert auth_service.verify_password(password, hashed) is True
        assert auth_service.verify_password("wrong_password", hashed) is False

    def test_create_access_token(self, test_db: AsyncSession):
        """Test JWT token creation."""
        auth_service = AuthService(test_db)
        user_id = "test-user-id-123"

        token = auth_service.create_access_token(user_id)
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_decode_token(self, test_db: AsyncSession):
        """Test JWT token decoding."""
        auth_service = AuthService(test_db)
        user_id = "test-user-id-123"

        token = auth_service.create_access_token(user_id)
        payload = auth_service.decode_token(token)

        assert payload is not None
        assert payload["sub"] == user_id

    def test_decode_invalid_token(self, test_db: AsyncSession):
        """Test decoding invalid token returns None."""
        auth_service = AuthService(test_db)
        payload = auth_service.decode_token("invalid.token.here")
        assert payload is None

    @pytest.mark.asyncio
    async def test_authenticate_default_admin_by_alias(self, test_db: AsyncSession):
        """Default admin should be reachable by the admin alias."""
        await BootstrapService(test_db).ensure_default_admin()
        auth_service = AuthService(test_db)

        user = await auth_service.authenticate_user("admin", "admin123")

        assert user is not None
        assert user.email == "admin@admin.com"


class TestBootstrapService:
    """Startup bootstrap behavior."""

    @pytest.mark.asyncio
    async def test_ensure_default_admin_is_idempotent(self, test_db: AsyncSession):
        bootstrap = BootstrapService(test_db)

        first = await bootstrap.ensure_default_admin()
        second = await bootstrap.ensure_default_admin()

        assert first is not None
        assert second is not None
        assert first.id == second.id
        assert second.email == "admin@admin.com"
        assert second.role.value == "admin"
        assert second.is_superuser is True


class TestProxyService:
    """Test cases for ProxyService."""

    @pytest.mark.asyncio
    async def test_create_proxy(self, test_db: AsyncSession):
        """Test proxy creation."""
        service = ProxyService(test_db)

        proxy = await service.create_proxy(
            host="192.168.1.1",
            port=3128,
            service_type=ServiceType.FETCH,
        )

        assert proxy.id is not None
        assert proxy.host == "192.168.1.1"
        assert proxy.port == 3128
        assert proxy.is_active is True
        assert proxy.service_keys == []

    @pytest.mark.asyncio
    async def test_get_proxy_for_service(self, test_db: AsyncSession, mock_proxy: Proxy):
        """Service proxy lookup uses explicit bindings, not legacy service_type."""
        service = ProxyService(test_db)
        await service.replace_service_bindings(mock_proxy, [ProxyServiceKey.MP_DETAIL])
        proxy = await service.get_proxy_for_service(ServiceType.FETCH)

        assert proxy is not None
        assert proxy.id == mock_proxy.id

    @pytest.mark.asyncio
    async def test_get_proxy_for_service_not_found(self, test_db: AsyncSession):
        """Missing service proxy means direct connection rather than an error."""
        service = ProxyService(test_db)

        assert await service.get_proxy_for_service(ServiceType.AI) is None

    @pytest.mark.asyncio
    async def test_proxy_service_bindings_validate_compatibility(self, test_db: AsyncSession):
        """Proxy type should limit which business services can use it."""
        service = ProxyService(test_db)

        with pytest.raises(ValueError):
            await service.create_proxy(
                host="10.0.0.1",
                port=8080,
                service_type=ServiceType.AI,
                proxy_kind=ProxyKind.DATACENTER,
                rotation_mode=ProxyRotationMode.ROUND_ROBIN,
                service_keys=[ProxyServiceKey.MP_ADMIN_LOGIN],
            )

        proxy = await service.create_proxy(
            host="10.0.0.2",
            port=8080,
            service_type=ServiceType.MP_DETAIL,
            proxy_kind=ProxyKind.ISP_STATIC,
            rotation_mode=ProxyRotationMode.STICKY,
            service_keys=[ProxyServiceKey.MP_ADMIN_LOGIN, ProxyServiceKey.MP_LIST, ProxyServiceKey.MP_DETAIL],
        )

        assert set(proxy.service_keys) == {
            ProxyServiceKey.MP_ADMIN_LOGIN,
            ProxyServiceKey.MP_LIST,
            ProxyServiceKey.MP_DETAIL,
        }

    @pytest.mark.asyncio
    async def test_proxy_selection_round_robin_skips_cooling_and_low_score(self, test_db: AsyncSession):
        """Detail proxy selection should rotate among healthy compatible proxies."""
        service = ProxyService(test_db)
        first = await service.create_proxy(
            host="10.0.0.10",
            port=8080,
            service_type=ServiceType.MP_DETAIL,
            proxy_kind=ProxyKind.RESIDENTIAL_ROTATING,
            rotation_mode=ProxyRotationMode.ROUND_ROBIN,
            service_keys=[ProxyServiceKey.MP_DETAIL],
        )
        second = await service.create_proxy(
            host="10.0.0.11",
            port=8080,
            service_type=ServiceType.MP_DETAIL,
            proxy_kind=ProxyKind.RESIDENTIAL_ROTATING,
            rotation_mode=ProxyRotationMode.ROUND_ROBIN,
            service_keys=[ProxyServiceKey.MP_DETAIL],
        )
        low_score = await service.create_proxy(
            host="10.0.0.12",
            port=8080,
            service_type=ServiceType.MP_DETAIL,
            proxy_kind=ProxyKind.RESIDENTIAL_ROTATING,
            rotation_mode=ProxyRotationMode.ROUND_ROBIN,
            service_keys=[ProxyServiceKey.MP_DETAIL],
        )
        await service.update_proxy(low_score.id, success_rate=10)
        await service.mark_proxy_failure(second, "captcha", cooldown_seconds=120)

        selected_one = await service.select_proxy(ProxyServiceKey.MP_DETAIL)
        selected_two = await service.select_proxy(ProxyServiceKey.MP_DETAIL)

        assert selected_one.id == first.id
        assert selected_two.id == first.id

    @pytest.mark.asyncio
    async def test_update_proxy_success_rate(self, test_db: AsyncSession, mock_proxy: Proxy):
        """Test updating proxy success rate."""
        service = ProxyService(test_db)
        updated = await service.update_proxy(
            mock_proxy.id,
            success_rate=85.0,
        )

        assert updated.success_rate == 85.0

    @pytest.mark.asyncio
    async def test_deactivate_proxy(self, test_db: AsyncSession, mock_proxy: Proxy):
        """Test deactivating proxy."""
        service = ProxyService(test_db)
        deactivated = await service.deactivate_proxy(mock_proxy.id)

        assert deactivated.is_active is False


class TestArticleService:
    """Test cases for ArticleService."""

    @pytest.mark.asyncio
    async def test_save_article(self, test_db: AsyncSession, mock_account: MonitoredAccount):
        """Test saving article."""
        service = ArticleService(test_db)

        article = await service.save_article(
            monitored_account_id=mock_account.id,
            title="New Article",
            content="Article content here",
            url="https://example.com/article",
        )

        assert article.id is not None
        assert article.title == "New Article"

    @pytest.mark.asyncio
    async def test_get_articles_by_account(
        self, test_db: AsyncSession, mock_account: MonitoredAccount, mock_article: Article
    ):
        """Test getting articles by account."""
        service = ArticleService(test_db)
        articles = await service.get_articles_by_monitored_account(mock_account.id)

        assert len(articles) >= 1
        assert any(a.id == mock_article.id for a in articles)

    @pytest.mark.asyncio
    async def test_get_article_by_url(self, test_db: AsyncSession, mock_article: Article):
        """Test getting article by URL."""
        service = ArticleService(test_db)
        article = await service.get_article_by_url(mock_article.url)

        assert article is not None
        assert article.url == mock_article.url


class TestMonitoringSourceService:
    """Test ownership behavior for monitored accounts."""

    @pytest.mark.asyncio
    async def test_create_from_url_allows_same_biz_for_different_owners(
        self,
        test_db: AsyncSession,
        mock_user: User,
        other_user: User,
    ):
        service = MonitoringSourceService(test_db)
        source_url = "https://mp.weixin.qq.com/s?__biz=shared_biz_123&mid=1&idx=1&sn=test"

        first, created_first = await service.create_from_url(mock_user.id, source_url, name="First")
        second, created_second = await service.create_from_url(other_user.id, source_url, name="Second")

        assert created_first is True
        assert created_second is True
        assert first.id != second.id
        assert first.owner_user_id == mock_user.id
        assert second.owner_user_id == other_user.id


class TestSchedulerService:
    """Test scheduler loading behavior."""

    @pytest.mark.asyncio
    async def test_load_account_schedules_sets_next_run(
        self,
        test_db: AsyncSession,
        mock_monitored_account: MonitoredAccount,
    ):
        scheduler = SchedulerService(test_db)
        stop_scheduler()
        scheduler = SchedulerService(test_db)

        async def fake_fetch(account_id: int):
            return {"account_id": account_id}

        try:
            count = await scheduler.load_account_schedules([mock_monitored_account], fake_fetch)
            assert count == 1
            assert mock_monitored_account.next_scheduled_at is not None
            assert mock_monitored_account.next_scheduled_at > datetime.now(timezone.utc)
            assert scheduler.get_job(mock_monitored_account.id) is not None
        finally:
            stop_scheduler()


class FakeRedis:
    """In-memory Redis stand-in for QR login tests."""

    def __init__(self):
        self.data = {}

    async def setex(self, key, ttl, value):
        self.data[key] = value

    async def get(self, key):
        return self.data.get(key)

    async def delete(self, key):
        self.data.pop(key, None)


class TestQRLoginService:
    """Test provider-driven QR login flows."""

    @pytest.mark.asyncio
    async def test_get_status_persists_confirmed_provider_account(
        self,
        test_db: AsyncSession,
        mock_user: User,
        monkeypatch,
    ):
        """Polling should persist a real provider result without simulate-confirm."""

        class StubProvider:
            provider_name = "weread_platform"

            async def generate(self):
                from app.services.qr_providers import ProviderGenerateResult

                return ProviderGenerateResult(
                    qr_url="https://scan.example.com/qr",
                    provider_ticket="provider-ticket-1",
                    expire_at=datetime.now(timezone.utc) + timedelta(minutes=5),
                    state={"provider_ticket": "provider-ticket-1"},
                )

            async def poll(self, state):
                from app.services.qr_providers import ProviderPollResult

                return ProviderPollResult(
                    status="confirmed",
                    state=state,
                    account_payload={
                        "external_id": "weread-user-1",
                        "display_name": "微信读书账号",
                        "credentials": {"token": "real-token", "vid": 123},
                        "expires_at": datetime.now(timezone.utc) + timedelta(days=7),
                        "metadata_json": {"provider": "weread_platform"},
                    },
                    message="登录成功",
                )

            async def cancel(self, state):
                return None

        monkeypatch.setattr("app.services.qr_login_service.get_qr_provider", lambda account_type: StubProvider())

        service = QRLoginService(test_db)
        service.redis = FakeRedis()

        generate_result = await service.generate(
            MagicMock(type=CollectorAccountType.WEREAD),
            mock_user,
        )

        status = await service.get_status(generate_result.ticket, mock_user)

        assert status.status == "confirmed"
        assert status.account_name == "微信读书账号"
        saved = await service.collector_account_service.repo.get_by_owner_type_and_external_id(
            mock_user.id,
            CollectorAccountType.WEREAD,
            "weread-user-1",
        )
        assert saved is not None
        assert saved.credentials["token"] == "real-token"

    @pytest.mark.asyncio
    async def test_update_ai_analysis(self, test_db: AsyncSession, mock_article: Article):
        """Test updating article AI analysis."""
        service = ArticleService(test_db)

        updated = await service.update_ai_analysis(
            article_id=mock_article.id,
            ai_relevance_ratio=0.92,
            ai_judgment={"ratio": 0.92, "reason": "High sports content"},
        )

        assert updated.ai_relevance_ratio == 0.92


class TestParserService:
    """Test cases for ParserService."""

    def test_clean_html(self):
        """Test HTML cleaning."""
        parser = ParserService()
        html = """
        <html>
            <head><title>Test</title></head>
            <body>
                <script>alert('bad');</script>
                <nav>Navigation</nav>
                <h1>Article Title</h1>
                <p>Article content here.</p>
            </body>
        </html>
        """

        text, images = parser.clean_html(html)

        assert "alert" not in text
        assert "Navigation" not in text
        assert "Article Title" in text
        assert "Article content here" in text

    def test_extract_title(self):
        """Test title extraction."""
        parser = ParserService()
        html = """
        <html>
            <head><meta property="og:title" content="Open Graph Title"/></head>
            <body><h1 class="article-title">Article Title</h1></body>
        </html>
        """

        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "lxml")
        title = parser.extract_title(soup)

        assert title == "Article Title"

    async def test_parse_article(self):
        """Test full article parsing."""
        parser = ParserService()
        html = """
        <html>
            <body>
                <h1 class="article-title">Test Article</h1>
                <p>Content paragraph</p>
                <img src="https://example.com/image.jpg"/>
            </body>
        </html>
        """

        result = await parser.parse_article(html, download_images=False)

        assert isinstance(result, ParsedArticle)
        assert result.title == "Test Article"
        assert "Content paragraph" in result.content

    async def test_parse_article_downloads_images_when_storage_id_provided(self):
        """Image downloads should use the configured storage target."""
        downloader = MagicMock()
        downloader.download_multiple = AsyncMock(return_value=["media/articles/1/test.jpg"])
        parser = ParserService(image_downloader=downloader)
        html = """
        <html>
            <body>
                <h1 class="article-title">Test Article</h1>
                <p>Content paragraph</p>
                <img src="https://example.com/image.jpg"/>
            </body>
        </html>
        """

        result = await parser.parse_article(
            html,
            download_images=True,
            storage_id=1,
            proxy="http://proxy.example.com:8080",
        )

        assert result.images == ["media/articles/1/test.jpg"]
        downloader.download_multiple.assert_awaited_once_with(
            ["https://example.com/image.jpg"],
            1,
            proxy="http://proxy.example.com:8080",
        )


class TestAIService:
    """Test cases for AIService."""

    @pytest.mark.asyncio
    async def test_mock_analysis(self):
        """Test mock AI analysis."""
        ai_service = AIService(mock_mode=True)

        result = await ai_service.analyze_article(
            content="This is a sports article about basketball and football games.",
        )

        assert "ratio" in result
        assert "reason" in result
        assert 0 <= result["ratio"] <= 1

    @pytest.mark.asyncio
    async def test_mock_analysis_with_sports_keywords(self):
        """Test mock analysis with sports content."""
        ai_service = AIService(mock_mode=True)

        # Content with clear sports keywords
        content = """
        The NBA finals are happening this weekend.
        Basketball teams competing for the championship.
        The championship game will be broadcast live.
        """

        result = await ai_service.analyze_article(content)

        assert result["ratio"] >= 0  # Mock returns random

    @pytest.mark.asyncio
    async def test_analyze_batch(self):
        """Test batch analysis."""
        ai_service = AIService(mock_mode=True)

        articles = [
            {"content": "Sports content about basketball"},
            {"content": "Tech news about AI"},
        ]

        results = await ai_service.analyze_batch(articles)

        assert len(results) == 2
        assert all("ratio" in r for r in results)


class TestFetcherService:
    """Test cases for FetcherService."""

    @pytest.mark.asyncio
    async def test_mp_fetcher_supports_pagination_and_dedup(self, test_db: AsyncSession):
        """Test MP fetcher paginates and de-duplicates update URLs."""
        fetcher = FetcherService(test_db)
        owner_user_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
        monitored = MonitoredAccount(
            owner_user_id=owner_user_id,
            biz="biz123",
            fakeid="fakeid123",
            name="Test MP",
            source_url="https://mp.weixin.qq.com/s/source",
            current_tier=3,
            composite_score=50.0,
            primary_fetch_mode=CollectorAccountType.MP_ADMIN,
            fallback_fetch_mode=CollectorAccountType.WEREAD,
            status=MonitoredAccountStatus.MONITORING,
            update_history={},
            ai_relevance_history={},
            strategy_config={"mp_max_pages": 3, "mp_page_size": 2},
        )
        collector = CollectorAccount(
            owner_user_id=owner_user_id,
            account_type=CollectorAccountType.MP_ADMIN,
            display_name="Collector",
            credentials={"cookies": {"session": "abc"}, "token": "token123"},
            status=CollectorAccountStatus.ACTIVE,
            health_status=CollectorHealthStatus.NORMAL,
            risk_status=RiskStatus.NORMAL,
            metadata_json={},
        )

        class DummyResponse:
            def __init__(self, payload, status_code=200):
                self._payload = payload
                self.status_code = status_code
                self.text = "{}"

            def json(self):
                return self._payload

        class DummyClient:
            def __init__(self, responses):
                self.responses = responses
                self.calls = []

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

            async def get(self, url, **kwargs):
                self.calls.append((url, kwargs))
                return self.responses.pop(0)

        client = DummyClient(
            [
                DummyResponse(
                    {
                        "app_msg_cnt": 4,
                        "can_msg_continue": 1,
                        "app_msg_list": [
                            {"title": "A", "link": "https://mp.weixin.qq.com/s/a", "update_time": 1710000000},
                            {"title": "B", "link": "https://mp.weixin.qq.com/s/b", "update_time": 1710000001},
                        ],
                    }
                ),
                DummyResponse(
                    {
                        "app_msg_cnt": 4,
                        "can_msg_continue": 0,
                        "app_msg_list": [
                            {"title": "B-dup", "link": "https://mp.weixin.qq.com/s/b", "update_time": 1710000001},
                            {"title": "C", "link": "https://mp.weixin.qq.com/s/c", "update_time": 1710000002},
                        ],
                    }
                ),
            ]
        )

        fetcher.mp_fetcher._build_client = lambda proxy_url: client
        fetcher.mp_fetcher._sleep_with_policy = AsyncMock()

        updates = await fetcher.mp_fetcher.fetch_updates(monitored, collector, None)

        assert [item.url for item in updates] == [
            "https://mp.weixin.qq.com/s/a",
            "https://mp.weixin.qq.com/s/b",
            "https://mp.weixin.qq.com/s/c",
        ]
        assert len(client.calls) == 2
        assert client.calls[0][1]["params"]["begin"] == 0
        assert client.calls[1][1]["params"]["begin"] == 2

    def test_extract_article_metadata_from_wechat_html(self):
        """Test detail metadata extraction from WeChat article HTML."""
        fetcher = FetcherService(MagicMock())
        raw_html = """
        <html>
          <head>
            <meta property="og:title" content="结构化标题" />
            <meta property="og:image" content="https://cdn.example.com/cover.jpg" />
            <meta property="article:published_time" content="2026-04-16T08:00:00+00:00" />
          </head>
          <body>
            <span id="js_name">结构化作者</span>
          </body>
        </html>
        """

        metadata = fetcher.mp_fetcher._extract_article_metadata(raw_html)

        assert metadata["title"] == "结构化标题"
        assert metadata["author"] == "结构化作者"
        assert metadata["cover_image"] == "https://cdn.example.com/cover.jpg"
        assert metadata["published_at"] == "2026-04-16T08:00:00+00:00"

    @pytest.mark.asyncio
    async def test_fetch_article_detail_rejects_wechat_captcha_page(self, test_db: AsyncSession):
        """A WeChat captcha page is HTTP 200 but must not be treated as article content."""
        fetcher = FetcherService(test_db)
        collector = CollectorAccount(
            owner_user_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
            account_type=CollectorAccountType.MP_ADMIN,
            display_name="Collector",
            credentials={"cookies": {}, "token": "token123"},
            status=CollectorAccountStatus.ACTIVE,
            health_status=CollectorHealthStatus.NORMAL,
            risk_status=RiskStatus.NORMAL,
            metadata_json={},
        )
        proxy = await ProxyService(test_db).create_proxy(
            host="127.0.0.20",
            port=8080,
            service_type=ServiceType.MP_DETAIL,
        )
        await test_db.refresh(proxy)

        async def fake_fetch_document(url, headers, proxy_url, prefer_curl=True):
            return DetailDocumentResponse(
                status_code=200,
                text="<html>wappoc_appmsgcaptcha poc_token 安全验证</html>",
                final_url="https://mp.weixin.qq.com/mp/wappoc_appmsgcaptcha?poc_token=test",
                headers={},
            )

        fetcher.mp_fetcher._fetch_document = fake_fetch_document
        fetcher.mp_fetcher._sleep_with_policy = AsyncMock()

        with pytest.raises(FetchFailedException) as exc_info:
            await fetcher.mp_fetcher.fetch_article_detail("https://mp.weixin.qq.com/s/test", collector, None)

        assert exc_info.value.details["category"] == "risk_control"
        assert exc_info.value.details["retryable"] is False

    @pytest.mark.asyncio
    async def test_fetch_article_detail_rotates_proxy_pool(self, test_db: AsyncSession):
        """Detail downloads should retry the next configured proxy before direct fallback."""
        first_proxy = Proxy(
            host="10.0.0.10",
            port=8080,
            service_type=ServiceType.MP_DETAIL,
            success_rate=90.0,
            is_active=True,
        )
        second_proxy = Proxy(
            host="10.0.0.11",
            port=8080,
            service_type=ServiceType.MP_DETAIL,
            success_rate=80.0,
            is_active=True,
        )
        test_db.add_all([first_proxy, second_proxy])
        await test_db.flush()
        proxy_service = ProxyService(test_db)
        await proxy_service.replace_service_bindings(first_proxy, [ProxyServiceKey.MP_DETAIL])
        await proxy_service.replace_service_bindings(second_proxy, [ProxyServiceKey.MP_DETAIL])

        fetcher = FetcherService(test_db)
        collector = CollectorAccount(
            owner_user_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
            account_type=CollectorAccountType.MP_ADMIN,
            display_name="Collector",
            credentials={"cookies": {"wxuin": "123"}, "token": "token123"},
            status=CollectorAccountStatus.ACTIVE,
            health_status=CollectorHealthStatus.NORMAL,
            risk_status=RiskStatus.NORMAL,
            metadata_json={},
        )
        calls = []

        async def fake_fetch_document(url, headers, proxy_url, prefer_curl=True):
            calls.append((url, headers, proxy_url))
            if proxy_url == first_proxy.proxy_url:
                return DetailDocumentResponse(
                    status_code=200,
                    text="<html>wappoc_appmsgcaptcha poc_token 安全验证</html>",
                    final_url="https://mp.weixin.qq.com/mp/wappoc_appmsgcaptcha",
                    headers={},
                )
            return DetailDocumentResponse(
                status_code=200,
                text=(
                    "<html><head><meta property=\"og:title\" content=\"OK\" />"
                    "<meta property=\"og:image\" content=\"https://cdn.example.com/a.jpg\" /></head>"
                    "<body><div id=\"js_content\">article</div></body></html>"
                ),
                final_url="https://mp.weixin.qq.com/s/test?token=token123",
                headers={},
            )

        fetcher.mp_fetcher._fetch_document = fake_fetch_document
        fetcher.mp_fetcher._sleep_with_policy = AsyncMock()

        detail = await fetcher.mp_fetcher.fetch_article_detail("https://mp.weixin.qq.com/s/test", collector, None)
        await test_db.refresh(first_proxy)
        await test_db.refresh(second_proxy)

        assert detail["title"] == "OK"
        assert [call[2] for call in calls] == [first_proxy.proxy_url, second_proxy.proxy_url]
        assert calls[0][0].endswith("token=token123")
        assert calls[0][1]["Cookie"] == "wxuin=123"
        assert first_proxy.success_rate == 75.0
        assert second_proxy.success_rate == 82.0

    def test_parse_wechat_public_page_from_general_msg_list(self):
        """Test WeRead/public page parser extracts article updates from embedded msg list."""
        fetcher = FetcherService(MagicMock())
        monitored = MonitoredAccount(
            owner_user_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
            biz="biz-public",
            fakeid="fake-public",
            name="Public Feed",
            source_url="https://mp.weixin.qq.com/mp/profile_ext?action=home&__biz=biz-public",
            current_tier=2,
            composite_score=50.0,
            primary_fetch_mode=CollectorAccountType.WEREAD,
            fallback_fetch_mode=CollectorAccountType.MP_ADMIN,
            status=MonitoredAccountStatus.MONITORING,
            update_history={},
            ai_relevance_history={},
            strategy_config={},
        )
        raw_html = r"""
        <script>
        var general_msg_list = "{\"list\":[{\"comm_msg_info\":{\"datetime\":1710000000},\"app_msg_ext_info\":{\"title\":\"主文章\",\"content_url\":\"/s?__biz=biz-public&mid=1&idx=1&sn=abc\",\"cover\":\"https://img.example.com/cover.jpg\",\"author\":\"作者A\",\"multi_app_msg_item_list\":[{\"title\":\"次文章\",\"content_url\":\"/s?__biz=biz-public&mid=1&idx=2&sn=def\",\"cover\":\"https://img.example.com/cover2.jpg\",\"author\":\"作者B\"}]}}]}";
        </script>
        """

        updates = fetcher.weread_fetcher._parse_wechat_public_page(raw_html, monitored)

        assert len(updates) == 2
        assert updates[0].title == "主文章"
        assert updates[0].url.startswith("https://mp.weixin.qq.com/s?")
        assert updates[0].author == "作者A"
        assert updates[1].title == "次文章"
        assert updates[1].author == "作者B"

    @pytest.mark.asyncio
    async def test_weread_fetcher_fetches_updates_from_public_history_page(self, test_db: AsyncSession):
        """Test WeRead fetcher uses public history page HTML to build updates."""
        fetcher = FetcherService(test_db)
        owner_user_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
        monitored = MonitoredAccount(
            owner_user_id=owner_user_id,
            biz="biz123",
            fakeid="fakeid123",
            name="Weread Feed",
            source_url="https://mp.weixin.qq.com/mp/profile_ext?action=home&__biz=biz123",
            current_tier=2,
            composite_score=50.0,
            primary_fetch_mode=CollectorAccountType.WEREAD,
            fallback_fetch_mode=CollectorAccountType.MP_ADMIN,
            status=MonitoredAccountStatus.MONITORING,
            update_history={},
            ai_relevance_history={},
            strategy_config={},
        )
        collector = CollectorAccount(
            owner_user_id=owner_user_id,
            account_type=CollectorAccountType.WEREAD,
            display_name="Weread Collector",
            credentials={"token": "token123", "cookies": {"session": "abc"}},
            status=CollectorAccountStatus.ACTIVE,
            health_status=CollectorHealthStatus.NORMAL,
            risk_status=RiskStatus.NORMAL,
            metadata_json={},
        )

        class DummyResponse:
            def __init__(self, text, status_code=200):
                self.text = text
                self.status_code = status_code

        class DummyClient:
            def __init__(self, responses):
                self.responses = responses
                self.calls = []

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

            async def get(self, url, **kwargs):
                self.calls.append((url, kwargs))
                return self.responses.pop(0)

        client = DummyClient(
            [
                DummyResponse(
                    r"""
                    <script>
                    var general_msg_list = "{\"list\":[{\"comm_msg_info\":{\"datetime\":1710000000},\"app_msg_ext_info\":{\"title\":\"文章一\",\"content_url\":\"/s?__biz=biz123&mid=1&idx=1&sn=aaa\",\"cover\":\"https://img.example.com/a.jpg\",\"author\":\"作者A\"}},{\"comm_msg_info\":{\"datetime\":1710000100},\"app_msg_ext_info\":{\"title\":\"文章二\",\"content_url\":\"/s?__biz=biz123&mid=2&idx=1&sn=bbb\",\"cover\":\"https://img.example.com/b.jpg\",\"author\":\"作者B\"}}]}";
                    </script>
                    """
                )
            ]
        )

        fetcher.weread_fetcher._build_client = lambda proxy_url: client
        fetcher.weread_fetcher._sleep_with_policy = AsyncMock()

        updates = await fetcher.weread_fetcher.fetch_updates(monitored, collector, None)

        assert len(updates) == 2
        assert updates[0].title == "文章一"
        assert updates[1].title == "文章二"
        assert updates[0].source_payload["channel"] == "weread"
        assert client.calls[0][0].startswith("https://mp.weixin.qq.com/mp/profile_ext")

    @pytest.mark.asyncio
    async def test_weread_fetcher_uses_source_article_before_history_page(self, test_db: AsyncSession):
        """Article-link monitors should fetch the seed article instead of parsing article anchors as history."""
        fetcher = FetcherService(test_db)
        owner_user_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
        monitored = MonitoredAccount(
            owner_user_id=owner_user_id,
            biz="MP_WXS_1",
            fakeid="MP_WXS_1",
            name="Weread Article",
            source_url="https://mp.weixin.qq.com/s/source-id",
            current_tier=2,
            composite_score=50.0,
            primary_fetch_mode=CollectorAccountType.WEREAD,
            fallback_fetch_mode=None,
            status=MonitoredAccountStatus.MONITORING,
            update_history={},
            ai_relevance_history={},
            strategy_config={},
        )
        collector = CollectorAccount(
            owner_user_id=owner_user_id,
            account_type=CollectorAccountType.WEREAD,
            display_name="Weread Collector",
            credentials={"token": "token123"},
            status=CollectorAccountStatus.ACTIVE,
            health_status=CollectorHealthStatus.NORMAL,
            risk_status=RiskStatus.NORMAL,
            metadata_json={"provider": "weread_platform", "platform_url": "https://platform.example.com"},
        )

        fetcher.weread_fetcher._fetch_platform_articles = AsyncMock(return_value=[])
        fetcher.weread_fetcher._build_client = MagicMock(side_effect=AssertionError("history page should not be fetched"))
        fetcher.weread_fetcher._sleep_with_policy = AsyncMock()

        updates = await fetcher.weread_fetcher.fetch_updates(monitored, collector, None)

        assert len(updates) == 1
        assert updates[0].url == monitored.source_url
        assert updates[0].source_payload["channel"] == "weread_source_article"

    def test_weread_platform_articles_support_real_payload_shape(self):
        """WeRead platform article payloads use camelCase fields and can be larger than one run should process."""
        fetcher = FetcherService(MagicMock())
        monitored = MonitoredAccount(
            owner_user_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
            biz="MP_WXS_1",
            fakeid="MP_WXS_1",
            name="Weread Feed",
            source_url="https://mp.weixin.qq.com/s/source",
            current_tier=2,
            composite_score=50.0,
            primary_fetch_mode=CollectorAccountType.WEREAD,
            fallback_fetch_mode=None,
            status=MonitoredAccountStatus.MONITORING,
            update_history={},
            ai_relevance_history={},
            strategy_config={},
        )

        updates = fetcher.weread_fetcher._parse_platform_articles(
            [
                {
                    "title": "A",
                    "url": "https://mp.weixin.qq.com/s/a",
                    "picUrl": "https://mmbiz.qpic.cn/a.jpg",
                    "publishTime": 1710000000,
                }
            ],
            monitored,
        )

        assert updates[0].published_at == 1710000000
        assert updates[0].cover_image == "https://mmbiz.qpic.cn/a.jpg"

    @pytest.mark.asyncio
    async def test_weread_detail_uses_direct_httpx_and_does_not_leak_token(self, test_db: AsyncSession):
        """WeRead platform bearer tokens must not be appended to mp.weixin.qq.com article URLs."""
        fetcher = FetcherService(test_db)
        collector = CollectorAccount(
            owner_user_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
            account_type=CollectorAccountType.WEREAD,
            display_name="Weread Collector",
            credentials={"token": "platform-token"},
            status=CollectorAccountStatus.ACTIVE,
            health_status=CollectorHealthStatus.NORMAL,
            risk_status=RiskStatus.NORMAL,
            metadata_json={"provider": "weread_platform"},
        )
        calls = []

        async def fake_fetch_document(url, headers, proxy_url, prefer_curl=True):
            calls.append((url, prefer_curl))
            return DetailDocumentResponse(
                status_code=200,
                text=(
                    "<html><head><meta property=\"og:title\" content=\"OK\" />"
                    "<meta property=\"og:image\" content=\"https://cdn.example.com/a.jpg\" /></head>"
                    "<body><div id=\"js_content\">article</div></body></html>"
                ),
                final_url=url,
                headers={},
            )

        fetcher.weread_fetcher._fetch_document = fake_fetch_document
        fetcher.weread_fetcher._sleep_with_policy = AsyncMock()

        detail = await fetcher.weread_fetcher.fetch_article_detail("https://mp.weixin.qq.com/s/test", collector, None)

        assert detail["title"] == "OK"
        assert calls == [("https://mp.weixin.qq.com/s/test", False)]

    @pytest.mark.asyncio
    async def test_weread_detail_caps_dynamic_interval(self, test_db: AsyncSession):
        """WeRead platform detail fetches should not inherit multi-minute MP-admin pacing."""
        fetcher = FetcherService(test_db)
        collector = CollectorAccount(
            owner_user_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
            account_type=CollectorAccountType.WEREAD,
            display_name="Weread Collector",
            credentials={"token": "platform-token"},
            status=CollectorAccountStatus.ACTIVE,
            health_status=CollectorHealthStatus.NORMAL,
            risk_status=RiskStatus.NORMAL,
            metadata_json={"provider": "weread_platform"},
        )

        async def fake_fetch_document(url, headers, proxy_url, prefer_curl=True):
            return DetailDocumentResponse(
                status_code=200,
                text=(
                    "<html><head><meta property=\"og:title\" content=\"OK\" />"
                    "<meta property=\"og:image\" content=\"https://cdn.example.com/a.jpg\" /></head>"
                    "<body><div id=\"js_content\">article</div></body></html>"
                ),
                final_url=url,
                headers={},
            )

        fetcher.weread_fetcher._fetch_document = fake_fetch_document
        fetcher.weread_fetcher._sleep_with_policy = AsyncMock()
        rate_limit_service.reset()
        try:
            await fetcher.weread_fetcher.fetch_article_detail("https://mp.weixin.qq.com/s/test", collector, None)
            assert rate_limit_service.detail_min_interval_seconds <= 2.0
        finally:
            rate_limit_service.reset()

    @pytest.mark.asyncio
    async def test_weread_platform_retries_transient_empty_article_list(self, test_db: AsyncSession):
        """The WeRead platform can return HTTP 200 with an empty list transiently."""
        fetcher = FetcherService(test_db)
        owner_user_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
        monitored = MonitoredAccount(
            owner_user_id=owner_user_id,
            biz="MP_WXS_1",
            fakeid="MP_WXS_1",
            name="Weread Feed",
            source_url="https://mp.weixin.qq.com/s/source",
            current_tier=2,
            composite_score=50.0,
            primary_fetch_mode=CollectorAccountType.WEREAD,
            fallback_fetch_mode=None,
            status=MonitoredAccountStatus.MONITORING,
            update_history={},
            ai_relevance_history={},
            strategy_config={"weread_empty_retry_count": 1},
            metadata_json={"weread_platform_mp_id": "MP_WXS_1"},
        )
        collector = CollectorAccount(
            owner_user_id=owner_user_id,
            account_type=CollectorAccountType.WEREAD,
            display_name="Weread Collector",
            credentials={"token": "platform-token", "vid": 123},
            status=CollectorAccountStatus.ACTIVE,
            health_status=CollectorHealthStatus.NORMAL,
            risk_status=RiskStatus.NORMAL,
            metadata_json={"provider": "weread_platform", "platform_url": "https://platform.example.com"},
        )

        class DummyResponse:
            status_code = 200

            def __init__(self, payload):
                self.payload = payload

            def json(self):
                return self.payload

        class DummyClient:
            def __init__(self):
                self.calls = 0

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

            async def get(self, url, **kwargs):
                self.calls += 1
                if self.calls == 1:
                    return DummyResponse([])
                return DummyResponse([{"title": "A", "url": "https://mp.weixin.qq.com/s/a"}])

        client = DummyClient()
        fetcher.weread_fetcher._build_client = lambda proxy_url: client
        monkey_sleep = AsyncMock()
        with patch("app.services.fetcher_service.asyncio.sleep", monkey_sleep):
            updates = await fetcher.weread_fetcher._fetch_platform_articles(monitored, collector, None)

        assert client.calls == 2
        assert updates[0].title == "A"
        monkey_sleep.assert_awaited_once_with(0.5)


class TestFetchPipelineService:
    """Targeted tests for monitored fetch pipeline behavior."""

    @pytest.mark.asyncio
    async def test_pipeline_skips_existing_article_urls(self, test_db: AsyncSession):
        """Pipeline should avoid refetching URLs already stored."""
        owner_user_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
        monitored = MonitoredAccount(
            owner_user_id=owner_user_id,
            biz="biz-pipeline",
            fakeid="fake-pipeline",
            name="Pipeline MP",
            source_url="https://mp.weixin.qq.com/s/pipeline",
            current_tier=3,
            composite_score=50.0,
            primary_fetch_mode=CollectorAccountType.MP_ADMIN,
            fallback_fetch_mode=CollectorAccountType.WEREAD,
            status=MonitoredAccountStatus.MONITORING,
            update_history={},
            ai_relevance_history={},
            strategy_config={},
            last_published_at=datetime.now(timezone.utc),
        )
        collector = CollectorAccount(
            owner_user_id=owner_user_id,
            account_type=CollectorAccountType.MP_ADMIN,
            display_name="Collector",
            credentials={"cookies": {"session": "abc"}, "token": "token123"},
            status=CollectorAccountStatus.ACTIVE,
            health_status=CollectorHealthStatus.NORMAL,
            risk_status=RiskStatus.NORMAL,
            metadata_json={},
        )
        test_db.add(monitored)
        test_db.add(collector)
        await test_db.commit()
        await test_db.refresh(monitored)
        await test_db.refresh(collector)

        pipeline = FetchPipelineService(test_db)
        pipeline.monitored_repo.get_by_id = AsyncMock(return_value=monitored)
        pipeline._select_collector = AsyncMock(return_value=collector)
        full_job = MagicMock(payload={})
        list_job = MagicMock(payload={})
        detail_job = MagicMock(payload={})
        pipeline.fetch_job_service.create_job = AsyncMock(side_effect=[full_job, list_job, detail_job])
        pipeline.fetch_job_service.mark_running = AsyncMock()
        pipeline.fetch_job_service.mark_success = AsyncMock()
        pipeline.fetch_job_service.mark_failed = AsyncMock()
        pipeline.collector_service.mark_success = AsyncMock()
        pipeline.collector_service.mark_failure = AsyncMock()
        pipeline.ai_service.analyze_article = AsyncMock(return_value={"ratio": 0.5, "reason": "ok", "keywords": []})
        pipeline.parser.parse_article = AsyncMock(
            return_value=MagicMock(content="parsed text", images=["media/articles/1/body.jpg"], title="Parsed Title")
        )
        pipeline.parser.image_downloader.download_image = AsyncMock(return_value="media/articles/1/cover.jpg")
        pipeline.parser.image_downloader.to_public_url = MagicMock(side_effect=lambda path: f"/{path}" if path else None)
        pipeline.adjuster.update_after_fetch = MagicMock(
            return_value={
                "new_tier": monitored.current_tier,
                "new_score": monitored.composite_score,
                "update_history": monitored.update_history,
                "ai_relevance_history": monitored.ai_relevance_history,
            }
        )
        pipeline._build_adjuster = AsyncMock(return_value=pipeline.adjuster)

        existing_url = "https://mp.weixin.qq.com/s/existing"
        new_url = "https://mp.weixin.qq.com/s/new"
        pipeline.fetcher.fetch_updates = AsyncMock(
            return_value=[
                MagicMock(url=existing_url, title="Existing", published_at=None, cover_image=None, author=None, source_payload={}),
                MagicMock(url=existing_url, title="Existing duplicate", published_at=None, cover_image=None, author=None, source_payload={}),
                MagicMock(url=new_url, title="New", published_at=None, cover_image=None, author=None, source_payload={}),
            ]
        )
        pipeline.fetcher.fetch_article_detail = AsyncMock(
            return_value={
                "raw_content": "<html></html>",
                "title": "Detail Title",
                "author": "Detail Author",
                "cover_image": "https://img.example.com/detail.jpg",
                "published_at": "2026-04-16T08:00:00+00:00",
            }
        )

        seen_new_url_checks = {"count": 0}

        async def fake_get_article_by_url(url):
            if url == existing_url:
                return MagicMock(url=url)
            seen_new_url_checks["count"] += 1
            return None

        pipeline.article_service.get_article_by_url = AsyncMock(side_effect=fake_get_article_by_url)
        pipeline.article_service.save_article = AsyncMock(return_value=MagicMock(published_at=datetime.now(timezone.utc)))
        pipeline.monitored_repo.update = AsyncMock(return_value=monitored)

        result = await pipeline.run_monitored_account(monitored.id)

        assert result["success"] is True
        assert result["articles_processed"] == 1
        assert pipeline.fetcher.fetch_article_detail.await_count == 1
        assert pipeline.article_service.save_article.await_count == 1
        save_kwargs = pipeline.article_service.save_article.await_args.kwargs
        assert save_kwargs["images"] == ["/media/articles/1/body.jpg"]
        assert save_kwargs["cover_image"] == "/media/articles/1/cover.jpg"
        assert seen_new_url_checks["count"] == 1
        assert pipeline.fetch_job_service.create_job.await_count == 3
        mark_success_calls = pipeline.fetch_job_service.mark_success.await_args_list
        assert len(mark_success_calls) == 3
        assert mark_success_calls[0].kwargs["payload"]["stage"] == "update_list"
        assert mark_success_calls[1].kwargs["payload"]["stage"] == "article_detail"
        assert mark_success_calls[2].kwargs["payload"]["stage"] == "full_sync"

    @pytest.mark.asyncio
    async def test_pipeline_records_failure_category_and_updates_collector(self, test_db: AsyncSession):
        """Pipeline should persist structured failure info for classified fetch failures."""
        owner_user_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
        monitored = MonitoredAccount(
            owner_user_id=owner_user_id,
            biz="biz-failure",
            fakeid="fake-failure",
            name="Failure MP",
            source_url="https://mp.weixin.qq.com/s/failure",
            current_tier=3,
            composite_score=50.0,
            primary_fetch_mode=CollectorAccountType.MP_ADMIN,
            fallback_fetch_mode=CollectorAccountType.WEREAD,
            status=MonitoredAccountStatus.MONITORING,
            update_history={},
            ai_relevance_history={},
            strategy_config={},
        )
        collector = CollectorAccount(
            owner_user_id=owner_user_id,
            account_type=CollectorAccountType.MP_ADMIN,
            display_name="Collector",
            credentials={"cookies": {"session": "abc"}, "token": "token123"},
            status=CollectorAccountStatus.ACTIVE,
            health_status=CollectorHealthStatus.NORMAL,
            risk_status=RiskStatus.NORMAL,
            metadata_json={},
        )
        test_db.add(monitored)
        test_db.add(collector)
        await test_db.commit()
        await test_db.refresh(monitored)
        await test_db.refresh(collector)

        pipeline = FetchPipelineService(test_db)
        full_job = MagicMock(payload={})
        list_job = MagicMock(payload={})
        pipeline.monitored_repo.get_by_id = AsyncMock(return_value=monitored)
        pipeline._select_collector = AsyncMock(return_value=collector)
        pipeline.fetch_job_service.create_job = AsyncMock(side_effect=[full_job, list_job])
        pipeline.fetch_job_service.mark_running = AsyncMock()
        pipeline.fetch_job_service.mark_success = AsyncMock()
        pipeline.fetch_job_service.mark_failed = AsyncMock()
        pipeline.collector_service.mark_success = AsyncMock()
        pipeline.collector_service.mark_failure = AsyncMock()
        pipeline.collector_service.mark_fetch_failure = AsyncMock()
        pipeline.fetcher.fetch_updates = AsyncMock(
            side_effect=FetchFailedException(
                monitored.id,
                "rate limited by upstream",
                category="risk_control",
                retryable=False,
            )
        )

        result = await pipeline.run_monitored_account(monitored.id)

        assert result["success"] is False
        pipeline.collector_service.mark_fetch_failure.assert_awaited_once()
        assert pipeline.fetch_job_service.mark_failed.await_count == 2
        stage_payloads = [call.kwargs["payload"] for call in pipeline.fetch_job_service.mark_failed.await_args_list]
        assert stage_payloads[0]["stage"] == "update_list"
        assert stage_payloads[0]["failure_category"] == "risk_control"
        assert stage_payloads[0]["retryable"] is False
        assert stage_payloads[1]["failure_category"] == "risk_control"

        notifications = (await test_db.execute(Select(Notification))).scalars().all()
        assert len(notifications) == 1
        assert notifications[0].owner_user_id == owner_user_id
        assert notifications[0].notification_type == "fetch_error_risk_control"

    @pytest.mark.asyncio
    async def test_pipeline_creates_high_relevance_notification(self, test_db: AsyncSession):
        """High relevance articles should emit user-scoped notifications."""
        owner_user_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
        monitored = MonitoredAccount(
            owner_user_id=owner_user_id,
            biz="biz-alert",
            fakeid="fake-alert",
            name="Alert MP",
            source_url="https://mp.weixin.qq.com/s/alert",
            current_tier=3,
            composite_score=50.0,
            primary_fetch_mode=CollectorAccountType.MP_ADMIN,
            fallback_fetch_mode=CollectorAccountType.WEREAD,
            status=MonitoredAccountStatus.MONITORING,
            update_history={},
            ai_relevance_history={},
            strategy_config={},
        )
        collector = CollectorAccount(
            owner_user_id=owner_user_id,
            account_type=CollectorAccountType.MP_ADMIN,
            display_name="Collector",
            credentials={"cookies": {"session": "abc"}, "token": "token123"},
            status=CollectorAccountStatus.ACTIVE,
            health_status=CollectorHealthStatus.NORMAL,
            risk_status=RiskStatus.NORMAL,
            metadata_json={},
        )
        test_db.add_all([monitored, collector])
        await test_db.commit()
        await test_db.refresh(monitored)
        await test_db.refresh(collector)

        pipeline = FetchPipelineService(test_db)
        full_job = MagicMock(payload={})
        list_job = MagicMock(payload={})
        detail_job = MagicMock(payload={})
        article = MagicMock(
            id=1,
            title="Hot Article",
            url="https://mp.weixin.qq.com/s/hot",
            published_at=datetime.now(timezone.utc),
        )

        pipeline.monitored_repo.get_by_id = AsyncMock(return_value=monitored)
        pipeline._select_collector = AsyncMock(return_value=collector)
        pipeline.fetch_job_service.create_job = AsyncMock(side_effect=[full_job, list_job, detail_job])
        pipeline.fetch_job_service.mark_running = AsyncMock()
        pipeline.fetch_job_service.mark_success = AsyncMock()
        pipeline.fetch_job_service.mark_failed = AsyncMock()
        pipeline.fetcher.fetch_updates = AsyncMock(
            return_value=[MagicMock(url="https://mp.weixin.qq.com/s/hot", title="Hot Article", cover_image=None, author=None, published_at=None, source_payload={})]
        )
        pipeline.fetcher.fetch_article_detail = AsyncMock(
            return_value={"raw_content": "<html><body>hot</body></html>", "title": "Hot Article"}
        )
        pipeline.fetcher.get_detail_proxy_for_mode = AsyncMock(return_value=None)
        pipeline.parser.parse_article = AsyncMock(
            return_value=ParsedArticle(title="Hot Article", content="hot content", images=[], raw_content="<html></html>")
        )
        pipeline.ai_service.analyze_article = AsyncMock(
            return_value={"ratio": 0.91, "reason": "high relevance", "keywords": [], "json_data": {}}
        )
        pipeline.article_service.get_article_by_url = AsyncMock(return_value=None)
        pipeline.article_service.save_article = AsyncMock(return_value=article)
        pipeline.adjuster.update_after_fetch = MagicMock(
            return_value={
                "new_tier": monitored.current_tier,
                "new_score": monitored.composite_score,
                "update_history": monitored.update_history,
                "ai_relevance_history": {datetime.now(timezone.utc).isoformat(): {"ratio": 0.91, "reason": "high relevance"}},
            }
        )
        pipeline._build_adjuster = AsyncMock(return_value=pipeline.adjuster)
        pipeline.monitored_repo.update = AsyncMock(return_value=monitored)
        pipeline.collector_service.mark_success = AsyncMock()

        result = await pipeline.run_monitored_account(monitored.id)

        assert result["success"] is True
        notifications = (await test_db.execute(Select(Notification))).scalars().all()
        assert len(notifications) == 1
        assert notifications[0].notification_type == "high_relevance"
        assert notifications[0].article_id == 1
        assert notifications[0].monitored_account_id == monitored.id


class TestCollectorHealthService:
    """Collector account health checks should use real credential probes."""

    @pytest.mark.asyncio
    async def test_mp_admin_redirect_to_login_is_expired(self):
        service = HealthCheckService()
        account = CollectorAccount(
            owner_user_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
            account_type=CollectorAccountType.MP_ADMIN,
            display_name="Collector",
            credentials={"cookies": {"session": "abc"}, "token": "token123"},
            status=CollectorAccountStatus.ACTIVE,
            health_status=CollectorHealthStatus.NORMAL,
            risk_status=RiskStatus.NORMAL,
            metadata_json={},
        )

        with patch.object(
            service,
            "_check_mp_admin_collector",
            new=AsyncMock(return_value=(CollectorHealthStatus.EXPIRED, "已跳转到登录页")),
        ):
            status, reason, _ = await service.check_collector_account_health(account)

        assert status == CollectorHealthStatus.EXPIRED
        assert reason == "已跳转到登录页"

    @pytest.mark.asyncio
    async def test_weread_expiring_soon_is_reported(self):
        service = HealthCheckService()
        account = CollectorAccount(
            owner_user_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
            account_type=CollectorAccountType.WEREAD,
            display_name="Weread",
            credentials={"token": "token123"},
            expires_at=datetime.now(timezone.utc) + timedelta(hours=2),
            status=CollectorAccountStatus.ACTIVE,
            health_status=CollectorHealthStatus.NORMAL,
            risk_status=RiskStatus.NORMAL,
            metadata_json={},
        )

        with patch.object(
            service,
            "_check_weread_collector",
            new=AsyncMock(return_value=(CollectorHealthStatus.NORMAL, "正常")),
        ):
            status, reason, expires_at = await service.check_collector_account_health(account)

        assert status == CollectorHealthStatus.NORMAL
        assert reason == "凭证即将过期"
        assert expires_at == account.expires_at

    @pytest.mark.asyncio
    async def test_weread_platform_404_probes_are_not_marked_normal(self):
        service = HealthCheckService()
        account = CollectorAccount(
            owner_user_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
            account_type=CollectorAccountType.WEREAD,
            display_name="Weread",
            credentials={"token": "token123"},
            status=CollectorAccountStatus.ACTIVE,
            health_status=CollectorHealthStatus.NORMAL,
            risk_status=RiskStatus.NORMAL,
            metadata_json={"provider": "weread_platform", "platform_url": "https://platform.example.com"},
        )

        class FakeResponse:
            status_code = 404

        class FakeClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                return None

            async def get(self, *args, **kwargs):
                return FakeResponse()

        with patch("app.services.health_service.httpx.AsyncClient", return_value=FakeClient()):
            status, reason = await service._check_weread_collector(account)

        assert status == CollectorHealthStatus.RESTRICTED
        assert reason == "平台健康检查接口不可用"

    @pytest.mark.asyncio
    async def test_weread_platform_article_probe_reports_expired_token(self, test_db: AsyncSession, mock_user: User):
        service = HealthCheckService()
        account = CollectorAccount(
            owner_user_id=mock_user.id,
            account_type=CollectorAccountType.WEREAD,
            display_name="Weread",
            credentials={"token": "token123", "vid": "vid123"},
            external_id="vid123",
            status=CollectorAccountStatus.ACTIVE,
            health_status=CollectorHealthStatus.NORMAL,
            risk_status=RiskStatus.NORMAL,
            metadata_json={"provider": "weread_platform", "platform_url": "https://platform.example.com"},
        )
        monitored = MonitoredAccount(
            owner_user_id=mock_user.id,
            biz="biz",
            fakeid="fakeid",
            name="Monitored",
            source_url="https://mp.weixin.qq.com/s/test",
            metadata_json={"weread_platform_mp_id": "MP_WXS_1"},
            current_tier=3,
            composite_score=50.0,
            primary_fetch_mode=CollectorAccountType.WEREAD,
            status=MonitoredAccountStatus.MONITORING,
        )
        test_db.add_all([account, monitored])
        await test_db.commit()

        class FakeResponse:
            status_code = 401

        class FakeClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                return None

            async def get(self, *args, **kwargs):
                return FakeResponse()

        with patch("app.services.health_service.httpx.AsyncClient", return_value=FakeClient()):
            status, reason, _ = await service.check_collector_account_health(account, test_db)

        assert status == CollectorHealthStatus.EXPIRED
        assert reason == "平台令牌失效"


class TestNotificationService:
    """Notification dispatch and de-duplication."""

    @pytest.mark.asyncio
    async def test_create_notification_posts_to_webhook(self, test_db: AsyncSession, mock_user: User):
        service = NotificationService(test_db)
        test_db.add(
            NotificationEmailConfig(
                enabled=True,
                smtp_host="smtp.example.com",
                smtp_port=587,
                smtp_username="user",
                smtp_password="secret",
                from_email="alerts@example.com",
                to_emails=["ops@example.com"],
                use_tls=True,
            )
        )
        await test_db.commit()

        with patch("app.services.notification_service.asyncio.to_thread", new=AsyncMock()) as to_thread:
            notification = await service.create_notification(
                owner_user_id=mock_user.id,
                notification_type="fetch_error",
                title="Fetch failed",
                content="boom",
            )

        assert notification.id is not None
        to_thread.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_duplicate_notification_is_suppressed(self, test_db: AsyncSession, mock_user: User):
        service = NotificationService(test_db)

        first = await service.create_notification(
            owner_user_id=mock_user.id,
            notification_type="collector_expired",
            title="Expired",
            content="expired",
            collector_account_id=1,
        )
        second = await service.create_notification(
            owner_user_id=mock_user.id,
            notification_type="collector_expired",
            title="Expired",
            content="expired",
            collector_account_id=1,
        )

        assert first.id == second.id
        notifications = (await test_db.execute(Select(Notification))).scalars().all()
        assert len(notifications) == 1
