#!/usr/bin/env python3
"""Stitched sovereign adjudicator for VT31 fill-time revalidation."""
from __future__ import annotations

import argparse
import json
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

import vt31_nas100_comp009_final_preholdout_metric_pack_v1 as pack
import vt31_nas100_specialist_r1_candidate as specialist

CONTROL = "COMP009_TRUTHFUL_CONTROL"
CANDIDATE = "FILL_REVALIDATE_REASONING"
LANES = ("r5", "r6", "r8", "consumed")


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _pf(metrics: dict[str, object]) -> Decimal:
    value = metrics.get("profit_factor")
    if value is None:
        return Decimal("Infinity")
    return _d(value)


def _load(root: Path, lane: str) -> dict[str, Any]:
    return json.loads(
        (root / "lanes" / lane / "normalized.json").read_text(
            encoding="utf-8"
        )
    )


def _daily(
    rows: list[dict[str, object]],
    eligible_dates: list[str],
) -> list[dict[str, str]]:
    totals = {day: Decimal(0) for day in eligible_dates}
    for row in rows:
        day = str(row["local_date"])
        if day not in totals:
            raise AssertionError(f"trade outside eligible session: {day}")
        totals[day] += _d(row["r_multiple"]) - pack.BASELINE_FRICTION_R
    return [
        {"local_date": day, "daily_r": format(totals[day], "f")}
        for day in eligible_dates
    ]


def _temporal_ok(
    control: dict[str, object],
    candidate: dict[str, object],
) -> bool:
    left = cast(dict[str, dict[str, object]], control["temporal_blocks"])
    right = cast(dict[str, dict[str, object]], candidate["temporal_blocks"])
    common = set(left) & set(right)
    if not common:
        return False
    return all(
        _d(right[key]["mean_r"]) >= _d(left[key]["mean_r"])
        and _d(right[key]["max_drawdown_r"])
        <= _d(left[key]["max_drawdown_r"])
        for key in common
    )


def _report(
    payloads: dict[str, dict[str, Any]],
    name: str,
) -> dict[str, object]:
    rows = [
        cast(dict[str, object], row)
        for lane in LANES
        for row in cast(
            list[dict[str, object]],
            payloads[lane]["variants"][name]["candidate_rows"],
        )
    ]
    rows.sort(key=lambda row: str(row["signal_at"]))
    ids = [str(row["signal_at"]) for row in rows]
    if len(ids) != len(set(ids)):
        raise AssertionError(f"{name}: overlapping signal identity")

    eligible = sorted(
        {
            str(day)
            for lane in LANES
            for day in cast(list[str], payloads[lane]["eligible_dates"])
        }
    )
    metrics = specialist._metrics(rows, friction=pack.BASELINE_FRICTION_R)
    payoff = pack._payoff(rows, pack.BASELINE_FRICTION_R)
    risk = pack._risk_adjusted(_daily(rows, eligible))
    stress = pack._cost_stress(rows)
    dd = pack._drawdown_episode(rows, pack.BASELINE_FRICTION_R)

    folds: dict[str, object] = {}
    all_pf = True
    all_dd = True
    all_density = True
    all_winner = True
    all_temporal = True
    changed = 0
    rejected: list[dict[str, object]] = []

    for lane in LANES:
        item = cast(dict[str, object], payloads[lane]["variants"][name])
        control = cast(dict[str, object], payloads[lane]["variants"][CONTROL])
        fm = cast(dict[str, object], item["metrics"])
        preserve = cast(dict[str, object], item["winner_preservation"])
        pf_ok = _pf(fm) >= Decimal("1.50")
        dd_ok = _d(fm["max_drawdown_r"]) <= Decimal("6")
        density_ok = _d(item["relative_density_vs_control"]) >= Decimal("0.75")
        winner_ok = (
            _d(preserve["winner_count_preservation"]) >= Decimal("0.80")
            and _d(preserve["winner_r_preservation"]) >= Decimal("0.90")
        )
        temporal_ok = _temporal_ok(control, item)
        all_pf &= pf_ok
        all_dd &= dd_ok
        all_density &= density_ok
        all_winner &= winner_ok
        all_temporal &= temporal_ok
        changed += int(item["changed_trade_count"])
        rejected.extend(
            cast(list[dict[str, object]], item["changed_trade_forensics"])
        )
        folds[lane] = {
            "metrics": fm,
            "pf_pass": pf_ok,
            "dd_pass": dd_ok,
            "density_pass": density_ok,
            "winner_pass": winner_ok,
            "temporal_nondegrade": temporal_ok,
            "changed_trade_count": item["changed_trade_count"],
        }

    cheap = {
        "all_fold_pf_at_least_1_50": all_pf,
        "all_fold_observed_dd_at_most_6r": all_dd,
        "density_at_least_0_75_all_folds": all_density,
        "winner_preservation_all_folds": all_winner,
        "halfyear_temporal_nondegrade_all_folds": all_temporal,
        "combined_pf_at_least_1_70": _pf(metrics) >= Decimal("1.70"),
        "combined_expectancy_at_least_0_15r": (
            _d(metrics["mean_r"]) >= Decimal("0.15")
        ),
        "payoff_at_least_1_20": (
            payoff is not None and payoff >= Decimal("1.20")
        ),
        "stitched_observed_dd_at_most_6r": (
            _d(dd["max_drawdown_r"]) <= Decimal("6")
        ),
        "annualized_sharpe_at_least_1_50": (
            risk["annualized_sharpe"] is not None
            and _d(risk["annualized_sharpe"]) >= Decimal("1.50")
        ),
        "annualized_sortino_at_least_2_00": (
            risk["annualized_sortino"] is not None
            and _d(risk["annualized_sortino"]) >= Decimal("2.00")
        ),
        "degraded_0_10r_pf_gt_1": (
            _pf(cast(dict[str, object], stress["0.10"])) > Decimal("1")
        ),
        "economic_actuation_present": name == CONTROL or changed > 0,
    }
    core = all(cheap.values())

    if core:
        mc = specialist._monte_carlo(rows)
        mc_gates = {
            "mc_positive_at_least_0_90": (
                _d(mc["positive_terminal_probability"]) >= Decimal("0.90")
            ),
            "mc_p95_dd_at_most_15r": (
                _d(mc["p95_max_drawdown_r"]) <= Decimal("15")
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

    gates = {**cheap, **mc_gates}
    return {
        "trade_count": len(rows),
        "eligible_session_count": len(eligible),
        "metrics": metrics,
        "payoff_ratio": None if payoff is None else format(payoff, "f"),
        "risk_adjusted": risk,
        "cost_stress": stress,
        "drawdown_episode": dd,
        "folds": folds,
        "changed_trade_count": changed,
        "rejected_trade_count": len(rejected),
        "rejected_winner_count": sum(
            item.get("control_winner") is True for item in rejected
        ),
        "rejected_zero_call_loss_count": sum(
            item.get("zero_post_entry_cognitive_calls") is True
            and item.get("control_winner") is False
            for item in rejected
        ),
        "rejected_trade_forensics": rejected,
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
    payloads = {lane: _load(args.output_root, lane) for lane in LANES}
    reports = {
        CONTROL: _report(payloads, CONTROL),
        CANDIDATE: _report(payloads, CANDIDATE),
    }
    result = {
        "schema": "qore.github-trader-lab.vt31-fill-time-stitched.v1",
        "reports": reports,
        "stitched_survivors": [
            name
            for name, row in reports.items()
            if name != CONTROL and row["stitched_gate_pass"] is True
        ],
        "governance": {
            "consumed_evidence_only": True,
            "pure_edge_only": True,
            "fresh_holdout_opened": False,
            "delay_threshold_used": False,
            "fill_bar_ohlc_decision_authority": False,
            "metric_conventions_retuned": False,
            "position_sizing_used": False,
            "leverage_used": False,
            "compounding_used": False,
            "candidate_certified": False,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        "VT31_FILL_STITCHED "
        + json.dumps(
            {
                name: {
                    "trades": row["trade_count"],
                    "dd": row["metrics"]["max_drawdown_r"],
                    "pf": row["metrics"]["profit_factor"],
                    "mean": row["metrics"]["mean_r"],
                    "sharpe": row["risk_adjusted"]["annualized_sharpe"],
                    "sortino": row["risk_adjusted"]["annualized_sortino"],
                    "changed": row["changed_trade_count"],
                    "rejected_winners": row["rejected_winner_count"],
                    "rejected_zero_call_losses": row[
                        "rejected_zero_call_loss_count"
                    ],
                    "pass": row["stitched_gate_pass"],
                    "mc": row["monte_carlo_stage"],
                }
                for name, row in reports.items()
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
