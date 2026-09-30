#!/usr/bin/env python3
"""Evaluate preregistered STI-8 economic response V3 on fresh research OOS."""

from __future__ import annotations

import argparse
import json
from decimal import Decimal
from pathlib import Path
from statistics import median
from typing import Any, cast

import shared_sti6_sti8_real_position_intelligence as base
import shared_sti8_economic_value_v1 as econ

from qore.infrastructure.core_stack_v2.shared_position_threat_intelligence import (
    SharedPositionThreatEngineAssessment,
    assess_position_threat,
)
from qore.infrastructure.traders.vt31_shared_threat_consumer_research import (
    Vt31ThreatConsumerAction,
)
from qore.infrastructure.traders.vt31_shared_threat_consumer_v3_research import (
    FROZEN_STI8_RESPONSE_V3,
    decide_vt31_threat_response_v3,
)

IDENTITY = "QORE_SHARED_STI8_ECONOMIC_RESPONSE_V3_RESEARCH_OOS_001"
PARTITION = "sti8_economic_response_v3_oos"
MINIMUM_TRADE_COUNT = 20


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def run(
    *,
    frozen_policy_path: Path,
    trades_path: Path,
    nas_path: Path,
    sp_path: Path,
    us_path: Path,
) -> dict[str, object]:
    frozen = json.loads(frozen_policy_path.read_text())
    if frozen.get("identity") != base.IDENTITY:
        raise ValueError("unexpected frozen STI-8 signal policy identity")
    if frozen.get("mode") != "SOURCE_ONLY_POLICY_FREEZE":
        raise ValueError("V3 OOS requires source-only frozen STI-8 policy")

    sti8_policy = base._sti8_policy(frozen)
    sequences = base._source_sequences(
        partition=PARTITION,
        trades_path=trades_path,
        nas_path=nas_path,
        sp_path=sp_path,
        us_path=us_path,
    )
    paths = base._reconstruct_source_partition(nas_path)
    if not sequences:
        raise ValueError("STI-8 response V3 OOS contains no valid trades")

    materialized: list[dict[str, Any]] = []
    source_observation_count = 0
    for sequence in sequences:
        row = cast(dict[str, object], sequence["row"])
        observations = cast(tuple[Any, ...], sequence["observations"])
        source_observation_count += len(observations)
        first_exit_index: int | None = None
        first_level: str | None = None
        first_scope: str | None = None
        previous_observation: Any | None = None
        previous_assessment: SharedPositionThreatEngineAssessment | None = None

        for index, observation in enumerate(observations):
            assessment = assess_position_threat(observation, policy=sti8_policy)
            decision = decide_vt31_threat_response_v3(
                previous_observation=previous_observation,
                previous_assessment=previous_assessment,
                observation=observation,
                assessment=assessment,
                shared_intelligence_ref=(
                    f"sti8:v3:{PARTITION}:{observation.observation_id}"
                ),
            )
            if (
                first_exit_index is None
                and decision.action
                is Vt31ThreatConsumerAction.EXIT_NEXT_M1_OPEN
            ):
                first_exit_index = index
                first_level = assessment.threat_level.value
                first_scope = assessment.threat_scope.value
            previous_observation = observation
            previous_assessment = assessment

        # No terminal trade outcome has been used before this point.
        materialized.append(
            {
                "row": row,
                "observations": observations,
                "first_exit_index": first_exit_index,
                "first_level": first_level,
                "first_scope": first_scope,
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
                raise ValueError(f"missing reconstructed V3 OOS path for {signal}")
            setup, day_bars = paths[signal]
            candidate = econ._next_open_exit_r(
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
                        "first_level": item["first_level"],
                        "first_scope": item["first_scope"],
                    }
                )
                if baseline_r < 0:
                    true_threat_leads.append(
                        len(observations) - 1 - first_exit_index
                    )
        treatment_values.append(managed_r)

    control = econ._metrics(control_values)
    treatment = econ._metrics(treatment_values)
    bootstrap = econ._paired_bootstrap_dd(control_values, treatment_values)
    retention = econ._winner_retention(control_values, treatment_values)

    loss_r_avoided = sum(
        (
            treatment_values[i] - control_values[i]
            for i in range(len(control_values))
            if control_values[i] < 0 and treatment_values[i] > control_values[i]
        ),
        Decimal(0),
    )
    false_threat_cost = sum(
        (
            control_values[i] - treatment_values[i]
            for i in range(len(control_values))
            if control_values[i] >= 0 and treatment_values[i] < control_values[i]
        ),
        Decimal(0),
    )
    net_utility = sum(treatment_values, Decimal(0)) - sum(
        control_values,
        Decimal(0),
    )

    gates = {
        "minimum_trade_count": len(control_values) >= MINIMUM_TRADE_COUNT,
        "treatment_total_r_gte_control": (
            _d(treatment["total_r"]) >= _d(control["total_r"])
        ),
        "treatment_profit_factor_gt_control": econ._pf_gt(
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
            >= econ.WINNER_COUNT_RETENTION_MIN
        ),
        "winner_r_retention_min": (
            _d(retention["winner_r_retention"])
            >= econ.WINNER_R_RETENTION_MIN
        ),
        "top_decile_winner_r_retention_min": (
            _d(retention["top_decile_winner_r_retention"])
            >= econ.TOP_DECILE_WINNER_R_RETENTION_MIN
        ),
        "top_5pct_winner_r_retention_min": (
            _d(retention["top_5pct_winner_r_retention"])
            >= econ.TOP_5PCT_WINNER_R_RETENTION_MIN
        ),
        "positive_tail_r_retention_min": (
            _d(retention["positive_tail_r_retention"])
            >= econ.POSITIVE_TAIL_R_RETENTION_MIN
        ),
    }
    passed = all(gates.values())
    return {
        "identity": IDENTITY,
        "partition": PARTITION,
        "status": (
            "STI8_RESPONSE_V3_RESEARCH_OOS_ECONOMIC_PASS"
            if passed
            else "STI8_RESPONSE_V3_RESEARCH_OOS_FALSIFIED"
        ),
        "economic_value_pass": passed,
        "trade_count": len(control_values),
        "source_observation_count": source_observation_count,
        "changed_trade_count": len(changed_rows),
        "control": control,
        "treatment": treatment,
        "bootstrap_dd": bootstrap,
        "winner_preservation": retention,
        "economic_effects": {
            "loss_r_avoided": str(loss_r_avoided),
            "false_threat_cost_r": str(false_threat_cost),
            "net_economic_utility_r": str(net_utility),
            "median_true_threat_lead_minutes": (
                None if not true_threat_leads else median(true_threat_leads)
            ),
        },
        "gates": gates,
        "signal_policy_fingerprint": frozen["sti8_policy_fingerprint"],
        "response_policy_fingerprint": FROZEN_STI8_RESPONSE_V3.fingerprint(),
        "changed_rows": changed_rows,
        "governance": {
            "parent_v2_burned_evidence_used_for_v3_value_claim": False,
            "all_source_decisions_materialized_before_outcome_scoring": True,
            "future_market_used_for_decision": False,
            "future_outcome_used_for_decision": False,
            "sti8_signal_engine_changed": False,
            "sti8_threat_thresholds_changed": False,
            "numeric_rescue_threshold_added": False,
            "response_policy_retuned_after_oos": False,
            "shared_exit_authority": False,
            "shared_stop_authority": False,
            "shared_target_authority": False,
            "protected_certification_holdout_opened": False,
            "temporal_replication_claim": False,
            "productive_authority": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--trades", type=Path, required=True)
    parser.add_argument("--nas", type=Path, required=True)
    parser.add_argument("--sp", type=Path, required=True)
    parser.add_argument("--us", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = run(
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
                "status": payload["status"],
                "trade_count": payload["trade_count"],
                "economic_effects": payload["economic_effects"],
                "gates": payload["gates"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
