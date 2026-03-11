"""Tests for the RazorpayBridge — real initialization tests.

Unit tests create real temporary files to satisfy the binary
existence check. No mocking, no patching.

Integration tests (TestBridgeConnectivity) require the actual
Go binary built at bin/razorpay-mcp-server and are skipped in
CI where Go is not available.
"""

from __future__ import annotations

import os
import stat
from pathlib import Path

import pytest

from vyapaar_mcp.config import VyapaarConfig
from vyapaar_mcp.ingress.razorpay_bridge import DEFAULT_BINARY_PATH, RazorpayBridge

GO_BINARY_EXISTS = os.path.isfile(DEFAULT_BINARY_PATH)

_requires_go_binary = pytest.mark.skipif(
    not GO_BINARY_EXISTS,
    reason=f"Go binary not found at {DEFAULT_BINARY_PATH}",
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
# Integration Tests (require real Go binary + API credentials)
# ================================================================


@pytest.fixture
def bridge(config: VyapaarConfig) -> RazorpayBridge:
    """Create a bridge with test credentials (skips if Go binary missing)."""
    if not GO_BINARY_EXISTS:
        pytest.skip(f"Go binary not found at {DEFAULT_BINARY_PATH}")
    return RazorpayBridge(
        key_id=config.razorpay_key_id,
        key_secret=config.razorpay_key_secret,
    )


@pytest.fixture
def account_number(config: VyapaarConfig) -> str:
    """Get account number from config."""
    return config.razorpay_account_number


@_requires_go_binary
class TestBridgeConnectivity:
    """Test MCP subprocess communication with Go binary."""

    async def test_ping(self, bridge: RazorpayBridge) -> None:
        result = await bridge.ping()
        assert result is True

    async def test_list_tools(self, bridge: RazorpayBridge) -> None:
        tools = await bridge.list_tools()
        assert len(tools) >= 40
        assert "fetch_all_payouts" in tools
        assert "fetch_all_payments" in tools

    async def test_fetch_all_payouts(self, bridge: RazorpayBridge, account_number: str) -> None:
        result = await bridge.fetch_all_payouts(account_number=account_number, count=5)
        assert "items" in result
        assert "count" in result
        assert isinstance(result["items"], list)

    async def test_fetch_all_payouts_with_status_filter(
        self, bridge: RazorpayBridge, account_number: str
    ) -> None:
        result = await bridge.fetch_all_payouts(
            account_number=account_number, count=5, status="queued"
        )
        assert "items" in result
        for item in result["items"]:
            assert item["status"] == "queued"

    async def test_fetch_all_payments(self, bridge: RazorpayBridge) -> None:
        result = await bridge.fetch_all_payments(count=3)
        assert "items" in result
        assert isinstance(result["items"], list)
