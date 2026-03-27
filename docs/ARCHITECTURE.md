# VyapaarClaw Architecture

## Overview

VyapaarClaw is an enterprise-grade Model Context Protocol (MCP) server written in Python, functioning as an **AI CFO** for financial governance. It evaluates, audits, and securely orchestrates corporate payouts, ensuring tight human-in-the-loop and LLM-driven policy alignment before funds move via platforms like Razorpay.

The system exposes **37 MCP tools** across three intelligence layers: **KNOW** (intelligence), **GUARD** (governance), and **ACT** (execution).

## Full Architecture Diagram

```mermaid
graph TB
    %% Professional C4 Architecture Styling
    classDef default fill:#FFFFFF,stroke:#333333,stroke-width:2px,color:#333333,font-family:sans-serif;
    classDef interface fill:#E0E7FF,stroke:#3B82F6,color:#1E40AF,rx:8,ry:8,stroke-width:2px;
    classDef engine fill:#1E40AF,stroke:#1E3A8A,color:#FFFFFF,rx:8,ry:8,stroke-width:2px;
    classDef layer fill:#F9FAFB,stroke:#9CA3AF,color:#1F2937,rx:8,ry:8,stroke-width:2px;
    classDef intelligence fill:#EFF6FF,stroke:#3B82F6,color:#1E40AF,rx:8,ry:8,stroke-width:2px;
    classDef governance fill:#FEF3C7,stroke:#F59E0B,color:#92400E,rx:8,ry:8,stroke-width:2px;
    classDef execution fill:#DCFCE7,stroke:#10B981,color:#065F46,rx:8,ry:8,stroke-width:2px;
    classDef boundary fill:none,stroke:#6B7280,stroke-width:2px,stroke-dasharray: 4 4;

    subgraph SystemBoundary[VyapaarClaw Extended System Architecture]
        direction TB

        MCP["Core MCP Server<br/>[FastAPI / 37 Tools]"]:::engine

        subgraph LayersBoundary[Functional Tiers]
            direction TB
            subgraph KNOW[Cognitive & Intelligence Tier]
                direction LR
                FC["Cash Flow Forecaster<br/>[Darts/EWMA]"]:::intelligence
                TC["Transaction Categorizer<br/>[FinBERT]"]:::intelligence
                CA["Contract Analysis<br/>[spaCy/Regex]"]:::intelligence
                FX["Currency Conversion<br/>[Frankfurter]"]:::intelligence
                CAL["Financial Calendar<br/>[Holidays]"]:::intelligence
            end

            subgraph GUARD[Risk & Governance Tier]
                direction LR
                GOV["6-Layer Governance<br/>[Pipeline]"]:::governance
                GFD["Graph Fraud Detection<br/>[NetworkX]"]:::governance
                KYB["Vendor KYB Engine<br/>[OpenSanctions/GLEIF]"]:::governance
                BV["Bank Validation<br/>[RBI/IFSC]"]:::governance
                GST["Compliance Engine<br/>[GST/TDS]"]:::governance
                WF["Approval Workflows<br/>[State Machine]"]:::governance
            end

            subgraph ACT[Execution & Operations Tier]
                direction LR
                PAY["Payment Gateway Integration<br/>[Razorpay]"]:::execution
                LED["Double-Entry Ledger<br/>[python-acct]"]:::execution
                RPT["Document Generation<br/>[FPDF2]"]:::execution
                NTF["Notification Broker<br/>[Slack/TG/ntfy]"]:::execution
            end
        end
    end

    %% Interactions
    AGENT["AI Client Agent"]:::interface <-->|Tool Execution| MCP
    DASH["Admin Dashboard<br/>[Next.js]"]:::interface <-->|REST/GraphQL| MCP
    CLAW["OpenClaw Framework"]:::interface <-->|Integration| MCP

    MCP -->|Delegates to| KNOW
    KNOW -->|Validates via| GUARD
    GUARD -->|Triggers| ACT

    class SystemBoundary,LayersBoundary boundary
```

## Three-Layer Architecture

### 🧠 KNOW — Intelligence Layer

The intelligence layer provides the CFO with financial awareness:

| Component | Tool | FOSS Library |
|-----------|------|-------------|
| **Cash Flow Forecaster** | `forecast_budget_runway` | Darts/EWMA + numpy |
| **Transaction Categorizer** | `categorize_transaction` | Keyword matching + FinBERT |
| **Contract Analyzer** | `analyze_contract` | spaCy/Regex NLP |
| **Currency Converter** | `convert_currency` | Frankfurter API (ECB data) |
| **Financial Calendar** | `get_indian_financial_calendar` | holidays + exchange_calendars |

### 🛡️ GUARD — Governance Layer

The governance layer enforces policy and catches fraud:

| Component | Tool | FOSS Library |
|-----------|------|-------------|
| **6-Layer Pipeline** | `score_transaction_risk` | IsolationForest + GLEIF + Safe Browsing |
| **Graph Fraud Detection** | `detect_fraud_network` | NetworkX + PyGOD |
| **Vendor KYB** | `screen_vendor_sanctions` | OpenSanctions + GLEIF |
| **Bank Validation** | `validate_bank_account` | razorpay/ifsc (RBI data) |
| **GST Compliance** | `validate_gstin`, `calculate_gst`, `check_tds` | gst_validator_india |
| **Approval Workflow** | `manage_payout_workflow` | Transitions (state machine) |

### ⚡ ACT — Execution Layer

The execution layer performs actions:

| Component | Tool | FOSS Library |
|-----------|------|-------------|
| **Razorpay Payouts** | `create_payout` | Razorpay Go MCP sidecar |
| **Double-Entry Ledger** | `track_payout_in_ledger`, `get_trial_balance` | python-accounting |
| **PDF Reports** | `generate_compliance_report` | FPDF2 |
| **Notifications** | `send_slack_notification` | Slack / Telegram / ntfy |

## Payout Approval Workflow

Every payout passes through a formal state machine with multi-level approvals:

```mermaid
stateDiagram-v2
    %% Professional State Diagram Styling
    classDef state fill:#EFF6FF,stroke:#3B82F6,color:#1E40AF,stroke-width:2px,rx:5,ry:5,font-family:sans-serif;
    classDef terminal fill:#374151,stroke:#111827,color:#FFFFFF,stroke-width:2px;
    classDef error fill:#FEE2E2,stroke:#EF4444,color:#991B1B,stroke-width:2px;
    classDef success fill:#DCFCE7,stroke:#10B981,color:#065F46,stroke-width:2px;

    [*] --> queued: Agent Initiates Request

    state queued {
        [*] --> Pending
    }

    queued --> policy_check: Begin Review
    
    state policy_check {
        [*] --> ValidatingConstraints
    }
    
    policy_check --> reputation_check: Policy Met
    policy_check --> held: Policy Violation
    policy_check --> rejected: Fatal Policy Error

    state reputation_check {
        [*] --> VerifyingEntity
    }

    reputation_check --> anomaly_check: Identity Verified
    reputation_check --> held: Elevated Risk
    reputation_check --> rejected: Entity Blocked

    state anomaly_check {
        [*] --> RunningModels
    }

    anomaly_check --> approved: Low Anomaly Score
    anomaly_check --> held: High Anomaly Score
    anomaly_check --> rejected: Critical Fraud Risk

    state held {
        [*] --> AwaitingManualAction
    }

    held --> pending_l1_approval: Escalate to Tier 1
    
    state pending_l1_approval {
        [*] --> Tier1Review
    }
    
    pending_l1_approval --> approved: Tier 1 Approved
    pending_l1_approval --> pending_l2_approval: Escalate to Tier 2
    pending_l1_approval --> rejected: Tier 1 Denied

    state pending_l2_approval {
        [*] --> Tier2Review
    }

    pending_l2_approval --> approved: Tier 2 Approved
    pending_l2_approval --> rejected: Tier 2 Denied

    state approved {
        [*] --> ReadyForExecution
    }

    approved --> disbursed: Trigger Payout Gateway
    
    state disbursed {
        [*] --> TransferInitiated
    }
    
    disbursed --> confirmed: Webhook Verified
    disbursed --> failed: Transfer Failed
    
    confirmed --> archived: Finalize
    rejected --> archived: Finalize
    failed --> archived: Finalize

    state archived {
        [*] --> RecordStored
    }

    archived --> [*]

    class queued,policy_check,reputation_check,anomaly_check state
    class held,pending_l1_approval,pending_l2_approval state
    class rejected,failed error
    class approved,confirmed success
    class archived terminal
```

## Governance Pipeline Flow

End-to-end flow from invoice/transaction input through governance to decision:

```mermaid
flowchart LR
    %% Professional Pipeline Styling
    classDef default fill:#FFFFFF,stroke:#333333,stroke-width:2px,color:#333333,font-family:sans-serif;
    classDef input fill:#F3F4F6,stroke:#6B7280,color:#1F2937,rx:8,ry:8,stroke-width:2px;
    classDef pipeline fill:#E0E7FF,stroke:#3B82F6,color:#1E40AF,rx:8,ry:8,stroke-width:2px;
    classDef intel fill:#FEF3C7,stroke:#F59E0B,color:#92400E,rx:8,ry:8,stroke-width:2px;
    classDef approve fill:#DCFCE7,stroke:#10B981,color:#065F46,rx:8,ry:8,stroke-width:2px;
    classDef hold fill:#FEF08A,stroke:#D97706,color:#78350F,rx:8,ry:8,stroke-width:2px;
    classDef reject fill:#FEE2E2,stroke:#EF4444,color:#991B1B,rx:8,ry:8,stroke-width:2px;
    classDef output fill:#F8FAFC,stroke:#9CA3AF,color:#374151,rx:8,ry:8,stroke-width:2px;
    classDef boundary fill:none,stroke:#9CA3AF,stroke-width:2px,stroke-dasharray: 4 4;

    subgraph InputBoundary[Ingestion Sources]
        INV["Invoice Document"]:::input
        TXN["Transaction Record"]:::input
        VENDOR["Vendor Identity"]:::input
    end

    subgraph PipelineBoundary[Sequential Governance Pipeline]
        direction TB
        P1["Phase 1<br/>Policy & Budget Checks"]:::pipeline
        P2["Phase 2<br/>Bank & IFSC Validation"]:::pipeline
        P3["Phase 3<br/>GSTIN Verification"]:::pipeline
        P4["Phase 4<br/>Reputation Check<br/>(Safe Browsing/GLEIF)"]:::pipeline
        P5["Phase 5<br/>Sanctions Screening"]:::pipeline
        P6["Phase 6<br/>Fraud Detection<br/>(ML/Graph Analysis)"]:::pipeline
        
        P1 --> P2 --> P3 --> P4 --> P5 --> P6
    end

    subgraph CFOBoundary[Financial Intelligence Processing]
        direction TB
        CAT["Classification Engine"]:::intel
        GST["Tax Calculation"]:::intel
        FX2["Currency Exchange"]:::intel
        FORE["Forecasting Impact"]:::intel
    end

    subgraph ResolutionBoundary[Decision & Execution]
        APR["AUTHORIZED"]:::approve
        HLD["QUARANTINED"]:::hold
        REJ["DECLINED"]:::reject
        LED2["Ledger Commitment"]:::output
        RPT2["Audit Report Generation"]:::output
    end

    INV --> PipelineBoundary
    TXN --> PipelineBoundary
    VENDOR --> PipelineBoundary
    
    PipelineBoundary --> CFOBoundary
    CFOBoundary --> APR
    CFOBoundary --> HLD
    CFOBoundary --> REJ
    
    APR --> LED2
    APR --> RPT2

    class InputBoundary,PipelineBoundary,CFOBoundary,ResolutionBoundary boundary
```

## FOSS Compliance Matrix

Every core capability has a FOSS alternative — no proprietary lock-in:

```mermaid
graph TD
    %% Professional Component Styling
    classDef default fill:#FFFFFF,stroke:#333333,stroke-width:2px,color:#333333,font-family:sans-serif;
    classDef primary fill:#EFF6FF,stroke:#3B82F6,color:#1E40AF,rx:8,ry:8,stroke-width:2px;
    classDef secondary fill:#F3F4F6,stroke:#6B7280,color:#374151,rx:8,ry:8,stroke-width:2px;
    classDef tier fill:none,stroke:#9CA3AF,stroke-width:2px,stroke-dasharray: 4 4;

    subgraph MatrixBoundary[Open Source Dependency & Compliance Matrix]
        direction TB
        
        subgraph Layer1[Tier 1: Document Processing]
            HA["HyperAPI<br/>[Primary Engine]"]:::primary
            DOC["Docling<br/>[MIT License]"]:::secondary
            TESS["Tesseract<br/>[Apache 2.0]"]:::secondary
            POCR["PaddleOCR<br/>[Apache 2.0]"]:::secondary
            
            HA -.->|Fallback Strategy| DOC
            DOC -.->|Fallback Strategy| TESS
            HA -.->|Table Extraction| POCR
        end

        subgraph Layer2[Tier 2: Financial Intelligence]
            DARTS["Darts<br/>[Apache 2.0]"]:::primary
            PROPHET["Prophet<br/>[MIT License]"]:::secondary
            SKLEARN["scikit-learn<br/>[BSD-3 Clause]"]:::primary
            NX["NetworkX<br/>[BSD-3 Clause]"]:::primary
        end

        subgraph Layer3[Tier 3: Regional Compliance]
            GSTV["gst_validator<br/>[MIT License]"]:::primary
            IFSC["razorpay/ifsc<br/>[MIT License]"]:::primary
            HOL["holidays<br/>[MIT License]"]:::primary
            FRANK["Frankfurter<br/>[MIT License]"]:::primary
        end

        subgraph Layer4[Tier 4: Vendor Trust & Verification]
            GLEIF2["GLEIF Database<br/>[Open Data]"]:::primary
            SB["Google Safe Browsing<br/>[Public API]"]:::secondary
            OS["OpenSanctions<br/>[MIT License]"]:::primary
        end

        subgraph Layer5[Tier 5: Core Infrastructure]
            REDIS["Redis Store<br/>[BSD-3 Clause]"]:::primary
            PG["PostgreSQL<br/>[PostgreSQL License]"]:::primary
            FPDF["FPDF2<br/>[LGPL 3.0]"]:::secondary
            TRANS["Transitions<br/>[MIT License]"]:::primary
        end
    end

    class MatrixBoundary,Layer1,Layer2,Layer3,Layer4,Layer5 tier
```

## Core Components

1. **MCP Server Engine (37 Tools)**:
   - Standard MCP JSON-RPC Server interface enabling connection to LLM clients
   - Serves internal Python actions and bridges externally to Go-based binaries

2. **AI CFO & Governance LLMs**:
   - Uses context windows to evaluate `HELD`, `APPROVED` or `REJECTED` states
   - Leverages localized MLX Mistral schemas, enforcing compliance safely off-grid
   - Dual-LLM quarantine pattern for prompt injection defense

3. **CFO Intelligence Layer** (NEW):
   - **Forecasting**: Budget runway prediction with EWMA trend detection
   - **Categorization**: Auto-tagging payouts by spending category
   - **Contract Analysis**: NLP extraction of payment terms and penalty clauses
   - **GST/TDS Compliance**: GSTIN validation, tax calculation, TDS deduction
   - **Multi-Currency**: Live FX rates with historical auditing
   - **Graph Fraud Detection**: Shared PAN/bank account detection, circular payment rings
   - **Sanctions Screening**: OpenSanctions watchlist + GLEIF entity verification
   - **Double-Entry Ledger**: IFRS-style journal entries for every payout
   - **PDF Reports**: Auto-generated compliance reports with charts

4. **Data Tier (Postgres & Redis)**:
   - **PostgreSQL (`asyncpg`)**: Immutable event logging, payout decisions, audit trails
   - **Redis (`hiredis`)**: Rate-limits, budget caching, anomaly detection computations

5. **User Interfaces**:
   - **Terminal UI (`Textual`)**: Deep system-level debugging, live metric feeds
   - **Web UI (`Next.js / React`)**: Human-facing CFO dashboard

6. **Exposed Action Providers (Egress)**:
   - **Razorpay**: Direct payout disbursement and vendor link creation
   - **Slack / Telegram / ntfy**: Notification channels for human-in-the-loop approvals

## Project Structure

```
vyapaarclaw/
├── apps/web/                    # Next.js web dashboard
├── src/
│   ├── cli/                     # Node.js CLI
│   ├── vyapaar_mcp/             # Python MCP server
│   │   ├── audit/               # Decision logging
│   │   ├── cfo/                 # 🆕 CFO Intelligence Layer
│   │   │   ├── calendar.py      #   Indian financial calendar
│   │   │   ├── currency.py      #   Multi-currency FX conversion
│   │   │   ├── tax.py           #   GST/TDS compliance
│   │   │   ├── bank.py          #   IFSC/bank validation
│   │   │   ├── categorizer.py   #   Expense categorization
│   │   │   ├── forecaster.py    #   Cash flow forecasting
│   │   │   ├── ledger.py        #   Double-entry bookkeeping
│   │   │   ├── fraud.py         #   Graph fraud detection
│   │   │   ├── workflow.py      #   Payout state machine
│   │   │   ├── reports.py       #   PDF report generation
│   │   │   ├── sanctions.py     #   OpenSanctions screening
│   │   │   └── contracts.py     #   Contract analysis
│   │   ├── db/                  # Redis + PostgreSQL
│   │   ├── egress/              # Notifications + Razorpay
│   │   ├── governance/          # Policy engine
│   │   ├── ingress/             # Webhooks + polling
│   │   ├── llm/                 # Azure OpenAI / Dual-LLM
│   │   ├── observability/       # Metrics
│   │   ├── reputation/          # Safe Browsing, GLEIF, anomaly
│   │   ├── resilience/          # Circuit breakers
│   │   └── server.py            # FastMCP server (37 tools)
│   └── entry.ts
├── skills/                      # OpenClaw skills
├── docs/
│   ├── diagrams/                # 🆕 Mermaid + PNG diagrams
│   ├── ARCHITECTURE.md          # This file
│   ├── SYSTEM_DESIGN.md         # Security governance
│   ├── FOSS_RESEARCH.md         # FOSS tools research
│   └── FOSSHACK_SUBMISSION.md   # Submission content
└── tests/
```
