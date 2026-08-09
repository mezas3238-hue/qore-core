from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from qore.domain.events import CorrelationId
from qore.functional.decisions import (
    DecisionId,
    DecisionMetadata,
    DecisionOutcome,
    DecisionPriority,
    DecisionReason,
    DecisionReasonCode,
    DecisionStatus,
    DecisionType,
    FunctionalDecision,
)
from qore.infrastructure.historical_dataset import (
    HistoricalDatasetId,
    HistoricalDatasetNormalizationVersion,
    HistoricalDatasetRevisionId,
    HistoricalDatasetSchemaVersion,
    HistoricalOhlcDatasetScope,
    build_historical_ohlc_replay_dataset,
)
from qore.infrastructure.historical_market_data import HistoricalOhlcWindow
from qore.infrastructure.market_data import (
    Instrument,
    MarketDataSnapshotId,
    OhlcSnapshot,
    Timeframe,
)
from qore.infrastructure.order_intent import (
    ExecutionIdempotencyKey,
    ExecutionInstrument,
    OrderIntent,
    OrderIntentId,
    OrderPrice,
    OrderQuantity,
    OrderSide,
    OrderType,
)
from qore.infrastructure.ports import (
    AdapterId,
    ExternalRequestMetadata,
    ExternalSourceDescriptor,
    PortName,
    SourceId,
)
from qore.infrastructure.proprietary_accounts import CurrencyCode, MoneyAmount
from qore.infrastructure.replay_availability import (
    ReplayAvailabilityBasis,
    ReplayAvailabilityEvidenceReference,
    ReplayMarketDataObservation,
    ReplayObservationId,
)
from qore.infrastructure.research_economic_evidence import (
    ResearchEconomicEvidenceReference,
    ResearchEconomicResultId,
    ResearchExecutionIntentEvidenceId,
    ResearchFillEvidence,
    ResearchFillId,
    ResearchGrossEconomicResult,
    ResearchReturnObservation,
    ResearchReturnObservationId,
    build_research_execution_intent_evidence,
    build_research_fill_evidence,
    build_research_gross_economic_result,
    build_research_return_observation,
)
from qore.infrastructure.research_oos_performance import (
    ResearchOosPerformanceEvidenceId,
    build_research_oos_performance_evidence,
)
from qore.infrastructure.research_performance_statistics import (
    ResearchPerformanceSnapshotId,
)
from qore.infrastructure.research_run import (
    ResearchExecutionModelId,
    ResearchRandomnessMode,
    ResearchReplayPolicyVersion,
    ResearchRunEvidence,
    ResearchRunId,
    ResearchSoftwareRevision,
    ResearchStrategyConfigurationId,
    build_research_run_evidence,
)
from qore.infrastructure.research_temporal_evaluation import (
    ResearchEvaluationWindow,
    ResearchTemporalEvaluationPlan,
    ResearchTemporalEvaluationPlanId,
    ResearchWalkForwardFold,
    build_research_temporal_evaluation_plan,
)
from qore.kernel.result import Failure, Success

_BASE = datetime(2026, 8, 9, 12, 0, tzinfo=UTC)
_USD = CurrencyCode("USD")
_MARKET_SOURCE = ExternalSourceDescriptor(
    adapter_id=AdapterId(UUID("70000000-0000-0000-0000-000000000001")),
    source_id=SourceId(UUID("70000000-0000-0000-0000-000000000002")),
    port_name=PortName("market-data.research-oos-test"),
)
_EXECUTION_SOURCE = ExternalSourceDescriptor(
    adapter_id=AdapterId(UUID("70000000-0000-0000-0000-000000000003")),
    source_id=SourceId(UUID("70000000-0000-0000-0000-000000000004")),
    port_name=PortName("execution.research-oos-test"),
)
_EXECUTION_MODEL = ResearchExecutionModelId(
    UUID("70000000-0000-0000-0000-000000000005")
)


def _uuid(suffix: int) -> UUID:
    return UUID(f"70000000-0000-0000-0000-{suffix:012d}")


def _money(value: str) -> MoneyAmount:
    return MoneyAmount(currency=_USD, amount=Decimal(value))


def _run() -> ResearchRunEvidence:
    instrument = Instrument("EURUSD")
    timeframe = Timeframe(300)
    window = HistoricalOhlcWindow(
        instrument=instrument,
        timeframe=timeframe,
        opened_at=_BASE,
        closed_at=_BASE + timedelta(hours=4),
    )
    snapshot = OhlcSnapshot(
        snapshot_id=MarketDataSnapshotId(_uuid(10)),
        instrument=instrument,
        source=_MARKET_SOURCE,
        timeframe=timeframe,
        opened_at=_BASE,
        closed_at=_BASE + timedelta(minutes=5),
        open=1.10,
        high=1.11,
        low=1.09,
        close=1.105,
    )
    replay = ReplayMarketDataObservation(
        observation_id=ReplayObservationId(_uuid(11)),
        payload=snapshot,
        availability_evidence_at=snapshot.closed_at,
        available_at=snapshot.closed_at,
        availability_basis=ReplayAvailabilityBasis.STRUCTURAL_BOUNDARY,
        availability_evidence_ref=ReplayAvailabilityEvidenceReference(_uuid(12)),
    )
    dataset = build_historical_ohlc_replay_dataset(
        dataset_id=HistoricalDatasetId(_uuid(13)),
        revision_id=HistoricalDatasetRevisionId(_uuid(14)),
        parent_revision_id=None,
        revision_reason=None,
        scope=HistoricalOhlcDatasetScope(source=_MARKET_SOURCE, window=window),
        assembled_at=_BASE + timedelta(days=1),
        schema_version=HistoricalDatasetSchemaVersion("ohlc-replay-v1"),
        normalization_version=HistoricalDatasetNormalizationVersion("ingestion-v1"),
        observations=(replay,),
    )
    assert isinstance(dataset, Success)
    built = build_research_run_evidence(
        run_id=ResearchRunId(_uuid(15)),
        created_at=_BASE + timedelta(days=2),
        datasets=(dataset.value.manifest,),
        replay_policy_version=ResearchReplayPolicyVersion("point-in-time-v1"),
        simulated_start=_BASE,
        simulated_end=_BASE + timedelta(hours=4),
        strategy_configuration_id=ResearchStrategyConfigurationId(_uuid(16)),
        software_revision=ResearchSoftwareRevision("231ffe3b"),
        execution_model_id=_EXECUTION_MODEL,
        transaction_cost_model_id=None,
        randomness_mode=ResearchRandomnessMode.DETERMINISTIC,
        random_seed=None,
    )
    assert isinstance(built, Success)
    return built.value


def _window(start_minutes: int, end_minutes: int) -> ResearchEvaluationWindow:
    return ResearchEvaluationWindow(
        opened_at=_BASE + timedelta(minutes=start_minutes),
        closed_at=_BASE + timedelta(minutes=end_minutes),
    )


def _plan(run: ResearchRunEvidence) -> ResearchTemporalEvaluationPlan:
    folds = (
        ResearchWalkForwardFold(
            fold_number=1,
            in_sample=_window(0, 60),
            out_of_sample=_window(60, 90),
        ),
        ResearchWalkForwardFold(
            fold_number=2,
            in_sample=_window(30, 90),
            out_of_sample=_window(90, 120),
        ),
    )
    built = build_research_temporal_evaluation_plan(
        plan_id=ResearchTemporalEvaluationPlanId(_uuid(20)),
        run=run,
        folds=folds,
        created_at=_BASE + timedelta(days=3),
    )
    assert isinstance(built, Success)
    return built.value


def _decision(suffix: int, at: datetime) -> FunctionalDecision:
    return FunctionalDecision(
        decision_id=DecisionId(_uuid(1000 + suffix)),
        timestamp=at,
        decision_type=DecisionType("core.trade"),
        status=DecisionStatus.RESOLVED,
        priority=DecisionPriority.NORMAL,
        metadata=DecisionMetadata(
            correlation_id=CorrelationId(_uuid(1100 + suffix))
        ),
        reasons=(
            DecisionReason(
                code=DecisionReasonCode("research.oos"),
                summary="OOS return evidence",
            ),
        ),
        outcome=DecisionOutcome.APPROVED,
    )


def _fill(
    run: ResearchRunEvidence,
    *,
    side: OrderSide,
    suffix: int,
    at: datetime,
) -> ResearchFillEvidence:
    decision_at = at - timedelta(seconds=4)
    intent = OrderIntent(
        intent_id=OrderIntentId(_uuid(1200 + suffix)),
        idempotency_key=ExecutionIdempotencyKey(_uuid(1300 + suffix)),
        instrument=ExecutionInstrument("EUR_USD"),
        side=side,
        order_type=OrderType.MARKET,
        quantity=OrderQuantity(Decimal("1")),
        created_at=decision_at + timedelta(seconds=1),
        metadata=ExternalRequestMetadata(
            correlation_id=CorrelationId(_uuid(1400 + suffix))
        ),
    )
    intent_evidence = build_research_execution_intent_evidence(
        evidence_id=ResearchExecutionIntentEvidenceId(_uuid(1500 + suffix)),
        run=run,
        decision=_decision(suffix, decision_at),
        intent=intent,
        evidenced_at=decision_at + timedelta(seconds=2),
    )
    assert isinstance(intent_evidence, Success)
    fill = build_research_fill_evidence(
        fill_id=ResearchFillId(_uuid(1600 + suffix)),
        intent_evidence=intent_evidence.value,
        source=_EXECUTION_SOURCE,
        price=OrderPrice(Decimal("1.10") if side is OrderSide.BUY else Decimal("1.11")),
        quantity=OrderQuantity(Decimal("1")),
        filled_at=at,
        evidence_ref=ResearchEconomicEvidenceReference(_uuid(1700 + suffix)),
    )
    assert isinstance(fill, Success)
    return fill.value


def _return(
    run: ResearchRunEvidence,
    *,
    suffix: int,
    valued_at: datetime,
    pnl: str,
) -> ResearchReturnObservation:
    entry = _fill(
        run,
        side=OrderSide.BUY,
        suffix=suffix * 2,
        at=valued_at - timedelta(seconds=2),
    )
    exit_fill = _fill(
        run,
        side=OrderSide.SELL,
        suffix=suffix * 2 + 1,
        at=valued_at - timedelta(seconds=1),
    )
    gross = build_research_gross_economic_result(
        result_id=ResearchEconomicResultId(_uuid(1800 + suffix)),
        run=run,
        entry_fills=(entry,),
        exit_fills=(exit_fill,),
        gross_pnl=_money(pnl),
        valued_at=valued_at,
        evidence_ref=ResearchEconomicEvidenceReference(_uuid(1900 + suffix)),
    )
    assert isinstance(gross, Success)
    result = build_research_return_observation(
        observation_id=ResearchReturnObservationId(_uuid(2000 + suffix)),
        source_result=gross.value,
        capital_basis=_money("1000"),
        observed_at=valued_at + timedelta(seconds=1),
    )
    assert isinstance(result, Success)
    return result.value


def _snapshot_ids() -> tuple[ResearchPerformanceSnapshotId, ...]:
    return (
        ResearchPerformanceSnapshotId(_uuid(2100)),
        ResearchPerformanceSnapshotId(_uuid(2101)),
    )


def test_oos_evidence_partitions_returns_and_derives_fold_statistics() -> None:
    run = _run()
    plan = _plan(run)
    first = _return(
        run,
        suffix=1,
        valued_at=_BASE + timedelta(minutes=70),
        pnl="100",
    )
    second = _return(
        run,
        suffix=2,
        valued_at=_BASE + timedelta(minutes=100),
        pnl="-50",
    )
    built = build_research_oos_performance_evidence(
        evidence_id=ResearchOosPerformanceEvidenceId(_uuid(2200)),
        plan=plan,
        observations=(second, first),
        statistics_snapshot_ids=_snapshot_ids(),
        observed_at=_BASE + timedelta(days=3, seconds=1),
    )
    assert isinstance(built, Success)
    evidence = built.value
    assert evidence.fold_performance[0].statistics.observations == (first,)
    assert evidence.fold_performance[1].statistics.observations == (second,)
    assert evidence.fold_performance[0].statistics.mean_return == Decimal("0.1")
    assert evidence.fold_performance[1].statistics.mean_return == Decimal("-0.05")


def test_oos_evidence_uses_half_open_boundaries() -> None:
    run = _run()
    plan = _plan(run)
    fold_one = _return(
        run,
        suffix=10,
        valued_at=_BASE + timedelta(minutes=89, seconds=59),
        pnl="10",
    )
    exact_boundary = _return(
        run,
        suffix=11,
        valued_at=_BASE + timedelta(minutes=90),
        pnl="20",
    )
    built = build_research_oos_performance_evidence(
        evidence_id=ResearchOosPerformanceEvidenceId(_uuid(2300)),
        plan=plan,
        observations=(fold_one, exact_boundary),
        statistics_snapshot_ids=_snapshot_ids(),
        observed_at=_BASE + timedelta(days=3, seconds=1),
    )
    assert isinstance(built, Success)
    assert built.value.fold_performance[0].statistics.observations == (fold_one,)
    assert built.value.fold_performance[1].statistics.observations == (exact_boundary,)


def test_oos_evidence_rejects_returns_outside_every_oos_window() -> None:
    run = _run()
    plan = _plan(run)
    in_sample_only = _return(
        run,
        suffix=20,
        valued_at=_BASE + timedelta(minutes=50),
        pnl="10",
    )
    second_fold = _return(
        run,
        suffix=21,
        valued_at=_BASE + timedelta(minutes=100),
        pnl="20",
    )
    built = build_research_oos_performance_evidence(
        evidence_id=ResearchOosPerformanceEvidenceId(_uuid(2400)),
        plan=plan,
        observations=(in_sample_only, second_fold),
        statistics_snapshot_ids=_snapshot_ids(),
        observed_at=_BASE + timedelta(days=3, seconds=1),
    )
    assert isinstance(built, Failure)


def test_oos_evidence_requires_observations_for_every_fold() -> None:
    run = _run()
    plan = _plan(run)
    only_first = _return(
        run,
        suffix=30,
        valued_at=_BASE + timedelta(minutes=70),
        pnl="10",
    )
    built = build_research_oos_performance_evidence(
        evidence_id=ResearchOosPerformanceEvidenceId(_uuid(2500)),
        plan=plan,
        observations=(only_first,),
        statistics_snapshot_ids=_snapshot_ids(),
        observed_at=_BASE + timedelta(days=3, seconds=1),
    )
    assert isinstance(built, Failure)
    assert "at least one OOS return" in str(built.error)


def test_oos_evidence_rejects_fill_reuse_across_folds() -> None:
    run = _run()
    plan = _plan(run)
    first = _return(
        run,
        suffix=40,
        valued_at=_BASE + timedelta(minutes=70),
        pnl="10",
    )
    assert isinstance(first.source_result, ResearchGrossEconomicResult)
    copied_result = replace(
        first.source_result,
        result_id=ResearchEconomicResultId(_uuid(2600)),
        valued_at=_BASE + timedelta(minutes=100),
    )
    copied_return = replace(
        first,
        observation_id=ResearchReturnObservationId(_uuid(2601)),
        source_result=copied_result,
        observed_at=_BASE + timedelta(minutes=100, seconds=1),
    )
    built = build_research_oos_performance_evidence(
        evidence_id=ResearchOosPerformanceEvidenceId(_uuid(2602)),
        plan=plan,
        observations=(first, copied_return),
        statistics_snapshot_ids=_snapshot_ids(),
        observed_at=_BASE + timedelta(days=3, seconds=1),
    )
    assert isinstance(built, Failure)
    assert "reuse economic fill evidence" in str(built.error)


def test_oos_evidence_claims_no_blindness_or_statistical_significance() -> None:
    run = _run()
    plan = _plan(run)
    first = _return(
        run,
        suffix=50,
        valued_at=_BASE + timedelta(minutes=70),
        pnl="10",
    )
    second = _return(
        run,
        suffix=51,
        valued_at=_BASE + timedelta(minutes=100),
        pnl="20",
    )
    built = build_research_oos_performance_evidence(
        evidence_id=ResearchOosPerformanceEvidenceId(_uuid(2700)),
        plan=plan,
        observations=(first, second),
        statistics_snapshot_ids=_snapshot_ids(),
        observed_at=_BASE + timedelta(days=3, seconds=1),
    )
    assert isinstance(built, Success)
    evidence = built.value
    assert not hasattr(evidence, "analyst_blind")
    assert not hasattr(evidence, "pre_registered")
    assert not hasattr(evidence, "p_value")
    assert not hasattr(evidence, "significant")
