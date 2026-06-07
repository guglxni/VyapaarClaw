"""Unit tests for VyapaarClaw MCP server helpers and initialization logic.

Covers:
- _require() service validation
- Tool registration on the FastMCP instance
- Health endpoint JSON structure
- _lifespan context manager startup/shutdown sequencing

All external dependencies are mocked with unittest.mock.
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from vyapaar_mcp import server

# ================================================================
# _require()
# ================================================================


class TestRequire:
    """Test the _require() helper that guards MCP tool execution."""

    def test_raises_runtimeerror_when_single_service_missing(self) -> None:
        with pytest.raises(RuntimeError, match="missing: redis"):
            server._require(redis=None)

    def test_raises_runtimeerror_when_multiple_services_missing(self) -> None:
        with pytest.raises(RuntimeError, match="missing: redis, postgres, governance"):
            server._require(redis=None, postgres=None, governance=None)

    def test_raises_runtimeerror_message_includes_startup_hint(self) -> None:
        with pytest.raises(RuntimeError, match="Ensure startup\\(\\) completed successfully"):
            server._require(config=None)

    def test_passes_silently_when_all_services_provided(self) -> None:
        # Should not raise
        server._require(
            redis=MagicMock(),
            postgres=MagicMock(),
            governance=MagicMock(),
        )

    def test_raises_when_any_explicit_service_is_none(self) -> None:
        with pytest.raises(RuntimeError, match="missing: postgres"):
            server._require(
                redis=MagicMock(),
                postgres=None,
            )


# ================================================================
# Tool Registration
# ================================================================


class TestToolRegistration:
    """Verify that @mcp.tool() decorators are applied and tools are registered."""

    def test_tools_are_registered_in_fastmcp_manager(self) -> None:
        tools = server.mcp._tool_manager._tools
        assert "health_check" in tools
        assert "handle_razorpay_webhook" in tools
        assert "get_metrics" in tools
        assert "poll_razorpay_payouts" in tools
        assert "check_vendor_reputation" in tools

    def test_tool_registration_count_is_nonzero(self) -> None:
        tools = server.mcp._tool_manager._tools
        assert len(tools) >= 10  # sanity check

    def test_custom_health_route_is_registered(self) -> None:
        routes = server.mcp._custom_starlette_routes
        path_map = {r.path: r for r in routes}
        assert "/health" in path_map
        assert "GET" in path_map["/health"].methods
        assert path_map["/health"].endpoint is server.health_endpoint

    def test_http_endpoint_handlers_are_extracted_and_bound(self) -> None:
        assert server.health_endpoint.__name__ == "health_endpoint"
        assert server.slack_actions_endpoint.__name__ == "slack_actions_endpoint"
        assert server.telegram_callback_endpoint.__name__ == "telegram_callback_endpoint"
        assert server.health_endpoint.__module__ == "vyapaar_mcp.handlers.http"
        assert server.slack_actions_endpoint.__module__ == "vyapaar_mcp.handlers.http"
        assert server.telegram_callback_endpoint.__module__ == "vyapaar_mcp.handlers.http"

    def test_registered_tool_has_correct_metadata(self) -> None:
        tools = server.mcp._tool_manager._tools
        health_tool = tools["health_check"]
        assert health_tool.name == "health_check"
        assert health_tool.is_async is True


# ================================================================
# Health Endpoint
# ================================================================


@pytest.mark.asyncio
class TestHealthEndpoint:
    """Test the /health HTTP endpoint with mocked services."""

    async def test_returns_ok_when_services_healthy(self) -> None:
        mock_redis = AsyncMock()
        mock_redis.ping.return_value = True
        mock_postgres = AsyncMock()
        mock_postgres.ping.return_value = True

        with (
            patch.object(server.state, "redis", mock_redis),
            patch.object(server.state, "postgres", mock_postgres),
            patch.object(server.state, "start_time", 0),
        ):
            request = MagicMock()
            response = await server.health_endpoint(request)

        assert response.status_code == 200
        body: dict[str, Any] = json.loads(response.body)
        assert body["status"] == "ok"
        assert body["service"] == "vyapaarclaw"
        assert body["version"] == "0.1.0"
        assert body["redis"] == "ok"
        assert body["postgres"] == "ok"
        assert "uptime_seconds" in body

    async def test_returns_degraded_when_redis_down(self) -> None:
        mock_redis = AsyncMock()
        mock_redis.ping.return_value = False
        mock_postgres = AsyncMock()
        mock_postgres.ping.return_value = True

        with (
            patch.object(server.state, "redis", mock_redis),
            patch.object(server.state, "postgres", mock_postgres),
            patch.object(server.state, "start_time", 0),
        ):
            request = MagicMock()
            response = await server.health_endpoint(request)

        body: dict[str, Any] = json.loads(response.body)
        assert body["status"] == "degraded"
        assert body["redis"] == "error"
        assert body["postgres"] == "ok"

    async def test_returns_degraded_when_postgres_down(self) -> None:
        mock_redis = AsyncMock()
        mock_redis.ping.return_value = True
        mock_postgres = AsyncMock()
        mock_postgres.ping.return_value = False

        with (
            patch.object(server.state, "redis", mock_redis),
            patch.object(server.state, "postgres", mock_postgres),
            patch.object(server.state, "start_time", 0),
        ):
            request = MagicMock()
            response = await server.health_endpoint(request)

        body: dict[str, Any] = json.loads(response.body)
        assert body["status"] == "degraded"
        assert body["redis"] == "ok"
        assert body["postgres"] == "error"

    async def test_handles_none_services(self) -> None:
        with (
            patch.object(server.state, "redis", None),
            patch.object(server.state, "postgres", None),
            patch.object(server.state, "start_time", 0),
        ):
            request = MagicMock()
            response = await server.health_endpoint(request)

        body: dict[str, Any] = json.loads(response.body)
        assert body["status"] == "degraded"
        assert body["redis"] == "error"
        assert body["postgres"] == "error"


# ================================================================
# Lifespan Context Manager
# ================================================================


@pytest.mark.asyncio
class TestLifespan:
    """Test the _lifespan context manager orchestrates startup and shutdown."""

    async def test_calls_startup_then_shutdown(self) -> None:
        with (
            patch.object(server, "_startup", new_callable=AsyncMock) as mock_startup,
            patch.object(server, "_shutdown", new_callable=AsyncMock) as mock_shutdown,
        ):
            async with server._lifespan(server.mcp):
                mock_startup.assert_awaited_once()
                mock_shutdown.assert_not_awaited()

            mock_shutdown.assert_awaited_once()

    async def test_calls_shutdown_even_on_exception(self) -> None:
        with (
            patch.object(server, "_startup", new_callable=AsyncMock) as mock_startup,
            patch.object(server, "_shutdown", new_callable=AsyncMock) as mock_shutdown,
        ):
            with pytest.raises(ValueError, match="boom"):
                async with server._lifespan(server.mcp):
                    mock_startup.assert_awaited_once()
                    raise ValueError("boom")

            mock_shutdown.assert_awaited_once()
