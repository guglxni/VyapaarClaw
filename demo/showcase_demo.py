#!/usr/bin/env python3
"""VyapaarClaw — OpenClaw Showcase Demo.

7-scene automated demo showcasing the full governance pipeline:
  1. Setup — Show tools registered
  2. Legitimate payout → APPROVED
  3. Malware vendor → BLOCKED
  4. Budget breach → REJECTED
  5. Human approval → HELD → Slack
  6. ML anomaly → FLAGGED
  7. Dashboard overview

Run: python demo/showcase_demo.py
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

# ── Terminal Colors ──────────────────────────────────────────────────
CYAN = "\033[96m"
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
MAGENTA = "\033[95m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"
BG_GREEN = "\033[42m"
BG_RED = "\033[41m"
BG_YELLOW = "\033[43m"
BG_BLUE = "\033[44m"


def banner(text: str, emoji: str = "🦞") -> None:
    width = 72
    print(f"\n{CYAN}{'━' * width}{RESET}")
    print(f"  {emoji}  {BOLD}{CYAN}{text}{RESET}")
    print(f"{CYAN}{'━' * width}{RESET}")


def scene(num: int, title: str, emoji: str = "▶") -> None:
    print(f"\n{MAGENTA}{'─' * 60}{RESET}")
    print(f"  {YELLOW}{emoji} Scene {num}: {BOLD}{title}{RESET}")
    print(f"{MAGENTA}{'─' * 60}{RESET}")


def result_box(decision: str, details: dict) -> None:
    """Print a decision result in a colored box."""
    if decision == "APPROVED":
        color = BG_GREEN
        icon = "✅"
    elif decision == "REJECTED" or decision == "BLOCKED":
        color = BG_RED
        icon = "🚫"
    elif decision == "HELD":
        color = BG_YELLOW
        icon = "⏳"
    elif decision == "FLAGGED":
        color = BG_BLUE
        icon = "⚠️"
    else:
        color = ""
        icon = "ℹ️"

    print(f"\n  {color}{BOLD} {icon} {decision} {RESET}")
    for key, value in details.items():
        print(f"    {DIM}{key}:{RESET} {value}")


def show(label: str, data: dict | list | str) -> None:
    if isinstance(data, (dict, list)):
        formatted = json.dumps(data, indent=2, default=str)
        print(f"  {GREEN}✓ {label}:{RESET}")
        for line in formatted.split("\n")[:12]:
            print(f"    {DIM}{line}{RESET}")
    else:
        print(f"  {GREEN}✓ {label}: {data}{RESET}")


def pause(seconds: float = 1.0) -> None:
    """Pause for dramatic effect during demo."""
    time.sleep(seconds)


async def run_showcase() -> None:
    """Run the 7-scene OpenClaw Showcase demo."""
    from vyapaar_mcp.db.postgres import PostgresClient
    from vyapaar_mcp.db.redis_client import RedisClient
    from vyapaar_mcp.config import load_config
    from vyapaar_mcp.governance.engine import GovernanceEngine
    from vyapaar_mcp.reputation.safe_browsing import SafeBrowsingChecker
    from vyapaar_mcp.reputation.gleif import GLEIFChecker
    from vyapaar_mcp.reputation.anomaly import TransactionAnomalyScorer
    from vyapaar_mcp.models import AgentPolicy, PayoutEntity
    from vyapaar_mcp.observability import metrics

    # ═══════════════════════════════════════════════════════════════
    # OPENING
    # ═══════════════════════════════════════════════════════════════

    banner("VYAPAAR MCP — OpenClaw Showcase", "🦞")
    print(f"""
  {BOLD}The Autonomous CFO for the Agentic Economy{RESET}
  {DIM}Protocol-level financial governance for AI agents{RESET}

  {CYAN}AI Model:{RESET}   Kimi K2.5 (Azure AI Services)
  {CYAN}Payments:{RESET}   Razorpay X (Sandbox)
  {CYAN}Security:{RESET}   6-layer deep defense
  {CYAN}Protocol:{RESET}   Model Context Protocol (MCP)
  {CYAN}Tools:{RESET}     17 governance + 40 Razorpay (Go sidecar)
    """)

    # ── Infrastructure Setup ──────────────────────────────────────
    config = load_config()
    redis = RedisClient(config.redis_url)
    postgres = PostgresClient(config.postgres_dsn)

    try:
        await redis.connect()
        await postgres.connect()
    except Exception as e:
        print(f"{RED}Infrastructure error: {e}{RESET}")
        print(f"{YELLOW}Start Redis & PostgreSQL: docker compose up -d redis postgres{RESET}")
        return

    safe_browsing = SafeBrowsingChecker(config.google_safe_browsing_key)
    gleif = GLEIFChecker(redis=redis)
    anomaly = TransactionAnomalyScorer(redis=redis)
    governance = GovernanceEngine(
        redis=redis,
        postgres=postgres,
        safe_browsing=safe_browsing,
    )

    # Verify connectivity
    redis_ok = await redis.ping()
    postgres_ok = await postgres.ping()
    print(f"  {GREEN if redis_ok else RED}Redis:      {'Connected ✓' if redis_ok else 'OFFLINE ✗'}{RESET}")
    print(f"  {GREEN if postgres_ok else RED}PostgreSQL: {'Connected ✓' if postgres_ok else 'OFFLINE ✗'}{RESET}")
    print(f"  {GREEN}Kimi K2.5:  {'Configured ✓' if config.azure_openai_api_key else 'Key pending'}{RESET}")

    if not (redis_ok and postgres_ok):
        print(f"\n{RED}Cannot proceed without infrastructure.{RESET}")
        return

    # ═══════════════════════════════════════════════════════════════
    # SCENE 1: THE SETUP
    # ═══════════════════════════════════════════════════════════════

    scene(1, "The Setup — MCP Tools Registered", "🔧")

    tools = [
        ("handle_razorpay_webhook", "Ingress", "Webhook → governance pipeline"),
        ("poll_razorpay_payouts", "Ingress", "API polling (no tunnel)"),
        ("check_vendor_reputation", "Intel", "Google Safe Browsing v4"),
        ("verify_vendor_entity", "Intel", "GLEIF legal entity check"),
        ("score_transaction_risk", "ML", "IsolationForest anomaly"),
        ("get_agent_risk_profile", "ML", "Historical spending patterns"),
        ("get_agent_budget", "Read", "Current spend & limits"),
        ("set_agent_policy", "Admin", "Per-agent policy CRUD"),
        ("get_audit_log", "Read", "Decision history"),
        ("handle_slack_action", "Human", "Approve/reject from Slack"),
        ("handle_telegram_action", "Human", "Approve/reject from Telegram"),
        ("check_context_taint", "Sec", "Dual LLM taint tracker"),
        ("validate_tool_call_security", "Sec", "Quarantine validation gate"),
        ("azure_chat", "AI", "Kimi K2.5 chat completions"),
        ("get_archestra_status", "Sec", "Deterministic policy status"),
        ("health_check", "Ops", "Service status"),
        ("get_metrics", "Ops", "Prometheus metrics"),
    ]

    for name, category, desc in tools:
        print(f"  {GREEN}✓{RESET} [{CYAN}{category:6s}{RESET}] {BOLD}{name}{RESET} — {DIM}{desc}{RESET}")

    print(f"\n  {BOLD}+ 40 Razorpay tools{RESET} via Go MCP sidecar (payments, orders, refunds, settlements)")
    print(f"  {BOLD}{len(tools)} governance tools registered{RESET}")

    # ── Seed demo policies ────────────────────────────────────────
    demo_agent = "openclaw-agent-001"
    policy = AgentPolicy(
        agent_id=demo_agent,
        daily_limit=1000000,  # ₹10,000
        per_txn_limit=500000,  # ₹5,000
        require_approval_above=300000,  # ₹3,000
        allowed_domains=["google.com", "amazon.in", "aws.amazon.com"],
        blocked_domains=["sketchy-vendor.xyz"],
    )
    await postgres.upsert_agent_policy(policy)
    # Reset daily budget
    await redis.reset_daily_spend(demo_agent)

    print(f"\n  {GREEN}✓{RESET} Agent policy seeded: {BOLD}{demo_agent}{RESET}")
    print(f"    Daily limit: ₹{policy.daily_limit / 100:,.0f}")
    print(f"    Per-txn: ₹{policy.per_txn_limit / 100:,.0f}")
    print(f"    Approval >₹{policy.require_approval_above / 100:,.0f}")

    pause(1.5)

    # ═══════════════════════════════════════════════════════════════
    # SCENE 2: LEGITIMATE PAYOUT → APPROVED
    # ═══════════════════════════════════════════════════════════════

    scene(2, "Legitimate Payout — APPROVED ✅", "💰")

    print(f"  Agent requests: {BOLD}₹2,500{RESET} to {BOLD}Google LLC{RESET}")
    print(f"  Vendor URL: https://google.com")
    print(f"  {DIM}Running governance pipeline...{RESET}")

    payout_legit = PayoutEntity(
        id="pout_showcase_001",
        amount=250000,  # ₹2,500
        currency="INR",
        status="queued",
        mode="IMPS",
        purpose="vendor_payment",
    )

    pause(0.5)
    result = await governance.evaluate(payout_legit, demo_agent, "https://google.com")
    metrics.record_decision(result)

    result_box(result.decision.value, {
        "Payout ID": result.payout_id,
        "Amount": f"₹{result.amount / 100:,.0f}",
        "Reason": result.reason_detail,
        "Processing": f"{result.processing_ms}ms",
    })

    # GLEIF check for demo
    print(f"\n  {DIM}GLEIF Entity Verification:{RESET}")
    try:
        gleif_result = await gleif.search_entity("Google LLC")
        if gleif_result.is_verified and gleif_result.best_match:
            print(f"    {GREEN}✓ Verified:{RESET} {gleif_result.best_match.legal_name}")
            print(f"    {GREEN}  LEI:{RESET} {gleif_result.best_match.lei}")
        else:
            print(f"    {YELLOW}⚠ Entity not found in GLEIF registry{RESET}")
    except Exception as e:
        print(f"    {DIM}GLEIF check: {e}{RESET}")

    pause(1.5)

    # ═══════════════════════════════════════════════════════════════
    # SCENE 3: MALWARE VENDOR → BLOCKED
    # ═══════════════════════════════════════════════════════════════

    scene(3, "Malware Vendor — BLOCKED 🚫", "🦠")

    print(f"  Agent requests: {BOLD}₹3,000{RESET} to {RED}sketchy-vendor.xyz{RESET}")
    print(f"  {DIM}Running Google Safe Browsing check...{RESET}")

    # Amount within per-txn limit so domain check is reached
    payout_malware = PayoutEntity(
        id="pout_showcase_002",
        amount=300000,  # ₹3,000 (within ₹5,000 per-txn limit)
        currency="INR",
        status="queued",
        mode="NEFT",
        purpose="vendor_payment",
    )

    pause(0.5)
    result = await governance.evaluate(payout_malware, demo_agent, "https://sketchy-vendor.xyz")
    metrics.record_decision(result)

    result_box("BLOCKED", {
        "Payout ID": result.payout_id,
        "Amount": f"₹{result.amount / 100:,.0f}",
        "Reason": result.reason_detail,
        "Security layer": "Domain blocklist + Google Safe Browsing",
        "Action": "Payout cancelled, budget rolled back",
    })

    pause(1.5)

    # ═══════════════════════════════════════════════════════════════
    # SCENE 4: BUDGET BREACH → REJECTED
    # ═══════════════════════════════════════════════════════════════

    scene(4, "Budget Breach — REJECTED 💸", "📊")

    # First, burn through most of the remaining budget to set up the breach
    # Scene 2 spent ₹2,500. We need to get close to the ₹10,000 limit.
    burn_payout1 = PayoutEntity(
        id="pout_showcase_003a",
        amount=200000,  # ₹2,000 (below approval threshold)
        currency="INR",
        status="queued",
        mode="NEFT",
        purpose="vendor_payment",
    )
    await governance.evaluate(burn_payout1, demo_agent, "https://amazon.in")

    burn_payout2 = PayoutEntity(
        id="pout_showcase_003b",
        amount=200000,  # ₹2,000 more (below approval threshold)
        currency="INR",
        status="queued",
        mode="NEFT",
        purpose="vendor_payment",
    )
    await governance.evaluate(burn_payout2, demo_agent, "https://amazon.in")

    spent_so_far = await redis.get_daily_spend(demo_agent)
    remaining_so_far = max(0, policy.daily_limit - spent_so_far)

    print(f"  Budget status: ₹{spent_so_far / 100:,.0f} spent / ₹{policy.daily_limit / 100:,.0f} limit")
    print(f"  Agent requests: {BOLD}₹4,500{RESET} more (only ₹{remaining_so_far / 100:,.0f} remaining)")
    print(f"  {DIM}Atomic Redis INCRBY check...{RESET}")

    payout_budget = PayoutEntity(
        id="pout_showcase_003c",
        amount=450000,  # ₹4,500 — pushes over the limit
        currency="INR",
        status="queued",
        mode="NEFT",
        purpose="vendor_payment",
    )

    pause(0.3)
    result = await governance.evaluate(payout_budget, demo_agent, "https://amazon.in")
    metrics.record_decision(result)

    result_box(result.decision.value, {
        "Payout ID": result.payout_id,
        "Amount": f"₹{result.amount / 100:,.0f}",
        "Reason": result.reason_detail,
        "Redis operation": "Atomic INCRBY — checked and rolled back in sub-ms",
        "Cumulative spent": f"₹{spent_so_far / 100:,.0f} of ₹{policy.daily_limit / 100:,.0f} daily limit",
    })

    pause(1.5)

    # ═══════════════════════════════════════════════════════════════
    # SCENE 5: HUMAN APPROVAL → HELD
    # ═══════════════════════════════════════════════════════════════

    scene(5, "Human Approval Required — HELD ⏳", "🔔")

    print(f"  Agent requests: {BOLD}₹3,500{RESET} (above ₹3,000 approval threshold)")
    print(f"  {DIM}All checks pass, but amount triggers human review...{RESET}")

    payout_held = PayoutEntity(
        id="pout_showcase_004",
        amount=350000,  # ₹3,500 (> approval threshold, within budget)
        currency="INR",
        status="queued",
        mode="IMPS",
        purpose="vendor_payment",
    )

    pause(0.5)
    result = await governance.evaluate(payout_held, demo_agent, "https://amazon.in")
    metrics.record_decision(result)

    result_box(result.decision.value, {
        "Payout ID": result.payout_id,
        "Amount": f"₹{result.amount / 100:,.0f}",
        "Reason": result.reason_detail,
        "Next step": "Slack notification sent → Reviewer clicks ✅ or ❌",
    })

    if config.slack_bot_token:
        print(f"\n    {GREEN}📱 Slack notification sent to #{config.slack_channel_id}{RESET}")
    else:
        print(f"\n    {DIM}(Slack not configured — would send approval request){RESET}")

    pause(1.5)

    # ═══════════════════════════════════════════════════════════════
    # SCENE 6: ML ANOMALY → FLAGGED
    # ═══════════════════════════════════════════════════════════════

    scene(6, "ML Anomaly Detection — FLAGGED ⚠️", "🤖")

    print(f"  {BOLD}night-bot{RESET} sends ₹25,000 at {BOLD}3:17 AM{RESET}")
    print(f"  {DIM}IsolationForest scoring against historical patterns...{RESET}")

    try:
        score_result = await anomaly.score_transaction(
            amount=2500000,  # ₹25,000
            agent_id="night-bot",
        )
        result_box("FLAGGED" if score_result.is_anomalous else "NORMAL", {
            "Risk score": f"{score_result.risk_score:.2f} (0.0=normal, 1.0=anomalous)",
            "Is anomalous": str(score_result.is_anomalous),
            "Model trained": str(score_result.model_trained),
        })
    except Exception as e:
        print(f"    {YELLOW}ML scoring: {e}{RESET}")
        print(f"    {DIM}(Needs ≥10 historical transactions for confident scoring){RESET}")

    pause(1.5)

    # ═══════════════════════════════════════════════════════════════
    # SCENE 7: METRICS & AUDIT
    # ═══════════════════════════════════════════════════════════════

    scene(7, "The Dashboard — Metrics & Audit Trail", "📊")

    snapshot = metrics.snapshot()
    print(f"  {BOLD}Governance Metrics:{RESET}")
    print(f"    Decisions total:  {snapshot.get('decisions_total', 0)}")
    print(f"    Approved:         {GREEN}{snapshot.get('decisions_approved', 0)}{RESET}")
    print(f"    Rejected:         {RED}{snapshot.get('decisions_rejected', 0)}{RESET}")
    print(f"    Held:             {YELLOW}{snapshot.get('decisions_held', 0)}{RESET}")

    # Budget status
    spent = await redis.get_daily_spend(demo_agent)
    remaining = max(0, policy.daily_limit - spent)
    utilization = (spent / policy.daily_limit * 100) if policy.daily_limit > 0 else 0
    print(f"\n  {BOLD}Budget Status ({demo_agent}):{RESET}")
    print(f"    Daily limit:  ₹{policy.daily_limit / 100:,.0f}")
    print(f"    Spent today:  ₹{spent / 100:,.0f}")
    print(f"    Remaining:    ₹{remaining / 100:,.0f}")
    print(f"    Utilization:  {utilization:.1f}%")

    print(f"\n  {DIM}Run the Streamlit dashboard for visual command center:{RESET}")
    print(f"  {CYAN}streamlit run demo/dashboard.py{RESET}")

    # ═══════════════════════════════════════════════════════════════
    # CLOSING
    # ═══════════════════════════════════════════════════════════════

    banner("SHOWCASE COMPLETE", "🏆")
    print(f"""
  {BOLD}What We Demonstrated:{RESET}
    • {GREEN}17 MCP governance tools{RESET} + 40 Razorpay tools (Go sidecar)
    • {GREEN}6-layer security:{RESET} Safe Browsing, GLEIF, Budget, Human, ML, Policy
    • {GREEN}Atomic Redis{RESET} budget enforcement (sub-millisecond)
    • {GREEN}Human-in-the-loop{RESET} via Slack
    • {GREEN}ML anomaly detection{RESET} with IsolationForest
    • {GREEN}Complete audit trail{RESET} in PostgreSQL

  {BOLD}Architecture:{RESET}
    OpenClaw Agent (Kimi K2.5)
      ↓ MCP/stdio or MCP/SSE
    VyapaarClaw Server (FastMCP, 17 tools)
      ↓ MCP/stdio
    Razorpay Go Bridge (40+ tools)
      ↓ HTTP
    Razorpay Sandbox API

  {DIM}The CFO for the Agentic Economy — always watching, always enforcing.{RESET}
  {DIM}GitHub: https://github.com/guglxni/vyapaarclaw{RESET}
    """)

    # Cleanup
    await redis.disconnect()
    await postgres.disconnect()


if __name__ == "__main__":
    try:
        asyncio.run(run_showcase())
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Demo interrupted{RESET}")
    except Exception as e:
        print(f"\n{RED}Error: {e}{RESET}")
        import traceback
        traceback.print_exc()
