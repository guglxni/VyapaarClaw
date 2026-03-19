"""Multi-Currency Conversion via Frankfurter (FOSS, ECB data).

Provides live and historical exchange rate lookups plus conversion,
used to enforce INR-equivalent budget limits on cross-border payouts.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.frankfurter.dev"


async def get_exchange_rate(
    base: str = "USD",
    target: str = "INR",
    date: str | None = None,
) -> dict[str, Any]:
    """Fetch exchange rate from Frankfurter (ECB data, daily, no API key).

    Args:
        base: Source currency (ISO 4217).
        target: Target currency (ISO 4217).
        date: ISO date for historical rate, or None for latest.
    """
    endpoint = f"{_BASE_URL}/{date or 'latest'}"
    params = {"base": base.upper(), "symbols": target.upper()}

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(endpoint, params=params)
        resp.raise_for_status()
        data = resp.json()

    rate = data.get("rates", {}).get(target.upper())
    return {
        "base": base.upper(),
        "target": target.upper(),
        "rate": rate,
        "date": data.get("date"),
        "source": "Frankfurter (ECB)",
    }


async def convert_amount(
    amount: float,
    from_currency: str,
    to_currency: str = "INR",
    date: str | None = None,
) -> dict[str, Any]:
    """Convert *amount* between currencies.

    Returns both original and converted amounts for audit trailing.
    """
    if from_currency.upper() == to_currency.upper():
        return {
            "original_amount": amount,
            "original_currency": from_currency.upper(),
            "converted_amount": amount,
            "converted_currency": to_currency.upper(),
            "rate": 1.0,
            "date": date or "latest",
        }

    rate_data = await get_exchange_rate(from_currency, to_currency, date)
    rate = rate_data["rate"]
    if rate is None:
        raise ValueError(f"No rate found for {from_currency} → {to_currency}")

    converted = round(amount * rate, 2)
    return {
        "original_amount": amount,
        "original_currency": from_currency.upper(),
        "converted_amount": converted,
        "converted_currency": to_currency.upper(),
        "rate": rate,
        "date": rate_data["date"],
        "source": rate_data["source"],
    }


async def get_supported_currencies() -> dict[str, str]:
    """Return all currencies supported by Frankfurter."""
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(f"{_BASE_URL}/currencies")
        resp.raise_for_status()
        return resp.json()  # type: ignore[no-any-return]
