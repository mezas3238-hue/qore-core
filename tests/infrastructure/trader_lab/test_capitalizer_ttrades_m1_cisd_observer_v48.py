from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
)
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_ttrades_m1_cisd_observer_v48 import (
    V48M1CISDStatus,
    observe_first_m1_cisd,
)


def _bar(index: int, open_: str, high: str, low: str, close: str) -> CapitalizerM1Bar:
    opened = datetime(2026, 1, 2, 12, 0, tzinfo=UTC) + timedelta(minutes=index)
    return CapitalizerM1Bar(
        symbol="EURUSD",
        opened_at=opened,
        closed_at=opened + timedelta(minutes=1),
        open=Decimal(open_),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
        volume=100,
        digits=5,
    )


def test_bullish_local_sweep_then_cisd_confirms_without_fvg_ob_or_ict_mss() -> None:
    bars = (
        _bar(0, "1.1000", "1.1010", "1.0995", "1.1005"),
        _bar(1, "1.1005", "1.1008", "1.0990", "1.0995"),  # pivot low
        _bar(2, "1.0995", "1.1002", "1.0993", "1.1000"),
        _bar(3, "1.1000", "1.1001", "1.0985", "1.0990"),  # sweeps pivot, down close
        _bar(4, "1.0990", "1.0994", "1.0988", "1.0991"),
        _bar(5, "1.0991", "1.1006", "1.0990", "1.1004"),  # closes through 1.1000
    )
    result = observe_first_m1_cisd(
        bars,
        thesis_at=bars[0].opened_at,
        deadline_at=bars[-1].closed_at,
        side=CapitalizerSide.LONG,
    )

    assert result.status is V48M1CISDStatus.CONFIRMED
    assert result.confirmed is True
    assert result.swept_level == Decimal("1.0990")
    assert result.causal_series_open == Decimal("1.1000")
    assert result.confirmation_close == Decimal("1.1004")
    assert result.fvg_required is False
    assert result.ict_mss_required is False
    assert result.order_block_required_for_cisd is False
    assert result.outcome_used is False
    assert result.target_used is False
    assert result.stop_used is False


def test_no_local_sweep_does_not_invent_cisd() -> None:
    bars = (
        _bar(0, "1.1000", "1.1010", "1.0995", "1.1005"),
        _bar(1, "1.1005", "1.1008", "1.0990", "1.0995"),
        _bar(2, "1.0995", "1.1002", "1.0993", "1.1000"),
        _bar(3, "1.1000", "1.1010", "1.0994", "1.1006"),
    )
    result = observe_first_m1_cisd(
        bars,
        thesis_at=bars[0].opened_at,
        deadline_at=bars[-1].closed_at,
        side=CapitalizerSide.LONG,
    )
    assert result.status is V48M1CISDStatus.NO_LOCAL_LIQUIDITY_SWEEP
    assert result.confirmed is False


def test_observer_requires_chronological_input() -> None:
    bars = (
        _bar(1, "1.1005", "1.1008", "1.0990", "1.0995"),
        _bar(0, "1.1000", "1.1010", "1.0995", "1.1005"),
        _bar(2, "1.0995", "1.1002", "1.0993", "1.1000"),
        _bar(3, "1.1000", "1.1001", "1.0985", "1.0990"),
    )
    try:
        observe_first_m1_cisd(
            bars,
            thesis_at=bars[1].opened_at,
            deadline_at=bars[-1].closed_at,
            side=CapitalizerSide.LONG,
        )
    except ValueError as exc:
        assert "chronological" in str(exc)
    else:
        raise AssertionError("non-chronological M1 must fail closed")


def test_sweep_bullish_requires_close_through_opposing_series_not_high_wick() -> None:
    """A wick through series open is NOT a confirmed CISD; the CLOSE is required."""
    bars = (
        _bar(0, "1.1000", "1.1010", "1.0995", "1.1005"),
        _bar(1, "1.1005", "1.1008", "1.0990", "1.0995"),
        _bar(2, "1.0995", "1.1002", "1.0993", "1.1000"),
        _bar(3, "1.1000", "1.1001", "1.0985", "1.0990"),
        _bar(4, "1.0990", "1.0994", "1.0988", "1.0991"),
        _bar(5, "1.0991", "1.1006", "1.0990", "1.0999"),
        _bar(6, "1.0999", "1.1004", "1.0997", "1.1001"),
    )
    denied = observe_first_m1_cisd(
        bars[:-1],
        thesis_at=bars[0].opened_at,
        deadline_at=bars[5].closed_at,
        side=CapitalizerSide.LONG,
    )
    assert denied.status is V48M1CISDStatus.NO_CISD_CLOSE
    confirmed = observe_first_m1_cisd(
        bars,
        thesis_at=bars[0].opened_at,
        deadline_at=bars[6].closed_at,
        side=CapitalizerSide.LONG,
    )
    assert confirmed.status is V48M1CISDStatus.CONFIRMED
    assert confirmed.causal_series_open == Decimal("1.1000")
    assert confirmed.confirmed_at == bars[6].closed_at
    assert confirmed.confirmation_close == Decimal("1.1001")


def test_sweep_bearish_requires_opposing_up_candle_series_close() -> None:
    """The bearish CLOSE crosses prior bullish series, not the swept high."""
    bars = (
        _bar(0, "1.1000", "1.1010", "1.0990", "1.1005"),
        _bar(1, "1.1005", "1.1020", "1.1000", "1.1010"),
        _bar(2, "1.1010", "1.1015", "1.1002", "1.1008"),
        _bar(3, "1.1008", "1.1025", "1.1007", "1.1020"),
        _bar(4, "1.1020", "1.1024", "1.1012", "1.1015"),
        _bar(5, "1.1015", "1.1017", "1.1000", "1.1006"),
    )
    not_yet = observe_first_m1_cisd(
        bars[:-1],
        thesis_at=bars[0].opened_at,
        deadline_at=bars[4].closed_at,
        side=CapitalizerSide.SHORT,
    )
    assert not_yet.status is V48M1CISDStatus.NO_CISD_CLOSE
    accepted = observe_first_m1_cisd(
        bars,
        thesis_at=bars[0].opened_at,
        deadline_at=bars[5].closed_at,
        side=CapitalizerSide.SHORT,
    )
    assert accepted.status is V48M1CISDStatus.CONFIRMED
    assert accepted.swept_level == Decimal("1.1020")
    assert accepted.causal_series_open == Decimal("1.1008")
    assert accepted.confirmed_at == bars[5].closed_at
