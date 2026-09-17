"""Build the eight linked consumed-only CIBO Atlas ledgers for VT-31.

The builder observes market paths independently, then overlays definitive trader
roots as diagnostic labels. It never opens fresh evidence or promotes a rule.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from statistics import median
from typing import Any, Iterable, cast
from zoneinfo import ZoneInfo

import cibo_atlas_vt31_complete_behavior_explainer as complete
import cibo_atlas_vt31_historical_market_scanner as strict
import cibo_atlas_vt31_pre_departure_structure_lab as predep
import vt31_r8_sparse_reference_forensics as sparse
from qore.infrastructure.market_data import OhlcSnapshot
from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_5_multi_index_research import (
    _day,
    _wall,
    load_market_evidence,
)
from qore.infrastructure.traders.vt31_silver_bullet_r2_2 import (
    Vt31R22EntryEvidence,
    Vt31R22ReferenceRange,
    _detect_raid,
    _entry_evidence,
    _structure,
)

MARKETS = ("NAS100", "SP500", "US30")
PARTITIONS = ("r8_fresh", "r6", "r5")
NY = ZoneInfo("America/New_York")
SCHEMA = "qore.cibo_atlas.vt31.eight_ledger_bundle.v1"
REF_TARGET_LADDER = tuple(Decimal(str(v)) for v in (0, 0.25, 0.5, 1, 1.5, 2))
R_TARGET_LADDER = tuple(Decimal(str(v)) for v in (1, 1.5, 2, 2.5, 3, 4, 5))


def dec(value: object) -> Decimal:
    return Decimal(str(value))


def fmt(value: Decimal | None) -> str | None:
    return None if value is None else format(value, "f")


def fraction(n: int, total: int) -> str | None:
    return None if total == 0 else fmt(Decimal(n) / Decimal(total))


def q(values: list[Decimal], p: Decimal) -> Decimal | None:
    if not values:
        return None
    xs = sorted(values)
    if len(xs) == 1:
        return xs[0]
    position = p * Decimal(len(xs) - 1)
    lo = int(position)
    hi = min(lo + 1, len(xs) - 1)
    weight = position - Decimal(lo)
    return xs[lo] * (Decimal(1) - weight) + xs[hi] * weight


def dt(value: str | None) -> datetime | None:
    if not value:
        return None
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise ValueError(f"timezone-naive timestamp: {value}")
    return parsed


def minutes(a: datetime | None, b: datetime | None) -> int | None:
    if a is None or b is None:
        return None
    return int((b - a).total_seconds() // 60)


def bars_between(
    bars: Iterable[OhlcSnapshot], start: tuple[int, int, int], end: tuple[int, int, int]
) -> tuple[OhlcSnapshot, ...]:
    return tuple(bar for bar in bars if start <= _wall(bar.opened_at) < end)


def partition_owns_day(partition: str, local_day: date) -> bool:
    if partition == "r8_fresh":
        return local_day < date(2018, 5, 19)
    if partition == "r6":
        return date(2018, 5, 19) <= local_day < date(2020, 6, 17)
    if partition == "r5":
        return local_day >= date(2020, 6, 17)
    raise ValueError(partition)


def episode_id(market: str, ny_date: str, breach: str, breach_at: str | None) -> str:
    raw = f"VT31|{market}|{ny_date}|{breach}|{breach_at or 'none'}".encode()
    return hashlib.sha256(raw).hexdigest()[:24]


def stable_root_family(status: object) -> str:
    text = str(status).lower()
    if "initial-stop" in text:
        return "initial_stop"
    if "protected-stop" in text:
        return "protected_stop"
    if "target" in text:
        return "target"
    return "other"


def load_json(path: Path, schema: str) -> dict[str, Any]:
    payload = cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))
    if payload.get("schema") != schema:
        raise ValueError(f"schema mismatch {path}: {payload.get('schema')} != {schema}")
    if payload.get("research_only") is not True or payload.get("opens_new_holdout") is not False:
        raise ValueError(f"research governance guard failed: {path}")
    return payload


def load_days(paths: dict[tuple[str, str], Path]) -> dict[tuple[str, str], dict[str, Any]]:
    days: dict[tuple[str, str], dict[str, Any]] = {}
    for partition in PARTITIONS:
        for market in MARKETS:
            series, _, _, _, _, provider = load_market_evidence(paths[(partition, market)])
            grouped: dict[date, list[OhlcSnapshot]] = defaultdict(list)
            for bar in series:
                grouped[_day(bar.opened_at)].append(bar)
            for local_day, raw in sorted(grouped.items()):
                if not partition_owns_day(partition, local_day):
                    continue
                frozen = tuple(sorted(raw, key=lambda bar: bar.opened_at))
                reference = cast(
                    tuple[OhlcSnapshot, ...],
                    sparse._reference_bars(cast(tuple[object, ...], frozen)),
                )
                session = bars_between(frozen, (10, 0, 0), (11, 0, 0))
                if (
                    len(session) != 60
                    or not strict.contiguous(session)
                    or not reference
                    or not sparse._policy_accepts(cast(tuple[object, ...], reference), "gap05")
                ):
                    continue
                key = (market, local_day.isoformat())
                if key in days:
                    raise ValueError(f"duplicate admitted market day {key}")
                days[key] = {
                    "partition": partition,
                    "market": market,
                    "ny_date": local_day.isoformat(),
                    "provider": provider,
                    "bars": frozen,
                    "reference": reference,
                    "session": session,
                    "lifecycle": bars_between(frozen, (10, 0, 0), (16, 0, 0)),
                }
    return days


def source_setup(day: dict[str, Any]) -> tuple[object | None, object | None, tuple[Vt31R22EntryEvidence, ...]]:
    reference = cast(tuple[OhlcSnapshot, ...], day["reference"])
    session = cast(tuple[OhlcSnapshot, ...], day["session"])
    ref = Vt31R22ReferenceRange(
        high=max(dec(bar.high) for bar in reference),
        low=min(dec(bar.low) for bar in reference),
        opened_at=reference[0].opened_at,
        closed_at=reference[-1].closed_at,
    )
    raid = _detect_raid(session, ref)
    if raid is None or raid.high_taken and raid.low_taken:
        return raid, None, ()
    structure = _structure(session, raid)
    if structure is None:
        return raid, None, ()
    confirmation_index, extreme_index, _, _ = structure
    candidates = _entry_evidence(session, raid, confirmation_index, extreme_index)
    return raid, structure, candidates


def touch_stats(
    candidate: Vt31R22EntryEvidence,
    path: tuple[OhlcSnapshot, ...],
) -> dict[str, Any] | None:
    eligible = [bar for bar in path if bar.closed_at >= candidate.formed_at]
    touched: list[tuple[int, OhlcSnapshot, Decimal]] = []
    width = candidate.zone_upper - candidate.zone_lower
    for index, bar in enumerate(eligible):
        lower = max(dec(bar.low), candidate.zone_lower)
        upper = min(dec(bar.high), candidate.zone_upper)
        if lower <= upper:
            penetration = Decimal(1) if width <= 0 else max(Decimal(0), upper - lower) / width
            touched.append((index, bar, penetration))
    if not touched:
        return None
    episodes = 1
    for left, right in zip(touched, touched[1:], strict=False):
        if right[0] != left[0] + 1:
            episodes += 1
    return {
        "structure_family": candidate.family.value,
        "formed_at": candidate.formed_at.isoformat(),
        "zone_lower": fmt(candidate.zone_lower),
        "zone_upper": fmt(candidate.zone_upper),
        "first_touch_at": touched[0][1].opened_at.isoformat(),
        "last_touch_at": touched[-1][1].opened_at.isoformat(),
        "touch_episode_count": episodes,
        "bars_touched": len(touched),
        "dwell_minutes": len(touched),
        "max_penetration_fraction": fmt(max(item[2] for item in touched)),
    }


def reference_sweep_events(
    path: tuple[OhlcSnapshot, ...], ref_high: Decimal, ref_low: Decimal
) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for bar in path:
        if dec(bar.high) > ref_high and dec(bar.close) < ref_high:
            events.append(
                {
                    "structure_family": "reference-liquidity-sweep",
                    "side": "bearish-reclaim",
                    "at": bar.opened_at.isoformat(),
                    "level": fmt(ref_high),
                }
            )
        if dec(bar.low) < ref_low and dec(bar.close) > ref_low:
            events.append(
                {
                    "structure_family": "reference-liquidity-sweep",
                    "side": "bullish-reclaim",
                    "at": bar.opened_at.isoformat(),
                    "level": fmt(ref_low),
                }
            )
    return events


def analyze_episode(day: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any] | None, dict[str, Any], dict[str, Any]]:
    market = str(day["market"])
    ny_date = str(day["ny_date"])
    partition = str(day["partition"])
    reference = cast(tuple[OhlcSnapshot, ...], day["reference"])
    session = cast(tuple[OhlcSnapshot, ...], day["session"])
    lifecycle = cast(tuple[OhlcSnapshot, ...], day["lifecycle"])
    all_bars = cast(tuple[OhlcSnapshot, ...], day["bars"])
    ref_high = max(dec(bar.high) for bar in reference)
    ref_low = min(dec(bar.low) for bar in reference)
    ref_width = ref_high - ref_low
    breach, breach_index, breach_bar, both_11 = strict.first_breach(session, ref_high, ref_low)
    breach_at = breach_bar.opened_at.isoformat() if breach_bar is not None else None
    eid = episode_id(market, ny_date, breach, breach_at)
    objective_at: datetime | None = None
    objective_index: int | None = None
    post_extension = Decimal(0)
    farthest_at: datetime | None = None
    pivot_at: datetime | None = None
    pivot_method: str | None = None
    pivot_to_objective_minutes: int | None = None
    path_from_breach: tuple[OhlcSnapshot, ...] = ()
    movement_side: str | None = None
    if breach in {"high", "low"} and breach_bar is not None:
        movement_side = "short" if breach == "high" else "long"
        path_from_breach = tuple(bar for bar in lifecycle if bar.opened_at >= breach_bar.opened_at)
        for i, bar in enumerate(path_from_breach):
            hit = dec(bar.low) <= ref_low if breach == "high" else dec(bar.high) >= ref_high
            if hit:
                objective_index = i
                objective_at = bar.opened_at
                break
        if objective_index is not None:
            to_objective = path_from_breach[: objective_index + 1]
            pivot_index, pivot_method = predep.departure_pivot(to_objective, movement_side)
            pivot_at = to_objective[pivot_index].opened_at
            pivot_to_objective_minutes = minutes(pivot_at, objective_at)
            tail = path_from_breach[objective_index:]
            if breach == "high":
                farthest = min(tail, key=lambda bar: dec(bar.low))
                post_extension = max(Decimal(0), ref_low - dec(farthest.low)) / ref_width
            else:
                farthest = max(tail, key=lambda bar: dec(bar.high))
                post_extension = max(Decimal(0), dec(farthest.high) - ref_high) / ref_width
            farthest_at = farthest.opened_at

    raid, structure, candidates = source_setup(day)
    confirmation_at: datetime | None = None
    if structure is not None:
        confirmation_index = cast(tuple[int, int, object, object], structure)[0]
        confirmation_at = session[confirmation_index].opened_at

    touch_path = path_from_breach if path_from_breach else lifecycle
    if objective_index is not None:
        touch_path = path_from_breach[: objective_index + 1]
    touches: list[dict[str, Any]] = []
    for candidate in candidates:
        stats = touch_stats(candidate, touch_path)
        if stats is not None:
            stats.update(
                {
                    "episode_id": eid,
                    "partition": partition,
                    "market": market,
                    "ny_date": ny_date,
                    "timing_class": "POST_OUTCOME_RESEARCH",
                }
            )
            touches.append(stats)
    local_sweeps = complete.local_sweep_events(touch_path)
    ref_sweeps = reference_sweep_events(touch_path, ref_high, ref_low)
    for event in local_sweeps:
        touches.append(
            {
                "episode_id": eid,
                "partition": partition,
                "market": market,
                "ny_date": ny_date,
                "structure_family": "local-liquidity-sweep",
                "formed_at": event["at"],
                "zone_lower": event.get("level"),
                "zone_upper": event.get("level"),
                "first_touch_at": event["at"],
                "last_touch_at": event["at"],
                "touch_episode_count": 1,
                "bars_touched": 1,
                "dwell_minutes": 1,
                "max_penetration_fraction": None,
                "timing_class": "POST_OUTCOME_RESEARCH",
            }
        )
    for event in ref_sweeps:
        touches.append(
            {
                "episode_id": eid,
                "partition": partition,
                "market": market,
                "ny_date": ny_date,
                "structure_family": "reference-liquidity-sweep",
                "formed_at": event["at"],
                "zone_lower": event["level"],
                "zone_upper": event["level"],
                "first_touch_at": event["at"],
                "last_touch_at": event["at"],
                "touch_episode_count": 1,
                "bars_touched": 1,
                "dwell_minutes": 1,
                "max_penetration_fraction": None,
                "timing_class": "POST_OUTCOME_RESEARCH",
            }
        )
    last_touch: dict[str, Any] | None = None
    if pivot_at is not None:
        eligible_touches = [row for row in touches if dt(cast(str, row["last_touch_at"])) <= pivot_at]
        if eligible_touches:
            last_touch = max(eligible_touches, key=lambda row: cast(datetime, dt(cast(str, row["last_touch_at"]))))
            last_touch["last_structure_before_departure"] = True
    for row in touches:
        row.setdefault("last_structure_before_departure", False)

    life_high = max((dec(bar.high) for bar in lifecycle), default=ref_high)
    life_low = min((dec(bar.low) for bar in lifecycle), default=ref_low)
    lifecycle_range_ref = (life_high - life_low) / ref_width if ref_width > 0 else Decimal(0)
    both_16 = life_high > ref_high and life_low < ref_low
    objective_hit = objective_at is not None
    if lifecycle_range_ref <= Decimal("1.25") and not objective_hit:
        day_regime = "lateral-compression-proxy"
    elif objective_hit:
        day_regime = "reversal-completion"
    elif breach == "none":
        day_regime = "inside-reference"
    elif both_16:
        day_regime = "two-sided-expansion"
    else:
        day_regime = "one-sided-expansion"

    observed_start = min(bar.opened_at for bar in all_bars)
    observed_end = max(bar.closed_at for bar in all_bars)
    full_high = max(dec(bar.high) for bar in all_bars)
    full_low = min(dec(bar.low) for bar in all_bars)
    daily = {
        "episode_id": eid,
        "partition": partition,
        "market": market,
        "ny_date": ny_date,
        "weekday": date.fromisoformat(ny_date).strftime("%A"),
        "provider": day["provider"],
        "observed_start": observed_start.isoformat(),
        "observed_end": observed_end.isoformat(),
        "observed_bar_count": len(all_bars),
        "reference_bar_count": len(reference),
        "reference_width": fmt(ref_width),
        "lifecycle_bar_count": len(lifecycle),
        "lifecycle_range_ref": fmt(lifecycle_range_ref),
        "full_observed_range_ref": fmt((full_high - full_low) / ref_width),
        "first_breach": breach,
        "first_breach_at": breach_at,
        "both_sides_by_11": both_11,
        "both_sides_by_16": both_16,
        "opposite_boundary_hit_by_16": objective_hit,
        "day_regime": day_regime,
        "timing_class": "POST_OUTCOME_RESEARCH",
    }

    milestones: list[dict[str, Any]] = []
    for event_type, when in (
        ("first_breach", dt(breach_at)),
        ("source_confirmation", confirmation_at),
        ("departure_pivot", pivot_at),
        ("opposite_09_boundary", objective_at),
        ("post_objective_farthest", farthest_at),
    ):
        if when is not None:
            milestones.append({"event": event_type, "at": when.isoformat()})
    milestones.sort(key=lambda item: item["at"])
    journey = {
        "episode_id": eid,
        "partition": partition,
        "market": market,
        "ny_date": ny_date,
        "provider": day["provider"],
        "reference_high": fmt(ref_high),
        "reference_low": fmt(ref_low),
        "reference_width": fmt(ref_width),
        "first_breach": breach,
        "first_breach_at": breach_at,
        "movement_side_after_first_breach": movement_side,
        "source_confirmation_at": confirmation_at.isoformat() if confirmation_at else None,
        "departure_pivot_at": pivot_at.isoformat() if pivot_at else None,
        "departure_pivot_method": pivot_method,
        "opposite_boundary_at": objective_at.isoformat() if objective_at else None,
        "post_objective_farthest_at": farthest_at.isoformat() if farthest_at else None,
        "post_boundary_extension_ref": fmt(post_extension if objective_hit else None),
        "milestones": milestones,
        "timing_class": "POST_OUTCOME_RESEARCH",
    }

    target = {
        "episode_id": eid,
        "partition": partition,
        "market": market,
        "ny_date": ny_date,
        "first_breach": breach,
        "opposite_boundary_available": breach in {"high", "low"},
        "opposite_boundary_hit_by_16": objective_hit,
        "opposite_boundary_at": objective_at.isoformat() if objective_at else None,
        "minutes_breach_to_opposite": minutes(dt(breach_at), objective_at),
        "post_boundary_extension_ref": fmt(post_extension if objective_hit else None),
        "post_objective_farthest_at": farthest_at.isoformat() if farthest_at else None,
        "post_boundary_ladder": {
            fmt(level): bool(objective_hit and post_extension >= level) for level in REF_TARGET_LADDER
        },
        "timing_class": "POST_OUTCOME_RESEARCH",
    }

    sequence: dict[str, Any] | None = None
    if objective_hit and breach_at and pivot_at and objective_at:
        events: list[dict[str, Any]] = [{"event": "first_breach", "at": breach_at}]
        if confirmation_at is not None:
            events.append({"event": "source_confirmation", "at": confirmation_at.isoformat()})
        for row in touches:
            events.append(
                {
                    "event": f"touch:{row['structure_family']}",
                    "at": row["first_touch_at"],
                }
            )
        for event in complete.displacement_events(touch_path):
            events.append({"event": f"displacement:{event['side']}", "at": event["at"]})
        events.append({"event": "departure_pivot", "at": pivot_at.isoformat()})
        events.append({"event": "opposite_09_boundary", "at": objective_at.isoformat()})
        events.sort(key=lambda item: (item["at"], item["event"]))
        sequence = {
            "episode_id": eid,
            "partition": partition,
            "market": market,
            "ny_date": ny_date,
            "weekday": date.fromisoformat(ny_date).strftime("%A"),
            "first_breach_at": breach_at,
            "departure_pivot_at": pivot_at.isoformat(),
            "opposite_boundary_at": objective_at.isoformat(),
            "last_structure_before_departure": (
                last_touch["structure_family"] if last_touch is not None else None
            ),
            "last_structure_touch_at": (
                last_touch["last_touch_at"] if last_touch is not None else None
            ),
            "event_sequence": events,
            "timing_class": "POST_OUTCOME_RESEARCH",
        }

    return journey, touches, sequence, target, daily


def leader(rows: list[dict[str, Any]], field: str) -> tuple[str | None, str | None, int | None]:
    timed = [(str(row["market"]), dt(cast(str | None, row.get(field)))) for row in rows]
    timed = [(market, when) for market, when in timed if when is not None]
    if not timed:
        return None, None, None
    ordered = sorted(timed, key=lambda item: cast(datetime, item[1]))
    first_market, first_time = ordered[0]
    last_market, last_time = ordered[-1]
    return first_market, last_market, minutes(first_time, last_time)


def cross_index(journeys: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in journeys:
        grouped[str(row["ny_date"])].append(row)
    output: list[dict[str, Any]] = []
    for ny_date, rows in sorted(grouped.items()):
        by_market = {str(row["market"]): row for row in rows}
        directions = {
            market: str(by_market[market]["first_breach"])
            for market in MARKETS
            if market in by_market
        }
        directional = [value for value in directions.values() if value in {"high", "low"}]
        if len(directional) == 3 and len(set(directional)) == 1:
            state = f"unanimous-{directional[0]}"
        elif len(directional) == 3:
            state = "three-market-divergence"
        else:
            state = "incomplete-or-nondirectional"
        breach_leader, breach_laggard, breach_lag = leader(rows, "first_breach_at")
        departure_leader, departure_laggard, departure_lag = leader(rows, "departure_pivot_at")
        objective_leader, objective_laggard, objective_lag = leader(rows, "opposite_boundary_at")
        output.append(
            {
                "ny_date": ny_date,
                "weekday": date.fromisoformat(ny_date).strftime("%A"),
                "markets_present": sorted(by_market),
                "direction_state": state,
                "breach_sides": directions,
                "breach_leader": breach_leader,
                "breach_laggard": breach_laggard,
                "breach_lead_lag_minutes": breach_lag,
                "departure_leader": departure_leader,
                "departure_laggard": departure_laggard,
                "departure_lead_lag_minutes": departure_lag,
                "objective_leader": objective_leader,
                "objective_laggard": objective_laggard,
                "objective_lead_lag_minutes": objective_lag,
                "timing_class": "POST_OUTCOME_RESEARCH",
            }
        )
    return output


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def summarize_daily(rows: list[dict[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for market in MARKETS:
        own = [row for row in rows if row["market"] == market]
        weekdays: dict[str, Any] = {}
        for weekday in ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday"):
            group = [row for row in own if row["weekday"] == weekday]
            if not group:
                continue
            weekdays[weekday] = {
                "n": len(group),
                "regimes": dict(sorted(Counter(str(row["day_regime"]) for row in group).items())),
                "objective_hit_rate": fraction(
                    sum(bool(row["opposite_boundary_hit_by_16"]) for row in group), len(group)
                ),
                "lifecycle_range_ref_p50": fmt(
                    q([dec(row["lifecycle_range_ref"]) for row in group], Decimal("0.5"))
                ),
            }
        out[market] = {
            "n": len(own),
            "regimes": dict(sorted(Counter(str(row["day_regime"]) for row in own).items())),
            "weekdays": weekdays,
        }
    return out


def build(args: argparse.Namespace) -> dict[str, Any]:
    forensics = load_json(
        cast(Path, args.forensics), "qore.vt31.tick_corrected.deep_forensics.v1"
    )
    attribution = load_json(
        cast(Path, args.attribution), "qore.cibo_atlas.vt31.root_cause_attribution.v1"
    )
    paths = {
        (partition, market): cast(Path, getattr(args, f"{partition}_{market.lower()}"))
        for partition in PARTITIONS
        for market in MARKETS
    }
    days = load_days(paths)
    journeys: list[dict[str, Any]] = []
    touches: list[dict[str, Any]] = []
    sequences: list[dict[str, Any]] = []
    targets: list[dict[str, Any]] = []
    daily: list[dict[str, Any]] = []
    for key in sorted(days, key=lambda item: (item[1], item[0])):
        journey, own_touches, sequence, target, day_row = analyze_episode(days[key])
        journeys.append(journey)
        touches.extend(own_touches)
        if sequence is not None:
            sequences.append(sequence)
        targets.append(target)
        daily.append(day_row)
    journey_by_key = {(row["market"], row["ny_date"]): row for row in journeys}
    target_by_key = {(row["market"], row["ny_date"]): row for row in targets}

    attr_by_root = {
        str(row["root_id"]): row for row in cast(list[dict[str, Any]], attribution["rows"])
    }
    roots = cast(list[dict[str, Any]], forensics["rows"])
    sync: list[dict[str, Any]] = []
    departure_timing: list[dict[str, Any]] = []
    target_root_overlays: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for root in roots:
        root_id = str(root["root_id"])
        key = (str(root["market"]), str(root["ny_date"]))
        journey = journey_by_key.get(key)
        target = target_by_key.get(key)
        if journey is None or target is None:
            raise ValueError(f"terminal root missing gap05 episode {root_id} {key}")
        signal_at = dt(str(root["signal_at"]))
        departure_at = dt(cast(str | None, journey.get("departure_pivot_at")))
        objective_at = dt(cast(str | None, journey.get("opposite_boundary_at")))
        a = attr_by_root[root_id]
        stopped_then_objective = (
            a.get("demonstrated_path_fact")
            == "demonstrated_exit_before_eventual_source_objective"
        )
        day_bars = cast(tuple[OhlcSnapshot, ...], days[key]["bars"])
        pre = tuple(
            bar
            for bar in day_bars
            if (10, 0, 0) <= _wall(bar.opened_at) and signal_at is not None and bar.opened_at < signal_at
        )
        pre_state = complete.pre_entry_state(pre)
        boundary_r = dec(root["opposing_liquidity_r"])
        risk_to_ref = dec(root["risk_to_reference"])
        post_ref = (
            dec(target["post_boundary_extension_ref"])
            if target.get("post_boundary_extension_ref") is not None
            else None
        )
        post_r = post_ref / risk_to_ref if post_ref is not None and risk_to_ref > 0 else None
        potential_r = boundary_r + post_r if post_r is not None else None
        family = stable_root_family(root.get("terminal_status"))
        relation = "departure-unavailable"
        if signal_at is not None and departure_at is not None:
            relation = "signal-before-final-departure" if signal_at < departure_at else "signal-at-or-after-final-departure"
        sync.append(
            {
                "root_id": root_id,
                "episode_id": journey["episode_id"],
                "partition": root["partition"],
                "market": root["market"],
                "ny_date": root["ny_date"],
                "weekday": date.fromisoformat(str(root["ny_date"])).strftime("%A"),
                "side": root["side"],
                "entry_family": root["entry_family"],
                "signal_at": root["signal_at"],
                "terminal_status": root["terminal_status"],
                "terminal_family": family,
                "terminal_r": root["terminal_r"],
                "first_breach": journey["first_breach"],
                "departure_pivot_at": journey["departure_pivot_at"],
                "signal_vs_departure": relation,
                "minutes_signal_to_departure": minutes(signal_at, departure_at),
                "opposite_boundary_at": journey["opposite_boundary_at"],
                "trader_stopped_before_eventual_source_objective": stopped_then_objective,
                "opposite_boundary_r_from_entry": fmt(boundary_r),
                "comparison_fixed_target_r": "2",
                "source_boundary_minus_2r": fmt(boundary_r - Decimal(2)),
                "post_boundary_extension_r_from_setup": fmt(post_r),
                "market_potential_r_to_farthest_by_16_if_objective_hit": fmt(potential_r),
                "pre_entry_behavior_proxy": pre_state["behavior_proxy"],
                "pre_entry_path_efficiency": pre_state["path_efficiency"],
                "pre_entry_overlap_rate": pre_state["overlap_rate"],
                "pre_entry_fvg_count": pre_state["fvg_count"],
                "pre_entry_sweep_reclaim_count": pre_state["local_sweep_reclaim_count"],
                "pre_entry_displacement_event_count": pre_state["displacement_event_count"],
                "timing_class": "MIXED_PRE_ENTRY_AND_POST_OUTCOME_RESEARCH",
            }
        )
        if objective_at is not None and departure_at is not None:
            local = departure_at.astimezone(NY)
            departure_timing.append(
                {
                    "root_id": root_id,
                    "episode_id": journey["episode_id"],
                    "market": root["market"],
                    "ny_date": root["ny_date"],
                    "weekday": local.strftime("%A"),
                    "departure_at": departure_at.isoformat(),
                    "departure_hour_minute_ny": local.strftime("%H:%M"),
                    "departure_bucket_5m": f"{local.hour:02d}:{(local.minute // 5) * 5:02d}",
                    "departure_bucket_15m": f"{local.hour:02d}:{(local.minute // 15) * 15:02d}",
                    "departure_bucket_30m": f"{local.hour:02d}:{(local.minute // 30) * 30:02d}",
                    "minutes_breach_to_departure": minutes(dt(cast(str | None, journey["first_breach_at"])), departure_at),
                    "minutes_departure_to_objective": minutes(departure_at, objective_at),
                    "trader_stopped_before_eventual_source_objective": stopped_then_objective,
                    "terminal_family": family,
                    "timing_class": "POST_OUTCOME_RESEARCH",
                }
            )
        target_root_overlays[key].append(
            {
                "root_id": root_id,
                "terminal_family": family,
                "opposite_boundary_r_from_entry": fmt(boundary_r),
                "fixed_2r_before_source_boundary": boundary_r > Decimal(2),
                "post_boundary_extension_r_from_setup": fmt(post_r),
                "potential_r_to_farthest": fmt(potential_r),
                "potential_r_ladder": {
                    fmt(level): bool(potential_r is not None and potential_r >= level)
                    for level in R_TARGET_LADDER
                },
            }
        )

    for row in targets:
        row["trader_root_overlays"] = target_root_overlays.get((row["market"], row["ny_date"]), [])

    cross = cross_index(journeys)
    if len(sync) != 618:
        raise AssertionError(f"expected 618 trader sync rows, got {len(sync)}")
    demonstrated = sum(bool(row["trader_stopped_before_eventual_source_objective"]) for row in sync)
    if demonstrated != 163:
        raise AssertionError(f"expected 163 demonstrated stopped-then-objective roots, got {demonstrated}")

    output_dir = cast(Path, args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    ledger_rows = {
        "MARKET_JOURNEY_LEDGER": journeys,
        "STRUCTURE_TOUCH_LEDGER": touches,
        "PRE_DEPARTURE_SEQUENCE_LEDGER": sequences,
        "DEPARTURE_TIMING_LEDGER": departure_timing,
        "TARGET_DESTINATION_LEDGER": targets,
        "CROSS_INDEX_JOURNEY_LEDGER": cross,
        "DAILY_PATH_LEDGER": daily,
        "TRADER_MARKET_SYNC_LEDGER": sync,
    }
    for name, rows in ledger_rows.items():
        write_jsonl(output_dir / f"{name}.jsonl", rows)

    summary = {
        "schema": SCHEMA,
        "research_only": True,
        "selection_prohibited": True,
        "opens_new_holdout": False,
        "candidate_status": "NO_R9_NOT_CERTIFIED",
        "live_authorized": False,
        "production_authorized": False,
        "reference_admission": "gap05-consumed",
        "session_admission": "strict60-10:00-11:00",
        "ledger_counts": {name: len(rows) for name, rows in ledger_rows.items()},
        "terminal_root_count": len(sync),
        "demonstrated_stop_before_source_objective_count": demonstrated,
        "daily_behavior": summarize_daily(daily),
        "structure_family_counts": dict(
            sorted(Counter(str(row["structure_family"]) for row in touches).items())
        ),
        "last_structure_before_departure_counts": dict(
            sorted(
                Counter(
                    str(row["structure_family"])
                    for row in touches
                    if row.get("last_structure_before_departure")
                ).items()
            )
        ),
        "pre_entry_behavior_proxy_counts": dict(
            sorted(Counter(str(row["pre_entry_behavior_proxy"]) for row in sync).items())
        ),
        "governance": {
            "post_outcome_fields_can_select_rule": False,
            "weekday_can_select_rule": False,
            "leader_can_select_rule": False,
            "target_ladder_can_select_rule": False,
            "requires_causal_predeclared_repair": True,
            "requires_leakage_free_walk_forward": True,
        },
    }
    (output_dir / "CIBO_ATLAS_VT31_EIGHT_LEDGER_SUMMARY.json").write_text(
        json.dumps(summary, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    return summary


def self_test() -> None:
    assert stable_root_family("initial-stop-after-fill") == "initial_stop"
    assert stable_root_family("terminal-protected-stop") == "protected_stop"
    assert stable_root_family("fixed-2r-target") == "target"
    assert partition_owns_day("r8_fresh", date(2018, 5, 18))
    assert partition_owns_day("r6", date(2018, 5, 19))
    assert partition_owns_day("r5", date(2020, 6, 17))
    assert not partition_owns_day("r6", date(2020, 6, 17))
    assert episode_id("NAS100", "2020-01-01", "high", "x") == episode_id(
        "NAS100", "2020-01-01", "high", "x"
    )
    print("CIBO Atlas VT31 eight-ledger builder self-test PASS")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--forensics", type=Path)
    parser.add_argument("--attribution", type=Path)
    parser.add_argument("--output-dir", type=Path)
    for partition in PARTITIONS:
        for market in MARKETS:
            parser.add_argument(f"--{partition.replace('_', '-')}-{market.lower()}", type=Path)
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    required = [args.forensics, args.attribution, args.output_dir]
    required.extend(
        getattr(args, f"{partition}_{market.lower()}")
        for partition in PARTITIONS
        for market in MARKETS
    )
    if any(value is None for value in required):
        parser.error("forensics, attribution, output-dir and all nine market files are required")
    result = build(args)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
