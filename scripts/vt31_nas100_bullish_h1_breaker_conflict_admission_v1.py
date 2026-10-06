"""VT31 NAS100 bullish-H1 Breaker conflict admission frontier V1.

Consumed-evidence development only.

Fixed base:
    VT31_AB_COMP007_RAPID_BREAKER_UNION_SURVIVOR

Only degree of freedom:
- abstain Breaker SHORT when prior-day, cash-open and H1 are all bullish.

No outcome, fold/date identity, sizing, leverage, compounding, portfolio or
capital state can influence action.
"""
from __future__ import annotations

import argparse
import json
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_nas100_a_b_admission_integration_frontier_v1 as admission
import vt31_nas100_comp007_residual_dd_forensics_v1 as comp007
import vt31_nas100_h3_dol2_composition_frontier_v1 as composition
import vt31_nas100_specialist_r1_candidate as specialist

SCHEMA = "qore.vt31.nas100.bullish_h1_breaker_conflict_admission.v1"
COMPARATOR_ID = "VT31_AB_COMP007_RAPID_BREAKER_UNION_SURVIVOR"
VARIANTS = (
    "COMP007_CONTROL",
    "COMP007_PLUS_BULLISH_H1_BREAKER_SHORT_CONFLICT",
)


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _conflict(row: dict[str, object]) -> bool:
    if str(row["entry_family"]) != "breaker":
        return False
    if str(row["side"]) != "short":
        return False
    context = cast(dict[str, object], row.get("entry_context", {}))
    return (
        str(context.get("prior_day_state")) == "bullish"
        and str(context.get("cash_open_state")) == "bullish"
        and str(context.get("h1_state")) == "bullish"
    )


def _report(
    *,
    structural_count: int,
    comparator: list[dict[str, object]],
    rows: list[dict[str, object]],
) -> dict[str, object]:
    kept = {str(row["signal_at"]) for row in rows}
    excluded = [
        row for row in comparator if str(row["signal_at"]) not in kept
    ]
    stressed_excluded = [
        _d(row["r_multiple"]) - specialist.FRICTION
        for row in excluded
    ]
    return {
        "trade_count": len(rows),
        "relative_density_vs_structural": (
            "0"
            if structural_count == 0
            else format(Decimal(len(rows)) / Decimal(structural_count), "f")
        ),
        "relative_density_vs_comp007": (
            "0"
            if not comparator
            else format(Decimal(len(rows)) / Decimal(len(comparator)), "f")
        ),
        "stress_0_05r": specialist._metrics(
            rows,
            friction=specialist.FRICTION,
        ),
        "monte_carlo": specialist._monte_carlo(rows),
        "halfyear_stress": specialist._block_metrics(rows, halfyear=True),
        "winner_preservation_vs_comp007": admission._winner_preservation(
            comparator,
            rows,
        ),
        "sequence_diagnostics": composition._sequence_diagnostics(rows),
        "excluded_trade_count": len(excluded),
        "excluded_winner_count": sum(value > 0 for value in stressed_excluded),
        "excluded_loss_count": sum(value < 0 for value in stressed_excluded),
        "excluded_trade_forensics": [
            {
                "signal_at": row["signal_at"],
                "r_multiple": row["r_multiple"],
                "exit_reason": row["exit_reason"],
                "entry_family": row["entry_family"],
                "side": row["side"],
                "bullish_h1_breaker_short_conflict": _conflict(row),
                "signature": comp007._signature(row),
                "entry_context": row.get("entry_context", {}),
                "cognitive_exit_evaluations": row.get(
                    "cognitive_exit_evaluations", []
                ),
            }
            for row in excluded
        ],
    }


def replay(evidence_path: Path) -> dict[str, object]:
    structural_rows, comparator = comp007._build_union_rows(evidence_path)
    candidate = [row for row in comparator if not _conflict(row)]

    variant_rows = {
        "COMP007_CONTROL": comparator,
        "COMP007_PLUS_BULLISH_H1_BREAKER_SHORT_CONFLICT": candidate,
    }
    reports = {
        name: _report(
            structural_count=len(structural_rows),
            comparator=comparator,
            rows=rows,
        )
        for name, rows in variant_rows.items()
    }

    return {
        "schema": SCHEMA,
        "market": "NAS100",
        "comparator_id": COMPARATOR_ID,
        "variants": reports,
        "governance": {
            "consumed_evidence_only": True,
            "same_position_logic_all_variants": True,
            "only_admission_degree_of_freedom": True,
            "conflict_entry_time_only": True,
            "new_numeric_threshold_added": False,
            "outcome_used_for_action": False,
            "fold_identity_used_for_action": False,
            "date_identity_used_for_action": False,
            "position_sizing_used": False,
            "dynamic_sizing_used": False,
            "leverage_used": False,
            "compounding_used": False,
            "capital_weighting_used": False,
            "absolute_volume_used": False,
            "fresh_holdout_opened": False,
            "policy_promoted": False,
            "candidate_frozen": False,
            "candidate_certified": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    payload = replay(args.evidence)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
