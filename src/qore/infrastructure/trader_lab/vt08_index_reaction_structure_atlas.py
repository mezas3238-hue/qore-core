"""Source-bound reaction-structure diagnostics for VT-08 Index consumed evidence.

This atlas explains where price arrived before expansion and what it did around
that reaction. It never changes frozen V7 or promotes an observed structure into
an automatic trading rule.
"""

from __future__ import annotations

import argparse
import json
from bisect import bisect_left
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from statistics import median
from typing import cast
from zoneinfo import ZoneInfo

from qore.infrastructure.trader_lab.vt08_index_market_journey_atlas import (
    Bar,
    _decimal,
    _dt,
    _fmt,
    _fvg_events,
    _load_bars,
    _local_sweep_events,
)

SCHEMA = "qore.trader_lab.vt08_index_reaction_structure_atlas.v2"
COMBINED_SCHEMA = "qore.trader_lab.vt08_index_reaction_structure_atlas.combined.v2"
_NY = ZoneInfo("America/New_York")


@dataclass(frozen=True, slots=True)
class StructureZone:
    kind: str
    side: str
    formed_at: datetime
    confirmed_at: datetime
    low: Decimal
    high: Decimal
    definition: str


def _median_int(values: Sequence[int]) -> int | None:
    return int(median(values)) if values else None


def _opposing_series(
    bars: Sequence[Bar],
    before_index: int,
    *,
    bullish: bool,
) -> tuple[Bar, ...]:
    selected: list[Bar] = []
    index = before_index - 1
    while index >= 0:
        bar = bars[index]
        opposing = bar.close < bar.open if bullish else bar.close > bar.open
        if not opposing:
            break
        selected.append(bar)
        index -= 1
    selected.reverse()
    return tuple(selected)


def _order_block_zones(bars: Sequence[Bar]) -> list[StructureZone]:
    """Return CISD-confirmed opposing-candle series, for diagnostics only."""
    zones: list[StructureZone] = []
    for index in range(1, len(bars)):
        current = bars[index]
        bullish = current.close > current.open
        bearish = current.close < current.open
        if not bullish and not bearish:
            continue
        series = _opposing_series(bars, index, bullish=bullish)
        if not series:
            continue
        confirmed = (
            current.close > max(bar.open for bar in series)
            if bullish
            else current.close < min(bar.open for bar in series)
        )
        if not confirmed:
            continue
        zones.append(
            StructureZone(
                kind="order-block",
                side="bullish" if bullish else "bearish",
                formed_at=series[0].opened_at,
                confirmed_at=current.closed_at,
                low=min(bar.low for bar in series),
                high=max(bar.high for bar in series),
                definition="ttrades-opposing-series-confirmed-by-close",
            )
        )
    return zones


def _pivot_points(
    bars: Sequence[Bar],
    radius: int = 1,
) -> list[tuple[str, int, Decimal]]:
    pivots: list[tuple[str, int, Decimal]] = []
    for index in range(radius, len(bars) - radius):
        bar = bars[index]
        neighbors = [
            *bars[index - radius : index],
            *bars[index + 1 : index + radius + 1],
        ]
        if bar.low < min(item.low for item in neighbors):
            pivots.append(("L", index, bar.low))
        if bar.high > max(item.high for item in neighbors):
            pivots.append(("H", index, bar.high))
    pivots.sort(key=lambda item: item[1])
    compressed: list[tuple[str, int, Decimal]] = []
    for pivot in pivots:
        if not compressed or compressed[-1][0] != pivot[0]:
            compressed.append(pivot)
            continue
        previous = compressed[-1]
        if pivot[0] == "L" and pivot[2] < previous[2]:
            compressed[-1] = pivot
        elif pivot[0] == "H" and pivot[2] > previous[2]:
            compressed[-1] = pivot
    return compressed


def _breaker_zones(bars: Sequence[Bar]) -> list[StructureZone]:
    """Return TTrades L-H-LL-HH / H-L-HH-LL breaker candidates."""
    pivots = _pivot_points(bars)
    zones: list[StructureZone] = []
    for first, second, third, fourth in zip(
        pivots,
        pivots[1:],
        pivots[2:],
        pivots[3:],
        strict=False,
    ):
        kinds = "".join((first[0], second[0], third[0], fourth[0]))
        bullish = kinds == "LHLH" and third[2] < first[2] and fourth[2] > second[2]
        bearish = kinds == "HLHL" and third[2] > first[2] and fourth[2] < second[2]
        if not bullish and not bearish:
            continue
        source = [
            bar
            for bar in bars[first[1] : second[1] + 1]
            if (bar.close > bar.open if bullish else bar.close < bar.open)
        ]
        if not source:
            continue
        zones.append(
            StructureZone(
                kind="breaker-block",
                side="bullish" if bullish else "bearish",
                formed_at=bars[first[1]].opened_at,
                confirmed_at=bars[fourth[1]].closed_at,
                low=min(bar.low for bar in source),
                high=max(bar.high for bar in source),
                definition=(
                    "ttrades-low-high-lower-low-higher-high"
                    if bullish
                    else "ttrades-high-low-higher-high-lower-low"
                ),
            )
        )
    return zones


def _fvg_zones(bars: Sequence[Bar]) -> list[StructureZone]:
    zones: list[StructureZone] = []
    for event in _fvg_events(bars):
        kind = str(event["kind"])
        zones.append(
            StructureZone(
                kind="fvg",
                side="bullish" if kind == "bullish-fvg" else "bearish",
                formed_at=_dt(event["formed_at"]),
                confirmed_at=_dt(event["formed_at"]),
                low=_decimal(event["low"]),
                high=_decimal(event["high"]),
                definition="ttrades-three-candle-imbalance",
            )
        )
    return zones


def _overlaps(zone: StructureZone, bar: Bar) -> bool:
    return bar.high >= zone.low and bar.low <= zone.high


def _zone_retests(
    zones: Sequence[StructureZone],
    bars: Sequence[Bar],
    signal_at: datetime,
) -> list[dict[str, object]]:
    events: list[dict[str, object]] = []
    for zone in zones:
        for bar in reversed(bars):
            if bar.closed_at >= signal_at or bar.opened_at < zone.confirmed_at:
                continue
            if not _overlaps(zone, bar):
                continue
            events.append(
                {
                    "kind": zone.kind,
                    "side": zone.side,
                    "observed_at": bar.closed_at.isoformat(),
                    "zone_low": _fmt(zone.low),
                    "zone_high": _fmt(zone.high),
                    "formed_at": zone.formed_at.isoformat(),
                    "confirmed_at": zone.confirmed_at.isoformat(),
                    "definition": zone.definition,
                }
            )
            break
    return events


def _liquidity_events(
    bars: Sequence[Bar],
    signal_at: datetime,
) -> list[dict[str, object]]:
    result: list[dict[str, object]] = []
    for event in _local_sweep_events(bars):
        observed = _dt(event["observed_at"])
        if observed >= signal_at:
            continue
        result.append(
            {
                "kind": "liquidity-sweep",
                "side": (
                    "bearish"
                    if str(event["kind"]).startswith("high")
                    else "bullish"
                ),
                "observed_at": observed.isoformat(),
                "level": event["level"],
                "definition": "short-term-extreme-run-and-close-back",
            }
        )
    return result


def _segment_behavior(bars: Sequence[Bar]) -> dict[str, object]:
    if not bars:
        return {
            "descriptor": "insufficient",
            "sample": 0,
            "efficiency": None,
            "body_flip_count": 0,
            "inside_bar_rate": None,
        }
    high = max(bar.high for bar in bars)
    low = min(bar.low for bar in bars)
    span = high - low
    displacement = abs(bars[-1].close - bars[0].open)
    efficiency = displacement / span if span > 0 else Decimal()
    directions = [
        1 if bar.close > bar.open else -1 if bar.close < bar.open else 0
        for bar in bars
    ]
    flips = sum(
        first != 0 and second != 0 and first != second
        for first, second in zip(directions, directions[1:], strict=False)
    )
    inside = sum(
        current.high <= previous.high and current.low >= previous.low
        for previous, current in zip(bars, bars[1:], strict=False)
    )
    denominator = max(1, len(bars) - 1)
    if efficiency <= Decimal("0.35") and flips >= 2:
        descriptor = "accumulation-like"
    elif efficiency >= Decimal("0.65"):
        descriptor = "expansion-like"
    else:
        descriptor = "transition-mixed"
    return {
        "descriptor": descriptor,
        "sample": len(bars),
        "efficiency": _fmt(efficiency),
        "body_flip_count": flips,
        "inside_bar_rate": _fmt(Decimal(inside) / Decimal(denominator)),
    }


def _slice(
    bars: Sequence[Bar],
    opened_times: Sequence[datetime],
    start: datetime,
    end: datetime,
) -> tuple[Bar, ...]:
    left = bisect_left(opened_times, start)
    right = bisect_left(opened_times, end)
    return tuple(bars[left:right])


def _hit(row: dict[str, object], level: str) -> bool:
    levels = cast(dict[str, object], row["time_to_favorable_levels"])
    payload = cast(dict[str, object], levels[level])
    return bool(payload["hit"])


def _hit_at(row: dict[str, object], level: str) -> datetime | None:
    levels = cast(dict[str, object], row["time_to_favorable_levels"])
    payload = cast(dict[str, object], levels[level])
    value = payload.get("at")
    return _dt(value) if value else None


def _episode(
    row: dict[str, object],
    bars: Sequence[Bar],
    opened_times: Sequence[datetime],
) -> dict[str, object]:
    signal_at = _dt(row["signal_at"])
    window = _slice(
        bars,
        opened_times,
        signal_at - timedelta(hours=24),
        signal_at,
    )
    structures = [
        *_zone_retests(_fvg_zones(window), window, signal_at),
        *_zone_retests(_order_block_zones(window), window, signal_at),
        *_zone_retests(_breaker_zones(window), window, signal_at),
        *_liquidity_events(window, signal_at),
    ]
    wanted_side = "bullish" if str(row["side"]) == "long" else "bearish"
    structures = [item for item in structures if item["side"] == wanted_side]
    structures.sort(key=lambda item: str(item["observed_at"]))

    reaction_at: datetime | None = None
    reaction_structures: list[dict[str, object]] = []
    if structures:
        reaction_at = _dt(structures[-1]["observed_at"])
        reaction_structures = [
            item
            for item in structures
            if _dt(item["observed_at"]) == reaction_at
        ]

    pre_arrival: tuple[Bar, ...] = ()
    reaction_to_signal: tuple[Bar, ...] = ()
    post_arrival_60m: tuple[Bar, ...] = ()
    if reaction_at is not None:
        pre_arrival = _slice(
            bars,
            opened_times,
            reaction_at - timedelta(minutes=60),
            reaction_at,
        )
        reaction_to_signal = _slice(
            bars,
            opened_times,
            reaction_at,
            signal_at,
        )
        post_arrival_60m = _slice(
            bars,
            opened_times,
            reaction_at,
            reaction_at + timedelta(minutes=60),
        )

    pre_phase = _segment_behavior(pre_arrival)
    transition_phase = _segment_behavior(reaction_to_signal)
    post_phase = _segment_behavior(post_arrival_60m)
    reaction_event = (
        "liquidity-take"
        if any(item["kind"] == "liquidity-sweep" for item in reaction_structures)
        else "structure-retest"
        if reaction_structures
        else "none-detected"
    )
    combo = "+".join(
        sorted({str(item["kind"]) for item in reaction_structures})
    ) or "none-detected"

    one_r_at = _hit_at(row, "1")
    two_r_at = _hit_at(row, "2")
    return {
        "symbol": row["symbol"],
        "signal_at": row["signal_at"],
        "weekday_new_york": row["weekday_new_york"],
        "anchor_hour_new_york": row["anchor_hour_new_york"],
        "side": row["side"],
        "v7_poi_kind": row["poi_kind"],
        "reaction_at": reaction_at.isoformat() if reaction_at else None,
        "reaction_hour_new_york": (
            reaction_at.astimezone(_NY).hour if reaction_at else None
        ),
        "reaction_event": reaction_event,
        "reaction_structure_combo": combo,
        "reaction_structures": reaction_structures,
        "pre_arrival_phase_60m": pre_phase["descriptor"],
        "reaction_to_signal_phase": transition_phase["descriptor"],
        "post_arrival_phase_60m": post_phase["descriptor"],
        "pre_arrival_detail": pre_phase,
        "reaction_to_signal_detail": transition_phase,
        "post_arrival_detail_60m": post_phase,
        "minutes_reaction_to_signal": (
            int((signal_at - reaction_at).total_seconds() // 60)
            if reaction_at is not None
            else None
        ),
        "minutes_reaction_to_1r": (
            int((one_r_at - reaction_at).total_seconds() // 60)
            if reaction_at is not None
            and one_r_at is not None
            and one_r_at >= reaction_at
            else None
        ),
        "minutes_reaction_to_2r": (
            int((two_r_at - reaction_at).total_seconds() // 60)
            if reaction_at is not None
            and two_r_at is not None
            and two_r_at >= reaction_at
            else None
        ),
        "hit_1r": _hit(row, "1"),
        "hit_2r": _hit(row, "2"),
        "hit_3r": _hit(row, "3"),
        "stopped": _decimal(row["raw_r"]) < 0,
        "post_stop_afterlife": row["post_stop_afterlife"],
        "known_directional_boundaries": row["known_directional_boundaries"],
        "peer_snapshot": row["peer_snapshot"],
        "prior_h4_range_regime": row["prior_h4_range_regime"],
    }


def _rate(episodes: Sequence[dict[str, object]], key: str) -> str:
    count = sum(bool(item[key]) for item in episodes)
    return _fmt(Decimal(count) / Decimal(len(episodes)))


def _summary(episodes: Sequence[dict[str, object]]) -> dict[str, object]:
    if not episodes:
        return {"sample": 0}
    reaction_to_signal = [
        int(str(item["minutes_reaction_to_signal"]))
        for item in episodes
        if item["minutes_reaction_to_signal"] is not None
    ]
    reaction_to_one = [
        int(str(item["minutes_reaction_to_1r"]))
        for item in episodes
        if item["minutes_reaction_to_1r"] is not None
    ]
    reaction_to_two = [
        int(str(item["minutes_reaction_to_2r"]))
        for item in episodes
        if item["minutes_reaction_to_2r"] is not None
    ]
    return {
        "sample": len(episodes),
        "stop_rate": _rate(episodes, "stopped"),
        "hit_1r_rate": _rate(episodes, "hit_1r"),
        "hit_2r_rate": _rate(episodes, "hit_2r"),
        "hit_3r_rate": _rate(episodes, "hit_3r"),
        "median_minutes_reaction_to_signal": _median_int(reaction_to_signal),
        "median_minutes_reaction_to_1r": _median_int(reaction_to_one),
        "median_minutes_reaction_to_2r": _median_int(reaction_to_two),
    }


def _group(
    episodes: Sequence[dict[str, object]],
    keys: tuple[str, ...],
) -> dict[str, object]:
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for episode in episodes:
        label = "|".join(str(episode.get(key, "unknown")) for key in keys)
        grouped[label].append(episode)
    return {
        label: _summary(items)
        for label, items in sorted(grouped.items())
    }


def _definition_status() -> dict[str, str]:
    return {
        "fvg": "SOURCE_BOUND_DIAGNOSTIC: TTrades three-candle imbalance",
        "liquidity_sweep": (
            "SOURCE_BOUND_DIAGNOSTIC: short-term extreme run with close-back"
        ),
        "order_block": (
            "SOURCE_BOUND_DIAGNOSTIC: opposing series confirmed by closure/CISD"
        ),
        "breaker_block": (
            "SOURCE_BOUND_DIAGNOSTIC: L-H-LL-HH or H-L-HH-LL plus retest"
        ),
        "mitigation_block": (
            "UNRESOLVED_FOR_THIS_ATLAS: separate formalization required"
        ),
        "phase_labels": (
            "DESCRIPTIVE_HEURISTIC_ONLY: fixed 60m efficiency/body-flip labels"
        ),
    }


def _governance() -> dict[str, bool]:
    return {
        "diagnostic_only": True,
        "consumed_evidence_only": True,
        "changes_v7": False,
        "observed_structure_is_not_causation": True,
        "post_arrival_phase_is_outcome_not_admission_feature": True,
        "automatic_rule_promotion_forbidden": True,
        "fresh_validation_required_for_any_specialist_rule": True,
        "live_authorized": False,
        "real_capital_authorized": False,
        "production_authorized": False,
    }


def _aggregates(episodes: Sequence[dict[str, object]]) -> dict[str, object]:
    return {
        "by_market_structure_combo": _group(
            episodes,
            ("symbol", "reaction_structure_combo"),
        ),
        "by_market_weekday_structure_combo": _group(
            episodes,
            ("symbol", "weekday_new_york", "reaction_structure_combo"),
        ),
        "by_market_hour_structure_combo": _group(
            episodes,
            ("symbol", "reaction_hour_new_york", "reaction_structure_combo"),
        ),
        "by_market_pre_arrival_phase": _group(
            episodes,
            ("symbol", "pre_arrival_phase_60m"),
        ),
        "by_market_post_arrival_phase": _group(
            episodes,
            ("symbol", "post_arrival_phase_60m"),
        ),
        "by_market_structure_post_phase": _group(
            episodes,
            ("symbol", "reaction_structure_combo", "post_arrival_phase_60m"),
        ),
    }


def analyze_window(
    *,
    journey: Path,
    nas100: Path,
    sp500: Path,
    us30: Path,
) -> dict[str, object]:
    payload = cast(
        dict[str, object],
        json.loads(journey.read_text(encoding="utf-8")),
    )
    trades = cast(list[dict[str, object]], payload["trades"])
    paths = {"NAS100": nas100, "SP500": sp500, "US30": us30}
    bars = {
        symbol: _load_bars(path, symbol)
        for symbol, path in paths.items()
    }
    opened_times = {
        symbol: tuple(bar.opened_at for bar in market_bars)
        for symbol, market_bars in bars.items()
    }
    episodes = [
        _episode(
            row,
            bars[str(row["symbol"])],
            opened_times[str(row["symbol"])],
        )
        for row in trades
    ]
    return {
        "schema": SCHEMA,
        "candidate_id": payload["candidate_id"],
        "rule_fingerprint": payload["rule_fingerprint"],
        "window": payload["window"],
        "episode_count": len(episodes),
        "episodes": episodes,
        **_aggregates(episodes),
        "definition_status": _definition_status(),
        "governance": _governance(),
    }


def combine(payloads: Sequence[dict[str, object]]) -> dict[str, object]:
    if not payloads:
        raise ValueError("at least one reaction-structure window is required")
    episodes = [
        episode
        for payload in payloads
        for episode in cast(list[dict[str, object]], payload["episodes"])
    ]
    first = payloads[0]
    return {
        "schema": COMBINED_SCHEMA,
        "candidate_id": first["candidate_id"],
        "rule_fingerprint": first["rule_fingerprint"],
        "windows": [payload["window"] for payload in payloads],
        "episode_count": len(episodes),
        "episodes": episodes,
        **_aggregates(episodes),
        "definition_status": first["definition_status"],
        "governance": first["governance"],
    }


def _write(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    path.write_text(serialized + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    window = sub.add_parser("window")
    window.add_argument("--journey", type=Path, required=True)
    window.add_argument("--nas100", type=Path, required=True)
    window.add_argument("--sp500", type=Path, required=True)
    window.add_argument("--us30", type=Path, required=True)
    window.add_argument("--out", type=Path, required=True)
    combined = sub.add_parser("combine")
    combined.add_argument("inputs", nargs="+", type=Path)
    combined.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "window":
        result = analyze_window(
            journey=args.journey,
            nas100=args.nas100,
            sp500=args.sp500,
            us30=args.us30,
        )
    else:
        payloads = [
            cast(
                dict[str, object],
                json.loads(path.read_text(encoding="utf-8")),
            )
            for path in args.inputs
        ]
        result = combine(payloads)
    _write(args.out, result)
    print(
        json.dumps(
            {
                "schema": result["schema"],
                "episode_count": result["episode_count"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
