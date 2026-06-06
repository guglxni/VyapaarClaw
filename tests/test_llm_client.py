"""Tests for the generic LLMClient (LiteLLM-based).

Covers:
- Configuration validation (new generic fields + legacy migration)
- Client initialization lifecycle
- Chat completions (success, error, timeout, empty response)
- Backward compatibility with legacy Azure OpenAI config
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from vyapaar_mcp.config import VyapaarConfig
from vyapaar_mcp.llm.client import LLMClient

# ================================================================
# Fixtures
# ================================================================


@pytest.fixture
def config_with_key() -> VyapaarConfig:
    """Config with all new-style LLM fields populated."""
    return VyapaarConfig(
        razorpay_key_id="rzp_test_xxx",
        razorpay_key_secret="secret",
        google_safe_browsing_key="gsb_key",
        postgres_dsn="postgresql://test:test@localhost/test",
        llm_model="azure/kimi-k2.5",
        llm_api_key="test-api-key-123",
        llm_base_url="https://vyapaar.services.ai.azure.com/models",
        llm_api_version="2024-05-01-preview",
    )


@pytest.fixture
def config_legacy_azure() -> VyapaarConfig:
    """Config using ONLY legacy Azure OpenAI fields (migration path)."""
    return VyapaarConfig(
        razorpay_key_id="rzp_test_xxx",
        razorpay_key_secret="secret",
        google_safe_browsing_key="gsb_key",
        postgres_dsn="postgresql://test:test@localhost/test",
        azure_openai_endpoint="https://vyapaar.services.ai.azure.com/models",
        azure_openai_api_key="legacy-key",
        azure_openai_deployment="kimi-k2.5",
        azure_openai_api_version="2024-05-01-preview",
    )


@pytest.fixture
def config_no_key() -> VyapaarConfig:
    """Config with empty LLM API key."""
    return VyapaarConfig(
        razorpay_key_id="rzp_test_xxx",
        razorpay_key_secret="secret",
        google_safe_browsing_key="gsb_key",
        postgres_dsn="postgresql://test:test@localhost/test",
        llm_model="azure/kimi-k2.5",
        llm_api_key="",
        # Explicitly clear legacy fields so .env doesn't migrate into them
        azure_openai_api_key="",
        azure_openai_deployment="",
        azure_openai_endpoint="",
    )


@pytest.fixture
def config_no_model() -> VyapaarConfig:
    """Config with empty LLM model."""
    return VyapaarConfig(
        razorpay_key_id="rzp_test_xxx",
        razorpay_key_secret="secret",
        google_safe_browsing_key="gsb_key",
        postgres_dsn="postgresql://test:test@localhost/test",
        llm_model="",
        llm_api_key="some-key",
        # Explicitly clear legacy fields so default deployment doesn't migrate
        azure_openai_deployment="",
        azure_openai_api_key="",
    )


@pytest.fixture
def client(config_with_key: VyapaarConfig) -> LLMClient:
    """Create a client instance with valid config."""
    return LLMClient(config_with_key)


# ================================================================
# Configuration Tests
# ================================================================


class TestConfiguration:
    """Tests for client configuration validation."""

    def test_is_configured_with_key(self, config_with_key: VyapaarConfig) -> None:
        client = LLMClient(config_with_key)
        assert client.is_configured is True
        assert client.model_id == "azure/kimi-k2.5"

    def test_legacy_migration(self, config_legacy_azure: VyapaarConfig) -> None:
        """Legacy Azure fields should be auto-mapped to generic ones."""
        assert config_legacy_azure.llm_model == "azure/kimi-k2.5"
        assert config_legacy_azure.llm_api_key == "legacy-key"
        assert config_legacy_azure.llm_base_url == "https://vyapaar.services.ai.azure.com/models"

        client = LLMClient(config_legacy_azure)
        assert client.is_configured is True
        assert client.model_id == "azure/kimi-k2.5"

    def test_is_not_configured_without_key(self, config_no_key: VyapaarConfig) -> None:
        client = LLMClient(config_no_key)
        assert client.is_configured is False

    def test_is_not_configured_without_model(self, config_no_model: VyapaarConfig) -> None:
        client = LLMClient(config_no_model)
        assert client.is_configured is False


# ================================================================
# Initialization Tests
# ================================================================


class TestInitialization:
    """Tests for client initialization lifecycle."""

    @pytest.mark.asyncio
    async def test_initialize_with_valid_config(self, client: LLMClient) -> None:
        await client.initialize()
        # initialize() is idempotent; nothing to assert beyond no exception

    @pytest.mark.asyncio
    async def test_initialize_without_config(self, config_no_key: VyapaarConfig) -> None:
        client = LLMClient(config_no_key)
        await client.initialize()  # should not raise

    @pytest.mark.asyncio
    async def test_close_is_safe(self, client: LLMClient) -> None:
        await client.close()
        await client.close()  # double close should be safe


# ================================================================
# Chat Completion Tests — Success
# ================================================================


def _mock_response(
    content: str | None = "Hello!",
    reasoning: str | None = None,
    finish_reason: str = "stop",
    prompt_tokens: int = 10,
    completion_tokens: int = 5,
) -> Any:
    """Build a mock litellm response object."""
    mock_message = AsyncMock()
    mock_message.content = content
    if reasoning:
        mock_message.reasoning_content = reasoning

    mock_choice = AsyncMock()
    mock_choice.message = mock_message
    mock_choice.finish_reason = finish_reason

    mock_usage = AsyncMock()
    mock_usage.prompt_tokens = prompt_tokens
    mock_usage.completion_tokens = completion_tokens
    mock_usage.total_tokens = prompt_tokens + completion_tokens

    mock_response = AsyncMock()
    mock_response.choices = [mock_choice]
    mock_response.usage = mock_usage
    return mock_response


class TestChatCompletionSuccess:
    """Tests for successful chat completions."""

    @pytest.mark.asyncio
    async def test_basic_chat(self, client: LLMClient) -> None:
        """Test basic chat completion returning content."""
        with patch("vyapaar_mcp.llm.client.litellm.acompletion", new_callable=AsyncMock) as mock_ac:
            mock_ac.return_value = _mock_response("Hello there!")

            response, status = await client.chat_completion(
                messages=[{"role": "user", "content": "Say hello"}],
                max_tokens=500,
            )

        assert status == "success"
        assert response == "Hello there!"
        mock_ac.assert_awaited_once()
        call_kwargs = mock_ac.call_args.kwargs
        assert call_kwargs["model"] == "azure/kimi-k2.5"
        assert call_kwargs["temperature"] == 0.7
        assert call_kwargs["max_tokens"] == 500
        assert call_kwargs["messages"][0]["role"] == "user"

    @pytest.mark.asyncio
    async def test_chat_with_reasoning_consumed_all_tokens(self, client: LLMClient) -> None:
        """Test when reasoning uses all tokens and content is None."""
        with patch("vyapaar_mcp.llm.client.litellm.acompletion", new_callable=AsyncMock) as mock_ac:
            mock_ac.return_value = _mock_response(
                content=None,
                reasoning="Very long reasoning...",
                finish_reason="length",
            )

            response, status = await client.chat_completion(
                messages=[{"role": "user", "content": "Hi"}],
                max_tokens=50,
            )

        assert response is None
        assert "reasoning consumed all tokens" in status

    @pytest.mark.asyncio
    async def test_empty_choices(self, client: LLMClient) -> None:
        """Test empty choices array in response."""
        with patch("vyapaar_mcp.llm.client.litellm.acompletion", new_callable=AsyncMock) as mock_ac:
            mock_response = AsyncMock()
            mock_response.choices = []
            mock_response.usage = AsyncMock()
            mock_response.usage.prompt_tokens = 0
            mock_response.usage.completion_tokens = 0
            mock_response.usage.total_tokens = 0
            mock_ac.return_value = mock_response

            response, status = await client.chat_completion(
                messages=[{"role": "user", "content": "Hi"}],
            )

        assert response is None
        assert "Empty response" in status

    @pytest.mark.asyncio
    async def test_custom_temperature_and_no_max_tokens(self, client: LLMClient) -> None:
        """Test that temperature is passed and max_tokens omitted when None."""
        with patch("vyapaar_mcp.llm.client.litellm.acompletion", new_callable=AsyncMock) as mock_ac:
            mock_ac.return_value = _mock_response("Test")

            await client.chat_completion(
                messages=[{"role": "user", "content": "Test"}],
                temperature=0.1,
                max_tokens=None,
            )

        call_kwargs = mock_ac.call_args.kwargs
        assert call_kwargs["temperature"] == 0.1
        assert "max_tokens" not in call_kwargs


# ================================================================
# Chat Completion Tests — Error Handling
# ================================================================


class TestChatCompletionErrors:
    """Tests for error handling in chat completions."""

    @pytest.mark.asyncio
    async def test_not_configured(self, config_no_key: VyapaarConfig) -> None:
        """Test calling chat when client is not configured."""
        client = LLMClient(config_no_key)
        response, status = await client.chat_completion(
            messages=[{"role": "user", "content": "Hi"}],
        )
        assert response is None
        assert "not configured" in status

    @pytest.mark.asyncio
    async def test_auth_failure(self, client: LLMClient) -> None:
        """Test litellm AuthenticationError."""
        import litellm

        with patch(
            "vyapaar_mcp.llm.client.litellm.acompletion",
            new_callable=AsyncMock,
            side_effect=litellm.AuthenticationError(
                "Invalid key",
                llm_provider="azure",
                model="kimi-k2.5",
            ),
        ):
            response, status = await client.chat_completion(
                messages=[{"role": "user", "content": "Hi"}],
            )

        assert response is None
        assert "Authentication failed" in status

    @pytest.mark.asyncio
    async def test_model_not_found(self, client: LLMClient) -> None:
        """Test litellm NotFoundError."""
        import litellm

        with patch(
            "vyapaar_mcp.llm.client.litellm.acompletion",
            new_callable=AsyncMock,
            side_effect=litellm.NotFoundError(
                "Model not found",
                llm_provider="azure",
                model="kimi-k2.5",
            ),
        ):
            response, status = await client.chat_completion(
                messages=[{"role": "user", "content": "Hi"}],
            )

        assert response is None
        assert "not found" in status

    @pytest.mark.asyncio
    async def test_rate_limited(self, client: LLMClient) -> None:
        """Test litellm RateLimitError."""
        import litellm

        with patch(
            "vyapaar_mcp.llm.client.litellm.acompletion",
            new_callable=AsyncMock,
            side_effect=litellm.RateLimitError(
                "Rate limited",
                llm_provider="azure",
                model="kimi-k2.5",
            ),
        ):
            response, status = await client.chat_completion(
                messages=[{"role": "user", "content": "Hi"}],
            )

        assert response is None
        assert "Rate limited" in status

    @pytest.mark.asyncio
    async def test_timeout(self, client: LLMClient) -> None:
        """Test litellm Timeout."""
        import litellm

        with patch(
            "vyapaar_mcp.llm.client.litellm.acompletion",
            new_callable=AsyncMock,
            side_effect=litellm.Timeout(
                "Request timed out",
                model="kimi-k2.5",
                llm_provider="azure",
            ),
        ):
            response, status = await client.chat_completion(
                messages=[{"role": "user", "content": "Hi"}],
            )

        assert response is None
        assert "timed out" in status

    @pytest.mark.asyncio
    async def test_bad_request(self, client: LLMClient) -> None:
        """Test litellm BadRequestError."""
        import litellm

        with patch(
            "vyapaar_mcp.llm.client.litellm.acompletion",
            new_callable=AsyncMock,
            side_effect=litellm.BadRequestError(
                "Bad request",
                llm_provider="azure",
                model="kimi-k2.5",
            ),
        ):
            response, status = await client.chat_completion(
                messages=[{"role": "user", "content": "Hi"}],
            )

        assert response is None
        assert "Model error" in status

    @pytest.mark.asyncio
    async def test_generic_exception(self, client: LLMClient) -> None:
        """Test handling of unexpected exceptions."""
        with patch(
            "vyapaar_mcp.llm.client.litellm.acompletion",
            new_callable=AsyncMock,
            side_effect=RuntimeError("Something went wrong"),
        ):
            response, status = await client.chat_completion(
                messages=[{"role": "user", "content": "Hi"}],
            )

        assert response is None
        assert "Something went wrong" in status
