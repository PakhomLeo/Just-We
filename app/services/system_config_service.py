"""Services for singleton system configuration."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.system_config import AIAnalysisConfig, FetchPolicy, NotificationEmailConfig
from app.repositories.system_config_repo import (
    AIAnalysisConfigRepository,
    FetchPolicyRepository,
    NotificationEmailConfigRepository,
)


settings = get_settings()


class SystemConfigService:
    """Read/write singleton configs with defaults."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.ai_repo = AIAnalysisConfigRepository(db)
        self.fetch_repo = FetchPolicyRepository(db)
        self.notification_repo = NotificationEmailConfigRepository(db)

    async def get_or_create_ai_config(self) -> AIAnalysisConfig:
        config = await self.ai_repo.get_first()
        if config:
            return config
        config = AIAnalysisConfig(
            api_url=settings.llm_api_url,
            api_key=settings.llm_api_key or "test-key",
            model=settings.llm_model,
            prompt_template=(
                "分析以下微信公众号文章内容及图片，返回 JSON："
                '{"ratio":0-1,"reason":"...","keywords":[],"summary":"...","category":"..."}'
                "\n内容：{{content}}"
            ),
            enabled=True,
        )
        self.db.add(config)
        await self.db.flush()
        await self.db.refresh(config)
        return config

    async def update_ai_config(self, **kwargs) -> AIAnalysisConfig:
        config = await self.get_or_create_ai_config()
        for key, value in kwargs.items():
            setattr(config, key, value)
        await self.db.flush()
        await self.db.refresh(config)
        return config

    async def get_or_create_fetch_policy(self) -> FetchPolicy:
        policy = await self.fetch_repo.get_first()
        if policy:
            return policy
        policy = FetchPolicy(
            tier_thresholds={
                "tier1": settings.tier_threshold_tier1,
                "tier2": settings.tier_threshold_tier2,
                "tier3": settings.tier_threshold_tier3,
                "tier4": settings.tier_threshold_tier4,
            },
            check_intervals={str(k): v for k, v in settings.check_intervals.items()},
            primary_modes={"1": "weread", "2": "weread", "3": "mp_admin", "4": "mp_admin", "5": "mp_admin"},
            retry_limit=2,
            retry_backoff_seconds=30,
            random_delay_min_ms=500,
            random_delay_max_ms=2000,
        )
        self.db.add(policy)
        await self.db.flush()
        await self.db.refresh(policy)
        return policy

    async def update_fetch_policy(self, **kwargs) -> FetchPolicy:
        policy = await self.get_or_create_fetch_policy()
        for key, value in kwargs.items():
            setattr(policy, key, value)
        await self.db.flush()
        await self.db.refresh(policy)
        return policy

    async def get_or_create_notification_email_config(self) -> NotificationEmailConfig:
        config = await self.notification_repo.get_first()
        if config:
            return config
        config = NotificationEmailConfig(
            enabled=False,
            smtp_host="",
            smtp_port=587,
            smtp_username="",
            smtp_password="",
            from_email="",
            to_emails=[],
            use_tls=True,
        )
        self.db.add(config)
        await self.db.flush()
        await self.db.refresh(config)
        return config

    async def update_notification_email_config(self, **kwargs) -> NotificationEmailConfig:
        config = await self.get_or_create_notification_email_config()
        for key, value in kwargs.items():
            setattr(config, key, value)
        await self.db.flush()
        await self.db.refresh(config)
        return config
