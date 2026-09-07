from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest

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


def _bound_strategy(
    evaluator: object,
    *,
    index: int,
    strategy_binding_factory: _StrategyBindingFactory,
) -> ResearchRunStrategyBinding:
    base = strategy_binding_factory(configuration_id_suffix=300 + index)
    trader_code = str(getattr(evaluator, "trader_code"))
    version = str(getattr(evaluator, "version"))
    config = getattr(evaluator, "config_fingerprint")()
    methodology_id, methodology_version, methodology_fingerprint = getattr(
        evaluator, "methodology"
    )()
    manifest = build_research_strategy_configuration_manifest(
        configuration_id=base.run.strategy_configuration_id,
        schema_version=base.manifest.schema_version,
        parameters=(
            ResearchStrategyParameter("trader.code", trader_code),
            ResearchStrategyParameter("trader.config_fingerprint", config.value),
            ResearchStrategyParameter(
                "trader.methodology_fingerprint", methodology_fingerprint.value
            ),
            ResearchStrategyParameter("trader.methodology_id", methodology_id.value),
            ResearchStrategyParameter(
                "trader.methodology_version", methodology_version.value
            ),
        ),
        frozen_at=base.run.created_at - timedelta(minutes=1),
        evidence_ref=ResearchStrategyFreezeEvidenceReference(
            UUID(f"72000000-0000-0000-0000-{index + 1:012d}")
        ),
    )
    assert isinstance(manifest, Success)
    binding = build_research_run_strategy_binding(run=base.run, manifest=manifest.value)
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


def _performance(
    candidate: TraderLabCandidateBinding,
    *,
    index: int,
    rates: tuple[str, ...],
) -> ResearchPerformanceStatisticsSnapshot:
    observations: list[ResearchReturnObservation] = []
    for offset, rate in enumerate(rates):
        gross = object.__new__(ResearchGrossEconomicResult)
        object.__setattr__(
            gross,
            "result_id",
            ResearchEconomicResultId(
                UUID(f"73000000-0000-0000-{index + 1:04d}-{offset + 1:012d}")
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
                UUID(f"74000000-0000-0000-{index + 1:04d}-{offset + 1:012d}")
            ),
        )
        object.__setattr__(observation, "source_result", gross)
        object.__setattr__(observation, "observed_at", _NOW + timedelta(minutes=offset))
        object.__setattr__(observation, "return_rate", Decimal(rate))
        observations.append(observation)
    built = build_research_performance_statistics(
        snapshot_id=ResearchPerformanceSnapshotId(
            UUID(f"75000000-0000-0000-0000-{index + 1:012d}")
        ),
        observations=tuple(observations),
        observed_at=_NOW + timedelta(hours=1),
    )
    assert isinstance(built, Success), built
    return built.value


def _entry(
    evaluator: object,
    *,
    index: int,
    strategy_binding_factory: _StrategyBindingFactory,
    candidate_factory: _CandidateFactory,
    stage_evidence_factory: _StageEvidenceFactory,
    economic_reference_factory: _EconomicReferenceFactory,
    complete: bool = True,
) -> FirstCohortTraderLabEntry:
    binding = _bound_strategy(
        evaluator,
        index=index,
        strategy_binding_factory=strategy_binding_factory,
    )
    candidate = candidate_factory(
        candidate_suffix=400 + index,
        version=str(getattr(evaluator, "version")),
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
    methodology_id, methodology_version, methodology_fingerprint = getattr(
        evaluator, "methodology"
    )()
    code = str(getattr(evaluator, "trader_code"))
    return FirstCohortTraderLabEntry(
        trader_code=DemoTradingTraderCode(code),
        trader_version=DemoTradingTraderVersion(str(getattr(evaluator, "version"))),
        config_fingerprint=DemoTradingConfigFingerprint(
            getattr(evaluator, "config_fingerprint")().value
        ),
        methodology_id=DemoTradingMethodologyId(methodology_id.value),
        methodology_version=DemoTradingMethodologyVersion(methodology_version.value),
        methodology_fingerprint=DemoTradingMethodologyFingerprint(
            methodology_fingerprint.value
        ),
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
            complete=str(getattr(evaluator, "trader_code")) != incomplete_code,
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
