const MCP_BASE = process.env.MCP_SERVER_URL || "http://localhost:8000";

export type McpToolResult = {
  content: Array<{ type: string; text: string }>;
  isError?: boolean;
};

export async function callMcpTool(
  toolName: string,
  args: Record<string, unknown> = {},
): Promise<Record<string, unknown>> {
  const res = await fetch(`${MCP_BASE}/sse`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    cache: "no-store",
  });

  if (!res.ok) {
    throw new Error(`MCP SSE connection failed: ${res.status}`);
  }

  return args;
}

export async function fetchHealth(): Promise<Record<string, unknown>> {
  const res = await fetch(`${MCP_BASE}/health`, { cache: "no-store" });
  return res.json();
}

export function formatPaise(paise: number): string {
  const rupees = paise / 100;
  return `₹${rupees.toLocaleString("en-IN", { minimumFractionDigits: 0 })}`;
}

export function healthColor(health: string): string {
  switch (health) {
    case "red":
      return "var(--color-health-red)";
    case "yellow":
      return "var(--color-health-yellow)";
    default:
      return "var(--color-health-green)";
  }
}

export function decisionBadgeClass(decision: string): string {
  switch (decision) {
    case "APPROVED":
      return "bg-[var(--color-approved)] text-[var(--color-approved-text)]";
    case "REJECTED":
      return "bg-[var(--color-rejected)] text-[var(--color-rejected-text)]";
    case "HELD":
      return "bg-[var(--color-held)] text-[var(--color-held-text)]";
    default:
      return "bg-[var(--color-surface)] text-[var(--color-text-muted)]";
  }
}
