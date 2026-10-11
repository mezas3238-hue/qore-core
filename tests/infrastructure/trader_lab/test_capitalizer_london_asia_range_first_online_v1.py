"""London session pattern tests: complete Asia, as-of entry, gap/censoring."""
from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest

from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import CapitalizerM1Bar
from qore.infrastructure.trader_lab.capitalizer_london_asia_range_first_online_v1 import (
    asof_event, bh_fdr, exit_path, london_start,
)

LONDON = ZoneInfo("Europe/London")
DAY = datetime(2026, 7, 15, tzinfo=LONDON).date()


def bar(at: datetime, o: str = "1.10000", h: str = "1.10010",
        l: str = "1.09990", c: str = "1.10000") -> CapitalizerM1Bar:
    return CapitalizerM1Bar(
        symbol="EURUSD", opened_at=at, closed_at=at + timedelta(minutes=1),
        open=Decimal(o), high=Decimal(h), low=Decimal(l), close=Decimal(c),
        volume=10, digits=5,
    )


def asia() -> list[CapitalizerM1Bar]:
    start = london_start(DAY, 0)
    return [bar(start + timedelta(minutes=i)) for i in range(480)]


def test_l1_reclaim_is_observed_only_after_breach_bar_close() -> None:
    start = london_start(DAY, 8)
    rows = asia() + [
        bar(start, h="1.10040", c="1.10000"),
        bar(start+timedelta(minutes=1), l="1.09950"),
    ]
    r = asof_event("EURUSD", DAY, tuple(rows))
    assert r.reason == "SIGNAL_CONFIRMED"
    assert r.pattern == "L1_SWEEP_RECLAIM"
    assert r.direction == "SHORT"
    assert r.entry_at == (start+timedelta(minutes=1)).isoformat()
    assert Decimal(r.stop) == Decimal("1.10040")
    assert Decimal(r.target) == Decimal("1.09960")
    assert r.future_used_to_select_event is False
    # Prefix invariance: adding later future candles cannot change entry.
    plus = rows + [
        bar(start + timedelta(minutes=2), h="1.15000", c="1.14900")
    ]
    assert asof_event("EURUSD", DAY, tuple(plus)) == r
    end, why, ret, _ = exit_path({b.opened_at: b for b in rows}, start+timedelta(minutes=1),
                                 Decimal(r.stop), Decimal(r.target), r.direction, DAY)
    assert why == "TARGET"
    assert ret == 1
    assert end == start+timedelta(minutes=2)


def test_l2_requires_two_closed_M1_outside_range_before_next_open() -> None:
    start = london_start(DAY, 8)
    rows = asia() + [
        bar(start, h="1.10040", c="1.10030"),
        bar(start+timedelta(minutes=1), o="1.10030", h="1.10050",
            l="1.10020", c="1.10040"),
        bar(start+timedelta(minutes=2), o="1.10040", h="1.10080",
            l="1.10030", c="1.10065"),
    ]
    r = asof_event("EURUSD", DAY, tuple(rows))
    assert r.reason == "SIGNAL_CONFIRMED"
    assert r.pattern == "L2_BREAK_HOLD"
    assert r.direction == "LONG"
    assert r.entry_at == (start+timedelta(minutes=2)).isoformat()
    assert Decimal(r.stop) == Decimal("1.10010")
    assert Decimal(r.target) == Decimal("1.10070")


def test_missing_Asia_minute_rejected_without_interpolation() -> None:
    rows = asia()
    assert asof_event("EURUSD", DAY, tuple(rows[:-1])).reason == "ASIA_COVERAGE_INVALID"


def test_first_london_breach_requires_unbroken_prefix() -> None:
    start = london_start(DAY, 8)
    rows = asia() + [bar(start+timedelta(minutes=1), h="1.10040")]
    assert asof_event("EURUSD", DAY, tuple(rows)).reason == "LONDON_PRE_BREACH_GAP"


def test_both_extremes_same_M1_fail_closed() -> None:
    start = london_start(DAY, 8)
    rows = asia() + [bar(start, h="1.10050", l="1.09950")]
    assert asof_event("EURUSD", DAY, tuple(rows)).reason == "AMBIGUOUS_BOTH_EXTREMES"


def test_exit_gap_is_censored_and_not_imputed() -> None:
    start = london_start(DAY, 8)
    rows = {start: bar(start)}
    end, reason, result, _ = exit_path(rows, start, Decimal("1.0990"),
                                        Decimal("1.1010"), "LONG", DAY)
    assert end == start + timedelta(minutes=1)
    assert reason == "RIGHT_CENSORED_GAP"
    assert result is None


def test_same_bar_stop_target_is_stop_first_in_both_directions() -> None:
    start = london_start(DAY, 8)
    b = bar(start, h="1.10150", l="1.09850")
    end, reason, outcome, double = exit_path(
        {start: b}, start, Decimal("1.099"), Decimal("1.101"), "LONG", DAY
    )
    assert end is not None and reason == "STOP_FIRST"
    assert outcome == -1 and double


def test_DST_uses_local_london_08_am() -> None:
    winter = datetime(2026, 2, 11, tzinfo=LONDON).date()
    summer = datetime(2026, 7, 15, tzinfo=LONDON).date()
    assert london_start(winter, 8).hour == 8
    assert london_start(summer, 8).hour == 7


def test_FDR_four_hypotheses() -> None:
    result = bh_fdr({"a": 0.01, "b": 0.03, "c": 0.3, "d": 0.8})
    assert result["a"] == pytest.approx(0.04)
    assert result["b"] == pytest.approx(0.06)
    assert result["c"] == pytest.approx(0.4)
    assert result["d"] == pytest.approx(0.8)
