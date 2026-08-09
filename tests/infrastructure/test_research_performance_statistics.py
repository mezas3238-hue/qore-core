from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest

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
    ResearchCashCostCategory,
    ResearchCashCostEvidence,
    ResearchCashCostStatus,
    ResearchEconomicEvidenceReference,
    ResearchEconomicResultId,
    ResearchExecutionIntentEvidenceId,
    ResearchFillEvidence,
    ResearchFillId,
    ResearchGrossEconomicResult,
    ResearchReturnObservation,
    ResearchReturnObservationId,
    build_research_cash_cost_coverage,
    build_research_execution_intent_evidence,
    build_research_fill_evidence,
    build_research_gross_economic_result,
    build_research_net_economic_result,
    build_research_return_observation,
)
from qore.infrastructure.research_performance_statistics import (
    ResearchPerformanceSnapshotId,
    ResearchPerformanceStatisticsValidationError,
    build_research_performance_statistics,
)
from qore.infrastructure.research_run import (
    ResearchExecutionModelId,
    ResearchRandomnessMode,
    ResearchReplayPolicyVersion,
    ResearchRunEvidence,
    ResearchRunId,
    ResearchSoftwareRevision,
    ResearchStrategyConfigurationId,
    ResearchTransactionCostModelId,
    build_research_run_evidence,
)
from qore.kernel.result import Failure, Success

_BASE = datetime(2026, 8, 9, 12, 0, tzinfo=UTC)
_USD = CurrencyCode("USD")
_EXECUTION_SOURCE = ExternalSourceDescriptor(
    adapter_id=AdapterId(UUID("67000000-0000-0000-0000-000000000001")),
    source_id=SourceId(UUID("67000000-0000-0000-0000-000000000002")),
    port_name=PortName("execution.research-performance-test"),
)
_MARKET_SOURCE = ExternalSourceDescriptor(
    adapter_id=AdapterId(UUID("67000000-0000-0000-0000-000000000003")),
    source_id=SourceId(UUID("67000000-0000-0000-0000-000000000004")),
    port_name=PortName("market-data.research-performance-test"),
)
_EXECUTION_MODEL = ResearchExecutionModelId(
    UUID("67000000-0000-0000-0000-000000000005")
)
_COST_MODEL = ResearchTransactionCostModelId(
    UUID("67000000-0000-0000-0000-000000000006")
)


def _uuid(suffix: int) -> UUID:
    return UUID(f"67000000-0000-0000-0000-{suffix:012d}")


def _money(value: str) -> MoneyAmount:
    return MoneyAmount(currency=_USD, amount=Decimal(value))


def _run() -> ResearchRunEvidence:
    instrument = Instrument("EURUSD")
    timeframe = Timeframe(300)
    scope = HistoricalOhlcDatasetScope(
        source=_MARKET_SOURCE,
        window=HistoricalOhlcWindow(
            instrument=instrument,
            timeframe=timeframe,
            opened_at=_BASE,
            closed_at=_BASE + timedelta(minutes=15),
        ),
    )
    snapshot = OhlcSnapshot(
        snapshot_id=MarketDataSnapshotId(_uuid(100)),
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
        observation_id=ReplayObservationId(_uuid(101)),
        payload=snapshot,
        availability_evidence_at=snapshot.closed_at,
        available_at=snapshot.closed_at,
        availability_basis=ReplayAvailabilityBasis.STRUCTURAL_BOUNDARY,
        availability_evidence_ref=ReplayAvailabilityEvidenceReference(_uuid(102)),
    )
    dataset = build_historical_ohlc_replay_dataset(
        dataset_id=HistoricalDatasetId(_uuid(103)),
        revision_id=HistoricalDatasetRevisionId(_uuid(104)),
        parent_revision_id=None,
        revision_reason=None,
        scope=scope,
        assembled_at=_BASE + timedelta(days=1),
        schema_version=HistoricalDatasetSchemaVersion("ohlc-replay-v1"),
        normalization_version=HistoricalDatasetNormalizationVersion("ingestion-v1"),
        observations=(replay,),
    )
    assert isinstance(dataset, Success)
    built = build_research_run_evidence(
        run_id=ResearchRunId(_uuid(105)),
        created_at=_BASE + timedelta(days=2),
        datasets=(dataset.value.manifest,),
        replay_policy_version=ResearchReplayPolicyVersion("point-in-time-v1"),
        simulated_start=_BASE,
        simulated_end=_BASE + timedelta(minutes=5),
        strategy_configuration_id=ResearchStrategyConfigurationId(_uuid(106)),
        software_revision=ResearchSoftwareRevision("8149e210"),
        execution_model_id=_EXECUTION_MODEL,
        transaction_cost_model_id=_COST_MODEL,
        randomness_mode=ResearchRandomnessMode.DETERMINISTIC,
        random_seed=None,
    )
    assert isinstance(built, Success)
    return built.value


def _decision(suffix: int) -> FunctionalDecision:
    return FunctionalDecision(
        decision_id=DecisionId(_uuid(200 + suffix)),
        timestamp=_BASE + timedelta(minutes=1),
        decision_type=DecisionType("core.trade"),
        status=DecisionStatus.RESOLVED,
        priority=DecisionPriority.NORMAL,
        metadata=DecisionMetadata(correlation_id=CorrelationId(_uuid(300 + suffix))),
        reasons=(
            DecisionReason(
                code=DecisionReasonCode("research.performance"),
                summary="performance evidence test",
            ),
        ),
        outcome=DecisionOutcome.APPROVED,
    )


def _intent(side: OrderSide, suffix: int) -> OrderIntent:
    return OrderIntent(
        intent_id=OrderIntentId(_uuid(400 + suffix)),
        idempotency_key=ExecutionIdempotencyKey(_uuid(500 + suffix)),
        instrument=ExecutionInstrument("EUR_USD"),
        side=side,
        order_type=OrderType.MARKET,
        quantity=OrderQuantity(Decimal("1")),
        created_at=_BASE + timedelta(minutes=1, seconds=1),
        metadata=ExternalRequestMetadata(
            correlation_id=CorrelationId(_uuid(600 + suffix))
        ),
    )


def _fill(
    run: ResearchRunEvidence,
    *,
    side: OrderSide,
    suffix: int,
    price: str,
    filled_at: datetime,
) -> ResearchFillEvidence:
    intent = _intent(side, suffix)
    intent_evidence = build_research_execution_intent_evidence(
        evidence_id=ResearchExecutionIntentEvidenceId(_uuid(700 + suffix)),
        run=run,
        decision=_decision(suffix),
        intent=intent,
        evidenced_at=intent.created_at + timedelta(seconds=1),
    )
    assert isinstance(intent_evidence, Success)
    fill = build_research_fill_evidence(
        fill_id=ResearchFillId(_uuid(800 + suffix)),
        intent_evidence=intent_evidence.value,
        source=_EXECUTION_SOURCE,
        price=OrderPrice(Decimal(price)),
        quantity=OrderQuantity(Decimal("1")),
        filled_at=filled_at,
        evidence_ref=ResearchEconomicEvidenceReference(_uuid(900 + suffix)),
    )
    assert isinstance(fill, Success)
    return fill.value


def _gross(
    run: ResearchRunEvidence,
    *,
    suffix: int,
    pnl: str,
) -> ResearchGrossEconomicResult:
    entry = _fill(
        run,
        side=OrderSide.BUY,
        suffix=suffix * 2,
        price="100",
        filled_at=_BASE + timedelta(minutes=2, seconds=suffix),
    )
    exit_fill = _fill(
        run,
        side=OrderSide.SELL,
        suffix=suffix * 2 + 1,
        price="102",
        filled_at=_BASE + timedelta(minutes=2, seconds=suffix + 1),
    )
    built = build_research_gross_economic_result(
        result_id=ResearchEconomicResultId(_uuid(1000 + suffix)),
        run=run,
        entry_fills=(entry,),
        exit_fills=(exit_fill,),
        gross_pnl=_money(pnl),
        valued_at=_BASE + timedelta(minutes=2, seconds=suffix + 2),
        evidence_ref=ResearchEconomicEvidenceReference(_uuid(1100 + suffix)),
    )
    assert isinstance(built, Success)
    return built.value


def _cost(suffix: int) -> ResearchCashCostEvidence:
    return ResearchCashCostEvidence(
        category=ResearchCashCostCategory.FEE,
        status=ResearchCashCostStatus.INCLUDED,
        amount=_money("10"),
        observed_at=_BASE + timedelta(minutes=3),
        evidence_ref=ResearchEconomicEvidenceReference(_uuid(1200 + suffix)),
    )


def _gross_return(
    run: ResearchRunEvidence,
    *,
    suffix: int,
    pnl: str,
    capital: str = "1000",
) -> ResearchReturnObservation:
    gross = _gross(run, suffix=suffix, pnl=pnl)
    built = build_research_return_observation(
        observation_id=ResearchReturnObservationId(_uuid(1300 + suffix)),
        source_result=gross,
        capital_basis=_money(capital),
        observed_at=gross.valued_at + timedelta(seconds=1),
    )
    assert isinstance(built, Success)
    return built.value


def _net_return(run: ResearchRunEvidence, *, suffix: int) -> ResearchReturnObservation:
    gross = _gross(run, suffix=suffix, pnl="100")
    coverage = build_research_cash_cost_coverage(
        run=run,
        model_id=_COST_MODEL,
        required_categories=(ResearchCashCostCategory.FEE,),
        costs=(_cost(suffix),),
    )
    assert isinstance(coverage, Success)
    net = build_research_net_economic_result(
        result_id=ResearchEconomicResultId(_uuid(1400 + suffix)),
        gross_result=gross,
        cost_coverage=coverage.value,
        valued_at=_BASE + timedelta(minutes=3, seconds=1),
    )
    assert isinstance(net, Success)
    built = build_research_return_observation(
        observation_id=ResearchReturnObservationId(_uuid(1500 + suffix)),
        source_result=net.value,
        capital_basis=_money("1000"),
        observed_at=net.value.valued_at + timedelta(seconds=1),
    )
    assert isinstance(built, Success)
    return built.value


def test_statistics_are_derived_only_from_return_evidence() -> None:
    run = _run()
    observations = (
        _gross_return(run, suffix=1, pnl="100"),
        _gross_return(run, suffix=2, pnl="-50"),
        _gross_return(run, suffix=3, pnl="0"),
    )
    built = build_research_performance_statistics(
        snapshot_id=ResearchPerformanceSnapshotId(_uuid(1600)),
        observations=tuple(reversed(observations)),
        observed_at=observations[-1].observed_at + timedelta(seconds=1),
    )
    assert isinstance(built, Success)
    snapshot = built.value
    assert snapshot.observations == observations
    assert snapshot.sample_size == 3
    assert snapshot.positive_count == 1
    assert snapshot.negative_count == 1
    assert snapshot.flat_count == 1
    assert snapshot.minimum_return == Decimal("-0.05")
    assert snapshot.maximum_return == Decimal("0.1")
    assert snapshot.mean_return == Decimal("0.01666666666666666666666666666666667")
    assert snapshot.win_rate == Decimal("0.3333333333333333333333333333333333")
    assert snapshot.population_variance > 0


def test_snapshot_rejects_mixed_research_runs() -> None:
    first_run = _run()
    second_run = replace(first_run, run_id=ResearchRunId(_uuid(1700)))
    built = build_research_performance_statistics(
        snapshot_id=ResearchPerformanceSnapshotId(_uuid(1701)),
        observations=(
            _gross_return(first_run, suffix=20, pnl="10"),
            _gross_return(second_run, suffix=21, pnl="20"),
        ),
        observed_at=_BASE + timedelta(minutes=4),
    )
    assert isinstance(built, Failure)
    assert "one research run" in str(built.error)


def test_snapshot_rejects_mixed_gross_and_net_basis() -> None:
    run = _run()
    built = build_research_performance_statistics(
        snapshot_id=ResearchPerformanceSnapshotId(_uuid(1800)),
        observations=(
            _gross_return(run, suffix=30, pnl="100"),
            _net_return(run, suffix=31),
        ),
        observed_at=_BASE + timedelta(minutes=4),
    )
    assert isinstance(built, Failure)
    assert "gross-or-net return basis" in str(built.error)


def test_snapshot_rejects_reused_fill_evidence_under_new_result_identity() -> None:
    run = _run()
    original = _gross_return(run, suffix=40, pnl="25")
    assert isinstance(original.source_result, ResearchGrossEconomicResult)
    duplicated_result = replace(
        original.source_result,
        result_id=ResearchEconomicResultId(_uuid(1900)),
    )
    duplicated_return = replace(
        original,
        observation_id=ResearchReturnObservationId(_uuid(1901)),
        source_result=duplicated_result,
    )
    built = build_research_performance_statistics(
        snapshot_id=ResearchPerformanceSnapshotId(_uuid(1902)),
        observations=(original, duplicated_return),
        observed_at=duplicated_return.observed_at + timedelta(seconds=1),
    )
    assert isinstance(built, Failure)
    assert "reuse economic fill evidence" in str(built.error)


def test_snapshot_rejects_metric_tampering() -> None:
    run = _run()
    observations = (
        _gross_return(run, suffix=50, pnl="10"),
        _gross_return(run, suffix=51, pnl="20"),
    )
    built = build_research_performance_statistics(
        snapshot_id=ResearchPerformanceSnapshotId(_uuid(2000)),
        observations=observations,
        observed_at=observations[-1].observed_at + timedelta(seconds=1),
    )
    assert isinstance(built, Success)
    with pytest.raises(ResearchPerformanceStatisticsValidationError):
        replace(built.value, mean_return=Decimal("999"))


def test_statistics_boundary_does_not_claim_advanced_metrics() -> None:
    run = _run()
    observation = _gross_return(run, suffix=60, pnl="10")
    built = build_research_performance_statistics(
        snapshot_id=ResearchPerformanceSnapshotId(_uuid(2100)),
        observations=(observation,),
        observed_at=observation.observed_at,
    )
    assert isinstance(built, Success)
    snapshot = built.value
    assert not hasattr(snapshot, "sharpe_ratio")
    assert not hasattr(snapshot, "sortino_ratio")
    assert not hasattr(snapshot, "max_drawdown")
    assert not hasattr(snapshot, "annualized_return")
    assert not hasattr(snapshot, "equity_curve")
