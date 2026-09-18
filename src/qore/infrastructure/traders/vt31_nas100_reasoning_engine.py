"""Deterministic pre-trade reasoning engine for VT31_NAS100.

Architecture:
Strategy Identity Memory
+ governed CIBO Market Memory
+ Trader Experience / Lab Memory
+ current causal Situation Model
-> reasoning
-> ENTER / WAIT / ABSTAIN
-> destination / management intent.

CIBO aggregate associations inform reasoning but cannot independently promote a
runtime rule. The current economic policy is deliberately preserved while the
new journey-capacity and contextual-management layers are researched on
consumed evidence.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from qore.infrastructure.traders.vt31_nas100_cibo_market_memory import (
    cibo_market_memory_fingerprint,
    dossier_runtime_view,
)
from qore.infrastructure.traders.vt31_nas100_cognitive_memory import (
    memory_fingerprint,
)
from qore.infrastructure.traders.vt31_nas100_situation_model import (
    Nas100SituationModel,
)
from qore.infrastructure.traders.vt31_nas100_strategy_identity_memory import (
    strategy_identity_fingerprint,
    strategy_identity_runtime_view,
)
from qore.infrastructure.traders.vt31_nas100_trader_experience_memory import (
    trader_experience_fingerprint,
    trader_experience_runtime_view,
)

Action = Literal["EXECUTE", "WAIT", "ABSTAIN"]
TargetPlan = Literal[
    "FULL_STRUCTURAL_BOUNDARY",
    "PARTIAL_1_25R_PLUS_BOUNDARY_RUNNER",
]

Nas100ReasoningState = Nas100SituationModel


@dataclass(frozen=True, slots=True)
class Nas100ReasoningDecision:
    action: Action
    target_plan: TargetPlan
    thesis: str
    journey_capacity_state: str
    management_context_state: str
    supporting_evidence: tuple[str, ...]
    contradictions: tuple[str, ...]
    uncertainty: tuple[str, ...]
    context_observations: tuple[str, ...]
    strategy_memory_used: tuple[str, ...]
    cibo_market_memory_used: tuple[str, ...]
    trader_experience_memory_used: tuple[str, ...]
    situation_fingerprint: str
    strategy_memory_fingerprint: str
    cibo_market_memory_fingerprint: str
    trader_experience_memory_fingerprint: str
    memory_fingerprint: str


def _target_plan(state: Nas100SituationModel) -> TargetPlan:
    reference_compressed = (
        state.reference_width_vs_prior5 is not None
        and state.reference_width_vs_prior5 < Decimal("0.75")
    )
    return (
        "FULL_STRUCTURAL_BOUNDARY"
        if reference_compressed
        else "PARTIAL_1_25R_PLUS_BOUNDARY_RUNNER"
    )


def reason(state: Nas100SituationModel) -> Nas100ReasoningDecision:
    """Reason from the three memories before constructing the operation."""
    strategy = strategy_identity_runtime_view()
    market = dossier_runtime_view()
    experience = trader_experience_runtime_view()
    source_identity = strategy["source_identity"]
    supported_mechanisms = experience["supported_mechanisms"]
    rejected_hypotheses = experience["rejected_hypotheses"]
    assert isinstance(source_identity, dict)
    assert isinstance(supported_mechanisms, dict)
    assert isinstance(rejected_hypotheses, dict)

    support: list[str] = []
    contradictions: list[str] = []
    uncertainty: list[str] = []
    context_observations: list[str] = []
    strategy_used: list[str] = []
    market_used: list[str] = []
    experience_used: list[str] = []

    # Strategy Identity is the first authority: the market brain cannot turn a
    # non-VT31 event into VT31.
    strategy_used.extend(
        [
            "source_identity",
            "invalidation_identity",
            "destination_identity",
            "lifecycle",
        ]
    )
    if state.confirmation_state != "confirmed":
        uncertainty.append("STRATEGY:SOURCE_CONFIRMATION_NOT_COMPLETE")
    if state.entry_evidence_family not in {
        "breaker",
        "fair-value-gap",
        "order-block",
    }:
        uncertainty.append("STRATEGY:ENTRY_EVIDENCE_NOT_ACTIONABLE")

    # General CIBO memory informs what a NAS100 journey historically looks like.
    journey = market["journey_memory"]
    target_memory = market["target_destination_memory"]
    structure_memory = market["structure_memory"]
    market_used.extend(
        [
            "journey_memory",
            "structure_memory",
            "target_destination_memory",
            "by_weekday",
        ]
    )
    assert isinstance(journey, dict)
    assert isinstance(target_memory, dict)
    assert isinstance(structure_memory, dict)

    # Higher context is observed and retained without being promoted to a
    # standalone entry prohibition. Its operational meaning must be learned
    # conjunctively on consumed NAS100 evidence.
    context_observations.extend(
        [
            f"PRIOR_DAY:{state.prior_day_state}",
            f"H4:{state.h4_state}",
            f"H1:{state.h1_state}",
            f"PREMARKET:{state.premarket_state}",
            f"CASH_OPEN:{state.cash_open_state}",
            f"PRIOR_RANGE_LOCATION:{state.position_in_prior_day_range}",
            f"RANGE_STATE:{state.range_state}",
            f"VOLATILITY_STATE:{state.volatility_state}",
            (
                "RAID_DEPTH_REF:unavailable"
                if state.raid_depth_ref is None
                else f"RAID_DEPTH_REF:{state.raid_depth_ref}"
            ),
            (
                "RECENT_PATH_EFFICIENCY:unavailable"
                if state.recent_path_efficiency is None
                else f"RECENT_PATH_EFFICIENCY:{state.recent_path_efficiency}"
            ),
            (
                "RECENT_OVERLAP_RATE:unavailable"
                if state.recent_overlap_rate is None
                else f"RECENT_OVERLAP_RATE:{state.recent_overlap_rate}"
            ),
        ]
    )
    if state.h4_state == "unavailable":
        uncertainty.append("SITUATION:H4_CONTEXT_UNAVAILABLE")
    if state.h1_state == "unavailable":
        uncertainty.append("SITUATION:H1_CONTEXT_UNAVAILABLE")
    if state.prior_day_state == "unavailable":
        uncertainty.append("SITUATION:PRIOR_DAY_CONTEXT_UNAVAILABLE")

    # Trader Experience says the latest reference-liquidity event, compression,
    # and freshness are meaningful jointly. They are not promoted independently.
    if state.last_structure_event_family == "reference-liquidity-sweep":
        support.append("CIBO:REFERENCE_LIQUIDITY_EVENT_OBSERVED")
        experience_used.append("reference_liquidity_context")
    elif state.decision_minute_ny < 10 * 60 + 30:
        uncertainty.append("SITUATION:REFERENCE_LIQUIDITY_STATE_NOT_YET_PRESENT")
    else:
        contradictions.append("SITUATION:NO_REFERENCE_LIQUIDITY_STATE_BY_CUTOFF")

    if state.current_path_vs_previous is None:
        uncertainty.append("SITUATION:PATH_VOLATILITY_CONTEXT_UNAVAILABLE")
    elif state.current_path_vs_previous < Decimal("0.75"):
        support.append("SITUATION:CURRENT_PATH_COMPRESSED")
        experience_used.append("context_is_multidimensional")
    else:
        contradictions.append("SITUATION:CURRENT_PATH_NOT_COMPRESSED")
        experience_used.append("context_is_multidimensional")

    reclaim_age = state.reference_reclaim_age_minutes
    stale = reclaim_age is not None and 8 <= reclaim_age < 15
    if stale:
        uncertainty.append("EXPERIENCE:SEQUENCE_STALE_8_14_REQUIRES_REEVALUATION")
        experience_used.append("sequence_freshness")
    elif reclaim_age is None:
        uncertainty.append("SITUATION:REFERENCE_RECLAIM_AGE_UNAVAILABLE")
    else:
        support.append("SITUATION:SEQUENCE_OUTSIDE_KNOWN_STALE_8_14_STATE")
        experience_used.append("sequence_freshness")

    if state.decision_minute_ny >= 10 * 60 + 30:
        contradictions.append("EXPERIENCE:CURRENT_SELECTED_STATE_TOO_LATE")

    # Weekday is remembered as association-only context, never a prohibition.
    weekday_table = market.get("by_weekday")
    if isinstance(weekday_table, dict) and state.weekday in weekday_table:
        support.append("CIBO:WEEKDAY_CONTEXT_AVAILABLE_ASSOCIATION_ONLY")
        market_used.append(f"by_weekday.{state.weekday}")

    reference_compressed = state.volatility_state == "compressed"
    noncompressed_low_dd_fallback = (
        state.side == "short" and state.h1_state == "mixed"
    )
    experience_used.append("low_dd_reference_gate")
    if reference_compressed:
        support.append("EXPERIENCE:LOW_DD_COMPRESSED_REFERENCE_CORE")
    elif noncompressed_low_dd_fallback:
        support.append("EXPERIENCE:LOW_DD_NONCOMPRESSED_SHORT_H1_MIXED")
    else:
        contradictions.append(
            "EXPERIENCE:NONCOMPRESSED_REFERENCE_OUTSIDE_LOW_DD_GATE"
        )

    plan = _target_plan(state)
    experience_used.append("dynamic_destination_management")
    experience_used.append("universal_partial_runner")
    if state.reference_width_vs_prior5 is None:
        uncertainty.append("SITUATION:REFERENCE_VOLATILITY_CONTEXT_UNAVAILABLE")

    # Capacity memory currently supports DOL1 as structural destination and
    # aggregate extension priors. It is not yet calibrated enough to authorize
    # deeper DOL ranks, so deeper capacity remains explicitly unresolved.
    journey_capacity_state = (
        "DOL1_STRUCTURAL_SUPPORTED__DEEPER_DOL_RESEARCH_UNCALIBRATED"
    )
    experience_used.append("journey_capacity_memory")

    # Do not copy Turtle Soup SUPPORTIVE/MIXED/CAUTIOUS thresholds. VT31 must
    # learn its own management-state mapping first.
    management_context_state = "UNRESOLVED_VT31_CONTEXTUAL_MANAGEMENT"
    experience_used.append("contextual_position_management")

    transient_wait = any(
        reason_code in uncertainty
        for reason_code in (
            "STRATEGY:SOURCE_CONFIRMATION_NOT_COMPLETE",
            "STRATEGY:ENTRY_EVIDENCE_NOT_ACTIONABLE",
            "SITUATION:REFERENCE_LIQUIDITY_STATE_NOT_YET_PRESENT",
            "EXPERIENCE:SEQUENCE_STALE_8_14_REQUIRES_REEVALUATION",
        )
    )
    if contradictions:
        action: Action = "ABSTAIN"
    elif transient_wait:
        action = "WAIT"
    else:
        action = "EXECUTE"

    return Nas100ReasoningDecision(
        action=action,
        target_plan=plan,
        thesis="REVERSAL_DELIVERY_TOWARD_OPPOSITE_09_REFERENCE_BOUNDARY",
        journey_capacity_state=journey_capacity_state,
        management_context_state=management_context_state,
        supporting_evidence=tuple(support),
        contradictions=tuple(contradictions),
        uncertainty=tuple(uncertainty),
        context_observations=tuple(context_observations),
        strategy_memory_used=tuple(dict.fromkeys(strategy_used)),
        cibo_market_memory_used=tuple(dict.fromkeys(market_used)),
        trader_experience_memory_used=tuple(dict.fromkeys(experience_used)),
        situation_fingerprint=state.fingerprint(),
        strategy_memory_fingerprint=strategy_identity_fingerprint(),
        cibo_market_memory_fingerprint=cibo_market_memory_fingerprint(),
        trader_experience_memory_fingerprint=trader_experience_fingerprint(),
        memory_fingerprint=memory_fingerprint(),
    )
