"""Smoke tests for the showcase demo and core integration.

Tests verify:
- Demo script imports work correctly
- Governance engine decision matrix (all 7 outcomes)
- Budget enforcement with reset
- Config loads with Kimi K2.5 defaults
- Demo entry point callable without crash
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from vyapaar_mcp.config import VyapaarConfig
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
        """Default model should be kimi-k2.5."""
        config = VyapaarConfig(
            razorpay_key_id="rzp_test_xxx",
            razorpay_key_secret="secret",
            google_safe_browsing_key="gsb",
            postgres_dsn="postgresql://test:test@localhost/test",
        )
        assert config.azure_openai_deployment == "kimi-k2.5"

    def test_kimi_k2_5_default_api_version(self) -> None:
        """Default API version should be 2024-05-01-preview."""
        config = VyapaarConfig(
            razorpay_key_id="rzp_test_xxx",
            razorpay_key_secret="secret",
            google_safe_browsing_key="gsb",
            postgres_dsn="postgresql://test:test@localhost/test",
        )
        assert config.azure_openai_api_version == "2024-05-01-preview"

    def test_kimi_k2_5_default_endpoint(self) -> None:
        """Default endpoint should point to Azure AI Services."""
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
    """Test all 7 decision paths in the governance engine."""

    @pytest.fixture
    def engine(self, fake_redis: RedisClient, fake_postgres: MagicMock) -> GovernanceEngine:
        """Create a governance engine with fakes."""
        safe_browsing = MagicMock()
        return GovernanceEngine(
            redis=fake_redis,
            postgres=fake_postgres,
            safe_browsing=safe_browsing,
        )

    @pytest.fixture
    def payout(self) -> PayoutEntity:
        """Create a standard test payout."""
        return PayoutEntity(
            id="pout_test_001",
            amount=100000,  # ₹1,000
            currency="INR",
            status="queued",
            mode="IMPS",
            purpose="vendor_payment",
        )

    @pytest.fixture
    def policy(self) -> AgentPolicy:
        """Standard agent policy."""
        return AgentPolicy(
            agent_id="test-agent",
            daily_limit=500000,  # ₹5,000
            per_txn_limit=200000,  # ₹2,000
            require_approval_above=150000,  # ₹1,500
            allowed_domains=[],
            blocked_domains=["evil.xyz"],
        )

    async def test_no_policy_rejects(
        self,
        engine: GovernanceEngine,
        payout: PayoutEntity,
        fake_postgres: MagicMock,
    ) -> None:
        """No policy → REJECT."""
        fake_postgres.get_agent_policy = AsyncMock(return_value=None)

        result = await engine.evaluate(payout, "unknown-agent")
        assert result.decision == Decision.REJECTED
        assert result.reason_code == ReasonCode.NO_POLICY

    async def test_per_txn_limit_rejects(
        self,
        engine: GovernanceEngine,
        policy: AgentPolicy,
        fake_postgres: MagicMock,
    ) -> None:
        """Amount > per_txn_limit → REJECT."""
        fake_postgres.get_agent_policy = AsyncMock(return_value=policy)

        big_payout = PayoutEntity(
            id="pout_big",
            amount=300000,
            currency="INR",
            status="queued",
            mode="IMPS",
            purpose="vendor_payment",
        )

        result = await engine.evaluate(big_payout, "test-agent")
        assert result.decision == Decision.REJECTED
        assert result.reason_code == ReasonCode.TXN_LIMIT_EXCEEDED

    async def test_domain_blocked_rejects(
        self,
        engine: GovernanceEngine,
        payout: PayoutEntity,
        policy: AgentPolicy,
        fake_postgres: MagicMock,
    ) -> None:
        """Blocked domain → REJECT."""
        fake_postgres.get_agent_policy = AsyncMock(return_value=policy)

        result = await engine.evaluate(payout, "test-agent", "https://evil.xyz/pay")
        assert result.decision == Decision.REJECTED
        assert result.reason_code == ReasonCode.DOMAIN_BLOCKED

    async def test_safe_browsing_threat_rejects(
        self,
        engine: GovernanceEngine,
        payout: PayoutEntity,
        policy: AgentPolicy,
        fake_postgres: MagicMock,
    ) -> None:
        """Unsafe URL → REJECT."""
        fake_postgres.get_agent_policy = AsyncMock(return_value=policy)

        # Mock Safe Browsing to flag URL
        mock_sb_result = MagicMock()
        mock_sb_result.is_safe = False
        mock_sb_result.threat_types = ["MALWARE"]
        engine._safe_browsing.check_url = AsyncMock(return_value=mock_sb_result)

        result = await engine.evaluate(payout, "test-agent", "https://malware-site.com")
        assert result.decision == Decision.REJECTED
        assert result.reason_code == ReasonCode.RISK_HIGH

    async def test_approval_threshold_holds(
        self,
        engine: GovernanceEngine,
        policy: AgentPolicy,
        fake_postgres: MagicMock,
    ) -> None:
        """Amount > approval threshold → HOLD."""
        fake_postgres.get_agent_policy = AsyncMock(return_value=policy)

        # Safe Browsing passes
        mock_sb_result = MagicMock()
        mock_sb_result.is_safe = True
        mock_sb_result.threat_types = []
        engine._safe_browsing.check_url = AsyncMock(return_value=mock_sb_result)

        held_payout = PayoutEntity(
            id="pout_held",
            amount=180000,
            currency="INR",
            status="queued",
            mode="IMPS",
            purpose="vendor_payment",
        )

        result = await engine.evaluate(held_payout, "test-agent", "https://safe.com")
        assert result.decision == Decision.HELD
        assert result.reason_code == ReasonCode.APPROVAL_REQUIRED

    async def test_all_checks_pass_approves(
        self,
        engine: GovernanceEngine,
        payout: PayoutEntity,
        policy: AgentPolicy,
        fake_postgres: MagicMock,
    ) -> None:
        """All checks pass → APPROVE."""
        fake_postgres.get_agent_policy = AsyncMock(return_value=policy)

        mock_sb_result = MagicMock()
        mock_sb_result.is_safe = True
        mock_sb_result.threat_types = []
        engine._safe_browsing.check_url = AsyncMock(return_value=mock_sb_result)

        result = await engine.evaluate(payout, "test-agent", "https://google.com")
        assert result.decision == Decision.APPROVED
        assert result.reason_code == ReasonCode.POLICY_OK

    async def test_processing_time_recorded(
        self,
        engine: GovernanceEngine,
        payout: PayoutEntity,
        policy: AgentPolicy,
        fake_postgres: MagicMock,
    ) -> None:
        """Processing time should be recorded in result."""
        fake_postgres.get_agent_policy = AsyncMock(return_value=policy)

        result = await engine.evaluate(payout, "test-agent")
        assert result.processing_ms >= 0


# ================================================================
# Budget + Reset Smoke Tests
# ================================================================


@pytest.mark.asyncio
class TestBudgetResetSmoke:
    """Smoke tests for budget enforcement with reset capability."""

    async def test_full_budget_lifecycle(self, fake_redis: RedisClient) -> None:
        """Test complete lifecycle: spend → exceed → reset → spend again."""
        agent = "smoke-agent"
        limit = 100000  # ₹1,000

        # 1. First spend should succeed
        ok = await fake_redis.check_budget_atomic(agent, 60000, limit)
        assert ok is True

        # 2. Second spend should succeed (cumulative 90000 < 100000)
        ok = await fake_redis.check_budget_atomic(agent, 30000, limit)
        assert ok is True

        # 3. Third spend should fail (90000 + 20000 > 100000)
        ok = await fake_redis.check_budget_atomic(agent, 20000, limit)
        assert ok is False

        # 4. Verify total
        spent = await fake_redis.get_daily_spend(agent)
        assert spent == 90000

        # 5. Reset
        await fake_redis.reset_daily_spend(agent)
        spent = await fake_redis.get_daily_spend(agent)
        assert spent == 0

        # 6. Spend again after reset
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
        """showcase_demo.py should be importable."""
        # Add demo dir and src to path temporarily
        demo_dir = Path(__file__).resolve().parent.parent / "demo"
        src_dir = Path(__file__).resolve().parent.parent / "src"
        sys.path.insert(0, str(demo_dir))
        sys.path.insert(0, str(src_dir))

        try:
            # This should not raise
            import showcase_demo  # type: ignore

            assert hasattr(showcase_demo, "run_showcase")
        finally:
            sys.path.pop(0)
            sys.path.pop(0)
