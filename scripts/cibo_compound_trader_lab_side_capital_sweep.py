#!/usr/bin/env python3
"""Trader Lab calibration sweep for protected-capital Compound reinvestment.

Preregistered research grid:
- USD60-equivalent protected-capital limits from ~1.80 through 3.00;
- LONG, SHORT and BOTH;
- baseline SHORT plus one causal SHORT hypothesis:
  STABLE regime + expected capital duration <= 30 minutes;
- CIBO_COMPOUND and COMPOUND_PORTFOLIO.

Each USD60-equivalent limit is converted into a capital-proportional ratio, so
the tested rule scales automatically with causally-known current realized
account capital. This is reused-holdout capability research only.

All failed variants remain in the artifact. No candidate trade outcome is used
at decision time, and no losing row is deleted after inspection.
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
    Decimal("1.90"),
    Decimal("2.00"),
    Decimal("2.10"),
    Decimal("2.20"),
    Decimal("2.30"),
    Decimal("2.40"),
    Decimal("2.50"),
    Decimal("2.60"),
    Decimal("2.70"),
    Decimal("2.80"),
    Decimal("2.90"),
    Decimal("3.00"),
)
SHORT_GATES: tuple[
    tuple[str, str | None, Decimal | None],
    ...,
] = (
    ("NONE", None, None),
    (
        "STABLE_EXPECTED_MINUTES_LE_30",
        "STABLE",
        Decimal("30"),
    ),
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
    short_gate_id: str,
    short_required_regime: str | None,
    short_max_expected_capital_minutes: Decimal | None,
) -> dict[str, Any]:
    ratio = usd60_limit / BASE_REFERENCE_CAPITAL_USD
    kwargs = {
        "eligible_sides": sides,
        "max_capital_need_to_current_capital_ratio": ratio,
        "short_required_regime": short_required_regime,
        "short_max_expected_capital_minutes": (
            short_max_expected_capital_minutes
        ),
    }
    local = _surface(rows, shared=False, **kwargs)
    portfolio = _surface(rows, shared=True, **kwargs)
    local_pass, local_failures = _surface_pass(local)
    portfolio_pass, portfolio_failures = _surface_pass(portfolio)
    qualified = local_pass and portfolio_pass
    return {
        "variant_id": (
            f"USD60_{_fmt(usd60_limit)}_{side_mode}_{short_gate_id}"
        ),
        "usd60_reference_limit_usd": _fmt(usd60_limit),
        "dynamic_ratio": _fmt(ratio),
        "side_mode": side_mode,
        "eligible_sides": list(sides),
        "short_gate_id": short_gate_id,
        "short_required_regime": short_required_regime,
        "short_max_expected_capital_minutes": (
            None
            if short_max_expected_capital_minutes is None
            else _fmt(short_max_expected_capital_minutes)
        ),
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
            values.append(
                _d(variant[key]["observed"]["weighted_average_roi"])
            )
    return min(values)


def _episode_density(variants: list[dict[str, Any]]) -> int:
    return sum(
        int(variant[key]["observed"]["episode_count"])
        for variant in variants
        for key in ("cibo_compound", "compound_portfolio")
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
    for usd60_limit in USD60_LIMIT_GRID:
        variants.append(
            _variant(
                rows,
                usd60_limit=usd60_limit,
                side_mode="LONG",
                sides=("long",),
                short_gate_id="NOT_APPLICABLE",
                short_required_regime=None,
                short_max_expected_capital_minutes=None,
            )
        )
        for gate_id, regime, minutes in SHORT_GATES:
            variants.append(
                _variant(
                    rows,
                    usd60_limit=usd60_limit,
                    side_mode="SHORT",
                    sides=("short",),
                    short_gate_id=gate_id,
                    short_required_regime=regime,
                    short_max_expected_capital_minutes=minutes,
                )
            )
            variants.append(
                _variant(
                    rows,
                    usd60_limit=usd60_limit,
                    side_mode="BOTH",
                    sides=("long", "short"),
                    short_gate_id=gate_id,
                    short_required_regime=regime,
                    short_max_expected_capital_minutes=minutes,
                )
            )

    candidate_groups: list[dict[str, Any]] = []
    for usd60_limit in USD60_LIMIT_GRID:
        limit_rows = [
            row
            for row in variants
            if _d(row["usd60_reference_limit_usd"]) == usd60_limit
        ]
        long_row = next(
            row for row in limit_rows if row["side_mode"] == "LONG"
        )
        for gate_id, _regime, _minutes in SHORT_GATES:
            short_row = next(
                row
                for row in limit_rows
                if row["side_mode"] == "SHORT"
                and row["short_gate_id"] == gate_id
            )
            both_row = next(
                row
                for row in limit_rows
                if row["side_mode"] == "BOTH"
                and row["short_gate_id"] == gate_id
            )
            group = [long_row, short_row, both_row]
            complete = all(row["qualified"] for row in group)
            candidate_groups.append(
                {
                    "usd60_reference_limit_usd": _fmt(usd60_limit),
                    "dynamic_ratio": _fmt(
                        usd60_limit / BASE_REFERENCE_CAPITAL_USD
                    ),
                    "short_gate_id": gate_id,
                    "long_qualified": long_row["qualified"],
                    "short_qualified": short_row["qualified"],
                    "both_qualified": both_row["qualified"],
                    "directionally_complete": complete,
                    "worst_observed_weighted_roi": (
                        _fmt(_worst_weighted_roi(group))
                        if complete
                        else None
                    ),
                    "aggregate_episode_density": (
                        _episode_density(group)
                        if complete
                        else None
                    ),
                }
            )

    eligible = [
        row
        for row in candidate_groups
        if row["directionally_complete"]
    ]
    selected = (
        max(
            eligible,
            key=lambda row: (
                _d(row["worst_observed_weighted_roi"]),
                int(row["aggregate_episode_density"]),
                -_d(row["usd60_reference_limit_usd"]),
            ),
        )
        if eligible
        else None
    )

    report = {
        "schema": "qore.cibo.compound-trader-lab-side-capital-sweep.v2",
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
            "side_modes": ["LONG", "SHORT", "BOTH"],
            "short_gate_ids": [
                gate_id for gate_id, _regime, _minutes in SHORT_GATES
            ],
            "dynamic_scaling": True,
            "ratio_formula": (
                "usd60_reference_limit / 60 * current_realized_capital"
            ),
        },
        "short_hypothesis": {
            "id": "STABLE_EXPECTED_MINUTES_LE_30",
            "causal_inputs_only": True,
            "required_regime": "STABLE",
            "max_expected_capital_minutes": "30",
            "derived_on_reused_holdout": True,
            "certification_claimed": False,
        },
        "qualification_rule": {
            "required_for_each_side_mode": [
                "CIBO_COMPOUND observed PnL > 0",
                "CIBO_COMPOUND weighted ROI > 0",
                "CIBO_COMPOUND observed protected-pool breaches = 0",
                "CIBO_COMPOUND 4/4 WFO folds positive",
                "CIBO_COMPOUND Monte Carlo median PnL > 0",
                "CIBO_COMPOUND Monte Carlo protected-pool breach paths = 0",
                "COMPOUND_PORTFOLIO same six gates",
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
        "candidate_groups": candidate_groups,
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
                "candidate_groups": candidate_groups,
            },
            sort_keys=True,
        )
    )
    if selected is None:
        raise RuntimeError(
            "no capital/short-gate candidate passed LONG, SHORT and BOTH "
            "across both Compound surfaces"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
