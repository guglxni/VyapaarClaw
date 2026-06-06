"""Tests for the dual-LLM security validator."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from vyapaar_mcp.config import VyapaarConfig
from vyapaar_mcp.llm.security_validator import (
    SecurityLLMClient,
    ToolCallRequest,
    ToolCallValidator,
    ValidationResult,
)


def _config(**overrides: Any) -> VyapaarConfig:
    values: dict[str, Any] = {
        "razorpay_key_id": "rzp_test_xxx",
        "razorpay_key_secret": "secret",
        "google_safe_browsing_key": "gsb_key",
        "postgres_dsn": "postgresql://test:test@localhost/test",
        "security_llm_model": "openai/gpt-4o-mini",
        "security_llm_base_url": "http://security-llm.test/v1",
        "security_llm_url": "",
        "security_llm_api_key": "security-key",
    }
    values.update(overrides)
    return VyapaarConfig(**values)


def _request() -> ToolCallRequest:
    return ToolCallRequest(
        tool_name="score_transaction_risk",
        parameters={"amount": 1000},
        agent_id="agent-1",
        context_tainted=True,
    )


def _llm_response(content: str | None) -> Any:
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content=content),
            )
        ]
    )


@pytest.mark.asyncio
class TestSecurityLLMClient:
    """Security LLM client should parse decisions and fail according to strictness."""

    async def test_unconfigured_strict_mode_denies(self) -> None:
        client = SecurityLLMClient(
            _config(security_llm_base_url="", security_llm_url="", quarantine_strict=True)
        )

        result = await client.validate_tool_call(_request(), {"rules": []})

        assert result == ValidationResult(
            approved=False,
            reason="Security LLM unavailable (strict mode)",
            risk_score=1.0,
            mitigation="DENY",
        )

    async def test_unconfigured_non_strict_mode_allows(self) -> None:
        client = SecurityLLMClient(
            _config(security_llm_base_url="", security_llm_url="", quarantine_strict=False)
        )

        result = await client.validate_tool_call(_request(), {"rules": []})

        assert result.approved is True
        assert result.reason == "Security LLM unavailable (non-strict mode)"
        assert result.risk_score == 0.5

    async def test_valid_json_response_returns_validation_result(self) -> None:
        client = SecurityLLMClient(_config())
        content = (
            '{"approved": false, "reason": "blocked by policy", '
            '"risk_score": 0.9, "mitigation": "DENY"}'
        )

        with patch(
            "vyapaar_mcp.llm.security_validator.litellm.acompletion",
            new_callable=AsyncMock,
        ) as mock_ac:
            mock_ac.return_value = _llm_response(content)
            result = await client.validate_tool_call(_request(), {"max_amount": 500})

        assert result == ValidationResult(
            approved=False,
            reason="blocked by policy",
            risk_score=0.9,
            mitigation="DENY",
        )
        call_kwargs = mock_ac.call_args.kwargs
        assert call_kwargs["model"] == "openai/gpt-4o-mini"
        assert call_kwargs["api_key"] == "security-key"
        assert call_kwargs["api_base"] == "http://security-llm.test/v1"
        assert "CONTEXT_TAINTED: True" in call_kwargs["messages"][1]["content"]

    async def test_invalid_json_strict_mode_denies(self) -> None:
        client = SecurityLLMClient(_config(quarantine_strict=True))

        with patch(
            "vyapaar_mcp.llm.security_validator.litellm.acompletion",
            new_callable=AsyncMock,
        ) as mock_ac:
            mock_ac.return_value = _llm_response("not json")
            result = await client.validate_tool_call(_request(), {})

        assert result.approved is False
        assert result.risk_score == 1.0
        assert result.mitigation == "DENY"
        assert result.reason.startswith("Invalid security LLM response:")

    async def test_validation_error_non_strict_mode_allows(self) -> None:
        client = SecurityLLMClient(_config(quarantine_strict=False))

        with patch(
            "vyapaar_mcp.llm.security_validator.litellm.acompletion",
            new_callable=AsyncMock,
        ) as mock_ac:
            mock_ac.side_effect = ValueError("empty response")
            result = await client.validate_tool_call(_request(), {})

        assert result.approved is True
        assert result.reason == "Validation error (non-strict mode, see server logs)"
        assert result.risk_score == 0.5


@pytest.mark.asyncio
class TestToolCallValidator:
    """ToolCallValidator should enforce deterministic taint tiers."""

    async def test_critical_tool_is_denied_when_context_tainted(self) -> None:
        validator = ToolCallValidator(_config())
        validator.mark_taint("handle_razorpay_webhook")

        result = await validator.validate(
            "set_agent_policy",
            {"agent_id": "agent-1"},
            "agent-1",
            {},
        )

        assert result.approved is False
        assert result.risk_score == 1.0
        assert "blocked when context is tainted" in result.reason

    async def test_dual_llm_tool_delegates_when_context_tainted(self) -> None:
        validator = ToolCallValidator(_config())
        validator.mark_taint("check_vendor_reputation")
        validator._security_llm.validate_tool_call = AsyncMock(
            return_value=ValidationResult(
                approved=True,
                reason="approved by security validator",
                risk_score=0.2,
            )
        )

        result = await validator.validate(
            "score_transaction_risk",
            {"amount": 1000},
            "agent-1",
            {"max_amount": 5000},
        )

        assert result.approved is True
        assert result.reason == "approved by security validator"
        validator._security_llm.validate_tool_call.assert_awaited_once()

    async def test_clean_context_allows_without_security_llm(self) -> None:
        validator = ToolCallValidator(_config())
        validator._security_llm.validate_tool_call = AsyncMock()

        result = await validator.validate(
            "score_transaction_risk",
            {"amount": 1000},
            "agent-1",
            {},
        )

        assert result == ValidationResult(
            approved=True,
            reason="Context clean or tool read-only",
            risk_score=0.0,
        )
        validator._security_llm.validate_tool_call.assert_not_awaited()
