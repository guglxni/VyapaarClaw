# Code Generation Plan — governance-enhancement

## Unit: governance-enhancement

**Phase:** 1 (P0)  
**Requirements:** FR-1, FR-2, FR-3, FR-4

## Checklist

- [x] Create `governance/options.py` — GovernanceOptions dataclass
- [x] Extend `models.py` — PayoutNotes fields, ReasonCode enums
- [x] Extend `config.py` — governance feature flags
- [x] Update `governance/engine.py` — wire compliance checks
- [x] Create `reputation/trust_score.py` — composite score
- [x] Update `cfo/sanctions.py` — GLEIF + Safe Browsing integration
- [x] Update `server.py` — pass anomaly_scorer + options to engine
- [x] Add `tests/test_governance_enhanced.py` — new check tests
- [x] Add `tests/test_trust_score.py` — trust score tests
- [x] Run pytest (34 passed)

## File Changes

| File | Action |
|------|--------|
| `src/vyapaar_mcp/governance/options.py` | CREATE |
| `src/vyapaar_mcp/reputation/trust_score.py` | CREATE |
| `src/vyapaar_mcp/models.py` | MODIFY |
| `src/vyapaar_mcp/config.py` | MODIFY |
| `src/vyapaar_mcp/governance/engine.py` | MODIFY |
| `src/vyapaar_mcp/cfo/sanctions.py` | MODIFY |
| `src/vyapaar_mcp/server.py` | MODIFY |
| `tests/test_governance_enhanced.py` | CREATE |
| `tests/test_trust_score.py` | CREATE |
