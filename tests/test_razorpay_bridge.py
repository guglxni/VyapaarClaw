"""Tests for the RazorpayBridge — real tests, zero mocks.

Unit tests: create real temp files to test constructor logic.
Binary tests: build + spawn the real Go MCP server, verify protocol.
API tests: hit real Razorpay API (skipped without credentials).
"""

from __future__ import annotations

import os
import stat
from pathlib import Path

import pytest

from vyapaar_mcp.config import VyapaarConfig
from vyapaar_mcp.ingress.razorpay_bridge import DEFAULT_BINARY_PATH, RazorpayBridge

GO_BINARY_EXISTS = os.path.isfile(DEFAULT_BINARY_PATH)

HAS_RAZORPAY_CREDS = bool(
    os.environ.get("VYAPAAR_RAZORPAY_KEY_ID", "").startswith("rzp_")
    and os.environ.get("VYAPAAR_RAZORPAY_KEY_SECRET", "")
    and not os.environ.get("VYAPAAR_RAZORPAY_KEY_ID", "").endswith("_ci")
)


# ================================================================
# Unit Tests — real temp files, no mocks
# ================================================================


class TestBridgeInit:
    """Test bridge initialization with real filesystem operations."""

    def test_init_with_real_binary(self, tmp_path: Path) -> None:
        """Bridge initializes when a real file exists at the given path."""
        fake_bin = tmp_path / "razorpay-mcp-server"
        fake_bin.write_text("#!/bin/sh\necho ok\n")
        fake_bin.chmod(stat.S_IRWXU)

        bridge = RazorpayBridge(
            key_id="rzp_test_1234",
            key_secret="test_secret",
            binary_path=str(fake_bin),
        )
        assert bridge._binary_path == str(fake_bin)
        assert bridge._key_id == "rzp_test_1234"

    def test_init_with_missing_binary_raises(self) -> None:
        """Bridge raises FileNotFoundError for a path that doesn't exist."""
        with pytest.raises(FileNotFoundError, match="razorpay-mcp-server"):
            RazorpayBridge(
                key_id="rzp_test_1234",
                key_secret="test_secret",
                binary_path="/nonexistent/path/razorpay-mcp-server",
            )

    def test_stores_credentials(self, tmp_path: Path) -> None:
        """Bridge stores key_id, key_secret, and starts with empty tools."""
        fake_bin = tmp_path / "razorpay-mcp-server"
        fake_bin.write_text("")

        bridge = RazorpayBridge(
            key_id="rzp_test_abc",
            key_secret="secret_xyz",
            binary_path=str(fake_bin),
        )
        assert bridge._key_id == "rzp_test_abc"
        assert bridge._key_secret == "secret_xyz"
        assert bridge._available_tools == []

    def test_session_initially_none(self, tmp_path: Path) -> None:
        """Bridge session is None before connect."""
        fake_bin = tmp_path / "razorpay-mcp-server"
        fake_bin.write_text("")

        bridge = RazorpayBridge(
            key_id="rzp_test_1234",
            key_secret="test_secret",
            binary_path=str(fake_bin),
        )
        assert bridge._session is None

    def test_custom_binary_path_stored(self, tmp_path: Path) -> None:
        """Bridge uses the provided binary path, not the default."""
        fake_bin = tmp_path / "custom-razorpay-server"
        fake_bin.write_text("")

        bridge = RazorpayBridge(
            key_id="rzp_test_1234",
            key_secret="test_secret",
            binary_path=str(fake_bin),
        )
        assert bridge._binary_path == str(fake_bin)
        assert bridge._binary_path != DEFAULT_BINARY_PATH


# ================================================================
# Binary Tests — require built Go binary, no real API credentials
# ================================================================


class TestBridgeBinary:
    """Test real Go binary spawning and MCP protocol.

    These tests build and run the actual razorpay-mcp-server binary.
    They verify MCP session establishment and tool listing —
    no Razorpay API calls are made.
    """

    @pytest.fixture
    def binary_bridge(self) -> RazorpayBridge:
        if not GO_BINARY_EXISTS:
            pytest.skip(f"Go binary not found at {DEFAULT_BINARY_PATH}")
        return RazorpayBridge(
            key_id="rzp_test_placeholder",
            key_secret="placeholder_secret",
        )

    @pytest.mark.asyncio
    async def test_ping(self, binary_bridge: RazorpayBridge) -> None:
        """Go binary spawns and responds to MCP health check."""
        result = await binary_bridge.ping()
        assert result is True

    @pytest.mark.asyncio
    async def test_list_tools(self, binary_bridge: RazorpayBridge) -> None:
        """Go binary exposes 40+ Razorpay tools via MCP."""
        tools = await binary_bridge.list_tools()
        assert len(tools) >= 40
        assert "fetch_all_payouts" in tools
        assert "fetch_payout_with_id" in tools
        assert "fetch_all_payments" in tools
        assert "fetch_payment" in tools
        assert "create_order" in tools
        assert "create_refund" in tools


# ================================================================
# API Integration Tests — require Go binary + real Razorpay credentials
# ================================================================


class TestBridgeAPI:
    """Test actual Razorpay API calls through the Go binary.

    Skipped unless real Razorpay test-mode credentials are provided.
    """

    @pytest.fixture
    def bridge(self, config: VyapaarConfig) -> RazorpayBridge:
        if not GO_BINARY_EXISTS:
            pytest.skip(f"Go binary not found at {DEFAULT_BINARY_PATH}")
        if not HAS_RAZORPAY_CREDS:
            pytest.skip("Real Razorpay credentials not available")
        return RazorpayBridge(
            key_id=config.razorpay_key_id,
            key_secret=config.razorpay_key_secret,
        )

    @pytest.fixture
    def account_number(self, config: VyapaarConfig) -> str:
        return config.razorpay_account_number

    @pytest.mark.asyncio
    async def test_fetch_all_payouts(self, bridge: RazorpayBridge, account_number: str) -> None:
        result = await bridge.fetch_all_payouts(account_number=account_number, count=5)
        assert "items" in result
        assert "count" in result
        assert isinstance(result["items"], list)

    @pytest.mark.asyncio
    async def test_fetch_all_payouts_with_status_filter(
        self, bridge: RazorpayBridge, account_number: str
    ) -> None:
        result = await bridge.fetch_all_payouts(
            account_number=account_number, count=5, status="queued"
        )
        assert "items" in result
        for item in result["items"]:
            assert item["status"] == "queued"

    @pytest.mark.asyncio
    async def test_fetch_all_payments(self, bridge: RazorpayBridge) -> None:
        result = await bridge.fetch_all_payments(count=3)
        assert "items" in result
        assert isinstance(result["items"], list)
