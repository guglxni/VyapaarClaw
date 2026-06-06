"""Tests for Google Safe Browsing reputation checks."""

from __future__ import annotations

from typing import Any

import httpx
import pytest
import redis

from vyapaar_mcp.models import SafeBrowsingResponse
from vyapaar_mcp.reputation.safe_browsing import SafeBrowsingChecker
from vyapaar_mcp.resilience import CircuitBreaker


class MemoryReputationCache:
    """Small deterministic cache fake for SafeBrowsingChecker tests."""

    def __init__(
        self,
        cached: dict[str, Any] | None = None,
        read_error: Exception | None = None,
        write_error: Exception | None = None,
    ) -> None:
        self.cached = cached
        self.read_error = read_error
        self.write_error = write_error
        self.writes: list[tuple[str, dict[str, Any], int]] = []

    async def get_cached_reputation(self, url: str) -> dict[str, Any] | None:
        if self.read_error:
            raise self.read_error
        return self.cached

    async def cache_reputation(self, url: str, result: dict[str, Any], ttl: int = 300) -> None:
        if self.write_error:
            raise self.write_error
        self.writes.append((url, result, ttl))


def _checker_with_transport(handler, redis_cache=None) -> SafeBrowsingChecker:
    checker = SafeBrowsingChecker(
        api_key="test-key",
        api_url="https://safe-browsing.test/v4/threatMatches:find",
        redis=redis_cache,
        circuit_breaker=CircuitBreaker("test-safe-browsing", failure_threshold=2),
    )
    checker._http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return checker


def _unsafe_payload(threat_type: str = "MALWARE") -> dict[str, Any]:
    return {
        "matches": [
            {
                "threatType": threat_type,
                "platformType": "ANY_PLATFORM",
                "threatEntryType": "URL",
                "threat": {"url": "https://unsafe.test"},
            }
        ]
    }


@pytest.mark.asyncio
class TestSafeBrowsingChecker:
    """SafeBrowsingChecker should fail closed for API errors and tolerate cache issues."""

    async def test_cache_hit_returns_cached_response_without_http_call(self) -> None:
        cache = MemoryReputationCache(cached=_unsafe_payload("SOCIAL_ENGINEERING"))

        def handler(request: httpx.Request) -> httpx.Response:
            raise AssertionError("HTTP should not be called on cache hit")

        checker = _checker_with_transport(handler, cache)
        try:
            result = await checker.check_url("https://cached.test")
        finally:
            await checker.close()

        assert result.is_safe is False
        assert result.threat_types == ["SOCIAL_ENGINEERING"]

    async def test_successful_api_response_is_cached(self) -> None:
        cache = MemoryReputationCache()

        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.params["key"] == "test-key"
            return httpx.Response(200, json={})

        checker = _checker_with_transport(handler, cache)
        try:
            result = await checker.check_url("https://safe.test")
        finally:
            await checker.close()

        assert result == SafeBrowsingResponse()
        assert cache.writes == [("https://safe.test", {"matches": []}, 300)]

    async def test_cache_read_failure_falls_back_to_api(self) -> None:
        cache = MemoryReputationCache(read_error=redis.exceptions.RedisError("redis down"))

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={})

        checker = _checker_with_transport(handler, cache)
        try:
            result = await checker.check_url("https://safe.test")
        finally:
            await checker.close()

        assert result.is_safe is True
        assert cache.writes == [("https://safe.test", {"matches": []}, 300)]

    async def test_invalid_cache_payload_falls_back_to_api(self) -> None:
        cache = MemoryReputationCache(cached={"matches": [{"threatType": 123}]})

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={})

        checker = _checker_with_transport(handler, cache)
        try:
            result = await checker.check_url("https://safe.test")
        finally:
            await checker.close()

        assert result.is_safe is True
        assert cache.writes == [("https://safe.test", {"matches": []}, 300)]

    async def test_cache_write_failure_does_not_override_api_verdict(self) -> None:
        cache = MemoryReputationCache(write_error=redis.exceptions.RedisError("readonly"))

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=_unsafe_payload())

        checker = _checker_with_transport(handler, cache)
        try:
            result = await checker.check_url("https://unsafe.test")
        finally:
            await checker.close()

        assert result.is_safe is False
        assert result.threat_types == ["MALWARE"]

    async def test_timeout_fails_closed(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.TimeoutException("timed out")

        checker = _checker_with_transport(handler)
        try:
            result = await checker.check_url("https://unknown.test")
        finally:
            await checker.close()

        assert result.is_safe is False
        assert result.threat_types == ["VYAPAAR_TIMEOUT"]

    async def test_invalid_api_json_fails_closed(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, content=b"{")

        checker = _checker_with_transport(handler)
        try:
            result = await checker.check_url("https://unknown.test")
        finally:
            await checker.close()

        assert result.is_safe is False
        assert result.threat_types == ["VYAPAAR_INTERNAL_ERROR"]
