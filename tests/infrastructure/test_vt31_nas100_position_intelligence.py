from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.traders.vt31_nas100_position_intelligence import (
    RESEARCH_UNCALIBRATED_POLICY,
    ContextualTrailingPolicy,
    FullCognitivePositionState,
    ManagementContext,
    PositionAction,
    ProtectionUrgency,
    SingleUnitTargetIntent,
    StructuralProtectionCandidate,
    assess_full_cognitive_position,
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
        planned_target_r=Decimal("3.4"),
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
        "MARKET_REGIME",
        "LIQUIDITY_SEQUENCE",
        "ENTRY_QUALITY",
        "RISK_GEOMETRY",
        "JOURNEY_DESTINATION",
        "INTERMARKET",
        "TEMPORAL",
    )
    assert state.minimum_volume_compatible == Decimal("0.01")
    assert state.cognitive_coverage_ratio == Decimal("1")
    assert "risk_ref" in state.observed_situation_fields
    assert "planned_target_r" in state.observed_situation_fields
    assert "structural_destination" in state.observation_only_situation_fields
    assert "current_path_vs_previous" in state.actuated_situation_fields
    assert state.terminal_pnl_used is False
    assert state.future_journey_label_used is False
    assert len(state.fingerprint()) == 64


def test_full_cognition_extends_single_unit_only_on_causal_deep_acceptance() -> None:
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
        is SingleUnitTargetIntent.EXTEND_FULL_UNIT_TO_DOL2
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
    assert state.target_intent is SingleUnitTargetIntent.PRESERVE_DOL1


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
    assert state.target_intent is SingleUnitTargetIntent.PRESERVE_DOL1
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
        is SingleUnitTargetIntent.EXIT_ON_CONFIRMED_EXHAUSTION
    )
