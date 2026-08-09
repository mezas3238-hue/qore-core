from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from uuid import UUID

import pytest

from qore.infrastructure.proprietary_accounts import CurrencyCode, MoneyAmount
from qore.infrastructure.research_periodic_drawdown import (
    ResearchPeriodicDrawdownSnapshotId,
    ResearchPeriodicDrawdownValidationError,
    build_research_periodic_drawdown_snapshot,
)
from qore.infrastructure.research_periodic_equity import (
    ResearchEquityObservationId,
    ResearchEquityValuationObservation,
    ResearchPeriodicEquityReturnSeries,
)
from qore.kernel.result import Success

_USD = CurrencyCode("USD")


def _uuid(suffix: int) -> UUID:
    return UUID(f"82000000-0000-0000-0000-{suffix:012d}")


def _observation(suffix: int, equity: str) -> ResearchEquityValuationObservation:
    observation = object.__new__(ResearchEquityValuationObservation)
    object.__setattr__(
        observation,
        "observation_id",
        ResearchEquityObservationId(_uuid(suffix)),
    )
    object.__setattr__(
        observation,
        "equity",
        MoneyAmount(currency=_USD, amount=Decimal(equity)),
    )
    return observation


def _series(*equities: str) -> ResearchPeriodicEquityReturnSeries:
    series = object.__new__(ResearchPeriodicEquityReturnSeries)
    object.__setattr__(
        series,
        "observations",
        tuple(_observation(index + 1, value) for index, value in enumerate(equities)),
    )
    return series


def test_periodic_drawdown_tracks_running_peaks_and_grid_drawdowns() -> None:
    built = build_research_periodic_drawdown_snapshot(
        snapshot_id=ResearchPeriodicDrawdownSnapshotId(_uuid(100)),
        series=_series("1000", "1100", "950", "1025", "1200"),
    )

    assert isinstance(built, Success)
    snapshot = built.value
    assert tuple(point.running_peak.amount for point in snapshot.points) == (
        Decimal("1000"),
        Decimal("1100"),
        Decimal("1100"),
        Decimal("1100"),
        Decimal("1200"),
    )
    assert tuple(point.drawdown_amount.amount for point in snapshot.points) == (
        Decimal("0"),
        Decimal("0"),
        Decimal("150"),
        Decimal("75"),
        Decimal("0"),
    )
    assert snapshot.maximum_drawdown_amount.amount == Decimal("150")
    assert snapshot.maximum_drawdown_rate == Decimal(
        "0.1363636363636363636363636363636364"
    )


def test_new_peak_resets_grid_drawdown_to_zero() -> None:
    built = build_research_periodic_drawdown_snapshot(
        snapshot_id=ResearchPeriodicDrawdownSnapshotId(_uuid(200)),
        series=_series("1000", "900", "1050"),
    )

    assert isinstance(built, Success)
    assert built.value.points[-1].drawdown_amount.amount == 0
    assert built.value.points[-1].drawdown_rate == 0


def test_periodic_drawdown_rejects_derived_metric_tampering() -> None:
    built = build_research_periodic_drawdown_snapshot(
        snapshot_id=ResearchPeriodicDrawdownSnapshotId(_uuid(300)),
        series=_series("1000", "900", "950"),
    )
    assert isinstance(built, Success)

    with pytest.raises(ResearchPeriodicDrawdownValidationError):
        replace(built.value, maximum_drawdown_rate=Decimal("0"))
    with pytest.raises(ResearchPeriodicDrawdownValidationError):
        replace(
            built.value,
            maximum_drawdown_amount=MoneyAmount(currency=_USD, amount=Decimal("0")),
        )


def test_periodic_drawdown_claims_no_intraperiod_extreme() -> None:
    built = build_research_periodic_drawdown_snapshot(
        snapshot_id=ResearchPeriodicDrawdownSnapshotId(_uuid(400)),
        series=_series("1000", "900", "950"),
    )
    assert isinstance(built, Success)
    snapshot = built.value

    assert not hasattr(snapshot, "intraperiod_maximum_drawdown")
    assert not hasattr(snapshot, "tick_drawdown")
    assert not hasattr(snapshot, "production_ready")
