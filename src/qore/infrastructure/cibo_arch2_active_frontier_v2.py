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
                "POST_FREEZE_EXPLICIT_TERMINAL_REASON_POPULATION_THEN_"
                "CIBO_ARCH2_T02_PROVIDER_BOUND_ECONOMIC_ABLATION_V1"
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
            state=Architect2ActiveState.FROZEN_GATE_WAITING_POPULATION,
            remaining_requirement=(
                "FRESH_OOS_GROSS_EDGE_VALIDATION_AND_"
                "MIN_VOLUME_MICROBUNDLE_MARKET_IMPACT_CALIBRATION"
            ),
        ),
        Architect2ActiveFront(
            workstream_id="T16",
            state=Architect2ActiveState.FROZEN_GATE_WAITING_POPULATION,
            remaining_requirement=(
                "POST_FREEZE_NAS100_US30_US500_M1_POPULATION_32_PLUS_"
                "THEN_STRICT_4_OF_4_HEDGE_UTILITY"
            ),
        ),
        Architect2ActiveFront(
            workstream_id="T20",
            state=Architect2ActiveState.WAITING_ON_AUTHORITATIVE_FORWARD_LIFECYCLE,
            remaining_requirement=(
                "REAL_CIBO_TO_RISK_TO_EXECUTION_TO_SETTLEMENT_TO_RELEASE_POPULATION"
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
