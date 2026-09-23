"""R2-BF AUDUSD profit-factor loss attribution.

This lab does not change any trade. It attributes the thin PF of the 15Y
high-density AUDUSD populations to observable cohorts.

Populations come directly from R2-BE:
- CONTROL_BE075
- OVERLAP_CANDIDATE

Dimensions:
- exit reason / stop subtype;
- direction;
- rolling H4 timing slot;
- source->confirmation delay in M15 bars;
- reference multiplicity;
- annual regime.

The report also computes break-even friction per trade (mean R/trade), because
any all-in execution cost above that level eliminates the observed expectancy.

Attribution dimensions overlap and MUST NOT be interpreted as additive causal
effects. No filter is promoted here.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from collections.abc import Callable
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.vt08_crt_pure_r2_model1_reference_lab import (
    Model1LabTrade,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2be_audusd_candidate_robustness import (
    END,
    START,
    build_populations,
)

IDENTITY = "VT08_CRT_PURE_R2BF_AUDUSD_PF_LOSS_ATTRIBUTION_001"
SCHEMA = "qore.vt08.crt_pure.r2bf_audusd_pf_loss_attribution.v1"


def _metrics(rows: tuple[Model1LabTrade, ...]) -> dict[str, Any]:
    values = [float(row.r_multiple) for row in rows]
    gross_profit = sum(value for value in values if value > 0)
    gross_loss = -sum(value for value in values if value < 0)
    total = sum(values)
    return {
        "trades": len(rows),
        "gross_profit_r": round(gross_profit, 8),
        "gross_loss_r": round(gross_loss, 8),
        "total_r": round(total, 8),
        "mean_r": None if not rows else round(total / len(rows), 8),
        "profit_factor": (
            None
            if gross_loss <= 0
            else round(gross_profit / gross_loss, 8)
        ),
        "wins": sum(value > 0 for value in values),
        "losses": sum(value < 0 for value in values),
        "flat": sum(value == 0 for value in values),
        "break_even_friction_r_per_trade": (
            None if not rows else round(total / len(rows), 8)
        ),
    }


def _group(
    rows: tuple[Model1LabTrade, ...],
    key: Callable[[Model1LabTrade], str],
) -> dict[str, dict[str, Any]]:
    groups: dict[str, list[Model1LabTrade]] = defaultdict(list)
    for row in rows:
        groups[key(row)].append(row)
    return {
        label: _metrics(tuple(group))
        for label, group in sorted(groups.items())
    }


def _stop_subtype(row: Model1LabTrade) -> str:
    if row.exit_reason != "STOP":
        return row.exit_reason
    value = float(row.r_multiple)
    if abs(value + 1.0) <= 1e-9:
        return "ORIGINAL_STOP_MINUS_1R"
    if abs(value) <= 1e-9:
        return "BE_STOP_0R"
    return "OTHER_IMPROVED_STOP"


def _delay_bars(row: Model1LabTrade) -> str:
    source = datetime.fromisoformat(row.source_opened_at)
    confirmation = datetime.fromisoformat(row.confirmation_opened_at)
    bars = round((confirmation - source).total_seconds() / (15 * 60))
    return f"D{bars}"


def _reference_bucket(row: Model1LabTrade) -> str:
    if row.reference_count == 1:
        return "REF1"
    if row.reference_count == 2:
        return "REF2"
    return "REF3_PLUS"


def _annual_bucket(row: Model1LabTrade) -> str:
    entered = datetime.fromisoformat(row.entry_opened_at)
    boundary = datetime(
        entered.year,
        9,
        21,
        tzinfo=entered.tzinfo,
    )
    start_year = entered.year if entered >= boundary else entered.year - 1
    return f"{start_year}_{start_year + 1}"


def _combined_bucket(
    row: Model1LabTrade,
    *,
    kind: str,
) -> str:
    if kind == "EARLY_VS_LATE_H4":
        slot = int(row.timing_triplet.rsplit(":", 1)[1])
        return "H4_SLOTS_1_3" if slot <= 3 else "H4_SLOTS_4_6"
    if kind == "SLOT5_VS_REST":
        return (
            "H4_SLOT_5"
            if row.timing_triplet.endswith(":5")
            else "OTHER_H4_SLOTS"
        )
    if kind == "D2_VS_REST":
        return "D2" if _delay_bars(row) == "D2" else "NOT_D2"
    if kind == "REF1_VS_MULTI":
        return "REF1" if row.reference_count == 1 else "REF2_PLUS"
    raise ValueError(kind)


def _population_report(
    rows: tuple[Model1LabTrade, ...],
) -> dict[str, Any]:
    overall = _metrics(rows)
    return {
        "overall": overall,
        "exit_reason": _group(rows, lambda row: row.exit_reason),
        "stop_subtype": _group(rows, _stop_subtype),
        "direction": _group(rows, lambda row: row.parent_direction),
        "timing_triplet": _group(rows, lambda row: row.timing_triplet),
        "confirmation_delay": _group(rows, _delay_bars),
        "reference_count": _group(rows, _reference_bucket),
        "annual": _group(rows, _annual_bucket),
        "contrasts": {
            "early_vs_late_h4": _group(
                rows,
                lambda row: _combined_bucket(row, kind="EARLY_VS_LATE_H4"),
            ),
            "slot5_vs_rest": _group(
                rows,
                lambda row: _combined_bucket(row, kind="SLOT5_VS_REST"),
            ),
            "d2_vs_rest": _group(
                rows,
                lambda row: _combined_bucket(row, kind="D2_VS_REST"),
            ),
            "ref1_vs_multi": _group(
                rows,
                lambda row: _combined_bucket(row, kind="REF1_VS_MULTI"),
            ),
        },
        "pf_loss_mechanism": {
            "original_stop_loss_r": round(
                -sum(
                    float(row.r_multiple)
                    for row in rows
                    if _stop_subtype(row) == "ORIGINAL_STOP_MINUS_1R"
                ),
                8,
            ),
            "fixed_target_gain_r": round(
                sum(
                    float(row.r_multiple)
                    for row in rows
                    if row.exit_reason == "TARGET_FIXED_1_5R"
                ),
                8,
            ),
            "c3_close_net_r": round(
                sum(
                    float(row.r_multiple)
                    for row in rows
                    if row.exit_reason == "C3_CLOSE"
                ),
                8,
            ),
            "mean_edge_before_cost_r_per_trade": overall[
                "break_even_friction_r_per_trade"
            ],
        },
    }


def run_attribution() -> tuple[
    dict[str, tuple[Model1LabTrade, ...]],
    dict[str, Any],
]:
    populations, diagnostics = build_populations()
    report = {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "window_start": START.isoformat(),
        "window_end_exclusive": END.isoformat(),
        "diagnostics": diagnostics,
        "populations": {
            name: _population_report(rows)
            for name, rows in populations.items()
        },
        "interpretation_guardrails": {
            "dimensions_overlap": True,
            "not_additive_causal_effects": True,
            "filter_promotion_forbidden": True,
            "purpose": "ROOT_CAUSE_ATTRIBUTION_ONLY",
        },
        "research_only": True,
        "candidate_certified": False,
        "demo_eligible": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "production_authorized": False,
    }
    return populations, report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    populations, report = run_attribution()
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n"
    )
    with (args.output / "trades.jsonl").open("w", encoding="utf-8") as handle:
        for population, rows in populations.items():
            for trade in rows:
                row = asdict(trade)
                row["population"] = population
                handle.write(json.dumps(row, sort_keys=True) + "\n")
    print("CRT_R2BF_PF_ATTRIBUTION_JSON=" + json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
