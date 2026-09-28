from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab.ict_turtle_soup_r4_source_exact import (
    Bar,
    Evidence,
)
from qore.infrastructure.trader_lab.nq_am_temporal_liquidity_reversal_v1 import (
    BearishFvg,
    RthSession,
    Variant,
    _bearish_fvgs,
    _ifvg_entry,
    _simulate,
    build_rth_sessions,
    evaluate_day,
)

D = Decimal


def _at(day: date, hour: int, minute: int) -> datetime:
    from zoneinfo import ZoneInfo

    ny = ZoneInfo("America/New_York")
    return datetime.combine(day, time(hour, minute), tzinfo=ny).astimezone(UTC)


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


def _session(
    day: date,
    *,
    opened: str,
    high: str,
    low: str,
    settle: str,
) -> RthSession:
    return RthSession(
        ny_day=day,
        open_at=_at(day, 9, 30),
        settle_at=_at(day, 16, 14),
        open=D(opened),
        high=D(high),
        low=D(low),
        settle=D(settle),
        bars=(),
    )


def test_build_rth_sessions_uses_0930_and_1614_anchors() -> None:
    day = date(2025, 3, 10)
    bars = (
        _bar(day, 9, 30, "100", "101", "99", "100.5"),
        _bar(day, 12, 0, "100.5", "105", "98", "104"),
        _bar(day, 16, 14, "104", "106", "103", "105"),
    )
    sessions = build_rth_sessions(bars)
    assert len(sessions) == 1
    session = sessions[0]
    assert session.open == D("100")
    assert session.settle == D("105")
    assert session.high == D("106")
    assert session.low == D("98")


def test_bearish_fvg_and_inversion_entry_are_causal() -> None:
    day = date(2025, 1, 8)
    bars = (
        _bar(day, 10, 47, "90", "91", "89", "90"),
        _bar(day, 10, 48, "89", "90", "87", "88"),
        _bar(day, 10, 49, "87", "88", "85", "86"),
        _bar(day, 10, 50, "86", "87", "83", "85"),
        _bar(day, 10, 51, "85", "91", "84", "90"),
    )
    zones = _bearish_fvgs(
        bars,
        start=_at(day, 10, 45),
        end=_at(day, 10, 51),
    )
    assert zones
    result = _ifvg_entry(
        bars,
        sweep_at=_at(day, 10, 50),
        deadline=_at(day, 11, 10),
    )
    assert result is not None
    zone, entry_at, entry = result
    assert isinstance(zone, BearishFvg)
    assert entry_at == _at(day, 10, 52)
    assert entry == D("90")


def test_same_bar_stop_target_collision_fails_conservative() -> None:
    day = date(2025, 1, 8)
    bars = (
        _bar(day, 11, 1, "90", "101", "82", "95"),
    )
    exit_at, price, reason, gross, _mfe, _mae = _simulate(
        bars,
        entry_at=_at(day, 11, 1),
        expiry=_at(day, 12, 0),
        entry=D("90"),
        stop=D("83"),
        target=D("100"),
    )
    assert exit_at == _at(day, 11, 2)
    assert price == D("83")
    assert reason == "stop-first-collision"
    assert gross == D("-1")


def _full_case() -> tuple[Evidence, tuple[RthSession, ...]]:
    old_day = date(2025, 1, 6)
    previous_day = date(2025, 1, 7)
    day = date(2025, 1, 8)

    sessions = (
        _session(old_day, opened="92", high="110", low="84", settle="100"),
        _session(previous_day, opened="105", high="112", low="102", settle="108"),
        _session(day, opened="100", high="101", low="83", settle="95"),
    )

    bars: list[Bar] = []
    # 09:30-09:34: gap lower quadrant = 102, lower octant = 101.
    bars.extend(
        [
            _bar(day, 9, 30, "100", "100.5", "99.5", "100.0"),
            _bar(day, 9, 31, "100", "100.6", "99.0", "99.5"),
            _bar(day, 9, 32, "99.5", "100.4", "98.8", "99.2"),
            _bar(day, 9, 33, "99.2", "100.0", "98.5", "99.0"),
            _bar(day, 9, 34, "99.0", "100.2", "98.0", "98.8"),
        ]
    )
    # Down-delivery leg creates a bearish FVG, but has not yet swept 84.
    bars.extend(
        [
            _bar(day, 10, 47, "90", "91", "89", "90"),
            _bar(day, 10, 48, "89", "90", "87", "88"),
            _bar(day, 10, 49, "87", "88", "85", "86"),
        ]
    )
    # First-half macro sweep + rejection. Gap=8 -> 2x extension=84.
    bars.append(_bar(day, 10, 50, "86", "87", "83", "85"))
    # Invert the bearish FVG and enter causally at the close.
    bars.append(_bar(day, 10, 51, "85", "91", "84.5", "90"))
    # Post-entry target touch.
    bars.append(_bar(day, 10, 52, "90", "101", "89", "100"))

    evidence = Evidence(symbol="NAS100", digits=2, bars=tuple(bars))
    return evidence, sessions


def test_full_candidate_produces_one_long_trade_without_low_of_day_oracle() -> None:
    evidence, sessions = _full_case()
    record = evaluate_day(evidence, sessions, 2, variant=Variant.FULL)
    assert record.terminal_stage == "trade"
    assert record.trade is not None
    assert record.reference_day == date(2025, 1, 6)
    assert record.reference_low == D("84")
    assert record.extension_2 == D("84")
    assert record.trade.entry == D("90")
    assert record.trade.stop == D("82.99")
    assert record.trade.target == D("100")
    assert record.trade.exit_reason == "target-0930-open"
    assert record.trade.gross_r > D("1")


def test_full_candidate_rejects_sellside_sweep_before_macro() -> None:
    evidence, sessions = _full_case()
    day = date(2025, 1, 8)
    early_sweep = _bar(day, 10, 49, "86", "87", "83", "85")
    later = tuple(
        bar for bar in evidence.bars if bar.opened_at != _at(day, 10, 49)
    )
    changed = Evidence(
        symbol=evidence.symbol,
        digits=evidence.digits,
        bars=tuple(sorted((*later, early_sweep), key=lambda item: item.opened_at)),
    )
    record = evaluate_day(changed, sessions, 2, variant=Variant.FULL)
    assert record.terminal_stage == "timing"
    assert record.reason == "sellside-swept-before-macro"


def test_future_after_am_expiry_cannot_change_entry_or_result() -> None:
    evidence, sessions = _full_case()
    first = evaluate_day(evidence, sessions, 2, variant=Variant.FULL)
    future = _bar(date(2025, 1, 8), 13, 0, "100", "101", "1", "2")
    extended = Evidence(
        symbol=evidence.symbol,
        digits=evidence.digits,
        bars=tuple((*evidence.bars, future)),
    )
    second = evaluate_day(extended, sessions, 2, variant=Variant.FULL)
    assert first.entry_at == second.entry_at
    assert first.trade == second.trade
