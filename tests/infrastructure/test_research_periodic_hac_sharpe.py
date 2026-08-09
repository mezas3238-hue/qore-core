from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from uuid import UUID

import pytest

from qore.infrastructure.research_periodic_hac_risk import (
    ResearchPeriodicHacRiskSnapshot,
    ResearchPeriodicHacRiskStatus,
)
from qore.infrastructure.research_periodic_hac_sharpe import (
    ResearchPeriodicHacSharpeMetricId,
    ResearchPeriodicHacSharpePolicy,
    ResearchPeriodicHacSharpeStatus,
    ResearchPeriodicHacSharpeValidationError,
    build_research_periodic_hac_sharpe_metric,
)
from qore.kernel.result import Success

# Exact-head CI refresh against the current main baseline.


def _uuid(suffix: int) -> UUID:
    return UUID(f"86000000-0000-0000-0000-{suffix:012d}")


def _risk(
    *,
    mean: str,
    long_run_stddev: str,
    status: ResearchPeriodicHacRiskStatus = ResearchPeriodicHacRiskStatus.DEFINED,
) -> ResearchPeriodicHacRiskSnapshot:
    risk = object.__new__(ResearchPeriodicHacRiskSnapshot)
    object.__setattr__(risk, "mean_return", Decimal(mean))
    object.__setattr__(risk, "long_run_standard_deviation", Decimal(long_run_stddev))
    object.__setattr__(risk, "status", status)
    return risk


def test_hac_sharpe_uses_long_run_stddev_and_explicit_periodic_risk_free_rate() -> None:
    built = build_research_periodic_hac_sharpe_metric(
        metric_id=ResearchPeriodicHacSharpeMetricId(_uuid(1)),
        risk=_risk(mean="0.02", long_run_stddev="0.015"),
        policy=ResearchPeriodicHacSharpePolicy(
            risk_free_rate_per_period=Decimal("0.005")
        ),
    )
    assert isinstance(built, Success)
    metric = built.value
    assert metric.status is ResearchPeriodicHacSharpeStatus.DEFINED
    assert metric.mean_excess_return == Decimal("0.015")
    assert metric.hac_sharpe_ratio == Decimal("1")


def test_hac_sharpe_supports_negative_excess_return() -> None:
    built = build_research_periodic_hac_sharpe_metric(
        metric_id=ResearchPeriodicHacSharpeMetricId(_uuid(2)),
        risk=_risk(mean="-0.01", long_run_stddev="0.02"),
        policy=ResearchPeriodicHacSharpePolicy(
            risk_free_rate_per_period=Decimal("0")
        ),
    )
    assert isinstance(built, Success)
    assert built.value.hac_sharpe_ratio == Decimal("-0.5")


def test_zero_long_run_variance_produces_no_infinite_ratio() -> None:
    built = build_research_periodic_hac_sharpe_metric(
        metric_id=ResearchPeriodicHacSharpeMetricId(_uuid(3)),
        risk=_risk(
            mean="0.02",
            long_run_stddev="0",
            status=ResearchPeriodicHacRiskStatus.ZERO_LONG_RUN_VARIANCE,
        ),
        policy=ResearchPeriodicHacSharpePolicy(
            risk_free_rate_per_period=Decimal("0")
        ),
    )
    assert isinstance(built, Success)
    assert built.value.status is ResearchPeriodicHacSharpeStatus.ZERO_LONG_RUN_VARIANCE
    assert built.value.hac_sharpe_ratio is None


def test_hac_sharpe_policy_rejects_non_finite_rate() -> None:
    for value in (Decimal("NaN"), Decimal("Infinity"), Decimal("-Infinity")):
        with pytest.raises(ResearchPeriodicHacSharpeValidationError):
            ResearchPeriodicHacSharpePolicy(risk_free_rate_per_period=value)


def test_hac_sharpe_rejects_derived_metric_tampering() -> None:
    built = build_research_periodic_hac_sharpe_metric(
        metric_id=ResearchPeriodicHacSharpeMetricId(_uuid(4)),
        risk=_risk(mean="0.02", long_run_stddev="0.015"),
        policy=ResearchPeriodicHacSharpePolicy(
            risk_free_rate_per_period=Decimal("0.005")
        ),
    )
    assert isinstance(built, Success)
    with pytest.raises(ResearchPeriodicHacSharpeValidationError):
        replace(built.value, hac_sharpe_ratio=Decimal("999"))


def test_hac_sharpe_makes_no_annualized_or_inferential_claims() -> None:
    built = build_research_periodic_hac_sharpe_metric(
        metric_id=ResearchPeriodicHacSharpeMetricId(_uuid(5)),
        risk=_risk(mean="0.02", long_run_stddev="0.015"),
        policy=ResearchPeriodicHacSharpePolicy(
            risk_free_rate_per_period=Decimal("0")
        ),
    )
    assert isinstance(built, Success)
    metric = built.value
    assert not hasattr(metric, "annualized_sharpe")
    assert not hasattr(metric, "periods_per_year")
    assert not hasattr(metric, "stationary")
    assert not hasattr(metric, "p_value")
    assert not hasattr(metric, "statistically_significant")
    assert not hasattr(metric, "production_ready")
