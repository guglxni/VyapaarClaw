"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  MessageSquare,
  Users,
  ScrollText,
  Clock,
  Settings,
  Shield,
} from "lucide-react";

const NAV_ITEMS = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/chat", label: "Chat", icon: MessageSquare },
  { href: "/agents", label: "Agents", icon: Users },
  { href: "/audit", label: "Audit Log", icon: ScrollText },
  { href: "/cron", label: "Cron Jobs", icon: Clock },
  { href: "/settings", label: "Settings", icon: Settings },
] as const;

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Sidebar */}
      <aside className="w-56 flex-shrink-0 border-r border-[var(--color-border)] bg-[var(--color-surface)] flex flex-col">
        {/* Logo */}
        <div className="p-4 border-b border-[var(--color-border)]">
          <div className="flex items-center gap-2">
            <Shield className="w-5 h-5 text-[var(--color-accent)]" />
            <span className="font-semibold text-sm tracking-tight">
              <span className="text-[var(--color-accent)]">Vyapaar</span>
              <span className="text-[var(--color-text)]">Claw</span>
            </span>
          </div>
          <p className="text-[10px] text-[var(--color-text-dim)] mt-1 tracking-wide uppercase">
            AI CFO Dashboard
          </p>
        </div>

        {/* Nav */}
        <nav className="flex-1 py-2 px-2 space-y-0.5">
          {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
            const active =
              href === "/" ? pathname === "/" : pathname.startsWith(href);
            return (
              <Link
                key={href}
                href={href}
                className={`flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-colors ${
                  active
                    ? "bg-[var(--color-accent)]/10 text-[var(--color-accent)]"
                    : "text-[var(--color-text-muted)] hover:bg-[var(--color-surface-hover)] hover:text-[var(--color-text)]"
                }`}
              >
                <Icon className="w-4 h-4" />
                {label}
              </Link>
            );
          })}
        </nav>

        {/* Footer */}
        <div className="p-3 border-t border-[var(--color-border)]">
          <div className="flex items-center gap-2 text-[11px] text-[var(--color-text-dim)]">
            <div className="w-1.5 h-1.5 rounded-full bg-[var(--color-health-green)]" />
            MCP Server Connected
          </div>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-y-auto">{children}</main>
    </div>
  );
}
