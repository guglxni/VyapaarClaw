"""Helpers for extracting and validating payout compliance context."""

from __future__ import annotations

from vyapaar_mcp.cfo.bank import validate_ifsc
from vyapaar_mcp.cfo.tax import validate_gstin
from vyapaar_mcp.models import PayoutEntity


def extract_payout_context(payout: PayoutEntity) -> dict[str, str]:
    """Extract vendor/compliance fields from payout entity and notes."""
    notes = payout.get_notes()
    gstin = (getattr(notes, "gstin", None) or "").strip().upper()
    pan = (getattr(notes, "pan", None) or "").strip().upper()
    vendor_name = (getattr(notes, "vendor_name", None) or "").strip()
    vendor_url = (getattr(notes, "vendor_url", None) or "").strip()

    ifsc = (getattr(notes, "ifsc", None) or "").strip().upper()
    if not ifsc and payout.fund_account and payout.fund_account.bank_account:
        ifsc = (payout.fund_account.bank_account.ifsc or "").strip().upper()
        if not vendor_name and payout.fund_account.bank_account.name:
            vendor_name = payout.fund_account.bank_account.name.strip()
        if payout.fund_account.contact and not vendor_name:
            vendor_name = (payout.fund_account.contact.name or "").strip()

    return {
        "gstin": gstin,
        "pan": pan,
        "ifsc": ifsc,
        "vendor_name": vendor_name,
        "vendor_url": vendor_url,
    }


def check_gstin_format(gstin: str) -> tuple[bool, str]:
    """Validate GSTIN format. Returns (ok, detail)."""
    if not gstin:
        return True, ""
    result = validate_gstin(gstin)
    if result.get("valid"):
        return True, ""
    return False, result.get("error", "Invalid GSTIN")


def check_ifsc_format(ifsc: str) -> tuple[bool, str]:
    """Validate IFSC format. Returns (ok, detail)."""
    if not ifsc:
        return True, ""
    result = validate_ifsc(ifsc)
    if result.get("valid"):
        return True, ""
    return False, result.get("error", "Invalid IFSC")
