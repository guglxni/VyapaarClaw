# VyapaarClaw — OpenClaw Showcase Technical Specification

> **Event:** OpenClaw Showcase by OpenAI, Razorpay & PeakXV (powered by GrowthX)  
> **Date:** Friday, March 13, 2026 | 6:00 PM – 9:00 PM IST  
> **Venue:** Razorpay HQ, SJR Cyber Laskar, Hosur Rd, Bengaluru  
> **Format:** Top 5 live demos, 5–10 min each + live Q&A

---

## 1. Project Identity

**VyapaarClaw** — *The Autonomous CFO for the Agentic Economy*

> A production-grade MCP governance server that sits between AI agents (via OpenClaw) and
> Razorpay X, intercepting every financial operation with 6 layers of security — budget
> enforcement, vendor reputation, ML anomaly detection, legal entity verification,
> domain policy enforcement, and human-in-the-loop approval.

### Tagline Options
- "Your AI's CFO — always watching, always enforcing budgets."
- "Protocol-level financial governance for autonomous agents."
- "The firewall between your AI agent and your bank account."

---

## 2. System Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    V Y A P A A R   M C P   S Y S T E M                  │
│                                                                         │
│  ┌───────────────┐     MCP/SSE      ┌────────────────────────────────┐ │
│  │   OpenClaw     │◄───────────────►│      VyapaarClaw Server        │ │
│  │   Agent        │                  │      (FastMCP, 12 Tools)       │ │
│  │  ┌───────────┐ │                  │                                │ │
│  │  │  Kimi K2.5│ │                  │  ┌─────────────────────────┐  │ │
│  │  │ (Azure AI)│ │                  │  │   GOVERNANCE ENGINE     │  │ │
│  │  └───────────┘ │                  │  │                         │  │ │
│  └───────────────┘                  │  │  1. Budget Guard (Redis) │  │ │
│                                      │  │  2. Rate Limiter         │  │ │
│                                      │  │  3. Domain Policy        │  │ │
│                                      │  │  4. Safe Browsing (Google)│  │ │
│                                      │  │  5. GLEIF Entity Check   │  │ │
│                                      │  │  6. ML Anomaly (IsoFor)  │  │ │
│                                      │  │  7. Human Approval Gate  │  │ │
│                                      │  └─────────────────────────┘  │ │
│                                      │                                │ │
│  ┌───────────────┐                  │  ┌─────────────────────────┐  │ │
│  │  Streamlit     │◄─── HTTP ──────►│  │  Razorpay Go Bridge     │  │ │
│  │  Dashboard     │                  │  │  (MCP/stdio → Go SDK)   │  │ │
│  │  (Command      │                  │  │  40+ native tools       │  │ │
│  │   Center)      │                  │  └───────────┬─────────────┘  │ │
│  └───────────────┘                  └──────────────┼────────────────┘ │
│                                                     │                   │
│                                              ┌──────▼──────┐           │
│                                              │  Razorpay X  │           │
│                                              │  Sandbox API │           │
│                                              └─────────────┘           │
│                                                                         │
│  ┌────────────┐   ┌────────────┐   ┌────────────┐   ┌──────────────┐  │
│  │   Redis     │   │ PostgreSQL │   │   Slack     │   │ ntfy (Push)  │  │
│  │  Budgets    │   │ Audit Logs │   │ Human Loop  │   │ Phone Alerts │  │
│  │  Rate Limit │   │ Policies   │   │ Approve/Rej │   │ Fallback     │  │
│  └────────────┘   └────────────┘   └────────────┘   └──────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Tech Stack

### Core Runtime

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| **Language** | Python | 3.12+ | Async-first, type-safe |
| **MCP Framework** | FastMCP | ≥1.0.0 | MCP server with SSE/stdio transport |
| **Package Manager** | UV | latest | Fast Python package management |
| **AI Model** | Kimi K2.5 | via Azure AI | Agent intelligence (chat completions) |
| **Payments** | Razorpay X | Go SDK + Python | Payout lifecycle management |
| **Go Sidecar** | razorpay-mcp-server | Go 1.25 | Native Razorpay API (40+ tools via MCP/stdio) |

### Data Layer

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Budget Tracking** | Redis 7+ (with hiredis) | Atomic `INCRBY` counters, rate limit sliding windows, idempotency keys |
| **Audit & Policy** | PostgreSQL 15+ (asyncpg) | Agent policies, audit trail, decision history |

### Security & Intelligence

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Vendor Reputation** | Google Safe Browsing v4 | Malware/phishing URL detection |
| **Legal Entity** | GLEIF API | LEI verification for vendor legitimacy |
| **ML Anomaly** | scikit-learn (IsolationForest) | Spending pattern anomaly detection |
| **Human Loop** | Slack Bot + ntfy | Interactive approve/reject for high-value txns |
| **Domain Policy** | Custom engine | Allowlist/blocklist enforcement |
| **Dual LLM** | Quarantine pattern | Prompt injection prevention |

### Observability

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Metrics** | Prometheus-compatible | Decision counts, latency, budget utilization |
| **Dashboard** | Streamlit | Real-time command center |
| **Circuit Breakers** | Custom implementation | Cascade failure prevention |

---

## 4. MCP Tool Registry (12 Tools)

### Governance Tools

| # | Tool | Type | Description |
|---|------|------|-------------|
| 1 | `handle_razorpay_webhook` | Ingress | Process Razorpay webhook → governance pipeline → approve/reject |
| 2 | `poll_razorpay_payouts` | Ingress | Poll Razorpay API for queued payouts (no tunnel needed) |
| 3 | `set_agent_policy` | Admin | Create/update per-agent spending policies |
| 4 | `handle_slack_action` | Human Loop | Process Slack approve/reject button callbacks |

### Intelligence Tools

| # | Tool | Type | Description |
|---|------|------|-------------|
| 5 | `check_vendor_reputation` | Reputation | Google Safe Browsing v4 threat check |
| 6 | `verify_vendor_entity` | Reputation | GLEIF legal entity verification |
| 7 | `score_transaction_risk` | ML | IsolationForest anomaly scoring |
| 8 | `get_agent_risk_profile` | ML | Historical spending pattern analysis |

### Observability Tools

| # | Tool | Type | Description |
|---|------|------|-------------|
| 9 | `get_agent_budget` | Read | Current daily spend and remaining budget |
| 10 | `get_audit_log` | Read | Decision history with filtering |
| 11 | `health_check` | Ops | Service connectivity (Redis, PG, Razorpay) |
| 12 | `get_metrics` | Ops | Prometheus-compatible metrics snapshot |

### Security Tools (Dual LLM Pattern)

| # | Tool | Type | Description |
|---|------|------|-------------|
| 13 | `check_context_taint` | Security | Detect if execution context is tainted |
| 14 | `validate_tool_call_security` | Security | Dual LLM quarantine validation |
| 15 | `azure_chat` | AI | Kimi K2.5 chat completion (marks context as tainted) |
| 16 | `get_archestra_status` | Security | Policy enforcement status |

---

## 5. Governance Decision Matrix

| # | Check | Pass → | Fail → | Reason Code |
|---|-------|--------|--------|-------------|
| 1 | Agent has policy? | Continue | REJECT | `NO_POLICY` |
| 2 | Amount ≤ per-txn limit? | Continue | REJECT | `TXN_LIMIT_EXCEEDED` |
| 3 | Rate limit OK? | Continue | REJECT | `RATE_LIMITED` |
| 4 | Daily budget OK? (atomic Redis) | Continue | REJECT | `LIMIT_EXCEEDED` |
| 5 | Domain not blocked? | Continue | REJECT | `DOMAIN_BLOCKED` |
| 6 | Google Safe Browsing = safe? | Continue | REJECT | `RISK_HIGH` |
| 7 | Amount ≤ approval threshold? | APPROVE | HOLD | `APPROVAL_REQUIRED` |
| 8 | All checks passed | APPROVE | — | `POLICY_OK` |

> **Design Principle:** Fail-closed. If any check fails or is unavailable, REJECT. It's safer to block a legitimate payment than approve a fraudulent one.

---

## 6. Razorpay Go Bridge (MCP Sidecar)

The Go sidecar is Razorpay's official MCP server, spawned as a subprocess:

```
Python (MCP client) ←—stdio—→ Go binary (MCP server) → Razorpay API
```

### Available Tool Categories (40+)

| Category | Tools |
|----------|-------|
| **Payouts** | `fetch_all_payouts`, `fetch_payout_with_id` |
| **Payments** | `fetch_all_payments`, `fetch_payment`, `capture_payment` |
| **Payment Links** | `create_payment_link`, `fetch_all_payment_links` |
| **Orders** | `create_order`, `fetch_all_orders` |
| **Refunds** | `create_refund`, `fetch_all_refunds` |
| **Settlements** | `fetch_all_settlements` |
| **Contacts** | Contact CRUD operations |
| **Fund Accounts** | Fund account management |

---

## 7. AI Model Configuration — Kimi K2.5

### Azure AI Endpoint

| Parameter | Value |
|-----------|-------|
| **Base URL** | `https://vyapaar.services.ai.azure.com/models` |
| **API Version** | `2024-05-01-preview` |
| **Model ID** | `kimi-k2.5` |
| **Transport** | OpenAI-compatible (Azure AI Inference) |

### Environment Variables

```bash
VYAPAAR_AZURE_OPENAI_ENDPOINT=https://vyapaar.services.ai.azure.com/models
VYAPAAR_AZURE_OPENAI_API_KEY=<provided-separately>
VYAPAAR_AZURE_OPENAI_DEPLOYMENT=kimi-k2.5
VYAPAAR_AZURE_OPENAI_API_VERSION=2024-05-01-preview
```

### Usage in Governance

Kimi K2.5 powers:
1. **`azure_chat` tool** — General-purpose chat for governance copilot queries
2. **Security LLM validation** — Dual LLM quarantine pattern for prompt injection defense
3. **Agent intelligence** — OpenClaw agent reasoning and tool selection

---

## 8. Database Schema

### PostgreSQL Tables

```sql
-- Agent spending policies
CREATE TABLE agent_policies (
    agent_id            VARCHAR(128) PRIMARY KEY,
    daily_limit         BIGINT NOT NULL DEFAULT 500000,  -- paise (₹5,000)
    per_txn_limit       BIGINT DEFAULT NULL,
    require_approval_above BIGINT DEFAULT NULL,
    allowed_domains     TEXT[] DEFAULT '{}',
    blocked_domains     TEXT[] DEFAULT '{}',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Immutable audit trail
CREATE TABLE audit_logs (
    id              BIGSERIAL PRIMARY KEY,
    payout_id       VARCHAR(64) NOT NULL UNIQUE,
    agent_id        VARCHAR(128) NOT NULL,
    amount          BIGINT NOT NULL,                    -- paise
    currency        VARCHAR(3) NOT NULL DEFAULT 'INR',
    vendor_name     TEXT,
    vendor_url      TEXT,
    decision        VARCHAR(20) NOT NULL,               -- APPROVED/REJECTED/HELD
    reason_code     VARCHAR(64) NOT NULL,
    reason_detail   TEXT,
    threat_types    TEXT[],
    processing_ms   INTEGER,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### Redis Keys

| Key Pattern | Type | TTL | Purpose |
|-------------|------|-----|---------|
| `vyapaar:budget:{agent_id}:{YYYYMMDD}` | Integer | 25h | Daily spend counter |
| `vyapaar:idempotent:{webhook_id}` | String | 48h | Webhook deduplication |
| `vyapaar:reputation:{url_hash}` | JSON | 5min | Safe Browsing cache |
| `vyapaar:rate:{agent_id}:{window}` | Sorted Set | dynamic | Rate limit window |
| `vyapaar:health:last_check` | String | 60s | Health check cache |

---

## 9. Live Demo Script (7 Scenes, ~5 Minutes)

### Pre-Demo Setup
```bash
# 1. Start infrastructure
docker compose up -d redis postgres

# 2. Seed agent policies
uv run python scripts/seed_policies.py

# 3. Start VyapaarClaw server
uv run python -m vyapaar_mcp

# 4. Open dashboard
streamlit run demo/dashboard.py
```

### Scene-by-Scene Flow

#### Scene 1: The Setup (30s)
**Show:** OpenClaw agent connected to VyapaarClaw with 12 tools registered.
**Talk:** "This MCP server governs every rupee an AI agent spends through Razorpay."

#### Scene 2: Legitimate Payout — APPROVED (60s)
**Action:** Agent requests ₹2,500 to Google LLC
**Pipeline:** Budget check → Safe Browsing → GLEIF → All pass → **APPROVED** ✅
**Talk:** "Every layer checked. Google is a verified legal entity, URL is clean, budget is fine."

#### Scene 3: Malware Vendor — BLOCKED (45s)
**Action:** Agent tries to pay `sketchy-vendor.xyz`
**Pipeline:** Safe Browsing flags MALWARE → **REJECTED** 🚫
**Talk:** "Your AI just tried to pay a malware distribution site. Blocked instantly."

#### Scene 4: Budget Breach — REJECTED (30s)
**Action:** Agent tries ₹50,000 but daily limit is ₹10,000
**Pipeline:** Atomic Redis INCRBY → exceeds limit → rollback → **REJECTED** 🚫
**Talk:** "Sub-millisecond budget enforcement. Atomic Redis operations prevent overspending."

#### Scene 5: Human Approval — HELD (60s)
**Action:** Agent requests ₹8,000 (above ₹5,000 approval threshold)
**Pipeline:** All checks pass but amount→ threshold → **HELD** → Slack notification → Reviewer approves ✅
**Talk:** "High-value transactions need human sign-off. Show Slack on phone."

#### Scene 6: ML Anomaly — FLAGGED (45s)
**Action:** Night-bot sends ₹25,000 at an unusual hour
**Pipeline:** IsolationForest scores 0.92 anomaly → **FLAGGED** ⚠️
**Talk:** "ML detected this doesn't match the agent's historical spending pattern."

#### Scene 7: The Dashboard (30s)
**Show:** Streamlit command center with all decisions streaming in real-time.
**Talk:** "Complete audit trail, Prometheus metrics, budget utilization — all in one view."

---

## 10. Project Structure

```
vyapaarclaw/
├── src/vyapaar_mcp/              # Core application
│   ├── server.py                   # FastMCP server (12+ tools, SSE transport)
│   ├── config.py                   # Pydantic Settings (env-based config)
│   ├── models.py                   # Pydantic V2 data models (strict mode)
│   ├── security.py                 # Security utilities
│   ├── logging_config.py           # Structured logging
│   ├── governance/                 # Policy enforcement engine
│   │   └── engine.py               # Decision matrix orchestrator
│   ├── ingress/                    # Data ingress (webhooks, polling)
│   │   ├── webhook.py              # Razorpay webhook handler + HMAC verification
│   │   ├── polling.py              # API polling (no tunnel needed)
│   │   └── razorpay_bridge.py      # Go MCP sidecar bridge (40+ tools)
│   ├── reputation/                 # Vendor intelligence
│   │   ├── safe_browsing.py        # Google Safe Browsing v4
│   │   ├── gleif.py                # GLEIF legal entity verification
│   │   └── anomaly.py              # ML anomaly detection (IsolationForest)
│   ├── egress/                     # Outbound actions
│   │   ├── razorpay_actions.py     # Approve/reject payouts
│   │   ├── slack_notifier.py       # Slack human-in-the-loop
│   │   └── ntfy_notifier.py        # Push notification fallback
│   ├── db/                         # Data layer
│   │   ├── redis_client.py         # Atomic budget ops, rate limiting
│   │   └── postgres.py             # Audit logs, policy CRUD
│   ├── llm/                        # AI/LLM clients
│   │   ├── azure_client.py         # Kimi K2.5 via Azure AI
│   │   └── security_validator.py   # Dual LLM quarantine pattern
│   ├── observability/              # Metrics & monitoring
│   │   └── metrics.py              # Prometheus-compatible metrics
│   └── resilience/                 # Fault tolerance
│       └── circuit_breaker.py      # Circuit breaker pattern
├── demo/                           # Demo scripts & dashboard
│   ├── dashboard.py                # Streamlit command center
│   ├── automated_demo.py           # Automated 12-tool demo
│   └── cli_demo.py                 # Interactive CLI demo
├── scripts/                        # Operations scripts
│   ├── seed_policies.py            # Seed sample agent policies
│   ├── simulate_webhook.py         # Send test webhooks
│   └── health_check.py             # Service health verification
├── tests/                          # Test suite (13 files)
│   ├── conftest.py                 # Shared fixtures
│   ├── test_governance.py          # Decision engine tests
│   ├── test_budget.py              # Atomic budget tests
│   ├── test_webhook.py             # Signature verification tests
│   ├── test_anomaly.py             # ML anomaly tests
│   ├── test_gleif.py               # GLEIF integration tests
│   ├── test_slack.py               # Slack notifier tests
│   ├── test_ntfy.py                # Push notification tests
│   ├── test_resilience.py          # Circuit breaker tests
│   └── ...
├── docs/                           # Documentation
│   ├── OPENCLAW_SHOWCASE.md        # This file
│   └── ...
├── deploy/                         # Deployment configs
├── docker-compose.yml              # Local infrastructure
├── pyproject.toml                  # Project config (UV)
├── SPEC.md                         # Full technical specification
└── README.md                       # Project overview
```

---

## 11. Environment Variables

```bash
# ── Razorpay X (Sandbox) ──────────────────────────────
VYAPAAR_RAZORPAY_KEY_ID=rzp_test_...
VYAPAAR_RAZORPAY_KEY_SECRET=...
VYAPAAR_RAZORPAY_WEBHOOK_SECRET=              # optional (polling mode)
VYAPAAR_RAZORPAY_ACCOUNT_NUMBER=...

# ── Azure AI — Kimi K2.5 ──────────────────────────────
VYAPAAR_AZURE_OPENAI_ENDPOINT=https://vyapaar.services.ai.azure.com/models
VYAPAAR_AZURE_OPENAI_API_KEY=<to-be-provided>
VYAPAAR_AZURE_OPENAI_DEPLOYMENT=kimi-k2.5
VYAPAAR_AZURE_OPENAI_API_VERSION=2024-05-01-preview

# ── Google Safe Browsing v4 ────────────────────────────
VYAPAAR_GOOGLE_SAFE_BROWSING_KEY=...

# ── Infrastructure ─────────────────────────────────────
VYAPAAR_REDIS_URL=redis://localhost:6379/0
VYAPAAR_POSTGRES_DSN=postgresql://vyapaar:...@localhost:5432/vyapaar_db

# ── Slack (Human-in-the-Loop) ──────────────────────────
VYAPAAR_SLACK_BOT_TOKEN=xoxb-...
VYAPAAR_SLACK_CHANNEL_ID=...

# ── Server ─────────────────────────────────────────────
VYAPAAR_HOST=0.0.0.0
VYAPAAR_PORT=8000
VYAPAAR_LOG_LEVEL=INFO
VYAPAAR_AUTO_POLL=true
VYAPAAR_POLL_INTERVAL=30
```

---

## 12. Security Model (6 Layers)

```
Layer 1: Google Safe Browsing v4 ──► Blocks malware/phishing vendor URLs
    │
Layer 2: GLEIF Verification ───────► Confirms vendor is a registered legal entity
    │
Layer 3: Budget Enforcement ───────► Atomic Redis INCRBY prevents overspending
    │
Layer 4: Human Approval Gate ──────► Slack interactive buttons for high-value txns
    │
Layer 5: ML Anomaly Detection ────► IsolationForest catches unusual patterns
    │
Layer 6: Domain Policy Engine ────► Real-time allow/blocklist enforcement
```

### Fail-Closed Design

| Failure | Response |
|---------|----------|
| Redis down | REJECT all (cannot verify budget) |
| PostgreSQL down | REJECT all (cannot fetch policy) |
| Safe Browsing timeout | HOLD for manual review |
| Safe Browsing 4xx | HOLD + alert ops |
| Razorpay 5xx | Retry with exponential backoff (max 3) |

---

## 13. Competitive Differentiators

| What Others Show | What Vyapaar Shows |
|------------------|-------------------|
| Chatbot calling one API | Full governance layer with 12 MCP tools + Go sidecar (40+ Razorpay tools) |
| No security consideration | 6-layer deep defense (SB, GLEIF, ML, Budget, Policy, Human) |
| Demo/mock data | Live Razorpay sandbox with real API calls |
| Simple prompt engineering | Atomic Redis budget enforcement with race condition prevention |
| No auditability | Streamlit command center + Prometheus metrics + PostgreSQL audit trail |
| No human oversight | Slack human-in-the-loop with interactive approve/reject |

---

## 14. Q&A Preparation

| Question | Answer |
|----------|--------|
| "Why not just use Razorpay's built-in approval queue?" | Razorpay's queue is binary. We add 6 intelligence layers before the payout even hits their queue — ML anomaly detection, vendor reputation, budget atomicity, domain policies, GLEIF entity verification, and human-in-the-loop. |
| "How does this scale?" | Budget checks are atomic Redis INCRBY (sub-millisecond). Circuit breakers prevent cascade failures. Async Python throughout. Go sidecar handles Razorpay API calls natively. |
| "Is this production-ready?" | Real MCP server with 13 test files, Go sidecar bridge to Razorpay's official MCP server, live sandbox API keys, PostgreSQL audit trail. Every decision logged. |
| "What's the business model?" | SaaS governance layer. Per-agent monthly pricing. Think "Cloudflare for AI spending." |
| "Why MCP protocol?" | Protocol-level interception. The agent calls our governance tools — it literally cannot bypass the CFO. This is architectural enforcement, not prompt-level enforcement. |

---

*VyapaarClaw — Built for the OpenClaw Showcase, March 2026*
