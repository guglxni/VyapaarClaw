"""Sanctions Screening & Vendor Due Diligence (KYB).

Multi-layered vendor screening:
1. OpenSanctions — global watchlist/PEP database (FOSS)
2. Negative news — basic adverse media signals
3. Integrates with existing GLEIF + Safe Browsing checks
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

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
        matches.append({
            "name": result.get("caption", ""),
            "score": score,
            "schema": result.get("schema", ""),
            "datasets": [d.get("name", "") for d in result.get("datasets", [])],
            "properties": {
                k: v for k, v in result.get("properties", {}).items()
                if k in ("country", "topics", "alias", "birthDate")
            },
        })

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
) -> dict[str, Any]:
    """Run a multi-layer vendor due diligence check.

    Combines:
    1. Sanctions screening (OpenSanctions)
    2. GSTIN validation (if provided)
    3. Produces a composite trust score

    Note: GLEIF and Safe Browsing checks are handled by existing
    VyapaarClaw reputation modules. This function adds the
    sanctions layer on top.
    """
    sanctions_result = await screen_against_sanctions(vendor_name)

    # Composite scoring
    scores: dict[str, float] = {}

    # Sanctions score (inverted — high match = low trust)
    if sanctions_result.get("screened"):
        sanctions_score = 1.0 - sanctions_result.get("max_match_score", 0)
        scores["sanctions"] = sanctions_score
    else:
        scores["sanctions"] = 0.5  # Unknown = medium risk

    # GSTIN score (if provided)
    if gstin:
        from vyapaar_mcp.cfo.tax import validate_gstin
        gstin_result = validate_gstin(gstin)
        scores["gstin"] = 1.0 if gstin_result.get("valid") else 0.0
    else:
        scores["gstin"] = 0.5  # Not provided = neutral

    # Composite trust score
    weights = {"sanctions": 0.6, "gstin": 0.4}
    trust_score = sum(scores[k] * weights[k] for k in scores)

    if trust_score >= 0.8:
        trust_level = "trusted"
    elif trust_score >= 0.5:
        trust_level = "review"
    else:
        trust_level = "blocked"

    return {
        "vendor_name": vendor_name,
        "vendor_url": vendor_url,
        "trust_score": round(trust_score, 2),
        "trust_level": trust_level,
        "component_scores": scores,
        "sanctions": sanctions_result,
        "recommendation": (
            "✅ Vendor cleared for payouts"
            if trust_level == "trusted"
            else "⚠️ Manual review recommended"
            if trust_level == "review"
            else "🛑 Block all payouts to this vendor"
        ),
    }
