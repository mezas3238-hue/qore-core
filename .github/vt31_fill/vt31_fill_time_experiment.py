#!/usr/bin/env python3
"""Apply predeclared VT31 causal fill-time thesis revalidation."""
from __future__ import annotations

import argparse
import json
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

import vt31_nas100_a_b_admission_integration_frontier_v1 as admission
import vt31_nas100_specialist_r1_candidate as specialist

CONTROL = "COMP009_TRUTHFUL_CONTROL"
CANDIDATE = "FILL_REVALIDATE_REASONING"


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _preservation(
    control: list[dict[str, object]],
    candidate: list[dict[str, object]],
) -> dict[str, object]:
    raw = admission._winner_preservation(control, candidate)
    return {
        **raw,
        "count": raw["winner_count_preservation"],
        "r": raw["winner_r_preservation"],
    }


def _payload(
    rows: list[dict[str, object]],
    *,
    control: list[dict[str, object]],
    rejected: list[dict[str, object]],
) -> dict[str, object]:
    return {
        "trade_count": len(rows),
        "relative_density_vs_control": (
            "0"
            if not control
            else format(Decimal(len(rows)) / Decimal(len(control)), "f")
        ),
        "metrics": specialist._metrics(
            rows,
            friction=specialist.FRICTION,
        ),
        "winner_preservation": _preservation(control, rows),
        "temporal_blocks": specialist._block_metrics(rows, halfyear=True),
        "net_r_values": [
            format(_d(row["r_multiple"]) - specialist.FRICTION, "f")
            for row in rows
        ],
        "candidate_rows": rows,
        "changed_trade_count": len(rejected),
        "changed_trade_forensics": rejected,
    }


def run(prepared_path: Path, lane: str) -> dict[str, Any]:
    prepared = json.loads(prepared_path.read_text(encoding="utf-8"))
    if prepared.get("schema") != "qore.github-trader-lab.vt31-fill-time-ledger.v1":
        raise ValueError("unexpected prepared schema")

    control = cast(list[dict[str, object]], prepared["rows"])
    candidate: list[dict[str, object]] = []
    rejected: list[dict[str, object]] = []

    for row in control:
        diag = cast(
            dict[str, object] | None,
            row.get("fill_revalidation"),
        )
        if diag is None:
            raise AssertionError("admitted control trade lacks fill revalidation")
        if diag.get("decision_authority_uses_fill_bar_ohlc") is not False:
            raise AssertionError("fill bar OHLC leaked into revalidation authority")

        if diag.get("fill_revalidation_accepts") is True:
            candidate.append(row)
            continue

        raw_r = _d(row["r_multiple"])
        rejected.append(
            {
                "signal_at": row["signal_at"],
                "filled_at": row.get("filled_at"),
                "local_date": row["local_date"],
                "entry_family": row["entry_family"],
                "side": row["side"],
                "control_r": format(raw_r, "f"),
                "stressed_control_r": format(
                    raw_r - specialist.FRICTION,
                    "f",
                ),
                "control_winner": raw_r - specialist.FRICTION > 0,
                "control_exit_reason": row.get("exit_reason"),
                "zero_post_entry_cognitive_calls": (
                    len(
                        cast(
                            list[object],
                            row.get("cognitive_exit_evaluations", []),
                        )
                    )
                    == 0
                ),
                "fill_revalidation": diag,
            }
        )

    variants = {
        CONTROL: _payload(
            control,
            control=control,
            rejected=[],
        ),
        CANDIDATE: _payload(
            candidate,
            control=control,
            rejected=rejected,
        ),
    }
    return {
        "schema": "qore.github-trader-lab.normalized-replay.v2",
        "adapter": "vt31-fill-time-revalidation-v1",
        "subject": "VT31_NAS100",
        "lane": lane,
        "control": CONTROL,
        "eligible_dates": prepared["eligible_dates"],
        "variants": variants,
        "governance": {
            "consumed_evidence_only": True,
            "pending_order_revalidation": True,
            "decision_at_prospective_fill_bar_open": True,
            "fill_bar_ohlc_used_for_decision": False,
            "new_delay_threshold_added": False,
            "outcome_used_for_action": False,
            "fold_identity_used_for_action": False,
            "date_identity_used_for_action": False,
            "position_sizing_used": False,
            "dynamic_sizing_used": False,
            "leverage_used": False,
            "compounding_used": False,
            "capital_weighting_used": False,
            "fresh_holdout_opened": False,
            "candidate_certified": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepared", required=True, type=Path)
    parser.add_argument("--lane", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    payload = run(args.prepared, args.lane)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    headline = {
        name: {
            "trade_count": row["trade_count"],
            "changed_trade_count": row["changed_trade_count"],
            "metrics": row["metrics"],
        }
        for name, row in payload["variants"].items()
    }
    print("VT31_FILL_REVALIDATION_LANE " + json.dumps(headline, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
