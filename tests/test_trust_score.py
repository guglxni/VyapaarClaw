"""Tests for composite Vendor Trust Score."""

from __future__ import annotations

import pytest

from vyapaar_mcp.reputation.trust_score import (
    compute_vendor_trust_score,
    score_from_gleif,
    score_from_gstin,
    score_from_safe_browsing,
    score_from_sanctions,
    trust_recommendation,
)


class TestTrustScore:
    """Unit tests for trust score helpers."""

    def test_score_from_sanctions_clear(self) -> None:
        assert score_from_sanctions({"screened": True, "max_match_score": 0.0}) == 1.0

    def test_score_from_sanctions_critical(self) -> None:
        assert score_from_sanctions({"screened": True, "max_match_score": 0.9}) == pytest.approx(0.1)

    def test_score_from_sanctions_unknown(self) -> None:
        assert score_from_sanctions({"screened": False}) == 0.5

    def test_score_from_gstin_valid(self) -> None:
        assert score_from_gstin("27AAPFU0939F1ZV", True) == 1.0

    def test_score_from_gstin_missing(self) -> None:
        assert score_from_gstin("", None) == 0.5

    def test_score_from_gleif_verified(self) -> None:
        assert score_from_gleif(True) == 1.0
        assert score_from_gleif(False) == 0.3
        assert score_from_gleif(None) == 0.5

    def test_score_from_safe_browsing(self) -> None:
        assert score_from_safe_browsing(True) == 1.0
        assert score_from_safe_browsing(False) == 0.0

    def test_compute_trusted_vendor(self) -> None:
        scores = {
            "sanctions": 0.95,
            "gstin": 1.0,
            "gleif": 1.0,
            "safe_browsing": 1.0,
        }
        trust_score, level = compute_vendor_trust_score(scores)
        assert trust_score >= 0.8
        assert level == "trusted"

    def test_compute_blocked_vendor(self) -> None:
        scores = {
            "sanctions": 0.05,
            "gstin": 0.0,
            "gleif": 0.3,
            "safe_browsing": 0.0,
        }
        trust_score, level = compute_vendor_trust_score(scores)
        assert trust_score < 0.5
        assert level == "blocked"

    def test_trust_recommendation_labels(self) -> None:
        assert "✅" in trust_recommendation("trusted")
        assert "⚠️" in trust_recommendation("review")
        assert "🛑" in trust_recommendation("blocked")
