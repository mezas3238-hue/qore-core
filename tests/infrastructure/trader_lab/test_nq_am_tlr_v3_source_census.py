from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from qore.infrastructure.trader_lab.ict_turtle_soup_r4_source_exact import Bar
from qore.infrastructure.trader_lab.nq_am_tlr_v3_source_census import (
    IDENTITY,
    SOURCE_RULE_LEDGER,
    _distance_bin,
    _first_touch,
    _opening_signature,
)

D = Decimal
NY = ZoneInfo("America/New_York")


def _at(day: date, hour: int, minute: int) -> datetime:
    return datetime.combine(day, time(hour, minute), tzinfo=NY).astimezone(UTC)


def _bar(
    day: date,
    hour: int,
    minute: int,
    o: str,
    h: str,
    lo: str,
    c: str,
) -> Bar:
    opened = _at(day, hour, minute)
    return Bar(
        opened_at=opened,
        closed_at=opened + timedelta(minutes=1),
        open=D(o),
        high=D(h),
        low=D(lo),
        close=D(c),
    )


def test_v3_is_source_census_not_trader_identity() -> None:
    assert IDENTITY == "QORE_NQ_AM_TLR_V3_SOURCE_CENSUS_001"
    classes = {item["class"] for item in SOURCE_RULE_LEDGER}
    assert "SOURCE_EXPLICIT" in classes
    assert "QORE_MECHANIZATION" in classes
    assert "PROXY_LIMITATION" in classes


def test_opening_signature_reports_1_2_5_without_selecting_one() -> None:
    day = date(2025, 1, 8)
    bars = (
        _bar(day, 9, 30, "100", "100.5", "99", "99.5"),
        _bar(day, 9, 31, "99.5", "100.8", "98.5", "99"),
        _bar(day, 9, 32, "99", "102.5", "98", "102"),
        _bar(day, 9, 33, "102", "103", "101", "102"),
        _bar(day, 9, 34, "102", "103", "101", "102"),
    )
    assert _opening_signature(
        bars,
        lower_quadrant=D("101"),
        lower_octant=D("100"),
        count=1,
    )
    assert _opening_signature(
        bars,
        lower_quadrant=D("101"),
        lower_octant=D("100"),
        count=2,
    )
    assert not _opening_signature(
        bars,
        lower_quadrant=D("101"),
        lower_octant=D("100"),
        count=5,
    )


def test_first_touch_uses_full_causal_window() -> None:
    day = date(2025, 1, 8)
    bars = (
        _bar(day, 10, 49, "90", "91", "89", "90"),
        _bar(day, 10, 55, "89", "90", "83", "85"),
        _bar(day, 11, 5, "85", "91", "84", "90"),
    )
    touch = _first_touch(
        bars,
        start=_at(day, 10, 50),
        end=_at(day, 11, 10),
        level=D("84"),
    )
    assert touch is not None
    assert touch.opened_at == _at(day, 10, 55)


def test_distance_bins_are_predeclared_descriptive_bins() -> None:
    assert _distance_bin(D("0.10")) == "<=0.125-gap"
    assert _distance_bin(D("0.20")) == "<=0.25-gap"
    assert _distance_bin(D("0.40")) == "<=0.50-gap"
    assert _distance_bin(D("0.80")) == "<=1.00-gap"
    assert _distance_bin(D("1.20")) == ">1.00-gap"
    assert _distance_bin(None) == "unavailable"
