"""VT31 NAS100 Comparator-010 stitched adjudicator V1.

Consumes four GitHub Trader Lab fold results and evaluates the same candidate
policies on one chronological equal-R path under the already-frozen Comparator
009 metric conventions.
"""
from __future__ import annotations

import argparse
import json
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_nas100_comp009_final_preholdout_metric_pack_v1 as pack
import vt31_nas100_specialist_r1_candidate as specialist

SCHEMA = "qore.vt31.nas100.comp010.stitched_adjudicator.v1"
CONTROL = "COMP006_CONTROL"
FOLDS = ("r5", "r6", "r8", "consumed")


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _parse_fold(value: str) -> tuple[str, Path]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("fold must be NAME=PATH")
    name, raw = value.split("=", 1)
    if name not in FOLDS:
        raise argparse.ArgumentTypeError(f"unexpected fold: {name}")
    return name, Path(raw)


def _daily_series(
    rows: list[dict[str, object]],
    eligible_dates: list[str],
) -> list[dict[str, str]]:
    eligible = set(eligible_dates)
    totals: dict[str, Decimal] = {
        day: Decimal(0) for day in eligible_dates
    }
    for row in rows:
        day = str(row["local_date"])
        if day not in eligible:
            raise AssertionError(
                f"trade {row['signal_at']} outside eligible sessions"
            )
        totals[day] += _d(row["r_multiple"]) - pack.BASELINE_FRICTION_R
    return [
        {"local_date": day, "daily_r": format(totals[day], "f")}
        for day in eligible_dates
    ]


def _pf(metrics: dict[str, object]) -> Decimal:
    value = metrics.get("profit_factor")
    if value is None:
        wins = int(metrics["wins"])
        losses = int(metrics["losses"])
        if wins > 0 and losses == 0:
            return Decimal("Infinity")
        return Decimal("-Infinity")
    return _d(value)


def _variant_report(
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
                cast(
                    dict[str, object],
                    payloads[fold]["variants"],
                )[name],
            )["candidate_rows"],
        )
    ]
    rows.sort(key=lambda row: str(row["signal_at"]))
    signal_ids = [str(row["signal_at"]) for row in rows]
    if len(signal_ids) != len(set(signal_ids)):
        raise AssertionError(f"{name}: signal overlap across folds")

    eligible_dates = sorted(
        {
            str(day)
            for fold in FOLDS
            for day in cast(
                list[str],
                cast(
                    dict[str, object],
                    cast(
                        dict[str, object],
                        payloads[fold]["variants"],
                    )[name],
                )["eligible_dates"],
            )
        }
    )

    metrics = specialist._metrics(rows, friction=pack.BASELINE_FRICTION_R)
    payoff = pack._payoff(rows, pack.BASELINE_FRICTION_R)
    daily = _daily_series(rows, eligible_dates)
    risk = pack._risk_adjusted(daily)
    mc = specialist._monte_carlo(rows)
    stress = pack._cost_stress(rows)
    dd = pack._drawdown_episode(rows, pack.BASELINE_FRICTION_R)

    folds: dict[str, object] = {}
    all_fold_dd = True
    all_fold_pf = True
    density_all = True
    winner_all = True
    for fold in FOLDS:
        item = cast(
            dict[str, object],
            cast(dict[str, object], payloads[fold]["variants"])[name],
        )
        metrics_fold = cast(dict[str, object], item["stress_0_05r"])
        winner = cast(
            dict[str, object],
            item["winner_preservation_vs_control"],
        )
        density = _d(item["relative_density_vs_control"])
        fold_dd_ok = _d(metrics_fold["max_drawdown_r"]) <= Decimal("6")
        fold_pf_ok = _pf(metrics_fold) >= Decimal("1.50")
        winner_ok = (
            _d(winner["winner_count_preservation"]) >= Decimal("0.80")
            and _d(winner["winner_r_preservation"]) >= Decimal("0.90")
        )
        all_fold_dd &= fold_dd_ok
        all_fold_pf &= fold_pf_ok
        density_all &= density >= Decimal("0.75")
        winner_all &= winner_ok
        folds[fold] = {
            "metrics": metrics_fold,
            "monte_carlo": item["monte_carlo"],
            "relative_density_vs_control": item[
                "relative_density_vs_control"
            ],
            "winner_preservation_vs_control": winner,
            "changed_trade_count": item["changed_trade_count"],
            "fold_dd_at_most_6r": fold_dd_ok,
            "fold_pf_at_least_1_50": fold_pf_ok,
            "winner_preservation_pass": winner_ok,
        }

    gates = {
        "all_fold_observed_dd_at_most_6r": all_fold_dd,
        "all_fold_pf_at_least_1_50": all_fold_pf,
        "density_at_least_0_75_all_folds": density_all,
        "winner_preservation_all_folds": winner_all,
        "stitched_observed_dd_at_most_6r": (
            _d(dd["max_drawdown_r"]) <= Decimal("6")
        ),
        "combined_pf_at_least_1_70": _pf(metrics) >= Decimal("1.70"),
        "combined_expectancy_positive": _d(metrics["mean_r"]) > 0,
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
        "mc_positive_at_least_0_90": (
            _d(mc["positive_terminal_probability"]) >= Decimal("0.90")
        ),
        "mc_p95_dd_at_most_15r": (
            _d(mc["p95_max_drawdown_r"]) <= Decimal("15")
        ),
        "degraded_0_10r_pf_gt_1": (
            _pf(cast(dict[str, object], stress["0.10"])) > Decimal("1")
        ),
    }
    return {
        "folds": folds,
        "trade_count": len(rows),
        "eligible_session_count": len(eligible_dates),
        "metrics": metrics,
        "payoff_ratio": None if payoff is None else format(payoff, "f"),
        "risk_adjusted": risk,
        "monte_carlo": mc,
        "cost_stress": stress,
        "drawdown_episode": dd,
        "gates": gates,
        "stitched_gate_pass": all(gates.values()),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--fold",
        action="append",
        type=_parse_fold,
        required=True,
    )
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    fold_map = dict(args.fold)
    if set(fold_map) != set(FOLDS) or len(args.fold) != len(FOLDS):
        raise SystemExit("exactly r5, r6, r8, consumed are required")

    payloads = {
        fold: json.loads(path.read_text(encoding="utf-8"))
        for fold, path in fold_map.items()
    }
    variant_names = tuple(
        cast(dict[str, object], payloads["r5"]["variants"]).keys()
    )
    for fold in FOLDS[1:]:
        if tuple(
            cast(dict[str, object], payloads[fold]["variants"]).keys()
        ) != variant_names:
            raise AssertionError("variant identities differ across folds")

    report = {
        name: _variant_report(name, payloads)
        for name in variant_names
    }
    result = {
        "schema": SCHEMA,
        "baseline_comparator_id": (
            "VT31_AB_COMP009_MAX_INTELLIGENCE_COMPOSED_SURVIVOR"
        ),
        "control_alias": CONTROL,
        "variants": report,
        "stitched_survivors": [
            name
            for name, item in report.items()
            if name != CONTROL
            and cast(dict[str, object], item)["stitched_gate_pass"] is True
        ],
        "control_stitched_gate_pass": cast(
            dict[str, object],
            report[CONTROL],
        )["stitched_gate_pass"],
        "governance": {
            "consumed_evidence_only": True,
            "fresh_holdout_opened": False,
            "pure_edge_only": True,
            "metric_conventions_retuned": False,
            "position_sizing_used": False,
            "dynamic_sizing_used": False,
            "leverage_used": False,
            "compounding_used": False,
            "portfolio_weighting_used": False,
            "capital_weighting_used": False,
            "candidate_frozen": False,
            "candidate_certified": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
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
