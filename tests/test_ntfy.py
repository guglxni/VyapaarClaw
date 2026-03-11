"""Tests for ntfy push notification fallback.

Uses httpx.MockTransport to exercise the real httpx client stack.
"""

from __future__ import annotations

import json

import httpx
import pytest

from vyapaar_mcp.egress.ntfy_notifier import (
    PRIORITY_HIGH,
    NtfyNotifier,
    notify_with_fallback,
)
from vyapaar_mcp.egress.slack_notifier import SlackNotifier
from vyapaar_mcp.models import Decision, GovernanceResult, ReasonCode
from vyapaar_mcp.resilience import CircuitBreaker

# ================================================================
# Helpers
# ================================================================


def make_result(
    decision: Decision = Decision.REJECTED,
    reason_code: ReasonCode = ReasonCode.RISK_HIGH,
    amount: int = 50000,
) -> GovernanceResult:
    """Create a test governance result."""
    return GovernanceResult(
        decision=decision,
        reason_code=reason_code,
        reason_detail="Test reason",
        payout_id="pout_test_123",
        agent_id="test-agent-001",
        amount=amount,
        threat_types=["MALWARE"] if reason_code == ReasonCode.RISK_HIGH else [],
        processing_ms=42,
    )


def _make_ntfy(handler, **kwargs) -> NtfyNotifier:
    """Create a real NtfyNotifier wired to a MockTransport handler."""
    notifier = NtfyNotifier(**kwargs) if kwargs else NtfyNotifier(topic="test")
    notifier._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return notifier


def _make_slack(handler) -> SlackNotifier:
    """Create a real SlackNotifier wired to a MockTransport handler."""
    notifier = SlackNotifier(bot_token="xoxb-test", channel_id="C123")
    notifier._http = httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url="https://slack.com/api",
    )
    return notifier


def _ok_ntfy_handler(log: list[httpx.Request]):
    """Return an ntfy handler that logs requests and returns 200."""

    def handler(request: httpx.Request) -> httpx.Response:
        log.append(request)
        return httpx.Response(200, json={"id": "abc123"})

    return handler


def _ok_slack_handler(log: list[httpx.Request]):
    """Return a Slack handler that logs requests and returns ok."""

    def handler(request: httpx.Request) -> httpx.Response:
        log.append(request)
        return httpx.Response(200, json={"ok": True, "ts": "123.456"})

    return handler


# ================================================================
# NtfyNotifier Tests
# ================================================================


@pytest.mark.asyncio
class TestNtfyNotifier:
    """Test NtfyNotifier send functionality."""

    async def test_send_basic_notification(self) -> None:
        """Test successful basic notification send."""
        requests_made: list[httpx.Request] = []

        notifier = _make_ntfy(_ok_ntfy_handler(requests_made), topic="vyapaar-test")

        result = await notifier.send(
            message="Test notification",
            title="Test Title",
            priority=PRIORITY_HIGH,
            tags=["warning"],
        )

        assert result is True
        assert len(requests_made) == 1
        payload = json.loads(requests_made[0].content)
        assert payload["topic"] == "vyapaar-test"
        assert payload["message"] == "Test notification"
        assert payload["title"] == "Test Title"
        assert payload["priority"] == PRIORITY_HIGH
        assert payload["tags"] == ["warning"]
        await notifier.close()

    async def test_send_to_root_url(self) -> None:
        """Verify POST goes to root URL, not topic URL (per ntfy API spec)."""
        requests_made: list[httpx.Request] = []

        notifier = _make_ntfy(
            _ok_ntfy_handler(requests_made),
            topic="test-topic",
            server_url="https://ntfy.example.com",
        )

        await notifier.send(message="Hello")

        assert len(requests_made) == 1
        assert str(requests_made[0].url) == "https://ntfy.example.com/"
        await notifier.close()

    async def test_send_failure_returns_false(self) -> None:
        """Test that HTTP errors return False."""

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(500, text="Internal Server Error")

        notifier = _make_ntfy(handler, topic="test-topic")

        result = await notifier.send(message="This will fail")
        assert result is False
        await notifier.close()

    async def test_send_circuit_open_returns_false(self) -> None:
        """Test circuit breaker open = notification dropped."""
        call_count = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            raise httpx.ConnectError("connection refused")

        cb = CircuitBreaker("ntfy", failure_threshold=1, recovery_timeout=300)
        notifier = NtfyNotifier(topic="test-topic", circuit_breaker=cb)
        notifier._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))

        result1 = await notifier.send(message="Trip the circuit")
        assert result1 is False
        assert call_count == 1

        result2 = await notifier.send(message="Dropped notification")
        assert result2 is False
        assert call_count == 1  # transport never called — circuit is OPEN
        await notifier.close()

    async def test_send_governance_held(self) -> None:
        """Test governance HELD notification format."""
        requests_made: list[httpx.Request] = []

        notifier = _make_ntfy(_ok_ntfy_handler(requests_made), topic="vyapaar-alerts")

        result_obj = make_result(
            decision=Decision.HELD,
            reason_code=ReasonCode.APPROVAL_REQUIRED,
            amount=75000,
        )
        sent = await notifier.send_governance_notification(
            result_obj,
            vendor_name="Test Vendor Pvt Ltd",
        )

        assert sent is True
        assert len(requests_made) == 1
        payload = json.loads(requests_made[0].content)
        assert "Approval Required" in payload["title"]
        assert "75,000" in payload["message"] or "750" in payload["message"]
        await notifier.close()

    async def test_send_governance_rejected(self) -> None:
        """Test governance REJECTED notification includes threat info."""
        requests_made: list[httpx.Request] = []

        notifier = _make_ntfy(_ok_ntfy_handler(requests_made), topic="vyapaar-alerts")

        result_obj = make_result(
            decision=Decision.REJECTED,
            reason_code=ReasonCode.RISK_HIGH,
        )
        sent = await notifier.send_governance_notification(result_obj)

        assert sent is True
        assert len(requests_made) == 1
        payload = json.loads(requests_made[0].content)
        assert "Rejected" in payload["title"]
        assert "MALWARE" in payload["message"]
        await notifier.close()

    async def test_send_governance_approved_is_silent(self) -> None:
        """APPROVED notifications should be silent (return True without sending)."""
        requests_made: list[httpx.Request] = []

        notifier = _make_ntfy(_ok_ntfy_handler(requests_made), topic="test")

        result_obj = make_result(decision=Decision.APPROVED, reason_code=ReasonCode.POLICY_OK)
        sent = await notifier.send_governance_notification(result_obj)

        assert sent is True
        assert len(requests_made) == 0
        await notifier.close()

    async def test_ping_success(self) -> None:
        """Test ping returns True on healthy server."""

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"healthy": True})

        notifier = _make_ntfy(handler, topic="test")
        assert await notifier.ping() is True
        await notifier.close()

    async def test_ping_failure(self) -> None:
        """Test ping returns False on unreachable server."""

        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("refused")

        notifier = _make_ntfy(handler, topic="test")
        assert await notifier.ping() is False
        await notifier.close()

    async def test_auth_token_in_headers(self) -> None:
        """Test that auth token is set in HTTP client headers."""
        notifier = NtfyNotifier(topic="test", auth_token="tk_my_secret_token")
        assert notifier._auth_token == "tk_my_secret_token"
        await notifier.close()


# ================================================================
# notify_with_fallback Tests
# ================================================================


@pytest.mark.asyncio
class TestNotifyWithFallback:
    """Test the Slack -> ntfy fallback notification routing."""

    async def test_slack_success_no_ntfy(self) -> None:
        """When Slack succeeds, ntfy should NOT be called."""
        slack_reqs: list[httpx.Request] = []
        ntfy_reqs: list[httpx.Request] = []

        slack = _make_slack(_ok_slack_handler(slack_reqs))
        ntfy = _make_ntfy(_ok_ntfy_handler(ntfy_reqs), topic="test")

        result = make_result(decision=Decision.HELD, reason_code=ReasonCode.APPROVAL_REQUIRED)
        await notify_with_fallback(slack, ntfy, result)

        assert len(slack_reqs) == 1
        assert len(ntfy_reqs) == 0
        await slack.close()
        await ntfy.close()

    async def test_slack_fails_ntfy_fallback(self) -> None:
        """When Slack fails, ntfy should be called as fallback."""
        ntfy_reqs: list[httpx.Request] = []

        def failing_slack_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"ok": False, "error": "channel_not_found"})

        slack = _make_slack(failing_slack_handler)
        ntfy = _make_ntfy(_ok_ntfy_handler(ntfy_reqs), topic="test")

        result = make_result(decision=Decision.HELD, reason_code=ReasonCode.APPROVAL_REQUIRED)
        await notify_with_fallback(slack, ntfy, result)

        assert len(ntfy_reqs) == 1
        await slack.close()
        await ntfy.close()

    async def test_slack_exception_ntfy_fallback(self) -> None:
        """When Slack raises an exception, ntfy should be called."""
        ntfy_reqs: list[httpx.Request] = []

        def error_slack_handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("Slack error")

        slack = _make_slack(error_slack_handler)
        ntfy = _make_ntfy(_ok_ntfy_handler(ntfy_reqs), topic="test")

        result = make_result(decision=Decision.REJECTED, reason_code=ReasonCode.RISK_HIGH)
        await notify_with_fallback(slack, ntfy, result)

        assert len(ntfy_reqs) == 1
        await slack.close()
        await ntfy.close()

    async def test_no_slack_ntfy_only(self) -> None:
        """When Slack is None, ntfy should be used directly."""
        ntfy_reqs: list[httpx.Request] = []

        ntfy = _make_ntfy(_ok_ntfy_handler(ntfy_reqs), topic="test")

        result = make_result(decision=Decision.REJECTED, reason_code=ReasonCode.DOMAIN_BLOCKED)
        await notify_with_fallback(None, ntfy, result)

        assert len(ntfy_reqs) == 1
        await ntfy.close()

    async def test_approved_is_silent(self) -> None:
        """APPROVED decisions should not trigger any notification."""
        slack_reqs: list[httpx.Request] = []
        ntfy_reqs: list[httpx.Request] = []

        slack = _make_slack(_ok_slack_handler(slack_reqs))
        ntfy = _make_ntfy(_ok_ntfy_handler(ntfy_reqs), topic="test")

        result = make_result(decision=Decision.APPROVED, reason_code=ReasonCode.POLICY_OK)
        await notify_with_fallback(slack, ntfy, result)

        assert len(slack_reqs) == 0
        assert len(ntfy_reqs) == 0
        await slack.close()
        await ntfy.close()

    async def test_both_none_no_error(self) -> None:
        """When both Slack and ntfy are None, should not raise."""
        result = make_result(decision=Decision.REJECTED, reason_code=ReasonCode.RISK_HIGH)
        await notify_with_fallback(None, None, result)

    async def test_rejected_non_alert_reason_no_notification(self) -> None:
        """Rejected with non-security reason should not trigger notification via Slack."""
        slack_reqs: list[httpx.Request] = []
        ntfy_reqs: list[httpx.Request] = []

        slack = _make_slack(_ok_slack_handler(slack_reqs))
        ntfy = _make_ntfy(_ok_ntfy_handler(ntfy_reqs), topic="test")

        result = make_result(
            decision=Decision.REJECTED,
            reason_code=ReasonCode.TXN_LIMIT_EXCEEDED,
        )
        await notify_with_fallback(slack, ntfy, result)

        # TXN_LIMIT_EXCEEDED is not in alert_reasons — Slack sets sent=True
        # without making any HTTP call, so ntfy is not called either.
        assert len(slack_reqs) == 0
        assert len(ntfy_reqs) == 0
        await slack.close()
        await ntfy.close()
