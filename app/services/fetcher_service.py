"""Fetcher service for monitored account updates and article details."""

import asyncio
import ast
import json
import random
import re
from html import unescape
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from urllib.parse import parse_qs, quote, urlparse

import httpx
from bs4 import BeautifulSoup
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import FetchFailedException
from app.models.collector_account import CollectorAccount, CollectorAccountType
from app.models.monitored_account import MonitoredAccount
from app.models.proxy import ServiceType
from app.services.proxy_service import ProxyService
from app.services.system_config_service import SystemConfigService


@dataclass
class ArticleUpdate:
    """Standardized article update metadata."""

    title: str
    url: str
    published_at: str | None
    raw_content: str | None = None
    cover_image: str | None = None
    author: str | None = None
    source_payload: dict[str, Any] | None = None


WECHAT_DESKTOP_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
)

FETCH_CATEGORY_CONFIGURATION = "configuration_error"
FETCH_CATEGORY_CREDENTIALS = "credentials_invalid"
FETCH_CATEGORY_RISK = "risk_control"
FETCH_CATEGORY_TEMPORARY = "temporary_failure"


class BaseChannelFetcher:
    """Base fetcher with helper utilities."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def _sleep_with_policy(self) -> None:
        policy = await SystemConfigService(self.db).get_or_create_fetch_policy()
        delay = random.randint(policy.random_delay_min_ms, policy.random_delay_max_ms) / 1000
        await asyncio.sleep(delay)

    def _build_client(self, proxy_url: str | None) -> httpx.AsyncClient:
        return httpx.AsyncClient(timeout=30.0, proxy=proxy_url, follow_redirects=True)

    def _build_headers(self, referer: str | None = None) -> dict[str, str]:
        headers = {
            "User-Agent": WECHAT_DESKTOP_UA,
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }
        if referer:
            headers["Referer"] = referer
        return headers

    def _classify_http_error(self, status_code: int, body: str | None = None) -> str:
        lowered = (body or "").lower()
        if status_code in {401, 403}:
            if "freq control" in lowered or "risk" in lowered:
                return FETCH_CATEGORY_RISK
            return FETCH_CATEGORY_CREDENTIALS
        if status_code == 429:
            return FETCH_CATEGORY_RISK
        if status_code >= 500:
            return FETCH_CATEGORY_TEMPORARY
        return FETCH_CATEGORY_TEMPORARY

    def _http_error_message(self, status_code: int, category: str) -> str:
        if category == FETCH_CATEGORY_RISK:
            return f"HTTP {status_code}: risk control or rate limited"
        if category == FETCH_CATEGORY_CREDENTIALS:
            return f"HTTP {status_code}: credentials invalid or permission denied"
        return f"HTTP {status_code}: upstream temporary failure"

    def _extract_article_metadata(self, raw_html: str) -> dict[str, Any]:
        soup = BeautifulSoup(raw_html or "", "lxml")
        title = ""
        author = ""
        cover_image = None
        published_at = None

        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            title = og_title["content"].strip()
        if not title:
            title_node = soup.find("h1", id="activity-name") or soup.find("h1", class_="rich_media_title")
            if title_node:
                title = title_node.get_text(" ", strip=True)

        author_node = soup.find(id="js_name") or soup.find("span", class_="rich_media_meta_text")
        if author_node:
            author = author_node.get_text(" ", strip=True)

        og_image = soup.find("meta", property="og:image")
        if og_image and og_image.get("content"):
            cover_image = og_image["content"].strip()

        published_node = soup.find("meta", property="article:published_time")
        if published_node and published_node.get("content"):
            published_at = published_node["content"].strip()

        if not published_at:
            match = re.search(r'var\s+ct\s*=\s*"?(?P<ts>\d{10})"?', raw_html or "")
            if match:
                published_at = datetime.fromtimestamp(int(match.group("ts")), tz=timezone.utc).isoformat()

        return {
            "title": title or None,
            "author": author or None,
            "cover_image": cover_image,
            "published_at": published_at,
        }

    def _extract_embedded_json_candidates(self, raw_html: str, variable_names: list[str]) -> list[dict[str, Any]]:
        candidates: list[dict[str, Any]] = []
        for variable_name in variable_names:
            string_pattern = rf"{re.escape(variable_name)}\s*=\s*(?P<quote>['\"])(?P<payload>(?:\\.|(?! (?P=quote)).)*)?(?P=quote)\s*;"
            object_pattern = rf"{re.escape(variable_name)}\s*=\s*(?P<payload>{{.*?}})\s*;"

            for match in re.finditer(string_pattern.replace(" ", ""), raw_html or "", re.DOTALL):
                payload = match.group("payload") or ""
                try:
                    decoded = ast.literal_eval(f'{match.group("quote")}{payload}{match.group("quote")}')
                    decoded = unescape(decoded)
                    candidates.append(json.loads(decoded))
                except Exception:
                    continue

            for match in re.finditer(object_pattern, raw_html or "", re.DOTALL):
                payload = match.group("payload")
                try:
                    decoded = unescape(payload)
                    candidates.append(json.loads(decoded))
                except Exception:
                    continue
        return candidates

    def _normalize_wechat_url(self, value: str | None, fallback_url: str) -> str:
        if not value:
            return fallback_url
        if value.startswith("//"):
            return f"https:{value}"
        if value.startswith("/"):
            return f"https://mp.weixin.qq.com{value}"
        return value

    def _extract_anchor_updates(self, raw_html: str, fallback_url: str) -> list[ArticleUpdate]:
        soup = BeautifulSoup(raw_html or "", "lxml")
        updates: list[ArticleUpdate] = []
        seen: set[str] = set()
        for anchor in soup.find_all("a", href=True):
            href = self._normalize_wechat_url(anchor.get("href"), fallback_url)
            if "mp.weixin.qq.com" not in href:
                continue
            if "/s/" not in href and "mid=" not in href:
                continue
            if href in seen:
                continue
            seen.add(href)
            title = anchor.get_text(" ", strip=True) or anchor.get("title") or "未命名文章"
            updates.append(
                ArticleUpdate(
                    title=title,
                    url=href,
                    published_at=None,
                    source_payload={"channel": "anchor_fallback"},
                )
            )
        return updates

    async def fetch_updates(
        self,
        monitored_account: MonitoredAccount,
        collector_account: CollectorAccount,
        proxy_url: str | None,
    ) -> list[ArticleUpdate]:
        raise NotImplementedError

    async def fetch_article_detail(
        self,
        url: str,
        collector_account: CollectorAccount,
        proxy_url: str | None,
    ) -> dict[str, Any]:
        await self._sleep_with_policy()
        try:
            async with self._build_client(proxy_url) as client:
                response = await client.get(url, headers=self._build_headers(referer="https://mp.weixin.qq.com/"))
                if response.status_code >= 400:
                    category = self._classify_http_error(response.status_code, response.text)
                    raise FetchFailedException(
                        getattr(collector_account, "id", 0) or 0,
                        self._http_error_message(response.status_code, category),
                        category=category,
                        retryable=category == FETCH_CATEGORY_TEMPORARY,
                    )
                metadata = self._extract_article_metadata(response.text)
                return {"raw_content": response.text, "final_url": str(response.url), **metadata}
        except httpx.RequestError as exc:
            raise FetchFailedException(
                getattr(collector_account, "id", 0) or 0,
                f"Detail request failed: {exc}",
                category=FETCH_CATEGORY_TEMPORARY,
                retryable=True,
            ) from exc


class WeReadFetcher(BaseChannelFetcher):
    """Fetcher for WeRead-based updates."""

    def _build_history_urls(self, monitored_account: MonitoredAccount) -> list[str]:
        urls = [monitored_account.source_url]
        parsed = urlparse(monitored_account.source_url)
        query = parse_qs(parsed.query)
        biz = monitored_account.biz or (query.get("__biz") or query.get("biz") or [None])[0]
        fakeid = monitored_account.fakeid or (query.get("fakeid") or [None])[0]
        if biz:
            urls.append(f"https://mp.weixin.qq.com/mp/profile_ext?action=home&__biz={quote(str(biz))}")
        if fakeid:
            urls.append(f"https://mp.weixin.qq.com/mp/profile_ext?action=home&fakeid={quote(str(fakeid))}")
        # de-duplicate while preserving order
        return list(dict.fromkeys(urls))

    def _parse_wechat_public_page(self, raw_html: str, monitored_account: MonitoredAccount) -> list[ArticleUpdate]:
        updates: list[ArticleUpdate] = []
        seen_urls: set[str] = set()
        json_candidates = self._extract_embedded_json_candidates(raw_html, ["msgList", "general_msg_list"])

        for candidate in json_candidates:
            items = candidate.get("list", [])
            for item in items:
                if item.get("comm_msg_info"):
                    comm_info = item.get("comm_msg_info") or {}
                    ext_info = item.get("app_msg_ext_info") or {}
                    content_url = self._normalize_wechat_url(ext_info.get("content_url"), monitored_account.source_url)
                    if content_url in seen_urls:
                        continue
                    seen_urls.add(content_url)
                    datetime_ts = comm_info.get("datetime")
                    published_at = (
                        datetime.fromtimestamp(int(datetime_ts), tz=timezone.utc).isoformat()
                        if datetime_ts
                        else None
                    )
                    updates.append(
                        ArticleUpdate(
                            title=ext_info.get("title") or monitored_account.name,
                            url=content_url,
                            published_at=published_at,
                            cover_image=ext_info.get("cover"),
                            author=ext_info.get("author"),
                            source_payload=item,
                        )
                    )
                    for child in ext_info.get("multi_app_msg_item_list", []) or []:
                        child_url = self._normalize_wechat_url(child.get("content_url"), monitored_account.source_url)
                        if child_url in seen_urls:
                            continue
                        seen_urls.add(child_url)
                        updates.append(
                            ArticleUpdate(
                                title=child.get("title") or monitored_account.name,
                                url=child_url,
                                published_at=published_at,
                                cover_image=child.get("cover"),
                                author=child.get("author"),
                                source_payload=child,
                            )
                        )

        if updates:
            return updates
        return self._extract_anchor_updates(raw_html, monitored_account.source_url)

    async def fetch_updates(
        self,
        monitored_account: MonitoredAccount,
        collector_account: CollectorAccount,
        proxy_url: str | None,
    ) -> list[ArticleUpdate]:
        await self._sleep_with_policy()
        token = collector_account.credentials.get("token") or collector_account.credentials.get("cookie")
        if not token:
            raise FetchFailedException(
                monitored_account.id,
                "Missing WeRead token",
                category=FETCH_CATEGORY_CONFIGURATION,
                retryable=False,
            )
        headers = self._build_headers(referer="https://mp.weixin.qq.com/")
        cookies = collector_account.credentials.get("cookies") or {}
        urls = self._build_history_urls(monitored_account)
        all_updates: list[ArticleUpdate] = []
        seen_urls: set[str] = set()

        try:
            async with self._build_client(proxy_url) as client:
                for url in urls:
                    response = await client.get(url, headers=headers, cookies=cookies)
                    if response.status_code >= 400:
                        category = self._classify_http_error(response.status_code, response.text)
                        if category != FETCH_CATEGORY_TEMPORARY:
                            raise FetchFailedException(
                                monitored_account.id,
                                f"WeRead list error: {self._http_error_message(response.status_code, category)}",
                                category=category,
                                retryable=False,
                            )
                        continue

                    page_updates = self._parse_wechat_public_page(response.text, monitored_account)
                    for update in page_updates:
                        if update.url in seen_urls:
                            continue
                        seen_urls.add(update.url)
                        update.source_payload = {
                            "channel": "weread",
                            "seed_url": url,
                            **(update.source_payload or {}),
                        }
                        all_updates.append(update)
                    if all_updates:
                        break
        except httpx.RequestError as exc:
            raise FetchFailedException(
                monitored_account.id,
                f"WeRead list request failed: {exc}",
                category=FETCH_CATEGORY_TEMPORARY,
                retryable=True,
            ) from exc

        if all_updates:
            return all_updates

        return [
            ArticleUpdate(
                title=f"{monitored_account.name} 最新文章",
                url=monitored_account.source_url,
                published_at=datetime.now(timezone.utc).isoformat(),
                source_payload={"channel": "weread_fallback", "biz": monitored_account.biz},
            )
        ]


class MpAdminFetcher(BaseChannelFetcher):
    """Fetcher for MP admin update list."""

    def _normalize_link(self, value: str | None, monitored_account: MonitoredAccount) -> str:
        if not value:
            return monitored_account.source_url
        if value.startswith("//"):
            return f"https:{value}"
        return value

    def _parse_appmsg_page(self, payload: dict[str, Any], monitored_account: MonitoredAccount) -> list[ArticleUpdate]:
        app_msg_list = payload.get("app_msg_list", []) or []
        updates = []
        for item in app_msg_list:
            updates.append(
                ArticleUpdate(
                    title=item.get("title") or monitored_account.name,
                    url=self._normalize_link(item.get("link"), monitored_account),
                    published_at=item.get("update_time"),
                    cover_image=item.get("cover"),
                    author=item.get("author"),
                    source_payload=item,
                )
            )
        return updates

    async def fetch_updates(
        self,
        monitored_account: MonitoredAccount,
        collector_account: CollectorAccount,
        proxy_url: str | None,
    ) -> list[ArticleUpdate]:
        await self._sleep_with_policy()
        cookies = collector_account.credentials.get("cookies") or collector_account.credentials
        token = collector_account.credentials.get("token")
        if not monitored_account.fakeid:
            raise FetchFailedException(
                monitored_account.id,
                "Missing fakeid",
                category=FETCH_CATEGORY_CONFIGURATION,
                retryable=False,
            )
        if not cookies:
            raise FetchFailedException(
                monitored_account.id,
                "Missing MP admin cookies",
                category=FETCH_CATEGORY_CREDENTIALS,
                retryable=False,
            )

        max_pages = int((monitored_account.strategy_config or {}).get("mp_max_pages", 3))
        page_size = int((monitored_account.strategy_config or {}).get("mp_page_size", 5))
        all_updates: list[ArticleUpdate] = []
        seen_urls: set[str] = set()

        async with self._build_client(proxy_url) as client:
            for page in range(max_pages):
                begin = page * page_size
                try:
                    response = await client.get(
                        "https://mp.weixin.qq.com/cgi-bin/appmsg",
                        params={
                            "action": "list_ex",
                            "fakeid": monitored_account.fakeid,
                            "token": token or "",
                            "lang": "zh_CN",
                            "f": "json",
                            "count": page_size,
                            "begin": begin,
                        },
                        cookies=cookies,
                        headers=self._build_headers(referer="https://mp.weixin.qq.com/"),
                    )
                except httpx.RequestError as exc:
                    raise FetchFailedException(
                        monitored_account.id,
                        f"MP list request failed: {exc}",
                        category=FETCH_CATEGORY_TEMPORARY,
                        retryable=True,
                    ) from exc
                if response.status_code >= 400:
                    category = self._classify_http_error(response.status_code, response.text)
                    reason = self._http_error_message(response.status_code, category)
                    raise FetchFailedException(
                        monitored_account.id,
                        f"MP list error: {reason}",
                        category=category,
                        retryable=category == FETCH_CATEGORY_TEMPORARY,
                    )

                data = response.json()
                if data.get("base_resp", {}).get("ret") not in {None, 0}:
                    error_msg = data.get("base_resp", {}).get("errmsg") or "mp appmsg api failed"
                    lowered = error_msg.lower()
                    category = FETCH_CATEGORY_TEMPORARY
                    if "freq control" in lowered or "risk" in lowered:
                        category = FETCH_CATEGORY_RISK
                    elif "invalid" in lowered or "expired" in lowered or "login" in lowered or "token" in lowered:
                        category = FETCH_CATEGORY_CREDENTIALS
                    raise FetchFailedException(
                        monitored_account.id,
                        error_msg,
                        category=category,
                        retryable=category == FETCH_CATEGORY_TEMPORARY,
                    )

                page_updates = self._parse_appmsg_page(data, monitored_account)
                if not page_updates:
                    break

                new_count = 0
                for update in page_updates:
                    if update.url in seen_urls:
                        continue
                    seen_urls.add(update.url)
                    all_updates.append(update)
                    new_count += 1

                can_continue = bool(data.get("can_msg_continue"))
                if new_count == 0 or not can_continue:
                    break

        if not all_updates:
            return [
                ArticleUpdate(
                    title=f"{monitored_account.name} 首篇文章",
                    url=monitored_account.source_url,
                    published_at=datetime.now(timezone.utc).isoformat(),
                    source_payload={"channel": "mp_admin_fallback"},
                )
            ]

        return all_updates


class FetcherService:
    """Coordinate fetchers, proxy selection, and detail requests."""

    def __init__(self, db: AsyncSession, proxy_service: ProxyService | None = None, mock_mode: bool = False):
        self.db = db
        self.proxy_service = proxy_service or ProxyService(db)
        self.weread_fetcher = WeReadFetcher(db)
        self.mp_fetcher = MpAdminFetcher(db)
        self.mock_mode = mock_mode

    async def get_proxy_for_mode(self, mode: CollectorAccountType) -> str | None:
        mapping = {
            CollectorAccountType.WEREAD: ServiceType.WEREAD_LIST,
            CollectorAccountType.MP_ADMIN: ServiceType.MP_LIST,
        }
        try:
            proxy_model = await self.proxy_service.get_proxy_for_service(mapping[mode])
        except Exception:
            return None
        return proxy_model.proxy_url

    async def get_detail_proxy_for_mode(self, mode: CollectorAccountType) -> str | None:
        mapping = {
            CollectorAccountType.WEREAD: ServiceType.WEREAD_DETAIL,
            CollectorAccountType.MP_ADMIN: ServiceType.MP_DETAIL,
        }
        try:
            proxy_model = await self.proxy_service.get_proxy_for_service(mapping[mode])
        except Exception:
            return None
        return proxy_model.proxy_url

    async def fetch_updates(
        self,
        monitored_account: MonitoredAccount,
        collector_account: CollectorAccount,
    ) -> list[ArticleUpdate]:
        if self.mock_mode:
            return [
                ArticleUpdate(
                    title=f"Mock {monitored_account.name}",
                    url=monitored_account.source_url,
                    published_at=datetime.now(timezone.utc).isoformat(),
                    raw_content=f"<html><body><h1>{monitored_account.name}</h1><p>mock content</p></body></html>",
                )
            ]
        proxy_url = await self.get_proxy_for_mode(collector_account.account_type)
        if collector_account.account_type == CollectorAccountType.WEREAD:
            return await self.weread_fetcher.fetch_updates(monitored_account, collector_account, proxy_url)
        return await self.mp_fetcher.fetch_updates(monitored_account, collector_account, proxy_url)

    async def fetch_article_detail(
        self,
        url: str,
        collector_account: CollectorAccount,
    ) -> dict[str, Any]:
        if self.mock_mode:
            return {"raw_content": f"<html><body><h1>Mock detail</h1><p>{url}</p></body></html>", "final_url": url}
        proxy_url = await self.get_detail_proxy_for_mode(collector_account.account_type)
        if collector_account.account_type == CollectorAccountType.WEREAD:
            return await self.weread_fetcher.fetch_article_detail(url, collector_account, proxy_url)
        return await self.mp_fetcher.fetch_article_detail(url, collector_account, proxy_url)

    async def fetch_new_articles(self, account) -> list[dict[str, Any]]:
        """Backward-compatible wrapper for legacy tests/services."""
        mode = CollectorAccountType.WEREAD if getattr(account, "current_tier", 3) <= 2 else CollectorAccountType.MP_ADMIN
        collector_stub = CollectorAccount(
            owner_user_id=getattr(account, "id", 0) or 0,
            account_type=mode,
            display_name=getattr(account, "name", "legacy"),
            credentials={"token": "mock", "cookies": getattr(account, "cookies", {}) or {}},
        )
        monitored_stub = MonitoredAccount(
            owner_user_id=getattr(account, "id", 0) or 0,
            biz=getattr(account, "biz", "legacy_biz"),
            fakeid=getattr(account, "fakeid", None),
            name=getattr(account, "name", "legacy"),
            source_url=f"https://mp.weixin.qq.com/s/{getattr(account, 'biz', 'legacy')}",
            current_tier=getattr(account, "current_tier", 3),
            composite_score=getattr(account, "composite_score", 50.0),
            primary_fetch_mode=mode,
            fallback_fetch_mode=CollectorAccountType.WEREAD if mode == CollectorAccountType.MP_ADMIN else CollectorAccountType.MP_ADMIN,
            strategy_config={},
            update_history=getattr(account, "update_history", {}) or {},
            ai_relevance_history=getattr(account, "ai_relevance_history", {}) or {},
        )
        updates = await self.fetch_updates(monitored_stub, collector_stub)
        return [
            {
                "title": item.title,
                "url": item.url,
                "published_at": item.published_at,
                "raw_content": item.raw_content,
            }
            for item in updates
        ]

    async def test_fetch_connection(self, account) -> dict[str, Any]:
        try:
            articles = await self.fetch_new_articles(account)
            return {
                "success": True,
                "backend_used": "weread" if getattr(account, "current_tier", 3) <= 2 else "mp",
                "article_count": len(articles),
                "error": None,
            }
        except Exception as exc:
            return {
                "success": False,
                "backend_used": "weread" if getattr(account, "current_tier", 3) <= 2 else "mp",
                "article_count": 0,
                "error": str(exc),
            }
