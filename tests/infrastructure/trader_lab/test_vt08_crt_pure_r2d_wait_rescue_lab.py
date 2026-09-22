from datetime import UTC, datetime, timedelta

from qore.infrastructure.trader_lab import vt08_crt_pure_r2d_wait_rescue_lab as r2d
from qore.infrastructure.trader_lab.vt08_crt_pure_r2_model1_reference_lab import M15Bar
from qore.infrastructure.traders.crt_pure_methodology_candidate import (
    CrtPureCandidateDirection,
)


_BASE = datetime(2026, 1, 2, 10, 0, tzinfo=UTC)


def _bars(
    rows: tuple[tuple[int, int, int, int], ...],
) -> tuple[M15Bar, ...]:
    return tuple(
        M15Bar(
            opened_at=_BASE + timedelta(minutes=15 * index),
            open_price=open_price,
            high_price=high,
            low_price=low,
            close_price=close,
        )
        for index, (open_price, high, low, close) in enumerate(rows)
    )


def test_cisd_uses_last_adverse_delivery_leg_open_and_next_bar_fill() -> None:
    bars = _bars(
        (
            (110, 111, 103, 105),
            (105, 106, 98, 100),  # bullish parent source; contiguous down leg starts at 110
            (100, 108, 99, 107),
            (107, 113, 106, 112),  # closes above adverse-leg open 110
            (112, 114, 111, 113),
        )
    )
    signal = r2d._cisd_signal(
        direction=CrtPureCandidateDirection.BULLISH,
        bars=bars,
        source_index=1,
    )
    assert signal is not None
    assert signal.family is r2d.RescueFamily.CISD
    assert signal.confirmation.opened_at == _BASE + timedelta(minutes=45)
    assert signal.entry_bar.opened_at == _BASE + timedelta(minutes=60)
    assert "adverse_leg_open=110" in signal.detail


def test_fvg_detects_first_direction_aligned_gap_after_source() -> None:
    bars = _bars(
        (
            (105, 106, 98, 100),  # source
            (100, 104, 99, 103),
            (103, 108, 102, 107),
            (107, 112, 107, 111),  # low 107 > first high 104 => bullish FVG
            (111, 113, 109, 112),
        )
    )
    signal = r2d._fvg_signal(
        direction=CrtPureCandidateDirection.BULLISH,
        bars=bars,
        source_index=0,
    )
    assert signal is not None
    assert signal.family is r2d.RescueFamily.FVG
    assert signal.confirmation.opened_at == _BASE + timedelta(minutes=45)
    assert signal.entry_bar.opened_at == _BASE + timedelta(minutes=60)


def test_ote_zone_uses_only_prior_closed_impulse_extreme() -> None:
    bars = _bars(
        (
            (105, 106, 98, 100),  # source origin low 98
            (100, 110, 100, 109),  # favorable extreme becomes 110 only after close
            (109, 111, 107, 110),  # prior extreme 110: no OTE touch
            (110, 110, 101, 106),  # prior extreme 111 => OTE zone approx 100.73..102.94
            (106, 108, 104, 107),
        )
    )
    signal = r2d._ote_signal(
        direction=CrtPureCandidateDirection.BULLISH,
        bars=bars,
        source_index=0,
    )
    assert signal is not None
    assert signal.family is r2d.RescueFamily.OTE
    assert signal.confirmation.opened_at == _BASE + timedelta(minutes=45)
    assert signal.entry_bar.opened_at == _BASE + timedelta(minutes=60)


def test_bearish_fvg_is_symmetric() -> None:
    bars = _bars(
        (
            (100, 108, 99, 106),  # source
            (106, 107, 102, 103),
            (103, 104, 96, 97),
            (97, 98, 91, 92),  # high 98 < first low 102 => bearish FVG
            (92, 95, 90, 93),
        )
    )
    signal = r2d._fvg_signal(
        direction=CrtPureCandidateDirection.BEARISH,
        bars=bars,
        source_index=0,
    )
    assert signal is not None
    assert signal.family is r2d.RescueFamily.FVG
    assert signal.entry_bar.opened_at == _BASE + timedelta(minutes=60)
