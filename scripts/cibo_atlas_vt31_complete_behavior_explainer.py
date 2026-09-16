"""Complete consumed-only behavior explainer for CIBO Atlas / VT-31.

Explains, without selecting a trader rule:
- what market structure/behavior appeared before the move;
- New York timing and expansion latency;
- whether the frozen trader had already exited;
- target geometry versus the opposite 09:00 boundary and post-boundary extension;
- weekday/day-regime behavior;
- pre-entry rotation/compression versus directional build;
- market-specific contrasts for NAS100, SP500 and US30.

All labels are descriptive research over already-consumed evidence. Post-outcome
fields cannot be used as live/pre-entry features. No fresh holdout is opened.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from statistics import median
from typing import Any, Iterable, cast
from zoneinfo import ZoneInfo

from qore.infrastructure.market_data import OhlcSnapshot
from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_5_multi_index_research import (
    _day,
    _wall,
    load_market_evidence,
)

MARKETS = ("NAS100", "SP500", "US30")
PARTITIONS = ("r5", "r6", "r8_fresh")
NY = ZoneInfo("America/New_York")
SCHEMA = "qore.cibo_atlas.vt31.complete_behavior_explainer.v1"
TARGET_LADDER_REF = tuple(Decimal(str(v)) for v in (0, 0.25, 0.5, 1, 1.5, 2))
TARGET_LADDER_R = tuple(Decimal(str(v)) for v in (1, 1.5, 2, 2.5, 3, 4, 5))


def d(value: object) -> Decimal:
    return Decimal(str(value))


def fmt(value: Decimal | None) -> str | None:
    return None if value is None else format(value, "f")


def quantile(values: list[Decimal], p: Decimal) -> Decimal | None:
    if not values:
        return None
    xs = sorted(values)
    if len(xs) == 1:
        return xs[0]
    pos = p * Decimal(len(xs) - 1)
    lo = int(pos)
    hi = min(lo + 1, len(xs) - 1)
    weight = pos - Decimal(lo)
    return xs[lo] * (Decimal(1) - weight) + xs[hi] * weight


def fraction(numerator: int, denominator: int) -> str | None:
    return None if denominator == 0 else fmt(Decimal(numerator) / Decimal(denominator))


def bars_between(
    bars: Iterable[OhlcSnapshot], start: tuple[int, int, int], end: tuple[int, int, int]
) -> tuple[OhlcSnapshot, ...]:
    return tuple(bar for bar in bars if start <= _wall(bar.opened_at) < end)


def body_fraction(bar: OhlcSnapshot) -> Decimal:
    span = d(bar.high) - d(bar.low)
    return Decimal(0) if span <= 0 else abs(d(bar.close) - d(bar.open)) / span


def bar_range(bar: OhlcSnapshot) -> Decimal:
    return max(Decimal(0), d(bar.high) - d(bar.low))


def local_swing_indices(path: tuple[OhlcSnapshot, ...]) -> tuple[list[int], list[int]]:
    highs: list[int] = []
    lows: list[int] = []
    for i in range(2, len(path) - 2):
        high = d(path[i].high)
        low = d(path[i].low)
        if high >= max(d(path[i - 2].high), d(path[i - 1].high)) and high > max(
            d(path[i + 1].high), d(path[i + 2].high)
        ):
            highs.append(i)
        if low <= min(d(path[i - 2].low), d(path[i - 1].low)) and low < min(
            d(path[i + 1].low), d(path[i + 2].low)
        ):
            lows.append(i)
    return highs, lows


def fvg_events(path: tuple[OhlcSnapshot, ...]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for i in range(2, len(path)):
        left = path[i - 2]
        current = path[i]
        if d(current.low) > d(left.high):
            events.append(
                {
                    "side": "bullish",
                    "at": current.opened_at.isoformat(),
                    "lower": fmt(d(left.high)),
                    "upper": fmt(d(current.low)),
                }
            )
        if d(current.high) < d(left.low):
            events.append(
                {
                    "side": "bearish",
                    "at": current.opened_at.isoformat(),
                    "lower": fmt(d(current.high)),
                    "upper": fmt(d(left.low)),
                }
            )
    return events


def local_sweep_events(path: tuple[OhlcSnapshot, ...]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    highs, lows = local_swing_indices(path)
    for i in range(len(path)):
        prior_highs = [idx for idx in highs if idx <= i - 2]
        prior_lows = [idx for idx in lows if idx <= i - 2]
        if prior_highs:
            level = d(path[prior_highs[-1]].high)
            if d(path[i].high) > level and d(path[i].close) < level:
                events.append(
                    {"side": "bearish-reclaim", "at": path[i].opened_at.isoformat(), "level": fmt(level)}
                )
        if prior_lows:
            level = d(path[prior_lows[-1]].low)
            if d(path[i].low) < level and d(path[i].close) > level:
                events.append(
                    {"side": "bullish-reclaim", "at": path[i].opened_at.isoformat(), "level": fmt(level)}
                )
    return events


def displacement_events(path: tuple[OhlcSnapshot, ...]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for i in range(5, len(path)):
        recent = [bar_range(bar) for bar in path[i - 5 : i]]
        baseline = d(median(recent)) if recent else Decimal(0)
        current_range = bar_range(path[i])
        if baseline <= 0:
            continue
        if body_fraction(path[i]) >= Decimal("0.70") and current_range >= baseline * Decimal("1.20"):
            side = "bullish" if d(path[i].close) > d(path[i].open) else "bearish"
            events.append(
                {
                    "side": side,
                    "at": path[i].opened_at.isoformat(),
                    "body_fraction": fmt(body_fraction(path[i])),
                    "range_vs_prior5_median": fmt(current_range / baseline),
                }
            )
    return events


def path_efficiency(path: tuple[OhlcSnapshot, ...]) -> Decimal | None:
    if len(path) < 2:
        return None
    total = Decimal(0)
    prior = d(path[0].open)
    for bar in path:
        close = d(bar.close)
        total += abs(close - prior)
        prior = close
    if total <= 0:
        return Decimal(0)
    net = abs(d(path[-1].close) - d(path[0].open))
    return net / total


def overlap_rate(path: tuple[OhlcSnapshot, ...]) -> Decimal | None:
    if len(path) < 2:
        return None
    overlaps = 0
    comparisons = 0
    for previous, current in zip(path, path[1:], strict=False):
        comparisons += 1
        if min(d(previous.high), d(current.high)) >= max(d(previous.low), d(current.low)):
            overlaps += 1
    return Decimal(overlaps) / Decimal(comparisons) if comparisons else None


def pre_entry_state(path: tuple[OhlcSnapshot, ...]) -> dict[str, Any]:
    efficiency = path_efficiency(path)
    overlap = overlap_rate(path)
    highs, lows = local_swing_indices(path)
    fvgs = fvg_events(path)
    sweeps = local_sweep_events(path)
    displacements = displacement_events(path)
    label = "insufficient"
    if efficiency is not None and overlap is not None:
        if efficiency <= Decimal("0.35") and overlap >= Decimal("0.60"):
            label = "rotation-compression-proxy"
        elif efficiency >= Decimal("0.65"):
            label = "directional-build-proxy"
        else:
            label = "mixed-build-proxy"
    full_range = (
        max(d(bar.high) for bar in path) - min(d(bar.low) for bar in path) if path else Decimal(0)
    )
    last5 = path[-5:]
    last5_range = (
        max(d(bar.high) for bar in last5) - min(d(bar.low) for bar in last5) if last5 else Decimal(0)
    )
    return {
        "bar_count": len(path),
        "behavior_proxy": label,
        "path_efficiency": fmt(efficiency),
        "overlap_rate": fmt(overlap),
        "two_by_two_swing_high_count": len(highs),
        "two_by_two_swing_low_count": len(lows),
        "fvg_count": len(fvgs),
        "local_sweep_reclaim_count": len(sweeps),
        "displacement_event_count": len(displacements),
        "last5_range_to_full_pre_entry_range": fmt(last5_range / full_range if full_range > 0 else None),
        "last_fvg": fvgs[-1] if fvgs else None,
        "last_local_sweep_reclaim": sweeps[-1] if sweeps else None,
        "last_displacement": displacements[-1] if displacements else None,
        "interpretation": "compression/accumulation is a geometric proxy, not inferred market intent",
    }


def first_breach(
    session: tuple[OhlcSnapshot, ...], ref_high: Decimal, ref_low: Decimal
) -> tuple[str, int | None]:
    for i, bar in enumerate(session):
        high = d(bar.high) > ref_high
        low = d(bar.low) < ref_low
        if high and low:
            return "both-same-bar", i
        if high:
            return "high", i
        if low:
            return "low", i
    return "none", None


def expansion_strength(value: Decimal) -> str:
    if value <= Decimal("1.25"):
        return "contained"
    if value <= Decimal("2"):
        return "moderate"
    if value <= Decimal("3"):
        return "strong"
    return "extreme"


def analyze_market_day(
    partition: str,
    market: str,
    provider: str,
    day_bars: tuple[OhlcSnapshot, ...],
) -> dict[str, Any] | None:
    reference = bars_between(day_bars, (9, 0, 0), (10, 0, 0))
    session = bars_between(day_bars, (10, 0, 0), (11, 0, 0))
    lifecycle = bars_between(day_bars, (10, 0, 0), (16, 0, 0))
    if len(reference) != 60 or len(session) != 60 or not lifecycle:
        return None
    ref_high = max(d(bar.high) for bar in reference)
    ref_low = min(d(bar.low) for bar in reference)
    width = ref_high - ref_low
    if width <= 0:
        return None
    side, breach_index = first_breach(session, ref_high, ref_low)
    life_high = max(d(bar.high) for bar in lifecycle)
    life_low = min(d(bar.low) for bar in lifecycle)
    high_extension = max(Decimal(0), life_high - ref_high) / width
    low_extension = max(Decimal(0), ref_low - life_low) / width
    breached_high = high_extension > 0
    breached_low = low_extension > 0
    if not breached_high and not breached_low:
        regime = "inside-reference"
    elif breached_high and breached_low:
        regime = "two-sided-expansion"
    elif breached_high:
        regime = "one-sided-high-expansion"
    else:
        regime = "one-sided-low-expansion"
    life_range_ref = (life_high - life_low) / width
    objective_at: str | None = None
    post_boundary_extension_ref: Decimal | None = None
    breach_at: str | None = None
    breach_to_objective: int | None = None
    objective_to_farthest: int | None = None
    if side in {"high", "low"} and breach_index is not None:
        breach_bar = session[breach_index]
        breach_at = breach_bar.opened_at.isoformat()
        path = tuple(bar for bar in lifecycle if bar.opened_at >= breach_bar.opened_at)
        objective_index: int | None = None
        for i, bar in enumerate(path):
            hit = d(bar.low) <= ref_low if side == "high" else d(bar.high) >= ref_high
            if hit:
                objective_index = i
                break
        if objective_index is not None:
            objective = path[objective_index]
            objective_at = objective.opened_at.isoformat()
            breach_to_objective = int((objective.opened_at - breach_bar.opened_at).total_seconds() // 60)
            tail = path[objective_index:]
            if side == "high":
                farthest_index = min(range(len(tail)), key=lambda i: d(tail[i].low))
                post_boundary_extension_ref = max(Decimal(0), ref_low - d(tail[farthest_index].low)) / width
            else:
                farthest_index = max(range(len(tail)), key=lambda i: d(tail[i].high))
                post_boundary_extension_ref = max(Decimal(0), d(tail[farthest_index].high) - ref_high) / width
            objective_to_farthest = int(
                (tail[farthest_index].opened_at - objective.opened_at).total_seconds() // 60
            )
    local_day = _day(reference[0].opened_at)
    return {
        "partition": partition,
        "market": market,
        "provider": provider,
        "ny_date": str(local_day),
        "weekday": local_day.strftime("%A"),
        "reference_width": fmt(width),
        "reference_high": fmt(ref_high),
        "reference_low": fmt(ref_low),
        "first_breach": side,
        "first_breach_at": breach_at,
        "day_regime": regime,
        "lifecycle_range_ref": fmt(life_range_ref),
        "expansion_strength": expansion_strength(life_range_ref),
        "high_extension_ref": fmt(high_extension),
        "low_extension_ref": fmt(low_extension),
        "opposite_boundary_hit_by_16": objective_at is not None,
        "opposite_boundary_at": objective_at,
        "breach_to_opposite_minutes": breach_to_objective,
        "post_boundary_extension_ref": fmt(post_boundary_extension_ref),
        "opposite_to_farthest_extension_minutes": objective_to_farthest,
        "post_boundary_ladder": {
            fmt(level): bool(post_boundary_extension_ref is not None and post_boundary_extension_ref >= level)
            for level in TARGET_LADDER_REF
        },
    }


def load_market_days(paths: dict[tuple[str, str], Path]) -> tuple[dict[tuple[str, str], tuple[OhlcSnapshot, ...]], list[dict[str, Any]]]:
    bars_by_key: dict[tuple[str, str], tuple[OhlcSnapshot, ...]] = {}
    rows: list[dict[str, Any]] = []
    for partition in PARTITIONS:
        for market in MARKETS:
            series, _, _, _, _, provider = load_market_evidence(paths[(partition, market)])
            grouped: dict[object, list[OhlcSnapshot]] = defaultdict(list)
            for bar in series:
                grouped[_day(bar.opened_at)].append(bar)
            for local_day, bars in sorted(grouped.items()):
                key = (market, str(local_day))
                if key in bars_by_key:
                    raise ValueError(f"overlapping consumed market day {key}")
                frozen = tuple(bars)
                bars_by_key[key] = frozen
                row = analyze_market_day(partition, market, provider, frozen)
                if row is not None:
                    rows.append(row)
    return bars_by_key, rows


def load_json(path: Path, schema: str) -> dict[str, Any]:
    payload = cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))
    if payload.get("schema") != schema:
        raise ValueError(f"schema mismatch: expected {schema}, got {payload.get('schema')}")
    if payload.get("research_only") is not True or payload.get("opens_new_holdout") is not False:
        raise ValueError("research governance guard failed")
    return payload


def summarize_numeric(rows: list[dict[str, Any]], field: str) -> dict[str, Any]:
    values = [d(row[field]) for row in rows if row.get(field) not in {None, ""}]
    return {
        "n": len(values),
        "p25": fmt(quantile(values, Decimal("0.25"))),
        "p50": fmt(quantile(values, Decimal("0.50"))),
        "p75": fmt(quantile(values, Decimal("0.75"))),
        "p90": fmt(quantile(values, Decimal("0.90"))),
    }


def day_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    objective = [row for row in rows if row["opposite_boundary_hit_by_16"]]
    return {
        "n": len(rows),
        "regimes": dict(sorted(Counter(str(row["day_regime"]) for row in rows).items())),
        "expansion_strength": dict(sorted(Counter(str(row["expansion_strength"]) for row in rows).items())),
        "opposite_boundary_hit_rate": fraction(len(objective), len(rows)),
        "lifecycle_range_ref": summarize_numeric(rows, "lifecycle_range_ref"),
        "post_boundary_extension_ref": summarize_numeric(objective, "post_boundary_extension_ref"),
        "breach_to_opposite_minutes": summarize_numeric(objective, "breach_to_opposite_minutes"),
        "post_boundary_hit_rates": {
            fmt(level): fraction(
                sum(d(row["post_boundary_extension_ref"]) >= level for row in objective), len(objective)
            )
            for level in TARGET_LADDER_REF
        },
    }


def grouped_summary(rows: list[dict[str, Any]], field: str) -> dict[str, Any]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[str(row[field])].append(row)
    return {key: day_summary(value) for key, value in sorted(groups.items())}


def behavior_taxonomy(
    bars: tuple[OhlcSnapshot, ...], signal_at: datetime, objective_at: datetime | None
) -> dict[str, Any]:
    pre = tuple(
        bar
        for bar in bars
        if (10, 0, 0) <= _wall(bar.opened_at) and bar.opened_at < signal_at
    )
    end = objective_at or datetime.combine(signal_at.date(), datetime.max.time(), tzinfo=NY)
    post = tuple(bar for bar in bars if signal_at <= bar.opened_at <= end)
    fvgs = fvg_events(post)
    sweeps = local_sweep_events(post)
    displacements = displacement_events(post)
    highs, lows = local_swing_indices(post)
    labels: list[str] = ["local-2x2-swing"] if highs or lows else []
    if fvgs:
        labels.append("new-post-entry-fvg")
    if sweeps:
        labels.append("new-local-sweep-reclaim")
    if displacements:
        labels.append("new-displacement-event")
    return {
        "pre_entry": pre_entry_state(pre),
        "post_entry_until_objective": {
            "bar_count": len(post),
            "cibo_behavior_labels": labels or ["none-of-current-cibo-taxonomy"],
            "new_fvg_count": len(fvgs),
            "local_sweep_reclaim_count": len(sweeps),
            "displacement_event_count": len(displacements),
            "two_by_two_swing_high_count": len(highs),
            "two_by_two_swing_low_count": len(lows),
            "last_new_fvg": fvgs[-1] if fvgs else None,
            "last_local_sweep_reclaim": sweeps[-1] if sweeps else None,
            "last_displacement": displacements[-1] if displacements else None,
        },
    }


def enrich_roots(
    forensics: dict[str, Any],
    attribution: dict[str, Any],
    predeparture: dict[str, Any],
    bars_by_key: dict[tuple[str, str], tuple[OhlcSnapshot, ...]],
    day_by_key: dict[tuple[str, str], dict[str, Any]],
) -> list[dict[str, Any]]:
    attr = {str(row["root_id"]): row for row in cast(list[dict[str, Any]], attribution["rows"])}
    dep = {
        str(row["root_id"]): row
        for row in cast(list[dict[str, Any]], predeparture["demonstrated_root_rows"])
    }
    roots: list[dict[str, Any]] = []
    for source in cast(list[dict[str, Any]], forensics["rows"]):
        root_id = str(source["root_id"])
        key = (str(source["market"]), str(source["ny_date"]))
        day = day_by_key.get(key)
        bars = bars_by_key.get(key)
        if day is None or bars is None:
            raise ValueError(f"terminal root missing market day {root_id}")
        signal_at = datetime.fromisoformat(str(source["signal_at"]))
        if signal_at.tzinfo is None:
            raise ValueError("signal timestamp must be timezone-aware")
        objective_at = (
            datetime.fromisoformat(str(day["opposite_boundary_at"]))
            if day.get("opposite_boundary_at")
            else None
        )
        taxonomy = behavior_taxonomy(bars, signal_at, objective_at)
        a = attr[root_id]
        demonstrated = a.get("demonstrated_path_fact") == "demonstrated_exit_before_eventual_source_objective"
        risk_to_ref = d(source["risk_to_reference"])
        post_ref = d(day["post_boundary_extension_ref"]) if day.get("post_boundary_extension_ref") else None
        post_r = post_ref / risk_to_ref if post_ref is not None and risk_to_ref > 0 else None
        boundary_r = d(source["opposing_liquidity_r"])
        potential_r = boundary_r + post_r if post_r is not None else None
        dep_row = dep.get(root_id)
        row = {
            "root_id": root_id,
            "partition": source["partition"],
            "market": source["market"],
            "ny_date": source["ny_date"],
            "weekday": day["weekday"],
            "side": source["side"],
            "entry_family": source["entry_family"],
            "terminal_status": source["terminal_status"],
            "terminal_r": source["terminal_r"],
            "signal_at": source["signal_at"],
            "signal_minute": source["signal_minute"],
            "risk_to_reference": source["risk_to_reference"],
            "fixed_target_r": "2",
            "opposite_boundary_r_from_entry": source["opposing_liquidity_r"],
            "fixed_2r_is_before_opposite_boundary": boundary_r > Decimal(2),
            "opposite_boundary_minus_fixed_target_r": fmt(boundary_r - Decimal(2)),
            "opposite_boundary_hit_by_16": day["opposite_boundary_hit_by_16"],
            "post_boundary_extension_ref": day["post_boundary_extension_ref"],
            "post_boundary_extension_r_from_setup": fmt(post_r),
            "market_potential_r_to_farthest_by_16_if_objective_hit": fmt(potential_r),
            "day_regime": day["day_regime"],
            "expansion_strength": day["expansion_strength"],
            "lifecycle_range_ref": day["lifecycle_range_ref"],
            "trader_already_stopped_before_eventual_source_objective": demonstrated,
            "path_fact": a["demonstrated_path_fact"],
            "pre_entry_behavior": taxonomy["pre_entry"],
            "post_entry_behavior": taxonomy["post_entry_until_objective"],
            "pre_departure_source_structure": dep_row.get("structure_signature") if dep_row else None,
            "pre_departure_pivot_at": dep_row.get("pivot_at") if dep_row else None,
            "pre_departure_objective_at": dep_row.get("objective_at") if dep_row else day.get("opposite_boundary_at"),
            "pre_departure_pivot_to_objective_minutes": (
                int(
                    (
                        datetime.fromisoformat(str(dep_row["objective_at"]))
                        - datetime.fromisoformat(str(dep_row["pivot_at"]))
                    ).total_seconds()
                    // 60
                )
                if dep_row
                else None
            ),
        }
        roots.append(row)
    if len(roots) != 618:
        raise AssertionError(f"expected 618 terminal roots, got {len(roots)}")
    return roots


def root_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    objective = [row for row in rows if row["opposite_boundary_hit_by_16"]]
    stopped_then_objective = [
        row for row in rows if row["trader_already_stopped_before_eventual_source_objective"]
    ]
    compression = Counter(str(row["pre_entry_behavior"]["behavior_proxy"]) for row in rows)
    structures = Counter(
        label
        for row in rows
        for label in cast(list[str], row["post_entry_behavior"]["cibo_behavior_labels"])
    )
    boundary_values = [d(row["opposite_boundary_r_from_entry"]) for row in rows]
    potential = [
        d(row["market_potential_r_to_farthest_by_16_if_objective_hit"])
        for row in rows
        if row.get("market_potential_r_to_farthest_by_16_if_objective_hit") is not None
    ]
    return {
        "n": len(rows),
        "terminal_status": dict(sorted(Counter(str(row["terminal_status"]) for row in rows).items())),
        "day_regime": dict(sorted(Counter(str(row["day_regime"]) for row in rows).items())),
        "pre_entry_behavior_proxy": dict(sorted(compression.items())),
        "post_entry_cibo_behavior_labels": dict(sorted(structures.items())),
        "opposite_boundary_hit_rate": fraction(len(objective), len(rows)),
        "stopped_before_eventual_source_objective_count": len(stopped_then_objective),
        "stopped_before_eventual_source_objective_rate": fraction(len(stopped_then_objective), len(rows)),
        "opposite_boundary_r_from_entry": {
            "p25": fmt(quantile(boundary_values, Decimal("0.25"))),
            "p50": fmt(quantile(boundary_values, Decimal("0.50"))),
            "p75": fmt(quantile(boundary_values, Decimal("0.75"))),
        },
        "market_potential_r_to_farthest_by_16_if_objective_hit": {
            "n": len(potential),
            "p25": fmt(quantile(potential, Decimal("0.25"))),
            "p50": fmt(quantile(potential, Decimal("0.50"))),
            "p75": fmt(quantile(potential, Decimal("0.75"))),
        },
        "fixed_target_geometry": {
            "fixed_target_r": "2",
            "source_boundary_farther_than_2r_count": sum(
                bool(row["fixed_2r_is_before_opposite_boundary"]) for row in rows
            ),
            "source_boundary_farther_than_2r_rate": fraction(
                sum(bool(row["fixed_2r_is_before_opposite_boundary"]) for row in rows), len(rows)
            ),
        },
        "target_ladder_market_potential_hit_rate": {
            fmt(level): fraction(sum(value >= level for value in potential), len(potential))
            for level in TARGET_LADDER_R
        },
    }


def build(args: argparse.Namespace) -> dict[str, Any]:
    forensics = load_json(
        cast(Path, args.forensics), "qore.vt31.tick_corrected.deep_forensics.v1"
    )
    attribution = load_json(
        cast(Path, args.attribution), "qore.cibo_atlas.vt31.root_cause_attribution.v1"
    )
    predeparture = load_json(
        cast(Path, args.predeparture), "qore.cibo_atlas.vt31.pre_departure_structure_lab.v1"
    )
    paths = {
        (partition, market): cast(Path, getattr(args, f"{partition}_{market.lower()}"))
        for partition in PARTITIONS
        for market in MARKETS
    }
    bars_by_key, market_days = load_market_days(paths)
    day_by_key = {(str(row["market"]), str(row["ny_date"])): row for row in market_days}
    if len(day_by_key) != len(market_days):
        raise ValueError("duplicate analyzed market day")
    roots = enrich_roots(forensics, attribution, predeparture, bars_by_key, day_by_key)
    by_market = {market: [row for row in market_days if row["market"] == market] for market in MARKETS}
    root_by_market = {market: [row for row in roots if row["market"] == market] for market in MARKETS}
    weekday_market = {
        market: grouped_summary(by_market[market], "weekday") for market in MARKETS
    }
    regime_market = {
        market: grouped_summary(by_market[market], "day_regime") for market in MARKETS
    }
    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "research_only": True,
        "selection_prohibited": True,
        "opens_new_holdout": False,
        "candidate_status": "NO_R9_NOT_CERTIFIED",
        "live_authorized": False,
        "production_authorized": False,
        "timezone": "America/New_York",
        "market_day_count": len(market_days),
        "terminal_root_count": len(roots),
        "demonstrated_stop_before_source_objective_count": sum(
            bool(row["trader_already_stopped_before_eventual_source_objective"]) for row in roots
        ),
        "market_behavior": {market: day_summary(by_market[market]) for market in MARKETS},
        "weekday_behavior_by_market": weekday_market,
        "day_regime_behavior_by_market": regime_market,
        "trader_behavior": {market: root_summary(root_by_market[market]) for market in MARKETS},
        "all_trader_roots": root_summary(roots),
        "market_days": market_days,
        "roots": roots,
        "explanation_contract": {
            "structure": "source pre-departure structure plus CIBO-native post-entry FVG/sweep/displacement/local-swing taxonomy",
            "time": "America/New_York DST-aware",
            "target": "fixed 2R versus opposite 09:00 boundary and observed extension beyond that boundary",
            "day_context": "weekday plus structural day regime plus normalized lifecycle expansion strength",
            "pre_entry": "M1 path efficiency, overlap, swing/FVG/sweep/displacement counts before signal",
            "trader_overlay": "terminal outcome and demonstrated stop-before-eventual-source-objective are post-outcome labels only",
        },
        "interpretation_constraints": [
            "target geometry does not by itself prove that a farther target is economically superior",
            "compression/accumulation is reported as a geometric proxy and not inferred market intent",
            "post-entry structures and eventual objectives are diagnostic labels and cannot be live entry features",
            "weekday frequencies cannot become trading filters without leakage-free causal walk-forward",
            "no fresh holdout was opened and no candidate was promoted",
        ],
    }
    output_dir = cast(Path, args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "cibo-atlas-vt31-complete-behavior-explainer.json").write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    compact = {
        "market_day_count": payload["market_day_count"],
        "terminal_root_count": payload["terminal_root_count"],
        "demonstrated_stop_before_source_objective_count": payload[
            "demonstrated_stop_before_source_objective_count"
        ],
        "market_behavior": payload["market_behavior"],
        "trader_behavior": payload["trader_behavior"],
        "weekday_behavior_by_market": payload["weekday_behavior_by_market"],
        "day_regime_behavior_by_market": payload["day_regime_behavior_by_market"],
    }
    (output_dir / "cibo-atlas-vt31-complete-behavior-summary.json").write_text(
        json.dumps(compact, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    return payload


def self_test() -> None:
    assert expansion_strength(Decimal("1")) == "contained"
    assert expansion_strength(Decimal("1.5")) == "moderate"
    assert expansion_strength(Decimal("2.5")) == "strong"
    assert expansion_strength(Decimal("4")) == "extreme"
    assert fraction(1, 4) == "0.25"
    print("CIBO Atlas complete behavior explainer self-test PASS")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--forensics", type=Path)
    parser.add_argument("--attribution", type=Path)
    parser.add_argument("--predeparture", type=Path)
    parser.add_argument("--output-dir", type=Path)
    for partition in PARTITIONS:
        for market in MARKETS:
            parser.add_argument(f"--{partition.replace('_', '-')}-{market.lower()}", type=Path)
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    required = [args.forensics, args.attribution, args.predeparture, args.output_dir]
    required.extend(
        getattr(args, f"{partition}_{market.lower()}")
        for partition in PARTITIONS
        for market in MARKETS
    )
    if any(value is None for value in required):
        parser.error("all evidence inputs and output-dir are required")
    payload = build(args)
    print(
        json.dumps(
            {
                "market_days": payload["market_day_count"],
                "terminal_roots": payload["terminal_root_count"],
                "stopped_then_objective": payload[
                    "demonstrated_stop_before_source_objective_count"
                ],
                "market_behavior": payload["market_behavior"],
                "trader_behavior": payload["trader_behavior"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
