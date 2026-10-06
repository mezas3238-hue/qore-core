from __future__ import annotations

import inspect
from dataclasses import replace
from decimal import Decimal

from qore.infrastructure.traders.vt31_nas100_position_intelligence import (
    RESEARCH_UNCALIBRATED_POLICY,
    ContextualTrailingPolicy,
    FullCognitivePositionState,
    ManagementContext,
    PositionAction,
    ProtectionUrgency,
    StructuralDestinationCandidate,
    StructuralProtectionCandidate,
    UniversalTargetIntent,
    assess_full_cognitive_position,
    decide_market_native_position,
    validate_full_cognitive_accounting_for_research,
    validate_maximum_cognition_for_certification,
    decide_structural_protection,
    structurally_rearmed,
)
from qore.infrastructure.traders.vt31_nas100_reasoning_engine import reason
from qore.infrastructure.traders.vt31_nas100_situation_model import (
    Nas100SituationModel,
)


def test_uncalibrated_vt31_trailing_holds_instead_of_copying_turtle_params() -> None:
    decision = decide_structural_protection(
        side="long",
        current_stop=Decimal("100"),
        target=Decimal("120"),
        context=ManagementContext.CAUTIOUS,
        swing=StructuralProtectionCandidate(
            level=Decimal("105"),
            confirmations=1,
            source="confirmed-m1-swing",
        ),
        conquered_dol=Decimal("110"),
        policy=RESEARCH_UNCALIBRATED_POLICY,
    )
    assert decision.action is PositionAction.HOLD
    assert decision.next_stop is None
    assert decision.policy_calibrated is False


def test_calibrated_policy_never_widens_stop() -> None:
    policy = ContextualTrailingPolicy(
        supportive_swing_confirmations=3,
        mixed_swing_confirmations=2,
        cautious_swing_confirmations=1,
        dol_lock_enabled=True,
    )
    decision = decide_structural_protection(
        side="long",
        current_stop=Decimal("100"),
        target=Decimal("120"),
        context=ManagementContext.CAUTIOUS,
        swing=StructuralProtectionCandidate(
            level=Decimal("99"),
            confirmations=3,
            source="confirmed-m1-swing",
        ),
        conquered_dol=None,
        policy=policy,
    )
    assert decision.action is PositionAction.HOLD
    assert decision.next_stop is None


def test_conquered_dol_can_lock_only_when_policy_enables_it() -> None:
    policy = ContextualTrailingPolicy(
        supportive_swing_confirmations=3,
        mixed_swing_confirmations=2,
        cautious_swing_confirmations=1,
        dol_lock_enabled=True,
    )
    decision = decide_structural_protection(
        side="short",
        current_stop=Decimal("120"),
        target=Decimal("90"),
        context=ManagementContext.SUPPORTIVE,
        swing=None,
        conquered_dol=Decimal("105"),
        policy=policy,
    )
    assert decision.action is PositionAction.DOL_LOCK
    assert decision.next_stop == Decimal("105")


def test_structural_rearm_requires_new_vt31_market_event() -> None:
    exit_at = 1000
    assert structurally_rearmed(
        protected_exit_at_epoch=exit_at,
        new_raid_at_epoch=1001,
        new_confirmation_at_epoch=1002,
        new_decision_at_epoch=1003,
    )
    assert not structurally_rearmed(
        protected_exit_at_epoch=exit_at,
        new_raid_at_epoch=999,
        new_confirmation_at_epoch=1002,
        new_decision_at_epoch=1003,
    )
    assert not structurally_rearmed(
        protected_exit_at_epoch=exit_at,
        new_raid_at_epoch=1001,
        new_confirmation_at_epoch=999,
        new_decision_at_epoch=1003,
    )



def _full_cognitive_situation(
    *,
    entry_family: str = "fair-value-gap",
    last_event: str = "reference-liquidity-sweep",
    latency: int = 4,
    volatility: str = "compressed",
    path_ratio: str = "0.62",
    exhaustion: str = "UNKNOWN",
    cross_index: str = "BOTH_PEERS_SAME_SIDE_ALIGNED",
) -> Nas100SituationModel:
    return Nas100SituationModel(
        as_of="2026-01-05T15:20:00+00:00",
        weekday="Monday",
        session="NY_AM_SILVER_BULLET",
        decision_minute_ny=10 * 60 + 20,
        side="long",
        setup_family="VT31_AM_SILVER_BULLET_R2_2",
        confirmation_state="confirmed",
        prior_day_state="bullish",
        h4_state="mixed",
        h1_state="mixed",
        premarket_state="bullish",
        cash_open_state="bullish",
        position_in_prior_day_range="middle-third",
        range_state="compressed",
        volatility_state=volatility,
        current_path_vs_previous=Decimal(path_ratio),
        reference_width_vs_prior5=Decimal("0.68"),
        raid_depth_ref=Decimal("0.14"),
        recent_path_efficiency=Decimal("0.61"),
        recent_overlap_rate=Decimal("0.42"),
        first_breach_side="low",
        double_sided_before_decision=False,
        reference_reclaimed=True,
        reference_reclaim_age_minutes=3,
        last_structure_event_family=last_event,
        last_structure_event_age_minutes=2,
        recent_liquidity_event_count_10m=2,
        displacement_state="STRUCTURAL_CONFIRMATION_OBSERVED",
        entry_evidence_family=entry_family,
        confirmation_latency_minutes=latency,
        entry_evidence_freshness="fresh-0-5m",
        stop_plan="SOURCE_SWING_EXTREME",
        risk_ref=Decimal("0.21"),
        planned_target_r=None,
        structural_destination="OPPOSITE_09_REFERENCE_BOUNDARY",
        destination_distance_ref=Decimal("0.71"),
        journey_stage="DOL1_TOUCH_CLOSED",
        dol1_state="REACHED_CLOSED_M1",
        dol2_state="ACTIVE_PLUS_0_25_REFERENCE",
        dol3_state="RESEARCH_ONLY_UNCALIBRATED",
        extension_capacity_state="RESEARCH_ONLY_UNCALIBRATED",
        exhaustion_state=exhaustion,
        cross_index_state=cross_index,
    )


def test_full_cognitive_position_consumes_all_domains_without_oracle() -> None:
    situation = _full_cognitive_situation()
    reasoning = reason(situation)
    state = assess_full_cognitive_position(
        situation=situation,
        reasoning=reasoning,
        entry_tier="CORE",
        dol1_acceptance_observed=True,
    )

    assert isinstance(state, FullCognitivePositionState)
    assert state.observed_domains == (
        "STRATEGY_REASONING",
        "MEMORY_SYNTHESIS",
        "MULTITIMEFRAME_CONTEXT",
        "MARKET_REGIME",
        "LIQUIDITY_SEQUENCE",
        "ENTRY_QUALITY",
        "RISK_GEOMETRY",
        "JOURNEY_DESTINATION",
        "TARGET_EXIT_INTELLIGENCE",
        "INTERMARKET",
        "TEMPORAL",
    )
    assert state.volume_agnostic is True
    assert state.partial_execution_required is False
    assert state.cognitive_coverage_ratio == Decimal("1")
    assert state.full_cognitive_accounting_verified is True
    assert state.reasoning_max_intelligence_ready is False
    assert "DEEPER_JOURNEY_CAPACITY_UNCALIBRATED" in (
        state.reasoning_max_intelligence_blockers
    )
    assert "CONTEXTUAL_POSITION_MANAGEMENT_UNRESOLVED" in (
        state.reasoning_max_intelligence_blockers
    )
    assert state.maximum_cognition_verified is False
    assert state.post_entry_reassessment is False
    assert state.entry_situation_fingerprint == situation.fingerprint()
    assert state.current_situation_fingerprint == situation.fingerprint()
    assert "risk_ref" in state.observed_situation_fields
    assert "planned_target_r" in state.observed_situation_fields
    assert "planned_target_r" in state.observation_only_situation_fields
    assert "structural_destination" in state.observation_only_situation_fields
    assert "current_path_vs_previous" in state.actuated_situation_fields
    assert "h4_state" in state.actuated_situation_fields
    assert "h1_state" in state.actuated_situation_fields
    assert "m15_state" in state.actuated_situation_fields
    assert state.terminal_pnl_used is False
    assert state.future_journey_label_used is False
    assert len(state.fingerprint()) == 64


def test_full_cognition_extends_volume_agnostically_on_causal_deep_acceptance() -> None:
    situation = _full_cognitive_situation()
    reasoning = reason(situation)
    state = assess_full_cognitive_position(
        situation=situation,
        reasoning=reasoning,
        entry_tier="CORE",
        dol1_acceptance_observed=True,
    )

    assert reasoning.action == "EXECUTE"
    assert state.destination_state == "DEEP"
    assert state.management_context is ManagementContext.SUPPORTIVE
    assert state.protection_urgency is ProtectionUrgency.LOW
    assert (
        state.target_intent
        is UniversalTargetIntent.EXTEND_TO_DOL2
    )


def test_full_cognition_fails_closed_without_dol1_acceptance() -> None:
    situation = _full_cognitive_situation()
    reasoning = reason(situation)
    state = assess_full_cognitive_position(
        situation=situation,
        reasoning=reasoning,
        entry_tier="CORE",
        dol1_acceptance_observed=None,
    )

    assert state.destination_state == "DEEP"
    assert state.target_intent is UniversalTargetIntent.PRESERVE_DOL1


def test_full_cognition_detects_shallow_breaker_interaction() -> None:
    situation = _full_cognitive_situation(
        entry_family="breaker",
        last_event="breaker",
        latency=12,
    )
    reasoning = reason(situation)
    state = assess_full_cognitive_position(
        situation=situation,
        reasoning=reasoning,
        entry_tier="SECONDARY",
        dol1_acceptance_observed=True,
    )

    assert state.destination_state == "SHALLOW"
    assert state.management_context is ManagementContext.CAUTIOUS
    assert state.target_intent is UniversalTargetIntent.PRESERVE_DOL1
    assert "DESTINATION:BREAKER_LATENCY_11M_PLUS" in state.signal_codes
    assert "DESTINATION:SECONDARY_BREAKER" in state.signal_codes


def test_full_cognition_exhaustion_overrides_extension() -> None:
    situation = _full_cognitive_situation(
        exhaustion="CONFIRMED_EXHAUSTION",
    )
    reasoning = reason(situation)
    state = assess_full_cognitive_position(
        situation=situation,
        reasoning=reasoning,
        entry_tier="CORE",
        dol1_acceptance_observed=True,
    )

    assert state.management_context is ManagementContext.CAUTIOUS
    assert state.protection_urgency is ProtectionUrgency.HIGH
    assert (
        state.target_intent
        is UniversalTargetIntent.EXIT_ON_CONFIRMED_EXHAUSTION
    )


def test_full_cognition_has_no_volume_input_or_fixed_lot_contract() -> None:
    situation = _full_cognitive_situation()
    reasoning = reason(situation)
    state = assess_full_cognitive_position(
        situation=situation,
        reasoning=reasoning,
        entry_tier="CORE",
        dol1_acceptance_observed=True,
    )

    assert state.volume_agnostic is True
    assert state.partial_execution_required is False
    assert "volume" not in state.__dataclass_fields__
    assert "lot" not in state.__dataclass_fields__
    assert "minimum_volume_compatible" not in state.__dataclass_fields__


def test_post_entry_cognition_reuses_frozen_entry_reasoning() -> None:
    entry = _full_cognitive_situation()
    reasoning = reason(entry)
    current = replace(
        entry,
        as_of="2026-01-05T15:45:00+00:00",
        decision_minute_ny=10 * 60 + 45,
        journey_stage="POST_ENTRY_DOL1_REASSESSMENT",
        dol1_state="REACHED_CLOSED_M1",
        recent_path_efficiency=Decimal("0.66"),
        recent_overlap_rate=Decimal("0.35"),
    )

    state = assess_full_cognitive_position(
        situation=current,
        reasoning=reasoning,
        entry_tier="CORE",
        dol1_acceptance_observed=True,
        entry_situation_fingerprint=entry.fingerprint(),
    )

    assert state.post_entry_reassessment is True
    assert state.entry_situation_fingerprint == entry.fingerprint()
    assert state.current_situation_fingerprint == current.fingerprint()
    assert state.target_intent is UniversalTargetIntent.EXTEND_TO_DOL2


def test_market_native_decision_signature_has_no_r_or_volume_authority() -> None:
    params = set(inspect.signature(decide_market_native_position).parameters)
    forbidden = {
        "r",
        "r_multiple",
        "mfe_r",
        "mae_r",
        "profit_r",
        "target_r",
        "risk_r",
        "volume",
        "lot_size",
        "position_size",
        "leverage",
        "risk_budget",
    }
    assert params.isdisjoint(forbidden)


def test_market_native_position_exits_on_structural_invalidation() -> None:
    situation = _full_cognitive_situation()
    cognition = assess_full_cognitive_position(
        situation=situation,
        reasoning=reason(situation),
        entry_tier="CORE",
        dol1_acceptance_observed=None,
    )

    decision = decide_market_native_position(
        side="long",
        current_stop=Decimal("100"),
        primary_structural_target=Decimal("120"),
        next_structural_target=None,
        cognition=cognition,
        protective_swing=None,
        primary_target_reached=False,
        primary_target_accepted=False,
        structure_invalidated=True,
        liquidity_failure_confirmed=False,
        momentum_deteriorated=False,
        regime_changed_against_thesis=False,
    )

    assert decision.action is PositionAction.EXIT
    assert decision.reason == "STRUCTURAL_INVALIDATION_CONFIRMED"
    assert decision.r_runtime_authority is False
    assert decision.volume_agnostic is True


def test_market_native_position_extends_only_after_structural_acceptance() -> None:
    situation = _full_cognitive_situation()
    cognition = assess_full_cognitive_position(
        situation=situation,
        reasoning=reason(situation),
        entry_tier="CORE",
        dol1_acceptance_observed=True,
    )
    assert cognition.target_intent is UniversalTargetIntent.EXTEND_TO_DOL2

    accepted = decide_market_native_position(
        side="long",
        current_stop=Decimal("100"),
        primary_structural_target=Decimal("120"),
        next_structural_target=StructuralDestinationCandidate(
            level=Decimal("128"),
            source="confirmed-liquidity-pool",
        ),
        cognition=cognition,
        protective_swing=None,
        primary_target_reached=True,
        primary_target_accepted=True,
        structure_invalidated=False,
        liquidity_failure_confirmed=False,
        momentum_deteriorated=False,
        regime_changed_against_thesis=False,
    )
    rejected = decide_market_native_position(
        side="long",
        current_stop=Decimal("100"),
        primary_structural_target=Decimal("120"),
        next_structural_target=StructuralDestinationCandidate(
            level=Decimal("128"),
            source="confirmed-liquidity-pool",
        ),
        cognition=cognition,
        protective_swing=None,
        primary_target_reached=True,
        primary_target_accepted=False,
        structure_invalidated=False,
        liquidity_failure_confirmed=False,
        momentum_deteriorated=False,
        regime_changed_against_thesis=False,
    )

    assert accepted.action is PositionAction.EXTEND
    assert accepted.next_target == Decimal("128")
    assert rejected.action is PositionAction.EXIT
    assert rejected.reason == "PRIMARY_STRUCTURAL_TARGET_DELIVERED"


def test_market_native_momentum_deterioration_uses_confirmed_swing_price() -> None:
    situation = _full_cognitive_situation(
        entry_family="breaker",
        last_event="breaker",
        latency=12,
    )
    cognition = assess_full_cognitive_position(
        situation=situation,
        reasoning=reason(situation),
        entry_tier="CORE",
        dol1_acceptance_observed=None,
    )
    swing = StructuralProtectionCandidate(
        level=Decimal("106"),
        confirmations=1,
        source="confirmed-m1-swing",
    )

    decision = decide_market_native_position(
        side="long",
        current_stop=Decimal("100"),
        primary_structural_target=Decimal("120"),
        next_structural_target=None,
        cognition=cognition,
        protective_swing=swing,
        primary_target_reached=False,
        primary_target_accepted=False,
        structure_invalidated=False,
        liquidity_failure_confirmed=False,
        momentum_deteriorated=True,
        regime_changed_against_thesis=False,
    )

    assert decision.action is PositionAction.TRAIL
    assert decision.next_stop == Decimal("106")
    assert decision.reason == "COGNITIVE_AND_MARKET_STRUCTURAL_PROTECTION"


def test_supportive_cognition_vetoes_premature_structural_trailing() -> None:
    situation = _full_cognitive_situation()
    cognition = assess_full_cognitive_position(
        situation=situation,
        reasoning=reason(situation),
        entry_tier="CORE",
        dol1_acceptance_observed=None,
    )
    swing = StructuralProtectionCandidate(
        level=Decimal("106"),
        confirmations=1,
        source="confirmed-m1-swing",
    )

    decision = decide_market_native_position(
        side="long",
        current_stop=Decimal("100"),
        primary_structural_target=Decimal("120"),
        next_structural_target=None,
        cognition=cognition,
        protective_swing=swing,
        primary_target_reached=False,
        primary_target_accepted=False,
        structure_invalidated=False,
        liquidity_failure_confirmed=False,
        momentum_deteriorated=True,
        regime_changed_against_thesis=False,
    )

    assert cognition.protection_urgency is ProtectionUrgency.LOW
    assert decision.action is PositionAction.HOLD
    assert decision.next_stop is None
    assert decision.reason == "COGNITIVE_WINNER_PRESERVATION_VETO"


def test_market_native_position_holds_when_market_thesis_is_intact() -> None:
    situation = _full_cognitive_situation()
    cognition = assess_full_cognitive_position(
        situation=situation,
        reasoning=reason(situation),
        entry_tier="CORE",
        dol1_acceptance_observed=None,
    )

    decision = decide_market_native_position(
        side="long",
        current_stop=Decimal("100"),
        primary_structural_target=Decimal("120"),
        next_structural_target=None,
        cognition=cognition,
        protective_swing=None,
        primary_target_reached=False,
        primary_target_accepted=False,
        structure_invalidated=False,
        liquidity_failure_confirmed=False,
        momentum_deteriorated=False,
        regime_changed_against_thesis=False,
    )

    assert decision.action is PositionAction.HOLD
    assert decision.reason == "MARKET_STRUCTURE_REMAINS_VALID"


def test_full_accounting_can_research_while_certification_stays_blocked() -> None:
    situation = _full_cognitive_situation()
    cognition = assess_full_cognitive_position(
        situation=situation,
        reasoning=reason(situation),
        entry_tier="CORE",
        dol1_acceptance_observed=True,
    )

    validate_full_cognitive_accounting_for_research(cognition)

    try:
        validate_maximum_cognition_for_certification(cognition)
    except ValueError as exc:
        message = str(exc)
    else:
        raise AssertionError("maximum cognition certification should be blocked")

    assert "DEEPER_JOURNEY_CAPACITY_UNCALIBRATED" in message
    assert "CONTEXTUAL_POSITION_MANAGEMENT_UNRESOLVED" in message
