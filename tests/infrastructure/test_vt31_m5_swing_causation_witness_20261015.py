"""VT31 M5 strict causal-pivot candidates do NOT prove TTrades causative swing."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import (
    M1Bar,
    Side,
)
from scripts.vt31_m5_swing_causation_witness_20261015 import (
    SWING_UNVERIFIED,
    confirmed_qore_pivots_before,
)


def m1(at, *, hi="105", lo="95"):
    return M1Bar(
        at, at+timedelta(minutes=1), Decimal("100"),
        Decimal(hi), Decimal(lo), Decimal("100"),
    )


def source():
    at = datetime(2025, 7, 1, 14, tzinfo=UTC)
    return tuple(
        m1(at+timedelta(minutes=i)) for i in range(12)
    )


def test_pivot_requires_third_right_candle_closed_before_fvg_asof():
    bars = list(source())
    bars[3] = m1(bars[3].opened_at, lo="90")
    src = tuple(bars)
    observed = confirmed_qore_pivots_before(
        src, Side.LONG, source_return_at=src[0].closed_at,
        fvg_confirmed_at=src[7].closed_at,
    )
    assert observed == (src[4].closed_at,)
    # At the pivot itself, the right neighbor is not closed and it must WAIT.
    not_yet = confirmed_qore_pivots_before(
        src, Side.LONG, source_return_at=src[0].closed_at,
        fvg_confirmed_at=src[4].closed_at,
    )
    assert not_yet == ()


def test_multiple_pivots_are_multiple_candidates_not_one_cause():
    bars = list(source())
    bars[2] = m1(bars[2].opened_at, lo="92")
    bars[5] = m1(bars[5].opened_at, lo="90")
    pivots = confirmed_qore_pivots_before(
        tuple(bars), Side.LONG,
        source_return_at=bars[0].closed_at,
        fvg_confirmed_at=bars[10].closed_at,
    )
    assert len(pivots) == 2
    assert pivots[0] < pivots[1]


def test_short_swing_high_is_opposite_semantics():
    bars = list(source())
    bars[3] = m1(bars[3].opened_at, hi="111")
    s = tuple(bars)
    short = confirmed_qore_pivots_before(
        s, Side.SHORT, source_return_at=s[0].closed_at,
        fvg_confirmed_at=s[8].closed_at,
    )
    long = confirmed_qore_pivots_before(
        s, Side.LONG, source_return_at=s[0].closed_at,
        fvg_confirmed_at=s[8].closed_at,
    )
    assert short == (s[4].closed_at,)
    assert long == ()


def test_tied_extremes_do_not_count_as_strict_structural_pivot():
    bars = list(source())
    bars[3] = m1(bars[3].opened_at, lo="95")
    pivots = confirmed_qore_pivots_before(
        tuple(bars), Side.LONG,
        source_return_at=bars[0].closed_at,
        fvg_confirmed_at=bars[8].closed_at,
    )
    assert pivots == ()


def test_gapped_m1_pair_may_not_form_causal_pivot():
    bars = list(source())
    bars[3] = m1(bars[3].opened_at, lo="90")
    # Remove exact adjacent right-neighbor M1, no pivot across missing M1.
    sample = tuple(bars[:4] + bars[5:])
    pivots = confirmed_qore_pivots_before(
        sample, Side.LONG, source_return_at=bars[0].closed_at,
        fvg_confirmed_at=bars[9].closed_at,
    )
    assert pivots == ()


def test_missing_clock_and_future_only_source_rejected():
    bars = source()
    with pytest.raises(ValueError, match="AWARE_ASOF"):
        confirmed_qore_pivots_before(
            bars, Side.LONG,
            source_return_at=datetime(2025, 7, 1, 14),
            fvg_confirmed_at=bars[7].closed_at,
        )
    with pytest.raises(ValueError, match="FVG_CANNOT_PRECEDE"):
        confirmed_qore_pivots_before(
            bars, Side.LONG,
            source_return_at=bars[9].closed_at,
            fvg_confirmed_at=bars[7].closed_at,
        )


def test_contract_never_falsely_equates_pivot_to_author_caused_displacement():
    assert SWING_UNVERIFIED == "AUTHOR_CAUSATIVE_SWING_NOT_ESTABLISHED"
