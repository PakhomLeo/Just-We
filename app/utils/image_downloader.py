"""Image downloader utility for localizing article images."""

import asyncio
import hashlib
from pathlib import Path

import httpx

from app.core.config import get_settings


settings = get_settings()


class ImageDownloader:
    """
    Utility for downloading and localizing images.

    Images are downloaded and saved to a local directory structure:
    media/articles/{account_id}/{image_hash}.{ext}
    """

    def __init__(
        self,
        base_dir: str | None = None,
        max_size_mb: int = 10,
        timeout: int = 30,
    ):
        """
        Initialize image downloader.

        Args:
            base_dir: Base directory for storing images
            max_size_mb: Maximum image size in MB to download
            timeout: Download timeout in seconds
        """
        base_dir = base_dir or str(Path(settings.media_root) / "articles")
        self.base_dir = Path(base_dir)
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.timeout = timeout
        self.public_prefix = f"{settings.media_url_prefix.rstrip('/')}/articles"

    def _get_extension(self, content_type: str | None, url: str) -> str:
        """Get file extension from content type or URL."""
        if content_type:
            # Map content type to extension
            mime_map = {
                "image/jpeg": "jpg",
                "image/png": "png",
                "image/gif": "gif",
                "image/webp": "webp",
                "image/svg+xml": "svg",
            }
            if content_type in mime_map:
                return mime_map[content_type]

        # Try to extract from URL
        if "." in url:
            ext = url.rsplit(".", 1)[-1].split("?")[0][:4]
            if ext.lower() in ["jpg", "jpeg", "png", "gif", "webp"]:
                return ext

        return "jpg"  # Default

    def _get_content_type(self, headers: httpx.Headers) -> str | None:
        """Extract content type from headers."""
        content_type = headers.get("content-type")
        if content_type:
            return content_type.split(";")[0].strip()
        return None

    async def download_image(
        self,
        url: str,
        account_id: int | str,
        proxy: str | None = None,
    ) -> str | None:
        """
        Download a single image and save locally.

        Args:
            url: Image URL
            account_id: Account ID for directory structure
            proxy: Optional proxy URL

        Returns:
            Local file path or None if download failed
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, proxy=proxy)
                response.raise_for_status()

                # Check size
                content_length = response.headers.get("content-length")
                if content_length and int(content_length) > self.max_size_bytes:
                    return None

                content = response.content
                if len(content) > self.max_size_bytes:
                    return None

                # Generate local path
                content_hash = hashlib.sha256(content).hexdigest()[:16]
                content_type = self._get_content_type(response.headers)
                ext = self._get_extension(content_type, url)

                account_dir = self.base_dir / str(account_id)
                account_dir.mkdir(parents=True, exist_ok=True)

                local_path = account_dir / f"{content_hash}.{ext}"

                # Save file
                with open(local_path, "wb") as f:
                    f.write(content)

                return str(local_path)
        except Exception:
            return None

    async def download_multiple(
        self,
        urls: list[str],
        account_id: int | str,
        proxy: str | None = None,
        max_concurrent: int = 5,
    ) -> list[str | None]:
        """
        Download multiple images concurrently.

        Args:
            urls: List of image URLs
            account_id: Account ID for directory structure
            proxy: Optional proxy URL
            max_concurrent: Maximum concurrent downloads

        Returns:
            List of local file paths (None for failed downloads)
        """
        semaphore = asyncio.Semaphore(max_concurrent)

        async def download_with_limit(url: str) -> str | None:
            async with semaphore:
                return await self.download_image(url, account_id, proxy)

        tasks = [download_with_limit(url) for url in urls]
        return await asyncio.gather(*tasks)

    def to_public_url(self, local_path: str | None) -> str | None:
        """Convert a local media path to a mounted public URL."""
        if not local_path:
            return None
        path = Path(local_path)
        try:
            relative = path.relative_to(Path(settings.media_root))
        except ValueError:
            text = local_path.lstrip("./")
            if text.startswith(f"{settings.media_root.rstrip('/')}/"):
                relative = Path(text[len(settings.media_root.rstrip('/')) + 1 :])
            else:
                return local_path
        return f"{settings.media_url_prefix.rstrip('/')}/{relative.as_posix()}"

    def delete_account_images(self, account_id: int) -> int:
        """
        Delete all images for an account.

        Args:
            account_id: Account ID

        Returns:
            Number of files deleted
        """
        account_dir = self.base_dir / str(account_id)
        if not account_dir.exists():
            return 0

        count = 0
        for file in account_dir.iterdir():
            if file.is_file():
                file.unlink()
                count += 1

        # Try to remove directory if empty
        try:
            account_dir.rmdir()
        except Exception:
            pass

        return count
