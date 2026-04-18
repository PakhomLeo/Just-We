"""Proxy rotator utility for managing proxy rotation."""


from app.models.proxy import Proxy, ServiceType


class ProxyRotator:
    """
    Utility for rotating proxies based on success rate and health.

    This class provides advanced proxy selection logic beyond simple round-robin.
    """

    def __init__(self):
        """Initialize proxy rotator."""
        self._last_proxy_index: dict[ServiceType, int] = {}

    def select_proxy(
        self,
        proxies: list[Proxy],
        service_type: ServiceType,
        prefer_high_success: bool = True,
    ) -> Proxy | None:
        """
        Select the best proxy based on criteria.

        Args:
            proxies: List of available proxies
            service_type: Service type filter
            prefer_high_success: If True, prefer proxies with higher success rate

        Returns:
            Selected Proxy or None if no proxies available
        """
        # Filter by service type and active status
        available = [
            p for p in proxies
            if p.service_type == service_type and p.is_active
        ]

        if not available:
            return None

        if prefer_high_success:
            # Sort by success rate descending
            available.sort(key=lambda p: p.success_rate, reverse=True)

            # Get the best one that's not recently used
            for proxy in available:
                if self._is_available(proxy, service_type):
                    self._mark_used(proxy, service_type)
                    return proxy

            # If all recently used, return best anyway
            self._mark_used(available[0], service_type)
            return available[0]
        else:
            # Round-robin
            return self._round_robin_select(available, service_type)

    def _round_robin_select(
        self,
        proxies: list[Proxy],
        service_type: ServiceType,
    ) -> Proxy:
        """Select proxy using round-robin."""
        current_index = self._last_proxy_index.get(service_type, 0)
        proxy = proxies[current_index % len(proxies)]
        self._last_proxy_index[service_type] = (current_index + 1) % len(proxies)
        return proxy

    def _is_available(self, proxy: Proxy, service_type: ServiceType) -> bool:
        """Check if proxy is available (not recently used)."""
        # Simple implementation - could add more sophisticated tracking
        return True

    def _mark_used(self, proxy: Proxy, service_type: ServiceType) -> None:
        """Mark proxy as recently used."""
        pass  # Could track in Redis for distributed scenarios

    def calculate_health_score(self, proxy: Proxy) -> float:
        """
        Calculate a health score for a proxy.

        Args:
            proxy: Proxy model

        Returns:
            Health score (0-100)
        """
        # Factors:
        # - Success rate (40%)
        # - Recency of last use (30%)
        # - Error rate trend (30%)

        success_score = proxy.success_rate * 0.4

        # Recency score (assume 100 if used recently, lower if not)
        recency_score = 80.0  # Simplified

        # Base score
        base_score = 30.0

        return min(100.0, success_score + recency_score + base_score)

    def rank_proxies(self, proxies: list[Proxy]) -> list[tuple[Proxy, float]]:
        """
        Rank proxies by health score.

        Args:
            proxies: List of proxies

        Returns:
            List of (proxy, score) tuples sorted by score descending
        """
        scored = [(p, self.calculate_health_score(p)) for p in proxies]
        return sorted(scored, key=lambda x: x[1], reverse=True)
