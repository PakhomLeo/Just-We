"""Schemas for article JSON exports."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator


ExportScope = Literal["all", "account", "time"]
TargetMatchFilter = Literal["all", "matched", "unmatched", "unknown"]


class ArticleExportCreate(BaseModel):
    """Request for generating a JSON export file."""

    scope: ExportScope = "all"
    monitored_account_id: int | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    target_match: TargetMatchFilter = "all"
    include_exported: bool = False

    @model_validator(mode="after")
    def validate_scope(self):
        if self.scope == "account" and self.monitored_account_id is None:
            raise ValueError("按账号导出时必须选择账号")
        if self.scope == "time" and not (self.start_date or self.end_date):
            raise ValueError("按时间导出时至少需要开始或结束时间")
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValueError("开始时间不能晚于结束时间")
        return self


class ArticleExportRecordResponse(BaseModel):
    """Response for a generated export record."""

    id: int
    scope: str
    target_match: str
    include_exported: bool
    filters: dict
    article_count: int
    file_name: str
    status: str
    error: str | None = None
    created_at: datetime
    updated_at: datetime
    download_url: str = Field(default="")

    model_config = {"from_attributes": True}


class ArticleExportListResponse(BaseModel):
    """List of export records."""

    total: int
    items: list[ArticleExportRecordResponse]
