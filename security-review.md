# Security Review: VyapaarClaw

## Summary
- Critical: 0 | High: 1 | Medium: 2 | Low: 1 | False Positives: 17

## Findings

### [HIGH] SQL Injection risk via manual string escaping
**Severity:** High
**Category:** OWASP A03 Injection
**File:** `src/vyapaar_mcp/integrations/denchclaw.py:93`
**CWE:** CWE-89
**Description:** DenchClaw CRM integration builds SQL queries using manual string escaping (`_sql_escape(object_name)` which replaces `'` with `''`). While this provides basic protection, it is an anti-pattern and can be bypassed in certain database contexts. Since `object_name` and `description` are concatenated directly into the SQL string via `f"{_sql_escape(object_name)}"`, it runs the risk of SQL injection if the downstream DuckDB/Postgres evaluates the string differently.
**Recommendation:** If the downstream DenchClaw HTTP API supports parameterized queries, refactor to use them. If it only accepts raw SQL strings, consider a more robust escaping library or ensure that all inputs passed to `_sql_escape` are strictly validated against an allowed character set (e.g. `^[a-zA-Z0-9_]+$`).

### [MEDIUM] Unauthenticated MCP Server Network Binding
**Severity:** Medium
**Category:** OWASP A05 Security Misconfiguration
**File:** `src/vyapaar_mcp/server.py` and `pyproject.toml`
**Description:** The FastMCP server uses Starlette/Uvicorn to start the SSE transport bound to `host="0.0.0.0"` port 8000 by default (intentional for containers per `pyproject.toml` ignores). However, if this is deployed on a public-facing container/server without an explicit reverse proxy, firewall, or API Gateway restricting access, the MCP server is exposed to the internet with no authentication. 
**Recommendation:** Document prominently that a reverse proxy with authentication is strictly required for `0.0.0.0` bindings, or add a built-in Bearer token authentication layer for the SSE transport.

### [MEDIUM] Unauthenticated MCP HTTP API Endpoints
**Severity:** Medium
**Category:** OWASP A01 Broken Access Control
**File:** `src/vyapaar_mcp/handlers/http.py` (`/api/v1/dashboard`, `/api/v1/audit`, `/api/v1/agents`)
**Description:** MCP HTTP endpoints expose dashboard statistics, agent configurations, and audit logs without authentication. The static `vyapaar-ui/` dashboard proxies these endpoints. Anyone with network access can read sensitive financial governance data.
**Recommendation:** Place a reverse proxy with Bearer token or mTLS in front of the MCP server. Bind to `127.0.0.1` in development. Never expose port 8000 publicly without an auth layer.

### [LOW] Unpinned GitHub Action Dependencies
**Severity:** Low
**Category:** OWASP A03 Software Supply Chain Failures
**File:** `.github/workflows/ci.yml` and `.github/workflows/release.yml`
**Description:** GitHub Actions use mutable version tags (e.g., `uses: actions/checkout@v6`) instead of immutable Git SHAs. If an attacker compromises a GitHub Action repository and pushes a malicious update to a major version tag, the CI pipeline will automatically execute the compromised code.
**Recommendation:** Pin all GitHub Actions to their specific commit SHAs and use tools like Dependabot to automatically update them.

---

## False Positives (Filtered from Automated Scan)
- **SQL Injection (14 instances):** Automated scanners flagged `src/vyapaar_mcp/db/postgres.py` for f-string SQL construction. Manual review confirmed that only PostgreSQL positional placeholders (`$1`, `$2`) and trusted string literals (`WHERE`, `AND`) are interpolated. Actual user data is passed safely via `*params`.
- **Sensitive Data in Logs (3 instances):** Flagged `mask_secrets(str(e))` but the function properly masks secrets before logging them.

## Passed Checks
- `dangerouslySetInnerHTML` is not unsafely used in the React frontend.
- No exposed hardcoded secrets in the `src/`, `apps/`, or `tests/` folders (checked against known credential/token patterns).
- Passwords for local development services in Docker Compose are appropriately scoped to development.
- Secure environment configuration defaults provided in `.env.example`.