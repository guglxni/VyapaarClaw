"""Telegram Bot integration for human-in-the-loop approval workflows.

Sends governance notifications and interactive approval requests via
the Telegram Bot API. Uses inline keyboards for Approve/Reject actions.

Architecture:
  GovernanceEngine -> HELD decision -> TelegramNotifier.request_approval()
                                         |
                                     Telegram Chat (inline keyboard)
                                         |
                                     Human taps Approve / Reject
                                         |
                                     /telegram/callback endpoint
                                         |
                                     handle_telegram_action MCP tool

Environment Variables:
  VYAPAAR_TELEGRAM_BOT_TOKEN  -- Bot token from @BotFather
  VYAPAAR_TELEGRAM_CHAT_ID    -- Chat / group / channel ID for notifications
"""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from vyapaar_mcp.models import Decision, GovernanceResult, ReasonCode

logger = logging.getLogger(__name__)

TELEGRAM_API_BASE = "https://api.telegram.org"


class TelegramNotifier:
    """Async Telegram Bot API client for governance notifications."""

    def __init__(self, bot_token: str, chat_id: str) -> None:
        self._bot_token = bot_token
        self._chat_id = chat_id
        self._base_url = f"{TELEGRAM_API_BASE}/bot{bot_token}"
        self._http = httpx.AsyncClient(timeout=15.0)
        logger.info("TelegramNotifier initialized (chat_id=%s)", chat_id)

    async def close(self) -> None:
        await self._http.aclose()

    async def ping(self) -> bool:
        """Verify bot token is valid via getMe."""
        try:
            resp = await self._http.get(f"{self._base_url}/getMe")
            data = resp.json()
            return bool(data.get("ok"))
        except Exception:
            return False

    # ================================================================
    # Approval Requests (HELD payouts)
    # ================================================================

    async def request_approval(
        self,
        result: GovernanceResult,
        vendor_name: str | None = None,
        vendor_url: str | None = None,
    ) -> bool:
        """Send an approval request with inline Approve/Reject buttons."""
        amount_rupees = result.amount / 100
        vendor_display = vendor_name or vendor_url or "Unknown Vendor"

        text = (
            f"<b>🔔 Payout Approval Required</b>\n\n"
            f"<b>Payout ID:</b> <code>{result.payout_id}</code>\n"
            f"<b>Amount:</b> ₹{amount_rupees:,.2f} ({result.amount} paise)\n"
            f"<b>Agent:</b> <code>{result.agent_id}</code>\n"
            f"<b>Vendor:</b> {_escape_html(vendor_display)}\n\n"
            f"<b>Reason:</b> {_escape_html(result.reason_detail)}\n\n"
            f"<i>⚖️ VyapaarClaw — Processing: {result.processing_ms}ms</i>"
        )

        keyboard = {
            "inline_keyboard": [
                [
                    {
                        "text": "✅ Approve",
                        "callback_data": json.dumps({
                            "a": "approve_payout",
                            "p": result.payout_id,
                        }),
                    },
                    {
                        "text": "❌ Reject",
                        "callback_data": json.dumps({
                            "a": "reject_payout",
                            "p": result.payout_id,
                        }),
                    },
                ]
            ]
        }

        return await self._send_message(text, reply_markup=keyboard)

    # ================================================================
    # Alert Notifications (REJECTED payouts)
    # ================================================================

    async def send_rejection_alert(
        self,
        result: GovernanceResult,
        vendor_name: str | None = None,
        vendor_url: str | None = None,
    ) -> bool:
        """Send a rejection alert to the configured Telegram chat."""
        amount_rupees = result.amount / 100
        vendor_display = vendor_name or vendor_url or "Unknown Vendor"

        reason_emoji = {
            ReasonCode.RISK_HIGH: "🦠",
            ReasonCode.DOMAIN_BLOCKED: "🚫",
            ReasonCode.LIMIT_EXCEEDED: "💰",
            ReasonCode.TXN_LIMIT_EXCEEDED: "💸",
            ReasonCode.NO_POLICY: "📋",
        }
        emoji = reason_emoji.get(result.reason_code, "❌")

        threat_line = ""
        if result.threat_types:
            threat_line = (
                f"\n<b>Threats:</b> {', '.join(result.threat_types)}"
            )

        text = (
            f"<b>{emoji} Payout Rejected — {result.reason_code.value}</b>\n\n"
            f"<b>Payout ID:</b> <code>{result.payout_id}</code>\n"
            f"<b>Amount:</b> ₹{amount_rupees:,.2f}\n"
            f"<b>Agent:</b> <code>{result.agent_id}</code>\n"
            f"<b>Vendor:</b> {_escape_html(vendor_display)}\n\n"
            f"<b>Detail:</b> {_escape_html(result.reason_detail)}"
            f"{threat_line}\n\n"
            f"<i>⚖️ VyapaarClaw — Processing: {result.processing_ms}ms</i>"
        )

        return await self._send_message(text)

    # ================================================================
    # Callback Handling
    # ================================================================

    async def answer_callback(self, callback_query_id: str, text: str) -> bool:
        """Acknowledge an inline keyboard callback (removes loading spinner)."""
        try:
            resp = await self._http.post(
                f"{self._base_url}/answerCallbackQuery",
                json={
                    "callback_query_id": callback_query_id,
                    "text": text,
                    "show_alert": False,
                },
            )
            return resp.json().get("ok", False)
        except Exception as e:
            logger.error("Telegram answerCallbackQuery failed: %s", e)
            return False

    async def update_message(
        self,
        chat_id: str | int,
        message_id: int,
        payout_id: str,
        action: str,
        user_name: str,
    ) -> bool:
        """Replace inline keyboard message with a decision confirmation."""
        emoji = "✅" if action == "approve" else "❌"
        verb = "APPROVED" if action == "approve" else "REJECTED"

        text = (
            f"{emoji} <b>Payout <code>{payout_id}</code> {verb}</b>\n"
            f"Decision by {_escape_html(user_name)}"
        )

        try:
            resp = await self._http.post(
                f"{self._base_url}/editMessageText",
                json={
                    "chat_id": chat_id,
                    "message_id": message_id,
                    "text": text,
                    "parse_mode": "HTML",
                },
            )
            return resp.json().get("ok", False)
        except Exception as e:
            logger.error("Telegram editMessageText failed: %s", e)
            return False

    # ================================================================
    # Telegram Bot API
    # ================================================================

    async def _send_message(
        self,
        text: str,
        reply_markup: dict[str, Any] | None = None,
    ) -> bool:
        """Send a message via the Telegram Bot API."""
        payload: dict[str, Any] = {
            "chat_id": self._chat_id,
            "text": text,
            "parse_mode": "HTML",
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup

        try:
            resp = await self._http.post(
                f"{self._base_url}/sendMessage",
                json=payload,
            )
            data = resp.json()
            if data.get("ok"):
                msg_id = data.get("result", {}).get("message_id")
                logger.info(
                    "Telegram message sent: msg_id=%s chat=%s",
                    msg_id,
                    self._chat_id,
                )
                return True
            else:
                logger.error(
                    "Telegram API error: %s",
                    data.get("description", "unknown"),
                )
                return False
        except httpx.TimeoutException:
            logger.error("Telegram API timeout")
            return False
        except Exception as e:
            logger.error("Telegram notification failed: %s", e)
            return False


def _escape_html(text: str) -> str:
    """Escape HTML special characters for Telegram's HTML parse mode."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
