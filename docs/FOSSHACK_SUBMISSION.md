# FOSS Hack 2026 — VyapaarClaw Submission

---

## Field 1: Title

```
VyapaarClaw
```

---

## Field 2: Short Description

```
AI Financial Governance Framework — The CFO for the Agentic Economy
```

---

## Field 3: Repository Link

```
https://github.com/guglxni/VyapaarClaw
```

---

## Field 4: Demo Link

> Can be added later — a video walkthrough or deployed dashboard URL.

---

## Field 5: Project Description

**VyapaarClaw** is a *Governance-as-a-Service* framework that transforms AI agents into financially governed entities. It acts as an autonomous financial firewall between AI agents and real payment infrastructure (Razorpay X), enforcing budgets, verifying vendors, scoring risk, and keeping humans in the loop — so AI agents can handle real money without uncontrolled spending.

### The Problem

We're entering the era of autonomous AI agents executing real-world financial tasks. The gap isn't intelligence — it's **trust**. Giving an AI agent a credit card is like giving a new hire the company chequebook on Day 1 with no spending policy. Without governance, agents can hallucinate and drain wallets, pay fraudulent vendors, or leave zero audit trail.

### The Solution — A 6-Layer Governance Pipeline

Every transaction passes through six layers of verification:

1. **Webhook Signature Verification** — Razorpay HMAC-SHA256 validation
2. **Agent Policy Enforcement** — Per-agent daily limits, per-txn caps, domain restrictions
3. **Vendor Reputation Check** — Google Safe Browsing threat analysis
4. **Entity Verification** — GLEIF legal entity lookup (fully FOSS)
5. **ML Anomaly Detection** — Isolation Forest on transaction patterns (scikit-learn)
6. **Composite Risk Scoring** — Automatic decision routing (APPROVE / REJECT / HOLD for human review)

### 25 MCP Governance Tools

Exposed via the **Model Context Protocol (MCP)**: Budget Control, Vendor Verification, Risk & Anomaly Scoring, Compliance Reporting, Payment Processing, Slack/Telegram/ntfy Human-in-the-Loop Approvals, Cash Flow Forecasting, and more.

### Document Intelligence Layer (HyperAPI Integration)

VyapaarClaw integrates [Hyperbots HyperAPI](http://hyperapi-production-12097051.us-east-1.elb.amazonaws.com/docs) for financial document intelligence, powered by [hyperbots-agent-skills](https://github.com/guglxni/hyperbots-agent-skills):

- **Parse** — High-fidelity OCR text extraction from invoices, receipts, and tax forms
- **Classify** — Automated document categorization (invoices, receipts, contracts, etc.)
- **Split** — Multi-document PDF segmentation into logical units
- **Extract** — Vision-language structured data extraction (invoice numbers, amounts, line items, vendor details)
- **Process** — Unified parse + extract pipeline for end-to-end document intelligence

### Sandboxed Agent Security (NVIDIA NemoClaw)

VyapaarClaw leverages [NVIDIA NemoClaw](https://github.com/NVIDIA/NemoClaw) for infrastructure-level agent security via the OpenShell runtime:

- **Sandboxed Execution** — Every agent runs in an isolated environment with deny-by-default access
- **Network Policy Enforcement** — Declarative egress rules prevent data exfiltration
- **Privacy Router** — Routes inference through NVIDIA cloud with PII anonymisation
- **Out-of-Process Controls** — Security enforcement happens outside the agent's process, immune to prompt injection

### Tech Stack

| Layer | Technologies |
|-------|-------------|
| **Backend** | Python 3.12, FastMCP, Redis (atomic budget locking), PostgreSQL (audit logs), asyncpg, httpx |
| **Frontend** | Next.js web dashboard — budget utilisation bars, risk heatmaps, AI CFO chat interface, searchable audit log, cron job management |
| **Payments** | Razorpay X integration (webhook + polling modes, Go MCP sidecar) |
| **Document AI** | HyperAPI (parse/classify/split/extract), Docling (FOSS PDF→Markdown), PaddleOCR (table extraction), invoice2data (template-based parsing) |
| **Agent Security** | NVIDIA NemoClaw + OpenShell (sandboxed runtime, network policy, privacy router) |
| **ML / AI** | scikit-learn IsolationForest anomaly detection, Azure OpenAI / local MLX LLM, Dual-LLM quarantine security pattern |
| **Notifications** | Slack, Telegram, ntfy (FOSS) — human-in-the-loop approval workflows |
| **CLI** | `npx vyapaarclaw bootstrap` & `npx vyapaarclaw start` — zero-config setup wizard |
| **Security** | HMAC-SHA256 webhook verification, atomic Redis INCRBY (no race conditions), circuit breakers, fail-closed design |
| **Infra** | Docker, GitHub Actions CI/CD, PyPI + GHCR publishing |

### Testing & Quality

- **214 tests** — unit, integration, and end-to-end
- Strict **mypy** type checking
- All amounts in **paise (integers)** — never floats for money

### FOSS Highlights

- **GLEIF** vendor verification (free, open API — no paid service needed)
- **ntfy** push notifications (fully self-hostable FOSS alternative to Slack)
- **scikit-learn** ML anomaly detection
- **Docling** (IBM) — FOSS document AI with MCP server support
- **PaddleOCR** (Baidu) — FOSS table recognition for financial reports
- **invoice2data** — FOSS invoice extraction with template system
- **NVIDIA NemoClaw** — open-source agent sandboxing
- **AGPL-3.0** licensed

### OpenClaw Integration

Built as a fully managed **OpenClaw Framework** — integrates with cron jobs (morning financial briefs, budget alarms, weekly compliance), webhooks, multi-agent delegation, canvas dashboards, and AI CFO skills.

---

# Development Expansion Plan

## Phase 1: HyperAPI Document Intelligence Integration

### 1.1 — HyperAPI MCP Bridge (`src/vyapaar_mcp/docai/`)

Create a new `docai` module that bridges HyperAPI's financial document intelligence APIs into VyapaarClaw's MCP server as new tools.

**New MCP Tools to add:**

| Tool Name | HyperAPI Endpoint | What It Does |
|-----------|-------------------|--------------|
| `parse_document` | `POST /v1/parse` | OCR text extraction from PDFs/images |
| `classify_document` | `POST /v1/classify` | Categorise document type (invoice, receipt, contract, tax form) |
| `split_document` | `POST /v1/split` | Segment multi-document PDFs into logical units |
| `extract_document` | `POST /v1/extract` | Extract structured data (invoice number, amounts, vendor, line items) |
| `process_document` | `POST /v1/process` | Unified parse + extract pipeline |
| `validate_invoice` | *internal* | Cross-reference extracted invoice data against governance policies |

**Implementation files:**

```
src/vyapaar_mcp/docai/
├── __init__.py
├── client.py            # HyperAPI httpx async client (parse/classify/split/extract)
├── models.py            # Pydantic V2 models for all HyperAPI responses
├── validator.py         # Invoice validation against agent policies (amount vs budget)
└── skill.py             # OpenClaw skill definition for document intelligence
```

**Config additions (`.env`):**

```bash
# HyperAPI Document Intelligence
VYAPAAR_HYPERAPI_KEY=hk_live_xxxxxxxxxxxx
VYAPAAR_HYPERAPI_BASE_URL=http://hyperapi-production-12097051.us-east-1.elb.amazonaws.com
```

**Key logic — Invoice Governance Bridge:**

When an agent submits an invoice for processing:
1. `parse_document` → OCR extracts raw text
2. `classify_document` → Confirms it's an invoice/receipt
3. `extract_document` → Pulls structured fields (vendor name, amount, date, line items)
4. `validate_invoice` → Cross-references extracted amount against agent's budget policy, runs vendor URL through Safe Browsing + GLEIF, and flags anomalies via IsolationForest
5. If validated → Creates a governed payout via `create_payout`

This creates an **end-to-end document-to-payout pipeline** — drop in a messy invoice PDF, VyapaarClaw does the rest.

### 1.2 — Install hyperbots-agent-skills as OpenClaw Skill

Clone and integrate the [hyperbots-agent-skills](https://github.com/guglxni/hyperbots-agent-skills) repo:

```bash
# Add as a skill in the skills/ directory
cp -r /path/to/hyperbots-agent-skills/skills/hyperbots-api skills/hyperbots-api
```

Update `templates/openclaw.json` to register the new skill.

---

## Phase 2: NVIDIA NemoClaw Sandboxed Runtime

### 2.1 — NemoClaw Bootstrap Integration

Add NemoClaw as an optional secure runtime for VyapaarClaw agents. This adds infrastructure-level security (sandboxing, network policy, privacy routing) on top of VyapaarClaw's application-level governance.

**New CLI command:**

```bash
npx vyapaarclaw nemoclaw:setup    # Install NemoClaw + onboard VyapaarClaw agent
npx vyapaarclaw nemoclaw:start    # Start sandboxed agent
npx vyapaarclaw nemoclaw:status   # Check sandbox health
```

**Implementation files:**

```
src/cli/nemoclaw.ts              # CLI commands for NemoClaw lifecycle
templates/nemoclaw-blueprint.json # NemoClaw sandbox blueprint with VyapaarClaw policies
```

**How it integrates:**

```
┌─────────────────────────────────────────────────────────────────┐
│                    NVIDIA NemoClaw (OpenShell)                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │              VyapaarClaw Agent (Sandboxed)                 │  │
│  │  ┌──────────┐  ┌──────────────┐  ┌─────────────────────┐ │  │
│  │  │ MCP      │  │  Governance  │  │  Document AI        │ │  │
│  │  │ Server   │→ │  Pipeline    │→ │  (HyperAPI/Docling)  │ │  │
│  │  └──────────┘  └──────────────┘  └─────────────────────┘ │  │
│  └───────────────────────────────────────────────────────────┘  │
│  Network Policy: razorpay.com, safebrowsing.googleapis.com      │
│  Filesystem: /sandbox (read-write), /tmp (ephemeral)            │
│  Inference: NVIDIA Cloud API (privacy router)                   │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 — NemoClaw Network Policy for VyapaarClaw

Define a strict egress allowlist specific to VyapaarClaw's needs:

```yaml
# nemoclaw-blueprint.json (network egress)
allowed_hosts:
  - api.razorpay.com           # Payout approve/reject
  - safebrowsing.googleapis.com # Vendor reputation
  - api.gleif.org              # Entity verification
  - api.hyperapi.dev           # Document intelligence
  - hooks.slack.com            # Human-in-the-loop
  - api.telegram.org           # Telegram notifications
  - ntfy.sh                    # FOSS push notifications
```

---

## Phase 3: FOSS Document Processing & Testing Pipeline

### 3.1 — FOSS OCR Fallback Stack

Add pure-FOSS document processing as a fallback when HyperAPI is unavailable or rate-limited, using only open-source tools:

| Tool | Purpose | License |
|------|---------|---------|
| **Docling** (`docling`) | PDF/DOCX → structured Markdown, layout analysis, XBRL parsing | MIT |
| **PaddleOCR** (`paddleocr`) | Table recognition (PP-TableMagic), complex financial report extraction | Apache 2.0 |
| **invoice2data** | Template-based invoice field extraction with regex patterns | MIT |
| **Tesseract** (`pytesseract`) | General OCR fallback | Apache 2.0 |

**Implementation files:**

```
src/vyapaar_mcp/docai/
├── foss_ocr.py          # FOSS OCR pipeline (Docling → PaddleOCR → Tesseract fallback)
├── invoice_parser.py    # invoice2data integration with custom YAML templates
└── table_extractor.py   # PaddleOCR PP-TableMagic for financial report tables
```

**Circuit breaker pattern:** If HyperAPI is down → fall back to Docling+PaddleOCR → fall back to Tesseract. Same pattern as existing Safe Browsing circuit breaker.

### 3.2 — Test Dataset Pipeline

Use the recommended datasets for comprehensive testing of document intelligence capabilities:

#### Vendor Invoices (Messy OCR)

| Dataset | Description | Source |
|---------|-------------|--------|
| **MIDD** | 630 invoices, 4 layouts, scanned versions | [MDPI / ResearchGate](https://www.mdpi.com/2306-5729/8/1/10) |
| **SROIE** | Scanned receipts — rotated, crumpled, noisy | [Kaggle](https://www.kaggle.com/datasets/urbikn/sroie-datasetv2) |

#### Financial Reports (Complex Tables)

| Dataset | Description | Source |
|---------|-------------|--------|
| **SEC EDGAR** | 10-K/10-Q PDF filings with complex multi-page tables | [SEC.gov EDGAR](https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany) |
| **PubLayNet** | Document images with layout annotations (tables, lists, paragraphs) | [GitHub - IBM/PubLayNet](https://github.com/ibm/PubLayNet) |

#### Tax Forms (Dense Key-Value)

| Dataset | Description | Source |
|---------|-------------|--------|
| **FUNSD** | Scanned forms with key/value/header annotations | [GitHub - FUNSD](https://guillaumejaume.github.io/FUNSD/) |
| **IRS Form Samples** | Historical 1040, K-1, etc. — print-and-rescan for challenge | [IRS.gov](https://www.irs.gov/forms-instructions) |

#### Messy Unstructured Documents

| Dataset | Description | Source |
|---------|-------------|--------|
| **DocVQA** | Documents with handwriting, stamps, overlapping text | [DocVQA.org](https://www.docvqa.org/) |

**Test implementation:**

```
tests/
├── test_docai_parse.py          # Parse accuracy on MIDD + SROIE
├── test_docai_classify.py       # Classification accuracy across document types
├── test_docai_extract.py        # Field extraction precision/recall on FUNSD
├── test_docai_tables.py         # Table extraction on SEC EDGAR PDFs
├── test_docai_invoice_to_payout.py  # End-to-end: invoice PDF → governance → payout decision
├── fixtures/
│   ├── invoices/                # Sample MIDD/SROIE invoices
│   ├── reports/                 # Sample SEC EDGAR pages
│   ├── tax_forms/               # Sample FUNSD/IRS forms
│   └── messy/                   # Sample DocVQA documents
```

**Benchmark script:**

```bash
# Run document intelligence benchmark across all datasets
uv run python scripts/benchmark_docai.py --datasets midd,sroie,funsd,edgar --report json
```

---

## Phase 4: Additional FOSS Integrations

### 4.1 — OpenBB Financial Data MCP Server

[OpenBB](https://github.com/OpenBB-finance/OpenBB) provides an open-source financial data platform with its own MCP server (`openbb-mcp-server`). Integrate it for:

- **Market data feeds** — Real-time stock/crypto prices for portfolio-aware governance
- **Financial statement data** — SEC filings, balance sheets, income statements
- **Economic indicators** — Interest rates, CPI, GDP for macro-aware risk scoring

```bash
pip install openbb[mcp]
```

**New MCP tools:**

| Tool | Purpose |
|------|---------|
| `get_market_data` | Fetch real-time prices for vendor stock tickers |
| `get_financial_statements` | Pull SEC filings for vendor due diligence |
| `get_macro_indicators` | Economic context for risk scoring |

### 4.2 — Docling MCP Server (IBM)

[Docling](https://github.com/docling-ai/docling) provides its own MCP server for document processing. Run it as a sidecar alongside VyapaarClaw:

```bash
pip install docling
# Docling provides a built-in MCP server for agentic applications
```

**Integration:**

- Use Docling's MCP server for PDF → Markdown conversion
- Feed Markdown into VyapaarClaw's governance pipeline
- Parse XBRL financial reports natively

### 4.3 — statement-parser (Bank Statements)

[statement-parser](https://pypi.org/project/statement-parser/) normalises bank statement CSVs/Excel into Pandas DataFrames:

- Import historical bank statements for agent budget calibration
- Cross-reference payout history against bank records
- Feed normalised data into anomaly detection model

---

## Implementation Priority

| Priority | Feature | Effort | Impact |
|----------|---------|--------|--------|
| 🔴 P0 | HyperAPI MCP tools (5 tools) | 2-3 days | Core differentiator — document-to-payout pipeline |
| 🔴 P0 | Invoice-to-governance bridge | 1-2 days | Links document AI to existing governance |
| 🟡 P1 | FOSS OCR fallback (Docling + PaddleOCR) | 2-3 days | True FOSS compliance, no vendor lock-in |
| 🟡 P1 | Test dataset pipeline (MIDD/SROIE/FUNSD) | 2 days | Proves accuracy, impresses judges |
| 🟡 P1 | NemoClaw bootstrap integration | 2-3 days | NVIDIA-grade agent security |
| 🟢 P2 | OpenBB financial data tools | 1-2 days | Market-aware risk scoring |
| 🟢 P2 | Docling MCP sidecar | 1 day | Additional FOSS document AI |
| 🟢 P2 | statement-parser integration | 1 day | Bank statement reconciliation |
| 🟢 P2 | NemoClaw network policy blueprint | 1 day | Hardened egress rules |

---

## Updated Project Structure

```
vyapaarclaw/
├── apps/web/              # Next.js web dashboard (existing)
├── src/
│   ├── cli/               # Node.js CLI (existing + nemoclaw.ts)
│   ├── vyapaar_mcp/       # Python MCP server
│   │   ├── audit/         # Decision logging (existing)
│   │   ├── db/            # Redis + PostgreSQL (existing)
│   │   ├── docai/         # NEW — Document Intelligence
│   │   │   ├── client.py          # HyperAPI async client
│   │   │   ├── models.py          # Pydantic models for document responses
│   │   │   ├── validator.py       # Invoice → governance bridge
│   │   │   ├── foss_ocr.py        # Docling + PaddleOCR + Tesseract fallback
│   │   │   ├── invoice_parser.py  # invoice2data templates
│   │   │   └── table_extractor.py # PaddleOCR table recognition
│   │   ├── egress/        # Notifications (existing)
│   │   ├── governance/    # Policy engine (existing)
│   │   ├── ingress/       # Webhooks + polling (existing)
│   │   ├── llm/           # Azure OpenAI (existing)
│   │   ├── observability/ # Metrics (existing)
│   │   ├── reputation/    # Safe Browsing, GLEIF, anomaly (existing)
│   │   ├── resilience/    # Circuit breakers (existing)
│   │   └── server.py      # FastMCP server (25 tools → 31+ tools)
│   └── entry.ts
├── skills/
│   ├── cfo/               # Core AI CFO skill (existing)
│   ├── cfo-delegation/    # Multi-agent delegation (existing)
│   ├── cfo-canvas/        # Canvas dashboards (existing)
│   └── hyperbots-api/     # NEW — HyperAPI document intelligence skill
├── templates/
│   ├── openclaw.json      # OpenClaw profile (existing, updated)
│   └── nemoclaw-blueprint.json  # NEW — NemoClaw sandbox config
├── tests/
│   ├── test_docai_*.py    # NEW — Document intelligence tests
│   └── fixtures/
│       ├── invoices/      # NEW — MIDD/SROIE samples
│       ├── reports/       # NEW — SEC EDGAR samples
│       ├── tax_forms/     # NEW — FUNSD samples
│       └── messy/         # NEW — DocVQA samples
├── scripts/
│   └── benchmark_docai.py # NEW — Document AI benchmark runner
└── vendor/
    └── nemoclaw/          # NemoClaw integration scripts
```

---

## FOSS Compliance Matrix

Every core capability has a FOSS alternative — no proprietary lock-in:

| Capability | Primary Tool | FOSS Fallback | License |
|-----------|-------------|---------------|---------|
| Document OCR | HyperAPI | Docling + Tesseract | MIT / Apache 2.0 |
| Table Extraction | HyperAPI Extract | PaddleOCR PP-TableMagic | Apache 2.0 |
| Invoice Parsing | HyperAPI Extract | invoice2data | MIT |
| Financial Data | — | OpenBB | AGPL-3.0 |
| Agent Sandboxing | NemoClaw | Docker isolation | Apache 2.0 |
| Vendor Reputation | Google Safe Browsing | VirusTotal (API) | — |
| Entity Verification | GLEIF | — | Open Data |
| Notifications | Slack | ntfy (self-hosted) | Apache 2.0 |
| Anomaly Detection | scikit-learn | — | BSD-3 |

---

## Key Judging Points

| Criteria | How VyapaarClaw Addresses It |
|----------|------------------------------|
| **Problem Solving** | Solves the critical trust gap in AI financial automation — agents can't spend unchecked |
| **FOSS License** | AGPL-3.0, every dependency has a FOSS fallback |
| **Completeness** | 25→31+ MCP tools, web dashboard, CLI, TUI, full test suite, CI/CD |
| **Code Quality** | `mypy --strict`, `ruff`, 214+ tests, Pydantic V2 strict models |
| **Documentation** | SPEC.md (1000+ lines), ARCHITECTURE.md, SYSTEM_DESIGN.md, SETUP.md |
| **Design** | Next.js dashboard with budget bars, risk heatmaps, AI chat, audit tables |
| **Video Demo** | 3-minute demo: bootstrap → invoice upload → governance → payout decision |
| **GitHub Activity** | Active development throughout March with meaningful commit messages |
| **Real-World Impact** | Any company deploying AI agents needs financial governance |
| **Creativity** | Novel "CFO-as-MCP" pattern + document-to-payout pipeline + NemoClaw sandboxing |
