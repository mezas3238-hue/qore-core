"""Real native H1 geometry must be exact; no C3 branch may trade."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
)
from qore.infrastructure.trader_lab.capitalizer_scalper_a2_c3_native_geometry_census_v1 import (
    NativeH1,
    build_geometry_rows,
    exact_native_h1,
)
from qore.infrastructure.trader_lab.capitalizer_source_observation_detectors_v2 import (
    CapitalizerSourceBar,
)

T0 = datetime(2026, 5, 4, 10, tzinfo=UTC)


def _minute(i: int) -> CapitalizerM1Bar:
    t = T0 + timedelta(minutes=i)
    return CapitalizerM1Bar(
        symbol="EURUSD", opened_at=t, closed_at=t+timedelta(minutes=1),
        open=Decimal("100"), high=Decimal("101"),
        low=Decimal("99"), close=Decimal("100"), volume=1, digits=5,
    )


def _bar(o: str, h: str, low: str, c: str) -> CapitalizerSourceBar:
    return CapitalizerSourceBar(
        open=Decimal(o), high=Decimal(h),
        low=Decimal(low), close=Decimal(c),
    )


def test_exact_native_h1_rejects_any_gap_without_forward_fill() -> None:
    native = tuple(_minute(i) for i in range(180))
    got = exact_native_h1(native)
    assert [x.closed_at for x in got] == [
        T0+timedelta(hours=1),
        T0+timedelta(hours=2),
        T0+timedelta(hours=3),
    ]
    # Removing one M1 from the middle hour removes precisely that H1.
    broken = tuple(x for x in native if x.opened_at != T0+timedelta(minutes=77))
    assert [x.closed_at for x in exact_native_h1(broken)] == [
        T0+timedelta(hours=1),
        T0+timedelta(hours=3),
    ]
    # No synthetic interstitial candle, hence no contiguous H1 triple.
    assert build_geometry_rows(exact_native_h1(broken)) == ()


def test_paired_december_and_january_use_identical_h1_triples() -> None:
    c1 = NativeH1(T0+timedelta(hours=1), _bar("100", "101", "99", "100"))
    c2 = NativeH1(T0+timedelta(hours=2), _bar("100", "103", "97", "98"))
    dec = NativeH1(T0+timedelta(hours=3), _bar("98", "102", "97.5", "100.5"))
    jan = NativeH1(T0+timedelta(hours=3), _bar("98", "105", "97.5", "104"))
    rows_dec = build_geometry_rows((c1, c2, dec))
    rows_jan = build_geometry_rows((c1, c2, jan))
    assert len(rows_dec) == len(rows_jan) == 1
    assert rows_dec[0]["category"] == "DECEMBER_ONLY"
    assert rows_jan[0]["category"] == "JANUARY_ONLY"
    assert all(
        not row["poi_attested"]
        and not row["ltf_cisd_attested"]
        and not row["changes_v49_admission"]
        for row in rows_dec+rows_jan
    )


def test_nonconsecutive_h1_cannot_be_used_for_c3() -> None:
    c1 = NativeH1(T0+timedelta(hours=1), _bar("100", "101", "99", "100"))
    c2 = NativeH1(T0+timedelta(hours=3), _bar("100", "103", "97", "98"))
    c3 = NativeH1(T0+timedelta(hours=4), _bar("98", "102", "97.5", "100.5"))
    assert build_geometry_rows((c1, c2, c3)) == ()
