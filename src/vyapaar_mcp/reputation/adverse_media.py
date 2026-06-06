"""Adverse media screening for vendor KYB.

Pattern inspired by plutopulp/adverse-media-screening:
search → classify → score risk from news/fraud signals.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from vyapaar_mcp.research.exa_client import ExaClient

logger = logging.getLogger(__name__)

_ADVERSE_KEYWORDS = re.compile(
    r"\b(fraud|scam|ponzi|money\s*launder|sanction|bribery|corrupt|"
    r"investigation|lawsuit|penalty|fine|default|bankrupt|insolv|"
    r"blacklist|shell\s*company|fake|forgery|embezzle)\b",
    re.IGNORECASE,
)

_POSITIVE_KEYWORDS = re.compile(
    r"\b(award|certified|iso|trusted|leader|growth|partnership)\b",
    re.IGNORECASE,
)


async def screen_adverse_media(
    vendor_name: str,
    exa_client: ExaClient | None = None,
    extra_queries: list[str] | None = None,
) -> dict[str, Any]:
    """Screen a vendor for adverse media using Exa search + keyword scoring.

    Returns risk_level (clear/low/medium/high) and flagged articles.
    """
    if exa_client is None or not exa_client.configured:
        return {
            "vendor_name": vendor_name,
            "screened": False,
            "risk_level": "unknown",
            "error": "Exa not configured — set VYAPAAR_EXA_API_KEY",
            "flagged_articles": [],
            "recommendation": "Configure Exa for adverse media screening",
        }

    queries = [
        f'"{vendor_name}" fraud OR scam OR investigation',
        f'"{vendor_name}" penalty OR lawsuit OR default',
    ]
    if extra_queries:
        queries.extend(extra_queries)

    all_results: list[dict[str, Any]] = []
    for query in queries:
        result = await exa_client.search(query, num_results=5)
        if result.get("error"):
            logger.warning("Adverse media search error: %s", result["error"])
            continue
        all_results.extend(result.get("results", []))

    flagged: list[dict[str, Any]] = []
    positive_hits = 0
    for article in all_results:
        text = f"{article.get('title', '')} {article.get('text', '')}"
        adverse_matches = _ADVERSE_KEYWORDS.findall(text)
        if adverse_matches:
            flagged.append({
                **article,
                "matched_keywords": list(set(m.lower() for m in adverse_matches)),
                "severity": _severity_from_keywords(adverse_matches),
            })
        if _POSITIVE_KEYWORDS.search(text):
            positive_hits += 1

    # Deduplicate by URL
    seen_urls: set[str] = set()
    unique_flagged: list[dict[str, Any]] = []
    for f in flagged:
        url = f.get("url", "")
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique_flagged.append(f)

    risk_level = _aggregate_risk(unique_flagged, positive_hits)

    return {
        "vendor_name": vendor_name,
        "screened": True,
        "risk_level": risk_level,
        "articles_scanned": len(all_results),
        "flagged_count": len(unique_flagged),
        "flagged_articles": unique_flagged[:10],
        "positive_signals": positive_hits,
        "recommendation": _recommendation(risk_level),
    }


def _severity_from_keywords(matches: list[str]) -> str:
    critical = {"fraud", "scam", "money launder", "sanction", "blacklist", "ponzi"}
    normalized = {m.lower().replace(" ", "") for m in matches}
    for kw in critical:
        if kw.replace(" ", "") in normalized or any(kw in m.lower() for m in matches):
            return "high"
    return "medium"


def _aggregate_risk(flagged: list[dict[str, Any]], positive: int) -> str:
    if not flagged:
        return "clear"
    high_count = sum(1 for f in flagged if f.get("severity") == "high")
    if high_count >= 2:
        return "high"
    if high_count >= 1 or len(flagged) >= 3:
        return "medium"
    if len(flagged) >= 1 and positive >= 2:
        return "low"
    return "low" if flagged else "clear"


def _recommendation(risk_level: str) -> str:
    return {
        "clear": "PASS — no adverse media detected",
        "low": "MONITOR — minor signals, continue with audit flag",
        "medium": "REVIEW — adverse media found, manual KYB required",
        "high": "BLOCK — serious adverse media, reject payouts",
        "unknown": "SKIP — screening unavailable",
    }.get(risk_level, "REVIEW")
