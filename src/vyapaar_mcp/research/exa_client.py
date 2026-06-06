"""Exa search client for vendor research and adverse media discovery.

Uses the Exa REST API directly (same backend as exa-labs/exa-mcp-server).
MCP hosted URL: https://mcp.exa.ai/mcp
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_EXA_API_BASE = "https://api.exa.ai"


class ExaClient:
    """Async client for Exa search and research APIs."""

    def __init__(self, api_key: str, timeout: float = 30.0) -> None:
        self._api_key = api_key
        self._timeout = timeout

    def _headers(self) -> dict[str, str]:
        return {
            "x-api-key": self._api_key,
            "Content-Type": "application/json",
        }

    @property
    def configured(self) -> bool:
        return bool(self._api_key)

    async def search(
        self,
        query: str,
        num_results: int = 8,
        search_type: str = "auto",
        include_text: bool = True,
    ) -> dict[str, Any]:
        """Run a web search via Exa."""
        if not self.configured:
            return {"error": "Exa API key not configured (VYAPAAR_EXA_API_KEY)", "results": []}

        payload: dict[str, Any] = {
            "query": query,
            "numResults": num_results,
            "type": search_type,
        }
        if include_text:
            payload["contents"] = {"text": {"maxCharacters": 2000}}

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(
                    f"{_EXA_API_BASE}/search",
                    json=payload,
                    headers=self._headers(),
                )
                if resp.status_code == 429:
                    return {"error": "Exa rate limited", "results": []}
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPError as exc:
            logger.warning("Exa search failed: %s", exc)
            return {"error": str(exc), "results": []}

        results = []
        for item in data.get("results", []):
            results.append({
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "published_date": item.get("publishedDate"),
                "score": item.get("score"),
                "text": (item.get("text") or "")[:500],
            })

        return {
            "query": query,
            "result_count": len(results),
            "results": results,
        }

    async def research_vendor(
        self,
        vendor_name: str,
        extra_context: str = "",
    ) -> dict[str, Any]:
        """Company research query tuned for KYB due diligence."""
        query = f'"{vendor_name}" company business registration India'
        if extra_context:
            query += f" {extra_context}"

        search_result = await self.search(query, num_results=6)

        adverse_query = (
            f'"{vendor_name}" fraud OR scam OR investigation OR lawsuit OR penalty OR default'
        )
        adverse_result = await self.search(adverse_query, num_results=5)

        return {
            "vendor_name": vendor_name,
            "company_research": search_result,
            "adverse_signals": adverse_result,
            "summary": _summarize_research(vendor_name, search_result, adverse_result),
        }


def _summarize_research(
    vendor_name: str,
    company: dict[str, Any],
    adverse: dict[str, Any],
) -> str:
    company_count = company.get("result_count", 0)
    adverse_count = adverse.get("result_count", 0)
    if company.get("error"):
        return f"Research incomplete for {vendor_name}: {company['error']}"
    if adverse_count == 0:
        return f"Found {company_count} sources for {vendor_name}; no adverse media hits in top results."
    return (
        f"Found {company_count} company sources and {adverse_count} potential adverse signals "
        f"for {vendor_name}. Manual review recommended."
    )
