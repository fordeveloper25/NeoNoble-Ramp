"""
Simple in-memory sliding-window rate limiter.
For production multi-instance, swap for Redis-backed equivalent.
"""
from __future__ import annotations

import time
from collections import defaultdict, deque
from typing import Deque, Dict

from fastapi import HTTPException, Request


class SlidingWindowLimiter:
    def __init__(self):
        self._buckets: Dict[str, Deque[float]] = defaultdict(deque)

    def check(self, key: str, max_calls: int, window_seconds: int):
        now = time.time()
        bucket = self._buckets[key]
        while bucket and bucket[0] <= now - window_seconds:
            bucket.popleft()
        if len(bucket) >= max_calls:
            retry_after = int(window_seconds - (now - bucket[0])) + 1
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded. Retry in {retry_after}s.",
                headers={"Retry-After": str(retry_after)},
            )
        bucket.append(now)


_limiter = SlidingWindowLimiter()


def rate_limit(max_calls: int, window_seconds: int, key_prefix: str = ""):
    """FastAPI dependency factory for rate limiting by client IP.

    Uses X-Forwarded-For when available (production behind K8s ingress / CDN)
    and falls back to request.client.host otherwise. Only the leftmost address
    in X-Forwarded-For is trusted — adjust if your proxy chain is different.
    """
    def dep(request: Request):
        xff = request.headers.get("x-forwarded-for") or request.headers.get("x-real-ip")
        if xff:
            client = xff.split(",")[0].strip()
        else:
            client = request.client.host if request.client else "unknown"
        _limiter.check(f"{key_prefix}:{client}", max_calls, window_seconds)
    return dep
