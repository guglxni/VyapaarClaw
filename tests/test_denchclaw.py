"""Tests for DenchClaw CRM integration."""

from __future__ import annotations

import json

import httpx
import pytest

from vyapaar_mcp.integrations.denchclaw import DenchClawClient
from vyapaar_mcp.integrations.denchclaw_schema import AUDIT_OBJECT, VENDOR_OBJECT


def _dench_handler(responses: dict[str, object]):
    """Build a MockTransport handler for DenchClaw API routes."""

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/api/workspace/list":
            return httpx.Response(200, json={"workspaces": ["default"]})
        if path == "/api/workspace/execute":
            body = json.loads(request.content)
            sql = body.get("sql", "")
            if "SELECT id FROM objects WHERE name = 'vyapaar_audit'" in sql:
                return httpx.Response(200, json={"rows": []})
            if "INSERT INTO objects" in sql and "vyapaar_audit" in sql:
                return httpx.Response(200, json={"rows": [{"id": "audit-obj-1"}]})
            if "SELECT id FROM objects WHERE name = 'vyapaar_vendor'" in sql:
                return httpx.Response(200, json={"rows": []})
            if "INSERT INTO objects" in sql and "vyapaar_vendor" in sql:
                return httpx.Response(200, json={"rows": [{"id": "vendor-obj-1"}]})
            if "SELECT id, name FROM fields" in sql:
                return httpx.Response(
                    200,
                    json={
                        "rows": [
                            {"id": "f1", "name": "Payout ID"},
                            {"id": "f2", "name": "Agent ID"},
                            {"id": "f3", "name": "Amount Paise"},
                            {"id": "f4", "name": "Decision"},
                            {"id": "f5", "name": "Reason Code"},
                            {"id": "f6", "name": "Reason Detail"},
                            {"id": "f7", "name": "Vendor Name"},
                            {"id": "f8", "name": "Vendor URL"},
                            {"id": "f9", "name": "Processing Ms"},
                        ]
                    },
                )
            if "INSERT INTO entries" in sql:
                return httpx.Response(200, json={"rows": [{"id": "entry-1"}]})
            if "SELECT e.id as entry_id" in sql:
                return httpx.Response(200, json={"rows": []})
            return httpx.Response(200, json={"rows": []})
        if path == "/api/workspace/file":
            return httpx.Response(200, json={"ok": True})
        if path == f"/api/workspace/objects/{AUDIT_OBJECT}":
            return httpx.Response(
                200,
                json={
                    "entries": [{"Payout ID": "pout_1", "Decision": "APPROVED"}],
                    "totalCount": 1,
                    "object": AUDIT_OBJECT,
                },
            )
        if path == f"/api/workspace/objects/{VENDOR_OBJECT}":
            return httpx.Response(
                200,
                json={
                    "entries": [],
                    "totalCount": 0,
                    "object": VENDOR_OBJECT,
                },
            )
        return httpx.Response(404, json={"error": "not found"})

    return handler


@pytest.fixture
def dench_client(monkeypatch: pytest.MonkeyPatch) -> DenchClawClient:
    """DenchClawClient with mocked HTTP transport."""
    client = DenchClawClient(base_url="http://localhost:3100", enabled=True)

    transport = httpx.MockTransport(_dench_handler({}))

    async def mock_execute(sql: str) -> list[dict]:
        async with httpx.AsyncClient(transport=transport) as http:
            resp = await http.post(
                "http://localhost:3100/api/workspace/execute",
                json={"sql": sql},
            )
            return resp.json().get("rows", [])

    async def mock_write(path: str, content: str) -> None:
        async with httpx.AsyncClient(transport=transport) as http:
            resp = await http.post(
                "http://localhost:3100/api/workspace/file",
                json={"path": path, "content": content},
            )
            if resp.status_code not in (200, 201):
                raise RuntimeError(f"HTTP {resp.status_code}")

    async def mock_available() -> bool:
        return True

    monkeypatch.setattr(client, "_execute", mock_execute)
    monkeypatch.setattr(client, "_write_file", mock_write)
    monkeypatch.setattr(client, "is_available", mock_available)
    return client


@pytest.mark.asyncio
async def test_ensure_schema_bootstraps_objects(dench_client: DenchClawClient) -> None:
    result = await dench_client.ensure_schema()
    assert result["bootstrapped"] is True
    assert AUDIT_OBJECT in result["objects"]
    assert VENDOR_OBJECT in result["objects"]


@pytest.mark.asyncio
async def test_sync_audit_entry(dench_client: DenchClawClient) -> None:
    result = await dench_client.sync_audit_entry(
        {
            "payout_id": "pout_test_001",
            "agent_id": "procurement-bot",
            "amount": 45000,
            "decision": "APPROVED",
            "reason_code": "POLICY_OK",
            "reason_detail": "All checks passed",
            "vendor_name": "Acme Corp",
            "processing_ms": 42,
        }
    )
    assert result["synced"] is True
    assert result["object"] == AUDIT_OBJECT


@pytest.mark.asyncio
async def test_sync_vendor(dench_client: DenchClawClient) -> None:
    result = await dench_client.sync_vendor(
        {
            "vendor_name": "Acme Corp",
            "gstin": "27AABCU9603R1ZM",
            "trust_score": 0.85,
            "trust_level": "HIGH",
            "sanctions_status": "CLEAR",
            "last_screened": "2026-06-06T12:00:00Z",
        }
    )
    assert result["synced"] is True
    assert result["object"] == VENDOR_OBJECT


@pytest.mark.asyncio
async def test_status_when_available(dench_client: DenchClawClient) -> None:
    transport = httpx.MockTransport(_dench_handler({}))

    async def mock_get_entries(object_name: str, page: int = 1, page_size: int = 50) -> dict:
        async with httpx.AsyncClient(transport=transport) as http:
            resp = await http.get(
                f"http://localhost:3100/api/workspace/objects/{object_name}",
                params={"page": page, "pageSize": page_size},
            )
            data = resp.json()
            return {
                "entries": data.get("entries", []),
                "total_count": data.get("totalCount", 0),
                "object": data.get("object"),
            }

    dench_client.get_object_entries = mock_get_entries  # type: ignore[method-assign]
    status = await dench_client.status()
    assert status["enabled"] is True
    assert status["available"] is True
    assert status["audit_count"] == 1


@pytest.mark.asyncio
async def test_disabled_client_returns_unavailable() -> None:
    client = DenchClawClient(enabled=False)
    assert await client.is_available() is False
    result = await client.sync_audit_entry({"payout_id": "x"})
    assert result["synced"] is False
