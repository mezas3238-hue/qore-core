"""Independent consumed-only historical market scanner for CIBO Atlas / VT-31.

Atlas studies NAS100, SP500 and US30 market days independently of trader
acceptance, then overlays the definitive tick-corrected trader ledger only as a
POST_OUTCOME_RESEARCH diagnostic label. No fresh evidence is opened and no
candidate/market is selected by this module.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from dataclasses import dataclass, replace
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterable, cast

from qore.infrastructure.market_data import OhlcSnapshot
from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_5_multi_index_research import (
    _day,
    _wall,
    load_market_evidence,
)

MARKETS = ("NAS100", "SP500", "US30")
PARTITIONS = ("r8_fresh", "r6", "r5")
SCHEMA = "qore.cibo_atlas.vt31.historical_market_scanner.v1"


def D(value: object) -> Decimal:
    return Decimal(str(value))


def fmt(value: Decimal | None) -> str | None:
    return None if value is None else format(value, "f")


def quantile(values: list[Decimal], p: Decimal) -> Decimal | None:
    if not values:
        return None
    xs = sorted(values)
    if len(xs) == 1:
        return xs[0]
    position = p * Decimal(len(xs) - 1)
    lo = int(position)
    hi = min(lo + 1, len(xs) - 1)
    frac = position - Decimal(lo)
    return xs[lo] * (Decimal(1) - frac) + xs[hi] * frac


def fraction(numerator: int, denominator: int) -> str | None:
    return None if denominator == 0 else fmt(Decimal(numerator) / Decimal(denominator))


def minute_from_1000(bar: OhlcSnapshot) -> int:
    hour, minute, _ = _wall(bar.opened_at)
    return hour * 60 + minute - 600


def bars_between(
    bars: Iterable[OhlcSnapshot], start: tuple[int, int, int], end: tuple[int, int, int]
) -> tuple[OhlcSnapshot, ...]:
    return tuple(bar for bar in bars if start <= _wall(bar.opened_at) < end)


def contiguous(bars: tuple[OhlcSnapshot, ...]) -> bool:
    return all(
        current.opened_at == previous.closed_at
        for previous, current in zip(bars, bars[1:], strict=False)
    )


def body_fraction(bar: OhlcSnapshot) -> Decimal | None:
    span = D(bar.high) - D(bar.low)
    return None if span <= 0 else abs(D(bar.close) - D(bar.open)) / span


def status_family(status: str) -> str:
    lowered = status.lower()
    if "initial-stop" in lowered:
        return "initial_stop"
    if "protected-stop" in lowered:
        return "protected_stop"
    if "target" in lowered:
        return "target"
    return "other"


@dataclass(frozen=True, slots=True)
class MarketDay:
    partition: str
    market: str
    ny_date: str
    provider: str
    reference_width: Decimal
    session_range_to_reference: Decimal
    lifecycle_range_to_reference: Decimal | None
    lifecycle_complete: bool
    first_breach: str
    first_breach_minute: int | None
    first_breach_depth_ref: Decimal | None
    first_breach_body_fraction: Decimal | None
    both_sides_by_11: bool
    close_reentry_latency_m1: int | None
    opposite_boundary_hit_by_11: bool | None
    opposite_boundary_hit_by_16: bool | None
    max_continuation_depth_ref: Decimal | None
    max_reversal_excursion_ref_by_11: Decimal | None
    max_reversal_excursion_ref_by_16: Decimal | None
    session_close_location_ref: Decimal
    lifecycle_close_location_ref: Decimal | None
    trader_root_count: int = 0
    trader_terminal_count: int = 0
    trader_initial_stop_count: int = 0
    trader_protected_stop_count: int = 0
    trader_target_count: int = 0
    trader_censored_count: int = 0
    trader_no_trade_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "partition": self.partition,
            "market": self.market,
            "ny_date": self.ny_date,
            "provider": self.provider,
            "reference_width": fmt(self.reference_width),
            "session_range_to_reference": fmt(self.session_range_to_reference),
            "lifecycle_range_to_reference": fmt(self.lifecycle_range_to_reference),
            "lifecycle_complete": self.lifecycle_complete,
            "first_breach": self.first_breach,
            "first_breach_minute": self.first_breach_minute,
            "first_breach_depth_ref": fmt(self.first_breach_depth_ref),
            "first_breach_body_fraction": fmt(self.first_breach_body_fraction),
            "both_sides_by_11": self.both_sides_by_11,
            "close_reentry_latency_m1": self.close_reentry_latency_m1,
            "opposite_boundary_hit_by_11": self.opposite_boundary_hit_by_11,
            "opposite_boundary_hit_by_16": self.opposite_boundary_hit_by_16,
            "max_continuation_depth_ref": fmt(self.max_continuation_depth_ref),
            "max_reversal_excursion_ref_by_11": fmt(self.max_reversal_excursion_ref_by_11),
            "max_reversal_excursion_ref_by_16": fmt(self.max_reversal_excursion_ref_by_16),
            "session_close_location_ref": fmt(self.session_close_location_ref),
            "lifecycle_close_location_ref": fmt(self.lifecycle_close_location_ref),
            "trader_root_count": self.trader_root_count,
            "trader_terminal_count": self.trader_terminal_count,
            "trader_initial_stop_count": self.trader_initial_stop_count,
            "trader_protected_stop_count": self.trader_protected_stop_count,
            "trader_target_count": self.trader_target_count,
            "trader_censored_count": self.trader_censored_count,
            "trader_no_trade_count": self.trader_no_trade_count,
        }


def first_breach(
    session: tuple[OhlcSnapshot, ...], ref_high: Decimal, ref_low: Decimal
) -> tuple[str, int | None, OhlcSnapshot | None, bool]:
    high_seen = False
    low_seen = False
    first_side = "none"
    first_index: int | None = None
    first_bar: OhlcSnapshot | None = None
    for index, bar in enumerate(session):
        high = D(bar.high) > ref_high
        low = D(bar.low) < ref_low
        high_seen = high_seen or high
        low_seen = low_seen or low
        if first_index is None and (high or low):
            first_index = index
            first_bar = bar
            first_side = "both-same-bar" if high and low else "high" if high else "low"
    return first_side, first_index, first_bar, high_seen and low_seen


def directional_path(
    side: str,
    path: tuple[OhlcSnapshot, ...],
    ref_high: Decimal,
    ref_low: Decimal,
    ref_width: Decimal,
) -> tuple[Decimal, Decimal, bool]:
    if side == "high":
        continuation = max(D(bar.high) for bar in path) - ref_high
        reversal = ref_high - min(D(bar.low) for bar in path)
        opposite = any(D(bar.low) <= ref_low for bar in path)
    elif side == "low":
        continuation = ref_low - min(D(bar.low) for bar in path)
        reversal = max(D(bar.high) for bar in path) - ref_low
        opposite = any(D(bar.high) >= ref_high for bar in path)
    else:
        raise ValueError("directional_path requires high or low")
    return (
        max(Decimal(0), continuation) / ref_width,
        max(Decimal(0), reversal) / ref_width,
        opposite,
    )


def analyze_day(
    partition: str,
    market: str,
    provider: str,
    local_day: date,
    day_bars: tuple[OhlcSnapshot, ...],
) -> MarketDay | None:
    reference = bars_between(day_bars, (9, 0, 0), (10, 0, 0))
    session = bars_between(day_bars, (10, 0, 0), (11, 0, 0))
    lifecycle = bars_between(day_bars, (10, 0, 0), (16, 0, 0))
    if len(reference) != 60 or len(session) != 60 or not contiguous(reference) or not contiguous(session):
        return None
    ref_high = max(D(bar.high) for bar in reference)
    ref_low = min(D(bar.low) for bar in reference)
    ref_width = ref_high - ref_low
    if ref_width <= 0:
        return None
    side, breach_index, breach_bar, both_sides = first_breach(session, ref_high, ref_low)
    life_complete = len(lifecycle) == 360 and contiguous(lifecycle)
    life_range = (
        (max(D(bar.high) for bar in lifecycle) - min(D(bar.low) for bar in lifecycle)) / ref_width
        if lifecycle
        else None
    )
    depth: Decimal | None = None
    breach_body: Decimal | None = None
    close_reentry: int | None = None
    opposite_11: bool | None = None
    opposite_16: bool | None = None
    continuation: Decimal | None = None
    reversal_11: Decimal | None = None
    reversal_16: Decimal | None = None
    if side in {"high", "low"} and breach_index is not None and breach_bar is not None:
        depth = (
            (D(breach_bar.high) - ref_high) / ref_width
            if side == "high"
            else (ref_low - D(breach_bar.low)) / ref_width
        )
        breach_body = body_fraction(breach_bar)
        path_11 = session[breach_index:]
        continuation, reversal_11, opposite_11 = directional_path(
            side, path_11, ref_high, ref_low, ref_width
        )
        path_16 = lifecycle[breach_index:] if len(lifecycle) > breach_index else path_11
        _, reversal_16, opposite_16 = directional_path(
            side, path_16, ref_high, ref_low, ref_width
        )
        for relative_index, bar in enumerate(path_11):
            close = D(bar.close)
            reentered = close < ref_high if side == "high" else close > ref_low
            if reentered:
                close_reentry = relative_index
                break
    session_high = max(D(bar.high) for bar in session)
    session_low = min(D(bar.low) for bar in session)
    return MarketDay(
        partition=partition,
        market=market,
        ny_date=local_day.isoformat(),
        provider=provider,
        reference_width=ref_width,
        session_range_to_reference=(session_high - session_low) / ref_width,
        lifecycle_range_to_reference=life_range,
        lifecycle_complete=life_complete,
        first_breach=side,
        first_breach_minute=minute_from_1000(breach_bar) if breach_bar is not None else None,
        first_breach_depth_ref=depth,
        first_breach_body_fraction=breach_body,
        both_sides_by_11=both_sides,
        close_reentry_latency_m1=close_reentry,
        opposite_boundary_hit_by_11=opposite_11,
        opposite_boundary_hit_by_16=opposite_16,
        max_continuation_depth_ref=continuation,
        max_reversal_excursion_ref_by_11=reversal_11,
        max_reversal_excursion_ref_by_16=reversal_16,
        session_close_location_ref=(D(session[-1].close) - ref_low) / ref_width,
        lifecycle_close_location_ref=(D(lifecycle[-1].close) - ref_low) / ref_width if lifecycle else None,
    )


def load_partition(partition: str, market: str, path: Path) -> list[MarketDay]:
    series, _, _, _, _, provider = load_market_evidence(path)
    by_day: dict[date, list[OhlcSnapshot]] = defaultdict(list)
    for bar in series:
        by_day[_day(bar.opened_at)].append(bar)
    result: list[MarketDay] = []
    for local_day, bars in sorted(by_day.items()):
        row = analyze_day(partition, market, provider, local_day, tuple(bars))
        if row is not None:
            result.append(row)
    return result


def load_ledger(path: Path) -> dict[str, Any]:
    payload = cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))
    if payload.get("schema") != "qore.vt31.tick_corrected.consumed_ledger.v2":
        raise ValueError("historical scanner requires definitive ledger v2")
    if payload.get("research_only") is not True or payload.get("opens_new_holdout") is not False:
        raise ValueError("ledger governance guard")
    roots = payload.get("roots")
    if not isinstance(roots, list) or len(roots) != 780:
        raise ValueError("definitive ledger must contain 780 roots")
    return payload


def overlay_trader(rows: list[MarketDay], ledger: dict[str, Any]) -> list[MarketDay]:
    by_key: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for raw in cast(list[object], ledger["roots"]):
        if not isinstance(raw, dict):
            raise ValueError("malformed ledger root")
        root = cast(dict[str, Any], raw)
        by_key[(str(root["market"]), str(root["ny_date"]))].append(root)
    result: list[MarketDay] = []
    for row in rows:
        roots = by_key.get((row.market, row.ny_date), [])
        classes = Counter(str(root["classification"]) for root in roots)
        terminal_families = Counter(
            status_family(str(root.get("terminal_status", "")))
            for root in roots
            if root.get("classification") == "terminal"
        )
        result.append(
            replace(
                row,
                trader_root_count=len(roots),
                trader_terminal_count=classes.get("terminal", 0),
                trader_initial_stop_count=terminal_families.get("initial_stop", 0),
                trader_protected_stop_count=terminal_families.get("protected_stop", 0),
                trader_target_count=terminal_families.get("target", 0),
                trader_censored_count=classes.get("censored", 0),
                trader_no_trade_count=classes.get("no_trade", 0),
            )
        )
    return result


def summarize(rows: list[MarketDay]) -> dict[str, Any]:
    if not rows:
        return {"market_day_count": 0}
    directional = [row for row in rows if row.first_breach in {"high", "low"}]
    depth = [cast(Decimal, row.first_breach_depth_ref) for row in directional if row.first_breach_depth_ref is not None]
    reverse_11 = [
        cast(Decimal, row.max_reversal_excursion_ref_by_11)
        for row in directional
        if row.max_reversal_excursion_ref_by_11 is not None
    ]
    reverse_16 = [
        cast(Decimal, row.max_reversal_excursion_ref_by_16)
        for row in directional
        if row.max_reversal_excursion_ref_by_16 is not None
    ]
    return {
        "market_day_count": len(rows),
        "from": min(row.ny_date for row in rows),
        "to": max(row.ny_date for row in rows),
        "partition_counts": dict(sorted(Counter(row.partition for row in rows).items())),
        "provider_counts": dict(sorted(Counter(row.provider for row in rows).items())),
        "first_breach_counts": dict(sorted(Counter(row.first_breach for row in rows).items())),
        "directional_breach_rate": fraction(len(directional), len(rows)),
        "both_sides_by_11_rate": fraction(sum(row.both_sides_by_11 for row in rows), len(rows)),
        "lifecycle_complete_rate": fraction(sum(row.lifecycle_complete for row in rows), len(rows)),
        "opposite_boundary_hit_by_11_rate": fraction(
            sum(row.opposite_boundary_hit_by_11 is True for row in directional), len(directional)
        ),
        "opposite_boundary_hit_by_16_rate": fraction(
            sum(row.opposite_boundary_hit_by_16 is True for row in directional), len(directional)
        ),
        "reference_width_p50": fmt(quantile([row.reference_width for row in rows], Decimal("0.5"))),
        "session_range_to_reference_p50": fmt(
            quantile([row.session_range_to_reference for row in rows], Decimal("0.5"))
        ),
        "raid_depth_ref_p50": fmt(quantile(depth, Decimal("0.5"))),
        "reversal_excursion_ref_by_11_p50": fmt(quantile(reverse_11, Decimal("0.5"))),
        "reversal_excursion_ref_by_16_p50": fmt(quantile(reverse_16, Decimal("0.5"))),
        "trader_root_count": sum(row.trader_root_count for row in rows),
        "trader_terminal_count": sum(row.trader_terminal_count for row in rows),
        "trader_initial_stop_count": sum(row.trader_initial_stop_count for row in rows),
        "trader_protected_stop_count": sum(row.trader_protected_stop_count for row in rows),
        "trader_target_count": sum(row.trader_target_count for row in rows),
        "trader_censored_count": sum(row.trader_censored_count for row in rows),
        "trader_no_trade_count": sum(row.trader_no_trade_count for row in rows),
    }


def outcome_contrasts(rows: list[MarketDay]) -> dict[str, Any]:
    predicates = {
        "initial_stop": lambda row: row.trader_initial_stop_count > 0,
        "protected_stop": lambda row: row.trader_protected_stop_count > 0,
        "target": lambda row: row.trader_target_count > 0,
    }
    result: dict[str, Any] = {}
    for name, predicate in predicates.items():
        group = [row for row in rows if predicate(row)]
        directional = [row for row in group if row.first_breach in {"high", "low"}]
        reversal = [
            cast(Decimal, row.max_reversal_excursion_ref_by_16)
            for row in directional
            if row.max_reversal_excursion_ref_by_16 is not None
        ]
        result[name] = {
            "day_count": len(group),
            "directional_breach_count": len(directional),
            "both_sides_by_11_rate": fraction(sum(row.both_sides_by_11 for row in group), len(group)),
            "opposite_boundary_hit_by_11_rate": fraction(
                sum(row.opposite_boundary_hit_by_11 is True for row in directional), len(directional)
            ),
            "opposite_boundary_hit_by_16_rate": fraction(
                sum(row.opposite_boundary_hit_by_16 is True for row in directional), len(directional)
            ),
            "post_breach_reversal_excursion_ref_by_16_p50": fmt(quantile(reversal, Decimal("0.5"))),
        }
    return result


def cross_index(rows: list[MarketDay]) -> dict[str, Any]:
    by_day: dict[str, dict[str, MarketDay]] = defaultdict(dict)
    for row in rows:
        by_day[row.ny_date][row.market] = row
    cohorts: list[dict[str, Any]] = []
    for ny_date, markets in sorted(by_day.items()):
        if set(markets) != set(MARKETS):
            continue
        directions = [markets[market].first_breach for market in MARKETS]
        directional = [value for value in directions if value in {"high", "low"}]
        if len(directional) == 3 and len(set(directional)) == 1:
            state = f"unanimous-{directional[0]}"
        elif len(directional) == 3:
            state = "three-directional-conflict"
        else:
            state = "mixed-or-incomplete"
        cohorts.append(
            {
                "ny_date": ny_date,
                "raid_breadth": len(directional),
                "direction_state": state,
                "trader_active_market_count": sum(markets[m].trader_root_count > 0 for m in MARKETS),
                "trader_initial_stop_count": sum(markets[m].trader_initial_stop_count for m in MARKETS),
                "trader_target_count": sum(markets[m].trader_target_count for m in MARKETS),
            }
        )
    return {
        "complete_three_market_day_count": len(cohorts),
        "raid_breadth_counts": dict(sorted(Counter(row["raid_breadth"] for row in cohorts).items())),
        "direction_state_counts": dict(
            sorted(Counter(row["direction_state"] for row in cohorts).items())
        ),
        "cohorts": cohorts,
    }


def write_csv(path: Path, rows: list[MarketDay]) -> None:
    records = [row.to_dict() for row in rows]
    if not records:
        raise ValueError("Atlas market-day matrix cannot be empty")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)


def build(args: argparse.Namespace) -> dict[str, Any]:
    ledger = load_ledger(cast(Path, args.ledger))
    raw_rows: list[MarketDay] = []
    for partition in PARTITIONS:
        for market in MARKETS:
            raw_rows.extend(
                load_partition(
                    partition,
                    market,
                    cast(Path, getattr(args, f"{partition}_{market.lower()}")),
                )
            )
    unique: dict[tuple[str, str], MarketDay] = {}
    for row in raw_rows:
        key = (row.market, row.ny_date)
        if key in unique:
            raise ValueError(f"overlapping consumed market day {key}")
        unique[key] = row
    rows = overlay_trader(sorted(unique.values(), key=lambda row: (row.ny_date, row.market)), ledger)
    by_market = {market: [row for row in rows if row.market == market] for market in MARKETS}
    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "research_only": True,
        "selection_prohibited": True,
        "opens_new_holdout": False,
        "candidate_status": "NO_R9_NOT_CERTIFIED",
        "live_authorized": False,
        "production_authorized": False,
        "methodology_family": "ttrades-am-silver-bullet",
        "market_universe": list(MARKETS),
        "source_partitions": list(PARTITIONS),
        "independent_market_day_count": len(rows),
        "market_summary": {market: summarize(by_market[market]) for market in MARKETS},
        "trader_outcome_market_contrasts": {
            market: outcome_contrasts(by_market[market]) for market in MARKETS
        },
        "cross_index": cross_index(rows),
        "timing_contract": {
            "market_day_features": "independent-market-observation",
            "trader_outcomes": "post-outcome-research-label-only",
        },
        "interpretation_constraints": [
            "market-day rows are independent of trader acceptance",
            "trader outcomes are post-outcome labels only",
            "no positive contrast is a candidate rule",
            "no fresh holdout was opened",
            "specialist changes require causal hypothesis and leakage-free walk-forward",
        ],
    }
    output_dir = cast(Path, args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "cibo-atlas-vt31-historical-market-scanner.json").write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    write_csv(output_dir / "cibo-atlas-vt31-market-day-matrix.csv", rows)
    return payload


def self_test() -> None:
    assert status_family("initial-stop-after-fill") == "initial_stop"
    assert status_family("terminal-protected-stop") == "protected_stop"
    assert status_family("fixed-2r-target") == "target"
    assert quantile([Decimal(1), Decimal(3)], Decimal("0.5")) == Decimal(2)
    assert fraction(1, 4) == "0.25"
    print("CIBO Atlas historical scanner self-test PASS")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--ledger", type=Path)
    parser.add_argument("--output-dir", type=Path)
    for partition in PARTITIONS:
        for market in MARKETS:
            parser.add_argument(f"--{partition.replace('_', '-')}-{market.lower()}", type=Path)
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    required = [args.ledger, args.output_dir]
    required.extend(
        getattr(args, f"{partition}_{market.lower()}")
        for partition in PARTITIONS
        for market in MARKETS
    )
    if any(value is None for value in required):
        parser.error("ledger, output-dir and all nine market evidence paths are required")
    payload = build(args)
    print(
        json.dumps(
            {
                "independent_market_day_count": payload["independent_market_day_count"],
                "market_summary": payload["market_summary"],
                "cross_index_complete_days": payload["cross_index"]["complete_three_market_day_count"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
