# VyapaarClaw Architecture

![VyapaarClaw Architecture Diagram](./architecture.png)

## Overview

VyapaarClaw is an enterprise-grade Model Context Protocol (MCP) server written in Python, functioning as an "AI CFO" for financial governance mapping directly onto established OpenClaw frameworks. It is designed to evaluate, audit, and securely orchestrate corporate payouts, ensuring tight human-in-the-loop and LLM-driven policy alignment before funds move via platforms like Razorpay.

## Core Components

1. **MCP Server Engine**: 
   - A standard MCP JSON-RPC Server interface enabling connection to LLM clients (like Anthropic, Ollama, MLX).
   - Serves internal Python actions and bridges externally to Go-based binaries (for heavy lifting / Razorpay SDKs).

2. **AI CFO & Governance LLMs**: 
   - Uses context windows effectively to evaluate `HELD`, `APPROVED` or `REJECTED` states on payouts.
   - Leverages localized MLX Mistral schemas, enforcing compliance safely off-grid.

3. **Data Tier (Postgres & Redis)**:
   - **PostgreSQL (`asyncpg`)**: Immutable event logging, storing payout decisions, agent logs, and audit trails.
   - **Redis (`hiredis`)**: Manages rate-limits, rapid event caching, and caching anomaly detection computations.

4. **User Interfaces**:
   - **Terminal UI (`Textual`)**: Deep system-level debugging, live agent metric feeds. 
   - **Web UI (`Next.js / React`)**: Human-facing CFO dashboard featuring TanStack DataTables and visual anomaly graphs.

5. **Exposed Action Providers (Egress)**:
   - **Razorpay**: Direct payout disbursement and vendor link creation securely integrated.
   - **Slack**: Notification channels and interactive callback actions for human-in-the-loop override approvals.
