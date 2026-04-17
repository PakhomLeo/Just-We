"""Article schemas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class ArticleResponse(BaseModel):
    """Schema for article response."""

    id: int
    account_id: int | None
    monitored_account_id: int | None = None
    title: str
    content: str
    raw_content: str | None
    images: list[str]
    cover_image: str | None = None
    url: str
    author: str | None = None
    published_at: datetime | None
    ai_relevance_ratio: float | None
    ai_judgment: dict[str, Any] | None
    fetch_mode: str | None = None
    source_payload: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ArticleWithAccountResponse(BaseModel):
    """Schema for article response with account_name included."""

    id: int
    account_id: int | None
    monitored_account_id: int | None = None
    title: str
    content: str
    raw_content: str | None
    images: list[str]
    cover_image: str | None = None
    url: str
    author: str | None = None
    published_at: datetime | None
    ai_relevance_ratio: float | None
    ai_judgment: dict[str, Any] | None
    fetch_mode: str | None = None
    source_payload: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime
    account_name: str | None = None

    model_config = {"from_attributes": True}


class ArticleListResponse(BaseModel):
    """Schema for paginated article list response."""

    total: int
    items: list[ArticleWithAccountResponse]
    page: int
    page_size: int
    total_pages: int


class ArticleCreate(BaseModel):
    """Schema for creating an article (internal use)."""

    account_id: int | None
    monitored_account_id: int | None = None
    title: str
    content: str
    raw_content: str | None = None
    images: list[str] = []
    cover_image: str | None = None
    url: str
    author: str | None = None
    published_at: datetime | None = None
    ai_relevance_ratio: float | None = None
    ai_judgment: dict[str, Any] | None = None
    fetch_mode: str | None = None
    source_payload: dict[str, Any] | None = None


class ArticleFilter(BaseModel):
    """Schema for filtering articles."""

    account_id: int | None = None
    monitored_account_id: int | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    min_relevance: float | None = None
    max_relevance: float | None = None
