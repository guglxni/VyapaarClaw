"""Tiered GSTIN verification providers.

T1: Format + checksum (offline, tax.py)
T2: Browserwire portal scrape
T3: GSP API (Cashfree Secure ID, ClearTax, Gridlines)
"""

from __future__ import annotations

import logging
from typing import Any, Protocol, runtime_checkable

import httpx

from vyapaar_mcp.cfo.tax import validate_gstin
from vyapaar_mcp.integrations.browserwire import BrowserwireClient

logger = logging.getLogger(__name__)


@runtime_checkable
class GstVerificationProvider(Protocol):
    """Protocol for GSTIN verification backends."""

    @property
    def tier(self) -> str:
        """Provider tier label: format, browserwire, gsp."""

    async def verify(self, gstin: str, vendor_name: str = "") -> dict[str, Any]:
        """Verify GSTIN and return normalized result dict."""


class FormatGstProvider:
    """T1 — offline format and checksum validation."""

    tier = "format"

    async def verify(self, gstin: str, vendor_name: str = "") -> dict[str, Any]:
        result = validate_gstin(gstin)
        return {
            "tier": self.tier,
            "valid": result.get("valid", False),
            "gstin": gstin.strip().upper(),
            "status": "format_valid" if result.get("valid") else "invalid_format",
            "legal_name": "",
            "name_match": None,
            "details": result,
            "recommendation": "PASS" if result.get("valid") else "REJECT",
        }


class BrowserwireGstProvider:
    """T2 — live portal status via Browserwire manifest."""

    tier = "browserwire"

    def __init__(self, client: BrowserwireClient) -> None:
        self._client = client

    async def verify(self, gstin: str, vendor_name: str = "") -> dict[str, Any]:
        fmt = validate_gstin(gstin)
        if not fmt.get("valid"):
            return {
                "tier": self.tier,
                "valid": False,
                "gstin": gstin,
                "status": "invalid_format",
                "recommendation": "REJECT",
                "details": fmt,
            }

        live = await self._client.lookup_gstin(gstin)
        if not live.get("verified"):
            return {
                "tier": self.tier,
                "valid": True,
                "gstin": gstin,
                "status": "lookup_failed",
                "live_verified": False,
                "recommendation": "REVIEW",
                "details": live,
            }

        status = live.get("status", "Unknown")
        legal_name = live.get("legal_name", "")
        name_match = _fuzzy_name_match(vendor_name, legal_name) if vendor_name and legal_name else None

        if live.get("cancelled"):
            recommendation = "REJECT"
        elif live.get("suspended"):
            recommendation = "HOLD"
        elif name_match is False:
            recommendation = "HOLD"
        else:
            recommendation = "PASS"

        return {
            "tier": self.tier,
            "valid": True,
            "gstin": gstin,
            "status": status,
            "legal_name": legal_name,
            "live_verified": True,
            "name_match": name_match,
            "active": live.get("active", False),
            "cancelled": live.get("cancelled", False),
            "suspended": live.get("suspended", False),
            "recommendation": recommendation,
            "details": live,
        }


class GspGstProvider:
    """T3 — commercial GSP API (Cashfree Secure ID pattern)."""

    tier = "gsp"

    def __init__(self, api_url: str, api_key: str) -> None:
        self._api_url = api_url.rstrip("/")
        self._api_key = api_key

    async def verify(self, gstin: str, vendor_name: str = "") -> dict[str, Any]:
        fmt = validate_gstin(gstin)
        if not fmt.get("valid"):
            return {
                "tier": self.tier,
                "valid": False,
                "gstin": gstin,
                "status": "invalid_format",
                "recommendation": "REJECT",
                "details": fmt,
            }

        if not self._api_url or not self._api_key:
            return {
                "tier": self.tier,
                "valid": True,
                "gstin": gstin,
                "status": "gsp_not_configured",
                "live_verified": False,
                "recommendation": "REVIEW",
                "error": "Set VYAPAAR_GSP_API_URL and VYAPAAR_GSP_API_KEY",
            }

        try:
            async with httpx.AsyncClient(timeout=20) as client:
                resp = await client.get(
                    f"{self._api_url}/gstin/{gstin}",
                    headers={"Authorization": f"Bearer {self._api_key}"},
                )
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPError as exc:
            logger.warning("GSP GST lookup failed: %s", exc)
            return {
                "tier": self.tier,
                "valid": True,
                "gstin": gstin,
                "status": "gsp_error",
                "live_verified": False,
                "recommendation": "REVIEW",
                "error": str(exc),
            }

        status = data.get("status") or data.get("registration_status") or "Unknown"
        legal_name = data.get("legal_name") or data.get("tradeNam") or ""
        name_match = _fuzzy_name_match(vendor_name, legal_name) if vendor_name and legal_name else None

        cancelled = "cancel" in status.lower()
        suspended = "suspend" in status.lower()
        if cancelled:
            recommendation = "REJECT"
        elif suspended:
            recommendation = "HOLD"
        elif name_match is False:
            recommendation = "HOLD"
        else:
            recommendation = "PASS"

        return {
            "tier": self.tier,
            "valid": True,
            "gstin": gstin,
            "status": status,
            "legal_name": legal_name,
            "live_verified": True,
            "name_match": name_match,
            "cancelled": cancelled,
            "suspended": suspended,
            "recommendation": recommendation,
            "details": data,
        }


def _fuzzy_name_match(expected: str, actual: str) -> bool:
    """Simple normalized name comparison for KYB."""
    def norm(s: str) -> str:
        return "".join(c for c in s.upper() if c.isalnum())

    a, b = norm(expected), norm(actual)
    if not a or not b:
        return True
    return a in b or b in a or _token_overlap(a, b) >= 0.5


def _token_overlap(a: str, b: str) -> float:
    ta = {t for t in a.split() if len(t) > 2} if " " in a else set(a[i:i+4] for i in range(0, len(a), 4))
    tb = {t for t in b.split() if len(t) > 2} if " " in b else set(b[i:i+4] for i in range(0, len(b), 4))
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / max(len(ta), len(tb))


class GstVerificationChain:
    """Run providers in tier order until live verification succeeds."""

    def __init__(self, providers: list[GstVerificationProvider]) -> None:
        self._providers = providers

    async def verify(self, gstin: str, vendor_name: str = "") -> dict[str, Any]:
        results: list[dict[str, Any]] = []
        best: dict[str, Any] | None = None

        for provider in self._providers:
            result = await provider.verify(gstin, vendor_name)
            results.append(result)
            if not result.get("valid"):
                return {**result, "chain": results}

            if result.get("live_verified") or result.get("tier") == "format":
                best = result
            if result.get("live_verified") and result.get("recommendation") in ("PASS", "REJECT"):
                return {**result, "chain": results}

        return {**(best or results[-1]), "chain": results}


def build_gst_chain(
    browserwire_url: str = "",
    browserwire_key: str = "",
    gsp_url: str = "",
    gsp_key: str = "",
    enable_live: bool = True,
) -> GstVerificationChain:
    """Factory for the configured provider chain."""
    providers: list[GstVerificationProvider] = [FormatGstProvider()]

    if enable_live and browserwire_url:
        providers.append(BrowserwireGstProvider(BrowserwireClient(browserwire_url, browserwire_key)))

    if enable_live and gsp_url and gsp_key:
        providers.append(GspGstProvider(gsp_url, gsp_key))

    return GstVerificationChain(providers)
