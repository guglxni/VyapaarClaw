"""Tests for Telegram notifier — human-in-the-loop approval workflow.

Tests message formatting, API calls, callback handling, and the
notify_with_fallback integration for the Telegram channel.
Uses httpx.MockTransport to exercise the real httpx client stack.
"""

from __future__ import annotations

import json

import httpx
import pytest

from vyapaar_mcp.egress.ntfy_notifier import notify_with_fallback
from vyapaar_mcp.egress.slack_notifier import SlackNotifier
from vyapaar_mcp.egress.telegram_notifier import TelegramNotifier, _escape_html
from vyapaar_mcp.models import Decision, GovernanceResult, ReasonCode


def _result(
    decision: Decision = Decision.HELD,
    reason_code: ReasonCode = ReasonCode.APPROVAL_REQUIRED,
    amount: int = 350000,
    payout_id: str = "pout_test_tg_001",
    agent_id: str = "test-agent-001",
) -> GovernanceResult:
    return GovernanceResult(
        decision=decision,
        reason_code=reason_code,
        reason_detail=f"Test: {reason_code.value}",
        payout_id=payout_id,
        agent_id=agent_id,
        amount=amount,
        processing_ms=15,
    )


def _make_tg(handler, bot_token: str = "tok", chat_id: str = "123") -> TelegramNotifier:
    """Create a real TelegramNotifier wired to a MockTransport handler."""
    notifier = TelegramNotifier(bot_token=bot_token, chat_id=chat_id)
    notifier._http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return notifier


def _make_slack(handler) -> SlackNotifier:
    """Create a real SlackNotifier wired to a MockTransport handler."""
    notifier = SlackNotifier(bot_token="xoxb-test", channel_id="C123")
    notifier._http = httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url="https://slack.com/api",
    )
    return notifier


def _ok_tg_handler(log: list[httpx.Request]):
    """Return a Telegram handler that logs requests and returns ok."""

    def handler(request: httpx.Request) -> httpx.Response:
        log.append(request)
        return httpx.Response(200, json={"ok": True, "result": {"message_id": 42}})

    return handler


def _ok_slack_handler(log: list[httpx.Request]):
    """Return a Slack handler that logs requests and returns ok."""

    def handler(request: httpx.Request) -> httpx.Response:
        log.append(request)
        return httpx.Response(200, json={"ok": True, "ts": "123.456"})

    return handler


class TestTelegramNotifierInit:
    def test_init(self) -> None:
        notifier = TelegramNotifier(bot_token="123:ABC", chat_id="-100999")
        assert notifier._chat_id == "-100999"
        assert "123:ABC" in notifier._base_url

    def test_base_url_format(self) -> None:
        notifier = TelegramNotifier(bot_token="tok", chat_id="1")
        assert notifier._base_url == "https://api.telegram.org/bottok"


class TestEscapeHtml:
    def test_escapes_angle_brackets(self) -> None:
        assert _escape_html("<script>") == "&lt;script&gt;"

    def test_escapes_ampersand(self) -> None:
        assert _escape_html("A & B") == "A &amp; B"

    def test_plain_text_unchanged(self) -> None:
        assert _escape_html("hello world") == "hello world"


@pytest.mark.asyncio
class TestRequestApproval:
    async def test_sends_message_with_inline_keyboard(self) -> None:
        requests_made: list[httpx.Request] = []

        notifier = _make_tg(_ok_tg_handler(requests_made))

        result = _result()
        success = await notifier.request_approval(result, vendor_name="Acme Corp")

        assert success is True
        assert len(requests_made) == 1
        assert "/sendMessage" in str(requests_made[0].url)

        payload = json.loads(requests_made[0].content)
        assert payload["parse_mode"] == "HTML"
        assert "inline_keyboard" in payload["reply_markup"]
        keyboard = payload["reply_markup"]["inline_keyboard"]
        assert len(keyboard) == 1
        assert len(keyboard[0]) == 2
        approve_btn = keyboard[0][0]
        reject_btn = keyboard[0][1]
        assert "Approve" in approve_btn["text"]
        assert "Reject" in reject_btn["text"]
        approve_data = json.loads(approve_btn["callback_data"])
        assert approve_data["a"] == "approve_payout"
        assert approve_data["p"] == result.payout_id
        await notifier.close()

    async def test_returns_false_on_api_error(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"ok": False, "description": "Forbidden"})

        notifier = _make_tg(handler)
        assert await notifier.request_approval(_result()) is False
        await notifier.close()

    async def test_returns_false_on_timeout(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.TimeoutException("timeout")

        notifier = _make_tg(handler)
        assert await notifier.request_approval(_result()) is False
        await notifier.close()


@pytest.mark.asyncio
class TestRejectionAlert:
    async def test_sends_rejection_message(self) -> None:
        requests_made: list[httpx.Request] = []

        notifier = _make_tg(_ok_tg_handler(requests_made))

        result = _result(
            decision=Decision.REJECTED,
            reason_code=ReasonCode.RISK_HIGH,
        )
        result.threat_types = ["MALWARE"]

        success = await notifier.send_rejection_alert(result, vendor_url="https://evil.xyz")
        assert success is True
        assert len(requests_made) == 1

        payload = json.loads(requests_made[0].content)
        assert "MALWARE" in payload["text"]
        assert "reply_markup" not in payload
        await notifier.close()


@pytest.mark.asyncio
class TestCallbackHandling:
    async def test_answer_callback(self) -> None:
        requests_made: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            requests_made.append(request)
            return httpx.Response(200, json={"ok": True})

        notifier = _make_tg(handler)

        ok = await notifier.answer_callback("qid_123", "Done!")
        assert ok is True
        assert len(requests_made) == 1
        assert "answerCallbackQuery" in str(requests_made[0].url)
        await notifier.close()

    async def test_update_message(self) -> None:
        requests_made: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            requests_made.append(request)
            return httpx.Response(200, json={"ok": True})

        notifier = _make_tg(handler)

        ok = await notifier.update_message(
            chat_id=123,
            message_id=42,
            payout_id="pout_x",
            action="approve",
            user_name="alice",
        )
        assert ok is True
        assert len(requests_made) == 1
        payload = json.loads(requests_made[0].content)
        assert "APPROVED" in payload["text"]
        assert payload["chat_id"] == 123
        assert payload["message_id"] == 42
        await notifier.close()


@pytest.mark.asyncio
class TestPing:
    async def test_ping_success(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"ok": True, "result": {"id": 1, "first_name": "Bot"}})

        notifier = _make_tg(handler)
        assert await notifier.ping() is True
        await notifier.close()

    async def test_ping_failure(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"ok": False})

        notifier = _make_tg(handler, bot_token="bad")
        assert await notifier.ping() is False
        await notifier.close()


@pytest.mark.asyncio
class TestNotifyWithFallbackTelegram:
    async def test_telegram_used_when_slack_none(self) -> None:
        """Telegram is tried when Slack is not configured."""
        tg_reqs: list[httpx.Request] = []

        tg = _make_tg(_ok_tg_handler(tg_reqs))

        result = _result(decision=Decision.HELD)
        await notify_with_fallback(
            None,
            None,
            result,
            vendor_name="V",
            telegram_notifier=tg,
        )

        assert len(tg_reqs) == 1
        assert "/sendMessage" in str(tg_reqs[0].url)
        await tg.close()

    async def test_telegram_skipped_when_slack_succeeds(self) -> None:
        """Telegram not called when Slack succeeds."""
        slack_reqs: list[httpx.Request] = []
        tg_reqs: list[httpx.Request] = []

        slack = _make_slack(_ok_slack_handler(slack_reqs))
        tg = _make_tg(_ok_tg_handler(tg_reqs))

        result = _result(decision=Decision.HELD)
        await notify_with_fallback(
            slack,
            None,
            result,
            vendor_name="V",
            telegram_notifier=tg,
        )

        assert len(slack_reqs) == 1
        assert len(tg_reqs) == 0
        await slack.close()
        await tg.close()

    async def test_telegram_rejection_alert(self) -> None:
        tg_reqs: list[httpx.Request] = []

        tg = _make_tg(_ok_tg_handler(tg_reqs))

        result = _result(
            decision=Decision.REJECTED,
            reason_code=ReasonCode.DOMAIN_BLOCKED,
        )
        await notify_with_fallback(
            None,
            None,
            result,
            telegram_notifier=tg,
        )

        assert len(tg_reqs) == 1
        await tg.close()

    async def test_approved_is_silent(self) -> None:
        tg_reqs: list[httpx.Request] = []

        tg = _make_tg(_ok_tg_handler(tg_reqs))

        result = _result(decision=Decision.APPROVED, reason_code=ReasonCode.POLICY_OK)
        await notify_with_fallback(None, None, result, telegram_notifier=tg)

        assert len(tg_reqs) == 0
        await tg.close()
