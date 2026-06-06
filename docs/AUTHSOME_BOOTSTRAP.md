# Authsome Credential Broker — Bootstrap Guide

VyapaarClaw manages 10+ API keys (Razorpay, Safe Browsing, Exa, Slack, GSP, HyperAPI).
[Authsome](https://github.com/agentrhq/authsome) (agentrhq/authsome, MIT) injects credentials at a
proxy boundary so AI agents never see raw tokens.

> **Note:** This is `agentrhq/authsome` (credential broker), NOT `xraph/authsome` (Go web auth).

## Install

```bash
pip install authsome
# or
uv pip install authsome
```

## One-Time Provider Setup

```bash
authsome login github
authsome provider add razorpay --env VYAPAAR_RAZORPAY_KEY_ID,VYAPAAR_RAZORPAY_KEY_SECRET
authsome provider add exa --env VYAPAAR_EXA_API_KEY
authsome provider add safe-browsing --env VYAPAAR_GOOGLE_SAFE_BROWSING_KEY
```

## Runtime (Production)

```bash
# Agents run behind Authsome — secrets injected, never in agent env
authsome run -- vyapaarclaw start

# SSE transport for web dashboard + MCP
VYAPAAR_TRANSPORT=sse authsome run -- vyapaarclaw start
```

## Synergy with Dual-LLM Quarantine

| Layer | Protects against |
|-------|------------------|
| Dual-LLM quarantine | Prompt injection, context taint |
| Authsome | Credential exfiltration from agent process |

## Environment Variables Managed

| Provider | Env vars |
|----------|----------|
| Razorpay | `VYAPAAR_RAZORPAY_KEY_ID`, `VYAPAAR_RAZORPAY_KEY_SECRET` |
| Exa | `VYAPAAR_EXA_API_KEY` |
| Safe Browsing | `VYAPAAR_GOOGLE_SAFE_BROWSING_KEY` |
| GSP GST | `VYAPAAR_GSP_API_KEY` |
| HyperAPI | `VYAPAAR_HYPERAPI_API_KEY` |
| Slack | `VYAPAAR_SLACK_BOT_TOKEN` |

## Docker Compose Pattern

```yaml
services:
  vyapaarclaw:
    command: authsome run -- vyapaarclaw start
    environment:
      VYAPAAR_TRANSPORT: sse
      VYAPAAR_POSTGRES_DSN: postgresql://...
      VYAPAAR_REDIS_URL: redis://redis:6379/0
    # Do NOT pass API keys here — Authsome injects them
```
