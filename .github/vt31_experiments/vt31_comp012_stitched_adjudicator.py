#!/usr/bin/env python3
"""Stitched adjudicator for VT31 Comparator-012.

Runs frozen deterministic gates first. Monte Carlo runs only after DD and
Sharpe, plus all other cheap sovereign gates, have passed.
"""
from __future__ import annotations

import argparse
import json
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

import vt31_nas100_comp009_final_preholdout_metric_pack_v1 as pack
import vt31_nas100_specialist_r1_candidate as specialist

CONTROL = "COMP009_CONTROL"
CANDIDATE = "COMP012_STALE_ENTRY_ZONE_FAILURE_EXIT"
LANES = ("r5", "r6", "r8", "consumed")
ELIGIBLE_SESSION_COUNT = 2023


def d(value: object) -> Decimal:
    return Decimal(str(value))


def pf(metrics: dict[str, object]) -> Decimal:
    value = metrics.get("profit_factor")
    if value is None:
        return Decimal("Infinity")
    return d(value)


def load_lane(root: Path, lane: str) -> dict[str, Any]:
    return json.loads(
        (root / "lanes" / lane / "normalized.json").read_text(
            encoding="utf-8"
        )
    )


def temporal_nondegrade(
    control: dict[str, object],
    candidate: dict[str, object],
) -> bool:
    left = cast(dict[str, dict[str, object]], control["temporal_blocks"])
    right = cast(dict[str, dict[str, object]], candidate["temporal_blocks"])
    common = set(left) & set(right)
    if not common:
        return False
    return all(
        d(right[key]["mean_r"]) >= d(left[key]["mean_r"])
        and d(right[key]["max_drawdown_r"])
        <= d(left[key]["max_drawdown_r"])
        for key in common
    )


def aggregate(
    payloads: dict[str, dict[str, Any]],
    variant: str,
) -> dict[str, object]:
    rows = [
        cast(dict[str, object], row)
        for lane in LANES
        for row in cast(
            list[dict[str, object]],
            payloads[lane]["variants"][variant]["candidate_rows"],
        )
    ]
    rows.sort(key=lambda row: str(row["signal_at"]))
    ids = [str(row["signal_at"]) for row in rows]
    if len(ids) != len(set(ids)):
        raise AssertionError(f"{variant}: overlapping signal identity")

    dates = [str(row["local_date"]) for row in rows]
    if len(dates) != len(set(dates)):
        raise AssertionError(f"{variant}: multiple trades on one eligible date")

    metrics = specialist._metrics(rows, friction=pack.BASELINE_FRICTION_R)
    payoff = pack._payoff(rows, pack.BASELINE_FRICTION_R)
    stress = pack._cost_stress(rows)
    dd = pack._drawdown_episode(rows, pack.BASELINE_FRICTION_R)

    daily = [
        {
            "local_date": str(row["local_date"]),
            "daily_r": format(
                d(row["r_multiple"]) - pack.BASELINE_FRICTION_R,
                "f",
            ),
        }
        for row in rows
    ]
    no_trade_count = ELIGIBLE_SESSION_COUNT - len(daily)
    if no_trade_count < 0:
        raise AssertionError("eligible-session count underflow")
    daily.extend(
        {
            "local_date": f"NO_TRADE_{index:04d}",
            "daily_r": "0",
        }
        for index in range(no_trade_count)
    )
    risk = pack._risk_adjusted(daily)

    fold_gate: dict[str, object] = {}
    all_pf = True
    all_dd = True
    all_winner = True
    all_temporal = True
    all_density = True
    changed_total = 0
    changes: list[dict[str, object]] = []
    for lane in LANES:
        item = cast(dict[str, object], payloads[lane]["variants"][variant])
        control = cast(dict[str, object], payloads[lane]["variants"][CONTROL])
        fm = cast(dict[str, object], item["metrics"])
        preserve = cast(dict[str, str], item["winner_preservation"])
        pf_ok = pf(fm) >= Decimal("1.50")
        dd_ok = d(fm["max_drawdown_r"]) <= Decimal("6")
        winner_ok = (
            d(preserve["count"]) >= Decimal("0.80")
            and d(preserve["r"]) >= Decimal("0.90")
        )
        density_ok = d(item["relative_density_vs_control"]) >= Decimal("0.75")
        temporal_ok = temporal_nondegrade(control, item)
        all_pf &= pf_ok
        all_dd &= dd_ok
        all_winner &= winner_ok
        all_density &= density_ok
        all_temporal &= temporal_ok
        changed_total += int(item["changed_trade_count"])
        changes.extend(
            cast(list[dict[str, object]], item["changed_trade_forensics"])
        )
        fold_gate[lane] = {
            "metrics": fm,
            "pf_pass": pf_ok,
            "dd_pass": dd_ok,
            "winner_pass": winner_ok,
            "density_pass": density_ok,
            "temporal_nondegrade": temporal_ok,
            "changed_trade_count": item["changed_trade_count"],
        }

    cheap_gates = {
        "all_fold_pf_at_least_1_50": all_pf,
        "all_fold_observed_dd_at_most_6r": all_dd,
        "density_at_least_0_75_all_folds": all_density,
        "winner_preservation_all_folds": all_winner,
        "halfyear_temporal_nondegrade_all_folds": all_temporal,
        "combined_pf_at_least_1_70": pf(metrics) >= Decimal("1.70"),
        "combined_expectancy_at_least_0_15r": (
            d(metrics["mean_r"]) >= Decimal("0.15")
        ),
        "payoff_at_least_1_20": (
            payoff is not None and payoff >= Decimal("1.20")
        ),
        "stitched_observed_dd_at_most_6r": (
            d(dd["max_drawdown_r"]) <= Decimal("6")
        ),
        "annualized_sharpe_at_least_1_50": (
            risk["annualized_sharpe"] is not None
            and d(risk["annualized_sharpe"]) >= Decimal("1.50")
        ),
        "annualized_sortino_at_least_2_00": (
            risk["annualized_sortino"] is not None
            and d(risk["annualized_sortino"]) >= Decimal("2.00")
        ),
        "degraded_0_10r_pf_gt_1": (
            pf(cast(dict[str, object], stress["0.10"])) > Decimal("1")
        ),
        "economic_actuation_present": (
            variant == CONTROL or changed_total > 0
        ),
    }
    core = all(cheap_gates.values())

    if core:
        mc = specialist._monte_carlo(rows)
        mc_gates = {
            "mc_positive_at_least_0_90": (
                d(mc["positive_terminal_probability"]) >= Decimal("0.90")
            ),
            "mc_p95_dd_at_most_15r": (
                d(mc["p95_max_drawdown_r"]) <= Decimal("15")
            ),
        }
        mc_stage = "EXECUTED_AFTER_CORE_SURVIVAL"
    else:
        mc = {
            "algorithm": "deferred-core-gates-failed",
            "paths": 0,
            "positive_terminal_probability": None,
            "p95_max_drawdown_r": None,
        }
        mc_gates = {}
        mc_stage = "DEFERRED_CORE_GATES_FAILED"

    gates = {**cheap_gates, **mc_gates}
    return {
        "trade_count": len(rows),
        "metrics": metrics,
        "payoff_ratio": None if payoff is None else format(payoff, "f"),
        "risk_adjusted": risk,
        "cost_stress": stress,
        "drawdown_episode": dd,
        "folds": fold_gate,
        "changed_trade_count": changed_total,
        "changed_trade_forensics": changes,
        "monte_carlo": mc,
        "monte_carlo_stage": mc_stage,
        "gates": gates,
        "stitched_gate_pass": core and all(mc_gates.values()),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    payloads = {
        lane: load_lane(args.output_root, lane)
        for lane in LANES
    }
    reports = {
        CONTROL: aggregate(payloads, CONTROL),
        CANDIDATE: aggregate(payloads, CANDIDATE),
    }
    result = {
        "schema": "qore.github-trader-lab.vt31-comp012-stitched.v1",
        "baseline_comparator_id": (
            "VT31_AB_COMP009_MAX_INTELLIGENCE_COMPOSED_SURVIVOR"
        ),
        "variant": CANDIDATE,
        "reports": reports,
        "stitched_survivors": [
            name
            for name, report in reports.items()
            if name != CONTROL and report["stitched_gate_pass"] is True
        ],
        "governance": {
            "consumed_evidence_only": True,
            "pure_edge_only": True,
            "fresh_holdout_opened": False,
            "metric_conventions_retuned": False,
            "position_sizing_used": False,
            "dynamic_sizing_used": False,
            "leverage_used": False,
            "compounding_used": False,
            "portfolio_weighting_used": False,
            "capital_weighting_used": False,
            "candidate_certified": False,
            "live_authorized": False,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    headline = {
        name: {
            "stitched_dd_r": report["metrics"]["max_drawdown_r"],
            "profit_factor": report["metrics"]["profit_factor"],
            "mean_r": report["metrics"]["mean_r"],
            "annualized_sharpe": report["risk_adjusted"]["annualized_sharpe"],
            "annualized_sortino": report["risk_adjusted"]["annualized_sortino"],
            "changed_trade_count": report["changed_trade_count"],
            "stitched_gate_pass": report["stitched_gate_pass"],
            "monte_carlo_stage": report["monte_carlo_stage"],
        }
        for name, report in reports.items()
    }
    print("VT31_COMP012_STITCHED " + json.dumps(headline, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
