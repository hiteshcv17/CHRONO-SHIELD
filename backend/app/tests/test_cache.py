import pytest
import asyncio
from app.utils.cache import cache_response, invalidate_cache_by_pattern
from app.db.session import redis_client


class TestCacheSubsystem:

    def test_cache_response_decorator(self):
        """Verify that the cache_response decorator correctly stores outputs and serves hits."""

        async def run_test():
            call_count = 0

            @cache_response(ttl=10, prefix="test")
            async def mock_endpoint(param1: str, db: str = "injected_dependency"):
                nonlocal call_count
                call_count += 1
                return {"data": param1, "count": call_count}

            # Clear existing test keys
            await invalidate_cache_by_pattern("test:*")

            # First call: should be a cache miss (executes function)
            res1 = await mock_endpoint("hello")
            assert res1["data"] == "hello"
            assert res1["count"] == 1
            assert call_count == 1

            # Second call: should be a cache hit (uses cached response, count remains 1)
            res2 = await mock_endpoint("hello")
            assert res2["data"] == "hello"
            assert res2["count"] == 1
            assert call_count == 1

            # Call with different arguments: should be a cache miss
            res3 = await mock_endpoint("world")
            assert res3["data"] == "world"
            assert res3["count"] == 2
            assert call_count == 2

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        loop.run_until_complete(run_test())

    def test_cache_invalidation(self):
        """Verify that invalidation deletes matching keys while leaving others intact."""

        async def run_test():
            call_count_1 = 0
            call_count_2 = 0

            @cache_response(ttl=10, prefix="test_inv1")
            async def endpoint_1(param: str):
                nonlocal call_count_1
                call_count_1 += 1
                return {"param": param, "count": call_count_1}

            @cache_response(ttl=10, prefix="test_inv2")
            async def endpoint_2(param: str):
                nonlocal call_count_2
                call_count_2 += 1
                return {"param": param, "count": call_count_2}

            # Warm up caches
            await endpoint_1("foo")
            await endpoint_2("bar")
            assert call_count_1 == 1
            assert call_count_2 == 1

            # Verify caching works (hits)
            await endpoint_1("foo")
            await endpoint_2("bar")
            assert call_count_1 == 1
            assert call_count_2 == 1

            # Invalidate only test_inv1
            await invalidate_cache_by_pattern("test_inv1:*")

            # endpoint_1 should miss and re-run
            await endpoint_1("foo")
            assert call_count_1 == 2

            # endpoint_2 should still hit cache (count remains 1)
            await endpoint_2("bar")
            assert call_count_2 == 1

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        loop.run_until_complete(run_test())
