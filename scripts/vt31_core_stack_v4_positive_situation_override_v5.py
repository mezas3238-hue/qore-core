"""VT31 Shared Positive Situation Override V5.

Starts from the V4 stable side-relative loss detector. It does not weaken the
negative bank. Instead it learns a small bank of causal positive-situation
overrides from R8 only.

A trade rejected by the negative bank may be rescued only when a deterministic
present-market rule with internally stable positive economics also matches.
Runtime inputs remain current causal perception; no analog/PnL lookup occurs.
R6 selects/freezes the override policy. R5 remains untouched.
"""
# ruff: noqa: B009,E501
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_core_stack_v3_analog_world_model_v1 as core_v3
import vt31_core_stack_v4_perception_first_v2 as perception
import vt31_core_stack_v4_situation_relation_stability_v4 as relation_v4
import vt31_core_stack_v4_situation_rule_bank_v3 as bank_v3

SCHEMA = "qore.core_stack_v4.vt31.positive_situation_override.v5"
IDENTITY = "VT31_NAS100_SHARED_POSITIVE_SITUATION_OVERRIDE_V5"

NEGATIVE_POLICY = relation_v4.StabilityPolicy(
    minimum_support=8,
    minimum_half_support=3,
    minimum_loss_rate=Decimal("0.82"),
    maximum_cell_total_r=Decimal("0"),
    winner_cost_multiplier=Decimal("2.5"),
    maximum_rules=4,
)


@dataclass(frozen=True, slots=True)
class RescuePolicy:
    minimum_support: int
    minimum_half_support: int
    minimum_profit_factor: Decimal
    minimum_total_r: Decimal
    loss_cost_multiplier: Decimal
    maximum_rules: int

    def payload(self) -> dict[str, object]:
        return {
            "minimum_support": self.minimum_support,
            "minimum_half_support": self.minimum_half_support,
            "minimum_profit_factor": format(self.minimum_profit_factor, "f"),
            "minimum_total_r": format(self.minimum_total_r, "f"),
            "loss_cost_multiplier": format(self.loss_cost_multiplier, "f"),
            "maximum_rules": self.maximum_rules,
        }


POLICIES = tuple(
    RescuePolicy(
        minimum_support=support,
        minimum_half_support=half_support,
        minimum_profit_factor=pf,
        minimum_total_r=total_r,
        loss_cost_multiplier=loss_cost,
        maximum_rules=max_rules,
    )
    for support in (6, 8, 12)
    for half_support in (2, 3)
    for pf in (Decimal("1.20"), Decimal("1.50"), Decimal("2.00"))
    for total_r in (Decimal("1"), Decimal("3"))
    for loss_cost in (Decimal("1.0"), Decimal("1.5"), Decimal("2.0"))
    for max_rules in (4, 6, 10)
)


@dataclass(frozen=True, slots=True)
class PositiveRule:
    fields: tuple[str, ...]
    values: tuple[str, ...]
    support: int
    wins: int
    losses: int
    profit_factor: Decimal
    total_r: Decimal
    winner_r: Decimal
    loss_r: Decimal
    utility: Decimal

    def payload(self) -> dict[str, object]:
        return {
            "fields": self.fields,
            "values": self.values,
            "support": self.support,
            "wins": self.wins,
            "losses": self.losses,
            "profit_factor": format(self.profit_factor, "f"),
            "total_r": format(self.total_r, "f"),
            "winner_r": format(self.winner_r, "f"),
            "loss_r": format(self.loss_r, "f"),
            "utility": format(self.utility, "f"),
        }


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _positive_stats(
    members: list[dict[str, object]],
    *,
    loss_cost_multiplier: Decimal,
) -> dict[str, object]:
    values = [_d(row["net_r_after_friction"]) for row in members]
    winner_r = sum((value for value in values if value > 0), Decimal(0))
    loss_r = -sum((value for value in values if value < 0), Decimal(0))
    wins = sum(value > 0 for value in values)
    losses = sum(value < 0 for value in values)
    pf = (
        Decimal("999")
        if loss_r == 0 and winner_r > 0
        else Decimal(0)
        if loss_r == 0
        else winner_r / loss_r
    )
    total_r = winner_r - loss_r
    return {
        "support": len(values),
        "wins": wins,
        "losses": losses,
        "profit_factor": pf,
        "total_r": total_r,
        "winner_r": winner_r,
        "loss_r": loss_r,
        "utility": winner_r - loss_cost_multiplier * loss_r,
    }


def _matches(rule: PositiveRule, row: dict[str, object]) -> bool:
    return all(
        str(row.get(field, "UNAVAILABLE")) == value
        for field, value in zip(rule.fields, rule.values, strict=True)
    )


def _candidate_positive_rules(
    rows: list[dict[str, object]],
    policy: RescuePolicy,
) -> list[PositiveRule]:
    ordered = sorted(rows, key=lambda row: cast(str, row["signal_at"]))
    cut = max(1, len(ordered) // 2)
    early_ids = {
        cast(str, row["signal_at"]) for row in ordered[:cut]
    }
    late_ids = {
        cast(str, row["signal_at"]) for row in ordered[cut:]
    }
    rules: list[PositiveRule] = []

    for fields in relation_v4._stable_field_sets():
        groups: dict[tuple[str, ...], list[dict[str, object]]] = {}
        for row in rows:
            values = tuple(
                str(row.get(field, "UNAVAILABLE"))
                for field in fields
            )
            groups.setdefault(values, []).append(row)

        for values, members in groups.items():
            overall = _positive_stats(
                members,
                loss_cost_multiplier=policy.loss_cost_multiplier,
            )
            if int(overall["support"]) < policy.minimum_support:
                continue
            if (
                cast(Decimal, overall["profit_factor"])
                < policy.minimum_profit_factor
            ):
                continue
            if (
                cast(Decimal, overall["total_r"])
                < policy.minimum_total_r
            ):
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
            early_stats = _positive_stats(
                early,
                loss_cost_multiplier=policy.loss_cost_multiplier,
            )
            late_stats = _positive_stats(
                late,
                loss_cost_multiplier=policy.loss_cost_multiplier,
            )
            if (
                cast(Decimal, early_stats["profit_factor"])
                < Decimal("1")
                or cast(Decimal, late_stats["profit_factor"])
                < Decimal("1")
            ):
                continue
            if (
                cast(Decimal, early_stats["total_r"]) <= 0
                or cast(Decimal, late_stats["total_r"]) <= 0
            ):
                continue

            rules.append(
                PositiveRule(
                    fields=fields,
                    values=values,
                    support=int(overall["support"]),
                    wins=int(overall["wins"]),
                    losses=int(overall["losses"]),
                    profit_factor=cast(Decimal, overall["profit_factor"]),
                    total_r=cast(Decimal, overall["total_r"]),
                    winner_r=cast(Decimal, overall["winner_r"]),
                    loss_r=cast(Decimal, overall["loss_r"]),
                    utility=cast(Decimal, overall["utility"]),
                )
            )

    rules.sort(
        key=lambda rule: (
            rule.utility,
            rule.winner_r,
            rule.profit_factor,
            -rule.loss_r,
            rule.support,
            rule.fields,
            rule.values,
        ),
        reverse=True,
    )
    return rules


def _negative_match(
    negative_rules: list[bank_v3.Rule],
    row: dict[str, object],
) -> bank_v3.Rule | None:
    return next(
        (
            rule
            for rule in negative_rules
            if bank_v3._rule_matches(rule, row)
        ),
        None,
    )


def _select_positive_bank(
    rows: list[dict[str, object]],
    negative_rules: list[bank_v3.Rule],
    candidates: list[PositiveRule],
    policy: RescuePolicy,
) -> list[PositiveRule]:
    negative_rows = [
        row for row in rows
        if _negative_match(negative_rules, row) is not None
    ]
    selected: list[PositiveRule] = []
    already_rescued: set[str] = set()

    for rule in candidates:
        if len(selected) >= policy.maximum_rules:
            break
        matched = [
            row
            for row in negative_rows
            if _matches(rule, row)
            and cast(str, row["signal_at"]) not in already_rescued
        ]
        if not matched:
            continue
        stats = _positive_stats(
            matched,
            loss_cost_multiplier=policy.loss_cost_multiplier,
        )
        if cast(Decimal, stats["utility"]) <= 0:
            continue
        selected.append(rule)
        already_rescued.update(
            cast(str, row["signal_at"]) for row in matched
        )
    return selected


def _evaluate(
    rows: list[dict[str, object]],
    negative_rules: list[bank_v3.Rule],
    rescue_rules: list[PositiveRule],
) -> dict[str, object]:
    ordered = sorted(rows, key=lambda row: cast(str, row["signal_at"]))
    baseline_values: list[Decimal] = []
    kept_values: list[Decimal] = []
    abstained: list[dict[str, object]] = []
    rescued: list[dict[str, object]] = []
    negative_hits: dict[str, int] = {}
    rescue_hits: dict[str, int] = {}

    for row in ordered:
        value = _d(row["net_r_after_friction"])
        baseline_values.append(value)
        negative = _negative_match(negative_rules, row)
        if negative is None:
            kept_values.append(value)
            continue

        rescue = next(
            (rule for rule in rescue_rules if _matches(rule, row)),
            None,
        )
        if rescue is not None:
            kept_values.append(value)
            rescued.append(row)
            key = "&".join(
                f"{field}={val}"
                for field, val in zip(
                    rescue.fields, rescue.values, strict=True
                )
            )
            rescue_hits[key] = rescue_hits.get(key, 0) + 1
            continue

        abstained.append(row)
        key = "&".join(
            f"{field}={val}"
            for field, val in zip(
                negative.fields, negative.values, strict=True
            )
        )
        negative_hits[key] = negative_hits.get(key, 0) + 1

    baseline = perception._metrics(baseline_values)
    shared = perception._metrics(kept_values)
    base_losses = int(baseline["losses"])
    base_wins = int(baseline["wins"])
    losses_avoided = sum(
        _d(row["net_r_after_friction"]) < 0 for row in abstained
    )
    winners_sacrificed = sum(
        _d(row["net_r_after_friction"]) > 0 for row in abstained
    )
    gross_winner_r = sum(
        (value for value in baseline_values if value > 0),
        Decimal(0),
    )
    sacrificed_winner_r = sum(
        (
            _d(row["net_r_after_friction"])
            for row in abstained
            if _d(row["net_r_after_friction"]) > 0
        ),
        Decimal(0),
    )
    rescued_winners = sum(
        _d(row["net_r_after_friction"]) > 0 for row in rescued
    )
    rescued_losses = sum(
        _d(row["net_r_after_friction"]) < 0 for row in rescued
    )

    return {
        "baseline": baseline,
        "shared_negative_plus_override": shared,
        "selection": {
            "input": len(rows),
            "kept": len(kept_values),
            "abstained": len(abstained),
            "losses_avoided": losses_avoided,
            "winners_sacrificed": winners_sacrificed,
            "loss_rejection_recall": (
                "0"
                if base_losses == 0
                else format(
                    Decimal(losses_avoided) / Decimal(base_losses), "f"
                )
            ),
            "winner_count_retention": (
                "0"
                if base_wins == 0
                else format(
                    Decimal(base_wins - winners_sacrificed)
                    / Decimal(base_wins),
                    "f",
                )
            ),
            "winner_r_retention": (
                "1"
                if gross_winner_r == 0
                else format(
                    (gross_winner_r - sacrificed_winner_r)
                    / gross_winner_r,
                    "f",
                )
            ),
            "density_retained": (
                "0"
                if not rows
                else format(
                    Decimal(len(kept_values)) / Decimal(len(rows)), "f"
                )
            ),
            "rescued": len(rescued),
            "rescued_winners": rescued_winners,
            "rescued_losses": rescued_losses,
        },
        "negative_hits": dict(sorted(negative_hits.items())),
        "rescue_hits": dict(sorted(rescue_hits.items())),
    }


def _gates(result: dict[str, object]) -> dict[str, bool]:
    baseline = cast(dict[str, object], result["baseline"])
    shared = cast(
        dict[str, object],
        result["shared_negative_plus_override"],
    )
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
        "total_r_not_lower": (
            _d(shared["total_r"]) >= _d(baseline["total_r"])
        ),
        "loss_recall_at_least_25pct": (
            _d(selection["loss_rejection_recall"])
            >= Decimal("0.25")
        ),
        "winner_count_retention_at_least_80pct": (
            _d(selection["winner_count_retention"])
            >= Decimal("0.80")
        ),
        "winner_r_retention_at_least_90pct": (
            _d(selection["winner_r_retention"])
            >= Decimal("0.90")
        ),
        "density_at_least_55pct": (
            _d(selection["density_retained"]) >= Decimal("0.55")
        ),
    }


def _score(result: dict[str, object]) -> Decimal | None:
    gates = _gates(result)
    if not all(gates.values()):
        return None
    baseline = cast(dict[str, object], result["baseline"])
    shared = cast(
        dict[str, object],
        result["shared_negative_plus_override"],
    )
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
        relation_v4._decorate(row)
        for row in perception._perception_rows(
            r8_raw,
            core_v3._decorate(core_v3._load_trades(r8_trades), daily),
        )
    ]
    r6 = [
        relation_v4._decorate(row)
        for row in perception._perception_rows(
            r6_raw,
            core_v3._decorate(core_v3._load_trades(r6_trades), daily),
        )
    ]
    r5 = [
        relation_v4._decorate(row)
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

    negative_candidates = relation_v4._candidate_rules(
        r8, NEGATIVE_POLICY
    )
    negative_rules = relation_v4._select_bank(
        r8, negative_candidates, NEGATIVE_POLICY
    )
    if not negative_rules:
        raise AssertionError("frozen V4 negative bank missing")

    frontier: list[dict[str, object]] = []
    best: tuple[
        Decimal,
        RescuePolicy,
        list[PositiveRule],
    ] | None = None

    for policy in POLICIES:
        candidates = _candidate_positive_rules(r8, policy)
        rescue_rules = _select_positive_bank(
            r8, negative_rules, candidates, policy
        )
        if not rescue_rules:
            continue

        r8_result = _evaluate(r8, negative_rules, rescue_rules)
        r8_gates = _gates(r8_result)
        if not all(r8_gates.values()):
            frontier.append({
                "policy": policy.payload(),
                "rescue_rule_count": len(rescue_rules),
                "rescue_rules": [rule.payload() for rule in rescue_rules],
                "r8": r8_result,
                "r8_gates": r8_gates,
                "r6": None,
                "r6_gates": None,
                "score": None,
            })
            continue

        r6_result = _evaluate(r6, negative_rules, rescue_rules)
        r6_gates = _gates(r6_result)
        score = _score(r6_result)
        frontier.append({
            "policy": policy.payload(),
            "rescue_rule_count": len(rescue_rules),
            "rescue_rules": [rule.payload() for rule in rescue_rules],
            "r8": r8_result,
            "r8_gates": r8_gates,
            "r6": r6_result,
            "r6_gates": r6_gates,
            "score": None if score is None else format(score, "f"),
        })
        if score is not None and (best is None or score > best[0]):
            best = (score, policy, rescue_rules)

    if best is None:
        return {
            "schema": SCHEMA,
            "identity": IDENTITY,
            "economic_status": "FALSIFIED_BEFORE_R5",
            "challenge_set": {"trades": 822, "losses": 711, "wins": 111},
            "negative_policy": NEGATIVE_POLICY.payload(),
            "negative_rules": [rule.payload() for rule in negative_rules],
            "frozen_rescue_policy": None,
            "frozen_rescue_rules": None,
            "evaluation": None,
            "gates": None,
            "passes_positive_override": False,
            "frontier": frontier,
            "governance": _governance(),
        }

    _, frozen_policy, frozen_rescue_rules = best
    evaluation = _evaluate(
        r5, negative_rules, frozen_rescue_rules
    )
    gates = _gates(evaluation)
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
            "r8": "STABLE_NEGATIVE_BANK_PLUS_STABLE_POSITIVE_OVERRIDES",
            "r6": "OVERRIDE_CALIBRATION_AND_FREEZE",
            "r5": "NO_RETUNE_EVALUATION",
        },
        "negative_policy": NEGATIVE_POLICY.payload(),
        "negative_rules": [rule.payload() for rule in negative_rules],
        "frozen_rescue_policy": frozen_policy.payload(),
        "frozen_rescue_rules": [
            rule.payload() for rule in frozen_rescue_rules
        ],
        "evaluation": evaluation,
        "gates": gates,
        "passes_positive_override": passed,
        "frontier": frontier,
        "governance": _governance(),
    }


def _governance() -> dict[str, bool]:
    return {
        "negative_bank_weakened": False,
        "runtime_positive_override_present_market_only": True,
        "runtime_analog_lookup_used": False,
        "runtime_outcome_label_used": False,
        "r8_internal_temporal_stability_required": True,
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
        "passes_positive_override": payload["passes_positive_override"],
        "frozen_rescue_policy": payload["frozen_rescue_policy"],
        "evaluation": payload["evaluation"],
        "gates": payload["gates"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
