"""Shared Core V2 dual-mission falsification lab on VT31 source-only NAS100.

Mission 1: decision support. Preserve the source methodology and use only
decision-time features to emit PASS or ABSTAIN before entry.

Mission 2: trade potentiation. Preserve every source trade and emit an
authority-free economic posture. A shadow QORE-Risk transform applies the
frozen multiplier; Shared itself never authorizes risk or orders.

Temporal protocol:
- R8 = historical memory / discovery only.
- R6 = calibration and single policy freeze.
- R5 = no-retune temporal evaluation.

Post-outcome fields (loss labels, MFE/MAE, exit reason, realized R) are never
features of the current decision.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_nas100_silver_bullet_native_streak_falsification_v1 as native

SCHEMA = "qore.core_stack_v2.vt31.shared_dual_mission_lab.v1"
IDENTITY = "VT31_NAS100_SHARED_DUAL_MISSION_V1"

BASE_FEATURES = (
    "side",
    "entry_family",
    "raid_minute_bucket",
    "confirmation_minute_bucket",
    "decision_minute_bucket",
    "raid_to_confirmation_bucket",
    "confirmation_to_decision_bucket",
)
GEOMETRY_FEATURES = BASE_FEATURES + (
    "raid_depth_ref_bucket",
    "risk_ref_bucket",
    "planned_target_r_bucket",
    "entry_location_ref_bucket",
    "zone_width_ref_bucket",
)
FULL_FEATURES = GEOMETRY_FEATURES + (
    "extreme_body_fraction_bucket",
    "reference_width_pct_bucket",
    "candidate_count_bucket",
    "candidate_combo",
)

FORBIDDEN_CURRENT_FEATURES = (
    "net_r_after_friction",
    "r_multiple",
    "loss_path_class",
    "mfe_r",
    "mae_r",
    "exit_reason",
    "exit_at",
    "filled_at",
    "fill_delay_minutes",
    "fill_delay_bucket",
    "pre_loss_streak_bucket",
)

INTERACTIONS = (
    ("side", "entry_family"),
    ("entry_family", "raid_minute_bucket"),
    ("entry_family", "confirmation_minute_bucket"),
    ("entry_family", "risk_ref_bucket"),
    ("entry_family", "planned_target_r_bucket"),
    ("entry_family", "candidate_combo"),
    ("side", "reference_width_pct_bucket"),
    ("raid_depth_ref_bucket", "risk_ref_bucket"),
    ("risk_ref_bucket", "planned_target_r_bucket"),
)


@dataclass(frozen=True, slots=True)
class Policy:
    profile: str
    shrinkage: int
    abstain_threshold: Decimal
    favorable_threshold: Decimal
    minimum_groups: int
    caution_multiplier: Decimal

    @property
    def features(self) -> tuple[str, ...]:
        if self.profile == "BASE":
            return BASE_FEATURES
        if self.profile == "GEOMETRY":
            return GEOMETRY_FEATURES
        if self.profile == "FULL":
            return FULL_FEATURES
        raise ValueError("unknown profile")

    def payload(self) -> dict[str, object]:
        return {
            "profile": self.profile,
            "features": self.features,
            "shrinkage": self.shrinkage,
            "abstain_threshold": str(self.abstain_threshold),
            "favorable_threshold": str(self.favorable_threshold),
            "minimum_groups": self.minimum_groups,
            "caution_multiplier": str(self.caution_multiplier),
        }


POLICIES = tuple(
    Policy(profile, shrinkage, abstain, favorable, min_groups, caution)
    for profile in ("BASE", "GEOMETRY", "FULL")
    for shrinkage in (8, 16, 32)
    for abstain in (Decimal("-0.10"), Decimal("-0.05"), Decimal("0"))
    for favorable in (Decimal("0.10"), Decimal("0.20"), Decimal("0.30"))
    for min_groups in (3, 5)
    for caution in (Decimal("0.25"), Decimal("0.50"))
    if favorable > abstain
)


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _values(rows: list[dict[str, object]], field: str) -> list[Decimal]:
    return [_d(row[field]) for row in rows]


def _metrics_values(values: list[Decimal]) -> dict[str, object]:
    if not values:
        return {
            "sample": 0,
            "wins": 0,
            "losses": 0,
            "flats": 0,
            "profit_factor": None,
            "total_r": "0",
            "mean_r": "0",
            "max_drawdown_r": "0",
            "max_losing_streak": 0,
        }
    gains = sum((v for v in values if v > 0), Decimal(0))
    losses_abs = -sum((v for v in values if v < 0), Decimal(0))
    total = sum(values, Decimal(0))
    equity = Decimal(0)
    peak = Decimal(0)
    max_dd = Decimal(0)
    streak = 0
    max_streak = 0
    for value in values:
        equity += value
        peak = max(peak, equity)
        max_dd = max(max_dd, peak - equity)
        if value < 0:
            streak += 1
            max_streak = max(max_streak, streak)
        else:
            streak = 0
    return {
        "sample": len(values),
        "wins": sum(v > 0 for v in values),
        "losses": sum(v < 0 for v in values),
        "flats": sum(v == 0 for v in values),
        "profit_factor": (
            None if losses_abs == 0 else format(gains / losses_abs, "f")
        ),
        "total_r": format(total, "f"),
        "mean_r": format(total / Decimal(len(values)), "f"),
        "max_drawdown_r": format(max_dd, "f"),
        "max_losing_streak": max_streak,
    }


def _metrics(
    rows: list[dict[str, object]],
    field: str = "net_r_after_friction",
) -> dict[str, object]:
    ordered = sorted(rows, key=lambda row: cast(str, row["signal_at"]))
    return _metrics_values(_values(ordered, field))


def _group_posterior(
    history: list[dict[str, object]],
    current: dict[str, object],
    fields: tuple[str, ...],
    *,
    global_mean: Decimal,
    shrinkage: int,
) -> tuple[Decimal, int] | None:
    key = tuple(str(current.get(field)) for field in fields)
    selected = [
        row
        for row in history
        if tuple(str(row.get(field)) for field in fields) == key
    ]
    if len(selected) < 4:
        return None
    total = sum((_d(row["net_r_after_friction"]) for row in selected), Decimal(0))
    n = Decimal(len(selected))
    alpha = Decimal(shrinkage)
    return (total + alpha * global_mean) / (n + alpha), len(selected)


def _score(
    history: list[dict[str, object]],
    current: dict[str, object],
    policy: Policy,
) -> tuple[Decimal | None, int]:
    if len(history) < 80:
        return None, 0
    for field in FORBIDDEN_CURRENT_FEATURES:
        if field in policy.features:
            raise AssertionError(f"post-outcome feature leaked into policy: {field}")
    global_mean = sum(
        (_d(row["net_r_after_friction"]) for row in history), Decimal(0)
    ) / Decimal(len(history))
    estimates: list[tuple[Decimal, Decimal]] = []
    for field in policy.features:
        item = _group_posterior(
            history,
            current,
            (field,),
            global_mean=global_mean,
            shrinkage=policy.shrinkage,
        )
        if item is not None:
            estimate, n = item
            estimates.append((estimate, Decimal(n).sqrt()))
    for fields in INTERACTIONS:
        if any(field not in policy.features for field in fields):
            continue
        item = _group_posterior(
            history,
            current,
            fields,
            global_mean=global_mean,
            shrinkage=policy.shrinkage,
        )
        if item is not None:
            estimate, n = item
            estimates.append((estimate, Decimal(n).sqrt() * Decimal("1.5")))
    if len(estimates) < policy.minimum_groups:
        return None, len(estimates)
    weight = sum((w for _, w in estimates), Decimal(0))
    return (
        sum((estimate * w for estimate, w in estimates), Decimal(0)) / weight,
        len(estimates),
    )


def _decision_and_weight(
    score: Decimal | None,
    policy: Policy,
) -> tuple[str, Decimal, str]:
    if score is None:
        return "PASS_INSUFFICIENT", Decimal("1"), "NEUTRAL"
    if score < policy.abstain_threshold:
        return "ABSTAIN_SHADOW", Decimal("0.25"), "CONFLICT"
    if score < policy.favorable_threshold:
        return "PASS_CAUTION", policy.caution_multiplier, "CAUTION"
    return "PASS_FAVORABLE", Decimal("1"), "FAVORABLE"


def _evaluate(
    history: list[dict[str, object]],
    rows: list[dict[str, object]],
    policy: Policy,
) -> dict[str, object]:
    decision_rows: list[dict[str, object]] = []
    weighted_rows: list[dict[str, object]] = []
    combined_rows: list[dict[str, object]] = []
    abstained: list[dict[str, object]] = []
    scores = 0
    score_sum = Decimal(0)

    for row in sorted(rows, key=lambda item: cast(str, item["signal_at"])):
        score, groups = _score(history, row, policy)
        action, multiplier, posture = _decision_and_weight(score, policy)
        updated = dict(row)
        updated["shared_score_r"] = None if score is None else format(score, "f")
        updated["shared_evidence_groups"] = groups
        updated["shared_decision_action"] = action
        updated["shared_economic_posture"] = posture
        updated["shadow_qore_risk_multiplier"] = format(multiplier, "f")
        if score is not None:
            scores += 1
            score_sum += score

        raw = _d(row["net_r_after_friction"])
        weighted = dict(updated)
        weighted["shared_weighted_r"] = format(raw * multiplier, "f")
        weighted_rows.append(weighted)

        if action == "ABSTAIN_SHADOW":
            abstained.append(updated)
        else:
            decision_rows.append(updated)
            combined = dict(updated)
            combined["shared_weighted_r"] = format(raw * multiplier, "f")
            combined_rows.append(combined)

    baseline = _metrics(rows)
    decision = _metrics(decision_rows)
    potentiation = _metrics(weighted_rows, "shared_weighted_r")
    combined = _metrics(combined_rows, "shared_weighted_r")

    base_losses = int(baseline["losses"])
    base_wins = int(baseline["wins"])
    losses_avoided = sum(_d(row["net_r_after_friction"]) < 0 for row in abstained)
    winners_sacrificed = sum(_d(row["net_r_after_friction"]) > 0 for row in abstained)
    return {
        "baseline": baseline,
        "mission_1_decision_support": {
            "metrics": decision,
            "abstained": len(abstained),
            "losses_avoided": losses_avoided,
            "winners_sacrificed": winners_sacrificed,
            "loss_rejection_recall": (
                format(Decimal(losses_avoided) / Decimal(base_losses), "f")
                if base_losses else "0"
            ),
            "winner_retention": (
                format(Decimal(base_wins - winners_sacrificed) / Decimal(base_wins), "f")
                if base_wins else "0"
            ),
            "density_retained": (
                format(Decimal(len(decision_rows)) / Decimal(len(rows)), "f")
                if rows else "0"
            ),
        },
        "mission_2_trade_potentiation": {
            "metrics": potentiation,
            "trade_count_preserved": len(weighted_rows) == len(rows),
            "shared_risk_authority": False,
            "qore_risk_shadow_transform": True,
        },
        "combined": {
            "metrics": combined,
            "trade_count": len(combined_rows),
        },
        "score_coverage": {
            "scored": scores,
            "mean_score_r": (
                None if scores == 0 else format(score_sum / Decimal(scores), "f")
            ),
        },
    }


def _ratio(new: object, old: object) -> Decimal:
    return _d(new) / _d(old)


def _calibration_score(result: dict[str, object]) -> Decimal | None:
    baseline = cast(dict[str, object], result["baseline"])
    m1 = cast(dict[str, object], result["mission_1_decision_support"])
    m2 = cast(dict[str, object], result["mission_2_trade_potentiation"])
    dmet = cast(dict[str, object], m1["metrics"])
    pmet = cast(dict[str, object], m2["metrics"])

    density = _d(m1["density_retained"])
    winner_retention = _d(m1["winner_retention"])
    loss_recall = _d(m1["loss_rejection_recall"])
    if density < Decimal("0.60") or density > Decimal("0.92"):
        return None
    if winner_retention < Decimal("0.80"):
        return None
    if loss_recall < Decimal("0.12"):
        return None

    bpf = baseline["profit_factor"]
    dpf = dmet["profit_factor"]
    ppf = pmet["profit_factor"]
    if bpf is None or dpf is None or ppf is None:
        return None
    if _ratio(dpf, bpf) < Decimal("1.10"):
        return None
    if _ratio(ppf, bpf) < Decimal("1.10"):
        return None

    bdd = _d(baseline["max_drawdown_r"])
    ddd = _d(dmet["max_drawdown_r"])
    pdd = _d(pmet["max_drawdown_r"])
    if ddd > bdd * Decimal("0.90"):
        return None
    if pdd > bdd:
        return None

    return (
        _ratio(dpf, bpf)
        * _ratio(ppf, bpf)
        * (bdd / max(ddd, Decimal("0.000001")))
        * winner_retention
    )


def _gates(result: dict[str, object]) -> dict[str, bool]:
    baseline = cast(dict[str, object], result["baseline"])
    m1 = cast(dict[str, object], result["mission_1_decision_support"])
    m2 = cast(dict[str, object], result["mission_2_trade_potentiation"])
    combined = cast(dict[str, object], result["combined"])
    dmet = cast(dict[str, object], m1["metrics"])
    pmet = cast(dict[str, object], m2["metrics"])
    cmet = cast(dict[str, object], combined["metrics"])

    bpf = _d(cast(object, baseline["profit_factor"]))
    dpf = _d(cast(object, dmet["profit_factor"]))
    ppf = _d(cast(object, pmet["profit_factor"]))
    cpf = _d(cast(object, cmet["profit_factor"]))
    bdd = _d(baseline["max_drawdown_r"])
    return {
        "mission1_pf_improvement_at_least_20pct": dpf >= bpf * Decimal("1.20"),
        "mission1_dd_reduction_at_least_25pct": (
            _d(dmet["max_drawdown_r"]) <= bdd * Decimal("0.75")
        ),
        "mission1_loss_rejection_recall_at_least_20pct": (
            _d(m1["loss_rejection_recall"]) >= Decimal("0.20")
        ),
        "mission1_winner_retention_at_least_75pct": (
            _d(m1["winner_retention"]) >= Decimal("0.75")
        ),
        "mission1_density_at_least_60pct": (
            _d(m1["density_retained"]) >= Decimal("0.60")
        ),
        "mission2_pf_improvement_at_least_15pct": ppf >= bpf * Decimal("1.15"),
        "mission2_dd_not_worse": _d(pmet["max_drawdown_r"]) <= bdd,
        "mission2_trade_count_preserved": bool(m2["trade_count_preserved"]),
        "combined_pf_above_both_individual_missions": (
            cpf >= max(dpf, ppf)
        ),
        "combined_dd_below_baseline": _d(cmet["max_drawdown_r"]) < bdd,
    }


def run(r8: Path, r6: Path, r5: Path) -> dict[str, object]:
    r8_result = native.replay(r8, partition="r8")
    r6_result = native.replay(r6, partition="r6")
    r5_result = native.replay(r5, partition="r5")
    r8_rows = cast(list[dict[str, object]], r8_result["trades"])
    r6_rows = cast(list[dict[str, object]], r6_result["trades"])
    r5_rows = cast(list[dict[str, object]], r5_result["trades"])

    if len(r8_rows) + len(r6_rows) + len(r5_rows) != 822:
        raise AssertionError("VT31 pure 5Y challenge set drift")
    if sum(_d(row["net_r_after_friction"]) < 0 for row in r8_rows + r6_rows + r5_rows) != 711:
        raise AssertionError("VT31 711-loss challenge set drift")
    if sum(_d(row["net_r_after_friction"]) > 0 for row in r8_rows + r6_rows + r5_rows) != 111:
        raise AssertionError("VT31 111-winner challenge set drift")

    frontier: list[dict[str, object]] = []
    best: tuple[Decimal, Policy] | None = None
    for policy in POLICIES:
        result = _evaluate(r8_rows, r6_rows, policy)
        score = _calibration_score(result)
        frontier.append({
            "policy": policy.payload(),
            "calibration": result,
            "selection_score": None if score is None else format(score, "f"),
        })
        if score is not None and (best is None or score > best[0]):
            best = (score, policy)

    if best is None:
        raise AssertionError("no Shared dual-mission calibration survivor")

    frozen = best[1]
    evaluation = _evaluate(r8_rows + r6_rows, r5_rows, frozen)
    gates = _gates(evaluation)
    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "challenge_set": {
            "source_only_trades_5y": 822,
            "winners_5y": 111,
            "losses_5y": 711,
            "r8": r8_result["metrics"],
            "r6": r6_result["metrics"],
            "r5": r5_result["metrics"],
        },
        "temporal_protocol": {
            "r8": "DISCOVERY_MEMORY_ONLY",
            "r6": "CALIBRATION_POLICY_FREEZE",
            "r5": "NO_RETUNE_TEMPORAL_EVALUATION",
        },
        "forbidden_current_features": FORBIDDEN_CURRENT_FEATURES,
        "policy_frontier_size": len(POLICIES),
        "frozen_policy": frozen.payload(),
        "evaluation": evaluation,
        "gates": gates,
        "passes_dual_mission": all(gates.values()),
        "governance": {
            "silver_bullet_methodology_modified": False,
            "shared_order_authority": False,
            "shared_risk_authority": False,
            "qore_risk_sovereign": True,
            "current_trade_outcome_used_by_shared": False,
            "post_outcome_features_used_by_shared": False,
            "r5_retuned_after_open": False,
            "live_authorized": False,
            "production_authorized": False,
            "merge_authorized": False,
        },
        "frontier": frontier,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--r8", type=Path, required=True)
    parser.add_argument("--r6", type=Path, required=True)
    parser.add_argument("--r5", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = run(args.r8, args.r6, args.r5)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    summary = {
        "identity": payload["identity"],
        "frozen_policy": payload["frozen_policy"],
        "evaluation": payload["evaluation"],
        "gates": payload["gates"],
        "passes_dual_mission": payload["passes_dual_mission"],
    }
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
