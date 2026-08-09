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
    ResearchNetEconomicResult,
    build_research_cash_cost_coverage,
    build_research_execution_intent_evidence,
    build_research_fill_evidence,
    build_research_gross_economic_result,
    build_research_net_economic_result,
)
from qore.infrastructure.research_realized_equity import (
    ResearchRealizedEquityPathId,
    ResearchRealizedEquityValidationError,
    build_research_realized_equity_path,
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
    adapter_id=AdapterId(UUID("68000000-0000-0000-0000-000000000001")),
    source_id=SourceId(UUID("68000000-0000-0000-0000-000000000002")),
    port_name=PortName("execution.research-equity-test"),
)
_MARKET_SOURCE = ExternalSourceDescriptor(
    adapter_id=AdapterId(UUID("68000000-0000-0000-0000-000000000003")),
    source_id=SourceId(UUID("68000000-0000-0000-0000-000000000004")),
    port_name=PortName("market-data.research-equity-test"),
)
_EXECUTION_MODEL = ResearchExecutionModelId(
    UUID("68000000-0000-0000-0000-000000000005")
)
_COST_MODEL = ResearchTransactionCostModelId(
    UUID("68000000-0000-0000-0000-000000000006")
)


def _uuid(suffix: int) -> UUID:
    return UUID(f"68000000-0000-0000-0000-{suffix:012d}")


def _money(value: str) -> MoneyAmount:
    return MoneyAmount(currency=_USD, amount=Decimal(value))


def _run(*, run_suffix: int = 105) -> ResearchRunEvidence:
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
        run_id=ResearchRunId(_uuid(run_suffix)),
        created_at=_BASE + timedelta(days=2),
        datasets=(dataset.value.manifest,),
        replay_policy_version=ResearchReplayPolicyVersion("point-in-time-v1"),
        simulated_start=_BASE,
        simulated_end=_BASE + timedelta(minutes=10),
        strategy_configuration_id=ResearchStrategyConfigurationId(_uuid(106)),
        software_revision=ResearchSoftwareRevision("e7e45d2b"),
        execution_model_id=_EXECUTION_MODEL,
        transaction_cost_model_id=_COST_MODEL,
        randomness_mode=ResearchRandomnessMode.DETERMINISTIC,
        random_seed=None,
    )
    assert isinstance(built, Success)
    return built.value


def _decision(suffix: int) -> FunctionalDecision:
    return FunctionalDecision(
        decision_id=DecisionId(_uuid(2000 + suffix)),
        timestamp=_BASE + timedelta(minutes=1),
        decision_type=DecisionType("core.trade"),
        status=DecisionStatus.RESOLVED,
        priority=DecisionPriority.NORMAL,
        metadata=DecisionMetadata(correlation_id=CorrelationId(_uuid(2100 + suffix))),
        reasons=(
            DecisionReason(
                code=DecisionReasonCode("research.equity"),
                summary="realized equity evidence",
            ),
        ),
        outcome=DecisionOutcome.APPROVED,
    )


def _fill(
    run: ResearchRunEvidence,
    *,
    side: OrderSide,
    suffix: int,
    seconds: int,
) -> ResearchFillEvidence:
    intent = OrderIntent(
        intent_id=OrderIntentId(_uuid(2200 + suffix)),
        idempotency_key=ExecutionIdempotencyKey(_uuid(2300 + suffix)),
        instrument=ExecutionInstrument("EUR_USD"),
        side=side,
        order_type=OrderType.MARKET,
        quantity=OrderQuantity(Decimal("1")),
        created_at=_BASE + timedelta(minutes=1, seconds=seconds),
        metadata=ExternalRequestMetadata(
            correlation_id=CorrelationId(_uuid(2400 + suffix))
        ),
    )
    intent_evidence = build_research_execution_intent_evidence(
        evidence_id=ResearchExecutionIntentEvidenceId(_uuid(2500 + suffix)),
        run=run,
        decision=_decision(suffix),
        intent=intent,
        evidenced_at=intent.created_at + timedelta(seconds=1),
    )
    assert isinstance(intent_evidence, Success)
    fill = build_research_fill_evidence(
        fill_id=ResearchFillId(_uuid(2600 + suffix)),
        intent_evidence=intent_evidence.value,
        source=_EXECUTION_SOURCE,
        price=OrderPrice(Decimal("1.10") if side is OrderSide.BUY else Decimal("1.11")),
        quantity=OrderQuantity(Decimal("1")),
        filled_at=_BASE + timedelta(minutes=2, seconds=seconds),
        evidence_ref=ResearchEconomicEvidenceReference(_uuid(2700 + suffix)),
    )
    assert isinstance(fill, Success)
    return fill.value


def _net_result(
    run: ResearchRunEvidence,
    *,
    suffix: int,
    pnl: str,
    seconds: int,
) -> ResearchNetEconomicResult:
    entry = _fill(
        run,
        side=OrderSide.BUY,
        suffix=suffix * 2,
        seconds=seconds,
    )
    exit_fill = _fill(
        run,
        side=OrderSide.SELL,
        suffix=suffix * 2 + 1,
        seconds=seconds + 1,
    )
    gross = build_research_gross_economic_result(
        result_id=ResearchEconomicResultId(_uuid(2800 + suffix)),
        run=run,
        entry_fills=(entry,),
        exit_fills=(exit_fill,),
        gross_pnl=_money(pnl),
        valued_at=_BASE + timedelta(minutes=3, seconds=seconds),
        evidence_ref=ResearchEconomicEvidenceReference(_uuid(2900 + suffix)),
    )
    assert isinstance(gross, Success)
    cost = ResearchCashCostEvidence(
        category=ResearchCashCostCategory.FEE,
        status=ResearchCashCostStatus.EXPLICIT_ZERO,
        amount=_money("0"),
        observed_at=gross.value.valued_at,
        evidence_ref=ResearchEconomicEvidenceReference(_uuid(3000 + suffix)),
    )
    coverage = build_research_cash_cost_coverage(
        run=run,
        model_id=_COST_MODEL,
        required_categories=(ResearchCashCostCategory.FEE,),
        costs=(cost,),
    )
    assert isinstance(coverage, Success)
    net = build_research_net_economic_result(
        result_id=ResearchEconomicResultId(_uuid(3100 + suffix)),
        gross_result=gross.value,
        cost_coverage=coverage.value,
        valued_at=gross.value.valued_at,
    )
    assert isinstance(net, Success)
    return net.value


def test_realized_equity_derives_terminal_equity_and_closed_drawdown() -> None:
    run = _run()
    results = (
        _net_result(run, suffix=1, pnl="100", seconds=1),
        _net_result(run, suffix=2, pnl="-150", seconds=10),
        _net_result(run, suffix=3, pnl="75", seconds=20),
    )
    built = build_research_realized_equity_path(
        path_id=ResearchRealizedEquityPathId(_uuid(4000)),
        initial_capital=_money("1000"),
        results=tuple(reversed(results)),
        observed_at=results[-1].valued_at + timedelta(seconds=1),
    )
    assert isinstance(built, Success)
    path = built.value
    assert path.results == results
    assert tuple(point.equity.amount for point in path.points) == (
        Decimal("1100"),
        Decimal("950"),
        Decimal("1025"),
    )
    assert path.terminal_equity == _money("1025")
    assert path.maximum_drawdown_amount == _money("150")
    assert path.maximum_drawdown_rate == Decimal(
        "0.1363636363636363636363636363636364"
    )


def test_realized_equity_rejects_mixed_runs() -> None:
    first_run = _run()
    second_run = _run(run_suffix=5000)
    built = build_research_realized_equity_path(
        path_id=ResearchRealizedEquityPathId(_uuid(5001)),
        initial_capital=_money("1000"),
        results=(
            _net_result(first_run, suffix=10, pnl="10", seconds=1),
            _net_result(second_run, suffix=11, pnl="20", seconds=10),
        ),
        observed_at=_BASE + timedelta(minutes=5),
    )
    assert isinstance(built, Failure)
    assert "one research run" in str(built.error)


def test_realized_equity_rejects_reused_fill_evidence() -> None:
    run = _run()
    original = _net_result(run, suffix=20, pnl="10", seconds=1)
    duplicated_gross = replace(
        original.gross_result,
        result_id=ResearchEconomicResultId(_uuid(6000)),
    )
    duplicate = replace(
        original,
        result_id=ResearchEconomicResultId(_uuid(6001)),
        gross_result=duplicated_gross,
    )
    built = build_research_realized_equity_path(
        path_id=ResearchRealizedEquityPathId(_uuid(6002)),
        initial_capital=_money("1000"),
        results=(original, duplicate),
        observed_at=duplicate.valued_at + timedelta(seconds=1),
    )
    assert isinstance(built, Failure)
    assert "reuse fill evidence" in str(built.error)


def test_realized_equity_rejects_metric_tampering_and_claims_no_intratrade_dd() -> None:
    run = _run()
    result = _net_result(run, suffix=30, pnl="-100", seconds=1)
    built = build_research_realized_equity_path(
        path_id=ResearchRealizedEquityPathId(_uuid(7000)),
        initial_capital=_money("1000"),
        results=(result,),
        observed_at=result.valued_at,
    )
    assert isinstance(built, Success)
    with pytest.raises(ResearchRealizedEquityValidationError):
        replace(built.value, maximum_drawdown_rate=Decimal("0"))
    assert not hasattr(built.value, "intratrade_drawdown")
    assert not hasattr(built.value, "unrealized_pnl")
    assert not hasattr(built.value, "margin")
