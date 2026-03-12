"""VyapaarClaw TUI — Financial Governance Dashboard in the terminal.

A Textual app providing real-time visibility into:
- Agent budget utilisation
- Governance decision feed
- System health status
- Quick actions (evaluate payout, check vendor, reset budget)
"""

from __future__ import annotations

import contextlib
import os
from datetime import datetime
from typing import ClassVar

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.widgets import (
    Footer,
    Header,
    Label,
    Static,
)

from vyapaar_mcp.tui.widgets import (
    AgentBudgetCard,
    HealthIndicator,
    StatsBar,
)


class VyapaarClawTUI(App):
    """Financial governance dashboard for VyapaarClaw."""

    TITLE = "VyapaarClaw"
    SUB_TITLE = "AI CFO Governance Dashboard"
    CSS_PATH = "theme.tcss"

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("d", "switch_tab('dashboard')", "Dashboard"),
        Binding("a", "switch_tab('agents')", "Agents"),
        Binding("l", "switch_tab('audit')", "Audit Log"),
        Binding("r", "refresh", "Refresh"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._active_tab = "dashboard"
        self._agents: list[dict] = []
        self._decisions: list[dict] = []
        self._health: dict = {}

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="main"):
            yield StatsBar(id="stats-bar")
            with Container(id="content"):
                yield self._build_dashboard()
        yield Footer()

    def _build_dashboard(self) -> ComposeResult:
        with Vertical(id="dashboard-view"):
            with Horizontal(id="dashboard-grid"):
                with VerticalScroll(id="budget-panel"):
                    yield Label("BUDGET UTILISATION", classes="section-title")
                    yield Container(id="budget-cards")
                with VerticalScroll(id="feed-panel"):
                    yield Label("RECENT DECISIONS", classes="section-title")
                    yield Container(id="decision-feed")
            yield Label("SYSTEM HEALTH", classes="section-title")
            with Horizontal(id="health-row"):
                yield HealthIndicator("MCP Server", status="checking", id="health-mcp")
                yield HealthIndicator("Redis", status="checking", id="health-redis")
                yield HealthIndicator("PostgreSQL", status="checking", id="health-pg")
                yield HealthIndicator("Go Bridge", status="checking", id="health-go")
        return

    async def on_mount(self) -> None:
        self.load_data()

    @work(exclusive=True)
    async def load_data(self) -> None:
        """Load governance data from the MCP server or show demo data."""
        mcp_url = os.environ.get("VYAPAAR_MCP_URL", "http://localhost:8000")
        try:
            import httpx

            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(f"{mcp_url}/health")
                if resp.status_code == 200:
                    health = resp.json()
                    self._health = health
                    self._update_health(
                        mcp=True,
                        redis=health.get("redis") == "connected",
                        pg=health.get("postgres") == "connected",
                        go=health.get("razorpay_bridge") == "connected",
                    )
                else:
                    self._load_demo_data()
                    return
        except Exception:
            self._load_demo_data()
            return

        with contextlib.suppress(Exception):
            async with httpx.AsyncClient(timeout=5.0) as client:
                agents_resp = await client.get(f"{mcp_url}/api/agents")
                if agents_resp.status_code == 200:
                    self._agents = agents_resp.json().get("agents", [])

                audit_resp = await client.get(f"{mcp_url}/api/audit")
                if audit_resp.status_code == 200:
                    self._decisions = audit_resp.json().get("entries", [])

        if not self._agents:
            self._load_demo_data()
        else:
            self._render_agents()
            self._render_decisions()
            self._update_stats()

    def _load_demo_data(self) -> None:
        self._agents = [
            {
                "agent_id": "procurement-bot",
                "daily_limit": 500000,
                "current_spend": 320000,
                "utilisation_pct": 64,
                "health": "yellow",
                "per_txn_limit": 100000,
            },
            {
                "agent_id": "payroll-agent",
                "daily_limit": 2500000,
                "current_spend": 1800000,
                "utilisation_pct": 72,
                "health": "yellow",
                "per_txn_limit": 500000,
            },
            {
                "agent_id": "marketing-bot",
                "daily_limit": 100000,
                "current_spend": 15000,
                "utilisation_pct": 15,
                "health": "green",
                "per_txn_limit": 25000,
            },
            {
                "agent_id": "infra-agent",
                "daily_limit": 1000000,
                "current_spend": 890000,
                "utilisation_pct": 89,
                "health": "red",
                "per_txn_limit": 200000,
            },
        ]
        self._decisions = [
            {
                "payout_id": "pout_001",
                "agent_id": "procurement-bot",
                "amount": 45000,
                "decision": "APPROVED",
                "reason_code": "POLICY_OK",
                "vendor_name": "Acme Corp",
                "created_at": datetime.now().isoformat(),
            },
            {
                "payout_id": "pout_002",
                "agent_id": "infra-agent",
                "amount": 250000,
                "decision": "HELD",
                "reason_code": "APPROVAL_REQUIRED",
                "vendor_name": "CloudHost India",
                "created_at": datetime.now().isoformat(),
            },
            {
                "payout_id": "pout_003",
                "agent_id": "marketing-bot",
                "amount": 15000,
                "decision": "APPROVED",
                "reason_code": "POLICY_OK",
                "vendor_name": "AdNetwork Pvt Ltd",
                "created_at": datetime.now().isoformat(),
            },
            {
                "payout_id": "pout_004",
                "agent_id": "procurement-bot",
                "amount": 120000,
                "decision": "REJECTED",
                "reason_code": "TXN_LIMIT_EXCEEDED",
                "vendor_name": "Unknown Vendor",
                "created_at": datetime.now().isoformat(),
            },
            {
                "payout_id": "pout_005",
                "agent_id": "payroll-agent",
                "amount": 500000,
                "decision": "APPROVED",
                "reason_code": "POLICY_OK",
                "vendor_name": "Salary Account",
                "created_at": datetime.now().isoformat(),
            },
        ]
        self._update_health(mcp=False, redis=False, pg=False, go=False)
        self._render_agents()
        self._render_decisions()
        self._update_stats()

    def _render_agents(self) -> None:
        container = self.query_one("#budget-cards", Container)
        container.remove_children()
        for agent in sorted(self._agents, key=lambda a: -a.get("utilisation_pct", 0)):
            container.mount(AgentBudgetCard(agent))

    def _render_decisions(self) -> None:
        container = self.query_one("#decision-feed", Container)
        container.remove_children()
        for decision in self._decisions[:10]:
            d = decision.get("decision", "APPROVED")
            agent = decision.get("agent_id", "unknown")
            amount = decision.get("amount", 0)
            reason = decision.get("reason_code", "")
            vendor = decision.get("vendor_name", "")
            amount_str = _format_inr(amount)

            color = {"APPROVED": "green", "REJECTED": "red", "HELD": "yellow"}.get(d, "white")

            line = Static(
                f"[bold {color}]{d:<9}[/] "
                f"[dim]{agent:<18}[/] "
                f"[bold]{amount_str:>10}[/]  "
                f"[dim]{vendor or reason}[/]",
                classes="decision-line",
            )
            container.mount(line)

    def _update_stats(self) -> None:
        stats = self.query_one("#stats-bar", StatsBar)
        total = len(self._decisions)
        approved = sum(1 for d in self._decisions if d.get("decision") == "APPROVED")
        rejected = sum(1 for d in self._decisions if d.get("decision") == "REJECTED")
        held = sum(1 for d in self._decisions if d.get("decision") == "HELD")
        volume = sum(d.get("amount", 0) for d in self._decisions)
        stats.update_stats(
            total=total,
            approved=approved,
            rejected=rejected,
            held=held,
            volume=volume,
            agents=len(self._agents),
        )

    def _update_health(self, *, mcp: bool, redis: bool, pg: bool, go: bool) -> None:
        mapping = {
            "health-mcp": mcp,
            "health-redis": redis,
            "health-pg": pg,
            "health-go": go,
        }
        for widget_id, connected in mapping.items():
            with contextlib.suppress(Exception):
                indicator = self.query_one(f"#{widget_id}", HealthIndicator)
                indicator.set_status("connected" if connected else "disconnected")

    def action_refresh(self) -> None:
        self.notify("Refreshing data...")
        self.load_data()

    def action_switch_tab(self, tab: str) -> None:
        self._active_tab = tab
        self.notify(f"Switched to {tab}")

    def action_quit(self) -> None:
        self.exit()


def _format_inr(paise: int) -> str:
    rupees = paise / 100
    if rupees >= 10_000_000:
        return f"₹{rupees / 10_000_000:.1f}Cr"
    if rupees >= 100_000:
        return f"₹{rupees / 100_000:.1f}L"
    if rupees >= 1_000:
        return f"₹{rupees / 1_000:.1f}K"
    return f"₹{rupees:,.0f}"


def run_tui() -> None:
    """Entry point for the TUI."""
    app = VyapaarClawTUI()
    app.run()
