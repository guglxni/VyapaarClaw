"""Audit logger — writes every governance decision to PostgreSQL.

If PostgreSQL is unreachable, falls back to local filesystem
(fail-safe per SPEC §14.1). Optionally syncs to DenchClaw CRM.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

import asyncpg

from vyapaar_mcp.db.postgres import PostgresClient
from vyapaar_mcp.models import GovernanceResult

if TYPE_CHECKING:
    from vyapaar_mcp.integrations.denchclaw import DenchClawClient

logger = logging.getLogger(__name__)

FALLBACK_DIR = Path(os.environ.get("VYAPAAR_AUDIT_FALLBACK_DIR", "./audit_logs"))

_dench_client: DenchClawClient | None = None


def set_denchclaw_client(client: DenchClawClient | None) -> None:
    """Attach DenchClaw client for CRM sync (set during server startup)."""
    global _dench_client
    _dench_client = client


async def log_decision(
    postgres: PostgresClient,
    result: GovernanceResult,
    vendor_name: str | None = None,
    vendor_url: str | None = None,
) -> None:
    """Log a governance decision to PostgreSQL with filesystem fallback."""
    try:
        await postgres.write_audit_log(
            result,
            vendor_name=vendor_name,
            vendor_url=vendor_url,
        )
    except (asyncpg.PostgresError, RuntimeError, ConnectionError, TimeoutError, OSError) as e:
        logger.error("PostgreSQL audit write failed: %s — falling back to filesystem", e)
        _write_fallback(result, vendor_name, vendor_url)

    await _sync_to_denchclaw(result, vendor_name, vendor_url)


async def _sync_to_denchclaw(
    result: GovernanceResult,
    vendor_name: str | None,
    vendor_url: str | None,
) -> None:
    """Best-effort sync to DenchClaw CRM object tables."""
    if _dench_client is None or not _dench_client.configured:
        return
    try:
        sync_result = await _dench_client.sync_audit_entry(
            {
                "payout_id": result.payout_id,
                "agent_id": result.agent_id,
                "amount": result.amount,
                "decision": result.decision.value,
                "reason_code": result.reason_code.value,
                "reason_detail": result.reason_detail,
                "vendor_name": vendor_name,
                "vendor_url": vendor_url,
                "processing_ms": result.processing_ms,
            }
        )
        if sync_result.get("synced"):
            logger.debug(
                "DenchClaw audit sync OK: payout=%s entry=%s",
                result.payout_id,
                sync_result.get("entry_id"),
            )
    except Exception as exc:
        logger.warning("DenchClaw audit sync failed (non-blocking): %s", exc)


def _write_fallback(
    result: GovernanceResult,
    vendor_name: str | None = None,
    vendor_url: str | None = None,
) -> None:
    """Emergency fallback: write audit to local JSON file."""
    FALLBACK_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(tz=UTC).strftime("%Y%m%dT%H%M%S")
    import re

    safe_id = re.sub(r"[^a-zA-Z0-9_-]", "_", result.payout_id)[:64]
    filename = FALLBACK_DIR / f"{safe_id}_{timestamp}.json"

    entry = {
        "payout_id": result.payout_id,
        "agent_id": result.agent_id,
        "amount": result.amount,
        "decision": result.decision.value,
        "reason_code": result.reason_code.value,
        "reason_detail": result.reason_detail,
        "threat_types": result.threat_types,
        "processing_ms": result.processing_ms,
        "vendor_name": vendor_name,
        "vendor_url": vendor_url,
        "timestamp": timestamp,
    }

    filename.write_text(json.dumps(entry, indent=2))
    logger.warning("Audit fallback written to: %s", filename)
