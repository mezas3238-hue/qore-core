from __future__ import annotations

import inspect
from dataclasses import replace
from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.traders.vt31_nas100_causal_fact_producers import (
    CausalBooleanFact,
    CausalDestinationFact,
    MarketNativeProducerReport,
)
from qore.infrastructure.traders.vt31_nas100_position_intelligence import (
    PositionAction,
    ProtectionUrgency,
    StructuralDestinationCandidate,
    StructuralProtectionCandidate,
)
from qore.infrastructure.traders.vt31_nas100_post_entry_cognitive_runtime import (
    PostEntryCausalObservation,
    PostEntryMarketFacts,
    build_market_facts_from_causal_report,
    reassess_and_decide_post_entry,
    rebuild_post_entry_situation,
    revalidate_prospective_fill,
)
from qore.infrastructure.traders.vt31_nas100_reasoning_engine import reason
from qore.infrastructure.traders.vt31_nas100_situation_model import (
    Nas100SituationModel,
)


def _entry_situation() -> Nas100SituationModel:
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
        volatility_state="compressed",
        current_path_vs_previous=Decimal("0.62"),
        reference_width_vs_prior5=Decimal("0.68"),
        raid_depth_ref=Decimal("0.14"),
        recent_path_efficiency=Decimal("0.61"),
        recent_overlap_rate=Decimal("0.42"),
        first_breach_side="low",
        double_sided_before_decision=False,
        reference_reclaimed=True,
        reference_reclaim_age_minutes=3,
        last_structure_event_family="reference-liquidity-sweep",
        last_structure_event_age_minutes=2,
        recent_liquidity_event_count_10m=2,
        displacement_state="STRUCTURAL_CONFIRMATION_OBSERVED",
        entry_evidence_family="fair-value-gap",
        confirmation_latency_minutes=4,
        entry_evidence_freshness="fresh-0-5m",
        stop_plan="SOURCE_SWING_EXTREME",
        risk_ref=Decimal("0.21"),
        planned_target_r=Decimal("3"),
        structural_destination="OPPOSITE_09_REFERENCE_BOUNDARY",
        destination_distance_ref=Decimal("0.71"),
        journey_stage="POST_CONFIRMATION_PRE_EXECUTION",
        dol1_state="ACTIVE_OPPOSITE_09_BOUNDARY",
        dol2_state="RESEARCH_ONLY_UNCALIBRATED",
        dol3_state="RESEARCH_ONLY_UNCALIBRATED",
        extension_capacity_state="RESEARCH_ONLY_UNCALIBRATED",
        exhaustion_state="UNKNOWN",
        cross_index_state="OPTIONAL_CONTEXT_NOT_REQUIRED",
    )


def _observation(
    *,
    exhaustion: str = "UNKNOWN",
    dol1_state: str = "REACHED_CLOSED_M1",
    cautious: bool = False,
) -> PostEntryCausalObservation:
    return PostEntryCausalObservation(
        as_of="2026-01-05T15:45:00+00:00",
        decision_minute_ny=10 * 60 + 45,
        prior_day_state="bullish",
        h4_state="mixed",
        h1_state="bearish" if cautious else "bullish",
        premarket_state="bearish" if cautious else "bullish",
        cash_open_state="bearish" if cautious else "bullish",
        position_in_prior_day_range="middle-third",
        range_state="expanded" if cautious else "compressed",
        volatility_state="expanded" if cautious else "compressed",
        current_path_vs_previous=Decimal("1.45" if cautious else "0.64"),
        reference_width_vs_prior5=Decimal("0.68"),
        raid_depth_ref=Decimal("0.14"),
        recent_path_efficiency=Decimal("0.20" if cautious else "0.66"),
        recent_overlap_rate=Decimal("0.90" if cautious else "0.35"),
        reference_reclaimed=not cautious,
        reference_reclaim_age_minutes=None if cautious else 7,
        last_structure_event_family=(
            "breaker" if cautious else "reference-liquidity-sweep"
        ),
        last_structure_event_age_minutes=3,
        recent_liquidity_event_count_10m=2,
        displacement_state="STRUCTURAL_CONFIRMATION_OBSERVED",
        journey_stage="POST_ENTRY_REASSESSMENT",
        dol1_state=dol1_state,
        dol2_state="CONFIRMED_LIQUIDITY_DESTINATION",
        dol3_state="UNRESOLVED",
        extension_capacity_state="SUPPORTIVE_CONTINUATION",
        exhaustion_state=exhaustion,
        cross_index_state=(
            "BOTH_PEERS_OPPOSITE"
            if cautious
            else "BOTH_PEERS_SAME_SIDE_ALIGNED"
        ),
    )


def _market(
    *,
    target_reached: bool = False,
    target_accepted: bool = False,
    swing: StructuralProtectionCandidate | None = None,
    momentum_bad: bool = False,
    invalidated: bool = False,
) -> PostEntryMarketFacts:
    return PostEntryMarketFacts(
        side="long",
        current_stop=Decimal("95"),
        primary_structural_target=Decimal("100"),
        next_structural_target=StructuralDestinationCandidate(
            level=Decimal("104"),
            source="confirmed-liquidity-pool",
        ),
        protective_swing=swing,
        primary_target_reached=target_reached,
        primary_target_accepted=target_accepted,
        structure_invalidated=invalidated,
        liquidity_failure_confirmed=False,
        momentum_deteriorated=momentum_bad,
        regime_changed_against_thesis=False,
    )


def test_post_entry_runtime_interfaces_expose_no_sizing_authority() -> None:
    forbidden = {
        "volume",
        "lot_size",
        "position_size",
        "sizing",
        "leverage",
        "risk_budget",
        "portfolio_weight",
        "capital_weight",
    }
    observation_fields = set(PostEntryCausalObservation.__dataclass_fields__)
    market_fields = set(PostEntryMarketFacts.__dataclass_fields__)
    function_params = set(
        inspect.signature(reassess_and_decide_post_entry).parameters
    )

    assert observation_fields.isdisjoint(forbidden)
    assert market_fields.isdisjoint(forbidden)
    assert function_params.isdisjoint(forbidden)


def test_rebuild_post_entry_situation_preserves_current_market_native_plan() -> None:
    entry = _entry_situation()
    current = rebuild_post_entry_situation(
        entry_situation=entry,
        observation=_observation(),
    )

    assert current.planned_target_r == Decimal("3")
    assert current.as_of != entry.as_of
    assert current.h1_state == "bullish"
    assert current.journey_stage == "POST_ENTRY_REASSESSMENT"
    assert current.entry_evidence_family == entry.entry_evidence_family
    assert current.stop_plan == entry.stop_plan


def test_full_cognition_reassesses_and_extends_only_on_structural_acceptance() -> None:
    entry = _entry_situation()
    decision = reassess_and_decide_post_entry(
        entry_situation=entry,
        entry_reasoning=reason(entry),
        observation=_observation(),
        market=_market(target_reached=True, target_accepted=True),
        entry_tier="CORE",
        dol1_acceptance_observed=True,
    )

    assert decision.full_cognition_reassessed is True
    assert decision.cognition.post_entry_reassessment is True
    assert decision.entry_situation_fingerprint == entry.fingerprint()
    assert (
        decision.current_situation_fingerprint
        != decision.entry_situation_fingerprint
    )
    assert decision.position.action is PositionAction.EXTEND
    assert decision.position.next_target == Decimal("104")
    assert decision.position.r_runtime_authority is False
    assert decision.position.r_runtime_strategy_allowed is True
    assert decision.position.volume_agnostic is True
    assert decision.r_runtime_authority is True
    assert decision.r_runtime_strategy_allowed is True
    assert decision.volume_runtime_authority is False
    assert decision.sizing_authority is False


def test_target_touch_without_structural_acceptance_exits_at_primary_target() -> None:
    entry = _entry_situation()
    decision = reassess_and_decide_post_entry(
        entry_situation=entry,
        entry_reasoning=reason(entry),
        observation=_observation(),
        market=_market(target_reached=True, target_accepted=False),
        entry_tier="CORE",
        dol1_acceptance_observed=True,
    )

    assert decision.position.action is PositionAction.EXIT
    assert decision.position.reason == "PRIMARY_STRUCTURAL_TARGET_DELIVERED"
    assert decision.position.next_target is None


def test_confirmed_exhaustion_exits_before_extension() -> None:
    entry = _entry_situation()
    decision = reassess_and_decide_post_entry(
        entry_situation=entry,
        entry_reasoning=reason(entry),
        observation=_observation(exhaustion="CONFIRMED_EXHAUSTION"),
        market=_market(target_reached=False),
        entry_tier="CORE",
        dol1_acceptance_observed=False,
    )

    assert decision.position.action is PositionAction.EXIT
    assert decision.position.reason == "COGNITIVE_EXHAUSTION_CONFIRMED"


def test_momentum_deterioration_trails_to_confirmed_market_swing() -> None:
    entry = _entry_situation()
    decision = reassess_and_decide_post_entry(
        entry_situation=entry,
        entry_reasoning=reason(entry),
        observation=_observation(
            dol1_state="ACTIVE_OPPOSITE_09_BOUNDARY",
            cautious=True,
        ),
        market=_market(
            swing=StructuralProtectionCandidate(
                level=Decimal("97"),
                confirmations=1,
                source="confirmed-m1-swing",
            ),
            momentum_bad=True,
        ),
        entry_tier="CORE",
        dol1_acceptance_observed=None,
    )

    assert decision.position.action is PositionAction.TRAIL
    assert decision.position.next_stop == Decimal("97")
    assert decision.cognition.protection_urgency is not ProtectionUrgency.LOW
    assert decision.position.reason == "COGNITIVE_AND_MARKET_STRUCTURAL_PROTECTION"


def test_structural_invalidation_has_immediate_market_authority() -> None:
    entry = _entry_situation()
    decision = reassess_and_decide_post_entry(
        entry_situation=entry,
        entry_reasoning=reason(entry),
        observation=_observation(),
        market=_market(invalidated=True),
        entry_tier="CORE",
        dol1_acceptance_observed=None,
    )

    assert decision.position.action is PositionAction.EXIT
    assert decision.position.reason == "STRUCTURAL_INVALIDATION_CONFIRMED"


def test_post_entry_side_cannot_drift_from_frozen_entry() -> None:
    entry = _entry_situation()
    market = PostEntryMarketFacts(
        side="short",
        current_stop=Decimal("105"),
        primary_structural_target=Decimal("90"),
        next_structural_target=None,
        protective_swing=None,
        primary_target_reached=False,
        primary_target_accepted=False,
        structure_invalidated=False,
        liquidity_failure_confirmed=False,
        momentum_deteriorated=False,
        regime_changed_against_thesis=False,
    )

    with pytest.raises(ValueError, match="side must match"):
        reassess_and_decide_post_entry(
            entry_situation=entry,
            entry_reasoning=reason(entry),
            observation=_observation(),
            market=market,
        )



def test_supportive_post_entry_cognition_preserves_winner_despite_swing() -> None:
    entry = _entry_situation()
    decision = reassess_and_decide_post_entry(
        entry_situation=entry,
        entry_reasoning=reason(entry),
        observation=_observation(
            dol1_state="ACTIVE_OPPOSITE_09_BOUNDARY",
            cautious=False,
        ),
        market=_market(
            swing=StructuralProtectionCandidate(
                level=Decimal("97"),
                confirmations=1,
                source="confirmed-m1-swing",
            ),
            momentum_bad=True,
        ),
        entry_tier="CORE",
        dol1_acceptance_observed=None,
    )

    assert decision.cognition.protection_urgency is ProtectionUrgency.LOW
    assert decision.position.action is PositionAction.HOLD
    assert decision.position.reason == "COGNITIVE_WINNER_PRESERVATION_VETO"


def test_post_entry_rebuild_carries_causal_open_r() -> None:
    entry = _entry_situation()
    observation = replace(
        _observation(dol1_state="ACTIVE_OPPOSITE_09_BOUNDARY"),
        m15_state="mixed",
        dol2_state="CALIBRATED_ECONOMIC_CAPACITY_COGNITION_REQUIRED",
        dol3_state="REJECTED_BY_EDGE_ECONOMICS",
        extension_capacity_state="CALIBRATED_PRE_DOL1_CURRENT_JOURNEY",
        exhaustion_state="NO_CONFIRMED_EXHAUSTION",
        current_open_r=Decimal("-0.50"),
    )
    current = rebuild_post_entry_situation(
        entry_situation=entry,
        observation=observation,
    )

    assert current.current_open_r == Decimal("-0.50")
    decision = reassess_and_decide_post_entry(
        entry_situation=entry,
        entry_reasoning=reason(entry),
        observation=observation,
        market=_market(
            swing=StructuralProtectionCandidate(
                level=Decimal("97"),
                confirmations=1,
                source="confirmed-m1-swing",
            ),
            momentum_bad=True,
        ),
        entry_tier="CORE",
        dol1_acceptance_observed=False,
    )
    assert decision.cognition.maximum_cognition_verified is True
    assert decision.cognition.protection_urgency is ProtectionUrgency.MODERATE
    assert decision.cognition.target_intent.value == "PRESERVE_DOL1"
    assert decision.position.action is PositionAction.EXIT
    assert decision.position.reason == "VALIDATED_ADVERSE_CONTEXT_EXIT"
    assert decision.r_runtime_authority is True


def test_validated_comp009_adverse_exit_requires_material_adverse_journey() -> None:
    entry = _entry_situation()
    observation = replace(
        _observation(dol1_state="ACTIVE_OPPOSITE_09_BOUNDARY"),
        m15_state="mixed",
        dol2_state="CALIBRATED_ECONOMIC_CAPACITY_COGNITION_REQUIRED",
        dol3_state="REJECTED_BY_EDGE_ECONOMICS",
        extension_capacity_state="CALIBRATED_PRE_DOL1_CURRENT_JOURNEY",
        exhaustion_state="NO_CONFIRMED_EXHAUSTION",
        current_open_r=Decimal("-0.49"),
    )
    decision = reassess_and_decide_post_entry(
        entry_situation=entry,
        entry_reasoning=reason(entry),
        observation=observation,
        market=_market(),
        entry_tier="CORE",
        dol1_acceptance_observed=False,
    )

    assert decision.cognition.maximum_cognition_verified is True
    assert decision.position.action is PositionAction.HOLD
    assert decision.position.reason == "MARKET_STRUCTURE_REMAINS_VALID"


def test_fill_time_shadow_uses_canonical_entry_reasoning_not_post_entry_r() -> None:
    entry = _entry_situation()
    observation = _observation()  # M15 defaults to UNWIRED.
    outcome = revalidate_prospective_fill(
        entry_situation=entry,
        entry_reasoning=reason(entry),
        observation=observation,
        prospective_fill_open_at=datetime.fromisoformat(observation.as_of),
        apply_comp008_admission=False,
    )
    assert outcome.execution_authority is False
    assert outcome.canonical_reasoning_evaluated is True
    assert outcome.candidate_fill_accepted is False
    assert "M15_CONTEXT_UNWIRED" in outcome.entry_mandatory_blockers
    current = rebuild_post_entry_situation(
        entry_situation=entry,
        observation=observation,
    )
    assert outcome.current_reasoning_action == reason(current).action
    assert outcome.entry_situation_fingerprint == entry.fingerprint()


def test_fill_time_fails_closed_if_post_fill_r_is_smuggled_in() -> None:
    entry = _entry_situation()
    observation = replace(_observation(), current_open_r=Decimal("1"))
    with pytest.raises(ValueError, match="post-fill open R"):
        revalidate_prospective_fill(
            entry_situation=entry,
            entry_reasoning=reason(entry),
            observation=observation,
            prospective_fill_open_at=datetime.fromisoformat(observation.as_of),
            apply_comp008_admission=False,
        )


def test_fill_time_requires_exact_as_of_prospective_open() -> None:
    entry = _entry_situation()
    observation = _observation()
    with pytest.raises(ValueError, match="exact prospective"):
        revalidate_prospective_fill(
            entry_situation=entry,
            entry_reasoning=reason(entry),
            observation=observation,
            prospective_fill_open_at=(
                datetime.fromisoformat(observation.as_of) + timedelta(minutes=1)
            ),
            apply_comp008_admission=False,
        )


def _native_report(
    *,
    as_of: str,
    structure: bool | None = True,
    target_status: str = "NOT_APPLICABLE",
) -> MarketNativeProducerReport:
    timestamp = datetime.fromisoformat(as_of)
    observed = lambda name, value: CausalBooleanFact(
        name=name,
        status="OBSERVED" if value is not None else "NOT_EVALUABLE",
        value=value,
        observed_at=timestamp if value is not None else None,
        source="closed-m1-frozen-thesis-fixture",
        reason="FIXTURE_EVIDENCE",
    )
    return MarketNativeProducerReport(
        as_of=timestamp,
        structure_invalidated=observed("structure_invalidated", structure),
        liquidity_failure_confirmed=observed(
            "liquidity_failure_confirmed", False
        ),
        regime_changed_against_thesis=observed(
            "regime_changed_against_thesis", False
        ),
        next_structural_target=CausalDestinationFact(
            status=target_status,
            candidate=None,
            observed_at=None,
            source="explicit-destination-lifecycle",
            reason="FIXTURE",
        ),
    )


def test_causal_native_report_reaches_canonical_position_exit() -> None:
    entry = _entry_situation()
    observation = _observation(dol1_state="ACTIVE_OPPOSITE_09_BOUNDARY")
    report = _native_report(as_of=observation.as_of, structure=True)
    market = build_market_facts_from_causal_report(
        template=_market(),
        report=report,
        observation=observation,
    )
    assert market.structure_invalidated is True
    assert market.next_structural_target is None
    decision = reassess_and_decide_post_entry(
        entry_situation=entry,
        entry_reasoning=reason(entry),
        observation=observation,
        market=market,
        entry_tier="CORE",
    )
    assert decision.position.action is PositionAction.EXIT
    assert decision.position.reason == "STRUCTURAL_INVALIDATION_CONFIRMED"


def test_missing_mandatory_native_report_refuses_canonical_bridge() -> None:
    observation = _observation()
    report = _native_report(as_of=observation.as_of, structure=None)
    with pytest.raises(ValueError, match="mandatory native fact not evaluable"):
        build_market_facts_from_causal_report(
            template=_market(),
            report=report,
            observation=observation,
        )


def test_required_next_target_and_future_report_fail_closed() -> None:
    observation = _observation()
    report = _native_report(
        as_of=observation.as_of,
        target_status="MISSING_REQUIRED",
    )
    with pytest.raises(ValueError, match="required next structural target"):
        build_market_facts_from_causal_report(
            template=_market(),
            report=report,
            observation=observation,
        )
    earlier = replace(
        observation,
        as_of=(
            datetime.fromisoformat(observation.as_of)
            - timedelta(minutes=1)
        ).isoformat(),
    )
    with pytest.raises(ValueError, match="must match position decision as_of"):
        build_market_facts_from_causal_report(
            template=_market(),
            report=report,
            observation=earlier,
        )
