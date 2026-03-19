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
# Module-level workflow registry
# ---------------------------------------------------------------------------

_workflows: dict[str, PayoutWorkflow] = {}


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


def list_workflows(state: str | None = None) -> list[dict[str, Any]]:
    """List all workflows, optionally filtered by state."""
    results = []
    for wf in _workflows.values():
        if state and wf.state != state:  # type: ignore[attr-defined]
            continue
        results.append(wf.get_status())
    return results
