"""HTML cleaner utility for extracting clean text from HTML."""

import re


class HTMLCleaner:
    """
    Utility for cleaning HTML and extracting clean text.

    This is a simplified version - the full implementation is in ParserService.
    """

    # Patterns for removing unwanted elements
    UNWANTED_TAGS = [
        "script",
        "style",
        "nav",
        "header",
        "footer",
        "aside",
        "form",
        "button",
        "input",
        "select",
        "textarea",
    ]

    # Patterns for removing ad-related classes/ids
    AD_PATTERNS = re.compile(
        r"(ad-|ads-|advert|sidebar|related|comment|social|share)",
        re.IGNORECASE,
    )

    def __init__(self):
        """Initialize HTML cleaner."""
        pass

    def clean(self, html: str) -> str:
        """
        Clean HTML and return plain text.

        Args:
            html: Raw HTML content

        Returns:
            Cleaned plain text
        """
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "lxml")

        # Remove unwanted tags
        for tag in self.UNWANTED_TAGS:
            for element in soup.find_all(tag):
                element.decompose()

        # Remove elements with ad-related classes
        for element in soup.find_all(class_=self.AD_PATTERNS):
            element.decompose()

        for element in soup.find_all(id=self.AD_PATTERNS):
            element.decompose()

        # Remove comments
        for comment in soup.find_all(string=lambda text: isinstance(text, str) and text.strip().startswith("<!--")):
            comment.extract()

        # Get text
        text = soup.get_text(separator="\n", strip=True)

        # Clean whitespace
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"[ \t]+", " ", text)

        return text

    def extract_images(self, html: str) -> list[str]:
        """
        Extract image URLs from HTML.

        Args:
            html: Raw HTML content

        Returns:
            List of image URLs
        """
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "lxml")
        images = []

        for img in soup.find_all("img"):
            src = img.get("src") or img.get("data-src")
            if src and not src.startswith("data:"):
                images.append(src)

        return images

    def extract_links(self, html: str) -> list[dict[str, str]]:
        """
        Extract links from HTML.

        Args:
            html: Raw HTML content

        Returns:
            List of dicts with {text, href} pairs
        """
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "lxml")
        links = []

        for a in soup.find_all("a", href=True):
            links.append({
                "text": a.get_text(strip=True),
                "href": a["href"],
            })

        return links
