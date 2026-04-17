"""Tests for DynamicWeightAdjuster service."""

from datetime import datetime, timedelta, timezone

import pytest

from app.services.dynamic_weight_adjuster import DynamicWeightAdjuster
from app.models.account import Account


class TestDynamicWeightAdjuster:
    """Test cases for DynamicWeightAdjuster."""

    def test_calculate_frequency_score_no_history(self):
        """Test frequency score with no history."""
        adjuster = DynamicWeightAdjuster()
        score = adjuster.calculate_frequency_score({})
        assert score == 30.0

    def test_calculate_frequency_score_with_updates(self):
        """Test frequency score calculation with updates."""
        adjuster = DynamicWeightAdjuster()
        now = datetime.now(timezone.utc)

        # Create 7 days of history
        update_history = {}
        for i in range(7):
            day = now - timedelta(days=i)
            update_history[day.isoformat()] = 3  # 3 articles per day

        score = adjuster.calculate_frequency_score(update_history)
        assert 0 <= score <= 100
        assert score > 30  # Should be higher than empty history

    def test_calculate_recency_score_recent(self):
        """Test recency score for recently updated account."""
        adjuster = DynamicWeightAdjuster()
        last_updated = datetime.now(timezone.utc) - timedelta(hours=2)

        score = adjuster.calculate_recency_score(last_updated, {})
        assert score >= 90  # Very recent

    def test_calculate_recency_score_old(self):
        """Test recency score for old account."""
        adjuster = DynamicWeightAdjuster()
        last_updated = datetime.now(timezone.utc) - timedelta(days=60)

        score = adjuster.calculate_recency_score(last_updated, {}, new_article_count=0)
        assert score < 30  # Old with no burst

    def test_calculate_recency_score_burst_bonus(self):
        """Test recency score burst bonus."""
        adjuster = DynamicWeightAdjuster()
        last_updated = datetime.now(timezone.utc) - timedelta(days=45)

        # Burst: 5 new articles
        score_with_burst = adjuster.calculate_recency_score(last_updated, {}, new_article_count=5)
        score_without_burst = adjuster.calculate_recency_score(last_updated, {}, new_article_count=1)

        assert score_with_burst > score_without_burst  # Burst should give bonus

    def test_calculate_relevance_score_no_history(self):
        """Test relevance score with no history."""
        adjuster = DynamicWeightAdjuster()
        score = adjuster.calculate_relevance_score({})
        assert score == 50.0

    def test_calculate_relevance_score_with_history(self):
        """Test relevance score with AI history."""
        adjuster = DynamicWeightAdjuster()
        now = datetime.now(timezone.utc)

        ai_history = {
            (now - timedelta(days=i)).isoformat(): {"ratio": 0.6 + i * 0.05, "reason": f"Day {i}"}
            for i in range(10)
        }

        score = adjuster.calculate_relevance_score(ai_history)
        assert 0 <= score <= 100

    def test_calculate_relevance_score_low_penalty(self):
        """Test penalty for consecutive low relevance."""
        adjuster = DynamicWeightAdjuster()
        now = datetime.now(timezone.utc)

        # 5 consecutive low relevance readings
        ai_history = {
            (now - timedelta(days=i)).isoformat(): {"ratio": 0.2, "reason": f"Low day {i}"}
            for i in range(5)
        }

        score = adjuster.calculate_relevance_score(ai_history)
        assert score < 50  # Should be penalized

    def test_calculate_stability_score_no_history(self):
        """Test stability score with no history."""
        adjuster = DynamicWeightAdjuster()
        score = adjuster.calculate_stability_score({})
        assert score == 50.0

    def test_calculate_stability_score_regular(self):
        """Test stability score with regular updates."""
        adjuster = DynamicWeightAdjuster()
        now = datetime.now(timezone.utc)

        # Regular updates every day
        update_history = {
            (now - timedelta(days=i)).isoformat(): 3
            for i in range(30)
        }

        score = adjuster.calculate_stability_score(update_history)
        assert 0 <= score <= 100

    def test_calculate_score_composite(self, mock_account: Account):
        """Test composite score calculation."""
        adjuster = DynamicWeightAdjuster()

        # Mock account has no history
        score = adjuster.calculate_score(mock_account, new_article_count=2)
        assert 0 <= score <= 100

    def test_calculate_score_with_ai_result(self, mock_account: Account, sample_ai_result: dict):
        """Test score calculation with AI result."""
        adjuster = DynamicWeightAdjuster()

        score = adjuster.calculate_score(
            mock_account,
            new_article_count=3,
            ai_result=sample_ai_result,
        )
        assert 0 <= score <= 100

    def test_determine_tier_tier1(self):
        """Test tier determination for tier 1."""
        adjuster = DynamicWeightAdjuster()
        assert adjuster.determine_tier(85) == 1
        assert adjuster.determine_tier(100) == 1

    def test_determine_tier_tier2(self):
        """Test tier determination for tier 2."""
        adjuster = DynamicWeightAdjuster()
        assert adjuster.determine_tier(70) == 2
        assert adjuster.determine_tier(80) == 1  # 80 is tier 1 boundary

    def test_determine_tier_tier3(self):
        """Test tier determination for tier 3."""
        adjuster = DynamicWeightAdjuster()
        assert adjuster.determine_tier(55) == 3
        assert adjuster.determine_tier(65) == 2

    def test_determine_tier_tier4(self):
        """Test tier determination for tier 4."""
        adjuster = DynamicWeightAdjuster()
        assert adjuster.determine_tier(40) == 4
        assert adjuster.determine_tier(50) == 3

    def test_determine_tier_tier5(self):
        """Test tier determination for tier 5."""
        adjuster = DynamicWeightAdjuster()
        assert adjuster.determine_tier(30) == 5
        assert adjuster.determine_tier(35) == 4

    def test_apply_manual_override_none(self, mock_account: Account):
        """Test no manual override active."""
        adjuster = DynamicWeightAdjuster()
        assert not adjuster.apply_manual_override(mock_account)

    def test_apply_manual_override_active(self, mock_account: Account):
        """Test active manual override."""
        adjuster = DynamicWeightAdjuster()
        mock_account.manual_override = {
            "target_tier": 1,
            "reason": "VIP account",
            "expire_at": (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat(),
        }
        assert adjuster.apply_manual_override(mock_account)

    def test_apply_manual_override_expired(self, mock_account: Account):
        """Test expired manual override."""
        adjuster = DynamicWeightAdjuster()
        mock_account.manual_override = {
            "target_tier": 1,
            "reason": "VIP account",
            "expire_at": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),
        }
        assert not adjuster.apply_manual_override(mock_account)

    def test_get_next_check_interval(self, mock_account: Account):
        """Test next check interval based on tier."""
        adjuster = DynamicWeightAdjuster()

        mock_account.current_tier = 1
        assert adjuster.get_next_check_interval(mock_account) == 24

        mock_account.current_tier = 2
        assert adjuster.get_next_check_interval(mock_account) == 48

        mock_account.current_tier = 3
        assert adjuster.get_next_check_interval(mock_account) == 72

        mock_account.current_tier = 4
        assert adjuster.get_next_check_interval(mock_account) == 144

        mock_account.current_tier = 5
        assert adjuster.get_next_check_interval(mock_account) == 336

    def test_update_after_fetch_no_override(self, mock_account: Account, sample_ai_result: dict):
        """Test update after fetch without override."""
        adjuster = DynamicWeightAdjuster()

        result = adjuster.update_after_fetch(
            account=mock_account,
            new_articles=[{"title": "Test"}],
            ai_result=sample_ai_result,
        )

        assert "new_score" in result
        assert "new_tier" in result
        assert "next_interval_hours" in result
        assert "tier_changed" in result
        assert result["override_active"] is False

    def test_update_after_fetch_with_override(self, mock_account: Account):
        """Test update after fetch with active override."""
        adjuster = DynamicWeightAdjuster()
        mock_account.manual_override = {
            "target_tier": 1,
            "reason": "VIP",
            "expire_at": (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat(),
        }

        result = adjuster.update_after_fetch(
            account=mock_account,
            new_articles=[{"title": "Test"}],
            ai_result={"ratio": 0.5},
        )

        assert result["override_active"] is True
        assert result["new_tier"] == 1

    def test_update_after_fetch_updates_history(self, mock_account: Account):
        """Test that update_after_fetch updates history."""
        adjuster = DynamicWeightAdjuster()

        initial_history_len = len(mock_account.update_history or {})

        result = adjuster.update_after_fetch(
            account=mock_account,
            new_articles=[{"title": "Test1"}, {"title": "Test2"}],
            ai_result={"ratio": 0.8, "reason": "High relevance"},
        )

        assert len(result["update_history"]) > initial_history_len

    def test_simulate_score(self):
        """Test score simulation without modifying account."""
        adjuster = DynamicWeightAdjuster()

        result = adjuster.simulate_score(
            update_history={
                (datetime.now(timezone.utc) - timedelta(days=i)).isoformat(): 3
                for i in range(10)
            },
            ai_relevance_history={
                (datetime.now(timezone.utc) - timedelta(days=i)).isoformat(): {"ratio": 0.7, "reason": "Good"}
                for i in range(10)
            },
            last_updated=(datetime.now(timezone.utc) - timedelta(days=2)).isoformat(),
            new_article_count=5,
            ai_result={"ratio": 0.85},
        )

        assert "new_score" in result
        assert "new_tier" in result
        assert "next_interval_hours" in result
        assert "score_breakdown" in result
        assert "frequency" in result["score_breakdown"]
        assert "recency" in result["score_breakdown"]
        assert "relevance" in result["score_breakdown"]
        assert "stability" in result["score_breakdown"]

    def test_weight_ratios_sum_to_one(self):
        """Test that weight ratios sum to 1.0."""
        adjuster = DynamicWeightAdjuster()

        total = (
            adjuster.frequency_ratio
            + adjuster.recency_ratio
            + adjuster.relevance_ratio
            + adjuster.stability_ratio
        )
        assert abs(total - 1.0) < 0.001

    def test_custom_configuration(self):
        """Test custom weight configuration."""
        adjuster = DynamicWeightAdjuster(
            frequency_ratio=0.40,
            recency_ratio=0.20,
            relevance_ratio=0.30,
            stability_ratio=0.10,
            tier_thresholds=[85, 70, 55, 40],
        )

        assert adjuster.frequency_ratio == 0.40
        assert adjuster.recency_ratio == 0.20
        assert adjuster.relevance_ratio == 0.30
        assert adjuster.stability_ratio == 0.10
        assert adjuster.tier_thresholds == [85, 70, 55, 40]

    def test_invalid_weight_ratios(self):
        """Test that invalid weight ratios raise error."""
        with pytest.raises(ValueError, match="must sum to 1.0"):
            DynamicWeightAdjuster(
                frequency_ratio=0.50,
                recency_ratio=0.50,
                relevance_ratio=0.50,  # Sum = 1.5, should fail
                stability_ratio=0.50,
            )

    def test_tier_boundaries(self):
        """Test exact tier boundary values."""
        adjuster = DynamicWeightAdjuster()

        # Test boundaries
        assert adjuster.determine_tier(80) == 1
        assert adjuster.determine_tier(79.99) == 2
        assert adjuster.determine_tier(65) == 2
        assert adjuster.determine_tier(64.99) == 3
        assert adjuster.determine_tier(50) == 3
        assert adjuster.determine_tier(49.99) == 4
        assert adjuster.determine_tier(35) == 4
        assert adjuster.determine_tier(34.99) == 5
