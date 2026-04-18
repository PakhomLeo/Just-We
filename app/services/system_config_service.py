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


DEFAULT_TEXT_ANALYSIS_PROMPT = """请分析以下微信公众号文章全文，并只返回 JSON。
必须输出合法 JSON，不要 Markdown，不要解释。
JSON 建议包含：summary、key_points、entities、topics、keywords、sentiment、structured_data。

文章全文：
{{content}}"""

DEFAULT_IMAGE_ANALYSIS_PROMPT = """请分析文章中的图片内容，并只返回 JSON。
必须输出合法 JSON，不要 Markdown，不要解释。
JSON 建议包含：summary、images、detected_objects、text_in_images、visual_topics、risk_notes。"""

DEFAULT_TYPE_JUDGMENT_PROMPT = """请判断这篇文章是否属于用户需要的目标类型，并只返回 JSON。
目标类型：{{target_type}}
文字解析结果：{{text_analysis}}
图片解析结果：{{image_analysis}}

必须输出合法 JSON，字段 target_match 只能是“是”或“不是”。
JSON 格式：
{"target_match":"是或不是","reason":"判断理由","confidence":0.0到1.0,"matched_signals":["依据"]}"""


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
            changed = False
            defaults = {
                "text_api_url": config.api_url,
                "text_api_key": config.api_key,
                "text_model": config.model,
                "image_api_url": config.api_url,
                "image_api_key": config.api_key,
                "image_model": config.model,
                "text_analysis_prompt": config.prompt_template or DEFAULT_TEXT_ANALYSIS_PROMPT,
                "image_analysis_prompt": DEFAULT_IMAGE_ANALYSIS_PROMPT,
                "type_judgment_prompt": DEFAULT_TYPE_JUDGMENT_PROMPT,
                "timeout_seconds": 60,
            }
            for key, value in defaults.items():
                if not getattr(config, key, None):
                    setattr(config, key, value)
                    changed = True
            if changed:
                await self.db.flush()
                await self.db.refresh(config)
            return config
        config = AIAnalysisConfig(
            api_url=settings.llm_api_url,
            api_key=settings.llm_api_key or "test-key",
            model=settings.llm_model,
            prompt_template=DEFAULT_TEXT_ANALYSIS_PROMPT,
            enabled=True,
            text_api_url=settings.llm_api_url,
            text_api_key=settings.llm_api_key or "test-key",
            text_model=settings.llm_model,
            text_enabled=True,
            image_api_url=settings.llm_api_url,
            image_api_key=settings.llm_api_key or "test-key",
            image_model=settings.llm_model,
            image_enabled=True,
            text_analysis_prompt=DEFAULT_TEXT_ANALYSIS_PROMPT,
            image_analysis_prompt=DEFAULT_IMAGE_ANALYSIS_PROMPT,
            type_judgment_prompt=DEFAULT_TYPE_JUDGMENT_PROMPT,
            target_article_type="",
            timeout_seconds=60,
        )
        self.db.add(config)
        await self.db.flush()
        await self.db.refresh(config)
        return config

    async def update_ai_config(self, **kwargs) -> AIAnalysisConfig:
        config = await self.get_or_create_ai_config()
        if not kwargs.get("text_analysis_prompt") and kwargs.get("prompt_template"):
            kwargs["text_analysis_prompt"] = kwargs["prompt_template"]
        for legacy, modern in [
            ("api_url", "text_api_url"),
            ("api_key", "text_api_key"),
            ("model", "text_model"),
        ]:
            if legacy in kwargs and not kwargs.get(modern):
                kwargs[modern] = kwargs[legacy]
        for key, value in kwargs.items():
            setattr(config, key, value)
        config.prompt_template = config.text_analysis_prompt or config.prompt_template
        config.api_url = config.text_api_url or config.api_url
        config.api_key = config.text_api_key or config.api_key
        config.model = config.text_model or config.model
        await self.db.flush()
        await self.db.refresh(config)
        return config

    async def get_or_create_fetch_policy(self) -> FetchPolicy:
        policy = await self.fetch_repo.get_first()
        if policy:
            changed = False
            rate_policy = dict(policy.rate_limit_policy or {})
            rate_defaults = {
                "global_limit_per_minute": 60,
                "account_limit_per_minute": 20,
                "proxy_limit_per_minute": 30,
                "monitored_limit_per_minute": 20,
                "detail_min_interval_seconds": 1.0,
                "proxy_failure_cooldown_seconds": 120,
                "article_content_interval_policy": {
                    "dynamic_enabled": True,
                    "min_seconds": 20,
                    "max_seconds": 180,
                },
            }
            for key, value in rate_defaults.items():
                if key not in rate_policy:
                    rate_policy[key] = value
                    changed = True
            if changed:
                policy.rate_limit_policy = rate_policy
            history_policy = dict(policy.history_backfill_policy or {})
            history_defaults = {
                "max_pages": 10,
                "page_size": 5,
                "consecutive_failure_threshold": 3,
                "daily_account_fetch_policy": {
                    "daily_runs": 2,
                    "quiet_start": "23:00",
                    "quiet_end": "06:00",
                    "allow_manual_in_quiet_window": True,
                    "allow_backlog_in_quiet_window": True,
                },
            }
            for key, value in history_defaults.items():
                if key not in history_policy:
                    history_policy[key] = value
                    changed = True
            if changed:
                policy.history_backfill_policy = history_policy
            if changed:
                await self.db.flush()
                await self.db.refresh(policy)
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
            rate_limit_policy={
                "global_limit_per_minute": 60,
                "account_limit_per_minute": 20,
                "proxy_limit_per_minute": 30,
                "monitored_limit_per_minute": 20,
                "detail_min_interval_seconds": 1.0,
                "proxy_failure_cooldown_seconds": 120,
                "article_content_interval_policy": {
                    "dynamic_enabled": True,
                    "min_seconds": 20,
                    "max_seconds": 180,
                },
            },
            proxy_policy={
                "disable_direct_wechat_fetch": True,
                "min_success_rate": 50.0,
                "proxy_failure_cooldown_seconds": 120,
                "detail_rotation_strategy": "round_robin",
                "list_sticky_ttl_seconds": 1800,
            },
            history_backfill_policy={
                "max_pages": 10,
                "page_size": 5,
                "consecutive_failure_threshold": 3,
                "daily_account_fetch_policy": {
                    "daily_runs": 2,
                    "quiet_start": "23:00",
                    "quiet_end": "06:00",
                    "allow_manual_in_quiet_window": True,
                    "allow_backlog_in_quiet_window": True,
                },
            },
            notification_policy={
                "credential_check_interval_hours": settings.collector_health_check_interval_hours,
                "expiring_notice_hours": [24, 6],
            },
        )
        self.db.add(policy)
        await self.db.flush()
        await self.db.refresh(policy)
        return policy

    async def update_fetch_policy(self, **kwargs) -> FetchPolicy:
        policy = await self.get_or_create_fetch_policy()
        for key, value in kwargs.items():
            if key in {"rate_limit_policy", "notification_policy"}:
                continue
            setattr(policy, key, value)
        await self.db.flush()
        await self.db.refresh(policy)
        return policy

    async def get_rate_limit_policy(self) -> dict:
        policy = await self.get_or_create_fetch_policy()
        return policy.rate_limit_policy or {}

    async def update_rate_limit_policy(self, **kwargs) -> FetchPolicy:
        policy = await self.get_or_create_fetch_policy()
        current = dict(policy.rate_limit_policy or {})
        if "article_content_interval_policy" in current and "article_content_interval_policy" not in kwargs:
            kwargs["article_content_interval_policy"] = current["article_content_interval_policy"]
        policy.rate_limit_policy = kwargs
        await self.db.flush()
        await self.db.refresh(policy)
        return policy

    async def get_proxy_policy(self) -> dict:
        policy = await self.get_or_create_fetch_policy()
        return policy.proxy_policy or {
            "disable_direct_wechat_fetch": True,
            "min_success_rate": 50.0,
            "proxy_failure_cooldown_seconds": 120,
            "detail_rotation_strategy": "round_robin",
            "list_sticky_ttl_seconds": 1800,
        }

    async def update_proxy_policy(self, **kwargs) -> dict:
        policy = await self.get_or_create_fetch_policy()
        policy.proxy_policy = kwargs
        await self.db.flush()
        await self.db.refresh(policy)
        return policy.proxy_policy or {}

    async def get_notification_policy(self) -> dict:
        policy = await self.get_or_create_fetch_policy()
        notification_config = await self.get_or_create_notification_email_config()
        payload = dict(policy.notification_policy or {})
        payload.setdefault("credential_check_interval_hours", settings.collector_health_check_interval_hours)
        payload.setdefault("expiring_notice_hours", [24, 6])
        payload["webhook_enabled"] = notification_config.webhook_enabled
        payload["webhook_url"] = notification_config.webhook_url
        return payload

    async def update_notification_policy(self, **kwargs) -> dict:
        webhook_enabled = bool(kwargs.pop("webhook_enabled", False))
        webhook_url = str(kwargs.pop("webhook_url", "") or "")
        policy = await self.get_or_create_fetch_policy()
        policy.notification_policy = kwargs
        notification_config = await self.get_or_create_notification_email_config()
        notification_config.webhook_enabled = webhook_enabled
        notification_config.webhook_url = webhook_url
        await self.db.flush()
        return {**kwargs, "webhook_enabled": webhook_enabled, "webhook_url": webhook_url}

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
