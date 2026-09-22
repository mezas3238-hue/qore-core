from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_b01_r3_8 import (
    OPERATIONAL_CONTAINMENTS,
    Vt08B01AbstainReason,
    Vt08B01Bar,
    evaluate_b01_at_entry,
    methodology_fingerprint,
    protected_swings_in_candle2,
    resolve_bias,
    source_h4_from_m15,
)

_NY = ZoneInfo("America/New_York")


def _bar(
    opened_at: datetime,
    *,
    minutes: int = 15,
    open_: str = "100",
    high: str = "101",
    low: str = "99",
    close: str = "100",
) -> Vt08B01Bar:
    return Vt08B01Bar(
        opened_at=opened_at.astimezone(UTC),
        closed_at=(opened_at + timedelta(minutes=minutes)).astimezone(UTC),
        open=Decimal(open_),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
    )


def test_bias_subset_covers_continuation_and_reversal_without_voting() -> None:
    start = datetime(2026, 1, 1, 17, tzinfo=_NY)
    previous = _bar(start, minutes=24 * 60, high="102", low="98", close="100")

    bullish_continuation = _bar(
        start + timedelta(days=1),
        minutes=24 * 60,
        high="104",
        low="99",
        close="103",
    )
    bearish_continuation = _bar(
        start + timedelta(days=1),
        minutes=24 * 60,
        open_="100",
        high="101",
        low="96",
        close="97",
    )
    bullish_reversal = _bar(
        start + timedelta(days=1),
        minutes=24 * 60,
        high="101",
        low="97",
        close="99",
    )
    bearish_reversal = _bar(
        start + timedelta(days=1),
        minutes=24 * 60,
        high="103",
        low="99",
        close="101",
    )
    both_sides_swept = _bar(
        start + timedelta(days=1),
        minutes=24 * 60,
        high="103",
        low="97",
        close="100",
    )

    assert (
        resolve_bias(previous_day=previous, current_day=bullish_continuation)
        is DemoTradingSetupSide.LONG
    )
    assert (
        resolve_bias(previous_day=previous, current_day=bearish_continuation)
        is DemoTradingSetupSide.SHORT
    )
    assert (
        resolve_bias(previous_day=previous, current_day=bullish_reversal)
        is DemoTradingSetupSide.LONG
    )
    assert (
        resolve_bias(previous_day=previous, current_day=bearish_reversal)
        is DemoTradingSetupSide.SHORT
    )
    assert resolve_bias(previous_day=previous, current_day=both_sides_swept) is None


def test_protected_swing_requires_sweep_and_close_through_first_series_open() -> None:
    opened = datetime(2026, 1, 8, 1, tzinfo=_NY)
    bars = (
        _bar(opened, open_="103", high="103.2", low="99", close="101"),
        _bar(
            opened + timedelta(minutes=15),
            open_="101",
            high="101.2",
            low="98.5",
            close="100",
        ),
        _bar(
            opened + timedelta(minutes=30),
            open_="100",
            high="103.7",
            low="99.8",
            close="103.5",
        ),
        _bar(
            opened + timedelta(minutes=45),
            open_="103.5",
            high="104",
            low="103",
            close="103.8",
        ),
    )
    swings = protected_swings_in_candle2(
        bars,
        side=DemoTradingSetupSide.LONG,
        important_level=Decimal("100"),
    )
    assert len(swings) == 1
    assert swings[0].price == Decimal("98.5")
    assert swings[0].cisd_level == Decimal("103")
    assert swings[0].confirmed_at == bars[2].closed_at


def _synthetic_candidate_history() -> tuple[Vt08B01Bar, ...]:
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


def test_b01_candidate_is_causal_and_uses_explicit_containments() -> None:
    bars = _synthetic_candidate_history()
    decision_at = datetime(2026, 1, 8, 5, tzinfo=_NY)
    result = evaluate_b01_at_entry(
        symbol="EURUSD",
        m15_bars=bars,
        decision_at=decision_at,
    )
    assert result.abstain_reason is None
    assert result.candidate is not None
    candidate = result.candidate
    assert candidate.side is DemoTradingSetupSide.LONG
    assert candidate.setup.entry_price == Decimal("104")
    assert candidate.setup.invalidation_price == Decimal("98.5")
    assert candidate.setup.take_profit_price == Decimal("115")
    assert candidate.protected_swing.confirmed_at < candidate.decision_at
    assert candidate.operational_containments == OPERATIONAL_CONTAINMENTS
    assert len(candidate.methodology_fingerprint) == 64


def test_entry_decision_does_not_read_future_body_of_entry_bar() -> None:
    bars = list(_synthetic_candidate_history())
    decision_at = datetime(2026, 1, 8, 5, tzinfo=_NY)
    original = evaluate_b01_at_entry(
        symbol="EURUSD",
        m15_bars=tuple(bars),
        decision_at=decision_at,
    )
    assert original.candidate is not None

    decision_utc = decision_at.astimezone(UTC)
    mutated = []
    for item in bars:
        if item.opened_at == decision_utc:
            mutated.append(
                Vt08B01Bar(
                    opened_at=item.opened_at,
                    closed_at=item.closed_at,
                    open=item.open,
                    high=Decimal("130"),
                    low=Decimal("80"),
                    close=Decimal("120"),
                )
            )
        else:
            mutated.append(item)
    replayed = evaluate_b01_at_entry(
        symbol="EURUSD",
        m15_bars=tuple(mutated),
        decision_at=decision_at,
    )
    assert replayed.candidate is not None
    assert replayed.candidate.setup == original.candidate.setup


def test_multiple_protected_swings_fail_closed() -> None:
    bars = list(_synthetic_candidate_history())
    c2_open = datetime(2026, 1, 8, 1, tzinfo=_NY).astimezone(UTC)
    replacements = {
        c2_open + timedelta(hours=2): _bar(
            datetime(2026, 1, 8, 3, tzinfo=_NY),
            open_="103",
            high="103.2",
            low="99",
            close="101",
        ),
        c2_open + timedelta(hours=2, minutes=15): _bar(
            datetime(2026, 1, 8, 3, 15, tzinfo=_NY),
            open_="101",
            high="104",
            low="98.8",
            close="103.5",
        ),
    }
    bars = [replacements.get(item.opened_at, item) for item in bars]
    result = evaluate_b01_at_entry(
        symbol="EURUSD",
        m15_bars=tuple(bars),
        decision_at=datetime(2026, 1, 8, 5, tzinfo=_NY),
    )
    assert result.candidate is None
    assert result.abstain_reason is Vt08B01AbstainReason.MULTIPLE_PROTECTED_SWINGS


def test_dst_transition_h4_is_not_silently_shortened() -> None:
    transition_open = datetime(2026, 3, 8, 1, tzinfo=_NY)
    assert source_h4_from_m15({}, opened_at_local=transition_open) is None


def test_futures_proxy_is_not_silently_admitted_to_first_r38_replay() -> None:
    result = evaluate_b01_at_entry(
        symbol="NAS100",
        m15_bars=(),
        decision_at=datetime(2026, 1, 8, 6, tzinfo=_NY),
    )
    assert result.candidate is None
    assert result.abstain_reason is Vt08B01AbstainReason.UNSUPPORTED_MARKET


def test_methodology_fingerprint_is_stable() -> None:
    assert methodology_fingerprint() == methodology_fingerprint()
    assert len(methodology_fingerprint()) == 64
