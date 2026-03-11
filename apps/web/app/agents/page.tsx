"use client";

import { AppShell } from "../components/shell";
import {
  Users,
  Shield,
  AlertTriangle,
  ChevronRight,
  TrendingUp,
} from "lucide-react";

type Agent = {
  agent_id: string;
  daily_limit: number;
  per_txn_limit: number | null;
  require_approval_above: number | null;
  current_spend: number;
  utilisation_pct: number;
  health: "green" | "yellow" | "red";
  tier: number;
  total_txns: number;
  blocked_domains: string[];
};

const DEMO_AGENTS: Agent[] = [
  {
    agent_id: "procurement-bot",
    daily_limit: 500000,
    per_txn_limit: 100000,
    require_approval_above: 50000,
    current_spend: 320000,
    utilisation_pct: 64,
    health: "yellow",
    tier: 2,
    total_txns: 156,
    blocked_domains: ["evil.com", "scam.org"],
  },
  {
    agent_id: "payroll-agent",
    daily_limit: 2500000,
    per_txn_limit: 500000,
    require_approval_above: 250000,
    current_spend: 1800000,
    utilisation_pct: 72,
    health: "yellow",
    tier: 3,
    total_txns: 89,
    blocked_domains: [],
  },
  {
    agent_id: "marketing-bot",
    daily_limit: 100000,
    per_txn_limit: 25000,
    require_approval_above: 10000,
    current_spend: 15000,
    utilisation_pct: 15,
    health: "green",
    tier: 1,
    total_txns: 24,
    blocked_domains: ["malware.org"],
  },
  {
    agent_id: "infra-agent",
    daily_limit: 1000000,
    per_txn_limit: 200000,
    require_approval_above: 100000,
    current_spend: 890000,
    utilisation_pct: 89,
    health: "red",
    tier: 2,
    total_txns: 203,
    blocked_domains: [],
  },
];

const TIER_LABELS: Record<number, { label: string; color: string }> = {
  1: { label: "New", color: "#94a3b8" },
  2: { label: "Established", color: "#3b82f6" },
  3: { label: "Trusted", color: "#22c55e" },
  4: { label: "Autonomous", color: "#c9a227" },
};

function formatINR(paise: number): string {
  const r = paise / 100;
  if (r >= 100000) return `₹${(r / 100000).toFixed(1)}L`;
  if (r >= 1000) return `₹${(r / 1000).toFixed(1)}K`;
  return `₹${r.toLocaleString("en-IN")}`;
}

function healthColor(h: string): string {
  return h === "red" ? "#ef4444" : h === "yellow" ? "#eab308" : "#22c55e";
}

export default function AgentsPage() {
  return (
    <AppShell>
      <div className="p-6 max-w-[1200px] space-y-6">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Agent Policies</h1>
          <p className="text-sm text-[var(--color-text-muted)] mt-0.5">
            {DEMO_AGENTS.length} agents with active spending policies
          </p>
        </div>

        <div className="space-y-3">
          {DEMO_AGENTS.map((agent) => {
            const tier = TIER_LABELS[agent.tier] ?? TIER_LABELS[1];
            return (
              <div
                key={agent.agent_id}
                className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl p-5 hover:border-[var(--color-accent)]/30 transition-colors"
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <div
                      className="w-2 h-2 rounded-full flex-shrink-0 mt-1.5"
                      style={{ backgroundColor: healthColor(agent.health) }}
                    />
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-sm">
                          {agent.agent_id}
                        </span>
                        <span
                          className="text-[10px] px-1.5 py-0.5 rounded font-medium"
                          style={{
                            backgroundColor: `${tier.color}15`,
                            color: tier.color,
                          }}
                        >
                          Tier {agent.tier}: {tier.label}
                        </span>
                      </div>
                      <div className="text-[11px] text-[var(--color-text-dim)] mt-0.5">
                        {agent.total_txns} total transactions
                        {agent.blocked_domains.length > 0 &&
                          ` · ${agent.blocked_domains.length} blocked domains`}
                      </div>
                    </div>
                  </div>

                  <div className="text-right">
                    <div
                      className="text-lg font-semibold tabular-nums"
                      style={{ color: healthColor(agent.health) }}
                    >
                      {agent.utilisation_pct}%
                    </div>
                    <div className="text-[10px] text-[var(--color-text-dim)]">
                      utilisation
                    </div>
                  </div>
                </div>

                {/* Policy details */}
                <div className="grid grid-cols-4 gap-4 mt-4 pt-3 border-t border-[var(--color-border-subtle)]">
                  <div>
                    <div className="text-[10px] text-[var(--color-text-dim)] uppercase tracking-wider">
                      Daily Limit
                    </div>
                    <div className="text-sm font-medium mt-0.5">
                      {formatINR(agent.daily_limit)}
                    </div>
                  </div>
                  <div>
                    <div className="text-[10px] text-[var(--color-text-dim)] uppercase tracking-wider">
                      Per-Txn Limit
                    </div>
                    <div className="text-sm font-medium mt-0.5">
                      {agent.per_txn_limit ? formatINR(agent.per_txn_limit) : "—"}
                    </div>
                  </div>
                  <div>
                    <div className="text-[10px] text-[var(--color-text-dim)] uppercase tracking-wider">
                      Approval Above
                    </div>
                    <div className="text-sm font-medium mt-0.5">
                      {agent.require_approval_above
                        ? formatINR(agent.require_approval_above)
                        : "—"}
                    </div>
                  </div>
                  <div>
                    <div className="text-[10px] text-[var(--color-text-dim)] uppercase tracking-wider">
                      Current Spend
                    </div>
                    <div className="text-sm font-medium mt-0.5">
                      {formatINR(agent.current_spend)} /{" "}
                      {formatINR(agent.daily_limit)}
                    </div>
                  </div>
                </div>

                {/* Budget bar */}
                <div className="mt-3 h-2 bg-[#1e293b] rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all duration-700"
                    style={{
                      width: `${Math.min(agent.utilisation_pct, 100)}%`,
                      backgroundColor: healthColor(agent.health),
                    }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </AppShell>
  );
}
