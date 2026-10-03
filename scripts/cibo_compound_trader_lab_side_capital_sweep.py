#!/usr/bin/env python3
"""Deep Trader Lab sweep for CIBO protected-capital Compound research.

This reused-holdout laboratory deliberately keeps every tested variant visible.
It tests a small preregistered family around the capital region that survived
the first broad sweep, plus the frozen ~USD1.80 and USD3.00 anchors.

The object under test is CIBO:
- LONG-only protected reinvestment;
- SHORT-only protected reinvestment;
- LONG+SHORT competing for the same protected-capital mechanics;
- local CIBO_COMPOUND and account-wide COMPOUND_PORTFOLIO.

All admission fields are causally available before the candidate outcome.
This is NON_CERTIFYING_REUSED_HOLDOUT research, not fresh OOS evidence.
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
LEGACY_V1_USD60_REFERENCE_LIMIT_USD = Decimal(
    "1.80416946006494203648874011988"
)
USD60_LIMIT_GRID = (
    LEGACY_V1_USD60_REFERENCE_LIMIT_USD,
    Decimal("2.40"),
    Decimal("2.50"),
    Decimal("2.55"),
    Decimal("2.60"),
    Decimal("2.65"),
    Decimal("2.70"),
    Decimal("3.00"),
)

LONG_GATES: tuple[dict[str, Any], ...] = (
    {
        "id": "NONE",
        "required_regime": None,
        "required_entry_type": None,
        "min_expected_net_value_usd": None,
        "max_expected_capital_minutes": None,
        "max_dynamic_limit_utilization": None,
    },
    {
        "id": "EV_GE_NEG_0075",
        "required_regime": None,
        "required_entry_type": None,
        "min_expected_net_value_usd": Decimal("-0.075"),
        "max_expected_capital_minutes": None,
        "max_dynamic_limit_utilization": None,
    },
    {
        "id": "MARKET_EV_GE_NEG_0075_MINUTES_LE_55",
        "required_regime": None,
        "required_entry_type": "market",
        "min_expected_net_value_usd": Decimal("-0.075"),
        "max_expected_capital_minutes": Decimal("55"),
        "max_dynamic_limit_utilization": None,
    },
    {
        "id": "MARKET_EV_GE_NEG_0075_MINUTES_LE_55_UTIL_LE_080",
        "required_regime": None,
        "required_entry_type": "market",
        "min_expected_net_value_usd": Decimal("-0.075"),
        "max_expected_capital_minutes": Decimal("55"),
        "max_dynamic_limit_utilization": Decimal("0.80"),
    },
    {
        "id": "MARKET_EV_GE_0_MINUTES_LE_55_UTIL_LE_080",
        "required_regime": None,
        "required_entry_type": "market",
        "min_expected_net_value_usd": Decimal("0"),
        "max_expected_capital_minutes": Decimal("55"),
        "max_dynamic_limit_utilization": Decimal("0.80"),
    },
)

SHORT_GATES: tuple[dict[str, Any], ...] = (
    {
        "id": "NONE",
        "required_regime": None,
        "required_entry_type": None,
        "min_expected_net_value_usd": None,
        "max_expected_capital_minutes": None,
        "max_dynamic_limit_utilization": None,
    },
    {
        "id": "STABLE_MINUTES_LE_30",
        "required_regime": "STABLE",
        "required_entry_type": None,
        "min_expected_net_value_usd": None,
        "max_expected_capital_minutes": Decimal("30"),
        "max_dynamic_limit_utilization": None,
    },
    {
        "id": "MARKET_EV_GE_0045_MINUTES_LE_45",
        "required_regime": None,
        "required_entry_type": "market",
        "min_expected_net_value_usd": Decimal("0.045"),
        "max_expected_capital_minutes": Decimal("45"),
        "max_dynamic_limit_utilization": None,
    },
    {
        "id": "MARKET_EV_GE_0045_MINUTES_LE_45_UTIL_LE_085",
        "required_regime": None,
        "required_entry_type": "market",
        "min_expected_net_value_usd": Decimal("0.045"),
        "max_expected_capital_minutes": Decimal("45"),
        "max_dynamic_limit_utilization": Decimal("0.85"),
    },
    {
        "id": "MARKET_EV_GE_0050_MINUTES_LE_45",
        "required_regime": None,
        "required_entry_type": "market",
        "min_expected_net_value_usd": Decimal("0.05"),
        "max_expected_capital_minutes": Decimal("45"),
        "max_dynamic_limit_utilization": None,
    },
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
    if observed["protected_pool_breach_count"] != 0:
        failures.append("OBSERVED_PROTECTED_POOL_BREACH")

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
    if _d(mc["p05_incremental_pnl_usd"]) <= 0:
        failures.append("MONTE_CARLO_P05_NON_POSITIVE")
    if mc["protected_pool_breach_paths"] != 0:
        failures.append("MONTE_CARLO_PROTECTED_POOL_BREACH")

    stress = surface["stress"]
    for scenario_name, scenario in stress.get("scenarios", {}).items():
        if bool(scenario["protected_pool_breach"]):
            failures.append(
                f"STRESS_{scenario_name}_PROTECTED_POOL_BREACH"
            )
        if (
            scenario_name != "WINNER_DROUGHT"
            and _d(scenario["incremental_pnl_usd"]) <= 0
        ):
            failures.append(f"STRESS_{scenario_name}_PNL_NON_POSITIVE")
    return not failures, failures


def _adverse_stress(surface: dict[str, Any]) -> list[str]:
    scenarios = surface["stress"].get("scenarios", {})
    if not isinstance(scenarios, dict):
        return ["NO_STRESS_POPULATION"]
    return sorted(
        name
        for name, row in scenarios.items()
        if (
            _d(row["incremental_pnl_usd"]) <= 0
            or bool(row["protected_pool_breach"])
        )
    )


def _kwargs(
    *,
    sides: tuple[str, ...],
    ratio: Decimal,
    long_gate: dict[str, Any],
    short_gate: dict[str, Any],
) -> dict[str, Any]:
    return {
        "eligible_sides": sides,
        "max_capital_need_to_current_capital_ratio": ratio,
        "long_required_regime": long_gate["required_regime"],
        "long_required_entry_type": long_gate["required_entry_type"],
        "long_min_expected_net_value_usd": (
            long_gate["min_expected_net_value_usd"]
        ),
        "long_max_expected_capital_minutes": (
            long_gate["max_expected_capital_minutes"]
        ),
        "long_max_dynamic_limit_utilization": (
            long_gate["max_dynamic_limit_utilization"]
        ),
        "short_required_regime": short_gate["required_regime"],
        "short_required_entry_type": short_gate["required_entry_type"],
        "short_min_expected_net_value_usd": (
            short_gate["min_expected_net_value_usd"]
        ),
        "short_max_expected_capital_minutes": (
            short_gate["max_expected_capital_minutes"]
        ),
        "short_max_dynamic_limit_utilization": (
            short_gate["max_dynamic_limit_utilization"]
        ),
    }


def _variant(
    rows: tuple[dict[str, Any], ...],
    *,
    usd60_limit: Decimal,
    side_mode: str,
    sides: tuple[str, ...],
    long_gate: dict[str, Any],
    short_gate: dict[str, Any],
) -> dict[str, Any]:
    ratio = usd60_limit / BASE_REFERENCE_CAPITAL_USD
    kwargs = _kwargs(
        sides=sides,
        ratio=ratio,
        long_gate=long_gate,
        short_gate=short_gate,
    )
    local = _surface(rows, shared=False, **kwargs)
    portfolio = _surface(rows, shared=True, **kwargs)
    local_pass, local_failures = _surface_pass(local)
    portfolio_pass, portfolio_failures = _surface_pass(portfolio)
    return {
        "variant_id": (
            f"USD60_{_fmt(usd60_limit)}_{side_mode}_"
            f"L_{long_gate['id']}_S_{short_gate['id']}"
        ),
        "usd60_reference_limit_usd": _fmt(usd60_limit),
        "dynamic_ratio": _fmt(ratio),
        "side_mode": side_mode,
        "eligible_sides": list(sides),
        "long_gate_id": long_gate["id"],
        "short_gate_id": short_gate["id"],
        "long_gate": {
            key: (
                _fmt(value)
                if isinstance(value, Decimal)
                else value
            )
            for key, value in long_gate.items()
        },
        "short_gate": {
            key: (
                _fmt(value)
                if isinstance(value, Decimal)
                else value
            )
            for key, value in short_gate.items()
        },
        "qualified": local_pass and portfolio_pass,
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


def _group_key(
    usd60_limit: Decimal,
    long_gate: dict[str, Any],
    short_gate: dict[str, Any],
) -> tuple[str, str, str]:
    return (
        _fmt(usd60_limit),
        str(long_gate["id"]),
        str(short_gate["id"]),
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--decision-trace", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    trace = json.loads(args.decision_trace.read_text(encoding="utf-8"))
    if not isinstance(trace, dict):
        raise ValueError("decision trace root must be object")
    rows = _settled_rows(trace)

    variants: list[dict[str, Any]] = []
    groups: list[dict[str, Any]] = []

    for usd60_limit in USD60_LIMIT_GRID:
        for long_gate in LONG_GATES:
            for short_gate in SHORT_GATES:
                long_row = _variant(
                    rows,
                    usd60_limit=usd60_limit,
                    side_mode="LONG",
                    sides=("long",),
                    long_gate=long_gate,
                    short_gate=SHORT_GATES[0],
                )
                short_row = _variant(
                    rows,
                    usd60_limit=usd60_limit,
                    side_mode="SHORT",
                    sides=("short",),
                    long_gate=LONG_GATES[0],
                    short_gate=short_gate,
                )
                both_row = _variant(
                    rows,
                    usd60_limit=usd60_limit,
                    side_mode="BOTH",
                    sides=("long", "short"),
                    long_gate=long_gate,
                    short_gate=short_gate,
                )
                variants.extend((long_row, short_row, both_row))
                complete = all(
                    row["qualified"]
                    for row in (long_row, short_row, both_row)
                )
                groups.append(
                    {
                        "group_key": list(
                            _group_key(
                                usd60_limit,
                                long_gate,
                                short_gate,
                            )
                        ),
                        "usd60_reference_limit_usd": _fmt(usd60_limit),
                        "dynamic_ratio": _fmt(
                            usd60_limit / BASE_REFERENCE_CAPITAL_USD
                        ),
                        "long_gate_id": long_gate["id"],
                        "short_gate_id": short_gate["id"],
                        "long_qualified": long_row["qualified"],
                        "short_qualified": short_row["qualified"],
                        "both_qualified": both_row["qualified"],
                        "directionally_complete": complete,
                        "aggregate_episode_density": (
                            sum(
                                int(row[surface]["observed"]["episode_count"])
                                for row in (long_row, short_row, both_row)
                                for surface in (
                                    "cibo_compound",
                                    "compound_portfolio",
                                )
                            )
                            if complete
                            else None
                        ),
                    }
                )

    qualified = [
        row for row in groups if row["directionally_complete"]
    ]
    # Selection is conservative and deterministic: first qualifying candidate in
    # the preregistered grid. It is not ranked by realized PnL or ROI.
    selected = qualified[0] if qualified else None

    report = {
        "schema": "qore.cibo.compound-trader-lab-side-capital-sweep.v4",
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
            "long_gate_ids": [row["id"] for row in LONG_GATES],
            "short_gate_ids": [row["id"] for row in SHORT_GATES],
            "side_modes": ["LONG", "SHORT", "BOTH"],
            "dynamic_scaling": True,
            "ratio_formula": (
                "usd60_reference_limit / 60 * current_realized_capital"
            ),
            "selection_rule": (
                "FIRST_QUALIFYING_PREREGISTERED_CANDIDATE_NOT_PNL_RANKED"
            ),
            "legacy_v1_reference_limit_usd": _fmt(
                LEGACY_V1_USD60_REFERENCE_LIMIT_USD
            ),
            "frozen_v2_reference_limit_usd": "2.40",
        },
        "hypothesis_governance": {
            "all_gate_inputs_are_predecision": True,
            "candidate_family_derived_on_reused_holdout": True,
            "failed_variants_retained": True,
            "fresh_oos_claimed": False,
            "certification_claimed": False,
        },
        "qualification_rule": {
            "each_of_long_short_both_requires": [
                "CIBO_COMPOUND observed PnL > 0",
                "CIBO_COMPOUND weighted ROI > 0",
                "CIBO_COMPOUND observed protected-pool breaches = 0",
                "CIBO_COMPOUND 4/4 chronological folds positive",
                "CIBO_COMPOUND Monte Carlo median PnL > 0",
                "CIBO_COMPOUND Monte Carlo p05 PnL > 0",
                "CIBO_COMPOUND Monte Carlo protected-pool breach paths = 0",
                "all stresses except WINNER_DROUGHT PnL > 0",
                "all stresses including WINNER_DROUGHT protected-pool breaches = 0",
                "COMPOUND_PORTFOLIO same robustness gates",
            ],
            "winner_drought_interpretation": (
                "SURVIVAL_STRESS_NO_POSITIVE_PNL_REQUIREMENT"
            ),
            "strict_train_test_roll": "OPEN_FOLLOWUP",
        },
        "candidate_groups": groups,
        "qualified_candidates": qualified,
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
                "selected_candidate": selected,
                "qualified_candidate_count": len(qualified),
            },
            sort_keys=True,
        )
    )
    if selected is None:
        raise RuntimeError(
            "no preregistered capital/side-gate candidate passed LONG, "
            "SHORT and BOTH across both Compound surfaces"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
