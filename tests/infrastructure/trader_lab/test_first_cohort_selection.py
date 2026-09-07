from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Protocol
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
from qore.infrastructure.market_data import Instrument
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
from qore.infrastructure.research_economic_evidence import (
    ResearchEconomicEvidenceReference,
    ResearchEconomicResultId,
    ResearchExecutionIntentEvidenceId,
    ResearchFillEvidence,
    ResearchFillId,
    ResearchReturnObservation,
    ResearchReturnObservationId,
    build_research_execution_intent_evidence,
    build_research_fill_evidence,
    build_research_gross_economic_result,
    build_research_return_observation,
)
from qore.infrastructure.research_performance_statistics import (
    ResearchPerformanceSnapshotId,
    ResearchPerformanceStatisticsSnapshot,
    build_research_performance_statistics,
)
from qore.infrastructure.research_run import (
    ResearchExecutionModelId,
    build_research_run_evidence,
)
from qore.infrastructure.research_strategy_freeze import (
    ResearchRunStrategyBinding,
    ResearchStrategyFreezeEvidenceReference,
    ResearchStrategyParameter,
    build_research_run_strategy_binding,
    build_research_strategy_configuration_manifest,
)
from qore.infrastructure.trader_lab.candidate import (
    TraderLabCandidateBinding,
    TraderLabValidationError,
)
from qore.infrastructure.trader_lab.cohort import (
    FIRST_DEMO_COHORT_CODES,
    FirstCohortLabStatus,
    FirstCohortSelectionPolicy,
    FirstCohortTraderLabEntry,
    select_first_demo_trader,
)
from qore.infrastructure.trader_lab.lifecycle import (
    MANDATORY_STAGES,
    TraderLabLifecycle,
    TraderLabPromotionRequest,
    apply_trader_lab_promotion,
    start_trader_lab_lifecycle,
)
from qore.infrastructure.trader_lab.stage_evidence import (
    TraderLabEvidenceReference,
    TraderLabStageEvidenceRecord,
)
from qore.infrastructure.traders.contracts import (
    DemoTradingConfigFingerprint,
    DemoTradingMethodologyFingerprint,
    DemoTradingMethodologyId,
    DemoTradingMethodologyVersion,
    DemoTradingTraderCode,
    DemoTradingTraderVersion,
)
from qore.infrastructure.traders.evaluators import cohort_evaluators
from qore.kernel.result import Success

_NOW = datetime(2026, 9, 7, 3, 0, tzinfo=UTC)
_INSTRUMENT = Instrument("EURUSD")
_USD = CurrencyCode("USD")
_EXECUTION_MODEL = ResearchExecutionModelId(
    UUID("72100000-0000-0000-0000-000000000001")
)
_EXECUTION_SOURCE = ExternalSourceDescriptor(
    adapter_id=AdapterId(UUID("72100000-0000-0000-0000-000000000002")),
    source_id=SourceId(UUID("72100000-0000-0000-0000-000000000003")),
    port_name=PortName("execution.first-cohort-selection-test"),
)
_POLICY = FirstCohortSelectionPolicy(
    min_sample_size=4,
    min_mean_return=Decimal("0"),
    min_win_rate=Decimal("0.50"),
    max_population_variance=Decimal("0.01"),
)
_RATES: dict[str, tuple[str, ...]] = {
    "vt-01": ("0.01", "0.02", "-0.01", "0.03"),
    "vt-08": ("0.03", "0.04", "-0.01", "0.05"),
    "vt-09": ("0.005", "0.01", "-0.02", "0.01"),
    "vt-17": ("0.02", "0.02", "-0.02", "0.02"),
    "vt-31": ("0.015", "0.025", "-0.005", "0.02"),
}

_StrategyBindingFactory = Callable[..., ResearchRunStrategyBinding]
_CandidateFactory = Callable[..., TraderLabCandidateBinding]
_StageEvidenceFactory = Callable[..., TraderLabStageEvidenceRecord]
_EconomicReferenceFactory = Callable[[TraderLabCandidateBinding], TraderLabEvidenceReference]


class _CohortEvaluator(Protocol):
    @property
    def trader_code(self) -> str: ...

    @property
    def version(self) -> str: ...

    def config_fingerprint(self) -> DemoTradingConfigFingerprint: ...

    def methodology(
        self,
    ) -> tuple[
        DemoTradingMethodologyId,
        DemoTradingMethodologyVersion,
        DemoTradingMethodologyFingerprint,
    ]: ...


def _bound_strategy(
    evaluator: _CohortEvaluator,
    *,
    index: int,
    strategy_binding_factory: _StrategyBindingFactory,
    instrument: Instrument = _INSTRUMENT,
) -> ResearchRunStrategyBinding:
    base = strategy_binding_factory(configuration_id_suffix=300 + index)
    rebuilt = build_research_run_evidence(
        run_id=base.run.run_id,
        created_at=base.run.created_at,
        datasets=base.run.datasets,
        replay_policy_version=base.run.replay_policy_version,
        simulated_start=base.run.simulated_start,
        simulated_end=base.run.simulated_end,
        strategy_configuration_id=base.run.strategy_configuration_id,
        software_revision=base.run.software_revision,
        execution_model_id=_EXECUTION_MODEL,
        transaction_cost_model_id=None,
        randomness_mode=base.run.randomness_mode,
        random_seed=base.run.random_seed,
    )
    assert isinstance(rebuilt, Success), rebuilt
    run = rebuilt.value
    trader_code = str(evaluator.trader_code)
    config = evaluator.config_fingerprint()
    methodology_id, methodology_version, methodology_fingerprint = evaluator.methodology()
    manifest = build_research_strategy_configuration_manifest(
        configuration_id=run.strategy_configuration_id,
        schema_version=base.manifest.schema_version,
        parameters=(
            ResearchStrategyParameter("trader.code", trader_code),
            ResearchStrategyParameter("trader.config_fingerprint", config.value),
            ResearchStrategyParameter("trader.instrument", instrument.symbol),
            ResearchStrategyParameter(
                "trader.methodology_fingerprint", methodology_fingerprint.value
            ),
            ResearchStrategyParameter("trader.methodology_id", methodology_id.value),
            ResearchStrategyParameter(
                "trader.methodology_version", methodology_version.value
            ),
        ),
        frozen_at=run.created_at - timedelta(minutes=1),
        evidence_ref=ResearchStrategyFreezeEvidenceReference(
            UUID(f"72000000-0000-0000-0000-{index + 1:012d}")
        ),
    )
    assert isinstance(manifest, Success)
    binding = build_research_run_strategy_binding(run=run, manifest=manifest.value)
    assert isinstance(binding, Success)
    return binding.value


def _complete_lifecycle(
    candidate: TraderLabCandidateBinding,
    *,
    index: int,
    stage_evidence_factory: _StageEvidenceFactory,
) -> TraderLabLifecycle:
    lifecycle = start_trader_lab_lifecycle(candidate)
    for offset, stage in enumerate(MANDATORY_STAGES):
        evidence = stage_evidence_factory(
            stage=stage,
            candidate=candidate,
            evidence_suffix=1_000 + index * 100 + offset,
            produced_at=_NOW + timedelta(minutes=offset),
        )
        promoted = apply_trader_lab_promotion(
            lifecycle,
            TraderLabPromotionRequest(stage=stage, evidence=evidence),
        )
        assert isinstance(promoted, Success), promoted
        lifecycle = promoted.value
    return lifecycle


def _uuid(prefix: str, *, index: int, suffix: int) -> UUID:
    return UUID(f"{prefix}-0000-{index + 1:04d}-0000-{suffix:012d}")


def _decision(
    candidate: TraderLabCandidateBinding,
    *,
    index: int,
    suffix: int,
) -> FunctionalDecision:
    return FunctionalDecision(
        decision_id=DecisionId(_uuid("72200000", index=index, suffix=100 + suffix)),
        timestamp=candidate.strategy_binding.run.simulated_start + timedelta(minutes=1),
        decision_type=DecisionType("core.trade"),
        status=DecisionStatus.RESOLVED,
        priority=DecisionPriority.NORMAL,
        metadata=DecisionMetadata(
            correlation_id=CorrelationId(
                _uuid("72200000", index=index, suffix=200 + suffix)
            )
        ),
        reasons=(
            DecisionReason(
                code=DecisionReasonCode("research.performance"),
                summary="First-cohort canonical economic evidence",
            ),
        ),
        outcome=DecisionOutcome.APPROVED,
    )


def _intent(
    candidate: TraderLabCandidateBinding,
    *,
    index: int,
    suffix: int,
    side: OrderSide,
) -> OrderIntent:
    return OrderIntent(
        intent_id=OrderIntentId(_uuid("72300000", index=index, suffix=100 + suffix)),
        idempotency_key=ExecutionIdempotencyKey(
            _uuid("72300000", index=index, suffix=200 + suffix)
        ),
        instrument=ExecutionInstrument(_INSTRUMENT.symbol),
        side=side,
        order_type=OrderType.MARKET,
        quantity=OrderQuantity(Decimal("1")),
        created_at=(
            candidate.strategy_binding.run.simulated_start
            + timedelta(minutes=1, seconds=1)
        ),
        metadata=ExternalRequestMetadata(
            correlation_id=CorrelationId(
                _uuid("72300000", index=index, suffix=300 + suffix)
            )
        ),
    )


def _fill(
    candidate: TraderLabCandidateBinding,
    *,
    index: int,
    suffix: int,
    side: OrderSide,
    filled_at: datetime,
) -> ResearchFillEvidence:
    intent = _intent(candidate, index=index, suffix=suffix, side=side)
    evidenced = build_research_execution_intent_evidence(
        evidence_id=ResearchExecutionIntentEvidenceId(
            _uuid("72400000", index=index, suffix=100 + suffix)
        ),
        run=candidate.strategy_binding.run,
        decision=_decision(candidate, index=index, suffix=suffix),
        intent=intent,
        evidenced_at=intent.created_at + timedelta(seconds=1),
    )
    assert isinstance(evidenced, Success), evidenced
    built = build_research_fill_evidence(
        fill_id=ResearchFillId(
            _uuid("72400000", index=index, suffix=200 + suffix)
        ),
        intent_evidence=evidenced.value,
        source=_EXECUTION_SOURCE,
        price=OrderPrice(Decimal("1.10000")),
        quantity=OrderQuantity(Decimal("1")),
        filled_at=filled_at,
        evidence_ref=ResearchEconomicEvidenceReference(
            _uuid("72400000", index=index, suffix=300 + suffix)
        ),
    )
    assert isinstance(built, Success), built
    return built.value


def _return_observation(
    candidate: TraderLabCandidateBinding,
    *,
    index: int,
    offset: int,
    rate: Decimal,
) -> ResearchReturnObservation:
    entry_at = candidate.strategy_binding.run.simulated_start + timedelta(
        minutes=2, seconds=offset * 2
    )
    exit_at = entry_at + timedelta(seconds=1)
    entry = _fill(
        candidate,
        index=index,
        suffix=offset * 2,
        side=OrderSide.BUY,
        filled_at=entry_at,
    )
    exit_fill = _fill(
        candidate,
        index=index,
        suffix=offset * 2 + 1,
        side=OrderSide.SELL,
        filled_at=exit_at,
    )
    capital = MoneyAmount(currency=_USD, amount=Decimal("100000"))
    gross = build_research_gross_economic_result(
        result_id=ResearchEconomicResultId(
            _uuid("72500000", index=index, suffix=100 + offset)
        ),
        run=candidate.strategy_binding.run,
        entry_fills=(entry,),
        exit_fills=(exit_fill,),
        gross_pnl=MoneyAmount(currency=_USD, amount=capital.amount * rate),
        valued_at=exit_at + timedelta(seconds=1),
        evidence_ref=ResearchEconomicEvidenceReference(
            _uuid("72500000", index=index, suffix=200 + offset)
        ),
    )
    assert isinstance(gross, Success), gross
    observed = build_research_return_observation(
        observation_id=ResearchReturnObservationId(
            _uuid("72500000", index=index, suffix=300 + offset)
        ),
        source_result=gross.value,
        capital_basis=capital,
        observed_at=gross.value.valued_at + timedelta(seconds=1),
    )
    assert isinstance(observed, Success), observed
    return observed.value


def _performance(
    candidate: TraderLabCandidateBinding,
    *,
    index: int,
    rates: tuple[str, ...],
) -> ResearchPerformanceStatisticsSnapshot:
    observations = tuple(
        _return_observation(
            candidate,
            index=index,
            offset=offset,
            rate=Decimal(rate),
        )
        for offset, rate in enumerate(rates, start=1)
    )
    built = build_research_performance_statistics(
        snapshot_id=ResearchPerformanceSnapshotId(
            UUID(f"75000000-0000-0000-0000-{index + 1:012d}")
        ),
        observations=observations,
        observed_at=_NOW + timedelta(hours=1),
    )
    assert isinstance(built, Success), built
    return built.value


def _entry(
    evaluator: _CohortEvaluator,
    *,
    index: int,
    strategy_binding_factory: _StrategyBindingFactory,
    candidate_factory: _CandidateFactory,
    stage_evidence_factory: _StageEvidenceFactory,
    economic_reference_factory: _EconomicReferenceFactory,
    complete: bool = True,
    instrument: Instrument = _INSTRUMENT,
) -> FirstCohortTraderLabEntry:
    binding = _bound_strategy(
        evaluator,
        index=index,
        strategy_binding_factory=strategy_binding_factory,
        instrument=instrument,
    )
    candidate = candidate_factory(
        candidate_suffix=400 + index,
        version=str(evaluator.version),
        binding=binding,
    )
    lifecycle = (
        _complete_lifecycle(
            candidate,
            index=index,
            stage_evidence_factory=stage_evidence_factory,
        )
        if complete
        else start_trader_lab_lifecycle(candidate)
    )
    methodology_id, methodology_version, methodology_fingerprint = evaluator.methodology()
    code = str(evaluator.trader_code)
    return FirstCohortTraderLabEntry(
        trader_code=DemoTradingTraderCode(code),
        trader_version=DemoTradingTraderVersion(str(evaluator.version)),
        config_fingerprint=DemoTradingConfigFingerprint(
            evaluator.config_fingerprint().value
        ),
        methodology_id=DemoTradingMethodologyId(methodology_id.value),
        methodology_version=DemoTradingMethodologyVersion(methodology_version.value),
        methodology_fingerprint=DemoTradingMethodologyFingerprint(
            methodology_fingerprint.value
        ),
        instrument=instrument,
        lifecycle=lifecycle,
        economic_evidence=economic_reference_factory(candidate),
        performance=_performance(candidate, index=index, rates=_RATES[code]),
    )


def _cohort(
    *,
    strategy_binding_factory: _StrategyBindingFactory,
    candidate_factory: _CandidateFactory,
    stage_evidence_factory: _StageEvidenceFactory,
    economic_reference_factory: _EconomicReferenceFactory,
    incomplete_code: str | None = None,
) -> tuple[FirstCohortTraderLabEntry, ...]:
    return tuple(
        _entry(
            evaluator,
            index=index,
            strategy_binding_factory=strategy_binding_factory,
            candidate_factory=candidate_factory,
            stage_evidence_factory=stage_evidence_factory,
            economic_reference_factory=economic_reference_factory,
            complete=str(evaluator.trader_code) != incomplete_code,
        )
        for index, evaluator in enumerate(cohort_evaluators())
    )


def test_exact_five_full_lab_candidates_select_vt08_on_evidence(
    strategy_binding_factory: _StrategyBindingFactory,
    candidate_factory: _CandidateFactory,
    stage_evidence_factory: _StageEvidenceFactory,
    economic_reference_factory: _EconomicReferenceFactory,
) -> None:
    entries = _cohort(
        strategy_binding_factory=strategy_binding_factory,
        candidate_factory=candidate_factory,
        stage_evidence_factory=stage_evidence_factory,
        economic_reference_factory=economic_reference_factory,
    )

    selection = select_first_demo_trader(entries, policy=_POLICY)

    assert tuple(item.entry.trader_code.value for item in selection.assessments) == (
        FIRST_DEMO_COHORT_CODES
    )
    assert all(item.status is FirstCohortLabStatus.SELECTABLE for item in selection.assessments)
    assert selection.selected is not None
    assert selection.selected.trader_code.value == "vt-08"
    assert selection.selected.instrument == _INSTRUMENT


def test_best_economics_cannot_bypass_incomplete_lab_chain(
    strategy_binding_factory: _StrategyBindingFactory,
    candidate_factory: _CandidateFactory,
    stage_evidence_factory: _StageEvidenceFactory,
    economic_reference_factory: _EconomicReferenceFactory,
) -> None:
    entries = _cohort(
        strategy_binding_factory=strategy_binding_factory,
        candidate_factory=candidate_factory,
        stage_evidence_factory=stage_evidence_factory,
        economic_reference_factory=economic_reference_factory,
        incomplete_code="vt-08",
    )

    selection = select_first_demo_trader(entries, policy=_POLICY)

    vt08 = next(item for item in selection.assessments if item.entry.trader_code.value == "vt-08")
    assert vt08.status is FirstCohortLabStatus.PROMOTION_BLOCKED
    assert selection.selected is not None
    assert selection.selected.trader_code.value == "vt-31"


def test_missing_or_duplicate_cohort_members_fail_closed(
    strategy_binding_factory: _StrategyBindingFactory,
    candidate_factory: _CandidateFactory,
    stage_evidence_factory: _StageEvidenceFactory,
    economic_reference_factory: _EconomicReferenceFactory,
) -> None:
    entries = _cohort(
        strategy_binding_factory=strategy_binding_factory,
        candidate_factory=candidate_factory,
        stage_evidence_factory=stage_evidence_factory,
        economic_reference_factory=economic_reference_factory,
    )

    with pytest.raises(TraderLabValidationError):
        select_first_demo_trader(entries[:-1], policy=_POLICY)
    with pytest.raises(TraderLabValidationError):
        select_first_demo_trader((*entries[:-1], entries[0]), policy=_POLICY)


def test_lab_entry_rejects_instrument_not_bound_by_strategy_freeze(
    strategy_binding_factory: _StrategyBindingFactory,
    candidate_factory: _CandidateFactory,
    stage_evidence_factory: _StageEvidenceFactory,
    economic_reference_factory: _EconomicReferenceFactory,
) -> None:
    evaluator = cohort_evaluators()[0]
    binding = _bound_strategy(
        evaluator,
        index=0,
        strategy_binding_factory=strategy_binding_factory,
        instrument=Instrument("EURUSD"),
    )
    candidate = candidate_factory(
        candidate_suffix=900,
        version=str(evaluator.version),
        binding=binding,
    )
    lifecycle = _complete_lifecycle(
        candidate,
        index=0,
        stage_evidence_factory=stage_evidence_factory,
    )
    methodology_id, methodology_version, methodology_fingerprint = evaluator.methodology()

    with pytest.raises(TraderLabValidationError, match="instrument binding"):
        FirstCohortTraderLabEntry(
            trader_code=DemoTradingTraderCode(str(evaluator.trader_code)),
            trader_version=DemoTradingTraderVersion(str(evaluator.version)),
            config_fingerprint=evaluator.config_fingerprint(),
            methodology_id=methodology_id,
            methodology_version=methodology_version,
            methodology_fingerprint=methodology_fingerprint,
            instrument=Instrument("GBPUSD"),
            lifecycle=lifecycle,
            economic_evidence=economic_reference_factory(candidate),
            performance=_performance(candidate, index=0, rates=_RATES[str(evaluator.trader_code)]),
        )
