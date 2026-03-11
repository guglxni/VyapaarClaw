# Recommended OpenClaw Skills for VyapaarClaw

Skills from [awesome-openclaw-skills](https://github.com/VoltAgent/awesome-openclaw-skills) that complement VyapaarClaw's AI CFO capabilities.

Install via: `clawhub install <skill-slug>` or copy to `~/.openclaw/skills/`

---

## Security & Audit (High Priority)

| Skill | Why |
|-------|-----|
| **agent-audit-trail** | Tamper-evident, hash-chained audit logging. Complements VyapaarClaw's PostgreSQL audit with cryptographic integrity. |
| **agent-self-governance** | WAL (Write-Ahead Log), VBR (Verify Before Reporting) protocols. Strengthens autonomous CFO decision-making. |
| **arc-security-audit** | Comprehensive security audit for the full skill stack. Run periodically against VyapaarClaw's skill set. |
| **credential-manager** | Secure credential handling for API keys (Razorpay, Safe Browsing, Azure). |
| **domain-trust-check** | URL phishing/malware checks via Outtake Trust API. Supplements Google Safe Browsing for vendor verification. |

## Finance & Accounting (High Priority)

| Skill | Why |
|-------|-----|
| **expense-tracker-pro** | Natural language expense tracking. Could feed into VyapaarClaw's budget monitoring. |
| **finance-tracker** | Complete personal finance management. Useful for extending VyapaarClaw to track cash flow beyond agent budgets. |
| **tax-professional** | US tax advisor and deduction optimizer. Extend VyapaarClaw with tax compliance awareness. |
| **ynab** | YNAB budget integration. Connect agent budgets to real budgeting tools. |
| **plaid** | Plaid finance platform CLI. Bank account connectivity for cash flow verification. |

## Communication & Notifications (Medium Priority)

| Skill | Why |
|-------|-----|
| **agent-mail** | Email inbox for AI agents. Send compliance reports and alerts via email. |
| **bluesky** / **bird** | Social media integration. The CFO agent could post public transparency reports. |
| **gotify** | Push notifications when long-running tasks complete. Useful for budget alarm cron jobs. |

## Automation & Scheduling (Medium Priority)

| Skill | Why |
|-------|-----|
| **casual-cron** | Natural language cron job creation. Users could add custom financial monitoring schedules. |
| **n8n** | n8n workflow automation. Chain VyapaarClaw tools into complex financial workflows. |
| **agent-autopilot** | Self-driving agent workflow with heartbeat-driven task execution. Powers autonomous CFO operations. |

## Data & Analytics (Medium Priority)

| Skill | Why |
|-------|-----|
| **csv-pipeline** | CSV/JSON processing, transformation, and reporting. Export audit logs and financial data. |
| **daily-report** | Track progress, report metrics, manage memory. Daily financial reporting automation. |
| **duckdb-en** | DuckDB SQL analysis for financial data querying across audit logs. |

## Agent Coordination (Lower Priority)

| Skill | Why |
|-------|-----|
| **agent-team-orchestration** | Multi-agent teams with roles, task lifecycles, handoff protocols. Extends VyapaarClaw's delegation. |
| **arc-department-manager** | Manage teams of AI sub-agents in departments. Map to financial functions. |
| **agent-orchestration** | Meta-agent skill for orchestrating complex multi-step financial workflows. |

## PDF & Documents (Lower Priority)

| Skill | Why |
|-------|-----|
| **ai-pdf-builder** | Generate PDF compliance reports, invoices, and governance summaries. |
| **chain-of-density** | Summarize long audit trails into concise executive briefings. |

---

## Installation Example

```bash
# Install the most impactful skills
clawhub install agent-audit-trail
clawhub install agent-self-governance
clawhub install expense-tracker-pro
clawhub install casual-cron
clawhub install agent-autopilot
clawhub install csv-pipeline
```

These skills complement VyapaarClaw's 25 built-in MCP tools with broader automation,
deeper security, and richer financial integrations.
