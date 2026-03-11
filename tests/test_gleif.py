"""Tests for GLEIF vendor verification integration.

All HTTP interactions use httpx.MockTransport — no unittest.mock.
Circuit breaker tests drive a real CircuitBreaker to its threshold.
"""

from __future__ import annotations

import httpx
import pytest

from vyapaar_mcp.db.redis_client import RedisClient
from vyapaar_mcp.reputation.gleif import (
    GLEIFChecker,
    GLEIFEntity,
    GLEIFResponse,
)
from vyapaar_mcp.resilience import CircuitBreaker, CircuitState

# ================================================================
# Shared GLEIF API Response Payloads
# ================================================================

_SEARCH_RESPONSE_RAHUL = {
    "data": [
        {
            "id": "9845001B2AD43E664E58",
            "type": "lei-records",
            "attributes": {
                "lei": "9845001B2AD43E664E58",
                "entity": {
                    "legalName": {"name": "RAHUL", "language": "en"},
                    "jurisdiction": "IN",
                    "category": "SOLE_PROPRIETOR",
                    "status": "ACTIVE",
                    "headquartersAddress": {
                        "city": "SONIPAT",
                        "country": "IN",
                    },
                },
                "registration": {
                    "status": "ISSUED",
                },
            },
        }
    ]
}

_LOOKUP_RESPONSE_RAHUL = {
    "data": {
        "id": "9845001B2AD43E664E58",
        "type": "lei-records",
        "attributes": {
            "lei": "9845001B2AD43E664E58",
            "entity": {
                "legalName": {"name": "RAHUL", "language": "en"},
                "jurisdiction": "IN",
                "category": "SOLE_PROPRIETOR",
                "status": "ACTIVE",
                "headquartersAddress": {"city": "SONIPAT", "country": "IN"},
            },
            "registration": {"status": "ISSUED"},
        },
    }
}


# ================================================================
# Helpers
# ================================================================


def _gleif_checker_with_transport(handler, **checker_kwargs) -> GLEIFChecker:
    """Create a GLEIFChecker whose HTTP client uses the given MockTransport handler."""
    checker = GLEIFChecker(**checker_kwargs)
    checker._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return checker


# ================================================================
# GLEIFEntity Tests
# ================================================================


class TestGLEIFEntity:
    """Test GLEIFEntity data class."""

    def test_to_dict(self) -> None:
        entity = GLEIFEntity(
            lei="9845001B2AD43E664E58",
            legal_name="RAHUL",
            jurisdiction="IN",
            category="SOLE_PROPRIETOR",
            entity_status="ACTIVE",
            registration_status="ISSUED",
            headquarters_country="IN",
            headquarters_city="SONIPAT",
        )
        d = entity.to_dict()
        assert d["lei"] == "9845001B2AD43E664E58"
        assert d["legal_name"] == "RAHUL"
        assert d["jurisdiction"] == "IN"
        assert d["headquarters_country"] == "IN"


# ================================================================
# GLEIFResponse Tests
# ================================================================


class TestGLEIFResponse:
    """Test GLEIFResponse logic."""

    def test_is_verified_with_active_issued(self) -> None:
        entity = GLEIFEntity(
            lei="TEST1234567890123456",
            legal_name="TCS Ltd",
            jurisdiction="IN",
            category="GENERAL",
            entity_status="ACTIVE",
            registration_status="ISSUED",
        )
        response = GLEIFResponse(query="TCS", entities=[entity])
        assert response.is_verified is True
        assert response.best_match == entity
        assert response.match_count == 1

    def test_is_not_verified_with_lapsed(self) -> None:
        entity = GLEIFEntity(
            lei="TEST1234567890123456",
            legal_name="Old Corp",
            jurisdiction="US",
            category="GENERAL",
            entity_status="ACTIVE",
            registration_status="LAPSED",
        )
        response = GLEIFResponse(query="Old Corp", entities=[entity])
        assert response.is_verified is False

    def test_is_not_verified_when_empty(self) -> None:
        response = GLEIFResponse(query="Nobody Inc")
        assert response.is_verified is False
        assert response.best_match is None
        assert response.match_count == 0

    def test_is_not_verified_when_inactive(self) -> None:
        entity = GLEIFEntity(
            lei="TEST1234567890123456",
            legal_name="Dead Corp",
            jurisdiction="US",
            category="GENERAL",
            entity_status="INACTIVE",
            registration_status="ISSUED",
        )
        response = GLEIFResponse(query="Dead Corp", entities=[entity])
        assert response.is_verified is False

    def test_best_match_prefers_active_issued(self) -> None:
        lapsed = GLEIFEntity(
            lei="LAPSED12345678901234",
            legal_name="Corp A",
            jurisdiction="US",
            category="GENERAL",
            entity_status="ACTIVE",
            registration_status="LAPSED",
        )
        active = GLEIFEntity(
            lei="ACTIVE12345678901234",
            legal_name="Corp B",
            jurisdiction="US",
            category="GENERAL",
            entity_status="ACTIVE",
            registration_status="ISSUED",
        )
        response = GLEIFResponse(query="Corp", entities=[lapsed, active])
        assert response.best_match == active

    def test_to_dict(self) -> None:
        entity = GLEIFEntity(
            lei="TEST1234567890123456",
            legal_name="TCS",
            jurisdiction="IN",
            category="GENERAL",
            entity_status="ACTIVE",
            registration_status="ISSUED",
        )
        response = GLEIFResponse(query="TCS", entities=[entity])
        d = response.to_dict()
        assert d["verified"] is True
        assert d["match_count"] == 1
        assert d["best_match"]["lei"] == "TEST1234567890123456"
        assert d["error"] is None

    def test_to_dict_with_error(self) -> None:
        response = GLEIFResponse(query="fail", error="API timeout")
        d = response.to_dict()
        assert d["verified"] is False
        assert d["error"] == "API timeout"


# ================================================================
# GLEIFChecker Tests
# ================================================================


@pytest.mark.asyncio
class TestGLEIFChecker:
    """Test GLEIFChecker async API calls."""

    async def test_search_entity_empty_name(self) -> None:
        checker = GLEIFChecker()
        result = await checker.search_entity("")
        assert result.error == "Empty entity name"
        assert result.is_verified is False
        await checker.close()

    async def test_search_entity_success(self) -> None:
        """Test successful GLEIF API search with httpx MockTransport."""

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=_SEARCH_RESPONSE_RAHUL)

        checker = _gleif_checker_with_transport(handler)

        result = await checker.search_entity("RAHUL")

        assert result.is_verified is True
        assert result.match_count == 1
        assert result.best_match is not None
        assert result.best_match.lei == "9845001B2AD43E664E58"
        assert result.best_match.legal_name == "RAHUL"
        assert result.best_match.jurisdiction == "IN"
        assert result.best_match.headquarters_country == "IN"
        assert result.best_match.headquarters_city == "SONIPAT"

        await checker.close()

    async def test_search_entity_no_results(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"data": []})

        checker = _gleif_checker_with_transport(handler)

        result = await checker.search_entity("Nonexistent Corp XYZ")

        assert result.is_verified is False
        assert result.match_count == 0
        await checker.close()

    async def test_search_entity_timeout(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.TimeoutException("timeout")

        checker = _gleif_checker_with_transport(handler)

        result = await checker.search_entity("Test Corp")

        assert result.is_verified is False
        assert result.error == "GLEIF API timeout"
        await checker.close()

    async def test_search_entity_circuit_open(self) -> None:
        """Drive a real CircuitBreaker to OPEN, then verify GLEIFChecker handles it."""
        cb = CircuitBreaker("gleif", failure_threshold=1, recovery_timeout=60.0)

        async def trip() -> None:
            raise RuntimeError("service down")

        with pytest.raises(RuntimeError):
            await cb.call(trip)

        assert cb.state == CircuitState.OPEN

        def should_not_be_called(request: httpx.Request) -> httpx.Response:
            raise AssertionError("HTTP should not be called when circuit is open")

        checker = _gleif_checker_with_transport(should_not_be_called, circuit_breaker=cb)

        result = await checker.search_entity("Test Corp")

        assert result.is_verified is False
        assert "circuit breaker open" in result.error
        await checker.close()

    async def test_lookup_lei_invalid(self) -> None:
        checker = GLEIFChecker()
        result = await checker.lookup_lei("SHORT")
        assert result.error == "Invalid LEI (must be 20 characters)"
        await checker.close()

    async def test_lookup_lei_success(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=_LOOKUP_RESPONSE_RAHUL)

        checker = _gleif_checker_with_transport(handler)

        result = await checker.lookup_lei("9845001B2AD43E664E58")

        assert result.is_verified is True
        assert result.best_match.lei == "9845001B2AD43E664E58"
        await checker.close()

    async def test_lookup_lei_not_found(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(404, json={})

        checker = _gleif_checker_with_transport(handler)

        result = await checker.lookup_lei("00000000000000000000")

        assert result.is_verified is False
        assert result.error == "LEI not found"
        await checker.close()

    async def test_redis_caching(self, fake_redis: RedisClient) -> None:
        """Test that results are cached in Redis."""
        call_count = {"n": 0}

        cached_response = {
            "data": [
                {
                    "id": "TEST1234567890123456",
                    "type": "lei-records",
                    "attributes": {
                        "lei": "TEST1234567890123456",
                        "entity": {
                            "legalName": {"name": "Cached Corp"},
                            "jurisdiction": "US",
                            "category": "GENERAL",
                            "status": "ACTIVE",
                            "headquartersAddress": {"city": "NYC", "country": "US"},
                        },
                        "registration": {"status": "ISSUED"},
                    },
                }
            ]
        }

        def handler(request: httpx.Request) -> httpx.Response:
            call_count["n"] += 1
            return httpx.Response(200, json=cached_response)

        checker = _gleif_checker_with_transport(handler, redis=fake_redis)

        # First call — should hit the transport handler
        result1 = await checker.search_entity("Cached Corp")
        assert result1.is_verified is True
        assert call_count["n"] == 1

        # Second call — should hit Redis cache, not the handler
        result2 = await checker.search_entity("Cached Corp")
        assert result2.is_verified is True
        assert call_count["n"] == 1

        await checker.close()

    async def test_parse_records_handles_bad_data(self) -> None:
        """Ensure malformed records don't crash the parser."""
        records = [
            {"attributes": {}},
            {"bad_key": "bad_value"},
            {
                "id": "VALID12345678901234",
                "attributes": {
                    "lei": "VALID12345678901234",
                    "entity": {
                        "legalName": {"name": "Valid Corp"},
                        "jurisdiction": "US",
                        "category": "GENERAL",
                        "status": "ACTIVE",
                        "headquartersAddress": {},
                    },
                    "registration": {"status": "ISSUED"},
                },
            },
        ]
        entities = GLEIFChecker._parse_records(records)
        assert len(entities) >= 1
        assert any(e.lei == "VALID12345678901234" for e in entities)
