"""Fetcher service for monitored account updates and article details."""

import asyncio
import ast
import json
import random
import re
from concurrent.futures import ThreadPoolExecutor
from html import unescape
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from urllib.parse import parse_qs, parse_qsl, quote, urlencode, urlparse, urlunparse

import httpx
from bs4 import BeautifulSoup
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import FetchFailedException, ProxyNotAvailableException
from app.models.collector_account import CollectorAccount, CollectorAccountType
from app.models.monitored_account import MonitoredAccount
from app.models.proxy import Proxy, ProxyServiceKey
from app.services.proxy_service import ProxyService
from app.services.rate_limit_service import rate_limit_service
from app.services.system_config_service import SystemConfigService

try:
    from curl_cffi.requests import Session as CurlSession

    HAS_CURL_CFFI = True
except Exception:  # pragma: no cover - exercised only when optional dependency is absent
    CurlSession = None
    HAS_CURL_CFFI = False


settings = get_settings()


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


@dataclass
class DetailDocumentResponse:
    """HTTP response data needed by article detail parsing."""

    status_code: int
    text: str
    final_url: str
    headers: dict[str, str]


WECHAT_DESKTOP_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
)
DETAIL_FETCH_EXECUTOR = ThreadPoolExecutor(max_workers=4)

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

    def _build_document_headers(self, collector_account: CollectorAccount) -> dict[str, str]:
        """Build browser-like headers for WeChat article HTML downloads."""
        headers = {
            "User-Agent": WECHAT_DESKTOP_UA,
            "Accept": (
                "text/html,application/xhtml+xml,application/xml;q=0.9,"
                "image/avif,image/webp,image/apng,*/*;q=0.8"
            ),
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Referer": "https://mp.weixin.qq.com/",
            "Sec-Ch-Ua": '"Chromium";v="123", "Google Chrome";v="123", "Not:A-Brand";v="8"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"macOS"',
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1",
        }
        cookie_header = self._credentials_cookie_header(collector_account)
        if cookie_header:
            headers["Cookie"] = cookie_header
        return headers

    def _credentials_cookie_header(self, collector_account: CollectorAccount) -> str | None:
        credentials = collector_account.credentials or {}
        if isinstance(credentials.get("cookie"), str):
            return credentials["cookie"]
        cookies = credentials.get("cookies")
        if isinstance(cookies, dict) and cookies:
            return "; ".join(f"{key}={value}" for key, value in cookies.items())
        return None

    def _append_credential_token(self, url: str, collector_account: CollectorAccount) -> str:
        if collector_account.account_type != CollectorAccountType.MP_ADMIN:
            return url
        token = (collector_account.credentials or {}).get("token")
        if not token or "token=" in url:
            return url
        parsed = urlparse(url)
        query = parse_qsl(parsed.query, keep_blank_values=True)
        query.append(("token", str(token)))
        return urlunparse(parsed._replace(query=urlencode(query)))

    async def _detail_proxy_candidates(
        self,
        collector_account: CollectorAccount,
        proxy_url: str | None,
    ) -> list[tuple[Proxy | None, str | None]]:
        if proxy_url:
            return [(None, proxy_url), (None, None)]
        service_type = {
            CollectorAccountType.WEREAD: ProxyServiceKey.WEREAD_DETAIL,
            CollectorAccountType.MP_ADMIN: ProxyServiceKey.MP_DETAIL,
        }.get(collector_account.account_type, ProxyServiceKey.MP_DETAIL)
        proxies = await ProxyService(self.db).get_proxy_pool_for_service_key(service_type)
        if not proxies:
            return [(None, None)]
        candidates: list[tuple[Proxy | None, str | None]] = [(proxy, proxy.proxy_url) for proxy in proxies]
        candidates.append((None, None))
        return candidates

    async def _fetch_document_with_httpx(
        self,
        url: str,
        headers: dict[str, str],
        proxy_url: str | None,
    ) -> DetailDocumentResponse:
        timeout = httpx.Timeout(20.0, read=10.0)
        async with httpx.AsyncClient(timeout=timeout, proxy=proxy_url, follow_redirects=True) as client:
            response = await client.get(url, headers=headers)
            return DetailDocumentResponse(
                status_code=response.status_code,
                text=response.text,
                final_url=str(response.url),
                headers={key.lower(): value for key, value in response.headers.items()},
            )

    async def _fetch_document(
        self,
        url: str,
        headers: dict[str, str],
        proxy_url: str | None,
        prefer_curl: bool = True,
    ) -> DetailDocumentResponse:
        if prefer_curl and HAS_CURL_CFFI:
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(
                DETAIL_FETCH_EXECUTOR,
                self._fetch_document_with_curl,
                url,
                headers,
                proxy_url,
            )

        return await self._fetch_document_with_httpx(url, headers, proxy_url)

    def _fetch_document_with_curl(
        self,
        url: str,
        headers: dict[str, str],
        proxy_url: str | None,
    ) -> DetailDocumentResponse:
        if CurlSession is None:
            raise RuntimeError("curl_cffi is not available")
        kwargs: dict[str, Any] = {
            "timeout": 30,
            "allow_redirects": True,
        }
        if proxy_url:
            kwargs["proxy"] = proxy_url
        with CurlSession(impersonate="chrome120") as session:
            response = session.get(url, headers=headers, **kwargs)
            return DetailDocumentResponse(
                status_code=response.status_code,
                text=response.text,
                final_url=str(response.url),
                headers={key.lower(): value for key, value in response.headers.items()},
            )

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

    def _is_wechat_risk_page(self, final_url: str, raw_html: str | None) -> bool:
        lowered_url = (final_url or "").lower()
        lowered_body = (raw_html or "").lower()
        risk_markers = [
            "wappoc_appmsgcaptcha",
            "poc_token",
            "mmlas-verifyresult",
            "安全验证",
            "环境异常",
        ]
        return any(marker.lower() in lowered_url or marker.lower() in lowered_body for marker in risk_markers)

    def _has_wechat_article_content(self, raw_html: str | None) -> bool:
        if not raw_html:
            return False
        soup = BeautifulSoup(raw_html, "lxml")
        if soup.find(id="js_content") or soup.find(id="activity-name"):
            return True
        if soup.find("meta", property="og:title") and soup.find("meta", property="og:image"):
            return True
        return bool(soup.find(class_="rich_media_content") or soup.find(class_="rich_media_title"))

    def _classify_non_article_response(self, response: DetailDocumentResponse) -> tuple[str, bool, str]:
        final_url = (response.final_url or "").lower()
        body = (response.text or "").lower()
        if "login" in final_url or "请使用微信扫描二维码登录" in response.text or "login_container" in body:
            return FETCH_CATEGORY_CREDENTIALS, False, "login_required"
        if "mp.weixin.qq.com/s/" not in final_url and "mp.weixin.qq.com" in final_url:
            return FETCH_CATEGORY_TEMPORARY, True, "redirect_page"
        if any(marker in body for marker in ["该内容已被发布者删除", "内容不存在", "已被删除"]):
            return "permanently_unavailable", False, "permanently_unavailable"
        return FETCH_CATEGORY_TEMPORARY, True, "empty_or_blocked"

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
        policy = await SystemConfigService(self.db).get_or_create_fetch_policy()
        rate_limit_service.configure(policy.rate_limit_policy or {})
        account_key = str(getattr(collector_account, "id", "") or collector_account.account_type.value)
        can_request, reason = await rate_limit_service.can_request_async(account_key)
        if not can_request and reason == "detail_min_interval":
            await asyncio.sleep(rate_limit_service.detail_min_interval_seconds)
        elif not can_request:
            raise FetchFailedException(
                getattr(collector_account, "id", 0) or 0,
                f"Rate limited: {reason}",
                category=FETCH_CATEGORY_RISK,
                retryable=True,
            )
        await rate_limit_service.mark_detail_request_async(account_key)
        await self._sleep_with_policy()
        full_url = self._append_credential_token(url, collector_account)
        headers = self._build_document_headers(collector_account)
        last_error: Exception | None = None

        for proxy_model, candidate_proxy_url in await self._detail_proxy_candidates(collector_account, proxy_url):
            try:
                response = await self._fetch_document(
                    full_url,
                    headers,
                    candidate_proxy_url,
                    prefer_curl=collector_account.account_type != CollectorAccountType.WEREAD,
                )
                if response.status_code >= 400:
                    category = self._classify_http_error(response.status_code, response.text)
                    raise FetchFailedException(
                        getattr(collector_account, "id", 0) or 0,
                        self._http_error_message(response.status_code, category),
                        category=category,
                        retryable=category == FETCH_CATEGORY_TEMPORARY,
                    )
                if self._is_wechat_risk_page(response.final_url, response.text):
                    raise FetchFailedException(
                        getattr(collector_account, "id", 0) or 0,
                        "WeChat risk control or captcha page returned instead of article content",
                        category=FETCH_CATEGORY_RISK,
                        retryable=False,
                    )
                if not self._has_wechat_article_content(response.text):
                    category, retryable, label = self._classify_non_article_response(response)
                    raise FetchFailedException(
                        getattr(collector_account, "id", 0) or 0,
                        f"WeChat response did not contain article content: {label}",
                        category=category,
                        retryable=retryable,
                    )

                if proxy_model is not None:
                    await ProxyService(self.db).mark_proxy_success(proxy_model)
                metadata = self._extract_article_metadata(response.text)
                return {"raw_content": response.text, "final_url": response.final_url, "fetch_category": "article_ok", **metadata}
            except FetchFailedException as exc:
                last_error = exc
                if proxy_model is not None:
                    cooldown = int((policy.rate_limit_policy or {}).get("proxy_failure_cooldown_seconds", 120))
                    await ProxyService(self.db).mark_proxy_failure(proxy_model, str(exc), cooldown_seconds=cooldown)
                if exc.details.get("category") == FETCH_CATEGORY_CREDENTIALS:
                    raise
            except Exception as exc:
                last_error = exc
                if proxy_model is not None:
                    cooldown = int((policy.rate_limit_policy or {}).get("proxy_failure_cooldown_seconds", 120))
                    await ProxyService(self.db).mark_proxy_failure(proxy_model, str(exc), cooldown_seconds=cooldown)

        if isinstance(last_error, FetchFailedException):
            raise last_error
        raise FetchFailedException(
            getattr(collector_account, "id", 0) or 0,
            f"Detail request failed: {last_error}",
            category=FETCH_CATEGORY_TEMPORARY,
            retryable=True,
        )


class WeReadFetcher(BaseChannelFetcher):
    """Fetcher for WeRead-based updates."""

    def _platform_mp_id(self, monitored_account: MonitoredAccount) -> str | None:
        metadata = monitored_account.metadata_json or {}
        platform_id = metadata.get("weread_platform_mp_id") if isinstance(metadata, dict) else None
        if platform_id:
            return str(platform_id)
        raw = metadata.get("raw") if isinstance(metadata, dict) else None
        if isinstance(raw, dict):
            for container in [raw, raw.get("weread_platform") if isinstance(raw.get("weread_platform"), dict) else None]:
                if not isinstance(container, dict):
                    continue
                for key in ["id", "mpId", "mp_id", "fakeid", "fakeId", "biz", "__biz"]:
                    value = container.get(key)
                    if value:
                        return str(value)
        return monitored_account.fakeid or monitored_account.biz

    def _parse_platform_articles(self, payload: Any, monitored_account: MonitoredAccount) -> list[ArticleUpdate]:
        if isinstance(payload, dict) and isinstance(payload.get("data"), (dict, list)):
            payload = payload["data"]
        if isinstance(payload, dict):
            items = payload.get("articles") or payload.get("items") or payload.get("list") or []
        else:
            items = payload if isinstance(payload, list) else []
        updates: list[ArticleUpdate] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            url = (
                item.get("url")
                or item.get("link")
                or item.get("content_url")
                or item.get("contentUrl")
                or monitored_account.source_url
            )
            updates.append(
                ArticleUpdate(
                    title=item.get("title") or monitored_account.name,
                    url=self._normalize_wechat_url(url, monitored_account.source_url),
                    published_at=(
                        item.get("published_at")
                        or item.get("publish_time")
                        or item.get("publishTime")
                        or item.get("update_time")
                        or item.get("updateTime")
                    ),
                    cover_image=(
                        item.get("cover")
                        or item.get("cover_image")
                        or item.get("pic_url")
                        or item.get("picUrl")
                    ),
                    author=item.get("author") or item.get("source"),
                    source_payload={"channel": "weread_platform", **item},
                )
            )
        return updates

    def _platform_auth_headers(self, collector_account: CollectorAccount, base_url: str) -> dict[str, str]:
        headers = self._build_headers(referer=base_url)
        token = (collector_account.credentials or {}).get("token")
        if token:
            headers["Authorization"] = f"Bearer {token}"
        xid = (collector_account.credentials or {}).get("vid") or collector_account.external_id
        if xid:
            headers["xid"] = str(xid)
        return headers

    def _extract_platform_mp_id(self, payload: Any) -> str | None:
        if isinstance(payload, dict) and isinstance(payload.get("data"), (dict, list)):
            payload = payload["data"]
        if isinstance(payload, list):
            payload = payload[0] if payload else {}
        if isinstance(payload, dict) and isinstance(payload.get("list"), list):
            payload = payload["list"][0] if payload["list"] else {}
        if not isinstance(payload, dict):
            return None
        value = (
            payload.get("id")
            or payload.get("mpId")
            or payload.get("mp_id")
            or payload.get("fakeid")
            or payload.get("fakeId")
            or payload.get("biz")
            or payload.get("__biz")
        )
        return str(value) if value else None

    async def _fetch_platform_articles(
        self,
        monitored_account: MonitoredAccount,
        collector_account: CollectorAccount,
        proxy_url: str | None,
    ) -> list[ArticleUpdate]:
        base_url = (
            (collector_account.metadata_json or {}).get("platform_url")
            or ""
        ).rstrip("/")
        if not base_url and (collector_account.metadata_json or {}).get("provider") == "weread_platform":
            base_url = (settings.weread_platform_url or "").rstrip("/")
        mp_id = self._platform_mp_id(monitored_account)
        token = (collector_account.credentials or {}).get("token")
        if not base_url or not mp_id or not token:
            if not base_url or not token:
                return []
        headers = self._platform_auth_headers(collector_account, base_url)
        async with self._build_client(proxy_url) as client:
            if not mp_id:
                resolve_response = await client.post(
                    f"{base_url}/api/v2/platform/wxs2mp",
                    json={"url": monitored_account.source_url},
                    headers=headers,
                )
                if resolve_response.status_code in {401, 403}:
                    raise FetchFailedException(
                        monitored_account.id,
                        "WeRead platform token is invalid",
                        category=FETCH_CATEGORY_CREDENTIALS,
                        retryable=False,
                    )
                if resolve_response.status_code >= 400:
                    return []
                mp_id = self._extract_platform_mp_id(resolve_response.json())
                if not mp_id:
                    return []
            response = await client.get(
                f"{base_url}/api/v2/platform/mps/{mp_id}/articles",
                params={"page": int((monitored_account.strategy_config or {}).get("weread_page", 1))},
                headers=headers,
            )
            if response.status_code in {401, 403}:
                raise FetchFailedException(
                    monitored_account.id,
                    "WeRead platform token is invalid",
                    category=FETCH_CATEGORY_CREDENTIALS,
                    retryable=False,
                )
            if response.status_code == 429:
                raise FetchFailedException(
                    monitored_account.id,
                    "WeRead platform rate limited",
                    category=FETCH_CATEGORY_RISK,
                    retryable=True,
                )
            if response.status_code >= 400:
                return []
            updates = self._parse_platform_articles(response.json(), monitored_account)
            max_items = int((monitored_account.strategy_config or {}).get("weread_max_items", 1))
            return updates[:max(max_items, 1)]

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

    def _is_source_article_url(self, source_url: str) -> bool:
        parsed = urlparse(source_url)
        if "mp.weixin.qq.com" not in parsed.netloc:
            return False
        query = parse_qs(parsed.query)
        return parsed.path.startswith("/s/") or bool(query.get("mid") and query.get("sn"))

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
            platform_updates = await self._fetch_platform_articles(monitored_account, collector_account, proxy_url)
            if platform_updates:
                return platform_updates
            if self._is_source_article_url(monitored_account.source_url):
                return [
                    ArticleUpdate(
                        title=f"{monitored_account.name} 原始文章",
                        url=monitored_account.source_url,
                        published_at=None,
                        cover_image=monitored_account.avatar_url,
                        author=monitored_account.name,
                        source_payload={
                            "channel": "weread_source_article",
                            "seed_url": monitored_account.source_url,
                        },
                    )
                ]
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
        publish_page = payload.get("publish_page")
        if publish_page and not app_msg_list:
            try:
                publish_payload = json.loads(publish_page) if isinstance(publish_page, str) else publish_page
                publish_list = publish_payload.get("publish_list", []) or publish_payload.get("list", [])
                for publish_item in publish_list:
                    ext_info = publish_item.get("appmsgex") or publish_item.get("app_msg_ext_info") or []
                    if isinstance(ext_info, str):
                        ext_info = json.loads(ext_info)
                    if isinstance(ext_info, dict):
                        ext_info = [ext_info]
                    for item in ext_info or []:
                        app_msg_list.append(
                            {
                                **item,
                                "update_time": item.get("update_time") or publish_item.get("publish_time"),
                                "link": item.get("link") or item.get("content_url"),
                            }
                        )
            except Exception:
                app_msg_list = []
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
                        "https://mp.weixin.qq.com/cgi-bin/appmsgpublish",
                        params={
                            "action": "list_ex",
                            "sub": "list",
                            "sub_action": "list_ex",
                            "fakeid": monitored_account.fakeid,
                            "token": token or "",
                            "lang": "zh_CN",
                            "f": "json",
                            "ajax": "1",
                            "count": page_size,
                            "begin": begin,
                            "query": "",
                            "type": "101_1",
                            "free_publish_type": "1",
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
            CollectorAccountType.WEREAD: ProxyServiceKey.WEREAD_LIST,
            CollectorAccountType.MP_ADMIN: ProxyServiceKey.MP_LIST,
        }
        try:
            proxy_model = await self.proxy_service.select_proxy(mapping[mode])
            return proxy_model.proxy_url
        except ProxyNotAvailableException:
            return None

    async def get_detail_proxy_for_mode(self, mode: CollectorAccountType) -> str | None:
        mapping = {
            CollectorAccountType.WEREAD: ProxyServiceKey.WEREAD_DETAIL,
            CollectorAccountType.MP_ADMIN: ProxyServiceKey.MP_DETAIL,
        }
        try:
            proxy_model = await self.proxy_service.select_proxy(mapping[mode])
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
        if collector_account.account_type == CollectorAccountType.WEREAD:
            return await self.weread_fetcher.fetch_article_detail(url, collector_account, None)
        return await self.mp_fetcher.fetch_article_detail(url, collector_account, None)
