"""Composite Vendor Trust Score from KYB signals."""

from __future__ import annotations

from typing import Any

DEFAULT_WEIGHTS: dict[str, float] = {
    "sanctions": 0.35,
    "gstin": 0.20,
    "gleif": 0.20,
    "safe_browsing": 0.25,
}


def score_from_sanctions(sanctions_result: dict[str, Any]) -> float:
    """Higher match score → lower trust (0.0–1.0)."""
    if not sanctions_result.get("screened"):
        return 0.5
    return 1.0 - float(sanctions_result.get("max_match_score", 0))


def score_from_gstin(gstin: str, gstin_valid: bool | None = None) -> float:
    """GSTIN provided and valid → 1.0; invalid → 0.0; missing → neutral 0.5."""
    if not gstin:
        return 0.5
    if gstin_valid is None:
        return 0.5
    return 1.0 if gstin_valid else 0.0


def score_from_gleif(verified: bool | None) -> float:
    """GLEIF verified → 1.0; not found → 0.3; unavailable → neutral 0.5."""
    if verified is None:
        return 0.5
    return 1.0 if verified else 0.3


def score_from_safe_browsing(is_safe: bool | None) -> float:
    """Safe URL → 1.0; flagged → 0.0; not checked → neutral 0.5."""
    if is_safe is None:
        return 0.5
    return 1.0 if is_safe else 0.0


def compute_vendor_trust_score(
    component_scores: dict[str, float],
    weights: dict[str, float] | None = None,
) -> tuple[float, str]:
    """Compute weighted trust score and level label.

    Returns:
        (trust_score 0.0–1.0, trust_level: trusted|review|blocked)
    """
    w = weights or DEFAULT_WEIGHTS
    active = {k: component_scores[k] for k in w if k in component_scores}
    if not active:
        return 0.5, "review"

    total_weight = sum(w[k] for k in active)
    trust_score = sum(active[k] * w[k] for k in active) / total_weight

    if trust_score >= 0.8:
        return round(trust_score, 2), "trusted"
    if trust_score >= 0.5:
        return round(trust_score, 2), "review"
    return round(trust_score, 2), "blocked"


def trust_recommendation(trust_level: str) -> str:
    """Human-readable recommendation for a trust level."""
    if trust_level == "trusted":
        return "✅ Vendor cleared for payouts"
    if trust_level == "review":
        return "⚠️ Manual review recommended"
    return "🛑 Block all payouts to this vendor"
