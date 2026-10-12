"""Simple in-memory rate limits per client key (IP or user id)."""

import threading
import time
from collections import defaultdict
from uuid import UUID

from fastapi import Request

from app.core.config import Settings
from app.core.exceptions import AppError


class RateLimiter:
    def __init__(self) -> None:
        self._windows: dict[str, list[float]] = defaultdict(list)
        self._lock = threading.Lock()

    def check(self, key: str, max_calls: int, window_seconds: int = 60) -> None:
        now = time.monotonic()
        with self._lock:
            hits = self._windows[key]
            cutoff = now - window_seconds
            hits[:] = [t for t in hits if t >= cutoff]
            if len(hits) >= max_calls:
                raise AppError("Too many requests. Try again shortly.", status_code=429)
            hits.append(now)


_limiter = RateLimiter()


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",", 1)[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def check_auth_rate_limit(request: Request, settings: Settings) -> None:
    _limiter.check(f"auth:{client_ip(request)}", settings.auth_rate_limit_per_minute)


def check_user_rate_limit(user_id: UUID, scope: str, max_calls: int) -> None:
    _limiter.check(f"{scope}:{user_id}", max_calls)