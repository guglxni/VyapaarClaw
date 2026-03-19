"""GST & India Tax Compliance.

Validates GSTINs, calculates GST (CGST/SGST/IGST), and checks TDS
applicability on vendor payouts.
"""

from __future__ import annotations

import re
from typing import Any


# GSTIN format: 2-digit state code + 10-char PAN + 1-digit entity number + Z + 1-digit checksum
_GSTIN_PATTERN = re.compile(
    r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][0-9A-Z]Z[0-9A-Z]$"
)

_STATE_CODES: dict[str, str] = {
    "01": "Jammu & Kashmir", "02": "Himachal Pradesh", "03": "Punjab",
    "04": "Chandigarh", "05": "Uttarakhand", "06": "Haryana",
    "07": "Delhi", "08": "Rajasthan", "09": "Uttar Pradesh",
    "10": "Bihar", "11": "Sikkim", "12": "Arunachal Pradesh",
    "13": "Nagaland", "14": "Manipur", "15": "Mizoram",
    "16": "Tripura", "17": "Meghalaya", "18": "Assam",
    "19": "West Bengal", "20": "Jharkhand", "21": "Odisha",
    "22": "Chhattisgarh", "23": "Madhya Pradesh", "24": "Gujarat",
    "26": "Dadra & Nagar Haveli", "27": "Maharashtra", "29": "Karnataka",
    "30": "Goa", "31": "Lakshadweep", "32": "Kerala",
    "33": "Tamil Nadu", "34": "Puducherry", "35": "Andaman & Nicobar",
    "36": "Telangana", "37": "Andhra Pradesh", "38": "Ladakh",
}

_GSTIN_CHARSET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def _compute_gstin_checksum(gstin_14: str) -> str:
    """Compute the checksum digit for a 14-character GSTIN prefix."""
    factor = 1
    total = 0
    for char in gstin_14:
        idx = _GSTIN_CHARSET.index(char)
        digit = idx * factor
        digit = (digit // 36) + (digit % 36)
        total += digit
        factor = 2 if factor == 1 else 1
    remainder = total % 36
    check_code_idx = (36 - remainder) % 36
    return _GSTIN_CHARSET[check_code_idx]


def validate_gstin(gstin: str) -> dict[str, Any]:
    """Validate an Indian GSTIN and extract metadata.

    Returns:
        Dict with validation result, state, PAN, entity type, etc.
    """
    gstin = gstin.strip().upper()

    if not _GSTIN_PATTERN.match(gstin):
        return {"valid": False, "gstin": gstin, "error": "Invalid format"}

    state_code = gstin[:2]
    pan = gstin[2:12]
    state_name = _STATE_CODES.get(state_code)

    if not state_name:
        return {"valid": False, "gstin": gstin, "error": f"Unknown state code: {state_code}"}

    # Checksum verification
    expected_checksum = _compute_gstin_checksum(gstin[:14])
    actual_checksum = gstin[14] if len(gstin) > 14 else ""

    if len(gstin) == 15 and actual_checksum != expected_checksum:
        return {
            "valid": False,
            "gstin": gstin,
            "error": f"Checksum mismatch: expected {expected_checksum}, got {actual_checksum}",
        }

    # PAN entity type
    pan_type_char = pan[3]
    entity_types = {
        "C": "Company", "P": "Person", "H": "HUF",
        "F": "Firm", "A": "AOP", "T": "Trust",
        "B": "BOI", "L": "Local Authority", "J": "Judicial Person",
        "G": "Government",
    }

    return {
        "valid": True,
        "gstin": gstin,
        "state_code": state_code,
        "state_name": state_name,
        "pan": pan,
        "entity_type": entity_types.get(pan_type_char, "Unknown"),
        "is_composition": gstin[13] != "Z",
    }


def calculate_gst(
    amount_paise: int,
    rate_percent: float = 18.0,
    is_igst: bool = False,
) -> dict[str, Any]:
    """Calculate GST on an amount (in paise).

    Args:
        amount_paise: Base amount in paise (before GST).
        rate_percent: GST rate (common: 5, 12, 18, 28).
        is_igst: True for inter-state (IGST), False for intra-state (CGST+SGST).

    Returns:
        Breakdown of tax components in paise.
    """
    gst_amount = int(amount_paise * rate_percent / 100)

    if is_igst:
        return {
            "base_amount_paise": amount_paise,
            "gst_rate_percent": rate_percent,
            "igst_paise": gst_amount,
            "cgst_paise": 0,
            "sgst_paise": 0,
            "total_paise": amount_paise + gst_amount,
            "type": "IGST",
        }

    cgst = gst_amount // 2
    sgst = gst_amount - cgst  # Handle odd paise

    return {
        "base_amount_paise": amount_paise,
        "gst_rate_percent": rate_percent,
        "igst_paise": 0,
        "cgst_paise": cgst,
        "sgst_paise": sgst,
        "total_paise": amount_paise + gst_amount,
        "type": "CGST+SGST",
    }


def check_tds_applicability(
    amount_paise: int,
    section: str = "194C",
) -> dict[str, Any]:
    """Check TDS applicability and compute deduction.

    Common sections for vendor payouts:
    - 194C: Contractors (1% individual, 2% company)
    - 194J: Professional/technical services (10%)
    - 194H: Commission/brokerage (5%)
    """
    thresholds: dict[str, dict[str, Any]] = {
        "194C": {"threshold_paise": 3000000, "rate_individual": 1.0, "rate_company": 2.0,
                 "description": "Payment to contractor"},
        "194J": {"threshold_paise": 3000000, "rate_individual": 10.0, "rate_company": 10.0,
                 "description": "Professional/technical fees"},
        "194H": {"threshold_paise": 1500000, "rate_individual": 5.0, "rate_company": 5.0,
                 "description": "Commission/brokerage"},
    }

    config = thresholds.get(section, thresholds["194C"])
    applicable = amount_paise >= config["threshold_paise"]
    tds_rate = config["rate_company"]
    tds_amount = int(amount_paise * tds_rate / 100) if applicable else 0

    return {
        "section": section,
        "description": config["description"],
        "applicable": applicable,
        "threshold_paise": config["threshold_paise"],
        "amount_paise": amount_paise,
        "tds_rate_percent": tds_rate if applicable else 0,
        "tds_amount_paise": tds_amount,
        "net_payable_paise": amount_paise - tds_amount,
    }
