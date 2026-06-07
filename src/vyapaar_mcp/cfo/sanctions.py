"""Sanctions Screening & Vendor Due Diligence (KYB).

Multi-layered vendor screening:
1. OpenSanctions — global watchlist/PEP database (FOSS)
2. GLEIF — legal entity verification (when checker provided)
3. Google Safe Browsing — URL reputation (when checker provided)
4. GSTIN format validation
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import httpx

from vyapaar_mcp.cfo.tax import validate_gstin
from vyapaar_mcp.reputation.trust_score import (
    compute_vendor_trust_score,
    score_from_gleif,
    score_from_gstin,
    score_from_safe_browsing,
    score_from_sanctions,
    trust_recommendation,
)

if TYPE_CHECKING:
    from vyapaar_mcp.reputation.gleif import GLEIFChecker
    from vyapaar_mcp.reputation.safe_browsing import SafeBrowsingChecker

logger = logging.getLogger(__name__)

_OPENSANCTIONS_API = "https://api.opensanctions.org"


async def screen_against_sanctions(
    entity_name: str,
    entity_type: str = "Company",
) -> dict[str, Any]:
    """Screen an entity against OpenSanctions watchlists.

    OpenSanctions is a FOSS database of sanctions targets,
    politically exposed persons (PEPs), and criminal entities.
    Free API with rate limits.

    Args:
        entity_name: Name of the entity to screen.
        entity_type: "Company" or "Person".
    """
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{_OPENSANCTIONS_API}/match/default",
                params={
                    "q": entity_name,
                    "schema": entity_type,
                    "limit": 5,
                },
            )

            if resp.status_code == 429:
                return {
                    "screened": False,
                    "entity": entity_name,
                    "error": "Rate limited — retry later",
                    "risk_level": "unknown",
                }

            if resp.status_code != 200:
                return {
                    "screened": False,
                    "entity": entity_name,
                    "error": f"API returned {resp.status_code}",
                    "risk_level": "unknown",
                }

            data = resp.json()
            results = data.get("results", [])

    except httpx.HTTPError as exc:
        logger.warning("OpenSanctions API error: %s", exc)
        return {
            "screened": False,
            "entity": entity_name,
            "error": str(exc),
            "risk_level": "unknown",
        }

    if not results:
        return {
            "screened": True,
            "entity": entity_name,
            "matches": 0,
            "risk_level": "clear",
            "details": [],
        }

    matches = []
    max_score = 0.0
    for result in results:
        score = result.get("score", 0)
        max_score = max(max_score, score)
        matches.append(
            {
                "name": result.get("caption", ""),
                "score": score,
                "schema": result.get("schema", ""),
                "datasets": [d.get("name", "") for d in result.get("datasets", [])],
                "properties": {
                    k: v
                    for k, v in result.get("properties", {}).items()
                    if k in ("country", "topics", "alias", "birthDate")
                },
            }
        )

    if max_score > 0.8:
        risk_level = "critical"
    elif max_score > 0.5:
        risk_level = "high"
    elif max_score > 0.3:
        risk_level = "medium"
    else:
        risk_level = "low"

    return {
        "screened": True,
        "entity": entity_name,
        "matches": len(matches),
        "max_match_score": round(max_score, 2),
        "risk_level": risk_level,
        "details": matches,
        "recommendation": (
            "BLOCK — entity appears on sanctions list"
            if risk_level == "critical"
            else "REVIEW — potential match found"
            if risk_level in ("high", "medium")
            else "PASS — no significant matches"
        ),
    }


async def comprehensive_vendor_screen(
    vendor_name: str,
    vendor_url: str = "",
    gstin: str = "",
    gleif_checker: GLEIFChecker | None = None,
    safe_browsing_checker: SafeBrowsingChecker | None = None,
) -> dict[str, Any]:
    """Run a multi-layer vendor due diligence check.

    Combines:
    1. Sanctions screening (OpenSanctions)
    2. GLEIF entity verification (optional checker)
    3. Google Safe Browsing URL check (optional checker)
    4. GSTIN format validation (if provided)
    5. Composite Vendor Trust Score
    """
    sanctions_result = await screen_against_sanctions(vendor_name)

    gleif_result: dict[str, Any] | None = None
    gleif_verified: bool | None = None
    if gleif_checker is not None:
        gleif_response = await gleif_checker.search_entity(vendor_name)
        gleif_verified = gleif_response.is_verified
        gleif_result = {
            "verified": gleif_verified,
            "match_count": gleif_response.match_count,
            "error": gleif_response.error,
        }

    safe_browsing_result: dict[str, Any] | None = None
    url_safe: bool | None = None
    if safe_browsing_checker is not None and vendor_url:
        sb = await safe_browsing_checker.check_url(vendor_url)
        url_safe = sb.is_safe
        safe_browsing_result = {
            "url": vendor_url,
            "safe": url_safe,
            "threat_types": sb.threat_types,
        }

    gstin_valid: bool | None = None
    if gstin:
        gstin_result = validate_gstin(gstin)
        gstin_valid = bool(gstin_result.get("valid"))

    scores: dict[str, float] = {
        "sanctions": score_from_sanctions(sanctions_result),
        "gstin": score_from_gstin(gstin, gstin_valid),
        "gleif": score_from_gleif(gleif_verified),
        "safe_browsing": score_from_safe_browsing(url_safe),
    }

    trust_score, trust_level = compute_vendor_trust_score(scores)

    return {
        "vendor_name": vendor_name,
        "vendor_url": vendor_url,
        "trust_score": trust_score,
        "trust_level": trust_level,
        "component_scores": scores,
        "sanctions": sanctions_result,
        "gleif": gleif_result,
        "safe_browsing": safe_browsing_result,
        "recommendation": trust_recommendation(trust_level),
    }
