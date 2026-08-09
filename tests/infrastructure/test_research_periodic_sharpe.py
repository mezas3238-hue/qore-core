from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from uuid import UUID

import pytest

from qore.infrastructure.research_periodic_risk_statistics import (
    ResearchPeriodicDispersionStatus,
    ResearchPeriodicRiskStatisticsSnapshot,
)
from qore.infrastructure.research_periodic_sharpe import (
    ResearchPeriodicSharpeMetricId,
    ResearchPeriodicSharpePolicy,
    ResearchPeriodicSharpeStatus,
    ResearchPeriodicSharpeValidationError,
    build_research_periodic_sharpe_metric,
)
from qore.kernel.result import Success


def _uuid(suffix: int) -> UUID:
    return UUID(f"80000000-0000-0000-0000-{suffix:012d}")


def _statistics(
    *,
    mean: str,
    standard_deviation: str | None,
    status: ResearchPeriodicDispersionStatus,
) -> ResearchPeriodicRiskStatisticsSnapshot:
    statistics = object.__new__(ResearchPeriodicRiskStatisticsSnapshot)
    object.__setattr__(statistics, "mean_return", Decimal(mean))
    object.__setattr__(
        statistics,
        "sample_standard_deviation",
        Decimal(standard_deviation) if standard_deviation is not None else None,
    )
    object.__setattr__(statistics, "dispersion_status", status)
    return statistics


def test_periodic_sharpe_uses_same_interval_risk_free_rate() -> None:
    built = build_research_periodic_sharpe_metric(
        metric_id=ResearchPeriodicSharpeMetricId(_uuid(1)),
        statistics=_statistics(
            mean="0.02",
            standard_deviation="0.01",
            status=ResearchPeriodicDispersionStatus.DEFINED,
        ),
        policy=ResearchPeriodicSharpePolicy(
            risk_free_rate_per_period=Decimal("0.005")
        ),
    )

    assert isinstance(built, Success)
    metric = built.value
    assert metric.status is ResearchPeriodicSharpeStatus.DEFINED
    assert metric.mean_excess_return == Decimal("0.015")
    assert metric.sharpe_ratio == Decimal("1.5")


def test_periodic_sharpe_supports_negative_excess_return() -> None:
    built = build_research_periodic_sharpe_metric(
        metric_id=ResearchPeriodicSharpeMetricId(_uuid(2)),
        statistics=_statistics(
            mean="-0.01",
            standard_deviation="0.02",
            status=ResearchPeriodicDispersionStatus.DEFINED,
        ),
        policy=ResearchPeriodicSharpePolicy(
            risk_free_rate_per_period=Decimal("0")
        ),
    )

    assert isinstance(built, Success)
    assert built.value.sharpe_ratio == Decimal("-0.5")


def test_insufficient_sample_produces_no_sharpe_number() -> None:
    built = build_research_periodic_sharpe_metric(
        metric_id=ResearchPeriodicSharpeMetricId(_uuid(3)),
        statistics=_statistics(
            mean="0.02",
            standard_deviation=None,
            status=ResearchPeriodicDispersionStatus.INSUFFICIENT_SAMPLE,
        ),
        policy=ResearchPeriodicSharpePolicy(
            risk_free_rate_per_period=Decimal("0.001")
        ),
    )

    assert isinstance(built, Success)
    metric = built.value
    assert metric.status is ResearchPeriodicSharpeStatus.INSUFFICIENT_SAMPLE
    assert metric.mean_excess_return == Decimal("0.019")
    assert metric.sharpe_ratio is None


def test_zero_variance_produces_no_infinite_sharpe() -> None:
    built = build_research_periodic_sharpe_metric(
        metric_id=ResearchPeriodicSharpeMetricId(_uuid(4)),
        statistics=_statistics(
            mean="0.02",
            standard_deviation="0",
            status=ResearchPeriodicDispersionStatus.ZERO_VARIANCE,
        ),
        policy=ResearchPeriodicSharpePolicy(
            risk_free_rate_per_period=Decimal("0")
        ),
    )

    assert isinstance(built, Success)
    assert built.value.status is ResearchPeriodicSharpeStatus.ZERO_VARIANCE
    assert built.value.sharpe_ratio is None


def test_risk_free_policy_rejects_non_finite_values() -> None:
    for value in (Decimal("NaN"), Decimal("Infinity"), Decimal("-Infinity")):
        with pytest.raises(ResearchPeriodicSharpeValidationError):
            ResearchPeriodicSharpePolicy(risk_free_rate_per_period=value)


def test_periodic_sharpe_rejects_metric_tampering() -> None:
    built = build_research_periodic_sharpe_metric(
        metric_id=ResearchPeriodicSharpeMetricId(_uuid(5)),
        statistics=_statistics(
            mean="0.02",
            standard_deviation="0.01",
            status=ResearchPeriodicDispersionStatus.DEFINED,
        ),
        policy=ResearchPeriodicSharpePolicy(
            risk_free_rate_per_period=Decimal("0.005")
        ),
    )
    assert isinstance(built, Success)

    with pytest.raises(ResearchPeriodicSharpeValidationError):
        replace(built.value, sharpe_ratio=Decimal("999"))
    with pytest.raises(ResearchPeriodicSharpeValidationError):
        replace(built.value, mean_excess_return=Decimal("999"))


def test_periodic_sharpe_makes_no_annualized_or_inferential_claims() -> None:
    built = build_research_periodic_sharpe_metric(
        metric_id=ResearchPeriodicSharpeMetricId(_uuid(6)),
        statistics=_statistics(
            mean="0.02",
            standard_deviation="0.01",
            status=ResearchPeriodicDispersionStatus.DEFINED,
        ),
        policy=ResearchPeriodicSharpePolicy(
            risk_free_rate_per_period=Decimal("0")
        ),
    )
    assert isinstance(built, Success)
    metric = built.value

    assert not hasattr(metric, "annualized_sharpe")
    assert not hasattr(metric, "periods_per_year")
    assert not hasattr(metric, "iid")
    assert not hasattr(metric, "stationary")
    assert not hasattr(metric, "p_value")
    assert not hasattr(metric, "statistically_significant")
    assert not hasattr(metric, "production_ready")
