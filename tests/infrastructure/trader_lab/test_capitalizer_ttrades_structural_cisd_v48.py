from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab.capitalizer_source_observation_detectors_v2 import (
    CapitalizerSourceBar,
    CapitalizerSourceDirection,
)
from qore.infrastructure.trader_lab.capitalizer_ttrades_structural_cisd_v48 import (
    V48TimedSourceBar,
    observe_first_structural_cisd,
)


def _bar(
    minute: int,
    open_: str,
    high: str,
    low: str,
    close: str,
) -> V48TimedSourceBar:
    opened = datetime(2026, 1, 2, 10, minute, tzinfo=UTC)
    return V48TimedSourceBar(
        opened_at=opened,
        closed_at=opened + timedelta(minutes=1),
        source=CapitalizerSourceBar(
            open=Decimal(open_),
            high=Decimal(high),
            low=Decimal(low),
            close=Decimal(close),
        ),
    )


def test_bullish_cisd_confirms_low_and_protected_swing() -> None:
    bars = (
        _bar(0, "10.0", "10.1", "9.8", "9.9"),
        _bar(1, "9.9", "10.0", "9.5", "9.7"),
        _bar(2, "9.7", "9.8", "9.2", "9.4"),
        _bar(3, "9.4", "9.7", "9.3", "9.6"),
        _bar(4, "9.6", "10.2", "9.5", "10.1"),
    )
    result = observe_first_structural_cisd(
        bars,
        direction=CapitalizerSourceDirection.BULLISH,
        after=bars[0].opened_at,
        before=bars[-1].closed_at,
        higher_timeframe_closure_confirmed=True,
    )
    assert result.structural_confirmed is True
    assert result.source_valid is True
    assert result.swing_price == Decimal("9.2")
    assert result.causal_series_open == Decimal("10.0")
    assert result.confirmation_close == Decimal("10.1")


def test_cisd_without_htf_closure_is_structural_but_not_source_valid() -> None:
    bars = (
        _bar(0, "10.0", "10.1", "9.8", "9.9"),
        _bar(1, "9.9", "10.0", "9.5", "9.7"),
        _bar(2, "9.7", "9.8", "9.2", "9.4"),
        _bar(3, "9.4", "9.7", "9.3", "9.6"),
        _bar(4, "9.6", "10.2", "9.5", "10.1"),
    )
    result = observe_first_structural_cisd(
        bars,
        direction=CapitalizerSourceDirection.BULLISH,
        after=bars[0].opened_at,
        before=bars[-1].closed_at,
        higher_timeframe_closure_confirmed=False,
    )
    assert result.structural_confirmed is True
    assert result.source_valid is False


def test_no_close_through_causal_series_means_no_cisd() -> None:
    bars = (
        _bar(0, "10.0", "10.1", "9.8", "9.9"),
        _bar(1, "9.9", "10.0", "9.5", "9.7"),
        _bar(2, "9.7", "9.8", "9.2", "9.4"),
        _bar(3, "9.4", "9.7", "9.3", "9.6"),
        _bar(4, "9.6", "9.9", "9.5", "9.8"),
    )
    result = observe_first_structural_cisd(
        bars,
        direction=CapitalizerSourceDirection.BULLISH,
        after=bars[0].opened_at,
        before=bars[-1].closed_at,
        higher_timeframe_closure_confirmed=True,
    )
    assert result.structural_confirmed is False
    assert result.source_valid is False


def test_bearish_cisd_confirms_high() -> None:
    bars = (
        _bar(0, "10.0", "10.2", "9.9", "10.1"),
        _bar(1, "10.1", "10.5", "10.0", "10.3"),
        _bar(2, "10.3", "10.8", "10.2", "10.6"),
        _bar(3, "10.6", "10.7", "10.3", "10.4"),
        _bar(4, "10.4", "10.5", "9.8", "9.9"),
    )
    result = observe_first_structural_cisd(
        bars,
        direction=CapitalizerSourceDirection.BEARISH,
        after=bars[0].opened_at,
        before=bars[-1].closed_at,
        higher_timeframe_closure_confirmed=True,
    )
    assert result.source_valid is True
    assert result.swing_price == Decimal("10.8")
    assert result.causal_series_open == Decimal("10.0")
