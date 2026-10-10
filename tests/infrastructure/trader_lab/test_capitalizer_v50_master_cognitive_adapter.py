from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal

from qore.infrastructure.trader_lab.capitalizer_confidence import (
    CapitalizerKnowledgeState,
)
from qore.infrastructure.trader_lab.capitalizer_contract import (
    CapitalizerSession,
    EvidenceStrength,
)
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_high_frequency_capacity_census_v49 import (
    V49Opportunity,
)
from qore.infrastructure.trader_lab.capitalizer_v50_cognitive_geometry_specialist import (
    IDENTITY as GEOMETRY_IDENTITY,
)
from qore.infrastructure.trader_lab.capitalizer_v50_cognitive_geometry_specialist import (
    V50GeometryDecision,
    V50GeometryProposal,
    V50StopMode,
)
from qore.infrastructure.trader_lab.capitalizer_v50_cognitive_hf_bridge import (
    IDENTITY as BRIDGE_IDENTITY,
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
from qore.infrastructure.trader_lab.capitalizer_v50_master_cognitive_adapter import (
    adapt_v50_to_master_context,
)
from qore.infrastructure.trader_lab.capitalizer_v50_target_stop_intelligence import (
    STOP_IDENTITY,
    TARGET_IDENTITY,
    V50DualInvalidation,
    V50H1TargetCandidate,
    V50H1TargetLadder,
)


def _snapshot() -> tuple[V50CognitiveOpportunitySnapshot, V50GeometryProposal]:
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
        m15_protected_swing_price="99",
        m1_trigger_confirmed_at=at.isoformat(),
        m1_trigger_family="FVG_RETRACE_CISD",
        decision_reference_price="100",
        structural_target_witness_price="101",
    )
    state = V50CognitiveState(
        identity=BRIDGE_IDENTITY,
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
        observation_tokens=(
            "SYMBOL=EURUSD",
            "SESSION=LONDON",
            "NEW_CAUSAL_EVENT=YES",
        ),
    )
    cognition = V50CognitiveAssessment(
        state=state,
        disposition=V50CognitiveDisposition.PASS_TO_COMPETITION,
        reasons=("TEST",),
        knowledge=CapitalizerKnowledgeState.UNKNOWN,
        experience_observations=0,
        experience_mean_r=None,
        experience_strength=EvidenceStrength.UNKNOWN,
        strategy_may_evaluate=True,
        requests_stop_refinement=False,
        requests_target_refinement=False,
    )
    target = V50H1TargetCandidate(
        candidate_id="H1:1",
        price=Decimal("101"),
        pivot_confirmed_at=at,
        distance_price=Decimal("1"),
        room_r_vs_thesis_stop=Decimal("1"),
        rank=1,
    )
    ladder = V50H1TargetLadder(
        identity=TARGET_IDENTITY,
        side=CapitalizerSide.LONG,
        decision_at=at,
        entry_price=Decimal("100"),
        thesis_stop_price=Decimal("99"),
        candidates=(target,),
    )
    dual = V50DualInvalidation(
        identity=STOP_IDENTITY,
        side=CapitalizerSide.LONG,
        decision_at=at,
        entry_price=Decimal("100"),
        thesis_stop_price=Decimal("99"),
        execution_stop_price=Decimal("99.5"),
        thesis_risk_price=Decimal("1"),
        execution_risk_price=Decimal("0.5"),
        execution_vs_thesis_ratio=Decimal("0.5"),
        execution_anchor_confirmed_at=at,
        execution_anchor_available=True,
    )
    snapshot = V50CognitiveOpportunitySnapshot(
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
        execution_stop_distance_ticks=Decimal("50"),
        target_refinement_available=True,
        stop_refinement_available=True,
    )
    geometry = V50GeometryProposal(
        identity=GEOMETRY_IDENTITY,
        decision=V50GeometryDecision.READY,
        side=CapitalizerSide.LONG,
        entry_price=Decimal("100"),
        stop_mode=V50StopMode.EXECUTION_M1,
        stop_price=Decimal("99.5"),
        stop_risk_price=Decimal("0.5"),
        stop_to_noise_ratio=Decimal("5"),
        t1=target,
        t1_reward_r=Decimal("2"),
        runner=None,
        runner_reward_r=None,
        reasons=("TEST_READY",),
    )
    return snapshot, geometry


def test_v50_candidate_is_adapted_into_existing_master_frame_contract() -> None:
    snapshot, geometry = _snapshot()
    result = adapt_v50_to_master_context(snapshot, geometry)
    assert result.master_frame_required is True
    assert result.source_strategy_bypassed is False
    assert result.outcome_visible is False
    assert result.context.event_is_fresh is True
    assert result.context.destination_context_known is True
    assert result.context.destination_available is True
    assert result.context.failure_state_fingerprint == "V50:test"
    assert "V50_MASTER_FRAME_REQUIRED=YES" in result.context.observation_tokens


def test_stale_v50_state_reaches_master_as_not_fresh() -> None:
    snapshot, geometry = _snapshot()
    stale_state = replace(
        snapshot.cognitive.state,
        h1_freshness=V50H1Freshness.STALE,
    )
    stale_cognition = replace(snapshot.cognitive, state=stale_state)
    result = adapt_v50_to_master_context(
        replace(snapshot, cognitive=stale_cognition),
        geometry,
    )
    assert result.context.event_is_fresh is False
