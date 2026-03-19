# FOSS Research — Expanding VyapaarClaw into a Full AI CFO

> Beyond payments governance: tools, libraries, and repos that can transform VyapaarClaw from a payout firewall into a complete autonomous AI Chief Financial Officer.

---

## 1. Double-Entry Bookkeeping & Accounting Engine

**Why a CFO needs this:** You can't govern spending you don't track. A proper ledger is the backbone of financial governance.

| Tool | What It Does | License | Link |
|------|-------------|---------|------|
| **python-accounting** | IFRS/GAAP-compliant double-entry bookkeeping — Income Statements, Balance Sheets, Cash Flow Statements, multi-entity support, tamper protection | MIT | [GitHub](https://github.com/ekmett/python-accounting) |
| **Pyluca** | Headless double-entry accounting — plug-and-play Python module for journal entries and balances | MIT | [GitHub](https://github.com/Lazarus-org/pyluca) |
| **Finac** | Double-entry bookkeeping with multi-currency support, SQLite/SQLAlchemy backend | MIT | [PyPI](https://pypi.org/project/finac/) |
| **Django Ledger** | Full financial management system — Chart of Accounts, financial statements, multi-tenancy, built on Django | GPLv3 | [PyPI](https://pypi.org/project/django-ledger/) |

**Integration idea → `track_transaction` MCP tool:**
Every time VyapaarClaw approves a payout, auto-generate a journal entry in a ledger. This creates a full double-entry accounting trail that goes way beyond the current flat `audit_logs` table.

---

## 2. Cash Flow Forecasting & Time Series Prediction

**Why a CFO needs this:** A CFO doesn't just look at the past — they predict the future. "At this spend rate, you'll run out of budget in 12 days."

| Tool | What It Does | License | Link |
|------|-------------|---------|------|
| **Darts** | Comprehensive time series forecasting — ARIMA, Prophet, XGBoost, transformers, probabilistic forecasting, backtesting | Apache 2.0 | [GitHub](https://github.com/unit8co/darts) |
| **Prophet** (Meta) | Business forecasting with strong seasonality — daily/weekly/yearly patterns, holiday effects | MIT | [GitHub](https://github.com/facebook/prophet) |
| **numpy-financial** | Financial math functions — PMT, NPV, IRR, IPMT, PPMT | BSD-3 | [PyPI](https://pypi.org/project/numpy-financial/) |
| **cashflows** | Investment modelling — compound interest, bond valuation, loan analysis, cash flow streams | MIT | [ReadTheDocs](https://cashflows.readthedocs.io/) |
| **finstmt** | Financial statement modelling — historical free cash flows, forecasting future FCF | MIT | [GitHub](https://github.com/nickderobertis/finstmt) |

**Integration idea → `forecast_cash_flow` MCP tool (enhanced):**
VyapaarClaw already has a `forecast_cash_flow` tool stub. Wire it to Darts + Prophet: feed in historical spend data from PostgreSQL, predict when the agent will exhaust its budget, and auto-alert when burn rate is unsustainable.

---

## 3. Expense Categorisation & Transaction Classification

**Why a CFO needs this:** Raw transaction descriptions are meaningless. "NEFT/vendor_pay_2024" needs to become "Office Supplies → Recurring → Low Risk".

| Tool | What It Does | License | Link |
|------|-------------|---------|------|
| **expense-classifier (Cashboard)** | UPI/NEFT transaction categorisation — rule-based + AI-ready classification for Indian payments | MIT | [GitHub](https://github.com/Petrinax/expense-classifier) |
| **SmartSpend** | ML expense categorisation — Logistic Regression + TF-IDF on bill descriptions + OCR | MIT | [GitHub](https://github.com/ravindran-dev/SmartSpend) |
| **Finance-TransactionCategorizer** | Naive Bayes transaction classifier — learns from user feedback, dynamic per-user categories | MIT | [GitHub](https://github.com/Foxel05/Finance-TransactionCategorizer) |
| **Hugging Face `FinancialBERT`** | Pre-trained BERT for financial text — sentiment + classification on financial narratives | Apache 2.0 | [HuggingFace](https://huggingface.co/yiyanghkust/finbert-tone) |

**Integration idea → `categorize_transaction` MCP tool:**
Auto-tag every payout with a category (salaries, vendor supplies, SaaS subscriptions, marketing, etc.). Feed categories into the anomaly detection model — "This agent usually pays for SaaS tools but just tried to pay for legal services."

---

## 4. GST & India Tax Compliance

**Why a CFO needs this:** India-specific. Every B2B payout needs GST treatment — CGST/SGST/IGST calculation, GSTIN validation, TDS deduction awareness.

| Tool | What It Does | License | Link |
|------|-------------|---------|------|
| **gst_validator_india** | GSTIN validation — checksum verification, OCR repair engine, PAN extraction, Composition Dealer detection, RCM applicability | MIT | [Libraries.io](https://libraries.io/pypi/gst-validator-india) |
| **india-compliance** | Full GST compliance on ERPNext/Frappe — GSTR-1 filing, GSTR-2B reconciliation, e-invoice + e-waybill, real-time GSTIN validation | GPLv3 | [GitHub](https://github.com/resilient-tech/india-compliance) |
| **gst_irn** | GST e-invoicing — generate Invoice Reference Numbers (IRN) via IRP portal | MIT | [GitHub](https://github.com/AhmedSabry/gst_irn) |
| **gst-calculator** | Simple GST rate calculator (New Regime) | MIT | [PyPI](https://pypi.org/project/gst-calculator/) |

**Integration idea → `validate_gst` + `calculate_tax` MCP tools:**
Before approving a vendor payout, validate their GSTIN against checksums. Calculate applicable GST and flag if TDS needs to be deducted. Auto-generate GST-compliant invoice metadata.

---

## 5. Multi-Currency & Exchange Rates

**Why a CFO needs this:** International vendor payments need live FX rates. ₹ → $ → € conversions must be tracked at the rate on the day of transaction.

| Tool | What It Does | License | Link |
|------|-------------|---------|------|
| **Frankfurter** | Free FX rate API — ECB data, daily updates, historical rates, self-hostable, no API key needed | MIT | [frankfurter.dev](https://frankfurter.dev/) |
| **forex-python** | Python FX library — currency conversion, historical rates since 1999, ECB data | MIT | [PyPI](https://pypi.org/project/forex-python/) |
| **exchange-api** | Free FX API — 200+ currencies including crypto, no rate limits, daily updates | Unlicense | [GitHub](https://github.com/fawazahmed0/exchange-api) |

**Integration idea → `convert_currency` MCP tool:**
When processing cross-border payouts, auto-convert to INR equivalent for budget enforcement. Log the exchange rate used for audit trailing. Flag FX exposure if cumulative USD payouts exceed a threshold.

---

## 6. Financial Report Generation (PDF)

**Why a CFO needs this:** Board presentations, compliance filings, and stakeholder reports need to be auto-generated — not manually assembled.

| Tool | What It Does | License | Link |
|------|-------------|---------|------|
| **FPDF2** | PDF creation — text, tables, images, charts, custom layouts | LGPL-3.0 | [GitHub](https://github.com/py-pdf/fpdf2) |
| **ReportLab** | Enterprise PDF generation — complex layouts, financial charts, professional quality | BSD-3 | [reportlab.com](https://www.reportlab.com/) |
| **WeasyPrint** | HTML/CSS → PDF — render beautiful reports from Jinja2 templates | BSD-3 | [GitHub](https://github.com/Kozea/WeasyPrint) |
| **Plotly** | Interactive charts — financial dashboards, candlestick charts, heatmaps, exportable to static images | MIT | [plotly.com](https://plotly.com/python/) |

**Integration idea → `generate_compliance_report` MCP tool (enhanced):**
Auto-generate PDF compliance reports: spending summary, vendor risk heatmap, anomaly flags, GSTIN compliance status, FX exposure, budget utilisation charts. Schedule via OpenClaw cron: "every Friday, generate weekly CFO report and post to Slack."

---

## 7. Contract & Vendor Agreement Analysis

**Why a CFO needs this:** Before paying a vendor, the CFO should know: what does the contract say? Are payment terms NET-30 or NET-60? Are there penalty clauses?

| Tool | What It Does | License | Link |
|------|-------------|---------|------|
| **LangExtract** (Google) | LLM-powered structured extraction from unstructured docs — user-defined schemas, source grounding | Apache 2.0 | [GitHub](https://github.com/google/langextract) |
| **RiskLexis** | Contract clause risk classification — T5 transformer, risk levels (Low/Med/High), actionable recommendations | MIT | [GitHub](https://github.com/ifrahnz26/RiskLexis) |
| **OpenContracts** | Collaborative document annotation platform — LLM-powered queries, semantic search, version control | Apache 2.0 | [GitHub](https://github.com/Open-Source-Legal/OpenContracts) |
| **spaCy** | Industrial NLP — Named Entity Recognition for extracting parties, dates, amounts from contracts | MIT | [spacy.io](https://spacy.io/) |

**Integration idea → `analyze_contract` MCP tool:**
Upload a vendor contract → extract payment terms, penalty clauses, SLA commitments → auto-set the agent policy (e.g., if contract says NET-30, flag any payment before 30 days as early; if there's a penalty clause, escalate to HOLD).

---

## 8. IFSC/Bank Validation & UPI Verification (India)

**Why a CFO needs this:** Before sending money, verify the destination bank account actually exists and the IFSC code is real. Catch typos before they become failed payouts.

| Tool | What It Does | License | Link |
|------|-------------|---------|------|
| **razorpay/ifsc** | Official IFSC code database — RBI + NPCI data, offline validation, NACH/IMPS member status | MIT | [GitHub](https://github.com/razorpay/ifsc) |
| **py-validate-india** | Indian document validators — IFSC, PAN, Aadhaar, GST format validation | MIT | [GitHub](https://github.com/soheltarir/py-validate-india) |
| **ifscApi** | IFSC → bank name/branch/address lookup | MIT | [PyPI](https://pypi.org/project/ifscApi/) |

**Integration idea → `validate_bank_account` MCP tool:**
Before `create_payout`, validate the fund account's IFSC code against the RBI database. Check if the bank is an IMPS/NACH member. Reject payouts to invalid bank accounts before they even reach Razorpay.

---

## 9. Approval Workflow & State Machine Engine

**Why a CFO needs this:** HELD payouts need formal approval workflows — not just a Slack button. Multi-level approvals, escalation chains, audit-tracked state transitions.

| Tool | What It Does | License | Link |
|------|-------------|---------|------|
| **SpiffWorkflow** | BPMN → executable Python workflows — visual diagram editor, complex approval chains, human tasks | LGPL-3.0 | [GitHub](https://github.com/sartography/SpiffWorkflow) |
| **python-statemachine** | Elegant state machine — compound states, guards, callbacks, async support | MIT | [ReadTheDocs](https://python-statemachine.readthedocs.io/) |
| **Transitions** | Lightweight FSM — callbacks, guards, diagram generation, well-documented | MIT | [GitHub](https://github.com/pytransitions/transitions) |

**Integration idea → Formal payout lifecycle:**
Replace the simple APPROVED/REJECTED/HELD with a full state machine:
```
QUEUED → POLICY_CHECK → REPUTATION_CHECK → ANOMALY_CHECK → 
  → APPROVED (auto) → DISBURSED → CONFIRMED
  → HELD → PENDING_L1_APPROVAL → PENDING_L2_APPROVAL → APPROVED → DISBURSED
  → REJECTED → ARCHIVED
```
Each transition is logged to PostgreSQL with timestamp, actor, and reason.

---

## 10. Financial Calendar & Business Day Computation

**Why a CFO needs this:** "Pay by next business day" means different things when Holi, Diwali, and RBI settlement holidays are involved.

| Tool | What It Does | License | Link |
|------|-------------|---------|------|
| **holidays** | Country-specific holiday calendars — India national + state holidays, custom calendars | MIT | [PyPI](https://pypi.org/project/holidays/) |
| **exchange_calendars** | Securities exchange trading calendars — 50+ exchanges, NSE/BSE India support | Apache 2.0 | [GitHub](https://github.com/gerrymanoim/exchange_calendars) |
| **networkdays** | Business day calculation — no dependencies, custom holidays, project scheduling | MIT | [PyPI](https://pypi.org/project/networkdays/) |

**Integration idea → `get_financial_calendar` MCP tool (enhanced):**
The existing tool is a stub. Wire it to the `holidays` library with Indian calendar: know that payouts scheduled on Diwali will settle on the next business day. Calculate T+2 settlement dates for NEFT/RTGS. Warn agents: "This payout will arrive 3 days late because of a bank holiday weekend."

---

## 11. Graph-Based Fraud Detection

**Why a CFO needs this:** Beyond IsolationForest (single-transaction anomalies) → detect fraud *networks*. "These 5 vendor accounts all share the same PAN — it's a fraud ring."

| Tool | What It Does | License | Link |
|------|-------------|---------|------|
| **UGFraud** | Unsupervised graph fraud detection — MRF, dense-block detection, SVD on bipartite graphs | MIT | [GitHub](https://github.com/safe-graph/UGFraud) |
| **DGFraud** | Deep graph fraud detection — GNN-based detectors for financial networks | Apache 2.0 | [GitHub](https://github.com/safe-graph/DGFraud) |
| **PyGOD** | Graph outlier detection — anomalous nodes/edges in transaction graphs | BSD-2 | [GitHub](https://github.com/pygod-team/pygod) |
| **NetworkX** | Graph analysis fundamentals — PageRank, centrality, community detection | BSD-3 | [networkx.org](https://networkx.org/) |

**Integration idea → `detect_fraud_network` MCP tool:**
Build a transaction graph: agents → vendors → bank accounts. Use NetworkX + PyGOD to detect:
- Vendor accounts with suspicious centrality (all agents pay the same vendor)
- Circular payment patterns (agent A pays vendor B who pays agent C)
- Shared PAN/IFSC clusters suggesting shell companies

---

## 12. Vendor Due Diligence & KYB

**Why a CFO needs this:** Beyond Safe Browsing (is the URL malicious?) → full Know Your Business checks. Is this a real company? Are they sanctioned? Do they have negative news?

| Tool | What It Does | License | Link |
|------|-------------|---------|------|
| **OpenSanctions** | Global sanctions & PEP watchlists — 100+ data sources, entity matching, fuzzy search | MIT | [opensanctions.org](https://www.opensanctions.org/) |
| **Negative-News (NNSAT)** | Adverse media screening — Google Custom Search + sentiment analysis for company names | MIT | [GitHub](https://github.com/your-user/NNSAT) |
| **GLEIF** *(already integrated)* | Legal Entity Identifier (LEI) lookup — global company registration verification | Open Data | [gleif.org](https://www.gleif.org/) |

**Integration idea → `screen_vendor` MCP tool:**
Before approving a large payout, run a multi-layered vendor screen:
1. **GLEIF** — Is the entity registered? (already done)
2. **OpenSanctions** — Is the entity/owner on any watchlist?
3. **NNSAT** — Any recent adverse news coverage?
4. **Safe Browsing** — Is their domain safe? (already done)

Result: a composite "Vendor Trust Score" that feeds into the risk decision.

---

## Summary — What a Full AI CFO Looks Like

```
┌─────────────────────────────────────────────────────────────────────┐
│                        VyapaarClaw — Full AI CFO                     │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                    KNOW (Intelligence Layer)                   │   │
│  │  📊 Darts/Prophet forecasting                                 │   │
│  │  🏷️  Transaction categorisation (FinBERT)                     │   │
│  │  📄 Contract analysis (LangExtract/spaCy)                    │   │
│  │  💱 Live FX rates (Frankfurter)                               │   │
│  │  📅 Indian financial calendar (holidays + exchange_calendars) │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                              ↓                                       │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                    GUARD (Governance Layer)                    │   │
│  │  🛡️  6-layer governance pipeline (existing)                   │   │
│  │  🔍 Graph fraud detection (PyGOD/NetworkX)                   │   │
│  │  🏢 Vendor KYB (OpenSanctions + GLEIF + Safe Browsing)       │   │
│  │  🏦 IFSC/bank validation (razorpay/ifsc)                     │   │
│  │  🧾 GST compliance (gst_validator_india)                     │   │
│  │  🔀 Formal state machine approvals (SpiffWorkflow)           │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                              ↓                                       │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                    ACT (Execution Layer)                       │   │
│  │  💸 Razorpay payout disbursement (existing)                   │   │
│  │  📒 Double-entry ledger (python-accounting)                   │   │
│  │  📑 PDF compliance reports (FPDF2/WeasyPrint)                │   │
│  │  🔔 Multi-channel notifications (Slack/Telegram/ntfy)        │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Integration Priority for FOSS Hack

| Priority | Feature | FOSS Tool | New MCP Tools | Effort |
|----------|---------|-----------|---------------|--------|
| 🔴 P0 | Cash flow forecasting | Darts + Prophet | `forecast_cash_flow` (enhanced) | 2d |
| 🔴 P0 | Expense categorisation | FinBERT / expense-classifier | `categorize_transaction` | 2d |
| 🔴 P0 | GST validation | gst_validator_india | `validate_gst` | 1d |
| 🔴 P0 | IFSC bank validation | razorpay/ifsc | `validate_bank_account` | 1d |
| 🟡 P1 | Double-entry ledger | python-accounting | `track_transaction`, `get_balance_sheet` | 3d |
| 🟡 P1 | PDF report generation | FPDF2 + Plotly | `generate_compliance_report` (enhanced) | 2d |
| 🟡 P1 | Indian financial calendar | holidays + exchange_calendars | `get_financial_calendar` (enhanced) | 1d |
| 🟡 P1 | Multi-currency FX | Frankfurter | `convert_currency` | 1d |
| 🟢 P2 | Graph fraud detection | PyGOD + NetworkX | `detect_fraud_network` | 3d |
| 🟢 P2 | Contract analysis | LangExtract + spaCy | `analyze_contract` | 3d |
| 🟢 P2 | Sanctions screening | OpenSanctions | `screen_vendor` | 2d |
| 🟢 P2 | Approval state machine | SpiffWorkflow / Transitions | Internal refactor | 2d |

**Total new MCP tools: 10–12** (bringing VyapaarClaw from 25 → 35+ tools)
