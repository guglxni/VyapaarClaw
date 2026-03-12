# VyapaarClaw

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

Follows a heavily guarded 6-layer protocol level execution topology:

![VyapaarClaw Architecture](docs/architecture.png)

## Features

### 25 MCP Governance Tools

| Category | Tools |
|----------|-------|
| **Budget Control** | `get_agent_budget`, `set_agent_policy`, `get_daily_spend`, `reallocate_budget` |
| **Vendor Verification** | `check_vendor_reputation`, `verify_vendor_entity`, `get_vendor_trust_score` |
| **Risk & Scoring** | `get_risk_score`, `evaluate_payout`, `detect_anomaly` |
| **Compliance** | `generate_compliance_report`, `get_spending_trends`, `get_financial_calendar` |
| **Monitoring** | `list_agents`, `forecast_cash_flow`, `get_audit_log` |
| **Payments** | `create_payout`, `get_payout_status`, `process_webhook` |
| **Notifications** | `send_slack_approval`, `send_telegram_alert` |

### Web Dashboard

A Next.js application providing:

- **Dashboard** — Budget utilisation bars, decision stats, risk heatmap
- **Chat** — Conversational interface to the AI CFO
- **Agents** — Agent policies, trust tiers, budget health
- **Audit Log** — Searchable governance decision history
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
- **OpenClaw** (optional) — For gateway, Telegram, and cron features

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

| Variable | Required | Description |
|----------|----------|-------------|
| `VYAPAAR_RAZORPAY_KEY_ID` | Yes | Razorpay API key |
| `VYAPAAR_RAZORPAY_KEY_SECRET` | Yes | Razorpay API secret |
| `VYAPAAR_REDIS_URL` | Yes | Redis connection URL |
| `VYAPAAR_PG_DSN` | Yes | PostgreSQL connection string |
| `VYAPAAR_SAFE_BROWSING_KEY` | No | Google Safe Browsing API key |
| `VYAPAAR_WEBHOOK_SECRET` | No | Razorpay webhook HMAC secret |
| `TELEGRAM_BOT_TOKEN` | No | Telegram bot for HITL approvals |
| `VYAPAAR_SLACK_TOKEN` | No | Slack bot for HITL approvals |
| `VYAPAAR_AZURE_ENDPOINT` | No | Azure OpenAI endpoint |
| `VYAPAAR_AZURE_KEY` | No | Azure OpenAI key |

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
