"""Rate limiting module for YtGenius backend.

Architecture Note:
------------------
This module implements a thread-safe, in-memory sliding window rate limiter
suitable for single-node / single-worker deployments or development/staging setups.

In horizontally scaled multi-worker / multi-container production deployments
behind a load balancer, each process maintains an isolated in-memory table.
To enforce unified global rate limits across a cluster, a distributed key-value store
such as Redis should be used (e.g. via redis-py executing a Lua token-bucket or
sliding-window script).
"""

import os
import time
from threading import Lock
from typing import Dict, List, Optional

from fastapi import HTTPException, Request, status

from app.core.config import settings


def get_client_ip(request: Request) -> str:
    """Extract client IP address safely, taking reverse proxies into account.

    Only if the immediate client is in TRUSTED_PROXIES will X-Forwarded-For headers
    be parsed to determine the originating client IP. This prevents spoofed
    X-Forwarded-For headers from untrusted clients bypassing rate limits.
    """
    if not request.client or not request.client.host:
        return "unknown"

    immediate_ip = request.client.host

    trusted_proxies = getattr(settings, "TRUSTED_PROXIES", ["127.0.0.1", "::1"])
    if isinstance(trusted_proxies, str):
        trusted_proxies = [p.strip() for p in trusted_proxies.split(",") if p.strip()]

    # If the immediate connecting IP is NOT a trusted proxy, do not trust X-Forwarded-For
    if immediate_ip not in trusted_proxies:
        return immediate_ip

    # If immediate connecting IP IS a trusted proxy, inspect X-Forwarded-For
    forwarded_for = request.headers.get("x-forwarded-for")
    if not forwarded_for:
        return immediate_ip

    # Parse hops from right to left
    hops = [ip.strip() for ip in forwarded_for.split(",") if ip.strip()]
    if not hops:
        return immediate_ip

    for ip in reversed(hops):
        if ip not in trusted_proxies:
            return ip

    return hops[0]


class RateLimiter:
    """Thread-safe in-memory sliding-window rate limiter with memory eviction."""

    def __init__(
        self,
        requests_per_minute: int = 10,
        burst: int = 20,
        max_keys: int = 10000,
        cleanup_interval_seconds: float = 60.0,
    ):
        self.requests_per_minute = requests_per_minute
        self.burst = burst
        self.max_keys = max_keys
        self.cleanup_interval_seconds = cleanup_interval_seconds
        self.lock = Lock()
        self.history: Dict[str, List[float]] = {}
        self._last_cleanup = time.time()

    def _evict_expired(self, now: float, window: float) -> None:
        """Evict keys whose timestamps have all expired beyond the sliding window."""
        stale_keys = [
            k for k, ts in self.history.items()
            if not ts or (now - ts[-1] >= window)
        ]
        for k in stale_keys:
            self.history.pop(k, None)

    def is_allowed(self, client_key: str) -> bool:
        if os.getenv("TESTING") == "1":
            return True

        now = time.time()
        window = 60.0

        with self.lock:
            # Periodic opportunistic garbage collection of expired keys
            if now - self._last_cleanup > self.cleanup_interval_seconds:
                self._evict_expired(now, window)
                self._last_cleanup = now

            # If capacity limit is reached, evict expired keys
            if len(self.history) >= self.max_keys:
                self._evict_expired(now, window)
                # If still over limit, drop oldest entries to prevent OOM
                if len(self.history) >= self.max_keys:
                    excess = len(self.history) - self.max_keys + 100
                    keys_to_remove = list(self.history.keys())[:excess]
                    for k in keys_to_remove:
                        self.history.pop(k, None)

            timestamps = self.history.get(client_key, [])
            valid_timestamps = [t for t in timestamps if now - t < window]

            if len(valid_timestamps) >= self.burst:
                self.history[client_key] = valid_timestamps
                return False

            valid_timestamps.append(now)
            self.history[client_key] = valid_timestamps
            return True

    def reset(self) -> None:
        """Clear all stored rate limit history (useful for test resets)."""
        with self.lock:
            self.history.clear()
            self._last_cleanup = time.time()


# Endpoint-appropriate limiter instances
auth_rate_limiter = RateLimiter(
    requests_per_minute=getattr(settings, "RATE_LIMIT_PER_MINUTE", 10),
    burst=getattr(settings, "RATE_LIMIT_BURST", 20),
)

resend_verification_rate_limiter = RateLimiter(
    requests_per_minute=3,
    burst=5,
)

video_process_rate_limiter = RateLimiter(
    requests_per_minute=5,
    burst=10,
)

ai_generation_rate_limiter = RateLimiter(
    requests_per_minute=20,
    burst=30,
)

otp_send_rate_limiter = RateLimiter(
    requests_per_minute=5,
    burst=10,
)

otp_verify_rate_limiter = RateLimiter(
    requests_per_minute=10,
    burst=15,
)


def create_rate_limit_checker(
    limiter: RateLimiter,
    error_message: str,
    retry_after: str = "60",
):
    """Factory to create FastAPI dependency checking rate limits."""
    async def dependency(request: Request) -> None:
        client_ip = get_client_ip(request)
        key = f"{client_ip}:{request.url.path}"
        if not limiter.is_allowed(key):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=error_message,
                headers={"Retry-After": retry_after},
            )
    return dependency


check_auth_rate_limit = create_rate_limit_checker(
    limiter=auth_rate_limiter,
    error_message="Too many authentication requests. Please try again in 1 minute.",
)

check_resend_verification_rate_limit = create_rate_limit_checker(
    limiter=resend_verification_rate_limiter,
    error_message="Too many verification requests. Please wait a few minutes before requesting another verification email.",
)

check_video_process_rate_limit = create_rate_limit_checker(
    limiter=video_process_rate_limiter,
    error_message="Too many video processing requests. Video ingestion is resource-intensive; please wait before submitting another video.",
)

check_ai_generation_rate_limit = create_rate_limit_checker(
    limiter=ai_generation_rate_limiter,
    error_message="Too many AI generation requests. Please wait before asking another question.",
)

check_otp_send_rate_limit = create_rate_limit_checker(
    limiter=otp_send_rate_limiter,
    error_message="Too many login code requests. Please wait before requesting another code.",
)

check_otp_verify_rate_limit = create_rate_limit_checker(
    limiter=otp_verify_rate_limiter,
    error_message="Too many code verification attempts. Please wait.",
)
