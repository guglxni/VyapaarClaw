# Requirements — VyapaarClaw Enhancement Program

## Intent Analysis

Transform VyapaarClaw from a payout governance toolkit into an enforced full AI CFO platform. Primary gap: documented 6-layer governance pipeline is not enforced at runtime.

## Functional Requirements

### FR-1: Governance Pipeline Enforcement (P0)

The system SHALL run GSTIN format validation, IFSC format validation, anomaly scoring, and sanctions screening automatically during `GovernanceEngine.evaluate()` when enabled via configuration.

### FR-2: Extended Payout Context (P0)

`PayoutNotes` SHALL support optional `gstin`, `pan`, `ifsc`, and `vendor_name` fields extracted from Razorpay payout metadata.

### FR-3: Vendor Trust Score (P0)

The system SHALL compute a composite Vendor Trust Score (0–100) from sanctions, GSTIN, GLEIF, and Safe Browsing signals via `compute_vendor_trust_score()`.

### FR-4: Comprehensive Vendor Screen Fix (P0)

`comprehensive_vendor_screen()` SHALL integrate GLEIF and Safe Browsing checks, not only OpenSanctions.

### FR-5: Live GST Verification (P1)

The system SHALL support tiered GSTIN verification: format (offline), portal (Browserwire), GSP API (commercial).

### FR-6: Exa Research Integration (P1)

Agents SHALL access Exa MCP for vendor adverse media and company research via `research_vendor` tool.

### FR-7: Authsome Credentials (P1)

Production deployments SHOULD run MCP server behind `authsome run` to prevent credential exfiltration.

### FR-8: Browserwire Portal APIs (P2)

Government portal lookups (GST, MCA) SHALL be accessible via Browserwire-trained REST manifests.

## Non-Functional Requirements

### NFR-1: Fail-Closed Security

GSTIN and IFSC format failures SHALL REJECT payouts. Safe Browsing remains fail-closed. GLEIF remains fail-open advisory.

### NFR-2: Backward Compatibility

New governance checks SHALL be feature-flagged (default enabled) and not break existing tests without payout metadata.

### NFR-3: AGPL Compliance

GPL library integration (`gst_validator_india`) deferred to Phase 2; Phase 1 uses existing checksum logic.

### NFR-4: Observability

New checks SHALL emit metrics via existing `observability.metrics` module.

## Traceability

| Requirement | Phase | Module |
|-------------|-------|--------|
| FR-1 | 1 | `governance/engine.py` |
| FR-2 | 1 | `models.py` |
| FR-3 | 1 | `reputation/trust_score.py` |
| FR-4 | 1 | `cfo/sanctions.py` |
| FR-5 | 2 | `cfo/gst_providers.py` |
| FR-6 | 2 | `research/exa_client.py` |
| FR-7 | 2 | CLI / bootstrap |
| FR-8 | 2 | `integrations/browserwire.py` |
