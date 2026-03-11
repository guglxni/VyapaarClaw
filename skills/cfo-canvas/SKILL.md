---
name: vyapaarclaw-cfo-canvas
description: Canvas financial dashboard rendering for VyapaarClaw. Teaches the CFO agent to render live financial dashboards using OpenClaw's Canvas workspace with HTML/CSS/JS visualisations.
metadata: { "openclaw": { "inject": false, "emoji": "📊" } }
---

# VyapaarClaw CFO — Canvas Financial Dashboard

When running inside OpenClaw's macOS app, you can render a live financial
dashboard using Canvas. This gives the human operator a visual overview
of all governed agents, budgets, and governance decisions.

## When to Use Canvas

- Human asks to "show me the dashboard" or "visualise budgets"
- Morning brief delivery (render alongside the text summary)
- After generating a compliance report (visual summary)
- When investigating anomalies (trend charts help explain patterns)

## Data Collection

Before rendering, fetch all needed data using MCP tools:

```
1. list_agents()           → agent roster with budget health
2. get_spending_trends()   → per-agent daily spend series
3. generate_compliance_report() → decision stats
4. get_audit_log(limit=20) → recent decisions for the feed
```

## Dashboard Layout

The dashboard has 4 sections arranged in a 2x2 grid:

```
┌────────────────────┬────────────────────┐
│                    │                    │
│  Budget Bars       │  Spending Trends   │
│  (per agent)       │  (sparklines)      │
│                    │                    │
├────────────────────┼────────────────────┤
│                    │                    │
│  Decision Feed     │  Risk Heatmap      │
│  (recent log)      │  (agent scores)    │
│                    │                    │
└────────────────────┴────────────────────┘
```

## HTML Template

Use this template structure when rendering to Canvas. Replace the
placeholder data with actual values from the MCP tool responses.

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>VyapaarClaw Financial Dashboard</title>
<style>
  :root {
    --bg: #0a0f1a;
    --card: #111827;
    --border: #1e293b;
    --green: #22c55e;
    --yellow: #eab308;
    --red: #ef4444;
    --text: #e2e8f0;
    --muted: #94a3b8;
    --accent: #c9a227;
  }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    font-family: 'SF Pro Display', -apple-system, sans-serif;
    background: var(--bg);
    color: var(--text);
    padding: 24px;
  }
  h1 {
    font-size: 1.5rem;
    color: var(--accent);
    margin-bottom: 20px;
    letter-spacing: -0.02em;
  }
  .grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
  }
  .card {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 20px;
  }
  .card h2 {
    font-size: 0.85rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--muted);
    margin-bottom: 16px;
  }

  /* Budget Bars */
  .budget-row {
    display: flex;
    align-items: center;
    margin-bottom: 12px;
    gap: 12px;
  }
  .budget-label {
    width: 120px;
    font-size: 0.8rem;
    color: var(--muted);
    text-overflow: ellipsis;
    overflow: hidden;
    white-space: nowrap;
  }
  .budget-bar {
    flex: 1;
    height: 24px;
    background: #1e293b;
    border-radius: 6px;
    overflow: hidden;
    position: relative;
  }
  .budget-fill {
    height: 100%;
    border-radius: 6px;
    transition: width 0.6s ease;
  }
  .budget-pct {
    width: 48px;
    text-align: right;
    font-size: 0.8rem;
    font-weight: 600;
  }

  /* Sparklines */
  .sparkline-row {
    display: flex;
    align-items: center;
    margin-bottom: 10px;
    gap: 12px;
  }
  .sparkline-label {
    width: 120px;
    font-size: 0.8rem;
    color: var(--muted);
  }
  .sparkline svg {
    width: 200px;
    height: 30px;
  }

  /* Decision Feed */
  .decision-row {
    display: flex;
    justify-content: space-between;
    padding: 8px 0;
    border-bottom: 1px solid var(--border);
    font-size: 0.8rem;
  }
  .decision-row:last-child { border-bottom: none; }
  .badge {
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 0.7rem;
    font-weight: 600;
  }
  .badge-approved { background: #052e16; color: var(--green); }
  .badge-rejected { background: #450a0a; color: var(--red); }
  .badge-held { background: #422006; color: var(--yellow); }

  /* Risk Heatmap */
  .heatmap-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(80px, 1fr));
    gap: 8px;
  }
  .heatmap-cell {
    text-align: center;
    padding: 12px 8px;
    border-radius: 8px;
    font-size: 0.75rem;
  }
  .risk-low { background: #052e16; color: var(--green); }
  .risk-medium { background: #422006; color: var(--yellow); }
  .risk-high { background: #450a0a; color: var(--red); }

  .timestamp {
    text-align: right;
    font-size: 0.7rem;
    color: var(--muted);
    margin-top: 16px;
  }
</style>
</head>
<body>
  <h1>VyapaarClaw Financial Dashboard</h1>

  <div class="grid">
    <!-- Budget Utilisation -->
    <div class="card">
      <h2>Budget Utilisation</h2>
      <div id="budget-bars">
        <!-- Rendered dynamically -->
      </div>
    </div>

    <!-- Spending Trends -->
    <div class="card">
      <h2>Spending Trends (7 days)</h2>
      <div id="sparklines">
        <!-- Rendered dynamically -->
      </div>
    </div>

    <!-- Recent Decisions -->
    <div class="card">
      <h2>Recent Governance Decisions</h2>
      <div id="decisions">
        <!-- Rendered dynamically -->
      </div>
    </div>

    <!-- Risk Heatmap -->
    <div class="card">
      <h2>Agent Risk Heatmap</h2>
      <div id="heatmap" class="heatmap-grid">
        <!-- Rendered dynamically -->
      </div>
    </div>
  </div>

  <div class="timestamp">
    Last updated: <span id="ts"></span>
  </div>

  <script>
    // DATA: Replace these with actual MCP tool responses
    const agents = [
      // From list_agents():
      // { agent_id, daily_limit, current_daily_spend_paise, utilisation_pct, budget_health }
    ];
    const trends = {
      // From get_spending_trends() per agent:
      // "agent-id": [0, 1200, 3400, ...]
    };
    const decisions = [
      // From get_audit_log():
      // { agent_id, amount, decision, reason_code, created_at }
    ];

    // Render budget bars
    const budgetEl = document.getElementById('budget-bars');
    agents.forEach(a => {
      const color = a.budget_health === 'red' ? 'var(--red)'
                  : a.budget_health === 'yellow' ? 'var(--yellow)'
                  : 'var(--green)';
      budgetEl.innerHTML += `
        <div class="budget-row">
          <span class="budget-label">${a.agent_id}</span>
          <div class="budget-bar">
            <div class="budget-fill" style="width:${a.utilisation_pct}%;background:${color}"></div>
          </div>
          <span class="budget-pct" style="color:${color}">${a.utilisation_pct}%</span>
        </div>`;
    });

    // Render sparklines
    const sparkEl = document.getElementById('sparklines');
    Object.entries(trends).forEach(([id, data]) => {
      const max = Math.max(...data, 1);
      const points = data.map((v, i) =>
        `${(i / (data.length - 1)) * 200},${30 - (v / max) * 28}`
      ).join(' ');
      sparkEl.innerHTML += `
        <div class="sparkline-row">
          <span class="sparkline-label">${id}</span>
          <div class="sparkline">
            <svg viewBox="0 0 200 30">
              <polyline points="${points}" fill="none" stroke="var(--accent)" stroke-width="1.5"/>
            </svg>
          </div>
        </div>`;
    });

    // Render decisions
    const decEl = document.getElementById('decisions');
    decisions.slice(0, 10).forEach(d => {
      const cls = d.decision === 'APPROVED' ? 'badge-approved'
                : d.decision === 'REJECTED' ? 'badge-rejected'
                : 'badge-held';
      const amt = (d.amount / 100).toLocaleString('en-IN', {style:'currency', currency:'INR'});
      decEl.innerHTML += `
        <div class="decision-row">
          <span>${d.agent_id}</span>
          <span>${amt}</span>
          <span class="badge ${cls}">${d.decision}</span>
        </div>`;
    });

    // Render heatmap
    const heatEl = document.getElementById('heatmap');
    agents.forEach(a => {
      const cls = a.budget_health === 'red' ? 'risk-high'
                : a.budget_health === 'yellow' ? 'risk-medium'
                : 'risk-low';
      heatEl.innerHTML += `
        <div class="heatmap-cell ${cls}">
          ${a.agent_id}<br>
          <strong>${a.utilisation_pct}%</strong>
        </div>`;
    });

    document.getElementById('ts').textContent = new Date().toLocaleString('en-IN', {timeZone: 'Asia/Kolkata'});
  </script>
</body>
</html>
```

## Rendering Instructions

1. Collect data from all 4 MCP tool calls
2. Replace the placeholder arrays in the `<script>` section with actual data
3. Render to Canvas using the canvas tool with a descriptive title
4. Use the returned `id` to update the same canvas on subsequent refreshes

**Colour mapping**:
- Green (#22c55e): healthy, < 50% utilisation
- Yellow (#eab308): caution, 50-80% utilisation
- Red (#ef4444): critical, > 80% utilisation

**Formatting rules**:
- Always show amounts in INR with Indian comma notation
- Agent IDs should be truncated if longer than 15 characters
- Sparklines cover the last 7 days by default
- Decision feed shows the 10 most recent entries

## Updating the Dashboard

When the user asks to refresh or update the dashboard:
1. Fetch fresh data from MCP tools
2. Re-render the Canvas using the same `id` (this replaces the content)
3. The timestamp at the bottom updates automatically

Do not cache data between renders — always fetch fresh numbers.
