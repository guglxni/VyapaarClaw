"use client";

import type { Agent } from "../dashboard";

function formatINR(paise: number): string {
  return `₹${(paise / 100).toLocaleString("en-IN")}`;
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

export function SpendingChart({ agents }: { agents: Agent[] }) {
  const totalBudget = agents.reduce((s, a) => s + a.daily_limit, 0);
  const totalSpend = agents.reduce(
    (s, a) => s + a.current_daily_spend_paise,
    0,
  );
  const overallUtil = totalBudget > 0 ? (totalSpend / totalBudget) * 100 : 0;

  return (
    <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl p-5">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xs uppercase tracking-widest text-[var(--color-text-dim)]">
          Agent Risk Heatmap
        </h2>
        <div className="text-xs text-[var(--color-text-muted)]">
          Overall utilisation:{" "}
          <span className="font-semibold text-[var(--color-text)]">
            {overallUtil.toFixed(1)}%
          </span>
          &nbsp;&middot;&nbsp;{formatINR(totalSpend)} / {formatINR(totalBudget)}
        </div>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3">
        {agents.map((agent) => (
          <div
            key={agent.agent_id}
            className="rounded-xl p-4 text-center transition-transform hover:scale-105"
            style={{
              backgroundColor:
                agent.budget_health === "red"
                  ? "#450a0a"
                  : agent.budget_health === "yellow"
                    ? "#422006"
                    : "#052e16",
            }}
          >
            <div
              className="text-xs truncate mb-1"
              style={{ color: healthColor(agent.budget_health) }}
            >
              {agent.agent_id}
            </div>
            <div
              className="text-2xl font-bold tabular-nums"
              style={{ color: healthColor(agent.budget_health) }}
            >
              {agent.utilisation_pct}%
            </div>
            <div className="text-[10px] text-[var(--color-text-dim)] mt-1">
              {formatINR(agent.current_daily_spend_paise)}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
