"""Smoke tests for the showcase demo and core integration.

Tests verify:
- Demo script imports work correctly
- Governance engine decision matrix (all 7 outcomes)
- Budget enforcement with reset
- Config loads with Kimi K2.5 defaults

Zero mocks. Uses real PostgresClient, real RedisClient (fakeredis),
and real SafeBrowsingChecker subclass.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from tests.conftest import StubSafeBrowsingChecker
from vyapaar_mcp.config import VyapaarConfig
from vyapaar_mcp.db.postgres import PostgresClient
from vyapaar_mcp.db.redis_client import RedisClient
from vyapaar_mcp.governance.engine import GovernanceEngine
from vyapaar_mcp.models import (
    AgentPolicy,
    Decision,
    PayoutEntity,
    ReasonCode,
)

# ================================================================
# Config Smoke Tests
# ================================================================


class TestConfigSmoke:
    """Verify config loads correctly with Kimi K2.5 defaults."""

    def test_kimi_k2_5_default_model(self) -> None:
        config = VyapaarConfig(
            razorpay_key_id="rzp_test_xxx",
            razorpay_key_secret="secret",
            google_safe_browsing_key="gsb",
            postgres_dsn="postgresql://test:test@localhost/test",
        )
        assert config.azure_openai_deployment == "kimi-k2.5"

    def test_kimi_k2_5_default_api_version(self) -> None:
        config = VyapaarConfig(
            razorpay_key_id="rzp_test_xxx",
            razorpay_key_secret="secret",
            google_safe_browsing_key="gsb",
            postgres_dsn="postgresql://test:test@localhost/test",
        )
        assert config.azure_openai_api_version == "2024-05-01-preview"

    def test_kimi_k2_5_default_endpoint(self) -> None:
        config = VyapaarConfig(
            razorpay_key_id="rzp_test_xxx",
            razorpay_key_secret="secret",
            google_safe_browsing_key="gsb",
            postgres_dsn="postgresql://test:test@localhost/test",
        )
        assert "services.ai.azure.com" in config.azure_openai_endpoint


# ================================================================
# Governance Decision Matrix Smoke Tests
# ================================================================


@pytest.mark.asyncio
class TestGovernanceDecisionMatrix:
    """Test all 7 decision paths using real components."""

    @pytest.fixture
    def engine(
        self,
        fake_redis: RedisClient,
        real_postgres: PostgresClient,
    ) -> GovernanceEngine:
        safe_browsing = StubSafeBrowsingChecker(threat_map={})
        return GovernanceEngine(
            redis=fake_redis,
            postgres=real_postgres,
            safe_browsing=safe_browsing,
        )

    @pytest.fixture
    def payout(self) -> PayoutEntity:
        return PayoutEntity(
            id="pout_test_001",
            amount=100000,
            currency="INR",
            status="queued",
            mode="IMPS",
            purpose="vendor_payment",
        )

    @pytest.fixture
    def policy(self) -> AgentPolicy:
        return AgentPolicy(
            agent_id="smoke-agent",
            daily_limit=500000,
            per_txn_limit=200000,
            require_approval_above=150000,
            allowed_domains=[],
            blocked_domains=["evil.xyz"],
        )

    async def test_no_policy_rejects(
        self,
        engine: GovernanceEngine,
        payout: PayoutEntity,
    ) -> None:
        result = await engine.evaluate(payout, "unknown-agent-zzz")
        assert result.decision == Decision.REJECTED
        assert result.reason_code == ReasonCode.NO_POLICY

    async def test_per_txn_limit_rejects(
        self,
        engine: GovernanceEngine,
        policy: AgentPolicy,
        real_postgres: PostgresClient,
    ) -> None:
        await real_postgres.upsert_agent_policy(policy)

        big_payout = PayoutEntity(
            id="pout_big",
            amount=300000,
            currency="INR",
            status="queued",
            mode="IMPS",
            purpose="vendor_payment",
        )

        result = await engine.evaluate(big_payout, "smoke-agent")
        assert result.decision == Decision.REJECTED
        assert result.reason_code == ReasonCode.TXN_LIMIT_EXCEEDED

    async def test_domain_blocked_rejects(
        self,
        engine: GovernanceEngine,
        payout: PayoutEntity,
        policy: AgentPolicy,
        real_postgres: PostgresClient,
    ) -> None:
        await real_postgres.upsert_agent_policy(policy)

        result = await engine.evaluate(payout, "smoke-agent", "https://evil.xyz/pay")
        assert result.decision == Decision.REJECTED
        assert result.reason_code == ReasonCode.DOMAIN_BLOCKED

    async def test_safe_browsing_threat_rejects(
        self,
        fake_redis: RedisClient,
        real_postgres: PostgresClient,
        payout: PayoutEntity,
        policy: AgentPolicy,
    ) -> None:
        await real_postgres.upsert_agent_policy(policy)

        unsafe_sb = StubSafeBrowsingChecker(threat_map={"malware": ["MALWARE"]})
        engine = GovernanceEngine(fake_redis, real_postgres, unsafe_sb)

        result = await engine.evaluate(payout, "smoke-agent", "https://malware-site.com")
        assert result.decision == Decision.REJECTED
        assert result.reason_code == ReasonCode.RISK_HIGH

    async def test_approval_threshold_holds(
        self,
        engine: GovernanceEngine,
        policy: AgentPolicy,
        real_postgres: PostgresClient,
    ) -> None:
        await real_postgres.upsert_agent_policy(policy)

        held_payout = PayoutEntity(
            id="pout_held",
            amount=180000,
            currency="INR",
            status="queued",
            mode="IMPS",
            purpose="vendor_payment",
        )

        result = await engine.evaluate(held_payout, "smoke-agent", "https://safe.com")
        assert result.decision == Decision.HELD
        assert result.reason_code == ReasonCode.APPROVAL_REQUIRED

    async def test_all_checks_pass_approves(
        self,
        engine: GovernanceEngine,
        payout: PayoutEntity,
        policy: AgentPolicy,
        real_postgres: PostgresClient,
    ) -> None:
        await real_postgres.upsert_agent_policy(policy)

        result = await engine.evaluate(payout, "smoke-agent", "https://google.com")
        assert result.decision == Decision.APPROVED
        assert result.reason_code == ReasonCode.POLICY_OK

    async def test_processing_time_recorded(
        self,
        engine: GovernanceEngine,
        payout: PayoutEntity,
        policy: AgentPolicy,
        real_postgres: PostgresClient,
    ) -> None:
        await real_postgres.upsert_agent_policy(policy)

        result = await engine.evaluate(payout, "smoke-agent")
        assert result.processing_ms >= 0


# ================================================================
# Budget + Reset Smoke Tests
# ================================================================


@pytest.mark.asyncio
class TestBudgetResetSmoke:
    """Smoke tests for budget enforcement with reset capability."""

    async def test_full_budget_lifecycle(self, fake_redis: RedisClient) -> None:
        agent = "smoke-agent"
        limit = 100000

        ok = await fake_redis.check_budget_atomic(agent, 60000, limit)
        assert ok is True

        ok = await fake_redis.check_budget_atomic(agent, 30000, limit)
        assert ok is True

        ok = await fake_redis.check_budget_atomic(agent, 20000, limit)
        assert ok is False

        spent = await fake_redis.get_daily_spend(agent)
        assert spent == 90000

        await fake_redis.reset_daily_spend(agent)
        spent = await fake_redis.get_daily_spend(agent)
        assert spent == 0

        ok = await fake_redis.check_budget_atomic(agent, 50000, limit)
        assert ok is True
        spent = await fake_redis.get_daily_spend(agent)
        assert spent == 50000


# ================================================================
# Demo Script Import Smoke Test
# ================================================================


class TestDemoImports:
    """Verify all demo imports work without errors."""

    def test_showcase_demo_importable(self) -> None:
        demo_dir = Path(__file__).resolve().parent.parent / "demo"
        src_dir = Path(__file__).resolve().parent.parent / "src"
        sys.path.insert(0, str(demo_dir))
        sys.path.insert(0, str(src_dir))

        try:
            import showcase_demo  # type: ignore

            assert hasattr(showcase_demo, "run_showcase")
        finally:
            sys.path.pop(0)
            sys.path.pop(0)
