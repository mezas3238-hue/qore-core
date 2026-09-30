#!/usr/bin/env python3
"""STI-8 sovereign control/treatment economic value research.

Control and treatment use the same VT31 source methodology, opportunity
universe, entry, initial stop, initial target and sizing. The only information
difference is frozen proactive STI-8 threat cognition consumed by a Trader-owned
research policy. Shared itself has no exit, stop, target, Risk, sizing, capital
or execution authority.

The Trader research consumer schedules EXIT only at the next M1 open after a
closed-M1 material STI-8 threat. Terminal outcomes are touched only after all
source-time decisions have been materialized.
"""

from __future__ import annotations

import argparse
import json
import math
import random
from decimal import Decimal
from pathlib import Path
from statistics import median
from typing import Any, cast

import shared_sti6_sti8_real_position_intelligence as base

from qore.infrastructure.core_stack_v2.shared_position_threat_intelligence import (
    assess_position_threat,
)
from qore.infrastructure.traders.vt31_shared_threat_consumer_research import (
    FROZEN_STI8_ECONOMIC_POLICY_V1,
    Vt31ThreatConsumerAction,
    decide_vt31_threat_response,
)

IDENTITY = "QORE_SHARED_STI8_ECONOMIC_VALUE_V1"
FRICTION = Decimal("0.05")
POSITIVE_TAIL_R = Decimal("2.0")
WINNER_COUNT_RETENTION_MIN = Decimal("0.98")
WINNER_R_RETENTION_MIN = Decimal("0.90")
TOP_DECILE_WINNER_R_RETENTION_MIN = Decimal("0.90")
TOP_5PCT_WINNER_R_RETENTION_MIN = Decimal("0.90")
POSITIVE_TAIL_R_RETENTION_MIN = Decimal("0.90")
MONTE_CARLO_PATHS = 5000
MONTE_CARLO_SEED = 20260930


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _pf(values: list[Decimal]) -> Decimal | None:
    gains = sum((value for value in values if value > 0), Decimal(0))
    losses = -sum((value for value in values if value < 0), Decimal(0))
    return None if losses == 0 else gains / losses


def _max_dd(values: list[Decimal]) -> Decimal:
    equity = Decimal(0)
    peak = Decimal(0)
    drawdown = Decimal(0)
    for value in values:
        equity += value
        peak = max(peak, equity)
        drawdown = max(drawdown, peak - equity)
    return drawdown


def _max_loss_cluster(values: list[Decimal]) -> int:
    current = 0
    largest = 0
    for value in values:
        if value < 0:
            current += 1
            largest = max(largest, current)
        else:
            current = 0
    return largest


def _expected_shortfall(values: list[Decimal], fraction: Decimal) -> Decimal:
    if not values:
        return Decimal(0)
    ordered = sorted(values)
    count = max(
        1,
        math.ceil(len(ordered) * float(fraction)),
    )
    return sum(ordered[:count], Decimal(0)) / Decimal(count)


def _metrics(values: list[Decimal]) -> dict[str, object]:
    pf = _pf(values)
    return {
        "trade_count": len(values),
        "total_r": str(sum(values, Decimal(0))),
        "profit_factor": None if pf is None else str(pf),
        "max_dd_r": str(_max_dd(values)),
        "tail_loss_r": str(min(values) if values else Decimal(0)),
        "expected_shortfall_5pct_r": str(
            _expected_shortfall(values, Decimal("0.05"))
        ),
        "wins": sum(value > 0 for value in values),
        "losses": sum(value < 0 for value in values),
        "flats": sum(value == 0 for value in values),
        "max_loss_cluster": _max_loss_cluster(values),
        "gross_winner_r": str(
            sum((value for value in values if value > 0), Decimal(0))
        ),
        "gross_loss_r": str(
            -sum((value for value in values if value < 0), Decimal(0))
        ),
    }


def _percentile(values: list[Decimal], quantile: Decimal) -> Decimal:
    if not values:
        return Decimal(0)
    ordered = sorted(values)
    index = max(
        0,
        min(
            len(ordered) - 1,
            math.ceil((len(ordered) - 1) * float(quantile)),
        ),
    )
    return ordered[index]


def _paired_bootstrap_dd(
    control: list[Decimal],
    treatment: list[Decimal],
) -> dict[str, str]:
    if len(control) != len(treatment) or not control:
        raise ValueError("paired bootstrap requires equal non-empty arms")

    rng = random.Random(MONTE_CARLO_SEED)
    control_dd: list[Decimal] = []
    treatment_dd: list[Decimal] = []
    for _ in range(MONTE_CARLO_PATHS):
        indexes = [rng.randrange(len(control)) for _ in control]
        control_dd.append(_max_dd([control[index] for index in indexes]))
        treatment_dd.append(_max_dd([treatment[index] for index in indexes]))

    return {
        "control_p95_dd_r": str(_percentile(control_dd, Decimal("0.95"))),
        "control_p99_dd_r": str(_percentile(control_dd, Decimal("0.99"))),
        "treatment_p95_dd_r": str(
            _percentile(treatment_dd, Decimal("0.95"))
        ),
        "treatment_p99_dd_r": str(
            _percentile(treatment_dd, Decimal("0.99"))
        ),
        "paths": str(MONTE_CARLO_PATHS),
        "seed": str(MONTE_CARLO_SEED),
    }


def _retention_ratio(
    *,
    control: list[Decimal],
    treatment: list[Decimal],
    indexes: list[int],
) -> Decimal:
    baseline = sum((control[index] for index in indexes), Decimal(0))
    if baseline == 0:
        return Decimal(1)
    managed = sum((treatment[index] for index in indexes), Decimal(0))
    return managed / baseline


def _winner_retention(
    control: list[Decimal],
    treatment: list[Decimal],
) -> dict[str, str]:
    winners = [index for index, value in enumerate(control) if value > 0]
    if not winners:
        return {
            "winner_count_retention": "1",
            "winner_r_retention": "1",
            "top_decile_winner_r_retention": "1",
            "top_5pct_winner_r_retention": "1",
            "positive_tail_r_retention": "1",
        }

    retained = sum(treatment[index] > 0 for index in winners)
    winner_count_retention = Decimal(retained) / Decimal(len(winners))
    winner_r_retention = _retention_ratio(
        control=control,
        treatment=treatment,
        indexes=winners,
    )

    ranked = sorted(winners, key=lambda index: control[index], reverse=True)
    top_decile_count = max(1, math.ceil(len(ranked) * 0.10))
    top_5pct_count = max(1, math.ceil(len(ranked) * 0.05))
    top_decile = ranked[:top_decile_count]
    top_5pct = ranked[:top_5pct_count]
    tails = [index for index in winners if control[index] >= POSITIVE_TAIL_R]

    return {
        "winner_count_retention": str(winner_count_retention),
        "winner_r_retention": str(winner_r_retention),
        "top_decile_winner_r_retention": str(
            _retention_ratio(
                control=control,
                treatment=treatment,
                indexes=top_decile,
            )
        ),
        "top_5pct_winner_r_retention": str(
            _retention_ratio(
                control=control,
                treatment=treatment,
                indexes=top_5pct,
            )
        ),
        "positive_tail_r_retention": str(
            _retention_ratio(
                control=control,
                treatment=treatment,
                indexes=tails,
            )
            if tails
            else Decimal(1)
        ),
    }


def _next_open_exit_r(
    *,
    row: dict[str, object],
    setup: object,
    day_bars: tuple[object, ...],
    threat_observation_index: int,
) -> Decimal | None:
    fill_index, _ = base.counter._fill_and_exit_indices(setup, day_bars, row)
    snapshot_index = fill_index + 1 + threat_observation_index
    next_index = snapshot_index + 1
    if next_index >= len(day_bars):
        return None

    next_bar = day_bars[next_index]
    if base.counter.v1._local_minute(next_bar) >= base.counter.v1.LIFECYCLE_MINUTE:
        return None

    side = cast(object, setup).side.value
    sign = base.counter.v1._side_sign(side)
    entry = cast(object, setup).entry_price
    risk = cast(object, setup).initial_risk
    opened = base.counter.v1._bar_values(next_bar)[0]
    return sign * (opened - entry) / risk - FRICTION


def _pf_gt(left: object, right: object) -> bool:
    left_value = None if left is None else _d(left)
    right_value = None if right is None else _d(right)
    if left_value is None:
        return False
    if right_value is None:
        return True
    return right_value > left_value


def run(
    *,
    partition: str,
    frozen_policy_path: Path,
    trades_path: Path,
    nas_path: Path,
    sp_path: Path,
    us_path: Path,
) -> dict[str, object]:
    frozen = json.loads(frozen_policy_path.read_text())
    if frozen.get("identity") != base.IDENTITY:
        raise ValueError("unexpected frozen STI-8 policy identity")
    if frozen.get("mode") != "SOURCE_ONLY_POLICY_FREEZE":
        raise ValueError("economic study requires source-only frozen STI-8 policy")
    if frozen.get("future_trade_outcomes_read_for_freeze") is not False:
        raise ValueError("frozen STI-8 policy is outcome contaminated")

    sti8_policy = base._sti8_policy(frozen)
    sequences = base._source_sequences(
        partition=partition,
        trades_path=trades_path,
        nas_path=nas_path,
        sp_path=sp_path,
        us_path=us_path,
    )
    paths = base._reconstruct_source_partition(nas_path)
    if not sequences:
        raise ValueError("economic study has no methodology-valid trades")

    materialized: list[dict[str, Any]] = []
    source_observation_count = 0

    for sequence in sequences:
        row = cast(dict[str, object], sequence["row"])
        observations = cast(tuple[Any, ...], sequence["observations"])
        source_observation_count += len(observations)
        first_exit_index: int | None = None
        first_level: str | None = None

        for index, observation in enumerate(observations):
            assessment = assess_position_threat(
                observation,
                policy=sti8_policy,
            )
            decision = decide_vt31_threat_response(
                decision_time=observation.as_of,
                shared_assessment=assessment,
                shared_intelligence_ref=(
                    f"sti8:{partition}:{observation.observation_id}"
                ),
            )
            if (
                first_exit_index is None
                and decision.action
                is Vt31ThreatConsumerAction.EXIT_NEXT_M1_OPEN
            ):
                first_exit_index = index
                first_level = assessment.threat_level.value

        # No terminal outcome has been read above this line.
        materialized.append(
            {
                "row": row,
                "observations": observations,
                "first_exit_index": first_exit_index,
                "first_level": first_level,
            }
        )

    control_values: list[Decimal] = []
    treatment_values: list[Decimal] = []
    changed_rows: list[dict[str, object]] = []
    true_threat_leads: list[int] = []

    for item in materialized:
        row = cast(dict[str, object], item["row"])
        observations = cast(tuple[Any, ...], item["observations"])
        signal = str(row["signal_at"])
        baseline_r = _d(row["net_r_after_friction"])
        control_values.append(baseline_r)
        managed_r = baseline_r

        first_exit_index = cast(int | None, item["first_exit_index"])
        if first_exit_index is not None:
            if signal not in paths:
                raise ValueError(f"missing reconstructed path for {signal}")
            setup, day_bars = paths[signal]
            candidate = _next_open_exit_r(
                row=row,
                setup=setup,
                day_bars=day_bars,
                threat_observation_index=first_exit_index,
            )
            if candidate is not None:
                managed_r = candidate
                changed_rows.append(
                    {
                        "signal_at": signal,
                        "baseline_r": str(baseline_r),
                        "treatment_r": str(managed_r),
                        "delta_r": str(managed_r - baseline_r),
                        "first_material_threat_level": item["first_level"],
                        "decision_effective": "NEXT_M1_OPEN",
                    }
                )
                if baseline_r < 0:
                    true_threat_leads.append(
                        len(observations) - 1 - first_exit_index
                    )

        treatment_values.append(managed_r)

    control = _metrics(control_values)
    treatment = _metrics(treatment_values)
    bootstrap = _paired_bootstrap_dd(control_values, treatment_values)
    retention = _winner_retention(control_values, treatment_values)

    loss_r_avoided = sum(
        (
            treatment_values[index] - control_values[index]
            for index in range(len(control_values))
            if control_values[index] < 0
            and treatment_values[index] > control_values[index]
        ),
        Decimal(0),
    )
    false_threat_cost = sum(
        (
            control_values[index] - treatment_values[index]
            for index in range(len(control_values))
            if control_values[index] >= 0
            and treatment_values[index] < control_values[index]
        ),
        Decimal(0),
    )
    premature_exit_regret = sum(
        (
            control_values[index] - treatment_values[index]
            for index in range(len(control_values))
            if control_values[index] > 0
            and treatment_values[index] < control_values[index]
        ),
        Decimal(0),
    )
    net_utility = sum(treatment_values, Decimal(0)) - sum(
        control_values,
        Decimal(0),
    )

    gates = {
        "treatment_total_r_gte_control": (
            _d(treatment["total_r"]) >= _d(control["total_r"])
        ),
        "treatment_profit_factor_gt_control": _pf_gt(
            control["profit_factor"],
            treatment["profit_factor"],
        ),
        "treatment_max_dd_lt_control": (
            _d(treatment["max_dd_r"]) < _d(control["max_dd_r"])
        ),
        "treatment_p95_bootstrap_dd_lte_control": (
            _d(bootstrap["treatment_p95_dd_r"])
            <= _d(bootstrap["control_p95_dd_r"])
        ),
        "treatment_p99_bootstrap_dd_lte_control": (
            _d(bootstrap["treatment_p99_dd_r"])
            <= _d(bootstrap["control_p99_dd_r"])
        ),
        "loss_r_avoided_gt_zero": loss_r_avoided > 0,
        "net_economic_utility_r_gt_zero": net_utility > 0,
        "winner_count_retention_min": (
            _d(retention["winner_count_retention"])
            >= WINNER_COUNT_RETENTION_MIN
        ),
        "winner_r_retention_min": (
            _d(retention["winner_r_retention"]) >= WINNER_R_RETENTION_MIN
        ),
        "top_decile_winner_r_retention_min": (
            _d(retention["top_decile_winner_r_retention"])
            >= TOP_DECILE_WINNER_R_RETENTION_MIN
        ),
        "top_5pct_winner_r_retention_min": (
            _d(retention["top_5pct_winner_r_retention"])
            >= TOP_5PCT_WINNER_R_RETENTION_MIN
        ),
        "positive_tail_r_retention_min": (
            _d(retention["positive_tail_r_retention"])
            >= POSITIVE_TAIL_R_RETENTION_MIN
        ),
    }
    passed = all(gates.values())

    return {
        "identity": IDENTITY,
        "partition": partition,
        "study_design": {
            "control": "VT31_SOURCE_METHODOLOGY_WITHOUT_PROACTIVE_STI8",
            "treatment": (
                "SAME_VT31_SOURCE_METHODOLOGY_PLUS_TRADER_OWNED_STI8_CONSUMER"
            ),
            "same_opportunity_universe": True,
            "same_trade_count": len(control_values) == len(treatment_values),
            "same_initial_entry_stop_target": True,
            "same_sizing": True,
            "only_information_difference_is_proactive_shared": True,
        },
        "signal_engine": {
            "sti8_policy_fingerprint": frozen["sti8_policy_fingerprint"],
            "consumer_policy_id": FROZEN_STI8_ECONOMIC_POLICY_V1.policy_id,
            "consumer_policy_fingerprint": (
                FROZEN_STI8_ECONOMIC_POLICY_V1.fingerprint()
            ),
        },
        "economic_status": (
            "STI8_V1_ECONOMIC_VALUE_PASS"
            if passed
            else "STI8_V1_ECONOMIC_RESPONSE_FALSIFIED"
        ),
        "economic_value_pass": passed,
        "trade_count": len(control_values),
        "source_observation_count": source_observation_count,
        "treatment_changed_trade_count": len(changed_rows),
        "control": control,
        "treatment": treatment,
        "bootstrap_dd": bootstrap,
        "winner_preservation": retention,
        "economic_effects": {
            "loss_r_avoided": str(loss_r_avoided),
            "false_threat_cost_r": str(false_threat_cost),
            "premature_exit_regret_r": str(premature_exit_regret),
            "net_economic_utility_r": str(net_utility),
            "median_true_threat_lead_minutes": (
                None
                if not true_threat_leads
                else median(true_threat_leads)
            ),
        },
        "gates": gates,
        "frozen_gate_values": {
            "winner_count_retention_min": str(
                WINNER_COUNT_RETENTION_MIN
            ),
            "winner_r_retention_min": str(WINNER_R_RETENTION_MIN),
            "top_decile_winner_r_retention_min": str(
                TOP_DECILE_WINNER_R_RETENTION_MIN
            ),
            "top_5pct_winner_r_retention_min": str(
                TOP_5PCT_WINNER_R_RETENTION_MIN
            ),
            "positive_tail_r_retention_min": str(
                POSITIVE_TAIL_R_RETENTION_MIN
            ),
            "monte_carlo_paths": MONTE_CARLO_PATHS,
            "monte_carlo_seed": MONTE_CARLO_SEED,
        },
        "changed_rows": changed_rows,
        "causal_governance": {
            "all_source_decisions_materialized_before_outcome_scoring": True,
            "future_market_used_for_decision": False,
            "future_trade_outcome_used_for_decision": False,
            "sti8_engine_retuned": False,
            "consumer_policy_retuned_after_outcomes": False,
            "shared_exit_authority": False,
            "shared_stop_authority": False,
            "shared_target_authority": False,
            "shared_sizing_authority": False,
            "shared_capital_authority": False,
            "protected_certification_holdout_opened": False,
            "productive_authority": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--partition", required=True)
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--trades", type=Path, required=True)
    parser.add_argument("--nas", type=Path, required=True)
    parser.add_argument("--sp", type=Path, required=True)
    parser.add_argument("--us", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    payload = run(
        partition=args.partition,
        frozen_policy_path=args.policy,
        trades_path=args.trades,
        nas_path=args.nas,
        sp_path=args.sp,
        us_path=args.us,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    print(
        json.dumps(
            {
                "partition": payload["partition"],
                "economic_status": payload["economic_status"],
                "economic_value_pass": payload["economic_value_pass"],
                "trade_count": payload["trade_count"],
                "economic_effects": payload["economic_effects"],
                "gates": payload["gates"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
