"""TTrades source June 29: CISD first opposing candle OPEN, not QORE last."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import (
    M1Bar,
    Side,
)
from scripts.vt31_m3_cisd_first_series_source_witness_20261015 import (
    canonical_hash,
    first_series_cisd,
)


def candle(at, o="100", h="110", low="90", c="100"):
    return M1Bar(
        at,at+timedelta(minutes=1),
        Decimal(o),Decimal(h),Decimal(low),Decimal(c),
    )


def time():
    return datetime(2025,7,1,14,tzinfo=UTC)


def witness(bars, side=Side.LONG, sweep_at=None):
    return first_series_cisd(
        bars,side=side,
        first_sweep_at=sweep_at or bars[0].closed_at,
        as_of=bars[-1].closed_at,
    )


def test_bullish_legacy_last_open_cross_only_is_not_author_cisd():
    t=time()
    a=candle(t,o="105",c="103")
    b=candle(t+timedelta(minutes=1),o="103",c="102")
    c=candle(t+timedelta(minutes=2),o="102",c="104")
    w=witness((a,b,c))
    assert w is not None and w.opposing_series_length==2
    assert w.last_candle_open_crossed is True
    assert w.first_candle_open_crossed is False
    assert w.author_component_not_full_ob_or_mss is True


def test_bullish_2_down_candles_cross_initial_first_open_is_confirmed():
    t=time()
    a=candle(t,o="105",c="103")
    b=candle(t+timedelta(minutes=1),o="103",c="102")
    c=candle(t+timedelta(minutes=2),o="102",c="106")
    w=witness((a,b,c))
    assert w is not None and w.first_candle_open_crossed
    assert w.last_candle_open_crossed
    assert w.confirmed_at==c.closed_at


def test_bearish_first_open_vs_last_open_is_symmetric():
    t=time()
    a=candle(t,o="95",c="97")
    b=candle(t+timedelta(minutes=1),o="97",c="99")
    c=candle(t+timedelta(minutes=2),o="99",c="96")
    w=witness((a,b,c),side=Side.SHORT)
    assert w is not None and not w.first_candle_open_crossed
    assert w.last_candle_open_crossed
    fully=candle(t+timedelta(minutes=2),o="99",c="94")
    e=witness((a,b,fully),side=Side.SHORT)
    assert e is not None and e.first_candle_open_crossed


def test_single_opposing_candle_reference_first_equals_last():
    t=time()
    a=candle(t,o="104",c="100")
    b=candle(t+timedelta(minutes=1),o="100",c="105")
    w=witness((a,b))
    assert w is not None and w.opposing_series_length==1
    assert w.first_candle_open_crossed==w.last_candle_open_crossed==True


def test_equal_close_to_first_open_is_not_accepted():
    t=time()
    a=candle(t,o="105",c="103")
    b=candle(t+timedelta(minutes=1),o="103",c="102")
    c=candle(t+timedelta(minutes=2),o="102",c="105")
    w=witness((a,b,c))
    assert w is not None and not w.first_candle_open_crossed


def test_doji_is_not_a_directional_opposing_bar_or_confirmation():
    t=time()
    doji=candle(t,o="101",c="101")
    up=candle(t+timedelta(minutes=1),o="101",c="104")
    assert witness((doji,up)) is None
    down=candle(t,o="104",c="101")
    flat=candle(t+timedelta(minutes=1),o="101",c="101")
    assert witness((down,flat)) is None


def test_missing_minute_and_overlap_both_fail_closed():
    t=time()
    a=candle(t,o="104",c="101")
    c=candle(t+timedelta(minutes=2),o="101",c="105")
    with pytest.raises(ValueError,match="MISSING_M1"):
        witness((a,c))
    overlap=candle(t+timedelta(seconds=30),o="101",c="105")
    with pytest.raises(ValueError,match="MISSING_M1"):
        witness((a,overlap))


def test_future_or_naive_clock_is_not_eligible():
    t=time()
    a=candle(t,o="104",c="101")
    b=candle(t+timedelta(minutes=1),o="101",c="105")
    with pytest.raises(ValueError,match="CLOSED_M1_ASOF"):
        first_series_cisd(
            (a,b),side=Side.LONG,first_sweep_at=a.closed_at,
            as_of=b.opened_at,
        )
    with pytest.raises(ValueError,match="AWARE_CLOCK"):
        first_series_cisd(
            (a,b),side=Side.LONG,
            first_sweep_at=datetime(2025,7,1,14),
            as_of=b.closed_at,
        )


def test_sweep_later_than_opposing_series_is_not_a_qualifier():
    t=time()
    a=candle(t,o="104",c="101")
    b=candle(t+timedelta(minutes=1),o="101",c="105")
    assert witness((a,b),sweep_at=b.closed_at) is None


def test_nonconsecutive_opposing_series_cannot_use_earlier_first_open():
    t=time()
    a=candle(t,o="106",c="104")
    b=candle(t+timedelta(minutes=1),o="104",c="105")
    c=candle(t+timedelta(minutes=2),o="105",c="103")
    d=candle(t+timedelta(minutes=3),o="103",c="106")
    w=witness((a,b,c,d))
    assert w is not None
    assert w.opposing_series_length==1
    assert w.first_candle_open_crossed


def test_canonical_full_case_digest_changes_one_cognitive_timestamp():
    left=[{"day":"2025-07-01","state":"WAIT","as_of":"2025-07-01T14:03:00Z"}]
    right=[{"day":"2025-07-01","state":"WAIT","as_of":"2025-07-01T14:04:00Z"}]
    assert canonical_hash(left)!=canonical_hash(right)
