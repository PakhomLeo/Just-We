"""In-memory rate-limit state for fetch observability and local throttling."""

from __future__ import annotations

from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
import asyncio
import random
import time
from typing import Any

from app.core.redis import get_redis_client


class RateLimitService:
    """Small process-local limiter used to expose and enforce basic fetch pacing."""

    def __init__(self) -> None:
        self.events: dict[str, deque[datetime]] = defaultdict(deque)
        self.last_detail_at: dict[str, datetime] = {}
        self.global_limit_per_minute = 60
        self.account_limit_per_minute = 20
        self.proxy_limit_per_minute = 30
        self.monitored_limit_per_minute = 20
        self.detail_min_interval_seconds = 1.0

    def reset(self) -> None:
        """Clear process-local counters and restore default limits."""
        self.events.clear()
        self.last_detail_at.clear()
        self.global_limit_per_minute = 60
        self.account_limit_per_minute = 20
        self.proxy_limit_per_minute = 30
        self.monitored_limit_per_minute = 20
        self.detail_min_interval_seconds = 1.0

    def _prune(self, key: str, now: datetime) -> None:
        window_start = now - timedelta(minutes=1)
        while self.events[key] and self.events[key][0] < window_start:
            self.events[key].popleft()

    def record(self, key: str) -> None:
        now = datetime.now(timezone.utc)
        self._prune(key, now)
        self.events[key].append(now)

    def configure(self, policy: dict[str, Any] | None) -> None:
        if not policy:
            return
        self.global_limit_per_minute = int(policy.get("global_limit_per_minute", self.global_limit_per_minute))
        self.account_limit_per_minute = int(policy.get("account_limit_per_minute", self.account_limit_per_minute))
        self.proxy_limit_per_minute = int(policy.get("proxy_limit_per_minute", self.proxy_limit_per_minute))
        self.monitored_limit_per_minute = int(policy.get("monitored_limit_per_minute", self.monitored_limit_per_minute))
        self.detail_min_interval_seconds = float(policy.get("detail_min_interval_seconds", self.detail_min_interval_seconds))
        article_policy = policy.get("article_content_interval_policy") or {}
        if article_policy:
            min_seconds = float(article_policy.get("min_seconds", 20))
            max_seconds = float(article_policy.get("max_seconds", 180))
            if bool(article_policy.get("dynamic_enabled", True)):
                self.detail_min_interval_seconds = random.uniform(min_seconds, max_seconds)
            else:
                self.detail_min_interval_seconds = min_seconds

    def _can_key(self, key: str, limit: int, reason: str, now: datetime) -> tuple[bool, str | None]:
        self._prune(key, now)
        if len(self.events[key]) >= limit:
            return False, reason
        return True, None

    def can_request(
        self,
        account_key: str | None = None,
        proxy_key: str | None = None,
        monitored_key: str | None = None,
    ) -> tuple[bool, str | None]:
        now = datetime.now(timezone.utc)
        ok, reason = self._can_key("global", self.global_limit_per_minute, "global_minute_limit", now)
        if not ok:
            return ok, reason
        if account_key:
            key = f"account:{account_key}"
            ok, reason = self._can_key(key, self.account_limit_per_minute, "account_minute_limit", now)
            if not ok:
                return ok, reason
            last = self.last_detail_at.get(key)
            if last and (now - last).total_seconds() < self.detail_min_interval_seconds:
                return False, "detail_min_interval"
        if proxy_key:
            ok, reason = self._can_key(f"proxy:{proxy_key}", self.proxy_limit_per_minute, "proxy_minute_limit", now)
            if not ok:
                return ok, reason
        if monitored_key:
            ok, reason = self._can_key(f"monitored:{monitored_key}", self.monitored_limit_per_minute, "monitored_minute_limit", now)
            if not ok:
                return ok, reason
        return True, None

    def mark_detail_request(
        self,
        account_key: str | None = None,
        proxy_key: str | None = None,
        monitored_key: str | None = None,
    ) -> None:
        now = datetime.now(timezone.utc)
        self.record("global")
        if account_key:
            key = f"account:{account_key}"
            self.record(key)
            self.last_detail_at[key] = now
        if proxy_key:
            self.record(f"proxy:{proxy_key}")
        if monitored_key:
            self.record(f"monitored:{monitored_key}")

    async def _redis_ready(self) -> Any | None:
        try:
            client = get_redis_client()
            await asyncio.wait_for(client.ping(), timeout=0.05)
            return client
        except Exception:
            return None

    async def _redis_count_ok(self, client, key: str, limit: int, reason: str, now: float) -> tuple[bool, str | None]:
        redis_key = f"rate_limit:{key}"
        await client.zremrangebyscore(redis_key, 0, now - 60)
        count = await client.zcard(redis_key)
        if count >= limit:
            return False, reason
        return True, None

    async def can_request_async(
        self,
        account_key: str | None = None,
        proxy_key: str | None = None,
        monitored_key: str | None = None,
    ) -> tuple[bool, str | None]:
        client = await self._redis_ready()
        if client is None:
            return self.can_request(account_key=account_key, proxy_key=proxy_key, monitored_key=monitored_key)
        now = time.time()
        checks = [
            ("global", self.global_limit_per_minute, "global_minute_limit"),
        ]
        if account_key:
            checks.append((f"account:{account_key}", self.account_limit_per_minute, "account_minute_limit"))
            last_raw = await client.get(f"rate_limit:last_detail:account:{account_key}")
            if last_raw and now - float(last_raw) < self.detail_min_interval_seconds:
                return False, "detail_min_interval"
        if proxy_key:
            checks.append((f"proxy:{proxy_key}", self.proxy_limit_per_minute, "proxy_minute_limit"))
        if monitored_key:
            checks.append((f"monitored:{monitored_key}", self.monitored_limit_per_minute, "monitored_minute_limit"))
        for key, limit, reason in checks:
            ok, error = await self._redis_count_ok(client, key, limit, reason, now)
            if not ok:
                return ok, error
        return True, None

    async def mark_detail_request_async(
        self,
        account_key: str | None = None,
        proxy_key: str | None = None,
        monitored_key: str | None = None,
    ) -> None:
        client = await self._redis_ready()
        if client is None:
            self.mark_detail_request(account_key=account_key, proxy_key=proxy_key, monitored_key=monitored_key)
            return
        now = time.time()
        keys = ["global"]
        if account_key:
            keys.append(f"account:{account_key}")
            await client.set(f"rate_limit:last_detail:account:{account_key}", str(now), ex=300)
            self.last_detail_at[f"account:{account_key}"] = datetime.fromtimestamp(now, tz=timezone.utc)
        if proxy_key:
            keys.append(f"proxy:{proxy_key}")
        if monitored_key:
            keys.append(f"monitored:{monitored_key}")
        for key in keys:
            redis_key = f"rate_limit:{key}"
            await client.zadd(redis_key, {str(now): now})
            await client.expire(redis_key, 120)

    def stats(self) -> dict[str, Any]:
        now = datetime.now(timezone.utc)
        keys = list(self.events)
        for key in keys:
            self._prune(key, now)
        return {
            "global_limit_per_minute": self.global_limit_per_minute,
            "account_limit_per_minute": self.account_limit_per_minute,
            "proxy_limit_per_minute": self.proxy_limit_per_minute,
            "monitored_limit_per_minute": self.monitored_limit_per_minute,
            "detail_min_interval_seconds": self.detail_min_interval_seconds,
            "current_global_minute_count": len(self.events["global"]),
            "account_minute_counts": {
                key.replace("account:", "", 1): len(value)
                for key, value in self.events.items()
                if key.startswith("account:")
            },
            "last_detail_at": {
                key.replace("account:", "", 1): value.isoformat()
                for key, value in self.last_detail_at.items()
            },
            "proxy_minute_counts": {
                key.replace("proxy:", "", 1): len(value)
                for key, value in self.events.items()
                if key.startswith("proxy:")
            },
            "monitored_minute_counts": {
                key.replace("monitored:", "", 1): len(value)
                for key, value in self.events.items()
                if key.startswith("monitored:")
            },
        }


rate_limit_service = RateLimitService()
