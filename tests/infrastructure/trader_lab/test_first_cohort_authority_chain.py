from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from qore.infrastructure.research_economic_evidence import (
    ResearchEconomicResultId,
    ResearchGrossEconomicResult,
    ResearchReturnObservation,
    ResearchReturnObservationId,
)
from qore.infrastructure.research_performance_statistics import (
    ResearchPerformanceSnapshotId,
    ResearchPerformanceStatisticsSnapshot,
    build_research_performance_statistics,
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
from qore.infrastructure.trader_lab.lifecycle import (
    MANDATORY_STAGES,
    TraderLabLifecycle,
    TraderLabPromotionRequest,
    TraderLabState,
    apply_trader_lab_promotion,
    start_trader_lab_lifecycle,
)
from qore.infrastructure.trader_lab.stage_evidence import (
    TraderLabEvidenceReference,
    TraderLabStage,
    TraderLabStageEvidenceRecord,
)
from qore.infrastructure.traders.evaluators import Vt01NyPrecisionCore
from qore.kernel.result import Failure, Success

_NOW = datetime(2026, 9, 7, 12, 0, tzinfo=UTC)

_StrategyBindingFactory = Callable[..., ResearchRunStrategyBinding]
_CandidateFactory = Callable[..., TraderLabCandidateBinding]
_StageEvidenceFactory = Callable[..., TraderLabStageEvidenceRecord]
_EconomicReferenceFactory = Callable[
    [TraderLabCandidateBinding], TraderLabEvidenceReference
]


def _bound_vt01_strategy(
    strategy_binding_factory: _StrategyBindingFactory,
) -> ResearchRunStrategyBinding:
    evaluator = Vt01NyPrecisionCore()
    base = strategy_binding_factory(configuration_id_suffix=951)
    methodology_id, methodology_version, methodology_fingerprint = evaluator.methodology()
    manifest = build_research_strategy_configuration_manifest(
        configuration_id=base.run.strategy_configuration_id,
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
        frozen_at=base.run.created_at - timedelta(minutes=1),
        evidence_ref=ResearchStrategyFreezeEvidenceReference(
            UUID("76400000-0000-0000-0000-000000000001")
        ),
    )
    assert isinstance(manifest, Success)
    bound = build_research_run_strategy_binding(
        run=base.run,
        manifest=manifest.value,
    )
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


def _performance(
    candidate: TraderLabCandidateBinding,
) -> ResearchPerformanceStatisticsSnapshot:
    rates = ("0.01", "0.02", "-0.01", "0.03")
    observations: list[ResearchReturnObservation] = []
    for index, rate in enumerate(rates):
        gross = object.__new__(ResearchGrossEconomicResult)
        object.__setattr__(
            gross,
            "result_id",
            ResearchEconomicResultId(
                UUID(f"76500000-0000-0000-0000-{index + 1:012d}")
            ),
        )
        object.__setattr__(gross, "run", candidate.strategy_binding.run)
        object.__setattr__(gross, "entry_fills", ())
        object.__setattr__(gross, "exit_fills", ())
        observation = object.__new__(ResearchReturnObservation)
        object.__setattr__(
            observation,
            "observation_id",
            ResearchReturnObservationId(
                UUID(f"76600000-0000-0000-0000-{index + 1:012d}")
            ),
        )
        object.__setattr__(observation, "source_result", gross)
        object.__setattr__(
            observation,
            "observed_at",
            _NOW + timedelta(minutes=10 + index),
        )
        object.__setattr__(observation, "return_rate", Decimal(rate))
        observations.append(observation)
    built = build_research_performance_statistics(
        snapshot_id=ResearchPerformanceSnapshotId(
            UUID("76700000-0000-0000-0000-000000000001")
        ),
        observations=tuple(observations),
        observed_at=_NOW + timedelta(hours=1),
    )
    assert isinstance(built, Success)
    return built.value


def test_real_authority_chain_reaches_demo_eligible_without_lab_minting(
    strategy_binding_factory: _StrategyBindingFactory,
    candidate_factory: _CandidateFactory,
    stage_evidence_factory: _StageEvidenceFactory,
    economic_reference_factory: _EconomicReferenceFactory,
) -> None:
    evaluator = Vt01NyPrecisionCore()
    binding = _bound_vt01_strategy(strategy_binding_factory)
    candidate = candidate_factory(
        candidate_suffix=951,
        version=evaluator.version,
        binding=binding,
    )
    lifecycle = _post_monte_carlo_lifecycle(
        candidate,
        stage_evidence_factory,
    )
    performance = _performance(candidate)

    completed = complete_first_cohort_authority_chain(
        FirstCohortAuthorityInput(
            lifecycle=lifecycle,
            performance=performance,
            economic_evidence=economic_reference_factory(candidate),
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
    risk_ref = completed.value.lifecycle.qualifications[-3].evidence.source_reference
    cibo_ref = completed.value.lifecycle.qualifications[-2].evidence.source_reference
    independent_ref = completed.value.lifecycle.qualifications[-1].evidence.source_reference
    assert risk_ref.external_authenticity_proof is not None
    assert cibo_ref.external_authenticity_proof is not None
    assert independent_ref.external_authenticity_proof is not None


def test_risk_policy_blocks_authority_chain_before_cibo(
    strategy_binding_factory: _StrategyBindingFactory,
    candidate_factory: _CandidateFactory,
    stage_evidence_factory: _StageEvidenceFactory,
    economic_reference_factory: _EconomicReferenceFactory,
) -> None:
    evaluator = Vt01NyPrecisionCore()
    binding = _bound_vt01_strategy(strategy_binding_factory)
    candidate = candidate_factory(
        candidate_suffix=952,
        version=evaluator.version,
        binding=binding,
    )
    lifecycle = _post_monte_carlo_lifecycle(
        candidate,
        stage_evidence_factory,
    )
    performance = _performance(candidate)

    blocked = complete_first_cohort_authority_chain(
        FirstCohortAuthorityInput(
            lifecycle=lifecycle,
            performance=performance,
            economic_evidence=economic_reference_factory(candidate),
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
