"""Tests for feed, rich content, image proxy, and cooldown additions."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
import httpx
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.image import _validate_image_url
from app.core.dependencies import get_current_user
from app.main import app
from app.models.fetch_job import FetchJobType
from app.models.proxy import Proxy, ProxyServiceKey, ServiceType
from app.models.user import UserRole
from app.services.monitoring_source_service import MonitoringSourceService
from app.services.parser_service import ParserService
from app.services.proxy_service import ProxyService


@pytest.mark.asyncio
async def test_parser_preserves_sanitized_rich_html_and_image_order():
    html = """
    <html><body>
      <h1 id="activity-name">标题</h1>
      <div id="js_content">
        <script>alert(1)</script>
        <p onclick="bad()">第一段</p>
        <img data-src="//mmbiz.qpic.cn/sz_mmbiz_jpg/a/1.jpg" />
        <mpvoice></mpvoice>
        <img src="https://mmbiz.qpic.cn/mmbiz_png/a/2.png" />
      </div>
    </body></html>
    """

    parsed = await ParserService().parse_article(html, download_images=False)

    assert parsed.title == "标题"
    assert parsed.content_type == "audio"
    assert parsed.original_images == [
        "https://mmbiz.qpic.cn/sz_mmbiz_jpg/a/1.jpg",
        "https://mmbiz.qpic.cn/mmbiz_png/a/2.png",
    ]
    assert "<script" not in (parsed.content_html or "")
    assert "onclick" not in (parsed.content_html or "")
    assert "wechat-audio-placeholder" in (parsed.content_html or "")


@pytest.mark.asyncio
async def test_parser_ignores_global_wechat_voice_script_when_classifying_article():
    html = """
    <html><body>
      <h1 id="activity-name">普通图文</h1>
      <script>var voice_encode_fileid = "";</script>
      <div id="js_content">
        <p>这是一篇普通图文正文，页面全局脚本不应该把它识别为音频。</p>
        <p>正文长度足够用于普通文章分类。</p>
      </div>
    </body></html>
    """

    parsed = await ParserService().parse_article(html, download_images=False)

    assert parsed.content_type == "article"


@pytest.mark.asyncio
async def test_parser_removes_hidden_wechat_content_style_from_rich_html():
    html = """
    <html><body>
      <h1 id="activity-name">可见图文</h1>
      <div id="js_content" style="visibility: hidden; opacity: 0;">
        <section style="margin-bottom: 12px; visibility: hidden;">
          <span>富文本预览应该可见</span>
        </section>
      </div>
    </body></html>
    """

    parsed = await ParserService().parse_article(html, download_images=False)

    assert "visibility" not in (parsed.content_html or "")
    assert "opacity" not in (parsed.content_html or "")
    assert "富文本预览应该可见" in (parsed.content_html or "")


@pytest.mark.asyncio
async def test_monitored_source_does_not_generate_fake_fakeid(test_db: AsyncSession, mock_user):
    service = MonitoringSourceService(test_db)

    with patch.object(service, "resolve_with_weread_platform", new=AsyncMock(return_value={})):
        account, created = await service.create_from_url(
            owner_user_id=mock_user.id,
            source_url="https://mp.weixin.qq.com/s?__biz=MzA_testbiz&mid=1",
            name=None,
            fakeid=None,
        )

    assert created is True
    assert account.fakeid is None
    assert account.strategy_config["capabilities"]["list_fetch"] is False
    assert account.feed_token


@pytest.mark.asyncio
async def test_public_feeds_rss_json_and_export(test_db: AsyncSession, mock_user, mock_account, mock_article):
    mock_article.content_html = "<p>完整正文<img src=\"https://mmbiz.qpic.cn/a.jpg\" /></p>"
    mock_article.original_images = ["https://mmbiz.qpic.cn/a.jpg"]
    await test_db.commit()
    await test_db.refresh(mock_article)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        rss = await client.get(f"/feeds/{mock_account.feed_token}.rss", params={"mode": "fulltext"})
        json_feed = await client.get(f"/feeds/{mock_account.feed_token}.json")

    assert rss.status_code == 200
    assert "Test Article" in rss.text
    assert "/api/image?url=" in rss.text
    assert json_feed.status_code == 200
    assert json_feed.json()["items"][0]["title"] == "Test Article"

    def override_get_current_user():
        return mock_user

    app.dependency_overrides[get_current_user] = override_get_current_user
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/feeds/export", params={"format": "opml"})
    app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 200
    assert "outline" in response.text
    assert mock_account.feed_token in response.text


def test_image_proxy_rejects_non_wechat_hosts():
    with pytest.raises(Exception):
        _validate_image_url("file:///etc/passwd")
    with pytest.raises(Exception):
        _validate_image_url("https://example.com/a.png")


@pytest.mark.asyncio
async def test_proxy_failure_sets_cooldown_and_pool_skips_it(test_db: AsyncSession):
    proxy = Proxy(
        host="127.0.0.1",
        port=8888,
        service_type=ServiceType.MP_DETAIL,
        success_rate=80.0,
        is_active=True,
    )
    test_db.add(proxy)
    await test_db.commit()
    await test_db.refresh(proxy)

    service = ProxyService(test_db)
    await service.replace_service_bindings(proxy, [ProxyServiceKey.MP_DETAIL])
    await service.mark_proxy_failure(proxy, "captcha", cooldown_seconds=60)
    await test_db.refresh(proxy)

    assert proxy.fail_until is not None
    assert proxy.last_error == "captcha"
    pool = await service.get_proxy_pool_for_service(ServiceType.MP_DETAIL)
    assert proxy not in pool

    proxy.fail_until = datetime.now(timezone.utc) - timedelta(seconds=1)
    await test_db.commit()
    pool = await service.get_proxy_pool_for_service(ServiceType.MP_DETAIL)
    assert proxy in pool


@pytest.mark.asyncio
async def test_history_backfill_endpoint_returns_existing_job(test_db: AsyncSession, mock_user, mock_account):
    from app.services.fetch_job_service import FetchJobService

    mock_user.role = UserRole.ADMIN
    job = await FetchJobService(test_db).create_job(mock_account.id, FetchJobType.HISTORY_BACKFILL)

    def override_get_current_user():
        return mock_user

    app.dependency_overrides[get_current_user] = override_get_current_user
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(f"/api/monitored-accounts/{mock_account.id}/history-backfill")
    app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 200
    assert response.json()["status"] == "already_running"
    assert response.json()["job_id"] == job.id


def test_mp_admin_login_helpers_parse_redirect_token_and_searchbiz_payload():
    from app.services.qr_providers import MpAdminQRProvider

    provider = MpAdminQRProvider()
    response = httpx.Response(
        200,
        request=httpx.Request("POST", "https://mp.weixin.qq.com/cgi-bin/bizlogin"),
        text='{"redirect_url":"/cgi-bin/home?t=home/index&token=abc123&lang=zh_CN"}',
    )
    token = provider._extract_token_from_login_response(
        response,
        {"redirect_url": "/cgi-bin/home?t=home/index&token=abc123&lang=zh_CN"},
    )
    parsed = provider._parse_searchbiz_response(
        {
            "list": [
                {
                    "fakeid": "fakeid_123",
                    "nickname": "测试公众号",
                    "round_head_img": "https://mmbiz.qpic.cn/avatar.jpg",
                }
            ]
        }
    )

    assert token == "abc123"
    assert parsed["fakeid"] == "fakeid_123"
    assert parsed["nickname"] == "测试公众号"


@pytest.mark.asyncio
async def test_system_rate_limit_and_notification_policy_endpoints(test_db: AsyncSession, mock_user):
    mock_user.role = UserRole.ADMIN

    def override_get_current_user():
        return mock_user

    app.dependency_overrides[get_current_user] = override_get_current_user
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        rate_response = await client.put(
            "/api/system/rate-limit-policy",
            json={
                "global_limit_per_minute": 12,
                "account_limit_per_minute": 5,
                "proxy_limit_per_minute": 7,
                "monitored_limit_per_minute": 8,
                "detail_min_interval_seconds": 1.5,
                "proxy_failure_cooldown_seconds": 90,
            },
        )
        notification_response = await client.put(
            "/api/system/notification-policy",
            json={
                "credential_check_interval_hours": 6,
                "expiring_notice_hours": [24, 6],
                "webhook_enabled": True,
                "webhook_url": "https://example.com/webhook",
            },
        )
    app.dependency_overrides.pop(get_current_user, None)

    assert rate_response.status_code == 200
    assert rate_response.json()["global_limit_per_minute"] == 12
    assert notification_response.status_code == 200
    assert notification_response.json()["webhook_enabled"] is True


@pytest.mark.asyncio
async def test_proxy_bulk_import_endpoint(test_db: AsyncSession, mock_user):
    mock_user.role = UserRole.ADMIN

    def override_get_current_user():
        return mock_user

    app.dependency_overrides[get_current_user] = override_get_current_user
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/proxies/bulk",
            json={
                "proxies": [
                    {"host": "127.0.0.10", "port": 8001, "service_type": "mp_list"},
                    {"host": "socks5://127.0.0.11", "port": 1080, "service_type": "mp_detail"},
                ]
            },
        )
    app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 201
    assert response.json()["created"] == 2
    assert response.json()["items"][1]["service_type"] == "mp_detail"


@pytest.mark.asyncio
async def test_history_backfill_status_and_stop(test_db: AsyncSession, mock_user, mock_account):
    from app.services.fetch_job_service import FetchJobService

    mock_user.role = UserRole.ADMIN
    service = FetchJobService(test_db)
    job = await service.create_job(mock_account.id, FetchJobType.HISTORY_BACKFILL)
    await service.mark_running(job, payload={"stage": "history_backfill", "page": 2, "saved_count": 3})

    def override_get_current_user():
        return mock_user

    app.dependency_overrides[get_current_user] = override_get_current_user
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        status_response = await client.get(f"/api/monitored-accounts/{mock_account.id}/history-backfill/status")
        stop_response = await client.post(f"/api/monitored-accounts/{mock_account.id}/history-backfill/stop")
    app.dependency_overrides.pop(get_current_user, None)

    assert status_response.status_code == 200
    assert status_response.json()["payload"]["page"] == 2
    assert stop_response.status_code == 200
    assert stop_response.json()["status"] == "stopped"
