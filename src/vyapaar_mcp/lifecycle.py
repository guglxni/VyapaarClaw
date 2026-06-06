"""Lifespan helpers for the VyapaarClaw MCP server."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager
from typing import Any

from mcp.server.fastmcp import FastMCP


def make_lifespan(
    startup: Callable[[], Awaitable[None]],
    shutdown: Callable[[], Awaitable[None]],
) -> Callable[[FastMCP], Any]:
    """Create a FastMCP lifespan context manager."""

    @asynccontextmanager
    async def lifespan(server: FastMCP) -> Any:
        await startup()
        try:
            yield
        finally:
            await shutdown()

    return lifespan
