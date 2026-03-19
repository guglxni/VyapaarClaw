"""IFSC / Bank Account Validation for Indian Payouts.

Validates IFSC codes against the official format (RBI specification),
extracts bank metadata, and verifies account number format before
payouts reach Razorpay.
"""

from __future__ import annotations

import re
from typing import Any

import httpx

# IFSC format: 4 alpha (bank code) + 0 + 6 alphanumeric (branch code)
_IFSC_PATTERN = re.compile(r"^[A-Z]{4}0[A-Z0-9]{6}$")

# Major Indian bank codes for quick offline validation
_KNOWN_BANK_CODES: dict[str, str] = {
    "SBIN": "State Bank of India",
    "HDFC": "HDFC Bank",
    "ICIC": "ICICI Bank",
    "UTIB": "Axis Bank",
    "KKBK": "Kotak Mahindra Bank",
    "PUNB": "Punjab National Bank",
    "BARB": "Bank of Baroda",
    "CNRB": "Canara Bank",
    "UBIN": "Union Bank of India",
    "IOBA": "Indian Overseas Bank",
    "BKID": "Bank of India",
    "IDIB": "Indian Bank",
    "YESB": "Yes Bank",
    "INDB": "IndusInd Bank",
    "FDRL": "Federal Bank",
    "RATN": "RBL Bank",
    "KARB": "Karnataka Bank",
    "CITI": "Citibank",
    "HSBC": "HSBC India",
    "SCBL": "Standard Chartered",
    "DEUT": "Deutsche Bank",
    "CBIN": "Central Bank of India",
    "UCBA": "UCO Bank",
}


def validate_ifsc(ifsc: str) -> dict[str, Any]:
    """Validate an IFSC code offline (format + known bank check).

    Returns metadata about the bank if the code is valid.
    """
    ifsc = ifsc.strip().upper()

    if not _IFSC_PATTERN.match(ifsc):
        return {
            "valid": False,
            "ifsc": ifsc,
            "error": "Invalid IFSC format. Expected: 4 letters + 0 + 6 alphanumeric",
        }

    bank_code = ifsc[:4]
    branch_code = ifsc[5:]
    bank_name = _KNOWN_BANK_CODES.get(bank_code)

    return {
        "valid": True,
        "ifsc": ifsc,
        "bank_code": bank_code,
        "bank_name": bank_name or f"Unknown bank ({bank_code})",
        "branch_code": branch_code,
        "is_known_bank": bank_name is not None,
    }


async def lookup_ifsc_online(ifsc: str) -> dict[str, Any]:
    """Look up IFSC details via Razorpay's public IFSC API.

    This is a free, public API with no authentication needed.
    """
    ifsc = ifsc.strip().upper()

    offline = validate_ifsc(ifsc)
    if not offline["valid"]:
        return offline

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"https://ifsc.razorpay.com/{ifsc}")
            if resp.status_code == 404:
                return {
                    "valid": False,
                    "ifsc": ifsc,
                    "error": "IFSC code not found in Razorpay database",
                }
            resp.raise_for_status()
            data = resp.json()

        return {
            "valid": True,
            "ifsc": ifsc,
            "bank": data.get("BANK", ""),
            "branch": data.get("BRANCH", ""),
            "address": data.get("ADDRESS", ""),
            "city": data.get("CITY", ""),
            "state": data.get("STATE", ""),
            "contact": data.get("CONTACT", ""),
            "imps": data.get("IMPS", False),
            "rtgs": data.get("RTGS", False),
            "neft": data.get("NEFT", False),
            "upi": data.get("UPI", False),
            "swift": data.get("SWIFT", ""),
        }
    except httpx.HTTPError as exc:
        # Fallback to offline validation
        return {
            **offline,
            "online_lookup_failed": True,
            "error_detail": str(exc),
        }


def validate_account_number(account_number: str) -> dict[str, Any]:
    """Basic validation of Indian bank account numbers.

    Indian bank accounts are typically 9-18 digits.
    """
    cleaned = re.sub(r"\s+", "", account_number)

    if not cleaned.isdigit():
        return {
            "valid": False,
            "account_number": account_number,
            "error": "Account number must be numeric",
        }

    length = len(cleaned)
    if length < 9 or length > 18:
        return {
            "valid": False,
            "account_number": cleaned,
            "error": f"Invalid length ({length}). Indian accounts are 9-18 digits",
        }

    return {
        "valid": True,
        "account_number": cleaned,
        "length": length,
    }


def validate_fund_account(
    ifsc: str,
    account_number: str,
    beneficiary_name: str = "",
) -> dict[str, Any]:
    """Full pre-flight validation of a fund account before creating a payout.

    Checks IFSC format, account number format, and returns a
    composite validation result.
    """
    ifsc_result = validate_ifsc(ifsc)
    account_result = validate_account_number(account_number)

    all_valid = ifsc_result["valid"] and account_result["valid"]
    errors: list[str] = []

    if not ifsc_result["valid"]:
        errors.append(f"IFSC: {ifsc_result.get('error')}")
    if not account_result["valid"]:
        errors.append(f"Account: {account_result.get('error')}")
    if beneficiary_name and len(beneficiary_name.strip()) < 3:
        errors.append("Beneficiary name too short")
        all_valid = False

    return {
        "valid": all_valid,
        "ifsc": ifsc_result,
        "account": account_result,
        "beneficiary_name": beneficiary_name.strip(),
        "errors": errors,
        "recommendation": "Proceed with payout" if all_valid else "Fix errors before payout",
    }
