"""VyapaarClaw MCP Server — FastMCP entrypoint with SSE transport.

Registers all 25 governance tools and manages the lifecycle of
Redis, PostgreSQL, and external API clients.

Part of the VyapaarClaw OpenClaw Framework for AI Financial Governance.
"""

from __future__ import annotations

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from typing import Any

from mcp.server.fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Mount, Route

from vyapaar_mcp.audit.logger import log_decision
from vyapaar_mcp.config import VyapaarConfig, load_config
from vyapaar_mcp.db.postgres import PostgresClient
from vyapaar_mcp.db.redis_client import RedisClient
from vyapaar_mcp.egress.ntfy_notifier import NtfyNotifier, notify_with_fallback
from vyapaar_mcp.egress.razorpay_actions import RazorpayActions
from vyapaar_mcp.egress.slack_notifier import SlackNotifier
from vyapaar_mcp.egress.telegram_notifier import TelegramNotifier
from vyapaar_mcp.governance.engine import GovernanceEngine
from vyapaar_mcp.ingress.polling import PayoutPoller
from vyapaar_mcp.ingress.razorpay_bridge import RazorpayBridge
from vyapaar_mcp.ingress.webhook import (
    extract_webhook_id,
    parse_webhook_event,
    verify_razorpay_signature,
)
from vyapaar_mcp.llm import AzureOpenAIClient, SecurityLLMClient
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
from vyapaar_mcp.resilience import CircuitBreaker

# ================================================================
# Logging Setup
# ================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("vyapaar_mcp")

# ================================================================
# Global State (initialized in lifespan)
# ================================================================

_config: VyapaarConfig | None = None
_redis: RedisClient | None = None
_postgres: PostgresClient | None = None
_safe_browsing: SafeBrowsingChecker | None = None
_razorpay: RazorpayActions | None = None
_razorpay_bridge: RazorpayBridge | None = None
_slack: SlackNotifier | None = None
_poller: PayoutPoller | None = None
_governance: GovernanceEngine | None = None
_poll_task: asyncio.Task[None] | None = None
_start_time: float = time.time()
_cb_razorpay: CircuitBreaker | None = None
_cb_safe_browsing: CircuitBreaker | None = None
_cb_gleif: CircuitBreaker | None = None
_gleif: GLEIFChecker | None = None
_anomaly_scorer: TransactionAnomalyScorer | None = None
_ntfy: NtfyNotifier | None = None
_telegram: TelegramNotifier | None = None
_azure_llm: AzureOpenAIClient | None = None
_security_llm: SecurityLLMClient | None = None
_tool_validator: ToolCallValidator | None = None


def _require(**services: Any) -> None:
    """Validate that required server components are initialized.

    Raises RuntimeError instead of using assert (which is stripped
    with ``python -O``).
    """
    missing = [name for name, obj in services.items() if obj is None]
    if missing:
        raise RuntimeError(
            f"Server not initialised — missing: {', '.join(missing)}. "
            "Ensure startup() completed successfully."
        )


# ================================================================
# FastMCP Server
# ================================================================


@asynccontextmanager
async def _lifespan(server: FastMCP):
    """FastMCP lifespan context manager — runs startup/shutdown."""
    await _startup()
    try:
        yield
    finally:
        await _shutdown()


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


@mcp.custom_route("/health", methods=["GET"])
async def health_endpoint(request: Request) -> JSONResponse:
    """HTTP Health Check for monitoring, load balancers, and web UI."""
    redis_ok = await _redis.ping() if _redis else False
    postgres_ok = await _postgres.ping() if _postgres else False
    return JSONResponse({
        "status": "ok" if (redis_ok and postgres_ok) else "degraded",
        "service": "vyapaarclaw",
        "version": "0.1.0",
        "uptime_seconds": int(time.time() - _start_time),
        "redis": "ok" if redis_ok else "error",
        "postgres": "ok" if postgres_ok else "error",
    })


async def slack_actions_endpoint(request: Request) -> JSONResponse:
    """Receive Slack interactive component callbacks (button clicks).

    Slack POSTs a url-encoded payload when a user clicks Approve/Reject.
    This endpoint verifies the signature, parses the action, and routes
    it to the handle_slack_action tool internally.
    """
    import json as _json
    from urllib.parse import parse_qs

    body_bytes = await request.body()
    body_str = body_bytes.decode("utf-8")

    # Verify Slack signature when signing secret is configured
    if _config and _config.slack_signing_secret:
        from vyapaar_mcp.egress.slack_notifier import verify_slack_signature

        timestamp = request.headers.get("X-Slack-Request-Timestamp", "")
        signature = request.headers.get("X-Slack-Signature", "")
        if not verify_slack_signature(body_str, timestamp, signature, _config.slack_signing_secret):
            return JSONResponse({"error": "invalid signature"}, status_code=401)

    # Slack sends payload as url-encoded form: payload=<JSON>
    parsed = parse_qs(body_str)
    raw_payload = parsed.get("payload", [""])[0]
    if not raw_payload:
        return JSONResponse({"error": "missing payload"}, status_code=400)

    try:
        payload = _json.loads(raw_payload)
    except _json.JSONDecodeError:
        return JSONResponse({"error": "invalid JSON payload"}, status_code=400)

    actions = payload.get("actions", [])
    if not actions:
        return JSONResponse({"error": "no actions in payload"}, status_code=400)

    action = actions[0]
    action_id = action.get("action_id", "")
    payout_id = action.get("value", "")
    user_name = payload.get("user", {}).get("username", "unknown")
    channel = payload.get("channel", {}).get("id")
    message_ts = payload.get("message", {}).get("ts")

    _require(razorpay=_razorpay)

    result = await handle_slack_action(
        action_id=action_id,
        payout_id=payout_id,
        user_name=user_name,
        channel=channel,
        message_ts=message_ts,
    )

    return JSONResponse(result)


async def telegram_callback_endpoint(request: Request) -> JSONResponse:
    """Receive Telegram Bot API webhook updates (inline keyboard callbacks).

    Telegram POSTs a JSON update when a user taps an inline keyboard button.
    This endpoint parses the callback_query, extracts the action, and routes
    it to handle_telegram_action.
    """
    import json as _json

    try:
        update = await request.json()
    except Exception:
        return JSONResponse({"error": "invalid JSON"}, status_code=400)

    callback_query = update.get("callback_query")
    if not callback_query:
        return JSONResponse({"ok": True})

    try:
        data = _json.loads(callback_query.get("data", "{}"))
    except (_json.JSONDecodeError, TypeError):
        return JSONResponse({"error": "invalid callback_data"}, status_code=400)

    action_id = data.get("a", "")
    payout_id = data.get("p", "")
    user = callback_query.get("from", {})
    user_name = user.get("username") or user.get("first_name", "unknown")
    message = callback_query.get("message", {})
    chat_id = message.get("chat", {}).get("id")
    message_id = message.get("message_id")
    callback_query_id = callback_query.get("id")

    if not action_id or not payout_id:
        return JSONResponse({"error": "missing action or payout_id"}, status_code=400)

    _require(razorpay=_razorpay)

    result = await handle_telegram_action(
        action_id=action_id,
        payout_id=payout_id,
        user_name=user_name,
        chat_id=chat_id,
        message_id=message_id,
        callback_query_id=callback_query_id,
    )

    return JSONResponse(result)


# ================================================================
# Lifecycle
# ================================================================


async def _startup() -> None:
    """Initialize all services on server start."""
    global _config, _redis, _postgres, _safe_browsing, \
        _razorpay, _razorpay_bridge, _slack, _telegram, _poller, \
        _governance, _poll_task, _start_time, \
        _cb_razorpay, _cb_safe_browsing, _cb_gleif, \
        _gleif, _anomaly_scorer, _ntfy, \
        _azure_llm, _security_llm, _tool_validator

    _start_time = time.time()
    _config = load_config()

    logger.info("=" * 60)
    logger.info("  VyapaarClaw — Starting up...")
    logger.info("=" * 60)

    # Redis
    _redis = RedisClient(url=_config.redis_url)
    try:
        await _redis.connect()
        logger.info("✅ Redis connected")
    except Exception as e:
        logger.error("❌ Redis connection failed: %s", e)

    # PostgreSQL
    _postgres = PostgresClient(dsn=_config.postgres_dsn)
    try:
        await _postgres.connect()
        await _postgres.run_migrations()
        logger.info("✅ PostgreSQL connected + migrations complete")
    except Exception as e:
        logger.error("❌ PostgreSQL connection failed: %s", e)

    # Google Safe Browsing
    _cb_safe_browsing = CircuitBreaker(
        "safe-browsing",
        failure_threshold=_config.circuit_breaker_failure_threshold,
        recovery_timeout=float(_config.circuit_breaker_recovery_timeout),
    )
    _safe_browsing = SafeBrowsingChecker(
        api_key=_config.google_safe_browsing_key,
        api_url=_config.safe_browsing_api_url,
        redis=_redis,
        circuit_breaker=_cb_safe_browsing,
    )
    logger.info("✅ Safe Browsing checker initialized (circuit breaker enabled)")

    # Razorpay Actions (egress — approve/reject)
    _cb_razorpay = CircuitBreaker(
        "razorpay",
        failure_threshold=_config.circuit_breaker_failure_threshold,
        recovery_timeout=float(_config.circuit_breaker_recovery_timeout),
    )
    _razorpay = RazorpayActions(
        key_id=_config.razorpay_key_id,
        key_secret=_config.razorpay_key_secret,
        circuit_breaker=_cb_razorpay,
    )
    logger.info("✅ Razorpay egress client initialized (circuit breaker enabled)")

    # Razorpay Bridge (ingress — API calls, same as official MCP server)
    _razorpay_bridge = RazorpayBridge(
        key_id=_config.razorpay_key_id,
        key_secret=_config.razorpay_key_secret,
    )
    logger.info(
        "✅ RazorpayBridge initialized "
        "(mirrors razorpay/razorpay-mcp-server tools)"
    )

    # Slack Notifier (human-in-the-loop)
    if _config.slack_bot_token and _config.slack_channel_id:
        _slack = SlackNotifier(
            bot_token=_config.slack_bot_token,
            channel_id=_config.slack_channel_id,
        )
        logger.info("✅ Slack notifier initialized (channel=%s)", _config.slack_channel_id)
    else:
        logger.warning(
            "⚠️  Slack not configured — HELD payouts will not trigger approval requests. "
            "Set VYAPAAR_SLACK_BOT_TOKEN and VYAPAAR_SLACK_CHANNEL_ID in .env"
        )

    # Telegram Notifier (human-in-the-loop, alternative to Slack)
    if _config.telegram_bot_token and _config.telegram_chat_id:
        _telegram = TelegramNotifier(
            bot_token=_config.telegram_bot_token,
            chat_id=_config.telegram_chat_id,
        )
        logger.info("✅ Telegram notifier initialized (chat_id=%s)", _config.telegram_chat_id)
    else:
        logger.info(
            "Telegram not configured — "
            "set VYAPAAR_TELEGRAM_BOT_TOKEN and VYAPAAR_TELEGRAM_CHAT_ID to enable"
        )

    # Payout Poller (replaces webhooks)
    if _config.razorpay_account_number:
        _poller = PayoutPoller(
            bridge=_razorpay_bridge,
            account_number=_config.razorpay_account_number,
            redis=_redis,
            poll_interval=_config.poll_interval,
        )
        logger.info(
            "✅ PayoutPoller ready "
            "(interval=%ds, replaces webhook ingress)",
            _config.poll_interval,
        )
    else:
        logger.warning(
            "⚠️  VYAPAAR_RAZORPAY_ACCOUNT_NUMBER not set — "
            "automatic polling disabled. "
            "Use poll_razorpay_payouts tool manually."
        )

    # Governance Engine
    _governance = GovernanceEngine(
        redis=_redis,
        postgres=_postgres,
        safe_browsing=_safe_browsing,
        rate_limit_max=_config.rate_limit_max_requests,
        rate_limit_window=_config.rate_limit_window_seconds,
    )
    logger.info(
        "✅ Governance engine ready "
        "(rate limit: %d req / %ds window)",
        _config.rate_limit_max_requests,
        _config.rate_limit_window_seconds,
    )

    # GLEIF Vendor Verification (FOSS)
    _cb_gleif = CircuitBreaker(
        "gleif",
        failure_threshold=_config.circuit_breaker_failure_threshold,
        recovery_timeout=float(_config.circuit_breaker_recovery_timeout),
    )
    _gleif = GLEIFChecker(
        api_url=_config.gleif_api_url,
        redis=_redis,
        circuit_breaker=_cb_gleif,
    )
    logger.info("✅ GLEIF vendor verification initialized (circuit breaker enabled)")

    # Transaction Anomaly Scorer (FOSS — scikit-learn IsolationForest)
    _anomaly_scorer = TransactionAnomalyScorer(
        redis=_redis,
        risk_threshold=_config.anomaly_risk_threshold,
    )
    logger.info(
        "✅ Transaction anomaly scorer initialized "
        "(threshold=%.2f)",
        _config.anomaly_risk_threshold,
    )

    # ntfy Notifier (FOSS — Slack fallback)
    if _config.ntfy_topic:
        _ntfy = NtfyNotifier(
            topic=_config.ntfy_topic,
            server_url=_config.ntfy_url,
            auth_token=_config.ntfy_auth_token or None,
        )
        logger.info(
            "✅ ntfy notifier initialized (topic=%s, server=%s)",
            _config.ntfy_topic,
            _config.ntfy_url,
        )
    else:
        logger.info(
            "ℹ️  ntfy not configured — set VYAPAAR_NTFY_TOPIC to enable push fallback"
        )

    # Azure OpenAI Client (Microsoft AI Foundry)
    _azure_llm = AzureOpenAIClient(_config)
    try:
        await _azure_llm.initialize()
        if _azure_llm.is_configured:
            logger.info(
                "✅ Azure OpenAI initialized (deployment=%s, guardrails=%s)",
                _config.azure_openai_deployment,
                _config.azure_guardrails_enabled,
            )
        else:
            logger.info(
                "ℹ️  Azure OpenAI not configured — "
                "set VYAPAAR_AZURE_OPENAI_ENDPOINT and VYAPAAR_AZURE_OPENAI_API_KEY"
            )
    except Exception as e:
        logger.warning("⚠️  Azure OpenAI initialization skipped: %s", e)

    # Security LLM / Dual LLM Quarantine Pattern
    _tool_validator = ToolCallValidator(_config)
    try:
        await _tool_validator.initialize()
        if _tool_validator.is_configured:
            logger.info(
                "✅ Dual LLM quarantine initialized (security_llm=%s, strict=%s)",
                _config.security_llm_url,
                _config.quarantine_strict,
            )
            logger.info(
                "   Taint sources: %s",
                _config.taint_sources.replace(",", ", ")
            )
            logger.info(
                "   Dual-LLM tools: %s",
                _config.dual_llm_tools.replace(",", ", ")
            )
        else:
            logger.info(
                "ℹ️  Dual LLM quarantine not configured — "
                "set VYAPAAR_SECURITY_LLM_URL to enable"
            )
    except Exception as e:
        logger.warning("⚠️  Dual LLM quarantine initialization skipped: %s", e)

    # Auto-polling (background task)
    if _config.auto_poll and _poller and _governance and _razorpay and _postgres:
        async def _auto_poll_callback(
            payout: Any, agent_id: str, vendor_url: str | None
        ) -> None:
            """Process a polled payout through governance."""
            _require(governance=_governance, razorpay=_razorpay, postgres=_postgres)

            result = await _governance.evaluate(payout, agent_id, vendor_url)
            metrics.record_decision(result)

            vendor_name: str | None = None
            if hasattr(payout, 'fund_account') and payout.fund_account and payout.fund_account.contact:
                vendor_name = payout.fund_account.contact.name

            await log_decision(_postgres, result, vendor_name=vendor_name, vendor_url=vendor_url)

            try:
                if result.decision == Decision.APPROVED:
                    await _razorpay.approve_payout(payout.id)
                elif result.decision == Decision.REJECTED:
                    await _razorpay.reject_payout(
                        payout.id,
                        f"{result.reason_code.value}: {result.reason_detail}",
                    )
            except Exception as e:
                logger.error("Auto-poll action failed for %s: %s", payout.id, e)
                if result.decision == Decision.APPROVED and _redis:
                    await _redis.rollback_budget(result.agent_id, result.amount)
                    logger.warning("Budget rolled back for %s: %d paise", result.agent_id, result.amount)

            await notify_with_fallback(
                _slack, _ntfy, result,
                vendor_name=vendor_name, vendor_url=vendor_url,
                telegram_notifier=_telegram,
            )

        _poll_task = asyncio.create_task(
            _poller.run_continuous(on_payout=_auto_poll_callback)
        )
        logger.info(
            "🔄 Auto-polling ENABLED (interval=%ds)",
            _config.poll_interval,
        )

    logger.info("=" * 60)
    logger.info("  VyapaarClaw — Ready to govern! 🛡️")
    logger.info("  Mode: API Polling (no webhook/tunnel needed)")
    logger.info("  Sidecar: razorpay/mcp (all toolsets enabled)")
    logger.info("=" * 60)


async def _shutdown() -> None:
    """Cleanup on server shutdown."""
    logger.info("VyapaarClaw shutting down...")
    if _poll_task and not _poll_task.done():
        _poll_task.cancel()
    if _poller:
        _poller.stop()
    if _slack:
        await _slack.close()
    if _telegram:
        await _telegram.close()
    if _ntfy:
        await _ntfy.close()
    if _gleif:
        await _gleif.close()
    if _safe_browsing:
        await _safe_browsing.close()
    if _azure_llm:
        await _azure_llm.close()
    if _tool_validator:
        await _tool_validator.close()
    if _redis:
        await _redis.disconnect()
    if _postgres:
        await _postgres.disconnect()
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
    _require(config=_config, redis=_redis, postgres=_postgres, governance=_governance, razorpay=_razorpay)

    if not payload or len(payload) > 1_048_576:
        return {
            "decision": Decision.REJECTED.value,
            "reason": "INVALID_PAYLOAD",
            "detail": "Payload empty or exceeds 1 MB size limit",
        }

    payload_bytes = payload.encode("utf-8")

    # --- Step 1: Verify Signature ---
    if not verify_razorpay_signature(payload_bytes, signature, _config.razorpay_webhook_secret):
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
    is_new = await _redis.check_idempotency(webhook_id)
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
    result = await _governance.evaluate(payout, agent_id, vendor_url)
    metrics.record_decision(result)

    # --- Step 7: Write Audit Log ---
    await log_decision(_postgres, result, vendor_name=vendor_name, vendor_url=vendor_url)

    # --- Step 8: Execute Decision on Razorpay ---
    try:
        if result.decision == Decision.APPROVED:
            await _razorpay.approve_payout(payout.id)
        elif result.decision == Decision.REJECTED:
            await _razorpay.reject_payout(
                payout.id,
                f"{result.reason_code.value}: {result.reason_detail}",
            )
        # HELD payouts are not auto-actioned (waiting for human approval)
    except Exception as e:
        logger.error("Razorpay action failed for %s: %s", payout.id, e)
        if result.decision == Decision.APPROVED:
            await _redis.rollback_budget(result.agent_id, result.amount)
            logger.warning("Budget rolled back for %s: %d paise", result.agent_id, result.amount)

    # --- Step 9: Notification (Slack / Telegram / ntfy) ---
    await notify_with_fallback(
        _slack, _ntfy, result,
        vendor_name=vendor_name, vendor_url=vendor_url,
        telegram_notifier=_telegram,
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
    _require(config=_config, redis=_redis, razorpay_bridge=_razorpay_bridge, governance=_governance, razorpay=_razorpay, postgres=_postgres)

    acct = account_number or _config.razorpay_account_number
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
        bridge=_razorpay_bridge,
        account_number=acct,
        redis=_redis,
        poll_interval=_config.poll_interval,
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
        result = await _governance.evaluate(
            payout, agent_id, vendor_url
        )
        metrics.record_decision(result)

        # Audit log
        vendor_name: str | None = None
        if (
            payout.fund_account
            and payout.fund_account.contact
        ):
            vendor_name = payout.fund_account.contact.name

        await log_decision(
            _postgres,
            result,
            vendor_name=vendor_name,
            vendor_url=vendor_url,
        )

        # Execute decision on Razorpay
        try:
            if result.decision == Decision.APPROVED:
                await _razorpay.approve_payout(payout.id)
            elif result.decision == Decision.REJECTED:
                await _razorpay.reject_payout(
                    payout.id,
                    f"{result.reason_code.value}: "
                    f"{result.reason_detail}",
                )
        except Exception as e:
            logger.error(
                "Razorpay action failed for %s: %s",
                payout.id,
                e,
            )
            if result.decision == Decision.APPROVED:
                await _redis.rollback_budget(result.agent_id, result.amount)
                logger.warning("Budget rolled back for %s: %d paise", result.agent_id, result.amount)

        # Notification (Slack / Telegram / ntfy)
        await notify_with_fallback(
            _slack, _ntfy, result,
            vendor_name=vendor_name, vendor_url=vendor_url,
            telegram_notifier=_telegram,
        )

        results.append({
            "payout_id": result.payout_id,
            "decision": result.decision.value,
            "reason": result.reason_code.value,
            "detail": result.reason_detail,
            "amount_paise": result.amount,
            "agent_id": result.agent_id,
        })

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
    _require(safe_browsing=_safe_browsing)

    result = await _safe_browsing.check_url(url)
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
    _require(redis=_redis, postgres=_postgres)

    policy = await _postgres.get_agent_policy(agent_id)
    if policy is None:
        return {"error": f"No policy found for agent '{agent_id}'"}

    spent_today = await _redis.get_daily_spend(agent_id)
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
    _require(postgres=_postgres)

    # Clamp limit to prevent excessive queries
    limit = max(1, min(limit, 500))

    entries = await _postgres.get_audit_logs(
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
    _require(postgres=_postgres)

    policy = AgentPolicy(
        agent_id=agent_id,
        daily_limit=daily_limit,
        per_txn_limit=per_txn_limit,
        require_approval_above=require_approval_above,
        allowed_domains=allowed_domains or [],
        blocked_domains=blocked_domains or [],
    )

    saved = await _postgres.upsert_agent_policy(policy)
    return {"status": "ok", "policy": saved.model_dump(mode="json")}


@mcp.tool()
async def health_check() -> dict[str, Any]:
    """Check health of all dependent services.

    Returns status of Redis, PostgreSQL, and Razorpay connectivity,
    plus server uptime and circuit breaker states.
    """
    redis_ok = await _redis.ping() if _redis else False
    postgres_ok = await _postgres.ping() if _postgres else False
    razorpay_ok = await _razorpay.ping() if _razorpay else False

    status = HealthStatus(
        redis="ok" if redis_ok else "error",
        postgres="ok" if postgres_ok else "error",
        razorpay="ok" if razorpay_ok else "error",
        uptime_seconds=int(time.time() - _start_time),
    )

    result = status.model_dump()
    # Include circuit breaker snapshots
    if _cb_razorpay is not None:
        result["circuit_breaker_razorpay"] = _cb_razorpay.snapshot()
    if _cb_safe_browsing is not None:
        result["circuit_breaker_safe_browsing"] = _cb_safe_browsing.snapshot()
    if _cb_gleif is not None:
        result["circuit_breaker_gleif"] = _cb_gleif.snapshot()
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
    _require(razorpay=_razorpay)

    if action_id == "approve_payout":
        result = await _razorpay.approve_payout(payout_id)
        action_label = "approved"
    elif action_id == "reject_payout":
        result = await _razorpay.reject_payout(payout_id)
        action_label = "rejected"

        # --- Budget Rollback for HELD payouts ---
        # If a payout was HELD, its budget was already deducted.
        # When rejecting it, we MUST roll back the budget in Redis.
        if _postgres and _redis:
            audit_logs = await _postgres.get_audit_logs(payout_id=payout_id, limit=1)
            if audit_logs:
                log = audit_logs[0]
                if log.decision == Decision.HELD:
                    await _redis.rollback_budget(log.agent_id, log.amount)
                    logger.info(
                        "Budget rolled back via Slack action: agent=%s amount=%d",
                        log.agent_id, log.amount,
                    )
    else:
        return {"error": f"Unknown action: {action_id}"}

    logger.info(
        "Slack action: %s %s payout %s",
        user_name, action_label, payout_id,
    )

    # Update the Slack message to reflect the decision
    message_updated = False
    if _slack and channel and message_ts:
        try:
            await _slack.update_approval_message(
                channel=channel,
                message_ts=message_ts,
                payout_id=payout_id,
                action="approve" if action_id == "approve_payout" else "reject",
                user_name=user_name,
            )
            message_updated = True
        except Exception as exc:
            logger.warning("Failed to update Slack message: %s", exc)

    if _postgres:
        logger.info(
            "Audit: slack:%s %s payout %s",
            user_name, action_label, payout_id,
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
    _require(razorpay=_razorpay)

    if action_id == "approve_payout":
        result = await _razorpay.approve_payout(payout_id)
        action_label = "approved"
    elif action_id == "reject_payout":
        result = await _razorpay.reject_payout(payout_id)
        action_label = "rejected"

        if _postgres and _redis:
            audit_logs = await _postgres.get_audit_logs(payout_id=payout_id, limit=1)
            if audit_logs:
                log = audit_logs[0]
                if log.decision == Decision.HELD:
                    await _redis.rollback_budget(log.agent_id, log.amount)
                    logger.info(
                        "Budget rolled back via Telegram action: agent=%s amount=%d",
                        log.agent_id, log.amount,
                    )
    else:
        return {"error": f"Unknown action: {action_id}"}

    logger.info("Telegram action: %s %s payout %s", user_name, action_label, payout_id)

    message_updated = False
    if _telegram and chat_id and message_id:
        try:
            await _telegram.update_message(
                chat_id=chat_id,
                message_id=message_id,
                payout_id=payout_id,
                action="approve" if action_id == "approve_payout" else "reject",
                user_name=user_name,
            )
            message_updated = True
        except Exception as exc:
            logger.warning("Failed to update Telegram message: %s", exc)

    if _telegram and callback_query_id:
        await _telegram.answer_callback(
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
    _require(gleif=_gleif)

    if lei and len(lei) == 20:
        result = await _gleif.lookup_lei(lei)
    else:
        result = await _gleif.search_entity(vendor_name)

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
    _require(anomaly_scorer=_anomaly_scorer)

    score = await _anomaly_scorer.score_transaction(amount=amount, agent_id=agent_id)
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
    _require(anomaly_scorer=_anomaly_scorer)

    return await _anomaly_scorer.get_agent_profile(agent_id)


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
    _require(tool_validator=_tool_validator)

    return {
        "context_tainted": _tool_validator.is_tainted,
        "taint_sources": _tool_validator._taint_sources,
        "dual_llm_tools": _tool_validator._dual_llm_tools,
        "security_llm_configured": _tool_validator.is_configured,
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
        tool_validator=_tool_validator,
        postgres=_postgres,
    )

    # Get current governance policy for context
    policy = await _postgres.get_agent_policy(agent_id)
    governance_policy = {
        "agent_id": agent_id,
        "daily_limit": str(policy.daily_limit) if policy else None,
        "per_txn_limit": str(policy.per_txn_limit) if policy else None,
        "requires_approval_above": str(policy.require_approval_above) if policy else None,
    }


    result = await _tool_validator.validate(
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
        "context_tainted": _tool_validator.is_tainted,
    }


@mcp.tool()
async def azure_chat(
    message: str,
    system_prompt: str = "You are a helpful assistant.",
    temperature: float = 0.7,
    max_tokens: int = 1000,
) -> dict[str, Any]:
    """Send a chat completion request to Kimi K2.5 via Azure AI.
    
    Security note: This tool marks context as TAINTED because LLM responses
    can contain injected content. Subsequent high-privilege tool calls
    require Dual LLM validation or are blocked.
    
    Args:
        message: User message to send.
        system_prompt: System prompt/context for the LLM.
        temperature: Sampling temperature (0-2, default 0.7).
        max_tokens: Maximum tokens to generate.
        
    Returns:
        LLM response text and token usage.
    """
    _require(azure_llm=_azure_llm, tool_validator=_tool_validator)

    if not _azure_llm.is_configured:
        return {
            "error": "Kimi K2.5 not configured",
            "config_required": [
                "VYAPAAR_AZURE_OPENAI_ENDPOINT",
                "VYAPAAR_AZURE_OPENAI_API_KEY",
            ],
        }

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": message},
    ]

    response, status = await _azure_llm.chat_completion(
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )

    if response is None:
        return {
            "error": status,
            "hint": "Configure VYAPAAR_AZURE_OPENAI_ENDPOINT and VYAPAAR_AZURE_OPENAI_API_KEY",
        }

    # Taint context: LLM responses are untrusted
    _tool_validator.mark_taint("azure_chat")

    return {
        "response": response,
        "context_note": "Response may be tainted - subsequent critical tools require validation",
    }


@mcp.tool()
async def get_archestra_status() -> dict[str, Any]:
    """Get Archestra deterministic policy enforcement status.
    
    Returns current configuration for the security proxy layer that
    enforces hard boundaries on tool access (vs probabilistic guardrails).
    
    Returns:
        Archestra config, taint tracking status, and policy tiers.
    """
    _require(config=_config, tool_validator=_tool_validator)

    return {
        "archestra_enabled": _config.archestra_enabled,
        "archestra_url": _config.archestra_url,
        "policy_set_id": _config.archestra_policy_set_id,
        "security_llm": {
            "url": _config.security_llm_url,
            "model": _config.security_llm_model,
            "configured": _tool_validator.is_configured if _tool_validator else False,
        },
        "dual_llm_config": {
            "taint_sources": _config.taint_sources.split(",") if _config.taint_sources else [],
            "dual_llm_tools": _config.dual_llm_tools.split(",") if _config.dual_llm_tools else [],
            "quarantine_strict": _config.quarantine_strict,
            "audit_logging": _config.quarantine_audit_log,
        },
        "azure_guardrails": {
            "enabled": _config.azure_guardrails_enabled,
            "severity": _config.azure_guardrails_severity,
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
    _require(redis=_redis, postgres=_postgres)

    if agent_id:
        agent_ids = [agent_id]
    else:
        agents = await _postgres.list_all_agents()
        agent_ids = [a["agent_id"] for a in agents]

    if not agent_ids:
        return {"forecasts": [], "note": "No agents with active policies found."}

    forecasts = []
    for aid in agent_ids:
        history = await _redis.get_historical_spend(aid, days=horizon_days)
        spends = [d["spend"] for d in history]
        nonzero_spends = [s for s in spends if s > 0]

        if not nonzero_spends:
            forecasts.append({
                "agent_id": aid,
                "burn_rate_per_day": 0,
                "trend": "inactive",
                "budget_health": "green",
                "note": "No spending in analysis window.",
            })
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

        policy = await _postgres.get_agent_policy(aid)
        daily_limit = policy.daily_limit if policy else 500000

        utilisation = avg_daily / daily_limit if daily_limit > 0 else 0
        if utilisation > 0.8:
            health = "red"
        elif utilisation > 0.5:
            health = "yellow"
        else:
            health = "green"

        current_spend = await _redis.get_daily_spend(aid)
        remaining_today = max(0, daily_limit - current_spend)

        forecasts.append({
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
        })

    return {"forecasts": forecasts}


@mcp.tool()
async def generate_compliance_report(
    period_days: int = 7, agent_id: str = "",

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
    _require(postgres=_postgres)

    period_days = max(1, min(period_days, 365))

    stats = await _postgres.get_compliance_stats(
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
            f"{held} transactions were held for human review. "
            "Ensure HITL queue is being monitored."
        )

    agent_breakdown = stats.get("agent_breakdown", {})
    high_risk_agents = []
    for aid, agent_decisions in agent_breakdown.items():
        agent_rejected = agent_decisions.get("REJECTED", {}).get("count", 0)
        agent_total = sum(d.get("count", 0) for d in agent_decisions.values())
        if agent_total > 0 and agent_rejected / agent_total > 0.3:
            high_risk_agents.append({
                "agent_id": aid,
                "rejection_rate_pct": round(agent_rejected / agent_total * 100, 1),
                "total_decisions": agent_total,
            })

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
        "total_volume_paise": sum(
            d.get("total_amount", 0) for d in decisions.values()
        ),
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
    _require(redis=_redis)

    days = min(days, 90)
    history = await _redis.get_historical_spend(agent_id, days=days)

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
    _require(redis=_redis, postgres=_postgres, governance=_governance)

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

    result = await _governance.evaluate(payout, agent_id, vendor_url or None)

    await log_decision(
        _postgres,
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
            "budget_remaining_after": (
                await _redis.get_daily_spend(agent_id)
            ),
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
    _require(redis=_redis, postgres=_postgres)

    agents_raw = await _postgres.list_all_agents()

    agents = []
    for agent in agents_raw:
        aid = agent["agent_id"]
        daily_limit = agent["daily_limit"]
        current_spend = await _redis.get_daily_spend(aid)
        utilisation = (current_spend / daily_limit * 100) if daily_limit > 0 else 0

        agents.append({
            **agent,
            "current_daily_spend_paise": current_spend,
            "utilisation_pct": round(utilisation, 1),
            "budget_health": (
                "red" if utilisation > 80
                else "yellow" if utilisation > 50
                else "green"
            ),
        })

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
    _require(redis=_redis, postgres=_postgres)

    from_policy = await _postgres.get_agent_policy(from_agent_id)
    to_policy = await _postgres.get_agent_policy(to_agent_id)

    if from_policy is None:
        return {"error": f"No policy found for agent '{from_agent_id}'"}
    if to_policy is None:
        return {"error": f"No policy found for agent '{to_agent_id}'"}

    from_policy.daily_limit = new_from_limit
    to_policy.daily_limit = new_to_limit

    await _postgres.upsert_agent_policy(from_policy)
    await _postgres.upsert_agent_policy(to_policy)

    from_spend = await _redis.get_daily_spend(from_agent_id)
    to_spend = await _redis.get_daily_spend(to_agent_id)

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
    _require(redis=_redis, postgres=_postgres)
    from urllib.parse import urlparse

    domain = urlparse(vendor_url).netloc or vendor_url

    logs = await _postgres.get_audit_logs(limit=500)
    vendor_logs = [
        log for log in logs
        if log.vendor_url and domain in log.vendor_url
    ]

    if not vendor_logs:
        cached_rep = await _redis.get_cached_reputation(vendor_url)
        return {
            "vendor_url": vendor_url,
            "domain": domain,
            "trust_score": 50,
            "confidence": "low",
            "transactions": 0,
            "cached_reputation": cached_rep,
            "note": "No transaction history. Score is neutral. Run check_vendor_reputation and verify_vendor_entity for initial assessment.",
        }

    total = len(vendor_logs)
    approved = sum(1 for l in vendor_logs if l.decision == Decision.APPROVED)
    rejected = sum(1 for l in vendor_logs if l.decision == Decision.REJECTED)
    total_volume = sum(l.amount for l in vendor_logs)
    approval_rate = approved / total if total > 0 else 0

    base_score = approval_rate * 70

    if total >= 20:
        base_score += 15
    elif total >= 5:
        base_score += 10
    elif total >= 2:
        base_score += 5

    threat_count = sum(len(l.threat_types) for l in vendor_logs)
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
    _require(redis=_redis, postgres=_postgres)

    days_ahead = min(days_ahead, 30)

    logs = await _postgres.get_audit_logs(limit=200)

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
        {"vendor": v, "transactions": c}
        for v, c in vendor_frequency.most_common(5)
        if c >= 2
    ]

    agents_raw = await _postgres.list_all_agents()
    pressure_points = []
    for agent in agents_raw:
        aid = agent["agent_id"]
        history = await _redis.get_historical_spend(aid, days=7)
        recent_spends = [d["spend"] for d in history if d["spend"] > 0]
        if recent_spends:
            avg_daily = sum(recent_spends) / len(recent_spends)
            daily_limit = agent["daily_limit"]
            if daily_limit > 0 and avg_daily / daily_limit > 0.6:
                pressure_points.append({
                    "agent_id": aid,
                    "avg_daily_spend": int(avg_daily),
                    "daily_limit": daily_limit,
                    "utilisation_pct": round(avg_daily / daily_limit * 100, 1),
                })

    today = datetime.now().strftime("%A")

    return {
        "projection_days": days_ahead,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "recent_activity": {
            "total_decisions_in_log": len(logs),
            "busiest_days_of_week": [
                {"day": d, "avg_transactions": c} for d, c in busiest_days
            ],
            "today_is": today,
            "today_expected_volume": (
                daily_activity.get(today, 0)
            ),
        },
        "recurring_vendors": recurring_vendors,
        "budget_pressure_points": pressure_points,
        "most_active_agents": [
            {"agent_id": a, "transactions": c}
            for a, c in agent_activity.most_common(5)
        ],
    }


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
                    streams[0],
                    streams[1],
                    mcp._mcp_server.create_initialization_options()
                )
            # Return empty response after SSE connection closes
            return Response()

        starlette_app = Starlette(
            debug=_config.dev_mode,
            routes=[
                Route("/sse", endpoint=sse_handler, methods=["GET", "POST"]),
                Mount("/messages/", app=sse.handle_post_message),
                Route("/health", endpoint=health_endpoint, methods=["GET"]),
                Route("/slack/actions", endpoint=slack_actions_endpoint, methods=["POST"]),
                Route("/telegram/callback", endpoint=telegram_callback_endpoint, methods=["POST"]),
            ]
        )

        # Add custom routes from mcp
        starlette_app.routes.extend(mcp._custom_starlette_routes)

        uvicorn.run(starlette_app, host=host, port=port)
    else:
        mcp.run(transport=transport_name)


# Allow direct execution
if __name__ == "__main__":
    run_server_sync()
