"""Complete CIBO market-intelligence ledgers for VT-08 Index consumed evidence.

Research-only diagnostics. The eight ledgers materialize the full market journey,
structure touches, pre-departure sequence, departure timing, target destination,
cross-index lead/lag, daily path, and trader-vs-market synchronization.

Nothing in this module changes frozen V7 economics or authorizes live trading.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import cast
from zoneinfo import ZoneInfo

from qore.infrastructure.trader_lab.vt08_index_market_journey_atlas import (
    Bar,
    _decimal,
    _dt,
    _fmt,
    _load_bars,
    _source_day_key,
)
from qore.infrastructure.trader_lab.vt08_index_reaction_structure_atlas import (
    StructureZone,
    _breaker_zones,
    _fvg_zones,
    _liquidity_events,
    _order_block_zones,
)

SCHEMA = "qore.trader_lab.vt08_index_cibo_complete_ledgers.v1"
_NY = ZoneInfo("America/New_York")
LEDGER_NAMES = (
    "MARKET_JOURNEY_LEDGER",
    "STRUCTURE_TOUCH_LEDGER",
    "PRE_DEPARTURE_SEQUENCE_LEDGER",
    "DEPARTURE_TIMING_LEDGER",
    "TARGET_DESTINATION_LEDGER",
    "CROSS_INDEX_JOURNEY_LEDGER",
    "DAILY_PATH_LEDGER",
    "TRADER_MARKET_SYNC_LEDGER",
)


def _load(path: Path) -> dict[str, object]:
    return cast(dict[str, object], json.loads(path.read_text(encoding="utf-8")))


def _write(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )


def _side_label(trade_side: str) -> str:
    return "bullish" if trade_side == "long" else "bearish"


def _overlaps(zone: StructureZone, bar: Bar) -> bool:
    return bar.high >= zone.low and bar.low <= zone.high


def _penetration_fraction(zone: StructureZone, bar: Bar) -> Decimal:
    width = zone.high - zone.low
    if width <= 0 or not _overlaps(zone, bar):
        return Decimal()
    if zone.side == "bullish":
        depth = zone.high - max(bar.low, zone.low)
    else:
        depth = min(bar.high, zone.high) - zone.low
    return max(Decimal(), min(Decimal(1), depth / width))


def _touch_payload(
    zone: StructureZone,
    bars: Sequence[Bar],
    signal_at: datetime,
) -> dict[str, object] | None:
    eligible = [
        bar
        for bar in bars
        if zone.confirmed_at <= bar.opened_at
        and bar.closed_at < signal_at
        and _overlaps(zone, bar)
    ]
    if not eligible:
        return None
    penetrations = [_penetration_fraction(zone, bar) for bar in eligible]
    return {
        "kind": zone.kind,
        "side": zone.side,
        "formed_at": zone.formed_at.isoformat(),
        "confirmed_at": zone.confirmed_at.isoformat(),
        "zone_low": _fmt(zone.low),
        "zone_high": _fmt(zone.high),
        "lookback_hours": 72,
        "touch_count": len(eligible),
        "first_touch_at": eligible[0].closed_at.isoformat(),
        "last_touch_at": eligible[-1].closed_at.isoformat(),
        "dwell_minutes": len(eligible) * 15,
        "max_penetration_fraction": _fmt(max(penetrations)),
        "mean_penetration_fraction": _fmt(
            sum(penetrations, Decimal()) / Decimal(len(penetrations))
        ),
        "definition": zone.definition,
    }


def _structure_touches(
    episode: dict[str, object],
    bars: Sequence[Bar],
) -> list[dict[str, object]]:
    signal_at = _dt(episode["signal_at"])
    start = signal_at - timedelta(hours=72)
    window = tuple(bar for bar in bars if start <= bar.opened_at < signal_at)
    aligned = _side_label(str(episode["side"]))
    zones = [
        zone
        for zone in [
            *_fvg_zones(window),
            *_order_block_zones(window),
            *_breaker_zones(window),
        ]
        if zone.side == aligned
    ]
    rows = [
        payload
        for zone in zones
        if (payload := _touch_payload(zone, window, signal_at))
    ]
    for event in _liquidity_events(window, signal_at):
        if str(event["side"]) != aligned:
            continue
        rows.append(
            {
                "kind": "liquidity-sweep",
                "side": event["side"],
                "formed_at": event["observed_at"],
                "confirmed_at": event["observed_at"],
                "touch_count": 1,
                "first_touch_at": event["observed_at"],
                "last_touch_at": event["observed_at"],
                "dwell_minutes": 15,
                "max_penetration_fraction": None,
                "mean_penetration_fraction": None,
                "level": event.get("level"),
                "definition": event["definition"],
            }
        )
    rows.sort(key=lambda item: (str(item["last_touch_at"]), str(item["kind"])))
    return rows


def _hit_payload(trade: dict[str, object], level: str) -> dict[str, object]:
    levels = cast(dict[str, object], trade["time_to_favorable_levels"])
    return cast(dict[str, object], levels[level])


def _event_sequence(
    trade: dict[str, object],
    touches: Sequence[dict[str, object]],
) -> list[dict[str, object]]:
    events: list[dict[str, object]] = []
    for touch in touches:
        events.append(
            {
                "event": f"structure-touch:{touch['kind']}",
                "at": touch["last_touch_at"],
                "detail": {
                    "touch_count": touch["touch_count"],
                    "dwell_minutes": touch["dwell_minutes"],
                    "max_penetration_fraction": touch[
                        "max_penetration_fraction"
                    ],
                },
            }
        )
    events.append({"event": "trader-signal", "at": str(trade["signal_at"])})
    for level in ("0.5", "1", "2", "3", "5"):
        hit = _hit_payload(trade, level)
        if bool(hit["hit"]):
            events.append({"event": f"favorable-{level}R", "at": hit["at"]})
    afterlife = cast(dict[str, object], trade["post_stop_afterlife"])
    if str(trade["exit_reason"]) == "stop":
        stop_levels = cast(dict[str, object], afterlife["levels"])
        first_after = [
            cast(dict[str, object], value).get("at")
            for value in stop_levels.values()
            if cast(dict[str, object], value).get("at")
        ]
        if first_after:
            events.append(
                {
                    "event": "post-stop-path-observed",
                    "at": min(map(str, first_after)),
                }
            )
    events.sort(key=lambda item: str(item["at"]))
    return events


def _departure_timing(
    trade: dict[str, object],
    reaction: dict[str, object],
) -> dict[str, object]:
    departure = _hit_payload(trade, "0.5")
    reaction_at = reaction.get("reaction_at")
    departure_at = departure.get("at") if bool(departure["hit"]) else None
    return {
        "symbol": trade["symbol"],
        "side": trade["side"],
        "weekday_new_york": trade["weekday_new_york"],
        "anchor_hour_new_york": trade["anchor_hour_new_york"],
        "reaction_at": reaction_at,
        "reaction_hour_new_york": reaction.get("reaction_hour_new_york"),
        "signal_at": trade["signal_at"],
        "signal_hour_new_york": trade["signal_hour_new_york"],
        "departure_definition": (
            "first favorable 0.5R touch after frozen V7 signal"
        ),
        "departure_at": departure_at,
        "minutes_signal_to_departure": departure.get("minutes"),
        "minutes_reaction_to_departure": (
            int((_dt(departure_at) - _dt(reaction_at)).total_seconds() // 60)
            if departure_at and reaction_at
            else None
        ),
        "minutes_reaction_to_1r": reaction.get("minutes_reaction_to_1r"),
        "minutes_reaction_to_2r": reaction.get("minutes_reaction_to_2r"),
        "departed": bool(departure["hit"]),
    }


def _furthest_standard_r(trade: dict[str, object]) -> Decimal:
    result = Decimal()
    levels = cast(dict[str, object], trade["time_to_favorable_levels"])
    for key, value in levels.items():
        payload = cast(dict[str, object], value)
        if bool(payload["hit"]):
            result = max(result, _decimal(key))
    return result


def _target_destination(trade: dict[str, object]) -> dict[str, object]:
    horizons = cast(dict[str, object], trade["horizon_excursions"])
    day = cast(dict[str, object], horizons["1440"])
    max_favorable = _decimal(day["max_favorable_r"])
    furthest = _furthest_standard_r(trade)
    if max_favorable < 1:
        destination = "sub-1R"
    elif max_favorable < 2:
        destination = "1R-to-2R"
    elif max_favorable < 3:
        destination = "2R-to-3R"
    elif max_favorable < 5:
        destination = "3R-to-5R"
    else:
        destination = "5R-plus"
    return {
        "symbol": trade["symbol"],
        "side": trade["side"],
        "signal_at": trade["signal_at"],
        "weekday_new_york": trade["weekday_new_york"],
        "anchor_hour_new_york": trade["anchor_hour_new_york"],
        "available_standard_targets": trade["time_to_favorable_levels"],
        "known_directional_boundaries": trade["known_directional_boundaries"],
        "furthest_standard_r_hit": _fmt(furthest),
        "max_favorable_r_24h": _fmt(max_favorable),
        "extension_beyond_2r_r": _fmt(
            max(Decimal(), max_favorable - Decimal(2))
        ),
        "natural_destination_band_24h": destination,
    }


def _ny_date(value: object) -> str:
    return _dt(value).astimezone(_NY).date().isoformat()


def _cross_index_ledger(
    trades: Sequence[dict[str, object]],
) -> list[dict[str, object]]:
    by_key: dict[tuple[str, int], list[dict[str, object]]] = defaultdict(list)
    for trade in trades:
        key = (
            _ny_date(trade["signal_at"]),
            int(str(trade["anchor_hour_new_york"])),
        )
        by_key[key].append(trade)
    rows: list[dict[str, object]] = []
    for (day, anchor), cohort in sorted(by_key.items()):
        ordered = sorted(cohort, key=lambda item: _dt(item["signal_at"]))
        sides = [str(item["side"]) for item in ordered]
        signals = {
            str(item["symbol"]): item["signal_at"] for item in ordered
        }
        signal_leader = str(ordered[0]["symbol"]) if ordered else None
        signal_base = _dt(ordered[0]["signal_at"]) if ordered else None
        signal_lags = {
            str(item["symbol"]): int(
                (_dt(item["signal_at"]) - signal_base).total_seconds() // 60
            )
            for item in ordered
            if signal_base is not None
        }
        departures: list[tuple[str, datetime]] = []
        for item in ordered:
            hit = _hit_payload(item, "0.5")
            if bool(hit["hit"]) and hit.get("at"):
                departures.append((str(item["symbol"]), _dt(hit["at"])))
        departures.sort(key=lambda item: item[1])
        departure_leader = departures[0][0] if departures else None
        departure_base = departures[0][1] if departures else None
        departure_lags = {
            symbol: int((moment - departure_base).total_seconds() // 60)
            for symbol, moment in departures
            if departure_base is not None
        }
        rows.append(
            {
                "new_york_date": day,
                "anchor_hour_new_york": anchor,
                "symbols_present": sorted(
                    {str(item["symbol"]) for item in ordered}
                ),
                "signal_count": len(ordered),
                "side_agreement": len(set(sides)) <= 1,
                "sides": {
                    str(item["symbol"]): item["side"] for item in ordered
                },
                "signals": signals,
                "signal_leader": signal_leader,
                "signal_lag_minutes": signal_lags,
                "departure_leader_0_5r": departure_leader,
                "departure_lag_minutes_0_5r": departure_lags,
                "relative_strength_rank": {
                    str(item["symbol"]): item["relative_strength_rank"]
                    for item in ordered
                },
                "peer_alignment_count": {
                    str(item["symbol"]): item["peer_alignment_count"]
                    for item in ordered
                },
            }
        )
    return rows


def _day_behavior(bars: Sequence[Bar]) -> dict[str, object]:
    if not bars:
        return {"sample": 0, "descriptor": "insufficient"}
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
        left != 0 and right != 0 and left != right
        for left, right in zip(directions, directions[1:], strict=False)
    )
    inside = sum(
        current.high <= previous.high and current.low >= previous.low
        for previous, current in zip(bars, bars[1:], strict=False)
    )
    if efficiency <= Decimal("0.35") and flips >= 4:
        descriptor = "lateral-accumulation-like"
    elif efficiency >= Decimal("0.65"):
        descriptor = "directional-expansion-like"
    else:
        descriptor = "mixed-transition"
    high_bar = next(bar for bar in bars if bar.high == high)
    low_bar = next(bar for bar in bars if bar.low == low)
    return {
        "sample": len(bars),
        "open": _fmt(bars[0].open),
        "high": _fmt(high),
        "low": _fmt(low),
        "close": _fmt(bars[-1].close),
        "range": _fmt(span),
        "directional_efficiency": _fmt(efficiency),
        "body_flip_count": flips,
        "inside_bar_rate": _fmt(
            Decimal(inside) / Decimal(max(1, len(bars) - 1))
        ),
        "high_at": high_bar.closed_at.isoformat(),
        "low_at": low_bar.closed_at.isoformat(),
        "first_extreme": (
            "high" if high_bar.closed_at <= low_bar.closed_at else "low"
        ),
        "descriptor": descriptor,
    }


def _daily_path_ledger(
    symbol_bars: Mapping[str, Sequence[Bar]],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for symbol, bars in symbol_bars.items():
        grouped: dict[str, list[Bar]] = defaultdict(list)
        for bar in bars:
            grouped[_source_day_key(bar.opened_at).isoformat()].append(bar)
        ordered_days = sorted(grouped)
        prior_ranges: list[Decimal] = []
        for key in ordered_days:
            day_bars = sorted(grouped[key], key=lambda bar: bar.opened_at)
            behavior = _day_behavior(day_bars)
            current_range = _decimal(behavior.get("range", "0"))
            prior20 = prior_ranges[-20:]
            median20 = sorted(prior20)[len(prior20) // 2] if prior20 else None
            rows.append(
                {
                    "symbol": symbol,
                    "source_day": key,
                    "weekday_new_york": day_bars[-1]
                    .opened_at.astimezone(_NY)
                    .strftime("%A"),
                    **behavior,
                    "range_ratio_to_prior20_median": (
                        _fmt(current_range / median20)
                        if median20 is not None and median20 > 0
                        else None
                    ),
                }
            )
            prior_ranges.append(current_range)
    rows.sort(key=lambda item: (str(item["source_day"]), str(item["symbol"])))
    return rows


def _sync_classification(trade: dict[str, object]) -> str:
    stopped = str(trade["exit_reason"]) == "stop"
    hit1 = bool(_hit_payload(trade, "1")["hit"])
    hit2 = bool(_hit_payload(trade, "2")["hit"])
    hit3 = bool(_hit_payload(trade, "3")["hit"])
    if stopped and hit2:
        return "STOPPED_BEFORE_LATER_2R_EXPANSION"
    if stopped and hit1:
        return "STOPPED_AFTER_PARTIAL_FAVORABLE_EXPANSION"
    if stopped:
        return "STOPPED_AND_NO_1R_EXPANSION"
    if hit3:
        return "TRADER_SURVIVED_AND_MARKET_EXTENDED_3R_PLUS"
    if hit2:
        return "TRADER_SURVIVED_TO_2R_REGION"
    if hit1:
        return "TRADER_SURVIVED_PARTIAL_EXPANSION"
    return "NO_MEANINGFUL_FAVORABLE_EXPANSION"


def _sync_row(trade: dict[str, object]) -> dict[str, object]:
    horizons = cast(dict[str, object], trade["horizon_excursions"])
    day = cast(dict[str, object], horizons["1440"])
    return {
        "symbol": trade["symbol"],
        "side": trade["side"],
        "signal_at": trade["signal_at"],
        "weekday_new_york": trade["weekday_new_york"],
        "anchor_hour_new_york": trade["anchor_hour_new_york"],
        "model_kind": trade["model_kind"],
        "poi_kind": trade["poi_kind"],
        "trader_exit_reason": trade["exit_reason"],
        "trader_raw_r": trade["raw_r"],
        "trader_primary_r": trade["primary_r"],
        "market_max_favorable_r_24h": day["max_favorable_r"],
        "market_max_adverse_r_24h": day["max_adverse_r"],
        "post_stop_afterlife": trade["post_stop_afterlife"],
        "sync_class": _sync_classification(trade),
    }


def _index_reactions(
    reactions: Sequence[dict[str, object]],
) -> dict[tuple[str, str], dict[str, object]]:
    return {
        (str(item["symbol"]), str(item["signal_at"])): item
        for item in reactions
    }


def _package(
    name: str,
    rows: Iterable[dict[str, object]],
    window_id: str,
) -> dict[str, object]:
    materialized = list(rows)
    return {
        "schema": f"{SCHEMA}.{name.lower()}",
        "ledger": name,
        "window_id": window_id,
        "row_count": len(materialized),
        "rows": materialized,
        "governance": {
            "diagnostic_only": True,
            "consumed_evidence_only": True,
            "changes_v7": False,
            "automatic_rule_promotion_forbidden": True,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        },
    }


def build_window(
    *,
    journey_path: Path,
    reaction_path: Path,
    nas100_path: Path,
    sp500_path: Path,
    us30_path: Path,
    out_dir: Path,
) -> None:
    journey = _load(journey_path)
    reaction = _load(reaction_path)
    trades = cast(list[dict[str, object]], journey["trades"])
    reactions = cast(list[dict[str, object]], reaction["episodes"])
    reaction_index = _index_reactions(reactions)
    bars = {
        "NAS100": _load_bars(nas100_path, "NAS100"),
        "SP500": _load_bars(sp500_path, "SP500"),
        "US30": _load_bars(us30_path, "US30"),
    }
    window_id = str(journey.get("window_id", journey.get("window", "unknown")))

    market_rows: list[dict[str, object]] = []
    structure_rows: list[dict[str, object]] = []
    sequence_rows: list[dict[str, object]] = []
    departure_rows: list[dict[str, object]] = []
    target_rows: list[dict[str, object]] = []
    sync_rows: list[dict[str, object]] = []

    for trade in trades:
        key = (str(trade["symbol"]), str(trade["signal_at"]))
        reaction_row = reaction_index[key]
        touches = _structure_touches(
            reaction_row,
            bars[str(trade["symbol"])],
        )
        last_touch = touches[-1] if touches else None
        market_rows.append({**trade, "reaction": reaction_row})
        structure_rows.append(
            {
                "symbol": trade["symbol"],
                "side": trade["side"],
                "signal_at": trade["signal_at"],
                "weekday_new_york": trade["weekday_new_york"],
                "anchor_hour_new_york": trade["anchor_hour_new_york"],
                "touches": touches,
                "structure_touch_count": len(touches),
                "last_structure_before_departure": last_touch,
            }
        )
        sequence_rows.append(
            {
                "symbol": trade["symbol"],
                "side": trade["side"],
                "signal_at": trade["signal_at"],
                "pre_arrival_phase_60m": reaction_row.get(
                    "pre_arrival_phase_60m"
                ),
                "reaction_to_signal_phase": reaction_row.get(
                    "reaction_to_signal_phase"
                ),
                "post_arrival_phase_60m": reaction_row.get(
                    "post_arrival_phase_60m"
                ),
                "events": _event_sequence(trade, touches),
            }
        )
        departure_rows.append(_departure_timing(trade, reaction_row))
        target_rows.append(_target_destination(trade))
        sync_rows.append(_sync_row(trade))

    ledgers = {
        "MARKET_JOURNEY_LEDGER": market_rows,
        "STRUCTURE_TOUCH_LEDGER": structure_rows,
        "PRE_DEPARTURE_SEQUENCE_LEDGER": sequence_rows,
        "DEPARTURE_TIMING_LEDGER": departure_rows,
        "TARGET_DESTINATION_LEDGER": target_rows,
        "CROSS_INDEX_JOURNEY_LEDGER": _cross_index_ledger(trades),
        "DAILY_PATH_LEDGER": _daily_path_ledger(bars),
        "TRADER_MARKET_SYNC_LEDGER": sync_rows,
    }
    for name, rows in ledgers.items():
        _write(out_dir / f"{name}.json", _package(name, rows, window_id))


def combine_windows(input_dirs: Sequence[Path], out_dir: Path) -> None:
    for name in LEDGER_NAMES:
        rows: list[dict[str, object]] = []
        windows: list[str] = []
        for root in input_dirs:
            payload = _load(root / f"{name}.json")
            windows.append(str(payload["window_id"]))
            rows.extend(cast(list[dict[str, object]], payload["rows"]))
        result = _package(name, rows, "combined-consumed-2018-2026")
        result["windows"] = windows
        _write(out_dir / f"{name}.json", result)
    manifest = {
        "schema": SCHEMA,
        "ledgers": list(LEDGER_NAMES),
        "window_count": len(input_dirs),
        "governance": {
            "diagnostic_only": True,
            "consumed_evidence_only": True,
            "changes_v7": False,
            "fresh_holdout_opened": False,
        },
    }
    _write(out_dir / "CIBO_COMPLETE_LEDGER_MANIFEST.json", manifest)


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    window = sub.add_parser("window")
    window.add_argument("--journey", type=Path, required=True)
    window.add_argument("--reaction", type=Path, required=True)
    window.add_argument("--nas100", type=Path, required=True)
    window.add_argument("--sp500", type=Path, required=True)
    window.add_argument("--us30", type=Path, required=True)
    window.add_argument("--out-dir", type=Path, required=True)
    combined = sub.add_parser("combine")
    combined.add_argument("input_dirs", nargs="+", type=Path)
    combined.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "window":
        build_window(
            journey_path=args.journey,
            reaction_path=args.reaction,
            nas100_path=args.nas100,
            sp500_path=args.sp500,
            us30_path=args.us30,
            out_dir=args.out_dir,
        )
    else:
        combine_windows(args.input_dirs, args.out_dir)


if __name__ == "__main__":
    main()
