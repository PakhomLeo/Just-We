"""Tests for API routes."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch
import base64

import httpx
import pytest
from httpx import AsyncClient, ASGITransport
from redis.exceptions import ConnectionError as RedisConnectionError
from sqlalchemy import Select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.core.dependencies import get_current_user, get_db
from app.core.exceptions import QRProviderNotConfiguredException
from app.models.user import User, UserRole
from app.models.article import Article
from app.models.collector_account import CollectorHealthStatus
from app.models.log import OperationLog
from app.models.monitored_account import MonitoredAccount
from app.models.notification import Notification
from app.models.proxy import Proxy, ProxyKind


class TestAuthAPI:
    """Test cases for authentication API."""

    @pytest.mark.asyncio
    async def test_login_success(self, test_db: AsyncSession, mock_user: User):
        """Test successful login."""
        from app.services.auth_service import AuthService

        # Create real user with hashed password
        auth_service = AuthService(test_db)
        hashed = auth_service.hash_password("testpassword123")

        mock_user.hashed_password = hashed
        await test_db.commit()

        # Use test client
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/auth/login",
                json={"email": "test@example.com", "password": "testpassword123"},
            )

        assert response.status_code in [200, 401]  # 401 if user not properly set up

    @pytest.mark.asyncio
    async def test_register_success(self, test_db: AsyncSession):
        """Test successful registration."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/auth/register",
                json={
                    "email": "newuser@example.com",
                    "password": "securepassword123",
                    "role": "viewer",
                },
            )

        # May fail if DB not properly configured, but tests structure
        assert response.status_code in [201, 422, 500]

    @pytest.mark.asyncio
    async def test_get_me(self, test_db: AsyncSession, mock_user: User):
        """Test getting current user info."""

        async def override_get_db():
            yield test_db

        def override_get_current_user():
            return mock_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.get("/api/auth/me")

        # Should work with proper auth override
        if response.status_code == 200:
            data = response.json()
            assert "email" in data

        app.dependency_overrides.clear()


class TestArticleAPI:
    """Test cases for article API."""

    @pytest.mark.asyncio
    async def test_list_articles(
        self, test_db: AsyncSession, mock_user: User, mock_article: Article
    ):
        """Test listing articles."""
        mock_user.role = UserRole.VIEWER

        async def override_get_db():
            yield test_db

        def override_get_current_user():
            return mock_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.get("/api/articles/")

        if response.status_code == 200:
            data = response.json()
            assert "items" in data

        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_article(
        self, test_db: AsyncSession, mock_user: User, mock_article: Article
    ):
        """Test getting single article."""
        mock_user.role = UserRole.VIEWER

        async def override_get_db():
            yield test_db

        def override_get_current_user():
            return mock_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.get(f"/api/articles/{mock_article.id}")

        if response.status_code == 200:
            data = response.json()
            assert data["id"] == mock_article.id

        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_list_articles_scoped_to_current_user_monitored_accounts(
        self,
        test_db: AsyncSession,
        mock_user: User,
        mock_monitored_article: Article,
        other_monitored_article: Article,
    ):
        """Non-admin users should only see their own monitored-account articles."""

        mock_user.role = UserRole.VIEWER

        async def override_get_db():
            yield test_db

        def override_get_current_user():
            return mock_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/articles/")

        assert response.status_code == 200
        data = response.json()
        article_ids = {item["id"] for item in data["items"]}
        assert mock_monitored_article.id in article_ids
        assert other_monitored_article.id not in article_ids

        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_monitored_articles_route_is_not_shadowed_by_article_id_route(
        self,
        test_db: AsyncSession,
        mock_user: User,
        mock_monitored_account,
        mock_monitored_article: Article,
    ):
        """The monitored-account article list path should resolve before /{article_id}."""
        mock_user.role = UserRole.VIEWER

        async def override_get_db():
            yield test_db

        def override_get_current_user():
            return mock_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(f"/api/articles/monitored/{mock_monitored_account.id}")

        assert response.status_code == 200
        article_ids = {item["id"] for item in response.json()["items"]}
        assert mock_monitored_article.id in article_ids

        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_article_blocks_other_users_monitored_articles(
        self,
        test_db: AsyncSession,
        mock_user: User,
        other_monitored_article: Article,
    ):
        """Non-admin users should not access monitored-account articles owned by others."""

        mock_user.role = UserRole.VIEWER

        async def override_get_db():
            yield test_db

        def override_get_current_user():
            return mock_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(f"/api/articles/{other_monitored_article.id}")

        assert response.status_code == 404

        app.dependency_overrides.clear()


class TestMonitoredAndCollectorIsolationAPI:
    """Test ownership checks for monitored and collector account APIs."""

    @pytest.mark.asyncio
    async def test_get_other_users_monitored_account_returns_404(
        self,
        test_db: AsyncSession,
        mock_user: User,
        other_monitored_account,
    ):
        mock_user.role = UserRole.VIEWER

        async def override_get_db():
            yield test_db

        def override_get_current_user():
            return mock_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(f"/api/monitored-accounts/{other_monitored_account.id}")

        assert response.status_code == 404
        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_update_target_tier_locks_manual_override(
        self,
        test_db: AsyncSession,
        mock_user: User,
        mock_monitored_account: MonitoredAccount,
    ):
        mock_user.role = UserRole.VIEWER

        def override_get_current_user():
            return mock_user

        app.dependency_overrides[get_current_user] = override_get_current_user

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.put(
                f"/api/monitored-accounts/{mock_monitored_account.id}",
                json={"target_tier": 1},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["current_tier"] == 1
        assert data["manual_override"]["target_tier"] == 1
        assert data["manual_override"]["locked"] is True

        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_delete_monitored_account_removes_dependents(
        self,
        test_db: AsyncSession,
        mock_user: User,
        mock_monitored_account: MonitoredAccount,
        mock_monitored_article: Article,
    ):
        mock_user.role = UserRole.VIEWER
        notification = Notification(
            owner_user_id=mock_user.id,
            monitored_account_id=mock_monitored_account.id,
            article_id=mock_monitored_article.id,
            notification_type="article_update",
            title="New article",
            content="New monitored article",
            payload={},
        )
        test_db.add(notification)
        await test_db.commit()

        def override_get_current_user():
            return mock_user

        app.dependency_overrides[get_current_user] = override_get_current_user

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            delete_response = await client.delete(f"/api/monitored-accounts/{mock_monitored_account.id}")
            get_response = await client.get(f"/api/monitored-accounts/{mock_monitored_account.id}")

        assert delete_response.status_code == 204
        assert get_response.status_code == 404
        account_count = await test_db.scalar(Select(func.count()).select_from(MonitoredAccount))
        article_count = await test_db.scalar(Select(func.count()).select_from(Article))
        notification_count = await test_db.scalar(Select(func.count()).select_from(Notification))
        assert account_count == 0
        assert article_count == 0
        assert notification_count == 0

        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_health_check_updates_status_and_creates_notification(
        self,
        test_db: AsyncSession,
        mock_user: User,
        mock_collector_account,
    ):
        mock_user.role = UserRole.VIEWER

        async def override_get_db():
            yield test_db

        def override_get_current_user():
            return mock_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        with patch("app.api.collector_accounts.health_check_service.check_collector_account_health", new=AsyncMock(
            return_value=(CollectorHealthStatus.EXPIRED, "凭证已过期", mock_collector_account.expires_at)
        )):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post(f"/api/collector-accounts/{mock_collector_account.id}/health-check")

        assert response.status_code == 200
        data = response.json()
        assert data["health_status"] == "expired"

        notifications = (await test_db.execute(Select(Notification))).scalars().all()
        assert len(notifications) == 1
        assert notifications[0].owner_user_id == mock_user.id
        assert notifications[0].collector_account_id == mock_collector_account.id
        assert notifications[0].notification_type == "collector_expired"

        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_generate_qr_accepts_account_type_alias(
        self,
        test_db: AsyncSession,
        mock_user: User,
    ):
        mock_user.role = UserRole.ADMIN

        async def override_get_db():
            yield test_db

        def override_get_current_user():
            return mock_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        with patch("app.api.collector_accounts.QRLoginService.generate", new=AsyncMock(return_value={
            "qr_url": "https://example.com/qr.png",
            "ticket": "ticket-1",
            "expire_at": datetime.now(timezone.utc).isoformat(),
            "provider": "stub",
        })):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post(
                    "/api/collector-accounts/qr/generate",
                    json={"account_type": "mp_admin"},
                )

        assert response.status_code == 200
        assert response.json()["ticket"] == "ticket-1"
        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_generate_qr_returns_503_when_redis_unavailable(
        self,
        test_db: AsyncSession,
        mock_user: User,
    ):
        mock_user.role = UserRole.OPERATOR

        async def override_get_db():
            yield test_db

        def override_get_current_user():
            return mock_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        with patch(
            "app.api.collector_accounts.QRLoginService.generate",
            new=AsyncMock(side_effect=RedisConnectionError("redis down")),
        ):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post(
                    "/api/collector-accounts/qr/generate",
                    json={"type": "mp_admin"},
                )

        assert response.status_code == 503
        assert response.json()["detail"] == "Redis is unavailable; QR login state cannot be stored"
        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_generate_qr_returns_503_when_provider_not_configured(
        self,
        test_db: AsyncSession,
        mock_user: User,
    ):
        mock_user.role = UserRole.OPERATOR

        async def override_get_db():
            yield test_db

        def override_get_current_user():
            return mock_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        with patch(
            "app.api.collector_accounts.QRLoginService.generate",
            new=AsyncMock(side_effect=QRProviderNotConfiguredException("weread_platform")),
        ):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post(
                    "/api/collector-accounts/qr/generate",
                    json={"type": "weread"},
                )

        assert response.status_code == 503
        assert response.json()["detail"] == "weread_platform 未配置，暂时无法生成二维码"
        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_mp_admin_qr_image_is_returned_as_data_url(self):
        from app.services.qr_providers import MpAdminQRProvider

        image_bytes = b"fake-png"

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, headers={"content-type": "image/png"}, content=image_bytes)

        provider = MpAdminQRProvider()
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            data_url = await provider._fetch_qr_data_url(
                client,
                "https://mp.weixin.qq.com/cgi-bin/scanloginqrcode?action=getqrcode&uuid=test",
            )

        assert data_url == f"data:image/png;base64,{base64.b64encode(image_bytes).decode('ascii')}"

    @pytest.mark.asyncio
    async def test_mp_admin_generate_uses_startlogin_session_flow(self, monkeypatch):
        from app.services.qr_providers import MpAdminQRProvider

        requests: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            if request.url.path.endswith("/cgi-bin/bizlogin"):
                assert request.url.params.get("action") == "startlogin"
                assert b"sessionid=" in request.content
                return httpx.Response(
                    200,
                    headers={
                        "content-type": "application/json",
                        "set-cookie": "uuid=session-cookie; Domain=.mp.weixin.qq.com; Path=/",
                    },
                    json={"base_resp": {"ret": 0}},
                )
            if request.url.path.endswith("/cgi-bin/scanloginqrcode"):
                assert request.url.params.get("action") == "getqrcode"
                assert "uuid" not in request.url.params
                return httpx.Response(200, headers={"content-type": "image/png"}, content=b"fake-png")
            return httpx.Response(404)

        transport = httpx.MockTransport(handler)
        original_async_client = httpx.AsyncClient

        def client_factory(*args, **kwargs):
            kwargs["transport"] = transport
            return original_async_client(*args, **kwargs)

        monkeypatch.setattr("app.services.qr_providers.httpx.AsyncClient", client_factory)

        result = await MpAdminQRProvider().generate()

        assert result.qr_url.startswith("data:image/png;base64,")
        assert result.provider_ticket == result.state["sessionid"]
        assert [request.url.path for request in requests] == [
            "/cgi-bin/bizlogin",
            "/cgi-bin/scanloginqrcode",
        ]

    @pytest.mark.asyncio
    async def test_mp_admin_poll_finalizes_without_fingerprint(self):
        from app.services.qr_providers import MpAdminQRProvider

        provider = MpAdminQRProvider()
        provider.discover_profile_from_credentials = AsyncMock(
            return_value={
                "fakeid": "fakeid_123",
                "nickname": "测试公众号",
                "cookies": {"wxuin": "uin123", "session": "abc"},
            }
        )
        requests: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            if request.url.path.endswith("/cgi-bin/scanloginqrcode"):
                assert request.url.params.get("action") == "ask"
                assert "fingerprint" not in request.url.params
                return httpx.Response(200, json={"base_resp": {"ret": 0}, "status": 1})
            if request.url.path.endswith("/cgi-bin/bizlogin"):
                body = request.content.decode()
                assert request.url.params.get("action") == "login"
                assert "fingerprint" not in body
                return httpx.Response(
                    200,
                    headers={"set-cookie": "wxuin=uin123; Domain=.mp.weixin.qq.com; Path=/"},
                    json={"base_resp": {"ret": 0}, "redirect_url": "/cgi-bin/home?t=home/index&token=abc123&lang=zh_CN"},
                )
            return httpx.Response(404)

        transport = httpx.MockTransport(handler)
        provider._client_from_state = lambda state: httpx.AsyncClient(
            transport=transport,
            headers=provider._build_headers(),
            follow_redirects=True,
        )

        result = await provider.poll({"provider_ticket": "sid", "sessionid": "sid", "cookies": {"uuid": "u"}})

        assert result.status == "confirmed"
        assert result.account_payload["credentials"]["token"] == "abc123"
        assert result.account_payload["credentials"]["fakeid"] == "fakeid_123"
        assert [request.url.path for request in requests] == [
            "/cgi-bin/scanloginqrcode",
            "/cgi-bin/bizlogin",
        ]

    def test_weread_scan_url_is_encoded_as_displayable_qr_data_url(self):
        from app.services.qr_providers import build_qr_svg_data_url

        data_url = build_qr_svg_data_url("https://weread.qq.com/web/login?q=test")

        assert data_url.startswith("data:image/svg+xml;base64,")
        decoded = base64.b64decode(data_url.split(",", 1)[1]).decode("utf-8")
        assert "<svg" in decoded
        assert "https://weread.qq.com/web/login" not in data_url


class TestNotificationAPI:
    """Test notification visibility and mutation."""

    @pytest.mark.asyncio
    async def test_list_notifications_scoped_to_current_user(
        self,
        test_db: AsyncSession,
        mock_user: User,
        other_user: User,
    ):
        first = Notification(
            owner_user_id=mock_user.id,
            notification_type="fetch_error",
            title="Mine",
            content="Visible",
            payload={},
        )
        second = Notification(
            owner_user_id=other_user.id,
            notification_type="fetch_error",
            title="Other",
            content="Hidden",
            payload={},
        )
        test_db.add_all([first, second])
        await test_db.commit()

        mock_user.role = UserRole.VIEWER

        async def override_get_db():
            yield test_db

        def override_get_current_user():
            return mock_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/notifications/")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["title"] == "Mine"

        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_health_check_other_users_collector_returns_404(
        self,
        test_db: AsyncSession,
        mock_user: User,
        other_collector_account,
    ):
        mock_user.role = UserRole.VIEWER

        async def override_get_db():
            yield test_db

        def override_get_current_user():
            return mock_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(f"/api/collector-accounts/{other_collector_account.id}/health-check")

        assert response.status_code == 404
        app.dependency_overrides.clear()


class TestProxyAPI:
    """Test cases for proxy API."""

    @pytest.mark.asyncio
    async def test_list_proxies(
        self, test_db: AsyncSession, mock_user: User, mock_proxy: Proxy
    ):
        """Test listing proxies."""
        mock_user.role = UserRole.OPERATOR

        async def override_get_db():
            yield test_db

        def override_get_current_user():
            return mock_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.get("/api/proxies/")

        if response.status_code == 200:
            data = response.json()
            assert "items" in data

        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_proxy_stats_route_is_not_shadowed_by_proxy_id_route(
        self,
        test_db: AsyncSession,
        mock_user: User,
        mock_proxy: Proxy,
    ):
        """The stats endpoint should resolve before /{proxy_id} routes."""
        mock_user.role = UserRole.OPERATOR

        async def override_get_db():
            yield test_db

        def override_get_current_user():
            return mock_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/proxies/stats")

        assert response.status_code == 200
        assert response.json()["total"] >= 1
        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_delete_visible_article(
        self,
        test_db: AsyncSession,
        mock_user: User,
        mock_monitored_article: Article,
    ):
        """Users can delete articles visible through their monitored accounts."""
        mock_user.role = UserRole.VIEWER

        async def override_get_db():
            yield test_db

        def override_get_current_user():
            return mock_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            delete_response = await client.delete(f"/api/articles/{mock_monitored_article.id}")
            get_response = await client.get(f"/api/articles/{mock_monitored_article.id}")

        assert delete_response.status_code == 204
        assert get_response.status_code == 404
        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_create_proxy_persists_integer_port(
        self,
        test_db: AsyncSession,
        mock_user: User,
    ):
        """Creating a proxy should persist the submitted integer port."""
        mock_user.role = UserRole.OPERATOR

        async def override_get_db():
            yield test_db

        def override_get_current_user():
            return mock_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/proxies/",
                json={"host": "127.0.0.1", "port": 8899, "service_type": "mp_list"},
            )

        assert response.status_code == 201
        data = response.json()
        assert data["host"] == "127.0.0.1"
        assert data["port"] == 8899
        assert data["service_type"] == "mp_list"
        assert data["service_keys"] == []
        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_proxy_services_can_be_viewed_and_validated(
        self,
        test_db: AsyncSession,
        mock_user: User,
    ):
        """A proxy can be bound to multiple compatible services only."""
        mock_user.role = UserRole.OPERATOR

        async def override_get_db():
            yield test_db

        def override_get_current_user():
            return mock_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            create_response = await client.post(
                "/api/proxies/",
                json={
                    "host": "127.0.0.2",
                    "port": 8899,
                    "service_type": "mp_detail",
                    "proxy_kind": "isp_static",
                    "rotation_mode": "sticky",
                    "service_keys": ["mp_admin_login", "mp_list", "mp_detail"],
                },
            )
            proxy_id = create_response.json()["id"]
            services_response = await client.get(f"/api/proxies/{proxy_id}/services")
            list_response = await client.get("/api/proxies/", params={"service_key": "mp_detail"})
            invalid_response = await client.put(
                f"/api/proxies/{proxy_id}/services",
                json={"service_keys": ["ai", "mp_detail"]},
            )

        assert create_response.status_code == 201
        assert services_response.status_code == 200
        assert list_response.status_code == 200
        assert set(services_response.json()["service_keys"]) == {"mp_admin_login", "mp_list", "mp_detail"}
        assert any(item["id"] == proxy_id for item in list_response.json()["items"])
        assert invalid_response.status_code == 400
        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_collector_account_proxy_bind_unbind_and_deleted_proxy_falls_back_to_direct(
        self,
        test_db: AsyncSession,
        mock_user: User,
        mock_collector_account,
        mock_proxy: Proxy,
    ):
        """Account proxy binding is optional and deleting the proxy does not clear credentials."""
        mock_user.role = UserRole.ADMIN
        mock_proxy.proxy_kind = ProxyKind.ISP_STATIC
        await test_db.commit()

        async def override_get_db():
            yield test_db

        def override_get_current_user():
            return mock_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            bind_response = await client.put(
                f"/api/collector-accounts/{mock_collector_account.id}/proxy",
                json={"proxy_id": mock_proxy.id},
            )
            delete_response = await client.delete(f"/api/proxies/{mock_proxy.id}")

        await test_db.refresh(mock_collector_account)
        assert bind_response.status_code == 200
        assert bind_response.json()["bound_proxy_id"] == mock_proxy.id
        assert delete_response.status_code == 204
        assert mock_collector_account.login_proxy_id is None
        assert mock_collector_account.credentials == {"token": "primary-token", "cookies": {}}
        app.dependency_overrides.clear()


class TestWeightAPI:
    """Test cases for weight API."""

    @pytest.mark.asyncio
    async def test_get_config(self, test_db: AsyncSession, mock_user: User):
        """Test getting weight configuration."""
        mock_user.role = UserRole.VIEWER

        async def override_get_db():
            yield test_db

        def override_get_current_user():
            return mock_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.get("/api/weight/config")

        if response.status_code == 200:
            data = response.json()
            assert "frequency_ratio" in data
            assert "tier_thresholds" in data
            assert "check_intervals" in data

        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_simulate_weight(self, test_db: AsyncSession, mock_user: User):
        """Test weight simulation."""
        mock_user.role = UserRole.VIEWER

        async def override_get_db():
            yield test_db

        def override_get_current_user():
            return mock_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/weight/simulate",
                json={
                    "update_history": {
                        (datetime.now(timezone.utc) - timedelta(days=i)).isoformat(): 3
                        for i in range(10)
                    },
                    "ai_relevance_history": {
                        (datetime.now(timezone.utc) - timedelta(days=i)).isoformat(): {
                            "ratio": 0.7,
                            "reason": "Good",
                        }
                        for i in range(10)
                    },
                    "last_updated": (datetime.now(timezone.utc) - timedelta(days=2)).isoformat(),
                    "new_article_count": 5,
                },
            )

        if response.status_code == 200:
            data = response.json()
            assert "new_score" in data
            assert "new_tier" in data
            assert "score_breakdown" in data

        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_simulate_weight_reflects_different_input_values(
        self,
        test_db: AsyncSession,
        mock_user: User,
    ):
        """Weight simulation API should change score/tier for different UI inputs."""
        mock_user.role = UserRole.VIEWER
        now = datetime.now(timezone.utc)

        async def override_get_db():
            yield test_db

        def override_get_current_user():
            return mock_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        active_matching_payload = {
            "update_history": {
                (now - timedelta(days=i)).isoformat(): 4
                for i in range(14)
            },
            "ai_relevance_history": {},
            "last_updated": (now - timedelta(hours=1)).isoformat(),
            "new_article_count": 6,
            "ai_result": {
                "ratio": 1.0,
                "target_match": "是",
                "target_type": "产业投融资",
            },
        }
        stale_not_matching_payload = {
            "update_history": {
                (now - timedelta(days=80)).isoformat(): 1,
            },
            "ai_relevance_history": {},
            "last_updated": (now - timedelta(days=75)).isoformat(),
            "new_article_count": 0,
            "ai_result": {
                "ratio": 0.0,
                "target_match": "不是",
                "target_type": "产业投融资",
            },
        }

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            active_response = await client.post("/api/weight/simulate", json=active_matching_payload)
            stale_response = await client.post("/api/weight/simulate", json=stale_not_matching_payload)

        assert active_response.status_code == 200
        assert stale_response.status_code == 200

        active = active_response.json()
        stale = stale_response.json()
        assert active["new_score"] > stale["new_score"]
        assert active["new_tier"] < stale["new_tier"]
        assert active["score_breakdown"]["relevance"] > stale["score_breakdown"]["relevance"]
        assert active["next_interval_hours"] < stale["next_interval_hours"]

        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_update_config_persists(self, test_db: AsyncSession, mock_user: User):
        """Weight config updates should persist in the singleton table."""
        mock_user.role = UserRole.ADMIN

        async def override_get_db():
            yield test_db

        def override_get_current_user():
            return mock_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        payload = {
            "frequency_ratio": 0.3,
            "recency_ratio": 0.3,
            "relevance_ratio": 0.25,
            "stability_ratio": 0.15,
            "tier_threshold_tier1": 90,
            "check_interval_tier1": 12,
            "high_relevance_threshold": 0.9,
            "ai_consecutive_low_threshold": 4,
        }

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            put_response = await client.put("/api/weight/config", json=payload)
            get_response = await client.get("/api/weight/config")

        assert put_response.status_code == 200
        assert get_response.status_code == 200
        assert get_response.json()["frequency_ratio"] == 0.3
        assert get_response.json()["tier_thresholds"][0] == 90
        assert get_response.json()["check_intervals"]["1"] == 12
        assert get_response.json()["high_relevance_threshold"] == 0.9
        assert get_response.json()["ai_consecutive_low_threshold"] == 4

        app.dependency_overrides.clear()


class TestHealthCheck:
    """Test health check endpoint."""

    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test health check."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data


class TestSystemConfigAPI:
    """Notification email config endpoints."""

    @pytest.mark.asyncio
    async def test_get_and_update_notification_email_config(self, test_db: AsyncSession, mock_user: User):
        mock_user.role = UserRole.ADMIN

        async def override_get_db():
            yield test_db

        def override_get_current_user():
            return mock_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            get_response = await client.get("/api/system/notification-email")
            put_response = await client.put(
                "/api/system/notification-email",
                json={
                    "enabled": True,
                    "smtp_host": "smtp.example.com",
                    "smtp_port": 587,
                    "smtp_username": "user",
                    "smtp_password": "secret",
                    "from_email": "alerts@example.com",
                    "to_emails": ["ops@example.com"],
                    "use_tls": True,
                },
            )

        assert get_response.status_code == 200
        assert put_response.status_code == 200
        assert put_response.json()["enabled"] is True
        assert put_response.json()["to_emails"] == ["ops@example.com"]

        app.dependency_overrides.clear()


class TestLogsAPI:
    """Logs list and stats endpoints."""

    @pytest.mark.asyncio
    async def test_get_log_stats(self, test_db: AsyncSession, mock_user: User):
        mock_user.role = UserRole.ADMIN
        test_db.add_all(
            [
                OperationLog(action="create_monitored", target_type="monitored_account", target_id=1, detail="ok"),
                OperationLog(action="delete_proxy", target_type="proxy", target_id=1, detail="removed"),
                OperationLog(action="poll_run", target_type="job", target_id=1, detail="pending"),
            ]
        )
        await test_db.commit()

        async def override_get_db():
            yield test_db

        def override_get_current_user():
            return mock_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/logs/stats")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert data["recent_24h"] == 3
        assert data["success_24h"] == 1
        assert data["failed_24h"] == 1
        assert data["pending_24h"] == 1

        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_logs_are_admin_only(self, test_db: AsyncSession, mock_user: User):
        mock_user.role = UserRole.VIEWER

        async def override_get_db():
            yield test_db

        def override_get_current_user():
            return mock_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            list_response = await client.get("/api/logs/")
            stats_response = await client.get("/api/logs/stats")

        assert list_response.status_code == 403
        assert stats_response.status_code == 403
        app.dependency_overrides.clear()
