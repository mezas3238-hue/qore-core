#!/usr/bin/env python3
"""Trader Lab calibration sweep for protected-capital Compound reinvestment.

Preregistered research grid:
- USD60-equivalent protected-capital limits: 1.804169460064942..., 2.00, 2.50, 3.00
- side modes: LONG, SHORT, BOTH
- surfaces: CIBO_COMPOUND and COMPOUND_PORTFOLIO

Each USD60-equivalent limit is converted into a capital-proportional ratio, so
the tested rule scales automatically with causally-known current realized
account capital. This is reused-holdout calibration only, never certification.

A candidate is directionally complete only when LONG, SHORT and BOTH each pass
the same preregistered positivity gates on both Compound surfaces. All failed
variants remain in the artifact; no losing row is deleted after inspection.
"""

from __future__ import annotations

import argparse
import json
from decimal import Decimal
from pathlib import Path
from typing import Any

from cibo_compound_protected_capital_reality_exam import (
    SIMULATIONS,
    WFO_FOLDS,
    _d,
    _fmt,
    _settled_rows,
    _surface,
)
from qore.infrastructure.cibo_protected_reinvestment_policy import (
    USD60_MAX_CAPITAL_NEED_USD,
)

BASE_REFERENCE_CAPITAL_USD = Decimal("60")
USD60_LIMIT_GRID = (
    USD60_MAX_CAPITAL_NEED_USD,
    Decimal("2.00"),
    Decimal("2.50"),
    Decimal("3.00"),
)
SIDE_MODES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("LONG", ("long",)),
    ("SHORT", ("short",)),
    ("BOTH", ("long", "short")),
)


def _surface_pass(surface: dict[str, Any]) -> tuple[bool, list[str]]:
    failures: list[str] = []
    observed = surface["observed"]
    if observed.get("status") != "MEASURED":
        failures.append("NO_PROTECTED_REINVESTMENT")
        return False, failures
    if observed["episode_count"] <= 0:
        failures.append("ZERO_EPISODES")
    if _d(observed["incremental_realized_pnl_usd"]) <= 0:
        failures.append("OBSERVED_PNL_NON_POSITIVE")
    if _d(observed["weighted_average_roi"]) <= 0:
        failures.append("OBSERVED_WEIGHTED_ROI_NON_POSITIVE")

    wfo = surface["walk_forward"]
    if wfo["fold_count"] != WFO_FOLDS:
        failures.append("WFO_NOT_4_FOLDS")
    elif any(
        _d(fold["incremental_realized_pnl_usd"]) <= 0
        or _d(fold["weighted_average_roi"]) <= 0
        for fold in wfo["folds"]
    ):
        failures.append("NON_POSITIVE_WFO_FOLD")

    mc = surface["monte_carlo"]
    if mc["simulation_count"] != SIMULATIONS:
        failures.append("MONTE_CARLO_COUNT_DRIFT")
    if _d(mc["median_incremental_pnl_usd"]) <= 0:
        failures.append("MONTE_CARLO_MEDIAN_NON_POSITIVE")
    if mc["protected_pool_breach_paths"] != 0:
        failures.append("MONTE_CARLO_PROTECTED_POOL_BREACH")

    return not failures, failures


def _adverse_stress(surface: dict[str, Any]) -> list[str]:
    scenarios = surface["stress"].get("scenarios", {})
    if not isinstance(scenarios, dict):
        return ["NO_STRESS_POPULATION"]
    result: list[str] = []
    for name, row in scenarios.items():
        if (
            _d(row["incremental_pnl_usd"]) <= 0
            or bool(row["protected_pool_breach"])
        ):
            result.append(name)
    return sorted(result)


def _variant(
    rows: tuple[dict[str, Any], ...],
    *,
    usd60_limit: Decimal,
    side_mode: str,
    sides: tuple[str, ...],
) -> dict[str, Any]:
    ratio = usd60_limit / BASE_REFERENCE_CAPITAL_USD
    local = _surface(
        rows,
        shared=False,
        eligible_sides=sides,
        max_capital_need_to_current_capital_ratio=ratio,
    )
    portfolio = _surface(
        rows,
        shared=True,
        eligible_sides=sides,
        max_capital_need_to_current_capital_ratio=ratio,
    )
    local_pass, local_failures = _surface_pass(local)
    portfolio_pass, portfolio_failures = _surface_pass(portfolio)
    qualified = local_pass and portfolio_pass
    return {
        "variant_id": f"USD60_{_fmt(usd60_limit)}_{side_mode}",
        "usd60_reference_limit_usd": _fmt(usd60_limit),
        "dynamic_ratio": _fmt(ratio),
        "side_mode": side_mode,
        "eligible_sides": list(sides),
        "qualified": qualified,
        "failures": {
            "cibo_compound": local_failures,
            "compound_portfolio": portfolio_failures,
        },
        "adverse_stress": {
            "cibo_compound": _adverse_stress(local),
            "compound_portfolio": _adverse_stress(portfolio),
        },
        "cibo_compound": local,
        "compound_portfolio": portfolio,
    }


def _worst_weighted_roi(variants: list[dict[str, Any]]) -> Decimal:
    values: list[Decimal] = []
    for variant in variants:
        for key in ("cibo_compound", "compound_portfolio"):
            values.append(_d(variant[key]["observed"]["weighted_average_roi"]))
    return min(values)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--decision-trace", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    trace = json.loads(args.decision_trace.read_text(encoding="utf-8"))
    if not isinstance(trace, dict):
        raise ValueError("decision trace root must be object")
    rows = _settled_rows(trace)

    variants = [
        _variant(
            rows,
            usd60_limit=usd60_limit,
            side_mode=side_mode,
            sides=sides,
        )
        for usd60_limit in USD60_LIMIT_GRID
        for side_mode, sides in SIDE_MODES
    ]

    grouped: list[dict[str, Any]] = []
    for usd60_limit in USD60_LIMIT_GRID:
        group = [
            row
            for row in variants
            if _d(row["usd60_reference_limit_usd"]) == usd60_limit
        ]
        by_mode = {row["side_mode"]: row for row in group}
        complete = all(
            by_mode[mode]["qualified"]
            for mode, _sides in SIDE_MODES
        )
        grouped.append(
            {
                "usd60_reference_limit_usd": _fmt(usd60_limit),
                "dynamic_ratio": _fmt(
                    usd60_limit / BASE_REFERENCE_CAPITAL_USD
                ),
                "long_qualified": by_mode["LONG"]["qualified"],
                "short_qualified": by_mode["SHORT"]["qualified"],
                "both_qualified": by_mode["BOTH"]["qualified"],
                "directionally_complete": complete,
                "worst_observed_weighted_roi": (
                    _fmt(_worst_weighted_roi(group))
                    if complete
                    else None
                ),
            }
        )

    eligible = [
        row for row in grouped if row["directionally_complete"]
    ]
    selected = (
        max(
            eligible,
            key=lambda row: (
                _d(row["worst_observed_weighted_roi"]),
                -_d(row["usd60_reference_limit_usd"]),
            ),
        )
        if eligible
        else None
    )

    report = {
        "schema": "qore.cibo.compound-trader-lab-side-capital-sweep.v1",
        "source_trace_sha256": trace.get("trace_sha256"),
        "source_settled_core_rows": len(rows),
        "calibration_mode": "NON_CERTIFYING_REUSED_HOLDOUT",
        "population_gate_used": False,
        "outcome_used_at_candidate_decision": False,
        "forward_generalization_claimed": False,
        "broker_mutation": False,
        "live": False,
        "production": False,
        "real_capital": False,
        "merge_authority": False,
        "grid": {
            "usd60_reference_limits_usd": [
                _fmt(value) for value in USD60_LIMIT_GRID
            ],
            "side_modes": [name for name, _sides in SIDE_MODES],
            "dynamic_scaling": True,
            "ratio_formula": (
                "usd60_reference_limit / 60 * current_realized_capital"
            ),
        },
        "qualification_rule": {
            "required_for_each_side_mode": [
                "CIBO_COMPOUND observed PnL > 0",
                "CIBO_COMPOUND weighted ROI > 0",
                "CIBO_COMPOUND 4/4 WFO folds positive",
                "CIBO_COMPOUND Monte Carlo median PnL > 0",
                "CIBO_COMPOUND Monte Carlo protected-pool breach paths = 0",
                "COMPOUND_PORTFOLIO same five gates",
            ],
            "directionally_complete_requires": [
                "LONG qualified",
                "SHORT qualified",
                "BOTH qualified",
            ],
            "stress": (
                "measured and retained; adverse scenarios do not get deleted "
                "or cosmetically forced green"
            ),
            "strict_train_test_wfo": "OPEN_FOLLOWUP",
        },
        "limits": grouped,
        "variants": variants,
        "selected_candidate": selected,
        "gate_verdict": (
            "PASS_DIRECTIONALLY_COMPLETE"
            if selected is not None
            else "REJECT_NO_DIRECTIONALLY_COMPLETE_LIMIT"
        ),
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "gate_verdict": report["gate_verdict"],
                "limits": grouped,
                "selected_candidate": selected,
            },
            sort_keys=True,
        )
    )
    if selected is None:
        raise RuntimeError(
            "no USD60-equivalent limit passed LONG, SHORT and BOTH "
            "across both Compound surfaces"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
