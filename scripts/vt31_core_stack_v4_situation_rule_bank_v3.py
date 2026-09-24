"""Perception-first Situation Rule Bank V3 for VT31.

This is supervised offline research, not runtime historical lookup.

R8 builds a compact set of deterministic causal rules from present-market
perception states. R6 only selects the frozen rule-bank hyperparameters.
R5 is untouched temporal evaluation.

At runtime a trade is evaluated only against its *current* perception fields.
There is no nearest-neighbour/analog query and no outcome/PnL input.
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

import vt31_core_stack_v3_analog_world_model_v1 as v3
import vt31_core_stack_v4_perception_first_v2 as pf

SCHEMA = "qore.core_stack_v4.vt31.situation_rule_bank.v3"
IDENTITY = "VT31_NAS100_SHARED_SITUATION_RULE_BANK_V3"

BASE_FIELDS = (
    "perception_regime",
    "momentum_state",
    "volatility_state",
    "structure_state",
    "alignment5",
    "alignment20",
    "peer_consensus",
    "pre_behavior_proxy",
    "h1_state_hr",
    "h4_state_hr",
    "premarket_state_hr",
    "cash_open_state_hr",
    "position_in_prior_day_range_hr",
)


@dataclass(frozen=True, slots=True)
class Rule:
    fields: tuple[str, ...]
    values: tuple[str, ...]
    support: int
    losses: int
    wins: int
    loss_rate: Decimal
    total_r: Decimal
    winner_r: Decimal
    loss_r: Decimal
    utility: Decimal

    def payload(self) -> dict[str, object]:
        return {
            "fields": self.fields,
            "values": self.values,
            "support": self.support,
            "losses": self.losses,
            "wins": self.wins,
            "loss_rate": format(self.loss_rate, "f"),
            "total_r": format(self.total_r, "f"),
            "winner_r": format(self.winner_r, "f"),
            "loss_r": format(self.loss_r, "f"),
            "utility": format(self.utility, "f"),
        }


@dataclass(frozen=True, slots=True)
class BankPolicy:
    minimum_support: int
    minimum_loss_rate: Decimal
    maximum_cell_total_r: Decimal
    winner_cost_multiplier: Decimal
    maximum_rules: int
    maximum_rule_width: int

    def payload(self) -> dict[str, object]:
        return {
            "minimum_support": self.minimum_support,
            "minimum_loss_rate": format(self.minimum_loss_rate, "f"),
            "maximum_cell_total_r": format(self.maximum_cell_total_r, "f"),
            "winner_cost_multiplier": format(self.winner_cost_multiplier, "f"),
            "maximum_rules": self.maximum_rules,
            "maximum_rule_width": self.maximum_rule_width,
        }


POLICIES = tuple(
    BankPolicy(
        minimum_support=support,
        minimum_loss_rate=loss_rate,
        maximum_cell_total_r=total_r,
        winner_cost_multiplier=winner_cost,
        maximum_rules=max_rules,
        maximum_rule_width=width,
    )
    for support in (8, 12, 16)
    for loss_rate in (Decimal("0.88"), Decimal("0.92"), Decimal("0.95"))
    for total_r in (Decimal("0"), Decimal("-2"))
    for winner_cost in (Decimal("1.5"), Decimal("2.5"), Decimal("4"))
    for max_rules in (6, 10, 16, 24)
    for width in (1, 2)
)


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _bucket(value: object, cuts: tuple[Decimal, ...], labels: tuple[str, ...]) -> str:
    try:
        number = _d(value)
    except Exception:
        return "UNAVAILABLE"
    for cut, label in zip(cuts, labels, strict=False):
        if number < cut:
            return label
    return labels[-1]


def _decorate_bins(row: dict[str, object]) -> dict[str, object]:
    out = dict(row)
    out["trend_bucket"] = _bucket(
        row["trend_pressure"],
        (Decimal("0.35"), Decimal("0.55"), Decimal("0.70")),
        ("LOW", "MID", "HIGH", "EXTREME"),
    )
    out["range_bucket"] = _bucket(
        row["range_pressure"],
        (Decimal("0.35"), Decimal("0.55"), Decimal("0.70")),
        ("LOW", "MID", "HIGH", "EXTREME"),
    )
    out["expansion_bucket"] = _bucket(
        row["expansion_pressure"],
        (Decimal("0.25"), Decimal("0.45"), Decimal("0.65")),
        ("LOW", "MID", "HIGH", "EXTREME"),
    )
    out["exhaustion_bucket"] = _bucket(
        row["exhaustion_pressure"],
        (Decimal("0.15"), Decimal("0.30"), Decimal("0.50")),
        ("LOW", "MID", "HIGH", "EXTREME"),
    )
    out["uncertainty_bucket"] = _bucket(
        row["uncertainty_pressure"],
        (Decimal("0.25"), Decimal("0.45"), Decimal("0.65")),
        ("LOW", "MID", "HIGH", "EXTREME"),
    )
    out["pre_eff_bucket"] = _bucket(
        row.get("pre_path_efficiency", "unavailable"),
        (Decimal("0.25"), Decimal("0.50"), Decimal("0.75")),
        ("LOW", "MID", "HIGH", "EXTREME"),
    )
    out["pre_overlap_bucket"] = _bucket(
        row.get("pre_overlap_rate", "unavailable"),
        (Decimal("0.35"), Decimal("0.60"), Decimal("0.80")),
        ("LOW", "MID", "HIGH", "EXTREME"),
    )
    out["pre_displacement_bucket"] = _bucket(
        row.get("pre_displacement_count", "unavailable"),
        (Decimal("1"), Decimal("3"), Decimal("6")),
        ("ZERO", "LOW", "MID", "HIGH"),
    )
    out["pre_sweep_bucket"] = _bucket(
        row.get("pre_sweep_reclaim_count", "unavailable"),
        (Decimal("1"), Decimal("2"), Decimal("4")),
        ("ZERO", "ONE", "FEW", "MANY"),
    )
    out["pre_fvg_bucket"] = _bucket(
        row.get("pre_fvg_count", "unavailable"),
        (Decimal("1"), Decimal("3"), Decimal("6")),
        ("ZERO", "LOW", "MID", "HIGH"),
    )
    out["raid_depth_bucket"] = _bucket(
        row.get("raid_depth_ref_hr", "unavailable"),
        (Decimal("0.10"), Decimal("0.25"), Decimal("0.50")),
        ("SHALLOW", "MID", "DEEP", "EXTREME"),
    )
    return out


RULE_FIELDS = BASE_FIELDS + (
    "trend_bucket",
    "range_bucket",
    "expansion_bucket",
    "exhaustion_bucket",
    "uncertainty_bucket",
    "pre_eff_bucket",
    "pre_overlap_bucket",
    "pre_displacement_bucket",
    "pre_sweep_bucket",
    "pre_fvg_bucket",
    "raid_depth_bucket",
)


def _rule_matches(rule: Rule, row: dict[str, object]) -> bool:
    return all(str(row.get(field, "UNAVAILABLE")) == value for field, value in zip(rule.fields, rule.values, strict=True))


def _build_rules(rows: list[dict[str, object]], policy: BankPolicy) -> list[Rule]:
    rules: list[Rule] = []
    field_sets: list[tuple[str, ...]] = [(field,) for field in RULE_FIELDS]
    if policy.maximum_rule_width >= 2:
        field_sets.extend(itertools.combinations(RULE_FIELDS, 2))

    for fields in field_sets:
        groups: dict[tuple[str, ...], list[dict[str, object]]] = {}
        for row in rows:
            values = tuple(str(row.get(field, "UNAVAILABLE")) for field in fields)
            groups.setdefault(values, []).append(row)
        for values, members in groups.items():
            support = len(members)
            if support < policy.minimum_support:
                continue
            returns = [_d(row["net_r_after_friction"]) for row in members]
            losses = sum(value < 0 for value in returns)
            wins = sum(value > 0 for value in returns)
            loss_rate = Decimal(losses) / Decimal(support)
            total_r = sum(returns, Decimal(0))
            if loss_rate < policy.minimum_loss_rate or total_r > policy.maximum_cell_total_r:
                continue
            winner_r = sum((value for value in returns if value > 0), Decimal(0))
            loss_r = -sum((value for value in returns if value < 0), Decimal(0))
            utility = loss_r - policy.winner_cost_multiplier * winner_r
            if utility <= 0:
                continue
            rules.append(
                Rule(
                    fields=tuple(fields),
                    values=values,
                    support=support,
                    losses=losses,
                    wins=wins,
                    loss_rate=loss_rate,
                    total_r=total_r,
                    winner_r=winner_r,
                    loss_r=loss_r,
                    utility=utility,
                )
            )
    rules.sort(
        key=lambda rule: (
            rule.utility,
            rule.losses,
            -rule.winner_r,
            rule.support,
            tuple(rule.fields),
            rule.values,
        ),
        reverse=True,
    )
    return rules


def _select_bank(
    rows: list[dict[str, object]],
    candidates: list[Rule],
    maximum_rules: int,
) -> list[Rule]:
    selected: list[Rule] = []
    currently_rejected: set[str] = set()

    for rule in candidates:
        if len(selected) >= maximum_rules:
            break
        matched = [
            row
            for row in rows
            if _rule_matches(rule, row)
            and cast(str, row["signal_at"]) not in currently_rejected
        ]
        if not matched:
            continue
        returns = [_d(row["net_r_after_friction"]) for row in matched]
        loss_r = -sum((value for value in returns if value < 0), Decimal(0))
        winner_r = sum((value for value in returns if value > 0), Decimal(0))
        marginal = loss_r - Decimal("2.5") * winner_r
        if marginal <= 0:
            continue
        selected.append(rule)
        currently_rejected.update(cast(str, row["signal_at"]) for row in matched)
    return selected


def _metrics(values: list[Decimal]) -> dict[str, object]:
    return pf._metrics(values)


def _evaluate(rows: list[dict[str, object]], rules: list[Rule]) -> dict[str, object]:
    ordered = sorted(rows, key=lambda row: cast(str, row["signal_at"]))
    baseline_values: list[Decimal] = []
    kept_values: list[Decimal] = []
    abstained: list[dict[str, object]] = []
    rule_hits: dict[str, int] = {}

    for row in ordered:
        value = _d(row["net_r_after_friction"])
        baseline_values.append(value)
        matched = next((rule for rule in rules if _rule_matches(rule, row)), None)
        if matched is None:
            kept_values.append(value)
            continue
        abstained.append(row)
        key = "&".join(
            f"{field}={value}"
            for field, value in zip(matched.fields, matched.values, strict=True)
        )
        rule_hits[key] = rule_hits.get(key, 0) + 1

    baseline = _metrics(baseline_values)
    shared = _metrics(kept_values)
    base_losses = int(baseline["losses"])
    base_wins = int(baseline["wins"])
    losses_avoided = sum(_d(row["net_r_after_friction"]) < 0 for row in abstained)
    winners_sacrificed = sum(_d(row["net_r_after_friction"]) > 0 for row in abstained)
    gross_winner_r = sum((v for v in baseline_values if v > 0), Decimal(0))
    sacrificed_winner_r = sum(
        (
            _d(row["net_r_after_friction"])
            for row in abstained
            if _d(row["net_r_after_friction"]) > 0
        ),
        Decimal(0),
    )
    return {
        "baseline": baseline,
        "shared_situation_rules": shared,
        "selection": {
            "input": len(rows),
            "kept": len(kept_values),
            "abstained": len(abstained),
            "losses_avoided": losses_avoided,
            "winners_sacrificed": winners_sacrificed,
            "loss_rejection_recall": "0" if base_losses == 0 else format(Decimal(losses_avoided) / Decimal(base_losses), "f"),
            "winner_count_retention": "0" if base_wins == 0 else format(Decimal(base_wins - winners_sacrificed) / Decimal(base_wins), "f"),
            "winner_r_retention": "1" if gross_winner_r == 0 else format((gross_winner_r - sacrificed_winner_r) / gross_winner_r, "f"),
            "density_retained": "0" if not rows else format(Decimal(len(kept_values)) / Decimal(len(rows)), "f"),
        },
        "rule_hits": dict(sorted(rule_hits.items())),
    }


def _gates(result: dict[str, object]) -> dict[str, bool]:
    baseline = cast(dict[str, object], result["baseline"])
    shared = cast(dict[str, object], result["shared_situation_rules"])
    selection = cast(dict[str, object], result["selection"])
    if baseline["profit_factor"] is None or shared["profit_factor"] is None:
        return {"valid": False}
    bpf = _d(cast(object, baseline["profit_factor"]))
    spf = _d(cast(object, shared["profit_factor"]))
    bdd = _d(baseline["max_drawdown_r"])
    sdd = _d(shared["max_drawdown_r"])
    return {
        "pf_plus_25pct": spf >= bpf * Decimal("1.25"),
        "dd_minus_30pct": sdd <= bdd * Decimal("0.70"),
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
    daily = v3._load_daily(daily_path)
    r8 = [
        _decorate_bins(row)
        for row in pf._perception_rows(
            r8_raw,
            v3._decorate(v3._load_trades(r8_trades), daily),
        )
    ]
    r6 = [
        _decorate_bins(row)
        for row in pf._perception_rows(
            r6_raw,
            v3._decorate(v3._load_trades(r6_trades), daily),
        )
    ]
    r5 = [
        _decorate_bins(row)
        for row in pf._perception_rows(
            r5_raw,
            v3._decorate(v3._load_trades(r5_trades), daily),
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
    best: tuple[Decimal, BankPolicy, list[Rule]] | None = None

    for policy in POLICIES:
        candidates = _build_rules(r8, policy)
        rules = _select_bank(r8, candidates, policy.maximum_rules)
        if not rules:
            continue
        r8_result = _evaluate(r8, rules)
        # Do not let a bad discovery bank reach calibration.
        r8_gates = _gates(r8_result)
        if not all(r8_gates.values()):
            frontier.append({
                "policy": policy.payload(),
                "rule_count": len(rules),
                "r8": r8_result,
                "r8_gates": r8_gates,
                "r6": None,
                "r6_gates": None,
                "score": None,
            })
            continue
        r6_result = _evaluate(r6, rules)
        r6_gates = _gates(r6_result)
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
            "passes_situation_rule_bank": False,
            "frontier": frontier,
            "governance": _governance(),
        }

    _, frozen_policy, frozen_rules = best
    evaluation = _evaluate(r5, frozen_rules)
    gates = _gates(evaluation)
    passed = all(gates.values())
    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "economic_status": "PASSED_TEMPORAL_EVALUATION" if passed else "FALSIFIED_ON_R5",
        "challenge_set": {"trades": 822, "losses": 711, "wins": 111},
        "temporal_protocol": {
            "r8": "BUILD_FIXED_CAUSAL_SITUATION_RULES",
            "r6": "VALIDATE_AND_FREEZE_RULE_BANK",
            "r5": "NO_RETUNE_EVALUATION",
        },
        "frozen_policy": frozen_policy.payload(),
        "frozen_rules": [rule.payload() for rule in frozen_rules],
        "evaluation": evaluation,
        "gates": gates,
        "passes_situation_rule_bank": passed,
        "frontier": frontier,
        "governance": _governance(),
    }


def _governance() -> dict[str, bool]:
    return {
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
    args.output.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    print(json.dumps({
        "economic_status": payload["economic_status"],
        "passes_situation_rule_bank": payload["passes_situation_rule_bank"],
        "frozen_policy": payload["frozen_policy"],
        "evaluation": payload["evaluation"],
        "gates": payload["gates"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
