from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from uuid import UUID

import pytest

from qore.infrastructure.research_periodic_equity import (
    ResearchPeriodicEquityReturnSeries,
    ResearchPeriodicReturnPoint,
)
from qore.infrastructure.research_periodic_risk_statistics import (
    ResearchPeriodicRiskStatisticsSnapshot,
)
from qore.infrastructure.research_periodic_sortino import (
    ResearchPeriodicSortinoMetricId,
    ResearchPeriodicSortinoPolicy,
    ResearchPeriodicSortinoStatus,
    ResearchPeriodicSortinoValidationError,
    build_research_periodic_sortino_metric,
)
from qore.kernel.result import Success


def _uuid(suffix: int) -> UUID:
    return UUID(f"83000000-0000-0000-0000-{suffix:012d}")


def _point(value: str) -> ResearchPeriodicReturnPoint:
    point = object.__new__(ResearchPeriodicReturnPoint)
    object.__setattr__(point, "return_rate", Decimal(value))
    return point


def _statistics(*values: str) -> ResearchPeriodicRiskStatisticsSnapshot:
    series = object.__new__(ResearchPeriodicEquityReturnSeries)
    object.__setattr__(series, "returns", tuple(_point(value) for value in values))
    statistics = object.__new__(ResearchPeriodicRiskStatisticsSnapshot)
    object.__setattr__(statistics, "series", series)
    object.__setattr__(statistics, "sample_size", len(values))
    object.__setattr__(
        statistics,
        "mean_return",
        sum((Decimal(value) for value in values), Decimal(0)) / Decimal(len(values)),
    )
    return statistics


def test_periodic_sortino_uses_explicit_mar_and_all_periods_denominator() -> None:
    built = build_research_periodic_sortino_metric(
        metric_id=ResearchPeriodicSortinoMetricId(_uuid(1)),
        statistics=_statistics("0.10", "-0.10", "0.10", "-0.10"),
        policy=ResearchPeriodicSortinoPolicy(
            minimum_acceptable_return_per_period=Decimal("0")
        ),
    )

    assert isinstance(built, Success)
    metric = built.value
    assert metric.status is ResearchPeriodicSortinoStatus.DEFINED
    assert metric.mean_excess_return == Decimal("0")
    assert metric.downside_observation_count == 2
    assert metric.downside_deviation == Decimal(
        "0.07071067811865475244008443621048490"
    )
    assert metric.sortino_ratio == Decimal("0E+34")


def test_periodic_sortino_supports_nonzero_minimum_acceptable_return() -> None:
    built = build_research_periodic_sortino_metric(
        metric_id=ResearchPeriodicSortinoMetricId(_uuid(2)),
        statistics=_statistics("0.03", "0.01", "0.02"),
        policy=ResearchPeriodicSortinoPolicy(
            minimum_acceptable_return_per_period=Decimal("0.02")
        ),
    )

    assert isinstance(built, Success)
    metric = built.value
    assert metric.status is ResearchPeriodicSortinoStatus.DEFINED
    assert metric.mean_excess_return == Decimal("0")
    assert metric.downside_observation_count == 1
    assert metric.downside_deviation is not None
    assert metric.downside_deviation > 0
    assert metric.sortino_ratio == 0


def test_no_downside_deviation_produces_no_infinite_sortino() -> None:
    built = build_research_periodic_sortino_metric(
        metric_id=ResearchPeriodicSortinoMetricId(_uuid(3)),
        statistics=_statistics("0.03", "0.04", "0.05"),
        policy=ResearchPeriodicSortinoPolicy(
            minimum_acceptable_return_per_period=Decimal("0.02")
        ),
    )

    assert isinstance(built, Success)
    metric = built.value
    assert metric.status is ResearchPeriodicSortinoStatus.NO_DOWNSIDE_DEVIATION
    assert metric.downside_observation_count == 0
    assert metric.downside_deviation == 0
    assert metric.sortino_ratio is None


def test_single_period_reports_insufficient_sample_without_sortino() -> None:
    built = build_research_periodic_sortino_metric(
        metric_id=ResearchPeriodicSortinoMetricId(_uuid(4)),
        statistics=_statistics("-0.01"),
        policy=ResearchPeriodicSortinoPolicy(
            minimum_acceptable_return_per_period=Decimal("0")
        ),
    )

    assert isinstance(built, Success)
    metric = built.value
    assert metric.status is ResearchPeriodicSortinoStatus.INSUFFICIENT_SAMPLE
    assert metric.downside_observation_count == 1
    assert metric.downside_deviation is None
    assert metric.sortino_ratio is None


def test_mar_policy_rejects_non_finite_values() -> None:
    for value in (Decimal("NaN"), Decimal("Infinity"), Decimal("-Infinity")):
        with pytest.raises(ResearchPeriodicSortinoValidationError):
            ResearchPeriodicSortinoPolicy(
                minimum_acceptable_return_per_period=value
            )


def test_periodic_sortino_rejects_derived_metric_tampering() -> None:
    built = build_research_periodic_sortino_metric(
        metric_id=ResearchPeriodicSortinoMetricId(_uuid(5)),
        statistics=_statistics("0.04", "-0.01", "0.03"),
        policy=ResearchPeriodicSortinoPolicy(
            minimum_acceptable_return_per_period=Decimal("0")
        ),
    )
    assert isinstance(built, Success)

    with pytest.raises(ResearchPeriodicSortinoValidationError):
        replace(built.value, sortino_ratio=Decimal("999"))
    with pytest.raises(ResearchPeriodicSortinoValidationError):
        replace(built.value, downside_deviation=Decimal("999"))


def test_periodic_sortino_makes_no_annualized_or_inferential_claims() -> None:
    built = build_research_periodic_sortino_metric(
        metric_id=ResearchPeriodicSortinoMetricId(_uuid(6)),
        statistics=_statistics("0.04", "-0.01", "0.03"),
        policy=ResearchPeriodicSortinoPolicy(
            minimum_acceptable_return_per_period=Decimal("0")
        ),
    )
    assert isinstance(built, Success)
    metric = built.value

    assert not hasattr(metric, "annualized_sortino")
    assert not hasattr(metric, "periods_per_year")
    assert not hasattr(metric, "iid")
    assert not hasattr(metric, "stationary")
    assert not hasattr(metric, "p_value")
    assert not hasattr(metric, "statistically_significant")
    assert not hasattr(metric, "production_ready")
