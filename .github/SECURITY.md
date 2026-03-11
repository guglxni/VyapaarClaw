# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| latest  | :white_check_mark: |

## Reporting a Vulnerability

If you discover a security vulnerability in VyapaarClaw, **please do not open a public issue.**

Instead, report it responsibly via one of these methods:

1. **GitHub Security Advisories** — [Report a vulnerability](../../security/advisories/new) (preferred)
2. **Email** — Send details to the maintainer listed in `pyproject.toml`

### What to include

- A description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

### Response timeline

- **Acknowledgement**: Within 48 hours
- **Initial assessment**: Within 1 week
- **Fix or mitigation**: Aim for 30 days for critical issues

### Scope

The following are in scope:
- VyapaarClaw MCP server (`src/vyapaar_mcp/`)
- Web dashboard (`apps/web/`)
- CLI tooling (`src/cli/`)
- Docker/deployment configurations (`deploy/`, `docker-compose.yml`)
- Webhook and API security
- Secret handling and credential management

### Out of scope

- Third-party dependencies (report upstream)
- Vulnerabilities in Razorpay/Azure/Slack/Telegram APIs themselves
- Social engineering attacks
- Denial of service via legitimate rate-limited endpoints

## Security Practices

VyapaarClaw implements the following security measures:

- **HMAC-SHA256** webhook signature verification
- **Atomic Redis** operations to prevent race conditions
- **Parameterized SQL** queries (no string concatenation)
- **Dual-LLM quarantine** pattern for untrusted data
- **Secret masking** in all log output
- **Rate limiting** via sliding-window Redis scripts
- **Input validation** on all webhook payloads
- **Security headers** on the web dashboard (HSTS, X-Frame-Options, CSP)

## Dependencies

We use Dependabot to automatically monitor and update dependencies. Security advisories trigger immediate patch reviews.
