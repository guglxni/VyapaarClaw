"""Focused tests for Razorpay action retry exception handling."""

from __future__ import annotations

import json
from typing import Any

import pytest

from vyapaar_mcp.egress import razorpay_actions
from vyapaar_mcp.egress.razorpay_actions import RazorpayActions


@pytest.mark.asyncio
async def test_retry_retries_json_decode_error(monkeypatch: pytest.MonkeyPatch) -> None:
    actions = RazorpayActions(key_id="rzp_test_key", key_secret="secret")
    attempts = 0

    async def no_sleep(delay: float) -> None:
        return None

    def flaky_decode() -> dict[str, Any]:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise json.JSONDecodeError("invalid", "not-json", 0)
        return {"ok": True}

    monkeypatch.setattr(razorpay_actions.asyncio, "sleep", no_sleep)

    result = await actions._retry_with_backoff("decode_test", flaky_decode)

    assert result == {"ok": True}
    assert attempts == 3


@pytest.mark.asyncio
async def test_retry_does_not_swallow_unrelated_value_error() -> None:
    actions = RazorpayActions(key_id="rzp_test_key", key_secret="secret")

    def invalid_operation() -> dict[str, Any]:
        raise ValueError("programming error")

    with pytest.raises(ValueError, match="programming error"):
        await actions._retry_with_backoff("value_error_test", invalid_operation)
