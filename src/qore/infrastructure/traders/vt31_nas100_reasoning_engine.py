"""Deterministic reasoning engine for the NAS100 VT31 specialist.

The engine reasons from current causal market state plus the specialist's
internalized cognitive memory.  It never calls CIBO at runtime.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from qore.infrastructure.traders.vt31_nas100_cognitive_memory import (
    memory_fingerprint,
    memory_payload,
)

Action = Literal["EXECUTE", "WAIT", "ABSTAIN"]
TargetPlan = Literal[
    "FULL_STRUCTURAL_BOUNDARY",
    "PARTIAL_1_25R_PLUS_BOUNDARY_RUNNER",
]


@dataclass(frozen=True, slots=True)
class Nas100ReasoningState:
    decision_minute_ny: int
    last_structure_event_family: str
    last_structure_event_age_minutes: int | None
    reference_reclaim_age_minutes: int | None
    current_path_vs_previous: Decimal | None
    reference_width_vs_prior5: Decimal | None


@dataclass(frozen=True, slots=True)
class Nas100ReasoningDecision:
    action: Action
    target_plan: TargetPlan
    thesis: str
    supporting_evidence: tuple[str, ...]
    contradictions: tuple[str, ...]
    uncertainty: tuple[str, ...]
    memory_fingerprint: str


def reason(state: Nas100ReasoningState) -> Nas100ReasoningDecision:
    """Interpret a causal market state using embedded CIBO/lab memory."""
    memory = memory_payload()
    lab = memory["laboratory_memory"]
    assert isinstance(lab, dict)

    support: list[str] = []
    contradictions: list[str] = []
    uncertainty: list[str] = []

    if state.last_structure_event_family == "reference-liquidity-sweep":
        support.append("MEMORY:REFERENCE_LIQUIDITY_STATE_SUPPORTED")
    else:
        contradictions.append("LATEST_STRUCTURE_NOT_REFERENCE_LIQUIDITY_SWEEP")

    path_compressed = (
        state.current_path_vs_previous is not None
        and state.current_path_vs_previous < Decimal("0.75")
    )
    if path_compressed:
        support.append("CURRENT_PATH_COMPRESSION_PRESENT")
    else:
        contradictions.append("CURRENT_PATH_COMPRESSION_ABSENT")

    reclaim_age = state.reference_reclaim_age_minutes
    stale = reclaim_age is not None and 8 <= reclaim_age < 15
    if stale:
        contradictions.append("MEMORY:SEQUENCE_FRESHNESS_STALE_8_14")
    elif reclaim_age is None:
        uncertainty.append("REFERENCE_RECLAIM_AGE_UNAVAILABLE")
    else:
        support.append("SEQUENCE_NOT_IN_KNOWN_STALE_8_14_STATE")

    if state.decision_minute_ny >= 10 * 60 + 30:
        contradictions.append("COMPRESSED_REFERENCE_SWEEP_STATE_TOO_LATE")

    reference_compressed = (
        state.reference_width_vs_prior5 is not None
        and state.reference_width_vs_prior5 < Decimal("0.75")
    )
    target_plan: TargetPlan = (
        "FULL_STRUCTURAL_BOUNDARY"
        if reference_compressed
        else "PARTIAL_1_25R_PLUS_BOUNDARY_RUNNER"
    )

    if state.reference_width_vs_prior5 is None:
        uncertainty.append("REFERENCE_VOLATILITY_MEMORY_UNAVAILABLE")

    hard_block = bool(contradictions)
    action: Action = "ABSTAIN" if hard_block else "EXECUTE"

    return Nas100ReasoningDecision(
        action=action,
        target_plan=target_plan,
        thesis="REVERSAL_DELIVERY_TOWARD_OPPOSITE_09_REFERENCE_BOUNDARY",
        supporting_evidence=tuple(support),
        contradictions=tuple(contradictions),
        uncertainty=tuple(uncertainty),
        memory_fingerprint=memory_fingerprint(),
    )
