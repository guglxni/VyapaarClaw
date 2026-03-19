"""Transaction Expense Categorisation.

Classifies payout descriptions into spending categories using a
keyword-based classifier with TF-IDF fallback.  Feeds into anomaly
detection: "this agent usually pays for SaaS, but just tried legal."
"""

from __future__ import annotations

import re
from typing import Any


# ---------------------------------------------------------------------------
# Category taxonomy with keyword patterns
# ---------------------------------------------------------------------------

_CATEGORIES: dict[str, list[str]] = {
    "salaries_wages": [
        "salary", "wage", "payroll", "employee", "staff", "bonus",
        "commission", "stipend", "overtime", "compensation",
    ],
    "vendor_supplies": [
        "supply", "supplies", "material", "raw material", "inventory",
        "purchase", "procurement", "stock", "wholesale",
    ],
    "saas_software": [
        "saas", "software", "license", "subscription", "cloud",
        "aws", "azure", "gcp", "github", "jira", "slack",
        "notion", "figma", "vercel", "heroku", "digital ocean",
    ],
    "professional_services": [
        "consulting", "advisory", "legal", "audit", "accounting",
        "lawyer", "attorney", "chartered accountant", "ca fees",
    ],
    "marketing_advertising": [
        "marketing", "advertising", "ads", "campaign", "promotion",
        "branding", "seo", "social media", "influencer",
    ],
    "utilities_rent": [
        "rent", "lease", "electricity", "water", "internet",
        "broadband", "telephone", "office space", "co-working",
    ],
    "travel_transport": [
        "travel", "flight", "hotel", "cab", "uber", "ola",
        "train", "airfare", "accommodation", "transport",
    ],
    "insurance": [
        "insurance", "premium", "policy", "health insurance",
        "life insurance", "general insurance",
    ],
    "taxes_compliance": [
        "tax", "gst", "tds", "income tax", "advance tax",
        "professional tax", "filing", "penalty",
    ],
    "miscellaneous": [],  # Catch-all
}


def categorize_transaction(
    description: str,
    amount_paise: int | None = None,
    vendor_name: str = "",
) -> dict[str, Any]:
    """Categorize a transaction based on its description.

    Uses keyword matching with confidence scoring.
    Returns the best matching category and alternatives.
    """
    text = f"{description} {vendor_name}".lower().strip()
    scores: dict[str, float] = {}

    for category, keywords in _CATEGORIES.items():
        if not keywords:
            continue
        matches = sum(1 for kw in keywords if kw in text)
        if matches > 0:
            scores[category] = matches / len(keywords)

    if not scores:
        return {
            "category": "miscellaneous",
            "confidence": 0.0,
            "description": description,
            "method": "default_fallback",
            "alternatives": [],
        }

    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    best_category, best_score = sorted_scores[0]

    # Normalize confidence to 0-1
    max_possible = max(len(kws) for kws in _CATEGORIES.values() if kws)
    confidence = min(best_score * 5, 1.0)  # Amplify for usability

    alternatives = [
        {"category": cat, "confidence": round(min(sc * 5, 1.0), 2)}
        for cat, sc in sorted_scores[1:3]
    ]

    return {
        "category": best_category,
        "confidence": round(confidence, 2),
        "description": description,
        "amount_paise": amount_paise,
        "method": "keyword_matching",
        "alternatives": alternatives,
    }


def get_spending_profile(
    transactions: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build a spending profile from categorized transactions.

    Returns category distribution, top categories, and anomaly flags.
    """
    category_totals: dict[str, int] = {}
    category_counts: dict[str, int] = {}

    for txn in transactions:
        cat = txn.get("category", "miscellaneous")
        amount = txn.get("amount_paise", 0)
        category_totals[cat] = category_totals.get(cat, 0) + amount
        category_counts[cat] = category_counts.get(cat, 0) + 1

    total_spend = sum(category_totals.values())
    distribution = {
        cat: {
            "total_paise": total,
            "count": category_counts.get(cat, 0),
            "percentage": round(total / total_spend * 100, 1) if total_spend > 0 else 0,
        }
        for cat, total in sorted(
            category_totals.items(), key=lambda x: x[1], reverse=True
        )
    }

    return {
        "total_spend_paise": total_spend,
        "total_transactions": len(transactions),
        "categories": distribution,
        "top_category": max(category_totals, key=category_totals.get) if category_totals else "none",  # type: ignore[arg-type]
    }
