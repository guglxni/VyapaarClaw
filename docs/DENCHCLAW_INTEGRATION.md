# DenchClaw CRM Integration

VyapaarClaw syncs governance audit logs and vendor KYB records to [DenchClaw](https://github.com/DenchHQ/DenchClaw) — an OpenClaw-based local CRM with DuckDB object tables and a web UI at `http://localhost:3100`.

## Architecture

```
VyapaarClaw MCP Server
  ├── PostgreSQL (source of truth for audit logs)
  ├── DenchClawClient (HTTP → localhost:3100)
  │     ├── vyapaar_audit  — governance decisions
  │     └── vyapaar_vendor — vendor KYB / trust scores
  └── Web Dashboard (/api/v1/audit)
```

On each governance decision, `log_decision()` writes to PostgreSQL and (when enabled) auto-syncs to DenchClaw. Vendor screening via `screen_vendor_sanctions` also upserts vendor records.

## Setup

### 1. Install DenchClaw

```bash
npx denchclaw@latest
```

Opens at `http://localhost:3100`. Uses a separate OpenClaw gateway on port 19001 (`openclaw --profile dench`).

### 2. Configure VyapaarClaw

```bash
# .env
VYAPAAR_DENCHCLAW_ENABLED=true
VYAPAAR_DENCHCLAW_URL=http://localhost:3100
VYAPAAR_DENCHCLAW_SYNC_AUTO=true
```

Or run `npx vyapaarclaw` bootstrap — DenchClaw sync is enabled by default.

### 3. Start both services

```bash
# Terminal 1 — DenchClaw CRM
npx denchclaw start

# Terminal 2 — VyapaarClaw MCP
VYAPAAR_TRANSPORT=sse uv run vyapaarclaw
```

On startup, VyapaarClaw bootstraps `vyapaar_audit` and `vyapaar_vendor` object schemas in the DenchClaw workspace.

## MCP Tools

| Tool | Description |
|------|-------------|
| `get_denchclaw_status` | Health check + object counts |
| `sync_audit_to_denchclaw` | Bulk sync from PostgreSQL |
| `get_denchclaw_audit_log` | Read audit entries from CRM |

## CRM Object Schemas

Defined in `src/vyapaar_mcp/integrations/denchclaw_schema.py`:

**vyapaar_audit** — Payout ID, Agent ID, Amount, Decision, Reason Code, Vendor Name, Processing Ms

**vyapaar_vendor** — Vendor Name, GSTIN, Trust Score, Trust Level, Sanctions Status, Last Screened

## Troubleshooting

| Issue | Fix |
|-------|-----|
| DenchClaw not reachable | `npx denchclaw start` or `npx denchclaw update` |
| Schema missing | Call `get_denchclaw_status` — auto-bootstraps on MCP start |
| Stale data | `sync_audit_to_denchclaw(limit=100)` |
| Pairing required | `openclaw --profile dench devices approve --latest` |

## References

- [DenchClaw GitHub](https://github.com/DenchHQ/DenchClaw)
- [DenchClaw install docs](https://github.com/DenchHQ/DenchClaw#install)
