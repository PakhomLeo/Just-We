"""Parser service for HTML cleaning and content extraction."""

from dataclasses import dataclass
from typing import Any

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

    def clean_html(self, html_content: str) -> tuple[str, list[str]]:
        """
        Clean HTML and extract text content and image URLs.

        Args:
            html_content: Raw HTML content

        Returns:
            Tuple of (cleaned_text, image_urls)
        """
        soup = BeautifulSoup(html_content, "lxml")

        # Extract image URLs before cleaning
        image_urls = []
        for img in soup.find_all("img"):
            src = img.get("src") or img.get("data-src")
            if src and not src.startswith("data:"):
                image_urls.append(src)

        # Remove script and style elements
        for element in soup(["script", "style", "nav", "header", "footer"]):
            element.decompose()

        # Remove unwanted classes
        for element in soup.find_all(class_=re.compile(r"(ad|comment|sidebar|related)-")):
            element.decompose()

        # Get text content
        text = soup.get_text(separator="\n", strip=True)

        # Clean up extra whitespace
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r" {2,}", " ", text)

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
        published_time = self.extract_published_time(soup)

        cleaned_content, image_urls = self.clean_html(raw_html)

        # Download and localize images if requested
        if download_images and image_urls and self.image_downloader and storage_id is not None:
            try:
                local_paths = await self.image_downloader.download_multiple(image_urls, storage_id, proxy=proxy)
                # Replace URLs with local paths in content
                for original_url, local_path in zip(image_urls, local_paths):
                    if local_path:
                        cleaned_content = cleaned_content.replace(original_url, local_path)
                image_urls = [p for p in local_paths if p]
            except Exception:
                # If download fails, keep original URLs
                pass

        return ParsedArticle(
            title=title,
            content=cleaned_content,
            images=image_urls,
            raw_content=raw_html,
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
