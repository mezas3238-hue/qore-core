"""VT08 Index R51 — frozen allocator concentration robustness.

R51 does not retune R47. It stress-tests the exact R47 candidate frozen by R48
for economic concentration and parameter-neighborhood fragility.

The Owner's secondary economic threshold (PF >= 1.30 at -0.10R/trade) is reused
as the acceptance floor under a pre-registered maximum-weight compression to
0.25R. A second robustness check removes the three largest winning
contributions from each consumed window. These are diagnostics of dependence on
rare large allocations, not runtime changes and not fresh holdout evidence.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import vt08_index_r6_5y_failure_forensics as fx
from qore.infrastructure.trader_lab import vt08_index_r15_concurrent_portfolio_validation as r15
from qore.infrastructure.trader_lab import (
    vt08_index_r31_source_complete_structural_concurrency as r31,
)
from qore.infrastructure.trader_lab import vt08_index_r34_hybrid_formation_poi_health as r34
from qore.infrastructure.trader_lab import vt08_index_r43_sp500_long_stability_prior as r43
from qore.infrastructure.trader_lab import (
    vt08_index_r45_frozen_recent_2y_reproduction as r45,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r47_transport_safe_structural_demotion as r47,
)
from qore.infrastructure.trader_lab import vt08_index_r48_candidate_freeze as freeze
from qore.infrastructure.traders.vt08_index_c2_positional_r1 import Vt08IndexC2R1Bar

# Quality rebind after shared lint repair.
SCHEMA = "qore.trader_lab.vt08_index_r51_concentration_robustness.v1"
IDENTITY = "VT08_INDEX_R51_R47_CONCENTRATION_ROBUSTNESS_001"
SECONDARY_STRESS = Decimal("0.10")
PF_FLOOR = Decimal("1.30")
MAX_WEIGHT_NEIGHBORHOOD = Decimal("0.25")
ADDITIONAL_CAPS = (Decimal("0.10"), Decimal("0.05"))
TOP_WINNER_REMOVAL_COUNT = 3
FLOOR_WEIGHT = Decimal("0.005")


def _ordered(
    assigned: Sequence[r15.AssignedTrade],
) -> tuple[r15.AssignedTrade, ...]:
    return tuple(
        sorted(
            assigned,
            key=lambda item: (item.exited_at, item.symbol, item.trade_id),
        )
    )


def _values(
    assigned: Sequence[r15.AssignedTrade],
    *,
    cap: Decimal | None = None,
) -> tuple[Decimal, ...]:
    values: list[Decimal] = []
    for item in _ordered(assigned):
        weight = min(item.weight, cap) if cap is not None else item.weight
        values.append((item.outcome.r_multiple - SECONDARY_STRESS) * weight)
    return tuple(values)


def _concentration(
    assigned: Sequence[r15.AssignedTrade],
) -> dict[str, Any]:
    ordered = _ordered(assigned)
    rows: list[dict[str, Any]] = [
        {
            "trade_id": item.trade_id,
            "weight": item.weight,
            "value": (item.outcome.r_multiple - SECONDARY_STRESS) * item.weight,
        }
        for item in ordered
    ]
    total_weight = sum((row["weight"] for row in rows), Decimal())
    floor_rows = [row for row in rows if row["weight"] == FLOOR_WEIGHT]
    nonfloor_rows = [row for row in rows if row["weight"] > FLOOR_WEIGHT]
    positive_rows = sorted(
        (row for row in rows if row["value"] > 0),
        key=lambda row: row["value"],
        reverse=True,
    )
    total_r = sum((row["value"] for row in rows), Decimal())
    top_one = positive_rows[0]["value"] if positive_rows else Decimal()
    top_three = sum(
        (row["value"] for row in positive_rows[:TOP_WINNER_REMOVAL_COUNT]),
        Decimal(),
    )
    hhi = (
        sum((row["weight"] / total_weight) ** 2 for row in rows)
        if total_weight > 0
        else Decimal()
    )
    effective_risk_breadth = Decimal(1) / hhi if hhi > 0 else Decimal()

    removed_ids = {
        int(row["trade_id"])
        for row in positive_rows[:TOP_WINNER_REMOVAL_COUNT]
    }
    leave_top_three_out = tuple(
        row["value"]
        for row in rows
        if int(row["trade_id"]) not in removed_ids
    )
    leave_metrics = fx._metrics(leave_top_three_out)

    return {
        "trade_count": len(rows),
        "floor_trade_count": len(floor_rows),
        "nonfloor_trade_count": len(nonfloor_rows),
        "floor_trade_fraction": str(
            Decimal(len(floor_rows)) / Decimal(len(rows))
        ),
        "total_effective_weight_r": str(total_weight),
        "floor_contribution_r": str(
            sum((row["value"] for row in floor_rows), Decimal())
        ),
        "nonfloor_contribution_r": str(
            sum((row["value"] for row in nonfloor_rows), Decimal())
        ),
        "top_one_winner_contribution_r": str(top_one),
        "top_three_winner_contribution_r": str(top_three),
        "top_one_fraction_of_terminal_r": (
            str(top_one / total_r) if total_r != 0 else "NA"
        ),
        "top_three_fraction_of_terminal_r": (
            str(top_three / total_r) if total_r != 0 else "NA"
        ),
        "weight_hhi": str(hhi),
        "effective_risk_breadth": str(effective_risk_breadth),
        "leave_top_three_winners_out": leave_metrics,
        "leave_top_three_terminal_positive": (
            Decimal(str(leave_metrics["total_r"])) > 0
        ),
    }


def _cap_neighborhood(
    assigned: Sequence[r15.AssignedTrade],
) -> dict[str, Any]:
    caps = (MAX_WEIGHT_NEIGHBORHOOD, *ADDITIONAL_CAPS)
    result: dict[str, Any] = {}
    for cap in caps:
        metrics = fx._metrics(_values(assigned, cap=cap))
        result[str(cap)] = {
            **metrics,
            "pf_meets_secondary_floor": (
                Decimal(str(metrics["profit_factor"])) >= PF_FLOOR
            ),
            "terminal_positive": Decimal(str(metrics["total_r"])) > 0,
        }
    return result


def _window(
    *,
    stream: Sequence[Any],
    bars_by_symbol: dict[str, Sequence[Vt08IndexC2R1Bar]],
) -> dict[str, Any]:
    _base_row, baseline = r34._row(stream, overlay=r43.BASE_POI_OVERLAY)
    assigned, diagnostics = r47._apply_transport_rules(
        baseline,
        bars_by_symbol=bars_by_symbol,
    )
    concentration = _concentration(assigned)
    neighborhood = _cap_neighborhood(assigned)
    hard_cap = neighborhood[str(MAX_WEIGHT_NEIGHBORHOOD)]
    pass_gate = (
        bool(hard_cap["pf_meets_secondary_floor"])
        and bool(hard_cap["terminal_positive"])
        and bool(concentration["leave_top_three_terminal_positive"])
    )
    return {
        "sample": len(assigned),
        "exact_secondary": fx._metrics(_values(assigned)),
        "concentration": concentration,
        "max_weight_cap_neighborhood": neighborhood,
        "diagnostics": diagnostics,
        "window_pass": pass_gate,
    }


def build_report(
    *,
    nas100_root: Path,
    sp500_root: Path,
    us30_root: Path,
) -> dict[str, Any]:
    if not freeze.dependency_contract_matches():
        raise ValueError("R51 R48 freeze dependency drift")
    if r47.RULE_FINGERPRINT != freeze.CANDIDATE_RULE_FINGERPRINT:
        raise ValueError("R51 candidate fingerprint drift")

    roots = {
        "NAS100": nas100_root,
        "SP500": sp500_root,
        "US30": us30_root,
    }
    five_stream, five_bars, _five_opened, five_provenance = (
        r31._build_source_complete_stream(roots=roots)
    )
    two_stream, two_bars, _two_opened, two_provenance = (
        r45._build_source_complete_stream_2y(roots=roots)
    )
    five = _window(
        stream=five_stream,
        bars_by_symbol={key: tuple(value) for key, value in five_bars.items()},
    )
    two = _window(
        stream=two_stream,
        bars_by_symbol={key: tuple(value) for key, value in two_bars.items()},
    )

    exact_reproduction = (
        five["sample"] == freeze.FIVE_YEAR["sample"]
        and two["sample"] == freeze.RECENT_TWO_YEAR["sample"]
        and str(five["exact_secondary"]["profit_factor"])
        == freeze.FIVE_YEAR["secondary_pf"]
        and str(two["exact_secondary"]["profit_factor"])
        == freeze.RECENT_TWO_YEAR["secondary_pf"]
    )
    hard_gate = exact_reproduction and five["window_pass"] and two["window_pass"]

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "candidate": {
            "candidate_id": freeze.CANDIDATE_ID,
            "candidate_rule_fingerprint": freeze.CANDIDATE_RULE_FINGERPRINT,
            "freeze_id": freeze.FREEZE_ID,
            "rules_changed": False,
            "retuning_performed": False,
        },
        "preregistered_stress": {
            "secondary_stress_r_per_trade": str(SECONDARY_STRESS),
            "secondary_pf_floor": str(PF_FLOOR),
            "maximum_weight_neighborhood_r": str(MAX_WEIGHT_NEIGHBORHOOD),
            "additional_descriptive_caps_r": [
                str(value) for value in ADDITIONAL_CAPS
            ],
            "top_winner_removal_count": TOP_WINNER_REMOVAL_COUNT,
        },
        "five_year": five,
        "recent_two_year": two,
        "exact_frozen_reproduction": exact_reproduction,
        "concentration_robustness_pass": hard_gate,
        "decision": (
            "PASS_R51_CONCENTRATION_ROBUSTNESS"
            if hard_gate
            else "FAIL_R51_CONCENTRATION_ROBUSTNESS"
        ),
        "provenance": {
            "five_year": five_provenance,
            "recent_two_year": two_provenance,
        },
        "governance": {
            "candidate_frozen": True,
            "runtime_rules_changed": False,
            "retuning_performed": False,
            "parameter_neighborhood_is_stress_only": True,
            "fresh_holdout_claim": False,
            "certified": False,
            "demo_eligible": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--nas100-root", type=Path, required=True)
    parser.add_argument("--sp500-root", type=Path, required=True)
    parser.add_argument("--us30-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    report = build_report(
        nas100_root=args.nas100_root,
        sp500_root=args.sp500_root,
        us30_root=args.us30_root,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "identity": IDENTITY,
                "five_year": report["five_year"],
                "recent_two_year": report["recent_two_year"],
                "exact_frozen_reproduction": report["exact_frozen_reproduction"],
                "concentration_robustness_pass": report[
                    "concentration_robustness_pass"
                ],
                "decision": report["decision"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
