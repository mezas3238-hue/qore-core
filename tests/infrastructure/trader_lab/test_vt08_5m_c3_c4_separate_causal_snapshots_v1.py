"""Independent clocks C3-H4 close vs C4 first-M15 close; no future data."""
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest

from qore.infrastructure.trader_lab.vt08_5m_c3_c4_separate_causal_snapshots_v1 import (
    c3_closed_source_shape,
    c4_first_m15_closed_observation,
)
from qore.infrastructure.traders.vt08_b01_r3_8 import Vt08B01Bar

NY = ZoneInfo("America/New_York")


def candle(t: datetime, o: str, hi: str, low: str, c: str, minutes: int) -> Vt08B01Bar:
    s = t.astimezone(UTC)
    return Vt08B01Bar(
        opened_at=s, closed_at=s + timedelta(minutes=minutes),
        open=Decimal(o), high=Decimal(hi), low=Decimal(low), close=Decimal(c),
    )


def bundle(hour: int = 1):
    t = datetime(2026, 1, 15, hour, tzinfo=NY)
    c1 = candle(t - timedelta(hours=4), "101", "110", "90", "100", 240)
    c2 = candle(t, "100", "105", "95", "98", 240)
    start_c3 = t + timedelta(hours=4)
    # C3 is inside C2 H/L and closes beyond C2 body high (100).
    m15 = tuple(
        candle(
            start_c3 + timedelta(minutes=15 * i),
            "97" if i == 0 else "98",
            "104" if i == 2 else "103",
            "96" if i == 3 else "97",
            "103" if i == 15 else "98",
            15,
        )
        for i in range(16)
    )
    c3 = candle(start_c3, "97", "104", "96", "103", 240)
    return c1, c2, c3, m15


def shape_for(bundle_data=None):
    c1, c2, c3, m15 = bundle_data or bundle()
    return c3_closed_source_shape(
        market="EURJPY", c1=c1, c2=c2, c3=c3,
        c3_m15=m15, observed_at=c3.closed_at,
    )


def test_c3_is_not_available_15m_before_close() -> None:
    c1, c2, c3, m15 = bundle()
    with pytest.raises(ValueError, match="unknowable"):
        c3_closed_source_shape(
            market="EURJPY", c1=c1, c2=c2, c3=c3,
            c3_m15=m15, observed_at=c3.closed_at - timedelta(minutes=15),
        )


def test_c3_snapshot_is_C4_free_and_has_stable_identity() -> None:
    s = shape_for()
    assert s is not None
    o = s.payload()
    assert o["no_c4_ohlc_consumed"] is True
    assert o["poi_source_confirmed"] is False
    assert o["order_authorized"] is False
    assert "c4_first" not in str(o).lower()
    assert o["as_of_stage"] == "C3_CLOSED"
    assert len(o["c3_m15_sha256"]) == 64
    assert len(o["c3_ps_internal_proxies"]) >= 0
    assert all(
        datetime.fromisoformat(ps[1]) <= s.c3_closed_at
        for ps in o["c3_ps_internal_proxies"]
    )


def test_c3_source_identity_does_not_depend_on_future_C4_prices() -> None:
    s = shape_for()
    assert s is not None
    t = s.c3_closed_at
    one = candle(t, "103", "105", "101", "104", 15)
    two = candle(t, "103", "108", "91", "92", 15)
    before = s.payload()
    a = c4_first_m15_closed_observation(s, first_c4_m15=one, observed_at=one.closed_at)
    b = c4_first_m15_closed_observation(s, first_c4_m15=two, observed_at=two.closed_at)
    assert s.payload() == before
    assert a["origin_id"] == b["origin_id"] == before["origin_id"]
    assert a["parent_snapshot_fingerprint"] == b["parent_snapshot_fingerprint"]
    assert a["snapshot_fingerprint"] != b["snapshot_fingerprint"]
    assert a["eq_half_respected_at_closed_m15"] != b["eq_half_respected_at_closed_m15"]


def test_c4_future_bar_cannot_be_consumed_at_open_or_preclose() -> None:
    s = shape_for()
    assert s is not None
    t = s.c3_closed_at
    m15 = candle(t, "103", "105", "101", "104", 15)
    with pytest.raises(ValueError, match="unclosed"):
        c4_first_m15_closed_observation(s, first_c4_m15=m15, observed_at=t)
    with pytest.raises(ValueError, match="unclosed"):
        c4_first_m15_closed_observation(
            s, first_c4_m15=m15, observed_at=t + timedelta(minutes=14),
        )


def test_c4_must_start_at_C3_close_exactly() -> None:
    s = shape_for()
    assert s is not None
    bad = candle(s.c3_closed_at + timedelta(minutes=15), "103", "105", "101", "104", 15)
    with pytest.raises(ValueError, match="first contiguous"):
        c4_first_m15_closed_observation(s, first_c4_m15=bad, observed_at=bad.closed_at)


def test_c3_raw_m15_injection_and_ohlc_tamper_fail_closed() -> None:
    c1, c2, c3, bars = bundle()
    bad = replace(bars[0], high=Decimal("111"))
    with pytest.raises(ValueError, match="not authenticated"):
        c3_closed_source_shape(
            market="EURJPY", c1=c1, c2=c2, c3=c3,
            c3_m15=(bad,) + bars[1:], observed_at=c3.closed_at,
        )
    future = replace(bars[15], opened_at=c3.closed_at, closed_at=c3.closed_at+timedelta(minutes=15))
    with pytest.raises(ValueError, match="future, missing or overlapping"):
        c3_closed_source_shape(
            market="EURJPY", c1=c1, c2=c2, c3=c3,
            c3_m15=bars[:15] + (future,), observed_at=c3.closed_at,
        )


def test_c3_already_completed_C2_reversal_partition_excludes_shape() -> None:
    c1, c2, c3, bars = bundle()
    # C2 sweeps C1 high 110 but closes inside C1 -> completed C2 closure.
    c1 = replace(c1, high=Decimal("104"))
    assert shape_for((c1, c2, c3, bars)) is None


@pytest.mark.parametrize(("month", "expected_utc_hour"), [(1, 14), (7, 13)])
def test_owner_09ny_c4_after_05ny_c3_both_dst(month: int, expected_utc_hour: int) -> None:
    c1, c2, c3, bars = bundle()
    dt = datetime(2026, month, 15, 1, tzinfo=NY).astimezone(UTC)
    offset = dt - c2.opened_at
    moved = (
        replace(c1, opened_at=c1.opened_at+offset, closed_at=c1.closed_at+offset),
        replace(c2, opened_at=c2.opened_at+offset, closed_at=c2.closed_at+offset),
        replace(c3, opened_at=c3.opened_at+offset, closed_at=c3.closed_at+offset),
        tuple(replace(x, opened_at=x.opened_at+offset, closed_at=x.closed_at+offset) for x in bars),
    )
    s = shape_for(moved)
    assert s is not None
    assert s.next_c4_owner_permitted is True
    assert s.c3_closed_at.astimezone(UTC).hour == expected_utc_hour


def test_13ny_c4_remains_owner_forbidden_without_ignoring_shape() -> None:
    s = shape_for(bundle(hour=5))
    assert s is not None
    assert s.c3_closed_at.astimezone(NY).hour == 13
    assert s.next_c4_owner_permitted is False


def test_source_event_rejects_other_market() -> None:
    c1, c2, c3, bars = bundle()
    with pytest.raises(ValueError, match="research scope"):
        c3_closed_source_shape(
            market="NAS100", c1=c1, c2=c2, c3=c3,
            c3_m15=bars, observed_at=c3.closed_at,
        )
