"""Public image proxy for WeChat CDN images."""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import unquote, urlparse

import httpx
from fastapi import APIRouter, HTTPException, Query, Response


router = APIRouter(prefix="/image", tags=["Image Proxy"])

ALLOWED_HOST_SUFFIXES = (
    "mmbiz.qpic.cn",
    "mmbiz.qlogo.cn",
    "wx.qlogo.cn",
    "res.wx.qq.com",
)
MAX_IMAGE_BYTES = 10 * 1024 * 1024


def _validate_image_url(raw_url: str) -> str:
    url = unquote(raw_url)
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise HTTPException(status_code=400, detail="Only HTTP(S) image URLs are allowed")
    host = parsed.hostname or ""
    if not any(host == suffix or host.endswith(f".{suffix}") for suffix in ALLOWED_HOST_SUFFIXES):
        raise HTTPException(status_code=400, detail="Image host is not allowed")
    try:
        for item in socket.getaddrinfo(host, None):
            address = item[4][0]
            ip = ipaddress.ip_address(address)
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                raise HTTPException(status_code=400, detail="Private image host is not allowed")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=400, detail="Unable to resolve image host")
    return url


@router.get("")
async def proxy_image(url: str = Query(..., min_length=1)):
    target = _validate_image_url(url)
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            response = await client.get(
                target,
                headers={
                    "Referer": "https://mp.weixin.qq.com/",
                    "User-Agent": "Mozilla/5.0",
                },
            )
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Image fetch failed: {exc}") from exc
    content_type = response.headers.get("content-type", "")
    if response.status_code >= 400:
        raise HTTPException(status_code=502, detail=f"Image upstream returned HTTP {response.status_code}")
    if not content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Upstream response is not an image")
    if len(response.content) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="Image is too large")
    return Response(
        content=response.content,
        media_type=content_type,
        headers={"Cache-Control": "public, max-age=86400"},
    )
