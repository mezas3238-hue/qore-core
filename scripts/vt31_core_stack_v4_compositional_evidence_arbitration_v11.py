"""VT31 Shared compositional evidence arbitration V11.

Repairs the exact-state rescue failure demonstrated by V9 and the fixed-weight
hypothesis failure demonstrated by V10.

The loss detector remains the temporally stable V8 negative-state contrast.
Winner preservation no longer requires an exact multi-feature historical cell.
Instead, single present-market facts contribute additive SUPPORT and FAILURE
evidence when their economic polarity is stable across both chronological
halves of R8. Runtime matches current facts only; there is no nearest-neighbor
or analog lookup.

R8 discovers the evidence model and candidate policy. R6 calibrates and freezes.
R5 remains unopened unless every hard R6 gate passes.
"""
# ruff: noqa: E501
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_core_stack_v4_perception_first_v2 as v2
import vt31_core_stack_v4_perception_sequence_topology_v8 as v8
import vt31_core_stack_v4_perception_state_model_v5 as v5

SCHEMA = "qore.core_stack_v4.vt31.compositional_evidence_arbitration.v11"
IDENTITY = "VT31_NAS100_SHARED_COMPOSITIONAL_EVIDENCE_ARBITRATION_V11"
ZERO = Decimal("0")
EPS = Decimal("0.000001")

FEATURES = (
    "alignment5",
    "alignment20",
    "perception_regime",
    "perception_transition",
    "momentum_state",
    "volatility_state",
    "structure_state",
    "peer_consensus",
    "sequence_chain",
    "sweep_alignment",
    "sweep_freshness",
    "displacement_alignment",
    "displacement_freshness",
    "fvg_alignment",
    "fvg_freshness",
    "h1_relation",
    "cash_open_relation",
    "premarket_relation",
    "prior_day_relation",
    "position_in_prior_day_range_hr",
    "trend_pressure",
    "range_pressure",
    "expansion_pressure",
    "exhaustion_pressure",
    "uncertainty_pressure",
    "pre_path_efficiency",
    "pre_overlap_rate",
    "pre_last5_range_fraction",
    "recent_path_efficiency_hr",
    "recent_overlap_rate_hr",
    "raid_depth_ref_hr",
    "current_path_vs_previous_hr",
    "reference_width_vs_prior5_hr",
)

NUMERIC = {
    "trend_pressure",
    "range_pressure",
    "expansion_pressure",
    "exhaustion_pressure",
    "uncertainty_pressure",
    "pre_path_efficiency",
    "pre_overlap_rate",
    "pre_last5_range_fraction",
    "recent_path_efficiency_hr",
    "recent_overlap_rate_hr",
    "raid_depth_ref_hr",
    "current_path_vs_previous_hr",
    "reference_width_vs_prior5_hr",
}


@dataclass(frozen=True, slots=True)
class Evidence:
    support: Decimal
    failure: Decimal
    sample_floor: int

    def payload(self) -> dict[str, object]:
        return {
            "support": format(self.support, "f"),
            "failure": format(self.failure, "f"),
            "sample_floor": self.sample_floor,
        }


@dataclass(frozen=True, slots=True)
class Policy:
    minimum_memory_risk_views: int
    support_threshold: Decimal
    support_minus_failure_margin: Decimal
    failure_multiplier: Decimal
    minimum_support_hits: int
    maximum_negative_views_for_rescue: int

    def payload(self) -> dict[str, object]:
        return {
            "minimum_memory_risk_views": self.minimum_memory_risk_views,
            "support_threshold": format(self.support_threshold, "f"),
            "support_minus_failure_margin": format(
                self.support_minus_failure_margin, "f"
            ),
            "failure_multiplier": format(self.failure_multiplier, "f"),
            "minimum_support_hits": self.minimum_support_hits,
            "maximum_negative_views_for_rescue": (
                self.maximum_negative_views_for_rescue
            ),
        }


POLICIES = tuple(
    Policy(
        minimum_memory_risk_views=memory_views,
        support_threshold=support,
        support_minus_failure_margin=margin,
        failure_multiplier=failure_multiplier,
        minimum_support_hits=hits,
        maximum_negative_views_for_rescue=max_negative,
    )
    for memory_views in (1, 2)
    for support in (
        Decimal("0.50"),
        Decimal("1.00"),
        Decimal("1.50"),
        Decimal("2.00"),
        Decimal("2.50"),
        Decimal("3.00"),
    )
    for margin in (
        Decimal("0"),
        Decimal("0.50"),
        Decimal("1.00"),
        Decimal("1.50"),
    )
    for failure_multiplier in (
        Decimal("0.50"),
        Decimal("0.75"),
        Decimal("1.00"),
        Decimal("1.25"),
    )
    for hits in (1, 2, 3)
    for max_negative in (1, 2, 99)
)


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _bin(value: object) -> str:
    raw = str(value)
    if raw in {"unavailable", "None", "null", ""}:
        return "UNAVAILABLE"
    try:
        x = Decimal(raw)
    except Exception:
        return raw
    cuts = (
        Decimal("-0.50"),
        Decimal("-0.10"),
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
        "LT_M050",
        "M050_M010",
        "M010_0",
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
        if x < cut:
            return label
    return labels[-1]


def _relative(state: object, side: str) -> str:
    raw = str(state)
    if raw not in {"bullish", "bearish"}:
        return raw.upper()
    aligned = (side == "long" and raw == "bullish") or (
        side == "short" and raw == "bearish"
    )
    return "ALIGNED" if aligned else "OPPOSED"


def _feature_value(row: dict[str, object], feature: str) -> str:
    side = str(row.get("side", ""))
    if feature == "h1_relation":
        return _relative(row.get("h1_state_hr", "unavailable"), side)
    if feature == "cash_open_relation":
        return _relative(row.get("cash_open_state_hr", "unavailable"), side)
    if feature == "premarket_relation":
        return _relative(row.get("premarket_state_hr", "unavailable"), side)
    if feature == "prior_day_relation":
        return _relative(row.get("prior_day_state_hr", "unavailable"), side)
    if feature in NUMERIC:
        return _bin(row.get(feature, "unavailable"))
    return str(row.get(feature, "unavailable"))


def _split(
    rows: list[dict[str, object]],
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    ordered = sorted(rows, key=lambda row: cast(str, row["signal_at"]))
    cut = len(ordered) // 2
    return ordered[:cut], ordered[cut:]


def _stats(rows: list[dict[str, object]]) -> dict[str, object]:
    values = [_d(row["net_r_after_friction"]) for row in rows]
    winners = [v for v in values if v > 0]
    losses = [v for v in values if v < 0]
    gp = sum(winners, ZERO)
    gl = -sum(losses, ZERO)
    return {
        "sample": len(values),
        "wins": len(winners),
        "losses": len(losses),
        "loss_rate": ZERO if not values else Decimal(len(losses)) / Decimal(len(values)),
        "gross_winner_r": gp,
        "gross_loss_r": gl,
        "winner_r_density": ZERO if not values else gp / Decimal(len(values)),
        "total_r": gp - gl,
    }


def _evidence_model(
    history: list[dict[str, object]],
    *,
    minimum_half_sample: int = 3,
) -> tuple[dict[str, dict[str, Evidence]], dict[str, object]]:
    old, recent = _split(history)
    old_global = _stats(old)
    recent_global = _stats(recent)
    model: dict[str, dict[str, Evidence]] = {}
    diagnostics: dict[str, object] = {}

    for feature in FEATURES:
        left: dict[str, list[dict[str, object]]] = defaultdict(list)
        right: dict[str, list[dict[str, object]]] = defaultdict(list)
        for row in old:
            left[_feature_value(row, feature)].append(row)
        for row in recent:
            right[_feature_value(row, feature)].append(row)

        learned: dict[str, Evidence] = {}
        diag: list[dict[str, object]] = []
        for value in set(left).intersection(right):
            l = _stats(left[value])
            r = _stats(right[value])
            l_n = int(l["sample"])
            r_n = int(r["sample"])
            if l_n < minimum_half_sample or r_n < minimum_half_sample:
                continue
            sample_floor = min(l_n, r_n)
            reliability = min(
                Decimal("2"),
                Decimal(sample_floor).sqrt() / Decimal("2"),
            )

            loss_delta = min(
                cast(Decimal, left_stats["loss_rate"]) - cast(Decimal, old_global["loss_rate"]),
                cast(Decimal, right_stats["loss_rate"]) - cast(Decimal, recent_global["loss_rate"]),
            )
            winner_delta = min(
                cast(Decimal, left_stats["winner_r_density"]) - cast(Decimal, old_global["winner_r_density"]),
                cast(Decimal, right_stats["winner_r_density"]) - cast(Decimal, recent_global["winner_r_density"]),
            )

            failure = max(ZERO, loss_delta) * reliability * Decimal("4")
            support = (
                max(ZERO, winner_delta)
                / max(
                    (
                        cast(Decimal, old_global["winner_r_density"])
                        + cast(Decimal, recent_global["winner_r_density"])
                    )
                    / Decimal("2"),
                    EPS,
                )
                * reliability
            )
            support = min(Decimal("3"), support)
            failure = min(Decimal("3"), failure)
            if support < Decimal("0.10") and failure < Decimal("0.10"):
                continue
            evidence = Evidence(
                support=support,
                failure=failure,
                sample_floor=sample_floor,
            )
            learned[value] = evidence
            diag.append({
                "value": value,
                "evidence": evidence.payload(),
                "old": {
                    "sample": l_n,
                    "wins": left_stats["wins"],
                    "losses": left_stats["losses"],
                    "loss_rate": format(cast(Decimal, left_stats["loss_rate"]), "f"),
                    "winner_r_density": format(cast(Decimal, left_stats["winner_r_density"]), "f"),
                    "total_r": format(cast(Decimal, left_stats["total_r"]), "f"),
                },
                "recent": {
                    "sample": r_n,
                    "wins": right_stats["wins"],
                    "losses": right_stats["losses"],
                    "loss_rate": format(cast(Decimal, right_stats["loss_rate"]), "f"),
                    "winner_r_density": format(cast(Decimal, right_stats["winner_r_density"]), "f"),
                    "total_r": format(cast(Decimal, right_stats["total_r"]), "f"),
                },
            })
        model[feature] = learned
        diagnostics[feature] = {
            "learned_values": len(learned),
            "values": diag,
        }
    return model, diagnostics


def _row_evidence(
    row: dict[str, object],
    model: dict[str, dict[str, Evidence]],
) -> tuple[Decimal, Decimal, int, int]:
    support = failure = ZERO
    support_hits = failure_hits = 0
    for feature in FEATURES:
        evidence = model[feature].get(_feature_value(row, feature))
        if evidence is None:
            continue
        support += evidence.support
        failure += evidence.failure
        if evidence.support >= Decimal("0.10"):
            support_hits += 1
        if evidence.failure >= Decimal("0.10"):
            failure_hits += 1
    return support, failure, support_hits, failure_hits


def _metrics(values: list[Decimal]) -> dict[str, object]:
    gains = sum((v for v in values if v > 0), ZERO)
    losses = -sum((v for v in values if v < 0), ZERO)
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
        "wins": sum(v > 0 for v in values),
        "losses": sum(v < 0 for v in values),
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
    model: dict[str, dict[str, Evidence]],
    policy: Policy,
) -> dict[str, object]:
    baseline_values: list[Decimal] = []
    kept_values: list[Decimal] = []
    abstained: list[dict[str, object]] = []
    rescued: list[dict[str, object]] = []

    for row in sorted(rows, key=lambda item: cast(str, item["signal_at"])):
        value = _d(row["net_r_after_friction"])
        baseline_values.append(value)
        negative_views = sum(
            v5._state(row, fields) in negative[name]
            for name, fields in v8.NEGATIVE_VIEWS.items()
        )
        candidate = negative_views >= policy.minimum_memory_risk_views
        if not candidate:
            kept_values.append(value)
            continue

        support, failure, support_hits, failure_hits = _row_evidence(row, model)
        allowed_depth = (
            policy.maximum_negative_views_for_rescue == 99
            or negative_views <= policy.maximum_negative_views_for_rescue
        )
        rescue = (
            allowed_depth
            and support_hits >= policy.minimum_support_hits
            and support >= policy.support_threshold
            and support - policy.failure_multiplier * failure
            >= policy.support_minus_failure_margin
        )
        if rescue:
            kept_values.append(value)
            item = dict(row)
            item["evidence"] = {
                "support": format(support, "f"),
                "failure": format(failure, "f"),
                "support_hits": support_hits,
                "failure_hits": failure_hits,
                "negative_views": negative_views,
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
    gross_winner_r = sum((v for v in baseline_values if v > 0), ZERO)
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
        "shared_compositional_evidence": shared,
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
    shared = cast(dict[str, object], result["shared_compositional_evidence"])
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
    shared = cast(dict[str, object], result["shared_compositional_evidence"])
    selection = cast(dict[str, object], result["selection"])
    return (
        _d(shared["profit_factor"]) / _d(baseline["profit_factor"])
        * _d(baseline["max_drawdown_r"]) / max(_d(shared["max_drawdown_r"]), EPS)
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
    r8 = v8._sequence_rows(r8_raw, v2.v3._decorate(v2.v3._load_trades(r8_trades), daily))
    r6 = v8._sequence_rows(r6_raw, v2.v3._decorate(v2.v3._load_trades(r6_trades), daily))
    if len(r8) != 228 or len(r6) != 278:
        raise AssertionError("VT31 R8/R6 challenge-set drift")

    negative = v8._negative_tables(r8)
    model, diagnostics = _evidence_model(r8)

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
            "evidence_model": diagnostics,
            "frozen_policy": None,
            "evaluation": None,
            "gates": None,
            "passes_compositional_evidence": False,
            "r8_frontier": r8_frontier,
            "r6_frontier": r6_frontier,
            "governance": _governance(),
        }

    frozen = best[1]
    r5 = v8._sequence_rows(r5_raw, v2.v3._decorate(v2.v3._load_trades(r5_trades), daily))
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
        "temporal_protocol": {
            "r8": "STABLE_SINGLE_FACT_EVIDENCE_DISCOVERY",
            "r6": "COMPOSITIONAL_POLICY_CALIBRATION_AND_FREEZE",
            "r5": "NO_RETUNE_EVALUATION",
        },
        "evidence_model": diagnostics,
        "frozen_policy": frozen.payload(),
        "evaluation": evaluation,
        "gates": gates,
        "passes_compositional_evidence": passed,
        "r8_frontier": r8_frontier,
        "r6_frontier": r6_frontier,
        "governance": _governance(),
    }


def _governance() -> dict[str, bool]:
    return {
        "present_market_facts_primary": True,
        "historical_memory_secondary_only": True,
        "runtime_exact_multifeature_state_lookup_used": False,
        "runtime_nearest_neighbor_used": False,
        "runtime_outcome_label_used": False,
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
        "passes_compositional_evidence": payload["passes_compositional_evidence"],
        "frozen_policy": payload["frozen_policy"],
        "evaluation": payload["evaluation"],
        "gates": payload["gates"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
