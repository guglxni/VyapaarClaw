"""Comprehensive tests for AzureOpenAIClient (Kimi K2.5).

Tests cover:
- Configuration validation
- Client initialization
- Chat completions (success, error, timeout)
- Reasoning model response parsing
- Error handling (401, 404, 429, timeout, empty response)
- Client lifecycle (init, close, double-close)
"""

# Note: httpx.Response requires a request= parameter for raise_for_status()
# to work. We use _MOCK_REQUEST for all test responses.

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from vyapaar_mcp.config import VyapaarConfig
from vyapaar_mcp.llm.azure_client import AzureOpenAIClient

# Shared mock request for httpx.Response construction
_MOCK_REQUEST = httpx.Request("POST", "https://vyapaar.services.ai.azure.com/models/chat/completions")


# ================================================================
# Fixtures
# ================================================================


@pytest.fixture
def config_with_key() -> VyapaarConfig:
    """Config with all Azure AI fields populated."""
    return VyapaarConfig(
        razorpay_key_id="rzp_test_xxx",
        razorpay_key_secret="secret",
        google_safe_browsing_key="gsb_key",
        postgres_dsn="postgresql://test:test@localhost/test",
        azure_openai_endpoint="https://vyapaar.services.ai.azure.com/models",
        azure_openai_api_key="test-api-key-123",
        azure_openai_deployment="kimi-k2.5",
        azure_openai_api_version="2024-05-01-preview",
    )


@pytest.fixture
def config_no_key() -> VyapaarConfig:
    """Config with empty Azure AI API key."""
    return VyapaarConfig(
        razorpay_key_id="rzp_test_xxx",
        razorpay_key_secret="secret",
        google_safe_browsing_key="gsb_key",
        postgres_dsn="postgresql://test:test@localhost/test",
        azure_openai_endpoint="https://vyapaar.services.ai.azure.com/models",
        azure_openai_api_key="",
        azure_openai_deployment="kimi-k2.5",
    )


@pytest.fixture
def config_no_endpoint() -> VyapaarConfig:
    """Config with empty endpoint."""
    return VyapaarConfig(
        razorpay_key_id="rzp_test_xxx",
        razorpay_key_secret="secret",
        google_safe_browsing_key="gsb_key",
        postgres_dsn="postgresql://test:test@localhost/test",
        azure_openai_endpoint="",
        azure_openai_api_key="test-api-key",
    )


@pytest.fixture
def client(config_with_key: VyapaarConfig) -> AzureOpenAIClient:
    """Create a client instance with valid config."""
    return AzureOpenAIClient(config_with_key)


def _mock_kimi_response(
    content: str | None = "Hello!",
    reasoning: str | None = "Thinking about this...",
    prompt_tokens: int = 10,
    completion_tokens: int = 50,
    finish_reason: str = "stop",
) -> dict:
    """Build a mock Kimi K2.5 API response."""
    message: dict = {"role": "assistant", "content": content}
    if reasoning is not None:
        message["reasoning_content"] = reasoning
    return {
        "choices": [
            {
                "index": 0,
                "message": message,
                "finish_reason": finish_reason,
            }
        ],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        },
        "model": "Kimi-K2.5",
        "id": "test-id-123",
    }


# ================================================================
# Configuration Tests
# ================================================================


class TestConfiguration:
    """Tests for client configuration validation."""

    def test_is_configured_with_key(self, config_with_key: VyapaarConfig) -> None:
        client = AzureOpenAIClient(config_with_key)
        assert client.is_configured is True

    def test_is_not_configured_without_key(self, config_no_key: VyapaarConfig) -> None:
        client = AzureOpenAIClient(config_no_key)
        assert client.is_configured is False

    def test_is_not_configured_without_endpoint(self, config_no_endpoint: VyapaarConfig) -> None:
        client = AzureOpenAIClient(config_no_endpoint)
        assert client.is_configured is False

    def test_model_id(self, config_with_key: VyapaarConfig) -> None:
        client = AzureOpenAIClient(config_with_key)
        assert client.model_id == "kimi-k2.5"


# ================================================================
# Initialization Tests
# ================================================================


class TestInitialization:
    """Tests for client initialization lifecycle."""

    @pytest.mark.asyncio
    async def test_initialize_with_valid_config(self, client: AzureOpenAIClient) -> None:
        await client.initialize()
        assert client._client is not None
        await client.close()

    @pytest.mark.asyncio
    async def test_initialize_without_config(self, config_no_key: VyapaarConfig) -> None:
        client = AzureOpenAIClient(config_no_key)
        await client.initialize()
        assert client._client is None

    @pytest.mark.asyncio
    async def test_close_uninitialised(self, client: AzureOpenAIClient) -> None:
        """Closing an uninitialised client should not raise."""
        await client.close()  # Should not raise

    @pytest.mark.asyncio
    async def test_close_twice(self, client: AzureOpenAIClient) -> None:
        """Double close should be safe."""
        await client.initialize()
        await client.close()
        await client.close()  # Should not raise


# ================================================================
# Chat Completion Tests — Success
# ================================================================


class TestChatCompletionSuccess:
    """Tests for successful chat completions."""

    @pytest.mark.asyncio
    async def test_basic_chat(self, client: AzureOpenAIClient) -> None:
        """Test basic chat completion with content + reasoning."""
        await client.initialize()

        mock_resp = httpx.Response(
            200,
            json=_mock_kimi_response("Hello there!", "I should greet the user."),
            request=_MOCK_REQUEST,
        )

        with patch.object(client._client, "post", new_callable=AsyncMock, return_value=mock_resp):
            response, status = await client.chat_completion(
                messages=[{"role": "user", "content": "Say hello"}],
                max_tokens=500,
            )

        assert status == "success"
        assert response == "Hello there!"
        await client.close()

    @pytest.mark.asyncio
    async def test_chat_without_reasoning(self, client: AzureOpenAIClient) -> None:
        """Test response without reasoning_content field."""
        await client.initialize()

        mock_resp = httpx.Response(
            200,
            json=_mock_kimi_response("Hello!", None),
            request=_MOCK_REQUEST,
        )

        with patch.object(client._client, "post", new_callable=AsyncMock, return_value=mock_resp):
            response, status = await client.chat_completion(
                messages=[{"role": "user", "content": "Hi"}],
            )

        assert status == "success"
        assert response == "Hello!"
        await client.close()

    @pytest.mark.asyncio
    async def test_custom_temperature(self, client: AzureOpenAIClient) -> None:
        """Test that temperature is passed through."""
        await client.initialize()

        mock_resp = httpx.Response(200, json=_mock_kimi_response("Test"), request=_MOCK_REQUEST)

        with patch.object(client._client, "post", new_callable=AsyncMock, return_value=mock_resp) as mock_post:
            await client.chat_completion(
                messages=[{"role": "user", "content": "Test"}],
                temperature=0.1,
                max_tokens=100,
            )

            # Verify the request body
            call_args = mock_post.call_args
            body = call_args[1]["json"]
            assert body["temperature"] == 0.1
            assert body["max_tokens"] == 100
            assert body["model"] == "kimi-k2.5"

        await client.close()

    @pytest.mark.asyncio
    async def test_no_max_tokens(self, client: AzureOpenAIClient) -> None:
        """Test that max_tokens is omitted when None."""
        await client.initialize()

        mock_resp = httpx.Response(200, json=_mock_kimi_response(), request=_MOCK_REQUEST)

        with patch.object(client._client, "post", new_callable=AsyncMock, return_value=mock_resp) as mock_post:
            await client.chat_completion(
                messages=[{"role": "user", "content": "Hi"}],
                max_tokens=None,
            )

            body = mock_post.call_args[1]["json"]
            assert "max_tokens" not in body

        await client.close()


# ================================================================
# Chat Completion Tests — Error Handling
# ================================================================


class TestChatCompletionErrors:
    """Tests for error handling in chat completions."""

    @pytest.mark.asyncio
    async def test_not_initialised(self, client: AzureOpenAIClient) -> None:
        """Test calling chat without initialization."""
        response, status = await client.chat_completion(
            messages=[{"role": "user", "content": "Hi"}],
        )
        assert response is None
        assert "not configured" in status

    @pytest.mark.asyncio
    async def test_auth_failure_401(self, client: AzureOpenAIClient) -> None:
        """Test 401 Unauthorized response."""
        await client.initialize()

        mock_resp = httpx.Response(401, json={"error": "Unauthorized"}, request=_MOCK_REQUEST)

        with patch.object(client._client, "post", new_callable=AsyncMock, return_value=mock_resp):
            response, status = await client.chat_completion(
                messages=[{"role": "user", "content": "Hi"}],
            )

        assert response is None
        assert "Authentication failed" in status
        await client.close()

    @pytest.mark.asyncio
    async def test_model_not_found_404(self, client: AzureOpenAIClient) -> None:
        """Test 404 Not Found response."""
        await client.initialize()

        mock_resp = httpx.Response(404, json={"error": "Not found"}, request=_MOCK_REQUEST)

        with patch.object(client._client, "post", new_callable=AsyncMock, return_value=mock_resp):
            response, status = await client.chat_completion(
                messages=[{"role": "user", "content": "Hi"}],
            )

        assert response is None
        assert "not found" in status
        await client.close()

    @pytest.mark.asyncio
    async def test_rate_limited_429(self, client: AzureOpenAIClient) -> None:
        """Test 429 Too Many Requests response."""
        await client.initialize()

        mock_resp = httpx.Response(429, json={"error": "Rate limited"}, request=_MOCK_REQUEST)

        with patch.object(client._client, "post", new_callable=AsyncMock, return_value=mock_resp):
            response, status = await client.chat_completion(
                messages=[{"role": "user", "content": "Hi"}],
            )

        assert response is None
        assert "Rate limited" in status
        await client.close()

    @pytest.mark.asyncio
    async def test_timeout(self, client: AzureOpenAIClient) -> None:
        """Test timeout handling."""
        await client.initialize()

        with patch.object(
            client._client, "post",
            new_callable=AsyncMock,
            side_effect=httpx.TimeoutException("Connection timed out"),
        ):
            response, status = await client.chat_completion(
                messages=[{"role": "user", "content": "Hi"}],
            )

        assert response is None
        assert "timed out" in status
        await client.close()

    @pytest.mark.asyncio
    async def test_empty_choices(self, client: AzureOpenAIClient) -> None:
        """Test empty choices array in response."""
        await client.initialize()

        mock_resp = httpx.Response(200, json={"choices": [], "usage": {}}, request=_MOCK_REQUEST)

        with patch.object(client._client, "post", new_callable=AsyncMock, return_value=mock_resp):
            response, status = await client.chat_completion(
                messages=[{"role": "user", "content": "Hi"}],
            )

        assert response is None
        assert "Empty response" in status
        await client.close()

    @pytest.mark.asyncio
    async def test_reasoning_consumed_all_tokens(self, client: AzureOpenAIClient) -> None:
        """Test when reasoning uses all tokens and content is None."""
        await client.initialize()

        mock_resp = httpx.Response(
            200,
            json=_mock_kimi_response(
                content=None,
                reasoning="Very long reasoning...",
                finish_reason="length",
            ),
            request=_MOCK_REQUEST,
        )

        with patch.object(client._client, "post", new_callable=AsyncMock, return_value=mock_resp):
            response, status = await client.chat_completion(
                messages=[{"role": "user", "content": "Hi"}],
                max_tokens=50,
            )

        assert response is None
        assert "reasoning consumed all tokens" in status
        await client.close()

    @pytest.mark.asyncio
    async def test_server_error_500(self, client: AzureOpenAIClient) -> None:
        """Test 500 Internal Server Error handling."""
        await client.initialize()

        mock_resp = httpx.Response(
            500,
            json={"error": "Internal server error"},
            request=httpx.Request("POST", "https://example.com"),
        )

        with patch.object(client._client, "post", new_callable=AsyncMock, return_value=mock_resp):
            response, status = await client.chat_completion(
                messages=[{"role": "user", "content": "Hi"}],
            )

        assert response is None
        assert "500" in status
        await client.close()

    @pytest.mark.asyncio
    async def test_generic_exception(self, client: AzureOpenAIClient) -> None:
        """Test handling of unexpected exceptions."""
        await client.initialize()

        with patch.object(
            client._client, "post",
            new_callable=AsyncMock,
            side_effect=RuntimeError("Something went wrong"),
        ):
            response, status = await client.chat_completion(
                messages=[{"role": "user", "content": "Hi"}],
            )

        assert response is None
        assert "Something went wrong" in status
        await client.close()


# ================================================================
# URL Construction Tests
# ================================================================


class TestURLConstruction:
    """Tests for correct API URL construction."""

    @pytest.mark.asyncio
    async def test_url_construction(self, client: AzureOpenAIClient) -> None:
        """Verify the correct URL is built from endpoint + /chat/completions."""
        await client.initialize()

        mock_resp = httpx.Response(200, json=_mock_kimi_response(), request=_MOCK_REQUEST)

        with patch.object(client._client, "post", new_callable=AsyncMock, return_value=mock_resp) as mock_post:
            await client.chat_completion(
                messages=[{"role": "user", "content": "Hi"}],
            )

            call_args = mock_post.call_args
            url = call_args[0][0]
            params = call_args[1]["params"]

            assert url == "https://vyapaar.services.ai.azure.com/models/chat/completions"
            assert params == {"api-version": "2024-05-01-preview"}

        await client.close()

    @pytest.mark.asyncio
    async def test_url_trailing_slash_stripped(self, config_with_key: VyapaarConfig) -> None:
        """Test that trailing slashes on endpoint are handled."""
        config_with_key.azure_openai_endpoint = "https://vyapaar.services.ai.azure.com/models/"
        client = AzureOpenAIClient(config_with_key)
        await client.initialize()

        mock_resp = httpx.Response(200, json=_mock_kimi_response(), request=_MOCK_REQUEST)

        with patch.object(client._client, "post", new_callable=AsyncMock, return_value=mock_resp) as mock_post:
            await client.chat_completion(
                messages=[{"role": "user", "content": "Hi"}],
            )

            url = mock_post.call_args[0][0]
            assert url == "https://vyapaar.services.ai.azure.com/models/chat/completions"

        await client.close()
