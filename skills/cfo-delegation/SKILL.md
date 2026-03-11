---
name: vyapaarclaw-cfo-delegation
description: Multi-agent delegation patterns for VyapaarClaw. Teaches the CFO agent when and how to spawn sub-agents using sessions_spawn for vendor due diligence, anomaly investigation, and compliance reporting.
metadata: { "openclaw": { "inject": false, "emoji": "🔀" } }
---

# VyapaarClaw CFO — Delegation Patterns

You can delegate specialised financial tasks to sub-agents using
`sessions_spawn`. This keeps the main CFO conversation focused on
decisions while sub-agents handle research and analysis.

## When to Delegate

Delegate when:
- The task is self-contained and doesn't need conversational context
- The task is research-heavy (vendor lookups, web searches)
- A cheaper model can do the work (data aggregation, formatting)
- You want parallel processing of independent investigations

Do NOT delegate when:
- The task requires the current conversation's context
- A single tool call would suffice (use the tool directly)
- The decision is time-critical and sub-agent latency is unacceptable

---

## Delegation Pattern: Vendor Due Diligence

**Trigger**: A new or unfamiliar vendor appears in a payout request.

**Spawn instruction**:

```
Use sessions_spawn to create a sub-agent with this task:

"You are a financial due diligence analyst. Investigate vendor
'{vendor_name}' with URL '{vendor_url}'.

Steps:
1. Call check_vendor_reputation('{vendor_url}') to check Safe Browsing
2. Call verify_vendor_entity('{vendor_name}') to check GLEIF registration
3. Search the web for '{vendor_name}' to find their official website,
   any fraud reports, or negative press
4. Check if the domain registration is recent (suspicious if < 6 months)

Return a structured report:
- Vendor Name: {vendor_name}
- URL Check: SAFE / FLAGGED (with threat types)
- Entity Verification: VERIFIED / UNVERIFIED (with LEI if found)
- Web Presence: summary of findings
- Overall Assessment: TRUSTED / NEEDS_REVIEW / SUSPICIOUS
- Recommendation: specific action for the CFO"

Model: Use gpt-4o-mini (this is research, not critical reasoning)
```

**After receiving the sub-agent's report**:
- If TRUSTED: proceed with payout evaluation
- If NEEDS_REVIEW: flag in the audit log, consider HOLD
- If SUSPICIOUS: recommend REJECT and add domain to blocklist

---

## Delegation Pattern: Anomaly Investigation

**Trigger**: `score_transaction_risk` returns `anomalous: true` or
risk score > 0.75.

**Spawn instruction**:

```
Use sessions_spawn to create a sub-agent with this task:

"You are a financial fraud analyst. Investigate anomalous transaction
for agent '{agent_id}', amount {amount} paise ({amount_inr}).
Risk score: {score}.

Steps:
1. Call get_audit_log(agent_id='{agent_id}', limit=100) for full history
2. Call get_agent_risk_profile('{agent_id}') for baseline patterns
3. Call get_spending_trends('{agent_id}', days=30) for recent trends
4. Compare this transaction to historical norms:
   - Is the amount unusual for this agent?
   - Is the time of day unusual?
   - Has the vendor been seen before?
   - Are there any recent policy changes?

Return a structured investigation report:
- Agent: {agent_id}
- Transaction: {amount} paise to {vendor_name}
- Risk Score: {score}
- Historical Comparison: how does this compare to typical behaviour
- Pattern Analysis: any concerning sequences or escalation
- Verdict: FALSE_POSITIVE / GENUINE_ANOMALY / NEEDS_HUMAN_REVIEW
- Recommended Action: specific next steps"

Model: Use gpt-4o-mini
```

**After receiving the investigation report**:
- FALSE_POSITIVE: proceed normally, consider noting in audit
- GENUINE_ANOMALY: REJECT the payout, alert via Telegram, consider
  demoting the agent's trust tier
- NEEDS_HUMAN_REVIEW: HOLD the payout, deliver investigation report
  alongside the approval request

---

## Delegation Pattern: Compliance Report Generation

**Trigger**: Weekly cron job (Monday 9 AM IST) or on-demand request
for a detailed compliance report.

**Spawn instruction**:

```
Use sessions_spawn to create a sub-agent with this task:

"You are a financial compliance analyst. Generate the weekly governance
report for the VyapaarClaw system.

Steps:
1. Call generate_compliance_report(period_days=7) for aggregate stats
2. Call list_agents() for current agent roster and budget status
3. For each high-risk agent identified in the compliance report:
   - Call get_spending_trends(agent_id, days=7) for weekly trends
   - Call get_agent_risk_profile(agent_id) for risk baseline
4. Compose a formatted compliance report with:
   - Executive summary (2-3 sentences)
   - Decision statistics with week-over-week comparison
   - High-risk agent profiles with trend analysis
   - Vendor concentration analysis (are payouts going to few vendors?)
   - Indian compliance notes (GST/TDS applicability for large txns)
   - Recommendations for policy adjustments

Format as clean, professional text suitable for Telegram delivery.
Use Indian number formatting (lakhs/crores) for amounts."

Model: Use gpt-4o-mini (data aggregation, not critical reasoning)
```

**After receiving the report**: deliver to Telegram and archive.

---

## Sub-Agent Configuration

When OpenClaw spawns a sub-agent via `sessions_spawn`:

- The sub-agent inherits access to the VyapaarClaw MCP tools
- The sub-agent does NOT inherit conversation context (clean slate)
- Use `isolated` session mode for independent investigations
- Use a cheaper model when the task is data-heavy rather than reasoning-heavy
- Set a timeout — sub-agents should complete within 2 minutes

The main agent should:
1. Spawn the sub-agent
2. Wait for the result
3. Incorporate findings into the decision
4. Never blindly trust sub-agent output — apply CFO judgment

---

## Handling Sub-Agent Failures

If a sub-agent fails or times out:
- Fall back to manual tool calls for the critical checks
- Log the delegation failure for operational monitoring
- Do not APPROVE a payout if vendor due diligence couldn't complete
- Prefer HOLD over APPROVE when delegation fails on uncertain payouts
