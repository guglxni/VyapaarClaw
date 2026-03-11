"use client";

import type { AuditEntry } from "../dashboard";

function formatINR(paise: number): string {
  return `₹${(paise / 100).toLocaleString("en-IN")}`;
}

function timeAgo(iso: string): string {
  const ms = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(ms / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

function badgeClass(decision: string): string {
  switch (decision) {
    case "APPROVED":
      return "bg-[#052e16] text-[#22c55e]";
    case "REJECTED":
      return "bg-[#450a0a] text-[#ef4444]";
    case "HELD":
      return "bg-[#422006] text-[#eab308]";
    default:
      return "bg-[var(--color-surface)] text-[var(--color-text-muted)]";
  }
}

export function DecisionFeed({
  decisions,
}: {
  decisions: AuditEntry[];
}) {
  return (
    <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl p-5 h-full">
      <h2 className="text-xs uppercase tracking-widest text-[var(--color-text-dim)] mb-4">
        Recent Decisions
      </h2>

      <div className="space-y-0.5">
        {decisions.slice(0, 8).map((d) => (
          <div
            key={d.payout_id}
            className="flex items-center justify-between py-2.5 border-b border-[var(--color-border-subtle)] last:border-b-0"
          >
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium truncate">
                  {d.vendor_name || d.agent_id}
                </span>
                <span
                  className={`px-1.5 py-0.5 rounded text-[10px] font-semibold ${badgeClass(d.decision)}`}
                >
                  {d.decision}
                </span>
              </div>
              <div className="text-[11px] text-[var(--color-text-dim)] mt-0.5">
                {d.agent_id} &middot; {d.reason_code}
              </div>
            </div>
            <div className="text-right ml-3 flex-shrink-0">
              <div className="text-sm font-medium tabular-nums">
                {formatINR(d.amount)}
              </div>
              <div className="text-[10px] text-[var(--color-text-dim)]">
                {timeAgo(d.created_at)}
              </div>
            </div>
          </div>
        ))}
      </div>

      {decisions.length === 0 && (
        <p className="text-sm text-[var(--color-text-dim)] text-center py-8">
          No decisions yet.
        </p>
      )}
    </div>
  );
}
