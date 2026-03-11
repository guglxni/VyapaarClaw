# Project Checkpoint: VyapaarClaw

> *Internal prototype record*

**Date:** 2026-02-11
**Status:** Production Ready (Full Feature Set)
**Tests:** 79/79 PASSED
**Previous:** [CHECKPOINT_v4.md](CHECKPOINT_v4.md)

---

## 🚀 Executive Summary

VyapaarClaw builds on the Hybrid Architecture with four major additions:

1. **Slack Integration** — HELD payouts trigger human-in-the-loop approval requests in Slack. Security-relevant rejections send alert notifications.
2. **Auto-Polling** — Background polling with configurable intervals replaces manual `poll_razorpay_payouts` calls. Set `VYAPAAR_AUTO_POLL=true` for cron-style automation.
3. **CLI Audit Dashboard** — Real-time terminal-based audit log viewer with color-coded decisions, filtering, and live tail mode.
4. **Prometheus Metrics** — Full observability with decision counters, latency histograms, budget/reputation stats, and Prometheus text exposition format.

---

## 🏗 Architecture

```mermaid
graph TD
    User[Developer / Cron] -->|poll_razorpay_payouts| PyServer(VyapaarClaw Python)
    Razorpay[Razorpay API] -->|Webhook: payout.queued| PyServer
    
    subgraph "VyapaarClaw (Python)"
        Ingress[Ingress Layer]
        Governance[Governance Engine]
        Bridge[Razorpay Bridge]
        Slack[Slack Notifier]
        Metrics[Prometheus Metrics]
    end
    
    subgraph "Sidecar (Go)"
        GoBinary[razorpay-mcp-server]
    end
    
    PyServer --> Governance
    Governance -->|Redis Atomic Lock| Redis[(Redis)]
    Governance -->|Policy Check| Postgres[(PostgreSQL)]
    Governance -->|Reputation Check| GSB[Google Safe Browsing]
    
    Governance -->|HELD| Slack
    Slack -->|Approval Request| SlackAPI[Slack Channel]
    
    Governance -->|Action: Approve/Reject| Bridge
    Bridge -->|MCP via stdio| GoBinary
    GoBinary -->|Native Go SDK| Razorpay
    
    Governance -->|Record| Metrics
    Metrics -->|/metrics| Prometheus[Prometheus / Archestra]
```

---

## ✅ Progress Report

| Feature | Status | Notes |
|:---|:---|:---|
| **Webhook Ingress** | ✅ Done | Signature verification, idempotency, model parsing. |
| **Governance Engine** | ✅ Done | Redis atomic locking, Postgres policies, domain blocking. |
| **Reputation System** | ✅ Done | Google Safe Browsing v4 + Redis caching. |
| **Go Integration** | ✅ Done | Python bridge spawns Go binary successfully. |
| **Polling Mode** | ✅ Done | `poll_razorpay_payouts` + auto-polling background task. |
| **Slack Integration** | ✅ **NEW** | HELD → approval request, REJECTED → security alert. |
| **Auto-Polling** | ✅ **NEW** | `VYAPAAR_AUTO_POLL=true` for cron-style background polling. |
| **CLI Dashboard** | ✅ **NEW** | `scripts/audit_dashboard.py` with tail mode. |
| **Prometheus Metrics** | ✅ **NEW** | `get_metrics` tool + Prometheus text format. |
| **Tests** | ✅ Done | **79/79 passing** (up from 52). |
| **Scripts** | ✅ Done | `seed_policies.py`, `simulate_webhook.py`, `audit_dashboard.py`. |

---

## 📁 New Files

| File | Purpose |
|:---|:---|
| `src/vyapaar_mcp/egress/slack_notifier.py` | Slack API integration — approval requests & rejection alerts |
| `src/vyapaar_mcp/observability/__init__.py` | Prometheus metrics collector with text exposition format |
| `scripts/audit_dashboard.py` | CLI audit dashboard with color, filtering, and tail mode |
| `tests/test_slack.py` | 11 tests for Slack notification logic |
| `tests/test_metrics.py` | 16 tests for Prometheus metrics collector |

## 🔧 Modified Files

| File | Changes |
|:---|:---|
| `src/vyapaar_mcp/server.py` | Added Slack, metrics, auto-poll wiring; new `get_metrics` tool |
| `src/vyapaar_mcp/config.py` | Added `slack_bot_token`, `slack_channel_id`, `auto_poll` fields |
| `src/vyapaar_mcp/egress/__init__.py` | Updated docstring |
| `archestra.yaml` | Added `poll_razorpay_payouts`, `get_metrics` tools; Slack secrets |
| `.env.example` | Added `VYAPAAR_AUTO_POLL`, `VYAPAAR_POLL_INTERVAL` |
| `README.md` | Documented dashboard, Slack, metrics |
| `scripts/seed_policies.py` | Fixed bug: `pg.close()` → `pg.disconnect()` |

---

## 🛠 Handover Instructions

### 1. Build the Go Binary (One-time)
```bash
cd vendor/razorpay-mcp-server
go build -o ../../bin/razorpay-mcp-server ./cmd/razorpay-mcp-server
cd ../..
```

### 2. Run the Server
```bash
docker compose up -d redis postgres
PYTHONPATH=src uv run mcp run src/vyapaar_mcp/server.py
```

### 3. Run the Tests
```bash
PYTHONPATH=src uv run pytest tests/ -v
```

### 4. Use the Audit Dashboard
```bash
# Table view
PYTHONPATH=src python scripts/audit_dashboard.py

# Live tail
PYTHONPATH=src python scripts/audit_dashboard.py --tail

# Filter by agent
PYTHONPATH=src python scripts/audit_dashboard.py --agent openclaw-agent-001 --detail
```

### 5. Enable Auto-Polling
```bash
# In .env:
VYAPAAR_AUTO_POLL=true
VYAPAAR_POLL_INTERVAL=30
```

### 6. Enable Slack Notifications
```bash
# In .env:
SLACK_BOT_TOKEN=xoxb-your-token
SLACK_CHANNEL_ID=C0123456789
```

### 7. Get Metrics
Call the `get_metrics` MCP tool. The response includes both a JSON snapshot and raw Prometheus text format (`prometheus_text` field).

---

## 📊 MCP Tools (Complete List)

| # | Tool | Type | Description |
|:---|:---|:---|:---|
| 1 | `handle_razorpay_webhook` | Ingress | Process Razorpay webhook events |
| 2 | `poll_razorpay_payouts` | Ingress/Ops | Poll API for queued payouts |
| 3 | `check_vendor_reputation` | Reputation | Check URL via Google Safe Browsing |
| 4 | `get_agent_budget` | Read | Get agent's daily spend status |
| 5 | `get_audit_log` | Read | Retrieve audit trail with filters |
| 6 | `set_agent_policy` | Admin | Create/update agent spending policies |
| 7 | `health_check` | Ops | Check Redis, Postgres, Razorpay health |
| 8 | `get_metrics` | **NEW** | Prometheus-compatible governance metrics |

---

## 🧪 Test Coverage (79 tests)

| File | Tests | Focus |
|:---|:---|:---|
| `test_webhook.py` | 12 | Signature verification, parsing, idempotency keys |
| `test_budget.py` | 12 | Atomic budget, race conditions, reputation cache |
| `test_governance.py` | 8 | Full decision matrix (every SPEC §8 row) |
| `test_models.py` | 12 | Pydantic V2 model validation |
| `test_razorpay_bridge.py` | 8 | Go binary init, MCP connectivity, API calls |
| `test_slack.py` | 11 | **NEW** — Approval blocks, notification routing, error handling |
| `test_metrics.py` | 16 | **NEW** — Counters, Prometheus format, snapshots |

---

## 🎯 Remaining Work (Optional Polish)

| Item | Priority | Notes |
|:---|:---|:---|
| **Slack interactive buttons** | Low | Add Approve/Reject buttons to Slack messages (requires Slack app webhook) |
| **Grafana dashboard** | Low | Pre-built Grafana JSON for Prometheus metrics |
| **Rate limiting** | Low | Per-agent API rate limiting for tool calls |
| **Audit log export** | Low | CSV/JSON export endpoint for compliance |

---

**Artifacts Locations:**
*   Spec: `SPEC.md`
*   Source: `src/vyapaar_mcp/`
*   Tests: `tests/`
*   Scripts: `scripts/`
*   Go Vendor: `vendor/razorpay-mcp-server/`
*   Go Binary: `bin/razorpay-mcp-server`
*   Metrics: `src/vyapaar_mcp/observability/`
*   Slack: `src/vyapaar_mcp/egress/slack_notifier.py`
*   Dashboard: `scripts/audit_dashboard.py`
