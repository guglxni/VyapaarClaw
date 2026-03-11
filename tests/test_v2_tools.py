"""Tests for VyapaarClaw v2 proactive CFO tools.

Covers the data-layer methods (Redis historical spend, Postgres
compliance stats / list_all_agents) and the 5 new MCP tool functions
(forecast_cash_flow, generate_compliance_report, get_spending_trends,
evaluate_payout, list_agents).
"""

from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from vyapaar_mcp.db.redis_client import RedisClient


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
# Postgres: list_all_agents (mocked)
# ================================================================


@pytest.mark.asyncio
class TestListAllAgents:
    """Test the list_all_agents Postgres method."""

    async def test_returns_agent_list(self) -> None:
        """list_all_agents returns properly structured dicts."""
        from vyapaar_mcp.db.postgres import PostgresClient

        pg = PostgresClient.__new__(PostgresClient)
        mock_pool = MagicMock()

        rows = [
            {
                "agent_id": "agent-A",
                "daily_limit": 500000,
                "per_txn_limit": 100000,
                "require_approval_above": 50000,
                "allowed_domains": [],
                "blocked_domains": ["evil.com"],
                "created_at": MagicMock(isoformat=lambda: "2026-01-01T00:00:00"),
                "updated_at": MagicMock(isoformat=lambda: "2026-01-15T00:00:00"),
            },
        ]

        conn = AsyncMock()
        conn.fetch = AsyncMock(return_value=rows)
        ctx = AsyncMock()
        ctx.__aenter__ = AsyncMock(return_value=conn)
        ctx.__aexit__ = AsyncMock(return_value=False)
        mock_pool.acquire = MagicMock(return_value=ctx)

        pg._pool = mock_pool
        result = await pg.list_all_agents()

        assert len(result) == 1
        assert result[0]["agent_id"] == "agent-A"
        assert result[0]["daily_limit"] == 500000
        assert result[0]["blocked_domains"] == ["evil.com"]


# ================================================================
# Postgres: get_compliance_stats (mocked)
# ================================================================


@pytest.mark.asyncio
class TestComplianceStats:
    """Test compliance stats aggregation."""

    async def test_returns_structured_stats(self) -> None:
        from vyapaar_mcp.db.postgres import PostgresClient

        pg = PostgresClient.__new__(PostgresClient)
        mock_pool = MagicMock()

        summary_rows = [
            {"decision": "APPROVED", "cnt": 8, "total_amount": 400000},
            {"decision": "REJECTED", "cnt": 2, "total_amount": 100000},
        ]
        reason_rows = [
            {"reason_code": "LIMIT_EXCEEDED", "cnt": 1},
            {"reason_code": "DOMAIN_BLOCKED", "cnt": 1},
        ]
        agent_rows = [
            {"agent_id": "agent-A", "decision": "APPROVED", "cnt": 6, "total_amount": 300000},
            {"agent_id": "agent-A", "decision": "REJECTED", "cnt": 2, "total_amount": 100000},
            {"agent_id": "agent-B", "decision": "APPROVED", "cnt": 2, "total_amount": 100000},
        ]

        conn = AsyncMock()
        conn.fetch = AsyncMock(side_effect=[summary_rows, reason_rows, agent_rows])
        conn.fetchval = AsyncMock(return_value=10)
        ctx = AsyncMock()
        ctx.__aenter__ = AsyncMock(return_value=conn)
        ctx.__aexit__ = AsyncMock(return_value=False)
        mock_pool.acquire = MagicMock(return_value=ctx)

        pg._pool = mock_pool
        result = await pg.get_compliance_stats(period_days=7)

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

    async def test_single_agent_forecast(self, fake_redis: RedisClient) -> None:
        """Forecast for an agent with spend history."""
        from vyapaar_mcp import server

        orig_redis = server._redis
        orig_postgres = server._postgres

        try:
            server._redis = fake_redis

            mock_pg = MagicMock()
            mock_pg.list_all_agents = AsyncMock(return_value=[])
            mock_pg.get_agent_policy = AsyncMock(
                return_value=MagicMock(daily_limit=500000)
            )
            server._postgres = mock_pg

            await fake_redis.check_budget_atomic("agent-fc", 50000, 500000)

            result = await server.forecast_cash_flow(agent_id="agent-fc", horizon_days=3)

            assert "forecasts" in result
            assert len(result["forecasts"]) == 1
            fc = result["forecasts"][0]
            assert fc["agent_id"] == "agent-fc"
            assert fc["budget_health"] in ("green", "yellow", "red")
            assert "burn_rate_per_day" in fc
        finally:
            server._redis = orig_redis
            server._postgres = orig_postgres

    async def test_no_agents(self, fake_redis: RedisClient) -> None:
        """Forecast with no agents returns empty list."""
        from vyapaar_mcp import server

        orig_redis = server._redis
        orig_postgres = server._postgres

        try:
            server._redis = fake_redis
            mock_pg = MagicMock()
            mock_pg.list_all_agents = AsyncMock(return_value=[])
            server._postgres = mock_pg

            result = await server.forecast_cash_flow(agent_id="", horizon_days=7)
            assert result["forecasts"] == []
        finally:
            server._redis = orig_redis
            server._postgres = orig_postgres

    async def test_inactive_agent(self, fake_redis: RedisClient) -> None:
        """Agent with zero spend should show 'inactive' trend."""
        from vyapaar_mcp import server

        orig_redis = server._redis
        orig_postgres = server._postgres

        try:
            server._redis = fake_redis
            mock_pg = MagicMock()
            mock_pg.list_all_agents = AsyncMock(return_value=[])
            server._postgres = mock_pg

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

    async def test_report_structure(self) -> None:
        from vyapaar_mcp import server

        orig_postgres = server._postgres

        try:
            mock_pg = MagicMock()
            mock_pg.get_compliance_stats = AsyncMock(return_value={
                "period_days": 7,
                "total_decisions": 20,
                "decisions": {
                    "APPROVED": {"count": 15, "total_amount": 750000},
                    "REJECTED": {"count": 5, "total_amount": 250000},
                },
                "top_rejection_reasons": [
                    {"reason": "LIMIT_EXCEEDED", "count": 3},
                ],
                "agent_breakdown": {
                    "agent-A": {
                        "APPROVED": {"count": 10, "total_amount": 500000},
                        "REJECTED": {"count": 5, "total_amount": 250000},
                    },
                },
            })
            server._postgres = mock_pg

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

    async def test_empty_period(self) -> None:
        """Report with zero decisions should return clean defaults."""
        from vyapaar_mcp import server

        orig_postgres = server._postgres

        try:
            mock_pg = MagicMock()
            mock_pg.get_compliance_stats = AsyncMock(return_value={
                "period_days": 7,
                "total_decisions": 0,
                "decisions": {},
                "top_rejection_reasons": [],
                "agent_breakdown": {},
            })
            server._postgres = mock_pg

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

    async def test_agents_with_budget(self, fake_redis: RedisClient) -> None:
        from vyapaar_mcp import server

        orig_redis = server._redis
        orig_postgres = server._postgres

        try:
            server._redis = fake_redis
            mock_pg = MagicMock()
            mock_pg.list_all_agents = AsyncMock(return_value=[
                {
                    "agent_id": "agent-list-1",
                    "daily_limit": 500000,
                    "per_txn_limit": 100000,
                    "require_approval_above": 50000,
                    "allowed_domains": [],
                    "blocked_domains": [],
                    "created_at": "2026-01-01",
                    "updated_at": "2026-01-01",
                },
            ])
            server._postgres = mock_pg

            await fake_redis.check_budget_atomic("agent-list-1", 250000, 500000)

            result = await server.list_agents()
            assert result["total_agents"] == 1
            agent = result["agents"][0]
            assert agent["agent_id"] == "agent-list-1"
            assert agent["current_daily_spend_paise"] == 250000
            assert agent["utilisation_pct"] == 50.0
            assert agent["budget_health"] == "green"
        finally:
            server._redis = orig_redis
            server._postgres = orig_postgres

    async def test_empty_agents(self, fake_redis: RedisClient) -> None:
        from vyapaar_mcp import server

        orig_redis = server._redis
        orig_postgres = server._postgres

        try:
            server._redis = fake_redis
            mock_pg = MagicMock()
            mock_pg.list_all_agents = AsyncMock(return_value=[])
            server._postgres = mock_pg

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

    async def test_approved_payout(self, fake_redis: RedisClient) -> None:
        from vyapaar_mcp import server
        from vyapaar_mcp.models import Decision, GovernanceResult, ReasonCode

        orig_redis = server._redis
        orig_postgres = server._postgres
        orig_governance = server._governance

        try:
            server._redis = fake_redis

            mock_result = GovernanceResult(
                payout_id="eval_test_123",
                agent_id="agent-eval",
                amount=50000,
                decision=Decision.APPROVED,
                reason_code=ReasonCode.POLICY_OK,
                reason_detail="All checks passed",
                threat_types=[],
                processing_ms=42,
            )
            mock_gov = MagicMock()
            mock_gov.evaluate = AsyncMock(return_value=mock_result)
            server._governance = mock_gov

            mock_pg = MagicMock()
            mock_pg.write_audit_log = AsyncMock()
            server._postgres = mock_pg

            result = await server.evaluate_payout(
                amount=50000,
                agent_id="agent-eval",
                vendor_name="Safe Corp",
                vendor_url="https://safe.com",
                purpose="Software license",
            )

            assert result["decision"] == "APPROVED"
            assert result["amount_paise"] == 50000
            assert result["agent_id"] == "agent-eval"
            assert "processing_ms" in result
        finally:
            server._redis = orig_redis
            server._postgres = orig_postgres
            server._governance = orig_governance

    async def test_rejected_payout(self, fake_redis: RedisClient) -> None:
        from vyapaar_mcp import server
        from vyapaar_mcp.models import Decision, GovernanceResult, ReasonCode

        orig_redis = server._redis
        orig_postgres = server._postgres
        orig_governance = server._governance

        try:
            server._redis = fake_redis

            mock_result = GovernanceResult(
                payout_id="eval_test_456",
                agent_id="agent-eval",
                amount=999999,
                decision=Decision.REJECTED,
                reason_code=ReasonCode.LIMIT_EXCEEDED,
                reason_detail="Daily limit exceeded",
                threat_types=[],
                processing_ms=15,
            )
            mock_gov = MagicMock()
            mock_gov.evaluate = AsyncMock(return_value=mock_result)
            server._governance = mock_gov

            mock_pg = MagicMock()
            mock_pg.write_audit_log = AsyncMock()
            server._postgres = mock_pg

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
