"""Tests for VyapaarClaw v2 proactive CFO tools.

Covers the data-layer methods (Redis historical spend, Postgres
compliance stats / list_all_agents) and the 5 new MCP tool functions
(forecast_cash_flow, generate_compliance_report, get_spending_trends,
evaluate_payout, list_agents).

All tests use REAL implementations — no MagicMock, no patch.
- Redis: fakeredis (in-process, real Lua script execution)
- PostgreSQL: real asyncpg against test database
- SafeBrowsing: StubSafeBrowsingChecker (deterministic, real model objects)
- GovernanceEngine: real engine wired to real Redis/Postgres/SafeBrowsing
"""

from __future__ import annotations

from datetime import date

import pytest

from vyapaar_mcp.db.postgres import PostgresClient
from vyapaar_mcp.db.redis_client import RedisClient
from vyapaar_mcp.governance.engine import GovernanceEngine
from vyapaar_mcp.models import AgentPolicy, Decision, GovernanceResult, ReasonCode

# ================================================================
# Redis: get_historical_spend
# ================================================================


@pytest.mark.asyncio
class TestHistoricalSpend:
    """Test historical spend retrieval from Redis."""

    async def test_empty_history(self, fake_redis: RedisClient) -> None:
        """Agent with no spend returns zero-filled history."""
        history = await fake_redis.get_historical_spend("agent-new", days=7)
        assert len(history) == 7
        assert all(d["spend"] == 0 for d in history)

    async def test_today_spend_appears(self, fake_redis: RedisClient) -> None:
        """Today's budget spend should appear in the last entry."""
        await fake_redis.check_budget_atomic("agent-hist", 25000, 500000)
        history = await fake_redis.get_historical_spend("agent-hist", days=3)
        assert len(history) == 3
        assert history[-1]["date"] == date.today().isoformat()
        assert history[-1]["spend"] == 25000

    async def test_returns_ordered_oldest_first(self, fake_redis: RedisClient) -> None:
        """History should be ordered oldest date first."""
        history = await fake_redis.get_historical_spend("agent-order", days=5)
        dates = [d["date"] for d in history]
        assert dates == sorted(dates)

    async def test_single_day(self, fake_redis: RedisClient) -> None:
        """Requesting 1 day returns only today."""
        await fake_redis.check_budget_atomic("agent-1d", 10000, 500000)
        history = await fake_redis.get_historical_spend("agent-1d", days=1)
        assert len(history) == 1
        assert history[0]["spend"] == 10000


# ================================================================
# Redis: get_all_budget_keys_today
# ================================================================


@pytest.mark.asyncio
class TestAllBudgetKeysToday:
    """Test scanning for today's active budget keys."""

    async def test_no_keys(self, fake_redis: RedisClient) -> None:
        """No budget keys returns empty list."""
        result = await fake_redis.get_all_budget_keys_today()
        assert result == []

    async def test_finds_active_agents(self, fake_redis: RedisClient) -> None:
        """Agents with today's spend should be discovered."""
        await fake_redis.check_budget_atomic("agent-scan-1", 1000, 500000)
        await fake_redis.check_budget_atomic("agent-scan-2", 2000, 500000)
        result = await fake_redis.get_all_budget_keys_today()
        assert set(result) == {"agent-scan-1", "agent-scan-2"}


# ================================================================
# Postgres: list_all_agents (real DB)
# ================================================================


@pytest.mark.asyncio
class TestListAllAgents:
    """Test the list_all_agents Postgres method."""

    async def test_returns_agent_list(self, real_postgres: PostgresClient) -> None:
        """list_all_agents returns properly structured dicts."""
        await real_postgres.upsert_agent_policy(
            AgentPolicy(
                agent_id="agent-A",
                daily_limit=500000,
                per_txn_limit=100000,
                require_approval_above=50000,
                blocked_domains=["evil.com"],
            )
        )

        result = await real_postgres.list_all_agents()

        assert len(result) >= 1
        agent_a = next(a for a in result if a["agent_id"] == "agent-A")
        assert agent_a["agent_id"] == "agent-A"
        assert agent_a["daily_limit"] == 500000
        assert agent_a["blocked_domains"] == ["evil.com"]
        assert agent_a["created_at"] is not None
        assert agent_a["updated_at"] is not None


# ================================================================
# Postgres: get_compliance_stats (real DB)
# ================================================================


@pytest.mark.asyncio
class TestComplianceStats:
    """Test compliance stats aggregation."""

    async def test_returns_structured_stats(self, real_postgres: PostgresClient) -> None:
        """get_compliance_stats returns properly aggregated results."""
        for i in range(8):
            await real_postgres.write_audit_log(
                GovernanceResult(
                    payout_id=f"pout_stat_appr_{i}",
                    agent_id="agent-A",
                    amount=50000,
                    decision=Decision.APPROVED,
                    reason_code=ReasonCode.POLICY_OK,
                    reason_detail="All checks passed",
                    threat_types=[],
                    processing_ms=10,
                )
            )

        reasons = [ReasonCode.LIMIT_EXCEEDED, ReasonCode.DOMAIN_BLOCKED]
        for i, reason in enumerate(reasons):
            await real_postgres.write_audit_log(
                GovernanceResult(
                    payout_id=f"pout_stat_rej_{i}",
                    agent_id="agent-A",
                    amount=50000,
                    decision=Decision.REJECTED,
                    reason_code=reason,
                    reason_detail="Rejected",
                    threat_types=[],
                    processing_ms=10,
                )
            )

        result = await real_postgres.get_compliance_stats(period_days=7)

        assert result["period_days"] == 7
        assert result["total_decisions"] == 10
        assert "APPROVED" in result["decisions"]
        assert result["decisions"]["APPROVED"]["count"] == 8
        assert len(result["top_rejection_reasons"]) == 2
        assert "agent-A" in result["agent_breakdown"]


# ================================================================
# MCP Tool: forecast_cash_flow
# ================================================================


@pytest.mark.asyncio
class TestForecastCashFlow:
    """Test the forecast_cash_flow MCP tool."""

    async def test_single_agent_forecast(
        self, fake_redis: RedisClient, real_postgres: PostgresClient
    ) -> None:
        """Forecast for an agent with spend history."""
        from vyapaar_mcp import server

        orig_redis = server._redis
        orig_postgres = server._postgres

        try:
            server._redis = fake_redis
            server._postgres = real_postgres

            await fake_redis.check_budget_atomic("test-agent-001", 50000, 500000)

            result = await server.forecast_cash_flow(agent_id="test-agent-001", horizon_days=3)

            assert "forecasts" in result
            assert len(result["forecasts"]) == 1
            fc = result["forecasts"][0]
            assert fc["agent_id"] == "test-agent-001"
            assert fc["budget_health"] in ("green", "yellow", "red")
            assert "burn_rate_per_day" in fc
        finally:
            server._redis = orig_redis
            server._postgres = orig_postgres

    async def test_no_agents(self, fake_redis: RedisClient, real_postgres: PostgresClient) -> None:
        """Forecast with no agents returns empty list."""
        from vyapaar_mcp import server

        orig_redis = server._redis
        orig_postgres = server._postgres

        try:
            server._redis = fake_redis
            server._postgres = real_postgres

            async with real_postgres.pool.acquire() as conn:
                await conn.execute("DELETE FROM agent_policies")

            result = await server.forecast_cash_flow(agent_id="", horizon_days=7)
            assert result["forecasts"] == []
        finally:
            server._redis = orig_redis
            server._postgres = orig_postgres

    async def test_inactive_agent(
        self, fake_redis: RedisClient, real_postgres: PostgresClient
    ) -> None:
        """Agent with zero spend should show 'inactive' trend."""
        from vyapaar_mcp import server

        orig_redis = server._redis
        orig_postgres = server._postgres

        try:
            server._redis = fake_redis
            server._postgres = real_postgres

            result = await server.forecast_cash_flow(agent_id="ghost-agent", horizon_days=7)
            fc = result["forecasts"][0]
            assert fc["trend"] == "inactive"
            assert fc["budget_health"] == "green"
        finally:
            server._redis = orig_redis
            server._postgres = orig_postgres


# ================================================================
# MCP Tool: generate_compliance_report
# ================================================================


@pytest.mark.asyncio
class TestGenerateComplianceReport:
    """Test the compliance report MCP tool."""

    async def test_report_structure(self, real_postgres: PostgresClient) -> None:
        """Report with real audit data returns correct structure and calculations."""
        from vyapaar_mcp import server

        orig_postgres = server._postgres

        try:
            server._postgres = real_postgres

            for i in range(10):
                await real_postgres.write_audit_log(
                    GovernanceResult(
                        payout_id=f"pout_rpt_appr_a_{i}",
                        agent_id="agent-A",
                        amount=50000,
                        decision=Decision.APPROVED,
                        reason_code=ReasonCode.POLICY_OK,
                        reason_detail="ok",
                        threat_types=[],
                        processing_ms=10,
                    )
                )

            for i in range(5):
                await real_postgres.write_audit_log(
                    GovernanceResult(
                        payout_id=f"pout_rpt_appr_b_{i}",
                        agent_id="agent-B",
                        amount=50000,
                        decision=Decision.APPROVED,
                        reason_code=ReasonCode.POLICY_OK,
                        reason_detail="ok",
                        threat_types=[],
                        processing_ms=10,
                    )
                )

            for i in range(5):
                await real_postgres.write_audit_log(
                    GovernanceResult(
                        payout_id=f"pout_rpt_rej_{i}",
                        agent_id="agent-A",
                        amount=50000,
                        decision=Decision.REJECTED,
                        reason_code=ReasonCode.LIMIT_EXCEEDED,
                        reason_detail="over limit",
                        threat_types=[],
                        processing_ms=10,
                    )
                )

            result = await server.generate_compliance_report(period_days=7)

            assert result["report_type"] == "compliance"
            assert result["summary"]["total_decisions"] == 20
            assert result["summary"]["approval_rate_pct"] == 75.0
            assert result["summary"]["rejection_rate_pct"] == 25.0
            assert result["summary"]["overall_risk_level"] == "medium"
            assert len(result["high_risk_agents"]) == 1
            assert result["high_risk_agents"][0]["agent_id"] == "agent-A"
        finally:
            server._postgres = orig_postgres

    async def test_empty_period(self, real_postgres: PostgresClient) -> None:
        """Report with zero decisions should return clean defaults."""
        from vyapaar_mcp import server

        orig_postgres = server._postgres

        try:
            server._postgres = real_postgres

            result = await server.generate_compliance_report(period_days=7)
            assert result["summary"]["total_decisions"] == 0
            assert result["summary"]["approval_rate_pct"] == 0
        finally:
            server._postgres = orig_postgres


# ================================================================
# MCP Tool: get_spending_trends
# ================================================================


@pytest.mark.asyncio
class TestGetSpendingTrends:
    """Test the spending trends MCP tool."""

    async def test_trends_with_data(self, fake_redis: RedisClient) -> None:
        """Trends with spend data returns correct summary."""
        from vyapaar_mcp import server

        orig_redis = server._redis

        try:
            server._redis = fake_redis
            await fake_redis.check_budget_atomic("agent-trend", 30000, 500000)

            result = await server.get_spending_trends(agent_id="agent-trend", days=7)

            assert result["agent_id"] == "agent-trend"
            assert len(result["daily_spend"]) == 7
            assert result["summary"]["total_spend_paise"] >= 30000
            assert result["summary"]["active_days"] >= 1
        finally:
            server._redis = orig_redis

    async def test_caps_at_90_days(self, fake_redis: RedisClient) -> None:
        """Days parameter should be capped at 90."""
        from vyapaar_mcp import server

        orig_redis = server._redis

        try:
            server._redis = fake_redis
            result = await server.get_spending_trends(agent_id="agent-cap", days=200)
            assert result["days_requested"] == 90
            assert len(result["daily_spend"]) == 90
        finally:
            server._redis = orig_redis


# ================================================================
# MCP Tool: list_agents
# ================================================================


@pytest.mark.asyncio
class TestListAgents:
    """Test the list_agents MCP tool."""

    async def test_agents_with_budget(
        self, fake_redis: RedisClient, real_postgres: PostgresClient
    ) -> None:
        """Agents list enriches policies with real-time budget data."""
        from vyapaar_mcp import server

        orig_redis = server._redis
        orig_postgres = server._postgres

        try:
            server._redis = fake_redis
            server._postgres = real_postgres

            await real_postgres.upsert_agent_policy(
                AgentPolicy(
                    agent_id="agent-list-1",
                    daily_limit=500000,
                    per_txn_limit=100000,
                    require_approval_above=50000,
                )
            )

            await fake_redis.check_budget_atomic("agent-list-1", 250000, 500000)

            result = await server.list_agents()
            assert result["total_agents"] >= 1
            agent = next(a for a in result["agents"] if a["agent_id"] == "agent-list-1")
            assert agent["agent_id"] == "agent-list-1"
            assert agent["current_daily_spend_paise"] == 250000
            assert agent["utilisation_pct"] == 50.0
            assert agent["budget_health"] == "green"
        finally:
            server._redis = orig_redis
            server._postgres = orig_postgres

    async def test_empty_agents(
        self, fake_redis: RedisClient, real_postgres: PostgresClient
    ) -> None:
        """Empty agent list when no policies exist."""
        from vyapaar_mcp import server

        orig_redis = server._redis
        orig_postgres = server._postgres

        try:
            server._redis = fake_redis
            server._postgres = real_postgres

            async with real_postgres.pool.acquire() as conn:
                await conn.execute("DELETE FROM agent_policies")

            result = await server.list_agents()
            assert result["total_agents"] == 0
            assert result["agents"] == []
        finally:
            server._redis = orig_redis
            server._postgres = orig_postgres


# ================================================================
# MCP Tool: evaluate_payout
# ================================================================


@pytest.mark.asyncio
class TestEvaluatePayout:
    """Test the evaluate_payout orchestrator tool."""

    async def test_approved_payout(
        self,
        fake_redis: RedisClient,
        real_postgres: PostgresClient,
        safe_browsing_safe,
    ) -> None:
        """Payout within policy limits is APPROVED by the real engine."""
        from vyapaar_mcp import server

        orig_redis = server._redis
        orig_postgres = server._postgres
        orig_governance = server._governance

        try:
            server._redis = fake_redis
            server._postgres = real_postgres
            server._governance = GovernanceEngine(
                redis=fake_redis,
                postgres=real_postgres,
                safe_browsing=safe_browsing_safe,
                rate_limit_max=100,
                rate_limit_window=60,
            )

            result = await server.evaluate_payout(
                amount=50000,
                agent_id="test-agent-001",
                vendor_name="Safe Corp",
                vendor_url="https://safe.com",
                purpose="Software license",
            )

            assert result["decision"] == "APPROVED"
            assert result["amount_paise"] == 50000
            assert result["agent_id"] == "test-agent-001"
            assert "processing_ms" in result
        finally:
            server._redis = orig_redis
            server._postgres = orig_postgres
            server._governance = orig_governance

    async def test_rejected_payout(
        self,
        fake_redis: RedisClient,
        real_postgres: PostgresClient,
        safe_browsing_safe,
    ) -> None:
        """Payout exceeding daily budget limit is REJECTED by the real engine."""
        from vyapaar_mcp import server

        orig_redis = server._redis
        orig_postgres = server._postgres
        orig_governance = server._governance

        try:
            server._redis = fake_redis
            server._postgres = real_postgres

            await real_postgres.upsert_agent_policy(
                AgentPolicy(
                    agent_id="agent-eval",
                    daily_limit=100000,
                )
            )

            server._governance = GovernanceEngine(
                redis=fake_redis,
                postgres=real_postgres,
                safe_browsing=safe_browsing_safe,
                rate_limit_max=100,
                rate_limit_window=60,
            )

            result = await server.evaluate_payout(
                amount=999999,
                agent_id="agent-eval",
            )

            assert result["decision"] == "REJECTED"
            assert result["reason_code"] == "LIMIT_EXCEEDED"
        finally:
            server._redis = orig_redis
            server._postgres = orig_postgres
            server._governance = orig_governance
