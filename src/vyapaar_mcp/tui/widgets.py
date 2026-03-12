"""Custom Textual widgets for VyapaarClaw TUI."""

from __future__ import annotations

import contextlib

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import ProgressBar, Static


def _format_inr(paise: int) -> str:
    rupees = paise / 100
    if rupees >= 10_000_000:
        return f"₹{rupees / 10_000_000:.1f}Cr"
    if rupees >= 100_000:
        return f"₹{rupees / 100_000:.1f}L"
    if rupees >= 1_000:
        return f"₹{rupees / 1_000:.1f}K"
    return f"₹{rupees:,.0f}"


class StatsBar(Widget):
    """Top bar showing key governance metrics."""

    total: reactive[int] = reactive(0)
    approved: reactive[int] = reactive(0)
    rejected: reactive[int] = reactive(0)
    held: reactive[int] = reactive(0)
    volume: reactive[int] = reactive(0)
    agents: reactive[int] = reactive(0)

    def compose(self) -> ComposeResult:
        with Horizontal(id="stats-row"):
            yield Static(id="stat-total", classes="stat-card")
            yield Static(id="stat-approved", classes="stat-card stat-green")
            yield Static(id="stat-rejected", classes="stat-card stat-red")
            yield Static(id="stat-held", classes="stat-card stat-yellow")
            yield Static(id="stat-volume", classes="stat-card")
            yield Static(id="stat-agents", classes="stat-card")

    def update_stats(
        self,
        *,
        total: int,
        approved: int,
        rejected: int,
        held: int,
        volume: int,
        agents: int,
    ) -> None:
        self.total = total
        self.approved = approved
        self.rejected = rejected
        self.held = held
        self.volume = volume
        self.agents = agents
        self._refresh_display()

    def _refresh_display(self) -> None:
        cards = {
            "stat-total": f"[bold]DECISIONS[/]\n[bold white]{self.total}[/]",
            "stat-approved": f"[bold]APPROVED[/]\n[bold green]{self.approved}[/]",
            "stat-rejected": f"[bold]REJECTED[/]\n[bold red]{self.rejected}[/]",
            "stat-held": f"[bold]HELD[/]\n[bold yellow]{self.held}[/]",
            "stat-volume": f"[bold]VOLUME[/]\n[bold white]{_format_inr(self.volume)}[/]",
            "stat-agents": f"[bold]AGENTS[/]\n[bold white]{self.agents}[/]",
        }
        for widget_id, text in cards.items():
            with contextlib.suppress(Exception):
                self.query_one(f"#{widget_id}", Static).update(text)


class AgentBudgetCard(Widget):
    """A single agent's budget utilisation card."""

    def __init__(self, agent: dict) -> None:
        super().__init__()
        self._agent = agent

    def compose(self) -> ComposeResult:
        agent = self._agent
        agent_id = agent.get("agent_id", "unknown")
        util = agent.get("utilisation_pct", 0)
        health = agent.get("health", "green")
        spent = agent.get("current_spend", 0)
        limit = agent.get("daily_limit", 0)

        color = {"red": "red", "yellow": "yellow", "green": "green"}.get(health, "white")
        bar_style = f"bar-{health}"

        yield Static(
            f"[bold]{agent_id}[/]  "
            f"[{color}]{util}%[/]  "
            f"[dim]{_format_inr(spent)} / {_format_inr(limit)}[/]",
            classes="budget-label",
        )
        yield ProgressBar(
            total=100,
            show_eta=False,
            show_percentage=False,
            classes=f"budget-bar {bar_style}",
        )

    def on_mount(self) -> None:
        util = self._agent.get("utilisation_pct", 0)
        with contextlib.suppress(Exception):
            bar = self.query_one(ProgressBar)
            bar.advance(util)


class HealthIndicator(Widget):
    """A service health status indicator."""

    status: reactive[str] = reactive("checking")

    def __init__(self, service_name: str, status: str = "checking", **kwargs) -> None:  # type: ignore[override]
        super().__init__(**kwargs)
        self._service_name = service_name
        self.status = status

    def compose(self) -> ComposeResult:
        yield Static(id="health-display", classes="health-widget")

    def watch_status(self, new_status: str) -> None:
        self._refresh()

    def set_status(self, status: str) -> None:
        self.status = status

    def _refresh(self) -> None:
        icons = {
            "connected": "[bold green]●[/]",
            "disconnected": "[bold red]●[/]",
            "checking": "[bold yellow]○[/]",
        }
        icon = icons.get(self.status, icons["checking"])
        with contextlib.suppress(Exception):
            display = self.query_one("#health-display", Static)
            display.update(f"{icon} {self._service_name}")

    def on_mount(self) -> None:
        self._refresh()


class DecisionBadge(Static):
    """A styled decision badge (APPROVED/REJECTED/HELD)."""

    def __init__(self, decision: str) -> None:
        color = {"APPROVED": "green", "REJECTED": "red", "HELD": "yellow"}.get(decision, "white")
        super().__init__(f"[bold {color}]{decision}[/]")
