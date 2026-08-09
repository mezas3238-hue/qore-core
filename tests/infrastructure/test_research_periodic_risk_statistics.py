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
    ResearchPeriodicDispersionStatus,
    ResearchPeriodicRiskSnapshotId,
    ResearchPeriodicRiskStatisticsValidationError,
    build_research_periodic_risk_statistics,
)
from qore.kernel.result import Success


def _uuid(suffix: int) -> UUID:
    return UUID(f"79000000-0000-0000-0000-{suffix:012d}")


def _point(value: str) -> ResearchPeriodicReturnPoint:
    point = object.__new__(ResearchPeriodicReturnPoint)
    object.__setattr__(point, "return_rate", Decimal(value))
    return point


def _series(*values: str) -> ResearchPeriodicEquityReturnSeries:
    series = object.__new__(ResearchPeriodicEquityReturnSeries)
    object.__setattr__(series, "returns", tuple(_point(value) for value in values))
    return series


def test_periodic_risk_statistics_use_sample_variance_n_minus_one() -> None:
    built = build_research_periodic_risk_statistics(
        snapshot_id=ResearchPeriodicRiskSnapshotId(_uuid(1)),
        series=_series("0.10", "0.20", "0.30"),
    )

    assert isinstance(built, Success)
    snapshot = built.value
    assert snapshot.sample_size == 3
    assert snapshot.positive_count == 3
    assert snapshot.negative_count == 0
    assert snapshot.flat_count == 0
    assert snapshot.mean_return == Decimal("0.20")
    assert snapshot.minimum_return == Decimal("0.10")
    assert snapshot.maximum_return == Decimal("0.30")
    assert snapshot.dispersion_status is ResearchPeriodicDispersionStatus.DEFINED
    assert snapshot.sample_variance == Decimal("0.01")
    assert snapshot.sample_standard_deviation == Decimal("0.1")


def test_single_period_reports_insufficient_sample_without_fake_dispersion() -> None:
    built = build_research_periodic_risk_statistics(
        snapshot_id=ResearchPeriodicRiskSnapshotId(_uuid(2)),
        series=_series("0.05"),
    )

    assert isinstance(built, Success)
    snapshot = built.value
    assert snapshot.sample_size == 1
    assert snapshot.mean_return == Decimal("0.05")
    assert snapshot.dispersion_status is ResearchPeriodicDispersionStatus.INSUFFICIENT_SAMPLE
    assert snapshot.sample_variance is None
    assert snapshot.sample_standard_deviation is None


def test_constant_period_returns_report_zero_variance_explicitly() -> None:
    built = build_research_periodic_risk_statistics(
        snapshot_id=ResearchPeriodicRiskSnapshotId(_uuid(3)),
        series=_series("0.02", "0.02", "0.02"),
    )

    assert isinstance(built, Success)
    snapshot = built.value
    assert snapshot.dispersion_status is ResearchPeriodicDispersionStatus.ZERO_VARIANCE
    assert snapshot.sample_variance == Decimal("0")
    assert snapshot.sample_standard_deviation == Decimal("0")


def test_periodic_risk_statistics_count_positive_negative_and_flat_periods() -> None:
    built = build_research_periodic_risk_statistics(
        snapshot_id=ResearchPeriodicRiskSnapshotId(_uuid(4)),
        series=_series("0.10", "-0.05", "0", "0.02"),
    )

    assert isinstance(built, Success)
    snapshot = built.value
    assert snapshot.positive_count == 2
    assert snapshot.negative_count == 1
    assert snapshot.flat_count == 1


def test_periodic_risk_statistics_reject_derived_metric_tampering() -> None:
    built = build_research_periodic_risk_statistics(
        snapshot_id=ResearchPeriodicRiskSnapshotId(_uuid(5)),
        series=_series("0.10", "0.20", "0.30"),
    )
    assert isinstance(built, Success)

    with pytest.raises(ResearchPeriodicRiskStatisticsValidationError):
        replace(built.value, mean_return=Decimal("999"))
    with pytest.raises(ResearchPeriodicRiskStatisticsValidationError):
        replace(built.value, sample_variance=Decimal("999"))
    with pytest.raises(ResearchPeriodicRiskStatisticsValidationError):
        replace(
            built.value,
            dispersion_status=ResearchPeriodicDispersionStatus.ZERO_VARIANCE,
        )


def test_periodic_risk_statistics_make_no_annualized_or_inferential_claims() -> None:
    built = build_research_periodic_risk_statistics(
        snapshot_id=ResearchPeriodicRiskSnapshotId(_uuid(6)),
        series=_series("0.10", "-0.05", "0.02"),
    )
    assert isinstance(built, Success)
    snapshot = built.value

    assert not hasattr(snapshot, "annualized_return")
    assert not hasattr(snapshot, "annualized_volatility")
    assert not hasattr(snapshot, "sharpe_ratio")
    assert not hasattr(snapshot, "sortino_ratio")
    assert not hasattr(snapshot, "p_value")
    assert not hasattr(snapshot, "statistically_significant")
    assert not hasattr(snapshot, "production_ready")
