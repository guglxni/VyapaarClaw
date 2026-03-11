"""Shared test fixtures for VyapaarClaw test suite.

All fixtures use REAL implementations — no MagicMock, no patch.
- Redis: fakeredis (in-process Redis implementation, runs real Lua scripts)
- PostgreSQL: real asyncpg client against a test database
- SafeBrowsing: real SafeBrowsingChecker subclass returning real model objects
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
from collections.abc import AsyncGenerator
from typing import Any

import pytest
import pytest_asyncio

from vyapaar_mcp.config import VyapaarConfig
from vyapaar_mcp.db.postgres import PostgresClient
from vyapaar_mcp.db.redis_client import RedisClient
from vyapaar_mcp.models import (
    AgentPolicy,
    SafeBrowsingResponse,
    ThreatMatch,
)
from vyapaar_mcp.reputation.safe_browsing import SafeBrowsingChecker

# ================================================================
# Configuration Fixture
# ================================================================


@pytest.fixture
def config() -> VyapaarConfig:
    """Test configuration with real service URLs from env or defaults."""
    return VyapaarConfig(
        razorpay_key_id=os.environ.get("VYAPAAR_RAZORPAY_KEY_ID", "rzp_test_1234567890"),
        razorpay_key_secret=os.environ.get("VYAPAAR_RAZORPAY_KEY_SECRET", "test_secret_key_12345"),
        razorpay_webhook_secret="test_webhook_secret",
        google_safe_browsing_key="test_gsb_key_12345",
        redis_url=os.environ.get("VYAPAAR_REDIS_URL", "redis://localhost:6379/0"),
        postgres_dsn=os.environ.get(
            "VYAPAAR_POSTGRES_DSN",
            "postgresql://vyapaar:testpass@localhost:5432/vyapaar_test",
        ),
    )


# ================================================================
# Redis Fixture (fakeredis — real Redis implementation in-process)
# ================================================================


@pytest_asyncio.fixture
async def fake_redis() -> AsyncGenerator[RedisClient, None]:
    """Create a fakeredis-backed RedisClient for testing.

    fakeredis implements the full Redis protocol including Lua scripts.
    This is NOT mocking — it's a functional Redis that runs in-process.
    """
    from fakeredis.aioredis import FakeRedis as FakeAioRedis

    client = RedisClient(url="redis://fake:6379/0")
    client._client = FakeAioRedis(decode_responses=True)
    yield client


# ================================================================
# PostgreSQL Fixture (real asyncpg against test database)
# ================================================================


@pytest_asyncio.fixture
async def real_postgres(config: VyapaarConfig) -> AsyncGenerator[PostgresClient, None]:
    """Real PostgreSQL client connected to the test database.

    Runs migrations, seeds a default policy, and cleans up after tests.
    """
    pg = PostgresClient(dsn=config.postgres_dsn)
    await pg.connect()
    await pg.run_migrations()

    default_policy = AgentPolicy(
        agent_id="test-agent-001",
        daily_limit=500000,
        per_txn_limit=100000,
        require_approval_above=50000,
        blocked_domains=["evil.com", "malware.org"],
    )
    await pg.upsert_agent_policy(default_policy)

    yield pg

    async with pg.pool.acquire() as conn:
        await conn.execute("DELETE FROM audit_logs")
        await conn.execute("DELETE FROM agent_policies")
    await pg.disconnect()


# ================================================================
# Safe Browsing Fixtures (real checker subclasses, no mocks)
# ================================================================


class StubSafeBrowsingChecker(SafeBrowsingChecker):
    """A real SafeBrowsingChecker that returns deterministic results.

    Instead of calling Google's API, this subclass returns real
    SafeBrowsingResponse model instances based on a threat map.
    """

    def __init__(self, threat_map: dict[str, list[str]] | None = None) -> None:
        self._threat_map: dict[str, list[str]] = threat_map or {}
        self._api_key = "stub"
        self._api_url = "https://safebrowsing.googleapis.com/v4/threatMatches:find"
        self._redis = None
        self._circuit_breaker = None

    async def check_url(self, url: str) -> SafeBrowsingResponse:
        """Return a real SafeBrowsingResponse based on the threat map."""
        threats = self._threat_map.get(url, [])
        if not threats:
            for pattern, threat_types in self._threat_map.items():
                if pattern in url:
                    threats = threat_types
                    break

        if not threats:
            return SafeBrowsingResponse()

        matches = [
            ThreatMatch(
                threatType=t,
                platformType="ANY_PLATFORM",
                threatEntryType="URL",
                threat={"url": url},
            )
            for t in threats
        ]
        return SafeBrowsingResponse(matches=matches)


@pytest.fixture
def safe_browsing_safe() -> StubSafeBrowsingChecker:
    """Safe Browsing checker that always returns SAFE."""
    return StubSafeBrowsingChecker(threat_map={})


@pytest.fixture
def safe_browsing_unsafe() -> StubSafeBrowsingChecker:
    """Safe Browsing checker that flags specific URLs as MALWARE."""
    return StubSafeBrowsingChecker(
        threat_map={
            "malware": ["MALWARE"],
            "evil": ["MALWARE"],
            "phishing": ["SOCIAL_ENGINEERING"],
        }
    )


# ================================================================
# Webhook Helpers
# ================================================================


def make_webhook_payload(
    payout_id: str = "pout_test_123456",
    amount: int = 50000,
    agent_id: str = "test-agent-001",
    vendor_url: str = "https://safe-vendor.com",
    status: str = "queued",
) -> dict[str, Any]:
    """Create a realistic Razorpay webhook payload for testing."""
    return {
        "entity": "event",
        "account_id": "acc_test_12345",
        "event": "payout.queued",
        "contains": ["payout"],
        "payload": {
            "payout": {
                "entity": {
                    "id": payout_id,
                    "entity": "payout",
                    "fund_account_id": "fa_test_12345",
                    "amount": amount,
                    "currency": "INR",
                    "notes": {
                        "agent_id": agent_id,
                        "purpose": "vendor_payment",
                        "vendor_url": vendor_url,
                    },
                    "fees": 590,
                    "tax": 90,
                    "status": status,
                    "purpose": "payout",
                    "mode": "NEFT",
                    "reference_id": f"txn_test_{payout_id}",
                    "fund_account": {
                        "id": "fa_test_12345",
                        "entity": "fund_account",
                        "contact_id": "cont_test_12345",
                        "account_type": "bank_account",
                        "bank_account": {
                            "ifsc": "HDFC0000001",
                            "bank_name": "HDFC Bank",
                            "name": "Test Vendor Pvt Ltd",
                            "account_number": "1234567890123456",
                        },
                        "contact": {
                            "id": "cont_test_12345",
                            "entity": "contact",
                            "name": "Test Vendor Pvt Ltd",
                            "type": "vendor",
                            "email": "vendor@safe-vendor.com",
                        },
                    },
                    "created_at": 1707561564,
                }
            }
        },
        "created_at": 1707561564,
    }


def sign_payload(payload: dict[str, Any] | bytes, secret: str) -> str:
    """Generate HMAC-SHA256 signature for a webhook payload."""
    body = json.dumps(payload).encode("utf-8") if isinstance(payload, dict) else payload
    return hmac.new(
        key=secret.encode("utf-8"),
        msg=body,
        digestmod=hashlib.sha256,
    ).hexdigest()
