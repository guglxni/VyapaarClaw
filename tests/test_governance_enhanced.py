"""Tests for Phase 1 governance pipeline enhancements.

Covers GSTIN, IFSC, sanctions, and anomaly checks wired into GovernanceEngine.
"""

from __future__ import annotations

from typing import Any

import pytest

from tests.conftest import StubSafeBrowsingChecker
from vyapaar_mcp.db.postgres import PostgresClient
from vyapaar_mcp.db.redis_client import RedisClient
from vyapaar_mcp.governance.engine import GovernanceEngine
from vyapaar_mcp.governance.options import GovernanceOptions
from vyapaar_mcp.models import (
    Decision,
    PayoutEntity,
    PayoutNotes,
    RazorpayBankAccount,
    RazorpayFundAccount,
    ReasonCode,
)
from vyapaar_mcp.reputation.anomaly import AnomalyScore, TransactionAnomalyScorer


class StubAnomalyScorer:
    """Returns a fixed anomaly score without sklearn."""

    def __init__(self, is_anomalous: bool = False) -> None:
        self._is_anomalous = is_anomalous

    async def score_transaction(
        self,
        amount: int,
        agent_id: str,
        timestamp: object = None,
    ) -> AnomalyScore:
        return AnomalyScore(
            risk_score=0.9 if self._is_anomalous else 0.1,
            raw_score=-0.5 if self._is_anomalous else 0.5,
            is_anomalous=self._is_anomalous,
            features={"amount_log": 4.0},
            model_trained=True,
            training_samples=50,
            detail="stub anomaly",
        )


def make_payout_with_notes(
    payout_id: str = "pout_enhanced_001",
    amount: int = 10000,
    notes: dict[str, Any] | None = None,
    fund_account: RazorpayFundAccount | None = None,
) -> PayoutEntity:
    """Create payout with optional notes and fund account."""
    return PayoutEntity(
        id=payout_id,
        amount=amount,
        status="queued",
        notes=PayoutNotes(**(notes or {"agent_id": "test-agent-001"})),
        fund_account=fund_account,
    )


@pytest.mark.asyncio
class TestGovernanceEnhanced:
    """Enhanced compliance checks in the governance pipeline."""

    async def test_invalid_gstin_rejects(
        self,
        fake_redis: RedisClient,
        real_postgres: PostgresClient,
        safe_browsing_safe: StubSafeBrowsingChecker,
    ) -> None:
        engine = GovernanceEngine(
            fake_redis,
            real_postgres,
            safe_browsing_safe,
            options=GovernanceOptions(check_gstin_format=True),
        )
        payout = make_payout_with_notes(
            notes={
                "agent_id": "test-agent-001",
                "gstin": "INVALID_GSTIN",
            },
        )
        result = await engine.evaluate(payout, "test-agent-001")

        assert result.decision == Decision.REJECTED
        assert result.reason_code == ReasonCode.GST_INVALID

    async def test_invalid_ifsc_rejects(
        self,
        fake_redis: RedisClient,
        real_postgres: PostgresClient,
        safe_browsing_safe: StubSafeBrowsingChecker,
    ) -> None:
        engine = GovernanceEngine(
            fake_redis,
            real_postgres,
            safe_browsing_safe,
            options=GovernanceOptions(check_ifsc_format=True),
        )
        payout = make_payout_with_notes(
            fund_account=RazorpayFundAccount(
                id="fa_test",
                bank_account=RazorpayBankAccount(
                    ifsc="BADCODE",
                    bank_name="Test Bank",
                    name="Vendor Ltd",
                ),
            ),
        )
        result = await engine.evaluate(payout, "test-agent-001")

        assert result.decision == Decision.REJECTED
        assert result.reason_code == ReasonCode.IFSC_INVALID

    async def test_sanctions_match_rejects(
        self,
        fake_redis: RedisClient,
        real_postgres: PostgresClient,
        safe_browsing_safe: StubSafeBrowsingChecker,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from vyapaar_mcp.governance import engine as gov_engine

        async def sanctions_hit(_name: str, entity_type: str = "Company") -> dict[str, Any]:
            return {
                "screened": True,
                "max_match_score": 0.95,
                "risk_level": "critical",
            }

        monkeypatch.setattr(gov_engine, "screen_against_sanctions", sanctions_hit)

        engine = GovernanceEngine(
            fake_redis,
            real_postgres,
            safe_browsing_safe,
            options=GovernanceOptions(check_sanctions=True),
        )
        payout = make_payout_with_notes(
            notes={
                "agent_id": "test-agent-001",
                "vendor_name": "Sanctioned Corp",
            },
        )
        result = await engine.evaluate(payout, "test-agent-001")

        assert result.decision == Decision.REJECTED
        assert result.reason_code == ReasonCode.SANCTIONS_MATCH

    async def test_anomaly_holds_payout(
        self,
        fake_redis: RedisClient,
        real_postgres: PostgresClient,
        safe_browsing_safe: StubSafeBrowsingChecker,
    ) -> None:
        engine = GovernanceEngine(
            fake_redis,
            real_postgres,
            safe_browsing_safe,
            options=GovernanceOptions(check_anomaly=True, anomaly_hold=True),
            anomaly_scorer=StubAnomalyScorer(is_anomalous=True),  # type: ignore[arg-type]
        )
        result = await engine.evaluate(
            make_payout_with_notes(amount=10000),
            "test-agent-001",
        )

        assert result.decision == Decision.HELD
        assert result.reason_code == ReasonCode.ANOMALY_DETECTED

    async def test_valid_gstin_and_ifsc_approves(
        self,
        fake_redis: RedisClient,
        real_postgres: PostgresClient,
        safe_browsing_safe: StubSafeBrowsingChecker,
    ) -> None:
        engine = GovernanceEngine(
            fake_redis,
            real_postgres,
            safe_browsing_safe,
            options=GovernanceOptions(
                check_gstin_format=True,
                check_ifsc_format=True,
                check_sanctions=False,
                check_anomaly=False,
            ),
        )
        payout = make_payout_with_notes(
            amount=10000,
            notes={
                "agent_id": "test-agent-001",
                "gstin": "27AAPFU0939F1ZV",
                "vendor_url": "https://safe-vendor.com",
            },
            fund_account=RazorpayFundAccount(
                id="fa_test",
                bank_account=RazorpayBankAccount(
                    ifsc="HDFC0001234",
                    bank_name="HDFC Bank",
                    name="Safe Vendor",
                ),
            ),
        )
        result = await engine.evaluate(
            payout,
            "test-agent-001",
            vendor_url="https://safe-vendor.com",
        )

        assert result.decision == Decision.APPROVED
        assert result.reason_code == ReasonCode.POLICY_OK
