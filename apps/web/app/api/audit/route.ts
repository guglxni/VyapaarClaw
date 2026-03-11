import { NextResponse } from "next/server";

export async function GET() {
  return NextResponse.json({
    note: "Audit data served via MCP tools. Use the dashboard or chat to query live data.",
  });
}
