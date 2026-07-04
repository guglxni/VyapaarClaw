"""VyapaarClaw MCP Server — FastMCP entrypoint with SSE transport.

Registers all 37 governance + CFO intelligence tools and manages the
lifecycle of Redis, PostgreSQL, and external API clients.

Part of the VyapaarClaw OpenClaw Framework for AI Financial Governance.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from mcp.server.fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Mount, Route
from transitions.core import MachineError

from vyapaar_mcp.audit.logger import log_decision, set_denchclaw_client
from vyapaar_mcp.cfo.gst_providers import build_gst_chain
from vyapaar_mcp.config import load_config
from vyapaar_mcp.db.postgres import PostgresClient
from vyapaar_mcp.db.redis_client import RedisClient
from vyapaar_mcp.egress.ntfy_notifier import NtfyNotifier, notify_with_fallback
from vyapaar_mcp.egress.razorpay_actions import RazorpayActions
from vyapaar_mcp.egress.slack_notifier import SlackNotifier
from vyapaar_mcp.egress.telegram_notifier import TelegramNotifier
from vyapaar_mcp.governance.engine import GovernanceEngine
from vyapaar_mcp.governance.options import GovernanceOptions
from vyapaar_mcp.handlers.http import (
    make_agents_endpoint,
    make_audit_endpoint,
    make_dashboard_endpoint,
    make_health_endpoint,
    make_slack_actions_endpoint,
    make_telegram_callback_endpoint,
)
from vyapaar_mcp.ingress.polling import PayoutPoller
from vyapaar_mcp.ingress.razorpay_bridge import RazorpayBridge
from vyapaar_mcp.ingress.webhook import (
    extract_webhook_id,
    parse_webhook_event,
    verify_razorpay_signature,
)
from vyapaar_mcp.integrations.denchclaw import DenchClawClient
from vyapaar_mcp.lifecycle import make_lifespan
from vyapaar_mcp.llm import LLMClient
from vyapaar_mcp.llm.security_validator import ToolCallValidator
from vyapaar_mcp.models import (
    AgentPolicy,
    BudgetStatus,
    Decision,
    HealthStatus,
    ReasonCode,
)
from vyapaar_mcp.observability import metrics
from vyapaar_mcp.reputation.anomaly import TransactionAnomalyScorer
from vyapaar_mcp.reputation.gleif import GLEIFChecker
from vyapaar_mcp.reputation.safe_browsing import SafeBrowsingChecker
from vyapaar_mcp.research.exa_client import ExaClient
from vyapaar_mcp.resilience import CircuitBreaker
from vyapaar_mcp.server_state import state
from vyapaar_mcp.server_support import (
    AUDIT_READ_ERRORS,
    NOTIFICATION_UPDATE_ERRORS,
    RAZORPAY_ACTION_ERRORS,
    SERVICE_CONNECT_ERRORS,
    require_services,
)

# ================================================================
# Logging Setup
# ================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("vyapaar_mcp")


def _require(**services: Any) -> None:
    """Validate that required server components are initialized.

    Raises RuntimeError instead of using assert (which is stripped
    with ``python -O``).
    """
    require_services(**services)


# ================================================================
# FastMCP Server
# ================================================================


_lifespan = make_lifespan(lambda: _startup(), lambda: _shutdown())


mcp = FastMCP(
    "vyapaarclaw",
    instructions=(
        "Agentic Financial Governance Server — "
        "The CFO for the Agentic Economy. "
        "Enforces spending policies, checks vendor reputation, "
        "and audits every AI agent transaction via Razorpay X."
    ),
    lifespan=_lifespan,
    sse_path="/sse",
    message_path="/messages/",
)


health_endpoint = mcp.custom_route("/health", methods=["GET"])(  # type: ignore[misc]
    make_health_endpoint(
        get_redis=lambda: state.redis,
        get_postgres=lambda: state.postgres,
        get_start_time=lambda: state.start_time,
    )
)


# ================================================================
# Lifecycle
# ================================================================


async def _startup() -> None:
    """Initialize all services on server start."""
    state.start_time = time.time()
    state.config = load_config()

    logger.info("=" * 60)
    logger.info("  VyapaarClaw — Starting up...")
    logger.info("=" * 60)

    # Redis
    state.redis = RedisClient(url=state.config.redis_url)
    try:
        await state.redis.connect()
        logger.info("✅ Redis connected")
    except SERVICE_CONNECT_ERRORS as e:
        logger.error("❌ Redis connection failed: %s", e)

    # PostgreSQL
    state.postgres = PostgresClient(dsn=state.config.postgres_dsn)
    try:
        await state.postgres.connect()
        await state.postgres.run_migrations()
        logger.info("✅ PostgreSQL connected + migrations complete")
    except SERVICE_CONNECT_ERRORS as e:
        logger.error("❌ PostgreSQL connection failed: %s", e)

    # Google Safe Browsing
    state.cb_safe_browsing = CircuitBreaker(
        "safe-browsing",
        failure_threshold=state.config.circuit_breaker_failure_threshold,
        recovery_timeout=float(state.config.circuit_breaker_recovery_timeout),
    )
    state.safe_browsing = SafeBrowsingChecker(
        api_key=state.config.google_safe_browsing_key,
        api_url=state.config.safe_browsing_api_url,
        redis=state.redis,
        circuit_breaker=state.cb_safe_browsing,
    )
    logger.info("✅ Safe Browsing checker initialized (circuit breaker enabled)")

    # Razorpay Actions (egress — approve/reject)
    state.cb_razorpay = CircuitBreaker(
        "razorpay",
        failure_threshold=state.config.circuit_breaker_failure_threshold,
        recovery_timeout=float(state.config.circuit_breaker_recovery_timeout),
    )
    state.razorpay = RazorpayActions(
        key_id=state.config.razorpay_key_id,
        key_secret=state.config.razorpay_key_secret,
        circuit_breaker=state.cb_razorpay,
    )
    logger.info("✅ Razorpay egress client initialized (circuit breaker enabled)")

    # Razorpay Bridge (ingress — API calls, same as official MCP server)
    state.razorpay_bridge = RazorpayBridge(
        key_id=state.config.razorpay_key_id,
        key_secret=state.config.razorpay_key_secret,
    )
    logger.info("✅ RazorpayBridge initialized (mirrors razorpay/razorpay-mcp-server tools)")

    # Slack Notifier (human-in-the-loop)
    if state.config.slack_bot_token and state.config.slack_channel_id:
        state.slack = SlackNotifier(
            bot_token=state.config.slack_bot_token,
            channel_id=state.config.slack_channel_id,
        )
        logger.info("✅ Slack notifier initialized (channel=%s)", state.config.slack_channel_id)
    else:
        logger.warning(
            "⚠️  Slack not configured — HELD payouts will not trigger approval requests. "
            "Set VYAPAAR_SLACK_BOT_TOKEN and VYAPAAR_SLACK_CHANNEL_ID in .env"
        )

    # Telegram Notifier (human-in-the-loop, alternative to Slack)
    if state.config.telegram_bot_token and state.config.telegram_chat_id:
        state.telegram = TelegramNotifier(
            bot_token=state.config.telegram_bot_token,
            chat_id=state.config.telegram_chat_id,
        )
        logger.info("✅ Telegram notifier initialized (chat_id=%s)", state.config.telegram_chat_id)
    else:
        logger.info(
            "Telegram not configured — "
            "set VYAPAAR_TELEGRAM_BOT_TOKEN and VYAPAAR_TELEGRAM_CHAT_ID to enable"
        )

    # Payout Poller (replaces webhooks)
    if state.config.razorpay_account_number:
        state.poller = PayoutPoller(
            bridge=state.razorpay_bridge,
            account_number=state.config.razorpay_account_number,
            redis=state.redis,
            poll_interval=state.config.poll_interval,
        )
        logger.info(
            "✅ PayoutPoller ready (interval=%ds, replaces webhook ingress)",
            state.config.poll_interval,
        )
    else:
        logger.warning(
            "⚠️  VYAPAAR_RAZORPAY_ACCOUNT_NUMBER not set — "
            "automatic polling disabled. "
            "Use poll_razorpay_payouts tool manually."
        )

    # GLEIF Vendor Verification (FOSS)
    state.cb_gleif = CircuitBreaker(
        "gleif",
        failure_threshold=state.config.circuit_breaker_failure_threshold,
        recovery_timeout=float(state.config.circuit_breaker_recovery_timeout),
    )
    state.gleif = GLEIFChecker(
        api_url=state.config.gleif_api_url,
        redis=state.redis,
        circuit_breaker=state.cb_gleif,
    )
    logger.info("✅ GLEIF vendor verification initialized (circuit breaker enabled)")

    # Transaction Anomaly Scorer (FOSS — scikit-learn IsolationForest)
    state.anomaly_scorer = TransactionAnomalyScorer(
        redis=state.redis,
        risk_threshold=state.config.anomaly_risk_threshold,
    )
    logger.info(
        "✅ Transaction anomaly scorer initialized (threshold=%.2f)",
        state.config.anomaly_risk_threshold,
    )

    # Governance Engine (after anomaly scorer — wired into 6-layer pipeline)
    gov_options = GovernanceOptions.from_config(state.config)
    state.governance = GovernanceEngine(
        redis=state.redis,
        postgres=state.postgres,
        safe_browsing=state.safe_browsing,
        rate_limit_max=state.config.rate_limit_max_requests,
        rate_limit_window=state.config.rate_limit_window_seconds,
        options=gov_options,
        anomaly_scorer=state.anomaly_scorer,
    )
    logger.info(
        "✅ Governance engine ready (rate limit: %d req / %ds, "
        "gstin=%s ifsc=%s sanctions=%s anomaly=%s)",
        state.config.rate_limit_max_requests,
        state.config.rate_limit_window_seconds,
        gov_options.check_gstin_format,
        gov_options.check_ifsc_format,
        gov_options.check_sanctions,
        gov_options.check_anomaly,
    )

    # ntfy Notifier (FOSS — Slack fallback)
    if state.config.ntfy_topic:
        state.ntfy = NtfyNotifier(
            topic=state.config.ntfy_topic,
            server_url=state.config.ntfy_url,
            auth_token=state.config.ntfy_auth_token or None,
        )
        logger.info(
            "✅ ntfy notifier initialized (topic=%s, server=%s)",
            state.config.ntfy_topic,
            state.config.ntfy_url,
        )
    else:
        logger.info("ℹ️  ntfy not configured — set VYAPAAR_NTFY_TOPIC to enable push fallback")

    # Exa research client (Phase 2)
    state.exa_client = ExaClient(api_key=state.config.exa_api_key)
    if state.exa_client.configured:
        logger.info("✅ Exa research client initialized")
    else:
        logger.info("ℹ️  Exa not configured — set VYAPAAR_EXA_API_KEY for vendor research")

    # GST verification chain (Phase 2)
    state.gst_chain = build_gst_chain(
        browserwire_url=state.config.browserwire_url,
        browserwire_key=state.config.browserwire_api_key,
        gsp_url=state.config.gsp_api_url,
        gsp_key=state.config.gsp_api_key,
        enable_live=bool(state.config.browserwire_url or state.config.gsp_api_key),
    )
    logger.info(
        "✅ GST verification chain ready (browserwire=%s, gsp=%s, live_gov=%s)",
        bool(state.config.browserwire_url),
        bool(state.config.gsp_api_key),
        state.config.governance_live_gst,
    )

    # Workflow Postgres persistence (Phase 3)
    from vyapaar_mcp.cfo.workflow import set_workflow_store

    if state.postgres:
        set_workflow_store(state.postgres)
        logger.info("✅ Workflow persistence enabled (PostgreSQL)")

    # DenchClaw CRM integration
    state.denchclaw = DenchClawClient(
        base_url=state.config.denchclaw_url,
        enabled=state.config.denchclaw_enabled,
    )
    set_denchclaw_client(state.denchclaw if state.config.denchclaw_sync_auto else None)
    if state.config.denchclaw_enabled:
        if await state.denchclaw.is_available():
            logger.info("✅ DenchClaw CRM connected at %s", state.config.denchclaw_url)
            try:
                await state.denchclaw.ensure_schema()
                logger.info("✅ DenchClaw vyapaar_audit + vyapaar_vendor objects ready")
            except Exception as exc:
                logger.warning("DenchClaw schema bootstrap skipped: %s", exc)
        else:
            logger.info(
                "ℹ️  DenchClaw not running at %s — install: npx denchclaw@latest",
                state.config.denchclaw_url,
            )

    # Primary LLM Client (LiteLLM — any provider)
    state.llm_client = LLMClient(state.config)
    try:
        await state.llm_client.initialize()
        if state.llm_client.is_configured:
            logger.info(
                "✅ LLM client initialized (model=%s, guardrails=%s)",
                state.config.llm_model,
                state.config.azure_guardrails_enabled,
            )
        else:
            logger.info("ℹ️  LLM not configured — set VYAPAAR_LLM_MODEL and VYAPAAR_LLM_API_KEY")
    except (RuntimeError, ValueError, TypeError) as exc:
        logger.warning("⚠️  LLM initialization skipped: %s", exc)

    # Security LLM / Dual LLM Quarantine Pattern
    state.tool_validator = ToolCallValidator(state.config)
    try:
        await state.tool_validator.initialize()
        if state.tool_validator.is_configured:
            logger.info(
                "✅ Dual LLM quarantine initialized (security_llm=%s, strict=%s)",
                state.config.security_llm_model,
                state.config.quarantine_strict,
            )
            logger.info("   Taint sources: %s", state.config.taint_sources.replace(",", ", "))
            logger.info("   Dual-LLM tools: %s", state.config.dual_llm_tools.replace(",", ", "))
        else:
            logger.info(
                "ℹ️  Dual LLM quarantine not configured — set VYAPAAR_SECURITY_LLM_MODEL to enable"
            )
    except (RuntimeError, ValueError, TypeError) as exc:
        logger.warning("⚠️  Dual LLM quarantine initialization skipped: %s", exc)

    # Auto-polling (background task)
    if (
        state.config.auto_poll
        and state.poller
        and state.governance
        and state.razorpay
        and state.postgres
    ):

        async def _auto_poll_callback(payout: Any, agent_id: str, vendor_url: str | None) -> None:
            """Process a polled payout through governance."""
            _require(governance=state.governance, razorpay=state.razorpay, postgres=state.postgres)

            result = await state.governance.evaluate(payout, agent_id, vendor_url)
            metrics.record_decision(result)

            vendor_name: str | None = None
            if (
                hasattr(payout, "fund_account")
                and payout.fund_account
                and payout.fund_account.contact
            ):
                vendor_name = payout.fund_account.contact.name

            await log_decision(
                state.postgres,
                result,
                vendor_name=vendor_name,
                vendor_url=vendor_url,
            )

            try:
                if result.decision == Decision.APPROVED:
                    await state.razorpay.approve_payout(payout.id)
                elif result.decision == Decision.REJECTED:
                    await state.razorpay.reject_payout(
                        payout.id,
                        f"{result.reason_code.value}: {result.reason_detail}",
                    )
            except RAZORPAY_ACTION_ERRORS as e:
                logger.error("Auto-poll action failed for %s: %s", payout.id, e)
                if result.decision == Decision.APPROVED and state.redis:
                    await state.redis.rollback_budget(result.agent_id, result.amount)
                    logger.warning(
                        "Budget rolled back for %s: %d paise", result.agent_id, result.amount
                    )

            await notify_with_fallback(
                state.slack,
                state.ntfy,
                result,
                vendor_name=vendor_name,
                vendor_url=vendor_url,
                telegram_notifier=state.telegram,
            )

        state.poll_task = asyncio.create_task(
            state.poller.run_continuous(on_payout=_auto_poll_callback)
        )
        logger.info(
            "🔄 Auto-polling ENABLED (interval=%ds)",
            state.config.poll_interval,
        )

    logger.info("=" * 60)
    logger.info("  VyapaarClaw — Ready to govern! 🛡️")
    logger.info("  Mode: API Polling (no webhook/tunnel needed)")
    logger.info("  Sidecar: razorpay/mcp (all toolsets enabled)")
    logger.info("=" * 60)


async def _shutdown() -> None:
    """Cleanup on server shutdown."""
    logger.info("VyapaarClaw shutting down...")
    if state.poll_task and not state.poll_task.done():
        state.poll_task.cancel()
    if state.poller:
        state.poller.stop()
    if state.slack:
        await state.slack.close()
    if state.telegram:
        await state.telegram.close()
    if state.ntfy:
        await state.ntfy.close()
    if state.gleif:
        await state.gleif.close()
    if state.safe_browsing:
        await state.safe_browsing.close()
    if state.llm_client:
        await state.llm_client.close()
    if state.tool_validator:
        await state.tool_validator.close()
    if state.redis:
        await state.redis.disconnect()
    if state.postgres:
        await state.postgres.disconnect()
    logger.info("VyapaarClaw shutdown complete")


# ================================================================
# MCP Tools
# ================================================================


@mcp.tool()
async def handle_razorpay_webhook(
    payload: str,
    signature: str,
) -> dict[str, Any]:
    """Receive and process a Razorpay X webhook event (payout.queued).

    This is the main ingress point. It verifies the webhook signature,
    checks idempotency, runs the governance pipeline, and either
    approves or rejects the payout on Razorpay.

    Args:
        payload: Raw JSON body of the Razorpay webhook.
        signature: Value of the X-Razorpay-Signature header.

    Returns:
        Decision result with payout_id, decision, and reason.
    """
    _require(
        config=state.config,
        redis=state.redis,
        postgres=state.postgres,
        governance=state.governance,
        razorpay=state.razorpay,
    )

    if not payload or len(payload) > 1_048_576:
        return {
            "decision": Decision.REJECTED.value,
            "reason": "INVALID_PAYLOAD",
            "detail": "Payload empty or exceeds 1 MB size limit",
        }

    payload_bytes = payload.encode("utf-8")

    # --- Step 1: Verify Signature ---
    if not verify_razorpay_signature(
        payload_bytes,
        signature,
        state.config.razorpay_webhook_secret,
    ):
        logger.warning("REJECTED: Invalid webhook signature")
        return {
            "decision": Decision.REJECTED.value,
            "reason": ReasonCode.INVALID_SIGNATURE.value,
            "detail": "Webhook signature verification failed (401)",
        }

    # --- Step 2: Parse Event ---
    try:
        event = parse_webhook_event(payload_bytes)
    except ValueError as e:
        logger.warning("Webhook parse error: %s", e)
        return {
            "decision": Decision.REJECTED.value,
            "reason": "PARSE_ERROR",
            "detail": "Invalid webhook payload format",
        }

    # --- Step 3: Only handle payout.queued ---
    if event.event != "payout.queued":
        return {
            "decision": "SKIPPED",
            "reason": "UNSUPPORTED_EVENT",
            "detail": f"Event '{event.event}' is not handled. Only 'payout.queued' is supported.",
        }

    # --- Step 4: Idempotency Check ---
    webhook_id = extract_webhook_id(event)
    is_new = await state.redis.check_idempotency(webhook_id)
    if not is_new:
        logger.info("Idempotent skip: webhook %s already processed", webhook_id)
        return {
            "decision": "SKIPPED",
            "reason": ReasonCode.IDEMPOTENT_SKIP.value,
            "detail": f"Webhook '{webhook_id}' already processed",
        }

    # --- Step 5: Extract context ---
    payout = event.payload.payout.entity
    notes = payout.get_notes()
    agent_id = notes.agent_id
    vendor_url = notes.vendor_url or None
    vendor_name: str | None = None

    # Try to get vendor name from fund account contact
    if payout.fund_account and payout.fund_account.contact:
        vendor_name = payout.fund_account.contact.name

    # --- Step 6: Run Governance ---
    result = await state.governance.evaluate(payout, agent_id, vendor_url)
    metrics.record_decision(result)

    # --- Step 7: Write Audit Log ---
    await log_decision(state.postgres, result, vendor_name=vendor_name, vendor_url=vendor_url)

    # --- Step 8: Execute Decision on Razorpay ---
    try:
        if result.decision == Decision.APPROVED:
            await state.razorpay.approve_payout(payout.id)
        elif result.decision == Decision.REJECTED:
            await state.razorpay.reject_payout(
                payout.id,
                f"{result.reason_code.value}: {result.reason_detail}",
            )
        # HELD payouts are not auto-actioned (waiting for human approval)
    except RAZORPAY_ACTION_ERRORS as e:
        logger.error("Razorpay action failed for %s: %s", payout.id, e)
        if result.decision == Decision.APPROVED:
            await state.redis.rollback_budget(result.agent_id, result.amount)
            logger.warning("Budget rolled back for %s: %d paise", result.agent_id, result.amount)

    # --- Step 9: Notification (Slack / Telegram / ntfy) ---
    await notify_with_fallback(
        state.slack,
        state.ntfy,
        result,
        vendor_name=vendor_name,
        vendor_url=vendor_url,
        telegram_notifier=state.telegram,
    )

    return {
        "payout_id": result.payout_id,
        "decision": result.decision.value,
        "reason": result.reason_code.value,
        "detail": result.reason_detail,
        "amount_paise": result.amount,
        "agent_id": result.agent_id,
        "processing_ms": result.processing_ms,
    }


@mcp.tool()
async def poll_razorpay_payouts(
    account_number: str = "",
) -> dict[str, Any]:
    """Poll Razorpay API for queued payouts and run governance.

    This replaces webhook-based ingress entirely. No tunnel, no
    ngrok, no public endpoint needed.

    Uses the same API as the official razorpay/razorpay-mcp-server's
    fetch_all_payouts tool, combined with Vyapaar's governance engine.

    Args:
        account_number: RazorpayX account number. If empty, uses
                       the configured VYAPAAR_RAZORPAY_ACCOUNT_NUMBER.

    Returns:
        Summary of payouts found and governance decisions made.
    """
    _require(
        config=state.config,
        redis=state.redis,
        razorpay_bridge=state.razorpay_bridge,
        governance=state.governance,
        razorpay=state.razorpay,
        postgres=state.postgres,
    )

    acct = account_number or state.config.razorpay_account_number
    if not acct:
        return {
            "error": (
                "No account number provided. Set "
                "VYAPAAR_RAZORPAY_ACCOUNT_NUMBER in .env "
                "or pass account_number parameter."
            ),
        }

    # Create a one-shot poller
    poller = PayoutPoller(
        bridge=state.razorpay_bridge,
        account_number=acct,
        redis=state.redis,
        poll_interval=state.config.poll_interval,
    )

    # Poll once
    new_payouts = await poller.poll_once()

    if not new_payouts:
        return {
            "status": "ok",
            "message": "No new queued payouts found",
            "payouts_found": 0,
            "poller_stats": poller.stats,
        }

    # Process each payout through governance
    results: list[dict[str, Any]] = []
    for payout, agent_id, vendor_url in new_payouts:
        # Run governance
        result = await state.governance.evaluate(payout, agent_id, vendor_url)
        metrics.record_decision(result)

        # Audit log
        vendor_name: str | None = None
        if payout.fund_account and payout.fund_account.contact:
            vendor_name = payout.fund_account.contact.name

        await log_decision(
            state.postgres,
            result,
            vendor_name=vendor_name,
            vendor_url=vendor_url,
        )

        # Execute decision on Razorpay
        try:
            if result.decision == Decision.APPROVED:
                await state.razorpay.approve_payout(payout.id)
            elif result.decision == Decision.REJECTED:
                await state.razorpay.reject_payout(
                    payout.id,
                    f"{result.reason_code.value}: {result.reason_detail}",
                )
        except RAZORPAY_ACTION_ERRORS as e:
            logger.error(
                "Razorpay action failed for %s: %s",
                payout.id,
                e,
            )
            if result.decision == Decision.APPROVED:
                await state.redis.rollback_budget(result.agent_id, result.amount)
                logger.warning(
                    "Budget rolled back for %s: %d paise", result.agent_id, result.amount
                )

        # Notification (Slack / Telegram / ntfy)
        await notify_with_fallback(
            state.slack,
            state.ntfy,
            result,
            vendor_name=vendor_name,
            vendor_url=vendor_url,
            telegram_notifier=state.telegram,
        )

        results.append(
            {
                "payout_id": result.payout_id,
                "decision": result.decision.value,
                "reason": result.reason_code.value,
                "detail": result.reason_detail,
                "amount_paise": result.amount,
                "agent_id": result.agent_id,
            }
        )

    return {
        "status": "ok",
        "payouts_found": len(new_payouts),
        "decisions": results,
        "poller_stats": poller.stats,
    }


@mcp.tool()
async def check_vendor_reputation(url: str) -> dict[str, Any]:
    """Check a URL against Google Safe Browsing v4 threat lists.

    Returns whether the URL is safe and any detected threats.

    Args:
        url: The vendor URL or domain to check.

    Returns:
        Safety result with threat details.
    """
    _require(safe_browsing=state.safe_browsing)

    result = await state.safe_browsing.check_url(url)
    return {
        "url": url,
        "safe": result.is_safe,
        "threats": result.threat_types,
        "match_count": len(result.matches),
    }


@mcp.tool()
async def get_agent_budget(agent_id: str) -> dict[str, Any]:
    """Get current daily spend and remaining budget for an agent.

    Args:
        agent_id: The unique identifier of the AI agent.

    Returns:
        Budget status with daily limit, spent today, and remaining.
    """
    _require(redis=state.redis, postgres=state.postgres)

    policy = await state.postgres.get_agent_policy(agent_id)
    if policy is None:
        return {"error": f"No policy found for agent '{agent_id}'"}

    spent_today = await state.redis.get_daily_spend(agent_id)
    remaining = max(0, policy.daily_limit - spent_today)

    status = BudgetStatus(
        agent_id=agent_id,
        daily_limit=policy.daily_limit,
        spent_today=spent_today,
        remaining=remaining,
    )
    return status.model_dump()


@mcp.tool()
async def get_audit_log(
    agent_id: str = "",
    payout_id: str = "",
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Retrieve spending audit trail with optional filtering.

    Args:
        agent_id: Filter by agent ID (optional).
        payout_id: Filter by payout ID (optional).
        limit: Maximum number of entries to return (default 50).

    Returns:
        List of audit log entries.
    """
    _require(postgres=state.postgres)

    # Clamp limit to prevent excessive queries
    limit = max(1, min(limit, 500))

    entries = await state.postgres.get_audit_logs(
        agent_id=agent_id or None,
        payout_id=payout_id or None,
        limit=limit,
    )
    return [entry.model_dump(mode="json") for entry in entries]


@mcp.tool()
async def set_agent_policy(
    agent_id: str,
    daily_limit: int = 500000,
    per_txn_limit: int | None = None,
    require_approval_above: int | None = None,
    allowed_domains: list[str] | None = None,
    blocked_domains: list[str] | None = None,
) -> dict[str, Any]:
    """Create or update spending policies for a specific agent.

    All amounts are in paise (₹500 = 50000 paise).

    Args:
        agent_id: The unique identifier of the AI agent.
        daily_limit: Maximum daily spend in paise (default ₹5,000).
        per_txn_limit: Maximum single transaction in paise (optional).
        require_approval_above: Trigger human approval above this amount (optional).
        allowed_domains: Whitelist of allowed vendor domains (optional).
        blocked_domains: Blacklist of blocked vendor domains (optional).

    Returns:
        The created/updated policy.
    """
    _require(postgres=state.postgres)

    policy = AgentPolicy(
        agent_id=agent_id,
        daily_limit=daily_limit,
        per_txn_limit=per_txn_limit,
        require_approval_above=require_approval_above,
        allowed_domains=allowed_domains or [],
        blocked_domains=blocked_domains or [],
    )

    saved = await state.postgres.upsert_agent_policy(policy)
    return {"status": "ok", "policy": saved.model_dump(mode="json")}


@mcp.tool()
async def health_check() -> dict[str, Any]:
    """Check health of all dependent services.

    Returns status of Redis, PostgreSQL, and Razorpay connectivity,
    plus server uptime and circuit breaker states.
    """
    redis_ok = await state.redis.ping() if state.redis else False
    postgres_ok = await state.postgres.ping() if state.postgres else False
    razorpay_ok = await state.razorpay.ping() if state.razorpay else False

    status = HealthStatus(
        redis="ok" if redis_ok else "error",
        postgres="ok" if postgres_ok else "error",
        razorpay="ok" if razorpay_ok else "error",
        uptime_seconds=int(time.time() - state.start_time),
    )

    result = status.model_dump()
    # Include circuit breaker snapshots
    if state.cb_razorpay is not None:
        result["circuit_breaker_razorpay"] = state.cb_razorpay.snapshot()
    if state.cb_safe_browsing is not None:
        result["circuit_breaker_safe_browsing"] = state.cb_safe_browsing.snapshot()
    if state.cb_gleif is not None:
        result["circuit_breaker_gleif"] = state.cb_gleif.snapshot()
    return result


@mcp.tool()
async def get_metrics() -> dict[str, Any]:
    """Get Prometheus-compatible governance metrics.

    Returns operational metrics including decision counts,
    budget checks, reputation checks, latency, and uptime.
    Use the 'format' field for raw Prometheus text exposition.

    Returns:
        Metrics snapshot as JSON, plus raw Prometheus text.
    """
    snapshot = metrics.snapshot()
    snapshot["prometheus_text"] = metrics.render()
    return snapshot


@mcp.tool()
async def handle_slack_action(
    action_id: str,
    payout_id: str,
    user_name: str = "unknown",
    channel: str | None = None,
    message_ts: str | None = None,
) -> dict[str, Any]:
    """Process a Slack interactive button callback (approve / reject).

    This is the human-in-the-loop handler: when a reviewer clicks
    ✅ Approve or ❌ Reject in Slack, call this tool with the payload.

    Args:
        action_id: Either "approve_payout" or "reject_payout".
        payout_id: The Razorpay payout ID (e.g. "pout_...").
        user_name: Slack username of the reviewer.
        channel: Slack channel ID (for updating the message).
        message_ts: Slack message timestamp (for updating the message).

    Returns:
        Result of the approve/reject action plus message update status.
    """
    _require(razorpay=state.razorpay)

    if action_id == "approve_payout":
        result = await state.razorpay.approve_payout(payout_id)
        action_label = "approved"
    elif action_id == "reject_payout":
        result = await state.razorpay.reject_payout(
            payout_id, reason="Rejected via Slack by human operator"
        )
        action_label = "rejected"

        # --- Budget Rollback for HELD payouts ---
        # If a payout was HELD, its budget was already deducted.
        # When rejecting it, we MUST roll back the budget in Redis.
        if state.postgres and state.redis:
            audit_logs = await state.postgres.get_audit_logs(payout_id=payout_id, limit=1)
            if audit_logs:
                log = audit_logs[0]
                if log.decision == Decision.HELD:
                    await state.redis.rollback_budget(log.agent_id, log.amount)
                    logger.info(
                        "Budget rolled back via Slack action: agent=%s amount=%d",
                        log.agent_id,
                        log.amount,
                    )
    else:
        return {"error": f"Unknown action: {action_id}"}

    logger.info(
        "Slack action: %s %s payout %s",
        user_name,
        action_label,
        payout_id,
    )

    # Update the Slack message to reflect the decision
    message_updated = False
    if state.slack and channel and message_ts:
        try:
            await state.slack.update_approval_message(
                channel=channel,
                message_ts=message_ts,
                payout_id=payout_id,
                action="approve" if action_id == "approve_payout" else "reject",
                user_name=user_name,
            )
            message_updated = True
        except NOTIFICATION_UPDATE_ERRORS as exc:
            logger.warning("Failed to update Slack message: %s", exc)

    if state.postgres:
        logger.info(
            "Audit: slack:%s %s payout %s",
            user_name,
            action_label,
            payout_id,
        )

    return {
        "status": "ok",
        "action": action_label,
        "payout_id": payout_id,
        "reviewer": user_name,
        "message_updated": message_updated,
        **result,
    }


@mcp.tool()
async def handle_telegram_action(
    action_id: str,
    payout_id: str,
    user_name: str = "unknown",
    chat_id: str | int | None = None,
    message_id: int | None = None,
    callback_query_id: str | None = None,
) -> dict[str, Any]:
    """Process a Telegram inline keyboard callback (approve / reject).

    Human-in-the-loop handler for Telegram: when a reviewer taps
    Approve or Reject on the inline keyboard, call this tool.

    Args:
        action_id: Either "approve_payout" or "reject_payout".
        payout_id: The Razorpay payout ID (e.g. "pout_...").
        user_name: Telegram username of the reviewer.
        chat_id: Telegram chat ID (for updating the message).
        message_id: Telegram message ID (for updating the message).
        callback_query_id: Telegram callback query ID (for acknowledging).

    Returns:
        Result of the approve/reject action plus message update status.
    """
    _require(razorpay=state.razorpay)

    if action_id == "approve_payout":
        result = await state.razorpay.approve_payout(payout_id)
        action_label = "approved"
    elif action_id == "reject_payout":
        result = await state.razorpay.reject_payout(
            payout_id, reason="Rejected via Telegram by human operator"
        )
        action_label = "rejected"

        if state.postgres and state.redis:
            audit_logs = await state.postgres.get_audit_logs(payout_id=payout_id, limit=1)
            if audit_logs:
                log = audit_logs[0]
                if log.decision == Decision.HELD:
                    await state.redis.rollback_budget(log.agent_id, log.amount)
                    logger.info(
                        "Budget rolled back via Telegram action: agent=%s amount=%d",
                        log.agent_id,
                        log.amount,
                    )
    else:
        return {"error": f"Unknown action: {action_id}"}

    logger.info("Telegram action: %s %s payout %s", user_name, action_label, payout_id)

    message_updated = False
    if state.telegram and chat_id and message_id:
        try:
            await state.telegram.update_message(
                chat_id=chat_id,
                message_id=message_id,
                payout_id=payout_id,
                action="approve" if action_id == "approve_payout" else "reject",
                user_name=user_name,
            )
            message_updated = True
        except NOTIFICATION_UPDATE_ERRORS as exc:
            logger.warning("Failed to update Telegram message: %s", exc)

    if state.telegram and callback_query_id:
        await state.telegram.answer_callback(
            callback_query_id,
            f"Payout {action_label} by {user_name}",
        )

    return {
        "status": "ok",
        "action": action_label,
        "payout_id": payout_id,
        "reviewer": user_name,
        "message_updated": message_updated,
        **result,
    }


slack_actions_endpoint = make_slack_actions_endpoint(
    get_config=lambda: state.config,
    get_razorpay=lambda: state.razorpay,
    require_services=_require,
    handle_slack_action=handle_slack_action,
)
telegram_callback_endpoint = make_telegram_callback_endpoint(
    get_razorpay=lambda: state.razorpay,
    require_services=_require,
    handle_telegram_action=handle_telegram_action,
)
dashboard_endpoint = make_dashboard_endpoint(
    get_postgres=lambda: state.postgres,
    get_redis=lambda: state.redis,
)
agents_endpoint = make_agents_endpoint(
    get_postgres=lambda: state.postgres,
    get_redis=lambda: state.redis,
)
audit_endpoint = make_audit_endpoint(get_postgres=lambda: state.postgres)


# ================================================================
# FOSS Integration Tools
# ================================================================


@mcp.tool()
async def verify_vendor_entity(
    vendor_name: str,
    lei: str = "",
) -> dict[str, Any]:
    """Verify a vendor's legal entity via GLEIF (Global LEI Foundation).

    Checks if the vendor is a registered legal entity with a valid LEI
    (Legal Entity Identifier). Uses the free GLEIF API — no API key needed.

    Can search by legal name or look up a specific LEI code directly.

    Args:
        vendor_name: Legal name of the vendor entity to verify.
        lei: Optional 20-character LEI code for direct lookup.

    Returns:
        Verification result with entity details, LEI, jurisdiction,
        and registration status (ISSUED = valid, LAPSED = expired).
    """
    _require(gleif=state.gleif)

    if lei and len(lei) == 20:
        result = await state.gleif.lookup_lei(lei)
    else:
        result = await state.gleif.search_entity(vendor_name)

    response = result.to_dict()
    response["verified"] = result.is_verified
    metrics.record_gleif_check(verified=result.is_verified)
    return response


@mcp.tool()
async def score_transaction_risk(
    amount: int,
    agent_id: str,
) -> dict[str, Any]:
    """Score a transaction for anomaly risk using ML (IsolationForest).

    Analyses the transaction against the agent's historical patterns
    to detect anomalies. Uses scikit-learn's IsolationForest algorithm.

    Features analysed: amount (log-scaled), time of day, day of week,
    and deviation from the agent's typical spending pattern.

    The model auto-trains from Redis-stored transaction history.
    Needs ≥10 historical transactions before producing confident scores.

    Args:
        amount: Transaction amount in paise (₹500 = 50000).
        agent_id: The AI agent initiating the transaction.

    Returns:
        Risk assessment with score (0.0=normal, 1.0=anomalous),
        whether it's flagged as anomalous, feature breakdown,
        and model training status.
    """
    _require(anomaly_scorer=state.anomaly_scorer)

    score = await state.anomaly_scorer.score_transaction(amount=amount, agent_id=agent_id)
    metrics.record_anomaly_check(
        anomalous=score.is_anomalous,
        model_trained=score.model_trained,
    )
    return score.to_dict()


@mcp.tool()
async def get_agent_risk_profile(
    agent_id: str,
) -> dict[str, Any]:
    """Get the transaction risk profile for an agent.

    Returns statistics about the agent's historical transaction patterns
    including amount distribution, most active hours, and total transactions.

    Useful for understanding what "normal" looks like for an agent before
    reviewing anomaly scores.

    Args:
        agent_id: The AI agent to profile.

    Returns:
        Transaction statistics and spending patterns.
    """
    _require(anomaly_scorer=state.anomaly_scorer)

    return await state.anomaly_scorer.get_agent_profile(agent_id)


# ================================================================
# AI & Security Tools (Kimi K2.5 + Dual LLM)
# ================================================================


@mcp.tool()
async def check_context_taint() -> dict[str, Any]:
    """Check if current execution context is tainted by untrusted data.

    The Dual LLM quarantine pattern tracks when tools that ingest external
    data (webhooks, Safe Browsing, GLEIF) have been called. Once tainted,
    certain high-privilege tools are blocked to prevent prompt injection.

    Returns:
        Taint status, sources that caused tainting, and affected tools.
    """
    _require(tool_validator=state.tool_validator)

    return {
        "context_tainted": state.tool_validator.is_tainted,
        "taint_sources": state.tool_validator._taint_sources,
        "dual_llm_tools": state.tool_validator._dual_llm_tools,
        "security_llm_configured": state.tool_validator.is_configured,
    }


@mcp.tool()
async def validate_tool_call_security(
    tool_name: str,
    parameters: dict[str, Any],
    agent_id: str = "default",
) -> dict[str, Any]:
    """Validate a tool call through the Dual LLM security layer.

    When context is tainted, this routes to the security LLM which validates
    the operation WITHOUT access to conversation context (quarantine pattern).

    Args:
        tool_name: Name of tool to call.
        parameters: Parameters for the tool call.
        agent_id: Agent requesting the operation.

    Returns:
        Validation result with approve/deny decision and reasoning.
    """
    _require(
        tool_validator=state.tool_validator,
        postgres=state.postgres,
    )

    # Get current governance policy for context
    policy = await state.postgres.get_agent_policy(agent_id)
    governance_policy = {
        "agent_id": agent_id,
        "daily_limit": str(policy.daily_limit) if policy else None,
        "per_txn_limit": str(policy.per_txn_limit) if policy else None,
        "requires_approval_above": str(policy.require_approval_above) if policy else None,
    }

    result = await state.tool_validator.validate(
        tool_name=tool_name,
        parameters=parameters,
        agent_id=agent_id,
        governance_policy=governance_policy,
    )

    return {
        "approved": result.approved,
        "reason": result.reason,
        "risk_score": result.risk_score,
        "mitigation": result.mitigation,
        "context_tainted": state.tool_validator.is_tainted,
    }


@mcp.tool()
async def llm_chat(
    message: str,
    system_prompt: str = "You are a helpful assistant.",
    temperature: float = 0.7,
    max_tokens: int = 1000,
) -> dict[str, Any]:
    """Send a chat completion to the configured LLM (any provider via LiteLLM).

    Security note: This tool marks context as TAINTED because LLM responses
    can contain injected content. Subsequent high-privilege tool calls
    require Dual LLM validation or are blocked.

    Args:
        message: User message to send.
        system_prompt: System prompt/context for the LLM.
        temperature: Sampling temperature (0-2, default 0.7).
        max_tokens: Maximum tokens to generate.

    Returns:
        LLM response text.
    """
    _require(llm_client=state.llm_client, tool_validator=state.tool_validator)

    if not state.llm_client.is_configured:
        return {
            "error": "LLM not configured",
            "config_required": [
                "VYAPAAR_LLM_MODEL",
                "VYAPAAR_LLM_API_KEY",
            ],
        }

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": message},
    ]

    response, status = await state.llm_client.chat_completion(
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )

    if response is None:
        return {
            "error": status,
            "hint": "Configure VYAPAAR_LLM_MODEL and VYAPAAR_LLM_API_KEY",
        }

    # Taint context: LLM responses are untrusted
    state.tool_validator.mark_taint("llm_chat")

    return {
        "response": response,
        "context_note": "Response may be tainted - subsequent critical tools require validation",
    }


@mcp.tool()
async def get_security_status() -> dict[str, Any]:
    """Get security proxy deterministic policy enforcement status.

    Returns current configuration for the security proxy layer that
    enforces hard boundaries on tool access (vs probabilistic guardrails).

    Returns:
        Security proxy config, taint tracking status, and policy tiers.
    """
    _require(config=state.config, tool_validator=state.tool_validator)

    return {
        "security_proxy_enabled": state.config.security_proxy_enabled,
        "security_proxy_url": state.config.security_proxy_url,
        "policy_set_id": state.config.policy_set_id,
        "security_llm": {
            "model": state.config.security_llm_model,
            "base_url": state.config.security_llm_base_url,
            "configured": state.tool_validator.is_configured if state.tool_validator else False,
        },
        "dual_llm_config": {
            "taint_sources": (
                state.config.taint_sources.split(",") if state.config.taint_sources else []
            ),
            "dual_llm_tools": (
                state.config.dual_llm_tools.split(",") if state.config.dual_llm_tools else []
            ),
            "quarantine_strict": state.config.quarantine_strict,
            "audit_logging": state.config.quarantine_audit_log,
        },
        "azure_guardrails": {
            "enabled": state.config.azure_guardrails_enabled,
            "severity": state.config.azure_guardrails_severity,
        },
    }


# ================================================================
# VyapaarClaw v2 — Proactive CFO Tools
# ================================================================


@mcp.tool()
async def forecast_cash_flow(agent_id: str = "", horizon_days: int = 7) -> dict[str, Any]:
    """Forecast budget burn rate and project when agents will exhaust daily limits.

    Uses historical spending data to calculate burn rate trends and
    project days until budget exhaustion. When agent_id is empty,
    forecasts for all active agents.

    Args:
        agent_id: Specific agent to forecast, or empty for all agents.
        horizon_days: How many days of history to analyze (default 7).

    Returns:
        Per-agent forecasts with burn_rate_per_day, projected_exhaustion_days,
        trend (increasing/decreasing/stable), and budget_health (green/yellow/red).
    """
    _require(redis=state.redis, postgres=state.postgres)

    if agent_id:
        agent_ids = [agent_id]
    else:
        agents = await state.postgres.list_all_agents()
        agent_ids = [a["agent_id"] for a in agents]

    if not agent_ids:
        return {"forecasts": [], "note": "No agents with active policies found."}

    forecasts = []
    for aid in agent_ids:
        history = await state.redis.get_historical_spend(aid, days=horizon_days)
        spends = [d["spend"] for d in history]
        nonzero_spends = [s for s in spends if s > 0]

        if not nonzero_spends:
            forecasts.append(
                {
                    "agent_id": aid,
                    "burn_rate_per_day": 0,
                    "trend": "inactive",
                    "budget_health": "green",
                    "note": "No spending in analysis window.",
                }
            )
            continue

        avg_daily = sum(nonzero_spends) / len(nonzero_spends)

        if len(nonzero_spends) >= 3:
            recent_half = nonzero_spends[len(nonzero_spends) // 2 :]
            older_half = nonzero_spends[: len(nonzero_spends) // 2]
            recent_avg = sum(recent_half) / len(recent_half)
            older_avg = sum(older_half) / len(older_half) if older_half else recent_avg
            if recent_avg > older_avg * 1.15:
                trend = "increasing"
            elif recent_avg < older_avg * 0.85:
                trend = "decreasing"
            else:
                trend = "stable"
        else:
            trend = "insufficient_data"

        policy = await state.postgres.get_agent_policy(aid)
        daily_limit = policy.daily_limit if policy else 500000

        utilisation = avg_daily / daily_limit if daily_limit > 0 else 0
        if utilisation > 0.8:
            health = "red"
        elif utilisation > 0.5:
            health = "yellow"
        else:
            health = "green"

        current_spend = await state.redis.get_daily_spend(aid)
        remaining_today = max(0, daily_limit - current_spend)

        forecasts.append(
            {
                "agent_id": aid,
                "daily_limit_paise": daily_limit,
                "avg_daily_spend_paise": int(avg_daily),
                "current_spend_today_paise": current_spend,
                "remaining_today_paise": remaining_today,
                "burn_rate_per_day": int(avg_daily),
                "utilisation_pct": round(utilisation * 100, 1),
                "trend": trend,
                "budget_health": health,
                "analysis_days": horizon_days,
                "active_spend_days": len(nonzero_spends),
            }
        )

    return {"forecasts": forecasts}


@mcp.tool()
async def generate_compliance_report(
    period_days: int = 7,
    agent_id: str = "",
) -> dict[str, Any]:
    """Generate a compliance report summarizing governance decisions over a period.

    Aggregates audit log data to produce approval/rejection ratios,
    top rejection reasons, highest-risk agents, and per-agent breakdowns.
    This is the weekly CFO governance review.

    Args:
        period_days: Number of days to cover (default 7).
        agent_id: Filter to a specific agent, or empty for all.

    Returns:
        Structured compliance report with decision stats, risk indicators,
        and actionable recommendations.
    """
    _require(postgres=state.postgres)

    period_days = max(1, min(period_days, 365))

    stats = await state.postgres.get_compliance_stats(
        period_days=period_days,
        agent_id=agent_id or None,
    )

    decisions = stats.get("decisions", {})
    total = stats.get("total_decisions", 0)

    approved = decisions.get("APPROVED", {}).get("count", 0)
    rejected = decisions.get("REJECTED", {}).get("count", 0)
    held = decisions.get("HELD", {}).get("count", 0)

    approval_rate = (approved / total * 100) if total > 0 else 0
    rejection_rate = (rejected / total * 100) if total > 0 else 0

    risk_level = "low"
    if rejection_rate > 30:
        risk_level = "high"
    elif rejection_rate > 15:
        risk_level = "medium"

    recommendations = []
    if rejection_rate > 30:
        recommendations.append(
            "High rejection rate detected. Review agent policies "
            "and vendor allowlists for misconfiguration."
        )
    if held > 0:
        recommendations.append(
            f"{held} transactions were held for human review. Ensure HITL queue is being monitored."
        )

    agent_breakdown = stats.get("agent_breakdown", {})
    high_risk_agents = []
    for aid, agent_decisions in agent_breakdown.items():
        agent_rejected = agent_decisions.get("REJECTED", {}).get("count", 0)
        agent_total = sum(d.get("count", 0) for d in agent_decisions.values())
        if agent_total > 0 and agent_rejected / agent_total > 0.3:
            high_risk_agents.append(
                {
                    "agent_id": aid,
                    "rejection_rate_pct": round(agent_rejected / agent_total * 100, 1),
                    "total_decisions": agent_total,
                }
            )

    return {
        "report_type": "compliance",
        "period_days": period_days,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "summary": {
            "total_decisions": total,
            "approved": approved,
            "rejected": rejected,
            "held": held,
            "approval_rate_pct": round(approval_rate, 1),
            "rejection_rate_pct": round(rejection_rate, 1),
            "overall_risk_level": risk_level,
        },
        "top_rejection_reasons": stats.get("top_rejection_reasons", []),
        "high_risk_agents": high_risk_agents,
        "agent_breakdown": agent_breakdown,
        "total_volume_paise": sum(d.get("total_amount", 0) for d in decisions.values()),
        "recommendations": recommendations,
    }


@mcp.tool()
async def get_spending_trends(agent_id: str, days: int = 30) -> dict[str, Any]:
    """Get daily spending trends for an agent over the past N days.

    Returns time-series data suitable for charting or analysis.
    Includes summary statistics (min, max, average, total).

    Args:
        agent_id: The agent whose spending to retrieve.
        days: Number of days of history (default 30, max 90).

    Returns:
        Daily spend amounts with summary statistics.
    """
    _require(redis=state.redis)

    days = min(days, 90)
    history = await state.redis.get_historical_spend(agent_id, days=days)

    spends = [d["spend"] for d in history]
    nonzero = [s for s in spends if s > 0]

    return {
        "agent_id": agent_id,
        "days_requested": days,
        "daily_spend": history,
        "summary": {
            "total_spend_paise": sum(spends),
            "active_days": len(nonzero),
            "avg_daily_paise": int(sum(nonzero) / len(nonzero)) if nonzero else 0,
            "max_daily_paise": max(spends) if spends else 0,
            "min_nonzero_paise": min(nonzero) if nonzero else 0,
        },
    }


@mcp.tool()
async def evaluate_payout(
    amount: int,
    agent_id: str,
    vendor_name: str = "",
    vendor_url: str = "",
    purpose: str = "",
) -> dict[str, Any]:
    """Run the complete governance pipeline on a proposed payout in one call.

    Orchestrates: budget check -> vendor reputation -> entity verification ->
    risk scoring -> domain allowlist/blocklist -> decision. This collapses
    what would otherwise be 4-5 sequential tool calls into a single evaluation.

    Args:
        amount: Payout amount in paise (e.g. 50000 = Rs 500).
        agent_id: The agent requesting the payout.
        vendor_name: Vendor/payee name (optional but recommended).
        vendor_url: Vendor URL for reputation check (optional).
        purpose: Description of the payment purpose.

    Returns:
        Full governance result including decision, reason, risk score,
        and all intermediate check results.
    """
    _require(redis=state.redis, postgres=state.postgres, governance=state.governance)

    from vyapaar_mcp.models import PayoutEntity, PayoutNotes

    payout_id = f"eval_{agent_id}_{int(time.time() * 1000)}"
    notes = PayoutNotes(
        agent_id=agent_id,
        purpose=purpose or "governance_evaluation",
        vendor_url=vendor_url,
    )
    payout = PayoutEntity(
        id=payout_id,
        amount=amount,
        currency="INR",
        notes=notes,
        status="evaluation",
    )

    result = await state.governance.evaluate(payout, agent_id, vendor_url or None)

    await log_decision(
        state.postgres,
        result,
        vendor_name=vendor_name,
        vendor_url=vendor_url,
    )

    return {
        "payout_id": payout_id,
        "amount_paise": amount,
        "amount_inr": f"Rs {amount / 100:,.2f}",
        "agent_id": agent_id,
        "vendor_name": vendor_name,
        "decision": result.decision.value,
        "reason_code": result.reason_code.value,
        "reason_detail": result.reason_detail,
        "threat_types": result.threat_types,
        "processing_ms": result.processing_ms,
        "risk_assessment": {
            "budget_remaining_after": (await state.redis.get_daily_spend(agent_id)),
        },
    }


@mcp.tool()
async def list_agents() -> dict[str, Any]:
    """List all agents with active spending policies and current budget status.

    Combines policy data from PostgreSQL with real-time budget
    utilisation from Redis. Useful for the morning brief and
    cross-agent monitoring.

    Returns:
        List of agents with their policies, current daily spend,
        and budget utilisation percentage.
    """
    _require(redis=state.redis, postgres=state.postgres)

    agents_raw = await state.postgres.list_all_agents()

    agents = []
    for agent in agents_raw:
        aid = agent["agent_id"]
        daily_limit = agent["daily_limit"]
        current_spend = await state.redis.get_daily_spend(aid)
        utilisation = (current_spend / daily_limit * 100) if daily_limit > 0 else 0

        agents.append(
            {
                **agent,
                "current_daily_spend_paise": current_spend,
                "utilisation_pct": round(utilisation, 1),
                "budget_health": (
                    "red" if utilisation > 80 else "yellow" if utilisation > 50 else "green"
                ),
            }
        )

    return {
        "total_agents": len(agents),
        "agents": agents,
    }


@mcp.tool()
async def reallocate_budget(
    from_agent_id: str,
    to_agent_id: str,
    new_from_limit: int,
    new_to_limit: int,
) -> dict[str, Any]:
    """Reallocate daily budget limits between two agents.

    Adjusts the daily_limit in both agents' policies atomically.
    Use when an agent consistently under-utilises budget while
    another needs more headroom.

    Args:
        from_agent_id: Agent donating budget capacity.
        to_agent_id: Agent receiving budget capacity.
        new_from_limit: New daily limit for the donor (paise).
        new_to_limit: New daily limit for the recipient (paise).

    Returns:
        Updated policies for both agents with budget status.
    """
    _require(redis=state.redis, postgres=state.postgres)

    from_policy = await state.postgres.get_agent_policy(from_agent_id)
    to_policy = await state.postgres.get_agent_policy(to_agent_id)

    if from_policy is None:
        return {"error": f"No policy found for agent '{from_agent_id}'"}
    if to_policy is None:
        return {"error": f"No policy found for agent '{to_agent_id}'"}

    from_policy.daily_limit = new_from_limit
    to_policy.daily_limit = new_to_limit

    await state.postgres.upsert_agent_policy(from_policy)
    await state.postgres.upsert_agent_policy(to_policy)

    from_spend = await state.redis.get_daily_spend(from_agent_id)
    to_spend = await state.redis.get_daily_spend(to_agent_id)

    return {
        "status": "reallocated",
        "from_agent": {
            "agent_id": from_agent_id,
            "new_daily_limit": new_from_limit,
            "current_spend": from_spend,
            "remaining": max(0, new_from_limit - from_spend),
        },
        "to_agent": {
            "agent_id": to_agent_id,
            "new_daily_limit": new_to_limit,
            "current_spend": to_spend,
            "remaining": max(0, new_to_limit - to_spend),
        },
    }


@mcp.tool()
async def get_vendor_trust_score(vendor_url: str) -> dict[str, Any]:
    """Calculate accumulated trust score for a vendor based on transaction history.

    Analyses past governance decisions involving this vendor's domain
    to build a trust profile. Factors: approval rate, total volume,
    reputation check history, entity verification status.

    Args:
        vendor_url: Vendor URL or domain to score.

    Returns:
        Trust score (0-100), transaction history summary, risk factors.
    """
    _require(redis=state.redis, postgres=state.postgres)
    from urllib.parse import urlparse

    domain = urlparse(vendor_url).netloc or vendor_url

    logs = await state.postgres.get_audit_logs(limit=500)
    vendor_logs = [log for log in logs if log.vendor_url and domain in log.vendor_url]

    if not vendor_logs:
        cached_rep = await state.redis.get_cached_reputation(vendor_url)
        return {
            "vendor_url": vendor_url,
            "domain": domain,
            "trust_score": 50,
            "confidence": "low",
            "transactions": 0,
            "cached_reputation": cached_rep,
            "note": (
                "No transaction history. Score is neutral. "
                "Run check_vendor_reputation and verify_vendor_entity for initial assessment."
            ),
        }

    total = len(vendor_logs)
    approved = sum(1 for entry in vendor_logs if entry.decision == Decision.APPROVED)
    rejected = sum(1 for entry in vendor_logs if entry.decision == Decision.REJECTED)
    total_volume = sum(entry.amount for entry in vendor_logs)
    approval_rate = approved / total if total > 0 else 0

    base_score = approval_rate * 70

    if total >= 20:
        base_score += 15
    elif total >= 5:
        base_score += 10
    elif total >= 2:
        base_score += 5

    threat_count = sum(len(entry.threat_types) for entry in vendor_logs)
    if threat_count > 0:
        base_score -= min(30, threat_count * 10)

    if total >= 10 and approval_rate > 0.9:
        base_score += 15

    trust_score = max(0, min(100, int(base_score)))

    confidence = "high" if total >= 10 else "medium" if total >= 3 else "low"
    risk_level = "low" if trust_score >= 70 else "medium" if trust_score >= 40 else "high"

    return {
        "vendor_url": vendor_url,
        "domain": domain,
        "trust_score": trust_score,
        "risk_level": risk_level,
        "confidence": confidence,
        "transactions": {
            "total": total,
            "approved": approved,
            "rejected": rejected,
            "total_volume_paise": total_volume,
        },
        "threat_history": threat_count,
        "recommendation": (
            "TRUSTED — safe for automated approvals"
            if trust_score >= 80
            else "STANDARD — normal governance applies"
            if trust_score >= 50
            else "ELEVATED RISK — require manual approval"
        ),
    }


@mcp.tool()
async def get_financial_calendar(days_ahead: int = 7) -> dict[str, Any]:
    """Get a financial activity summary and projected upcoming patterns.

    Analyses recent transaction patterns to project upcoming spending
    activity, recurring vendor payments, and budget pressure points.

    Args:
        days_ahead: Number of days to project (default 7, max 30).

    Returns:
        Recent activity summary, recurring patterns, and projected
        budget pressure for upcoming days.
    """
    _require(redis=state.redis, postgres=state.postgres)

    days_ahead = min(days_ahead, 30)

    logs = await state.postgres.get_audit_logs(limit=200)

    from collections import Counter
    from datetime import datetime

    vendor_frequency: Counter[str] = Counter()
    daily_activity: Counter[str] = Counter()
    agent_activity: Counter[str] = Counter()

    for log in logs:
        if log.vendor_name:
            vendor_frequency[log.vendor_name] += 1
        if log.created_at:
            day = log.created_at.strftime("%A")
            daily_activity[day] += 1
        agent_activity[log.agent_id] += 1

    busiest_days = daily_activity.most_common(3)
    recurring_vendors = [
        {"vendor": v, "transactions": c} for v, c in vendor_frequency.most_common(5) if c >= 2
    ]

    agents_raw = await state.postgres.list_all_agents()
    pressure_points = []
    for agent in agents_raw:
        aid = agent["agent_id"]
        history = await state.redis.get_historical_spend(aid, days=7)
        recent_spends = [d["spend"] for d in history if d["spend"] > 0]
        if recent_spends:
            avg_daily = sum(recent_spends) / len(recent_spends)
            daily_limit = agent["daily_limit"]
            if daily_limit > 0 and avg_daily / daily_limit > 0.6:
                pressure_points.append(
                    {
                        "agent_id": aid,
                        "avg_daily_spend": int(avg_daily),
                        "daily_limit": daily_limit,
                        "utilisation_pct": round(avg_daily / daily_limit * 100, 1),
                    }
                )

    today = datetime.now().strftime("%A")

    return {
        "projection_days": days_ahead,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "recent_activity": {
            "total_decisions_in_log": len(logs),
            "busiest_days_of_week": [{"day": d, "avg_transactions": c} for d, c in busiest_days],
            "today_is": today,
            "today_expected_volume": (daily_activity.get(today, 0)),
        },
        "recurring_vendors": recurring_vendors,
        "budget_pressure_points": pressure_points,
        "most_active_agents": [
            {"agent_id": a, "transactions": c} for a, c in agent_activity.most_common(5)
        ],
    }


# ================================================================
# CFO Intelligence Tools (expanded AI CFO capabilities)
# ================================================================


@mcp.tool()
async def get_indian_financial_calendar(
    days_ahead: int = 30,
    include_deadlines: bool = True,
) -> dict[str, Any]:
    """Get Indian financial calendar with holidays, deadlines, and settlement info.

    Includes Indian public holidays, GST/TDS filing deadlines, and
    settlement date computation for NEFT/RTGS/IMPS payments.

    Args:
        days_ahead: Days to look ahead for holidays and deadlines.
        include_deadlines: Include GST/TDS compliance deadlines.
    """
    import datetime as dt

    from vyapaar_mcp.cfo.calendar import (
        is_business_day,
        next_business_day,
        settlement_date,
        upcoming_deadlines,
        upcoming_holidays,
    )

    today = dt.date.today()
    holidays_list = upcoming_holidays(today, count=min(days_ahead, 15))
    deadlines = upcoming_deadlines(today, count=10) if include_deadlines else []

    neft_settlement = settlement_date(today, t_plus=0)
    stock_settlement = settlement_date(today, t_plus=1)

    return {
        "today": today.isoformat(),
        "is_business_day": is_business_day(today),
        "next_business_day": next_business_day(today).isoformat(),
        "neft_settlement_date": neft_settlement.isoformat(),
        "stock_settlement_t1": stock_settlement.isoformat(),
        "upcoming_holidays": holidays_list,
        "compliance_deadlines": deadlines,
    }


@mcp.tool()
async def convert_currency(
    amount: float,
    from_currency: str,
    to_currency: str = "INR",
    date: str | None = None,
) -> dict[str, Any]:
    """Convert currency amounts using live ECB exchange rates.

    Uses Frankfurter (FOSS, no API key). Supports 30+ currencies.
    All cross-border payouts should use this for INR-equivalent budget check.

    Args:
        amount: Amount to convert.
        from_currency: Source currency code (e.g., USD, EUR, GBP).
        to_currency: Target currency code (default INR).
        date: ISO date for historical rate (optional, default: latest).
    """
    from vyapaar_mcp.cfo.currency import convert_amount

    return await convert_amount(amount, from_currency, to_currency, date, redis_client=_redis)


@mcp.tool()
async def validate_gstin(gstin: str) -> dict[str, Any]:
    """Validate an Indian GSTIN (Goods and Services Tax ID).

    Performs checksum verification, extracts state, PAN, entity type,
    and detects composition dealers. Use before approving vendor payouts.

    Args:
        gstin: 15-character GSTIN to validate.
    """
    from vyapaar_mcp.cfo.tax import validate_gstin as _validate

    return _validate(gstin)


@mcp.tool()
async def calculate_gst(
    amount_paise: int,
    rate_percent: float = 18.0,
    is_interstate: bool = False,
) -> dict[str, Any]:
    """Calculate GST breakdown (CGST/SGST or IGST) on a payout amount.

    Args:
        amount_paise: Base amount in paise (before GST).
        rate_percent: GST rate: 5, 12, 18, or 28 percent.
        is_interstate: True for inter-state (IGST), False for intra-state (CGST+SGST).
    """
    from vyapaar_mcp.cfo.tax import calculate_gst as _calc

    return _calc(amount_paise, rate_percent, is_interstate)


@mcp.tool()
async def check_tds(
    amount_paise: int,
    section: str = "194C",
) -> dict[str, Any]:
    """Check TDS (Tax Deducted at Source) applicability on a vendor payout.

    Common sections: 194C (contractors), 194J (professionals), 194H (commission).

    Args:
        amount_paise: Payout amount in paise.
        section: TDS section code.
    """
    from vyapaar_mcp.cfo.tax import check_tds_applicability

    return check_tds_applicability(amount_paise, section)


@mcp.tool()
async def validate_bank_account(
    ifsc: str,
    account_number: str,
    beneficiary_name: str = "",
    online_lookup: bool = False,
) -> dict[str, Any]:
    """Validate an Indian bank account before creating a payout.

    Checks IFSC format (RBI spec), account number format,
    and optionally looks up IFSC details via Razorpay's free API.

    Args:
        ifsc: 11-character IFSC code.
        account_number: Bank account number (9-18 digits).
        beneficiary_name: Optional beneficiary name.
        online_lookup: If True, also query Razorpay IFSC API for branch details.
    """
    from vyapaar_mcp.cfo.bank import lookup_ifsc_online, validate_fund_account

    result = validate_fund_account(ifsc, account_number, beneficiary_name)

    if online_lookup and result["valid"]:
        online_data = await lookup_ifsc_online(ifsc)
        result["online_details"] = online_data

    return result


@mcp.tool()
async def categorize_transaction(
    description: str,
    amount_paise: int = 0,
    vendor_name: str = "",
) -> dict[str, Any]:
    """Categorize a transaction into spending categories.

    Uses keyword matching to classify payouts into: salaries, SaaS,
    professional services, marketing, utilities, travel, etc.

    Args:
        description: Transaction description or narration.
        amount_paise: Transaction amount in paise.
        vendor_name: Vendor or payee name.
    """
    from vyapaar_mcp.cfo.categorizer import categorize_transaction as _categorize

    return _categorize(description, amount_paise, vendor_name)


@mcp.tool()
async def forecast_budget_runway(
    agent_id: str,
    forecast_days: int = 30,
) -> dict[str, Any]:
    """Forecast budget runway for an agent using historical spend data.

    Predicts when the agent will exhaust its budget, detects
    spending trend (increasing/decreasing/stable), and flags
    critical burn rates.

    Args:
        agent_id: Agent to forecast.
        forecast_days: Days to project forward (max 90).
    """
    _require(redis=state.redis, postgres=state.postgres)

    from vyapaar_mcp.cfo.forecaster import forecast_burn_rate

    forecast_days = min(forecast_days, 90)

    history = await state.redis.get_historical_spend(agent_id, days=30)
    daily_spends = [d["spend"] for d in history]

    policy = await state.postgres.get_policy(agent_id)
    if not policy:
        return {"error": f"No policy found for agent '{agent_id}'"}

    budget_remaining = policy.daily_limit - sum(daily_spends[:1])  # Today's remaining

    return forecast_burn_rate(daily_spends, budget_remaining, forecast_days)


@mcp.tool()
async def track_payout_in_ledger(
    amount_paise: int,
    description: str,
    vendor_name: str = "",
    category: str = "vendor_payments",
    payout_id: str = "",
    gst_paise: int = 0,
    tds_paise: int = 0,
) -> dict[str, Any]:
    """Record a payout as a double-entry journal entry in the ledger.

    Creates proper accounting entries: debits the expense account,
    credits the Razorpay balance, with GST/TDS lines if applicable.

    Args:
        amount_paise: Payout amount in paise.
        description: Transaction description.
        vendor_name: Vendor or payee name.
        category: Expense category (e.g., saas_software, salaries_wages).
        payout_id: Razorpay payout ID for reference.
        gst_paise: GST amount in paise (if applicable).
        tds_paise: TDS deduction in paise (if applicable).
    """
    from vyapaar_mcp.cfo.ledger import get_ledger, persist_journal_entry

    ledger = get_ledger()
    entry = ledger.record_payout(
        amount_paise=amount_paise,
        description=description,
        vendor_name=vendor_name,
        category=category,
        payout_id=payout_id,
        gst_paise=gst_paise,
        tds_paise=tds_paise,
    )
    if state.postgres:
        await persist_journal_entry(state.postgres, entry)
        entry["persisted"] = True
    return entry


@mcp.tool()
async def get_trial_balance() -> dict[str, Any]:
    """Get the trial balance from the double-entry ledger.

    Returns all account balances showing debits and credits.
    A balanced trial confirms accounting integrity.
    """
    from vyapaar_mcp.cfo.ledger import get_ledger

    in_memory = get_ledger().get_trial_balance()
    if state.postgres:
        try:
            pg_balance = await state.postgres.get_ledger_trial_balance()
            if pg_balance:
                in_memory["postgres_trial_balance"] = pg_balance
                in_memory["source"] = "memory+postgres"
        except Exception as exc:
            in_memory["postgres_error"] = str(exc)
    return in_memory


@mcp.tool()
async def get_income_statement() -> dict[str, Any]:
    """Get the income statement (P&L) from the ledger.

    Shows total revenue, expense breakdown by category,
    and net income. Essential for CFO decision-making.
    """
    from vyapaar_mcp.cfo.ledger import get_ledger

    return get_ledger().get_income_statement()


@mcp.tool()
async def generate_compliance_pdf(
    output_path: str = "",
) -> dict[str, Any]:
    """Generate a PDF compliance report with governance summary.

    Creates a professional PDF with budget summary, risk analysis,
    recent transactions, GST compliance, and fraud findings.

    Args:
        output_path: Where to save the PDF (default: /tmp/).
    """
    from vyapaar_mcp.cfo.reports import generate_governance_report

    # Gather data from available services
    summary: dict[str, Any] = {
        "budget_summary": {},
        "risk_summary": {
            "total_reviewed": 0,
            "anomalies_detected": 0,
            "payouts_held": 0,
            "payouts_rejected": 0,
        },
        "recent_transactions": [],
        "forecast": {"severity": "healthy"},
    }

    if state.postgres:
        try:
            logs = await state.postgres.get_audit_logs(limit=20)
            summary["recent_transactions"] = [
                {
                    "date": log.created_at.strftime("%Y-%m-%d") if log.created_at else "",
                    "vendor": log.vendor_name or "",
                    "amount_paise": log.amount_paise,
                    "category": "misc",
                    "status": log.decision.value if log.decision else "",
                }
                for log in logs
            ]
            summary["risk_summary"]["total_reviewed"] = len(logs)
        except AUDIT_READ_ERRORS as exc:
            logger.warning("Skipping audit-log section in compliance PDF: %s", exc)

    path = generate_governance_report(summary, output_path or "")
    return {"report_path": path, "status": "generated"}


@mcp.tool()
async def detect_fraud_network(
    transactions: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Run graph-based fraud detection on transaction data.

    Detects fraud patterns beyond single-transaction anomalies:
    - Shared PAN/bank accounts (shell companies)
    - Circular payment patterns (money laundering)
    - High vendor centrality (concentration risk)

    Args:
        transactions: List of transaction dicts with agent_id, vendor_name,
                     amount_paise, bank_account, ifsc, pan fields.
                     If None, loads from audit logs.
    """
    from vyapaar_mcp.cfo.fraud import detect_fraud_patterns

    if transactions is None:
        transactions = []
        if state.postgres:
            try:
                logs = await state.postgres.get_audit_logs(limit=100)
                transactions = [
                    {
                        "agent_id": log.agent_id,
                        "vendor_name": log.vendor_name or "unknown",
                        "amount_paise": log.amount_paise,
                    }
                    for log in logs
                ]
            except AUDIT_READ_ERRORS as exc:
                logger.warning("Skipping audit-log load for fraud network: %s", exc)

    return detect_fraud_patterns(transactions)


@mcp.tool()
async def analyze_contract(
    contract_text: str,
) -> dict[str, Any]:
    """Analyze a vendor contract to extract financial terms and risk flags.

    Extracts payment terms, penalty clauses, SLA commitments,
    auto-renewal clauses, and termination notice requirements.

    Args:
        contract_text: Plain text content of the vendor contract.
    """
    from vyapaar_mcp.cfo.contracts import analyze_contract_text

    return analyze_contract_text(contract_text)


@mcp.tool()
async def screen_vendor_sanctions(
    vendor_name: str,
    gstin: str = "",
) -> dict[str, Any]:
    """Screen a vendor against global sanctions and watchlists.

    Uses OpenSanctions (FOSS) to check against 100+ data sources
    including UN, EU, OFAC sanctions, and PEP databases.
    Combines with GSTIN validation for composite trust scoring.

    Args:
        vendor_name: Name of the vendor to screen.
        gstin: Optional GSTIN for additional verification.
    """
    from vyapaar_mcp.cfo.sanctions import comprehensive_vendor_screen

    result = await comprehensive_vendor_screen(
        vendor_name,
        gstin=gstin,
        gleif_checker=state.gleif,
        safe_browsing_checker=state.safe_browsing,
    )

    if state.denchclaw and state.config.denchclaw_enabled:
        try:
            from datetime import UTC, datetime

            await state.denchclaw.sync_vendor(
                {
                    "vendor_name": vendor_name,
                    "gstin": gstin,
                    "trust_score": result.get("trust_score"),
                    "trust_level": result.get("trust_level"),
                    "sanctions_status": result.get("sanctions", {}).get("risk_level", ""),
                    "last_screened": datetime.now(tz=UTC).isoformat(),
                }
            )
            result["denchclaw_synced"] = True
        except Exception as exc:
            result["denchclaw_synced"] = False
            result["denchclaw_error"] = str(exc)

    return result


@mcp.tool()
async def manage_payout_workflow(
    action: str,
    payout_id: str = "",
    amount_paise: int = 0,
    agent_id: str = "",
    reason: str = "",
) -> dict[str, Any]:
    """Manage payout approval workflows with formal state machine.

    Replaces simple APPROVED/REJECTED with multi-stage lifecycle:
    QUEUED → POLICY_CHECK → REPUTATION_CHECK → ANOMALY_CHECK →
      → APPROVED → DISBURSED → CONFIRMED
      → HELD → PENDING_L1 → PENDING_L2 → APPROVED

    Args:
        action: One of create, start_review, pass_policy, pass_reputation,
               pass_anomaly, hold, escalate_l1, approve_l1, reject, disburse,
               confirm, status, list.
        payout_id: Payout ID (required for all actions except create/list).
        amount_paise: Amount (required for create).
        agent_id: Agent ID (required for create).
        reason: Reason for the action (for audit trail).
    """
    from vyapaar_mcp.cfo.workflow import (
        create_workflow,
        get_workflow_async,
        list_workflows_async,
        persist_workflow,
    )

    if action == "create":
        wf = create_workflow(payout_id, amount_paise, agent_id)
        await persist_workflow(wf)
        return wf.get_status()

    if action == "list":
        return {"workflows": await list_workflows_async()}

    if action == "status":
        wf = await get_workflow_async(payout_id)
        if not wf:
            return {"error": f"Workflow '{payout_id}' not found"}
        return wf.get_status()

    # State transitions
    wf = await get_workflow_async(payout_id)
    if not wf:
        return {"error": f"Workflow '{payout_id}' not found"}

    transition_map = {
        "start_review": wf.start_review,
        "pass_policy": wf.pass_policy,
        "pass_reputation": wf.pass_reputation,
        "pass_anomaly": wf.pass_anomaly,
        "hold": wf.hold,
        "escalate_l1": wf.escalate_l1,
        "approve_l1": wf.approve_l1,
        "escalate_l2": wf.escalate_l2,
        "approve_l2": wf.approve_l2,
        "reject": wf.reject,
        "disburse": wf.disburse,
        "confirm": wf.confirm,
        "archive": wf.archive,
    }

    trigger = transition_map.get(action)
    if not trigger:
        return {
            "error": f"Unknown action: {action}",
            "available_actions": list(transition_map.keys()),
        }

    try:
        trigger(reason=reason)  # type: ignore[call-arg]
    except (MachineError, TypeError, AttributeError, ValueError) as exc:
        return {"error": str(exc), "current_state": wf.state}  # type: ignore[attr-defined]

    await persist_workflow(wf)
    return wf.get_status()


# ================================================================
# DenchClaw CRM Integration Tools
# ================================================================


@mcp.tool()
async def get_denchclaw_status() -> dict[str, Any]:
    """Check DenchClaw CRM integration health and object counts.

    DenchClaw (https://github.com/DenchHQ/DenchClaw) stores audit logs
    and vendor KYB records as searchable CRM object tables.
    """
    if state.denchclaw is None:
        return {"enabled": False, "error": "DenchClaw client not initialized"}
    return await state.denchclaw.status()


@mcp.tool()
async def sync_audit_to_denchclaw(
    payout_id: str = "",
    limit: int = 50,
) -> dict[str, Any]:
    """Sync governance audit logs from PostgreSQL to DenchClaw CRM.

    Syncs one payout by ID, or the most recent `limit` entries if no ID given.
    """
    _require(postgres=state.postgres)
    if state.denchclaw is None or not state.config.denchclaw_enabled:
        return {"synced": 0, "error": "DenchClaw integration disabled"}

    logs = await state.postgres.get_audit_logs(payout_id=payout_id or None, limit=limit)
    synced = 0
    errors: list[str] = []
    for log in logs:
        try:
            result = await state.denchclaw.sync_audit_entry(
                {
                    "payout_id": log.payout_id,
                    "agent_id": log.agent_id,
                    "amount": log.amount,
                    "decision": log.decision.value,
                    "reason_code": log.reason_code.value,
                    "reason_detail": log.reason_detail,
                    "vendor_name": log.vendor_name,
                    "vendor_url": log.vendor_url,
                    "processing_ms": log.processing_ms,
                }
            )
            if result.get("synced"):
                synced += 1
        except Exception as exc:
            errors.append(f"{log.payout_id}: {exc}")

    return {"synced": synced, "total": len(logs), "errors": errors}


@mcp.tool()
async def get_denchclaw_audit_log(
    page: int = 1,
    page_size: int = 50,
) -> dict[str, Any]:
    """Read audit log entries from DenchClaw CRM object table."""
    if state.denchclaw is None:
        return {"entries": [], "error": "DenchClaw not initialized"}
    from vyapaar_mcp.integrations.denchclaw_schema import AUDIT_OBJECT

    return await state.denchclaw.get_object_entries(AUDIT_OBJECT, page, page_size)


# ================================================================
# Phase 2 — Live Verification & Research Tools
# ================================================================


@mcp.tool()
async def verify_gstin_live(
    gstin: str,
    vendor_name: str = "",
) -> dict[str, Any]:
    """Verify GSTIN with tiered providers: format → Browserwire → GSP API.

    Returns live registration status, legal name, and recommendation
    (PASS / HOLD / REJECT) when portal or GSP credentials are configured.
    """
    if state.gst_chain is None:
        state.gst_chain = build_gst_chain(
            browserwire_url=state.config.browserwire_url if state.config else "",
            browserwire_key=state.config.browserwire_api_key if state.config else "",
            gsp_url=state.config.gsp_api_url if state.config else "",
            gsp_key=state.config.gsp_api_key if state.config else "",
        )
    return await state.gst_chain.verify(gstin, vendor_name)


@mcp.tool()
async def research_vendor(
    vendor_name: str,
    extra_context: str = "",
) -> dict[str, Any]:
    """Research a vendor using Exa search for KYB due diligence.

    Returns company research results and adverse signal scan.
    Requires VYAPAAR_EXA_API_KEY.
    """
    if state.exa_client is None:
        state.exa_client = ExaClient(api_key=state.config.exa_api_key if state.config else "")
    return await state.exa_client.research_vendor(vendor_name, extra_context)


@mcp.tool()
async def screen_adverse_media(
    vendor_name: str,
) -> dict[str, Any]:
    """Screen vendor for adverse media (fraud, lawsuits, penalties).

    Uses Exa search with keyword risk scoring. Requires VYAPAAR_EXA_API_KEY.
    """
    from vyapaar_mcp.reputation.adverse_media import screen_adverse_media as _screen

    if state.exa_client is None:
        state.exa_client = ExaClient(api_key=state.config.exa_api_key if state.config else "")
    return await _screen(vendor_name, exa_client=state.exa_client)


# ================================================================
# Phase 3 — Full AI CFO Tools
# ================================================================


@mcp.tool()
async def validate_einvoice(
    irn: str = "",
    ack_no: str = "",
    gstin: str = "",
    invoice_number: str = "",
    invoice_date: str = "",
) -> dict[str, Any]:
    """Validate GST e-invoice IRN / ack number for B2B payout matching."""
    from vyapaar_mcp.cfo.einvoice import validate_einvoice_bundle

    return validate_einvoice_bundle(
        irn=irn,
        ack_no=ack_no,
        gstin=gstin,
        invoice_number=invoice_number,
        invoice_date=invoice_date,
    )


@mcp.tool()
async def extract_invoice_data(
    file_path: str = "",
    file_base64: str = "",
) -> dict[str, Any]:
    """Extract structured invoice data via HyperAPI OCR.

    Returns vendor name, GSTIN, amounts, and line items from PDF/image.
    Requires VYAPAAR_HYPERAPI_API_KEY.
    """
    from vyapaar_mcp.cfo.invoice_ocr import extract_invoice

    cfg = state.config
    return await extract_invoice(
        file_path=file_path,
        file_base64=file_base64,
        api_key=cfg.hyperapi_api_key if cfg else "",
        base_url=cfg.hyperapi_base_url if cfg else "https://api.hyperbots.com",
    )


@mcp.tool()
async def detect_fraud_network_ml(
    transactions: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Enhanced fraud detection with graph patterns + optional PyGOD GNN."""
    from vyapaar_mcp.cfo.fraud import detect_fraud_with_ml

    if transactions is None and state.postgres:
        try:
            logs = await state.postgres.get_audit_logs(limit=100)
            transactions = [
                {
                    "agent_id": log.agent_id,
                    "vendor_name": log.vendor_name or "unknown",
                    "amount_paise": log.amount,
                }
                for log in logs
            ]
        except AUDIT_READ_ERRORS as exc:
            logger.warning("Skipping audit-log load for ML fraud: %s", exc)
            transactions = []

    return detect_fraud_with_ml(transactions or [])


# ================================================================
# Server Runner
# ================================================================


async def run_server() -> None:
    """Start the VyapaarClaw server.

    When run directly, lifespan is handled by FastMCP automatically.
    """
    await mcp.run_stdio_async()


def run_server_sync() -> None:
    """Synchronous entrypoint with custom SSE path handling."""
    import os

    import uvicorn
    from mcp.server.sse import SseServerTransport

    transport_name = os.environ.get("VYAPAAR_TRANSPORT", "stdio")

    if transport_name == "sse":
        host = os.environ.get("VYAPAAR_HOST", "0.0.0.0")
        port = int(os.environ.get("VYAPAAR_PORT", "8000"))

        # Create SSE transport - messages endpoint is relative
        sse = SseServerTransport("/messages/")

        async def sse_handler(request: Request) -> Response:
            """Handle SSE connections - returns session ID via SSE event.

            Note: POST is accepted as a workaround for Kimi CLI bug that sends POST instead of GET.
            """
            scope, receive, send = request.scope, request.receive, request._send
            async with sse.connect_sse(scope, receive, send) as streams:
                await mcp._mcp_server.run(
                    streams[0], streams[1], mcp._mcp_server.create_initialization_options()
                )
            # Return empty response after SSE connection closes
            return Response()

        from starlette.middleware import Middleware
        from starlette.middleware.base import BaseHTTPMiddleware
        from starlette.responses import JSONResponse

        async def auth_middleware(request: Request, call_next: Any) -> Response:
            secret = os.environ.get("VYAPAAR_MCP_SECRET")
            if not secret:
                return await call_next(request)

            # Allow health checks and unauthenticated webhooks
            if request.url.path in ["/health", "/slack/actions", "/telegram/callback"]:
                return await call_next(request)

            auth_header = request.headers.get("authorization", "")
            if not auth_header.startswith("Bearer ") or auth_header[7:] != secret:
                return JSONResponse({"error": "Unauthorized"}, status_code=401)

            return await call_next(request)

        starlette_app = Starlette(
            debug=state.config.dev_mode
            if state.config
            else os.environ.get("VYAPAAR_DEV_MODE", "").lower() == "true",
            middleware=[Middleware(BaseHTTPMiddleware, dispatch=auth_middleware)],
            routes=[
                Route("/sse", endpoint=sse_handler, methods=["GET", "POST"]),
                Mount("/messages/", app=sse.handle_post_message),
                Route("/health", endpoint=health_endpoint, methods=["GET"]),
                Route("/api/v1/dashboard", endpoint=dashboard_endpoint, methods=["GET"]),
                Route("/api/v1/agents", endpoint=agents_endpoint, methods=["GET"]),
                Route("/api/v1/audit", endpoint=audit_endpoint, methods=["GET"]),
                Route("/slack/actions", endpoint=slack_actions_endpoint, methods=["POST"]),
                Route("/telegram/callback", endpoint=telegram_callback_endpoint, methods=["POST"]),
            ],
        )

        # Add custom routes from mcp
        starlette_app.routes.extend(mcp._custom_starlette_routes)

        uvicorn.run(starlette_app, host=host, port=port)
    else:
        mcp.run(transport=transport_name)  # type: ignore[arg-type]


# Allow direct execution
if __name__ == "__main__":
    run_server_sync()
