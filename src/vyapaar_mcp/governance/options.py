"""Governance engine feature flags and thresholds."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GovernanceOptions:
    """Configurable compliance checks for the governance pipeline."""

    check_gstin_format: bool = True
    check_ifsc_format: bool = True
    check_sanctions: bool = True
    check_anomaly: bool = True
    live_gst: bool = False
    sanctions_reject_score: float = 0.8
    anomaly_hold: bool = True
    browserwire_url: str = ""
    browserwire_key: str = ""
    gsp_url: str = ""
    gsp_key: str = ""

    @classmethod
    def from_config(cls, config: object) -> GovernanceOptions:
        """Build options from VyapaarConfig."""
        return cls(
            check_gstin_format=getattr(config, "governance_check_gstin", True),
            check_ifsc_format=getattr(config, "governance_check_ifsc", True),
            check_sanctions=getattr(config, "governance_check_sanctions", True),
            check_anomaly=getattr(config, "governance_check_anomaly", True),
            live_gst=getattr(config, "governance_live_gst", False),
            sanctions_reject_score=getattr(config, "governance_sanctions_reject_score", 0.8),
            anomaly_hold=getattr(config, "governance_anomaly_hold", True),
            browserwire_url=getattr(config, "browserwire_url", ""),
            browserwire_key=getattr(config, "browserwire_api_key", ""),
            gsp_url=getattr(config, "gsp_api_url", ""),
            gsp_key=getattr(config, "gsp_api_key", ""),
        )
