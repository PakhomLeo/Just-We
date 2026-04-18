"""Service for persisted weight configuration."""

from app.core.config import get_settings
from app.services.dynamic_weight_adjuster import DynamicWeightAdjuster
from app.models.weight_config import WeightConfig
from app.repositories.weight_config_repo import WeightConfigRepository
from app.schemas.weight import WeightConfigUpdate


settings = get_settings()


class WeightConfigService:
    """Read/write the singleton weight configuration."""

    def __init__(self, db):
        self.db = db
        self.repo = WeightConfigRepository(db)

    async def get_or_create(self) -> WeightConfig:
        config = await self.repo.get_first()
        if config is not None:
            return config

        config = WeightConfig(
            frequency_ratio=settings.weight_frequency_ratio,
            recency_ratio=settings.weight_recency_ratio,
            relevance_ratio=settings.weight_relevance_ratio,
            stability_ratio=settings.weight_stability_ratio,
            tier_threshold_tier1=settings.tier_threshold_tier1,
            tier_threshold_tier2=settings.tier_threshold_tier2,
            tier_threshold_tier3=settings.tier_threshold_tier3,
            tier_threshold_tier4=settings.tier_threshold_tier4,
            check_interval_tier1=settings.check_interval_tier1,
            check_interval_tier2=settings.check_interval_tier2,
            check_interval_tier3=settings.check_interval_tier3,
            check_interval_tier4=settings.check_interval_tier4,
            check_interval_tier5=settings.check_interval_tier5,
            high_relevance_threshold=settings.high_relevance_threshold,
            ai_consecutive_low_threshold=settings.ai_consecutive_low_threshold,
        )
        self.db.add(config)
        await self.db.flush()
        await self.db.refresh(config)
        return config

    async def update(self, payload: WeightConfigUpdate) -> WeightConfig:
        config = await self.get_or_create()
        update_data = payload.model_dump(exclude_none=True)
        merged_data = {
            "frequency_ratio": update_data.get("frequency_ratio", config.frequency_ratio),
            "recency_ratio": update_data.get("recency_ratio", config.recency_ratio),
            "relevance_ratio": update_data.get("relevance_ratio", config.relevance_ratio),
            "stability_ratio": update_data.get("stability_ratio", config.stability_ratio),
            "tier_thresholds": [
                update_data.get("tier_threshold_tier1", config.tier_threshold_tier1),
                update_data.get("tier_threshold_tier2", config.tier_threshold_tier2),
                update_data.get("tier_threshold_tier3", config.tier_threshold_tier3),
                update_data.get("tier_threshold_tier4", config.tier_threshold_tier4),
            ],
            "check_intervals": {
                1: update_data.get("check_interval_tier1", config.check_interval_tier1),
                2: update_data.get("check_interval_tier2", config.check_interval_tier2),
                3: update_data.get("check_interval_tier3", config.check_interval_tier3),
                4: update_data.get("check_interval_tier4", config.check_interval_tier4),
                5: update_data.get("check_interval_tier5", config.check_interval_tier5),
            },
        }
        DynamicWeightAdjuster(**merged_data)
        for key, value in update_data.items():
            setattr(config, key, value)
        await self.db.flush()
        await self.db.refresh(config)
        return config

    @staticmethod
    def to_response(config: WeightConfig):
        from app.schemas.weight import WeightConfig as WeightConfigPayload

        return WeightConfigPayload(
            frequency_ratio=config.frequency_ratio,
            recency_ratio=config.recency_ratio,
            relevance_ratio=config.relevance_ratio,
            stability_ratio=config.stability_ratio,
            tier_thresholds=[
                config.tier_threshold_tier1,
                config.tier_threshold_tier2,
                config.tier_threshold_tier3,
                config.tier_threshold_tier4,
            ],
            check_intervals={
                "1": config.check_interval_tier1,
                "2": config.check_interval_tier2,
                "3": config.check_interval_tier3,
                "4": config.check_interval_tier4,
                "5": config.check_interval_tier5,
            },
            high_relevance_threshold=config.high_relevance_threshold,
            ai_consecutive_low_threshold=config.ai_consecutive_low_threshold,
        )

    @staticmethod
    def to_adjuster_kwargs(config: WeightConfig) -> dict:
        return {
            "frequency_ratio": config.frequency_ratio,
            "recency_ratio": config.recency_ratio,
            "relevance_ratio": config.relevance_ratio,
            "stability_ratio": config.stability_ratio,
            "tier_thresholds": [
                config.tier_threshold_tier1,
                config.tier_threshold_tier2,
                config.tier_threshold_tier3,
                config.tier_threshold_tier4,
            ],
            "check_intervals": {
                1: config.check_interval_tier1,
                2: config.check_interval_tier2,
                3: config.check_interval_tier3,
                4: config.check_interval_tier4,
                5: config.check_interval_tier5,
            },
        }
