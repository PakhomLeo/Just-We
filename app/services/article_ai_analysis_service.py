"""Background AI analysis service for saved articles."""

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.proxy import ProxyServiceKey
from app.repositories.article_repo import ArticleRepository
from app.repositories.monitored_account_repo import MonitoredAccountRepository
from app.services.ai_service import AIService
from app.services.article_service import ArticleService
from app.services.dynamic_weight_adjuster import DynamicWeightAdjuster
from app.services.notification_service import NotificationService
from app.services.proxy_service import ProxyService
from app.services.weight_config_service import WeightConfigService

HISTORY_RETENTION_DAYS = 90


class ArticleAIAnalysisService:
    """Run the AI pipeline for an already-saved article without blocking fetch."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.article_service = ArticleService(db)
        self.article_repo = ArticleRepository(db)
        self.monitored_repo = MonitoredAccountRepository(db)
        self.proxy_service = ProxyService(db)
        self.notification_service = NotificationService(db)

    async def _analyze_with_proxy_fallback(self, content: str, images: list[str]) -> dict[str, Any]:
        ai_service = AIService(db=self.db)
        proxy = await self.proxy_service.select_proxy(ProxyServiceKey.AI)
        if proxy is None:
            return await ai_service.analyze_article_pipeline(content, images)
        try:
            result = await ai_service.analyze_article_pipeline(content, images, proxy=proxy.proxy_url)
            if result.get("status") != "failed":
                await self.proxy_service.mark_proxy_success(proxy)
                return result
            await self.proxy_service.mark_proxy_failure(
                proxy,
                result.get("ai_analysis_error") or "AI analysis failed",
                cooldown_seconds=120,
            )
        except Exception as exc:
            await self.proxy_service.mark_proxy_failure(proxy, str(exc), cooldown_seconds=120)
        return await ai_service.analyze_article_pipeline(content, images)

    def _append_ai_history(self, history: dict | None, ai_result: dict[str, Any]) -> dict[str, Any]:
        now = datetime.now(timezone.utc)
        next_history = dict(history or {})
        next_history[now.isoformat()] = {
            "ratio": ai_result.get("ratio", 0),
            "reason": ai_result.get("reason", ""),
            "match": ai_result.get("target_match"),
            "target_type": ai_result.get("target_type"),
            "text_summary": (
                (ai_result.get("text_analysis") or {}).get("summary")
                if isinstance(ai_result.get("text_analysis"), dict)
                else None
            ),
            "image_summary": (
                (ai_result.get("image_analysis") or {}).get("summary")
                if isinstance(ai_result.get("image_analysis"), dict)
                else None
            ),
        }
        cutoff = now - timedelta(days=HISTORY_RETENTION_DAYS)
        return {
            key: value
            for key, value in next_history.items()
            if datetime.fromisoformat(key.replace("Z", "+00:00")) >= cutoff
        }

    async def _apply_ai_account_effects(self, article, pipeline: dict[str, Any]) -> None:
        if not article.monitored_account_id or pipeline.get("status") != "success":
            return
        monitored = await self.monitored_repo.get_by_id(article.monitored_account_id)
        if monitored is None:
            return

        ai_result = pipeline.get("ai_judgment") or {}
        config = await WeightConfigService(self.db).get_or_create()
        adjuster = DynamicWeightAdjuster(**WeightConfigService.to_adjuster_kwargs(config))
        ai_history = self._append_ai_history(monitored.ai_relevance_history, ai_result)
        new_score = adjuster.calculate_score(monitored, new_article_count=0, ai_result=ai_result)
        new_tier = adjuster.determine_tier(new_score)
        monitored = await self.monitored_repo.update(
            monitored,
            current_tier=new_tier,
            composite_score=new_score,
            ai_relevance_history=ai_history,
        )

        ratio = pipeline.get("ratio") or 0.0
        if ratio >= config.high_relevance_threshold:
            await self.notification_service.create_notification(
                owner_user_id=monitored.owner_user_id,
                notification_type="high_relevance",
                title=f"高相关文章发现 ({ratio:.0%})",
                content=f"监测对象 {monitored.name} 的文章《{article.title}》相关度达到 {ratio:.0%}",
                monitored_account_id=monitored.id,
                article_id=article.id,
                payload={"relevance_ratio": ratio, "article_url": article.url},
            )

        low_count = 0
        for item in reversed(list(ai_history.values())):
            ratio_value = item.get("ratio") if isinstance(item, dict) else None
            if ratio_value is None or ratio_value >= config.high_relevance_threshold:
                break
            low_count += 1
        await self.notification_service.check_and_notify_ai_consecutive_low(
            owner_user_id=monitored.owner_user_id,
            monitored_account=monitored,
            consecutive_count=low_count,
        )

    async def run_article(self, article_id: int) -> dict[str, Any]:
        article = await self.article_repo.get_visible_by_id(article_id)
        if article is None:
            return {"success": False, "error": f"Article {article_id} not found"}

        await self.article_service.mark_ai_pending(article.id)
        await self.db.commit()

        pipeline = await self._analyze_with_proxy_fallback(article.content or "", article.images or [])
        updated = await self.article_service.update_ai_analysis(
            article_id=article.id,
            ai_relevance_ratio=pipeline.get("ratio"),
            ai_judgment=pipeline.get("ai_judgment"),
            ai_text_analysis=pipeline.get("ai_text_analysis"),
            ai_image_analysis=pipeline.get("ai_image_analysis"),
            ai_type_judgment=pipeline.get("ai_type_judgment"),
            ai_combined_analysis=pipeline.get("ai_combined_analysis"),
            ai_target_match=pipeline.get("ai_target_match"),
            ai_analysis_status=pipeline.get("status"),
            ai_analysis_error=pipeline.get("ai_analysis_error"),
        )
        if updated is not None:
            await self._apply_ai_account_effects(article, pipeline)
        return {
            "success": pipeline.get("status") != "failed",
            "article_id": article.id,
            "status": pipeline.get("status"),
            "error": pipeline.get("ai_analysis_error"),
        }
