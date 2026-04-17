"""Weight configuration and simulation schemas."""

from typing import Any

from pydantic import BaseModel


class WeightConfig(BaseModel):
    """Schema for weight configuration."""

    # Weight ratios
    frequency_ratio: float
    recency_ratio: float
    relevance_ratio: float
    stability_ratio: float

    # Tier thresholds
    tier_thresholds: list[float]

    # Check intervals per tier
    check_intervals: dict[str, int]

    # Alert thresholds
    high_relevance_threshold: float
    ai_consecutive_low_threshold: int


class WeightConfigUpdate(BaseModel):
    """Schema for updating weight configuration."""

    frequency_ratio: float | None = None
    recency_ratio: float | None = None
    relevance_ratio: float | None = None
    stability_ratio: float | None = None
    tier_threshold_tier1: float | None = None
    tier_threshold_tier2: float | None = None
    tier_threshold_tier3: float | None = None
    tier_threshold_tier4: float | None = None
    check_interval_tier1: int | None = None
    check_interval_tier2: int | None = None
    check_interval_tier3: int | None = None
    check_interval_tier4: int | None = None
    check_interval_tier5: int | None = None
    high_relevance_threshold: float | None = None
    ai_consecutive_low_threshold: int | None = None


class WeightSimulateInput(BaseModel):
    """Schema for weight simulation input."""

    # Account current state
    update_history: dict[str, int]  # timestamp -> count
    ai_relevance_history: dict[str, dict[str, Any]]  # timestamp -> {ratio, reason}
    last_updated: str | None = None

    # This fetch results
    new_article_count: int
    ai_result: dict[str, Any] | None = None


class WeightSimulateResult(BaseModel):
    """Schema for weight simulation result."""

    new_score: float
    new_tier: int
    next_interval_hours: int
    score_breakdown: dict[str, float]
    tier_changed: bool
    override_active: bool = False


class WeightUpdateEvent(BaseModel):
    """Schema for weight update event (internal use)."""

    account_id: int
    old_tier: int
    new_tier: int
    old_score: float
    new_score: float
    reason: str
    timestamp: str
