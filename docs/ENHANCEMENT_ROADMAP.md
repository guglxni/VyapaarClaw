# VyapaarClaw Enhancement Roadmap

> Comprehensive plan to evolve VyapaarClaw from a payout governance MCP server into a full **AI CFO platform** with live India compliance, multi-layer vendor KYB, research integrations (Exa), credential security (Authsome), and government portal automation (Browserwire).

**Status:** All phases complete (AIDLC Construction + Operations ready)  
**Workflow:** [AWS AI-DLC](https://github.com/awslabs/aidlc-workflows) v0.1.8  
**Related:** `aidlc-docs/`, `docs/FOSS_RESEARCH.md`, `graphify-out/GRAPH_REPORT.md`

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Current State Assessment](#current-state-assessment)
3. [Target Architecture](#target-architecture)
4. [Phase 1 — Enforcement Gap (P0)](#phase-1--enforcement-gap-p0)
5. [Phase 2 — Live Verification & Research (P1)](#phase-2--live-verification--research-p1)
6. [Phase 3 — Full AI CFO Platform (P2)](#phase-3--full-ai-cfo-platform-p2)
7. [GST Payments Verification](#gst-payments-verification)
8. [Vendor Verification (KYB)](#vendor-verification-kyb)
9. [Exa Search Integration](#exa-search-integration)
10. [Authsome Credential Broker](#authsome-credential-broker)
11. [Browserwire Portal APIs](#browserwire-portal-apis)
12. [FOSS Repository Catalog](#foss-repository-catalog)
13. [New MCP Tools](#new-mcp-tools)
14. [Configuration Reference](#configuration-reference)
15. [Risk & Compliance Notes](#risk--compliance-notes)

---

## Executive Summary

VyapaarClaw has **37 MCP tools** and a documented **6-layer governance pipeline**, but the runtime `GovernanceEngine` only enforces **5 of 9** documented checks automatically. Rich CFO modules (GST, IFSC, GLEIF, OpenSanctions, anomaly ML, fraud graphs) exist as opt-in tools.

**Highest-impact work:**

| Priority | Enhancement | Why |
|----------|-------------|-----|
| P0 | Wire existing checks into `GovernanceEngine` | Closes doc vs code gap immediately |
| P0 | Extend `PayoutNotes` with GSTIN/IFSC/PAN | Enables compliance on every payout |
| P1 | Live GST verification (Browserwire + GSP) | Detect cancelled/shell GSTINs |
| P1 | Exa MCP for vendor adverse media | Replace hand-wavy "search the web" |
| P1 | Authsome for API credentials | Agents never see secrets |
| P2 | Browserwire manifests for GST/MCA portals | CAPTCHA-gated govt data as REST |
| P2 | Double-entry ledger, Darts forecasting | Full AI CFO |

---

## Current State Assessment

### Documented vs Implemented

```text
DOCUMENTED (6 layers)          IMPLEMENTED (engine.py)
─────────────────────          ───────────────────────
1. Policy check                ✅ Policy + budget + rate limit
2. Bank/IFSC                   ❌ Tool only (validate_bank_account)
3. GSTIN                       ❌ Tool only (validate_gstin — format only)
4. Reputation (GLEIF + SB)     ⚠️  Safe Browsing only
5. Sanctions                   ❌ Tool only (screen_vendor_sanctions)
6. Fraud ML (anomaly)          ❌ Tool only (score_transaction_risk)
```

### Key Gaps

- `comprehensive_vendor_screen()` does not call GLEIF or Safe Browsing (docstring says it should)
- `PayoutEntity` / `PayoutNotes` lack `gstin`, `pan`, `ifsc`, `vendor_name`
- Web dashboard (`vyapaar-ui/`) served via OpenClaw gateway; live MCP HTTP API at `/api/v1/*`
- FOSS libraries in `FOSS_RESEARCH.md` are mostly not in `pyproject.toml`
- Workflow state machine (`cfo/workflow.py`) is in-memory only

---

## Target Architecture

```text
┌─────────────────────────────────────────────────────────────────────┐
│                     VyapaarClaw — Full AI CFO                        │
│                                                                      │
│  KNOW (Intelligence)                                                 │
│    Darts/Prophet · FinBERT categorization · LangExtract contracts   │
│    Frankfurter FX · Indian calendar · Exa research                    │
│                              ↓                                       │
│  GUARD (Governance)                                                  │
│    6-layer pipeline (enforced) · Vendor Trust Score 0-100           │
│    PyGOD fraud · OpenSanctions · GLEIF · Safe Browsing · GST live   │
│    Dual-LLM quarantine · Authsome credential proxy                  │
│                              ↓                                       │
│  ACT (Execution)                                                     │
│    Razorpay payouts · python-accounting ledger · PDF reports        │
│    Slack/Telegram/ntfy HITL                                         │
└─────────────────────────────────────────────────────────────────────┘

Infrastructure: Redis (budget/cache) · PostgreSQL (audit/policies) · Browserwire (:8787)
```

---

## Phase 1 — Enforcement Gap (P0)

**AIDLC Unit:** `governance-enhancement`  
**Timeline:** ~2 weeks  
**Goal:** Make documented pipeline match runtime behavior.

### Deliverables

- [x] AIDLC workflow installed (`.cursor/rules/ai-dlc-workflow.mdc`)
- [x] This roadmap document
- [x] `PayoutNotes` extended: `gstin`, `pan`, `ifsc`, `vendor_name`
- [x] `ReasonCode` additions: `GST_INVALID`, `IFSC_INVALID`, `SANCTIONS_MATCH`
- [x] `GovernanceEngine` wires: GST format, IFSC format, anomaly HOLD, sanctions gate
- [x] `GovernanceOptions` config via `VYAPAAR_GOVERNANCE_*` env vars
- [x] `reputation/trust_score.py` — composite Vendor Trust Score
- [x] `comprehensive_vendor_screen()` calls GLEIF + Safe Browsing
- [x] Tests in `tests/test_governance_enhanced.py` + `tests/test_trust_score.py`

### Governance Pipeline (Post Phase 1)

```text
1. Policy lookup          → REJECT if missing
2. Per-txn limit          → REJECT if exceeded
3. Rate limit             → REJECT if exceeded
4. Daily budget (atomic)  → REJECT if exceeded
5. Domain allow/block     → REJECT if blocked
6. Safe Browsing          → REJECT if unsafe
7. GSTIN format (notes)   → REJECT if invalid [NEW]
8. IFSC format (payout)   → REJECT if invalid [NEW]
9. Anomaly score          → HOLD if above threshold [NEW]
10. Sanctions (≥ threshold)→ REJECT/HOLD by risk level [NEW]
11. Approval threshold    → HOLD if above limit
12. APPROVE
```

---

## Phase 2 — Live Verification & Research (P1)

**Status:** ✅ Complete  
**Timeline:** ~3 weeks

### Deliverables

- [x] `cfo/gst_providers.py` — `GstVerificationProvider` protocol + tiered chain
- [x] `integrations/browserwire.py` — Browserwire REST client
- [x] `research/exa_client.py` — Exa search client
- [x] `reputation/adverse_media.py` — adverse media screening
- [x] MCP tools: `verify_gstin_live`, `research_vendor`, `screen_adverse_media`
- [x] Live GST in governance pipeline (`VYAPAAR_GOVERNANCE_LIVE_GST`)
- [x] HTTP dashboard API: `/api/v1/dashboard`, `/api/v1/agents`, `/api/v1/audit`
- [x] Web app wired to live MCP data (`mcp-client.ts`, API routes, dashboard)
- [x] `docs/AUTHSOME_BOOTSTRAP.md` — credential broker guide
- [x] CFO delegation skill updated for Exa/adverse media tools

### GST Live Verification

| Tier | Method | Repo / Service |
|------|--------|----------------|
| T1 | Format + checksum | [Piyush4u/gst_validator_india](https://github.com/Piyush4u/gst_validator_india) |
| T2 | Portal scrape | [avstrix/gstin-verify-api](https://github.com/avstrix/gstin-verify-api) + Browserwire |
| T3 | GSP API | Cashfree Secure ID, ClearTax, Gridlines |

New module: `src/vyapaar_mcp/cfo/gst_providers.py` with `GstVerificationProvider` protocol.

### Exa Search

- MCP: [exa-labs/exa-mcp-server](https://github.com/exa-labs/exa-mcp-server)
- URL: `https://mcp.exa.ai/mcp`
- Tools: `web_search_exa`, `company_research_exa`, `deep_researcher_exa`
- Module: `src/vyapaar_mcp/research/exa_client.py`
- MCP tool: `research_vendor`

### Authsome

- Repo: [agentrhq/authsome](https://github.com/agentrhq/authsome) (NOT xraph/authsome)
- Usage: `authsome run -- python -m vyapaar_mcp`
- Providers: Razorpay, Slack, Exa, Safe Browsing, OpenSanctions, GSP APIs

### Adverse Media

- Pattern: [plutopulp/adverse-media-screening](https://github.com/plutopulp/adverse-media-screening)
- Module: `src/vyapaar_mcp/reputation/adverse_media.py`
- MCP tool: `screen_adverse_media`

### Web Dashboard

- Wire `vyapaar-ui/` dashboard to live MCP `/api/v1/dashboard` and `/api/v1/audit`
- Auth via [xraph/authsome](https://github.com/xraph/authsome) or NextAuth

---

## Phase 3 — Full AI CFO Platform (P2)

**Status:** ✅ Complete  
**Timeline:** 4–6 weeks

### Deliverables

- [x] `cfo/einvoice.py` — GST IRN / ack validation
- [x] `cfo/invoice_ocr.py` — HyperAPI invoice extraction
- [x] `cfo/forecaster_darts.py` — Darts upgrade with numpy fallback
- [x] `cfo/fraud.py` — structural anomaly scoring + PyGOD detection hook
- [x] Workflow Postgres persistence (`payout_workflows` table)
- [x] Ledger Postgres persistence (`ledger_entries` table)
- [x] MCP tools: `validate_einvoice`, `extract_invoice_data`, `detect_fraud_network_ml`
- [x] Optional `cfo-advanced` deps (`u8darts`) in `pyproject.toml`
- [x] Tests: `tests/test_phase2_phase3.py` (350 total passing)

| Feature | FOSS | Module |
|---------|------|--------|
| Double-entry ledger | [ekmungai/python-accounting](https://github.com/ekmungai/python-accounting) | Replace `cfo/ledger.py` |
| Cash flow forecasting | [unit8co/darts](https://github.com/unit8co/darts) | `cfo/forecaster.py` |
| GNN fraud detection | [pygod-team/pygod](https://github.com/pygod-team/pygod) | `cfo/fraud.py` |
| E-invoice IRN | [AhmedSabry/gst_irn](https://github.com/AhmedSabry/gst_irn) | New `cfo/einvoice.py` |
| Invoice OCR | HyperAPI + Docling | New `cfo/invoice_ocr.py` |
| Workflow persistence | `transitions` + Postgres | `cfo/workflow.py` |
| GSP production GST | Cashfree/ClearTax API | `cfo/gst_providers.py` |

---

## GST Payments Verification

### Current (`cfo/tax.py`)

- Regex + custom checksum
- CGST/SGST/IGST calculation
- TDS sections 194C/J/H

### Enhancements

1. **Replace checksum** with `gst_validator_india` (GSTN-accurate, OCR repair)
2. **Live status** via Browserwire-trained GST portal manifest
3. **GSP API** for production (registration status, legal name match, filing history)
4. **E-invoice IRN** validation for B2B payouts
5. **TDS auto-deduction flag** in governance for contractor payments

### Governance Rules (proposed)

| Condition | Action |
|-----------|--------|
| GSTIN in notes, format invalid | REJECT (`GST_INVALID`) |
| GSTIN live status = Cancelled | REJECT |
| GSTIN live status = Suspended | HOLD |
| Legal name mismatch vs vendor_name | HOLD |
| No GSTIN, amount > ₹2.5L B2B | HOLD (request GSTIN) |

---

## Vendor Verification (KYB)

### Vendor Trust Score (0–100)

| Layer | Weight | Source |
|-------|--------|--------|
| Identity (GLEIF LEI) | 15% | `GLEIFChecker` |
| Compliance (GSTIN) | 20% | `validate_gstin` / live verify |
| Sanctions (OpenSanctions) | 25% | `screen_against_sanctions` |
| Reputation (Safe Browsing) | 15% | `SafeBrowsingChecker` |
| Adverse media (Exa + LLM) | 15% | Phase 2 |
| Behavioral (anomaly + history) | 10% | `TransactionAnomalyScorer` + audit |

### Decision Matrix

| Score | Amount | Action |
|-------|--------|--------|
| 80–100 | Any | Auto-approve (within policy) |
| 60–79 | < ₹1L | Approve with audit flag |
| 60–79 | ≥ ₹1L | HOLD → Slack review |
| 40–59 | Any | HOLD → mandatory L1 |
| 0–39 | Any | REJECT + blocklist |

---

## Exa Search Integration

### Setup (Cursor MCP)

```json
{
  "mcpServers": {
    "exa": {
      "url": "https://mcp.exa.ai/mcp?tools=web_search_exa,web_fetch_exa,company_research_exa,deep_researcher_exa",
      "headers": { "x-api-key": "${EXA_API_KEY}" }
    }
  }
}
```

### Use Cases

1. Vendor due diligence — `"{vendor}" fraud OR scam OR investigation`
2. Company research — structured business intel for KYB
3. FOSS discovery — find integration libraries during development
4. Adverse media pipeline input (Phase 2)

### Alternative: Unified Search

[spences10/mcp-omnisearch](https://github.com/spences10/mcp-omnisearch) — Exa + Brave + Tavily + Kagi in one MCP.

---

## Authsome Credential Broker

**Repo:** [agentrhq/authsome](https://github.com/agentrhq/authsome) (MIT, Python 3.13+)

### Problem Solved

VyapaarClaw manages 10+ API keys via `VYAPAAR_*` env vars. Agents with env access can exfiltrate secrets. Authsome injects credentials at proxy boundary — agents never see raw tokens.

### Integration

```bash
# One-time setup
authsome login github
authsome login razorpay  # custom provider JSON if needed

# Runtime
authsome run -- vyapaarclaw start
```

### Synergy with Dual-LLM Quarantine

| Layer | Protects against |
|-------|------------------|
| Dual-LLM quarantine | Prompt injection, context taint |
| Authsome | Credential exfiltration from agent process |

---

## Browserwire Portal APIs

**Repo:** [gearsec/browserwire](https://github.com/gearsec/browserwire) (MIT, 25 stars)

### What It Does

```text
Record browser session (rrweb) → Cloud LLM training → StateMachineManifest → bw run REST API
```

Unlike BrowserMCP (live Chrome control), Browserwire **learns** a site once and exposes typed endpoints.

### India Fintech Portals

| Portal | Data | VyapaarClaw Use |
|--------|------|-----------------|
| GST Portal | GSTIN status, legal name, filings | `verify_gstin_live` |
| MCA21 | CIN, directors, company status | `verify_mca_company` |
| TRACES | TDS credits | TDS reconciliation |

### Integration

```python
# src/vyapaar_mcp/integrations/browserwire.py
class BrowserwireClient:
    base_url: str = "http://localhost:8787"

    async def verify_gstin(self, gstin: str) -> dict: ...
```

### Browser MCP Alternatives (for other use cases)

| Tool | Stars | Best for |
|------|-------|----------|
| [BrowserMCP/mcp](https://github.com/BrowserMCP/mcp) | 6.3K | Logged-in Chrome sessions |
| [Agent360dk/browser-mcp](https://github.com/Agent360dk/browser-mcp) | New | CAPTCHA solve, 29 tools |
| [cherchyk/MCPBrowser](https://github.com/cherchyk/MCPBrowser) | Active | SSO/CAPTCHA sites |
| [microsoft/playwright-mcp](https://github.com/microsoft/playwright-mcp) | 32K+ | Headless testing |

---

## FOSS Repository Catalog

### P0 — Phase 1

| Repo | License | Integration |
|------|---------|-------------|
| [Piyush4u/gst_validator_india](https://github.com/Piyush4u/gst_validator_india) | GPL-3.0 | `cfo/tax.py` |
| [razorpay/ifsc](https://github.com/razorpay/ifsc) | MIT | `cfo/bank.py` offline bundle |
| [opensanctions/opensanctions](https://github.com/opensanctions/opensanctions) | MIT | Already integrated |

### P1 — Phase 2

| Repo | License | Integration |
|------|---------|-------------|
| [exa-labs/exa-mcp-server](https://github.com/exa-labs/exa-mcp-server) | — | MCP + `research/` |
| [agentrhq/authsome](https://github.com/agentrhq/authsome) | MIT | CLI bootstrap |
| [avstrix/gstin-verify-api](https://github.com/avstrix/gstin-verify-api) | MIT | `cfo/gst_portal.py` |
| [gearsec/browserwire](https://github.com/gearsec/browserwire) | MIT | `integrations/browserwire.py` |
| [plutopulp/adverse-media-screening](https://github.com/plutopulp/adverse-media-screening) | — | `reputation/adverse_media.py` |
| [Pranjalbkn/Invoice_Auditor](https://github.com/Pranjalbkn/Invoice_Auditor) | — | Reference for AP automation |

### P2 — Phase 3

| Repo | License | Integration |
|------|---------|-------------|
| [ekmungai/python-accounting](https://github.com/ekmungai/python-accounting) | GPL-3.0 | `cfo/ledger.py` |
| [unit8co/darts](https://github.com/unit8co/darts) | Apache-2.0 | `cfo/forecaster.py` |
| [pygod-team/pygod](https://github.com/pygod-team/pygod) | BSD-2 | `cfo/fraud.py` |
| [resilient-tech/india-compliance](https://github.com/resilient-tech/india-compliance) | GPL-3.0 | GST API patterns |
| [google/langextract](https://github.com/google/langextract) | Apache-2.0 | `cfo/contracts.py` |

---

## New MCP Tools

| Tool | Phase | Description |
|------|-------|-------------|
| `verify_gstin_live` | P1 | Live portal/GSP GSTIN status |
| `research_vendor` | P1 | Exa-powered deep vendor DD |
| `screen_adverse_media` | P1 | LLM adverse media screening |
| `get_vendor_trust_score` | P1 | Enhanced composite 0–100 score |
| `verify_einvoice` | P2 | IRN validation |
| `parse_invoice` | P2 | OCR → GSTIN extraction |
| `verify_mca_company` | P2 | MCA21 via Browserwire |
| `reconcile_itc` | P3 | GSTR-2B matching |

Total: **37 → 45+** tools with enforcement behind them.

---

## Configuration Reference

### Phase 1 (new env vars)

```bash
# Governance feature flags
VYAPAAR_GOVERNANCE_GST_CHECK=true
VYAPAAR_GOVERNANCE_IFSC_CHECK=true
VYAPAAR_GOVERNANCE_ANOMALY_CHECK=true
VYAPAAR_GOVERNANCE_SANCTIONS_CHECK=true
VYAPAAR_GOVERNANCE_SANCTIONS_THRESHOLD_PAISE=5000000  # ₹50,000
VYAPAAR_GOVERNANCE_TRUST_HOLD_THRESHOLD=40

# Phase 2
EXA_API_KEY=
BROWSERWIRE_BASE_URL=http://localhost:8787
GST_GSP_PROVIDER=cashfree  # cashfree | cleartax | browserwire
```

---

## Risk & Compliance Notes

| Risk | Mitigation |
|------|------------|
| GPL deps (`gst_validator_india`, `python-accounting`) | AGPL VyapaarClaw compatible; document in LICENSE |
| Browserwire cloud uploads vendor data | Self-host `@browserwire/core`; use GSP for production PII |
| GSP API costs | Tiered: free format → Browserwire → paid GSP for high-value only |
| Exa rate limits | Redis cache 24h vendor DD, 7d company research |
| Two "Authsome" projects | **agentrhq** for agents; **xraph** for web dashboard auth only |

---

## AIDLC Artifact Index

| Artifact | Path |
|----------|------|
| Workflow state | `aidlc-docs/aidlc-state.md` |
| Audit trail | `aidlc-docs/audit.md` |
| Requirements | `aidlc-docs/inception/requirements/requirements.md` |
| Execution plan | `aidlc-docs/inception/plans/execution-plan.md` |
| Code gen plan | `aidlc-docs/construction/plans/governance-enhancement-code-generation-plan.md` |

---

*Last updated: 2026-06-06 — Phase 1 implementation in progress*
