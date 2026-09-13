from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_b01_r3_8 import (
    Vt08B01Bar,
    evaluate_b01_at_entry,
)

_NY = ZoneInfo("America/New_York")
_MIRROR_AXIS = Decimal("300")


def _bar(
    opened_at: datetime,
    *,
    open_: str = "100",
    high: str = "101",
    low: str = "99",
    close: str = "100",
) -> Vt08B01Bar:
    return Vt08B01Bar(
        opened_at=opened_at.astimezone(UTC),
        closed_at=(opened_at + timedelta(minutes=15)).astimezone(UTC),
        open=Decimal(open_),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
    )


def _long_candidate_history() -> tuple[Vt08B01Bar, ...]:
    start_local = datetime(2026, 1, 5, 17, tzinfo=_NY)
    end_local = datetime(2026, 1, 8, 9, tzinfo=_NY)
    bars: dict[datetime, Vt08B01Bar] = {}
    cursor = start_local
    while cursor < end_local:
        if cursor < datetime(2026, 1, 6, 17, tzinfo=_NY):
            item = _bar(cursor, open_="100", high="102", low="98", close="100")
        elif cursor < datetime(2026, 1, 7, 17, tzinfo=_NY):
            item = _bar(cursor, open_="102", high="104", low="99", close="103")
        else:
            item = _bar(cursor, open_="103", high="105", low="101", close="103")
        bars[item.opened_at] = item
        cursor += timedelta(minutes=15)

    reference_open = datetime(2026, 1, 7, 21, tzinfo=_NY)
    cursor = reference_open
    while cursor < datetime(2026, 1, 8, 1, tzinfo=_NY):
        item = _bar(cursor, open_="103", high="106", low="100", close="104")
        bars[item.opened_at] = item
        cursor += timedelta(minutes=15)

    c2_open = datetime(2026, 1, 8, 1, tzinfo=_NY)
    special = (
        _bar(c2_open, open_="103", high="103.2", low="99", close="101"),
        _bar(
            c2_open + timedelta(minutes=15),
            open_="101",
            high="101.2",
            low="98.5",
            close="100",
        ),
        _bar(
            c2_open + timedelta(minutes=30),
            open_="100",
            high="104",
            low="99.8",
            close="103.5",
        ),
    )
    for item in special:
        bars[item.opened_at] = item
    cursor = c2_open + timedelta(minutes=45)
    while cursor < datetime(2026, 1, 8, 5, tzinfo=_NY):
        item = _bar(cursor, open_="103.5", high="105", low="102", close="103.5")
        bars[item.opened_at] = item
        cursor += timedelta(minutes=15)

    entry_open = datetime(2026, 1, 8, 5, tzinfo=_NY)
    entry = _bar(entry_open, open_="104", high="105", low="103", close="104")
    bars[entry.opened_at] = entry
    return tuple(bars[key] for key in sorted(bars))


def _mirror(bar: Vt08B01Bar) -> Vt08B01Bar:
    return Vt08B01Bar(
        opened_at=bar.opened_at,
        closed_at=bar.closed_at,
        open=_MIRROR_AXIS - bar.open,
        high=_MIRROR_AXIS - bar.low,
        low=_MIRROR_AXIS - bar.high,
        close=_MIRROR_AXIS - bar.close,
    )


def test_b01_long_short_full_pipeline_is_price_mirror_symmetric() -> None:
    decision_at = datetime(2026, 1, 8, 5, tzinfo=_NY)
    long_result = evaluate_b01_at_entry(
        symbol="EURUSD",
        m15_bars=_long_candidate_history(),
        decision_at=decision_at,
    )
    mirrored_history = tuple(_mirror(bar) for bar in _long_candidate_history())
    short_result = evaluate_b01_at_entry(
        symbol="EURUSD",
        m15_bars=mirrored_history,
        decision_at=decision_at,
    )

    assert long_result.abstain_reason is None
    assert short_result.abstain_reason is None
    assert long_result.candidate is not None
    assert short_result.candidate is not None

    long = long_result.candidate
    short = short_result.candidate
    assert long.side is DemoTradingSetupSide.LONG
    assert short.side is DemoTradingSetupSide.SHORT

    assert short.setup.entry_price == _MIRROR_AXIS - long.setup.entry_price
    assert short.setup.invalidation_price == _MIRROR_AXIS - long.setup.invalidation_price
    assert short.setup.take_profit_price == _MIRROR_AXIS - long.setup.take_profit_price
    assert short.protected_swing.price == _MIRROR_AXIS - long.protected_swing.price
    assert short.protected_swing.cisd_level == _MIRROR_AXIS - long.protected_swing.cisd_level
    assert short.protected_swing.confirmed_at == long.protected_swing.confirmed_at
    assert (
        short.protected_swing.opposing_series_opened_at
        == long.protected_swing.opposing_series_opened_at
    )

    long_risk = long.setup.entry_price - long.setup.invalidation_price
    short_risk = short.setup.invalidation_price - short.setup.entry_price
    assert long_risk == short_risk
    assert long.setup.take_profit_price - long.setup.entry_price == Decimal(2) * long_risk
    assert short.setup.entry_price - short.setup.take_profit_price == Decimal(2) * short_risk
    assert short.methodology_fingerprint == long.methodology_fingerprint
