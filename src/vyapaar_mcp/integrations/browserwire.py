"""Browserwire REST client for government portal lookups.

Browserwire (gearsec/browserwire) records browser sessions on govt portals
and exposes them as deterministic REST APIs — useful for GST/MCA lookups
behind CAPTCHA walls.

Reference: https://github.com/gearsec/browserwire
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class BrowserwireClient:
    """HTTP client for a Browserwire-trained portal manifest."""

    def __init__(
        self,
        base_url: str,
        api_key: str = "",
        timeout: float = 30.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout = timeout

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        return headers

    async def lookup_gstin(self, gstin: str) -> dict[str, Any]:
        """Look up GSTIN registration status via Browserwire GST manifest.

        Expected manifest endpoint: POST /gst/lookup with {"gstin": "..."}
        Response shape (convention):
          {"status": "Active"|"Cancelled"|"Suspended", "legal_name": "...", ...}
        """
        gstin = gstin.strip().upper()
        if not self._base_url:
            return {
                "verified": False,
                "gstin": gstin,
                "error": "Browserwire not configured (VYAPAAR_BROWSERWIRE_URL)",
                "tier": "browserwire",
            }

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(
                    f"{self._base_url}/gst/lookup",
                    json={"gstin": gstin},
                    headers=self._headers(),
                )
                if resp.status_code == 404:
                    return {
                        "verified": False,
                        "gstin": gstin,
                        "error": "GSTIN not found on portal",
                        "tier": "browserwire",
                    }
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPError as exc:
            logger.warning("Browserwire GST lookup failed: %s", exc)
            return {
                "verified": False,
                "gstin": gstin,
                "error": str(exc),
                "tier": "browserwire",
            }

        status = (data.get("status") or data.get("registration_status") or "").strip()
        legal_name = data.get("legal_name") or data.get("trade_name") or ""

        return {
            "verified": True,
            "gstin": gstin,
            "status": status or "Unknown",
            "legal_name": legal_name,
            "raw": data,
            "tier": "browserwire",
            "active": status.lower() in ("active", "valid", "registered"),
            "cancelled": "cancel" in status.lower(),
            "suspended": "suspend" in status.lower(),
        }

    async def lookup_mca(self, cin: str) -> dict[str, Any]:
        """Look up MCA company data via Browserwire MCA manifest."""
        cin = cin.strip().upper()
        if not self._base_url:
            return {"verified": False, "cin": cin, "error": "Browserwire not configured"}

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(
                    f"{self._base_url}/mca/lookup",
                    json={"cin": cin},
                    headers=self._headers(),
                )
                resp.raise_for_status()
                return {"verified": True, "cin": cin, **resp.json()}
        except httpx.HTTPError as exc:
            return {"verified": False, "cin": cin, "error": str(exc)}
