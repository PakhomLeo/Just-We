"""Full fetch pipeline orchestrator for monitored accounts."""

import asyncio
import hashlib
import logging
import random
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import FetchFailedException
from app.models.article import Article
from app.models.collector_account import CollectorAccountType
from app.models.fetch_job import FetchJobType
from app.repositories.monitored_account_repo import MonitoredAccountRepository
from app.services.ai_service import AIService
from app.services.article_service import ArticleService
from app.services.collector_account_service import CollectorAccountService
from app.services.dynamic_weight_adjuster import DynamicWeightAdjuster
from app.services.fetch_job_service import FetchJobService
from app.services.fetcher_service import FetcherService
from app.services.notification_service import NotificationService
from app.services.parser_service import ParserService
from app.services.scheduler_service import SchedulerService
from app.services.system_config_service import SystemConfigService
from app.services.weight_config_service import WeightConfigService

settings = get_settings()
logger = logging.getLogger(__name__)


class FetchPipelineService:
    """Execute the monitored account fetch pipeline."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.monitored_repo = MonitoredAccountRepository(db)
        self.collector_service = CollectorAccountService(db)
        self.fetcher = FetcherService(db)
        self.parser = ParserService()
        self.article_service = ArticleService(db)
        self.ai_service = AIService(db=db)
        self.fetch_job_service = FetchJobService(db)
        self.scheduler_service = SchedulerService(db)
        self.notification_service = NotificationService(db)
        self.system_config_service = SystemConfigService(db)
        self.adjuster = DynamicWeightAdjuster()

    async def _build_adjuster(self) -> DynamicWeightAdjuster:
        config = await WeightConfigService(self.db).get_or_create()
        return DynamicWeightAdjuster(**WeightConfigService.to_adjuster_kwargs(config))

    def _schedule_monitored_account(self, monitored_account_id: int, tier: int):
        from app.tasks.fetch_task import run_single_account

        interval_hours = self.adjuster.check_intervals.get(tier, 72)
        self.scheduler_service.schedule_next_fetch(monitored_account_id, interval_hours, run_single_account)
        return self.scheduler_service.get_next_run_at(interval_hours)

    def _schedule_article_ai_analysis(self, article_ids: list[int]) -> None:
        if not article_ids:
            return
        from app.tasks.ai_task import run_article_ai_analysis

        for article_id in article_ids:
            task = asyncio.create_task(run_article_ai_analysis(article_id))
            task.add_done_callback(self._log_ai_task_result)

    @staticmethod
    def _log_ai_task_result(task: asyncio.Task) -> None:
        try:
            result = task.result()
            if not result.get("success"):
                logger.info("Background AI analysis finished with non-success result: %s", result)
        except asyncio.CancelledError:
            logger.info("Background AI analysis task was cancelled")
        except Exception:
            logger.exception("Background AI analysis task failed")

    async def _count_consecutive_low_relevance(self, history: dict) -> int:
        if not history:
            return 0
        config = await WeightConfigService(self.db).get_or_create()
        ranked_items = []
        for timestamp, item in history.items():
            ranked_items.append((self._parse_datetime(timestamp) or datetime.min.replace(tzinfo=timezone.utc), item))
        count = 0
        for _, item in sorted(ranked_items, key=lambda pair: pair[0], reverse=True):
            ratio = item.get("ratio") if isinstance(item, dict) else None
            if ratio is None or ratio >= config.high_relevance_threshold:
                break
            count += 1
        return count

    async def _select_collector(self, monitored_account):
        policy = await self.system_config_service.get_or_create_fetch_policy()
        policy_mode = CollectorAccountType(
            policy.primary_modes.get(str(monitored_account.current_tier), monitored_account.primary_fetch_mode.value)
        )
        metadata = monitored_account.metadata_json or {}
        is_weread_platform_account = (
            metadata.get("resolve_source") == "weread_platform"
            or bool(metadata.get("weread_platform_mp_id"))
        )
        if is_weread_platform_account:
            candidate_modes = [
                monitored_account.primary_fetch_mode,
                policy_mode,
                monitored_account.fallback_fetch_mode,
                CollectorAccountType.WEREAD,
                CollectorAccountType.MP_ADMIN,
            ]
        else:
            candidate_modes = [policy_mode, monitored_account.primary_fetch_mode, monitored_account.fallback_fetch_mode]
        seen_modes: set[CollectorAccountType] = set()
        for fetch_mode in candidate_modes:
            if fetch_mode is None or fetch_mode in seen_modes:
                continue
            seen_modes.add(fetch_mode)
            accounts = await self.collector_service.repo.get_by_owner_and_type(monitored_account.owner_user_id, fetch_mode)
            healthy = [a for a in accounts if self.collector_service.is_available_for_fetch(a)]
            if healthy:
                collector = random.choice(healthy)
                if monitored_account.primary_fetch_mode != fetch_mode or monitored_account.fallback_fetch_mode is not None:
                    await self.monitored_repo.update(
                        monitored_account,
                        primary_fetch_mode=fetch_mode,
                        fallback_fetch_mode=None,
                    )
                return collector
        if not is_weread_platform_account and (
            monitored_account.primary_fetch_mode != policy_mode or monitored_account.fallback_fetch_mode is not None
        ):
            await self.monitored_repo.update(
                monitored_account,
                primary_fetch_mode=policy_mode,
                fallback_fetch_mode=None,
            )
        return None

    async def _run_update_list_stage(self, monitored, collector) -> list:
        job = await self.fetch_job_service.create_job(monitored.id, FetchJobType.UPDATE_LIST)
        await self.fetch_job_service.mark_running(
            job,
            collector_account_id=collector.id,
            fetch_mode=collector.account_type,
            payload={"stage": "update_list"},
        )
        try:
            updates = await self.fetcher.fetch_updates(monitored, collector)
            await self.fetch_job_service.mark_success(
                job,
                payload={"stage": "update_list", "updates_found": len(updates)},
            )
            return updates
        except Exception as exc:
            if isinstance(exc, FetchFailedException):
                category = exc.details.get("category", "temporary_failure")
                retryable = exc.details.get("retryable", True)
                await self.fetch_job_service.mark_failed(
                    job,
                    str(exc),
                    payload={
                        "stage": "update_list",
                        "failure_category": category,
                        "retryable": retryable,
                    },
                )
            else:
                await self.fetch_job_service.mark_failed(
                    job,
                    str(exc),
                    payload={
                        "stage": "update_list",
                        "failure_category": "unclassified",
                        "retryable": True,
                    },
                )
            raise

    async def _run_article_detail_stage(self, monitored, collector, update):
        job = await self.fetch_job_service.create_job(monitored.id, FetchJobType.ARTICLE_DETAIL)
        await self.fetch_job_service.mark_running(
            job,
            collector_account_id=collector.id,
            fetch_mode=collector.account_type,
            payload={
                "stage": "article_detail",
                "url": update.url,
                "title": update.title,
            },
        )
        try:
            detail = await self.fetcher.fetch_article_detail(update.url, collector)
            await self.fetch_job_service.mark_success(
                job,
                payload={
                    "stage": "article_detail",
                    "url": update.url,
                    "title": detail.get("title") or update.title,
                },
            )
            return detail
        except Exception as exc:
            if isinstance(exc, FetchFailedException):
                category = exc.details.get("category", "temporary_failure")
                retryable = exc.details.get("retryable", True)
                await self.fetch_job_service.mark_failed(
                    job,
                    str(exc),
                    payload={
                        "stage": "article_detail",
                        "url": update.url,
                        "title": update.title,
                        "failure_category": category,
                        "retryable": retryable,
                    },
                )
            else:
                await self.fetch_job_service.mark_failed(
                    job,
                    str(exc),
                    payload={
                        "stage": "article_detail",
                        "url": update.url,
                        "title": update.title,
                        "failure_category": "unclassified",
                        "retryable": True,
                    },
                )
            raise

    async def run_monitored_account(self, monitored_account_id: int) -> dict:
        monitored = await self.monitored_repo.get_by_id(monitored_account_id)
        if monitored is None:
            return {"success": False, "error": "Monitored account not found"}
        if type(self.adjuster) is DynamicWeightAdjuster:
            self.adjuster = await self._build_adjuster()

        collector = await self._select_collector(monitored)
        job = await self.fetch_job_service.create_job(monitored_account_id, FetchJobType.FULL_SYNC)
        if collector is None:
            await self.fetch_job_service.mark_failed(job, "No available collector account")
            await self.notification_service.create_notification(
                owner_user_id=monitored.owner_user_id,
                notification_type="collector_unavailable",
                title="无可用抓取账号",
                content=f"监测对象 {monitored.name} 当前没有可用抓取账号，自动抓取已中断。",
                monitored_account_id=monitored.id,
            )
            return {"success": False, "error": "No available collector account"}

        await self.fetch_job_service.mark_running(
            job,
            collector_account_id=collector.id,
            fetch_mode=collector.account_type,
        )

        try:
            updates = await self._run_update_list_stage(monitored, collector)
            unique_updates = []
            seen_urls = set()
            for update in updates:
                if update.url in seen_urls:
                    continue
                seen_urls.add(update.url)
                existing = await self.article_service.get_article_by_url(update.url)
                if existing is not None:
                    continue
                unique_updates.append(update)
            saved_articles = []
            queued_ai_article_ids: list[int] = []
            for update in unique_updates:
                detail = await self._run_article_detail_stage(monitored, collector, update)
                detail_proxy = await self.fetcher.get_detail_proxy_for_mode(collector.account_type)
                localize_images = collector.account_type != CollectorAccountType.WEREAD
                parsed = await self.parser.parse_article(
                    detail.get("raw_content", ""),
                    download_images=localize_images,
                    storage_id=monitored.id,
                    proxy=detail_proxy,
                )
                fingerprint = hashlib.sha256(parsed.content.encode("utf-8")).hexdigest()
                localized_images = [
                    self.parser.image_downloader.to_public_url(path) or path
                    for path in parsed.images
                ]
                localized_cover_image = None
                cover_source = detail.get("cover_image") or update.cover_image
                if cover_source and localize_images:
                    local_cover = await self.parser.image_downloader.download_image(
                        cover_source,
                        monitored.id,
                        proxy=detail_proxy,
                    )
                    localized_cover_image = self.parser.image_downloader.to_public_url(local_cover) if local_cover else cover_source
                elif cover_source:
                    localized_cover_image = cover_source
                article = await self.article_service.save_article(
                    monitored_account_id=monitored.id,
                    title=detail.get("title") or parsed.title or update.title,
                    content=parsed.content,
                    content_html=parsed.content_html,
                    content_type=parsed.content_type,
                    raw_content=detail.get("raw_content"),
                    images=localized_images,
                    original_images=parsed.original_images or [],
                    cover_image=localized_cover_image,
                    author=detail.get("author") or update.author,
                    url=update.url,
                    published_at=self._parse_datetime(detail.get("published_at") or update.published_at),
                    ai_relevance_ratio=None,
                    ai_judgment=None,
                    ai_text_analysis=None,
                    ai_image_analysis=None,
                    ai_type_judgment=None,
                    ai_combined_analysis=None,
                    ai_target_match=None,
                    ai_analysis_status="pending",
                    ai_analysis_error=None,
                    fetch_mode=collector.account_type.value,
                    content_fingerprint=fingerprint,
                    source_payload=update.source_payload,
                )
                saved_articles.append(article)
                if isinstance(article, Article) and isinstance(getattr(article, "id", None), int):
                    queued_ai_article_ids.append(article.id)

            weight_update = self.adjuster.update_after_fetch(monitored, saved_articles, None)
            latest_published = max(
                [a.published_at for a in saved_articles if a.published_at] or [monitored.last_published_at],
                key=lambda value: value or datetime.min.replace(tzinfo=timezone.utc),
            )
            next_run_at = self._schedule_monitored_account(monitored.id, weight_update["new_tier"])
            policy = await self.system_config_service.get_or_create_fetch_policy()
            next_fetch_mode = CollectorAccountType(policy.primary_modes.get(str(weight_update["new_tier"]), collector.account_type.value))
            metadata = monitored.metadata_json or {}
            if (
                metadata.get("resolve_source") == "weread_platform"
                or bool(metadata.get("weread_platform_mp_id"))
            ):
                next_fetch_mode = collector.account_type
            monitored = await self.monitored_repo.update(
                monitored,
                current_tier=weight_update["new_tier"],
                primary_fetch_mode=next_fetch_mode,
                fallback_fetch_mode=None,
                composite_score=weight_update["new_score"],
                last_polled_at=datetime.now(timezone.utc),
                last_published_at=latest_published,
                next_scheduled_at=next_run_at,
                update_history=weight_update.get("update_history", monitored.update_history),
                ai_relevance_history=weight_update.get("ai_relevance_history", monitored.ai_relevance_history),
            )
            consecutive_low_count = await self._count_consecutive_low_relevance(monitored.ai_relevance_history)
            await self.notification_service.check_and_notify_ai_consecutive_low(
                owner_user_id=monitored.owner_user_id,
                monitored_account=monitored,
                consecutive_count=consecutive_low_count,
            )
            await self.collector_service.mark_success(collector)
            await self.fetch_job_service.mark_success(
                job,
                payload={
                    "stage": "full_sync",
                    "updates_found": len(updates),
                    "new_articles": len(unique_updates),
                    "articles": len(saved_articles),
                    "ai_analysis_queued": len(queued_ai_article_ids),
                },
            )
            await self.db.commit()
            self._schedule_article_ai_analysis(queued_ai_article_ids)
            return {
                "success": True,
                "monitored_account_id": monitored.id,
                "collector_account_id": collector.id,
                "articles_processed": len(saved_articles),
                "ai_analysis_queued": len(queued_ai_article_ids),
                "new_tier": monitored.current_tier,
            }
        except Exception as exc:
            if isinstance(exc, FetchFailedException):
                category = exc.details.get("category", "temporary_failure")
                retryable = exc.details.get("retryable", True)
                await self.collector_service.mark_fetch_failure(collector, category, str(exc))
                await self.notification_service.check_and_notify_fetch_error(
                    owner_user_id=monitored.owner_user_id,
                    monitored_account=monitored,
                    collector_account=collector,
                    error_message=str(exc),
                    category=category,
                )
                next_run_at = self._schedule_monitored_account(monitored.id, monitored.current_tier)
                await self.monitored_repo.update(monitored, next_scheduled_at=next_run_at)
                await self.fetch_job_service.mark_failed(
                    job,
                    str(exc),
                    payload={"failure_category": category, "retryable": retryable},
                )
            else:
                await self.collector_service.mark_failure(collector, str(exc))
                await self.notification_service.check_and_notify_fetch_error(
                    owner_user_id=monitored.owner_user_id,
                    monitored_account=monitored,
                    collector_account=collector,
                    error_message=str(exc),
                    category="unclassified",
                )
                next_run_at = self._schedule_monitored_account(monitored.id, monitored.current_tier)
                await self.monitored_repo.update(monitored, next_scheduled_at=next_run_at)
                await self.fetch_job_service.mark_failed(
                    job,
                    str(exc),
                    payload={"failure_category": "unclassified", "retryable": True},
                )
            return {"success": False, "error": str(exc)}

    async def run_history_backfill(self, monitored_account_id: int, job_id: int | None = None) -> dict:
        """Run a single-instance history backfill wrapper around the fetch pipeline."""
        monitored = await self.monitored_repo.get_by_id(monitored_account_id)
        if monitored is None:
            return {"success": False, "error": "Monitored account not found"}

        job = await self.fetch_job_service.repo.get_by_id(job_id) if job_id else None
        if job_id is not None and job is None:
            return {
                "success": False,
                "error": f"History backfill job {job_id} not found",
                "job_id": job_id,
            }
        if job is None:
            existing = await self.fetch_job_service.get_running_history_backfill(monitored_account_id)
            if existing is not None:
                return {"success": True, "status": "already_running", "job_id": existing.id}
            job = await self.fetch_job_service.create_job(monitored_account_id, FetchJobType.HISTORY_BACKFILL)

        await self.fetch_job_service.mark_running(
            job,
            payload={
                "stage": "history_backfill",
                "page": 1,
                "begin": 0,
                "fetched_count": 0,
                "saved_count": 0,
                "failure_category": None,
                "proxy_id": None,
                "collector_account_id": None,
            },
        )
        try:
            before_count = await self.article_service.get_article_count(monitored_account_id)
            result = await self.run_monitored_account(monitored_account_id)
            after_count = await self.article_service.get_article_count(monitored_account_id)
            payload = {
                "stage": "history_backfill",
                "page": 1,
                "begin": before_count,
                "fetched_count": result.get("articles_processed", 0),
                "saved_count": max(after_count - before_count, 0),
                "failure_category": None if result.get("success") else "pipeline_failure",
                "proxy_id": None,
                "collector_account_id": result.get("collector_account_id"),
                "result": result,
            }
            if result.get("success"):
                await self.fetch_job_service.mark_success(job, payload=payload)
            else:
                await self.fetch_job_service.mark_failed(
                    job,
                    result.get("error", "History backfill failed"),
                    payload={**payload, "failure_category": "pipeline_failure"},
                )
            return {**result, "job_id": job.id}
        except Exception as exc:
            await self.fetch_job_service.mark_failed(
                job,
                str(exc),
                payload={
                    "stage": "history_backfill",
                    "failure_category": "unclassified",
                    "page": 1,
                },
            )
            return {"success": False, "error": str(exc), "job_id": job.id}

    def _aggregate_ai_results(self, results):
        ratios = [item.get("ratio", 0) for item in results if item.get("ratio") is not None]
        if not ratios:
            return {"ratio": 0.0, "reason": "No successful AI results"}
        matched_count = len([item for item in results if item.get("target_match") == "是"])
        first_match = next((item for item in results if item.get("target_match") in {"是", "不是"}), {})
        return {
            "ratio": sum(ratios) / len(ratios),
            "reason": f"Aggregated from {len(ratios)} items; matched {matched_count}",
            "target_match": "是" if matched_count else ("不是" if first_match else None),
            "target_type": first_match.get("target_type"),
            "text_analysis": first_match.get("text_analysis"),
            "image_analysis": first_match.get("image_analysis"),
        }

    def _parse_datetime(self, value):
        if not value:
            return None
        if isinstance(value, datetime):
            return value
        try:
            if isinstance(value, (int, float)):
                return datetime.fromtimestamp(value, tz=timezone.utc)
            return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except Exception:
            return None
