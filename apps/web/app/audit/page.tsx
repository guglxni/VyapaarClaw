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

import { DataTable } from "../components/data-table";
import { createColumnHelper, ColumnDef } from "@tanstack/react-table";

const columnHelper = createColumnHelper<AuditEntry>();

const columns: ColumnDef<AuditEntry, any>[] = [
  columnHelper.accessor("decision", {
    header: "Decision",
    cell: (info) => (
      <div className="flex items-center gap-2">
        {decisionIcon(info.getValue())}
        <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded ${badgeClass(info.getValue())}`}>
          {info.getValue()}
        </span>
      </div>
    ),
  }),
  columnHelper.accessor("agent_id", {
    header: "Agent",
    cell: (info) => <span className="text-[var(--color-text-muted)]">{info.getValue()}</span>,
  }),
  columnHelper.accessor("vendor_name", {
    header: "Vendor",
    cell: (info) => info.getValue() || "—",
  }),
  columnHelper.accessor("amount", {
    header: "Amount",
    cell: (info) => <div className="text-right font-medium tabular-nums">{formatINR(info.getValue())}</div>,
  }),
  columnHelper.accessor("reason_code", {
    header: "Reason",
    cell: (info) => (
      <div>
        <div className="text-[var(--color-text-muted)] text-xs">{info.getValue()}</div>
        <div className="text-[var(--color-text-dim)] text-[11px] mt-0.5 max-w-[300px] truncate">
          {info.row.original.reason_detail}
        </div>
      </div>
    ),
  }),
  columnHelper.accessor("created_at", {
    header: "Time",
    cell: (info) => (
      <div className="text-right text-[var(--color-text-dim)] text-xs whitespace-nowrap">
        {formatTime(info.getValue())}
        <div className="text-[10px]">{info.row.original.processing_ms}ms</div>
      </div>
    ),
  }),
];

export default function AuditPage() {
  const [filter, setFilter] = useState<string>("all");

  const filtered = DEMO_ENTRIES.filter((e) => {
    if (filter !== "all" && e.decision !== filter) return false;
    return true;
  });

  return (
    <AppShell>
      <div className="p-6 max-w-[1200px] space-y-5">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold tracking-tight">Audit Log</h1>
            <p className="text-sm text-[var(--color-text-muted)] mt-0.5">
              {DEMO_ENTRIES.length} governance decisions recorded
            </p>
          </div>
          <div className="flex items-center gap-1 bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg p-1">
            {["all", "APPROVED", "REJECTED", "HELD"].map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`px-3 py-1.5 text-xs rounded-md font-medium transition-colors ${
                  filter === f
                    ? "bg-[var(--color-bg)] text-[var(--color-text)] shadow-sm"
                    : "text-[var(--color-text-muted)] hover:text-[var(--color-text)]"
                }`}
              >
                {f === "all" ? "All" : f}
              </button>
            ))}
          </div>
        </div>

        {/* CRM Data Table inside Audit Page */}
        <DataTable columns={columns} data={filtered} searchPlaceholder="Search audit logs..." />
      </div>
    </AppShell>
  );
}
