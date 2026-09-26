"""One-shot fresh holdout evaluator for frozen Shared V15.

The evaluator reconstructs the frozen R8 model, applies the exact V15 policy
and coherence veto, and evaluates a pre-registered pre-R8 market partition.
Fresh outcomes are evaluation labels only and cannot alter the model or policy.
"""
# ruff: noqa: E501,I001
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any, cast

import cibo_atlas_vt31_eight_ledger_builder as atlas
import cibo_atlas_vt31_historical_market_scanner as strict
import vt31_core_stack_v4_cross_market_coherence_veto_v15 as v15
import vt31_core_stack_v4_cross_market_sequence_hypothesis_v13 as v13
import vt31_core_stack_v4_perception_first_v2 as v2
import vt31_core_stack_v4_perception_sequence_topology_v8 as v8
import vt31_nas100_silver_bullet_native_streak_falsification_v1 as native
import vt31_r8_sparse_reference_forensics as sparse
from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_5_multi_index_research import (
    _day,
    load_market_evidence,
)

SCHEMA = "qore.core_stack_v4.vt31.v15_fresh_holdout.v1"
IDENTITY = "VT31_NAS100_SHARED_CROSS_MARKET_COHERENCE_VETO_V15"
HOLDOUT_END_EXCLUSIVE = "2016-04-18T00:00:00+00:00"
MINIMUM_HOLDOUT_TRADES = 200


def _daily_context(paths: dict[str, Path]) -> dict[str, dict[str, dict[str, object]]]:
    result: dict[str, dict[str, dict[str, object]]] = {}
    for market, path in paths.items():
        series, _, _, _, _, provider = load_market_evidence(path)
        grouped: dict[date, list[object]] = defaultdict(list)
        for bar in series:
            grouped[_day(bar.opened_at)].append(bar)
        for local_day, raw in sorted(grouped.items()):
            frozen = tuple(sorted(raw, key=lambda bar: bar.opened_at))
            reference = cast(
                tuple[object, ...],
                sparse._reference_bars(cast(tuple[object, ...], frozen)),
            )
            session = atlas.bars_between(cast(tuple, frozen), (10, 0, 0), (11, 0, 0))
            if (
                len(session) != 60
                or not strict.contiguous(cast(tuple, session))
                or not reference
                or not sparse._policy_accepts(reference, "gap05")
            ):
                continue
            day: dict[str, Any] = {
                "partition": "v15_fresh_holdout",
                "market": market,
                "ny_date": local_day.isoformat(),
                "provider": provider,
                "bars": frozen,
                "reference": reference,
                "session": session,
                "lifecycle": atlas.bars_between(cast(tuple, frozen), (10, 0, 0), (16, 0, 0)),
            }
            _, _, _, _, daily = atlas.analyze_episode(day)
            result.setdefault(local_day.isoformat(), {})[market] = cast(dict[str, object], daily)
    return result


def _coverage(path: Path) -> dict[str, object]:
    payload = cast(dict[str, object], json.loads(path.read_text()))
    coverage = cast(dict[str, object], payload["coverage"])
    return {
        "market": payload.get("market"),
        "provider_symbol_name": payload.get("provider_symbol_name"),
        "first_opened_at": coverage["first_opened_at"],
        "last_closed_at": coverage["last_closed_at"],
        "bar_count": coverage["bar_count"],
        "actual_calendar_span_days": payload["actual_calendar_span_days"],
        "historical_fresh_coverage_sufficient": payload["historical_fresh_coverage_sufficient"],
        "holdout_end_exclusive": payload["holdout_end_exclusive"],
        "evidence_purpose": payload["evidence_purpose"],
    }


def run(
    *,
    calibration_path: Path,
    r8_trades: Path,
    r8_nas: Path,
    r8_sp: Path,
    r8_us: Path,
    r8_daily_path: Path,
    fresh_nas: Path,
    fresh_sp: Path,
    fresh_us: Path,
) -> dict[str, object]:
    calibration = cast(dict[str, object], json.loads(calibration_path.read_text()))
    if calibration["identity"] != IDENTITY:
        raise AssertionError("V15 calibration identity mismatch")
    if calibration["passes_calibration"] is not True:
        raise AssertionError("V15 calibration did not pass")
    if calibration["r5_opened"] is not False or calibration["new_holdout_opened"] is not False:
        raise AssertionError("V15 calibration governance drift")
    if calibration["frozen_policy"] != {
        "base_policy": v15.POLICY.payload(),
        "coherence_veto": {
            "field": "peer_sequence_leader",
            "reject_values": sorted(v15.UNILATERAL_LEADERS),
            "semantics": "N1_RESCUE_REQUIRES_NO_UNILATERAL_PEER_ONSET_LEADER",
        },
    }:
        raise AssertionError("V15 frozen policy mismatch")

    old_daily = v2.v3._load_daily(r8_daily_path)
    r8 = v13._cross_rows(
        nas_path=r8_nas,
        sp_path=r8_sp,
        us_path=r8_us,
        rows=v2.v3._decorate(v2.v3._load_trades(r8_trades), old_daily),
    )
    if len(r8) != 228:
        raise AssertionError("R8 frozen challenge drift")
    negative = v8._negative_tables(r8)
    r8_n1 = [row for row in r8 if v13._negative_views(row, negative) == 1]
    if (
        len(r8_n1) != 42
        or sum(v15._d(row["net_r_after_friction"]) > 0 for row in r8_n1) != 5
        or sum(v15._d(row["net_r_after_friction"]) < 0 for row in r8_n1) != 37
    ):
        raise AssertionError("R8 N1 model population drift")
    model, _ = v13._learn_model(r8_n1)

    fresh_paths = {"NAS100": fresh_nas, "SP500": fresh_sp, "US30": fresh_us}
    coverage = {market: _coverage(path) for market, path in fresh_paths.items()}
    coverage_gate = all(
        bool(item["historical_fresh_coverage_sufficient"])
        and str(item["holdout_end_exclusive"]) == HOLDOUT_END_EXCLUSIVE
        for item in coverage.values()
    )

    baseline_payload = native.replay(fresh_nas, partition="v15_fresh_holdout")
    source_freeze = cast(dict[str, object], baseline_payload["silver_bullet_freeze"])
    if source_freeze["source_module_modified_by_lab"] is not False:
        raise AssertionError("source methodology mutation detected")
    trades = cast(list[dict[str, object]], baseline_payload["trades"])

    fresh_daily = _daily_context(fresh_paths)
    decorated = v2.v3._decorate(trades, fresh_daily)
    fresh = v13._cross_rows(
        nas_path=fresh_nas,
        sp_path=fresh_sp,
        us_path=fresh_us,
        rows=decorated,
    )
    if len(fresh) != len(trades):
        raise AssertionError("fresh trade decoration drift")

    evaluation = v15._evaluate(fresh, negative=negative, model=model)
    economic_gates = v15._gates(evaluation)
    sample_gate = len(trades) >= MINIMUM_HOLDOUT_TRADES
    passed = coverage_gate and sample_gate and all(economic_gates.values())

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "economic_status": "PASSED_FRESH_HOLDOUT" if passed else "FALSIFIED_ON_FRESH_HOLDOUT",
        "holdout": {
            "partition": "PRE_R8_FRESH_ONE_SHOT",
            "end_exclusive": HOLDOUT_END_EXCLUSIVE,
            "minimum_trade_count": MINIMUM_HOLDOUT_TRADES,
            "trade_count": len(trades),
            "trade_count_gate": sample_gate,
            "coverage": coverage,
            "coverage_gate": coverage_gate,
        },
        "frozen_policy": calibration["frozen_policy"],
        "evaluation": evaluation,
        "gates": economic_gates,
        "passes_fresh_holdout": passed,
        "r5_opened": False,
        "governance": {
            "calibration_frozen_before_holdout": True,
            "pre_r8_temporally_disjoint_holdout": True,
            "r5_opened": False,
            "r5_outcomes_used": False,
            "holdout_outcomes_used_for_retuning": False,
            "runtime_current_outcome_used": False,
            "runtime_exact_state_lookup_used": False,
            "runtime_nearest_neighbor_used": False,
            "three_index_closed_m1_used": True,
            "future_m1_used": False,
            "capital_risk_weighting_used": False,
            "methodology_modified": False,
            "shared_order_authority": False,
            "shared_risk_authority": False,
            "shared_execution_authority": False,
            "live_authorized": False,
            "production_authorized": False,
            "merge_authorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--calibration", type=Path, required=True)
    parser.add_argument("--r8-trades", type=Path, required=True)
    parser.add_argument("--r8-nas", type=Path, required=True)
    parser.add_argument("--r8-sp", type=Path, required=True)
    parser.add_argument("--r8-us", type=Path, required=True)
    parser.add_argument("--r8-daily", type=Path, required=True)
    parser.add_argument("--fresh-nas", type=Path, required=True)
    parser.add_argument("--fresh-sp", type=Path, required=True)
    parser.add_argument("--fresh-us", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = run(
        calibration_path=args.calibration,
        r8_trades=args.r8_trades,
        r8_nas=args.r8_nas,
        r8_sp=args.r8_sp,
        r8_us=args.r8_us,
        r8_daily_path=args.r8_daily,
        fresh_nas=args.fresh_nas,
        fresh_sp=args.fresh_sp,
        fresh_us=args.fresh_us,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    print(json.dumps({
        "economic_status": payload["economic_status"],
        "passes_fresh_holdout": payload["passes_fresh_holdout"],
        "holdout": payload["holdout"],
        "evaluation": payload["evaluation"],
        "gates": payload["gates"],
        "r5_opened": payload["r5_opened"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
