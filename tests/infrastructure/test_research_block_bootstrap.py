from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from uuid import UUID

import pytest

from qore.infrastructure.research_block_bootstrap import (
    ResearchBlockBootstrapDistributionId,
    ResearchBlockBootstrapPolicy,
    ResearchBlockBootstrapValidationError,
    build_research_block_bootstrap_distribution,
)
from qore.infrastructure.research_economic_evidence import ResearchReturnObservation
from qore.infrastructure.research_sampling_frame import ResearchSamplingFrame
from qore.infrastructure.research_serial_dependence import (
    ResearchSerialDependenceDiagnostic,
    ResearchSerialDependenceDiagnosticId,
    build_research_serial_dependence_diagnostic,
)
from qore.kernel.result import Failure, Success


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


def test_full_length_circular_blocks_preserve_sample_mean_every_replicate() -> None:
    diagnostic = _diagnostic("1", "2", "3", "4")
    built = build_research_block_bootstrap_distribution(
        distribution_id=ResearchBlockBootstrapDistributionId(_uuid(10)),
        diagnostic=diagnostic,
        policy=ResearchBlockBootstrapPolicy(
            block_length=4,
            resample_count=8,
            seed=17,
        ),
    )

    assert isinstance(built, Success)
    distribution = built.value
    assert distribution.sample_size == 4
    assert distribution.source_mean == Decimal("2.5")
    assert distribution.resampled_means == (Decimal("2.5"),) * 8


def test_same_samples_policy_and_seed_produce_identical_resampling_distribution() -> None:
    diagnostic = _diagnostic("0.10", "-0.05", "0.20", "0.00", "0.15")
    policy = ResearchBlockBootstrapPolicy(
        block_length=2,
        resample_count=20,
        seed=42,
    )
    first = build_research_block_bootstrap_distribution(
        distribution_id=ResearchBlockBootstrapDistributionId(_uuid(20)),
        diagnostic=diagnostic,
        policy=policy,
    )
    second = build_research_block_bootstrap_distribution(
        distribution_id=ResearchBlockBootstrapDistributionId(_uuid(21)),
        diagnostic=diagnostic,
        policy=policy,
    )

    assert isinstance(first, Success)
    assert isinstance(second, Success)
    assert first.value.source_mean == second.value.source_mean
    assert first.value.resampled_means == second.value.resampled_means
    assert len(first.value.resampled_means) == 20


def test_seed_is_part_of_deterministic_resampling_policy() -> None:
    diagnostic = _diagnostic("0.10", "-0.05", "0.20", "0.00", "0.15", "-0.10")
    first = build_research_block_bootstrap_distribution(
        distribution_id=ResearchBlockBootstrapDistributionId(_uuid(30)),
        diagnostic=diagnostic,
        policy=ResearchBlockBootstrapPolicy(
            block_length=2,
            resample_count=32,
            seed=1,
        ),
    )
    second = build_research_block_bootstrap_distribution(
        distribution_id=ResearchBlockBootstrapDistributionId(_uuid(31)),
        diagnostic=diagnostic,
        policy=ResearchBlockBootstrapPolicy(
            block_length=2,
            resample_count=32,
            seed=2,
        ),
    )

    assert isinstance(first, Success)
    assert isinstance(second, Success)
    assert first.value.resampled_means != second.value.resampled_means


def test_policy_rejects_iid_singleton_blocks_and_blocks_larger_than_sample() -> None:
    with pytest.raises(ResearchBlockBootstrapValidationError):
        ResearchBlockBootstrapPolicy(block_length=1, resample_count=10, seed=0)

    diagnostic = _diagnostic("0.1", "0.2", "0.3")
    built = build_research_block_bootstrap_distribution(
        distribution_id=ResearchBlockBootstrapDistributionId(_uuid(40)),
        diagnostic=diagnostic,
        policy=ResearchBlockBootstrapPolicy(
            block_length=4,
            resample_count=10,
            seed=0,
        ),
    )
    assert isinstance(built, Failure)
    assert "cannot exceed source sample size" in str(built.error)


def test_distribution_rejects_derived_resampling_tampering() -> None:
    diagnostic = _diagnostic("0.1", "0.2", "-0.1", "0.05")
    built = build_research_block_bootstrap_distribution(
        distribution_id=ResearchBlockBootstrapDistributionId(_uuid(50)),
        diagnostic=diagnostic,
        policy=ResearchBlockBootstrapPolicy(
            block_length=2,
            resample_count=12,
            seed=5,
        ),
    )
    assert isinstance(built, Success)

    with pytest.raises(ResearchBlockBootstrapValidationError):
        replace(
            built.value,
            resampled_means=(Decimal("999"),) * 12,
        )
    with pytest.raises(ResearchBlockBootstrapValidationError):
        replace(built.value, source_mean=Decimal("999"))


def test_block_distribution_makes_no_interval_or_significance_claims() -> None:
    diagnostic = _diagnostic("0.1", "0.2", "0.15", "0.05")
    built = build_research_block_bootstrap_distribution(
        distribution_id=ResearchBlockBootstrapDistributionId(_uuid(60)),
        diagnostic=diagnostic,
        policy=ResearchBlockBootstrapPolicy(
            block_length=2,
            resample_count=10,
            seed=7,
        ),
    )
    assert isinstance(built, Success)
    distribution = built.value

    assert not hasattr(distribution, "confidence_interval")
    assert not hasattr(distribution, "p_value")
    assert not hasattr(distribution, "statistically_significant")
    assert not hasattr(distribution, "iid")
    assert not hasattr(distribution, "sharpe_ratio")
    assert not hasattr(distribution, "production_ready")
