"""Integrated Shared intelligence falsification for VT31 NAS100.

This is Phase A Shared intelligence only:
1) pre-entry decision intelligence,
2) live market-situation recognition,
3) causal position-journey intelligence (EXTEND / HOLD / DEFEND).

Capital potentiation and risk weighting are forbidden.

Temporal protocol:
- R8 = historical memory for decision intelligence.
- R6 = calibrate/freeze one integrated Shared policy.
- R5 = no-retune temporal evaluation.

Journey actions are causal:
- EXTEND can only be armed from a CLOSED M1 before the original target is hit,
  and becomes effective on the next M1.
- DEFEND can only be armed from a CLOSED M1 anomaly/deterioration state and
  becomes effective at the next M1 open.
- No future bar, terminal PnL, MFE/MAE outcome label or fold identity may be a
  current decision input.
"""
# ruff: noqa: B009
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

import vt31_core_stack_v3_analog_world_model_v1 as v3
import vt31_core_stack_v3_shared_decision_intelligence_v2 as decision
import vt31_nas100_r1_candidate as baseline
import vt31_nas100_silver_bullet_native_streak_falsification_v1 as native
import vt31_nas100_specialist_r1_candidate as specialist

from qore.infrastructure.traders.vt31_silver_bullet_r2_2 import (
    Vt31R22ExecutableSetup,
    Vt31R22ExecutionPolicy,
    evaluate_vt31_r2_2_source,
    make_executable_setup,
)

SCHEMA = "qore.core_stack_v3.vt31.integrated_shared_intelligence.v1"
IDENTITY = "VT31_NAS100_INTEGRATED_SHARED_INTELLIGENCE_PHASE_A_V1"
FRICTION = Decimal("0.05")
LIFECYCLE_MINUTE = 16 * 60

# Frozen from the best Phase-A-V2 R6 near-miss. It passed 5/6 hard gates and
# failed only PF +25%. It is not retuned on R5.
DECISION_POLICY = decision.Policy(
    maximum_analogs=32,
    minimum_similarity_bps=6500,
    minimum_confidence_bps=2500,
    abstain_ev_r=Decimal("-0.10"),
    required_negative_views=2,
    maximum_positive_views=0,
    winner_archetype_ev_floor=Decimal("0.30"),
    winner_archetype_payoff_floor=Decimal("2.5"),
    tail_mean_win_r_floor=Decimal("4.5"),
    tail_payoff_floor=Decimal("3"),
    tail_min_win_rate=Decimal("0.12"),
)


@dataclass(frozen=True, slots=True)
class JourneyPolicy:
    window_bars: int
    extend_progress_fraction: Decimal
    extend_efficiency_min: Decimal
    extend_overlap_max: Decimal
    extension_reference_fraction: Decimal
    defend_close_r: Decimal
    defend_body_r: Decimal
    defend_confirmations: int

    def payload(self) -> dict[str, object]:
        return {
            "window_bars": self.window_bars,
            "extend_progress_fraction": format(
                self.extend_progress_fraction, "f"
            ),
            "extend_efficiency_min": format(
                self.extend_efficiency_min, "f"
            ),
            "extend_overlap_max": format(
                self.extend_overlap_max, "f"
            ),
            "extension_reference_fraction": format(
                self.extension_reference_fraction, "f"
            ),
            "defend_close_r": format(self.defend_close_r, "f"),
            "defend_body_r": format(self.defend_body_r, "f"),
            "defend_confirmations": self.defend_confirmations,
        }


JOURNEY_POLICIES = tuple(
    JourneyPolicy(
        window_bars=window,
        extend_progress_fraction=progress,
        extend_efficiency_min=efficiency,
        extend_overlap_max=overlap,
        extension_reference_fraction=extension,
        defend_close_r=defend_close,
        defend_body_r=defend_body,
        defend_confirmations=confirmations,
    )
    for window in (3, 5)
    for progress in (Decimal("0.60"), Decimal("0.75"))
    for efficiency in (Decimal("0.45"), Decimal("0.60"))
    for overlap in (Decimal("0.70"), Decimal("0.85"))
    for extension in (Decimal("0.25"), Decimal("0.50"))
    for defend_close in (Decimal("-0.15"), Decimal("-0.30"))
    for defend_body in (Decimal("0.25"), Decimal("0.40"))
    for confirmations in (1, 2)
)


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _side_sign(side: str) -> Decimal:
    if side == "long":
        return Decimal(1)
    if side == "short":
        return Decimal(-1)
    raise ValueError(f"unsupported side {side}")


def _bar_values(bar: object) -> tuple[Decimal, Decimal, Decimal, Decimal]:
    return (
        _d(getattr(bar, "open")),
        _d(getattr(bar, "high")),
        _d(getattr(bar, "low")),
        _d(getattr(bar, "close")),
    )


def _touch(bar: object, level: Decimal) -> bool:
    _, high, low, _ = _bar_values(bar)
    return low <= level <= high


def _local_minute(bar: object) -> int:
    return baseline._local_minute(bar)


def _reconstruct_partition(
    evidence_path: Path,
) -> dict[str, tuple[Vt31R22ExecutableSetup, tuple[object, ...]]]:
    series, _, evidence, _, _, _ = native.load_market_evidence(evidence_path)
    grouped: dict[date, list[object]] = defaultdict(list)
    for bar in series:
        grouped[native._day(getattr(bar, "opened_at"))].append(bar)

    result: dict[str, tuple[Vt31R22ExecutableSetup, tuple[object, ...]]] = {}
    policy = Vt31R22ExecutionPolicy()
    for local_day in sorted(grouped):
        day_bars = tuple(
            sorted(grouped[local_day], key=lambda item: getattr(item, "opened_at"))
        )
        reference = specialist._slice(day_bars, (9, 0, 0), (10, 0, 0))
        session = specialist._slice(day_bars, (10, 0, 0), (11, 0, 0))
        if len(reference) != 60 or len(session) != 60:
            continue
        prefix = list(reference)
        selected: Vt31R22ExecutableSetup | None = None
        for bar in session:
            prefix.append(bar)
            evaluation = evaluate_vt31_r2_2_source(
                instrument=getattr(bar, "instrument"),
                as_of=cast(datetime, getattr(bar, "closed_at")),
                m1_candles=cast(Any, tuple(prefix)),
                evidence_fingerprint=evidence,
            )
            if evaluation.setup is None:
                if evaluation.both_sides_swept:
                    break
                continue
            executable, _ = make_executable_setup(evaluation.setup, policy)
            if executable is None:
                break
            selected = executable
            break
        if selected is None:
            continue
        outcome = baseline._simulate(day_bars, selected)
        if outcome.get("status") != "terminal":
            continue
        signal = selected.decision_at.astimezone(UTC).isoformat()
        result[signal] = (selected, day_bars)
    return result


def _recent_state(
    bars: list[object],
    *,
    side: str,
    entry: Decimal,
    risk: Decimal,
    window: int,
) -> dict[str, Decimal | str]:
    recent = bars[-window:]
    sign = _side_sign(side)
    if len(recent) < 2:
        return {
            "mode": "UNRESOLVED",
            "efficiency": Decimal(0),
            "overlap": Decimal(1),
            "signed_body_r": Decimal(0),
            "close_r": Decimal(0),
        }

    closes = [_bar_values(bar)[3] for bar in recent]
    travel = sum(
        (abs(right - left) for left, right in zip(closes, closes[1:], strict=False)),
        Decimal(0),
    )
    signed_net = sign * (closes[-1] - closes[0])
    efficiency = Decimal(0) if travel == 0 else signed_net / travel

    overlaps: list[Decimal] = []
    for left, right in zip(recent, recent[1:], strict=False):
        _, lh, ll, _ = _bar_values(left)
        _, rh, rl, _ = _bar_values(right)
        overlap = max(Decimal(0), min(lh, rh) - max(ll, rl))
        denom = min(lh - ll, rh - rl)
        overlaps.append(Decimal(0) if denom <= 0 else min(Decimal(1), overlap / denom))
    overlap_rate = (
        Decimal(1)
        if not overlaps
        else sum(overlaps, Decimal(0)) / Decimal(len(overlaps))
    )

    opened, _, _, closed = _bar_values(recent[-1])
    signed_body_r = sign * (closed - opened) / risk
    close_r = sign * (closed - entry) / risk

    if efficiency >= Decimal("0.55") and overlap_rate <= Decimal("0.75"):
        mode = "TREND"
    elif abs(efficiency) <= Decimal("0.20") or overlap_rate >= Decimal("0.90"):
        mode = "RANGE"
    elif signed_body_r <= Decimal("-0.40"):
        mode = "ANOMALOUS"
    else:
        mode = "TRANSITION"
    return {
        "mode": mode,
        "efficiency": efficiency,
        "overlap": overlap_rate,
        "signed_body_r": signed_body_r,
        "close_r": close_r,
    }


def _adverse_confirmation_count(
    bars: list[object],
    *,
    side: str,
    risk: Decimal,
    body_threshold: Decimal,
) -> int:
    sign = _side_sign(side)
    count = 0
    for bar in reversed(bars):
        opened, _, _, closed = _bar_values(bar)
        signed_body = sign * (closed - opened) / risk
        if signed_body <= -body_threshold:
            count += 1
        else:
            break
    return count


def _simulate_shared_journey(
    setup: Vt31R22ExecutableSetup,
    day_bars: tuple[object, ...],
    policy: JourneyPolicy,
) -> dict[str, object]:
    side = setup.side.value
    sign = _side_sign(side)
    entry = setup.entry_price
    initial_stop = setup.stop_price
    original_target = setup.target_price
    risk = setup.initial_risk
    ref_width = (
        setup.source_setup.reference.high
        - setup.source_setup.reference.low
    )
    if risk <= 0 or ref_width <= 0:
        raise ValueError("invalid journey geometry")

    fill_index: int | None = None
    for index, bar in enumerate(day_bars):
        if getattr(bar, "opened_at") < setup.decision_at:
            continue
        if _local_minute(bar) >= 11 * 60:
            break
        if _touch(bar, entry):
            fill_index = index
            break
    if fill_index is None:
        raise ValueError("expected filled terminal trade")

    first = day_bars[fill_index]
    _, first_high, first_low, _ = _bar_values(first)
    first_stop = first_low <= initial_stop if side == "long" else first_high >= initial_stop
    first_target = first_high >= original_target if side == "long" else first_low <= original_target
    if first_stop or first_target:
        raise ValueError("challenge trade cannot be censored on fill bar")

    extension_target = (
        original_target
        + sign * ref_width * policy.extension_reference_fraction
    )
    active_target = original_target
    current_stop = initial_stop
    be_armed = False
    extension_pending = False
    extended = False
    defend_pending = False
    observed: list[object] = [first]
    max_favorable_r = Decimal(0)
    extend_signals = 0
    defend_signals = 0
    situation_counts: dict[str, int] = {}

    for index in range(fill_index + 1, len(day_bars)):
        bar = day_bars[index]
        if _local_minute(bar) >= LIFECYCLE_MINUTE:
            break

        opened, high, low, close = _bar_values(bar)

        # Decisions from the prior CLOSED M1 are effective at this M1 open.
        if defend_pending:
            terminal = sign * (opened - entry) / risk
            return {
                "r_multiple": format(terminal, "f"),
                "exit_reason": "SHARED_DEFEND_NEXT_OPEN",
                "extended": extended,
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
            terminal = sign * (current_stop - entry) / risk
            return {
                "r_multiple": format(terminal, "f"),
                "exit_reason": "SHARED_STOP_FIRST_AMBIGUITY",
                "extended": extended,
                "extend_signals": extend_signals,
                "defend_signals": defend_signals,
                "situation_counts": dict(sorted(situation_counts.items())),
            }
        if hit_stop:
            terminal = sign * (current_stop - entry) / risk
            return {
                "r_multiple": format(terminal, "f"),
                "exit_reason": (
                    "SHARED_BREAKEVEN_STOP"
                    if current_stop == entry
                    else "SHARED_INITIAL_STOP"
                ),
                "extended": extended,
                "extend_signals": extend_signals,
                "defend_signals": defend_signals,
                "situation_counts": dict(sorted(situation_counts.items())),
            }
        if hit_target:
            terminal = abs(active_target - entry) / risk
            return {
                "r_multiple": format(terminal, "f"),
                "exit_reason": (
                    "SHARED_EXTENDED_TARGET"
                    if extended
                    else "SHARED_ORIGINAL_TARGET"
                ),
                "extended": extended,
                "extend_signals": extend_signals,
                "defend_signals": defend_signals,
                "situation_counts": dict(sorted(situation_counts.items())),
            }

        favorable = sign * (
            (high - entry) if side == "long" else (entry - low)
        ) / risk
        max_favorable_r = max(max_favorable_r, favorable)

        if not be_armed:
            touched_three_r = (
                high >= setup.three_r_price
                if side == "long"
                else low <= setup.three_r_price
            )
            if touched_three_r:
                be_armed = True
                current_stop = entry

        observed.append(bar)
        state = _recent_state(
            observed,
            side=side,
            entry=entry,
            risk=risk,
            window=policy.window_bars,
        )
        mode = str(state["mode"])
        situation_counts[mode] = situation_counts.get(mode, 0) + 1

        adverse_count = _adverse_confirmation_count(
            observed,
            side=side,
            risk=risk,
            body_threshold=policy.defend_body_r,
        )
        if (
            _d(state["close_r"]) <= policy.defend_close_r
            and _d(state["signed_body_r"]) <= -policy.defend_body_r
            and adverse_count >= policy.defend_confirmations
        ):
            defend_pending = True
            defend_signals += 1
            continue

        target_r = abs(original_target - entry) / risk
        if (
            not extended
            and not extension_pending
            and max_favorable_r >= target_r * policy.extend_progress_fraction
            and _d(state["efficiency"]) >= policy.extend_efficiency_min
            and _d(state["overlap"]) <= policy.extend_overlap_max
            and _d(state["close_r"]) > 0
            and mode in {"TREND", "TRANSITION"}
        ):
            extension_pending = True
            extend_signals += 1

    eligible = [
        bar
        for bar in day_bars[fill_index:]
        if _local_minute(bar) < LIFECYCLE_MINUTE
    ]
    if not eligible:
        raise ValueError("missing lifecycle close")
    close = _bar_values(eligible[-1])[3]
    terminal = sign * (close - entry) / risk
    return {
        "r_multiple": format(terminal, "f"),
        "exit_reason": "SHARED_LIFECYCLE",
        "extended": extended,
        "extend_signals": extend_signals,
        "defend_signals": defend_signals,
        "situation_counts": dict(sorted(situation_counts.items())),
    }


def _metrics_values(values: list[Decimal]) -> dict[str, object]:
    gains = sum((value for value in values if value > 0), Decimal(0))
    losses = -sum((value for value in values if value < 0), Decimal(0))
    total = sum(values, Decimal(0))
    equity = peak = dd = Decimal(0)
    streak = max_streak = 0
    for value in values:
        equity += value
        peak = max(peak, equity)
        dd = max(dd, peak - equity)
        if value < 0:
            streak += 1
            max_streak = max(max_streak, streak)
        else:
            streak = 0
    return {
        "sample": len(values),
        "wins": sum(value > 0 for value in values),
        "losses": sum(value < 0 for value in values),
        "profit_factor": None if losses == 0 else format(gains / losses, "f"),
        "total_r": format(total, "f"),
        "mean_r": (
            "0" if not values else format(total / Decimal(len(values)), "f")
        ),
        "max_drawdown_r": format(dd, "f"),
        "max_losing_streak": max_streak,
    }


def _evaluate(
    *,
    history: list[dict[str, object]],
    rows: list[dict[str, object]],
    paths: dict[str, tuple[Vt31R22ExecutableSetup, tuple[object, ...]]],
    policy: JourneyPolicy,
) -> dict[str, object]:
    memories = {
        name: decision._memory(history, fields)
        for name, fields in decision.VIEWS.items()
    }
    baseline_values: list[Decimal] = []
    shared_values: list[Decimal] = []
    kept_baseline_values: list[Decimal] = []
    abstained: list[dict[str, object]] = []
    kept_rows: list[dict[str, object]] = []
    extension_trades = 0
    defense_trades = 0
    extension_uplift = Decimal(0)
    defense_uplift = Decimal(0)
    action_uplift = Decimal(0)
    situation_counts: dict[str, int] = {}

    for source in sorted(rows, key=lambda row: cast(str, row["signal_at"])):
        baseline_r = _d(source["net_r_after_friction"])
        baseline_values.append(baseline_r)
        view = decision._decision(memories, source, DECISION_POLICY)
        if view["action"] == "ABSTAIN_SHADOW":
            abstained.append(source)
            continue

        signal = cast(str, source["signal_at"])
        if signal not in paths:
            raise AssertionError(f"missing causal M1 path for {signal}")
        setup, day_bars = paths[signal]
        journey = _simulate_shared_journey(setup, day_bars, policy)
        shared_r = _d(journey["r_multiple"]) - FRICTION
        shared_values.append(shared_r)
        kept_baseline_values.append(baseline_r)
        kept_rows.append(source)

        uplift = shared_r - baseline_r
        action_uplift += uplift
        if int(journey["extend_signals"]) > 0:
            extension_trades += 1
            extension_uplift += uplift
        if int(journey["defend_signals"]) > 0:
            defense_trades += 1
            defense_uplift += uplift
        for mode, count in cast(dict[str, int], journey["situation_counts"]).items():
            situation_counts[mode] = situation_counts.get(mode, 0) + count

    baseline = _metrics_values(baseline_values)
    shared = _metrics_values(shared_values)
    selected_baseline = _metrics_values(kept_baseline_values)
    baseline_losses = int(baseline["losses"])
    baseline_wins = int(baseline["wins"])
    losses_avoided = sum(_d(row["net_r_after_friction"]) < 0 for row in abstained)
    winners_sacrificed = sum(_d(row["net_r_after_friction"]) > 0 for row in abstained)
    gross_winner_r = sum(
        (value for value in baseline_values if value > 0),
        Decimal(0),
    )
    winner_r_sacrificed = sum(
        (
            _d(row["net_r_after_friction"])
            for row in abstained
            if _d(row["net_r_after_friction"]) > 0
        ),
        Decimal(0),
    )

    return {
        "baseline": baseline,
        "selected_baseline_before_journey": selected_baseline,
        "shared_integrated": shared,
        "decision": {
            "input": len(rows),
            "kept": len(kept_rows),
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
                else format(Decimal(len(kept_rows)) / Decimal(len(rows)), "f")
            ),
        },
        "journey": {
            "extension_signaled_trades": extension_trades,
            "defense_signaled_trades": defense_trades,
            "extension_signaled_trade_uplift_r": format(extension_uplift, "f"),
            "defense_signaled_trade_uplift_r": format(defense_uplift, "f"),
            "all_journey_uplift_r_vs_kept_baseline": format(action_uplift, "f"),
            "situation_counts": dict(sorted(situation_counts.items())),
        },
    }


def _gates(result: dict[str, object]) -> dict[str, bool]:
    baseline = cast(dict[str, object], result["baseline"])
    shared = cast(dict[str, object], result["shared_integrated"])
    decision_result = cast(dict[str, object], result["decision"])
    journey = cast(dict[str, object], result["journey"])
    if baseline["profit_factor"] is None or shared["profit_factor"] is None:
        return {
            "pf_plus_25pct": False,
            "dd_minus_30pct": False,
            "total_r_not_lower": False,
            "loss_recall_at_least_25pct": False,
            "winner_count_retention_at_least_80pct": False,
            "winner_r_retention_at_least_90pct": False,
            "density_at_least_55pct": False,
            "extension_demonstrated_positive_uplift": False,
            "defense_demonstrated_positive_uplift": False,
        }
    bpf = _d(cast(object, baseline["profit_factor"]))
    spf = _d(cast(object, shared["profit_factor"]))
    bdd = _d(baseline["max_drawdown_r"])
    sdd = _d(shared["max_drawdown_r"])
    return {
        "pf_plus_25pct": spf >= bpf * Decimal("1.25"),
        "dd_minus_30pct": sdd <= bdd * Decimal("0.70"),
        "total_r_not_lower": _d(shared["total_r"]) >= _d(baseline["total_r"]),
        "loss_recall_at_least_25pct": (
            _d(decision_result["loss_rejection_recall"]) >= Decimal("0.25")
        ),
        "winner_count_retention_at_least_80pct": (
            _d(decision_result["winner_count_retention"]) >= Decimal("0.80")
        ),
        "winner_r_retention_at_least_90pct": (
            _d(decision_result["winner_r_retention"]) >= Decimal("0.90")
        ),
        "density_at_least_55pct": (
            _d(decision_result["density_retained"]) >= Decimal("0.55")
        ),
        "extension_demonstrated_positive_uplift": (
            int(journey["extension_signaled_trades"]) > 0
            and _d(journey["extension_signaled_trade_uplift_r"]) > 0
        ),
        "defense_demonstrated_positive_uplift": (
            int(journey["defense_signaled_trades"]) > 0
            and _d(journey["defense_signaled_trade_uplift_r"]) > 0
        ),
    }


def _selection_score(result: dict[str, object]) -> Decimal | None:
    gates = _gates(result)
    if not all(gates.values()):
        return None
    baseline = cast(dict[str, object], result["baseline"])
    shared = cast(dict[str, object], result["shared_integrated"])
    bpf = _d(cast(object, baseline["profit_factor"]))
    spf = _d(cast(object, shared["profit_factor"]))
    bdd = _d(baseline["max_drawdown_r"])
    sdd = _d(shared["max_drawdown_r"])
    return (
        (spf / bpf)
        * (bdd / max(sdd, Decimal("0.000001")))
        * (_d(shared["total_r"]) / max(_d(baseline["total_r"]), Decimal("0.000001")))
    )


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
        raise AssertionError("VT31 challenge set drift")
    if sum(_d(row["net_r_after_friction"]) < 0 for row in all_rows) != 711:
        raise AssertionError("VT31 loss binding drift")
    if sum(_d(row["net_r_after_friction"]) > 0 for row in all_rows) != 111:
        raise AssertionError("VT31 winner binding drift")

    paths_r8 = _reconstruct_partition(r8_evidence)
    paths_r6 = _reconstruct_partition(r6_evidence)
    paths_r5 = _reconstruct_partition(r5_evidence)
    if not all(cast(str, row["signal_at"]) in paths_r8 for row in r8):
        raise AssertionError("R8 source-path reconstruction drift")
    if not all(cast(str, row["signal_at"]) in paths_r6 for row in r6):
        raise AssertionError("R6 source-path reconstruction drift")
    if not all(cast(str, row["signal_at"]) in paths_r5 for row in r5):
        raise AssertionError("R5 source-path reconstruction drift")

    frontier: list[dict[str, object]] = []
    best: tuple[Decimal, JourneyPolicy] | None = None
    for policy in JOURNEY_POLICIES:
        calibration = _evaluate(
            history=r8,
            rows=r6,
            paths=paths_r6,
            policy=policy,
        )
        gates = _gates(calibration)
        score = _selection_score(calibration)
        frontier.append(
            {
                "journey_policy": policy.payload(),
                "calibration": calibration,
                "gates": gates,
                "selection_score": None if score is None else format(score, "f"),
            }
        )
        if score is not None and (best is None or score > best[0]):
            best = (score, policy)

    if best is None:
        return {
            "schema": SCHEMA,
            "identity": IDENTITY,
            "research_phase": "PHASE_A_SHARED_INTELLIGENCE",
            "capital_potentiator_status": "DEFERRED_BLOCKED",
            "economic_status": "FALSIFIED_IN_CALIBRATION",
            "challenge_set": {"trades": 822, "losses": 711, "wins": 111},
            "decision_policy": DECISION_POLICY.payload(),
            "frozen_journey_policy": None,
            "evaluation": None,
            "gates": None,
            "passes_integrated_shared": False,
            "frontier": frontier,
            "governance": {
                "capital_risk_weighting_used": False,
                "target_extension_is_causal_next_bar": True,
                "loss_defense_is_causal_next_bar": True,
                "future_path_used_for_current_decision": False,
                "current_terminal_outcome_used_for_current_decision": False,
                "r5_retuned": False,
                "shared_order_authority": False,
                "shared_risk_authority": False,
                "shared_execution_authority": False,
                "stop_widening_allowed": False,
                "live_authorized": False,
                "merge_authorized": False,
            },
        }

    frozen = best[1]
    evaluation = _evaluate(
        history=r8 + r6,
        rows=r5,
        paths=paths_r5,
        policy=frozen,
    )
    gates = _gates(evaluation)
    passed = all(gates.values())
    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "research_phase": "PHASE_A_SHARED_INTELLIGENCE",
        "capital_potentiator_status": "DEFERRED_BLOCKED",
        "economic_status": (
            "PASSED_TEMPORAL_EVALUATION"
            if passed
            else "FALSIFIED_ON_R5"
        ),
        "challenge_set": {"trades": 822, "losses": 711, "wins": 111},
        "temporal_protocol": {
            "r8": "DECISION_MEMORY_DISCOVERY",
            "r6": "INTEGRATED_SHARED_CALIBRATION_AND_FREEZE",
            "r5": "NO_RETUNE_TEMPORAL_EVALUATION",
        },
        "decision_policy": DECISION_POLICY.payload(),
        "frozen_journey_policy": frozen.payload(),
        "evaluation": evaluation,
        "gates": gates,
        "passes_integrated_shared": passed,
        "frontier": frontier,
        "governance": {
            "capital_risk_weighting_used": False,
            "target_extension_is_causal_next_bar": True,
            "loss_defense_is_causal_next_bar": True,
            "future_path_used_for_current_decision": False,
            "current_terminal_outcome_used_for_current_decision": False,
            "historical_closed_outcomes_allowed_for_memory": True,
            "r5_retuned": False,
            "shared_order_authority": False,
            "shared_risk_authority": False,
            "shared_execution_authority": False,
            "stop_widening_allowed": False,
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
                "passes_integrated_shared": payload["passes_integrated_shared"],
                "frozen_journey_policy": payload["frozen_journey_policy"],
                "evaluation": payload["evaluation"],
                "gates": payload["gates"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
