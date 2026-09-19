from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from qore.infrastructure.trader_lab.capitalizer_contract import (
    CapitalizerDecision,
    CapitalizerSession,
    CapitalizerStrategyIdentity,
    EvidenceStrength,
    ExecutionQuality,
    MarketState,
    allowed_markets,
)
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import (
    CapitalizerExposurePosition,
    CapitalizerSide,
    factor_exposures,
)
from qore.infrastructure.trader_lab.capitalizer_memory import (
    CapitalizerLossCause,
    CapitalizerLossMemory,
    CapitalizerSessionLedger,
)
from qore.infrastructure.trader_lab.capitalizer_reasoning import (
    reason_capitalizer_opportunity,
)
from qore.infrastructure.trader_lab.capitalizer_situation_model import (
    CapitalizerExecutionState,
    CapitalizerSituationModel,
)


def _execution(quality: ExecutionQuality = ExecutionQuality.GOOD) -> CapitalizerExecutionState:
    return CapitalizerExecutionState(
        spread_points=Decimal("0.1"),
        commission_cost_r=Decimal("0.02"),
        expected_slippage_r=Decimal("0.01"),
        quote_age_ms=50,
        observed_latency_ms=20,
        quality=quality,
    )


def _situation(
    *,
    symbol: str = "USDJPY",
    session: CapitalizerSession = CapitalizerSession.ASIA,
    hypothesis_id: str = "H-1",
    source_event_id: str = "E-1",
    execution_quality: ExecutionQuality = ExecutionQuality.GOOD,
    evidence_strength: EvidenceStrength = EvidenceStrength.HIGH,
    trigger_ready: bool = True,
    displacement_confirmed: bool = True,
    destination_available: bool = True,
    late_entry: bool = False,
    correlated_exposure_blocked: bool = False,
    contradictions: tuple[str, ...] = (),
    failure_state_fingerprint: str | None = None,
) -> CapitalizerSituationModel:
    return CapitalizerSituationModel(
        symbol=symbol,
        session=session,
        observed_at=datetime(2026, 9, 19, 10, 0, tzinfo=UTC),
        hypothesis_id=hypothesis_id,
        source_event_id=source_event_id,
        event_generation=1,
        market_state=MarketState.DISPLACEMENT,
        evidence_strength=evidence_strength,
        execution=_execution(execution_quality),
        strategy_trigger_ready=trigger_ready,
        displacement_confirmed=displacement_confirmed,
        destination_available=destination_available,
        late_entry=late_entry,
        correlated_exposure_blocked=correlated_exposure_blocked,
        contradictions=contradictions,
        failure_state_fingerprint=failure_state_fingerprint,
    )


def test_strategy_identity_is_fail_closed_and_has_no_authority() -> None:
    identity = CapitalizerStrategyIdentity()
    assert identity.runtime_mutation_allowed is False
    assert identity.risk_authority is False
    assert identity.production_authority is False
    with pytest.raises(ValueError, match="session execution ceiling"):
        CapitalizerStrategyIdentity(max_executions_per_session=3)


def test_session_universe_is_frozen() -> None:
    assert allowed_markets(CapitalizerSession.ASIA) == frozenset(
        {"USDJPY", "AUDJPY", "AUDUSD", "GBPJPY"}
    )
    assert allowed_markets(CapitalizerSession.LONDON) == frozenset({"EURUSD", "GBPUSD"})
    assert allowed_markets(CapitalizerSession.NEW_YORK) == frozenset(
        {"XAUUSD", "USDCAD", "NAS100"}
    )


def test_clean_causal_state_can_reach_execute_without_granting_capital_authority() -> None:
    decision = reason_capitalizer_opportunity(
        situation=_situation(),
        ledger=CapitalizerSessionLedger(CapitalizerSession.ASIA),
        loss_memory=CapitalizerLossMemory(),
    )
    assert decision.decision is CapitalizerDecision.EXECUTE
    assert "ADVERSARIAL_CHECK_PASSED" in decision.reasons


def test_low_evidence_or_degraded_execution_waits() -> None:
    low = reason_capitalizer_opportunity(
        situation=_situation(evidence_strength=EvidenceStrength.LOW),
        ledger=CapitalizerSessionLedger(CapitalizerSession.ASIA),
        loss_memory=CapitalizerLossMemory(),
    )
    degraded = reason_capitalizer_opportunity(
        situation=_situation(execution_quality=ExecutionQuality.DEGRADED),
        ledger=CapitalizerSessionLedger(CapitalizerSession.ASIA),
        loss_memory=CapitalizerLossMemory(),
    )
    assert low.decision is CapitalizerDecision.WAIT
    assert degraded.decision is CapitalizerDecision.WAIT


def test_bad_execution_and_late_entry_fail_closed() -> None:
    bad = reason_capitalizer_opportunity(
        situation=_situation(execution_quality=ExecutionQuality.BAD),
        ledger=CapitalizerSessionLedger(CapitalizerSession.ASIA),
        loss_memory=CapitalizerLossMemory(),
    )
    late = reason_capitalizer_opportunity(
        situation=_situation(late_entry=True),
        ledger=CapitalizerSessionLedger(CapitalizerSession.ASIA),
        loss_memory=CapitalizerLossMemory(),
    )
    assert bad.decision is CapitalizerDecision.ABSTAIN
    assert late.decision is CapitalizerDecision.ABSTAIN


def test_abstain_kills_hypothesis_and_source_event() -> None:
    ledger = CapitalizerSessionLedger(CapitalizerSession.ASIA)
    killed = ledger.record_decision(
        decision=CapitalizerDecision.ABSTAIN,
        hypothesis_id="H-1",
        source_event_id="E-1",
    )
    decision = reason_capitalizer_opportunity(
        situation=_situation(),
        ledger=killed,
        loss_memory=CapitalizerLossMemory(),
    )
    assert decision.decision is CapitalizerDecision.ABSTAIN
    assert "HYPOTHESIS_ALREADY_KILLED" in decision.reasons
    assert "SOURCE_EVENT_ALREADY_KILLED" in decision.reasons


def test_session_budget_is_hard_ceiling_of_two_executions() -> None:
    ledger = CapitalizerSessionLedger(CapitalizerSession.ASIA)
    ledger = ledger.record_decision(
        decision=CapitalizerDecision.EXECUTE,
        hypothesis_id="H-1",
        source_event_id="E-1",
    )
    ledger = ledger.record_decision(
        decision=CapitalizerDecision.EXECUTE,
        hypothesis_id="H-2",
        source_event_id="E-2",
    )
    decision = reason_capitalizer_opportunity(
        situation=_situation(hypothesis_id="H-3", source_event_id="E-3"),
        ledger=ledger,
        loss_memory=CapitalizerLossMemory(),
    )
    assert ledger.execution_budget_remaining == 0
    assert decision.decision is CapitalizerDecision.ABSTAIN
    assert "SESSION_EXECUTION_BUDGET_EXHAUSTED" in decision.reasons


def test_unresolved_same_failure_state_blocks_repetition() -> None:
    loss = CapitalizerLossCause(
        loss_id="L-1",
        symbol="USDJPY",
        session=CapitalizerSession.ASIA,
        hypothesis_id="OLD-H",
        failure_state_fingerprint="fp-failed-break-no-displacement",
        realized_r=Decimal("-1"),
        causes=("FAILED_BREAK", "NO_DISPLACEMENT"),
    )
    decision = reason_capitalizer_opportunity(
        situation=_situation(
            hypothesis_id="NEW-H",
            source_event_id="NEW-E",
            failure_state_fingerprint="fp-failed-break-no-displacement",
        ),
        ledger=CapitalizerSessionLedger(CapitalizerSession.ASIA),
        loss_memory=CapitalizerLossMemory(unresolved=(loss,)),
    )
    assert decision.decision is CapitalizerDecision.ABSTAIN
    assert "UNRESOLVED_FAILURE_STATE_REPEAT" in decision.reasons


def test_correlated_exposure_is_wait_not_a_second_blind_bet() -> None:
    decision = reason_capitalizer_opportunity(
        situation=_situation(correlated_exposure_blocked=True),
        ledger=CapitalizerSessionLedger(CapitalizerSession.ASIA),
        loss_memory=CapitalizerLossMemory(),
    )
    assert decision.decision is CapitalizerDecision.WAIT
    assert "CORRELATED_EXPOSURE_BLOCKED" in decision.reasons


def test_exposure_graph_reveals_repeated_jpy_factor() -> None:
    exposures = factor_exposures(
        (
            CapitalizerExposurePosition(
                symbol="USDJPY",
                side=CapitalizerSide.LONG,
                risk_r=Decimal("0.10"),
            ),
            CapitalizerExposurePosition(
                symbol="AUDJPY",
                side=CapitalizerSide.LONG,
                risk_r=Decimal("0.10"),
            ),
            CapitalizerExposurePosition(
                symbol="GBPJPY",
                side=CapitalizerSide.LONG,
                risk_r=Decimal("0.10"),
            ),
        )
    )
    by_factor = {item.factor: item for item in exposures}
    assert by_factor["JPY"].net_r == Decimal("-0.30")
    assert by_factor["JPY"].gross_r == Decimal("0.30")


def test_capitalization_governor_is_non_authoritative_and_fail_closed() -> None:
    from qore.infrastructure.trader_lab.capitalizer_contract import CapitalizationPosture
    from qore.infrastructure.trader_lab.capitalizer_governor import (
        CapitalizerPortfolioState,
        recommend_capitalization_posture,
    )

    stopped = recommend_capitalization_posture(
        CapitalizerPortfolioState(day_stop_required=True)
    )
    selective = recommend_capitalization_posture(
        CapitalizerPortfolioState(loss_cluster_active=True)
    )
    assert stopped.posture is CapitalizationPosture.STOP_DAY
    assert stopped.grants_capital_authority is False
    assert selective.posture is CapitalizationPosture.HIGH_SELECTIVITY
    assert selective.grants_capital_authority is False


def test_cognitive_engine_records_execute_and_preserves_risk_sovereignty() -> None:
    from qore.infrastructure.trader_lab.capitalizer_cognitive_engine import evaluate_capitalizer
    from qore.infrastructure.trader_lab.capitalizer_governor import CapitalizerPortfolioState

    evaluation = evaluate_capitalizer(
        situation=_situation(),
        ledger=CapitalizerSessionLedger(CapitalizerSession.ASIA),
        loss_memory=CapitalizerLossMemory(),
        portfolio_state=CapitalizerPortfolioState(),
    )
    assert evaluation.final_decision is CapitalizerDecision.EXECUTE
    assert evaluation.ledger_after.executions == 1
    assert evaluation.grants_capital_authority is False


def test_governor_stop_day_forces_abstain_and_kills_current_hypothesis() -> None:
    from qore.infrastructure.trader_lab.capitalizer_cognitive_engine import evaluate_capitalizer
    from qore.infrastructure.trader_lab.capitalizer_governor import CapitalizerPortfolioState

    evaluation = evaluate_capitalizer(
        situation=_situation(),
        ledger=CapitalizerSessionLedger(CapitalizerSession.ASIA),
        loss_memory=CapitalizerLossMemory(),
        portfolio_state=CapitalizerPortfolioState(day_stop_required=True),
    )
    assert evaluation.final_decision is CapitalizerDecision.ABSTAIN
    assert "H-1" in evaluation.ledger_after.killed_hypotheses
    assert "E-1" in evaluation.ledger_after.killed_source_events


def test_high_selectivity_requires_high_evidence_before_execute() -> None:
    from qore.infrastructure.trader_lab.capitalizer_cognitive_engine import evaluate_capitalizer
    from qore.infrastructure.trader_lab.capitalizer_governor import CapitalizerPortfolioState

    evaluation = evaluate_capitalizer(
        situation=_situation(evidence_strength=EvidenceStrength.MEDIUM),
        ledger=CapitalizerSessionLedger(CapitalizerSession.ASIA),
        loss_memory=CapitalizerLossMemory(),
        portfolio_state=CapitalizerPortfolioState(loss_cluster_active=True),
    )
    assert evaluation.final_decision is CapitalizerDecision.WAIT
    assert evaluation.ledger_after.executions == 0


def test_session_handoff_preserves_causal_day_state() -> None:
    from qore.infrastructure.trader_lab.capitalizer_exposure_graph import factor_exposures
    from qore.infrastructure.trader_lab.capitalizer_memory import CapitalizerDailyJourney
    from qore.infrastructure.trader_lab.capitalizer_session_handoff import build_session_handoff

    ledger = CapitalizerSessionLedger(CapitalizerSession.ASIA).record_decision(
        decision=CapitalizerDecision.EXECUTE,
        hypothesis_id="ASIA-H-1",
        source_event_id="ASIA-E-1",
    )
    journey = CapitalizerDailyJourney(
        completed_sessions=(CapitalizerSession.ASIA,),
        consumed_destinations=frozenset({"ASIA_HIGH"}),
        dominant_factors=("JPY_WEAKNESS",),
        realized_r=Decimal("0.35"),
    )
    exposures = factor_exposures(
        (
            CapitalizerExposurePosition(
                symbol="USDJPY",
                side=CapitalizerSide.LONG,
                risk_r=Decimal("0.10"),
            ),
        )
    )
    handoff = build_session_handoff(
        from_session=CapitalizerSession.ASIA,
        to_session=CapitalizerSession.LONDON,
        ledger=ledger,
        journey=journey,
        loss_memory=CapitalizerLossMemory(),
        factor_exposure_state=exposures,
    )
    assert handoff.prior_executions == 1
    assert handoff.consumed_destinations == frozenset({"ASIA_HIGH"})
    assert handoff.dominant_factors == ("JPY_WEAKNESS",)
    assert handoff.realized_day_r == Decimal("0.35")


def test_session_handoff_cannot_move_backward() -> None:
    from qore.infrastructure.trader_lab.capitalizer_memory import CapitalizerDailyJourney
    from qore.infrastructure.trader_lab.capitalizer_session_handoff import build_session_handoff

    with pytest.raises(ValueError, match="Asia -> London -> New York"):
        build_session_handoff(
            from_session=CapitalizerSession.LONDON,
            to_session=CapitalizerSession.ASIA,
            ledger=CapitalizerSessionLedger(CapitalizerSession.LONDON),
            journey=CapitalizerDailyJourney(
                completed_sessions=(CapitalizerSession.LONDON,)
            ),
            loss_memory=CapitalizerLossMemory(),
            factor_exposure_state=(),
        )


def test_future_observation_is_rejected_from_situation_model() -> None:
    from datetime import timedelta

    from qore.infrastructure.trader_lab.capitalizer_situation_model import (
        CapitalizerCausalObservation,
    )

    decision_time = datetime(2026, 9, 19, 10, 0, tzinfo=UTC)
    future = CapitalizerCausalObservation(
        name="future_bar",
        observed_at=decision_time + timedelta(seconds=1),
        value_token="KNOWN_LATER",
    )
    with pytest.raises(ValueError, match="future observation"):
        CapitalizerSituationModel(
            symbol="USDJPY",
            session=CapitalizerSession.ASIA,
            observed_at=decision_time,
            hypothesis_id="H-FUTURE",
            source_event_id="E-FUTURE",
            event_generation=1,
            market_state=MarketState.DISPLACEMENT,
            evidence_strength=EvidenceStrength.HIGH,
            execution=_execution(),
            strategy_trigger_ready=True,
            displacement_confirmed=True,
            destination_available=True,
            late_entry=False,
            correlated_exposure_blocked=False,
            observations=(future,),
        )


def test_confidence_is_evidence_bound_not_a_free_percentage() -> None:
    from qore.infrastructure.trader_lab.capitalizer_confidence import (
        CapitalizerEvidenceCalibration,
        CapitalizerEvidenceSource,
        CapitalizerKnowledgeState,
        assess_knowledge_state,
    )

    calibration = CapitalizerEvidenceCalibration(
        state_family_id="ASIA_USDJPY_DISPLACEMENT",
        source=CapitalizerEvidenceSource.WALK_FORWARD,
        source_fingerprint="a" * 64,
        observations=120,
        mean_r=Decimal("0.08"),
        strength=EvidenceStrength.HIGH,
    )
    assert (
        assess_knowledge_state(calibration=calibration, contradictions=())
        is CapitalizerKnowledgeState.KNOWN
    )
    assert (
        assess_knowledge_state(calibration=calibration, contradictions=("DOL_CONFLICT",))
        is CapitalizerKnowledgeState.CONFLICTED
    )
    with pytest.raises(ValueError, match="canonical sha256"):
        CapitalizerEvidenceCalibration(
            state_family_id="BAD",
            source=CapitalizerEvidenceSource.DEVELOPMENT_REPLAY,
            source_fingerprint="not-a-sha",
            observations=1,
            mean_r=Decimal("0"),
            strength=EvidenceStrength.LOW,
        )


def test_experience_memory_is_market_session_bound_and_runtime_immutable() -> None:
    from qore.infrastructure.trader_lab.capitalizer_confidence import (
        CapitalizerEvidenceCalibration,
        CapitalizerEvidenceSource,
    )
    from qore.infrastructure.trader_lab.capitalizer_experience_memory import (
        CapitalizerExperienceMemory,
        CapitalizerExperienceProfile,
    )

    calibration = CapitalizerEvidenceCalibration(
        state_family_id="ASIA_USDJPY_REVERSAL",
        source=CapitalizerEvidenceSource.WALK_FORWARD,
        source_fingerprint="b" * 64,
        observations=80,
        mean_r=Decimal("0.06"),
        strength=EvidenceStrength.MEDIUM,
    )
    profile = CapitalizerExperienceProfile(
        strategy_identity="QORE_CAPITALIZER_COGNITIVE_SCALPER_V1",
        symbol="USDJPY",
        session=CapitalizerSession.ASIA,
        state_family_id="ASIA_USDJPY_REVERSAL",
        calibration=calibration,
        behavior_tags=("FAILED_BREAK", "RECLAIM"),
    )
    memory = CapitalizerExperienceMemory(profiles=(profile,))
    assert (
        memory.lookup(
            symbol="USDJPY",
            session=CapitalizerSession.ASIA,
            state_family_id="ASIA_USDJPY_REVERSAL",
        )
        == profile
    )
    with pytest.raises(ValueError, match="cannot self-train"):
        CapitalizerExperienceMemory(profiles=(profile,), runtime_mutation_allowed=True)


def test_journey_returns_only_available_unconsumed_destinations() -> None:
    from qore.infrastructure.trader_lab.capitalizer_journey import (
        CapitalizerDestinationState,
        CapitalizerJourneyStage,
        CapitalizerJourneyState,
    )

    journey = CapitalizerJourneyState(
        stage=CapitalizerJourneyStage.DELIVERY,
        destinations=(
            CapitalizerDestinationState(
                destination_id="D2",
                family="LOCAL_LIQUIDITY",
                distance_r=Decimal("0.8"),
                consumed=False,
                structurally_available=True,
                evidence_strength=EvidenceStrength.HIGH,
            ),
            CapitalizerDestinationState(
                destination_id="D1",
                family="LOCAL_LIQUIDITY",
                distance_r=Decimal("0.3"),
                consumed=False,
                structurally_available=True,
                evidence_strength=EvidenceStrength.HIGH,
            ),
            CapitalizerDestinationState(
                destination_id="DONE",
                family="LOCAL_LIQUIDITY",
                distance_r=Decimal("0.1"),
                consumed=True,
                structurally_available=True,
                evidence_strength=EvidenceStrength.HIGH,
            ),
        ),
    )
    assert tuple(item.destination_id for item in journey.eligible_destinations()) == ("D1", "D2")


def test_position_intelligence_exits_invalidation_and_cannot_grant_reentry() -> None:
    from qore.infrastructure.trader_lab.capitalizer_position_intelligence import (
        CapitalizerOpenPositionState,
        CapitalizerPositionAction,
        reason_open_position,
        rearm_is_genuinely_new,
    )

    position = CapitalizerOpenPositionState(
        hypothesis_id="H-OLD",
        source_event_id="E-OLD",
        invalidated=True,
        destination_reached=False,
        structural_protection_available=False,
    )
    recommendation = reason_open_position(position)
    assert recommendation.action is CapitalizerPositionAction.EXIT
    assert recommendation.grants_reentry is False
    assert recommendation.grants_capital_authority is False

    new_situation = _situation(hypothesis_id="H-NEW", source_event_id="E-NEW")
    assert (
        rearm_is_genuinely_new(
            prior_hypothesis_id="H-OLD",
            prior_source_event_id="E-OLD",
            prior_event_generation=0,
            new_situation=new_situation,
        )
        is True
    )
    assert (
        rearm_is_genuinely_new(
            prior_hypothesis_id="H-NEW",
            prior_source_event_id="E-OLD",
            prior_event_generation=0,
            new_situation=new_situation,
        )
        is False
    )
