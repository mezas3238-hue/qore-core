"""Offline, causal SMT research for three US equity-index CFD feeds.

Research only: no alerts, position sizing, orders, account access or LIVE authority.
The rolling prior-high/low rule is a QORE engineering hypothesis, not an
author-certified ICT/SMT rule. All candles are completed M15 bars in UTC.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from decimal import Decimal
from typing import Literal
from zoneinfo import ZoneInfo

Symbol = Literal["SPX500", "NDX100", "US30"]
Side = Literal["BULLISH", "BEARISH"]
Route = Literal["CRT_SMT_MSS", "SMT_MSS_NO_CRT"]

SYMBOLS: tuple[Symbol, ...] = ("SPX500", "NDX100", "US30")
PAIRS: tuple[tuple[Symbol, Symbol], ...] = (
    ("SPX500", "NDX100"),
    ("SPX500", "US30"),
    ("NDX100", "US30"),
)
NY = ZoneInfo("America/New_York")
BAR = timedelta(minutes=15)
WINDOW_START = time(9, 30)
WINDOW_END = time(11, 30)


def _utc(value: datetime) -> bool:
    return value.tzinfo is not None and value.utcoffset() == timedelta(0)


@dataclass(frozen=True, slots=True)
class Candle:
    symbol: Symbol
    feed_id: str
    closed_at: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal

    def __post_init__(self) -> None:
        if self.symbol not in SYMBOLS or not self.feed_id.strip():
            raise ValueError("unsupported symbol or missing feed provenance")
        if not _utc(self.closed_at):
            raise ValueError("timestamps must be UTC-aware")
        if self.closed_at.second or self.closed_at.microsecond or self.closed_at.minute % 15:
            raise ValueError("only completed, aligned M15 bar end timestamps are supported")
        prices = (self.open, self.high, self.low, self.close)
        if any(not isinstance(p, Decimal) or not p.is_finite() or p <= 0 for p in prices):
            raise ValueError("prices must be positive finite Decimals")
        if self.low > min(self.open, self.close) or self.high < max(self.open, self.close):
            raise ValueError("OHLC is inconsistent")
        if self.low > self.high:
            raise ValueError("low > high")


@dataclass(frozen=True, slots=True)
class SMT:
    pair: tuple[Symbol, Symbol]
    direction: Side
    sweeping_symbol: Symbol
    observed_at: datetime
    reference: Decimal
    swept_extreme: Decimal

    def __post_init__(self) -> None:
        if self.pair not in PAIRS or self.sweeping_symbol not in self.pair:
            raise ValueError("invalid SMT pairing")


@dataclass(frozen=True, slots=True)
class MSS:
    symbol: Symbol
    direction: Side
    confirmed_at: datetime
    protected_swing: Decimal
    confirming_close: Decimal

    def valid(self) -> bool:
        if self.symbol not in SYMBOLS or not _utc(self.confirmed_at):
            return False
        if (not self.protected_swing.is_finite() or
                not self.confirming_close.is_finite()):
            return False
        if self.protected_swing <= 0 or self.confirming_close <= 0:
            return False
        return (
            self.confirming_close > self.protected_swing
            if self.direction == "BULLISH"
            else self.confirming_close < self.protected_swing
            if self.direction == "BEARISH"
            else False
        )


@dataclass(frozen=True, slots=True)
class CRT:
    symbol: Symbol
    direction: Side
    confirmed_at: datetime
    family: str
    valid: bool

    def usable(self, observed_at: datetime) -> bool:
        return (
            self.valid
            and self.symbol in SYMBOLS
            and self.direction in ("BULLISH", "BEARISH")
            and bool(self.family.strip())
            and _utc(self.confirmed_at)
            and self.confirmed_at <= observed_at
        )


@dataclass(frozen=True, slots=True)
class ResearchOpportunity:
    instrument: Symbol
    route: Route
    direction: Side
    smt: SMT
    mss_confirmed_at: datetime
    crt_family: str | None
    evaluated_at: datetime
    status: Literal["RESEARCH_ONLY"] = "RESEARCH_ONLY"


def _validate_bars(
    bars: Mapping[Symbol, Sequence[Candle]], lookback: int
) -> datetime:
    if not isinstance(lookback, int) or isinstance(lookback, bool) or lookback < 3:
        raise ValueError("lookback must be an integer >= 3")
    if set(bars) != set(SYMBOLS):
        raise ValueError("exactly three supported instruments are required")
    if any(len(bars[s]) < lookback + 1 for s in SYMBOLS):
        raise ValueError("insufficient closed-bar history")
    snapshots = [bars[s][-lookback - 1:] for s in SYMBOLS]
    common_times = tuple(c.closed_at for c in snapshots[0])
    if any((b.closed_at - a.closed_at) != BAR for a, b in zip(
        snapshots[0], snapshots[0][1:], strict=False
    )):
        raise ValueError("missing M15 bars; no synthetic bars permitted")
    feeds: set[str] = set()
    for symbol, seq in zip(SYMBOLS, snapshots, strict=True):
        feeds.update(c.feed_id for c in seq)
        if any(c.symbol != symbol for c in seq):
            raise ValueError("symbol mismatched to feed")
        if tuple(c.closed_at for c in seq) != common_times:
            raise ValueError("M15 series not strictly synchronized")
    if len(feeds) != 1:
        raise ValueError("provider/feed mismatch; parity not certified")
    return common_times[-1]


def detect_smt(
    bars: Mapping[Symbol, Sequence[Candle]], *, lookback: int = 8
) -> tuple[SMT, ...]:
    """Find paired prior-window breakout NON-confirmations, without lookahead.

    A sweep also requires the sweeping bar to close back inside its prior
    rolling extreme; equal highs/lows are NOT sweeps. These are *candidate*
    divergences, not historical ICT swing-pivot certification.
    """
    timestamp = _validate_bars(bars, lookback)
    previous = {s: bars[s][-lookback - 1:-1] for s in SYMBOLS}
    current = {s: bars[s][-1] for s in SYMBOLS}
    high = {s: max(c.high for c in previous[s]) for s in SYMBOLS}
    low = {s: min(c.low for c in previous[s]) for s in SYMBOLS}
    events: list[SMT] = []
    for pair in PAIRS:
        a, b = pair
        for sweeping, follower in ((a, b), (b, a)):
            if (
                current[sweeping].high > high[sweeping]
                and current[sweeping].close < high[sweeping]
                and current[follower].high <= high[follower]
            ):
                events.append(SMT(
                    pair, "BEARISH", sweeping, timestamp,
                    high[sweeping], current[sweeping].high,
                ))
            if (
                current[sweeping].low < low[sweeping]
                and current[sweeping].close > low[sweeping]
                and current[follower].low >= low[follower]
            ):
                events.append(SMT(
                    pair, "BULLISH", sweeping, timestamp,
                    low[sweeping], current[sweeping].low,
                ))
    return tuple(events)


def qualify_research_opportunities(
    *,
    candidates: Sequence[SMT],
    mss_by_symbol: Mapping[Symbol, MSS],
    crt_by_symbol: Mapping[Symbol, CRT],
    evaluated_at: datetime,
    max_age: timedelta = timedelta(minutes=60),
) -> tuple[ResearchOpportunity, ...]:
    """Evaluate either route only after corroborating closed MSS evidence.

    An opposite active CRT is NOT reclassified as "no CRT" to sneak an
    independent entry. Pairs are deduplicated per instrument and direction.
    No live signal, order or position recommendation is produced.
    """
    if not _utc(evaluated_at) or max_age <= timedelta(0):
        raise ValueError("evaluation timestamp/age invalid")
    local_time = evaluated_at.astimezone(NY)
    if local_time.weekday() >= 5 or not WINDOW_START <= local_time.time() < WINDOW_END:
        return ()
    if set(mss_by_symbol) - set(SYMBOLS) or set(crt_by_symbol) - set(SYMBOLS):
        raise ValueError("unsupported evidence symbol")
    # If the same symbol has both SMT directions at once, it is ambiguous.
    direction_sets: dict[Symbol, set[Side]] = {s: set() for s in SYMBOLS}
    for candidate in candidates:
        if candidate.observed_at <= evaluated_at:
            for symbol in candidate.pair:
                direction_sets[symbol].add(candidate.direction)
    opportunities: list[ResearchOpportunity] = []
    seen: set[tuple[Symbol, Side]] = set()
    for candidate in sorted(candidates, key=lambda e: PAIRS.index(e.pair)):
        if not _utc(candidate.observed_at):
            continue
        if not timedelta(0) <= evaluated_at - candidate.observed_at <= max_age:
            continue
        for symbol in candidate.pair:
            if len(direction_sets[symbol]) > 1:
                continue
            key = (symbol, candidate.direction)
            if key in seen:
                continue
            mss = mss_by_symbol.get(symbol)
            if mss is None or mss.symbol != symbol or mss.direction != candidate.direction:
                continue
            if not mss.valid() or mss.confirmed_at > evaluated_at:
                continue
            if abs(mss.confirmed_at - candidate.observed_at) > max_age:
                continue
            crt = crt_by_symbol.get(symbol)
            if crt is not None and crt.usable(evaluated_at):
                if crt.direction != candidate.direction:
                    continue
                route: Route = "CRT_SMT_MSS"
                family: str | None = crt.family
            else:
                # An invalid/old CRT is not a validated CRT condition.
                route = "SMT_MSS_NO_CRT"
                family = None
            opportunities.append(ResearchOpportunity(
                instrument=symbol,
                route=route,
                direction=candidate.direction,
                smt=candidate,
                mss_confirmed_at=mss.confirmed_at,
                crt_family=family,
                evaluated_at=evaluated_at,
            ))
            seen.add(key)
    return tuple(opportunities)
