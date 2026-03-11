"use client";

import { useState } from "react";
import { AppShell } from "../components/shell";
import {
  ScrollText,
  Search,
  Filter,
  CheckCircle2,
  XCircle,
  Clock,
} from "lucide-react";

type AuditEntry = {
  payout_id: string;
  agent_id: string;
  amount: number;
  decision: "APPROVED" | "REJECTED" | "HELD";
  reason_code: string;
  reason_detail: string;
  vendor_name: string | null;
  created_at: string;
  processing_ms: number;
};

const DEMO_ENTRIES: AuditEntry[] = [
  {
    payout_id: "pout_eval_001",
    agent_id: "procurement-bot",
    amount: 45000,
    decision: "APPROVED",
    reason_code: "POLICY_OK",
    reason_detail: "All governance checks passed — budget OK, vendor safe, within limits",
    vendor_name: "Acme Corp",
    created_at: new Date(Date.now() - 300000).toISOString(),
    processing_ms: 42,
  },
  {
    payout_id: "pout_eval_002",
    agent_id: "infra-agent",
    amount: 250000,
    decision: "HELD",
    reason_code: "APPROVAL_REQUIRED",
    reason_detail: "Amount 250000 exceeds approval threshold of 100000",
    vendor_name: "CloudHost India",
    created_at: new Date(Date.now() - 900000).toISOString(),
    processing_ms: 38,
  },
  {
    payout_id: "pout_eval_003",
    agent_id: "marketing-bot",
    amount: 15000,
    decision: "APPROVED",
    reason_code: "POLICY_OK",
    reason_detail: "Within all governance limits",
    vendor_name: "AdNetwork Pvt Ltd",
    created_at: new Date(Date.now() - 1800000).toISOString(),
    processing_ms: 29,
  },
  {
    payout_id: "pout_eval_004",
    agent_id: "procurement-bot",
    amount: 120000,
    decision: "REJECTED",
    reason_code: "TXN_LIMIT_EXCEEDED",
    reason_detail: "Amount 120000 paise exceeds per-txn limit of 100000 paise",
    vendor_name: "Unknown Vendor",
    created_at: new Date(Date.now() - 3600000).toISOString(),
    processing_ms: 12,
  },
  {
    payout_id: "pout_eval_005",
    agent_id: "payroll-agent",
    amount: 500000,
    decision: "APPROVED",
    reason_code: "POLICY_OK",
    reason_detail: "Payroll disbursement cleared through all checks",
    vendor_name: "Salary Account",
    created_at: new Date(Date.now() - 7200000).toISOString(),
    processing_ms: 55,
  },
  {
    payout_id: "pout_eval_006",
    agent_id: "infra-agent",
    amount: 50000,
    decision: "REJECTED",
    reason_code: "RISK_HIGH",
    reason_detail: "Google Safe Browsing flagged vendor URL as MALWARE threat",
    vendor_name: "suspicious-host.ru",
    created_at: new Date(Date.now() - 14400000).toISOString(),
    processing_ms: 234,
  },
  {
    payout_id: "pout_eval_007",
    agent_id: "procurement-bot",
    amount: 75000,
    decision: "APPROVED",
    reason_code: "POLICY_OK",
    reason_detail: "Vendor verified via GLEIF, clean reputation",
    vendor_name: "Office Supplies India Ltd",
    created_at: new Date(Date.now() - 28800000).toISOString(),
    processing_ms: 178,
  },
];

function formatINR(paise: number): string {
  return `₹${(paise / 100).toLocaleString("en-IN")}`;
}

function formatTime(iso: string): string {
  return new Date(iso).toLocaleString("en-IN", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function decisionIcon(d: string) {
  switch (d) {
    case "APPROVED":
      return <CheckCircle2 className="w-4 h-4 text-[#22c55e]" />;
    case "REJECTED":
      return <XCircle className="w-4 h-4 text-[#ef4444]" />;
    case "HELD":
      return <Clock className="w-4 h-4 text-[#eab308]" />;
    default:
      return null;
  }
}

function badgeClass(d: string): string {
  switch (d) {
    case "APPROVED":
      return "bg-[#052e16] text-[#22c55e]";
    case "REJECTED":
      return "bg-[#450a0a] text-[#ef4444]";
    case "HELD":
      return "bg-[#422006] text-[#eab308]";
    default:
      return "";
  }
}

export default function AuditPage() {
  const [filter, setFilter] = useState<string>("all");
  const [search, setSearch] = useState("");

  const filtered = DEMO_ENTRIES.filter((e) => {
    if (filter !== "all" && e.decision !== filter) return false;
    if (search) {
      const q = search.toLowerCase();
      return (
        e.agent_id.toLowerCase().includes(q) ||
        e.payout_id.toLowerCase().includes(q) ||
        (e.vendor_name?.toLowerCase().includes(q) ?? false) ||
        e.reason_code.toLowerCase().includes(q)
      );
    }
    return true;
  });

  return (
    <AppShell>
      <div className="p-6 max-w-[1200px] space-y-5">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Audit Log</h1>
          <p className="text-sm text-[var(--color-text-muted)] mt-0.5">
            {DEMO_ENTRIES.length} governance decisions recorded
          </p>
        </div>

        {/* Filters */}
        <div className="flex items-center gap-3">
          <div className="relative flex-1 max-w-xs">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--color-text-dim)]" />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by agent, vendor, payout ID..."
              className="w-full bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg pl-9 pr-3 py-2 text-sm text-[var(--color-text)] placeholder:text-[var(--color-text-dim)] focus:outline-none focus:border-[var(--color-accent)]/50"
            />
          </div>
          <div className="flex gap-1">
            {["all", "APPROVED", "REJECTED", "HELD"].map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`px-3 py-1.5 text-xs rounded-lg border transition-colors ${
                  filter === f
                    ? "border-[var(--color-accent)] bg-[var(--color-accent)]/10 text-[var(--color-accent)]"
                    : "border-[var(--color-border)] text-[var(--color-text-muted)] hover:bg-[var(--color-surface-hover)]"
                }`}
              >
                {f === "all" ? "All" : f}
              </button>
            ))}
          </div>
        </div>

        {/* Table */}
        <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[var(--color-border)]">
                <th className="text-left text-[10px] uppercase tracking-wider text-[var(--color-text-dim)] px-4 py-3">
                  Decision
                </th>
                <th className="text-left text-[10px] uppercase tracking-wider text-[var(--color-text-dim)] px-4 py-3">
                  Agent
                </th>
                <th className="text-left text-[10px] uppercase tracking-wider text-[var(--color-text-dim)] px-4 py-3">
                  Vendor
                </th>
                <th className="text-right text-[10px] uppercase tracking-wider text-[var(--color-text-dim)] px-4 py-3">
                  Amount
                </th>
                <th className="text-left text-[10px] uppercase tracking-wider text-[var(--color-text-dim)] px-4 py-3">
                  Reason
                </th>
                <th className="text-right text-[10px] uppercase tracking-wider text-[var(--color-text-dim)] px-4 py-3">
                  Time
                </th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((entry) => (
                <tr
                  key={entry.payout_id}
                  className="border-b border-[var(--color-border-subtle)] last:border-b-0 hover:bg-[var(--color-surface-hover)] transition-colors"
                >
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      {decisionIcon(entry.decision)}
                      <span
                        className={`text-[10px] font-semibold px-1.5 py-0.5 rounded ${badgeClass(entry.decision)}`}
                      >
                        {entry.decision}
                      </span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-[var(--color-text-muted)]">
                    {entry.agent_id}
                  </td>
                  <td className="px-4 py-3">
                    {entry.vendor_name || "—"}
                  </td>
                  <td className="px-4 py-3 text-right font-medium tabular-nums">
                    {formatINR(entry.amount)}
                  </td>
                  <td className="px-4 py-3">
                    <div className="text-[var(--color-text-muted)] text-xs">
                      {entry.reason_code}
                    </div>
                    <div className="text-[var(--color-text-dim)] text-[11px] mt-0.5 max-w-[300px] truncate">
                      {entry.reason_detail}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-right text-[var(--color-text-dim)] text-xs whitespace-nowrap">
                    {formatTime(entry.created_at)}
                    <div className="text-[10px]">{entry.processing_ms}ms</div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {filtered.length === 0 && (
            <div className="text-center py-12 text-sm text-[var(--color-text-dim)]">
              No matching entries found.
            </div>
          )}
        </div>
      </div>
    </AppShell>
  );
}
