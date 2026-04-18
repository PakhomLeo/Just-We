"""
Dynamic Weight Adjuster for WeChat Public Account Monitoring.

This module implements the core algorithm for dynamically adjusting account
weights based on update frequency, recency, AI-assessed relevance, and stability.

Score Formula:
    Score = 0.35*Frequency + 0.25*Recency + 0.25*Relevance + 0.15*Stability

Author: Just-We
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Protocol

from app.core.config import get_settings


settings = get_settings()

# Default weights if not configured
DEFAULT_WEIGHT_FREQUENCY_RATIO = 0.35
DEFAULT_WEIGHT_RECENCY_RATIO = 0.25
DEFAULT_WEIGHT_RELEVANCE_RATIO = 0.25
DEFAULT_WEIGHT_STABILITY_RATIO = 0.15

# Tier thresholds
DEFAULT_TIER_THRESHOLDS = [80.0, 65.0, 50.0, 35.0]

# Check intervals in hours per tier
DEFAULT_CHECK_INTERVALS = {1: 24, 2: 48, 3: 72, 4: 144, 5: 336}

# History retention period
HISTORY_RETENTION_DAYS = 90

# Burst detection threshold
BURST_UPDATE_COUNT = 3
BURST_GRACE_PERIOD_DAYS = 30


class WeightSubject(Protocol):
    current_tier: int
    composite_score: float
    update_history: dict[str, Any]
    ai_relevance_history: dict[str, Any]
    manual_override: dict[str, Any] | None
    last_updated: datetime | None
    last_published_at: datetime | None


class DynamicWeightAdjuster:
    """
    Dynamic Weight Adjuster for calculating account scores and tiers.

    This class implements the complete weight adjustment algorithm based on:
    - Frequency: Update frequency over the past 90 days
    - Recency: Time since last update with burst bonus
    - Relevance: AI-assessed sports/relevance ratio
    - Stability: Variance in update patterns (high variance can be positive)
    """

    def __init__(
        self,
        frequency_ratio: float | None = None,
        recency_ratio: float | None = None,
        relevance_ratio: float | None = None,
        stability_ratio: float | None = None,
        tier_thresholds: list[float] | None = None,
        check_intervals: dict[int, int] | None = None,
    ):
        """Initialize with custom or default configuration."""
        self.frequency_ratio = frequency_ratio or settings.weight_frequency_ratio or DEFAULT_WEIGHT_FREQUENCY_RATIO
        self.recency_ratio = recency_ratio or settings.weight_recency_ratio or DEFAULT_WEIGHT_RECENCY_RATIO
        self.relevance_ratio = relevance_ratio or settings.weight_relevance_ratio or DEFAULT_WEIGHT_RELEVANCE_RATIO
        self.stability_ratio = stability_ratio or settings.weight_stability_ratio or DEFAULT_WEIGHT_STABILITY_RATIO

        self.tier_thresholds = tier_thresholds or settings.tier_thresholds or DEFAULT_TIER_THRESHOLDS
        self.check_intervals = check_intervals or settings.check_intervals or DEFAULT_CHECK_INTERVALS

        # Validate ratios sum to 1.0
        total_ratio = (
            self.frequency_ratio
            + self.recency_ratio
            + self.relevance_ratio
            + self.stability_ratio
        )
        if abs(total_ratio - 1.0) > 0.001:
            raise ValueError(f"Weight ratios must sum to 1.0, got {total_ratio}")

    @staticmethod
    def _as_utc_datetime(value: datetime) -> datetime:
        """Normalize naive and aware datetimes before comparing them."""
        if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    def calculate_frequency_score(
        self,
        update_history: dict[str, int],
        new_article_count: int = 0,
    ) -> float:
        """
        Calculate frequency score based on update history.

        Considers:
        - Total update days in last 90 days
        - Update density (articles per update day)
        - Burst pattern detection (sudden increase in activity)

        Args:
            update_history: Dict of {timestamp: update_count}
            new_article_count: Number of new articles in this fetch

        Returns:
            Frequency score (0-100)
        """
        if not update_history:
            return 30.0  # Default for accounts with no history

        now = datetime.now(timezone.utc)
        cutoff_date = now - timedelta(days=HISTORY_RETENTION_DAYS)

        # Filter updates within retention period
        recent_updates = {}
        for timestamp_str, count in update_history.items():
            try:
                timestamp = self._as_utc_datetime(datetime.fromisoformat(timestamp_str.replace("Z", "+00:00")))
                if timestamp >= cutoff_date:
                    recent_updates[timestamp] = count
            except (ValueError, TypeError):
                continue

        if not recent_updates:
            return 30.0

        # Calculate metrics
        total_update_days = len(recent_updates)
        total_articles = sum(recent_updates.values()) + new_article_count

        # Days since first update
        first_update = min(recent_updates.keys())
        days_active = (now - first_update).days or 1

        # Update frequency (updates per week)
        updates_per_week = (total_update_days / days_active) * 7 if days_active > 0 else 0

        # Density (articles per update)
        density = total_articles / total_update_days if total_update_days > 0 else 0

        # Base score from frequency
        frequency_score = min(100.0, updates_per_week * 10 + density * 5)

        # Burst bonus: accounts with sudden increase in activity
        if new_article_count >= BURST_UPDATE_COUNT:
            # Check if this is unusual
            avg_articles = total_articles / max(1, total_update_days)
            if new_article_count > avg_articles * 2:
                frequency_score = min(100.0, frequency_score + 15)

        return frequency_score

    def calculate_recency_score(
        self,
        last_updated: datetime | None,
        update_history: dict[str, int],
        new_article_count: int = 0,
    ) -> float:
        """
        Calculate recency score based on time since last update.

        Considers:
        - Days since last update
        - Burst bonus for long-dormant accounts that suddenly update

        Args:
            last_updated: Last update timestamp
            update_history: Dict of {timestamp: update_count}
            new_article_count: Number of new articles in this fetch

        Returns:
            Recency score (0-100)
        """
        if last_updated is None:
            # Never updated
            return 50.0

        now = datetime.now(timezone.utc)
        last_updated = self._as_utc_datetime(last_updated)
        days_since_update = (now - last_updated).days

        if days_since_update <= 1:
            return 95.0  # Very recent
        elif days_since_update <= 3:
            return 80.0
        elif days_since_update <= 7:
            return 65.0
        elif days_since_update <= 14:
            return 50.0
        elif days_since_update <= 30:
            return 35.0
        else:
            # More than 30 days - check for burst pattern
            base_score = max(15.0, 35.0 - (days_since_update - 30) * 0.5)

            # Burst bonus: long silence followed by significant update
            if new_article_count >= BURST_UPDATE_COUNT and days_since_update > BURST_GRACE_PERIOD_DAYS:
                base_score = min(100.0, base_score + 35)

            return base_score

    def calculate_relevance_score(
        self,
        ai_relevance_history: dict[str, dict[str, Any]],
        ai_result: dict[str, Any] | None = None,
    ) -> float:
        """
        Calculate relevance score based on AI analysis history.

        Considers:
        - Average relevance ratio over recent history
        - Trend (improving or declining)
        - Current fetch relevance if available

        Args:
            ai_relevance_history: Dict of {timestamp: {ratio, reason}}
            ai_result: Current AI analysis result {ratio, reason}

        Returns:
            Relevance score (0-100)
        """
        # Start with base score of 50
        base_score = 50.0

        if not ai_relevance_history and ai_result is None:
            return base_score

        # Calculate average from history
        ratios = []
        for timestamp, data in ai_relevance_history.items():
            if isinstance(data, dict) and "ratio" in data:
                ratio = data.get("ratio")
                if ratio is not None:
                    ratios.append(ratio)

        # Add current result if available
        current_ratio = None
        if ai_result and isinstance(ai_result, dict):
            current_ratio = ai_result.get("ratio")
            if current_ratio is not None:
                ratios.append(current_ratio)

        if not ratios:
            return base_score

        # Average relevance
        avg_relevance = sum(ratios) / len(ratios)

        # Convert relevance (0-1) to score (0-100)
        relevance_score = avg_relevance * 100

        # Penalty for low relevance (< 0.5)
        low_relevance_count = sum(1 for r in ratios if r < 0.5)
        if low_relevance_count >= 3:
            relevance_score = max(20.0, relevance_score - 15)

        # Bonus for consistently high relevance
        high_relevance_count = sum(1 for r in ratios if r >= 0.8)
        if high_relevance_count >= 5:
            relevance_score = min(100.0, relevance_score + 10)

        return relevance_score

    def calculate_stability_score(
        self,
        update_history: dict[str, int],
    ) -> float:
        """
        Calculate stability score based on update variance.

        Note: High variance (burst + silence) is actually positive for this
        system's purpose - it indicates an active but irregular publisher.

        Args:
            update_history: Dict of {timestamp: update_count}

        Returns:
            Stability score (0-100)
        """
        if not update_history or len(update_history) < 2:
            return 50.0  # Default for insufficient data

        now = datetime.now(timezone.utc)
        cutoff_date = now - timedelta(days=HISTORY_RETENTION_DAYS)

        # Filter updates within retention period
        recent_updates = []
        for timestamp_str, count in update_history.items():
            try:
                timestamp = self._as_utc_datetime(datetime.fromisoformat(timestamp_str.replace("Z", "+00:00")))
                if timestamp >= cutoff_date:
                    recent_updates.append((timestamp, count))
            except (ValueError, TypeError):
                continue

        if len(recent_updates) < 2:
            return 50.0

        # Sort by timestamp
        recent_updates.sort(key=lambda x: x[0])

        # Calculate variance in update intervals
        intervals = []
        for i in range(1, len(recent_updates)):
            interval_days = (recent_updates[i][0] - recent_updates[i - 1][0]).days
            intervals.append(interval_days)

        if not intervals:
            return 50.0

        avg_interval = sum(intervals) / len(intervals)
        variance = sum((i - avg_interval) ** 2 for i in intervals) / len(intervals)

        # Lower variance = more stable = higher stability score
        # But very regular (low variance) might be less interesting
        # We want to reward some variance (irregular but active publishers)

        if variance == 0:
            return 60.0  # Perfectly regular

        # Normalize variance (expected range 0-100)
        normalized_variance = min(100.0, variance / 10)

        # Higher variance gets moderate score (irregular but active)
        # Very low variance gets slightly lower score (too predictable)
        # Moderate variance gets highest score (interesting publisher)
        if normalized_variance < 20:
            return 55.0 + normalized_variance * 0.5
        elif normalized_variance < 50:
            return 65.0 + (normalized_variance - 20) * 0.5
        else:
            return 80.0  # High variance but still active

    def calculate_score(
        self,
        account: WeightSubject,
        new_article_count: int = 0,
        ai_result: dict[str, Any] | None = None,
    ) -> float:
        """
        Calculate the composite score for a monitored account.

        Score = 0.35*Frequency + 0.25*Recency + 0.25*Relevance + 0.15*Stability

        Args:
            account: Monitored account-like object
            new_article_count: Number of new articles in this fetch
            ai_result: AI analysis result for current fetch

        Returns:
            Composite score (0-100)
        """
        # Calculate individual components
        frequency = self.calculate_frequency_score(
            account.update_history or {},
            new_article_count,
        )

        recency_source = getattr(account, "last_published_at", None) or getattr(account, "last_updated", None)
        recency = self.calculate_recency_score(
            recency_source,
            account.update_history or {},
            new_article_count,
        )

        relevance = self.calculate_relevance_score(
            account.ai_relevance_history or {},
            ai_result,
        )

        stability = self.calculate_stability_score(
            account.update_history or {},
        )

        # Weighted composite score
        composite = (
            self.frequency_ratio * frequency
            + self.recency_ratio * recency
            + self.relevance_ratio * relevance
            + self.stability_ratio * stability
        )

        return round(composite, 2)

    def determine_tier(self, score: float) -> int:
        """
        Determine tier based on score.

        Tier 1: score >= 80 (highest priority, 24h check interval)
        Tier 2: score >= 65 (high priority, 48h check interval)
        Tier 3: score >= 50 (medium priority, 72h check interval)
        Tier 4: score >= 35 (low priority, 144h check interval)
        Tier 5: score < 35 (lowest priority, 336h check interval)

        Args:
            score: Composite score (0-100)

        Returns:
            Tier (1-5)
        """
        if score >= self.tier_thresholds[0]:  # 80
            return 1
        elif score >= self.tier_thresholds[1]:  # 65
            return 2
        elif score >= self.tier_thresholds[2]:  # 50
            return 3
        elif score >= self.tier_thresholds[3]:  # 35
            return 4
        else:
            return 5

    def apply_manual_override(self, account: WeightSubject) -> bool:
        """
        Check if manual override is active and apply it.

        Args:
            account: Monitored account-like object

        Returns:
            True if manual override is active, False otherwise
        """
        if account.manual_override is None:
            return False

        # Check if expired
        expire_at_str = account.manual_override.get("expire_at")
        if expire_at_str:
            try:
                expire_at = datetime.fromisoformat(expire_at_str.replace("Z", "+00:00"))
                if datetime.now(timezone.utc) > expire_at:
                    return False  # Override expired
            except (ValueError, TypeError):
                return False

        return True

    def get_next_check_interval(self, account: WeightSubject) -> int:
        """
        Get the next check interval in hours based on tier.

        Args:
            account: Monitored account-like object

        Returns:
            Check interval in hours
        """
        return self.check_intervals.get(account.current_tier, 72)

    def update_after_fetch(
        self,
        account: WeightSubject,
        new_articles: list[dict[str, Any]],
        ai_result: dict[str, Any] | None,
        fetch_time: datetime | None = None,
    ) -> dict[str, Any]:
        """
        Update account after a fetch operation.

        This is the main entry point for weight adjustment after fetching.

        Args:
            account: Monitored account-like object
            new_articles: List of new articles fetched
            ai_result: AI analysis result for the articles
            fetch_time: Timestamp of the fetch (defaults to now)

        Returns:
            Dict with new_score, new_tier, next_interval_hours, tier_changed
        """
        if fetch_time is None:
            fetch_time = datetime.now(timezone.utc)

        new_article_count = len(new_articles)

        # Store old values for comparison
        old_tier = account.current_tier
        old_score = account.composite_score

        # Check manual override first
        if self.apply_manual_override(account):
            return {
                "new_score": old_score,
                "new_tier": account.manual_override["target_tier"],
                "next_interval_hours": self.check_intervals.get(
                    account.manual_override["target_tier"], 72
                ),
                "tier_changed": old_tier != account.manual_override["target_tier"],
                "override_active": True,
            }

        # Calculate new score
        new_score = self.calculate_score(
            account,
            new_article_count=new_article_count,
            ai_result=ai_result,
        )

        # Determine new tier
        new_tier = self.determine_tier(new_score)

        # Update history
        timestamp_str = fetch_time.isoformat()

        # Update update_history
        update_history = dict(account.update_history or {})
        update_history[timestamp_str] = new_article_count

        # Clean old entries (older than 90 days)
        cutoff = fetch_time - timedelta(days=HISTORY_RETENTION_DAYS)
        update_history = {
            k: v
            for k, v in update_history.items()
            if datetime.fromisoformat(k.replace("Z", "+00:00")) >= cutoff
        }

        # Update ai_relevance_history
        ai_relevance_history = dict(account.ai_relevance_history or {})
        if ai_result and isinstance(ai_result, dict):
            ai_relevance_history[timestamp_str] = {
                "ratio": ai_result.get("ratio", 0),
                "reason": ai_result.get("reason", ""),
                "match": ai_result.get("target_match"),
                "target_type": ai_result.get("target_type"),
                "text_summary": (ai_result.get("text_analysis") or {}).get("summary") if isinstance(ai_result.get("text_analysis"), dict) else None,
                "image_summary": (ai_result.get("image_analysis") or {}).get("summary") if isinstance(ai_result.get("image_analysis"), dict) else None,
            }

        # Clean old AI history
        ai_relevance_history = {
            k: v
            for k, v in ai_relevance_history.items()
            if datetime.fromisoformat(k.replace("Z", "+00:00")) >= cutoff
        }

        # Get next check interval
        next_interval = self.check_intervals.get(new_tier, 72)

        return {
            "new_score": new_score,
            "new_tier": new_tier,
            "next_interval_hours": next_interval,
            "tier_changed": old_tier != new_tier,
            "override_active": False,
            "update_history": update_history,
            "ai_relevance_history": ai_relevance_history,
            "score_breakdown": {
                "frequency": self.calculate_frequency_score(
                    account.update_history or {}, new_article_count
                ),
                "recency": self.calculate_recency_score(
                    getattr(account, "last_published_at", None) or getattr(account, "last_updated", None),
                    account.update_history or {},
                    new_article_count,
                ),
                "relevance": self.calculate_relevance_score(
                    account.ai_relevance_history or {}, ai_result
                ),
                "stability": self.calculate_stability_score(account.update_history or {}),
            },
        }

    def simulate_score(
        self,
        update_history: dict[str, int],
        ai_relevance_history: dict[str, dict[str, Any]],
        last_updated: str | None,
        new_article_count: int,
        ai_result: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Simulate score calculation without modifying account.

        Useful for testing and previews.

        Args:
            update_history: Current update history dict
            ai_relevance_history: Current AI relevance history dict
            last_updated: ISO timestamp string of last update
            new_article_count: Number of new articles
            ai_result: AI result for current fetch

        Returns:
            Dict with new_score, new_tier, next_interval_hours, score_breakdown
        """
        # Parse last_updated
        last_updated_dt = None
        if last_updated:
            try:
                last_updated_dt = datetime.fromisoformat(last_updated.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                pass

        # Calculate components
        frequency = self.calculate_frequency_score(update_history, new_article_count)
        recency = self.calculate_recency_score(
            last_updated_dt, update_history, new_article_count
        )
        relevance = self.calculate_relevance_score(ai_relevance_history, ai_result)
        stability = self.calculate_stability_score(update_history)

        # Calculate composite score
        new_score = (
            self.frequency_ratio * frequency
            + self.recency_ratio * recency
            + self.relevance_ratio * relevance
            + self.stability_ratio * stability
        )
        new_score = round(new_score, 2)

        # Determine tier
        new_tier = self.determine_tier(new_score)

        return {
            "new_score": new_score,
            "new_tier": new_tier,
            "next_interval_hours": self.check_intervals.get(new_tier, 72),
            "score_breakdown": {
                "frequency": round(frequency, 2),
                "recency": round(recency, 2),
                "relevance": round(relevance, 2),
                "stability": round(stability, 2),
            },
        }
