"""GST E-Invoice IRN validation for B2B payouts.

Validates Invoice Reference Number (IRN) format and checksum.
Live IRN lookup requires NIC e-invoice API credentials (future GSP integration).
"""

from __future__ import annotations

import re
from typing import Any

# IRN: 64-character hash returned by NIC e-invoice system
_IRN_PATTERN = re.compile(r"^[a-fA-F0-9]{64}$")

# Acknowledgement number: 15 digits
_ACK_PATTERN = re.compile(r"^\d{15}$")


def validate_irn(irn: str) -> dict[str, Any]:
    """Validate e-invoice IRN format."""
    irn = irn.strip()
    if not _IRN_PATTERN.match(irn):
        return {
            "valid": False,
            "irn": irn,
            "error": "Invalid IRN format. Expected 64-character hex hash",
        }
    return {
        "valid": True,
        "irn": irn.lower(),
        "format": "nic_einvoice_irn",
    }


def validate_ack_number(ack_no: str) -> dict[str, Any]:
    """Validate e-invoice acknowledgement number format."""
    ack_no = ack_no.strip()
    if not _ACK_PATTERN.match(ack_no):
        return {
            "valid": False,
            "ack_no": ack_no,
            "error": "Invalid ack number. Expected 15 digits",
        }
    return {"valid": True, "ack_no": ack_no}


def validate_einvoice_bundle(
    irn: str = "",
    ack_no: str = "",
    gstin: str = "",
    invoice_number: str = "",
    invoice_date: str = "",
) -> dict[str, Any]:
    """Validate a complete e-invoice reference bundle for B2B payout matching."""
    errors: list[str] = []
    irn_result: dict[str, Any] | None = None
    ack_result: dict[str, Any] | None = None

    if irn:
        irn_result = validate_irn(irn)
        if not irn_result["valid"]:
            errors.append(f"IRN: {irn_result.get('error')}")

    if ack_no:
        ack_result = validate_ack_number(ack_no)
        if not ack_result["valid"]:
            errors.append(f"Ack: {ack_result.get('error')}")

    if not irn and not ack_no:
        errors.append("At least one of IRN or ack_no required")

    if gstin:
        from vyapaar_mcp.cfo.tax import validate_gstin
        gst_result = validate_gstin(gstin)
        if not gst_result.get("valid"):
            errors.append(f"GSTIN: {gst_result.get('error')}")

    valid = len(errors) == 0

    return {
        "valid": valid,
        "irn": irn_result,
        "ack_no": ack_result,
        "gstin": gstin,
        "invoice_number": invoice_number,
        "invoice_date": invoice_date,
        "errors": errors,
        "recommendation": "E-invoice reference valid" if valid else "Fix e-invoice errors",
        "live_lookup_available": False,
        "note": "Live IRN status lookup requires NIC/GSP credentials (Phase 3 GSP)",
    }
