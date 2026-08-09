from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from uuid import UUID

import pytest

from qore.infrastructure.research_periodic_autocorrelation_profile import (
    ResearchPeriodicAutocorrelationPolicy,
    ResearchPeriodicAutocorrelationProfileId,
    ResearchPeriodicAutocorrelationStatus,
    ResearchPeriodicAutocorrelationValidationError,
    build_research_periodic_autocorrelation_profile,
)
from qore.infrastructure.research_periodic_equity import (
    ResearchPeriodicEquityReturnSeries,
    ResearchPeriodicReturnPoint,
)
from qore.kernel.result import Failure, Success


def _uuid(suffix: int) -> UUID:
    return UUID(f"84000000-0000-0000-0000-{suffix:012d}")


def _point(value: str) -> ResearchPeriodicReturnPoint:
    point = object.__new__(ResearchPeriodicReturnPoint)
    object.__setattr__(point, "return_rate", Decimal(value))
    return point


def _series(*values: str) -> ResearchPeriodicEquityReturnSeries:
    series = object.__new__(ResearchPeriodicEquityReturnSeries)
    object.__setattr__(series, "returns", tuple(_point(value) for value in values))
    return series


def test_profile_derives_all_requested_lags_in_order() -> None:
    built = build_research_periodic_autocorrelation_profile(
        profile_id=ResearchPeriodicAutocorrelationProfileId(_uuid(1)),
        series=_series("1", "2", "3", "4"),
        policy=ResearchPeriodicAutocorrelationPolicy(max_lag=2),
    )
    assert isinstance(built, Success)
    assert tuple(point.lag for point in built.value.points) == (1, 2)
    assert tuple(point.pair_count for point in built.value.points) == (3, 2)
    assert tuple(point.correlation for point in built.value.points) == (
        Decimal("1"),
        Decimal("1"),
    )


def test_alternating_sequence_exposes_opposite_lag_signs() -> None:
    built = build_research_periodic_autocorrelation_profile(
        profile_id=ResearchPeriodicAutocorrelationProfileId(_uuid(2)),
        series=_series("1", "-1", "1", "-1"),
        policy=ResearchPeriodicAutocorrelationPolicy(max_lag=2),
    )
    assert isinstance(built, Success)
    assert built.value.points[0].correlation == Decimal("-1")
    assert built.value.points[1].correlation == Decimal("1")


def test_zero_variance_at_a_lag_is_explicitly_undefined() -> None:
    built = build_research_periodic_autocorrelation_profile(
        profile_id=ResearchPeriodicAutocorrelationProfileId(_uuid(3)),
        series=_series("1", "1", "1", "2"),
        policy=ResearchPeriodicAutocorrelationPolicy(max_lag=1),
    )
    assert isinstance(built, Success)
    point = built.value.points[0]
    assert point.status is ResearchPeriodicAutocorrelationStatus.UNDEFINED_ZERO_VARIANCE
    assert point.correlation is None


def test_profile_rejects_lag_without_two_pairs() -> None:
    built = build_research_periodic_autocorrelation_profile(
        profile_id=ResearchPeriodicAutocorrelationProfileId(_uuid(4)),
        series=_series("1", "2", "3", "4"),
        policy=ResearchPeriodicAutocorrelationPolicy(max_lag=3),
    )
    assert isinstance(built, Failure)
    assert "at least two return pairs" in str(built.error)


def test_profile_rejects_derived_point_tampering() -> None:
    built = build_research_periodic_autocorrelation_profile(
        profile_id=ResearchPeriodicAutocorrelationProfileId(_uuid(5)),
        series=_series("1", "2", "3", "4"),
        policy=ResearchPeriodicAutocorrelationPolicy(max_lag=2),
    )
    assert isinstance(built, Success)
    tampered = replace(built.value.points[0], correlation=Decimal("0"))
    with pytest.raises(ResearchPeriodicAutocorrelationValidationError):
        replace(built.value, points=(tampered, built.value.points[1]))


def test_profile_does_not_authorize_independence_or_annualization() -> None:
    built = build_research_periodic_autocorrelation_profile(
        profile_id=ResearchPeriodicAutocorrelationProfileId(_uuid(6)),
        series=_series("0.1", "0.2", "0.15", "0.25", "0.05"),
        policy=ResearchPeriodicAutocorrelationPolicy(max_lag=2),
    )
    assert isinstance(built, Success)
    profile = built.value
    assert not hasattr(profile, "iid")
    assert not hasattr(profile, "stationary")
    assert not hasattr(profile, "annualization_safe")
    assert not hasattr(profile, "annualized_sharpe")
    assert not hasattr(profile, "statistically_significant")
    assert not hasattr(profile, "production_ready")
