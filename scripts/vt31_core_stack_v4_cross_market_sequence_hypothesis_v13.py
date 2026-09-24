"""VT31 Shared cross-market sequence hypothesis V13.

Adds genuinely new decision-time information after V12 proved that the existing
NAS100 + compact peer features cannot preserve >=90% winner-R on R6.

For NAS100, SP500 and US30, V13 reconstructs only CLOSED M1 bars observable at
signal_at and derives:
- short/medium directional state relative to the VT31 side;
- directional acceleration / reversal;
- current aligned/adverse run onset and age;
- SP500/US30 confirmation latency and leader;
- peer divergence duration and convergence;
- three-index breadth;
- causal liquidity-room context on NAS100.

The V8 negative-memory screen remains secondary. The N1 conditional hypothesis
uses coarse single-fact likelihoods learned offline on R8. No exact-state
lookup, nearest neighbor, future candle, sizing, Risk or execution authority.

R8 = discovery, R6 = calibration + freeze, R5 = untouched evaluation only
after every R6 hard gate passes.
"""
# ruff: noqa: B009,E501,I001
from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_core_stack_v4_n1_conditional_hypothesis_v12 as v12
import vt31_core_stack_v4_perception_first_v2 as v2
import vt31_core_stack_v4_perception_sequence_topology_v8 as v8
import vt31_core_stack_v4_perception_state_model_v5 as v5
from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_5_multi_index_research import (
    _day,
    _wall,
    load_market_evidence,
)

SCHEMA = "qore.core_stack_v4.vt31.cross_market_sequence_hypothesis.v13"
IDENTITY = "VT31_NAS100_SHARED_CROSS_MARKET_SEQUENCE_HYPOTHESIS_V13"
ZERO = Decimal("0")

CHANNELS: dict[str, tuple[str, ...]] = {
    **v12.CHANNELS,
    "CROSS_SEQUENCE": (
        "sp500_move3_bin",
        "sp500_move10_bin",
        "sp500_transition",
        "sp500_run_state",
        "sp500_run_age",
        "us30_move3_bin",
        "us30_move10_bin",
        "us30_transition",
        "us30_run_state",
        "us30_run_age",
        "peer_sync3",
        "peer_confirmation_latency",
        "peer_sequence_leader",
        "peer_divergence_age",
        "breadth3",
        "breadth10",
        "breadth_transition",
    ),
    "LIQUIDITY_ROOM": (
        "destination_room_ref_bin",
        "reference_room_ref_bin",
        "prior_range_location_causal",
    ),
}


@dataclass(frozen=True, slots=True)
class Policy:
    score_threshold: float
    minimum_supportive_channels: int
    maximum_adverse_channels: int
    minimum_cross_sequence_score: float
    rescue_n2_threshold: float | None

    def payload(self) -> dict[str, object]:
        return {
            "score_threshold": self.score_threshold,
            "minimum_supportive_channels": self.minimum_supportive_channels,
            "maximum_adverse_channels": self.maximum_adverse_channels,
            "minimum_cross_sequence_score": self.minimum_cross_sequence_score,
            "rescue_n2_threshold": self.rescue_n2_threshold,
        }


POLICIES = tuple(
    Policy(threshold, min_support, max_adverse, cross_floor, rescue_n2)
    for threshold in (-0.50, 0.0, 0.50, 1.0, 1.50, 2.0, 2.50, 3.0)
    for min_support in (1, 2, 3, 4)
    for max_adverse in (1, 2, 3, 4, 7)
    for cross_floor in (-99.0, -0.25, 0.0, 0.25, 0.50)
    for rescue_n2 in (None, 3.0, 4.0)
)


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _group_market(path: Path) -> dict[date, tuple[object, ...]]:
    series, _, _, _, _, _ = load_market_evidence(path)
    grouped: dict[date, list[object]] = defaultdict(list)
    for bar in series:
        grouped[_day(getattr(bar, "opened_at"))].append(bar)
    return {
        key: tuple(sorted(values, key=lambda bar: getattr(bar, "opened_at")))
        for key, values in grouped.items()
    }


def _eligible(
    by_day: dict[date, tuple[object, ...]],
    local_day: date,
    decision_at: datetime,
) -> tuple[object, ...]:
    return tuple(
        bar for bar in by_day.get(local_day, ())
        if getattr(bar, "closed_at") <= decision_at
    )


def _signed_move(
    bars: tuple[object, ...],
    *,
    side: str,
    window: int,
) -> Decimal | None:
    recent = bars[-window:]
    if len(recent) < min(window, 2):
        return None
    high = max(_d(getattr(bar, "high")) for bar in recent)
    low = min(_d(getattr(bar, "low")) for bar in recent)
    span = high - low
    if span <= 0:
        return ZERO
    move = _d(getattr(recent[-1], "close")) - _d(getattr(recent[0], "open"))
    sign = Decimal("1") if side == "long" else Decimal("-1")
    return sign * move / span


def _bar_side(bar: object, side: str) -> int:
    move = _d(getattr(bar, "close")) - _d(getattr(bar, "open"))
    if side == "short":
        move = -move
    if move > 0:
        return 1
    if move < 0:
        return -1
    return 0


def _trailing_run(
    bars: tuple[object, ...],
    *,
    side: str,
    decision_at: datetime,
) -> tuple[str, int, datetime | None]:
    recent = bars[-15:]
    if not recent:
        return "NONE", 0, None
    directions = [_bar_side(bar, side) for bar in recent]
    target = directions[-1]
    if target == 0:
        return "NEUTRAL", 0, None
    count = 0
    start_at: datetime | None = None
    for bar, direction in reversed(list(zip(recent, directions, strict=False))):
        if direction != target:
            break
        count += 1
        start_at = cast(datetime, getattr(bar, "closed_at"))
    state = "ALIGNED" if target > 0 else "ADVERSE"
    if start_at is None:
        return state, count, None
    age = int((decision_at - start_at).total_seconds() // 60)
    if age < 0:
        raise ValueError("future peer run start")
    return state, count, start_at


def _age_bucket(minutes: int | None) -> str:
    if minutes is None:
        return "NONE"
    if minutes <= 1:
        return "0_1"
    if minutes <= 3:
        return "2_3"
    if minutes <= 5:
        return "4_5"
    if minutes <= 10:
        return "6_10"
    return "GT10"


def _transition(move3: Decimal | None, move10: Decimal | None) -> str:
    if move3 is None or move10 is None:
        return "UNAVAILABLE"
    if move3 >= Decimal("0.15") and move10 <= Decimal("-0.10"):
        return "REVERSING_TO_SUPPORT"
    if move3 <= Decimal("-0.15") and move10 >= Decimal("0.10"):
        return "REVERSING_TO_ADVERSE"
    delta = move3 - move10
    if move3 > 0 and delta >= Decimal("0.15"):
        return "SUPPORT_ACCELERATING"
    if move3 > 0:
        return "SUPPORTIVE"
    if move3 < 0 and delta <= Decimal("-0.15"):
        return "ADVERSE_ACCELERATING"
    if move3 < 0:
        return "ADVERSE"
    return "NEUTRAL"


def _sync(a: Decimal | None, b: Decimal | None) -> str:
    if a is None or b is None:
        return "INCOMPLETE"
    if a > Decimal("0.10") and b > Decimal("0.10"):
        return "BOTH_SUPPORT"
    if a < Decimal("-0.10") and b < Decimal("-0.10"):
        return "BOTH_ADVERSE"
    if a * b < 0:
        return "DIVERGENT"
    return "MIXED_NEUTRAL"


def _divergence_age(
    sp: tuple[object, ...],
    us: tuple[object, ...],
    *,
    side: str,
) -> str:
    sp_recent = sp[-10:]
    us_recent = us[-10:]
    n = min(len(sp_recent), len(us_recent))
    if n == 0:
        return "NONE"
    count = 0
    for sp_bar, us_bar in reversed(
        list(zip(sp_recent[-n:], us_recent[-n:], strict=False))
    ):
        a = _bar_side(sp_bar, side)
        b = _bar_side(us_bar, side)
        if a == 0 or b == 0 or a == b:
            break
        count += 1
    return _age_bucket(count)


def _breadth(moves: tuple[Decimal | None, ...]) -> str:
    support = sum(move is not None and move > Decimal("0.10") for move in moves)
    adverse = sum(move is not None and move < Decimal("-0.10") for move in moves)
    if support == 3:
        return "3_SUPPORT"
    if support == 2:
        return "2_SUPPORT"
    if adverse == 3:
        return "3_ADVERSE"
    if adverse == 2:
        return "2_ADVERSE"
    if support and adverse:
        return "SPLIT"
    return "NEUTRAL"


def _prior_day_range(
    by_day: dict[date, tuple[object, ...]],
    local_day: date,
) -> tuple[Decimal, Decimal] | None:
    prior_days = sorted(day for day in by_day if day < local_day)
    if not prior_days:
        return None
    bars = tuple(
        bar for bar in by_day[prior_days[-1]]
        if (0, 0, 0) <= _wall(getattr(bar, "opened_at")) < (16, 0, 0)
    )
    if not bars:
        return None
    return (
        max(_d(getattr(bar, "high")) for bar in bars),
        min(_d(getattr(bar, "low")) for bar in bars),
    )


def _liquidity_context(
    nas_by_day: dict[date, tuple[object, ...]],
    local_day: date,
    decision_at: datetime,
    side: str,
) -> dict[str, str]:
    bars = _eligible(nas_by_day, local_day, decision_at)
    reference = tuple(
        bar for bar in nas_by_day.get(local_day, ())
        if (9, 0, 0) <= _wall(getattr(bar, "opened_at")) < (10, 0, 0)
    )
    if not bars or not reference:
        return {
            "destination_room_ref_bin": "UNAVAILABLE",
            "reference_room_ref_bin": "UNAVAILABLE",
            "prior_range_location_causal": "UNAVAILABLE",
        }
    ref_high = max(_d(getattr(bar, "high")) for bar in reference)
    ref_low = min(_d(getattr(bar, "low")) for bar in reference)
    width = ref_high - ref_low
    if width <= 0:
        return {
            "destination_room_ref_bin": "UNAVAILABLE",
            "reference_room_ref_bin": "UNAVAILABLE",
            "prior_range_location_causal": "UNAVAILABLE",
        }
    price = _d(getattr(bars[-1], "close"))
    prior = _prior_day_range(nas_by_day, local_day)
    if prior is None:
        destination = None
        location = "UNAVAILABLE"
    else:
        prior_high, prior_low = prior
        destination = (
            (prior_high - price) / width
            if side == "long"
            else (price - prior_low) / width
        )
        if price > prior_high:
            location = "ABOVE"
        elif price < prior_low:
            location = "BELOW"
        else:
            percentile = (price - prior_low) / max(
                prior_high - prior_low,
                Decimal("0.000001"),
            )
            if percentile >= Decimal("0.67"):
                location = "UPPER"
            elif percentile <= Decimal("0.33"):
                location = "LOWER"
            else:
                location = "MIDDLE"
    reference_room = (
        (ref_high - price) / width
        if side == "long"
        else (price - ref_low) / width
    )
    return {
        "destination_room_ref_bin": v12._bin(
            "unavailable" if destination is None else destination
        ),
        "reference_room_ref_bin": v12._bin(reference_room),
        "prior_range_location_causal": location,
    }


def _cross_rows(
    *,
    nas_path: Path,
    sp_path: Path,
    us_path: Path,
    rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    base = v8._sequence_rows(nas_path, rows)
    nas_by_day = _group_market(nas_path)
    sp_by_day = _group_market(sp_path)
    us_by_day = _group_market(us_path)
    output: list[dict[str, object]] = []

    for source in base:
        row = v12._decorate(source)
        local_day = date.fromisoformat(cast(str, row["local_date"]))
        decision_at = v2.v3._dt(row["signal_at"])
        side = str(row["side"])
        nas = _eligible(nas_by_day, local_day, decision_at)
        sp = _eligible(sp_by_day, local_day, decision_at)
        us = _eligible(us_by_day, local_day, decision_at)

        nas3 = _signed_move(nas, side=side, window=3)
        nas10 = _signed_move(nas, side=side, window=10)
        sp3 = _signed_move(sp, side=side, window=3)
        sp10 = _signed_move(sp, side=side, window=10)
        us3 = _signed_move(us, side=side, window=3)
        us10 = _signed_move(us, side=side, window=10)

        sp_state, sp_run, sp_start = _trailing_run(
            sp, side=side, decision_at=decision_at
        )
        us_state, us_run, us_start = _trailing_run(
            us, side=side, decision_at=decision_at
        )
        if sp_start is not None and us_start is not None:
            delta = int(abs((sp_start - us_start).total_seconds()) // 60)
            if delta == 0:
                leader = "SIMULTANEOUS"
            elif sp_start < us_start:
                leader = "SP500"
            else:
                leader = "US30"
            latency = _age_bucket(delta)
        else:
            leader = "INCOMPLETE"
            latency = "INCOMPLETE"

        breadth3 = _breadth((nas3, sp3, us3))
        breadth10 = _breadth((nas10, sp10, us10))
        if breadth10 in {"2_ADVERSE", "3_ADVERSE", "SPLIT"} and breadth3 in {
            "2_SUPPORT", "3_SUPPORT"
        }:
            breadth_transition = "CONVERGING_TO_SUPPORT"
        elif breadth10 in {"2_SUPPORT", "3_SUPPORT"} and breadth3 in {
            "2_ADVERSE", "3_ADVERSE"
        }:
            breadth_transition = "DETERIORATING_TO_ADVERSE"
        elif breadth3 == breadth10:
            breadth_transition = "STABLE"
        else:
            breadth_transition = "CHANGING"

        row.update({
            "sp500_move3_bin": v12._bin(
                "unavailable" if sp3 is None else sp3
            ),
            "sp500_move10_bin": v12._bin(
                "unavailable" if sp10 is None else sp10
            ),
            "sp500_transition": _transition(sp3, sp10),
            "sp500_run_state": f"{sp_state}_{min(sp_run, 5)}",
            "sp500_run_age": _age_bucket(
                None if sp_start is None
                else int((decision_at - sp_start).total_seconds() // 60)
            ),
            "us30_move3_bin": v12._bin(
                "unavailable" if us3 is None else us3
            ),
            "us30_move10_bin": v12._bin(
                "unavailable" if us10 is None else us10
            ),
            "us30_transition": _transition(us3, us10),
            "us30_run_state": f"{us_state}_{min(us_run, 5)}",
            "us30_run_age": _age_bucket(
                None if us_start is None
                else int((decision_at - us_start).total_seconds() // 60)
            ),
            "peer_sync3": _sync(sp3, us3),
            "peer_confirmation_latency": latency,
            "peer_sequence_leader": leader,
            "peer_divergence_age": _divergence_age(sp, us, side=side),
            "breadth3": breadth3,
            "breadth10": breadth10,
            "breadth_transition": breadth_transition,
        })
        row.update(
            _liquidity_context(
                nas_by_day,
                local_day,
                decision_at,
                side,
            )
        )
        output.append(row)
    return output


def _negative_views(
    row: dict[str, object],
    negative: dict[str, set[tuple[str, ...]]],
) -> int:
    return sum(
        v5._state(row, fields) in negative[name]
        for name, fields in v8.NEGATIVE_VIEWS.items()
    )


def _learn_model(
    history_n1: list[dict[str, object]],
) -> tuple[dict[str, dict[str, dict[str, float]]], dict[str, object]]:
    wins = [row for row in history_n1 if _d(row["net_r_after_friction"]) > 0]
    losses = [row for row in history_n1 if _d(row["net_r_after_friction"]) < 0]
    if not wins or not losses:
        raise ValueError("cross sequence model requires N1 wins and losses")
    model: dict[str, dict[str, dict[str, float]]] = {}
    diagnostics: dict[str, object] = {}
    for channel, fields in CHANNELS.items():
        model[channel] = {}
        cdiag: dict[str, object] = {}
        for field in fields:
            win_counts: dict[str, int] = defaultdict(int)
            loss_counts: dict[str, int] = defaultdict(int)
            values: set[str] = set()
            for row in wins:
                value = str(row.get(field, "unavailable"))
                win_counts[value] += 1
                values.add(value)
            for row in losses:
                value = str(row.get(field, "unavailable"))
                loss_counts[value] += 1
                values.add(value)
            cardinality = max(1, len(values))
            learned: dict[str, float] = {}
            details: list[dict[str, object]] = []
            for value in values:
                p_win = (win_counts[value] + 1.0) / (
                    len(wins) + cardinality
                )
                p_loss = (loss_counts[value] + 1.0) / (
                    len(losses) + cardinality
                )
                log_lr = math.log(p_win / p_loss)
                learned[value] = log_lr
                details.append({
                    "value": value,
                    "wins": win_counts[value],
                    "losses": loss_counts[value],
                    "log_lr": log_lr,
                })
            model[channel][field] = learned
            cdiag[field] = sorted(
                details,
                key=lambda item: float(item["log_lr"]),
                reverse=True,
            )
        diagnostics[channel] = cdiag
    return model, diagnostics


def _channel_scores(
    row: dict[str, object],
    model: dict[str, dict[str, dict[str, float]]],
) -> dict[str, float]:
    scores: dict[str, float] = {}
    for channel, fields in CHANNELS.items():
        hits: list[float] = []
        for field in fields:
            value = str(row.get(field, "unavailable"))
            score = model[channel][field].get(value)
            if score is not None:
                hits.append(score)
        scores[channel] = 0.0 if not hits else sum(hits) / len(hits)
    return scores


def _tail_score(scores: dict[str, float]) -> tuple[float, int, int]:
    supportive = sum(score > 0.10 for score in scores.values())
    adverse = sum(score < -0.10 for score in scores.values())
    ordered = sorted(scores.values(), reverse=True)
    score = sum(ordered[:3]) + 0.25 * sum(ordered[3:])
    return score, supportive, adverse


def _metrics(values: list[Decimal]) -> dict[str, object]:
    gains = sum((value for value in values if value > 0), ZERO)
    losses = -sum((value for value in values if value < 0), ZERO)
    total = sum(values, ZERO)
    equity = peak = dd = ZERO
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
        "mean_r": "0" if not values else format(total / Decimal(len(values)), "f"),
        "max_drawdown_r": format(dd, "f"),
        "max_losing_streak": max_streak,
    }


def _evaluate(
    rows: list[dict[str, object]],
    *,
    negative: dict[str, set[tuple[str, ...]]],
    model: dict[str, dict[str, dict[str, float]]],
    policy: Policy,
) -> dict[str, object]:
    baseline_values: list[Decimal] = []
    kept_values: list[Decimal] = []
    abstained: list[dict[str, object]] = []
    rescued: list[dict[str, object]] = []

    for row in sorted(rows, key=lambda item: cast(str, item["signal_at"])):
        value = _d(row["net_r_after_friction"])
        baseline_values.append(value)
        n_views = _negative_views(row, negative)
        if n_views == 0:
            kept_values.append(value)
            continue
        scores = _channel_scores(row, model)
        total_score, supportive, adverse = _tail_score(scores)
        cross_score = scores.get("CROSS_SEQUENCE", 0.0)
        rescue = False
        if n_views == 1:
            rescue = (
                total_score >= policy.score_threshold
                and supportive >= policy.minimum_supportive_channels
                and adverse <= policy.maximum_adverse_channels
                and cross_score >= policy.minimum_cross_sequence_score
            )
        elif n_views == 2 and policy.rescue_n2_threshold is not None:
            rescue = (
                total_score >= policy.rescue_n2_threshold
                and supportive >= policy.minimum_supportive_channels + 1
                and adverse <= policy.maximum_adverse_channels
                and cross_score >= max(
                    policy.minimum_cross_sequence_score,
                    0.0,
                )
            )
        if rescue:
            kept_values.append(value)
            item = dict(row)
            item["cross_sequence_hypothesis"] = {
                "score": total_score,
                "supportive_channels": supportive,
                "adverse_channels": adverse,
                "cross_sequence_score": cross_score,
                "channel_scores": scores,
                "negative_views": n_views,
            }
            rescued.append(item)
        else:
            abstained.append(row)

    baseline = _metrics(baseline_values)
    shared = _metrics(kept_values)
    base_losses = int(baseline["losses"])
    base_wins = int(baseline["wins"])
    losses_avoided = sum(_d(row["net_r_after_friction"]) < 0 for row in abstained)
    winners_sacrificed = sum(_d(row["net_r_after_friction"]) > 0 for row in abstained)
    rescued_winners = sum(_d(row["net_r_after_friction"]) > 0 for row in rescued)
    rescued_losses = sum(_d(row["net_r_after_friction"]) < 0 for row in rescued)
    gross_winner_r = sum((value for value in baseline_values if value > 0), ZERO)
    sacrificed_r = sum(
        (
            _d(row["net_r_after_friction"])
            for row in abstained
            if _d(row["net_r_after_friction"]) > 0
        ),
        ZERO,
    )
    return {
        "baseline": baseline,
        "shared_cross_sequence_hypothesis": shared,
        "selection": {
            "input": len(rows),
            "kept": len(kept_values),
            "abstained": len(abstained),
            "losses_avoided": losses_avoided,
            "winners_sacrificed": winners_sacrificed,
            "loss_rejection_recall": "0" if base_losses == 0 else format(Decimal(losses_avoided) / Decimal(base_losses), "f"),
            "winner_count_retention": "0" if base_wins == 0 else format(Decimal(base_wins - winners_sacrificed) / Decimal(base_wins), "f"),
            "winner_r_retention": "1" if gross_winner_r == 0 else format((gross_winner_r - sacrificed_r) / gross_winner_r, "f"),
            "density_retained": "0" if not rows else format(Decimal(len(kept_values)) / Decimal(len(rows)), "f"),
            "rescued_trades": len(rescued),
            "rescued_winners": rescued_winners,
            "rescued_losses": rescued_losses,
            "rescue_precision": "0" if not rescued else format(Decimal(rescued_winners) / Decimal(len(rescued)), "f"),
        },
    }


def _gates(result: dict[str, object]) -> dict[str, bool]:
    baseline = cast(dict[str, object], result["baseline"])
    shared = cast(dict[str, object], result["shared_cross_sequence_hypothesis"])
    selection = cast(dict[str, object], result["selection"])
    if baseline["profit_factor"] is None or shared["profit_factor"] is None:
        return {"valid": False}
    return {
        "pf_plus_25pct": _d(shared["profit_factor"]) >= _d(baseline["profit_factor"]) * Decimal("1.25"),
        "dd_minus_30pct": _d(shared["max_drawdown_r"]) <= _d(baseline["max_drawdown_r"]) * Decimal("0.70"),
        "total_r_not_lower": _d(shared["total_r"]) >= _d(baseline["total_r"]),
        "loss_recall_at_least_25pct": _d(selection["loss_rejection_recall"]) >= Decimal("0.25"),
        "winner_count_retention_at_least_80pct": _d(selection["winner_count_retention"]) >= Decimal("0.80"),
        "winner_r_retention_at_least_90pct": _d(selection["winner_r_retention"]) >= Decimal("0.90"),
        "density_at_least_55pct": _d(selection["density_retained"]) >= Decimal("0.55"),
    }


def _score(result: dict[str, object]) -> Decimal | None:
    gates = _gates(result)
    if not gates or not all(gates.values()):
        return None
    baseline = cast(dict[str, object], result["baseline"])
    shared = cast(dict[str, object], result["shared_cross_sequence_hypothesis"])
    selection = cast(dict[str, object], result["selection"])
    return (
        _d(shared["profit_factor"]) / _d(baseline["profit_factor"])
        * _d(baseline["max_drawdown_r"])
        / max(_d(shared["max_drawdown_r"]), Decimal("0.000001"))
        * _d(selection["winner_r_retention"])
        * (Decimal("1") + _d(selection["loss_rejection_recall"]))
    )


def run(
    *,
    r8_trades: Path,
    r6_trades: Path,
    r5_trades: Path,
    r8_nas: Path,
    r8_sp: Path,
    r8_us: Path,
    r6_nas: Path,
    r6_sp: Path,
    r6_us: Path,
    r5_nas: Path,
    r5_sp: Path,
    r5_us: Path,
    daily_path: Path,
) -> dict[str, object]:
    daily = v2.v3._load_daily(daily_path)
    r8 = _cross_rows(
        nas_path=r8_nas,
        sp_path=r8_sp,
        us_path=r8_us,
        rows=v2.v3._decorate(v2.v3._load_trades(r8_trades), daily),
    )
    r6 = _cross_rows(
        nas_path=r6_nas,
        sp_path=r6_sp,
        us_path=r6_us,
        rows=v2.v3._decorate(v2.v3._load_trades(r6_trades), daily),
    )
    if len(r8) != 228 or len(r6) != 278:
        raise AssertionError("VT31 R8/R6 challenge-set drift")

    negative = v8._negative_tables(r8)
    r8_n1 = [row for row in r8 if _negative_views(row, negative) == 1]
    model, diagnostics = _learn_model(r8_n1)

    discovery: list[tuple[Decimal, Policy]] = []
    r8_frontier: list[dict[str, object]] = []
    for policy in POLICIES:
        result = _evaluate(r8, negative=negative, model=model, policy=policy)
        gates = _gates(result)
        score = _score(result)
        r8_frontier.append({
            "policy": policy.payload(),
            "result": result,
            "gates": gates,
            "score": None if score is None else format(score, "f"),
        })
        if score is not None:
            discovery.append((score, policy))

    discovery.sort(key=lambda item: item[0], reverse=True)
    r6_frontier: list[dict[str, object]] = []
    best: tuple[Decimal, Policy] | None = None
    for _, policy in discovery[:160]:
        result = _evaluate(r6, negative=negative, model=model, policy=policy)
        gates = _gates(result)
        score = _score(result)
        r6_frontier.append({
            "policy": policy.payload(),
            "result": result,
            "gates": gates,
            "score": None if score is None else format(score, "f"),
        })
        if score is not None and (best is None or score > best[0]):
            best = (score, policy)

    if best is None:
        return {
            "schema": SCHEMA,
            "identity": IDENTITY,
            "economic_status": "FALSIFIED_BEFORE_R5",
            "challenge_set": {"r8": 228, "r6": 278, "r5": 316},
            "r5_opened": False,
            "r8_n1_population": {
                "sample": len(r8_n1),
                "wins": sum(_d(row["net_r_after_friction"]) > 0 for row in r8_n1),
                "losses": sum(_d(row["net_r_after_friction"]) < 0 for row in r8_n1),
            },
            "feature_model": diagnostics,
            "frozen_policy": None,
            "evaluation": None,
            "gates": None,
            "passes_cross_sequence": False,
            "r8_frontier": r8_frontier,
            "r6_frontier": r6_frontier,
            "governance": _governance(),
        }

    frozen = best[1]
    r5 = _cross_rows(
        nas_path=r5_nas,
        sp_path=r5_sp,
        us_path=r5_us,
        rows=v2.v3._decorate(v2.v3._load_trades(r5_trades), daily),
    )
    if len(r5) != 316:
        raise AssertionError("VT31 R5 challenge-set drift")
    evaluation = _evaluate(r5, negative=negative, model=model, policy=frozen)
    gates = _gates(evaluation)
    passed = all(gates.values())
    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "economic_status": "PASSED_TEMPORAL_EVALUATION" if passed else "FALSIFIED_ON_R5",
        "challenge_set": {"r8": 228, "r6": 278, "r5": 316},
        "r5_opened": True,
        "r8_n1_population": {
            "sample": len(r8_n1),
            "wins": sum(_d(row["net_r_after_friction"]) > 0 for row in r8_n1),
            "losses": sum(_d(row["net_r_after_friction"]) < 0 for row in r8_n1),
        },
        "temporal_protocol": {
            "r8": "CROSS_MARKET_SEQUENCE_MODEL_DISCOVERY",
            "r6": "CALIBRATION_AND_FREEZE",
            "r5": "NO_RETUNE_EVALUATION",
        },
        "feature_model": diagnostics,
        "frozen_policy": frozen.payload(),
        "evaluation": evaluation,
        "gates": gates,
        "passes_cross_sequence": passed,
        "r8_frontier": r8_frontier,
        "r6_frontier": r6_frontier,
        "governance": _governance(),
    }


def _governance() -> dict[str, bool]:
    return {
        "present_market_cross_sequence_primary": True,
        "three_index_closed_m1_used": True,
        "historical_outcomes_offline_model_only": True,
        "negative_memory_secondary_screen": True,
        "runtime_exact_state_lookup_used": False,
        "runtime_nearest_neighbor_used": False,
        "runtime_current_outcome_used": False,
        "future_m1_used": False,
        "r5_retuned": False,
        "capital_risk_weighting_used": False,
        "methodology_modified": False,
        "shared_order_authority": False,
        "shared_risk_authority": False,
        "shared_execution_authority": False,
        "live_authorized": False,
        "merge_authorized": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--r8-trades", type=Path, required=True)
    parser.add_argument("--r6-trades", type=Path, required=True)
    parser.add_argument("--r5-trades", type=Path, required=True)
    for fold in ("r8", "r6", "r5"):
        parser.add_argument(f"--{fold}-nas", type=Path, required=True)
        parser.add_argument(f"--{fold}-sp", type=Path, required=True)
        parser.add_argument(f"--{fold}-us", type=Path, required=True)
    parser.add_argument("--daily-path", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = run(
        r8_trades=args.r8_trades,
        r6_trades=args.r6_trades,
        r5_trades=args.r5_trades,
        r8_nas=args.r8_nas,
        r8_sp=args.r8_sp,
        r8_us=args.r8_us,
        r6_nas=args.r6_nas,
        r6_sp=args.r6_sp,
        r6_us=args.r6_us,
        r5_nas=args.r5_nas,
        r5_sp=args.r5_sp,
        r5_us=args.r5_us,
        daily_path=args.daily_path,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    print(json.dumps({
        "economic_status": payload["economic_status"],
        "r5_opened": payload["r5_opened"],
        "r8_n1_population": payload["r8_n1_population"],
        "passes_cross_sequence": payload["passes_cross_sequence"],
        "frozen_policy": payload["frozen_policy"],
        "evaluation": payload["evaluation"],
        "gates": payload["gates"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
