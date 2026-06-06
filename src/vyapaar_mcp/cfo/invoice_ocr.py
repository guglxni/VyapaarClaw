"""Invoice OCR and structured extraction via HyperAPI.

Extracts vendor name, GSTIN, amounts, and line items from invoice PDFs/images
for automated payout reconciliation.
"""

from __future__ import annotations

import base64
import logging
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)


async def extract_invoice(
    file_path: str = "",
    file_base64: str = "",
    api_key: str = "",
    base_url: str = "https://api.hyperbots.com",
) -> dict[str, Any]:
    """Extract structured data from an invoice document.

    Provide either file_path or file_base64. Requires VYAPAAR_HYPERAPI_API_KEY.
    """
    if not api_key:
        return {
            "extracted": False,
            "error": "HyperAPI not configured (VYAPAAR_HYPERAPI_API_KEY)",
        }

    content_b64 = file_base64
    filename = "invoice.pdf"

    if file_path and not content_b64:
        path = Path(file_path)
        if not path.exists():
            return {"extracted": False, "error": f"File not found: {file_path}"}
        content_b64 = base64.b64encode(path.read_bytes()).decode()
        filename = path.name

    if not content_b64:
        return {"extracted": False, "error": "Provide file_path or file_base64"}

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{base_url.rstrip('/')}/v1/documents/extract",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "document": content_b64,
                    "filename": filename,
                    "document_type": "invoice",
                },
            )
            if resp.status_code == 401:
                return {"extracted": False, "error": "Invalid HyperAPI key"}
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPError as exc:
        logger.warning("HyperAPI extraction failed: %s", exc)
        return {"extracted": False, "error": str(exc)}

    entities = data.get("entities") or data.get("fields") or {}
    return {
        "extracted": True,
        "vendor_name": entities.get("vendor_name") or entities.get("seller_name"),
        "gstin": entities.get("gstin") or entities.get("seller_gstin"),
        "invoice_number": entities.get("invoice_number"),
        "invoice_date": entities.get("invoice_date"),
        "total_amount": entities.get("total_amount"),
        "currency": entities.get("currency", "INR"),
        "line_items": entities.get("line_items", []),
        "confidence": data.get("confidence"),
        "raw": data,
    }
