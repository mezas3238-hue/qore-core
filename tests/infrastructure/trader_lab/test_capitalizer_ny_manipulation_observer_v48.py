from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import CapitalizerM1Bar
from qore.infrastructure.trader_lab.capitalizer_ny_manipulation_observer_v48 import (
    V48NYManipulationState,
    V48NYSweptSide,
    observe_new_york_manipulation,
)
from qore.infrastructure.trader_lab.capitalizer_source_observation_detectors_v2 import (
    CapitalizerSourceDirection,
)


def _bar(minute: int, open_: str, high: str, low: str, close: str) -> CapitalizerM1Bar:
    opened = datetime(2026, 1, 2, 14, minute, tzinfo=UTC)
    return CapitalizerM1Bar(
        symbol="XAUUSD",
        opened_at=opened,
        closed_at=opened + timedelta(minutes=1),
        open=Decimal(open_),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
        volume=1,
        digits=2,
    )


def test_bullish_london_low_sweep_plus_cisd_confirms_profile() -> None:
    bars = (
        _bar(0, "100.0", "100.2", "99.5", "99.7"),
        _bar(1, "99.7", "99.9", "98.8", "99.2"),
        _bar(2, "99.2", "100.1", "98.7", "99.5"),
        _bar(3, "99.5", "100.4", "99.4", "100.3"),
    )
    result = observe_new_york_manipulation(
        bars,
        london_range_high=Decimal("102"),
        london_range_low=Decimal("99"),
        london_context_resolved=True,
    )
    assert result.state is V48NYManipulationState.CONFIRMED
    assert result.swept_side is V48NYSweptSide.LOW
    assert result.direction is CapitalizerSourceDirection.BULLISH
    assert result.swept_level == Decimal("99")


def test_bearish_london_high_sweep_plus_cisd_confirms_profile() -> None:
    bars = (
        _bar(0, "101.0", "101.5", "100.8", "101.3"),
        _bar(1, "101.3", "102.4", "101.2", "101.8"),
        _bar(2, "101.8", "102.5", "101.5", "101.7"),
        _bar(3, "101.7", "101.8", "100.7", "100.8"),
    )
    result = observe_new_york_manipulation(
        bars,
        london_range_high=Decimal("102"),
        london_range_low=Decimal("99"),
        london_context_resolved=True,
    )
    assert result.state is V48NYManipulationState.CONFIRMED
    assert result.swept_side is V48NYSweptSide.HIGH
    assert result.direction is CapitalizerSourceDirection.BEARISH


def test_sweep_without_close_through_opposing_series_stays_wait() -> None:
    bars = (
        _bar(0, "100.0", "100.2", "99.5", "99.7"),
        _bar(1, "99.7", "99.9", "98.8", "99.2"),
        _bar(2, "99.2", "99.8", "98.7", "99.4"),
        _bar(3, "99.4", "99.9", "99.3", "99.8"),
    )
    result = observe_new_york_manipulation(
        bars,
        london_range_high=Decimal("102"),
        london_range_low=Decimal("99"),
        london_context_resolved=True,
    )
    assert result.state is V48NYManipulationState.WAIT


def test_unresolved_london_context_fails_closed_before_sweep() -> None:
    bars = (
        _bar(0, "100.0", "100.2", "98.8", "99.5"),
        _bar(1, "99.5", "100.5", "99.4", "100.4"),
    )
    result = observe_new_york_manipulation(
        bars,
        london_range_high=Decimal("102"),
        london_range_low=Decimal("99"),
        london_context_resolved=False,
    )
    assert result.state is V48NYManipulationState.WAIT
    assert result.swept_side is None
    assert result.outcome_used is False
