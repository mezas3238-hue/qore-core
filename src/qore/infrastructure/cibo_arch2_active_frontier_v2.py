"""Current non-overlapping Architect-2 closure frontier for Integrator intake."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from qore.infrastructure.cibo_arch2_active_scope_v2 import (
    ARCHITECT2_ACTIVE_OWNERSHIP,
)


class Architect2ActiveState(StrEnum):
    TERMINAL_RECOMMENDATION_READY = "TERMINAL_RECOMMENDATION_READY"
    PARTIAL_EVIDENCE_READY = "PARTIAL_EVIDENCE_READY"
    FROZEN_GATE_WAITING_POPULATION = "FROZEN_GATE_WAITING_POPULATION"
    WAITING_ON_AUTHORITATIVE_FORWARD_LIFECYCLE = (
        "WAITING_ON_AUTHORITATIVE_FORWARD_LIFECYCLE"
    )
    WAITING_ON_INTEGRATOR_RECEIPT = "WAITING_ON_INTEGRATOR_RECEIPT"


@dataclass(frozen=True, slots=True)
class Architect2ActiveFront:
    workstream_id: str
    state: Architect2ActiveState
    remaining_requirement: str
    proposed_terminal_disposition: str | None = None
    canonical_ledger_modified: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if self.workstream_id not in ARCHITECT2_ACTIVE_OWNERSHIP:
            raise ValueError("Architect-2 active frontier ownership drift")
        if (
            self.state is Architect2ActiveState.TERMINAL_RECOMMENDATION_READY
            and self.proposed_terminal_disposition is None
        ):
            raise ValueError("terminal recommendation requires disposition")
        if (
            self.state is not Architect2ActiveState.TERMINAL_RECOMMENDATION_READY
            and self.proposed_terminal_disposition is not None
        ):
            raise ValueError("non-terminal front cannot carry terminal disposition")
        if self.canonical_ledger_modified or self.productive_authority:
            raise ValueError("Architect-2 active frontier exceeded authority")


def architect2_active_frontier_v2() -> tuple[Architect2ActiveFront, ...]:
    rows = (
        Architect2ActiveFront(
            workstream_id="T02",
            state=Architect2ActiveState.WAITING_ON_AUTHORITATIVE_FORWARD_LIFECYCLE,
            remaining_requirement=(
                "LIFECYCLE_INTAKE_READY__POST_FREEZE_EXPLICIT_TERMINAL_REASON_"
                "POPULATION_THEN_PROVIDER_BOUND_ECONOMIC_ABLATION"
            ),
        ),
        Architect2ActiveFront(
            workstream_id="T03",
            state=Architect2ActiveState.TERMINAL_RECOMMENDATION_READY,
            remaining_requirement="INTEGRATOR_EVIDENCE_AUDIT",
            proposed_terminal_disposition="FALSIFIED_AND_CLOSED",
        ),
        Architect2ActiveFront(
            workstream_id="T11",
            state=Architect2ActiveState.PARTIAL_EVIDENCE_READY,
            remaining_requirement=(
                "AUTHORIZED_FORWARD_MANIFEST_FOR_GROSS_EDGE_PLUS_"
                "FROZEN_144_EPISODE_216_CHILD_MARKET_IMPACT_RUN_"
                "36945327912_IN_PROGRESS"
            ),
        ),
        Architect2ActiveFront(
            workstream_id="T16",
            state=Architect2ActiveState.TERMINAL_RECOMMENDATION_READY,
            remaining_requirement="INTEGRATOR_EVIDENCE_AUDIT",
            proposed_terminal_disposition="FALSIFIED_AND_CLOSED",
        ),
        Architect2ActiveFront(
            workstream_id="T20",
            state=Architect2ActiveState.WAITING_ON_AUTHORITATIVE_FORWARD_LIFECYCLE,
            remaining_requirement=(
                "QUALIFIER_READY__REAL_CIBO_TO_RISK_TO_EXECUTION_TO_SETTLEMENT_"
                "TO_RELEASE_POPULATION"
            ),
        ),
        Architect2ActiveFront(
            workstream_id="PROVIDER_ECONOMICS",
            state=Architect2ActiveState.TERMINAL_RECOMMENDATION_READY,
            remaining_requirement="INTEGRATOR_EVIDENCE_AUDIT",
            proposed_terminal_disposition="SUPERSEDED_WITH_PROVEN_LINEAGE",
        ),
        Architect2ActiveFront(
            workstream_id="FORWARD_QUALIFICATION",
            state=Architect2ActiveState.TERMINAL_RECOMMENDATION_READY,
            remaining_requirement="INTEGRATOR_EVIDENCE_AUDIT",
            proposed_terminal_disposition="SUPERSEDED_WITH_PROVEN_LINEAGE",
        ),
        Architect2ActiveFront(
            workstream_id="FRESH_OOS",
            state=Architect2ActiveState.WAITING_ON_INTEGRATOR_RECEIPT,
            remaining_requirement="AUTHORIZED_PHASE22_V2_FRESH_OUTCOME_RECEIPT",
        ),
    )
    if tuple(item.workstream_id for item in rows) != ARCHITECT2_ACTIVE_OWNERSHIP:
        raise ValueError("Architect-2 active frontier order/surface drift")
    return rows
