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
    ResearchCashCostCategory,
    ResearchCashCostEvidence,
    ResearchCashCostStatus,
    ResearchEconomicEvidenceReference,
    ResearchEconomicResultId,
    ResearchExecutionIntentEvidence,
    ResearchExecutionIntentEvidenceId,
    ResearchFillEvidence,
    ResearchFillId,
    ResearchReturnBasis,
    ResearchReturnObservationId,
    build_research_cash_cost_coverage,
    build_research_execution_intent_evidence,
    build_research_fill_evidence,
    build_research_gross_economic_result,
    build_research_net_economic_result,
    build_research_return_observation,
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
_SOURCE = ExternalSourceDescriptor(
    adapter_id=AdapterId(UUID("66000000-0000-0000-0000-000000000001")),
    source_id=SourceId(UUID("66000000-0000-0000-0000-000000000002")),
    port_name=PortName("execution.research-test"),
)
_MARKET_SOURCE = ExternalSourceDescriptor(
    adapter_id=AdapterId(UUID("66000000-0000-0000-0000-000000000003")),
    source_id=SourceId(UUID("66000000-0000-0000-0000-000000000004")),
    port_name=PortName("market-data.research-economic-test"),
)
_EXECUTION_MODEL = ResearchExecutionModelId(
    UUID("66000000-0000-0000-0000-000000000005")
)
_COST_MODEL = ResearchTransactionCostModelId(
    UUID("66000000-0000-0000-0000-000000000006")
)


def _uuid(suffix: int) -> UUID:
    return UUID(f"66000000-0000-0000-0000-{suffix:012d}")


def _money(value: str, currency: CurrencyCode = _USD) -> MoneyAmount:
    return MoneyAmount(currency=currency, amount=Decimal(value))


def _run(
    *,
    execution_model: bool = True,
    cost_model: bool = True,
) -> ResearchRunEvidence:
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
        software_revision=ResearchSoftwareRevision("2f4e578f"),
        execution_model_id=_EXECUTION_MODEL if execution_model else None,
        transaction_cost_model_id=_COST_MODEL if cost_model else None,
        randomness_mode=ResearchRandomnessMode.DETERMINISTIC,
        random_seed=None,
    )
    assert isinstance(built, Success)
    return built.value


def _decision(*, approved: bool = True, kind: str = "core.trade") -> FunctionalDecision:
    return FunctionalDecision(
        decision_id=DecisionId(_uuid(200 if approved else 201)),
        timestamp=_BASE + timedelta(minutes=1),
        decision_type=DecisionType(kind),
        status=DecisionStatus.RESOLVED,
        priority=DecisionPriority.NORMAL,
        metadata=DecisionMetadata(correlation_id=CorrelationId(_uuid(202))),
        reasons=(
            DecisionReason(
                code=DecisionReasonCode("research.test"),
                summary="research execution evidence",
            ),
        ),
        outcome=DecisionOutcome.APPROVED if approved else DecisionOutcome.BLOCKED,
    )


def _intent(side: OrderSide, *, instrument: str = "EUR_USD") -> OrderIntent:
    return OrderIntent(
        intent_id=OrderIntentId(_uuid(300 if side is OrderSide.BUY else 301)),
        idempotency_key=ExecutionIdempotencyKey(
            _uuid(302 if side is OrderSide.BUY else 303)
        ),
        instrument=ExecutionInstrument(instrument),
        side=side,
        order_type=OrderType.MARKET,
        quantity=OrderQuantity(Decimal("1")),
        created_at=_BASE + timedelta(minutes=1, seconds=1),
        metadata=ExternalRequestMetadata(correlation_id=CorrelationId(_uuid(304))),
    )


def _intent_evidence(
    run: ResearchRunEvidence,
    side: OrderSide,
    *,
    instrument: str = "EUR_USD",
) -> ResearchExecutionIntentEvidence:
    built = build_research_execution_intent_evidence(
        evidence_id=ResearchExecutionIntentEvidenceId(
            _uuid(310 if side is OrderSide.BUY else 311)
        ),
        run=run,
        decision=_decision(),
        intent=_intent(side, instrument=instrument),
        evidenced_at=_BASE + timedelta(minutes=1, seconds=2),
    )
    assert isinstance(built, Success)
    return built.value


def _fill(
    run: ResearchRunEvidence,
    side: OrderSide,
    *,
    suffix: int,
    price: str,
    quantity: str = "1",
    instrument: str = "EUR_USD",
    seconds: int = 0,
) -> ResearchFillEvidence:
    built = build_research_fill_evidence(
        fill_id=ResearchFillId(_uuid(suffix)),
        intent_evidence=_intent_evidence(run, side, instrument=instrument),
        source=_SOURCE,
        price=OrderPrice(Decimal(price)),
        quantity=OrderQuantity(Decimal(quantity)),
        filled_at=_BASE + timedelta(minutes=2, seconds=seconds),
        evidence_ref=ResearchEconomicEvidenceReference(_uuid(suffix + 1)),
    )
    assert isinstance(built, Success)
    return built.value


def _gross(run: ResearchRunEvidence, *, pnl: str = "250"):
    entry = _fill(run, OrderSide.BUY, suffix=400, price="100")
    exit_fill = _fill(
        run,
        OrderSide.SELL,
        suffix=410,
        price="102",
        seconds=10,
    )
    built = build_research_gross_economic_result(
        result_id=ResearchEconomicResultId(_uuid(420)),
        run=run,
        entry_fills=(entry,),
        exit_fills=(exit_fill,),
        gross_pnl=_money(pnl),
        valued_at=_BASE + timedelta(minutes=2, seconds=11),
        evidence_ref=ResearchEconomicEvidenceReference(_uuid(421)),
    )
    return built


def test_intent_requires_resolved_approved_core_trade_decision() -> None:
    run = _run()
    blocked = build_research_execution_intent_evidence(
        evidence_id=ResearchExecutionIntentEvidenceId(_uuid(500)),
        run=run,
        decision=_decision(approved=False),
        intent=_intent(OrderSide.BUY),
        evidenced_at=_BASE + timedelta(minutes=1, seconds=2),
    )
    wrong_kind = build_research_execution_intent_evidence(
        evidence_id=ResearchExecutionIntentEvidenceId(_uuid(501)),
        run=run,
        decision=_decision(kind="validation.assess"),
        intent=_intent(OrderSide.BUY),
        evidenced_at=_BASE + timedelta(minutes=1, seconds=2),
    )
    assert isinstance(blocked, Failure)
    assert isinstance(wrong_kind, Failure)


def test_fill_preserves_actual_price_quantity_and_causal_intent() -> None:
    run = _run()
    fill = _fill(run, OrderSide.BUY, suffix=510, price="1.1007", quantity="0.4")
    assert fill.price == OrderPrice(Decimal("1.1007"))
    assert fill.quantity == OrderQuantity(Decimal("0.4"))
    assert fill.intent_evidence.decision.decision_type.value == "core.trade"
    assert fill.run == run


def test_fill_cannot_exceed_originating_intent_quantity() -> None:
    run = _run()
    built = build_research_fill_evidence(
        fill_id=ResearchFillId(_uuid(520)),
        intent_evidence=_intent_evidence(run, OrderSide.BUY),
        source=_SOURCE,
        price=OrderPrice(Decimal("1.1")),
        quantity=OrderQuantity(Decimal("1.1")),
        filled_at=_BASE + timedelta(minutes=2),
        evidence_ref=ResearchEconomicEvidenceReference(_uuid(521)),
    )
    assert isinstance(built, Failure)


def test_gross_result_accepts_partial_fills_and_requires_flat_position() -> None:
    run = _run()
    entries = (
        _fill(run, OrderSide.BUY, suffix=530, price="100", quantity="0.4"),
        _fill(
            run,
            OrderSide.BUY,
            suffix=532,
            price="101",
            quantity="0.6",
            seconds=1,
        ),
    )
    exits = (
        _fill(
            run,
            OrderSide.SELL,
            suffix=540,
            price="102",
            quantity="1",
            seconds=2,
        ),
    )
    built = build_research_gross_economic_result(
        result_id=ResearchEconomicResultId(_uuid(550)),
        run=run,
        entry_fills=tuple(reversed(entries)),
        exit_fills=exits,
        gross_pnl=_money("250"),
        valued_at=_BASE + timedelta(minutes=2, seconds=3),
        evidence_ref=ResearchEconomicEvidenceReference(_uuid(551)),
    )
    assert isinstance(built, Success)
    assert built.value.entry_fills == entries
    assert built.value.quantity == Decimal("1.0")
    assert built.value.gross_pnl == _money("250")


def test_gross_result_does_not_invent_generic_cash_pnl_formula() -> None:
    built = _gross(_run(), pnl="777.25")
    assert isinstance(built, Success)
    assert built.value.gross_pnl == _money("777.25")
    assert built.value.entry_fills[0].price == OrderPrice(Decimal("100"))
    assert built.value.exit_fills[0].price == OrderPrice(Decimal("102"))


def test_gross_result_requires_bound_execution_model() -> None:
    run = _run(execution_model=False)
    built = _gross(run)
    assert isinstance(built, Failure)
    assert "execution model identity" in str(built.error)


def test_gross_result_rejects_unbalanced_or_cross_instrument_fills() -> None:
    run = _run()
    entry = _fill(run, OrderSide.BUY, suffix=560, price="100")
    short_exit = _fill(
        run,
        OrderSide.SELL,
        suffix=562,
        price="102",
        quantity="0.5",
        seconds=1,
    )
    other_exit = _fill(
        run,
        OrderSide.SELL,
        suffix=564,
        price="102",
        instrument="GBP_USD",
        seconds=1,
    )
    unbalanced = build_research_gross_economic_result(
        result_id=ResearchEconomicResultId(_uuid(566)),
        run=run,
        entry_fills=(entry,),
        exit_fills=(short_exit,),
        gross_pnl=_money("1"),
        valued_at=_BASE + timedelta(minutes=3),
        evidence_ref=ResearchEconomicEvidenceReference(_uuid(567)),
    )
    mixed = build_research_gross_economic_result(
        result_id=ResearchEconomicResultId(_uuid(568)),
        run=run,
        entry_fills=(entry,),
        exit_fills=(other_exit,),
        gross_pnl=_money("1"),
        valued_at=_BASE + timedelta(minutes=3),
        evidence_ref=ResearchEconomicEvidenceReference(_uuid(569)),
    )
    assert isinstance(unbalanced, Failure)
    assert isinstance(mixed, Failure)


def _cost(
    category: ResearchCashCostCategory,
    status: ResearchCashCostStatus,
    amount: str | None,
    suffix: int,
    *,
    currency: CurrencyCode = _USD,
) -> ResearchCashCostEvidence:
    return ResearchCashCostEvidence(
        category=category,
        status=status,
        amount=_money(amount, currency) if amount is not None else None,
        observed_at=_BASE + timedelta(minutes=3),
        evidence_ref=ResearchEconomicEvidenceReference(_uuid(suffix)),
    )


def test_cost_coverage_requires_exact_run_bound_model_and_explicit_categories() -> None:
    run = _run()
    built = build_research_cash_cost_coverage(
        run=run,
        model_id=_COST_MODEL,
        required_categories=(ResearchCashCostCategory.FEE, ResearchCashCostCategory.COMMISSION),
        costs=(
            _cost(
                ResearchCashCostCategory.COMMISSION,
                ResearchCashCostStatus.INCLUDED,
                "5",
                600,
            ),
            _cost(
                ResearchCashCostCategory.FEE,
                ResearchCashCostStatus.EXPLICIT_ZERO,
                "0",
                601,
            ),
        ),
    )
    assert isinstance(built, Success)
    assert built.value.complete
    assert built.value.required_categories == (
        ResearchCashCostCategory.COMMISSION,
        ResearchCashCostCategory.FEE,
    )


def test_unknown_required_cost_is_not_silently_zero() -> None:
    run = _run()
    gross = _gross(run)
    assert isinstance(gross, Success)
    coverage = build_research_cash_cost_coverage(
        run=run,
        model_id=_COST_MODEL,
        required_categories=(ResearchCashCostCategory.COMMISSION,),
        costs=(
            _cost(
                ResearchCashCostCategory.COMMISSION,
                ResearchCashCostStatus.UNKNOWN,
                None,
                610,
            ),
        ),
    )
    assert isinstance(coverage, Success)
    assert not coverage.value.complete
    net = build_research_net_economic_result(
        result_id=ResearchEconomicResultId(_uuid(611)),
        gross_result=gross.value,
        cost_coverage=coverage.value,
        valued_at=_BASE + timedelta(minutes=3, seconds=1),
    )
    assert isinstance(net, Failure)
    assert "unknown required cash cost" in str(net.error)


def test_net_pnl_subtracts_only_explicit_cash_adjustments() -> None:
    run = _run()
    gross = _gross(run, pnl="100")
    assert isinstance(gross, Success)
    coverage = build_research_cash_cost_coverage(
        run=run,
        model_id=_COST_MODEL,
        required_categories=(ResearchCashCostCategory.COMMISSION, ResearchCashCostCategory.FEE),
        costs=(
            _cost(
                ResearchCashCostCategory.COMMISSION,
                ResearchCashCostStatus.INCLUDED,
                "5",
                620,
            ),
            _cost(
                ResearchCashCostCategory.FEE,
                ResearchCashCostStatus.EXPLICIT_ZERO,
                "0",
                621,
            ),
        ),
    )
    assert isinstance(coverage, Success)
    net = build_research_net_economic_result(
        result_id=ResearchEconomicResultId(_uuid(622)),
        gross_result=gross.value,
        cost_coverage=coverage.value,
        valued_at=_BASE + timedelta(minutes=3, seconds=1),
    )
    assert isinstance(net, Success)
    assert net.value.net_pnl == _money("95")
    assert not hasattr(ResearchCashCostCategory, "SPREAD")
    assert not hasattr(ResearchCashCostCategory, "SLIPPAGE")


def test_signed_cash_adjustment_supports_evidence_backed_rebate() -> None:
    run = _run()
    gross = _gross(run, pnl="100")
    assert isinstance(gross, Success)
    coverage = build_research_cash_cost_coverage(
        run=run,
        model_id=_COST_MODEL,
        required_categories=(ResearchCashCostCategory.COMMISSION,),
        costs=(
            _cost(
                ResearchCashCostCategory.COMMISSION,
                ResearchCashCostStatus.INCLUDED,
                "-1",
                630,
            ),
        ),
    )
    assert isinstance(coverage, Success)
    net = build_research_net_economic_result(
        result_id=ResearchEconomicResultId(_uuid(631)),
        gross_result=gross.value,
        cost_coverage=coverage.value,
        valued_at=_BASE + timedelta(minutes=3, seconds=1),
    )
    assert isinstance(net, Success)
    assert net.value.net_pnl == _money("101")


def test_net_result_rejects_cost_currency_mismatch() -> None:
    run = _run()
    gross = _gross(run, pnl="100")
    assert isinstance(gross, Success)
    coverage = build_research_cash_cost_coverage(
        run=run,
        model_id=_COST_MODEL,
        required_categories=(ResearchCashCostCategory.FEE,),
        costs=(
            _cost(
                ResearchCashCostCategory.FEE,
                ResearchCashCostStatus.INCLUDED,
                "2",
                640,
                currency=CurrencyCode("EUR"),
            ),
        ),
    )
    assert isinstance(coverage, Success)
    net = build_research_net_economic_result(
        result_id=ResearchEconomicResultId(_uuid(641)),
        gross_result=gross.value,
        cost_coverage=coverage.value,
        valued_at=_BASE + timedelta(minutes=3, seconds=1),
    )
    assert isinstance(net, Failure)


def test_return_requires_explicit_positive_capital_basis_and_preserves_net_basis() -> None:
    run = _run()
    gross = _gross(run, pnl="100")
    assert isinstance(gross, Success)
    coverage = build_research_cash_cost_coverage(
        run=run,
        model_id=_COST_MODEL,
        required_categories=(ResearchCashCostCategory.FEE,),
        costs=(
            _cost(
                ResearchCashCostCategory.FEE,
                ResearchCashCostStatus.INCLUDED,
                "5",
                650,
            ),
        ),
    )
    assert isinstance(coverage, Success)
    net = build_research_net_economic_result(
        result_id=ResearchEconomicResultId(_uuid(651)),
        gross_result=gross.value,
        cost_coverage=coverage.value,
        valued_at=_BASE + timedelta(minutes=3, seconds=1),
    )
    assert isinstance(net, Success)
    returned = build_research_return_observation(
        observation_id=ResearchReturnObservationId(_uuid(652)),
        source_result=net.value,
        capital_basis=_money("10000"),
        observed_at=_BASE + timedelta(minutes=3, seconds=2),
    )
    assert isinstance(returned, Success)
    assert returned.value.return_rate == Decimal("0.0095")
    assert returned.value.basis is ResearchReturnBasis.NET
    assert returned.value.run == run


def test_return_rejects_zero_capital_and_tampered_rate() -> None:
    gross = _gross(_run(), pnl="100")
    assert isinstance(gross, Success)
    zero = build_research_return_observation(
        observation_id=ResearchReturnObservationId(_uuid(660)),
        source_result=gross.value,
        capital_basis=_money("0"),
        observed_at=_BASE + timedelta(minutes=3),
    )
    assert isinstance(zero, Failure)
    valid = build_research_return_observation(
        observation_id=ResearchReturnObservationId(_uuid(661)),
        source_result=gross.value,
        capital_basis=_money("10000"),
        observed_at=_BASE + timedelta(minutes=3),
    )
    assert isinstance(valid, Success)
    tampered = replace(valid.value, return_rate=Decimal("0.5"))
    assert tampered.return_rate == Decimal("0.5")
