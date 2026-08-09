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
    ResearchEconomicEvidenceReference,
    ResearchEconomicResultId,
    ResearchExecutionIntentEvidenceId,
    ResearchFillId,
    ResearchReturnObservationId,
    build_research_execution_intent_evidence,
    build_research_fill_evidence,
    build_research_gross_economic_result,
    build_research_return_observation,
)
from qore.infrastructure.research_evaluation_freeze import (
    ResearchEvaluationFreezeEvidence,
    ResearchEvaluationFreezeEvidenceId,
    build_research_evaluation_freeze_evidence,
)
from qore.infrastructure.research_frozen_oos_evidence import (
    ResearchFrozenOosEvidenceId,
    ResearchFrozenOosEvidenceValidationError,
    ResearchFrozenOosFingerprint,
    build_research_frozen_oos_evidence,
)
from qore.infrastructure.research_oos_performance import (
    ResearchOosPerformanceEvidence,
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
from qore.infrastructure.research_strategy_freeze import (
    ResearchRunStrategyBinding,
    ResearchStrategyFreezeEvidenceReference,
    ResearchStrategyParameter,
    ResearchStrategySchemaVersion,
    build_research_run_strategy_binding,
    build_research_strategy_configuration_manifest,
)
from qore.infrastructure.research_temporal_evaluation import (
    ResearchEvaluationWindow,
    ResearchTemporalEvaluationPlan,
    ResearchTemporalEvaluationPlanId,
    ResearchWalkForwardFold,
    build_research_temporal_evaluation_plan,
)
from qore.kernel.result import Failure, Success

_SIMULATED = datetime(2026, 1, 5, 12, 0, tzinfo=UTC)
_PROCESS = datetime(2026, 8, 9, 12, 0, tzinfo=UTC)
_USD = CurrencyCode("USD")
_MARKET_SOURCE = ExternalSourceDescriptor(
    adapter_id=AdapterId(UUID("73000000-0000-0000-0000-000000000001")),
    source_id=SourceId(UUID("73000000-0000-0000-0000-000000000002")),
    port_name=PortName("market-data.research-frozen-oos-test"),
)
_EXECUTION_SOURCE = ExternalSourceDescriptor(
    adapter_id=AdapterId(UUID("73000000-0000-0000-0000-000000000003")),
    source_id=SourceId(UUID("73000000-0000-0000-0000-000000000004")),
    port_name=PortName("execution.research-frozen-oos-test"),
)
_CONFIG_ID = ResearchStrategyConfigurationId(
    UUID("73000000-0000-0000-0000-000000000005")
)
_EXECUTION_MODEL = ResearchExecutionModelId(
    UUID("73000000-0000-0000-0000-000000000006")
)


def _uuid(suffix: int) -> UUID:
    return UUID(f"73000000-0000-0000-0000-{suffix:012d}")


def _money(value: str) -> MoneyAmount:
    return MoneyAmount(currency=_USD, amount=Decimal(value))


def _run(*, run_suffix: int = 10) -> ResearchRunEvidence:
    instrument = Instrument("EURUSD")
    timeframe = Timeframe(300)
    window = HistoricalOhlcWindow(
        instrument=instrument,
        timeframe=timeframe,
        opened_at=_SIMULATED,
        closed_at=_SIMULATED + timedelta(hours=1),
    )
    snapshot = OhlcSnapshot(
        snapshot_id=MarketDataSnapshotId(_uuid(20)),
        instrument=instrument,
        source=_MARKET_SOURCE,
        timeframe=timeframe,
        opened_at=_SIMULATED,
        closed_at=_SIMULATED + timedelta(minutes=5),
        open=1.10,
        high=1.11,
        low=1.09,
        close=1.105,
    )
    replay = ReplayMarketDataObservation(
        observation_id=ReplayObservationId(_uuid(21)),
        payload=snapshot,
        availability_evidence_at=snapshot.closed_at,
        available_at=snapshot.closed_at,
        availability_basis=ReplayAvailabilityBasis.STRUCTURAL_BOUNDARY,
        availability_evidence_ref=ReplayAvailabilityEvidenceReference(_uuid(22)),
    )
    dataset = build_historical_ohlc_replay_dataset(
        dataset_id=HistoricalDatasetId(_uuid(23)),
        revision_id=HistoricalDatasetRevisionId(_uuid(24)),
        parent_revision_id=None,
        revision_reason=None,
        scope=HistoricalOhlcDatasetScope(source=_MARKET_SOURCE, window=window),
        assembled_at=_PROCESS - timedelta(days=1),
        schema_version=HistoricalDatasetSchemaVersion("ohlc-replay-v1"),
        normalization_version=HistoricalDatasetNormalizationVersion("ingestion-v1"),
        observations=(replay,),
    )
    assert isinstance(dataset, Success)
    built = build_research_run_evidence(
        run_id=ResearchRunId(_uuid(run_suffix)),
        created_at=_PROCESS - timedelta(minutes=3),
        datasets=(dataset.value.manifest,),
        replay_policy_version=ResearchReplayPolicyVersion("point-in-time-v1"),
        simulated_start=_SIMULATED,
        simulated_end=_SIMULATED + timedelta(hours=1),
        strategy_configuration_id=_CONFIG_ID,
        software_revision=ResearchSoftwareRevision("7eb8c336"),
        execution_model_id=_EXECUTION_MODEL,
        transaction_cost_model_id=None,
        randomness_mode=ResearchRandomnessMode.DETERMINISTIC,
        random_seed=None,
    )
    assert isinstance(built, Success)
    return built.value


def _strategy_binding(run: ResearchRunEvidence) -> ResearchRunStrategyBinding:
    manifest = build_research_strategy_configuration_manifest(
        configuration_id=_CONFIG_ID,
        schema_version=ResearchStrategySchemaVersion("strategy-config-v1"),
        parameters=(
            ResearchStrategyParameter("entry.threshold", Decimal("0.75")),
            ResearchStrategyParameter("risk.enabled", True),
        ),
        frozen_at=run.created_at - timedelta(minutes=1),
        evidence_ref=ResearchStrategyFreezeEvidenceReference(_uuid(30)),
    )
    assert isinstance(manifest, Success)
    binding = build_research_run_strategy_binding(run=run, manifest=manifest.value)
    assert isinstance(binding, Success)
    return binding.value


def _plan(
    run: ResearchRunEvidence,
    *,
    plan_suffix: int = 40,
) -> ResearchTemporalEvaluationPlan:
    fold = ResearchWalkForwardFold(
        fold_number=1,
        in_sample=ResearchEvaluationWindow(
            opened_at=_SIMULATED,
            closed_at=_SIMULATED + timedelta(minutes=30),
        ),
        out_of_sample=ResearchEvaluationWindow(
            opened_at=_SIMULATED + timedelta(minutes=30),
            closed_at=_SIMULATED + timedelta(minutes=45),
        ),
    )
    built = build_research_temporal_evaluation_plan(
        plan_id=ResearchTemporalEvaluationPlanId(_uuid(plan_suffix)),
        run=run,
        folds=(fold,),
        created_at=_PROCESS - timedelta(minutes=2),
    )
    assert isinstance(built, Success)
    return built.value


def _evaluation_freeze(
    run: ResearchRunEvidence,
    plan: ResearchTemporalEvaluationPlan,
) -> ResearchEvaluationFreezeEvidence:
    built = build_research_evaluation_freeze_evidence(
        evidence_id=ResearchEvaluationFreezeEvidenceId(_uuid(50)),
        strategy_binding=_strategy_binding(run),
        plan=plan,
        established_at=_PROCESS - timedelta(minutes=1),
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
                code=DecisionReasonCode("research.frozen-oos"),
                summary="frozen OOS evidence test",
            ),
        ),
        outcome=DecisionOutcome.APPROVED,
    )


def _fill(
    run: ResearchRunEvidence,
    *,
    side: OrderSide,
    suffix: int,
    filled_at: datetime,
):
    decision_at = filled_at - timedelta(seconds=4)
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
        filled_at=filled_at,
        evidence_ref=ResearchEconomicEvidenceReference(_uuid(1700 + suffix)),
    )
    assert isinstance(fill, Success)
    return fill.value


def _oos_performance(
    run: ResearchRunEvidence,
    plan: ResearchTemporalEvaluationPlan,
    *,
    observed_at: datetime = _PROCESS,
) -> ResearchOosPerformanceEvidence:
    valued_at = _SIMULATED + timedelta(minutes=35)
    entry = _fill(
        run,
        side=OrderSide.BUY,
        suffix=60,
        filled_at=valued_at - timedelta(seconds=2),
    )
    exit_fill = _fill(
        run,
        side=OrderSide.SELL,
        suffix=61,
        filled_at=valued_at - timedelta(seconds=1),
    )
    gross = build_research_gross_economic_result(
        result_id=ResearchEconomicResultId(_uuid(1800)),
        run=run,
        entry_fills=(entry,),
        exit_fills=(exit_fill,),
        gross_pnl=_money("100"),
        valued_at=valued_at,
        evidence_ref=ResearchEconomicEvidenceReference(_uuid(1801)),
    )
    assert isinstance(gross, Success)
    returned = build_research_return_observation(
        observation_id=ResearchReturnObservationId(_uuid(1802)),
        source_result=gross.value,
        capital_basis=_money("1000"),
        observed_at=valued_at + timedelta(seconds=1),
    )
    assert isinstance(returned, Success)
    built = build_research_oos_performance_evidence(
        evidence_id=ResearchOosPerformanceEvidenceId(_uuid(1803)),
        plan=plan,
        observations=(returned.value,),
        statistics_snapshot_ids=(ResearchPerformanceSnapshotId(_uuid(1804)),),
        observed_at=observed_at,
    )
    assert isinstance(built, Success)
    return built.value


def test_frozen_oos_evidence_composes_exact_plan_and_real_oos_returns() -> None:
    run = _run()
    plan = _plan(run)
    evaluation_freeze = _evaluation_freeze(run, plan)
    oos = _oos_performance(run, plan)
    built = build_research_frozen_oos_evidence(
        evidence_id=ResearchFrozenOosEvidenceId(_uuid(2000)),
        evaluation_freeze=evaluation_freeze,
        oos_performance=oos,
        certified_at=_PROCESS + timedelta(seconds=1),
    )
    assert isinstance(built, Success)
    evidence = built.value
    assert evidence.evaluation_freeze.plan == evidence.oos_performance.plan
    assert evidence.oos_performance.fold_performance[0].statistics.sample_size == 1
    assert evidence.oos_performance.fold_performance[0].statistics.mean_return == Decimal("0.1")


def test_frozen_oos_evidence_rejects_different_temporal_plan() -> None:
    run = _run()
    frozen_plan = _plan(run, plan_suffix=2100)
    other_plan = _plan(run, plan_suffix=2101)
    evaluation_freeze = _evaluation_freeze(run, frozen_plan)
    oos = _oos_performance(run, other_plan)
    built = build_research_frozen_oos_evidence(
        evidence_id=ResearchFrozenOosEvidenceId(_uuid(2102)),
        evaluation_freeze=evaluation_freeze,
        oos_performance=oos,
        certified_at=_PROCESS + timedelta(seconds=1),
    )
    assert isinstance(built, Failure)
    assert "exact frozen temporal evaluation plan" in str(built.error)


def test_frozen_oos_evidence_rejects_oos_recorded_before_freeze() -> None:
    run = _run()
    plan = _plan(run)
    evaluation_freeze = _evaluation_freeze(run, plan)
    oos = _oos_performance(
        run,
        plan,
        observed_at=evaluation_freeze.established_at - timedelta(seconds=1),
    )
    built = build_research_frozen_oos_evidence(
        evidence_id=ResearchFrozenOosEvidenceId(_uuid(2200)),
        evaluation_freeze=evaluation_freeze,
        oos_performance=oos,
        certified_at=_PROCESS + timedelta(seconds=1),
    )
    assert isinstance(built, Failure)
    assert "must not predate evaluation freeze" in str(built.error)


def test_frozen_oos_evidence_rejects_fingerprint_tampering() -> None:
    run = _run()
    plan = _plan(run)
    built = build_research_frozen_oos_evidence(
        evidence_id=ResearchFrozenOosEvidenceId(_uuid(2300)),
        evaluation_freeze=_evaluation_freeze(run, plan),
        oos_performance=_oos_performance(run, plan),
        certified_at=_PROCESS + timedelta(seconds=1),
    )
    assert isinstance(built, Success)
    with pytest.raises(ResearchFrozenOosEvidenceValidationError):
        replace(
            built.value,
            fingerprint=ResearchFrozenOosFingerprint("0" * 64),
        )


def test_frozen_oos_evidence_makes_no_epistemic_or_production_claims() -> None:
    run = _run()
    plan = _plan(run)
    built = build_research_frozen_oos_evidence(
        evidence_id=ResearchFrozenOosEvidenceId(_uuid(2400)),
        evaluation_freeze=_evaluation_freeze(run, plan),
        oos_performance=_oos_performance(run, plan),
        certified_at=_PROCESS + timedelta(seconds=1),
    )
    assert isinstance(built, Success)
    evidence = built.value
    assert not hasattr(evidence, "analyst_blind")
    assert not hasattr(evidence, "pre_registered")
    assert not hasattr(evidence, "statistically_significant")
    assert not hasattr(evidence, "production_ready")
