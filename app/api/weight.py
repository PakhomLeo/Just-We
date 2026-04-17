"""Weight API routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import DbSession, CurrentUser, AdminUser
from app.core.config import get_settings
from app.schemas.weight import (
    WeightConfig,
    WeightConfigUpdate,
    WeightSimulateInput,
    WeightSimulateResult,
)
from app.services.dynamic_weight_adjuster import DynamicWeightAdjuster


router = APIRouter(prefix="/weight", tags=["Weight"])


@router.get("/config", response_model=WeightConfig)
async def get_weight_config(
    current_user: CurrentUser,
):
    """Get current weight configuration."""
    settings = get_settings()

    return WeightConfig(
        frequency_ratio=settings.weight_frequency_ratio,
        recency_ratio=settings.weight_recency_ratio,
        relevance_ratio=settings.weight_relevance_ratio,
        stability_ratio=settings.weight_stability_ratio,
        tier_thresholds=settings.tier_thresholds,
        check_intervals={
            str(k): v for k, v in settings.check_intervals.items()
        },
        high_relevance_threshold=settings.high_relevance_threshold,
        ai_consecutive_low_threshold=settings.ai_consecutive_low_threshold,
    )


@router.put("/config", response_model=WeightConfig)
async def update_weight_config(
    request: WeightConfigUpdate,
    current_user: AdminUser,  # Only admin can update config
):
    """Update weight configuration (admin only)."""
    # Note: In a full implementation, these would be stored in DB
    # For now, this is a placeholder that validates the request
    update_data = {k: v for k, v in request.model_dump().items() if v is not None}

    if update_data:
        # Would update settings here
        pass

    return await get_weight_config(current_user)


@router.post("/simulate", response_model=WeightSimulateResult)
async def simulate_weight_calculation(
    request: WeightSimulateInput,
    current_user: CurrentUser,
):
    """Simulate weight calculation without modifying account."""
    adjuster = DynamicWeightAdjuster()

    result = adjuster.simulate_score(
        update_history=request.update_history,
        ai_relevance_history=request.ai_relevance_history,
        last_updated=request.last_updated,
        new_article_count=request.new_article_count,
        ai_result=request.ai_result,
    )

    return WeightSimulateResult(
        new_score=result["new_score"],
        new_tier=result["new_tier"],
        next_interval_hours=result["next_interval_hours"],
        score_breakdown=result["score_breakdown"],
        tier_changed=False,  # Can't determine without current state
        override_active=False,
    )
