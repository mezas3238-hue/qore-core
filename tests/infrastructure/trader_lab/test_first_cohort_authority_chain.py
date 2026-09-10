from __future__ import annotations

from collections.abc import Callable
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
from qore.infrastructure.risk_trader_lab_authority import RiskTraderLabPolicy
from qore.infrastructure.trader_lab.candidate import TraderLabCandidateBinding
from qore.infrastructure.trader_lab.cohort_authority import (
    FirstCohortAuthorityInput,
    complete_first_cohort_authority_chain,
)
from qore.infrastructure.trader_lab.economic_binding import (
    reference_instrument_bound_research_economic,
)
from qore.infrastructure.trader_lab.lifecycle import (
    MANDATORY_STAGES,
    TraderLabLifecycle,
    TraderLabPromotionRequest,
    TraderLabState,
    apply_trader_lab_promotion,
    start_trader_lab_lifecycle,
)
from qore.infrastructure.trader_lab.stage_evidence import (
    TraderLabEvidenceKind,
    TraderLabStage,
    TraderLabStageEvidenceRecord,
)
from qore.infrastructure.traders.evaluators import Vt01NyPrecisionCore
from qore.kernel.result import Failure, Success

_NOW = datetime(2026, 9, 7, 12, 0, tzinfo=UTC)
_USD = CurrencyCode("USD")
_EXECUTION_MODEL = ResearchExecutionModelId(
    UUID("76800000-0000-0000-0000-000000000001")
)
_EXECUTION_SOURCE = ExternalSourceDescriptor(
    adapter_id=AdapterId(UUID("76800000-0000-0000-0000-000000000002")),
    source_id=SourceId(UUID("76800000-0000-0000-0000-000000000003")),
    port_name=PortName("execution.trader-lab-authority-test"),
)

_StrategyBindingFactory = Callable[..., ResearchRunStrategyBinding]
_CandidateFactory = Callable[..., TraderLabCandidateBinding]
_StageEvidenceFactory = Callable[..., TraderLabStageEvidenceRecord]


def _uuid(prefix: str, suffix: int) -> UUID:
    return UUID(f"{prefix}-0000-0000-0000-{suffix:012d}")


def _bound_vt01_strategy(
    strategy_binding_factory: _StrategyBindingFactory,
) -> ResearchRunStrategyBinding:
    evaluator = Vt01NyPrecisionCore()
    base = strategy_binding_factory(configuration_id_suffix=951)
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
    assert isinstance(rebuilt, Success)
    run = rebuilt.value
    methodology_id, methodology_version, methodology_fingerprint = evaluator.methodology()
    manifest = build_research_strategy_configuration_manifest(
        configuration_id=run.strategy_configuration_id,
        schema_version=base.manifest.schema_version,
        parameters=(
            ResearchStrategyParameter("trader.code", evaluator.trader_code),
            ResearchStrategyParameter(
                "trader.config_fingerprint",
                evaluator.config_fingerprint().value,
            ),
            ResearchStrategyParameter("trader.instrument", "EURUSD"),
            ResearchStrategyParameter(
                "trader.methodology_fingerprint",
                methodology_fingerprint.value,
            ),
            ResearchStrategyParameter(
                "trader.methodology_id",
                methodology_id.value,
            ),
            ResearchStrategyParameter(
                "trader.methodology_version",
                methodology_version.value,
            ),
        ),
        frozen_at=run.created_at - timedelta(minutes=1),
        evidence_ref=ResearchStrategyFreezeEvidenceReference(
            UUID("76400000-0000-0000-0000-000000000001")
        ),
    )
    assert isinstance(manifest, Success)
    bound = build_research_run_strategy_binding(run=run, manifest=manifest.value)
    assert isinstance(bound, Success)
    return bound.value


def _post_monte_carlo_lifecycle(
    candidate: TraderLabCandidateBinding,
    stage_evidence_factory: _StageEvidenceFactory,
) -> TraderLabLifecycle:
    lifecycle = start_trader_lab_lifecycle(candidate)
    prior_stages = MANDATORY_STAGES[
        : MANDATORY_STAGES.index(TraderLabStage.RISK_REVIEW)
    ]
    for offset, stage in enumerate(prior_stages):
        evidence = stage_evidence_factory(
            stage=stage,
            candidate=candidate,
            evidence_suffix=9_500 + offset,
            produced_at=_NOW + timedelta(minutes=offset),
        )
        promoted = apply_trader_lab_promotion(
            lifecycle,
            TraderLabPromotionRequest(stage=stage, evidence=evidence),
        )
        assert isinstance(promoted, Success)
        lifecycle = promoted.value
    assert lifecycle.state is TraderLabState.MONTE_CARLO_QUALIFIED
    return lifecycle


def _decision(candidate: TraderLabCandidateBinding, suffix: int) -> FunctionalDecision:
    return FunctionalDecision(
        decision_id=DecisionId(_uuid("76900000", 100 + suffix)),
        timestamp=candidate.strategy_binding.run.simulated_start + timedelta(minutes=1),
        decision_type=DecisionType("core.trade"),
        status=DecisionStatus.RESOLVED,
        priority=DecisionPriority.NORMAL,
        metadata=DecisionMetadata(
            correlation_id=CorrelationId(_uuid("76900000", 200 + suffix))
        ),
        reasons=(
            DecisionReason(
                code=DecisionReasonCode("research.performance"),
                summary="Trader Lab authority-chain economic evidence",
            ),
        ),
        outcome=DecisionOutcome.APPROVED,
    )


def _intent(
    candidate: TraderLabCandidateBinding,
    *,
    side: OrderSide,
    suffix: int,
) -> OrderIntent:
    created_at = candidate.strategy_binding.run.simulated_start + timedelta(
        minutes=1,
        seconds=1,
    )
    return OrderIntent(
        intent_id=OrderIntentId(_uuid("76a00000", 100 + suffix)),
        idempotency_key=ExecutionIdempotencyKey(_uuid("76a00000", 200 + suffix)),
        instrument=ExecutionInstrument("EURUSD"),
        side=side,
        order_type=OrderType.MARKET,
        quantity=OrderQuantity(Decimal("1")),
        created_at=created_at,
        metadata=ExternalRequestMetadata(
            correlation_id=CorrelationId(_uuid("76a00000", 300 + suffix))
        ),
    )


def _fill(
    candidate: TraderLabCandidateBinding,
    *,
    side: OrderSide,
    suffix: int,
    filled_at: datetime,
) -> ResearchFillEvidence:
    run = candidate.strategy_binding.run
    intent = _intent(candidate, side=side, suffix=suffix)
    intent_evidence = build_research_execution_intent_evidence(
        evidence_id=ResearchExecutionIntentEvidenceId(_uuid("76b00000", 100 + suffix)),
        run=run,
        decision=_decision(candidate, suffix),
        intent=intent,
        evidenced_at=intent.created_at + timedelta(seconds=1),
    )
    assert isinstance(intent_evidence, Success), intent_evidence
    built = build_research_fill_evidence(
        fill_id=ResearchFillId(_uuid("76b00000", 200 + suffix)),
        intent_evidence=intent_evidence.value,
        source=_EXECUTION_SOURCE,
        price=OrderPrice(Decimal("1.10000")),
        quantity=OrderQuantity(Decimal("1")),
        filled_at=filled_at,
        evidence_ref=ResearchEconomicEvidenceReference(
            _uuid("76b00000", 300 + suffix)
        ),
    )
    assert isinstance(built, Success), built
    return built.value


def _return_observation(
    candidate: TraderLabCandidateBinding,
    *,
    index: int,
    rate: Decimal,
) -> ResearchReturnObservation:
    run = candidate.strategy_binding.run
    entry_at = run.simulated_start + timedelta(minutes=2, seconds=index * 2)
    exit_at = entry_at + timedelta(seconds=1)
    entry = _fill(
        candidate,
        side=OrderSide.BUY,
        suffix=index * 2,
        filled_at=entry_at,
    )
    exit_fill = _fill(
        candidate,
        side=OrderSide.SELL,
        suffix=index * 2 + 1,
        filled_at=exit_at,
    )
    capital = MoneyAmount(currency=_USD, amount=Decimal("100000"))
    gross = build_research_gross_economic_result(
        result_id=ResearchEconomicResultId(_uuid("76c00000", 100 + index)),
        run=run,
        entry_fills=(entry,),
        exit_fills=(exit_fill,),
        gross_pnl=MoneyAmount(currency=_USD, amount=capital.amount * rate),
        valued_at=exit_at + timedelta(seconds=1),
        evidence_ref=ResearchEconomicEvidenceReference(
            _uuid("76c00000", 200 + index)
        ),
    )
    assert isinstance(gross, Success), gross
    observed = build_research_return_observation(
        observation_id=ResearchReturnObservationId(_uuid("76c00000", 300 + index)),
        source_result=gross.value,
        capital_basis=capital,
        observed_at=gross.value.valued_at + timedelta(seconds=1),
    )
    assert isinstance(observed, Success), observed
    return observed.value


def _performance(
    candidate: TraderLabCandidateBinding,
) -> ResearchPerformanceStatisticsSnapshot:
    rates = (Decimal("0.01"), Decimal("0.02"), Decimal("-0.01"), Decimal("0.03"))
    observations = tuple(
        _return_observation(candidate, index=index, rate=rate)
        for index, rate in enumerate(rates, start=1)
    )
    built = build_research_performance_statistics(
        snapshot_id=ResearchPerformanceSnapshotId(
            UUID("76700000-0000-0000-0000-000000000001")
        ),
        observations=observations,
        observed_at=max(item.observed_at for item in observations) + timedelta(seconds=1),
    )
    assert isinstance(built, Success), built
    return built.value


def test_governed_authority_chain_reaches_demo_eligible_without_lab_minting(
    strategy_binding_factory: _StrategyBindingFactory,
    candidate_factory: _CandidateFactory,
    stage_evidence_factory: _StageEvidenceFactory,
) -> None:
    evaluator = Vt01NyPrecisionCore()
    binding = _bound_vt01_strategy(strategy_binding_factory)
    candidate = candidate_factory(
        candidate_suffix=951,
        version=evaluator.version,
        binding=binding,
    )
    lifecycle = _post_monte_carlo_lifecycle(candidate, stage_evidence_factory)
    performance = _performance(candidate)
    economic_evidence = reference_instrument_bound_research_economic(
        candidate,
        performance.observations[0],
    )

    completed = complete_first_cohort_authority_chain(
        FirstCohortAuthorityInput(
            lifecycle=lifecycle,
            performance=performance,
            economic_evidence=economic_evidence,
            qualified_timeframes=("M5",),
            risk_policy=RiskTraderLabPolicy(
                policy_id="first-demo-v1",
                min_sample_size=4,
                max_population_variance=Decimal("0.01"),
            ),
            risk_reviewed_at=_NOW + timedelta(hours=2),
            cibo_reviewed_at=_NOW + timedelta(hours=3),
            independent_validated_at=_NOW + timedelta(hours=4),
        )
    )

    assert isinstance(completed, Success), completed
    assert completed.value.trader_code.value == "vt-01"
    assert completed.value.lifecycle.state is TraderLabState.DEMO_ELIGIBLE
    assert completed.value.lifecycle.completed_stages == MANDATORY_STAGES
    risk_ref = completed.value.lifecycle.qualifications[-4].evidence.source_reference
    cibo_ref = completed.value.lifecycle.qualifications[-3].evidence.source_reference
    independent_ref = completed.value.lifecycle.qualifications[-2].evidence.source_reference
    economic_ref = completed.value.lifecycle.qualifications[-1].evidence.source_reference
    assert risk_ref.external_authenticity_proof is not None
    assert cibo_ref.external_authenticity_proof is not None
    assert independent_ref.external_authenticity_proof is not None
    assert economic_ref.kind is TraderLabEvidenceKind.ECONOMIC_EVALUATION
    assert economic_ref.self_authenticating is True


def test_risk_policy_blocks_authority_chain_before_cibo(
    strategy_binding_factory: _StrategyBindingFactory,
    candidate_factory: _CandidateFactory,
    stage_evidence_factory: _StageEvidenceFactory,
) -> None:
    evaluator = Vt01NyPrecisionCore()
    binding = _bound_vt01_strategy(strategy_binding_factory)
    candidate = candidate_factory(
        candidate_suffix=952,
        version=evaluator.version,
        binding=binding,
    )
    lifecycle = _post_monte_carlo_lifecycle(candidate, stage_evidence_factory)
    performance = _performance(candidate)
    economic_evidence = reference_instrument_bound_research_economic(
        candidate,
        performance.observations[0],
    )

    blocked = complete_first_cohort_authority_chain(
        FirstCohortAuthorityInput(
            lifecycle=lifecycle,
            performance=performance,
            economic_evidence=economic_evidence,
            qualified_timeframes=("M5",),
            risk_policy=RiskTraderLabPolicy(
                policy_id="first-demo-v1",
                min_sample_size=100,
                max_population_variance=Decimal("0.01"),
            ),
            risk_reviewed_at=_NOW + timedelta(hours=2),
            cibo_reviewed_at=_NOW + timedelta(hours=3),
            independent_validated_at=_NOW + timedelta(hours=4),
        )
    )

    assert isinstance(blocked, Failure)
