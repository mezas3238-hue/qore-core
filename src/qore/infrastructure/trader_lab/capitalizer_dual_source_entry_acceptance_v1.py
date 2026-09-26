"""Strict ICT + TTrades entry-acceptance gate for QORE Capitalizer.

Authority:
1. ICT / Michael J. Huddleston supplies the original liquidity, time/context,
   market-structure-shift, displacement and FVG execution logic.
2. TTrades supplies a compatible secondary refinement through higher-timeframe
   closure, lower-timeframe CISD, protected swings and continuation structure.
3. QORE may operationalize detection, but may not waive a source condition.

This gate is intentionally fail-closed. It never scores or compensates for a missing
condition. An entry is acceptable only when every mandatory source condition is
confirmed causally before execution.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from qore.infrastructure.trader_lab.capitalizer_decision_sovereignty import (
    CapitalizerCognitiveGateDecision,
)

IDENTITY = "QORE_CAPITALIZER_ICT_TTRADES_ENTRY_ACCEPTANCE_V1"


class CapitalizerEntryAcceptanceState(StrEnum):
    ACCEPTABLE_FOR_QORE_RISK = "ACCEPTABLE_FOR_QORE_RISK"
    WAIT = "WAIT"
    REJECT = "REJECT"


@dataclass(frozen=True, slots=True)
class CapitalizerM1EntryStructureFacts:
    """Owner-frozen execution structure required on the M1 entry timeframe."""

    timeframe: str = "M1"
    market_structure_shift_confirmed: bool = False
    fair_value_gap_confirmed: bool = False
    order_block_confirmed: bool = False

    def __post_init__(self) -> None:
        if self.timeframe != "M1":
            raise ValueError("Capitalizer execution entry structure must be M1")

    @property
    def complete(self) -> bool:
        return (
            self.market_structure_shift_confirmed
            and self.fair_value_gap_confirmed
            and self.order_block_confirmed
        )


@dataclass(frozen=True, slots=True)
class CapitalizerDualSourceEntryFacts:
    cognitive_gate_decision: CapitalizerCognitiveGateDecision

    source_session_resolved: bool
    source_session_eligible: bool
    higher_timeframe_bias_confirmed_aligned: bool
    structural_target_intact: bool
    structural_stop_geometry_valid: bool

    ict_liquidity_reference_defined: bool
    ict_liquidity_raid_observed: bool
    ict_market_structure_shift_confirmed: bool
    ict_displacement_significant: bool
    ict_fvg_present_in_displacement: bool
    ict_entry_retrace_into_valid_pd_array: bool
    ict_entry_not_chasing: bool

    ttrades_htf_closure_at_poi_confirmed: bool
    ttrades_ltf_cisd_confirmed: bool
    ttrades_protected_swing_confirmed: bool
    ttrades_continuation_confirmed: bool
    ttrades_wick_formation_confirmed: bool

    m1_entry_structure: CapitalizerM1EntryStructureFacts | None = None
    contradictions: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class CapitalizerDualSourceEntryAcceptance:
    identity: str
    state: CapitalizerEntryAcceptanceState
    reasons: tuple[str, ...]
    all_mandatory_conditions_confirmed: bool
    passes_to_qore_risk: bool
    ict_original_primary: bool = True
    ttrades_secondary_refinement: bool = True
    qore_operationalization_only: bool = True
    numeric_score_used: bool = False
    outcome_aware: bool = False
    executes_trade: bool = False
    sizes_position: bool = False
    grants_capital_authority: bool = False

    def __post_init__(self) -> None:
        if self.identity != IDENTITY:
            raise ValueError("entry-acceptance identity is frozen")
        if not self.reasons:
            raise ValueError("entry acceptance requires explicit reasons")
        accepted = self.state is CapitalizerEntryAcceptanceState.ACCEPTABLE_FOR_QORE_RISK
        if accepted != self.all_mandatory_conditions_confirmed:
            raise ValueError("accepted entry must have all mandatory conditions confirmed")
        if accepted != self.passes_to_qore_risk:
            raise ValueError("QORE Risk handoff must match strict entry acceptance")
        if self.numeric_score_used or self.outcome_aware:
            raise ValueError("source entry gate cannot score or use future outcomes")
        if self.executes_trade or self.sizes_position or self.grants_capital_authority:
            raise ValueError("entry gate stops before QORE Risk/execution")


def assess_dual_source_entry(
    facts: CapitalizerDualSourceEntryFacts,
) -> CapitalizerDualSourceEntryAcceptance:
    """Require the full ICT + TTrades source sequence without compensating scores."""

    if facts.cognitive_gate_decision is CapitalizerCognitiveGateDecision.ABSTAIN:
        return CapitalizerDualSourceEntryAcceptance(
            identity=IDENTITY,
            state=CapitalizerEntryAcceptanceState.REJECT,
            reasons=("COGNITIVE_GATE_ABSTAIN",),
            all_mandatory_conditions_confirmed=False,
            passes_to_qore_risk=False,
        )
    if facts.cognitive_gate_decision is CapitalizerCognitiveGateDecision.WAIT:
        return CapitalizerDualSourceEntryAcceptance(
            identity=IDENTITY,
            state=CapitalizerEntryAcceptanceState.WAIT,
            reasons=("COGNITIVE_GATE_WAIT",),
            all_mandatory_conditions_confirmed=False,
            passes_to_qore_risk=False,
        )

    reject_reasons: list[str] = []
    if facts.contradictions:
        reject_reasons.extend(f"CONTRADICTION:{item}" for item in facts.contradictions)
    if facts.source_session_resolved and not facts.source_session_eligible:
        reject_reasons.append("OUTSIDE_SOURCE_SESSION_CONTEXT")
    if not facts.higher_timeframe_bias_confirmed_aligned:
        reject_reasons.append("HTF_BIAS_NOT_CONFIRMED_ALIGNED")
    if not facts.structural_target_intact:
        reject_reasons.append("STRUCTURAL_TARGET_NOT_INTACT")
    if not facts.structural_stop_geometry_valid:
        reject_reasons.append("STRUCTURAL_STOP_GEOMETRY_INVALID")
    if facts.ict_entry_retrace_into_valid_pd_array and not facts.ict_entry_not_chasing:
        reject_reasons.append("ICT_ENTRY_IS_CHASING_AFTER_FAVORABLE_AREA")

    if reject_reasons:
        return CapitalizerDualSourceEntryAcceptance(
            identity=IDENTITY,
            state=CapitalizerEntryAcceptanceState.REJECT,
            reasons=tuple(dict.fromkeys(reject_reasons)),
            all_mandatory_conditions_confirmed=False,
            passes_to_qore_risk=False,
        )

    wait_reasons: list[str] = []
    m1 = facts.m1_entry_structure
    if m1 is None:
        wait_reasons.append("M1_ENTRY_STRUCTURE_UNRESOLVED")
    else:
        if not m1.market_structure_shift_confirmed:
            wait_reasons.append("M1_MSS_NOT_CONFIRMED")
        if not m1.fair_value_gap_confirmed:
            wait_reasons.append("M1_FVG_NOT_CONFIRMED")
        if not m1.order_block_confirmed:
            wait_reasons.append("M1_ORDER_BLOCK_NOT_CONFIRMED")

    required = (
        ("SOURCE_SESSION_CONTEXT_UNRESOLVED", facts.source_session_resolved),
        ("ICT_LIQUIDITY_REFERENCE_UNDEFINED", facts.ict_liquidity_reference_defined),
        ("ICT_LIQUIDITY_RAID_NOT_OBSERVED", facts.ict_liquidity_raid_observed),
        (
            "ICT_MARKET_STRUCTURE_SHIFT_NOT_CONFIRMED",
            facts.ict_market_structure_shift_confirmed,
        ),
        ("ICT_DISPLACEMENT_NOT_SIGNIFICANT", facts.ict_displacement_significant),
        (
            "ICT_FVG_NOT_PRESENT_IN_DISPLACEMENT",
            facts.ict_fvg_present_in_displacement,
        ),
        (
            "ICT_ENTRY_RETRACE_TO_VALID_PD_ARRAY_NOT_OBSERVED",
            facts.ict_entry_retrace_into_valid_pd_array,
        ),
        ("ICT_ENTRY_CHASE_STATE_UNRESOLVED", facts.ict_entry_not_chasing),
        (
            "TTRADES_HTF_CLOSURE_AT_POI_NOT_CONFIRMED",
            facts.ttrades_htf_closure_at_poi_confirmed,
        ),
        ("TTRADES_LTF_CISD_NOT_CONFIRMED", facts.ttrades_ltf_cisd_confirmed),
        (
            "TTRADES_PROTECTED_SWING_NOT_CONFIRMED",
            facts.ttrades_protected_swing_confirmed,
        ),
        (
            "TTRADES_CONTINUATION_NOT_CONFIRMED",
            facts.ttrades_continuation_confirmed,
        ),
        (
            "TTRADES_WICK_FORMATION_NOT_CONFIRMED",
            facts.ttrades_wick_formation_confirmed,
        ),
    )
    wait_reasons.extend(reason for reason, confirmed in required if not confirmed)

    if wait_reasons:
        return CapitalizerDualSourceEntryAcceptance(
            identity=IDENTITY,
            state=CapitalizerEntryAcceptanceState.WAIT,
            reasons=tuple(wait_reasons),
            all_mandatory_conditions_confirmed=False,
            passes_to_qore_risk=False,
        )

    return CapitalizerDualSourceEntryAcceptance(
        identity=IDENTITY,
        state=CapitalizerEntryAcceptanceState.ACCEPTABLE_FOR_QORE_RISK,
        reasons=(
            "COGNITIVE_GATE_PASSED",
            "SOURCE_SESSION_CONTEXT_PASSED",
            "HTF_BIAS_CONFIRMED_ALIGNED",
            "ICT_LIQUIDITY_REFERENCE_DEFINED",
            "ICT_LIQUIDITY_RAID_OBSERVED",
            "ICT_MARKET_STRUCTURE_SHIFT_CONFIRMED",
            "ICT_SIGNIFICANT_DISPLACEMENT_CONFIRMED",
            "ICT_FVG_IN_DISPLACEMENT_CONFIRMED",
            "ICT_VALID_PD_ARRAY_RETRACE_CONFIRMED",
            "ICT_ENTRY_NOT_CHASING",
            "TTRADES_HTF_CLOSURE_AT_POI_CONFIRMED",
            "TTRADES_LTF_CISD_CONFIRMED",
            "TTRADES_PROTECTED_SWING_CONFIRMED",
            "TTRADES_CONTINUATION_CONFIRMED",
            "TTRADES_WICK_FORMATION_CONFIRMED",
            "M1_MSS_CONFIRMED",
            "M1_FVG_CONFIRMED",
            "M1_ORDER_BLOCK_CONFIRMED",
            "STRUCTURAL_TARGET_INTACT",
            "STRUCTURAL_STOP_GEOMETRY_VALID",
        ),
        all_mandatory_conditions_confirmed=True,
        passes_to_qore_risk=True,
    )


@dataclass(frozen=True, slots=True)
class CapitalizerCurrentEntryCoverageAudit:
    """Compare the current Capitalizer source engine against the stricter dual-source gate."""

    current_engine_explicitly_requires_source_session: bool = True
    current_engine_explicitly_requires_htf_bias: bool = True
    current_engine_explicitly_requires_structural_target: bool = True
    current_engine_explicitly_requires_ttrades_htf_closure: bool = True
    current_engine_explicitly_requires_ttrades_ltf_cisd: bool = True
    current_engine_explicitly_requires_protected_swing: bool = True

    current_engine_explicitly_requires_ict_liquidity_raid: bool = False
    current_engine_explicitly_requires_ict_significant_displacement: bool = False
    current_engine_explicitly_requires_ict_fvg_in_displacement: bool = False
    current_engine_explicitly_requires_ict_fvg_retrace_entry: bool = False
    current_engine_explicitly_rejects_entry_chasing: bool = False
    current_engine_explicitly_requires_wick_formed_before_body: bool = False
    current_engine_explicitly_requires_m1_mss: bool = True
    current_engine_explicitly_requires_m1_fvg: bool = True
    current_engine_explicitly_requires_m1_order_block: bool = True

    current_next_bar_open_is_universally_dual_source_entry: bool = False
    current_engine_may_claim_full_entry_fidelity: bool = False
    integration_required_before_entry_acceptance: bool = True


CURRENT_ENTRY_COVERAGE_AUDIT = CapitalizerCurrentEntryCoverageAudit()
