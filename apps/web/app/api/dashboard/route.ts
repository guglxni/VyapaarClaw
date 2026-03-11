import { NextResponse } from "next/server";

const MCP_BASE = process.env.MCP_SERVER_URL || "http://localhost:8000";

async function callMcpHttpFallback(endpoint: string) {
  try {
    const res = await fetch(`${MCP_BASE}${endpoint}`, { cache: "no-store" });
    if (res.ok) return await res.json();
  } catch {}
  return null;
}

export async function GET() {
  const health = await callMcpHttpFallback("/health");

  return NextResponse.json({
    mcp_connected: !!health,
    mcp_url: MCP_BASE,
    timestamp: new Date().toISOString(),
  });
}
