"""Architect-2 exhaustive closure frontier for the 43 assigned workstreams.

The frontier is a governance/checkpoint artifact.  It guarantees that every
Architect-2-owned workstream has exactly one explained state and a concrete
next evidence dependency.  It does not mutate the canonical ledger.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Arch2ClosureState(StrEnum):
    TERMINAL_RECOMMENDATION_READY = "TERMINAL_RECOMMENDATION_READY"
    PARTIAL_EVIDENCE_READY = "PARTIAL_EVIDENCE_READY"
    FROZEN_GATE_WAITING_POPULATION = "FROZEN_GATE_WAITING_POPULATION"
    ACTIVE_PROVIDER_RESEARCH = "ACTIVE_PROVIDER_RESEARCH"
    WAITING_ON_INTEGRATOR_RECEIPT = "WAITING_ON_INTEGRATOR_RECEIPT"
    WAITING_ON_AUTHORITATIVE_FORWARD_LIFECYCLE = (
        "WAITING_ON_AUTHORITATIVE_FORWARD_LIFECYCLE"
    )
    WAITING_ON_UPSTREAM_AND_OWNER_REVIEW = (
        "WAITING_ON_UPSTREAM_AND_OWNER_REVIEW"
    )


@dataclass(frozen=True, slots=True)
class Arch2WorkstreamFrontier:
    workstream_id: str
    state: Arch2ClosureState
    next_dependency: str
    terminal_recommendation: str | None = None
    productive_authority: bool = False


ASSIGNED_WORKSTREAMS = (
    "T02", "T03", "T04", "T06", "T07", "T08", "T09", "T10", "T11",
    "T12", "T13", "T14", "T15", "T16", "T18", "T20",
    "GEN-C2", "GEN-C3", "GEN-C4", "GEN-C5", "GEN-C6", "GEN-C7",
    "GEN-C8", "GEN-C9", "GEN-C10", "GEN-C11", "GEN-C12", "GEN-C13",
    "GEN-C14", "COMPOUND_ENGINE", "COMPOUND_PORTFOLIO",
    "INTERNAL_CAPITAL_MARKET", "CAPITAL_GENERATIONS",
    "PROTECTED_BASE_CAPITAL", "PROFIT_PROTECTION", "PROVIDER_ECONOMICS",
    "FORWARD_QUALIFICATION", "PATH_DEPENDENT_MONTE_CARLO",
    "ADVERSARIAL_STRESS", "FRESH_OOS", "TEMPORAL_REPLICATION",
    "CAPITAL_AMPLIFICATION", "AS_IS_ECONOMIC_BASELINE",
)

_PHASE22_CAUSAL = (
    "AUTHORIZED_PHASE22_FRESH_OUTCOME_RECEIPT_WITH_CAUSAL_CONTROL_TREATMENT"
)
_PHASE22_FOUR_FOLD = (
    "AUTHORIZED_PHASE22_FRESH_OUTCOME_RECEIPT_WITH_WF1_WF2_WF3_WF4"
)
_INTEGRATED_CAPITAL = (
    "INTEGRATOR_INTEGRATED_CAPITAL_TRUTH_AND_SETTLED_COMPOUND_EPISODES"
)


def architect2_closure_frontier() -> tuple[Arch2WorkstreamFrontier, ...]:
    rows: dict[str, Arch2WorkstreamFrontier] = {}

    def add(
        workstream_id: str,
        state: Arch2ClosureState,
        next_dependency: str,
        terminal_recommendation: str | None = None,
    ) -> None:
        rows[workstream_id] = Arch2WorkstreamFrontier(
            workstream_id=workstream_id,
            state=state,
            next_dependency=next_dependency,
            terminal_recommendation=terminal_recommendation,
            productive_authority=False,
        )

    add(
        "PROVIDER_ECONOMICS",
        Arch2ClosureState.TERMINAL_RECOMMENDATION_READY,
        "INTEGRATOR_LEDGER_REVIEW",
        "SUPERSEDED_WITH_PROVEN_LINEAGE",
    )
    add(
        "FORWARD_QUALIFICATION",
        Arch2ClosureState.TERMINAL_RECOMMENDATION_READY,
        "INTEGRATOR_LEDGER_REVIEW",
        "SUPERSEDED_WITH_PROVEN_LINEAGE",
    )
    add(
        "T11",
        Arch2ClosureState.PARTIAL_EVIDENCE_READY,
        "FRESH_GROSS_EDGE_MODEL_AND_PROVIDER_BOUND_MULTI_VOLUME_MARKET_IMPACT",
    )
    add(
        "T16",
        Arch2ClosureState.FROZEN_GATE_WAITING_POPULATION,
        "POST_FREEZE_T16_FRESH_OOS_UTILITY_POPULATION_32_PLUS",
    )
    add(
        "T03",
        Arch2ClosureState.TERMINAL_RECOMMENDATION_READY,
        "INTEGRATOR_LEDGER_REVIEW",
        "FALSIFIED_AND_CLOSED",
    )
    add(
        "T20",
        Arch2ClosureState.WAITING_ON_AUTHORITATIVE_FORWARD_LIFECYCLE,
        "REAL_CIBO_RISK_EXECUTION_SETTLEMENT_RELEASE_LIFECYCLE",
    )
    add(
        "FRESH_OOS",
        Arch2ClosureState.WAITING_ON_INTEGRATOR_RECEIPT,
        "PHASE22_V2_FRESH_OUTCOME_RECEIPT_REQUIRED",
    )

    for workstream_id in ("T02", "T04", "T06", "T07", "T08", "T10", "T12", "T14", "T15"):
        add(
            workstream_id,
            Arch2ClosureState.WAITING_ON_INTEGRATOR_RECEIPT,
            _PHASE22_CAUSAL,
        )
    for workstream_id in ("T09", "T13", "T18"):
        add(
            workstream_id,
            Arch2ClosureState.WAITING_ON_INTEGRATOR_RECEIPT,
            _PHASE22_FOUR_FOLD,
        )

    for workstream_id in ("GEN-C2", "GEN-C3", "GEN-C4", "GEN-C5", "GEN-C6"):
        add(
            workstream_id,
            Arch2ClosureState.WAITING_ON_INTEGRATOR_RECEIPT,
            _INTEGRATED_CAPITAL,
        )
    for workstream_id in ("GEN-C7", "GEN-C8", "GEN-C9", "GEN-C10", "GEN-C11", "GEN-C12", "GEN-C13"):
        add(
            workstream_id,
            Arch2ClosureState.WAITING_ON_INTEGRATOR_RECEIPT,
            _PHASE22_FOUR_FOLD + "_PLUS_" + _INTEGRATED_CAPITAL,
        )
    add(
        "GEN-C14",
        Arch2ClosureState.WAITING_ON_UPSTREAM_AND_OWNER_REVIEW,
        "ALL_GEN_C_UPSTREAM_TERMINAL_PLUS_OWNER_REVIEW",
    )

    for workstream_id in (
        "COMPOUND_ENGINE",
        "COMPOUND_PORTFOLIO",
        "INTERNAL_CAPITAL_MARKET",
        "CAPITAL_GENERATIONS",
        "PATH_DEPENDENT_MONTE_CARLO",
        "ADVERSARIAL_STRESS",
        "TEMPORAL_REPLICATION",
        "CAPITAL_AMPLIFICATION",
    ):
        add(
            workstream_id,
            Arch2ClosureState.WAITING_ON_INTEGRATOR_RECEIPT,
            _INTEGRATED_CAPITAL + "_PLUS_" + _PHASE22_FOUR_FOLD,
        )

    for workstream_id in (
        "PROTECTED_BASE_CAPITAL",
        "PROFIT_PROTECTION",
        "AS_IS_ECONOMIC_BASELINE",
    ):
        add(
            workstream_id,
            Arch2ClosureState.WAITING_ON_INTEGRATOR_RECEIPT,
            _PHASE22_FOUR_FOLD,
        )

    ordered = tuple(rows[item] for item in ASSIGNED_WORKSTREAMS)
    if len(ordered) != 43 or len(rows) != 43:
        raise ValueError("Architect-2 closure frontier must explain exactly 43 workstreams")
    if any(item.productive_authority for item in ordered):
        raise ValueError("Architect-2 frontier cannot grant productive authority")
    return ordered
