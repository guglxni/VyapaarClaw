# DenchClaw Integration — Code Generation Plan

**AIDLC Unit:** denchclaw-integration  
**Status:** Complete  
**Reference:** [DenchHQ/DenchClaw](https://github.com/DenchHQ/DenchClaw)

## Objective

Replace aspirational DenchClaw mentions with a real CRM sync integration for governance audit logs and vendor KYB records, while ensuring LLM configuration remains provider-agnostic via LiteLLM.

## Deliverables

### Backend

- [x] `integrations/denchclaw_schema.py` — `vyapaar_audit`, `vyapaar_vendor` object defs
- [x] `integrations/denchclaw.py` — `DenchClawClient` (bootstrap, sync, read)
- [x] `audit/logger.py` — auto-sync hook via `set_denchclaw_client()`
- [x] `config.py` — `denchclaw_url`, `denchclaw_enabled`, `denchclaw_sync_auto`
- [x] `server.py` — startup init, vendor sync on `screen_vendor_sanctions`
- [x] MCP tools: `get_denchclaw_status`, `sync_audit_to_denchclaw`, `get_denchclaw_audit_log`
- [x] HTTP `/api/v1/audit` includes `processing_ms`

### Frontend

- [x] MCP HTTP `/api/v1/audit` — live audit data for dashboard
- [x] `.env.example` — LiteLLM + DenchClaw + Exa env vars

### Bootstrap & Templates

- [x] `src/cli/bootstrap.ts` — LLM + DenchClaw prompts
- [x] `templates/openclaw.json` — env-driven model config
- [x] `templates/AGENTS.md` — LiteLLM + DenchClaw references
- [x] Skills updated for delegation model env var

### LLM Agnostic

- [x] No hardcoded provider defaults in `VyapaarConfig`
- [x] Legacy Azure auto-migration preserved
- [x] `docs/LLM_CONFIGURATION.md`

### Tests & Docs

- [x] `tests/test_denchclaw.py`
- [x] `tests/test_smoke.py` updated for LLM-agnostic defaults
- [x] `docs/DENCHCLAW_INTEGRATION.md`
- [x] README updated

## Verification

```bash
uv run pytest tests/test_denchclaw.py tests/test_smoke.py -q
VYAPAAR_TRANSPORT=sse uv run vyapaarclaw  # check DenchClaw log line on startup
```
