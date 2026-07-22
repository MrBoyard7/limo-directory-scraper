"""
scraper/utils/rate_limiter.py
------------------------------
Async-friendly rate limiter with random delay between requests.
Prevents IP bans and respects target websites.
"""

import asyncio
import random
import logging
import time
from functools import wraps
from typing import Callable, Any

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Simple rate limiter with randomised delay between calls.

    Usage:
        limiter = RateLimiter(min_delay=1.5, max_delay=3.5)
        await limiter.wait()  # async
        limiter.wait_sync()   # sync
    """

    def __init__(self, min_delay: float = 1.5, max_delay: float = 3.5):
        self.min_delay = min_delay
        self.max_delay = max_delay
        self._last_call: float = 0.0

    def _compute_delay(self) -> float:
        elapsed = time.monotonic() - self._last_call
        desired = random.uniform(self.min_delay, self.max_delay)
        return max(0.0, desired - elapsed)

    async def wait(self) -> None:
        delay = self._compute_delay()
        if delay > 0:
            logger.debug("Rate limiter sleeping %.2fs", delay)
            await asyncio.sleep(delay)
        self._last_call = time.monotonic()

    def wait_sync(self) -> None:
        delay = self._compute_delay()
        if delay > 0:
            logger.debug("Rate limiter sleeping %.2fs", delay)
            time.sleep(delay)
        self._last_call = time.monotonic()


def with_rate_limit(min_delay: float = 1.5, max_delay: float = 3.5):
    """
    Decorator: adds a random sync delay before each call.

    Example:
        @with_rate_limit(1.0, 2.0)
        def fetch_page(url): ...
    """
    limiter = RateLimiter(min_delay, max_delay)

    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            limiter.wait_sync()
            return fn(*args, **kwargs)
        return wrapper
    return decorator


def async_with_rate_limit(min_delay: float = 1.5, max_delay: float = 3.5):
    """
    Decorator: adds a random async delay before each coroutine call.

    Example:
        @async_with_rate_limit(1.0, 2.0)
        async def fetch_page(url): ...
    """
    limiter = RateLimiter(min_delay, max_delay)

    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            await limiter.wait()
            return await fn(*args, **kwargs)
        return wrapper
    return decorator
