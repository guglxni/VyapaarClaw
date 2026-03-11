"use client";

import {
  CheckCircle2,
  XCircle,
  Clock,
  Activity,
  Users,
  AlertTriangle,
  IndianRupee,
} from "lucide-react";

function formatINR(paise: number): string {
  const rupees = paise / 100;
  if (rupees >= 10000000) return `₹${(rupees / 10000000).toFixed(1)} Cr`;
  if (rupees >= 100000) return `₹${(rupees / 100000).toFixed(1)} L`;
  if (rupees >= 1000) return `₹${(rupees / 1000).toFixed(1)}K`;
  return `₹${rupees.toLocaleString("en-IN")}`;
}

type Props = {
  total: number;
  approved: number;
  rejected: number;
  held: number;
  totalVolume: number;
  agentCount: number;
  redAgents: number;
};

export function StatsCards({
  total,
  approved,
  rejected,
  held,
  totalVolume,
  agentCount,
  redAgents,
}: Props) {
  const cards = [
    {
      label: "Total Decisions",
      value: total,
      icon: Activity,
      color: "var(--color-accent)",
    },
    {
      label: "Approved",
      value: approved,
      icon: CheckCircle2,
      color: "var(--color-health-green)",
    },
    {
      label: "Rejected",
      value: rejected,
      icon: XCircle,
      color: "var(--color-health-red)",
    },
    {
      label: "Held for Review",
      value: held,
      icon: Clock,
      color: "var(--color-health-yellow)",
    },
    {
      label: "Total Volume",
      value: formatINR(totalVolume),
      icon: IndianRupee,
      color: "var(--color-accent)",
    },
    {
      label: "Active Agents",
      value: agentCount,
      icon: Users,
      color: "var(--color-text-muted)",
      alert: redAgents > 0 ? `${redAgents} critical` : undefined,
    },
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
      {cards.map((card) => (
        <div
          key={card.label}
          className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl p-4"
        >
          <div className="flex items-center gap-2 mb-2">
            <card.icon
              className="w-4 h-4"
              style={{ color: card.color }}
            />
            <span className="text-[11px] text-[var(--color-text-dim)] uppercase tracking-wider">
              {card.label}
            </span>
          </div>
          <div className="text-2xl font-semibold tabular-nums">{card.value}</div>
          {card.alert && (
            <div className="flex items-center gap-1 mt-1 text-[11px] text-[var(--color-health-red)]">
              <AlertTriangle className="w-3 h-3" />
              {card.alert}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
