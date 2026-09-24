"""VT31 Shared Situation Relation Stability Bank V4.

Purpose:
- express current market state relative to the trade side, not as absolute
  labels such as H1=bullish;
- require each rejection rule to combine a directional/context relation with
  an independent present-market situation feature;
- require R8 internal temporal stability before a rule may reach R6;
- freeze on R6 only if all hard gates pass; R5 remains no-retune.

Runtime rule inputs are present-market causal observations only.
Historical outcomes are offline research labels only.
"""
# ruff: noqa: B009,E501
from __future__ import annotations

import argparse
import itertools
import json
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_core_stack_v3_analog_world_model_v1 as core_v3
import vt31_core_stack_v4_perception_first_v2 as perception
import vt31_core_stack_v4_situation_rule_bank_v3 as bank_v3

SCHEMA = "qore.core_stack_v4.vt31.situation_relation_stability.v4"
IDENTITY = "VT31_NAS100_SHARED_SITUATION_RELATION_STABILITY_V4"


@dataclass(frozen=True, slots=True)
class StabilityPolicy:
    minimum_support: int
    minimum_half_support: int
    minimum_loss_rate: Decimal
    maximum_cell_total_r: Decimal
    winner_cost_multiplier: Decimal
    maximum_rules: int

    def payload(self) -> dict[str, object]:
        return {
            "minimum_support": self.minimum_support,
            "minimum_half_support": self.minimum_half_support,
            "minimum_loss_rate": format(self.minimum_loss_rate, "f"),
            "maximum_cell_total_r": format(self.maximum_cell_total_r, "f"),
            "winner_cost_multiplier": format(self.winner_cost_multiplier, "f"),
            "maximum_rules": self.maximum_rules,
        }


POLICIES = tuple(
    StabilityPolicy(
        minimum_support=support,
        minimum_half_support=half,
        minimum_loss_rate=loss_rate,
        maximum_cell_total_r=total_r,
        winner_cost_multiplier=winner_cost,
        maximum_rules=max_rules,
    )
    for support in (8, 12, 16)
    for half in (3, 4)
    for loss_rate in (Decimal("0.82"), Decimal("0.86"), Decimal("0.90"))
    for total_r in (Decimal("0"), Decimal("-2"))
    for winner_cost in (Decimal("2.5"), Decimal("4"), Decimal("6"))
    for max_rules in (4, 6, 10)
)


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _relative_direction(raw: object, side: str) -> str:
    value = str(raw).lower()
    if value in {"unavailable", "mixed", "flat", "rotation"}:
        return value.upper()
    if value == "bullish":
        return "ALIGNED" if side == "long" else "OPPOSED"
    if value == "bearish":
        return "ALIGNED" if side == "short" else "OPPOSED"
    return value.upper()


def _relative_prior_range(raw: object, side: str) -> str:
    value = str(raw).lower()
    if value == "middle-third":
        return "MIDDLE"
    if side == "long":
        if value in {"below", "lower-third"}:
            return "FAVORABLE_SIDE"
        if value in {"above", "upper-third"}:
            return "ADVERSE_SIDE"
    elif side == "short":
        if value in {"above", "upper-third"}:
            return "FAVORABLE_SIDE"
        if value in {"below", "lower-third"}:
            return "ADVERSE_SIDE"
    return value.upper()


def _decorate(row: dict[str, object]) -> dict[str, object]:
    out = bank_v3._decorate_bins(row)
    side = str(out["side"])
    out["h1_relation"] = _relative_direction(out.get("h1_state_hr"), side)
    out["h4_relation"] = _relative_direction(out.get("h4_state_hr"), side)
    out["premarket_relation"] = _relative_direction(
        out.get("premarket_state_hr"), side
    )
    out["cash_open_relation"] = _relative_direction(
        out.get("cash_open_state_hr"), side
    )
    out["prior_day_relation"] = _relative_direction(
        out.get("prior_day_state_hr"), side
    )
    out["prior_range_relation"] = _relative_prior_range(
        out.get("position_in_prior_day_range_hr"), side
    )
    return out


RELATION_FIELDS = (
    "h1_relation",
    "h4_relation",
    "premarket_relation",
    "cash_open_relation",
    "prior_day_relation",
    "prior_range_relation",
    "alignment5",
    "alignment20",
    "peer_consensus",
)

SITUATION_FIELDS = (
    "perception_regime",
    "perception_transition",
    "momentum_state",
    "volatility_state",
    "structure_state",
    "trend_bucket",
    "range_bucket",
    "expansion_bucket",
    "exhaustion_bucket",
    "uncertainty_bucket",
    "pre_behavior_proxy",
    "pre_eff_bucket",
    "pre_overlap_bucket",
    "pre_displacement_bucket",
    "pre_sweep_bucket",
    "pre_fvg_bucket",
    "raid_depth_bucket",
)


def _stable_field_sets() -> tuple[tuple[str, str], ...]:
    return tuple(
        (left, right)
        for left in RELATION_FIELDS
        for right in SITUATION_FIELDS
        if left != right
    )


def _rule_stats(
    members: list[dict[str, object]],
    *,
    winner_cost_multiplier: Decimal,
) -> dict[str, object]:
    values = [_d(row["net_r_after_friction"]) for row in members]
    losses = sum(value < 0 for value in values)
    wins = sum(value > 0 for value in values)
    support = len(values)
    total_r = sum(values, Decimal(0))
    winner_r = sum((value for value in values if value > 0), Decimal(0))
    loss_r = -sum((value for value in values if value < 0), Decimal(0))
    return {
        "support": support,
        "losses": losses,
        "wins": wins,
        "loss_rate": (
            Decimal(0)
            if support == 0
            else Decimal(losses) / Decimal(support)
        ),
        "total_r": total_r,
        "winner_r": winner_r,
        "loss_r": loss_r,
        "utility": loss_r - winner_cost_multiplier * winner_r,
    }


def _candidate_rules(
    rows: list[dict[str, object]],
    policy: StabilityPolicy,
) -> list[bank_v3.Rule]:
    ordered = sorted(rows, key=lambda row: cast(str, row["signal_at"]))
    cut = max(1, len(ordered) // 2)
    early_ids = {
        cast(str, row["signal_at"]) for row in ordered[:cut]
    }
    late_ids = {
        cast(str, row["signal_at"]) for row in ordered[cut:]
    }

    rules: list[bank_v3.Rule] = []
    for fields in _stable_field_sets():
        groups: dict[tuple[str, ...], list[dict[str, object]]] = {}
        for row in rows:
            values = tuple(
                str(row.get(field, "UNAVAILABLE")) for field in fields
            )
            groups.setdefault(values, []).append(row)

        for values, members in groups.items():
            overall = _rule_stats(
                members,
                winner_cost_multiplier=policy.winner_cost_multiplier,
            )
            if int(overall["support"]) < policy.minimum_support:
                continue
            if cast(Decimal, overall["loss_rate"]) < policy.minimum_loss_rate:
                continue
            if cast(Decimal, overall["total_r"]) > policy.maximum_cell_total_r:
                continue
            if cast(Decimal, overall["utility"]) <= 0:
                continue

            early = [
                row
                for row in members
                if cast(str, row["signal_at"]) in early_ids
            ]
            late = [
                row
                for row in members
                if cast(str, row["signal_at"]) in late_ids
            ]
            if (
                len(early) < policy.minimum_half_support
                or len(late) < policy.minimum_half_support
            ):
                continue
            early_stats = _rule_stats(
                early,
                winner_cost_multiplier=policy.winner_cost_multiplier,
            )
            late_stats = _rule_stats(
                late,
                winner_cost_multiplier=policy.winner_cost_multiplier,
            )
            if (
                cast(Decimal, early_stats["loss_rate"])
                < policy.minimum_loss_rate
                or cast(Decimal, late_stats["loss_rate"])
                < policy.minimum_loss_rate
            ):
                continue
            if (
                cast(Decimal, early_stats["total_r"]) > Decimal(0)
                or cast(Decimal, late_stats["total_r"]) > Decimal(0)
            ):
                continue
            if (
                cast(Decimal, early_stats["utility"]) <= 0
                or cast(Decimal, late_stats["utility"]) <= 0
            ):
                continue

            rules.append(
                bank_v3.Rule(
                    fields=fields,
                    values=values,
                    support=int(overall["support"]),
                    losses=int(overall["losses"]),
                    wins=int(overall["wins"]),
                    loss_rate=cast(Decimal, overall["loss_rate"]),
                    total_r=cast(Decimal, overall["total_r"]),
                    winner_r=cast(Decimal, overall["winner_r"]),
                    loss_r=cast(Decimal, overall["loss_r"]),
                    utility=cast(Decimal, overall["utility"]),
                )
            )

    rules.sort(
        key=lambda rule: (
            rule.utility,
            rule.losses,
            -rule.winner_r,
            rule.support,
            rule.fields,
            rule.values,
        ),
        reverse=True,
    )
    return rules


def _select_bank(
    rows: list[dict[str, object]],
    candidates: list[bank_v3.Rule],
    policy: StabilityPolicy,
) -> list[bank_v3.Rule]:
    selected: list[bank_v3.Rule] = []
    rejected: set[str] = set()

    for rule in candidates:
        if len(selected) >= policy.maximum_rules:
            break
        matched = [
            row
            for row in rows
            if bank_v3._rule_matches(rule, row)
            and cast(str, row["signal_at"]) not in rejected
        ]
        if not matched:
            continue
        stats = _rule_stats(
            matched,
            winner_cost_multiplier=policy.winner_cost_multiplier,
        )
        if cast(Decimal, stats["utility"]) <= 0:
            continue
        if (
            cast(Decimal, stats["loss_rate"])
            < policy.minimum_loss_rate
        ):
            continue
        selected.append(rule)
        rejected.update(
            cast(str, row["signal_at"]) for row in matched
        )
    return selected


def _score(result: dict[str, object]) -> Decimal | None:
    gates = bank_v3._gates(result)
    if not all(gates.values()):
        return None
    baseline = cast(dict[str, object], result["baseline"])
    shared = cast(dict[str, object], result["shared_situation_rules"])
    selection = cast(dict[str, object], result["selection"])
    return (
        _d(cast(object, shared["profit_factor"]))
        / _d(cast(object, baseline["profit_factor"]))
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
    daily = core_v3._load_daily(daily_path)
    r8 = [
        _decorate(row)
        for row in perception._perception_rows(
            r8_raw,
            core_v3._decorate(core_v3._load_trades(r8_trades), daily),
        )
    ]
    r6 = [
        _decorate(row)
        for row in perception._perception_rows(
            r6_raw,
            core_v3._decorate(core_v3._load_trades(r6_trades), daily),
        )
    ]
    r5 = [
        _decorate(row)
        for row in perception._perception_rows(
            r5_raw,
            core_v3._decorate(core_v3._load_trades(r5_trades), daily),
        )
    ]
    all_rows = r8 + r6 + r5
    if len(all_rows) != 822:
        raise AssertionError("VT31 challenge set drift")
    if sum(_d(row["net_r_after_friction"]) < 0 for row in all_rows) != 711:
        raise AssertionError("VT31 loss binding drift")
    if sum(_d(row["net_r_after_friction"]) > 0 for row in all_rows) != 111:
        raise AssertionError("VT31 winner binding drift")

    frontier: list[dict[str, object]] = []
    best: tuple[
        Decimal,
        StabilityPolicy,
        list[bank_v3.Rule],
    ] | None = None

    for policy in POLICIES:
        candidates = _candidate_rules(r8, policy)
        rules = _select_bank(r8, candidates, policy)
        if not rules:
            continue

        r8_result = bank_v3._evaluate(r8, rules)
        r8_gates = bank_v3._gates(r8_result)
        if not all(r8_gates.values()):
            frontier.append({
                "policy": policy.payload(),
                "rule_count": len(rules),
                "rules": [rule.payload() for rule in rules],
                "r8": r8_result,
                "r8_gates": r8_gates,
                "r6": None,
                "r6_gates": None,
                "score": None,
            })
            continue

        r6_result = bank_v3._evaluate(r6, rules)
        r6_gates = bank_v3._gates(r6_result)
        score = _score(r6_result)
        frontier.append({
            "policy": policy.payload(),
            "rule_count": len(rules),
            "rules": [rule.payload() for rule in rules],
            "r8": r8_result,
            "r8_gates": r8_gates,
            "r6": r6_result,
            "r6_gates": r6_gates,
            "score": None if score is None else format(score, "f"),
        })
        if score is not None and (best is None or score > best[0]):
            best = (score, policy, rules)

    if best is None:
        return {
            "schema": SCHEMA,
            "identity": IDENTITY,
            "economic_status": "FALSIFIED_BEFORE_R5",
            "challenge_set": {"trades": 822, "losses": 711, "wins": 111},
            "frozen_policy": None,
            "frozen_rules": None,
            "evaluation": None,
            "gates": None,
            "passes_relation_stability": False,
            "frontier": frontier,
            "governance": _governance(),
        }

    _, frozen_policy, frozen_rules = best
    evaluation = bank_v3._evaluate(r5, frozen_rules)
    gates = bank_v3._gates(evaluation)
    passed = all(gates.values())
    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "economic_status": (
            "PASSED_TEMPORAL_EVALUATION"
            if passed
            else "FALSIFIED_ON_R5"
        ),
        "challenge_set": {"trades": 822, "losses": 711, "wins": 111},
        "temporal_protocol": {
            "r8": "RELATIVE_RULE_DISCOVERY_WITH_INTERNAL_STABILITY",
            "r6": "EXTERNAL_CALIBRATION_AND_FREEZE",
            "r5": "NO_RETUNE_EVALUATION",
        },
        "frozen_policy": frozen_policy.payload(),
        "frozen_rules": [rule.payload() for rule in frozen_rules],
        "evaluation": evaluation,
        "gates": gates,
        "passes_relation_stability": passed,
        "frontier": frontier,
        "governance": _governance(),
    }


def _governance() -> dict[str, bool]:
    return {
        "absolute_direction_rule_forbidden": True,
        "relative_to_trade_side_required": True,
        "rule_requires_relation_plus_situation": True,
        "r8_internal_temporal_stability_required": True,
        "runtime_analog_lookup_used": False,
        "runtime_outcome_label_used": False,
        "runtime_rule_inputs_present_market_only": True,
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
    args.output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n"
    )
    print(json.dumps({
        "economic_status": payload["economic_status"],
        "passes_relation_stability": payload["passes_relation_stability"],
        "frozen_policy": payload["frozen_policy"],
        "evaluation": payload["evaluation"],
        "gates": payload["gates"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
