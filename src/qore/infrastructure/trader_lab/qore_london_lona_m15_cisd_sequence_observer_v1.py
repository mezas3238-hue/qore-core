"""LON-A M15 *research observer*, no author-exact CISD, no trades.

Source: https://ttrades.com/understanding-the-change-in-state-of-delivery-cisd/
Author describes a close through the opening of the FIRST candle in a
consecutive opposing delivery series. Selecting the unique causal "series
that made the swing" is still unadjudicated for LON-A (Issue #785).

Emit all schematic crossings, never select the most profitable candidate.
Dates, raw candle prices and provider provenance come from the caller,
not inferred from any outcome. Nothing here can authorize replay/live.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation

from qore.infrastructure.trader_lab.qore_london_lona_first_online_chronology_gate_v1 import _utc

IDENTITY = "QORE_LONA_M15_CISD_SEQUENCE_OBSERVER_NOT_AUTHOR_EXACT"
PERIOD = timedelta(minutes=15)
SYMBOLS = frozenset({"EURUSD", "GBPUSD"})


def _price(raw: str) -> Decimal:
    if not isinstance(raw, str):
        raise ValueError("PRICE_MUST_BE_DECIMAL_STRING")
    try:
        p = Decimal(raw)
    except InvalidOperation as exc:
        raise ValueError("BAD_PRICE_DECIMAL") from exc
    if not p.is_finite() or p <= 0:
        raise ValueError("NONFINITE_OR_NONPOSITIVE_PRICE")
    return p


@dataclass(frozen=True)
class Candle:
    symbol: str
    provider_id: str
    bar_open_utc: str
    bar_close_utc: str
    first_known_utc: str
    open: str
    high: str
    low: str
    close: str

    def validated(self) -> tuple[datetime, datetime, Decimal, Decimal, Decimal, Decimal]:
        if self.symbol not in SYMBOLS or not self.provider_id:
            raise ValueError("UNKNOWN_SYMBOL_OR_PROVIDER")
        start, end, known = (_utc(self.bar_open_utc), _utc(self.bar_close_utc),
                             _utc(self.first_known_utc))
        if (end - start) != PERIOD or known < end:
            raise ValueError("BAR_DURATION_OR_FUTURE_CLOSE_LEAK")
        if start.minute % 15 or start.second or start.microsecond:
            raise ValueError("M15_GRID_MISALIGNED")
        o, h, l, c = tuple(_price(v) for v in
                           (self.open, self.high, self.low, self.close))
        if not l <= min(o, c) <= max(o, c) <= h:
            raise ValueError("INVALID_OHLC_GEOMETRY")
        return start, end, o, h, l, c


def observe_sequences(
    *, bars: tuple[Candle, ...], decision_at_utc: str, direction: str,
) -> dict[str, object]:
    """Stateless as-of audit. A crossed first-open is schematic, NOT a trade.

    All visible bars must be contiguous; partition around known market
    closures before calling. Gap/DST/provider conflicts fail closed.
    Missing unobserved upstream data cannot be detected: Gate B separate.
    """
    decision = _utc(decision_at_utc)
    if direction not in {"BULLISH", "BEARISH"}:
        raise ValueError("DIRECTION_MUST_BE_EXPLICIT")
    visible = tuple(bar for bar in bars if _utc(bar.first_known_utc) <= decision)
    problems: list[str] = []
    prepared: list[tuple[Candle, datetime, datetime, Decimal, Decimal, Decimal, Decimal]] = []
    for index, bar in enumerate(visible):
        try:
            start, end, o, h, l, c = bar.validated()
        except ValueError as exc:
            problems.append(f"INVALID_BAR:{index}:{exc}")
            continue
        prepared.append((bar, start, end, o, h, l, c))
    if prepared:
        if any(bar.symbol != prepared[0][0].symbol for bar, *_ in prepared):
            problems.append("CROSS_SYMBOL_BAR_MIX")
        if any(bar.provider_id != prepared[0][0].provider_id for bar, *_ in prepared):
            problems.append("CROSS_PROVIDER_BAR_MIX")
        for older, later in zip(prepared, prepared[1:]):
            if later[1] < older[2]:
                problems.append("DUPLICATE_OR_OVERLAPPING_BARS")
            elif later[1] > older[2]:
                problems.append("M15_GAP_NOT_BACKFILLED")
    if problems:
        return {
            "identity": IDENTITY, "status": "BLOCKED_INPUT",
            "blockers": sorted(set(problems)), "schematic_candidates": [],
            "visible_bars": len(visible),
            "future_bars_ignored": len(bars) - len(visible),
            "author_exact": False, "protected_swing_certified": False,
            "entry_authorized": False, "economic_replay_authorized": False,
        }
    # A maximal contiguous run of down-closing bars (for bullish) or
    # up-closing bars (for bearish) is *one* interpretation of "series".
    # It is a research hypothesis, not an author-validated swing selector.
    def opposing(row: tuple) -> bool:
        o, c = row[3], row[6]
        return c < o if direction == "BULLISH" else c > o

    events: list[dict[str, object]] = []
    i = 0
    while i < len(prepared):
        if not opposing(prepared[i]):
            i += 1
            continue
        first = i
        while i < len(prepared) and opposing(prepared[i]):
            i += 1
        last = i - 1
        first_open = prepared[first][3]
        swing_extreme = (min(row[5] for row in prepared[first:i])
                         if direction == "BULLISH"
                         else max(row[4] for row in prepared[first:i]))
        for j in range(i, len(prepared)):
            bar, _, end, _, _, _, c = prepared[j]
            crossed = c > first_open if direction == "BULLISH" else c < first_open
            if crossed:
                period_extreme = (min(row[5] for row in prepared[i:j + 1])
                                  if direction == "BULLISH"
                                  else max(row[4] for row in prepared[i:j + 1]))
                later_extreme_worse = (period_extreme < swing_extreme
                                       if direction == "BULLISH"
                                       else period_extreme > swing_extreme)
                events.append({
                    "candidate_id": f"{direction}:{prepared[first][1].isoformat()}:{end.isoformat()}",
                    "direction": direction,
                    "first_series_bar_open_utc": prepared[first][0].bar_open_utc,
                    "last_series_bar_close_utc": prepared[last][0].bar_close_utc,
                    "series_length_observed_not_author_threshold": last - first + 1,
                    "first_opposing_open_price": str(first_open),
                    "raw_series_extreme_not_protected_swing": str(swing_extreme),
                    "cross_bar_close_utc": bar.bar_close_utc,
                    "cross_first_known_utc": bar.first_known_utc,
                    "post_series_extreme_worse_before_cross": later_extreme_worse,
                    "source_id": bar.provider_id,
                    "rule_reference": "LONA-LA08 / CISD 2025-06-29",
                    "author_exact": False,
                    "valid_protected_swing": False,
                    "fill_price": None,
                })
                break
    by_cross: dict[str, int] = {}
    for event in events:
        key = str(event["cross_bar_close_utc"])
        by_cross[key] = by_cross.get(key, 0) + 1
    for event in events:
        event["multiple_series_cross_same_bar"] = by_cross[str(event["cross_bar_close_utc"])] > 1
    return {
        "identity": IDENTITY, "status": "OBSERVATIONAL_ONLY",
        "blockers": [],
        "schematic_candidates": events,
        "ambiguous_same_bar_candidate_count": sum(
            1 for event in events if event["multiple_series_cross_same_bar"]
        ),
        "visible_bars": len(visible),
        "future_bars_ignored": len(bars) - len(visible),
        "symbol": prepared[0][0].symbol if prepared else None,
        "author_exact": False,
        "protected_swing_certified": False,
        "entry_authorized": False,
        "economic_replay_authorized": False,
    }
