from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from uuid import UUID

import pytest

from qore.infrastructure.research_periodic_equity import (
    ResearchPeriodicEquityReturnSeries,
    ResearchPeriodicReturnPoint,
)
from qore.infrastructure.research_periodic_hac_risk import (
    ResearchPeriodicHacPolicy,
    ResearchPeriodicHacRiskSnapshotId,
    ResearchPeriodicHacRiskStatus,
    ResearchPeriodicHacRiskValidationError,
    build_research_periodic_hac_risk_snapshot,
)
from qore.kernel.result import Failure, Success


def _uuid(suffix: int) -> UUID:
    return UUID(f"85000000-0000-0000-0000-{suffix:012d}")


def _point(value: str) -> ResearchPeriodicReturnPoint:
    point = object.__new__(ResearchPeriodicReturnPoint)
    object.__setattr__(point, "return_rate", Decimal(value))
    return point


def _series(*values: str) -> ResearchPeriodicEquityReturnSeries:
    series = object.__new__(ResearchPeriodicEquityReturnSeries)
    object.__setattr__(series, "returns", tuple(_point(value) for value in values))
    return series


def test_hac_zero_lag_equals_population_variance_of_periodic_returns() -> None:
    built = build_research_periodic_hac_risk_snapshot(
        snapshot_id=ResearchPeriodicHacRiskSnapshotId(_uuid(1)),
        series=_series("1", "2", "3"),
        policy=ResearchPeriodicHacPolicy(max_lag=0),
    )
    assert isinstance(built, Success)
    snapshot = built.value
    assert snapshot.mean_return == Decimal("2")
    assert snapshot.autocovariances == (
        Decimal("0.6666666666666666666666666666666667"),
    )
    assert snapshot.bartlett_weights == ()
    assert snapshot.long_run_variance == snapshot.autocovariances[0]
    assert snapshot.status is ResearchPeriodicHacRiskStatus.DEFINED


def test_bartlett_lag_one_adjusts_long_run_variance_for_serial_dependence() -> None:
    built = build_research_periodic_hac_risk_snapshot(
        snapshot_id=ResearchPeriodicHacRiskSnapshotId(_uuid(2)),
        series=_series("1", "2", "3", "4"),
        policy=ResearchPeriodicHacPolicy(max_lag=1),
    )
    assert isinstance(built, Success)
    snapshot = built.value
    assert snapshot.bartlett_weights == (Decimal("0.5"),)
    assert snapshot.autocovariances[0] == Decimal("1.25")
    assert snapshot.autocovariances[1] == Decimal("0.3125")
    assert snapshot.long_run_variance == Decimal("1.5625")
    assert snapshot.long_run_standard_deviation == Decimal("1.25")


def test_constant_returns_report_zero_long_run_variance() -> None:
    built = build_research_periodic_hac_risk_snapshot(
        snapshot_id=ResearchPeriodicHacRiskSnapshotId(_uuid(3)),
        series=_series("0.1", "0.1", "0.1"),
        policy=ResearchPeriodicHacPolicy(max_lag=1),
    )
    assert isinstance(built, Success)
    assert built.value.status is ResearchPeriodicHacRiskStatus.ZERO_LONG_RUN_VARIANCE
    assert built.value.long_run_variance == 0
    assert built.value.long_run_standard_deviation == 0


def test_hac_rejects_invalid_lag_or_insufficient_sample() -> None:
    too_large = build_research_periodic_hac_risk_snapshot(
        snapshot_id=ResearchPeriodicHacRiskSnapshotId(_uuid(4)),
        series=_series("0.1", "0.2"),
        policy=ResearchPeriodicHacPolicy(max_lag=2),
    )
    too_short = build_research_periodic_hac_risk_snapshot(
        snapshot_id=ResearchPeriodicHacRiskSnapshotId(_uuid(5)),
        series=_series("0.1"),
        policy=ResearchPeriodicHacPolicy(max_lag=0),
    )
    assert isinstance(too_large, Failure)
    assert isinstance(too_short, Failure)


def test_hac_rejects_derived_metric_tampering() -> None:
    built = build_research_periodic_hac_risk_snapshot(
        snapshot_id=ResearchPeriodicHacRiskSnapshotId(_uuid(6)),
        series=_series("1", "2", "3", "4"),
        policy=ResearchPeriodicHacPolicy(max_lag=1),
    )
    assert isinstance(built, Success)
    with pytest.raises(ResearchPeriodicHacRiskValidationError):
        replace(built.value, long_run_variance=Decimal("999"))


def test_hac_risk_makes_no_stationarity_annualization_or_production_claims() -> None:
    built = build_research_periodic_hac_risk_snapshot(
        snapshot_id=ResearchPeriodicHacRiskSnapshotId(_uuid(7)),
        series=_series("0.1", "0.2", "0.15", "0.25"),
        policy=ResearchPeriodicHacPolicy(max_lag=1),
    )
    assert isinstance(built, Success)
    snapshot = built.value
    assert not hasattr(snapshot, "stationary")
    assert not hasattr(snapshot, "annualized_volatility")
    assert not hasattr(snapshot, "annualized_sharpe")
    assert not hasattr(snapshot, "p_value")
    assert not hasattr(snapshot, "production_ready")
