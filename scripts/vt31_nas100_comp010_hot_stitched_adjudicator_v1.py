"""Staged hot stitched adjudicator for VT31 GitHub Trader Lab.

Cheap sovereign gates (stitched DD and frozen eligible-session Sharpe) run
first. The canonical 10,000-path Monte Carlo executes only for variants that
survive those blockers, avoiding expensive work on already-falsified ideas.
"""
from __future__ import annotations

import argparse
import json
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_nas100_comp009_final_preholdout_metric_pack_v1 as pack
import vt31_nas100_specialist_r1_candidate as specialist

SCHEMA = "qore.vt31.nas100.comp010.hot_stitched_adjudicator.v1"
CONTROL = "COMP006_CONTROL"
FOLDS = ("r5", "r6", "r8", "consumed")


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _parse(value: str) -> tuple[str, Path]:
    name, sep, raw = value.partition("=")
    if not sep or name not in FOLDS:
        raise argparse.ArgumentTypeError("fold must be r5|r6|r8|consumed=PATH")
    return name, Path(raw)


def _pf(metrics: dict[str, object]) -> Decimal:
    value = metrics.get("profit_factor")
    if value is None:
        return Decimal("Infinity")
    return _d(value)


def _daily(
    rows: list[dict[str, object]],
    eligible_dates: list[str],
) -> list[dict[str, str]]:
    totals = {day: Decimal(0) for day in eligible_dates}
    for row in rows:
        totals[str(row["local_date"])] += (
            _d(row["r_multiple"]) - pack.BASELINE_FRICTION_R
        )
    return [
        {"local_date": day, "daily_r": format(totals[day], "f")}
        for day in eligible_dates
    ]


def _report(
    name: str,
    payloads: dict[str, dict[str, object]],
) -> dict[str, object]:
    rows = [
        cast(dict[str, object], row)
        for fold in FOLDS
        for row in cast(
            list[dict[str, object]],
            cast(
                dict[str, object],
                cast(dict[str, object], payloads[fold]["variants"])[name],
            )["candidate_rows"],
        )
    ]
    rows.sort(key=lambda row: str(row["signal_at"]))
    ids = [str(row["signal_at"]) for row in rows]
    if len(ids) != len(set(ids)):
        raise AssertionError(f"{name}: signal overlap")

    eligible = sorted(
        {
            str(day)
            for fold in FOLDS
            for day in cast(
                list[str],
                cast(
                    dict[str, object],
                    cast(dict[str, object], payloads[fold]["variants"])[name],
                )["eligible_dates"],
            )
        }
    )
    metrics = specialist._metrics(rows, friction=pack.BASELINE_FRICTION_R)
    payoff = pack._payoff(rows, pack.BASELINE_FRICTION_R)
    risk = pack._risk_adjusted(_daily(rows, eligible))
    stress = pack._cost_stress(rows)
    dd = pack._drawdown_episode(rows, pack.BASELINE_FRICTION_R)

    folds: dict[str, object] = {}
    all_fold_dd = True
    all_fold_pf = True
    winner_all = True
    for fold in FOLDS:
        item = cast(
            dict[str, object],
            cast(dict[str, object], payloads[fold]["variants"])[name],
        )
        fm = cast(dict[str, object], item["stress_0_05r"])
        winner = cast(
            dict[str, object],
            item["winner_preservation_vs_control"],
        )
        dd_ok = _d(fm["max_drawdown_r"]) <= Decimal("6")
        pf_ok = _pf(fm) >= Decimal("1.50")
        winner_ok = (
            _d(winner["winner_count_preservation"]) >= Decimal("0.80")
            and _d(winner["winner_r_preservation"]) >= Decimal("0.90")
        )
        all_fold_dd &= dd_ok
        all_fold_pf &= pf_ok
        winner_all &= winner_ok
        folds[fold] = {
            "metrics": fm,
            "changed_trade_count": item["changed_trade_count"],
            "dd_pass": dd_ok,
            "pf_pass": pf_ok,
            "winner_pass": winner_ok,
        }

    cheap_gates = {
        "all_fold_dd_at_most_6r": all_fold_dd,
        "all_fold_pf_at_least_1_50": all_fold_pf,
        "winner_preservation_all_folds": winner_all,
        "stitched_dd_at_most_6r": (
            _d(dd["max_drawdown_r"]) <= Decimal("6")
        ),
        "combined_pf_at_least_1_70": _pf(metrics) >= Decimal("1.70"),
        "combined_expectancy_at_least_0_15r": (
            _d(metrics["mean_r"]) >= Decimal("0.15")
        ),
        "payoff_at_least_1_20": (
            payoff is not None and payoff >= Decimal("1.20")
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
    }
    core_survivor = (
        cheap_gates["stitched_dd_at_most_6r"]
        and cheap_gates["annualized_sharpe_at_least_1_50"]
        and all(cheap_gates.values())
    )

    if core_survivor:
        mc = specialist._monte_carlo(rows)
        mc_gates = {
            "mc_positive_at_least_0_90": (
                _d(mc["positive_terminal_probability"]) >= Decimal("0.90")
            ),
            "mc_p95_dd_at_most_15r": (
                _d(mc["p95_max_drawdown_r"]) <= Decimal("15")
            ),
        }
        mc_status = "EXECUTED_AFTER_CORE_SURVIVAL"
    else:
        mc = {
            "algorithm": "deferred-core-gates-failed",
            "paths": 0,
            "positive_terminal_probability": None,
            "p95_max_drawdown_r": None,
        }
        mc_gates = {}
        mc_status = "DEFERRED_CORE_GATES_FAILED"

    gates = {**cheap_gates, **mc_gates}
    return {
        "folds": folds,
        "trade_count": len(rows),
        "eligible_session_count": len(eligible),
        "metrics": metrics,
        "payoff_ratio": None if payoff is None else format(payoff, "f"),
        "risk_adjusted": risk,
        "cost_stress": stress,
        "drawdown_episode": dd,
        "monte_carlo": mc,
        "monte_carlo_stage": mc_status,
        "gates": gates,
        "stitched_gate_pass": core_survivor and all(mc_gates.values()),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fold", action="append", type=_parse, required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    paths = dict(args.fold)
    if set(paths) != set(FOLDS) or len(args.fold) != 4:
        raise SystemExit("exactly four unique folds are required")
    payloads = {
        fold: json.loads(path.read_text(encoding="utf-8"))
        for fold, path in paths.items()
    }
    names = tuple(
        cast(dict[str, object], payloads["r5"]["variants"]).keys()
    )
    reports = {name: _report(name, payloads) for name in names}
    result = {
        "schema": SCHEMA,
        "baseline_comparator_id": (
            "VT31_AB_COMP009_MAX_INTELLIGENCE_COMPOSED_SURVIVOR"
        ),
        "control_alias": CONTROL,
        "variants": reports,
        "stitched_survivors": [
            name
            for name, row in reports.items()
            if name != CONTROL and row["stitched_gate_pass"] is True
        ],
        "governance": {
            "consumed_evidence_only": True,
            "fresh_holdout_opened": False,
            "staged_science": True,
            "mc_only_after_dd_and_sharpe_survival": True,
            "pure_edge_only": True,
            "position_sizing_used": False,
            "leverage_used": False,
            "compounding_used": False,
            "candidate_certified": False,
            "live_authorized": False,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
