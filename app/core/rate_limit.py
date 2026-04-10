"""
Simple in-memory rate limiter (no external dependencies).
Use as a FastAPI dependency.
"""

import time
from collections import defaultdict

from fastapi import Request, HTTPException


class RateLimiter:
    """Token-bucket style rate limiter keyed by client IP."""

    def __init__(self, max_calls: int = 10, period: int = 60):
        self.max_calls = max_calls
        self.period = period
        self._calls: dict[str, list[float]] = defaultdict(list)

    async def __call__(self, request: Request):
        key = request.client.host if request.client else "unknown"
        now = time.time()
        # Prune expired entries
        self._calls[key] = [t for t in self._calls[key] if now - t < self.period]
        if len(self._calls[key]) >= self.max_calls:
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        self._calls[key].append(now)


rate_limit_session_start = RateLimiter(max_calls=10, period=60)
