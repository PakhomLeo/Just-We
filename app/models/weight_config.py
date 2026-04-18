"""Persisted weight configuration."""

from sqlalchemy import Float, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class WeightConfig(Base, TimestampMixin):
    """Singleton weight configuration used by the scoring pipeline."""

    __tablename__ = "weight_configs"

    frequency_ratio: Mapped[float] = mapped_column(Float, nullable=False, default=0.35)
    recency_ratio: Mapped[float] = mapped_column(Float, nullable=False, default=0.25)
    relevance_ratio: Mapped[float] = mapped_column(Float, nullable=False, default=0.25)
    stability_ratio: Mapped[float] = mapped_column(Float, nullable=False, default=0.15)

    tier_threshold_tier1: Mapped[float] = mapped_column(Float, nullable=False, default=80.0)
    tier_threshold_tier2: Mapped[float] = mapped_column(Float, nullable=False, default=65.0)
    tier_threshold_tier3: Mapped[float] = mapped_column(Float, nullable=False, default=50.0)
    tier_threshold_tier4: Mapped[float] = mapped_column(Float, nullable=False, default=35.0)

    check_interval_tier1: Mapped[int] = mapped_column(Integer, nullable=False, default=24)
    check_interval_tier2: Mapped[int] = mapped_column(Integer, nullable=False, default=48)
    check_interval_tier3: Mapped[int] = mapped_column(Integer, nullable=False, default=72)
    check_interval_tier4: Mapped[int] = mapped_column(Integer, nullable=False, default=144)
    check_interval_tier5: Mapped[int] = mapped_column(Integer, nullable=False, default=336)

    high_relevance_threshold: Mapped[float] = mapped_column(Float, nullable=False, default=0.8)
    ai_consecutive_low_threshold: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
