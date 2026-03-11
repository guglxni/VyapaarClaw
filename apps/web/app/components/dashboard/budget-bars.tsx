"use client";

import type { Agent } from "../dashboard";

function formatINR(paise: number): string {
  const rupees = paise / 100;
  if (rupees >= 100000) return `₹${(rupees / 100000).toFixed(1)}L`;
  if (rupees >= 1000) return `₹${(rupees / 1000).toFixed(1)}K`;
  return `₹${rupees.toLocaleString("en-IN")}`;
}

function healthColor(health: string): string {
  switch (health) {
    case "red":
      return "#ef4444";
    case "yellow":
      return "#eab308";
    default:
      return "#22c55e";
  }
}

export function BudgetBars({ agents }: { agents: Agent[] }) {
  const sorted = [...agents].sort(
    (a, b) => b.utilisation_pct - a.utilisation_pct,
  );

  return (
    <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl p-5">
      <h2 className="text-xs uppercase tracking-widest text-[var(--color-text-dim)] mb-4">
        Budget Utilisation
      </h2>

      <div className="space-y-4">
        {sorted.map((agent) => (
          <div key={agent.agent_id} className="flex items-center gap-3">
            <div className="w-32 truncate text-sm text-[var(--color-text-muted)]">
              {agent.agent_id}
            </div>

            <div className="flex-1 h-6 bg-[#1e293b] rounded-md overflow-hidden relative">
              <div
                className="h-full rounded-md transition-all duration-700 ease-out"
                style={{
                  width: `${Math.min(agent.utilisation_pct, 100)}%`,
                  backgroundColor: healthColor(agent.budget_health),
                }}
              />
              <div className="absolute inset-0 flex items-center justify-end pr-2">
                <span className="text-[10px] font-medium text-white/80 drop-shadow">
                  {formatINR(agent.current_daily_spend_paise)} /{" "}
                  {formatINR(agent.daily_limit)}
                </span>
              </div>
            </div>

            <div
              className="w-12 text-right text-sm font-semibold tabular-nums"
              style={{ color: healthColor(agent.budget_health) }}
            >
              {agent.utilisation_pct}%
            </div>
          </div>
        ))}
      </div>

      {agents.length === 0 && (
        <p className="text-sm text-[var(--color-text-dim)] text-center py-8">
          No agents found. Connect the MCP server to see live data.
        </p>
      )}
    </div>
  );
}
