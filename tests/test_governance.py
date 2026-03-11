"""Tests for the governance engine decision matrix.

Tests every row of SPEC section 8 Decision Matrix using real components:
- Real RedisClient (fakeredis)
- Real PostgresClient (against test database)
- Real SafeBrowsingChecker subclass (StubSafeBrowsingChecker)
- Real model instances throughout

Zero mocks. Zero patches.
"""

from __future__ import annotations

import pytest

from tests.conftest import StubSafeBrowsingChecker
from vyapaar_mcp.db.postgres import PostgresClient
from vyapaar_mcp.db.redis_client import RedisClient
from vyapaar_mcp.governance.engine import GovernanceEngine
from vyapaar_mcp.models import (
    Decision,
    PayoutEntity,
    ReasonCode,
)


def make_payout(
    payout_id: str = "pout_test_001",
    amount: int = 50000,
) -> PayoutEntity:
    """Create a test PayoutEntity."""
    return PayoutEntity(
        id=payout_id,
        amount=amount,
        status="queued",
    )


@pytest.mark.asyncio
class TestGovernanceEngine:
    """Test the full governance decision engine."""

    async def test_no_policy_rejects(
        self,
        fake_redis: RedisClient,
        real_postgres: PostgresClient,
        safe_browsing_safe: StubSafeBrowsingChecker,
    ) -> None:
        """Agent with no policy should be REJECTED (SPEC section 8 row 3)."""
        engine = GovernanceEngine(fake_redis, real_postgres, safe_browsing_safe)
        result = await engine.evaluate(make_payout(), "nonexistent-agent-xyz")

        assert result.decision == Decision.REJECTED
        assert result.reason_code == ReasonCode.NO_POLICY

    async def test_per_txn_limit_exceeded(
        self,
        fake_redis: RedisClient,
        real_postgres: PostgresClient,
        safe_browsing_safe: StubSafeBrowsingChecker,
    ) -> None:
        """Amount exceeding per-txn limit should be REJECTED (SPEC section 8 row 5)."""
        engine = GovernanceEngine(fake_redis, real_postgres, safe_browsing_safe)
        result = await engine.evaluate(make_payout(amount=200000), "test-agent-001")

        assert result.decision == Decision.REJECTED
        assert result.reason_code == ReasonCode.TXN_LIMIT_EXCEEDED

    async def test_daily_limit_exceeded(
        self,
        fake_redis: RedisClient,
        real_postgres: PostgresClient,
        safe_browsing_safe: StubSafeBrowsingChecker,
    ) -> None:
        """Cumulative spend exceeding daily limit should be REJECTED (SPEC section 8 row 4)."""
        engine = GovernanceEngine(fake_redis, real_postgres, safe_browsing_safe)

        for i in range(5):
            await engine.evaluate(
                make_payout(payout_id=f"pout_fill_{i}", amount=100000),
                "test-agent-001",
            )

        result = await engine.evaluate(
            make_payout(payout_id="pout_over", amount=100000), "test-agent-001"
        )
        assert result.decision == Decision.REJECTED
        assert result.reason_code == ReasonCode.LIMIT_EXCEEDED

    async def test_domain_blocked_rejects(
        self,
        fake_redis: RedisClient,
        real_postgres: PostgresClient,
        safe_browsing_safe: StubSafeBrowsingChecker,
    ) -> None:
        """Vendor on blocklist should be REJECTED (SPEC section 8 row 7)."""
        engine = GovernanceEngine(fake_redis, real_postgres, safe_browsing_safe)
        result = await engine.evaluate(
            make_payout(amount=10000),
            "test-agent-001",
            vendor_url="https://evil.com/pay",
        )

        assert result.decision == Decision.REJECTED
        assert result.reason_code == ReasonCode.DOMAIN_BLOCKED

    async def test_safe_browsing_unsafe_rejects(
        self,
        fake_redis: RedisClient,
        real_postgres: PostgresClient,
        safe_browsing_unsafe: StubSafeBrowsingChecker,
    ) -> None:
        """URL flagged by Safe Browsing should be REJECTED (SPEC section 8 row 6)."""
        engine = GovernanceEngine(fake_redis, real_postgres, safe_browsing_unsafe)
        result = await engine.evaluate(
            make_payout(amount=10000),
            "test-agent-001",
            vendor_url="https://malware-site.com",
        )

        assert result.decision == Decision.REJECTED
        assert result.reason_code == ReasonCode.RISK_HIGH
        assert "MALWARE" in result.threat_types

    async def test_approval_threshold_holds(
        self,
        fake_redis: RedisClient,
        real_postgres: PostgresClient,
        safe_browsing_safe: StubSafeBrowsingChecker,
    ) -> None:
        """Amount above approval threshold should be HELD (SPEC section 8 row 8)."""
        engine = GovernanceEngine(fake_redis, real_postgres, safe_browsing_safe)
        result = await engine.evaluate(
            make_payout(amount=75000),
            "test-agent-001",
            vendor_url="https://safe-vendor.com",
        )

        assert result.decision == Decision.HELD
        assert result.reason_code == ReasonCode.APPROVAL_REQUIRED

    async def test_all_checks_pass_approves(
        self,
        fake_redis: RedisClient,
        real_postgres: PostgresClient,
        safe_browsing_safe: StubSafeBrowsingChecker,
    ) -> None:
        """All checks passing should APPROVE (SPEC section 8 row 9)."""
        engine = GovernanceEngine(fake_redis, real_postgres, safe_browsing_safe)
        result = await engine.evaluate(
            make_payout(amount=10000),
            "test-agent-001",
            vendor_url="https://safe-vendor.com",
        )

        assert result.decision == Decision.APPROVED
        assert result.reason_code == ReasonCode.POLICY_OK

    async def test_processing_time_tracked(
        self,
        fake_redis: RedisClient,
        real_postgres: PostgresClient,
        safe_browsing_safe: StubSafeBrowsingChecker,
    ) -> None:
        """Processing time should be tracked in milliseconds."""
        engine = GovernanceEngine(fake_redis, real_postgres, safe_browsing_safe)
        result = await engine.evaluate(
            make_payout(amount=10000),
            "test-agent-001",
        )

        assert result.processing_ms is not None
        assert result.processing_ms >= 0
