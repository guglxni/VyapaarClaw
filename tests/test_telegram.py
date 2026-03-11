"""Tests for Telegram notifier — human-in-the-loop approval workflow.

Tests message formatting, API calls, callback handling, and the
notify_with_fallback integration for the Telegram channel.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from vyapaar_mcp.egress.telegram_notifier import TelegramNotifier, _escape_html
from vyapaar_mcp.egress.ntfy_notifier import notify_with_fallback
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
        notifier = TelegramNotifier(bot_token="tok", chat_id="123")
        notifier._http = AsyncMock(spec=httpx.AsyncClient)
        notifier._http.post = AsyncMock(return_value=MagicMock(
            json=lambda: {"ok": True, "result": {"message_id": 42}}
        ))

        result = _result()
        success = await notifier.request_approval(result, vendor_name="Acme Corp")

        assert success is True
        call_args = notifier._http.post.call_args
        payload = call_args.kwargs.get("json") or call_args[1].get("json")
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

    async def test_returns_false_on_api_error(self) -> None:
        notifier = TelegramNotifier(bot_token="tok", chat_id="123")
        notifier._http = AsyncMock(spec=httpx.AsyncClient)
        notifier._http.post = AsyncMock(return_value=MagicMock(
            json=lambda: {"ok": False, "description": "Forbidden"}
        ))

        assert await notifier.request_approval(_result()) is False

    async def test_returns_false_on_timeout(self) -> None:
        notifier = TelegramNotifier(bot_token="tok", chat_id="123")
        notifier._http = AsyncMock(spec=httpx.AsyncClient)
        notifier._http.post = AsyncMock(side_effect=httpx.TimeoutException("timeout"))

        assert await notifier.request_approval(_result()) is False


@pytest.mark.asyncio
class TestRejectionAlert:
    async def test_sends_rejection_message(self) -> None:
        notifier = TelegramNotifier(bot_token="tok", chat_id="123")
        notifier._http = AsyncMock(spec=httpx.AsyncClient)
        notifier._http.post = AsyncMock(return_value=MagicMock(
            json=lambda: {"ok": True, "result": {"message_id": 99}}
        ))

        result = _result(
            decision=Decision.REJECTED,
            reason_code=ReasonCode.RISK_HIGH,
        )
        result.threat_types = ["MALWARE"]

        success = await notifier.send_rejection_alert(result, vendor_url="https://evil.xyz")
        assert success is True
        payload = notifier._http.post.call_args.kwargs.get("json") or \
            notifier._http.post.call_args[1].get("json")
        assert "MALWARE" in payload["text"]
        assert "reply_markup" not in payload


@pytest.mark.asyncio
class TestCallbackHandling:
    async def test_answer_callback(self) -> None:
        notifier = TelegramNotifier(bot_token="tok", chat_id="123")
        notifier._http = AsyncMock(spec=httpx.AsyncClient)
        notifier._http.post = AsyncMock(return_value=MagicMock(
            json=lambda: {"ok": True}
        ))

        ok = await notifier.answer_callback("qid_123", "Done!")
        assert ok is True
        call_url = notifier._http.post.call_args[0][0]
        assert "answerCallbackQuery" in call_url

    async def test_update_message(self) -> None:
        notifier = TelegramNotifier(bot_token="tok", chat_id="123")
        notifier._http = AsyncMock(spec=httpx.AsyncClient)
        notifier._http.post = AsyncMock(return_value=MagicMock(
            json=lambda: {"ok": True}
        ))

        ok = await notifier.update_message(
            chat_id=123, message_id=42,
            payout_id="pout_x", action="approve", user_name="alice",
        )
        assert ok is True
        payload = notifier._http.post.call_args.kwargs.get("json") or \
            notifier._http.post.call_args[1].get("json")
        assert "APPROVED" in payload["text"]
        assert payload["chat_id"] == 123
        assert payload["message_id"] == 42


@pytest.mark.asyncio
class TestPing:
    async def test_ping_success(self) -> None:
        notifier = TelegramNotifier(bot_token="tok", chat_id="123")
        notifier._http = AsyncMock(spec=httpx.AsyncClient)
        notifier._http.get = AsyncMock(return_value=MagicMock(
            json=lambda: {"ok": True, "result": {"id": 1, "first_name": "Bot"}}
        ))
        assert await notifier.ping() is True

    async def test_ping_failure(self) -> None:
        notifier = TelegramNotifier(bot_token="bad", chat_id="123")
        notifier._http = AsyncMock(spec=httpx.AsyncClient)
        notifier._http.get = AsyncMock(return_value=MagicMock(
            json=lambda: {"ok": False}
        ))
        assert await notifier.ping() is False


@pytest.mark.asyncio
class TestNotifyWithFallbackTelegram:
    async def test_telegram_used_when_slack_none(self) -> None:
        """Telegram is tried when Slack is not configured."""
        tg = MagicMock(spec=TelegramNotifier)
        tg.request_approval = AsyncMock(return_value=True)

        result = _result(decision=Decision.HELD)
        await notify_with_fallback(
            None, None, result,
            vendor_name="V",
            telegram_notifier=tg,
        )
        tg.request_approval.assert_awaited_once()

    async def test_telegram_skipped_when_slack_succeeds(self) -> None:
        """Telegram not called when Slack succeeds."""
        slack = MagicMock()
        slack.request_approval = AsyncMock(return_value=True)
        tg = MagicMock(spec=TelegramNotifier)
        tg.request_approval = AsyncMock(return_value=True)

        result = _result(decision=Decision.HELD)
        await notify_with_fallback(
            slack, None, result,
            vendor_name="V",
            telegram_notifier=tg,
        )
        slack.request_approval.assert_awaited_once()
        tg.request_approval.assert_not_awaited()

    async def test_telegram_rejection_alert(self) -> None:
        tg = MagicMock(spec=TelegramNotifier)
        tg.send_rejection_alert = AsyncMock(return_value=True)

        result = _result(
            decision=Decision.REJECTED,
            reason_code=ReasonCode.DOMAIN_BLOCKED,
        )
        await notify_with_fallback(
            None, None, result,
            telegram_notifier=tg,
        )
        tg.send_rejection_alert.assert_awaited_once()

    async def test_approved_is_silent(self) -> None:
        tg = MagicMock(spec=TelegramNotifier)
        tg.request_approval = AsyncMock()

        result = _result(decision=Decision.APPROVED, reason_code=ReasonCode.POLICY_OK)
        await notify_with_fallback(None, None, result, telegram_notifier=tg)
        tg.request_approval.assert_not_awaited()
