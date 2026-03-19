"""Vendor Contract Analysis.

Extracts key financial terms from vendor contracts using
pattern matching and NLP heuristics. Identifies payment
terms, penalty clauses, and SLA commitments.
"""

from __future__ import annotations

import re
from typing import Any


# ---------------------------------------------------------------------------
# Payment term patterns
# ---------------------------------------------------------------------------

_NET_TERMS = re.compile(
    r"(?:net|payment\s+(?:due|terms?|within))\s*[-:]?\s*(\d+)\s*(?:days?|business\s+days?|calendar\s+days?)",
    re.IGNORECASE,
)

_DUE_DATE = re.compile(
    r"(?:due\s+(?:on|by|within|date))\s*[-:]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d+\s+days?)",
    re.IGNORECASE,
)

_PENALTY_CLAUSE = re.compile(
    r"(?:penalty|late\s+(?:payment\s+)?(?:fee|charge|interest)|overdue\s+interest)\s*[-:]?\s*"
    r"(\d+(?:\.\d+)?)\s*%?\s*(?:per\s+(?:month|annum|day))?",
    re.IGNORECASE,
)

_AUTO_RENEWAL = re.compile(
    r"(?:auto(?:matic(?:ally)?)?[-\s]+renew(?:al|s|ed)?|shall\s+(?:automatically\s+)?renew)",
    re.IGNORECASE,
)

_TERMINATION = re.compile(
    r"(?:terminat(?:e|ion)|cancel(?:lation)?)\s*.*?(\d+)\s*(?:days?|months?|weeks?)\s*(?:notice|prior|advance|written)",
    re.IGNORECASE,
)

_AMOUNT_PATTERN = re.compile(
    r"(?:₹|INR|Rs\.?|USD|\$|EUR|€)\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)",
    re.IGNORECASE,
)

_SLA_PATTERN = re.compile(
    r"(?:SLA|service\s+level\s+agreement|uptime|availability)\s*[-:]?\s*(\d+(?:\.\d+)?)\s*%",
    re.IGNORECASE,
)

_INDEMNITY = re.compile(
    r"(?:indemnif(?:y|ication)|hold\s+harmless|liability\s+cap)",
    re.IGNORECASE,
)

_CONFIDENTIALITY = re.compile(
    r"(?:confidential(?:ity)?|non[-\s]+disclosure|NDA)",
    re.IGNORECASE,
)


def analyze_contract_text(text: str) -> dict[str, Any]:
    """Analyze contract text to extract key financial terms.

    Args:
        text: Plain text content of the contract.

    Returns:
        Dict with extracted terms, risk flags, and recommendations.
    """
    findings: list[dict[str, Any]] = []
    risk_flags: list[str] = []

    # Payment terms
    net_matches = _NET_TERMS.findall(text)
    payment_terms_days: int | None = None
    if net_matches:
        payment_terms_days = int(net_matches[0])
        findings.append({
            "type": "payment_terms",
            "value": f"Net {payment_terms_days} days",
            "days": payment_terms_days,
        })
        if payment_terms_days < 15:
            risk_flags.append("Short payment terms (< 15 days)")

    # Penalty clauses
    penalty_matches = _PENALTY_CLAUSE.findall(text)
    if penalty_matches:
        rate = float(penalty_matches[0])
        findings.append({
            "type": "penalty_clause",
            "value": f"{rate}% late payment penalty",
            "rate_percent": rate,
        })
        if rate > 2.0:
            risk_flags.append(f"High penalty rate ({rate}%)")

    # Auto-renewal
    if _AUTO_RENEWAL.search(text):
        findings.append({"type": "auto_renewal", "value": "Contract auto-renews"})
        risk_flags.append("Auto-renewal clause detected — review before expiry")

    # Termination notice
    term_matches = _TERMINATION.findall(text)
    if term_matches:
        findings.append({
            "type": "termination_notice",
            "value": f"{term_matches[0]} notice required",
        })

    # Contract values
    amounts = _AMOUNT_PATTERN.findall(text)
    if amounts:
        parsed_amounts = [float(a.replace(",", "")) for a in amounts[:5]]
        findings.append({
            "type": "contract_values",
            "values": parsed_amounts,
            "max_value": max(parsed_amounts),
        })

    # SLA
    sla_matches = _SLA_PATTERN.findall(text)
    if sla_matches:
        uptime = float(sla_matches[0])
        findings.append({
            "type": "sla",
            "value": f"{uptime}% uptime/availability",
            "uptime_percent": uptime,
        })

    # Indemnification
    if _INDEMNITY.search(text):
        findings.append({"type": "indemnification", "value": "Indemnification clause present"})

    # Confidentiality
    if _CONFIDENTIALITY.search(text):
        findings.append({"type": "confidentiality", "value": "NDA/confidentiality clause present"})

    # Risk assessment
    risk_score = len(risk_flags) / 5.0  # Normalize to 0-1
    if risk_score > 0.6:
        risk_level = "high"
    elif risk_score > 0.2:
        risk_level = "medium"
    else:
        risk_level = "low"

    return {
        "findings_count": len(findings),
        "findings": findings,
        "risk_flags": risk_flags,
        "risk_level": risk_level,
        "payment_terms_days": payment_terms_days,
        "has_penalty": bool(penalty_matches),
        "has_auto_renewal": bool(_AUTO_RENEWAL.search(text)),
        "has_indemnification": bool(_INDEMNITY.search(text)),
        "has_confidentiality": bool(_CONFIDENTIALITY.search(text)),
        "recommendation": (
            "⚠️ Review flagged risk items before proceeding"
            if risk_flags
            else "✅ No significant risk flags detected"
        ),
    }
