"""
tests/test_scraper/test_rate_limiter.py
----------------------------------------
Tests for the rate limiter utility.
"""

import time
import pytest
from scraper.utils.rate_limiter import RateLimiter, with_rate_limit, async_with_rate_limit


class TestRateLimiter:
    def test_init_defaults(self):
        limiter = RateLimiter()
        assert limiter.min_delay == 1.5
        assert limiter.max_delay == 3.5

    def test_init_custom(self):
        limiter = RateLimiter(min_delay=0.1, max_delay=0.2)
        assert limiter.min_delay == 0.1
        assert limiter.max_delay == 0.2

    def test_wait_sync_runs(self):
        limiter = RateLimiter(min_delay=0.01, max_delay=0.02)
        start = time.monotonic()
        limiter.wait_sync()
        elapsed = time.monotonic() - start
        # First call should be nearly instant (no previous call)
        assert elapsed < 1.0

    def test_wait_sync_respects_delay(self):
        limiter = RateLimiter(min_delay=0.05, max_delay=0.1)
        limiter.wait_sync()   # first call — sets _last_call
        start = time.monotonic()
        limiter.wait_sync()   # second call — should wait
        elapsed = time.monotonic() - start
        assert elapsed >= 0.04  # allow tiny margin

    def test_compute_delay_non_negative(self):
        limiter = RateLimiter(min_delay=0.0, max_delay=0.1)
        delay = limiter._compute_delay()
        assert delay >= 0.0

    def test_with_rate_limit_decorator(self):
        call_times = []

        @with_rate_limit(min_delay=0.01, max_delay=0.02)
        def my_func():
            call_times.append(time.monotonic())
            return 42

        result = my_func()
        assert result == 42
        assert len(call_times) == 1

    def test_with_rate_limit_preserves_return(self):
        @with_rate_limit(0.01, 0.02)
        def add(a, b):
            return a + b

        assert add(2, 3) == 5

    @pytest.mark.asyncio
    async def test_async_wait(self):
        limiter = RateLimiter(min_delay=0.01, max_delay=0.02)
        await limiter.wait()   # should not raise

    @pytest.mark.asyncio
    async def test_async_decorator(self):
        @async_with_rate_limit(0.01, 0.02)
        async def fetch():
            return "data"

        result = await fetch()
        assert result == "data"
