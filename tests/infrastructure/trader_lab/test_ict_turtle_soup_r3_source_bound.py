from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from qore.infrastructure.trader_lab.ict_turtle_soup_r2_all_session import M5Bar
from qore.infrastructure.trader_lab.ict_turtle_soup_r3_source_bound import (
    Evidence,
    Side,
    replay_symbol,
)

NY = ZoneInfo("America/New_York")
D = Decimal


def _expand_m15(
    start: datetime,
    specs: list[tuple[str, str, str, str]],
) -> list[M5Bar]:
    bars: list[M5Bar] = []
    for m15_index, raw in enumerate(specs):
        o, h, low, c = map(D, raw)
        base = start + timedelta(minutes=15 * m15_index)
        for offset in range(3):
            opened = base + timedelta(minutes=5 * offset)
            bars.append(
                M5Bar(
                    opened_at=opened,
                    closed_at=opened + timedelta(minutes=5),
                    open=o,
                    high=h,
                    low=low,
                    close=c,
                )
            )
    return bars


def _flat_specs(
    o: str, h: str, low: str, c: str
) -> list[tuple[str, str, str, str]]:
    return [(o, h, low, c) for _ in range(16)]


def _long_evidence(
    c2_hour: int = 0,
    *,
    target_high: str = "110",
    both_sides: bool = False,
    no_cisd: bool = False,
) -> Evidence:
    c2_local = datetime(2021, 1, 12, c2_hour, 0, tzinfo=NY)
    first_local = c2_local - timedelta(hours=12)
    specs = [
        _flat_specs("104", "108", "100", "104"),
        _flat_specs("104", "109", "99", "104"),
        _flat_specs("104", target_high, "98", "104"),
    ]
    c2 = _flat_specs("101", "105", "99", "101")
    c2[4] = ("100", "101", "97", "99")
    if no_cisd:
        c2[5] = ("99", "100", "98", "99")
        for idx in range(6, 16):
            c2[idx] = ("99", "100", "98", "99")
    else:
        c2[5] = ("99", "103", "98", "102")
        c2[-1] = ("102", "104", "99", "102")
    if both_sides:
        c2[6] = ("103", "111", "102", "104")
        c2[-1] = ("104", "105", "99", "104")
    specs.append(c2)

    c3 = _flat_specs("102", "109", "100", "106")
    c3[2] = ("103", "111", "102", "108")
    specs.append(c3)

    bars: list[M5Bar] = []
    for index, h4_specs in enumerate(specs):
        start = (first_local + timedelta(hours=4 * index)).astimezone(UTC)
        bars.extend(_expand_m15(start, h4_specs))
    return Evidence(symbol="EURUSD", digits=5, bars=tuple(bars))


def _short_evidence() -> Evidence:
    c2_local = datetime(2021, 1, 12, 8, 0, tzinfo=NY)
    first_local = c2_local - timedelta(hours=12)
    specs = [
        _flat_specs("104", "108", "100", "104"),
        _flat_specs("104", "109", "99", "104"),
        _flat_specs("104", "110", "98", "104"),
    ]
    c2 = _flat_specs("104", "109", "100", "104")
    c2[4] = ("108", "111", "107", "109")
    c2[5] = ("109", "110", "104", "106")
    c2[-1] = ("106", "108", "101", "103")
    specs.append(c2)
    c3 = _flat_specs("103", "106", "99", "101")
    c3[2] = ("102", "103", "97", "99")
    specs.append(c3)
    bars: list[M5Bar] = []
    for index, h4_specs in enumerate(specs):
        start = (first_local + timedelta(hours=4 * index)).astimezone(UTC)
        bars.extend(_expand_m15(start, h4_specs))
    return Evidence(symbol="GBPUSD", digits=5, bars=tuple(bars))


def test_long_source_sequence_uses_protected_swing_without_offset() -> None:
    trades, funnel = replay_symbol(_long_evidence())
    assert funnel["trade"] == 1
    assert len(trades) == 1
    trade = trades[0]
    assert trade.side is Side.LONG
    assert trade.relevant_level == D("98")
    assert trade.cisd_threshold == D("100")
    assert trade.protected_swing == D("97")
    assert trade.stop == D("97")
    assert trade.entry == D("102")
    assert trade.target == D("110")


def test_short_is_exact_mirror() -> None:
    trades, funnel = replay_symbol(_short_evidence())
    assert funnel["trade"] == 1
    assert len(trades) == 1
    trade = trades[0]
    assert trade.side is Side.SHORT
    assert trade.relevant_level == D("110")
    assert trade.cisd_threshold == D("108")
    assert trade.protected_swing == D("111")
    assert trade.stop == D("111")
    assert trade.entry == D("103")
    assert trade.target == D("98")


def test_c2_reversal_without_cisd_abstains() -> None:
    trades, funnel = replay_symbol(_long_evidence(no_cisd=True))
    assert trades == []
    assert funnel["no-cisd"] == 1


def test_both_side_c2_reversal_fails_closed() -> None:
    trades, funnel = replay_symbol(_long_evidence(both_sides=True))
    assert trades == []
    assert funnel["ambiguous-both-sides"] == 1


def test_no_minimum_projected_r_gate() -> None:
    evidence = _long_evidence(target_high="104.5")
    trades, funnel = replay_symbol(evidence)
    assert funnel["trade"] == 1
    assert len(trades) == 1
    assert D("0") < trades[0].projected_r < D("1.5")


def test_clock_does_not_filter_asia_london_or_new_york() -> None:
    # Sweep M15 #4 occurs one hour after C2 starts.
    expected = {
        20: "asia",
        4: "london",
        8: "new-york",
    }
    for c2_hour, session in expected.items():
        trades, funnel = replay_symbol(_long_evidence(c2_hour=c2_hour))
        assert funnel["trade"] == 1
        assert len(trades) == 1
        assert trades[0].session_bucket == session
