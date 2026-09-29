from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from qore.infrastructure.trader_lab.ict_turtle_soup_r4_source_exact import Bar, Evidence
from qore.infrastructure.trader_lab.nq_am_temporal_liquidity_reversal_v1 import (
    RthSession,
    Variant,
)
from qore.infrastructure.trader_lab.nq_am_temporal_liquidity_reversal_v2 import (
    EthDailySession,
    _eth_bounds,
    _untouched_daily_reference,
    build_eth_daily_sessions,
    evaluate_day,
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


def _rth(
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


def _eth(
    day: date,
    *,
    high: str,
    low: str,
    close: str,
) -> EthDailySession:
    opened_at, closed_at = _eth_bounds(day)
    return EthDailySession(
        trade_day=day,
        opened_at=opened_at,
        closed_at=closed_at,
        high=D(high),
        low=D(low),
        close=D(close),
        bars=(),
    )


def test_eth_bounds_are_previous_1800_to_trade_date_1700_dst_aware() -> None:
    day = date(2025, 3, 10)
    opened, closed = _eth_bounds(day)
    assert opened.astimezone(NY).date() == date(2025, 3, 9)
    assert opened.astimezone(NY).time() == time(18, 0)
    assert closed.astimezone(NY).date() == day
    assert closed.astimezone(NY).time() == time(17, 0)


def test_build_eth_daily_session_includes_overnight_and_excludes_1700() -> None:
    trade_day = date(2025, 3, 10)
    prior_day = trade_day - timedelta(days=1)
    bars = (
        _bar(prior_day, 18, 0, "100", "101", "99", "100"),
        _bar(trade_day, 9, 30, "100", "110", "95", "105"),
        _bar(trade_day, 16, 59, "105", "108", "104", "107"),
        _bar(trade_day, 17, 0, "107", "999", "1", "2"),
    )
    sessions = build_eth_daily_sessions(bars, [trade_day])
    assert len(sessions) == 1
    session = sessions[0]
    assert session.high == D("110")
    assert session.low == D("95")
    assert session.close == D("107")
    assert len(session.bars) == 3


def test_daily_reference_ranks_2sd_confluence_not_nearest_price() -> None:
    current_day = date(2025, 1, 8)
    sessions = (
        _eth(date(2025, 1, 6), high="110", low="84", close="100"),
        _eth(date(2025, 1, 7), high="112", low="92", close="108"),
    )
    selected = _untouched_daily_reference(
        sessions,
        current_day=current_day,
        current_open_at=_at(current_day, 9, 30),
        current_open=D("100"),
        all_bars=(),
        extension_2=D("84"),
        gap=D("8"),
        variant=Variant.FULL,
    )
    assert selected is not None
    session, low = selected
    assert session.trade_day == date(2025, 1, 6)
    assert low == D("84")


def test_daily_reference_rejects_level_revisited_after_daily_close() -> None:
    current_day = date(2025, 1, 8)
    candidate = _eth(date(2025, 1, 6), high="110", low="84", close="100")
    revisit = _bar(date(2025, 1, 7), 9, 45, "90", "91", "83", "85")
    selected = _untouched_daily_reference(
        (candidate,),
        current_day=current_day,
        current_open_at=_at(current_day, 9, 30),
        current_open=D("100"),
        all_bars=(revisit,),
        extension_2=D("84"),
        gap=D("8"),
        variant=Variant.FULL,
    )
    assert selected is None


def _full_case() -> tuple[Evidence, tuple[RthSession, ...], tuple[EthDailySession, ...]]:
    older = date(2025, 1, 6)
    previous = date(2025, 1, 7)
    day = date(2025, 1, 8)

    rth = (
        _rth(older, opened="92", high="110", low="84", settle="100"),
        _rth(previous, opened="105", high="112", low="90", settle="108"),
        _rth(day, opened="100", high="101", low="83", settle="95"),
    )
    eth = (
        _eth(older, high="110", low="84", close="100"),
        _eth(previous, high="112", low="90", close="108"),
        _eth(day, high="101", low="83", close="95"),
    )

    bars: list[Bar] = [
        _bar(day, 9, 30, "100", "100.5", "99.5", "100.0"),
        _bar(day, 9, 31, "100", "100.6", "99.0", "99.5"),
        _bar(day, 9, 32, "99.5", "100.4", "98.8", "99.2"),
        _bar(day, 9, 33, "99.2", "100.0", "98.5", "99.0"),
        _bar(day, 9, 34, "99.0", "100.2", "98.0", "98.8"),
        _bar(day, 10, 47, "90", "91", "89", "90"),
        _bar(day, 10, 48, "89", "90", "87", "88"),
        _bar(day, 10, 49, "87", "88", "85", "86"),
        _bar(day, 10, 50, "86", "87", "83", "85"),
        _bar(day, 10, 51, "85", "91", "84.5", "90"),
        _bar(day, 10, 52, "90", "101", "89", "100"),
    ]
    return Evidence(symbol="NAS100", digits=2, bars=tuple(bars)), rth, eth


def test_full_v2_uses_prior_eth_daily_low_and_produces_causal_long() -> None:
    evidence, rth, eth = _full_case()
    record = evaluate_day(evidence, rth, eth, 2, variant=Variant.FULL)
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


def test_full_v2_does_not_use_post_expiry_future_for_decision_or_result() -> None:
    evidence, rth, eth = _full_case()
    first = evaluate_day(evidence, rth, eth, 2, variant=Variant.FULL)
    future = _bar(date(2025, 1, 8), 13, 0, "100", "101", "1", "2")
    changed = Evidence(
        symbol=evidence.symbol,
        digits=evidence.digits,
        bars=tuple((*evidence.bars, future)),
    )
    second = evaluate_day(changed, rth, eth, 2, variant=Variant.FULL)
    assert first.entry_at == second.entry_at
    assert first.trade == second.trade
