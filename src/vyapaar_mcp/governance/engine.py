"""Core Governance Engine — orchestrates the entire decision pipeline.

Implements the Decision Matrix from SPEC §8:
1. Verify signature (ingress layer handles this)
2. Check idempotency (Redis SETNX)
3. Fetch agent policy (PostgreSQL)
4. Check budget (Redis INCRBY atomic)
5. Check per-transaction limit
6. Check domain blacklist/whitelist
7. GSTIN / IFSC format validation (when present in payout context)
8. Sanctions screening (when vendor name present)
9. Check vendor reputation (Google Safe Browsing)
10. Anomaly scoring (IsolationForest — HOLD when anomalous)
11. Check approval threshold (human-in-the-loop trigger)
12. Final decision: APPROVE / REJECT / HOLD
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING
from urllib.parse import urlparse

from vyapaar_mcp.cfo.gst_providers import build_gst_chain
from vyapaar_mcp.cfo.sanctions import screen_against_sanctions
from vyapaar_mcp.db.postgres import PostgresClient
from vyapaar_mcp.db.redis_client import RedisClient
from vyapaar_mcp.governance.compliance_checks import (
    check_gstin_format,
    check_ifsc_format,
    extract_payout_context,
)
from vyapaar_mcp.governance.options import GovernanceOptions
from vyapaar_mcp.models import (
    Decision,
    GovernanceResult,
    PayoutEntity,
    ReasonCode,
)
from vyapaar_mcp.observability import metrics
from vyapaar_mcp.reputation.safe_browsing import SafeBrowsingChecker

if TYPE_CHECKING:
    from vyapaar_mcp.reputation.anomaly import TransactionAnomalyScorer

logger = logging.getLogger(__name__)


class GovernanceEngine:
    """Core decision engine for payout governance.

    Evaluates a payout against all policy checks and returns
    a final APPROVE / REJECT / HOLD decision.
    """

    def __init__(
        self,
        redis: RedisClient,
        postgres: PostgresClient,
        safe_browsing: SafeBrowsingChecker,
        rate_limit_max: int = 10,
        rate_limit_window: int = 60,
        options: GovernanceOptions | None = None,
        anomaly_scorer: TransactionAnomalyScorer | None = None,
    ) -> None:
        self._redis = redis
        self._postgres = postgres
        self._safe_browsing = safe_browsing
        self._rate_limit_max = rate_limit_max
        self._rate_limit_window = rate_limit_window
        self._options = options or GovernanceOptions()
        self._anomaly_scorer = anomaly_scorer

    async def evaluate(
        self,
        payout: PayoutEntity,
        agent_id: str,
        vendor_url: str | None = None,
    ) -> GovernanceResult:
        """Run the full governance pipeline on a payout.

        Returns a GovernanceResult with the decision, reason, and metadata.
        """
        start_time = time.monotonic()
        ctx = extract_payout_context(payout)
        if not vendor_url:
            vendor_url = ctx.get("vendor_url") or None

        # --- Step 1: Fetch agent policy ---
        policy = await self._postgres.get_agent_policy(agent_id)
        if policy is None:
            return self._result(
                payout,
                agent_id,
                start_time,
                Decision.REJECTED,
                ReasonCode.NO_POLICY,
                f"No spending policy found for agent '{agent_id}'",
            )

        # --- Step 2: Per-transaction limit check ---
        if policy.per_txn_limit is not None and payout.amount > policy.per_txn_limit:
            return self._result(
                payout,
                agent_id,
                start_time,
                Decision.REJECTED,
                ReasonCode.TXN_LIMIT_EXCEEDED,
                f"Amount {payout.amount} paise exceeds per-txn limit"
                f" of {policy.per_txn_limit} paise",
            )

        # --- Step 2.5: Rate limit check (sliding window) ---
        if self._rate_limit_max > 0:
            allowed, count = await self._redis.check_rate_limit(
                agent_id,
                max_requests=self._rate_limit_max,
                window_seconds=self._rate_limit_window,
            )
            metrics.record_rate_limit_check(allowed=allowed)
            if not allowed:
                return self._result(
                    payout,
                    agent_id,
                    start_time,
                    Decision.REJECTED,
                    ReasonCode.RATE_LIMITED,
                    f"Rate limit exceeded: {count}/{self._rate_limit_max}"
                    f" requests in {self._rate_limit_window}s window",
                )

        # --- Step 3: Daily budget check (ATOMIC Redis) ---
        budget_ok = await self._redis.check_budget_atomic(
            agent_id, payout.amount, policy.daily_limit
        )
        metrics.record_budget_check(ok=budget_ok)
        if not budget_ok:
            current_spend = await self._redis.get_daily_spend(agent_id)
            return self._result(
                payout,
                agent_id,
                start_time,
                Decision.REJECTED,
                ReasonCode.LIMIT_EXCEEDED,
                f"Daily budget exceeded: spent {current_spend}"
                f" + {payout.amount} > limit {policy.daily_limit} paise",
            )

        # --- Step 4: Domain blacklist/whitelist check ---
        if vendor_url:
            domain = self._extract_domain(vendor_url)

            # Check blacklist
            if domain and policy.blocked_domains and domain in policy.blocked_domains:
                await self._redis.rollback_budget(agent_id, payout.amount)
                return self._result(
                    payout,
                    agent_id,
                    start_time,
                    Decision.REJECTED,
                    ReasonCode.DOMAIN_BLOCKED,
                    f"Vendor domain '{domain}' is on the blocklist",
                )

            # Check whitelist (if set, domain must be in it)
            if domain and policy.allowed_domains and domain not in policy.allowed_domains:
                await self._redis.rollback_budget(agent_id, payout.amount)
                return self._result(
                    payout,
                    agent_id,
                    start_time,
                    Decision.REJECTED,
                    ReasonCode.DOMAIN_BLOCKED,
                    f"Vendor domain '{domain}' not in allowlist",
                )

        # --- Step 5: GSTIN format validation ---
        gstin = ctx.get("gstin") or ""
        if self._options.check_gstin_format and gstin:
            gst_ok, gst_detail = check_gstin_format(gstin)
            if not gst_ok:
                await self._redis.rollback_budget(agent_id, payout.amount)
                return self._result(
                    payout,
                    agent_id,
                    start_time,
                    Decision.REJECTED,
                    ReasonCode.GST_INVALID,
                    f"Invalid GSTIN '{gstin}': {gst_detail}",
                )

        # --- Step 5b: Live GSTIN verification (Browserwire / GSP) ---
        if self._options.live_gst and gstin:
            chain = build_gst_chain(
                browserwire_url=self._options.browserwire_url,
                browserwire_key=self._options.browserwire_key,
                gsp_url=self._options.gsp_url,
                gsp_key=self._options.gsp_key,
                enable_live=True,
            )
            live_gst = await chain.verify(gstin, vendor_name)
            recommendation = live_gst.get("recommendation", "PASS")
            if recommendation == "REJECT" or live_gst.get("cancelled"):
                await self._redis.rollback_budget(agent_id, payout.amount)
                return self._result(
                    payout,
                    agent_id,
                    start_time,
                    Decision.REJECTED,
                    ReasonCode.GST_INVALID,
                    f"GSTIN '{gstin}' live status: {live_gst.get('status', 'cancelled')}",
                )
            if recommendation == "HOLD" or live_gst.get("suspended") or live_gst.get("name_match") is False:
                return self._result(
                    payout,
                    agent_id,
                    start_time,
                    Decision.HELD,
                    ReasonCode.APPROVAL_REQUIRED,
                    f"GSTIN '{gstin}' requires review: status={live_gst.get('status')}, "
                    f"name_match={live_gst.get('name_match')}",
                )

        # --- Step 6: IFSC format validation ---
        ifsc = ctx.get("ifsc") or ""
        if self._options.check_ifsc_format and ifsc:
            ifsc_ok, ifsc_detail = check_ifsc_format(ifsc)
            if not ifsc_ok:
                await self._redis.rollback_budget(agent_id, payout.amount)
                return self._result(
                    payout,
                    agent_id,
                    start_time,
                    Decision.REJECTED,
                    ReasonCode.IFSC_INVALID,
                    f"Invalid IFSC '{ifsc}': {ifsc_detail}",
                )

        # --- Step 7: Sanctions screening ---
        vendor_name = ctx.get("vendor_name") or ""
        if self._options.check_sanctions and vendor_name:
            sanctions = await screen_against_sanctions(vendor_name)
            if sanctions.get("screened"):
                match_score = float(sanctions.get("max_match_score", 0))
                if match_score >= self._options.sanctions_reject_score:
                    await self._redis.rollback_budget(agent_id, payout.amount)
                    return self._result(
                        payout,
                        agent_id,
                        start_time,
                        Decision.REJECTED,
                        ReasonCode.SANCTIONS_MATCH,
                        f"Vendor '{vendor_name}' matched sanctions list"
                        f" (score={match_score:.2f})",
                    )

        # --- Step 8: Google Safe Browsing reputation check ---
        if vendor_url:
            sb_result = await self._safe_browsing.check_url(vendor_url)
            metrics.record_reputation_check(safe=sb_result.is_safe)
            if not sb_result.is_safe:
                await self._redis.rollback_budget(agent_id, payout.amount)
                threat_types = sb_result.threat_types
                return self._result(
                    payout,
                    agent_id,
                    start_time,
                    Decision.REJECTED,
                    ReasonCode.RISK_HIGH,
                    f"Google Safe Browsing flagged URL as unsafe: {', '.join(threat_types)}",
                    threat_types=threat_types,
                )

        # --- Step 9: Anomaly scoring ---
        if self._options.check_anomaly and self._anomaly_scorer is not None:
            anomaly = await self._anomaly_scorer.score_transaction(
                amount=payout.amount,
                agent_id=agent_id,
            )
            metrics.record_anomaly_check(
                anomalous=anomaly.is_anomalous,
                model_trained=anomaly.model_trained,
            )
            if anomaly.is_anomalous:
                decision = (
                    Decision.HELD
                    if self._options.anomaly_hold
                    else Decision.REJECTED
                )
                return self._result(
                    payout,
                    agent_id,
                    start_time,
                    decision,
                    ReasonCode.ANOMALY_DETECTED,
                    f"Transaction anomaly detected: risk={anomaly.risk_score:.2f}"
                    f" ({anomaly.detail or 'pattern outlier'})",
                )

        # --- Step 10: Approval threshold check ---
        if (
            policy.require_approval_above is not None
            and payout.amount > policy.require_approval_above
        ):
            return self._result(
                payout,
                agent_id,
                start_time,
                Decision.HELD,
                ReasonCode.APPROVAL_REQUIRED,
                f"Amount {payout.amount} paise exceeds approval"
                f" threshold of {policy.require_approval_above} paise",
            )

        # --- Step 11: All checks passed → APPROVE ---
        return self._result(
            payout,
            agent_id,
            start_time,
            Decision.APPROVED,
            ReasonCode.POLICY_OK,
            "All governance checks passed",
        )

    @staticmethod
    def _extract_domain(url: str) -> str | None:
        """Extract domain from a URL."""
        try:
            parsed = urlparse(url)
            return parsed.netloc or parsed.path.split("/")[0]
        except (ValueError, TypeError, AttributeError):
            return None

    @staticmethod
    def _result(
        payout: PayoutEntity,
        agent_id: str,
        start_time: float,
        decision: Decision,
        reason_code: ReasonCode,
        reason_detail: str,
        threat_types: list[str] | None = None,
    ) -> GovernanceResult:
        """Create a GovernanceResult with processing time."""
        elapsed_ms = int((time.monotonic() - start_time) * 1000)
        result = GovernanceResult(
            decision=decision,
            reason_code=reason_code,
            reason_detail=reason_detail,
            payout_id=payout.id,
            agent_id=agent_id,
            amount=payout.amount,
            threat_types=threat_types or [],
            processing_ms=elapsed_ms,
        )

        log_level = logging.WARNING if decision != Decision.APPROVED else logging.INFO
        logger.log(
            log_level,
            "DECISION: %s | payout=%s agent=%s amount=%d reason=%s (%dms)",
            decision.value,
            payout.id,
            agent_id,
            payout.amount,
            reason_code.value,
            elapsed_ms,
        )
        return result
