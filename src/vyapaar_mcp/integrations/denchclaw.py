"""DenchClaw CRM integration for VyapaarClaw.

Syncs governance audit logs and vendor KYB records into DenchClaw's
DuckDB object tables via the local web API (default http://localhost:3100).

Reference: https://github.com/DenchHQ/DenchClaw
"""

from __future__ import annotations

import logging
import re
from typing import Any

import httpx

from vyapaar_mcp.integrations.denchclaw_schema import (
    AUDIT_FIELDS,
    AUDIT_OBJECT,
    OBJECT_YAMLS,
    VENDOR_FIELDS,
    VENDOR_OBJECT,
)

logger = logging.getLogger(__name__)

_DEFAULT_URL = "http://localhost:3100"


def _sql_escape(value: Any) -> str:
    """Escape values for DuckDB raw SQL string literals."""
    return str(value).replace("'", "''").replace("\x00", "")

def _sql_identifier(value: str) -> str:
    """Strictly validate identifiers (table/column names) to prevent injection."""
    if not re.match(r"^[a-zA-Z0-9_]+$", str(value)):
        raise ValueError(f"Invalid SQL identifier: {value}")
    return str(value)


class DenchClawClient:
    """HTTP client for DenchClaw workspace CRM APIs."""

    def __init__(
        self,
        base_url: str = _DEFAULT_URL,
        enabled: bool = True,
        timeout: float = 15.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._enabled = enabled
        self._timeout = timeout
        self._field_cache: dict[str, dict[str, str]] = {}

    @property
    def configured(self) -> bool:
        return self._enabled and bool(self._base_url)

    async def is_available(self) -> bool:
        """Check if DenchClaw web UI is reachable."""
        if not self.configured:
            return False
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self._base_url}/api/workspace/list")
                return resp.status_code == 200
        except httpx.HTTPError:
            return False

    async def _execute(self, sql: str) -> list[dict[str, Any]]:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(
                f"{self._base_url}/api/workspace/execute",
                json={"sql": sql},
            )
            if resp.status_code != 200:
                data = resp.json() if resp.content else {}
                raise RuntimeError(data.get("error", f"HTTP {resp.status_code}"))
            data = resp.json()
            return data.get("rows", [])

    async def _write_file(self, path: str, content: str) -> None:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(
                f"{self._base_url}/api/workspace/file",
                json={"path": path, "content": content},
            )
            if resp.status_code not in (200, 201):
                data = resp.json() if resp.content else {}
                raise RuntimeError(data.get("error", f"HTTP {resp.status_code}"))

    async def _ensure_object(
        self,
        object_name: str,
        description: str,
        fields: list[tuple[str, str, bool]],
    ) -> str:
        """Ensure CRM object + fields exist. Returns object_id."""
        rows = await self._execute(
            "SELECT id FROM objects WHERE name = '{}'".format(_sql_escape(object_name))
        )
        if rows:
            object_id = str(rows[0]["id"])
        else:
            insert_rows = await self._execute(
                "INSERT INTO objects (name, description, default_view, immutable) "
                "VALUES ('{}', '{}', 'table', false) RETURNING id".format(_sql_escape(object_name), _sql_escape(description))
            )
            object_id = str(insert_rows[0]["id"])

        yaml_path = f"{object_name}/.object.yaml"
        try:
            await self._write_file(yaml_path, OBJECT_YAMLS[object_name])
        except RuntimeError as exc:
            logger.debug("DenchClaw yaml write skipped for %s: %s", object_name, exc)

        for idx, (field_name, field_type, required) in enumerate(fields):
            existing = await self._execute(
                "SELECT id FROM fields "
                "WHERE object_id = '{}' AND name = '{}'".format(_sql_escape(object_id), _sql_escape(field_name))
            )
            if not existing:
                await self._execute(
                    "INSERT INTO fields (object_id, name, type, required, sort_order) "
                    "VALUES ('{}', '{}', '{}', {}, {})".format(
                        _sql_escape(object_id), _sql_escape(field_name), _sql_escape(field_type), str(required).lower(), idx
                    )
                )

        await self._refresh_pivot_view(object_name, object_id, fields)
        return object_id

    async def _refresh_pivot_view(
        self,
        object_name: str,
        object_id: str,
        fields: list[tuple[str, str, bool]],
    ) -> None:
        field_names = ", ".join(
            f"'{_sql_escape(name)}'" for name, _, _ in fields
        )
        view = f"v_{re.sub(r'[^a-zA-Z0-9_]', '_', object_name)}"
        await self._execute("DROP VIEW IF EXISTS {}".format(_sql_identifier(view)))
        await self._execute(
            ("CREATE OR REPLACE VIEW {} AS "
             "PIVOT ("
             "  SELECT e.id as entry_id, e.created_at, e.updated_at,"
             "         f.name as field_name, ef.value"
             "  FROM entries e"
             "  JOIN entry_fields ef ON ef.entry_id = e.id"
             "  JOIN fields f ON f.id = ef.field_id"
             "  WHERE e.object_id = '{}' AND f.type != 'action'"
             ") ON field_name IN ({}) USING first(value)").format(
                 _sql_identifier(view), _sql_escape(object_id), field_names
             )
        )

    async def _load_field_map(self, object_id: str) -> dict[str, str]:
        if object_id in self._field_cache:
            return self._field_cache[object_id]
        rows = await self._execute(
            "SELECT id, name FROM fields WHERE object_id = '{}'".format(_sql_escape(object_id))
        )
        mapping = {str(r["name"]): str(r["id"]) for r in rows}
        self._field_cache[object_id] = mapping
        return mapping

    async def _upsert_entry(
        self,
        object_id: str,
        unique_field: str,
        unique_value: str,
        values: dict[str, str],
    ) -> str:
        """Insert or update an EAV entry keyed by a unique text field."""
        field_map = await self._load_field_map(object_id)
        unique_field_id = field_map.get(unique_field)
        if not unique_field_id:
            raise RuntimeError(f"Field '{unique_field}' not found")

        existing = await self._execute(
            ("SELECT e.id as entry_id FROM entries e "
             "JOIN entry_fields ef ON ef.entry_id = e.id "
             "WHERE e.object_id = '{}' "
             "AND ef.field_id = '{}' "
             "AND ef.value = '{}' "
             "LIMIT 1").format(
                 _sql_escape(object_id),
                 _sql_escape(unique_field_id),
                 _sql_escape(unique_value)
             )
        )

        if existing:
            entry_id = str(existing[0]["entry_id"])
        else:
            created = await self._execute(
                "INSERT INTO entries (object_id) VALUES ('{}') RETURNING id".format(_sql_escape(object_id))
            )
            entry_id = str(created[0]["id"])

        for field_name, value in values.items():
            field_id = field_map.get(field_name)
            if not field_id:
                continue
            await self._execute(
                ("INSERT INTO entry_fields (entry_id, field_id, value) "
                 "VALUES ('{}', '{}', '{}') "
                 "ON CONFLICT (entry_id, field_id) DO UPDATE SET "
                 "value = EXCLUDED.value, updated_at = now()").format(
                     _sql_escape(entry_id), _sql_escape(field_id), _sql_escape(str(value))
                 )
            )

        return entry_id

    async def ensure_schema(self) -> dict[str, Any]:
        """Bootstrap VyapaarClaw CRM objects in DenchClaw workspace."""
        audit_id = await self._ensure_object(
            AUDIT_OBJECT,
            "VyapaarClaw governance audit decisions",
            AUDIT_FIELDS,
        )
        vendor_id = await self._ensure_object(
            VENDOR_OBJECT,
            "VyapaarClaw vendor KYB records",
            VENDOR_FIELDS,
        )
        return {
            "bootstrapped": True,
            "objects": {
                AUDIT_OBJECT: audit_id,
                VENDOR_OBJECT: vendor_id,
            },
        }

    async def sync_audit_entry(self, entry: dict[str, Any]) -> dict[str, Any]:
        """Sync a single governance audit record to DenchClaw."""
        if not await self.is_available():
            return {"synced": False, "error": "DenchClaw unavailable"}

        schema = await self.ensure_schema()
        object_id = schema["objects"][AUDIT_OBJECT]
        payout_id = str(entry.get("payout_id", ""))

        entry_id = await self._upsert_entry(
            object_id,
            "Payout ID",
            payout_id,
            {
                "Payout ID": payout_id,
                "Agent ID": str(entry.get("agent_id", "")),
                "Amount Paise": str(entry.get("amount", 0)),
                "Decision": str(entry.get("decision", "")),
                "Reason Code": str(entry.get("reason_code", "")),
                "Reason Detail": str(entry.get("reason_detail", "")),
                "Vendor Name": str(entry.get("vendor_name") or ""),
                "Vendor URL": str(entry.get("vendor_url") or ""),
                "Processing Ms": str(entry.get("processing_ms") or 0),
            },
        )
        return {"synced": True, "entry_id": entry_id, "object": AUDIT_OBJECT}

    async def sync_vendor(self, vendor: dict[str, Any]) -> dict[str, Any]:
        """Sync vendor KYB record to DenchClaw."""
        if not await self.is_available():
            return {"synced": False, "error": "DenchClaw unavailable"}

        schema = await self.ensure_schema()
        object_id = schema["objects"][VENDOR_OBJECT]
        vendor_name = str(vendor.get("vendor_name", ""))

        entry_id = await self._upsert_entry(
            object_id,
            "Vendor Name",
            vendor_name,
            {
                "Vendor Name": vendor_name,
                "GSTIN": str(vendor.get("gstin") or ""),
                "Trust Score": str(vendor.get("trust_score", "")),
                "Trust Level": str(vendor.get("trust_level", "")),
                "Sanctions Status": str(vendor.get("sanctions_status", "")),
                "Last Screened": str(vendor.get("last_screened", "")),
            },
        )
        return {"synced": True, "entry_id": entry_id, "object": VENDOR_OBJECT}

    async def get_object_entries(
        self,
        object_name: str,
        page: int = 1,
        page_size: int = 50,
    ) -> dict[str, Any]:
        """Read entries from a DenchClaw object table."""
        if not await self.is_available():
            return {"entries": [], "error": "DenchClaw unavailable"}

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.get(
                f"{self._base_url}/api/workspace/objects/{object_name}",
                params={"page": page, "pageSize": page_size},
            )
            if resp.status_code != 200:
                return {"entries": [], "error": f"HTTP {resp.status_code}"}
            data = resp.json()
            return {
                "entries": data.get("entries", []),
                "total_count": data.get("totalCount", 0),
                "object": data.get("object"),
            }

    async def status(self) -> dict[str, Any]:
        """Return integration health and object stats."""
        available = await self.is_available()
        result: dict[str, Any] = {
            "enabled": self._enabled,
            "url": self._base_url,
            "available": available,
        }
        if available:
            try:
                audit = await self.get_object_entries(AUDIT_OBJECT, page_size=1)
                vendor = await self.get_object_entries(VENDOR_OBJECT, page_size=1)
                result["audit_count"] = audit.get("total_count", 0)
                result["vendor_count"] = vendor.get("total_count", 0)
            except (httpx.HTTPError, RuntimeError, KeyError) as exc:
                result["stats_error"] = str(exc)
        return result
