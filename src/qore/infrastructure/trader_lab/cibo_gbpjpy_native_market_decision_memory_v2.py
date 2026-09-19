"""CIBO GBPJPY Native Market Decision Memory V2.

This is a CIBO-native memory, not a Turtle-Soup Rxx-derived memory.

Inputs are only immutable CIBO market evidence:
- raw GBPJPY M5 10Y corpus;
- CIBO Market Journey V1;
- CIBO Target Destination V2.

The memory learns distributions directly from market episodes and stores:
- pre-departure market state;
- distinct active DOL ladder ranks;
- destination distance / CIBO protected-risk geometry;
- full target completion;
- stop-before-target;
- partial/protectable journey;
- structural lifecycle outcomes under STATIC, LET_RUN, and PROTECT;
- economic outcome after fixed 0.10R friction.

No R11/R16/R17/R20/R21/R22/R23 label or result is an input.
"""
from __future__ import annotations

import bisect
import json
import sys
from collections import Counter, defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from statistics import median
from typing import Any, cast

from qore.infrastructure.trader_lab import (
    cibo_market_atlas_journey_extractor_v1 as journey,
)
from qore.infrastructure.trader_lab import ict_turtle_soup_behavior_lab as behavior
from qore.infrastructure.trader_lab import (
    ict_turtle_soup_behavior_lab_fast_runner as fast,
)
from qore.infrastructure.trader_lab.ict_turtle_soup_r4_source_exact import (
    Bar,
    Side,
)

IDENTITY = "CIBO_GBPJPY_NATIVE_MARKET_DECISION_MEMORY_V2"
SYMBOL = "GBPJPY"
STRESS_FRICTION_R = Decimal("0.10")
MIN_PERIOD_N = 10
MAX_TARGET_RANK = 3

POSTURE_STATIC = "STATIC"
POSTURE_LET_RUN = "LET_RUN"
POSTURE_PROTECT = "PROTECT"
POSTURES = (POSTURE_STATIC, POSTURE_LET_RUN, POSTURE_PROTECT)

ROBUST = "ROBUST_NET_POSITIVE_010"
MAJORITY = "MAJORITY_NET_POSITIVE_010"
NEGATIVE = "NET_NEGATIVE_010"
UNRESOLVED = "UNRESOLVED"

RR_CUTS = (
    Decimal("0.5"),
    Decimal("1.0"),
    Decimal("1.5"),
    Decimal("2.5"),
    Decimal("4.0"),
    Decimal("6.0"),
)
RATIO_CUTS = (
    Decimal("0.25"),
    Decimal("0.50"),
    Decimal("1.0"),
    Decimal("2.0"),
)
FRACTION_CUTS = (
    Decimal("0.25"),
    Decimal("0.50"),
    Decimal("0.75"),
)

MEMORY_LEVELS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "full",
        (
            "timeframe",
            "reference_type",
            "side",
            "session",
            "prior_body_alignment",
            "fvg",
            "equal_liquidity",
            "reclaim_bucket",
            "cisd_progress_bucket",
            "raid_depth_bucket",
            "protected_risk_bucket",
            "body_bucket",
            "wick_bucket",
            "close_bucket",
            "target_rank",
            "target_route",
            "rr_bucket",
        ),
    ),
    (
        "causal_core",
        (
            "timeframe",
            "reference_type",
            "prior_body_alignment",
            "fvg",
            "equal_liquidity",
            "reclaim_bucket",
            "cisd_progress_bucket",
            "raid_depth_bucket",
            "protected_risk_bucket",
            "target_rank",
            "target_route",
            "rr_bucket",
        ),
    ),
    (
        "anatomy",
        (
            "timeframe",
            "reference_type",
            "fvg",
            "reclaim_bucket",
            "cisd_progress_bucket",
            "protected_risk_bucket",
            "target_rank",
            "target_route",
            "rr_bucket",
        ),
    ),
    (
        "destination",
        (
            "timeframe",
            "target_rank",
            "target_route",
            "rr_bucket",
        ),
    ),
    (
        "geometry",
        (
            "target_rank",
            "rr_bucket",
        ),
    ),
)


@dataclass(frozen=True, slots=True)
class NativeTarget:
    rank: int
    level: Decimal
    route: str
    distance_ticks: Decimal
    touched: bool
    touch_at: datetime | None


@dataclass(frozen=True, slots=True)
class Lifecycle:
    posture: str
    gross_r: Decimal
    net_010_r: Decimal
    exit_reason: str
    target_reached: bool
    protected_exit: bool
    stop_exit: bool
    trail_moves: int


def _single(root: Path, name: str) -> Path:
    matches = list(root.rglob(name))
    if len(matches) != 1:
        raise ValueError(f"expected exactly one {name}, got {len(matches)}")
    return matches[0]


def _dt(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return parsed


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                row = json.loads(line)
                if not isinstance(row, dict):
                    raise ValueError(f"expected object row in {path}")
                rows.append(row)
    return rows


def _bucket(value: Decimal | None, cuts: Sequence[Decimal]) -> str:
    if value is None:
        return "missing"
    for index, cut in enumerate(cuts, start=1):
        if value <= cut:
            return f"q{index}:<={cut}"
    return f"q{len(cuts)+1}:>{cuts[-1]}"


def _latency_bucket(minutes: int | None) -> str:
    if minutes is None:
        return "missing"
    if minutes <= 5:
        return "<=5m"
    if minutes <= 15:
        return "6-15m"
    if minutes <= 30:
        return "16-30m"
    if minutes <= 60:
        return "31-60m"
    if minutes <= 120:
        return "61-120m"
    return ">120m"


def _period(year: int) -> str:
    if 2016 <= year <= 2020:
        return "early_2016_2020"
    if 2021 <= year <= 2023:
        return "transition_2021_2023"
    if 2024 <= year <= 2026:
        return "recent_2024_2026"
    return "outside"


def _event_state(event: behavior.Event) -> dict[str, Any]:
    duration = {
        "H1": Decimal(60),
        "H4": Decimal(240),
        "D1": Decimal(1440),
    }[event.timeframe]
    cisd_progress = (
        None
        if event.cisd_latency_minutes is None
        else Decimal(event.cisd_latency_minutes) / duration
    )
    risk_ratio = (
        None
        if event.protected_swing_distance_ticks is None
        or event.source_range_ticks <= 0
        else event.protected_swing_distance_ticks / event.source_range_ticks
    )
    return {
        "timeframe": event.timeframe,
        "reference_type": event.reference_type,
        "side": event.side,
        "session": event.session_bucket,
        "weekday": event.raid_at.strftime("%A"),
        "prior_body_alignment": event.prior_body_alignment,
        "fvg": "yes" if event.fvg_after_raid else "no",
        "equal_liquidity": "yes" if event.exact_equal_count > 1 else "no",
        "reclaim_bucket": _latency_bucket(event.reclaim_latency_minutes),
        "cisd_progress_bucket": _bucket(cisd_progress, FRACTION_CUTS),
        "raid_depth_bucket": _bucket(event.raid_depth_range_units, RATIO_CUTS),
        "protected_risk_bucket": _bucket(risk_ratio, RATIO_CUTS),
        "body_bucket": _bucket(event.body_fraction, FRACTION_CUTS),
        "wick_bucket": _bucket(
            event.rejection_wick_fraction,
            (Decimal("0.10"), Decimal("0.25"), Decimal("0.50")),
        ),
        "close_bucket": _bucket(event.close_location, FRACTION_CUTS),
    }


def _route(rows: Sequence[dict[str, Any]]) -> str:
    values = sorted(
        {
            f"{row['candidate_type']}:{row['source_timeframe']}"
            for row in rows
        }
    )
    return "+".join(values)


def _distinct_targets(rows: Sequence[dict[str, Any]]) -> list[NativeTarget]:
    by_price: dict[Decimal, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_price[Decimal(str(row["candidate_price"]))].append(row)
    grouped = sorted(
        by_price.items(),
        key=lambda item: Decimal(str(item[1][0]["candidate_distance_ticks"])),
    )
    result: list[NativeTarget] = []
    for rank, (price, members) in enumerate(grouped, start=1):
        if rank > MAX_TARGET_RANK:
            break
        touched_rows = [row for row in members if bool(row["touch_within_24h"])]
        touch_at = (
            None
            if not touched_rows
            else min(_dt(str(row["touch_m5_opened_at"])) for row in touched_rows)
        )
        result.append(
            NativeTarget(
                rank=rank,
                level=price,
                route=_route(members),
                distance_ticks=Decimal(
                    str(members[0]["candidate_distance_ticks"])
                ),
                touched=bool(touched_rows),
                touch_at=touch_at,
            )
        )
    return result


def _swing_candidate(
    *,
    side: Side,
    bars: Sequence[Bar],
    entry: Decimal,
    target: Decimal,
) -> Decimal | None:
    if len(bars) < 3:
        return None
    left, middle, right = bars[-3], bars[-2], bars[-1]
    if side is Side.LONG:
        if middle.low < left.low and middle.low < right.low:
            if entry < middle.low < target:
                return middle.low
        return None
    if middle.high > left.high and middle.high > right.high:
        if target < middle.high < entry:
            return middle.high
    return None


def _better_stop(side: Side, a: Decimal, b: Decimal) -> Decimal:
    return max(a, b) if side is Side.LONG else min(a, b)


def _improves_stop(
    *,
    side: Side,
    previous: Decimal,
    candidate: Decimal,
    target: Decimal,
) -> bool:
    if side is Side.LONG:
        return previous < candidate < target
    return target < candidate < previous


def _target_touch(side: Side, level: Decimal, bar: Bar) -> bool:
    if side is Side.LONG:
        return bool(bar.open >= level or bar.high >= level)
    return bool(bar.open <= level or bar.low <= level)


def _simulate(
    *,
    posture: str,
    side: Side,
    entry_at: datetime,
    entry: Decimal,
    risk_price: Decimal,
    target: NativeTarget,
    ladder: Sequence[NativeTarget],
    bars: Sequence[Bar],
    opens: Sequence[datetime],
) -> Lifecycle:
    if risk_price <= 0:
        raise ValueError("risk must be positive")
    initial_stop = (
        entry - risk_price if side is Side.LONG else entry + risk_price
    )
    target_price = target.level
    reward = (
        target_price - entry if side is Side.LONG else entry - target_price
    )
    if reward <= 0:
        return Lifecycle(
            posture=posture,
            gross_r=Decimal("-1"),
            net_010_r=Decimal("-1.10"),
            exit_reason="INVALID_TARGET_GEOMETRY",
            target_reached=False,
            protected_exit=False,
            stop_exit=True,
            trail_moves=0,
        )
    left = bisect.bisect_left(opens, entry_at)
    right = bisect.bisect_left(opens, entry_at + timedelta(hours=24))
    path = bars[left:right]
    if not path:
        return Lifecycle(
            posture=posture,
            gross_r=Decimal(0),
            net_010_r=-STRESS_FRICTION_R,
            exit_reason="NO_PATH",
            target_reached=False,
            protected_exit=False,
            stop_exit=False,
            trail_moves=0,
        )

    current_stop = initial_stop
    pending: Decimal | None = None
    observed: list[Bar] = []
    conquered: set[int] = set()
    trail_moves = 0
    exit_price = path[-1].close
    exit_reason = "TIME_24H"

    for bar in path:
        if pending is not None and _improves_stop(
            side=side,
            previous=current_stop,
            candidate=pending,
            target=target_price,
        ):
            current_stop = pending
            trail_moves += 1
        pending = None

        if side is Side.LONG:
            if bar.open <= current_stop:
                exit_price = bar.open
                exit_reason = "GAP_TRAIL" if current_stop != initial_stop else "GAP_STOP"
                break
            if bar.open >= target_price:
                exit_price = target_price
                exit_reason = "TARGET"
                break
            stop_touch = bar.low <= current_stop
            target_hit = bar.high >= target_price
        else:
            if bar.open >= current_stop:
                exit_price = bar.open
                exit_reason = "GAP_TRAIL" if current_stop != initial_stop else "GAP_STOP"
                break
            if bar.open <= target_price:
                exit_price = target_price
                exit_reason = "TARGET"
                break
            stop_touch = bar.high >= current_stop
            target_hit = bar.low <= target_price

        if stop_touch and target_hit:
            exit_price = current_stop
            exit_reason = "TRAIL_STOP_FIRST" if current_stop != initial_stop else "STOP_FIRST"
            break
        if stop_touch:
            exit_price = current_stop
            exit_reason = "TRAIL_STOP" if current_stop != initial_stop else "STOP"
            break
        if target_hit:
            exit_price = target_price
            exit_reason = "TARGET"
            break

        observed.append(bar)

        if posture != POSTURE_STATIC and target.rank > 1:
            for earlier in ladder[: target.rank - 1]:
                if earlier.rank in conquered:
                    continue
                if _target_touch(side, earlier.level, bar):
                    conquered.add(earlier.rank)
                    if _improves_stop(
                        side=side,
                        previous=current_stop,
                        candidate=earlier.level,
                        target=target_price,
                    ):
                        if pending is None:
                            pending = earlier.level
                        else:
                            pending = _better_stop(side, pending, earlier.level)

        if posture == POSTURE_PROTECT:
            swing = _swing_candidate(
                side=side,
                bars=observed,
                entry=entry,
                target=target_price,
            )
            if (
                swing is not None
                and _improves_stop(
                    side=side,
                    previous=current_stop,
                    candidate=swing,
                    target=target_price,
                )
            ):
                if pending is None:
                    pending = swing
                else:
                    pending = _better_stop(side, pending, swing)

    if side is Side.LONG:
        gross = (exit_price - entry) / risk_price
    else:
        gross = (entry - exit_price) / risk_price
    target_reached = exit_reason == "TARGET"
    protected_exit = (
        not target_reached
        and gross >= 0
        and current_stop != initial_stop
    )
    stop_exit = "STOP" in exit_reason
    return Lifecycle(
        posture=posture,
        gross_r=gross,
        net_010_r=gross - STRESS_FRICTION_R,
        exit_reason=exit_reason,
        target_reached=target_reached,
        protected_exit=protected_exit,
        stop_exit=stop_exit,
        trail_moves=trail_moves,
    )


def _pf(values: Sequence[Decimal]) -> str | None:
    gains = sum((value for value in values if value > 0), Decimal(0))
    losses = -sum((value for value in values if value < 0), Decimal(0))
    if losses == 0:
        return None if gains == 0 else "inf"
    return str(gains / losses)


def _posture_summary(rows: Sequence[dict[str, Any]], posture: str) -> dict[str, Any]:
    values = [Decimal(str(row[f"{posture}_net_010_r"])) for row in rows]
    gross = [Decimal(str(row[f"{posture}_gross_r"])) for row in rows]
    n = len(rows)
    if not rows:
        return {"n": 0}
    return {
        "n": n,
        "mean_gross_r": str(sum(gross, Decimal(0)) / Decimal(n)),
        "mean_net_010_r": str(sum(values, Decimal(0)) / Decimal(n)),
        "median_net_010_r": str(median(values)),
        "profit_factor_010": _pf(values),
        "target_rate": str(
            Decimal(sum(bool(row[f"{posture}_target_reached"]) for row in rows))
            / Decimal(n)
        ),
        "protected_exit_rate": str(
            Decimal(sum(bool(row[f"{posture}_protected_exit"]) for row in rows))
            / Decimal(n)
        ),
        "stop_exit_rate": str(
            Decimal(sum(bool(row[f"{posture}_stop_exit"]) for row in rows))
            / Decimal(n)
        ),
        "positive_net_rate": str(
            Decimal(sum(value > 0 for value in values)) / Decimal(n)
        ),
    }


def _classify(rows: Sequence[dict[str, Any]], posture: str) -> dict[str, Any]:
    by_period = {
        period: [
            row
            for row in rows
            if row["period"] == period
        ]
        for period in (
            "early_2016_2020",
            "transition_2021_2023",
            "recent_2024_2026",
        )
    }
    period_profiles = {
        period: _posture_summary(items, posture)
        for period, items in by_period.items()
    }
    sufficient = all(
        int(profile.get("n", 0)) >= MIN_PERIOD_N
        for profile in period_profiles.values()
    )
    combined = _posture_summary(rows, posture)
    period_means = [
        Decimal(str(profile["mean_net_010_r"]))
        for profile in period_profiles.values()
        if profile.get("n", 0)
    ]
    positive_periods = sum(value > 0 for value in period_means)
    combined_mean = (
        Decimal(str(combined["mean_net_010_r"]))
        if combined.get("n", 0)
        else Decimal(0)
    )
    if sufficient and positive_periods == 3 and combined_mean > 0:
        classification = ROBUST
    elif sufficient and positive_periods >= 2 and combined_mean > 0:
        classification = MAJORITY
    elif sufficient and combined_mean <= 0:
        classification = NEGATIVE
    else:
        classification = UNRESOLVED
    return {
        "classification": classification,
        "combined": combined,
        "periods": period_profiles,
        "minimum_period_n": MIN_PERIOD_N,
    }


def _key(row: dict[str, Any], fields: Sequence[str]) -> str:
    return "|".join(str(row[field]) for field in fields)


def _build_memory(observations: Sequence[dict[str, Any]]) -> dict[str, Any]:
    hierarchy: dict[str, Any] = {}
    for level_name, fields in MEMORY_LEVELS:
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in observations:
            grouped[_key(row, fields)].append(row)
        signatures: dict[str, Any] = {}
        for signature, rows in sorted(grouped.items()):
            posture_models = {
                posture: _classify(rows, posture)
                for posture in POSTURES
            }
            signatures[signature] = {
                "fields": list(fields),
                "values": {field: rows[0][field] for field in fields},
                "observations": len(rows),
                "postures": posture_models,
                "full_target_rate": str(
                    Decimal(sum(bool(row["full_target_touched"]) for row in rows))
                    / Decimal(len(rows))
                ),
                "median_rr": str(
                    median(Decimal(str(row["planned_rr"])) for row in rows)
                ),
                "median_time_to_target_minutes": (
                    None
                    if not [
                        row["time_to_target_minutes"]
                        for row in rows
                        if row["time_to_target_minutes"] is not None
                    ]
                    else str(
                        median(
                            Decimal(str(row["time_to_target_minutes"]))
                            for row in rows
                            if row["time_to_target_minutes"] is not None
                        )
                    )
                ),
            }
        hierarchy[level_name] = {
            "fields": list(fields),
            "signatures": signatures,
            "posture_classification_counts": {
                posture: dict(
                    Counter(
                        str(item["postures"][posture]["classification"])
                        for item in signatures.values()
                    )
                )
                for posture in POSTURES
            },
        }
    return hierarchy


def resolve(
    hierarchy: dict[str, Any],
    row: dict[str, Any],
) -> tuple[dict[str, Any] | None, str | None, str | None]:
    for level_name, fields in MEMORY_LEVELS:
        signature = _key(row, fields)
        item = cast(dict[str, Any], hierarchy[level_name]["signatures"]).get(signature)
        if item is not None:
            # A group is decision-capable if at least one posture is resolved
            # as positive or negative and all three temporal blocks meet support.
            if any(
                model["classification"] in {ROBUST, MAJORITY, NEGATIVE}
                for model in item["postures"].values()
            ):
                return item, level_name, signature
    return None, None, None


def _best_posture(item: dict[str, Any]) -> tuple[str | None, str]:
    robust = [
        posture
        for posture, model in item["postures"].items()
        if model["classification"] == ROBUST
    ]
    if robust:
        # deterministic: preserve freedom first, then protection, then static
        for posture in (POSTURE_LET_RUN, POSTURE_PROTECT, POSTURE_STATIC):
            if posture in robust:
                return posture, ROBUST
    majority = [
        posture
        for posture, model in item["postures"].items()
        if model["classification"] == MAJORITY
    ]
    if majority:
        for posture in (POSTURE_LET_RUN, POSTURE_PROTECT, POSTURE_STATIC):
            if posture in majority:
                return posture, MAJORITY
    return None, NEGATIVE



def _decision_index(hierarchy: dict[str, Any]) -> dict[str, Any]:
    compact: dict[str, Any] = {}
    for level_name, fields in MEMORY_LEVELS:
        source = hierarchy[level_name]
        signatures: dict[str, Any] = {}
        for signature, item in cast(dict[str, Any], source["signatures"]).items():
            posture, classification = _best_posture(item)
            if posture is None:
                # Keep temporally-supported negative knowledge, but omit groups
                # that remain entirely unresolved.
                resolved = [
                    model["classification"]
                    for model in item["postures"].values()
                    if model["classification"] != UNRESOLVED
                ]
                if not resolved:
                    continue
                signatures[signature] = {
                    "classification": NEGATIVE,
                    "preferred_posture": None,
                    "observations": item["observations"],
                    "mean_net_010_r": None,
                    "target_rate": item["full_target_rate"],
                    "values": item["values"],
                }
                continue
            combined = item["postures"][posture]["combined"]
            signatures[signature] = {
                "classification": classification,
                "preferred_posture": posture,
                "observations": item["observations"],
                "mean_net_010_r": combined["mean_net_010_r"],
                "profit_factor_010": combined["profit_factor_010"],
                "target_rate": combined["target_rate"],
                "protected_exit_rate": combined["protected_exit_rate"],
                "stop_exit_rate": combined["stop_exit_rate"],
                "values": item["values"],
            }
        compact[level_name] = {
            "fields": list(fields),
            "signatures": signatures,
            "classification_counts": dict(
                Counter(
                    str(item["classification"])
                    for item in signatures.values()
                )
            ),
        }
    return compact


def resolve_index(
    index: dict[str, Any],
    row: dict[str, Any],
) -> tuple[dict[str, Any] | None, str | None, str | None]:
    for level_name, fields in MEMORY_LEVELS:
        signature = _key(row, fields)
        item = cast(dict[str, Any], index[level_name]["signatures"]).get(signature)
        if item is not None:
            return item, level_name, signature
    return None, None, None


def build(
    raw_root: Path,
    journey_root: Path,
    target_root: Path,
    output: Path,
) -> dict[str, Any]:
    evidence, provenance = journey.load_raw_m5(raw_root)
    if evidence.symbol != SYMBOL or int(provenance["retained_bars"]) != 745478:
        raise ValueError("unexpected GBPJPY raw corpus")
    journey_manifest = json.loads(_single(journey_root, "journey-manifest.json").read_text())
    target_manifest = json.loads(
        _single(target_root, "target-destination-v2-manifest.json").read_text()
    )
    if journey_manifest["identity"] != "CIBO_MARKET_JOURNEY_LAYER_V1":
        raise ValueError("unexpected Journey V1 identity")
    if target_manifest["identity"] != "CIBO_TARGET_DESTINATION_V2_SUPPORTED_REFERENCE_UNIVERSE":
        raise ValueError("unexpected Target Destination V2 identity")

    fast.install()
    events = behavior.extract_events(
        evidence,
        asset_class="forex",
        provider=str(provenance["provider_symbol"]),
        evidence_id="cibo-native-memory-v2",
    )
    if len(events) != 125664:
        raise ValueError("CIBO behavior event reproduction drift")

    event_by_episode = {
        journey._episode_id(event): event
        for event in events
        if event.cisd_confirmed and event.cisd_latency_minutes is not None
    }
    target_rows = _read_jsonl(_single(target_root, "TARGET_DESTINATION_LEDGER_V2.jsonl"))
    by_episode: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for target_row in target_rows:
        by_episode[str(target_row["episode_id"])].append(target_row)

    opens = tuple(bar.opened_at for bar in evidence.bars)
    observations: list[dict[str, Any]] = []
    episodes_used = 0
    missing_event = 0

    for episode_id, rows in sorted(by_episode.items()):
        event = event_by_episode.get(episode_id)
        if event is None:
            missing_event += 1
            continue
        if event.protected_swing_distance_ticks is None:
            continue
        risk_ticks = event.protected_swing_distance_ticks
        if risk_ticks <= 0:
            continue
        targets = _distinct_targets(rows)
        if not targets:
            continue
        episodes_used += 1
        anchor = Decimal(str(rows[0]["departure_anchor_price"]))
        departure = _dt(str(rows[0]["departure_at"]))
        side = Side(event.side)
        risk_price = risk_ticks * event.tick_size
        state = _event_state(event)

        for target in targets:
            reward = (
                target.level - anchor
                if side is Side.LONG
                else anchor - target.level
            )
            if reward <= 0:
                continue
            rr = reward / risk_price
            lifecycle = {
                posture: _simulate(
                    posture=posture,
                    side=side,
                    entry_at=departure,
                    entry=anchor,
                    risk_price=risk_price,
                    target=target,
                    ladder=targets,
                    bars=evidence.bars,
                    opens=opens,
                )
                for posture in POSTURES
            }
            observation: dict[str, Any] = {
                **state,
                "episode_id": episode_id,
                "departure_at": departure.isoformat(),
                "year": departure.year,
                "period": _period(departure.year),
                "target_rank": target.rank,
                "target_route": target.route,
                "planned_rr": str(rr),
                "rr_bucket": _bucket(rr, RR_CUTS),
                "full_target_touched": target.touched,
                "time_to_target_minutes": (
                    None
                    if target.touch_at is None
                    else int((target.touch_at - departure).total_seconds() // 60)
                ),
                "mfe_240_r": str(event.mfe_240m_ticks / risk_ticks),
                "mae_240_r": str(event.mae_240m_ticks / risk_ticks),
                "mfe_1440_r": str(event.mfe_1440m_ticks / risk_ticks),
                "mae_1440_r": str(event.mae_1440m_ticks / risk_ticks),
            }
            for posture, result in lifecycle.items():
                observation[f"{posture}_gross_r"] = str(result.gross_r)
                observation[f"{posture}_net_010_r"] = str(result.net_010_r)
                observation[f"{posture}_exit_reason"] = result.exit_reason
                observation[f"{posture}_target_reached"] = result.target_reached
                observation[f"{posture}_protected_exit"] = result.protected_exit
                observation[f"{posture}_stop_exit"] = result.stop_exit
                observation[f"{posture}_trail_moves"] = result.trail_moves
            observations.append(observation)

    hierarchy = _build_memory(observations)
    decision_index = _decision_index(hierarchy)

    decision_counts: Counter[str] = Counter()
    posture_counts: Counter[str] = Counter()
    for observation in observations:
        item, level, _signature = resolve(hierarchy, observation)
        if item is None:
            decision_counts["UNRESOLVED"] += 1
            continue
        preferred_posture, classification = _best_posture(item)
        decision_counts[f"{level}:{classification}"] += 1
        if preferred_posture is not None:
            posture_counts[preferred_posture] += 1

    payload = {
        "schema": "qore.cibo.gbpjpy.native_market_decision_memory.v2",
        "identity": IDENTITY,
        "symbol": SYMBOL,
        "evidence_status": "CONSUMED_10Y_CIBO_NATIVE_MARKET_MEMORY",
        "source_contract": {
            "raw_m5_only": True,
            "journey_v1": True,
            "target_destination_v2": True,
            "r11_used": False,
            "r16_used": False,
            "r17_used": False,
            "r20_used": False,
            "r21_used": False,
            "r22_used": False,
            "r23_used": False,
        },
        "memory_contract": {
            "stress_friction_r": str(STRESS_FRICTION_R),
            "maximum_target_rank": MAX_TARGET_RANK,
            "postures": list(POSTURES),
            "classification": {
                ROBUST: "all three temporal blocks positive at 0.10R",
                MAJORITY: "combined positive and at least two temporal blocks positive",
                NEGATIVE: "combined non-positive with full temporal support",
                UNRESOLVED: "insufficient temporal support",
            },
            "minimum_observations_per_period": MIN_PERIOD_N,
            "automatic_threshold_search": False,
            "post_hoc_rxx_labels_used": False,
            "native_market_lifecycle_simulated": True,
        },
        "reproduction": {
            "retained_bars": int(provenance["retained_bars"]),
            "behavior_events": len(events),
            "target_candidate_rows": len(target_rows),
            "target_episodes": len(by_episode),
            "episodes_used": episodes_used,
            "missing_event_bindings": missing_event,
            "memory_observations": len(observations),
        },
        "hierarchy": hierarchy,
        "decision_index_summary": {
            level: {
                "fields": payload["fields"],
                "classification_counts": payload["classification_counts"],
                "signatures": len(payload["signatures"]),
            }
            for level, payload in decision_index.items()
        },
        "resolution_counts": dict(decision_counts),
        "preferred_posture_counts": dict(posture_counts),
        "governance": {
            "research_memory_only": True,
            "fresh_holdout_consumed": False,
            "rule_promoted": False,
            "demo_eligible": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        },
    }

    output.mkdir(parents=True, exist_ok=True)
    (output / "cibo-gbpjpy-native-memory-v2-report.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n"
    )
    (output / "cibo-gbpjpy-native-memory-v2-observations.json").write_text(
        json.dumps(observations, indent=2, sort_keys=True) + "\n"
    )
    (output / "cibo-gbpjpy-native-memory-v2-hierarchy.json").write_text(
        json.dumps(hierarchy, indent=2, sort_keys=True) + "\n"
    )
    (output / "cibo-gbpjpy-native-memory-v2-decision-index.json").write_text(
        json.dumps(decision_index, indent=2, sort_keys=True) + "\n"
    )
    return payload


def main() -> None:
    if len(sys.argv) != 5:
        raise SystemExit(
            "usage: module RAW_ROOT JOURNEY_ROOT TARGET_ROOT OUTPUT_DIR"
        )
    print(
        json.dumps(
            build(
                Path(sys.argv[1]),
                Path(sys.argv[2]),
                Path(sys.argv[3]),
                Path(sys.argv[4]),
            ),
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
