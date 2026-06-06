"""Tests for security utility helpers."""

from __future__ import annotations

import logging

from vyapaar_mcp.security import SecurityFormatter, mask_secrets, sanitize_dict


class TestMaskSecrets:
    """Secret masking should cover common credential formats."""

    def test_masks_named_tokens_case_insensitively(self) -> None:
        message = "API_KEY='abcdefghi12345' auth-token=secretToken123"

        masked = mask_secrets(message)

        assert "abcdefghi12345" not in masked
        assert "secretToken123" not in masked
        assert "API_KEY='****" in masked
        assert "auth-token=****" in masked

    def test_masks_authorization_headers(self) -> None:
        message = (
            "Bearer eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjMifQ.signature "
            "Basic QWxhZGRpbjpvcGVuIHNlc2FtZQ=="
        )

        masked = mask_secrets(message)

        assert "eyJhbGciOiJIUzI1NiJ9" not in masked
        assert "QWxhZGRpbjpvcGVuIHNlc2FtZQ==" not in masked
        assert "Bearer ****" in masked
        assert "Basic ****" in masked


class TestSecurityFormatter:
    """Log formatting should sanitize both message templates and args."""

    def test_format_masks_message_and_string_args(self) -> None:
        record = logging.LogRecord(
            name="test.security",
            level=logging.INFO,
            pathname=__file__,
            lineno=1,
            msg="api_key=supersecret123 for %s",
            args=("Bearer aaa.bbb.ccc",),
            exc_info=None,
        )
        formatter = SecurityFormatter("%(message)s")

        formatted = formatter.format(record)

        assert "supersecret123" not in formatted
        assert "aaa.bbb.ccc" not in formatted
        assert "api_key=****" in formatted
        assert "Bearer ****" in formatted


class TestSanitizeDict:
    """Dictionary sanitization should mask nested sensitive values."""

    def test_masks_nested_sensitive_keys_without_mutating_input(self) -> None:
        data = {
            "service": "razorpay",
            "metadata": {
                "slack_bot_token": "xoxb-123",
                "public_id": "visible",
            },
            "custom_access_token_value": "abcdefghi",
        }

        sanitized = sanitize_dict(data)

        assert sanitized["service"] == "razorpay"
        assert sanitized["metadata"]["slack_bot_token"] == "****"
        assert sanitized["metadata"]["public_id"] == "visible"
        assert sanitized["custom_access_token_value"] == "****"
        assert data["metadata"]["slack_bot_token"] == "xoxb-123"
