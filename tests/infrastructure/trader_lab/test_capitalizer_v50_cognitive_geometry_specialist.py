from datetime import UTC, datetime
from decimal import Decimal

from qore.infrastructure.trader_lab.capitalizer_contract import CapitalizerSession
from qore.infrastructure.trader_lab.capitalizer_high_frequency_capacity_census_v49 import (
    V49Opportunity,
)
from qore.infrastructure.trader_lab.capitalizer_v50_cognitive_geometry_specialist import (
    V50GeometryDecision,
    propose_v50_geometry,
)
from qore.infrastructure.trader_lab.capitalizer_v50_cognitive_hf_bridge import (
    V50CognitiveAssessment,
    V50CognitiveDisposition,
    V50CognitiveState,
    V50DestinationState,
    V50ExecutionFreshness,
    V50H1Freshness,
    V50SessionRunway,
    V50StopNoiseState,
)
from qore.infrastructure.trader_lab.capitalizer_v50_cognitive_opportunity import (
    IDENTITY as SNAPSHOT_IDENTITY,
)
from qore.infrastructure.trader_lab.capitalizer_v50_cognitive_opportunity import (
    V50CognitiveOpportunitySnapshot,
)
from qore.infrastructure.trader_lab.capitalizer_v50_target_stop_intelligence import (
    STOP_IDENTITY,
    TARGET_IDENTITY,
    V50DualInvalidation,
    V50H1TargetCandidate,
    V50H1TargetLadder,
)


def _snapshot(
    *,
    execution_risk: str = "0.5",
    thesis_risk: str = "1.0",
    target_price: str = "101.0",
) -> V50CognitiveOpportunitySnapshot:
    at = datetime(2026, 1, 5, 12, 0, tzinfo=UTC)
    opportunity = V49Opportunity(
        symbol="EURUSD",
        session="LONDON",
        operating_date="2026-01-05",
        h1_state_direction="BULLISH",
        h1_state_from=at.isoformat(),
        h1_state_until=at.isoformat(),
        h1_state_basis="CANDLE2_REVERSAL:BULLISH_FVG",
        m15_setup_confirmed_at=at.isoformat(),
        m15_protected_swing_price=str(Decimal("100") - Decimal(thesis_risk)),
        m1_trigger_confirmed_at=at.isoformat(),
        m1_trigger_family="FVG_RETRACE_CISD",
        decision_reference_price="100",
        structural_target_witness_price=target_price,
    )
    state = V50CognitiveState(
        identity="QORE_CAPITALIZER_V50_COGNITIVE_HF_BRIDGE",
        state_family_id="V50:test",
        symbol="EURUSD",
        session=CapitalizerSession.LONDON,
        h1_freshness=V50H1Freshness.FRESH,
        execution_freshness=V50ExecutionFreshness.IMMEDIATE,
        session_runway=V50SessionRunway.AMPLE,
        stop_noise_state=V50StopNoiseState.BALANCED,
        stop_to_noise_ratio=Decimal("5"),
        destination_state=V50DestinationState.BALANCED,
        destination_room_r=Decimal("1"),
        trigger_family="FVG_RETRACE_CISD",
        h1_basis="CANDLE2_REVERSAL:BULLISH_FVG",
        session_slot_ordinal=1,
        observation_tokens=("TEST",),
    )
    cognition = V50CognitiveAssessment(
        state=state,
        disposition=V50CognitiveDisposition.PASS_TO_COMPETITION,
        reasons=("TEST",),
        knowledge=__import__(
            "qore.infrastructure.trader_lab.capitalizer_confidence",
            fromlist=["CapitalizerKnowledgeState"],
        ).CapitalizerKnowledgeState.UNKNOWN,
        experience_observations=0,
        experience_mean_r=None,
        experience_strength=__import__(
            "qore.infrastructure.trader_lab.capitalizer_contract",
            fromlist=["EvidenceStrength"],
        ).EvidenceStrength.UNKNOWN,
        strategy_may_evaluate=True,
        requests_stop_refinement=False,
        requests_target_refinement=False,
    )
    candidate = V50H1TargetCandidate(
        candidate_id="H1:1",
        price=Decimal(target_price),
        pivot_confirmed_at=at,
        distance_price=abs(Decimal(target_price) - Decimal("100")),
        room_r_vs_thesis_stop=abs(
            Decimal(target_price) - Decimal("100")
        ) / Decimal(thesis_risk),
        rank=1,
    )
    ladder = V50H1TargetLadder(
        identity=TARGET_IDENTITY,
        side=__import__(
            "qore.infrastructure.trader_lab.capitalizer_exposure_graph",
            fromlist=["CapitalizerSide"],
        ).CapitalizerSide.LONG,
        decision_at=at,
        entry_price=Decimal("100"),
        thesis_stop_price=Decimal("100") - Decimal(thesis_risk),
        candidates=(candidate,),
    )
    execution = Decimal(execution_risk)
    dual = V50DualInvalidation(
        identity=STOP_IDENTITY,
        side=ladder.side,
        decision_at=at,
        entry_price=Decimal("100"),
        thesis_stop_price=Decimal("100") - Decimal(thesis_risk),
        execution_stop_price=Decimal("100") - execution,
        thesis_risk_price=Decimal(thesis_risk),
        execution_risk_price=execution,
        execution_vs_thesis_ratio=execution / Decimal(thesis_risk),
        execution_anchor_confirmed_at=at,
        execution_anchor_available=True,
    )
    return V50CognitiveOpportunitySnapshot(
        identity=SNAPSHOT_IDENTITY,
        symbol="EURUSD",
        session=CapitalizerSession.LONDON,
        observed_at=at,
        source_opportunity=opportunity,
        cognitive=cognition,
        target_ladder=ladder,
        dual_invalidation=dual,
        recent_m1_range_ticks=Decimal("10"),
        thesis_stop_distance_ticks=Decimal("100"),
        execution_stop_distance_ticks=execution * Decimal("100"),
        target_refinement_available=True,
        stop_refinement_available=True,
    )


def test_ready_geometry_uses_execution_stop_and_at_least_one_r_target() -> None:
    result = propose_v50_geometry(_snapshot(execution_risk="0.5", target_price="101"))
    assert result.decision is V50GeometryDecision.READY
    assert result.stop_price == Decimal("99.5")
    assert result.t1_reward_r == Decimal("2")
    assert result.full_exit_at_t1_required is False
    assert result.outcome_used is False


def test_execution_stop_inside_noise_waits_instead_of_forcing_entry() -> None:
    result = propose_v50_geometry(_snapshot(execution_risk="0.2", target_price="101"))
    assert result.decision is V50GeometryDecision.WAIT_STOP_BREATHING


def test_destination_below_one_r_waits_for_better_asymmetry() -> None:
    result = propose_v50_geometry(_snapshot(execution_risk="0.5", target_price="100.4"))
    assert result.decision is V50GeometryDecision.WAIT_ECONOMIC_ASYMMETRY
