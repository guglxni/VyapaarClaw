"""PostgreSQL client for audit logs and agent policies.

Uses asyncpg for async, parameterized queries (SQL injection safe).
"""

from __future__ import annotations

import logging
from typing import Any

import asyncpg

from vyapaar_mcp.models import AgentPolicy, AuditLogEntry, Decision, GovernanceResult, ReasonCode

logger = logging.getLogger(__name__)


class PostgresClient:
    """Async PostgreSQL client for Vyapaar data layer."""

    def __init__(self, dsn: str) -> None:
        self._dsn = dsn
        self._pool: asyncpg.Pool | None = None  # type: ignore[type-arg]

    async def connect(self) -> None:
        """Create connection pool with timeouts."""
        self._pool = await asyncpg.create_pool(
            self._dsn,
            min_size=2,
            max_size=10,
            command_timeout=30,
        )
        logger.info("PostgreSQL pool created: %s", self._dsn.split("@")[-1])

    async def disconnect(self) -> None:
        """Close connection pool."""
        if self._pool:
            await self._pool.close()
            logger.info("PostgreSQL pool closed")

    @property
    def pool(self) -> asyncpg.Pool:  # type: ignore[type-arg]
        """Get the connection pool."""
        if self._pool is None:
            raise RuntimeError("PostgreSQL not connected. Call connect() first.")
        return self._pool

    async def ping(self) -> bool:
        """Check if PostgreSQL is reachable."""
        try:
            async with self.pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            return True
        except (asyncpg.PostgresError, RuntimeError, ConnectionError, TimeoutError):
            return False

    # ================================================================
    # Schema Migration
    # ================================================================

    async def run_migrations(self) -> None:
        """Run database migrations to create tables."""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS agent_policies (
                    agent_id        VARCHAR(128) PRIMARY KEY,
                    daily_limit     BIGINT       NOT NULL DEFAULT 500000,
                    per_txn_limit   BIGINT       DEFAULT NULL,
                    require_approval_above BIGINT DEFAULT NULL,
                    allowed_domains TEXT[]       DEFAULT '{}',
                    blocked_domains TEXT[]       DEFAULT '{}',
                    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
                    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
                );
            """)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id              BIGSERIAL    PRIMARY KEY,
                    payout_id       VARCHAR(64)  NOT NULL UNIQUE,
                    agent_id        VARCHAR(128) NOT NULL,
                    amount          BIGINT       NOT NULL,
                    currency        VARCHAR(3)   NOT NULL DEFAULT 'INR',
                    vendor_name     TEXT,
                    vendor_url      TEXT,
                    decision        VARCHAR(20)  NOT NULL,
                    reason_code     VARCHAR(64)  NOT NULL,
                    reason_detail   TEXT,
                    threat_types    TEXT[]        DEFAULT '{}',
                    processing_ms   INTEGER,
                    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
                );
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_audit_agent
                ON audit_logs(agent_id);
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_audit_created
                ON audit_logs(created_at);
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_audit_payout
                ON audit_logs(payout_id);
            """)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS payout_workflows (
                    payout_id       VARCHAR(64)  PRIMARY KEY,
                    agent_id        VARCHAR(128) NOT NULL DEFAULT '',
                    amount_paise    BIGINT       NOT NULL DEFAULT 0,
                    current_state   VARCHAR(32)  NOT NULL DEFAULT 'queued',
                    history         JSONB        NOT NULL DEFAULT '[]',
                    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
                    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
                );
            """)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS ledger_entries (
                    id              BIGSERIAL    PRIMARY KEY,
                    reference       VARCHAR(128) NOT NULL DEFAULT '',
                    description     TEXT         NOT NULL,
                    account_code    VARCHAR(16)  NOT NULL,
                    account_name    VARCHAR(128) NOT NULL,
                    debit_paise     BIGINT       NOT NULL DEFAULT 0,
                    credit_paise    BIGINT       NOT NULL DEFAULT 0,
                    entry_date      DATE         NOT NULL DEFAULT CURRENT_DATE,
                    metadata        JSONB        NOT NULL DEFAULT '{}',
                    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
                );
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_ledger_reference
                ON ledger_entries(reference);
            """)
            logger.info("Database migrations completed")

    # ================================================================
    # Agent Policies
    # ================================================================

    async def get_agent_policy(self, agent_id: str) -> AgentPolicy | None:
        """Fetch spending policy for an agent."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM agent_policies WHERE agent_id = $1",
                agent_id,
            )
            if row is None:
                return None
            return AgentPolicy(
                agent_id=row["agent_id"],
                daily_limit=row["daily_limit"],
                per_txn_limit=row["per_txn_limit"],
                require_approval_above=row["require_approval_above"],
                allowed_domains=list(row["allowed_domains"] or []),
                blocked_domains=list(row["blocked_domains"] or []),
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )

    async def upsert_agent_policy(self, policy: AgentPolicy) -> AgentPolicy:
        """Create or update an agent policy."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO agent_policies
                    (agent_id, daily_limit, per_txn_limit, require_approval_above,
                     allowed_domains, blocked_domains, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, NOW())
                ON CONFLICT (agent_id) DO UPDATE SET
                    daily_limit = EXCLUDED.daily_limit,
                    per_txn_limit = EXCLUDED.per_txn_limit,
                    require_approval_above = EXCLUDED.require_approval_above,
                    allowed_domains = EXCLUDED.allowed_domains,
                    blocked_domains = EXCLUDED.blocked_domains,
                    updated_at = NOW()
                """,
                policy.agent_id,
                policy.daily_limit,
                policy.per_txn_limit,
                policy.require_approval_above,
                policy.allowed_domains,
                policy.blocked_domains,
            )
        logger.info("Policy upserted for agent: %s", policy.agent_id)
        return policy

    # ================================================================
    # Audit Logs
    # ================================================================

    async def write_audit_log(self, result: GovernanceResult, **kwargs: str | None) -> None:
        """Write a governance decision to the audit log."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO audit_logs
                    (payout_id, agent_id, amount, vendor_name, vendor_url,
                     decision, reason_code, reason_detail, threat_types, processing_ms)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                ON CONFLICT (payout_id) DO NOTHING
                """,
                result.payout_id,
                result.agent_id,
                result.amount,
                kwargs.get("vendor_name"),
                kwargs.get("vendor_url"),
                result.decision.value,
                result.reason_code.value,
                result.reason_detail,
                result.threat_types,
                result.processing_ms,
            )
        logger.info(
            "Audit logged: payout=%s decision=%s reason=%s",
            result.payout_id,
            result.decision.value,
            result.reason_code.value,
        )

    async def list_all_agents(self) -> list[dict[str, Any]]:
        """List all agents with active policies.

        Returns agent_id, daily_limit, per_txn_limit,
        require_approval_above, and domain restrictions.
        """
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM agent_policies ORDER BY agent_id")

        return [
            {
                "agent_id": row["agent_id"],
                "daily_limit": row["daily_limit"],
                "per_txn_limit": row["per_txn_limit"],
                "require_approval_above": row["require_approval_above"],
                "allowed_domains": list(row["allowed_domains"] or []),
                "blocked_domains": list(row["blocked_domains"] or []),
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
            }
            for row in rows
        ]

    async def get_compliance_stats(
        self,
        period_days: int = 7,
        agent_id: str | None = None,
    ) -> dict[str, Any]:
        """Aggregate governance decisions for compliance reporting.

        Returns decision counts, top rejection reasons, highest-risk
        agents, and per-agent breakdowns.
        """
        from datetime import timedelta

        conditions: list[str] = ["created_at >= NOW() - $1::interval"]
        params: list[Any] = [timedelta(days=period_days)]
        param_idx = 2

        if agent_id:
            conditions.append(f"agent_id = ${param_idx}")
            params.append(agent_id)
            param_idx += 1

        where = "WHERE " + " AND ".join(conditions)

        async with self.pool.acquire() as conn:
            summary = await conn.fetch(
                f"""
                SELECT decision, COUNT(*) as cnt, SUM(amount) as total_amount
                FROM audit_logs {where}
                GROUP BY decision
                """,
                *params,
            )

            top_reasons = await conn.fetch(
                f"""
                SELECT reason_code, COUNT(*) as cnt
                FROM audit_logs {where} AND decision != 'APPROVED'
                GROUP BY reason_code
                ORDER BY cnt DESC
                LIMIT 10
                """,
                *params,
            )

            by_agent = await conn.fetch(
                f"""
                SELECT agent_id, decision, COUNT(*) as cnt, SUM(amount) as total_amount
                FROM audit_logs {where}
                GROUP BY agent_id, decision
                ORDER BY agent_id
                """,
                *params,
            )

            total_rows = await conn.fetchval(
                f"SELECT COUNT(*) FROM audit_logs {where}",
                *params,
            )

        decisions = {
            row["decision"]: {"count": row["cnt"], "total_amount": row["total_amount"] or 0}
            for row in summary
        }

        agent_breakdown: dict[str, dict[str, Any]] = {}
        for row in by_agent:
            aid = row["agent_id"]
            if aid not in agent_breakdown:
                agent_breakdown[aid] = {}
            agent_breakdown[aid][row["decision"]] = {
                "count": row["cnt"],
                "total_amount": row["total_amount"] or 0,
            }

        return {
            "period_days": period_days,
            "total_decisions": total_rows or 0,
            "decisions": decisions,
            "top_rejection_reasons": [
                {"reason": r["reason_code"], "count": r["cnt"]} for r in top_reasons
            ],
            "agent_breakdown": agent_breakdown,
        }

    async def get_audit_logs(
        self,
        agent_id: str | None = None,
        payout_id: str | None = None,
        limit: int = 50,
    ) -> list[AuditLogEntry]:
        """Retrieve audit log entries with optional filters."""
        conditions: list[str] = []
        params: list[str | int] = []
        param_idx = 1

        if agent_id:
            conditions.append(f"agent_id = ${param_idx}")
            params.append(agent_id)
            param_idx += 1

        if payout_id:
            conditions.append(f"payout_id = ${param_idx}")
            params.append(payout_id)
            param_idx += 1

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        params.append(limit)
        query = f"""
            SELECT * FROM audit_logs
            {where_clause}
            ORDER BY created_at DESC
            LIMIT ${param_idx}
        """

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *params)

        return [
            AuditLogEntry(
                payout_id=row["payout_id"],
                agent_id=row["agent_id"],
                amount=row["amount"],
                currency=row["currency"],
                vendor_name=row["vendor_name"],
                vendor_url=row["vendor_url"],
                decision=Decision(row["decision"]),
                reason_code=ReasonCode(row["reason_code"]),
                reason_detail=row["reason_detail"] or "",
                threat_types=list(row["threat_types"] or []),
                processing_ms=row["processing_ms"],
                created_at=row["created_at"],
            )
            for row in rows
        ]

    # ================================================================
    # Payout Workflows (Phase 3 persistence)
    # ================================================================

    async def save_workflow(
        self,
        payout_id: str,
        agent_id: str,
        amount_paise: int,
        current_state: str,
        history: list[dict[str, Any]],
    ) -> None:
        """Upsert payout workflow state."""
        import json

        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO payout_workflows
                    (payout_id, agent_id, amount_paise, current_state, history, updated_at)
                VALUES ($1, $2, $3, $4, $5::jsonb, NOW())
                ON CONFLICT (payout_id) DO UPDATE SET
                    current_state = EXCLUDED.current_state,
                    history = EXCLUDED.history,
                    updated_at = NOW()
                """,
                payout_id,
                agent_id,
                amount_paise,
                current_state,
                json.dumps(history),
            )

    async def get_workflow(self, payout_id: str) -> dict[str, Any] | None:
        """Load workflow by payout ID."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM payout_workflows WHERE payout_id = $1",
                payout_id,
            )
        if not row:
            return None
        return {
            "payout_id": row["payout_id"],
            "agent_id": row["agent_id"],
            "amount_paise": row["amount_paise"],
            "current_state": row["current_state"],
            "history": row["history"] or [],
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
        }

    async def list_workflows(self, state: str | None = None) -> list[dict[str, Any]]:
        """List all persisted workflows."""
        async with self.pool.acquire() as conn:
            if state:
                rows = await conn.fetch(
                    "SELECT * FROM payout_workflows "
                    "WHERE current_state = $1 ORDER BY updated_at DESC",
                    state,
                )
            else:
                rows = await conn.fetch(
                    "SELECT * FROM payout_workflows ORDER BY updated_at DESC LIMIT 100"
                )
        return [
            {
                "payout_id": row["payout_id"],
                "agent_id": row["agent_id"],
                "amount_paise": row["amount_paise"],
                "current_state": row["current_state"],
                "history": row["history"] or [],
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            }
            for row in rows
        ]

    # ================================================================
    # Ledger Entries (Phase 3 persistence)
    # ================================================================

    async def write_ledger_entries(
        self,
        reference: str,
        description: str,
        entries: list[dict[str, Any]],
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Persist balanced ledger journal lines."""
        import json
        from datetime import date

        async with self.pool.acquire() as conn:
            entry_date = date.today()
            for line in entries:
                await conn.execute(
                    """
                    INSERT INTO ledger_entries
                        (reference, description, account_code, account_name,
                         debit_paise, credit_paise, entry_date, metadata)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8::jsonb)
                    """,
                    reference,
                    description,
                    line.get("account_code", ""),
                    line.get("account_name", ""),
                    line.get("debit_paise", 0),
                    line.get("credit_paise", 0),
                    entry_date,
                    json.dumps(metadata or {}),
                )

    async def get_ledger_trial_balance(self) -> list[dict[str, Any]]:
        """Aggregate ledger entries into trial balance."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT account_code, account_name,
                       SUM(debit_paise) as total_debit,
                       SUM(credit_paise) as total_credit
                FROM ledger_entries
                GROUP BY account_code, account_name
                ORDER BY account_code
                """
            )
        return [
            {
                "account_code": row["account_code"],
                "account_name": row["account_name"],
                "debit_paise": row["total_debit"] or 0,
                "credit_paise": row["total_credit"] or 0,
                "balance_paise": (row["total_debit"] or 0) - (row["total_credit"] or 0),
            }
            for row in rows
        ]

    async def get_dashboard_agents_with_spend(
        self,
        redis_get_spend: Any,
    ) -> list[dict[str, Any]]:
        """Build agent list with budget utilisation for dashboard API."""
        agents = await self.list_all_agents()
        result = []
        for agent in agents:
            agent_id = agent["agent_id"]
            daily_limit = agent["daily_limit"]
            spent = 0
            if redis_get_spend:
                spent = await redis_get_spend(agent_id)
            util = round((spent / daily_limit) * 100, 1) if daily_limit else 0
            if util >= 85:
                health = "red"
            elif util >= 60:
                health = "yellow"
            else:
                health = "green"
            result.append(
                {
                    **agent,
                    "current_daily_spend_paise": spent,
                    "utilisation_pct": util,
                    "budget_health": health,
                }
            )
        return result
