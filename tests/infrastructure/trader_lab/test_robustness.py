from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

import pytest

from qore.infrastructure.research_block_bootstrap import (
    ResearchBlockBootstrapDistribution,
    ResearchBlockBootstrapDistributionId,
    ResearchBlockBootstrapPolicy,
    build_research_block_bootstrap_distribution,
)
from qore.infrastructure.research_economic_evidence import ResearchReturnObservation
from qore.infrastructure.research_resampling_envelope import (
    ResearchResamplingEnvelope,
    ResearchResamplingEnvelopeId,
    ResearchResamplingEnvelopePolicy,
    build_research_resampling_envelope,
)
from qore.infrastructure.research_sampling_frame import ResearchSamplingFrame
from qore.infrastructure.research_serial_dependence import (
    ResearchSerialDependenceDiagnostic,
    ResearchSerialDependenceDiagnosticId,
    build_research_serial_dependence_diagnostic,
)
from qore.infrastructure.trader_lab.candidate import (
    TraderLabCandidateBinding,
    TraderLabValidationError,
    _canonical_decimal,
)
from qore.infrastructure.trader_lab.robustness import (
    TraderLabCostPerturbationSpec,
    TraderLabExperimentId,
    TraderLabExperimentRegistration,
    TraderLabMonteCarloEvidenceId,
    TraderLabMonteCarloStatus,
    TraderLabRobustnessFamily,
    TraderLabStressEvidenceId,
    TraderLabStressStatus,
    TraderLabThreshold,
    build_trader_lab_experiment_registration,
    build_trader_lab_monte_carlo_experiment_evidence,
    build_trader_lab_stress_evidence,
    compute_trader_lab_experiment_fingerprint,
    reference_trader_lab_monte_carlo,
    reference_trader_lab_stress,
)
from qore.kernel.result import Failure, Success

_PROCESS_TIME = datetime(2026, 8, 9, 12, 0, tzinfo=UTC)

_CandidateFactory = Callable[..., TraderLabCandidateBinding]


def _uuid(suffix: int) -> UUID:
    return UUID(f"76000000-0000-0000-0000-{suffix:012d}")


def _sample(value: str) -> ResearchReturnObservation:
    sample = object.__new__(ResearchReturnObservation)
    object.__setattr__(sample, "return_rate", Decimal(value))
    return sample


def _diagnostic(*values: str) -> ResearchSerialDependenceDiagnostic:
    frame = object.__new__(ResearchSamplingFrame)
    object.__setattr__(frame, "samples", tuple(_sample(value) for value in values))
    built = build_research_serial_dependence_diagnostic(
        diagnostic_id=ResearchSerialDependenceDiagnosticId(_uuid(1)),
        frame=frame,
    )
    assert isinstance(built, Success)
    return built.value


def _distribution(
    diagnostic: ResearchSerialDependenceDiagnostic,
    *,
    block_length: int,
    resample_count: int,
    seed: int,
    suffix: int,
) -> ResearchBlockBootstrapDistribution:
    built = build_research_block_bootstrap_distribution(
        distribution_id=ResearchBlockBootstrapDistributionId(_uuid(suffix)),
        diagnostic=diagnostic,
        policy=ResearchBlockBootstrapPolicy(
            block_length=block_length,
            resample_count=resample_count,
            seed=seed,
        ),
    )
    assert isinstance(built, Success)
    return built.value


def _envelope(
    distribution: ResearchBlockBootstrapDistribution,
    *,
    suffix: int,
) -> ResearchResamplingEnvelope:
    built = build_research_resampling_envelope(
        envelope_id=ResearchResamplingEnvelopeId(_uuid(suffix)),
        distribution=distribution,
        policy=ResearchResamplingEnvelopePolicy(
            lower_quantile_bps=500,
            upper_quantile_bps=9500,
        ),
    )
    assert isinstance(built, Success)
    return built.value


def _registration(
    candidate: TraderLabCandidateBinding,
    *,
    block_length: int = 2,
    seed: int = 42,
    simulation_count: int = 16,
    min_sample_size: int = 4,
    suffix: int = 1,
) -> TraderLabExperimentRegistration:
    built = build_trader_lab_experiment_registration(
        experiment_id=TraderLabExperimentId(_uuid(suffix)),
        candidate=candidate,
        family=TraderLabRobustnessFamily.BLOCK_BOOTSTRAP,
        algorithm="research.circular_block_bootstrap",
        algorithm_version="v1",
        block_length=block_length,
        seed=seed,
        simulation_count=simulation_count,
        min_sample_size=min_sample_size,
        thresholds=(
            TraderLabThreshold("distribution.source_mean", Decimal("-0.01"), None),
        ),
        registered_at=_PROCESS_TIME,
    )
    assert isinstance(built, Success)
    return built.value


def test_registration_fingerprint_is_sensitive_to_seed_and_threshold(
    candidate_factory: _CandidateFactory,
) -> None:
    candidate = candidate_factory()
    base = _registration(candidate, seed=42, suffix=1)
    different_seed = _registration(candidate, seed=43, suffix=2)
    assert base.fingerprint != different_seed.fingerprint

    changed_threshold = build_trader_lab_experiment_registration(
        experiment_id=TraderLabExperimentId(_uuid(3)),
        candidate=candidate,
        family=TraderLabRobustnessFamily.BLOCK_BOOTSTRAP,
        algorithm="research.circular_block_bootstrap",
        algorithm_version="v1",
        block_length=2,
        seed=42,
        simulation_count=16,
        min_sample_size=4,
        thresholds=(
            TraderLabThreshold("distribution.source_mean", Decimal("-0.02"), None),
        ),
        registered_at=_PROCESS_TIME,
    )
    assert isinstance(changed_threshold, Success)
    assert base.fingerprint != changed_threshold.value.fingerprint


def test_registration_rejects_zero_negative_and_bool_simulation_count(
    candidate_factory: _CandidateFactory,
) -> None:
    candidate = candidate_factory()
    for bad_count in (0, -1):
        built = build_trader_lab_experiment_registration(
            experiment_id=TraderLabExperimentId(_uuid(10)),
            candidate=candidate,
            family=TraderLabRobustnessFamily.BLOCK_BOOTSTRAP,
            algorithm="research.circular_block_bootstrap",
            algorithm_version="v1",
            block_length=2,
            seed=42,
            simulation_count=bad_count,
            min_sample_size=4,
            thresholds=(),
            registered_at=_PROCESS_TIME,
        )
        assert isinstance(built, Failure)
    bool_count: Any = True
    built = build_trader_lab_experiment_registration(
        experiment_id=TraderLabExperimentId(_uuid(11)),
        candidate=candidate,
        family=TraderLabRobustnessFamily.BLOCK_BOOTSTRAP,
        algorithm="research.circular_block_bootstrap",
        algorithm_version="v1",
        block_length=2,
        seed=42,
        simulation_count=bool_count,
        min_sample_size=4,
        thresholds=(),
        registered_at=_PROCESS_TIME,
    )
    assert isinstance(built, Failure)


def test_monte_carlo_qualifies_on_sufficient_sample(candidate_factory: _CandidateFactory) -> None:
    candidate = candidate_factory()
    registration = _registration(candidate, suffix=20)
    diagnostic = _diagnostic("0.10", "-0.05", "0.20", "0.00", "0.15")
    distribution = _distribution(
        diagnostic,
        block_length=2,
        resample_count=16,
        seed=42,
        suffix=21,
    )
    envelope = _envelope(distribution, suffix=22)
    built = build_trader_lab_monte_carlo_experiment_evidence(
        evidence_id=TraderLabMonteCarloEvidenceId(_uuid(23)),
        registration=registration,
        policy=ResearchBlockBootstrapPolicy(
            block_length=2,
            resample_count=16,
            seed=42,
        ),
        distribution=distribution,
        envelope=envelope,
    )
    assert isinstance(built, Success)
    assert built.value.status is TraderLabMonteCarloStatus.QUALIFIED


def test_insufficient_sample_cannot_qualify(candidate_factory: _CandidateFactory) -> None:
    candidate = candidate_factory()
    registration = _registration(candidate, min_sample_size=10, suffix=30)
    diagnostic = _diagnostic("0.10", "-0.05", "0.20", "0.00")
    distribution = _distribution(
        diagnostic,
        block_length=2,
        resample_count=16,
        seed=42,
        suffix=31,
    )
    envelope = _envelope(distribution, suffix=32)
    built = build_trader_lab_monte_carlo_experiment_evidence(
        evidence_id=TraderLabMonteCarloEvidenceId(_uuid(33)),
        registration=registration,
        policy=ResearchBlockBootstrapPolicy(
            block_length=2,
            resample_count=16,
            seed=42,
        ),
        distribution=distribution,
        envelope=envelope,
    )
    assert isinstance(built, Success)
    assert built.value.status is TraderLabMonteCarloStatus.INSUFFICIENT_SAMPLE


def test_zero_variance_dependence_cannot_qualify(candidate_factory: _CandidateFactory) -> None:
    candidate = candidate_factory()
    registration = _registration(candidate, suffix=40)
    diagnostic = _diagnostic("1", "1", "1", "1")
    distribution = _distribution(
        diagnostic,
        block_length=2,
        resample_count=16,
        seed=42,
        suffix=41,
    )
    envelope = _envelope(distribution, suffix=42)
    built = build_trader_lab_monte_carlo_experiment_evidence(
        evidence_id=TraderLabMonteCarloEvidenceId(_uuid(43)),
        registration=registration,
        policy=ResearchBlockBootstrapPolicy(
            block_length=2,
            resample_count=16,
            seed=42,
        ),
        distribution=distribution,
        envelope=envelope,
    )
    assert isinstance(built, Success)
    assert built.value.status is TraderLabMonteCarloStatus.UNSUPPORTED_DEPENDENCE


def test_seed_substitution_and_simulation_count_mutation_are_rejected(
    candidate_factory: _CandidateFactory,
) -> None:
    candidate = candidate_factory()
    registration = _registration(candidate, seed=42, simulation_count=16, suffix=50)
    diagnostic = _diagnostic("0.10", "-0.05", "0.20", "0.00", "0.15")
    distribution = _distribution(
        diagnostic,
        block_length=2,
        resample_count=16,
        seed=42,
        suffix=51,
    )
    envelope = _envelope(distribution, suffix=52)

    seed_swapped = build_trader_lab_monte_carlo_experiment_evidence(
        evidence_id=TraderLabMonteCarloEvidenceId(_uuid(53)),
        registration=registration,
        policy=ResearchBlockBootstrapPolicy(
            block_length=2,
            resample_count=16,
            seed=7,
        ),
        distribution=distribution,
        envelope=envelope,
    )
    assert isinstance(seed_swapped, Failure)
    assert "seed must match" in str(seed_swapped.error)

    count_changed = build_trader_lab_monte_carlo_experiment_evidence(
        evidence_id=TraderLabMonteCarloEvidenceId(_uuid(54)),
        registration=registration,
        policy=ResearchBlockBootstrapPolicy(
            block_length=2,
            resample_count=8,
            seed=42,
        ),
        distribution=distribution,
        envelope=envelope,
    )
    assert isinstance(count_changed, Failure)
    assert "resample_count must match" in str(count_changed.error)


def test_same_spec_seeds_and_sample_reproduce_identical_evidence() -> None:
    diagnostic = _diagnostic("0.10", "-0.05", "0.20", "0.00", "0.15")
    first_dist = _distribution(
        diagnostic, block_length=2, resample_count=16, seed=42, suffix=61
    )
    second_dist = _distribution(
        diagnostic, block_length=2, resample_count=16, seed=42, suffix=62
    )
    assert first_dist.resampled_means == second_dist.resampled_means


def test_cost_spec_rejects_negative_and_bool_bounds() -> None:
    with pytest.raises(TraderLabValidationError):
        TraderLabCostPerturbationSpec(spread_bps=-1, slippage_bps=0, cost_bps=0)
    bad_bps: Any = True
    with pytest.raises(TraderLabValidationError):
        TraderLabCostPerturbationSpec(spread_bps=bad_bps, slippage_bps=0, cost_bps=0)


def test_monte_carlo_requires_block_bootstrap_registration(
    candidate_factory: _CandidateFactory,
) -> None:
    candidate = candidate_factory()
    built = build_trader_lab_experiment_registration(
        experiment_id=TraderLabExperimentId(_uuid(70)),
        candidate=candidate,
        family=TraderLabRobustnessFamily.START_SUBWINDOW,
        algorithm="research.start_subwindow",
        algorithm_version="v1",
        block_length=None,
        seed=None,
        simulation_count=16,
        min_sample_size=4,
        thresholds=(),
        registered_at=_PROCESS_TIME,
    )
    assert isinstance(built, Success)
    diagnostic = _diagnostic("0.10", "-0.05", "0.20", "0.00", "0.15")
    distribution = _distribution(
        diagnostic, block_length=2, resample_count=16, seed=42, suffix=71
    )
    envelope = _envelope(distribution, suffix=72)
    built_evidence = build_trader_lab_monte_carlo_experiment_evidence(
        evidence_id=TraderLabMonteCarloEvidenceId(_uuid(73)),
        registration=built.value,
        policy=ResearchBlockBootstrapPolicy(
            block_length=2, resample_count=16, seed=42
        ),
        distribution=distribution,
        envelope=envelope,
    )
    assert isinstance(built_evidence, Failure)
    assert "block bootstrap" in str(built_evidence.error)


def test_diagnostic_insufficient_sample_cannot_qualify(
    candidate_factory: _CandidateFactory,
) -> None:
    candidate = candidate_factory()
    # min_sample_size <= sample_size so the distribution-size guard passes, but
    # the lag-one diagnostic reports INSUFFICIENT_SAMPLE for fewer than 3 samples.
    registration = _registration(candidate, min_sample_size=2, suffix=80)
    diagnostic = _diagnostic("0.10", "-0.05")
    distribution = _distribution(
        diagnostic, block_length=2, resample_count=16, seed=42, suffix=81
    )
    envelope = _envelope(distribution, suffix=82)
    built = build_trader_lab_monte_carlo_experiment_evidence(
        evidence_id=TraderLabMonteCarloEvidenceId(_uuid(83)),
        registration=registration,
        policy=ResearchBlockBootstrapPolicy(
            block_length=2, resample_count=16, seed=42
        ),
        distribution=distribution,
        envelope=envelope,
    )
    assert isinstance(built, Success)
    assert built.value.status is TraderLabMonteCarloStatus.INSUFFICIENT_SAMPLE


def test_experiment_fingerprint_rejects_bool_int_metadata(
    candidate_factory: _CandidateFactory,
) -> None:
    candidate = candidate_factory()
    with pytest.raises(TraderLabValidationError):
        compute_trader_lab_experiment_fingerprint(
            experiment_id=TraderLabExperimentId(_uuid(90)),
            candidate=candidate,
            family=TraderLabRobustnessFamily.BLOCK_BOOTSTRAP,
            algorithm="research.circular_block_bootstrap",
            algorithm_version="v1",
            block_length=2,
            seed=42,
            simulation_count=True,
            min_sample_size=4,
            thresholds=(),
            registered_at=_PROCESS_TIME,
        )


def test_canonical_decimal_normalizes_scale_and_negative_zero() -> None:
    assert (
        _canonical_decimal(Decimal("1.0"))
        == _canonical_decimal(Decimal("1.00"))
        == "1"
    )
    assert _canonical_decimal(Decimal("-0.0")) == "0"
    assert _canonical_decimal(Decimal("0.0500")) == _canonical_decimal(Decimal("0.05"))
    assert _canonical_decimal(Decimal("100")) == "1E+2"


def test_monte_carlo_threshold_violation_fails_closed(
    candidate_factory: _CandidateFactory,
) -> None:
    candidate = candidate_factory()
    built = build_trader_lab_experiment_registration(
        experiment_id=TraderLabExperimentId(_uuid(100)),
        candidate=candidate,
        family=TraderLabRobustnessFamily.BLOCK_BOOTSTRAP,
        algorithm="research.circular_block_bootstrap",
        algorithm_version="v1",
        block_length=2,
        seed=42,
        simulation_count=16,
        min_sample_size=4,
        thresholds=(
            TraderLabThreshold("distribution.source_mean", Decimal("100"), None),
        ),
        registered_at=_PROCESS_TIME,
    )
    assert isinstance(built, Success)
    diagnostic = _diagnostic("0.10", "-0.05", "0.20", "0.00", "0.15")
    distribution = _distribution(
        diagnostic, block_length=2, resample_count=16, seed=42, suffix=101
    )
    envelope = _envelope(distribution, suffix=102)
    evidence = build_trader_lab_monte_carlo_experiment_evidence(
        evidence_id=TraderLabMonteCarloEvidenceId(_uuid(103)),
        registration=built.value,
        policy=ResearchBlockBootstrapPolicy(
            block_length=2, resample_count=16, seed=42
        ),
        distribution=distribution,
        envelope=envelope,
    )
    assert isinstance(evidence, Success)
    assert evidence.value.status is TraderLabMonteCarloStatus.THRESHOLD_VIOLATION


def test_monte_carlo_unsupported_metric_fails_closed(
    candidate_factory: _CandidateFactory,
) -> None:
    candidate = candidate_factory()
    built = build_trader_lab_experiment_registration(
        experiment_id=TraderLabExperimentId(_uuid(110)),
        candidate=candidate,
        family=TraderLabRobustnessFamily.BLOCK_BOOTSTRAP,
        algorithm="research.circular_block_bootstrap",
        algorithm_version="v1",
        block_length=2,
        seed=42,
        simulation_count=16,
        min_sample_size=4,
        thresholds=(TraderLabThreshold("profitability", Decimal("0.0"), None),),
        registered_at=_PROCESS_TIME,
    )
    assert isinstance(built, Success)
    diagnostic = _diagnostic("0.10", "-0.05", "0.20", "0.00", "0.15")
    distribution = _distribution(
        diagnostic, block_length=2, resample_count=16, seed=42, suffix=111
    )
    envelope = _envelope(distribution, suffix=112)
    evidence = build_trader_lab_monte_carlo_experiment_evidence(
        evidence_id=TraderLabMonteCarloEvidenceId(_uuid(113)),
        registration=built.value,
        policy=ResearchBlockBootstrapPolicy(
            block_length=2, resample_count=16, seed=42
        ),
        distribution=distribution,
        envelope=envelope,
    )
    assert isinstance(evidence, Success)
    assert evidence.value.status is TraderLabMonteCarloStatus.INSUFFICIENT_EVIDENCE


def test_monte_carlo_reference_requires_qualified(
    candidate_factory: _CandidateFactory,
) -> None:
    candidate = candidate_factory()
    built = build_trader_lab_experiment_registration(
        experiment_id=TraderLabExperimentId(_uuid(120)),
        candidate=candidate,
        family=TraderLabRobustnessFamily.BLOCK_BOOTSTRAP,
        algorithm="research.circular_block_bootstrap",
        algorithm_version="v1",
        block_length=2,
        seed=42,
        simulation_count=16,
        min_sample_size=4,
        thresholds=(
            TraderLabThreshold("distribution.source_mean", Decimal("100"), None),
        ),
        registered_at=_PROCESS_TIME,
    )
    assert isinstance(built, Success)
    diagnostic = _diagnostic("0.10", "-0.05", "0.20", "0.00", "0.15")
    distribution = _distribution(
        diagnostic, block_length=2, resample_count=16, seed=42, suffix=121
    )
    envelope = _envelope(distribution, suffix=122)
    evidence = build_trader_lab_monte_carlo_experiment_evidence(
        evidence_id=TraderLabMonteCarloEvidenceId(_uuid(123)),
        registration=built.value,
        policy=ResearchBlockBootstrapPolicy(
            block_length=2, resample_count=16, seed=42
        ),
        distribution=distribution,
        envelope=envelope,
    )
    assert isinstance(evidence, Success)
    assert evidence.value.status is TraderLabMonteCarloStatus.THRESHOLD_VIOLATION
    with pytest.raises(TraderLabValidationError):
        reference_trader_lab_monte_carlo(candidate, evidence.value)


def test_stress_reference_rejects_failed(
    candidate_factory: _CandidateFactory,
) -> None:
    candidate = candidate_factory()
    failed = build_trader_lab_stress_evidence(
        evidence_id=TraderLabStressEvidenceId(_uuid(130)),
        candidate=candidate,
        family=TraderLabRobustnessFamily.COST_PERTURBATION,
        scenario="cost-perturbation-2x",
        bounds=(Decimal("0.0"), Decimal("0.01")),
        status=TraderLabStressStatus.FAILED,
        certified_at=_PROCESS_TIME,
    )
    assert isinstance(failed, Success)
    with pytest.raises(TraderLabValidationError):
        reference_trader_lab_stress(candidate, failed.value)
