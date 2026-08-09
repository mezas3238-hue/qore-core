from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from uuid import UUID

import pytest

from qore.infrastructure.research_periodic_equity import (
    ResearchPeriodicEquityReturnSeries,
    ResearchPeriodicReturnPoint,
)
from qore.infrastructure.research_periodic_serial_dependence import (
    ResearchPeriodicLagOneStatus,
    ResearchPeriodicSerialDependenceValidationError,
    ResearchPeriodicSerialDiagnosticId,
    build_research_periodic_serial_dependence_diagnostic,
)
from qore.kernel.result import Success


def _uuid(suffix: int) -> UUID:
    return UUID(f"81000000-0000-0000-0000-{suffix:012d}")


def _point(value: str) -> ResearchPeriodicReturnPoint:
    point = object.__new__(ResearchPeriodicReturnPoint)
    object.__setattr__(point, "return_rate", Decimal(value))
    return point


def _series(*values: str) -> ResearchPeriodicEquityReturnSeries:
    series = object.__new__(ResearchPeriodicEquityReturnSeries)
    object.__setattr__(series, "returns", tuple(_point(value) for value in values))
    return series


def test_periodic_lag_one_detects_perfect_positive_dependence() -> None:
    built = build_research_periodic_serial_dependence_diagnostic(
        diagnostic_id=ResearchPeriodicSerialDiagnosticId(_uuid(1)),
        series=_series("0.1", "0.2", "0.3"),
    )

    assert isinstance(built, Success)
    diagnostic = built.value
    assert diagnostic.status is ResearchPeriodicLagOneStatus.DEFINED
    assert diagnostic.sample_size == 3
    assert diagnostic.pair_count == 2
    assert diagnostic.correlation == Decimal("1")


def test_periodic_lag_one_detects_perfect_negative_dependence() -> None:
    built = build_research_periodic_serial_dependence_diagnostic(
        diagnostic_id=ResearchPeriodicSerialDiagnosticId(_uuid(2)),
        series=_series("0.1", "-0.1", "0.1"),
    )

    assert isinstance(built, Success)
    assert built.value.status is ResearchPeriodicLagOneStatus.DEFINED
    assert built.value.correlation == Decimal("-1")


def test_periodic_lag_one_reports_insufficient_sample_without_number() -> None:
    built = build_research_periodic_serial_dependence_diagnostic(
        diagnostic_id=ResearchPeriodicSerialDiagnosticId(_uuid(3)),
        series=_series("0.1", "0.2"),
    )

    assert isinstance(built, Success)
    assert built.value.status is ResearchPeriodicLagOneStatus.INSUFFICIENT_SAMPLE
    assert built.value.pair_count == 1
    assert built.value.correlation is None


def test_periodic_lag_one_reports_zero_variance_as_undefined() -> None:
    built = build_research_periodic_serial_dependence_diagnostic(
        diagnostic_id=ResearchPeriodicSerialDiagnosticId(_uuid(4)),
        series=_series("0.1", "0.1", "0.1"),
    )

    assert isinstance(built, Success)
    assert built.value.status is ResearchPeriodicLagOneStatus.UNDEFINED_ZERO_VARIANCE
    assert built.value.correlation is None


def test_periodic_lag_one_rejects_metric_tampering() -> None:
    built = build_research_periodic_serial_dependence_diagnostic(
        diagnostic_id=ResearchPeriodicSerialDiagnosticId(_uuid(5)),
        series=_series("0.1", "0.2", "0.3"),
    )
    assert isinstance(built, Success)

    with pytest.raises(ResearchPeriodicSerialDependenceValidationError):
        replace(built.value, correlation=Decimal("0"))
    with pytest.raises(ResearchPeriodicSerialDependenceValidationError):
        replace(
            built.value,
            status=ResearchPeriodicLagOneStatus.UNDEFINED_ZERO_VARIANCE,
        )


def test_periodic_lag_one_does_not_authorize_time_scaling_or_inference() -> None:
    built = build_research_periodic_serial_dependence_diagnostic(
        diagnostic_id=ResearchPeriodicSerialDiagnosticId(_uuid(6)),
        series=_series("0.1", "0.2", "0.15", "0.25"),
    )
    assert isinstance(built, Success)
    diagnostic = built.value

    assert not hasattr(diagnostic, "iid")
    assert not hasattr(diagnostic, "stationary")
    assert not hasattr(diagnostic, "annualization_safe")
    assert not hasattr(diagnostic, "annualized_sharpe")
    assert not hasattr(diagnostic, "p_value")
    assert not hasattr(diagnostic, "statistically_significant")
    assert not hasattr(diagnostic, "production_ready")
