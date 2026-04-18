"""Parser service for HTML cleaning and content extraction."""

from dataclasses import dataclass
from urllib.parse import urlparse

from bs4 import BeautifulSoup
import re

from app.utils.image_downloader import ImageDownloader


@dataclass
class ParsedArticle:
    """Parsed article content."""

    title: str
    content: str
    images: list[str]
    raw_content: str
    content_html: str | None = None
    content_type: str | None = None
    original_images: list[str] | None = None


class ParserService:
    """Service for parsing and cleaning article HTML."""

    def __init__(self, image_downloader: ImageDownloader | None = None):
        """Initialize parser with optional image downloader."""
        self.image_downloader = image_downloader or ImageDownloader()

    def extract_title(self, soup: BeautifulSoup) -> str:
        """Extract article title from HTML."""
        # Try common title selectors
        title = soup.find("h1", class_="article-title")
        if title:
            return title.get_text(strip=True)

        title = soup.find("h1", id="title")
        if title:
            return title.get_text(strip=True)

        title = soup.find("h1", id="activity-name")
        if title:
            return title.get_text(strip=True)

        title = soup.find("h1", class_="rich_media_title")
        if title:
            return title.get_text(strip=True)

        title = soup.find("meta", property="og:title")
        if title:
            return title.get("content", "")

        # Fallback to page title
        title_tag = soup.find("title")
        if title_tag:
            return title_tag.get_text(strip=True)

        return ""

    def extract_published_time(self, soup: BeautifulSoup) -> str | None:
        """Extract published time from HTML."""
        # Try meta tags
        time_tag = soup.find("meta", property="article:published_time")
        if time_tag:
            return time_tag.get("content")

        time_tag = soup.find("meta", attrs={"name": "publish_time"})
        if time_tag:
            return time_tag.get("content")

        # Try time tag
        time_element = soup.find("time")
        if time_element:
            return time_element.get("datetime")

        return None

    def _normalize_image_url(self, src: str | None) -> str | None:
        if not src:
            return None
        src = src.strip()
        if not src or src.startswith("data:"):
            return None
        if src.startswith("//"):
            return f"https:{src}"
        return src

    def _extract_body_container(self, soup: BeautifulSoup):
        return (
            soup.find(id="js_content")
            or soup.find(class_="rich_media_content")
            or soup.find("article")
            or soup.body
            or soup
        )

    def _classify_content_type(self, soup: BeautifulSoup, text: str, images: list[str]) -> str:
        raw = str(soup)
        item_show_type = None
        match = re.search(r"item_show_type\s*[:=]\s*['\"]?(\d+)", raw)
        if match:
            item_show_type = match.group(1)
        if soup.find("mpvoice") or soup.find(class_="wechat-audio-placeholder"):
            return "audio"
        if "video_iframe" in raw or "iframe/video" in raw or soup.find("iframe"):
            return "video"
        if item_show_type == "7":
            return "media_share"
        if item_show_type == "8":
            return "image_text"
        if item_show_type == "10":
            return "short_content"
        if images and len(text.strip()) < 80:
            return "image_only"
        return "article"

    def _sanitize_style_value(self, value: object) -> str | None:
        hidden_properties = {"display", "opacity", "visibility"}
        declarations = []
        for declaration in str(value or "").split(";"):
            if ":" not in declaration:
                continue
            property_name, property_value = declaration.split(":", 1)
            property_name = property_name.strip().lower()
            if property_name in hidden_properties:
                continue
            declarations.append(f"{property_name}: {property_value.strip()}")
        return "; ".join(declarations) or None

    def _sanitize_rich_html(self, html_content: str) -> tuple[str, list[str], str]:
        soup = BeautifulSoup(html_content, "lxml")
        container = self._extract_body_container(soup)

        image_urls: list[str] = []
        for element in container.find_all(["script", "style", "link", "meta", "noscript", "form", "input", "nav", "header", "footer"]):
            element.decompose()
        for element in container.find_all(class_=re.compile(r"(ad|comment|sidebar|related|profile|reward|share|qr)")):
            element.decompose()

        safe_attrs = {
            "a": {"href", "title", "target", "rel"},
            "img": {"src", "alt", "title", "width", "height", "data-src"},
            "section": {"style"},
            "span": {"style"},
            "p": {"style"},
            "strong": set(),
            "em": set(),
            "blockquote": set(),
            "br": set(),
            "ul": set(),
            "ol": set(),
            "li": set(),
            "h1": set(),
            "h2": set(),
            "h3": set(),
            "h4": set(),
            "pre": set(),
            "code": set(),
        }
        allowed_tags = set(safe_attrs)
        if getattr(container, "attrs", None) and container.get("style"):
            style = self._sanitize_style_value(container.get("style"))
            if style:
                container["style"] = style
            else:
                del container.attrs["style"]

        for tag in list(container.find_all(True)):
            if tag.name == "mpvoice":
                tag.name = "div"
                tag["class"] = "wechat-audio-placeholder"
                tag.string = "音频内容需在微信原文中播放"
                continue
            if tag.name not in allowed_tags:
                tag.unwrap()
                continue
            attrs = dict(tag.attrs)
            for attr, value in attrs.items():
                if attr.startswith("on") or attr not in safe_attrs[tag.name]:
                    del tag.attrs[attr]
                    continue
                if attr == "style":
                    style = self._sanitize_style_value(value)
                    if style:
                        tag.attrs[attr] = style
                    else:
                        del tag.attrs[attr]
                    continue
                if attr in {"href", "src", "data-src"}:
                    value_str = value[0] if isinstance(value, list) else str(value)
                    if value_str.startswith(("javascript:", "data:")):
                        del tag.attrs[attr]

            if tag.name == "img":
                src = self._normalize_image_url(tag.get("data-src") or tag.get("src"))
                if not src:
                    tag.decompose()
                    continue
                image_urls.append(src)
                tag["src"] = src
                tag.attrs.pop("data-src", None)
                tag["loading"] = "lazy"
                tag["referrerpolicy"] = "no-referrer"

            if tag.name == "a":
                href = tag.get("href")
                if href:
                    parsed = urlparse(str(href))
                    if parsed.scheme not in {"http", "https", ""}:
                        del tag.attrs["href"]
                    else:
                        tag["target"] = "_blank"
                        tag["rel"] = "noopener noreferrer"

        html = str(container)
        text = BeautifulSoup(html, "lxml").get_text(separator="\n", strip=True)
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r" {2,}", " ", text)
        return text, list(dict.fromkeys(image_urls)), html

    def clean_html(self, html_content: str) -> tuple[str, list[str]]:
        """
        Clean HTML and extract text content and image URLs.

        Args:
            html_content: Raw HTML content

        Returns:
            Tuple of (cleaned_text, image_urls)
        """
        text, image_urls, _ = self._sanitize_rich_html(html_content)
        return text, image_urls

    async def parse_article(
        self,
        raw_html: str,
        download_images: bool = True,
        storage_id: int | str | None = None,
        proxy: str | None = None,
    ) -> ParsedArticle:
        """
        Parse raw HTML into structured content.

        Args:
            raw_html: Raw HTML content
            download_images: Whether to download images locally

        Returns:
            ParsedArticle with title, content, images, raw_content
        """
        soup = BeautifulSoup(raw_html, "lxml")

        title = self.extract_title(soup)

        cleaned_content, image_urls, content_html = self._sanitize_rich_html(raw_html)
        original_images = list(image_urls)
        content_type = self._classify_content_type(BeautifulSoup(content_html, "lxml"), cleaned_content, image_urls)

        # Download and localize images if requested
        if download_images and image_urls and self.image_downloader and storage_id is not None:
            try:
                local_paths = await self.image_downloader.download_multiple(image_urls, storage_id, proxy=proxy)
                # Replace URLs with local paths in content
                for original_url, local_path in zip(image_urls, local_paths):
                    if local_path:
                        public_url = local_path
                        to_public_url = getattr(self.image_downloader, "to_public_url", None)
                        if callable(to_public_url):
                            converted = to_public_url(local_path)
                            if isinstance(converted, str):
                                public_url = converted
                        content_html = content_html.replace(original_url, public_url)
                image_urls = [
                    self._to_public_image_url(path)
                    for path in local_paths
                    if path
                ]
            except Exception:
                # If download fails, keep original URLs
                pass

        return ParsedArticle(
            title=title,
            content=cleaned_content,
            images=image_urls,
            raw_content=raw_html,
            content_html=content_html,
            content_type=content_type,
            original_images=original_images,
        )

    def extract_text_only(self, html_content: str) -> str:
        """
        Extract only text content without image processing.

        Args:
            html_content: Raw HTML content

        Returns:
            Cleaned text content
        """
        cleaned_content, _ = self.clean_html(html_content)
        return cleaned_content

    def _to_public_image_url(self, path: str) -> str:
        to_public_url = getattr(self.image_downloader, "to_public_url", None)
        if callable(to_public_url):
            converted = to_public_url(path)
            if isinstance(converted, str):
                return converted
        return path
