"""Feed generation and export service."""

from __future__ import annotations

import csv
import html
import io
import json
from datetime import datetime, timezone
from urllib.parse import quote
from xml.etree import ElementTree as ET

from sqlalchemy import Select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.monitored_account import MonitoredAccount
from app.models.user import User
from app.repositories.article_repo import ArticleRepository
from app.repositories.monitored_account_repo import MonitoredAccountRepository


class FeedService:
    """Generate RSS/Atom/JSON feeds from monitored accounts and articles."""

    def __init__(self, db: AsyncSession, public_base_url: str = ""):
        self.db = db
        self.public_base_url = public_base_url.rstrip("/")
        self.monitored_repo = MonitoredAccountRepository(db)
        self.article_repo = ArticleRepository(db)

    async def get_account_by_token(self, feed_token: str) -> MonitoredAccount | None:
        return await self.monitored_repo.get_by_feed_token(feed_token)

    async def get_user_by_aggregate_token(self, token: str) -> User | None:
        result = await self.db.execute(Select(User).where(User.aggregate_feed_token == token))
        return result.scalar_one_or_none()

    async def generate_for_account(
        self,
        account: MonitoredAccount,
        feed_type: str,
        *,
        limit: int = 50,
        page: int = 1,
        mode: str = "summary",
        title_include: str | None = None,
        title_exclude: str | None = None,
    ) -> tuple[str, str]:
        articles = await self.article_repo.get_for_feed(
            [account.id],
            skip=max(page - 1, 0) * limit,
            limit=limit,
            title_include=title_include,
            title_exclude=title_exclude,
        )
        return self._render_feed(feed_type, account.name, account.source_url, articles, mode)

    async def generate_aggregate(
        self,
        user: User,
        feed_type: str,
        *,
        limit: int = 50,
        page: int = 1,
        mode: str = "summary",
        title_include: str | None = None,
        title_exclude: str | None = None,
    ) -> tuple[str, str]:
        accounts = await self.monitored_repo.get_visible_accounts(user.id)
        articles = await self.article_repo.get_for_feed(
            [account.id for account in accounts],
            skip=max(page - 1, 0) * limit,
            limit=limit,
            title_include=title_include,
            title_exclude=title_exclude,
        )
        return self._render_feed(feed_type, f"{user.email} 的公众号聚合订阅", self.public_base_url or "", articles, mode)

    async def export_visible(self, current_user, export_format: str) -> tuple[str, str, str]:
        owner_user_id = None if current_user.role.value == "admin" else current_user.id
        accounts = await self.monitored_repo.get_visible_accounts(owner_user_id)
        if export_format == "csv":
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(["name", "biz", "rss_url", "source_url", "group", "updated_at"])
            for account in accounts:
                writer.writerow([
                    account.name,
                    account.biz,
                    self.feed_url(account.feed_token, "rss"),
                    account.source_url,
                    f"Tier {account.current_tier}",
                    account.updated_at.isoformat() if account.updated_at else "",
                ])
            return output.getvalue(), "text/csv; charset=utf-8", "feeds.csv"
        if export_format == "opml":
            body = ET.Element("opml", version="2.0")
            head = ET.SubElement(body, "head")
            ET.SubElement(head, "title").text = "Just-We Feeds"
            outline = ET.SubElement(body, "body")
            groups: dict[str, ET.Element] = {}
            for account in accounts:
                group_name = f"Tier {account.current_tier}"
                group = groups.setdefault(group_name, ET.SubElement(outline, "outline", {"text": group_name, "title": group_name}))
                ET.SubElement(
                    group,
                    "outline",
                    {
                        "type": "rss",
                        "text": account.name,
                        "title": account.name,
                        "xmlUrl": self.feed_url(account.feed_token, "rss"),
                        "htmlUrl": account.source_url,
                        "updated": account.updated_at.isoformat() if account.updated_at else "",
                    },
                )
            return ET.tostring(body, encoding="unicode"), "text/x-opml; charset=utf-8", "feeds.opml"
        raise ValueError("Unsupported export format")

    def feed_url(self, token: str, feed_type: str = "rss") -> str:
        if self.public_base_url:
            return f"{self.public_base_url}/feeds/{token}.{feed_type}"
        return f"/feeds/{token}.{feed_type}"

    def aggregate_feed_url(self, token: str, feed_type: str = "rss") -> str:
        if self.public_base_url:
            return f"{self.public_base_url}/feeds/all/{token}.{feed_type}"
        return f"/feeds/all/{token}.{feed_type}"

    def _render_feed(self, feed_type: str, title: str, link: str, articles: list, mode: str) -> tuple[str, str]:
        feed_type = feed_type.lower()
        if feed_type == "rss":
            return self._render_rss(title, link, articles, mode), "application/rss+xml; charset=utf-8"
        if feed_type == "atom":
            return self._render_atom(title, link, articles, mode), "application/atom+xml; charset=utf-8"
        if feed_type == "json":
            return self._render_json(title, link, articles, mode), "application/feed+json; charset=utf-8"
        raise ValueError("Unsupported feed type")

    def _article_content(self, article, mode: str) -> str:
        if mode == "fulltext":
            content = article.content_html or f"<p>{html.escape(article.content or '')}</p>"
            for image_url in article.original_images or []:
                content = content.replace(image_url, self.image_proxy_url(image_url))
            return content
        summary = article.content or ""
        if len(summary) > 500:
            summary = summary[:500].rstrip() + "..."
        return f"<p>{html.escape(summary)}</p>"

    def _pub_date(self, value: datetime | None) -> str:
        date = value or datetime.now(timezone.utc)
        if date.tzinfo is None:
            date = date.replace(tzinfo=timezone.utc)
        return date.strftime("%a, %d %b %Y %H:%M:%S %z")

    def _iso_date(self, value: datetime | None) -> str:
        date = value or datetime.now(timezone.utc)
        if date.tzinfo is None:
            date = date.replace(tzinfo=timezone.utc)
        return date.isoformat()

    def _render_rss(self, title: str, link: str, articles: list, mode: str) -> str:
        parts = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<rss version="2.0" xmlns:content="http://purl.org/rss/1.0/modules/content/">',
            "<channel>",
            f"<title>{html.escape(title)}</title>",
            f"<link>{html.escape(link or self.public_base_url or '')}</link>",
            f"<description>{html.escape(title)}</description>",
        ]
        for article in articles:
            content = self._article_content(article, mode).replace("]]>", "]]]]><![CDATA[>")
            parts.extend(
                [
                    "<item>",
                    f"<title>{html.escape(article.title or '')}</title>",
                    f"<link>{html.escape(article.url or '')}</link>",
                    f"<guid isPermaLink=\"true\">{html.escape(article.url or '')}</guid>",
                    f"<pubDate>{html.escape(self._pub_date(article.published_at))}</pubDate>",
                    f"<description><![CDATA[{content}]]></description>",
                    f"<content:encoded><![CDATA[{content}]]></content:encoded>",
                    "</item>",
                ]
            )
        parts.extend(["</channel>", "</rss>"])
        return "".join(parts)

    def _render_atom(self, title: str, link: str, articles: list, mode: str) -> str:
        feed = ET.Element("feed", xmlns="http://www.w3.org/2005/Atom")
        ET.SubElement(feed, "title").text = title
        ET.SubElement(feed, "id").text = link or title
        ET.SubElement(feed, "updated").text = self._iso_date(articles[0].published_at if articles else None)
        ET.SubElement(feed, "link", href=link or self.public_base_url or "")
        ET.SubElement(feed, "link", href=link or self.public_base_url or "", rel="self")
        for article in articles:
            entry = ET.SubElement(feed, "entry")
            ET.SubElement(entry, "title").text = article.title
            ET.SubElement(entry, "id").text = article.url
            ET.SubElement(entry, "updated").text = self._iso_date(article.published_at)
            ET.SubElement(entry, "link", href=article.url)
            ET.SubElement(entry, "content", type="html").text = self._article_content(article, mode)
        return ET.tostring(feed, encoding="unicode")

    def _render_json(self, title: str, link: str, articles: list, mode: str) -> str:
        payload = {
            "version": "https://jsonfeed.org/version/1.1",
            "title": title,
            "home_page_url": link,
            "feed_url": link,
            "items": [
                {
                    "id": article.url,
                    "url": article.url,
                    "title": article.title,
                    "content_html": self._article_content(article, mode),
                    "date_published": self._iso_date(article.published_at),
                    "image": article.cover_image,
                    "attachments": [
                        {"url": self.image_proxy_url(image) if image.startswith("http") else image, "mime_type": "image/*"}
                        for image in (article.images or article.original_images or [])
                    ],
                }
                for article in articles
            ],
        }
        return json.dumps(payload, ensure_ascii=False)

    def image_proxy_url(self, image_url: str) -> str:
        if self.public_base_url:
            return f"{self.public_base_url}/api/image?url={quote(image_url, safe='')}"
        return f"/api/image?url={quote(image_url, safe='')}"
