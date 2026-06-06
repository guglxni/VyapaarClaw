"""Shared support helpers for the VyapaarClaw MCP server."""

from __future__ import annotations

from typing import Any

import asyncpg
import httpx
import razorpay
import redis

SERVICE_CONNECT_ERRORS = (
    asyncpg.PostgresError,
    redis.exceptions.RedisError,
    RuntimeError,
    ConnectionError,
    TimeoutError,
    OSError,
)
RAZORPAY_ACTION_ERRORS = (
    httpx.HTTPError,
    razorpay.errors.BadRequestError,
    razorpay.errors.GatewayError,
    razorpay.errors.ServerError,
    RuntimeError,
    ConnectionError,
    TimeoutError,
    OSError,
)
NOTIFICATION_UPDATE_ERRORS = (
    httpx.HTTPError,
    RuntimeError,
    ConnectionError,
    TimeoutError,
    OSError,
)
AUDIT_READ_ERRORS = (
    asyncpg.PostgresError,
    RuntimeError,
    ConnectionError,
    TimeoutError,
    AttributeError,
)


def require_services(**services: Any) -> None:
    """Validate that required server components are initialized."""
    missing = [name for name, obj in services.items() if obj is None]
    if missing:
        raise RuntimeError(
            f"Server not initialised — missing: {', '.join(missing)}. "
            "Ensure startup() completed successfully."
        )
