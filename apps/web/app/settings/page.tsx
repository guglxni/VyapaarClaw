"use client";

import { useState, useEffect } from "react";
import { AppShell } from "../components/shell";
import {
  Settings,
  Server,
  Database,
  Key,
  Globe,
  Shield,
  Bell,
  CheckCircle2,
  XCircle,
  Loader2,
  ExternalLink,
} from "lucide-react";

type ServiceHealth = {
  name: string;
  status: "connected" | "disconnected" | "checking";
  details?: string;
};

type ConfigSection = {
  title: string;
  icon: React.ComponentType<{ className?: string }>;
  fields: ConfigField[];
};

type ConfigField = {
  label: string;
  envVar: string;
  value: string;
  masked?: boolean;
  help?: string;
};

const SECTIONS: ConfigSection[] = [
  {
    title: "MCP Server",
    icon: Server,
    fields: [
      { label: "Transport", envVar: "VYAPAAR_TRANSPORT", value: "sse", help: "SSE or stdio" },
      { label: "Host", envVar: "VYAPAAR_HOST", value: "0.0.0.0" },
      { label: "Port", envVar: "VYAPAAR_PORT", value: "8000" },
    ],
  },
  {
    title: "Razorpay X",
    icon: Key,
    fields: [
      { label: "Key ID", envVar: "VYAPAAR_RAZORPAY_KEY_ID", value: "rzp_test_•••", masked: true },
      { label: "Key Secret", envVar: "VYAPAAR_RAZORPAY_KEY_SECRET", value: "•••••••••", masked: true },
      { label: "Webhook Secret", envVar: "VYAPAAR_RAZORPAY_WEBHOOK_SECRET", value: "•••••••••", masked: true },
    ],
  },
  {
    title: "Database",
    icon: Database,
    fields: [
      { label: "Redis URL", envVar: "VYAPAAR_REDIS_URL", value: "redis://localhost:6379/0" },
      { label: "Postgres DSN", envVar: "VYAPAAR_POSTGRES_DSN", value: "postgresql://•••@localhost:5432/vyapaar", masked: true },
    ],
  },
  {
    title: "Google Safe Browsing",
    icon: Globe,
    fields: [
      { label: "API Key", envVar: "VYAPAAR_GOOGLE_SAFE_BROWSING_KEY", value: "•••••••••", masked: true },
    ],
  },
  {
    title: "Notifications",
    icon: Bell,
    fields: [
      { label: "Slack Bot Token", envVar: "VYAPAAR_SLACK_BOT_TOKEN", value: "Not configured", masked: true },
      { label: "Slack Channel", envVar: "VYAPAAR_SLACK_CHANNEL_ID", value: "Not configured" },
      { label: "Telegram Bot Token", envVar: "VYAPAAR_TELEGRAM_BOT_TOKEN", value: "Not configured", masked: true },
      { label: "Telegram Chat ID", envVar: "VYAPAAR_TELEGRAM_CHAT_ID", value: "Not configured" },
    ],
  },
  {
    title: "AI / LLM",
    icon: Shield,
    fields: [
      { label: "Azure Endpoint", envVar: "VYAPAAR_AZURE_OPENAI_ENDPOINT", value: "https://models.inference.ai.azure.com" },
      { label: "Model", envVar: "VYAPAAR_AZURE_OPENAI_DEPLOYMENT", value: "kimi-k2.5" },
      { label: "API Version", envVar: "VYAPAAR_AZURE_OPENAI_API_VERSION", value: "2024-05-01-preview" },
    ],
  },
];

export default function SettingsPage() {
  const [services, setServices] = useState<ServiceHealth[]>([
    { name: "MCP Server", status: "checking" },
    { name: "Redis", status: "checking" },
    { name: "PostgreSQL", status: "checking" },
    { name: "Go Bridge", status: "checking" },
  ]);

  useEffect(() => {
    const checkHealth = async () => {
      try {
        const res = await fetch("/api/dashboard");
        if (res.ok) {
          const data = await res.json();
          setServices([
            { name: "MCP Server", status: data.mcp_connected ? "connected" : "disconnected" },
            { name: "Redis", status: data.redis === "connected" ? "connected" : "disconnected" },
            { name: "PostgreSQL", status: data.postgres === "connected" ? "connected" : "disconnected" },
            { name: "Go Bridge", status: data.razorpay_bridge === "connected" ? "connected" : "disconnected" },
          ]);
        } else {
          setServices((prev) => prev.map((s) => ({ ...s, status: "disconnected" as const })));
        }
      } catch {
        setServices((prev) => prev.map((s) => ({ ...s, status: "disconnected" as const })));
      }
    };
    checkHealth();
  }, []);

  return (
    <AppShell>
      <div className="p-6 max-w-[1000px] space-y-6">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Settings</h1>
          <p className="text-sm text-[var(--color-text-muted)] mt-0.5">
            VyapaarClaw configuration and service health
          </p>
        </div>

        {/* Service Health */}
        <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl p-5">
          <h2 className="text-xs uppercase tracking-widest text-[var(--color-text-dim)] mb-4">
            Service Health
          </h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {services.map((svc) => (
              <div
                key={svc.name}
                className="flex items-center gap-2.5 p-3 rounded-lg border border-[var(--color-border-subtle)]"
              >
                {svc.status === "checking" && (
                  <Loader2 className="w-4 h-4 text-[var(--color-text-dim)] animate-spin" />
                )}
                {svc.status === "connected" && (
                  <CheckCircle2 className="w-4 h-4 text-[var(--color-health-green)]" />
                )}
                {svc.status === "disconnected" && (
                  <XCircle className="w-4 h-4 text-[var(--color-health-red)]" />
                )}
                <div>
                  <div className="text-sm font-medium">{svc.name}</div>
                  <div className="text-[10px] text-[var(--color-text-dim)] capitalize">
                    {svc.status}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Configuration Sections */}
        {SECTIONS.map((section) => (
          <div
            key={section.title}
            className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl p-5"
          >
            <div className="flex items-center gap-2 mb-4">
              <section.icon className="w-4 h-4 text-[var(--color-accent)]" />
              <h2 className="text-xs uppercase tracking-widest text-[var(--color-text-dim)]">
                {section.title}
              </h2>
            </div>
            <div className="space-y-3">
              {section.fields.map((field) => (
                <div key={field.envVar} className="flex items-center justify-between">
                  <div>
                    <div className="text-sm text-[var(--color-text-muted)]">
                      {field.label}
                    </div>
                    <div className="text-[10px] text-[var(--color-text-dim)] font-mono mt-0.5">
                      {field.envVar}
                    </div>
                  </div>
                  <div className="text-sm font-mono text-[var(--color-text)] bg-[var(--color-bg)] px-3 py-1.5 rounded-lg border border-[var(--color-border-subtle)]">
                    {field.value}
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}

        {/* Links */}
        <div className="flex items-center gap-4 text-sm text-[var(--color-text-dim)]">
          <a
            href="https://github.com/guglxni/VyapaarClaw"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 hover:text-[var(--color-accent)] transition-colors"
          >
            <ExternalLink className="w-3.5 h-3.5" />
            GitHub
          </a>
          <span>v0.1.0</span>
          <span>MIT License</span>
        </div>
      </div>
    </AppShell>
  );
}
