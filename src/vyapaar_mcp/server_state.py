"""Mutable server state for the VyapaarClaw MCP entrypoint."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from vyapaar_mcp.config import VyapaarConfig
    from vyapaar_mcp.db.postgres import PostgresClient
    from vyapaar_mcp.db.redis_client import RedisClient
    from vyapaar_mcp.egress.ntfy_notifier import NtfyNotifier
    from vyapaar_mcp.egress.razorpay_actions import RazorpayActions
    from vyapaar_mcp.egress.slack_notifier import SlackNotifier
    from vyapaar_mcp.egress.telegram_notifier import TelegramNotifier
    from vyapaar_mcp.governance.engine import GovernanceEngine
    from vyapaar_mcp.ingress.polling import PayoutPoller
    from vyapaar_mcp.ingress.razorpay_bridge import RazorpayBridge
    from vyapaar_mcp.llm import LLMClient
    from vyapaar_mcp.llm.security_validator import ToolCallValidator
    from vyapaar_mcp.reputation.anomaly import TransactionAnomalyScorer
    from vyapaar_mcp.reputation.gleif import GLEIFChecker
    from vyapaar_mcp.reputation.safe_browsing import SafeBrowsingChecker
    from vyapaar_mcp.resilience import CircuitBreaker


@dataclass
class ServerState:
    """Container for services initialized during FastMCP lifespan."""

    config: VyapaarConfig | None = None
    redis: RedisClient | None = None
    postgres: PostgresClient | None = None
    safe_browsing: SafeBrowsingChecker | None = None
    razorpay: RazorpayActions | None = None
    razorpay_bridge: RazorpayBridge | None = None
    slack: SlackNotifier | None = None
    poller: PayoutPoller | None = None
    governance: GovernanceEngine | None = None
    poll_task: asyncio.Task[None] | None = None
    start_time: float = field(default_factory=time.time)
    cb_razorpay: CircuitBreaker | None = None
    cb_safe_browsing: CircuitBreaker | None = None
    cb_gleif: CircuitBreaker | None = None
    gleif: GLEIFChecker | None = None
    anomaly_scorer: TransactionAnomalyScorer | None = None
    ntfy: NtfyNotifier | None = None
    telegram: TelegramNotifier | None = None
    llm_client: LLMClient | None = None
    tool_validator: ToolCallValidator | None = None


state = ServerState()
