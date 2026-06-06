"""Focused tests for Razorpay payout polling stability."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from vyapaar_mcp.ingress import polling
from vyapaar_mcp.ingress.polling import PayoutPoller


def _raw_payout(payout_id: str = "pout_test_001") -> dict[str, Any]:
    return {
        "id": payout_id,
        "entity": "payout",
        "amount": 12500,
        "currency": "INR",
        "status": "queued",
        "notes": {
            "agent_id": "agent-001",
            "vendor_url": "https://vendor.example",
        },
    }


class FakeBridge:
    def __init__(
        self,
        items: list[Any] | None = None,
        error: BaseException | None = None,
    ) -> None:
        self.items = items or []
        self.error = error

    async def fetch_all_payouts(self, **kwargs: Any) -> dict[str, Any]:
        if self.error:
            raise self.error
        return {"items": self.items, "count": len(self.items)}


class FakeRedis:
    def __init__(self) -> None:
        self.keys: list[str] = []

    async def check_idempotency(self, key: str) -> bool:
        self.keys.append(key)
        return True


@pytest.mark.asyncio
async def test_poll_once_returns_empty_on_runtime_fetch_error() -> None:
    poller = PayoutPoller(
        bridge=FakeBridge(error=RuntimeError("api down")),  # type: ignore[arg-type]
        account_number="acc_1234",
        redis=FakeRedis(),  # type: ignore[arg-type]
    )

    result = await poller.poll_once()

    assert result == []
    assert poller.stats["error_count"] == 1


@pytest.mark.asyncio
async def test_poll_once_does_not_swallow_cancellation() -> None:
    poller = PayoutPoller(
        bridge=FakeBridge(error=asyncio.CancelledError()),  # type: ignore[arg-type]
        account_number="acc_1234",
        redis=FakeRedis(),  # type: ignore[arg-type]
    )

    with pytest.raises(asyncio.CancelledError):
        await poller.poll_once()


@pytest.mark.asyncio
async def test_poll_once_skips_malformed_payout_record() -> None:
    redis = FakeRedis()
    poller = PayoutPoller(
        bridge=FakeBridge(
            items=[
                {"id": "pout_bad", "status": "queued"},
                _raw_payout("pout_good"),
            ]
        ),  # type: ignore[arg-type]
        account_number="acc_1234",
        redis=redis,  # type: ignore[arg-type]
    )

    result = await poller.poll_once()

    assert len(result) == 1
    payout, agent_id, vendor_url = result[0]
    assert payout.id == "pout_good"
    assert agent_id == "agent-001"
    assert vendor_url == "https://vendor.example"
    assert redis.keys == ["poll:payout.queued:pout_bad", "poll:payout.queued:pout_good"]
    assert poller.stats["total_processed"] == 1


@pytest.mark.asyncio
async def test_run_continuous_catches_callback_value_error(monkeypatch: pytest.MonkeyPatch) -> None:
    poller = PayoutPoller(
        bridge=FakeBridge(items=[_raw_payout()]),  # type: ignore[arg-type]
        account_number="acc_1234",
        redis=FakeRedis(),  # type: ignore[arg-type]
    )
    callback_calls = 0

    async def callback(*args: Any) -> None:
        nonlocal callback_calls
        callback_calls += 1
        raise ValueError("bad callback payload")

    async def stop_after_sleep(interval: float) -> None:
        poller.stop()

    monkeypatch.setattr(polling.asyncio, "sleep", stop_after_sleep)

    await poller.run_continuous(on_payout=callback)

    assert callback_calls == 1
