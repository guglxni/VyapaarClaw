"""Generic LLM Client using LiteLLM.

Supports any provider via LiteLLM's unified interface:
- Azure (azure/model-name)
- OpenAI (openai/gpt-4o, gpt-4o)
- Anthropic (anthropic/claude-3-opus)
- Google (gemini/gemini-pro)
- Groq, Ollama, local models, etc.

LiteLLM normalises provider quirks into a single OpenAI-compatible API.
"""

from __future__ import annotations

import logging
from typing import Any

import litellm
from litellm.exceptions import OpenAIError

from vyapaar_mcp.config import VyapaarConfig

logger = logging.getLogger(__name__)

# LiteLLM can be chatty; respect our log level
litellm.suppress_debug_info = True


class LLMClient:
    """Provider-agnostic async LLM client via LiteLLM.

    Usage::

        client = LLMClient(config)
        await client.initialize()
        response, status = await client.chat_completion(
            messages=[{"role": "user", "content": "Hello"}],
        )
    """

    def __init__(self, config: VyapaarConfig) -> None:
        self._config = config

    @property
    def is_configured(self) -> bool:
        """Check whether the client has enough config to make calls."""
        return bool(self.model_id and self._config.llm_api_key)

    @property
    def model_id(self) -> str:
        """Return the effective LiteLLM model identifier.

        Examples: ``azure/kimi-k2.5``, ``gpt-4o``, ``anthropic/claude-3-opus``.
        """
        # Computed by the config migration validator so old Azure fields
        # automatically produce a valid LiteLLM string.
        return self._config.llm_model

    async def initialize(self) -> None:
        """Validate configuration and log readiness."""
        if not self.is_configured:
            logger.warning(
                "LLM not configured — set VYAPAAR_LLM_MODEL and "
                "VYAPAAR_LLM_API_KEY (or the legacy "
                "VYAPAAR_AZURE_OPENAI_* vars)."
            )
            return
        logger.info("LLM client ready: model=%s", self.model_id)

    async def chat_completion(
        self,
        messages: list[dict[str, Any]],
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> tuple[str | None, str]:
        """Send a chat-completion request via LiteLLM.

        Args:
            messages: OpenAI-style message list.
            temperature: Sampling temperature (0-2).
            max_tokens: Maximum tokens to generate (``None`` = omitted).

        Returns:
            ``(content, status)`` where *content* is the assistant message
            or ``None`` on error, and *status* is ``"success"`` or an
            error description.
        """
        if not self.is_configured:
            return None, "LLM client not configured"

        try:
            params: dict[str, Any] = {
                "model": self.model_id,
                "messages": messages,
                "temperature": temperature,
            }
            if max_tokens is not None:
                params["max_tokens"] = max_tokens
            if self._config.llm_api_key:
                params["api_key"] = self._config.llm_api_key
            if self._config.llm_base_url:
                params["api_base"] = self._config.llm_base_url
            if self._config.llm_api_version:
                params["api_version"] = self._config.llm_api_version

            response = await litellm.acompletion(**params)

            content: str | None = None
            reasoning: str | None = None
            if response.choices:
                msg = response.choices[0].message
                content = getattr(msg, "content", None)
                reasoning = getattr(msg, "reasoning_content", None)

            usage = getattr(response, "usage", None) or {}
            prompt_tok = getattr(usage, "prompt_tokens", 0)
            completion_tok = getattr(usage, "completion_tokens", 0)
            total_tok = getattr(usage, "total_tokens", 0)
            finish_reason = (
                response.choices[0].finish_reason
                if response.choices
                else None
            )

            logger.info(
                "LLM response: model=%s tokens=%d→%d total=%d finish=%s",
                self.model_id,
                prompt_tok,
                completion_tok,
                total_tok,
                finish_reason,
            )

            if not content and reasoning and finish_reason == "length":
                return None, "reasoning consumed all tokens"
            if not content:
                return None, "Empty response from LLM"

            return content, "success"

        except litellm.AuthenticationError as exc:
            logger.error("LLM authentication failed: %s", exc)
            return None, f"Authentication failed: {exc}"
        except litellm.BadRequestError as exc:
            logger.error("LLM bad request: %s", exc)
            return None, f"Model error: {exc}"
        except litellm.NotFoundError as exc:
            logger.error("LLM model not found: %s", exc)
            return None, f"Model not found: {exc}"
        except litellm.RateLimitError:
            logger.warning("LLM rate limited")
            return None, "Rate limited. Please retry after a moment."
        except litellm.Timeout:
            logger.warning("LLM request timed out")
            return None, "Request timed out. LLM may need more time."
        except (OpenAIError, TypeError, AttributeError, ValueError, RuntimeError) as exc:
            logger.error("LLM API error: %s", exc)
            return None, f"LLM error: {exc!s}"

    async def close(self) -> None:
        """No-op — LiteLLM manages its own HTTP sessions."""
        pass
