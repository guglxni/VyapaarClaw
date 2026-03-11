"""Azure AI Services Client for Kimi K2.5 integration.

Connects to Azure AI Services (Models API) to access the Kimi K2.5 model
for agent intelligence, governance copilot, and security validation.

Kimi K2.5 is a reasoning model that returns:
  - content: The final response
  - reasoning_content: Chain-of-thought reasoning (internal)

Endpoint: https://vyapaar.services.ai.azure.com/models
Model: kimi-k2.5
API Version: 2024-05-01-preview
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from vyapaar_mcp.config import VyapaarConfig

logger = logging.getLogger(__name__)


class AzureOpenAIClient:
    """Azure AI Services client for Kimi K2.5 integration.

    Uses the Azure AI Inference REST API directly (not the Azure OpenAI SDK)
    because Kimi K2.5 is served from Azure AI Services Models API, which
    has a different URL structure than Azure OpenAI.

    The endpoint format is:
        POST {base_url}/chat/completions?api-version={version}
    """

    def __init__(self, config: VyapaarConfig) -> None:
        self._config = config
        self._client: httpx.AsyncClient | None = None

    @property
    def is_configured(self) -> bool:
        """Check if Azure AI is properly configured."""
        return bool(self._config.azure_openai_endpoint and self._config.azure_openai_api_key)

    @property
    def model_id(self) -> str:
        """Return the configured model ID."""
        return self._config.azure_openai_deployment

    async def initialize(self) -> None:
        """Initialize the HTTP client for Azure AI Services."""
        if not self.is_configured:
            logger.warning(
                "Azure AI not configured — set VYAPAAR_AZURE_OPENAI_ENDPOINT "
                "and VYAPAAR_AZURE_OPENAI_API_KEY"
            )
            return

        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(120.0, connect=10.0),
            headers={
                "Content-Type": "application/json",
                "api-key": self._config.azure_openai_api_key,
            },
        )
        logger.info(
            "Azure AI client initialized: endpoint=%s, model=%s, api_version=%s",
            self._config.azure_openai_endpoint,
            self._config.azure_openai_deployment,
            self._config.azure_openai_api_version,
        )

    async def chat_completion(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> tuple[str | None, str]:
        """Send a chat completion request to Kimi K2.5 via Azure AI.

        Kimi K2.5 is a reasoning model. Responses contain both:
        - content: The final answer for the user
        - reasoning_content: Internal chain-of-thought (logged but not returned)

        Args:
            messages: List of {"role": "user|assistant|system", "content": "..."}
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens to generate (must be large enough for
                       reasoning + completion — recommend ≥500)

        Returns:
            Tuple of (generated_text or None, status_message)
        """
        if not self._client:
            return None, (
                "Azure AI not configured — set VYAPAAR_AZURE_OPENAI_ENDPOINT "
                "and VYAPAAR_AZURE_OPENAI_API_KEY"
            )

        # Build the REST API URL
        base_url = self._config.azure_openai_endpoint.rstrip("/")
        url = f"{base_url}/chat/completions"
        params = {"api-version": self._config.azure_openai_api_version}

        body: dict[str, Any] = {
            "model": self._config.azure_openai_deployment,
            "messages": messages,
            "temperature": temperature,
        }
        if max_tokens is not None:
            body["max_tokens"] = max_tokens

        try:
            response = await self._client.post(url, json=body, params=params)

            if response.status_code == 401:
                return None, "Authentication failed. Check VYAPAAR_AZURE_OPENAI_API_KEY."
            if response.status_code == 404:
                return None, (
                    f"Model '{self._config.azure_openai_deployment}' not found "
                    f"at endpoint. Check VYAPAAR_AZURE_OPENAI_ENDPOINT."
                )
            if response.status_code == 429:
                return None, "Rate limited by Azure AI. Please retry after a moment."

            response.raise_for_status()
            data = response.json()

            # Extract response from the choices
            choices = data.get("choices", [])
            if not choices:
                return None, "Empty response from Kimi K2.5"

            message = choices[0].get("message", {})
            content = message.get("content")
            reasoning = message.get("reasoning_content")

            # Log usage info
            usage = data.get("usage", {})
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)
            logger.info(
                "Kimi K2.5 response: tokens=%d→%d, reasoning=%s",
                prompt_tokens,
                completion_tokens,
                "yes" if reasoning else "no",
            )

            # Content can be None if reasoning consumed all tokens
            if content is None and reasoning:
                return None, (
                    "Kimi K2.5 reasoning consumed all tokens — "
                    "increase max_tokens (reasoning model needs overhead)"
                )

            return content, "success"

        except httpx.TimeoutException:
            logger.error("Kimi K2.5 request timed out")
            return None, "Request timed out. Kimi K2.5 reasoning may need more time."
        except httpx.HTTPStatusError as e:
            logger.error(
                "Azure AI HTTP error: %s %s",
                e.response.status_code,
                e.response.text[:200],
            )
            return None, f"Azure AI HTTP error: {e.response.status_code}"
        except Exception as e:
            logger.error("Azure AI API error: %s", e)
            return None, f"Azure AI error: {e!s}"

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
