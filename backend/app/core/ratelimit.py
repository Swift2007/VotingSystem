"""A tiny in-memory sliding-window rate limiter.

Used for login and receipt verification so receipt codes and passwords
can't be brute-forced quickly. It's per process, which is fine for this
single-server prototype; a multi-server deployment would need Redis or similar.
"""
import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status


class RateLimiter:
    def __init__(self, limit: int, window_seconds: float = 60.0) -> None:
        self.limit = limit
        self.window = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def hit(self, key: str) -> bool:
        """Record a request; return False if the key is over its limit."""
        now = time.monotonic()
        with self._lock:
            hits = self._hits[key]
            while hits and now - hits[0] > self.window:
                hits.popleft()
            if len(hits) >= self.limit:
                return False
            hits.append(now)
            return True

    def check(self, request: Request, scope: str) -> None:
        client = request.client.host if request.client else "unknown"
        if not self.hit(f"{scope}:{client}"):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many attempts. Please wait a minute and try again.",
            )
