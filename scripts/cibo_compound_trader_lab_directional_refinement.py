#!/usr/bin/env python3
"""Trader Lab directional refinement for protected-capital Compound.

This is a preregistered reused-holdout calibration stage built after the broad
LONG/SHORT/BOTH sweep. It tests a small causal neighborhood, not arbitrary
per-trade outcome selection.

Frozen candidate family:
- USD60-equivalent capital ceilings: 2.55, 2.60, 2.65;
- LONG: historical-prior expected net value >= -0.10 USD;
- SHORT: market entry, expected capital duration <= 45 minutes,
  historical-prior expected net value >= +0.05 USD;
- SHORT dynamic-cap utilization ceiling: 0.97, 0.98, 0.99;
- same policy tested as LONG-only, SHORT-only and BOTH;
- same policy tested on CIBO_COMPOUND and COMPOUND_PORTFOLIO.

All admission inputs are known at or before decision time. This stage grants no
certification, broker, LIVE, Production, real-capital, merge, Risk or sizing
authority.
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

BASE_REFERENCE_CAPITAL_USD = Decimal("60")
USD60_LIMITS = (Decimal("2.55"), Decimal("2.60"), Decimal("2.65"))
SHORT_UTILIZATION_CEILINGS = (
    Decimal("0.97"),
    Decimal("0.98"),
    Decimal("0.99"),
)
LONG_MIN_EXPECTED_NET_USD = Decimal("-0.10")
SHORT_MIN_EXPECTED_NET_USD = Decimal("0.05")
SHORT_MAX_EXPECTED_CAPITAL_MINUTES = Decimal("45")
SHORT_REQUIRED_ENTRY_TYPE = "market"


def _qualify(surface: dict[str, Any]) -> tuple[bool, list[str]]:
    failures: list[str] = []
    observed = surface["observed"]
    if observed.get("status") != "MEASURED":
        return False, ["NO_PROTECTED_REINVESTMENT"]
    if int(observed["episode_count"]) <= 0:
        failures.append("ZERO_EPISODES")
    if _d(observed["incremental_realized_pnl_usd"]) <= 0:
        failures.append("OBSERVED_PNL_NON_POSITIVE")
    if _d(observed["weighted_average_roi"]) <= 0:
        failures.append("OBSERVED_WEIGHTED_ROI_NON_POSITIVE")
    if int(observed["protected_pool_breach_count"]) != 0:
        failures.append("OBSERVED_PROTECTED_POOL_BREACH")

    wfo = surface["walk_forward"]
    if int(wfo["fold_count"]) != WFO_FOLDS:
        failures.append("WFO_NOT_4_FOLDS")
    elif any(
        _d(fold["incremental_realized_pnl_usd"]) <= 0
        or _d(fold["weighted_average_roi"]) <= 0
        for fold in wfo["folds"]
    ):
        failures.append("NON_POSITIVE_WFO_FOLD")

    mc = surface["monte_carlo"]
    if int(mc["simulation_count"]) != SIMULATIONS:
        failures.append("MONTE_CARLO_COUNT_DRIFT")
    if _d(mc["median_incremental_pnl_usd"]) <= 0:
        failures.append("MONTE_CARLO_MEDIAN_NON_POSITIVE")
    if int(mc["protected_pool_breach_paths"]) != 0:
        failures.append("MONTE_CARLO_PROTECTED_POOL_BREACH")
    return not failures, failures


def _stress_debt(surface: dict[str, Any]) -> list[str]:
    scenarios = surface["stress"].get("scenarios", {})
    if not isinstance(scenarios, dict):
        return ["NO_STRESS_POPULATION"]
    return sorted(
        name
        for name, row in scenarios.items()
        if _d(row["incremental_pnl_usd"]) <= 0
        or bool(row["protected_pool_breach"])
    )


def _surface_result(
    rows: tuple[dict[str, Any], ...],
    *,
    shared: bool,
    sides: tuple[str, ...],
    usd60_limit: Decimal,
    utilization: Decimal,
) -> dict[str, Any]:
    ratio = usd60_limit / BASE_REFERENCE_CAPITAL_USD
    surface = _surface(
        rows,
        shared=shared,
        eligible_sides=sides,
        max_capital_need_to_current_capital_ratio=ratio,
        long_min_expected_net_value_usd=LONG_MIN_EXPECTED_NET_USD,
        short_required_entry_type=SHORT_REQUIRED_ENTRY_TYPE,
        short_min_expected_net_value_usd=SHORT_MIN_EXPECTED_NET_USD,
        short_max_expected_capital_minutes=(
            SHORT_MAX_EXPECTED_CAPITAL_MINUTES
        ),
        short_max_dynamic_limit_utilization=utilization,
    )
    qualified, failures = _qualify(surface)
    return {
        "qualified": qualified,
        "failures": failures,
        "stress_debt": _stress_debt(surface),
        "surface": surface,
    }


def _candidate(
    rows: tuple[dict[str, Any], ...],
    *,
    usd60_limit: Decimal,
    utilization: Decimal,
) -> dict[str, Any]:
    modes = {
        "LONG": ("long",),
        "SHORT": ("short",),
        "BOTH": ("long", "short"),
    }
    results: dict[str, Any] = {}
    for mode, sides in modes.items():
        results[mode] = {
            "cibo_compound": _surface_result(
                rows,
                shared=False,
                sides=sides,
                usd60_limit=usd60_limit,
                utilization=utilization,
            ),
            "compound_portfolio": _surface_result(
                rows,
                shared=True,
                sides=sides,
                usd60_limit=usd60_limit,
                utilization=utilization,
            ),
        }
    all_six = [
        results[mode][surface]["qualified"]
        for mode in modes
        for surface in ("cibo_compound", "compound_portfolio")
    ]
    return {
        "candidate_id": (
            f"USD60_{_fmt(usd60_limit)}_SHORT_UTIL_{_fmt(utilization)}"
        ),
        "usd60_reference_limit_usd": _fmt(usd60_limit),
        "dynamic_ratio": _fmt(
            usd60_limit / BASE_REFERENCE_CAPITAL_USD
        ),
        "short_dynamic_limit_utilization_ceiling": _fmt(utilization),
        "directionally_complete": all(all_six),
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--decision-trace", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    trace = json.loads(args.decision_trace.read_text(encoding="utf-8"))
    if not isinstance(trace, dict):
        raise ValueError("decision trace root must be object")
    rows = _settled_rows(trace)

    candidates = [
        _candidate(
            rows,
            usd60_limit=limit,
            utilization=utilization,
        )
        for limit in USD60_LIMITS
        for utilization in SHORT_UTILIZATION_CEILINGS
    ]
    qualified = [
        item for item in candidates if item["directionally_complete"]
    ]
    # Outcome-independent tie-break: prefer less protected capital first,
    # then the tighter SHORT utilization ceiling.
    selected = (
        min(
            qualified,
            key=lambda item: (
                _d(item["usd60_reference_limit_usd"]),
                _d(item["short_dynamic_limit_utilization_ceiling"]),
            ),
        )
        if qualified
        else None
    )

    report = {
        "schema": "qore.cibo.compound-directional-refinement.v1",
        "source_trace_sha256": trace.get("trace_sha256"),
        "source_settled_core_rows": len(rows),
        "calibration_mode": "NON_CERTIFYING_REUSED_HOLDOUT",
        "preregistered_candidate_family": {
            "usd60_reference_limits_usd": [
                _fmt(value) for value in USD60_LIMITS
            ],
            "short_dynamic_limit_utilization_ceilings": [
                _fmt(value) for value in SHORT_UTILIZATION_CEILINGS
            ],
            "long_min_expected_net_value_usd": _fmt(
                LONG_MIN_EXPECTED_NET_USD
            ),
            "short_required_entry_type": SHORT_REQUIRED_ENTRY_TYPE,
            "short_min_expected_net_value_usd": _fmt(
                SHORT_MIN_EXPECTED_NET_USD
            ),
            "short_max_expected_capital_minutes": _fmt(
                SHORT_MAX_EXPECTED_CAPITAL_MINUTES
            ),
        },
        "governance": {
            "population_gate_used": False,
            "function_availability_conditioned_on_population": False,
            "outcome_used_at_candidate_decision": False,
            "future_market_used_at_candidate_decision": False,
            "forward_generalization_claimed": False,
            "reused_holdout_calibration": True,
            "strict_train_test_wfo_status": "OPEN_FOLLOWUP",
            "broker_mutation": False,
            "orders": False,
            "live": False,
            "production": False,
            "real_capital": False,
            "certification_claimed": False,
            "merge_authority": False,
        },
        "qualification_rule": {
            "required_for_each_of_six_surfaces": [
                "observed incremental PnL > 0",
                "observed weighted ROI > 0",
                "observed protected-pool breaches = 0",
                "4/4 chronological WFO measurement folds positive",
                "Monte Carlo simulation count = 1000",
                "Monte Carlo median incremental PnL > 0",
                "Monte Carlo protected-pool breach paths = 0",
            ],
            "stress_is_reported_not_hidden": True,
            "selection_tiebreak": (
                "minimum passing USD60-equivalent limit, then tightest "
                "passing SHORT dynamic-limit utilization ceiling"
            ),
        },
        "candidates": candidates,
        "selected_candidate": selected,
        "gate_verdict": (
            "PASS_DIRECTIONALLY_COMPLETE"
            if selected is not None
            else "REJECT_NO_DIRECTIONALLY_COMPLETE_CANDIDATE"
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
                "qualified_candidate_ids": [
                    item["candidate_id"] for item in qualified
                ],
                "selected_candidate_id": (
                    None
                    if selected is None
                    else selected["candidate_id"]
                ),
            },
            sort_keys=True,
        )
    )
    if selected is None:
        raise RuntimeError(
            "directional refinement produced no fully qualified candidate"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
