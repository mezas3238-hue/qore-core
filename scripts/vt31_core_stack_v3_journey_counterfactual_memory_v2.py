"""Shared Journey Intelligence V2: historical counterfactual memory.

The previous integrated lab falsified fixed local thresholds. V2 replaces them
with a historical, closed-episode counterfactual memory.

For historical trades only, Shared learns the realized uplift of two actions at
each causal M1 state:
- EXTEND: replace the original target from the NEXT M1 with a farther
  reference-width destination.
- DEFEND: exit at the NEXT M1 open.

For a current R6/R5 trade, only state variables observable at that closed M1
are queried. Current/future outcome is never an input.

R8 -> memory/discovery
R6 -> calibrate and freeze
R5 -> no-retune temporal evaluation
"""
# ruff: noqa: B009
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_core_stack_v3_analog_world_model_v1 as v3
import vt31_core_stack_v3_integrated_shared_intelligence_v1 as v1
import vt31_core_stack_v3_shared_decision_intelligence_v2 as decision

SCHEMA = "qore.core_stack_v3.vt31.journey_counterfactual_memory.v2"
IDENTITY = "VT31_NAS100_SHARED_JOURNEY_COUNTERFACTUAL_MEMORY_V2"
FRICTION = Decimal("0.05")


@dataclass(frozen=True, slots=True)
class JourneyMemoryPolicy:
    extension_reference_fraction: Decimal
    minimum_samples: int
    minimum_positive_rate: Decimal
    extend_min_mean_uplift_r: Decimal
    defend_min_mean_uplift_r: Decimal
    extend_min_progress_fraction: Decimal

    def payload(self) -> dict[str, object]:
        return {
            "extension_reference_fraction": format(
                self.extension_reference_fraction, "f"
            ),
            "minimum_samples": self.minimum_samples,
            "minimum_positive_rate": format(
                self.minimum_positive_rate, "f"
            ),
            "extend_min_mean_uplift_r": format(
                self.extend_min_mean_uplift_r, "f"
            ),
            "defend_min_mean_uplift_r": format(
                self.defend_min_mean_uplift_r, "f"
            ),
            "extend_min_progress_fraction": format(
                self.extend_min_progress_fraction, "f"
            ),
        }


POLICIES = tuple(
    JourneyMemoryPolicy(
        extension_reference_fraction=extension,
        minimum_samples=samples,
        minimum_positive_rate=positive_rate,
        extend_min_mean_uplift_r=extend_ev,
        defend_min_mean_uplift_r=defend_ev,
        extend_min_progress_fraction=progress,
    )
    for extension in (Decimal("0.25"), Decimal("0.50"))
    for samples in (4, 8, 12)
    for positive_rate in (Decimal("0.55"), Decimal("0.65"))
    for extend_ev in (Decimal("0.10"), Decimal("0.25"))
    for defend_ev in (Decimal("0.10"), Decimal("0.25"))
    for progress in (Decimal("0.50"), Decimal("0.75"))
)


@dataclass(slots=True)
class ActionStats:
    count: int = 0
    total_uplift: Decimal = Decimal(0)
    positive: int = 0

    def add(self, uplift: Decimal) -> None:
        self.count += 1
        self.total_uplift += uplift
        if uplift > 0:
            self.positive += 1

    def view(self) -> dict[str, object]:
        return {
            "count": self.count,
            "mean_uplift_r": (
                None
                if self.count == 0
                else format(self.total_uplift / Decimal(self.count), "f")
            ),
            "positive_rate": (
                "0"
                if self.count == 0
                else format(Decimal(self.positive) / Decimal(self.count), "f")
            ),
        }


@dataclass(slots=True)
class JourneyMemory:
    exact: dict[tuple[str, ...], dict[str, ActionStats]]
    reduced: dict[tuple[str, ...], dict[str, ActionStats]]


def _bucket(value: Decimal, cuts: tuple[Decimal, ...], labels: tuple[str, ...]) -> str:
    for cut, label in zip(cuts, labels, strict=False):
        if value < cut:
            return label
    return labels[-1]


def _state_signature(
    *,
    row: dict[str, object],
    bars: list[object],
    setup: object,
    fill_index: int,
    current_index: int,
) -> tuple[tuple[str, ...], tuple[str, ...], dict[str, object]]:
    side = cast(str, row["side"])
    entry = cast(object, setup).entry_price
    risk = cast(object, setup).initial_risk
    target = cast(object, setup).target_price
    target_r = abs(target - entry) / risk
    observed = list(cast(tuple[object, ...], bars[fill_index : current_index + 1]))
    state = v1._recent_state(
        observed,
        side=side,
        entry=entry,
        risk=risk,
        window=5,
    )

    sign = v1._side_sign(side)
    _, high, low, close = v1._bar_values(bars[current_index])
    favorable_r = (
        (high - entry) / risk
        if side == "long"
        else (entry - low) / risk
    )
    progress_fraction = (
        Decimal(0) if target_r <= 0 else favorable_r / target_r
    )
    minutes = current_index - fill_index

    progress = _bucket(
        progress_fraction,
        (
            Decimal("0"),
            Decimal("0.25"),
            Decimal("0.50"),
            Decimal("0.75"),
            Decimal("1.00"),
        ),
        ("NEG", "P0_25", "P25_50", "P50_75", "P75_100", "GE100"),
    )
    close_bucket = _bucket(
        cast(Decimal, state["close_r"]),
        (
            Decimal("-0.50"),
            Decimal("0"),
            Decimal("0.50"),
            Decimal("1.00"),
        ),
        ("LT_M050", "M050_0", "0_050", "050_100", "GE100"),
    )
    efficiency_bucket = _bucket(
        cast(Decimal, state["efficiency"]),
        (
            Decimal("-0.25"),
            Decimal("0.25"),
            Decimal("0.55"),
        ),
        ("ADVERSE", "MIXED", "FAVORABLE", "STRONG"),
    )
    overlap_bucket = _bucket(
        cast(Decimal, state["overlap"]),
        (Decimal("0.40"), Decimal("0.75")),
        ("LOW", "MID", "HIGH"),
    )
    body_bucket = _bucket(
        cast(Decimal, state["signed_body_r"]),
        (
            Decimal("-0.40"),
            Decimal("-0.10"),
            Decimal("0.10"),
            Decimal("0.40"),
        ),
        ("ADV_STRONG", "ADV", "NEUTRAL", "FAV", "FAV_STRONG"),
    )
    time_bucket = (
        "0_5"
        if minutes <= 5
        else "6_15"
        if minutes <= 15
        else "16_30"
        if minutes <= 30
        else "GT30"
    )
    target_bucket = _bucket(
        target_r,
        (Decimal("1"), Decimal("2"), Decimal("3")),
        ("LT1", "1_2", "2_3", "GE3"),
    )
    peer = str(row.get("peer_consensus", "unavailable"))
    prior_regime = str(row.get("prior_nas100_regime", "unavailable"))
    mode = str(state["mode"])

    full = (
        side,
        str(row["entry_family"]),
        mode,
        progress,
        close_bucket,
        efficiency_bucket,
        overlap_bucket,
        body_bucket,
        time_bucket,
        target_bucket,
        peer,
        prior_regime,
    )
    reduced = (
        mode,
        progress,
        close_bucket,
        efficiency_bucket,
        overlap_bucket,
        body_bucket,
        time_bucket,
        target_bucket,
    )
    return full, reduced, {
        "mode": mode,
        "progress_fraction": format(progress_fraction, "f"),
        "close_r": format(cast(Decimal, state["close_r"]), "f"),
        "efficiency": format(cast(Decimal, state["efficiency"]), "f"),
        "overlap": format(cast(Decimal, state["overlap"]), "f"),
        "signed_body_r": format(cast(Decimal, state["signed_body_r"]), "f"),
        "minutes_since_fill": minutes,
        "target_r": format(target_r, "f"),
        "signed_close_delta_r": format(sign * (close - entry) / risk, "f"),
    }


def _fill_and_exit_indices(
    setup: object,
    day_bars: tuple[object, ...],
    row: dict[str, object],
) -> tuple[int, int]:
    fill_at = v3._dt(row["filled_at"])
    exit_at = v3._dt(row["exit_at"])
    fill = next(
        index
        for index, bar in enumerate(day_bars)
        if getattr(bar, "closed_at") == fill_at
    )
    exit_index = next(
        index
        for index, bar in enumerate(day_bars)
        if getattr(bar, "closed_at") == exit_at
    )
    return fill, exit_index


def _stop_at_snapshot(
    setup: object,
    day_bars: tuple[object, ...],
    fill_index: int,
    snapshot_index: int,
) -> Decimal:
    side = cast(object, setup).side.value
    current_stop = cast(object, setup).stop_price
    three_r = cast(object, setup).three_r_price
    for bar in day_bars[fill_index + 1 : snapshot_index + 1]:
        _, high, low, _ = v1._bar_values(bar)
        touched = high >= three_r if side == "long" else low <= three_r
        if touched:
            current_stop = cast(object, setup).entry_price
            break
    return current_stop


def _extension_counterfactual(
    *,
    setup: object,
    day_bars: tuple[object, ...],
    fill_index: int,
    snapshot_index: int,
    extension_fraction: Decimal,
) -> Decimal | None:
    if snapshot_index + 1 >= len(day_bars):
        return None
    side = cast(object, setup).side.value
    sign = v1._side_sign(side)
    entry = cast(object, setup).entry_price
    risk = cast(object, setup).initial_risk
    reference = cast(object, setup).source_setup.reference
    ref_width = reference.high - reference.low
    target = cast(object, setup).target_price + sign * ref_width * extension_fraction
    current_stop = _stop_at_snapshot(
        setup,
        day_bars,
        fill_index,
        snapshot_index,
    )
    be_armed = current_stop == entry

    for bar in day_bars[snapshot_index + 1 :]:
        if v1._local_minute(bar) >= v1.LIFECYCLE_MINUTE:
            break
        _, high, low, _ = v1._bar_values(bar)
        hit_stop = low <= current_stop if side == "long" else high >= current_stop
        hit_target = high >= target if side == "long" else low <= target
        if hit_stop and hit_target:
            return sign * (current_stop - entry) / risk
        if hit_stop:
            return sign * (current_stop - entry) / risk
        if hit_target:
            return abs(target - entry) / risk
        if not be_armed:
            touched_three_r = (
                high >= cast(object, setup).three_r_price
                if side == "long"
                else low <= cast(object, setup).three_r_price
            )
            if touched_three_r:
                be_armed = True
                current_stop = entry

    eligible = [
        bar
        for bar in day_bars[fill_index:]
        if v1._local_minute(bar) < v1.LIFECYCLE_MINUTE
    ]
    if not eligible:
        return None
    close = v1._bar_values(eligible[-1])[3]
    return sign * (close - entry) / risk


def _defend_counterfactual(
    *,
    setup: object,
    day_bars: tuple[object, ...],
    snapshot_index: int,
) -> Decimal | None:
    if snapshot_index + 1 >= len(day_bars):
        return None
    next_bar = day_bars[snapshot_index + 1]
    if v1._local_minute(next_bar) >= v1.LIFECYCLE_MINUTE:
        return None
    side = cast(object, setup).side.value
    sign = v1._side_sign(side)
    entry = cast(object, setup).entry_price
    risk = cast(object, setup).initial_risk
    opened = v1._bar_values(next_bar)[0]
    return sign * (opened - entry) / risk


def _add_stat(
    mapping: dict[tuple[str, ...], dict[str, ActionStats]],
    key: tuple[str, ...],
    action: str,
    uplift: Decimal,
) -> None:
    actions = mapping.setdefault(key, {})
    stats = actions.setdefault(action, ActionStats())
    stats.add(uplift)


def _build_memory(
    *,
    rows: list[dict[str, object]],
    paths: dict[str, tuple[object, tuple[object, ...]]],
    extension_fraction: Decimal,
) -> JourneyMemory:
    exact: dict[tuple[str, ...], dict[str, ActionStats]] = {}
    reduced: dict[tuple[str, ...], dict[str, ActionStats]] = {}

    for row in rows:
        signal = cast(str, row["signal_at"])
        setup, day_bars = paths[signal]
        fill_index, exit_index = _fill_and_exit_indices(setup, day_bars, row)
        baseline_r = v3._d(row["net_r_after_friction"])
        for snapshot_index in range(fill_index + 1, exit_index):
            full, small, _ = _state_signature(
                row=row,
                bars=list(day_bars),
                setup=setup,
                fill_index=fill_index,
                current_index=snapshot_index,
            )
            defense = _defend_counterfactual(
                setup=setup,
                day_bars=day_bars,
                snapshot_index=snapshot_index,
            )
            if defense is not None:
                uplift = (defense - FRICTION) - baseline_r
                _add_stat(exact, full, "DEFEND", uplift)
                _add_stat(reduced, small, "DEFEND", uplift)

            extension = _extension_counterfactual(
                setup=setup,
                day_bars=day_bars,
                fill_index=fill_index,
                snapshot_index=snapshot_index,
                extension_fraction=extension_fraction,
            )
            if extension is not None:
                uplift = (extension - FRICTION) - baseline_r
                _add_stat(exact, full, "EXTEND", uplift)
                _add_stat(reduced, small, "EXTEND", uplift)

    return JourneyMemory(exact=exact, reduced=reduced)


def _query(
    memory: JourneyMemory,
    full: tuple[str, ...],
    reduced: tuple[str, ...],
    action: str,
    minimum_samples: int,
) -> dict[str, object] | None:
    for scope, key in (("EXACT", full), ("REDUCED", reduced)):
        stats = (
            memory.exact.get(key, {}).get(action)
            if scope == "EXACT"
            else memory.reduced.get(key, {}).get(action)
        )
        if stats is None or stats.count < minimum_samples:
            continue
        view = stats.view()
        return {"scope": scope, **view}
    return None


def _simulate_with_memory(
    *,
    row: dict[str, object],
    setup: object,
    day_bars: tuple[object, ...],
    memory: JourneyMemory,
    policy: JourneyMemoryPolicy,
) -> dict[str, object]:
    fill_index, _ = _fill_and_exit_indices(setup, day_bars, row)
    side = cast(object, setup).side.value
    sign = v1._side_sign(side)
    entry = cast(object, setup).entry_price
    risk = cast(object, setup).initial_risk
    original_target = cast(object, setup).target_price
    reference = cast(object, setup).source_setup.reference
    ref_width = reference.high - reference.low
    extension_target = (
        original_target
        + sign * ref_width * policy.extension_reference_fraction
    )
    current_stop = cast(object, setup).stop_price
    active_target = original_target
    be_armed = False
    extended = False
    extension_pending = False
    defend_pending = False
    extend_signals = 0
    defend_signals = 0
    situation_counts: dict[str, int] = {}

    for index in range(fill_index + 1, len(day_bars)):
        bar = day_bars[index]
        if v1._local_minute(bar) >= v1.LIFECYCLE_MINUTE:
            break
        opened, high, low, _ = v1._bar_values(bar)

        if defend_pending:
            return {
                "r_multiple": format(sign * (opened - entry) / risk, "f"),
                "exit_reason": "MEMORY_DEFEND_NEXT_OPEN",
                "extend_signals": extend_signals,
                "defend_signals": defend_signals,
                "situation_counts": dict(sorted(situation_counts.items())),
            }
        if extension_pending:
            active_target = extension_target
            extended = True
            extension_pending = False

        hit_stop = low <= current_stop if side == "long" else high >= current_stop
        hit_target = high >= active_target if side == "long" else low <= active_target
        if hit_stop and hit_target:
            return {
                "r_multiple": format(sign * (current_stop - entry) / risk, "f"),
                "exit_reason": "MEMORY_STOP_FIRST_AMBIGUITY",
                "extend_signals": extend_signals,
                "defend_signals": defend_signals,
                "situation_counts": dict(sorted(situation_counts.items())),
            }
        if hit_stop:
            return {
                "r_multiple": format(sign * (current_stop - entry) / risk, "f"),
                "exit_reason": "MEMORY_STOP",
                "extend_signals": extend_signals,
                "defend_signals": defend_signals,
                "situation_counts": dict(sorted(situation_counts.items())),
            }
        if hit_target:
            return {
                "r_multiple": format(abs(active_target - entry) / risk, "f"),
                "exit_reason": (
                    "MEMORY_EXTENDED_TARGET"
                    if extended
                    else "MEMORY_ORIGINAL_TARGET"
                ),
                "extend_signals": extend_signals,
                "defend_signals": defend_signals,
                "situation_counts": dict(sorted(situation_counts.items())),
            }

        if not be_armed:
            touched_three_r = (
                high >= cast(object, setup).three_r_price
                if side == "long"
                else low <= cast(object, setup).three_r_price
            )
            if touched_three_r:
                be_armed = True
                current_stop = entry

        full, small, state = _state_signature(
            row=row,
            bars=list(day_bars),
            setup=setup,
            fill_index=fill_index,
            current_index=index,
        )
        mode = cast(str, state["mode"])
        situation_counts[mode] = situation_counts.get(mode, 0) + 1
        progress = v3._d(state["progress_fraction"])
        close_r = v3._d(state["close_r"])

        defense = _query(
            memory,
            full,
            small,
            "DEFEND",
            policy.minimum_samples,
        )
        extension = _query(
            memory,
            full,
            small,
            "EXTEND",
            policy.minimum_samples,
        )

        defense_ok = False
        defense_ev = Decimal("-999")
        if defense is not None:
            defense_ev = v3._d(cast(object, defense["mean_uplift_r"]))
            defense_ok = (
                close_r <= 0
                and defense_ev >= policy.defend_min_mean_uplift_r
                and v3._d(defense["positive_rate"]) >= policy.minimum_positive_rate
            )

        extension_ok = False
        extension_ev = Decimal("-999")
        if extension is not None and not extended and not extension_pending:
            extension_ev = v3._d(cast(object, extension["mean_uplift_r"]))
            extension_ok = (
                progress >= policy.extend_min_progress_fraction
                and close_r > 0
                and extension_ev >= policy.extend_min_mean_uplift_r
                and v3._d(extension["positive_rate"]) >= policy.minimum_positive_rate
            )

        if defense_ok and (not extension_ok or defense_ev >= extension_ev):
            defend_pending = True
            defend_signals += 1
        elif extension_ok:
            extension_pending = True
            extend_signals += 1

    eligible = [
        bar
        for bar in day_bars[fill_index:]
        if v1._local_minute(bar) < v1.LIFECYCLE_MINUTE
    ]
    if not eligible:
        raise ValueError("missing lifecycle close")
    close = v1._bar_values(eligible[-1])[3]
    return {
        "r_multiple": format(sign * (close - entry) / risk, "f"),
        "exit_reason": "MEMORY_LIFECYCLE",
        "extend_signals": extend_signals,
        "defend_signals": defend_signals,
        "situation_counts": dict(sorted(situation_counts.items())),
    }


def _evaluate(
    *,
    decision_history: list[dict[str, object]],
    journey_memory_rows: list[dict[str, object]],
    rows: list[dict[str, object]],
    memory_paths: dict[str, tuple[object, tuple[object, ...]]],
    evaluation_paths: dict[str, tuple[object, tuple[object, ...]]],
    policy: JourneyMemoryPolicy,
) -> dict[str, object]:
    memories = {
        name: decision._memory(decision_history, fields)
        for name, fields in decision.VIEWS.items()
    }
    journey_memory = _build_memory(
        rows=journey_memory_rows,
        paths=memory_paths,
        extension_fraction=policy.extension_reference_fraction,
    )

    baseline_values: list[Decimal] = []
    shared_values: list[Decimal] = []
    kept_baseline: list[Decimal] = []
    abstained: list[dict[str, object]] = []
    extension_trades = 0
    defense_trades = 0
    extension_uplift = Decimal(0)
    defense_uplift = Decimal(0)
    total_journey_uplift = Decimal(0)
    situations: dict[str, int] = {}

    for row in sorted(rows, key=lambda item: cast(str, item["signal_at"])):
        baseline_r = v3._d(row["net_r_after_friction"])
        baseline_values.append(baseline_r)
        pre = decision._decision(memories, row, v1.DECISION_POLICY)
        if pre["action"] == "ABSTAIN_SHADOW":
            abstained.append(row)
            continue

        signal = cast(str, row["signal_at"])
        setup, day_bars = evaluation_paths[signal]
        result = _simulate_with_memory(
            row=row,
            setup=setup,
            day_bars=day_bars,
            memory=journey_memory,
            policy=policy,
        )
        shared_r = v3._d(result["r_multiple"]) - FRICTION
        shared_values.append(shared_r)
        kept_baseline.append(baseline_r)
        uplift = shared_r - baseline_r
        total_journey_uplift += uplift

        if int(result["extend_signals"]) > 0:
            extension_trades += 1
            extension_uplift += uplift
        if int(result["defend_signals"]) > 0:
            defense_trades += 1
            defense_uplift += uplift
        for mode, count in cast(dict[str, int], result["situation_counts"]).items():
            situations[mode] = situations.get(mode, 0) + count

    baseline = v1._metrics_values(baseline_values)
    selected_baseline = v1._metrics_values(kept_baseline)
    shared = v1._metrics_values(shared_values)
    baseline_losses = int(baseline["losses"])
    baseline_wins = int(baseline["wins"])
    losses_avoided = sum(v3._d(row["net_r_after_friction"]) < 0 for row in abstained)
    winners_sacrificed = sum(v3._d(row["net_r_after_friction"]) > 0 for row in abstained)
    gross_winner_r = sum((value for value in baseline_values if value > 0), Decimal(0))
    winner_r_sacrificed = sum(
        (
            v3._d(row["net_r_after_friction"])
            for row in abstained
            if v3._d(row["net_r_after_friction"]) > 0
        ),
        Decimal(0),
    )

    return {
        "baseline": baseline,
        "selected_baseline_before_journey": selected_baseline,
        "shared_integrated": shared,
        "decision": {
            "input": len(rows),
            "kept": len(shared_values),
            "abstained": len(abstained),
            "losses_avoided": losses_avoided,
            "winners_sacrificed": winners_sacrificed,
            "loss_rejection_recall": (
                "0"
                if baseline_losses == 0
                else format(Decimal(losses_avoided) / Decimal(baseline_losses), "f")
            ),
            "winner_count_retention": (
                "0"
                if baseline_wins == 0
                else format(
                    Decimal(baseline_wins - winners_sacrificed)
                    / Decimal(baseline_wins),
                    "f",
                )
            ),
            "winner_r_retention": (
                "1"
                if gross_winner_r == 0
                else format(
                    (gross_winner_r - winner_r_sacrificed) / gross_winner_r,
                    "f",
                )
            ),
            "density_retained": (
                "0"
                if not rows
                else format(Decimal(len(shared_values)) / Decimal(len(rows)), "f")
            ),
        },
        "journey": {
            "extension_signaled_trades": extension_trades,
            "defense_signaled_trades": defense_trades,
            "extension_signaled_trade_uplift_r": format(extension_uplift, "f"),
            "defense_signaled_trade_uplift_r": format(defense_uplift, "f"),
            "all_journey_uplift_r_vs_kept_baseline": format(
                total_journey_uplift, "f"
            ),
            "situation_counts": dict(sorted(situations.items())),
        },
        "memory": {
            "exact_state_count": len(journey_memory.exact),
            "reduced_state_count": len(journey_memory.reduced),
        },
    }


def _gates(result: dict[str, object]) -> dict[str, bool]:
    return v1._gates(result)


def _score(result: dict[str, object]) -> Decimal | None:
    return v1._selection_score(result)


def run(
    *,
    r8_json: Path,
    r6_json: Path,
    r5_json: Path,
    daily_path: Path,
    r8_evidence: Path,
    r6_evidence: Path,
    r5_evidence: Path,
) -> dict[str, object]:
    daily = v3._load_daily(daily_path)
    r8 = v3._decorate(v3._load_trades(r8_json), daily)
    r6 = v3._decorate(v3._load_trades(r6_json), daily)
    r5 = v3._decorate(v3._load_trades(r5_json), daily)
    all_rows = r8 + r6 + r5
    if len(all_rows) != 822:
        raise AssertionError("challenge set drift")
    if sum(v3._d(row["net_r_after_friction"]) < 0 for row in all_rows) != 711:
        raise AssertionError("loss binding drift")
    if sum(v3._d(row["net_r_after_friction"]) > 0 for row in all_rows) != 111:
        raise AssertionError("winner binding drift")

    paths_r8 = cast(
        dict[str, tuple[object, tuple[object, ...]]],
        v1._reconstruct_partition(r8_evidence),
    )
    paths_r6 = cast(
        dict[str, tuple[object, tuple[object, ...]]],
        v1._reconstruct_partition(r6_evidence),
    )
    paths_r5 = cast(
        dict[str, tuple[object, tuple[object, ...]]],
        v1._reconstruct_partition(r5_evidence),
    )

    memory_cache: dict[str, JourneyMemory] = {}
    frontier: list[dict[str, object]] = []
    best: tuple[Decimal, JourneyMemoryPolicy] | None = None

    # _evaluate builds the memory internally. Cache by extension fraction by
    # temporarily memoizing its expensive historical memory after first use.
    original_builder = _build_memory

    for policy in POLICIES:
        cache_key = format(policy.extension_reference_fraction, "f")

        def cached_builder(
            *,
            rows: list[dict[str, object]],
            paths: dict[str, tuple[object, tuple[object, ...]]],
            extension_fraction: Decimal,
        ) -> JourneyMemory:
            if cache_key not in memory_cache:
                memory_cache[cache_key] = original_builder(
                    rows=rows,
                    paths=paths,
                    extension_fraction=extension_fraction,
                )
            return memory_cache[cache_key]

        globals()["_build_memory"] = cached_builder
        calibration = _evaluate(
            decision_history=r8,
            journey_memory_rows=r8,
            rows=r6,
            memory_paths=paths_r8,
            evaluation_paths=paths_r6,
            policy=policy,
        )
        gates = _gates(calibration)
        score = _score(calibration)
        frontier.append(
            {
                "policy": policy.payload(),
                "calibration": calibration,
                "gates": gates,
                "selection_score": None if score is None else format(score, "f"),
            }
        )
        if score is not None and (best is None or score > best[0]):
            best = (score, policy)

    globals()["_build_memory"] = original_builder

    if best is None:
        return {
            "schema": SCHEMA,
            "identity": IDENTITY,
            "economic_status": "FALSIFIED_IN_CALIBRATION",
            "challenge_set": {"trades": 822, "losses": 711, "wins": 111},
            "decision_policy": v1.DECISION_POLICY.payload(),
            "frozen_journey_memory_policy": None,
            "evaluation": None,
            "gates": None,
            "passes_shared": False,
            "frontier": frontier,
            "governance": {
                "counterfactual_labels_historical_only": True,
                "current_trade_future_used": False,
                "target_extension_effective_next_bar": True,
                "loss_defense_effective_next_bar": True,
                "capital_risk_weighting_used": False,
                "r5_retuned": False,
                "shared_order_authority": False,
                "shared_risk_authority": False,
                "shared_execution_authority": False,
                "live_authorized": False,
                "merge_authorized": False,
            },
        }

    frozen = best[1]
    evaluation = _evaluate(
        decision_history=r8 + r6,
        journey_memory_rows=r8 + r6,
        rows=r5,
        memory_paths={**paths_r8, **paths_r6},
        evaluation_paths=paths_r5,
        policy=frozen,
    )
    gates = _gates(evaluation)
    passed = all(gates.values())
    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "economic_status": (
            "PASSED_TEMPORAL_EVALUATION" if passed else "FALSIFIED_ON_R5"
        ),
        "challenge_set": {"trades": 822, "losses": 711, "wins": 111},
        "temporal_protocol": {
            "r8": "CLOSED_COUNTERFACTUAL_MEMORY",
            "r6": "CALIBRATION_AND_POLICY_FREEZE",
            "r5": "NO_RETUNE_EVALUATION",
        },
        "decision_policy": v1.DECISION_POLICY.payload(),
        "frozen_journey_memory_policy": frozen.payload(),
        "evaluation": evaluation,
        "gates": gates,
        "passes_shared": passed,
        "frontier": frontier,
        "governance": {
            "counterfactual_labels_historical_only": True,
            "current_trade_future_used": False,
            "target_extension_effective_next_bar": True,
            "loss_defense_effective_next_bar": True,
            "capital_risk_weighting_used": False,
            "r5_retuned": False,
            "shared_order_authority": False,
            "shared_risk_authority": False,
            "shared_execution_authority": False,
            "live_authorized": False,
            "merge_authorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--r8-json", type=Path, required=True)
    parser.add_argument("--r6-json", type=Path, required=True)
    parser.add_argument("--r5-json", type=Path, required=True)
    parser.add_argument("--daily-path", type=Path, required=True)
    parser.add_argument("--r8-evidence", type=Path, required=True)
    parser.add_argument("--r6-evidence", type=Path, required=True)
    parser.add_argument("--r5-evidence", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = run(
        r8_json=args.r8_json,
        r6_json=args.r6_json,
        r5_json=args.r5_json,
        daily_path=args.daily_path,
        r8_evidence=args.r8_evidence,
        r6_evidence=args.r6_evidence,
        r5_evidence=args.r5_evidence,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    print(
        json.dumps(
            {
                "economic_status": payload["economic_status"],
                "passes_shared": payload["passes_shared"],
                "frozen_journey_memory_policy": payload[
                    "frozen_journey_memory_policy"
                ],
                "evaluation": payload["evaluation"],
                "gates": payload["gates"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
