"""Article schemas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class ArticleResponse(BaseModel):
    """Schema for article response."""

    id: int
    monitored_account_id: int | None = None
    title: str
    content: str
    content_html: str | None = None
    content_type: str | None = None
    raw_content: str | None
    images: list[str]
    original_images: list[str] | None = None
    cover_image: str | None = None
    url: str
    author: str | None = None
    published_at: datetime | None
    ai_relevance_ratio: float | None
    ai_judgment: dict[str, Any] | None
    ai_text_analysis: dict[str, Any] | None = None
    ai_image_analysis: dict[str, Any] | None = None
    ai_type_judgment: dict[str, Any] | None = None
    ai_combined_analysis: dict[str, Any] | None = None
    ai_target_match: str | None = None
    ai_analysis_status: str | None = None
    ai_analysis_error: str | None = None
    fetch_mode: str | None = None
    source_payload: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ArticleWithAccountResponse(BaseModel):
    """Schema for article response with account_name included."""

    id: int
    monitored_account_id: int | None = None
    title: str
    content: str
    content_html: str | None = None
    content_type: str | None = None
    raw_content: str | None
    images: list[str]
    original_images: list[str] | None = None
    cover_image: str | None = None
    url: str
    author: str | None = None
    published_at: datetime | None
    ai_relevance_ratio: float | None
    ai_judgment: dict[str, Any] | None
    ai_text_analysis: dict[str, Any] | None = None
    ai_image_analysis: dict[str, Any] | None = None
    ai_type_judgment: dict[str, Any] | None = None
    ai_combined_analysis: dict[str, Any] | None = None
    ai_target_match: str | None = None
    ai_analysis_status: str | None = None
    ai_analysis_error: str | None = None
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

    monitored_account_id: int | None = None
    title: str
    content: str
    content_html: str | None = None
    content_type: str | None = None
    raw_content: str | None = None
    images: list[str] = []
    original_images: list[str] | None = None
    cover_image: str | None = None
    url: str
    author: str | None = None
    published_at: datetime | None = None
    ai_relevance_ratio: float | None = None
    ai_judgment: dict[str, Any] | None = None
    ai_text_analysis: dict[str, Any] | None = None
    ai_image_analysis: dict[str, Any] | None = None
    ai_type_judgment: dict[str, Any] | None = None
    ai_combined_analysis: dict[str, Any] | None = None
    ai_target_match: str | None = None
    ai_analysis_status: str | None = None
    ai_analysis_error: str | None = None
    fetch_mode: str | None = None
    source_payload: dict[str, Any] | None = None


class ArticleFilter(BaseModel):
    """Schema for filtering articles."""

    monitored_account_id: int | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    min_relevance: float | None = None
    max_relevance: float | None = None
