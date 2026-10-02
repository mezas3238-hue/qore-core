"""VT31 Shared N1 conditional hypothesis model V12.

V8/V11 isolate the economic frontier: strong multi-view negative states are
mostly losses, while the single-negative-view (N1) population contains the
rare high-payoff winners that must be separated from ordinary losses.

V12 keeps N2+ as strong failure evidence and applies a conditional,
compositional winner-support model only inside N1. The model uses coarse
decision-time facts grouped into causal channels. Historical R8 outcomes learn
single-fact likelihoods offline; runtime combines current facts only. There is
no exact-state, nearest-neighbor, analog, future, sizing or capital weighting.

R8 discovers candidate thresholds. R6 calibrates and freezes. R5 is opened
only if a frozen R6 policy passes every hard gate.
"""
# ruff: noqa: E501
from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_core_stack_v4_perception_first_v2 as v2
import vt31_core_stack_v4_perception_sequence_topology_v8 as v8
import vt31_core_stack_v4_perception_state_model_v5 as v5

SCHEMA = "qore.core_stack_v4.vt31.n1_conditional_hypothesis.v12"
IDENTITY = "VT31_NAS100_SHARED_N1_CONDITIONAL_HYPOTHESIS_V12"
ZERO = Decimal("0")

CHANNELS: dict[str, tuple[str, ...]] = {
    "PATH": (
        "alignment5",
        "alignment20",
        "perception_regime",
        "perception_transition",
        "structure_state",
        "volatility_state",
    ),
    "EVENT": (
        "sequence_chain",
        "sweep_alignment",
        "sweep_freshness",
        "displacement_alignment",
        "displacement_freshness",
        "fvg_alignment",
        "fvg_freshness",
    ),
    "CROSS": (
        "peer_consensus",
        "first_peer_leader",
        "first_peer_lead_bucket",
    ),
    "HIGHER": (
        "h1_relation",
        "cash_open_relation",
        "premarket_relation",
        "prior_day_relation",
        "position_in_prior_day_range_hr",
    ),
    "PRESSURE": (
        "trend_pressure_bin",
        "range_pressure_bin",
        "expansion_pressure_bin",
        "exhaustion_pressure_bin",
        "uncertainty_pressure_bin",
        "raid_depth_ref_hr_bin",
        "current_path_vs_previous_hr_bin",
    ),
}


@dataclass(frozen=True, slots=True)
class Policy:
    score_threshold: float
    minimum_supportive_channels: int
    maximum_adverse_channels: int
    rescue_n2_threshold: float | None

    def payload(self) -> dict[str, object]:
        return {
            "score_threshold": self.score_threshold,
            "minimum_supportive_channels": self.minimum_supportive_channels,
            "maximum_adverse_channels": self.maximum_adverse_channels,
            "rescue_n2_threshold": self.rescue_n2_threshold,
        }


POLICIES = tuple(
    Policy(
        score_threshold=threshold,
        minimum_supportive_channels=min_support,
        maximum_adverse_channels=max_adverse,
        rescue_n2_threshold=rescue_n2,
    )
    for threshold in (-0.50, 0.0, 0.50, 1.0, 1.50, 2.0, 2.50, 3.0)
    for min_support in (1, 2, 3)
    for max_adverse in (1, 2, 3, 5)
    for rescue_n2 in (None, 2.5, 3.5, 4.5)
)


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _relative(value: object, side: str) -> str:
    raw = str(value)
    if raw not in {"bullish", "bearish"}:
        return raw.upper()
    aligned = (side == "long" and raw == "bullish") or (
        side == "short" and raw == "bearish"
    )
    return "ALIGNED" if aligned else "OPPOSED"


def _bin(value: object) -> str:
    raw = str(value)
    if raw in {"unavailable", "None", "null", ""}:
        return "UNAVAILABLE"
    try:
        number = Decimal(raw)
    except Exception:
        return raw
    cuts = (
        Decimal("-0.25"),
        Decimal("0"),
        Decimal("0.20"),
        Decimal("0.40"),
        Decimal("0.60"),
        Decimal("0.80"),
        Decimal("1.00"),
        Decimal("1.25"),
        Decimal("1.50"),
        Decimal("2.00"),
    )
    labels = (
        "LT_M025",
        "M025_0",
        "0_020",
        "020_040",
        "040_060",
        "060_080",
        "080_100",
        "100_125",
        "125_150",
        "150_200",
        "GE200",
    )
    for cut, label in zip(cuts, labels, strict=False):
        if number < cut:
            return label
    return labels[-1]


def _decorate(row: dict[str, object]) -> dict[str, object]:
    item = dict(row)
    side = str(item.get("side", ""))
    item["h1_relation"] = _relative(item.get("h1_state_hr", "unavailable"), side)
    item["cash_open_relation"] = _relative(
        item.get("cash_open_state_hr", "unavailable"), side
    )
    item["premarket_relation"] = _relative(
        item.get("premarket_state_hr", "unavailable"), side
    )
    item["prior_day_relation"] = _relative(
        item.get("prior_day_state_hr", "unavailable"), side
    )
    for field in (
        "trend_pressure",
        "range_pressure",
        "expansion_pressure",
        "exhaustion_pressure",
        "uncertainty_pressure",
        "raid_depth_ref_hr",
        "current_path_vs_previous_hr",
    ):
        item[f"{field}_bin"] = _bin(item.get(field, "unavailable"))
    return item


def _negative_views(
    row: dict[str, object],
    negative: dict[str, set[tuple[str, ...]]],
) -> int:
    return sum(
        v5._state(row, fields) in negative[name]
        for name, fields in v8.NEGATIVE_VIEWS.items()
    )


def _n1_rows(
    rows: list[dict[str, object]],
    negative: dict[str, set[tuple[str, ...]]],
) -> list[dict[str, object]]:
    return [
        row for row in rows
        if _negative_views(row, negative) == 1
    ]


def _learn_feature_models(
    history_n1: list[dict[str, object]],
) -> tuple[dict[str, dict[str, dict[str, float]]], dict[str, object]]:
    wins = [row for row in history_n1 if _d(row["net_r_after_friction"]) > 0]
    losses = [row for row in history_n1 if _d(row["net_r_after_friction"]) < 0]
    if not wins or not losses:
        raise ValueError("N1 model requires winner and loss examples")

    model: dict[str, dict[str, dict[str, float]]] = {}
    diagnostics: dict[str, object] = {}
    for channel, fields in CHANNELS.items():
        model[channel] = {}
        channel_diag: dict[str, object] = {}
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
            per_value: dict[str, float] = {}
            value_diag: list[dict[str, object]] = []
            for value in values:
                p_win = (win_counts[value] + 1.0) / (
                    len(wins) + cardinality
                )
                p_loss = (loss_counts[value] + 1.0) / (
                    len(losses) + cardinality
                )
                log_lr = math.log(p_win / p_loss)
                per_value[value] = log_lr
                value_diag.append({
                    "value": value,
                    "wins": win_counts[value],
                    "losses": loss_counts[value],
                    "log_likelihood_ratio": log_lr,
                })
            model[channel][field] = per_value
            channel_diag[field] = sorted(
                value_diag,
                key=lambda item: float(item["log_likelihood_ratio"]),
                reverse=True,
            )
        diagnostics[channel] = channel_diag
    return model, diagnostics


def _channel_scores(
    row: dict[str, object],
    model: dict[str, dict[str, dict[str, float]]],
) -> dict[str, float]:
    scores: dict[str, float] = {}
    for channel, fields in CHANNELS.items():
        values: list[float] = []
        for field in fields:
            raw = str(row.get(field, "unavailable"))
            score = model[channel][field].get(raw)
            if score is not None:
                values.append(score)
        scores[channel] = 0.0 if not values else sum(values) / len(values)
    return scores


def _tail_score(scores: dict[str, float]) -> tuple[float, int, int]:
    supportive = sum(value > 0.10 for value in scores.values())
    adverse = sum(value < -0.10 for value in scores.values())
    ordered = sorted(scores.values(), reverse=True)
    # Preserve rare winners only when support is distributed: strongest two
    # channels carry most weight, remaining channels contribute context.
    top = ordered[:2]
    rest = ordered[2:]
    score = sum(top) + 0.35 * sum(rest)
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
    n_histogram: dict[str, int] = {}

    for row in sorted(rows, key=lambda item: cast(str, item["signal_at"])):
        value = _d(row["net_r_after_friction"])
        baseline_values.append(value)
        n_views = _negative_views(row, negative)
        n_histogram[str(n_views)] = n_histogram.get(str(n_views), 0) + 1
        if n_views == 0:
            kept_values.append(value)
            continue

        scores = _channel_scores(row, model)
        tail_score, supportive, adverse = _tail_score(scores)
        rescue = False
        if n_views == 1:
            rescue = (
                tail_score >= policy.score_threshold
                and supportive >= policy.minimum_supportive_channels
                and adverse <= policy.maximum_adverse_channels
            )
        elif (
            n_views == 2
            and policy.rescue_n2_threshold is not None
        ):
            rescue = (
                tail_score >= policy.rescue_n2_threshold
                and supportive >= policy.minimum_supportive_channels + 1
                and adverse <= policy.maximum_adverse_channels
            )

        if rescue:
            kept_values.append(value)
            item = dict(row)
            item["tail_hypothesis"] = {
                "score": tail_score,
                "supportive_channels": supportive,
                "adverse_channels": adverse,
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
        "shared_n1_hypothesis": shared,
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
            "negative_view_histogram": dict(sorted(n_histogram.items())),
        },
    }


def _gates(result: dict[str, object]) -> dict[str, bool]:
    baseline = cast(dict[str, object], result["baseline"])
    shared = cast(dict[str, object], result["shared_n1_hypothesis"])
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
    shared = cast(dict[str, object], result["shared_n1_hypothesis"])
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
    r8_raw: Path,
    r6_raw: Path,
    r5_raw: Path,
    daily_path: Path,
) -> dict[str, object]:
    daily = v2.v3._load_daily(daily_path)
    r8 = [
        _decorate(row)
        for row in v8._sequence_rows(
            r8_raw,
            v2.v3._decorate(v2.v3._load_trades(r8_trades), daily),
        )
    ]
    r6 = [
        _decorate(row)
        for row in v8._sequence_rows(
            r6_raw,
            v2.v3._decorate(v2.v3._load_trades(r6_trades), daily),
        )
    ]
    if len(r8) != 228 or len(r6) != 278:
        raise AssertionError("VT31 R8/R6 challenge-set drift")

    negative = v8._negative_tables(r8)
    r8_n1 = _n1_rows(r8, negative)
    model, diagnostics = _learn_feature_models(r8_n1)

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
    for _, policy in discovery[:128]:
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
            "passes_n1_hypothesis": False,
            "r8_frontier": r8_frontier,
            "r6_frontier": r6_frontier,
            "governance": _governance(),
        }

    frozen = best[1]
    r5 = [
        _decorate(row)
        for row in v8._sequence_rows(
            r5_raw,
            v2.v3._decorate(v2.v3._load_trades(r5_trades), daily),
        )
    ]
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
            "r8": "N1_CAUSAL_CHANNEL_MODEL_DISCOVERY",
            "r6": "THRESHOLD_CALIBRATION_AND_FREEZE",
            "r5": "NO_RETUNE_EVALUATION",
        },
        "feature_model": diagnostics,
        "frozen_policy": frozen.payload(),
        "evaluation": evaluation,
        "gates": gates,
        "passes_n1_hypothesis": passed,
        "r8_frontier": r8_frontier,
        "r6_frontier": r6_frontier,
        "governance": _governance(),
    }


def _governance() -> dict[str, bool]:
    return {
        "present_market_hypothesis_primary": True,
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
    parser.add_argument("--r8-raw", type=Path, required=True)
    parser.add_argument("--r6-raw", type=Path, required=True)
    parser.add_argument("--r5-raw", type=Path, required=True)
    parser.add_argument("--daily-path", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = run(
        r8_trades=args.r8_trades,
        r6_trades=args.r6_trades,
        r5_trades=args.r5_trades,
        r8_raw=args.r8_raw,
        r6_raw=args.r6_raw,
        r5_raw=args.r5_raw,
        daily_path=args.daily_path,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    print(json.dumps({
        "economic_status": payload["economic_status"],
        "r5_opened": payload["r5_opened"],
        "r8_n1_population": payload["r8_n1_population"],
        "passes_n1_hypothesis": payload["passes_n1_hypothesis"],
        "frozen_policy": payload["frozen_policy"],
        "evaluation": payload["evaluation"],
        "gates": payload["gates"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
