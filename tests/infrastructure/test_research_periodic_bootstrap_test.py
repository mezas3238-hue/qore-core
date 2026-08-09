from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from uuid import UUID

import pytest

from qore.infrastructure.research_periodic_bootstrap_test import (
    ResearchPeriodicBootstrapAlternative,
    ResearchPeriodicBootstrapTestId,
    ResearchPeriodicBootstrapTestPolicy,
    ResearchPeriodicBootstrapTestValidationError,
    build_research_periodic_bootstrap_test_evidence,
)
from qore.infrastructure.research_periodic_equity import (
    ResearchPeriodicEquityReturnSeries,
    ResearchPeriodicReturnPoint,
)
from qore.kernel.result import Failure, Success


def _uuid(suffix: int) -> UUID:
    return UUID(f"87000000-0000-0000-0000-{suffix:012d}")


def _point(value: str) -> ResearchPeriodicReturnPoint:
    point = object.__new__(ResearchPeriodicReturnPoint)
    object.__setattr__(point, "return_rate", Decimal(value))
    return point


def _series(*values: str) -> ResearchPeriodicEquityReturnSeries:
    series = object.__new__(ResearchPeriodicEquityReturnSeries)
    object.__setattr__(series, "returns", tuple(_point(value) for value in values))
    return series


def test_full_length_blocks_give_exact_plus_one_p_value_under_positive_mean() -> None:
    built = build_research_periodic_bootstrap_test_evidence(
        test_id=ResearchPeriodicBootstrapTestId(_uuid(1)),
        series=_series("1", "1", "1", "1"),
        policy=ResearchPeriodicBootstrapTestPolicy(
            null_mean_per_period=Decimal("0"),
            alternative=ResearchPeriodicBootstrapAlternative.GREATER,
            block_length=4,
            resample_count=9,
            seed=7,
        ),
    )
    assert isinstance(built, Success)
    evidence = built.value
    assert evidence.observed_mean == Decimal("1")
    assert evidence.null_resampled_means == (Decimal("0"),) * 9
    assert evidence.extreme_count == 0
    assert evidence.bootstrap_p_value == Decimal("0.1")


def test_null_equal_observed_mean_yields_unit_p_value() -> None:
    built = build_research_periodic_bootstrap_test_evidence(
        test_id=ResearchPeriodicBootstrapTestId(_uuid(2)),
        series=_series("1", "1", "1", "1"),
        policy=ResearchPeriodicBootstrapTestPolicy(
            null_mean_per_period=Decimal("1"),
            alternative=ResearchPeriodicBootstrapAlternative.TWO_SIDED,
            block_length=4,
            resample_count=9,
            seed=7,
        ),
    )
    assert isinstance(built, Success)
    assert built.value.extreme_count == 9
    assert built.value.bootstrap_p_value == Decimal("1")


def test_same_policy_and_seed_are_reproducible() -> None:
    series = _series("0.1", "-0.05", "0.2", "0", "0.15")
    policy = ResearchPeriodicBootstrapTestPolicy(
        null_mean_per_period=Decimal("0"),
        alternative=ResearchPeriodicBootstrapAlternative.GREATER,
        block_length=2,
        resample_count=20,
        seed=42,
    )
    first = build_research_periodic_bootstrap_test_evidence(
        test_id=ResearchPeriodicBootstrapTestId(_uuid(3)),
        series=series,
        policy=policy,
    )
    second = build_research_periodic_bootstrap_test_evidence(
        test_id=ResearchPeriodicBootstrapTestId(_uuid(4)),
        series=series,
        policy=policy,
    )
    assert isinstance(first, Success)
    assert isinstance(second, Success)
    assert first.value.null_resampled_means == second.value.null_resampled_means
    assert first.value.bootstrap_p_value == second.value.bootstrap_p_value


def test_bootstrap_test_rejects_too_short_sample_or_oversized_block() -> None:
    short = build_research_periodic_bootstrap_test_evidence(
        test_id=ResearchPeriodicBootstrapTestId(_uuid(5)),
        series=_series("0.1", "0.2"),
        policy=ResearchPeriodicBootstrapTestPolicy(
            null_mean_per_period=Decimal("0"),
            alternative=ResearchPeriodicBootstrapAlternative.GREATER,
            block_length=2,
            resample_count=10,
            seed=0,
        ),
    )
    oversized = build_research_periodic_bootstrap_test_evidence(
        test_id=ResearchPeriodicBootstrapTestId(_uuid(6)),
        series=_series("0.1", "0.2", "0.3"),
        policy=ResearchPeriodicBootstrapTestPolicy(
            null_mean_per_period=Decimal("0"),
            alternative=ResearchPeriodicBootstrapAlternative.GREATER,
            block_length=4,
            resample_count=10,
            seed=0,
        ),
    )
    assert isinstance(short, Failure)
    assert isinstance(oversized, Failure)


def test_bootstrap_test_rejects_derived_p_value_tampering() -> None:
    built = build_research_periodic_bootstrap_test_evidence(
        test_id=ResearchPeriodicBootstrapTestId(_uuid(7)),
        series=_series("0.1", "0.2", "0.3", "0.4"),
        policy=ResearchPeriodicBootstrapTestPolicy(
            null_mean_per_period=Decimal("0"),
            alternative=ResearchPeriodicBootstrapAlternative.GREATER,
            block_length=2,
            resample_count=12,
            seed=5,
        ),
    )
    assert isinstance(built, Success)
    with pytest.raises(ResearchPeriodicBootstrapTestValidationError):
        replace(built.value, bootstrap_p_value=Decimal("0.999"))


def test_bootstrap_p_value_does_not_create_significance_or_production_verdict() -> None:
    built = build_research_periodic_bootstrap_test_evidence(
        test_id=ResearchPeriodicBootstrapTestId(_uuid(8)),
        series=_series("0.1", "0.2", "0.3", "0.4"),
        policy=ResearchPeriodicBootstrapTestPolicy(
            null_mean_per_period=Decimal("0"),
            alternative=ResearchPeriodicBootstrapAlternative.GREATER,
            block_length=2,
            resample_count=20,
            seed=1,
        ),
    )
    assert isinstance(built, Success)
    evidence = built.value
    assert not hasattr(evidence, "alpha")
    assert not hasattr(evidence, "significant")
    assert not hasattr(evidence, "multiple_testing_corrected")
    assert not hasattr(evidence, "stationary")
    assert not hasattr(evidence, "production_ready")
