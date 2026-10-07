#!/usr/bin/env python3
"""Adjudicate VT31 on one owner-designated three-year base only."""
from __future__ import annotations

import argparse
import json
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_nas100_comp009_final_preholdout_metric_pack_v1 as pack
import vt31_nas100_specialist_r1_candidate as specialist

SCHEMA = "qore.vt31.nas100.owner_3y_adjudication.v1"
BASE_ID = "VT31_NAS100_OWNER_3Y_BASE_001"
TARGET_TRADES = 450
REASONABLE_DENSITY_FLOOR = 400


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _pf(metrics: dict[str, object]) -> Decimal:
    value = metrics.get("profit_factor")
    if value is None:
        wins = int(metrics["wins"])
        losses = int(metrics["losses"])
        if wins > 0 and losses == 0:
            return Decimal("Infinity")
        return Decimal("-Infinity")
    return _d(value)


def _daily_series(
    rows: list[dict[str, object]],
    eligible_dates: list[str],
) -> list[dict[str, str]]:
    totals = {day: Decimal(0) for day in eligible_dates}
    for row in rows:
        day = str(row["local_date"])
        if day not in totals:
            raise AssertionError(f"trade {row['signal_at']} outside eligible day")
        totals[day] += _d(row["r_multiple"]) - pack.BASELINE_FRICTION_R
    return [
        {"local_date": day, "daily_r": format(totals[day], "f")}
        for day in eligible_dates
    ]


def _variant_report(
    item: dict[str, object],
) -> dict[str, object]:
    rows = cast(list[dict[str, object]], item["candidate_rows"])
    rows = sorted(rows, key=lambda row: str(row["signal_at"]))
    eligible_dates = sorted(cast(list[str], item["eligible_dates"]))

    metrics = specialist._metrics(rows, friction=pack.BASELINE_FRICTION_R)
    payoff = pack._payoff(rows, pack.BASELINE_FRICTION_R)
    risk = pack._risk_adjusted(_daily_series(rows, eligible_dates))
    mc = specialist._monte_carlo(rows)
    stress = pack._cost_stress(rows)
    dd = pack._drawdown_episode(rows, pack.BASELINE_FRICTION_R)

    trade_count = len(rows)
    gates = {
        "reasonable_density_at_least_400_trades": (
            trade_count >= REASONABLE_DENSITY_FLOOR
        ),
        "observed_dd_at_most_6r": (
            _d(dd["max_drawdown_r"]) <= Decimal("6")
        ),
        "pf_at_least_1_50": _pf(metrics) >= Decimal("1.50"),
        "expectancy_at_least_0_15r": (
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
        "trade_count": trade_count,
        "target_trades_3y": TARGET_TRADES,
        "gap_to_450": TARGET_TRADES - trade_count,
        "eligible_session_count": len(eligible_dates),
        "metrics": metrics,
        "payoff_ratio": None if payoff is None else format(payoff, "f"),
        "risk_adjusted": risk,
        "monte_carlo": mc,
        "cost_stress": stress,
        "drawdown_episode": dd,
        "gates": gates,
        "certification_gate_pass": all(gates.values()),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("replay", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    payload = json.loads(args.replay.read_text(encoding="utf-8"))
    if payload.get("base_id") != BASE_ID:
        raise SystemExit("unexpected 3Y base identity")
    if cast(dict[str, object], payload["governance"])[
        "legacy_r5_r6_r8_operating_folds_used"
    ] is not False:
        raise SystemExit("legacy folds are forbidden in 3Y adjudication")

    stack = cast(dict[str, object], payload["current_stack"])
    variants = cast(dict[str, dict[str, object]], stack["variants"])
    control_name = str(stack["lab_control_alias"])
    reports = {
        name: _variant_report(item)
        for name, item in variants.items()
    }
    result = {
        "schema": SCHEMA,
        "base_id": BASE_ID,
        "window": payload["window"],
        "control_alias": control_name,
        "variants": reports,
        "survivors": [
            name
            for name, report in reports.items()
            if report["certification_gate_pass"] is True
        ],
        "control_certification_gate_pass": reports[control_name][
            "certification_gate_pass"
        ],
        "density": payload["density"],
        "governance": {
            "single_contiguous_3y_base": True,
            "legacy_r5_r6_r8_operating_folds_used": False,
            "pure_edge_only": True,
            "position_sizing_used": False,
            "dynamic_sizing_used": False,
            "leverage_used": False,
            "compounding_used": False,
            "portfolio_weighting_used": False,
            "capital_weighting_used": False,
            "fresh_independent_holdout_claimed": False,
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
