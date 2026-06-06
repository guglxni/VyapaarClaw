"""Formal Payout Approval State Machine.

Replaces simple APPROVED/REJECTED/HELD with a full lifecycle:
  QUEUED → POLICY_CHECK → REPUTATION_CHECK → ANOMALY_CHECK →
    → APPROVED (auto) → DISBURSED → CONFIRMED
    → HELD → PENDING_L1 → PENDING_L2 → APPROVED
    → REJECTED → ARCHIVED

Each transition is logged with timestamp, actor, and reason.
"""

from __future__ import annotations

import datetime as _dt
import uuid
from typing import Any

from transitions import Machine


class PayoutWorkflow:
    """State machine for a single payout's lifecycle."""

    states = [
        "queued",
        "policy_check",
        "reputation_check",
        "anomaly_check",
        "approved",
        "held",
        "pending_l1_approval",
        "pending_l2_approval",
        "disbursed",
        "confirmed",
        "rejected",
        "archived",
        "failed",
    ]

    def __init__(self, payout_id: str = "", amount_paise: int = 0, agent_id: str = "") -> None:
        self.payout_id = payout_id or str(uuid.uuid4())[:8]
        self.amount_paise = amount_paise
        self.agent_id = agent_id
        self.created_at = _dt.datetime.now(_dt.timezone.utc).isoformat()
        self.history: list[dict[str, Any]] = []

        self.machine = Machine(
            model=self,
            states=PayoutWorkflow.states,
            initial="queued",
            auto_transitions=False,
            send_event=True,
        )

        # Governance pipeline transitions
        self.machine.add_transition("start_review", "queued", "policy_check", after="_log_transition")
        self.machine.add_transition("pass_policy", "policy_check", "reputation_check", after="_log_transition")
        self.machine.add_transition("pass_reputation", "reputation_check", "anomaly_check", after="_log_transition")
        self.machine.add_transition("pass_anomaly", "anomaly_check", "approved", after="_log_transition")

        # Hold path (escalation)
        self.machine.add_transition("hold", ["policy_check", "reputation_check", "anomaly_check"], "held", after="_log_transition")
        self.machine.add_transition("escalate_l1", "held", "pending_l1_approval", after="_log_transition")
        self.machine.add_transition("approve_l1", "pending_l1_approval", "approved", after="_log_transition")
        self.machine.add_transition("escalate_l2", "pending_l1_approval", "pending_l2_approval", after="_log_transition")
        self.machine.add_transition("approve_l2", "pending_l2_approval", "approved", after="_log_transition")

        # Rejection path
        self.machine.add_transition("reject", ["policy_check", "reputation_check", "anomaly_check", "held", "pending_l1_approval", "pending_l2_approval"], "rejected", after="_log_transition")

        # Disbursement path
        self.machine.add_transition("disburse", "approved", "disbursed", after="_log_transition")
        self.machine.add_transition("confirm", "disbursed", "confirmed", after="_log_transition")
        self.machine.add_transition("fail_disbursement", "disbursed", "failed", after="_log_transition")

        # Archive
        self.machine.add_transition("archive", ["rejected", "confirmed", "failed"], "archived", after="_log_transition")

    def _log_transition(self, event: Any) -> None:
        """Log every state transition with metadata."""
        self.history.append({
            "timestamp": _dt.datetime.now(_dt.timezone.utc).isoformat(),
            "from_state": event.transition.source,
            "to_state": event.transition.dest,
            "trigger": event.event.name,
            "actor": getattr(event, "kwargs", {}).get("actor", "system"),
            "reason": getattr(event, "kwargs", {}).get("reason", ""),
        })

    def get_status(self) -> dict[str, Any]:
        """Return current payout workflow status."""
        return {
            "payout_id": self.payout_id,
            "amount_paise": self.amount_paise,
            "agent_id": self.agent_id,
            "current_state": self.state,  # type: ignore[attr-defined]
            "created_at": self.created_at,
            "history": self.history,
            "transitions_available": [
                t.name for t in self.machine.get_triggers(self.state)  # type: ignore[attr-defined]
            ] if hasattr(self, "state") else [],
        }


# ---------------------------------------------------------------------------
# Module-level workflow registry (in-memory + optional Postgres)
# ---------------------------------------------------------------------------

_workflows: dict[str, PayoutWorkflow] = {}
_postgres_store: Any = None


def set_workflow_store(postgres: Any) -> None:
    """Attach Postgres client for workflow persistence (Phase 3)."""
    global _postgres_store
    _postgres_store = postgres


async def persist_workflow(wf: PayoutWorkflow) -> None:
    """Save workflow to Postgres if store is configured."""
    if _postgres_store is None:
        return
    await _postgres_store.save_workflow(
        payout_id=wf.payout_id,
        agent_id=wf.agent_id,
        amount_paise=wf.amount_paise,
        current_state=wf.state,  # type: ignore[attr-defined]
        history=wf.history,
    )


def create_workflow(
    payout_id: str = "",
    amount_paise: int = 0,
    agent_id: str = "",
) -> PayoutWorkflow:
    """Create and register a new payout workflow."""
    wf = PayoutWorkflow(payout_id=payout_id, amount_paise=amount_paise, agent_id=agent_id)
    _workflows[wf.payout_id] = wf
    return wf


def get_workflow(payout_id: str) -> PayoutWorkflow | None:
    """Retrieve an existing workflow by payout ID."""
    return _workflows.get(payout_id)


async def get_workflow_async(payout_id: str) -> PayoutWorkflow | None:
    """Load workflow from memory or hydrate from Postgres."""
    wf = _workflows.get(payout_id)
    if wf:
        return wf
    if _postgres_store is None:
        return None
    data = await _postgres_store.get_workflow(payout_id)
    if not data:
        return None
    wf = PayoutWorkflow(
        payout_id=data["payout_id"],
        amount_paise=data["amount_paise"],
        agent_id=data["agent_id"],
    )
    wf.history = data.get("history", [])
    # Restore state without replaying transitions
    if hasattr(wf, "state"):
        wf.state = data["current_state"]  # type: ignore[attr-defined]
    _workflows[payout_id] = wf
    return wf


def list_workflows(state: str | None = None) -> list[dict[str, Any]]:
    """List all in-memory workflows, optionally filtered by state."""
    results = []
    for wf in _workflows.values():
        if state and wf.state != state:  # type: ignore[attr-defined]
            continue
        results.append(wf.get_status())
    return results


async def list_workflows_async(state: str | None = None) -> list[dict[str, Any]]:
    """List workflows from Postgres when available, else in-memory."""
    if _postgres_store is not None:
        persisted = await _postgres_store.list_workflows(state)
        if persisted:
            return persisted
    return list_workflows(state)
