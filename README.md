<div align="center">
  <img src="assets/logo.png" alt="VyapaarClaw Logo" width="400"/>
</div>

**Fully Managed OpenClaw Framework for AI Financial Governance.**
The AI CFO for the agentic economy.

VyapaarClaw is an [OpenClaw](https://openclaw.ai) framework that transforms AI agents into financially governed entities. It provides a complete governance layer — budget enforcement, vendor verification, risk scoring, compliance reporting, and human-in-the-loop approvals — so AI agents can handle real money without uncontrolled spending.

```
npx vyapaarclaw bootstrap   # Set up credentials & OpenClaw profile
npx vyapaarclaw start        # Launch MCP server + Web UI + OpenClaw gateway
```

---

## Architecture

Three-layer AI CFO architecture: **KNOW** (intelligence) → **GUARD** (governance) → **ACT** (execution):

```mermaid
graph TD
    %% Scientific Block Diagram
    classDef ext fill:#fff,stroke:#333,stroke-width:1px,stroke-dasharray: 3 3,font-family:monospace;
    classDef core fill:#f0f0f0,stroke:#000,stroke-width:1px,font-family:monospace;
    classDef node fill:#fff,stroke:#333,stroke-width:1px,font-family:monospace;

    Client(["Agent Client"]):::ext -->|JSON-RPC| MCP
    
    subgraph VyapaarClaw ["System Architecture (VyapaarClaw)"]
        direction TB
        MCP["MCP Server Engine"]:::core
        
        subgraph Pipeline ["Three-Tier Logic Processing"]
            direction TB
            KNOW["L1: Intelligence<br/>(Forecasting, Classification, FX)"]:::node
            GUARD["L2: Governance<br/>(Policy, Fraud, Validations)"]:::node
            ACT["L3: Execution<br/>(Payouts, Ledger, Reports)"]:::node
            
            KNOW --> GUARD --> ACT
        end
        
        MCP --> Pipeline
    end
    
    Pipeline -->|Webhooks/APIs| Integrations(["External Services<br/>(Razorpay, Slack)"]):::ext
```

## Features

### 37 MCP Tools (25 Governance + 12 CFO Intelligence)

| Category | Tools |
|----------|-------|
| **Budget Control** | `get_agent_budget`, `set_agent_policy`, `get_daily_spend`, `reallocate_budget` |
| **Vendor Verification** | `check_vendor_reputation`, `verify_vendor_entity`, `get_vendor_trust_score` |
| **Risk & Scoring** | `get_risk_score`, `evaluate_payout`, `detect_anomaly` |
| **Compliance** | `generate_compliance_report`, `get_spending_trends`, `get_financial_calendar` |
| **Monitoring** | `list_agents`, `forecast_cash_flow`, `get_audit_log` |
| **Payments** | `create_payout`, `get_payout_status`, `process_webhook` |
| **Notifications** | `send_slack_approval`, `send_telegram_alert` |
| **🆕 India Tax** | `validate_gstin`, `calculate_gst`, `check_tds` |
| **🆕 Banking** | `validate_bank_account` (IFSC/account validation) |
| **🆕 Multi-Currency** | `convert_currency` (Frankfurter FX, ECB data) |
| **🆕 Calendar** | `get_indian_financial_calendar` (holidays, deadlines, T+N settlement) |
| **🆕 Categorization** | `categorize_transaction` (auto-tagging spending categories) |
| **🆕 Forecasting** | `forecast_budget_runway` (EWMA trend, runway days, severity) |
| **🆕 Accounting** | `track_payout_in_ledger`, `get_trial_balance`, `get_income_statement` |
| **🆕 Reports** | `generate_compliance_report` (PDF with charts) |
| **🆕 Fraud** | `detect_fraud_network` (graph-based: shared PAN, circular payments) |
| **🆕 Contracts** | `analyze_contract` (payment terms, penalty clauses, SLA) |
| **🆕 Sanctions** | `screen_vendor_sanctions` (OpenSanctions watchlists) |
| **🆕 Workflow** | `manage_payout_workflow` (formal state machine approvals) |

### Web Dashboard

A Next.js application providing:

- **Dashboard** — Budget utilisation bars, decision stats, risk heatmap
- **Chat** — Conversational interface to the AI CFO
- **Agents** — Agent policies, trust tiers, budget health
- **Audit Log** — Searchable governance decision history *(Driven by robust CRM Data Tables integrated directly from DenchClaw)*
- **Cron Jobs** — Scheduled autonomous operations

### OpenClaw Integration

- **Cron Jobs** — Morning financial brief, budget alarms, weekly compliance reports
- **Webhooks** — Razorpay payment event processing
- **Multi-Agent Delegation** — Spawn sub-agents for vendor due diligence
- **Canvas Dashboard** — Real-time financial visualisations
- **Skills** — CFO, delegation, and canvas skills for OpenClaw agents

### Governance Pipeline

Every transaction passes through a 6-layer verification:

1. **Webhook Signature Verification** — Razorpay HMAC validation
2. **Agent Policy Enforcement** — Daily limits, per-txn limits, domain restrictions
3. **Vendor Reputation Check** — Google Safe Browsing threat analysis
4. **Entity Verification** — GLEIF legal entity lookup
5. **ML Anomaly Detection** — Isolation Forest on transaction patterns
6. **Risk Scoring** — Composite score with automatic decision routing

---

## Quick Start

### Prerequisites

- **Python 3.12+** and [uv](https://docs.astral.sh/uv/)
- **Node.js 22+** and pnpm
- **Redis** — Budget tracking and caching
- **PostgreSQL** — Audit logs and policies
- **OpenClaw** — Required core framework for the AI agents, gateway, Slack integration, and autonomous cron features

### Installation

```bash
# Clone and install
git clone https://github.com/guglxni/VyapaarClaw.git
cd VyapaarClaw

# Install Python dependencies
uv sync --dev

# Install Node.js dependencies
pnpm install --no-frozen-lockfile

# Build the CLI and web UI
pnpm build
pnpm web:build

# Run the bootstrap wizard
node vyapaarclaw.mjs bootstrap
```

### Running

```bash
# Start everything (MCP server + Web UI + OpenClaw gateway)
node vyapaarclaw.mjs start

# Start MCP server only
node vyapaarclaw.mjs start --mcp-only

# Start without web UI
node vyapaarclaw.mjs start --no-web

# Check status
node vyapaarclaw.mjs status

# Stop all services
node vyapaarclaw.mjs stop
```

### Development

```bash
# Run MCP server in dev mode
VYAPAAR_TRANSPORT=sse uv run vyapaarclaw

# Run web UI in dev mode
pnpm web:dev

# Run Python tests
uv run pytest tests/ --ignore=tests/test_razorpay_bridge.py

# Run linter
uv run ruff check src/vyapaar_mcp/
```

---

## Project Structure

```
vyapaarclaw/
├── apps/web/              # Next.js web dashboard
│   ├── app/
│   │   ├── components/    # Dashboard, shell, charts
│   │   ├── agents/        # Agent policies page
│   │   ├── audit/         # Audit log page
│   │   ├── chat/          # CFO chat interface
│   │   └── cron/          # Scheduled jobs page
│   └── package.json
├── src/
│   ├── cli/               # Node.js CLI (bootstrap, program, web-runtime)
│   ├── vyapaar_mcp/       # Python MCP server
│   │   ├── audit/         # Decision logging
│   │   ├── db/            # Redis + PostgreSQL clients
│   │   ├── egress/        # Notifications (Slack, Telegram, ntfy)
│   │   ├── governance/    # Policy engine
│   │   ├── ingress/       # Webhooks + polling
│   │   ├── llm/           # Azure OpenAI integration
│   │   ├── observability/ # Metrics + monitoring
│   │   ├── reputation/    # Safe Browsing, GLEIF, anomaly detection
│   │   ├── resilience/    # Circuit breakers
│   │   └── server.py      # FastMCP server (25 tools)
│   └── entry.ts           # CLI entry point
├── skills/                # OpenClaw skills
│   ├── cfo/               # Core AI CFO skill
│   ├── cfo-delegation/    # Multi-agent delegation patterns
│   └── cfo-canvas/        # Canvas dashboard templates
├── templates/             # OpenClaw profile templates
├── tests/                 # Python test suite (214 tests)
└── vyapaarclaw.mjs        # CLI binary
```

---

## Configuration

### Environment Variables

| Variable | Description |
|----------|-------------|
| `VYAPAAR_RAZORPAY_KEY_ID` | Razorpay API key |
| `VYAPAAR_RAZORPAY_KEY_SECRET` | Razorpay API secret |
| `VYAPAAR_RAZORPAY_WEBHOOK_SECRET` | Razorpay webhook HMAC secret |
| `VYAPAAR_REDIS_URL` | Redis connection URL |
| `VYAPAAR_PG_DSN` | PostgreSQL connection string |
| `VYAPAAR_SAFE_BROWSING_KEY` | Google Safe Browsing API key |
| `VYAPAAR_SLACK_BOT_TOKEN` | Slack bot token for Human-in-the-Loop |
| `VYAPAAR_SLACK_CHANNEL_ID` | Slack channel ID for alerting |
| `VYAPAAR_AZURE_OPENAI_ENDPOINT` | AI endpoint (Azure / Local MLX) |
| `VYAPAAR_AZURE_OPENAI_API_KEY` | AI authentication key |

### OpenClaw Profile

The `templates/openclaw.json` configures:

- **Channels** — Telegram integration for approvals and alerts
- **Cron** — Morning brief (daily), budget alarm (30 min), weekly compliance
- **Webhooks** — Razorpay payment event processing
- **Skills** — CFO, delegation, and canvas skills
- **MCP Server** — Connection to VyapaarClaw at `localhost:8000/sse`

---

## Inspired By

- [DenchClaw](https://github.com/DenchHQ/DenchClaw) — Fully Managed OpenClaw Framework for CRM & Sales
- [OpenClaw](https://openclaw.ai) — The personal AI assistant framework

## License

[AGPL-3.0](LICENSE)
