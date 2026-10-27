"""Global Requests-Per-Minute (RPM) rate limiter, Retry-After handler, and health tracker."""

from __future__ import annotations

import email.utils
import time
from typing import Dict, List, Tuple
from .config import ProviderConfig
from .models import ProviderHealthStatus


class ProviderRateLimiter:
    """Sliding-window rate limiter and cooldown tracker per AI provider."""

    def __init__(self) -> None:
        # provider -> list of monotonic timestamps in past 60 seconds
        self._request_timestamps: dict[str, list[float]] = {}
        # provider -> cooldown expiration timestamp (time.time())
        self._cooldown_until: dict[str, float] = {}
        # provider -> telemetry stats
        self._total_calls: dict[str, int] = {}
        self._successful_calls: dict[str, int] = {}
        self._failed_calls: dict[str, int] = {}
        self._last_error: dict[str, str] = {}
        self._last_latency: dict[str, float] = {}

    def parse_retry_after(self, retry_after: str | int | float | None) -> float:
        """Parse Retry-After header into seconds.

        Can be integer/float seconds, or an HTTP-date format string.
        """
        if retry_after is None:
            return 60.0  # Default 60s cooldown on 429 without header

        if isinstance(retry_after, (int, float)):
            return max(1.0, float(retry_after))

        val_str = str(retry_after).strip()
        try:
            # Try numeric seconds first
            return max(1.0, float(val_str))
        except ValueError:
            pass

        # Try parsing RFC 1123 / HTTP-date
        try:
            parsed_tuple = email.utils.parsedate(val_str)
            if parsed_tuple:
                target_timestamp = time.mktime(parsed_tuple)
                now = time.time()
                diff = target_timestamp - now
                return max(1.0, diff)
        except Exception:
            pass

        return 60.0

    def can_request(self, provider_name: str, rpm_limit: int) -> tuple[bool, str]:
        """Check whether provider is available or blocked by cooldown / RPM limit."""
        now = time.time()

        # 1. Check cooldown (e.g. from 429 Retry-After)
        cooldown_end = self._cooldown_until.get(provider_name, 0.0)
        if now < cooldown_end:
            remaining = round(cooldown_end - now, 1)
            return False, f"cooldown ({remaining}s remaining from Retry-After / 429)"

        # 2. Check sliding window RPM
        timestamps = self._request_timestamps.setdefault(provider_name, [])
        # Prune timestamps older than 60 seconds
        cutoff = now - 60.0
        self._request_timestamps[provider_name] = [t for t in timestamps if t > cutoff]

        if len(self._request_timestamps[provider_name]) >= rpm_limit:
            return False, f"rpm_limit_exceeded ({len(self._request_timestamps[provider_name])}/{rpm_limit} in 60s)"

        return True, ""

    def record_request(self, provider_name: str) -> None:
        """Record start of a request for sliding window tracking."""
        now = time.time()
        self._request_timestamps.setdefault(provider_name, []).append(now)
        self._total_calls[provider_name] = self._total_calls.get(provider_name, 0) + 1

    def record_success(self, provider_name: str, latency_ms: float = 0.0) -> None:
        """Record a successful response."""
        self._successful_calls[provider_name] = self._successful_calls.get(provider_name, 0) + 1
        self._last_latency[provider_name] = latency_ms

    def record_failure(
        self,
        provider_name: str,
        error_msg: str,
        status_code: int | None = None,
        retry_after: str | int | float | None = None,
    ) -> None:
        """Record a failed response and trigger cooldown if rate-limited (429) or quota exceeded."""
        self._failed_calls[provider_name] = self._failed_calls.get(provider_name, 0) + 1
        self._last_error[provider_name] = error_msg

        is_quota = (
            status_code == 429
            or "429" in error_msg
            or "quota" in error_msg.lower()
            or "rate limit" in error_msg.lower()
        )

        if is_quota:
            cooldown_seconds = self.parse_retry_after(retry_after)
            self._cooldown_until[provider_name] = time.time() + cooldown_seconds

    def get_health_status(self, provider_name: str, config: ProviderConfig) -> ProviderHealthStatus:
        """Construct public health status for admin monitoring (never exposes keys)."""
        now = time.time()
        cooldown_end = self._cooldown_until.get(provider_name, 0.0)
        cooldown_remaining = max(0.0, round(cooldown_end - now, 1))

        # Prune window
        cutoff = now - 60.0
        recent = [t for t in self._request_timestamps.get(provider_name, []) if t > cutoff]
        used_rpm = len(recent)
        remaining_rpm = max(0, config.rpm_limit - used_rpm)

        has_key = bool(config.api_key and len(config.api_key) > 0)

        # Determine status string
        if not has_key and provider_name not in ("fake", "ollama"):
            status = "no_key"
        elif cooldown_remaining > 0:
            status = "cooldown"
        elif remaining_rpm <= 0:
            status = "rate_limited"
        else:
            status = "healthy"

        return ProviderHealthStatus(
            name=provider_name,
            status=status,
            model=config.model,
            trains_on_prompts=config.trains_on_prompts,
            has_api_key=has_key,
            rpm_limit=config.rpm_limit,
            rpm_used=used_rpm,
            rpm_remaining=remaining_rpm,
            cooldown_remaining_seconds=cooldown_remaining,
            total_calls=self._total_calls.get(provider_name, 0),
            successful_calls=self._successful_calls.get(provider_name, 0),
            failed_calls=self._failed_calls.get(provider_name, 0),
            last_error=self._last_error.get(provider_name),
            last_latency_ms=round(self._last_latency.get(provider_name, 0.0), 2),
        )

    def reset(self) -> None:
        """Reset all rate limiter state (useful in tests)."""
        self._request_timestamps.clear()
        self._cooldown_until.clear()
        self._total_calls.clear()
        self._successful_calls.clear()
        self._failed_calls.clear()
        self._last_error.clear()
        self._last_latency.clear()


GLOBAL_RATE_LIMITER = ProviderRateLimiter()
