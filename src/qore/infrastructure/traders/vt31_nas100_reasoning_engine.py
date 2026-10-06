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

from dataclasses import dataclass, replace
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
TargetPlan = Literal["PRIMARY_STRUCTURAL_BOUNDARY"]

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
    cognitive_domains_consulted: tuple[str, ...] = ()
    max_intelligence_blockers: tuple[str, ...] = ()
    max_intelligence_ready: bool = False


def _max_intelligence_audit(
    state: Nas100SituationModel,
    *,
    journey_capacity_state: str,
    management_context_state: str,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Audit cognitive completeness without changing the current trade action."""

    domains = (
        "strategy_identity",
        "prior_day_context",
        "h4_context",
        "h1_context",
        "m15_context",
        "m1_microstructure",
        "structure",
        "liquidity",
        "regime",
        "volatility",
        "timing_freshness",
        "entry_intelligence",
        "risk_geometry",
        "journey_intelligence",
        "target_exit_intelligence",
        "cibo_market_memory",
        "trader_experience_memory",
        "cross_index_context",
        "post_entry_reassessment_capability",
        "strategy_native_r_capability",
    )
    blockers: list[str] = []

    if state.m15_state.upper() in {"UNWIRED", ""}:
        blockers.append("M15_CONTEXT_UNWIRED")
    if state.h1_state == "unavailable":
        blockers.append("H1_CONTEXT_UNAVAILABLE")
    if state.last_structure_event_family in {"", "unavailable"}:
        blockers.append("STRUCTURE_CONTEXT_UNAVAILABLE")
    if state.volatility_state in {"", "unavailable"}:
        blockers.append("VOLATILITY_CONTEXT_UNAVAILABLE")
    if state.entry_evidence_family in {"", "unavailable"}:
        blockers.append("ENTRY_INTELLIGENCE_UNAVAILABLE")
    if "DEEPER_DOL_RESEARCH_UNCALIBRATED" in journey_capacity_state:
        blockers.append("DEEPER_JOURNEY_CAPACITY_UNCALIBRATED")
    if management_context_state.startswith("UNRESOLVED"):
        blockers.append("CONTEXTUAL_POSITION_MANAGEMENT_UNRESOLVED")

    unresolved_target_tokens = (
        "RESEARCH_ONLY",
        "UNCALIBRATED",
        "UNRESOLVED",
        "UNKNOWN",
    )
    if any(
        token in state.dol2_state.upper()
        for token in unresolved_target_tokens
    ):
        blockers.append("DOL2_TARGET_INTELLIGENCE_UNCALIBRATED")
    if any(
        token in state.dol3_state.upper()
        for token in unresolved_target_tokens
    ):
        blockers.append("DOL3_TARGET_INTELLIGENCE_UNCALIBRATED")

    return domains, tuple(blockers)


def _target_plan(state: Nas100SituationModel) -> TargetPlan:
    """Use the current candidate's structural destination.

    This candidate is structural by design. The sovereign certification rule
    still permits independently validated R-based or hybrid target policies.
    """
    _ = state
    return "PRIMARY_STRUCTURAL_BOUNDARY"


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
            f"M15:{state.m15_state}",
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
    if state.m15_state.upper() == "UNWIRED":
        uncertainty.append("SITUATION:M15_CONTEXT_UNWIRED")
    elif state.m15_state.lower() == "unavailable":
        uncertainty.append("SITUATION:M15_CONTEXT_UNAVAILABLE")
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

    # Post-entry journey capacity may become calibrated only from a causal
    # state produced by VT31's own closed-bar journey logic. Pre-entry remains
    # unresolved because future persistence is unknowable at admission.
    extension_state = state.extension_capacity_state.upper()
    if extension_state == "CALIBRATED_POST1R_CONTINUATION_SUPPORTED":
        journey_capacity_state = state.extension_capacity_state
        management_context_state = "CALIBRATED_POST1R_SUPPORTIVE"
        support.append("JOURNEY:POST1R_CONTINUATION_SUPPORTED")
    elif extension_state == "CALIBRATED_POST1R_CONTINUATION_WEAKENED":
        journey_capacity_state = state.extension_capacity_state
        management_context_state = "CALIBRATED_POST1R_MIXED"
        uncertainty.append("JOURNEY:POST1R_CONTINUATION_WEAKENED")
    elif extension_state == "CALIBRATED_POST1R_CONTINUATION_DEPLETED":
        journey_capacity_state = state.extension_capacity_state
        management_context_state = "CALIBRATED_POST1R_CAUTIOUS"
        contradictions.append("JOURNEY:POST1R_CONTINUATION_DEPLETED")
    else:
        journey_capacity_state = (
            "DOL1_STRUCTURAL_SUPPORTED__DEEPER_DOL_RESEARCH_UNCALIBRATED"
        )
        management_context_state = "UNRESOLVED_VT31_CONTEXTUAL_MANAGEMENT"

    experience_used.append("journey_capacity_memory")
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

    cognitive_domains, max_intelligence_blockers = _max_intelligence_audit(
        state,
        journey_capacity_state=journey_capacity_state,
        management_context_state=management_context_state,
    )

    if not strategy_used or not market_used or not experience_used:
        raise AssertionError(
            "VT31 partial cognition before EXECUTE/WAIT/ABSTAIN is forbidden"
        )

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
        cognitive_domains_consulted=cognitive_domains,
        max_intelligence_blockers=max_intelligence_blockers,
        max_intelligence_ready=not max_intelligence_blockers,
    )


# Admission predicates answer whether VT31 should create a *new* position.
# They remain useful observations after entry, but cannot by themselves
# invalidate a thesis that was already admitted causally.
_POSITION_NONBLOCKING_ADMISSION_CONTRADICTIONS = frozenset(
    {
        "SITUATION:NO_REFERENCE_LIQUIDITY_STATE_BY_CUTOFF",
        "SITUATION:CURRENT_PATH_NOT_COMPRESSED",
        "EXPERIENCE:CURRENT_SELECTED_STATE_TOO_LATE",
        "EXPERIENCE:NONCOMPRESSED_REFERENCE_OUTSIDE_LOW_DD_GATE",
    }
)

_POSITION_NONBLOCKING_ADMISSION_UNCERTAINTIES = frozenset(
    {
        "STRATEGY:SOURCE_CONFIRMATION_NOT_COMPLETE",
        "STRATEGY:ENTRY_EVIDENCE_NOT_ACTIONABLE",
        "SITUATION:REFERENCE_LIQUIDITY_STATE_NOT_YET_PRESENT",
        "EXPERIENCE:SEQUENCE_STALE_8_14_REQUIRES_REEVALUATION",
    }
)


_POSITION_NONBLOCKING_ADMISSION_SUPPORT = frozenset(
    {
        "EXPERIENCE:LOW_DD_COMPRESSED_REFERENCE_CORE",
        "EXPERIENCE:LOW_DD_NONCOMPRESSED_SHORT_H1_MIXED",
    }
)


def reason_position(
    state: Nas100SituationModel,
    *,
    frozen_entry_reasoning: Nas100ReasoningDecision,
) -> Nas100ReasoningDecision:
    """Reassess a live VT31 position with the full current cognition.

    The frozen entry decision proves that the trade was valid when admitted.
    Current structure/regime/liquidity/journey information is re-read in full,
    while predicates that only answer "would I open a *new* trade now?" are
    demoted to observations instead of being treated as exit authority.

    Position-authoritative contradictions (for example calibrated journey
    depletion) remain contradictions and can make the current reasoning
    cautious/abstaining.
    """

    if frozen_entry_reasoning.action != "EXECUTE":
        raise ValueError(
            "position reasoning requires a frozen EXECUTE entry decision"
        )

    raw = reason(state)

    admission_only_contradictions = tuple(
        code
        for code in raw.contradictions
        if code in _POSITION_NONBLOCKING_ADMISSION_CONTRADICTIONS
    )
    position_contradictions = tuple(
        code
        for code in raw.contradictions
        if code not in _POSITION_NONBLOCKING_ADMISSION_CONTRADICTIONS
    )
    admission_only_uncertainties = tuple(
        code
        for code in raw.uncertainty
        if code in _POSITION_NONBLOCKING_ADMISSION_UNCERTAINTIES
    )
    position_uncertainties = tuple(
        code
        for code in raw.uncertainty
        if code not in _POSITION_NONBLOCKING_ADMISSION_UNCERTAINTIES
    )
    admission_only_support = tuple(
        code
        for code in raw.supporting_evidence
        if code in _POSITION_NONBLOCKING_ADMISSION_SUPPORT
    )
    position_support = tuple(
        code
        for code in raw.supporting_evidence
        if code not in _POSITION_NONBLOCKING_ADMISSION_SUPPORT
    )

    context = list(raw.context_observations)
    context.append(
        f"POSITION:ENTRY_ACTION_FROZEN={frozen_entry_reasoning.action}"
    )
    context.extend(
        f"POSITION:ADMISSION_ONLY_CONTRADICTION={code}"
        for code in admission_only_contradictions
    )
    context.extend(
        f"POSITION:ADMISSION_ONLY_UNCERTAINTY={code}"
        for code in admission_only_uncertainties
    )
    context.extend(
        f"POSITION:ADMISSION_ONLY_SUPPORT={code}"
        for code in admission_only_support
    )

    # WAIT is an admission state. Once a position exists, current uncertainty
    # is represented in cognition/support-vs-caution rather than pretending the
    # already-open trade is waiting to be admitted.
    action: Action = "ABSTAIN" if position_contradictions else "EXECUTE"

    return replace(
        raw,
        action=action,
        supporting_evidence=position_support,
        contradictions=position_contradictions,
        uncertainty=position_uncertainties,
        context_observations=tuple(context),
    )
