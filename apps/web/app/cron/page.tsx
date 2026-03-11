"use client";

import { AppShell } from "../components/shell";
import { Clock, CheckCircle2, Loader2, Calendar } from "lucide-react";

type CronJob = {
  name: string;
  schedule: string;
  description: string;
  lastRun: string | null;
  status: "idle" | "running" | "completed";
  channel: string;
};

const CRON_JOBS: CronJob[] = [
  {
    name: "VyapaarClaw Morning Brief",
    schedule: "30 1 * * * (7:00 AM IST daily)",
    description:
      "Scans all agent budgets, generates yesterday's compliance summary, and forecasts cash flow for agents showing yellow or red health.",
    lastRun: new Date(Date.now() - 3600000 * 5).toISOString(),
    status: "completed",
    channel: "Telegram",
  },
  {
    name: "VyapaarClaw Budget Alarm",
    schedule: "*/30 * * * * (every 30 min)",
    description:
      "Checks all agent budget utilisation. Alerts via Telegram if any agent exceeds 80% daily limit. Silent when all agents are green.",
    lastRun: new Date(Date.now() - 1800000).toISOString(),
    status: "completed",
    channel: "Telegram",
  },
  {
    name: "VyapaarClaw Weekly Compliance",
    schedule: "30 3 * * 1 (Mon 9:00 AM IST)",
    description:
      "Generates comprehensive weekly governance report with decision stats, high-risk agents, spending trends, and Indian compliance notes (GST/TDS).",
    lastRun: new Date(Date.now() - 3600000 * 72).toISOString(),
    status: "completed",
    channel: "Telegram",
  },
];

function formatTime(iso: string): string {
  return new Date(iso).toLocaleString("en-IN", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function CronPage() {
  return (
    <AppShell>
      <div className="p-6 max-w-[900px] space-y-6">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">
            Scheduled Jobs
          </h1>
          <p className="text-sm text-[var(--color-text-muted)] mt-0.5">
            {CRON_JOBS.length} cron jobs configured for autonomous CFO operations
          </p>
        </div>

        <div className="space-y-3">
          {CRON_JOBS.map((job) => (
            <div
              key={job.name}
              className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl p-5"
            >
              <div className="flex items-start justify-between">
                <div className="flex items-start gap-3">
                  <div className="w-8 h-8 rounded-lg bg-[var(--color-accent)]/10 flex items-center justify-center flex-shrink-0 mt-0.5">
                    {job.status === "running" ? (
                      <Loader2 className="w-4 h-4 text-[var(--color-accent)] animate-spin" />
                    ) : (
                      <Clock className="w-4 h-4 text-[var(--color-accent)]" />
                    )}
                  </div>
                  <div>
                    <h3 className="font-medium text-sm">{job.name}</h3>
                    <p className="text-[11px] text-[var(--color-text-dim)] mt-0.5 font-mono">
                      {job.schedule}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-1.5">
                  <div className="w-1.5 h-1.5 rounded-full bg-[var(--color-health-green)]" />
                  <span className="text-[11px] text-[var(--color-text-dim)]">
                    Active
                  </span>
                </div>
              </div>

              <p className="text-sm text-[var(--color-text-muted)] mt-3 leading-relaxed">
                {job.description}
              </p>

              <div className="flex items-center gap-4 mt-3 pt-3 border-t border-[var(--color-border-subtle)]">
                <div className="flex items-center gap-1.5 text-[11px] text-[var(--color-text-dim)]">
                  <Calendar className="w-3 h-3" />
                  Last run:{" "}
                  {job.lastRun ? formatTime(job.lastRun) : "Never"}
                </div>
                <div className="flex items-center gap-1.5 text-[11px] text-[var(--color-text-dim)]">
                  Channel: {job.channel}
                </div>
                {job.status === "completed" && (
                  <div className="flex items-center gap-1 text-[11px] text-[var(--color-health-green)]">
                    <CheckCircle2 className="w-3 h-3" />
                    Completed
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </AppShell>
  );
}
