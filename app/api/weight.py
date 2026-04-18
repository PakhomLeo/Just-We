"""Weight API routes."""

from fastapi import APIRouter

from app.core.dependencies import DbSession, CurrentUser, AdminUser
from app.schemas.weight import (
    WeightConfig,
    WeightConfigUpdate,
    WeightSimulateInput,
    WeightSimulateResult,
)
from app.services.dynamic_weight_adjuster import DynamicWeightAdjuster
from app.services.weight_config_service import WeightConfigService


router = APIRouter(prefix="/weight", tags=["Weight"])


@router.get("/config", response_model=WeightConfig)
async def get_weight_config(
    db: DbSession,
    current_user: CurrentUser,
):
    """Get current weight configuration."""
    config = await WeightConfigService(db).get_or_create()
    return WeightConfigService.to_response(config)


@router.put("/config", response_model=WeightConfig)
async def update_weight_config(
    request: WeightConfigUpdate,
    db: DbSession,
    current_user: AdminUser,  # Only admin can update config
):
    """Update weight configuration (admin only)."""
    config = await WeightConfigService(db).update(request)
    return WeightConfigService.to_response(config)


@router.post("/simulate", response_model=WeightSimulateResult)
async def simulate_weight_calculation(
    request: WeightSimulateInput,
    db: DbSession,
    current_user: CurrentUser,
):
    """Simulate weight calculation without modifying account."""
    config = await WeightConfigService(db).get_or_create()
    adjuster = DynamicWeightAdjuster(**WeightConfigService.to_adjuster_kwargs(config))

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
