"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Shield,
  TrendingUp,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Clock,
  RefreshCw,
  Users,
  Activity,
} from "lucide-react";
import { BudgetBars } from "./dashboard/budget-bars";
import { DecisionFeed } from "./dashboard/decision-feed";
import { StatsCards } from "./dashboard/stats-cards";
import { SpendingChart } from "./dashboard/spending-chart";

export type Agent = {
  agent_id: string;
  daily_limit: number;
  current_daily_spend_paise: number;
  utilisation_pct: number;
  budget_health: "green" | "yellow" | "red";
  per_txn_limit: number | null;
  require_approval_above: number | null;
};

export type AuditEntry = {
  payout_id: string;
  agent_id: string;
  amount: number;
  decision: "APPROVED" | "REJECTED" | "HELD";
  reason_code: string;
  reason_detail: string;
  vendor_name: string | null;
  created_at: string;
};

export type ComplianceStats = {
  total_decisions: number;
  decisions: Record<string, { count: number; total_amount: number }>;
  top_rejection_reasons: Array<{ reason: string; count: number }>;
  high_risk_agents: Array<{
    agent_id: string;
    rejection_rate_pct: number;
    total_decisions: number;
  }>;
};

export type DashboardData = {
  agents: Agent[];
  compliance: ComplianceStats | null;
  recentDecisions: AuditEntry[];
  mcpConnected: boolean;
};

const DEMO_AGENTS: Agent[] = [
  {
    agent_id: "procurement-bot",
    daily_limit: 500000,
    current_daily_spend_paise: 320000,
    utilisation_pct: 64,
    budget_health: "yellow",
    per_txn_limit: 100000,
    require_approval_above: 50000,
  },
  {
    agent_id: "payroll-agent",
    daily_limit: 2500000,
    current_daily_spend_paise: 1800000,
    utilisation_pct: 72,
    budget_health: "yellow",
    per_txn_limit: 500000,
    require_approval_above: 250000,
  },
  {
    agent_id: "marketing-bot",
    daily_limit: 100000,
    current_daily_spend_paise: 15000,
    utilisation_pct: 15,
    budget_health: "green",
    per_txn_limit: 25000,
    require_approval_above: 10000,
  },
  {
    agent_id: "infra-agent",
    daily_limit: 1000000,
    current_daily_spend_paise: 890000,
    utilisation_pct: 89,
    budget_health: "red",
    per_txn_limit: 200000,
    require_approval_above: 100000,
  },
];

const DEMO_DECISIONS: AuditEntry[] = [
  {
    payout_id: "pout_eval_001",
    agent_id: "procurement-bot",
    amount: 45000,
    decision: "APPROVED",
    reason_code: "POLICY_OK",
    reason_detail: "All governance checks passed",
    vendor_name: "Acme Corp",
    created_at: new Date(Date.now() - 300000).toISOString(),
  },
  {
    payout_id: "pout_eval_002",
    agent_id: "infra-agent",
    amount: 250000,
    decision: "HELD",
    reason_code: "APPROVAL_REQUIRED",
    reason_detail: "Amount exceeds approval threshold",
    vendor_name: "CloudHost India",
    created_at: new Date(Date.now() - 900000).toISOString(),
  },
  {
    payout_id: "pout_eval_003",
    agent_id: "marketing-bot",
    amount: 15000,
    decision: "APPROVED",
    reason_code: "POLICY_OK",
    reason_detail: "Within budget and policy limits",
    vendor_name: "AdNetwork Pvt Ltd",
    created_at: new Date(Date.now() - 1800000).toISOString(),
  },
  {
    payout_id: "pout_eval_004",
    agent_id: "procurement-bot",
    amount: 120000,
    decision: "REJECTED",
    reason_code: "TXN_LIMIT_EXCEEDED",
    reason_detail: "Amount 120000 exceeds per-txn limit of 100000",
    vendor_name: "Unknown Vendor",
    created_at: new Date(Date.now() - 3600000).toISOString(),
  },
  {
    payout_id: "pout_eval_005",
    agent_id: "payroll-agent",
    amount: 500000,
    decision: "APPROVED",
    reason_code: "POLICY_OK",
    reason_detail: "Payroll disbursement cleared",
    vendor_name: "Salary Account",
    created_at: new Date(Date.now() - 7200000).toISOString(),
  },
];

const DEMO_COMPLIANCE: ComplianceStats = {
  total_decisions: 47,
  decisions: {
    APPROVED: { count: 38, total_amount: 2850000 },
    REJECTED: { count: 6, total_amount: 450000 },
    HELD: { count: 3, total_amount: 750000 },
  },
  top_rejection_reasons: [
    { reason: "TXN_LIMIT_EXCEEDED", count: 3 },
    { reason: "LIMIT_EXCEEDED", count: 2 },
    { reason: "DOMAIN_BLOCKED", count: 1 },
  ],
  high_risk_agents: [
    { agent_id: "infra-agent", rejection_rate_pct: 25, total_decisions: 12 },
  ],
};

export function Dashboard() {
  const [data, setData] = useState<DashboardData>({
    agents: DEMO_AGENTS,
    compliance: DEMO_COMPLIANCE,
    recentDecisions: DEMO_DECISIONS,
    mcpConnected: false,
  });
  const [loading, setLoading] = useState(false);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/dashboard");
      if (res.ok) {
        const json = await res.json();
        setData((prev) => ({ ...prev, mcpConnected: json.mcp_connected }));
      }
    } catch {
      // MCP server not reachable -- use demo data
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const approved =
    data.compliance?.decisions?.APPROVED?.count ?? 0;
  const rejected =
    data.compliance?.decisions?.REJECTED?.count ?? 0;
  const held = data.compliance?.decisions?.HELD?.count ?? 0;
  const total = data.compliance?.total_decisions ?? 0;

  return (
    <div className="p-6 space-y-6 max-w-[1400px]">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">
            Financial Governance Dashboard
          </h1>
          <p className="text-sm text-[var(--color-text-muted)] mt-0.5">
            {data.agents.length} agents monitored &middot; {total} decisions
            this period
          </p>
        </div>
        <button
          onClick={refresh}
          disabled={loading}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-lg border border-[var(--color-border)] text-[var(--color-text-muted)] hover:bg-[var(--color-surface-hover)] transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
          Refresh
        </button>
      </div>

      {/* Stats row */}
      <StatsCards
        total={total}
        approved={approved}
        rejected={rejected}
        held={held}
        totalVolume={
          Object.values(data.compliance?.decisions ?? {}).reduce(
            (s, d) => s + (d.total_amount ?? 0),
            0,
          )
        }
        agentCount={data.agents.length}
        redAgents={data.agents.filter((a) => a.budget_health === "red").length}
      />

      {/* Main grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Budget Bars (2/3) */}
        <div className="lg:col-span-2">
          <BudgetBars agents={data.agents} />
        </div>

        {/* Decision Feed (1/3) */}
        <div>
          <DecisionFeed decisions={data.recentDecisions} />
        </div>
      </div>

      {/* Spending chart */}
      <SpendingChart agents={data.agents} />
    </div>
  );
}
