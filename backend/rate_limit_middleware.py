"""Redis-backed HTTP rate limiting middleware (TF-018)."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Literal

from fastapi import Request
from fastapi.responses import JSONResponse
from redis.asyncio import Redis

from backend.dependencies.auth import decode_access_token
from backend.exceptions import UnauthorizedError
from backend.logging_config import get_logger
from backend.metrics import RATE_LIMIT_EXCEEDED_TOTAL
from backend.security.rate_limit import InMemoryRateLimiter, get_client_ip
from backend.settings import Settings, get_settings

logger = get_logger(__name__)


@dataclass(frozen=True)
class RateLimitDecision:
    allowed: bool
    remaining: int
    retry_after_seconds: int
    key_type: Literal["user", "ip"]


class RedisFixedWindowRateLimiter:
    """Simple fixed-window rate limiter using Redis INCR with per-window expiry."""

    def __init__(self, *, redis_client: Redis, max_requests: int, window_seconds: int) -> None:
        self._redis = redis_client
        self._max_requests = max_requests
        self._window_seconds = window_seconds

    async def check(self, *, key: str) -> RateLimitDecision:
        now = time.time()
        bucket = int(now // self._window_seconds)
        redis_key = f"rate:{key}:{bucket}"

        retry_after = int(self._window_seconds - (now % self._window_seconds))
        if retry_after <= 0:
            retry_after = self._window_seconds

        count = await self._redis.incr(redis_key)
        if count == 1:
            # First request in this window sets expiry.
            await self._redis.expire(redis_key, self._window_seconds)

        allowed = int(count) <= self._max_requests
        remaining = max(self._max_requests - int(count), 0)
        return RateLimitDecision(
            allowed=allowed,
            remaining=remaining,
            retry_after_seconds=retry_after,
            key_type="user",
        )


class CompositeRateLimiter:
    """Try Redis first; fall back to in-memory limiter if Redis is unavailable."""

    def __init__(self, *, settings: Settings, max_requests: int, window_seconds: int) -> None:
        self._settings = settings
        self._max_requests = max_requests
        self._window_seconds = window_seconds
        self._fallback = InMemoryRateLimiter(
            max_requests=max_requests,
            window_seconds=window_seconds,
        )
        self._redis: Redis | None = None

    def _get_ip_key(self, request: Request) -> str:
        return get_client_ip(
            forwarded_for=request.headers.get("X-Forwarded-For"),
            client_host=request.client.host if request.client else None,
        )

    async def _try_get_redis(self) -> Redis | None:
        if self._redis is not None:
            return self._redis
        try:
            # Lazy connect: construction is cheap; commands confirm availability.
            self._redis = Redis.from_url(self._settings.redis_url, decode_responses=True)
            await self._redis.ping()
            return self._redis
        except Exception:
            logger.warning("redis_unavailable_for_rate_limit", redis_url=self._settings.redis_url)
            self._redis = None
            return None

    async def decide(self, *, request: Request) -> RateLimitDecision:
        # Authorization header is optional; if invalid, fall back to IP.
        auth_header = request.headers.get("Authorization")
        user_id: str | None = None
        key_type: Literal["user", "ip"] = "ip"

        if auth_header and auth_header.lower().startswith("bearer "):
            token = auth_header.split(" ", 1)[1].strip()
            try:
                claims = decode_access_token(token, self._settings)
                user_id = claims.get("sub")
                key_type = "user" if isinstance(user_id, str) else "ip"
            except (UnauthorizedError, ValueError):
                user_id = None
                key_type = "ip"

        if user_id:
            key = user_id
        else:
            key = self._get_ip_key(request)

        now = time.time()
        retry_after = int(self._window_seconds - (now % self._window_seconds))
        if retry_after <= 0:
            retry_after = self._window_seconds

        redis = await self._try_get_redis()
        if redis is not None and key_type == "user":
            decision = await RedisFixedWindowRateLimiter(
                redis_client=redis,
                max_requests=self._max_requests,
                window_seconds=self._window_seconds,
            ).check(key=key)
            # Redis limiter's key_type is fixed as "user"; correct for ip case too.
            return RateLimitDecision(
                allowed=decision.allowed,
                remaining=decision.remaining,
                retry_after_seconds=decision.retry_after_seconds,
                key_type=key_type,
            )

        allowed = self._fallback.is_allowed(key)
        remaining = self._max_requests - 1 if allowed else 0
        return RateLimitDecision(
            allowed=allowed,
            remaining=max(remaining, 0),
            retry_after_seconds=retry_after,
            key_type=key_type,
        )


async def rate_limit_middleware(request: Request, call_next):  # type: ignore[no-untyped-def]
    """Apply collaboration rate limits across `api/v1/*` except auth/health/metrics."""
    path = request.url.path
    if not path.startswith("/api/v1/"):
        return await call_next(request)

    if path.startswith("/api/v1/auth/") or path in {"/api/v1/auth/me"}:
        return await call_next(request)

    # Basic policy for MVP 2: 100/min per user, 100/min per IP fallback.
    # AI endpoints are stricter (TF-037): 10 AI requests/min per user.
    settings = get_settings()
    max_requests = 10 if path.startswith("/api/v1/ai/") else 100
    limiter = CompositeRateLimiter(settings=settings, max_requests=max_requests, window_seconds=60)
    decision = await limiter.decide(request=request)

    if decision.allowed:
        return await call_next(request)

    RATE_LIMIT_EXCEEDED_TOTAL.labels(decision.key_type, path).inc()
    return JSONResponse(
        status_code=429,
        content={"error": "rate_limit_exceeded", "message": "Too many requests. Try again later."},
        headers={
            "X-RateLimit-Remaining": str(decision.remaining),
            "Retry-After": str(decision.retry_after_seconds),
        },
    )
