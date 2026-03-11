"""VyapaarClaw — Command Center Dashboard.

Premium dark-themed governance dashboard for the OpenClaw Showcase.
Features: KPI cards, live decision stream, budget meters, vendor
intelligence tools, and real-time metrics.

Run: streamlit run demo/dashboard.py
"""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

# Add src to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))


# ── Persistent Event Loop (background thread) ────────────────────
# Streamlit's rerun model destroys event loops after each script run.
# asyncpg connections are bound to the loop they were created on.
# Solution: keep ONE loop alive in a daemon thread, dispatch to it.

import threading

_LOOP: asyncio.AbstractEventLoop | None = None
_THREAD: threading.Thread | None = None
_ASYNC_LOCK = threading.Lock()


def _start_background_loop(loop: asyncio.AbstractEventLoop) -> None:
    asyncio.set_event_loop(loop)
    loop.run_forever()


def get_event_loop() -> asyncio.AbstractEventLoop:
    global _LOOP, _THREAD
    if _LOOP is None or _LOOP.is_closed():
        _LOOP = asyncio.new_event_loop()
        _THREAD = threading.Thread(target=_start_background_loop, args=(_LOOP,), daemon=True)
        _THREAD.start()
    return _LOOP


def run_async(coro):
    """Run an async coroutine on the persistent background loop.

    Serialized with a lock to prevent asyncpg connection contention
    when Streamlit reruns interleave abandoned and new coroutines
    on the shared event loop.
    """
    loop = get_event_loop()
    with _ASYNC_LOCK:
        future = asyncio.run_coroutine_threadsafe(coro, loop)
        try:
            return future.result(timeout=30)
        except Exception:
            future.cancel()
            raise


# ── Initialize Clients (cached, persistent) ───────────────────────
@st.cache_resource
def get_clients():
    """Initialize database and API clients as singletons."""
    from vyapaar_mcp.config import load_config
    from vyapaar_mcp.db.postgres import PostgresClient
    from vyapaar_mcp.db.redis_client import RedisClient
    from vyapaar_mcp.reputation.safe_browsing import SafeBrowsingChecker

    config = load_config()
    postgres = PostgresClient(config.postgres_dsn)
    redis = RedisClient(config.redis_url)
    safe_browsing = SafeBrowsingChecker(config.google_safe_browsing_key)

    run_async(postgres.connect())
    run_async(redis.connect())

    return postgres, redis, safe_browsing, config


# ── Page Config ──────────────────────────────────────────────────
st.set_page_config(
    page_title="Vyapaar Command Center",
    page_icon="🦞",
    layout="wide",
)

# ── Sidebar ──────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🦞 VyapaarClaw")
    st.caption("The Autonomous CFO for the Agentic Economy")

    navigation = st.radio(
        "Navigate",
        options=["🎯 Command", "🛡️ Governance", "🔍 Research", "📊 Metrics"],
        label_visibility="collapsed",
    )

    st.divider()

    with st.container(border=True):
        st.markdown("**Active Tools**")
        st.caption("17 MCP Tools Registered")
        tool_groups = {
            "Ingress": ["webhook", "poll"],
            "Intel": ["reputation", "gleif"],
            "ML": ["anomaly", "risk_profile"],
            "Budget": ["budget", "policy"],
            "Human": ["slack_action", "telegram_action"],
            "AI": ["azure_chat", "taint_check"],
            "Ops": ["health", "metrics", "audit", "archestra"],
        }
        for group, tools in tool_groups.items():
            st.markdown(f"**{group}** · {len(tools)} tools")

    st.divider()
    st.caption("Kimi K2.5 · Azure AI Services")
    st.caption("Razorpay X · Go MCP Sidecar")

# ── Load Clients ─────────────────────────────────────────────────
postgres, redis, safe_browsing, config = get_clients()

# ── Header ───────────────────────────────────────────────────────
st.title("🛡️ Autonomous Fintech Firewall", anchor=False)
st.caption(
    f"Protocol-level financial governance · "
    f"Kimi K2.5 · "
    f"PostgreSQL {config.postgres_dsn.split('@')[-1].split('/')[0]}"
)

# ═════════════════════════════════════════════════════════════════
# 1. COMMAND VIEW
# ═════════════════════════════════════════════════════════════════
if "Command" in navigation:
    st.subheader("System Status", anchor=False)

    # Live health checks
    redis_ok = run_async(redis.ping())
    postgres_ok = run_async(postgres.ping())

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric(
            "Redis",
            "ONLINE" if redis_ok else "OFFLINE",
            delta="Budget · Rate Limit",
            delta_color="normal" if redis_ok else "inverse",
            border=True,
        )
    with c2:
        st.metric(
            "PostgreSQL",
            "ONLINE" if postgres_ok else "OFFLINE",
            delta="Audit · Policies",
            delta_color="normal" if postgres_ok else "inverse",
            border=True,
        )
    with c3:
        st.metric(
            "Kimi K2.5",
            "READY" if config.azure_openai_api_key else "NO KEY",
            delta="Azure AI",
            delta_color="normal" if config.azure_openai_api_key else "inverse",
            border=True,
        )
    with c4:
        st.metric(
            "Slack",
            "ENABLED" if config.slack_bot_token else "OFF",
            delta="Human-in-Loop",
            delta_color="normal" if config.slack_bot_token else "off",
            border=True,
        )

    st.divider()

    # Budget overview for demo agent
    st.subheader("💰 Live Budget Status", anchor=False)

    demo_agent = st.text_input(
        "Agent ID",
        value="openclaw-agent-001",
        label_visibility="collapsed",
        placeholder="Enter agent ID...",
    )

    policy = run_async(postgres.get_agent_policy(demo_agent))

    if policy:
        spent = run_async(redis.get_daily_spend(demo_agent))
        remaining = max(0, policy.daily_limit - spent)
        util = (spent / policy.daily_limit * 100) if policy.daily_limit > 0 else 0

        bc1, bc2, bc3, bc4 = st.columns(4)
        with bc1:
            st.metric(
                "Daily Allowance",
                f"₹{policy.daily_limit / 100:,.0f}",
                border=True,
            )
        with bc2:
            st.metric(
                "Spent Today",
                f"₹{spent / 100:,.0f}",
                delta=f"{util:.0f}% utilized",
                delta_color="inverse" if util > 80 else "normal",
                border=True,
            )
        with bc3:
            st.metric(
                "Remaining",
                f"₹{remaining / 100:,.0f}",
                border=True,
            )
        with bc4:
            if policy.per_txn_limit:
                st.metric(
                    "Per-Txn Cap",
                    f"₹{policy.per_txn_limit / 100:,.0f}",
                    border=True,
                )

        st.progress(min(util / 100, 1.0), text=f"Budget Utilization: {util:.1f}%")
    else:
        st.warning(f"No policy found for **{demo_agent}**")

    st.divider()

    # Live decision stream
    st.subheader("📡 Live Decision Stream", anchor=False)

    entries = run_async(postgres.get_audit_logs(limit=15))

    if entries:
        rows = []
        for e in entries:
            d = e.model_dump(mode="json")
            # Add decision emoji
            if d["decision"] == "APPROVED":
                d["status"] = "✅ APPROVED"
            elif d["decision"] == "REJECTED":
                d["status"] = "🚫 REJECTED"
            elif d["decision"] == "HELD":
                d["status"] = "⏳ HELD"
            else:
                d["status"] = d["decision"]
            rows.append(d)

        df = pd.DataFrame(rows)

        display_cols = [
            c for c in ["created_at", "payout_id", "agent_id", "amount",
                        "status", "reason_code", "reason_detail"]
            if c in df.columns
        ]

        st.dataframe(
            df[display_cols],
            column_config={
                "created_at": st.column_config.DatetimeColumn(
                    "Timestamp", format="D MMM, HH:mm:ss",
                ),
                "payout_id": "Payout",
                "agent_id": "Agent",
                "amount": st.column_config.NumberColumn(
                    "Amount (₹)", format="₹%.0f",
                ),
                "status": "Decision",
                "reason_code": "Policy",
                "reason_detail": "Details",
            },
            hide_index=True,
            use_container_width=True,
        )
    else:
        st.info("No decisions recorded yet. Run the showcase demo first!")
        st.code("python demo/showcase_demo.py", language="bash")

# ═════════════════════════════════════════════════════════════════
# 2. GOVERNANCE VIEW
# ═════════════════════════════════════════════════════════════════
elif "Governance" in navigation:
    tab_policy, tab_budget = st.tabs(
        ["⚙️ Agent Policies", "💳 Budget Enforcement"],
    )

    with tab_policy:
        st.subheader("Policy Configuration", anchor=False)

        with st.form("policy_editor", border=True):
            col1, col2 = st.columns(2)
            agent_id = col1.text_input(
                "Agent Identity",
                value="openclaw-agent-001",
                help="Unique AI agent identifier",
            )
            daily_limit = col2.number_input(
                "Daily Spend Limit (₹)", value=10000, step=500, min_value=0,
            )

            col3, col4 = st.columns(2)
            per_txn = col3.number_input(
                "Max Per Transaction (₹)", value=5000, step=100, min_value=0,
            )
            approval = col4.number_input(
                "Approval Threshold (₹)", value=3000, step=100, min_value=0,
            )

            col5, col6 = st.columns(2)
            allowed = col5.text_area(
                "Allowed Domains",
                value="google.com, amazon.in, aws.amazon.com",
                help="Comma-separated domain whitelist",
            )
            blocked = col6.text_area(
                "Blocked Domains",
                value="sketchy-vendor.xyz",
                help="Comma-separated domain blocklist",
            )

            if st.form_submit_button("💾 Update Policy", type="primary"):
                from vyapaar_mcp.models import AgentPolicy

                new_policy = AgentPolicy(
                    agent_id=agent_id,
                    daily_limit=int(daily_limit * 100),
                    per_txn_limit=int(per_txn * 100),
                    require_approval_above=int(approval * 100),
                    allowed_domains=[
                        d.strip() for d in allowed.split(",") if d.strip()
                    ],
                    blocked_domains=[
                        d.strip() for d in blocked.split(",") if d.strip()
                    ],
                )
                run_async(postgres.upsert_agent_policy(new_policy))
                st.toast(f"Policy updated for {agent_id} ✓")

    with tab_budget:
        st.subheader("Real-time Budget Meter", anchor=False)

        b_agent = st.text_input("Lookup Agent", value="openclaw-agent-001")
        policy = run_async(postgres.get_agent_policy(b_agent))

        if policy:
            spent = run_async(redis.get_daily_spend(b_agent))
            rem = max(0, policy.daily_limit - spent)
            util = (
                (spent / policy.daily_limit * 100)
                if policy.daily_limit > 0
                else 0
            )

            gb1, gb2, gb3 = st.columns(3)
            with gb1:
                st.metric(
                    "Allowance",
                    f"₹{policy.daily_limit / 100:,.0f}",
                    border=True,
                )
            with gb2:
                st.metric(
                    "Burned",
                    f"₹{spent / 100:,.0f}",
                    delta=f"{util:.1f}%",
                    delta_color="inverse",
                    border=True,
                )
            with gb3:
                st.metric("Available", f"₹{rem / 100:,.0f}", border=True)

            st.progress(min(util / 100, 1.0), text=f"Utilization: {util:.1f}%")

            # Policy details
            with st.expander("📋 Full Policy Details"):
                st.json(policy.model_dump(mode="json"))
        else:
            st.warning("No governing policy found for this identity.")

# ═════════════════════════════════════════════════════════════════
# 3. RESEARCH VIEW
# ═════════════════════════════════════════════════════════════════
elif "Research" in navigation:
    st.subheader("🔍 Intelligence Tools", anchor=False)

    col_v, col_e = st.columns(2)

    with col_v, st.container(border=True):
        st.markdown("**🌐 Safe Browsing Lookup**")
        st.caption("Google Safe Browsing v4 — threat detection")
        url_check = st.text_input(
            "Target URL", value="https://google.com",
        )
        if st.button("🔎 Analyze Threats", type="primary"):
            with st.spinner("Querying Google Safe Browsing..."):
                res = run_async(safe_browsing.check_url(url_check))
                if res.is_safe:
                    st.success("**CLEAN** — No malicious patterns detected")
                else:
                    st.error(
                        f"**DANGER** — Threats: {', '.join(res.threat_types)}"
                    )

    with col_e, st.container(border=True):
        st.markdown("**🏢 Legal Entity Verification**")
        st.caption("GLEIF Registry — LEI verification")
        v_name = st.text_input("Vendor Name", value="Google LLC")
        if st.button("🔎 Verify Identity", type="primary"):
            from vyapaar_mcp.reputation.gleif import GLEIFChecker

            checker = GLEIFChecker(redis=redis)
            with st.spinner("Querying GLEIF registry..."):
                res = run_async(checker.search_entity(v_name))
                if res.is_verified and res.best_match:
                    st.success(
                        f"**VERIFIED** — {res.best_match.legal_name}"
                    )
                    st.json(res.best_match.model_dump())
                else:
                    st.warning(
                        "**UNVERIFIED** — No issued LEI found for this entity"
                    )

# ═════════════════════════════════════════════════════════════════
# 4. METRICS VIEW
# ═════════════════════════════════════════════════════════════════
elif "Metrics" in navigation:
    from vyapaar_mcp.observability import metrics as governance_metrics

    st.subheader("📊 Operational Analytics", anchor=False)

    snapshot = governance_metrics.snapshot()

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric(
            "Total Decisions",
            snapshot.get("decisions_total", 0),
            border=True,
        )
    with m2:
        st.metric(
            "Approved",
            snapshot.get("decisions_approved", 0),
            border=True,
        )
    with m3:
        st.metric(
            "Rejected",
            snapshot.get("decisions_rejected", 0),
            border=True,
        )
    with m4:
        st.metric(
            "Held",
            snapshot.get("decisions_held", 0),
            border=True,
        )

    st.divider()

    col1, col2 = st.columns(2)
    with col1, st.container(border=True):
        st.markdown("**⚡ Latency Performance**")
        avg_latency = snapshot.get("avg_latency_ms", 0)
        st.metric(
            "Average Processing",
            f"{avg_latency:.1f} ms",
            delta="Real-time" if avg_latency < 500 else "Slow",
            delta_color="normal" if avg_latency < 500 else "inverse",
        )

    with col2, st.container(border=True):
        st.markdown("**🌍 Intelligence Hits**")
        rep = snapshot.get("reputation_checks", 0)
        total_checks = sum(rep.values()) if isinstance(rep, dict) else rep
        st.metric("Reputation Lookups", total_checks)

    with st.expander("📁 Raw Prometheus Data"):
        st.code(governance_metrics.render(), language="text")


# ── Footer ───────────────────────────────────────────────────────
st.divider()
st.caption(
    "VyapaarClaw · v2.0.0 · OpenClaw Showcase · "
    f"Powered by Kimi K2.5 · {datetime.now().strftime('%B %d, %Y')}"
)
