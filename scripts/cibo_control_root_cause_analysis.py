#!/usr/bin/env python3
"""Post-replay root-cause analysis for CIBO ceiling research.

This script is deliberately post-decision and non-certifying. It uses burned
research outcomes only to locate failure mechanisms. It cannot tune or mutate
the sovereign runtime and cannot promote any rule into production.

It separates:
- cognitive reach/invariance;
- first upstream selection cause;
- expected-value calibration;
- expected-vs-realized capital duration;
- realized loss concentration.

CORRELATION != CAUSATION. Component economics still require isolated ablation.
"""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter, defaultdict
from datetime import datetime
from decimal import Decimal, localcontext
from pathlib import Path
from typing import Any

_TURTLE = {
    "R34_XAUUSD",
    "R38_EURUSD",
    "R38_GBPJPY",
    "R42_AUDJPY",
    "R43_GBPUSD",
}


def _d(value: object) -> Decimal:
    result = Decimal(str(value))
    if not result.is_finite():
        raise ValueError("non-finite decimal")
    return result


def _provider_cost_per_volume(row: dict[str, Any]) -> Decimal:
    observed = row["market_predecision_state"]["provider_observation"]
    ask = _d(observed["ask"])
    bid = _d(observed["bid"])
    tick_size = _d(observed["tick_size"])
    tick_value = _d(observed["tick_value"])
    commission = _d(observed.get("commission_per_volume_usd", "0"))
    slippage = _d(
        observed.get("slippage_reserve_per_volume_usd", "0")
    )
    if tick_size <= 0 or tick_value <= 0 or ask < bid:
        raise ValueError("invalid provider economics")
    return (
        ((ask - bid) / tick_size) * tick_value
        + commission
        + slippage
    )


def _predecision_net_utility(row: dict[str, Any]) -> Decimal:
    expectation = row["expectation"]
    opportunity = row["trader_opportunity"]
    provider_cost = (
        _provider_cost_per_volume(row)
        * _d(opportunity["minimum_volume"])
    )
    return (
        _d(expectation["expected_net_value_usd"])
        - provider_cost
        - _d(expectation.get("uncertainty_penalty_usd", "0"))
    )


def _gross_structural_r(row: dict[str, Any]) -> Decimal:
    value = _d(
        row["settlement_outcome_research_only"][
            "gross_structural_outcome_r"
        ]
    )
    # The five Turtle traces freeze net-010 source semantics. The sovereign
    # settlement boundary repairs that source representation by +0.10R before
    # provider economics. Mirror only that already-validated semantic repair.
    if row["trader_id"] in _TURTLE:
        return value + Decimal("0.10")
    return value


def _duration_minutes(row: dict[str, Any]) -> Decimal:
    outcome = row["settlement_outcome_research_only"]
    entry = datetime.fromisoformat(outcome["entry_at"])
    exit_at = datetime.fromisoformat(outcome["exit_at"])
    return Decimal(str((exit_at - entry).total_seconds())) / Decimal(60)


def _stats(values: list[Decimal]) -> dict[str, object]:
    if not values:
        return {
            "count": 0,
            "positive_count": 0,
            "negative_count": 0,
            "flat_count": 0,
            "net_r": "0",
            "gross_positive_r": "0",
            "gross_negative_r": "0",
            "profit_factor": None,
            "average_r": None,
        }
    positive = [v for v in values if v > 0]
    negative = [v for v in values if v < 0]
    gross_positive = sum(positive, Decimal(0))
    gross_negative = -sum(negative, Decimal(0))
    total = sum(values, Decimal(0))
    with localcontext() as context:
        context.prec = 100
        profit_factor = (
            None
            if gross_negative == 0
            else gross_positive / gross_negative
        )
        average = total / Decimal(len(values))
    return {
        "count": len(values),
        "positive_count": len(positive),
        "negative_count": len(negative),
        "flat_count": len(values) - len(positive) - len(negative),
        "net_r": format(total, "f"),
        "gross_positive_r": format(gross_positive, "f"),
        "gross_negative_r": format(gross_negative, "f"),
        "profit_factor": (
            None if profit_factor is None else format(profit_factor, "f")
        ),
        "average_r": format(average, "f"),
    }


def _pearson(left: list[float], right: list[float]) -> float | None:
    if len(left) != len(right) or len(left) < 2:
        return None
    mean_left = sum(left) / len(left)
    mean_right = sum(right) / len(right)
    num = sum(
        (x - mean_left) * (y - mean_right)
        for x, y in zip(left, right, strict=True)
    )
    den_left = math.sqrt(sum((x - mean_left) ** 2 for x in left))
    den_right = math.sqrt(sum((y - mean_right) ** 2 for y in right))
    if den_left == 0 or den_right == 0:
        return None
    return num / (den_left * den_right)


def _ranks(values: list[float]) -> list[float]:
    ordered = sorted(enumerate(values), key=lambda item: item[1])
    ranks = [0.0] * len(values)
    index = 0
    while index < len(ordered):
        end = index + 1
        while end < len(ordered) and ordered[end][1] == ordered[index][1]:
            end += 1
        average_rank = ((index + 1) + end) / 2
        for pos in range(index, end):
            ranks[ordered[pos][0]] = average_rank
        index = end
    return ranks


def _spearman(left: list[float], right: list[float]) -> float | None:
    return _pearson(_ranks(left), _ranks(right))


def analyze(
    *,
    replay: dict[str, Any],
    manifest: dict[str, Any],
) -> dict[str, Any]:
    decisions = {
        item["signal_fingerprint"]: item
        for item in replay["decision_receipts"]
    }
    rows = manifest["opportunities"]
    if len(decisions) != 3368 or len(rows) != 3368:
        raise ValueError("root-cause analysis requires frozen 3368 population")

    upstream: Counter[str] = Counter()
    upstream_r: dict[str, list[Decimal]] = defaultdict(list)
    upstream_by_trader: dict[
        str, dict[str, list[Decimal]]
    ] = defaultdict(lambda: defaultdict(list))
    context_rule_combinations: dict[
        tuple[str, ...], list[Decimal]
    ] = defaultdict(list)

    expected_value: list[float] = []
    realized_r: list[float] = []
    expected_velocity: list[float] = []
    realized_velocity: list[float] = []

    duration_all: list[tuple[str, bool, Decimal, Decimal]] = []

    for row in rows:
        signal = row["signal_fingerprint"]
        decision = decisions[signal]
        selected = decision["risk_decision"] == "ALLOW"
        context_allowed = row["context_quality"]["disposition"] == "ALLOW"
        net_utility = _predecision_net_utility(row)
        realized = _gross_structural_r(row)

        if selected:
            cause = "EXECUTED_POSITIVE_ELIGIBLE"
        elif not context_allowed:
            cause = "CONTEXT_QUALITY_ABSTAIN"
        elif net_utility <= 0:
            cause = "NONPOSITIVE_EXPECTED_NET_UTILITY"
        else:
            cause = "UNEXPLAINED_DOWNSTREAM_BLOCK"

        upstream[cause] += 1
        upstream_r[cause].append(realized)
        upstream_by_trader[cause][row["trader_id"]].append(realized)

        if not context_allowed:
            rules = tuple(
                sorted(row["context_quality"].get("matched_rule_ids", []))
            )
            context_rule_combinations[rules].append(realized)

        expectation = _d(row["expectation"]["expected_net_value_usd"])
        expected_minutes = _d(row["expectation"]["expected_capital_minutes"])
        actual_minutes = _duration_minutes(row)
        expected_value.append(float(expectation))
        realized_r.append(float(realized))
        expected_velocity.append(float(expectation / expected_minutes))
        realized_velocity.append(
            float(realized / actual_minutes)
            if actual_minutes > 0
            else 0.0
        )
        duration_all.append(
            (row["trader_id"], selected, expected_minutes, actual_minutes)
        )

    if upstream["UNEXPLAINED_DOWNSTREAM_BLOCK"]:
        raise ValueError("unexpected downstream block escaped first-cause model")

    cognitive = replay["cognitive_reach_sensors"]["components"]
    cognitive_invariant = all(
        item["constraint_or_gate_count"] == 0
        and item["reached_capital_decision_count"] == 3368
        for item in cognitive.values()
    )

    duration_groups: dict[str, list[tuple[Decimal, Decimal]]] = defaultdict(list)
    duration_selected: dict[
        str, list[tuple[Decimal, Decimal]]
    ] = defaultdict(list)
    for trader, selected, expected, actual in duration_all:
        duration_groups[trader].append((expected, actual))
        if selected:
            duration_selected[trader].append((expected, actual))

    def duration_summary(
        data: dict[str, list[tuple[Decimal, Decimal]]]
    ) -> dict[str, object]:
        result: dict[str, object] = {}
        for trader, pairs in sorted(data.items()):
            with localcontext() as context:
                context.prec = 100
                expected_avg = (
                    sum((x for x, _ in pairs), Decimal(0))
                    / Decimal(len(pairs))
                )
                actual_avg = (
                    sum((y for _, y in pairs), Decimal(0))
                    / Decimal(len(pairs))
                )
                ratio = (
                    None
                    if expected_avg == 0
                    else actual_avg / expected_avg
                )
            result[trader] = {
                "count": len(pairs),
                "expected_minutes_average": format(expected_avg, "f"),
                "actual_minutes_average": format(actual_avg, "f"),
                "actual_to_expected_ratio": (
                    None if ratio is None else format(ratio, "f")
                ),
            }
        return result

    return {
        "schema": "qore.cibo.control-root-cause-analysis.v1",
        "research_only": True,
        "certification_claimed": False,
        "outcome_aware_tuning_authorized": False,
        "population": {
            "decision_count": len(rows),
            "settlement_count": replay["settlement_count"],
            "ending_capital_usd": replay["ending_capital_usd"],
            "net_pnl_usd": replay["net_pnl_usd"],
        },
        "cognition": {
            "component_count": len(cognitive),
            "sensor_event_count": replay[
                "cognitive_reach_sensors"
            ]["sensor_count"],
            "all_components_reached_capital_every_decision": (
                cognitive_invariant
            ),
            "total_observed_cognitive_gate_count": sum(
                int(item["constraint_or_gate_count"])
                for item in cognitive.values()
            ),
            "observed_control_discrimination": (
                "NONE_IN_FROZEN_POPULATION"
                if cognitive_invariant
                else "PRESENT"
            ),
            "individual_economic_contribution": (
                "UNPROVEN_PENDING_ISOLATED_ABLATIONS"
            ),
        },
        "first_upstream_decision_cause": {
            cause: {
                "decision_count": upstream[cause],
                "post_outcome_diagnostic": _stats(upstream_r[cause]),
                "by_trader": {
                    trader: _stats(values)
                    for trader, values in sorted(
                        upstream_by_trader[cause].items()
                    )
                },
            }
            for cause in sorted(upstream)
        },
        "context_rule_combinations_post_outcome_diagnostic": {
            "+".join(combo) if combo else "NO_RULE": _stats(values)
            for combo, values in sorted(
                context_rule_combinations.items(),
                key=lambda item: (-len(item[1]), item[0]),
            )
        },
        "expectation_calibration": {
            "expected_value_vs_realized_r_pearson": _pearson(
                expected_value, realized_r
            ),
            "expected_value_vs_realized_r_spearman": _spearman(
                expected_value, realized_r
            ),
            "expected_velocity_vs_realized_r_per_minute_pearson": _pearson(
                expected_velocity, realized_velocity
            ),
            "expected_velocity_vs_realized_r_per_minute_spearman": _spearman(
                expected_velocity, realized_velocity
            ),
        },
        "duration_calibration_all": duration_summary(duration_groups),
        "duration_calibration_selected": duration_summary(duration_selected),
        "interpretation_contract": {
            "burned_outcomes_are_diagnostic_only": True,
            "correlation_is_not_causation": True,
            "same_population_outcomes_must_not_be_used_as_tuning_labels": True,
            "individual_module_contribution_requires_isolated_ablation": True,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--replay", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    replay = json.loads(args.replay.read_text(encoding="utf-8"))
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    result = analyze(replay=replay, manifest=manifest)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "observed_control_discrimination": result["cognition"][
                    "observed_control_discrimination"
                ],
                "cognitive_gate_count": result["cognition"][
                    "total_observed_cognitive_gate_count"
                ],
                "first_upstream_decision_cause": {
                    key: value["decision_count"]
                    for key, value in result[
                        "first_upstream_decision_cause"
                    ].items()
                },
                "expectation_calibration": result[
                    "expectation_calibration"
                ],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
