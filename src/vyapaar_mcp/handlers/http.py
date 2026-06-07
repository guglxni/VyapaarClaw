"""HTTP endpoints for the VyapaarClaw MCP server."""

from __future__ import annotations

import json
import time
from collections.abc import Awaitable, Callable
from typing import Any
from urllib.parse import parse_qs

from starlette.requests import Request
from starlette.responses import JSONResponse

from vyapaar_mcp.egress.slack_notifier import verify_slack_signature

JsonDict = dict[str, Any]


def make_health_endpoint(
    get_redis: Callable[[], Any],
    get_postgres: Callable[[], Any],
    get_start_time: Callable[[], float],
) -> Callable[[Request], Awaitable[JSONResponse]]:
    """Create the HTTP health endpoint bound to server state accessors."""

    async def health_endpoint(request: Request) -> JSONResponse:
        """HTTP Health Check for monitoring, load balancers, and web UI."""
        redis = get_redis()
        postgres = get_postgres()
        redis_ok = await redis.ping() if redis else False
        postgres_ok = await postgres.ping() if postgres else False
        return JSONResponse(
            {
                "status": "ok" if (redis_ok and postgres_ok) else "degraded",
                "service": "vyapaarclaw",
                "version": "0.1.0",
                "uptime_seconds": int(time.time() - get_start_time()),
                "redis": "ok" if redis_ok else "error",
                "postgres": "ok" if postgres_ok else "error",
            }
        )

    health_endpoint.__name__ = "health_endpoint"
    return health_endpoint


def make_slack_actions_endpoint(
    get_config: Callable[[], Any],
    get_razorpay: Callable[[], Any],
    require_services: Callable[..., None],
    handle_slack_action: Callable[..., Awaitable[JsonDict]],
) -> Callable[[Request], Awaitable[JSONResponse]]:
    """Create the Slack interactive callback endpoint."""

    async def slack_actions_endpoint(request: Request) -> JSONResponse:
        """Receive Slack interactive component callbacks."""
        body_bytes = await request.body()
        body_str = body_bytes.decode("utf-8")

        config = get_config()
        if config and config.slack_signing_secret:
            timestamp = request.headers.get("X-Slack-Request-Timestamp", "")
            signature = request.headers.get("X-Slack-Signature", "")
            if not verify_slack_signature(
                body_str,
                timestamp,
                signature,
                config.slack_signing_secret,
            ):
                return JSONResponse({"error": "invalid signature"}, status_code=401)

        parsed = parse_qs(body_str)
        raw_payload = parsed.get("payload", [""])[0]
        if not raw_payload:
            return JSONResponse({"error": "missing payload"}, status_code=400)

        try:
            payload = json.loads(raw_payload)
        except json.JSONDecodeError:
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

        require_services(razorpay=get_razorpay())

        result = await handle_slack_action(
            action_id=action_id,
            payout_id=payout_id,
            user_name=user_name,
            channel=channel,
            message_ts=message_ts,
        )

        return JSONResponse(result)

    slack_actions_endpoint.__name__ = "slack_actions_endpoint"
    return slack_actions_endpoint


def make_telegram_callback_endpoint(
    get_razorpay: Callable[[], Any],
    require_services: Callable[..., None],
    handle_telegram_action: Callable[..., Awaitable[JsonDict]],
) -> Callable[[Request], Awaitable[JSONResponse]]:
    """Create the Telegram Bot API callback endpoint."""

    async def telegram_callback_endpoint(request: Request) -> JSONResponse:
        """Receive Telegram Bot API webhook updates."""
        try:
            update = await request.json()
        except (json.JSONDecodeError, UnicodeDecodeError):
            return JSONResponse({"error": "invalid JSON"}, status_code=400)

        callback_query = update.get("callback_query")
        if not callback_query:
            return JSONResponse({"ok": True})

        try:
            data = json.loads(callback_query.get("data", "{}"))
        except (json.JSONDecodeError, TypeError):
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

        require_services(razorpay=get_razorpay())

        result = await handle_telegram_action(
            action_id=action_id,
            payout_id=payout_id,
            user_name=user_name,
            chat_id=chat_id,
            message_id=message_id,
            callback_query_id=callback_query_id,
        )

        return JSONResponse(result)

    telegram_callback_endpoint.__name__ = "telegram_callback_endpoint"
    return telegram_callback_endpoint


def make_dashboard_endpoint(
    get_postgres: Callable[[], Any],
    get_redis: Callable[[], Any],
) -> Callable[[Request], Awaitable[JSONResponse]]:
    """Combined dashboard data for web UI."""

    async def dashboard_endpoint(request: Request) -> JSONResponse:
        postgres = get_postgres()
        redis = get_redis()
        if not postgres:
            return JSONResponse({"error": "postgres unavailable"}, status_code=503)

        try:
            redis_get = redis.get_daily_spend if redis else None
            agents = await postgres.get_dashboard_agents_with_spend(redis_get)
            compliance = await postgres.get_compliance_stats(period_days=7)
            logs = await postgres.get_audit_logs(limit=20)
            recent = [
                {
                    "payout_id": log.payout_id,
                    "agent_id": log.agent_id,
                    "amount": log.amount,
                    "decision": log.decision.value,
                    "reason_code": log.reason_code.value,
                    "reason_detail": log.reason_detail,
                    "vendor_name": log.vendor_name,
                    "created_at": log.created_at.isoformat() if log.created_at else None,
                }
                for log in logs
            ]
            high_risk = []
            for aid, breakdown in compliance.get("agent_breakdown", {}).items():
                total = sum(d.get("count", 0) for d in breakdown.values())
                rejected = breakdown.get("REJECTED", {}).get("count", 0)
                if total > 0 and rejected / total > 0.2:
                    high_risk.append(
                        {
                            "agent_id": aid,
                            "rejection_rate_pct": round(rejected / total * 100, 1),
                            "total_decisions": total,
                        }
                    )

            return JSONResponse(
                {
                    "agents": agents,
                    "compliance": {
                        "total_decisions": compliance.get("total_decisions", 0),
                        "decisions": compliance.get("decisions", {}),
                        "top_rejection_reasons": compliance.get("top_rejection_reasons", []),
                        "high_risk_agents": high_risk,
                    },
                    "recent_decisions": recent,
                    "mcp_connected": True,
                }
            )
        except Exception as exc:
            return JSONResponse({"error": str(exc)}, status_code=500)

    dashboard_endpoint.__name__ = "dashboard_endpoint"
    return dashboard_endpoint


def make_agents_endpoint(
    get_postgres: Callable[[], Any],
    get_redis: Callable[[], Any],
) -> Callable[[Request], Awaitable[JSONResponse]]:
    """Agent list with budget utilisation."""

    async def agents_endpoint(request: Request) -> JSONResponse:
        postgres = get_postgres()
        redis = get_redis()
        if not postgres:
            return JSONResponse({"error": "postgres unavailable"}, status_code=503)
        redis_get = redis.get_daily_spend if redis else None
        agents = await postgres.get_dashboard_agents_with_spend(redis_get)
        return JSONResponse({"agents": agents})

    agents_endpoint.__name__ = "agents_endpoint"
    return agents_endpoint


def make_audit_endpoint(
    get_postgres: Callable[[], Any],
) -> Callable[[Request], Awaitable[JSONResponse]]:
    """Recent audit log entries."""

    async def audit_endpoint(request: Request) -> JSONResponse:
        postgres = get_postgres()
        if not postgres:
            return JSONResponse({"error": "postgres unavailable"}, status_code=503)
        limit = int(request.query_params.get("limit", "50"))
        agent_id = request.query_params.get("agent_id") or None
        logs = await postgres.get_audit_logs(agent_id=agent_id, limit=limit)
        return JSONResponse(
            {
                "entries": [
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
                        "created_at": log.created_at.isoformat() if log.created_at else None,
                    }
                    for log in logs
                ],
            }
        )

    audit_endpoint.__name__ = "audit_endpoint"
    return audit_endpoint
