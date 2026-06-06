"""DenchClaw CRM object definitions for VyapaarClaw sync.

Follows DenchClaw DuckDB EAV schema (see DenchHQ/DenchClaw skills/crm).
Object names are singular lowercase per DenchClaw conventions.
"""

from __future__ import annotations

AUDIT_OBJECT = "vyapaar_audit"
VENDOR_OBJECT = "vyapaar_vendor"

AUDIT_FIELDS: list[tuple[str, str, bool]] = [
    ("Payout ID", "text", True),
    ("Agent ID", "text", False),
    ("Amount Paise", "number", False),
    ("Decision", "text", False),
    ("Reason Code", "text", False),
    ("Reason Detail", "text", False),
    ("Vendor Name", "text", False),
    ("Vendor URL", "text", False),
    ("Processing Ms", "number", False),
]

VENDOR_FIELDS: list[tuple[str, str, bool]] = [
    ("Vendor Name", "text", True),
    ("GSTIN", "text", False),
    ("Trust Score", "number", False),
    ("Trust Level", "text", False),
    ("Sanctions Status", "text", False),
    ("Last Screened", "text", False),
]

OBJECT_YAMLS: dict[str, str] = {
    AUDIT_OBJECT: """name: vyapaar_audit
description: VyapaarClaw governance audit decisions
default_view: table
icon: scroll-text
""",
    VENDOR_OBJECT: """name: vyapaar_vendor
description: VyapaarClaw vendor KYB and trust scores
default_view: table
icon: building-2
""",
}
