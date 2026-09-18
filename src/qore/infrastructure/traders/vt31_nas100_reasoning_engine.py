"""Deterministic three-memory reasoning engine for VT31_NAS100.

The engine combines:
- Long-Term Semantic Memory: internalized CIBO NAS100 knowledge;
- Episodic/Research Memory: lessons from VT31 development;
- Working Memory: causal state of the market now.

There is no runtime CIBO query.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from qore.infrastructure.traders.vt31_nas100_cognitive_memory import (
    memory_fingerprint,
)
from qore.infrastructure.traders.vt31_nas100_episodic_memory import (
    episodic_memory_fingerprint,
    episodic_memory_payload,
)
from qore.infrastructure.traders.vt31_nas100_long_term_memory import (
    long_term_memory_fingerprint,
    long_term_memory_payload,
)
from qore.infrastructure.traders.vt31_nas100_working_memory import (
    Nas100WorkingMemory,
)

Action = Literal["EXECUTE", "WAIT", "ABSTAIN"]
TargetPlan = Literal[
    "FULL_STRUCTURAL_BOUNDARY",
    "PARTIAL_1_25R_PLUS_BOUNDARY_RUNNER",
]

Nas100ReasoningState = Nas100WorkingMemory


@dataclass(frozen=True, slots=True)
class Nas100ReasoningDecision:
    action: Action
    target_plan: TargetPlan
    thesis: str
    supporting_evidence: tuple[str, ...]
    contradictions: tuple[str, ...]
    uncertainty: tuple[str, ...]
    long_term_memory_used: tuple[str, ...]
    episodic_memory_used: tuple[str, ...]
    working_memory_fingerprint: str
    long_term_memory_fingerprint: str
    episodic_memory_fingerprint: str
    memory_fingerprint: str


def reason(state: Nas100WorkingMemory) -> Nas100ReasoningDecision:
    """Interpret current causal state through all three memory stores."""
    long_term = long_term_memory_payload()
    episodic = episodic_memory_payload()

    structure_knowledge = long_term["structure_knowledge"]
    sequence_knowledge = long_term["sequence_knowledge"]
    destination_knowledge = long_term["destination_knowledge"]
    supported = episodic["supported_mechanisms"]
    rejected = episodic["rejected_hypotheses"]

    assert isinstance(structure_knowledge, dict)
    assert isinstance(sequence_knowledge, dict)
    assert isinstance(destination_knowledge, dict)
    assert isinstance(supported, dict)
    assert isinstance(rejected, dict)

    support: list[str] = []
    contradictions: list[str] = []
    uncertainty: list[str] = []
    long_term_used: list[str] = []
    episodic_used: list[str] = []

    if state.last_structure_event_family == "reference-liquidity-sweep":
        support.append("LONG_TERM:REFERENCE_LIQUIDITY_STATE_SUPPORTED")
        long_term_used.append("structure_knowledge")
        episodic_used.append("reference_liquidity_state")
    else:
        contradictions.append("LATEST_STRUCTURE_NOT_REFERENCE_LIQUIDITY_SWEEP")
        long_term_used.append("structure_knowledge")

    path_compressed = (
        state.current_path_vs_previous is not None
        and state.current_path_vs_previous < Decimal("0.75")
    )
    if path_compressed:
        support.append("WORKING:CURRENT_PATH_COMPRESSION_PRESENT")
        episodic_used.append("context_required")
    else:
        contradictions.append("WORKING:CURRENT_PATH_COMPRESSION_ABSENT")
        episodic_used.append("context_required")

    reclaim_age = state.reference_reclaim_age_minutes
    stale = reclaim_age is not None and 8 <= reclaim_age < 15
    if stale:
        contradictions.append("EPISODIC:SEQUENCE_FRESHNESS_STALE_8_14")
        long_term_used.append("sequence_knowledge")
        episodic_used.append("sequence_freshness")
    elif reclaim_age is None:
        uncertainty.append("WORKING:REFERENCE_RECLAIM_AGE_UNAVAILABLE")
        long_term_used.append("sequence_knowledge")
    else:
        support.append("WORKING:SEQUENCE_NOT_IN_KNOWN_STALE_8_14_STATE")
        long_term_used.append("sequence_knowledge")
        episodic_used.append("sequence_freshness")

    if state.decision_minute_ny >= 10 * 60 + 30:
        contradictions.append("WORKING:COMPRESSED_REFERENCE_SWEEP_STATE_TOO_LATE")

    reference_compressed = (
        state.reference_width_vs_prior5 is not None
        and state.reference_width_vs_prior5 < Decimal("0.75")
    )
    target_plan: TargetPlan = (
        "FULL_STRUCTURAL_BOUNDARY"
        if reference_compressed
        else "PARTIAL_1_25R_PLUS_BOUNDARY_RUNNER"
    )
    long_term_used.append("destination_knowledge")
    episodic_used.append("dynamic_destination_management")
    episodic_used.append("universal_target_plan")

    if state.reference_width_vs_prior5 is None:
        uncertainty.append("WORKING:REFERENCE_VOLATILITY_UNAVAILABLE")

    hard_block = bool(contradictions)
    action: Action = "ABSTAIN" if hard_block else "EXECUTE"

    return Nas100ReasoningDecision(
        action=action,
        target_plan=target_plan,
        thesis="REVERSAL_DELIVERY_TOWARD_OPPOSITE_09_REFERENCE_BOUNDARY",
        supporting_evidence=tuple(support),
        contradictions=tuple(contradictions),
        uncertainty=tuple(uncertainty),
        long_term_memory_used=tuple(dict.fromkeys(long_term_used)),
        episodic_memory_used=tuple(dict.fromkeys(episodic_used)),
        working_memory_fingerprint=state.fingerprint(),
        long_term_memory_fingerprint=long_term_memory_fingerprint(),
        episodic_memory_fingerprint=episodic_memory_fingerprint(),
        memory_fingerprint=memory_fingerprint(),
    )
