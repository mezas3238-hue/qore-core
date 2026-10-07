#!/usr/bin/env python3
"""Single-base 3Y replay wrapper for the current VT31 cognitive stack.

This module deliberately has no R5/R6/R8 fold abstraction. It captures the
current specialist's causal attrition telemetry during the same replay pass
used by the current Comparator-010 position stack, then reports the owner's
approximately-450-trade density objective on one contiguous 3Y population.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_nas100_comp010_live_context_adverse_exit_v1 as current

SCHEMA = "qore.vt31.nas100.owner_3y_replay.v1"
BASE_ID = "VT31_NAS100_OWNER_3Y_BASE_001"
TARGET_TRADES = 450
REASONABLE_DENSITY_FLOOR = 400


def _validate_evidence(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("base_id") != BASE_ID:
        raise ValueError("evidence is not the owner-designated VT31 3Y base")
    if payload.get("market") != "NAS100":
        raise ValueError("3Y base must be NAS100")
    if payload.get("base_start_at") != "2023-10-01T00:00:00+00:00":
        raise ValueError("unexpected 3Y base start")
    if payload.get("base_end_exclusive") != "2026-10-01T00:00:00+00:00":
        raise ValueError("unexpected 3Y base end")
    if payload.get("coverage_sufficient") is not True:
        raise ValueError("3Y base coverage is insufficient")
    return cast(dict[str, object], payload)


def _month_counts(
    rows: list[dict[str, object]],
) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for row in rows:
        counts[str(row["local_date"])[:7]] += 1
    return dict(sorted(counts.items()))


def _year_counts(
    rows: list[dict[str, object]],
) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for row in rows:
        counts[str(row["local_date"])[:4]] += 1
    return dict(sorted(counts.items()))


def replay(evidence_path: Path) -> dict[str, object]:
    evidence = _validate_evidence(evidence_path)

    captured: dict[str, object] = {}
    original_replay = current.specialist.replay

    def capture_specialist(path: Path) -> dict[str, object]:
        payload = original_replay(path)
        captured.update(payload)
        return payload

    current.specialist.replay = capture_specialist
    try:
        payload = current.replay(evidence_path)
    finally:
        current.specialist.replay = original_replay

    variants = cast(dict[str, dict[str, object]], payload["variants"])
    control_name = str(payload["lab_control_alias"])
    control = variants[control_name]
    rows = cast(list[dict[str, object]], control["candidate_rows"])
    structural_count = int(captured["trade_count"])
    admitted_count = int(control["trade_count"])
    status_counts = cast(dict[str, int], captured["status_counts"])
    reasoning_trace = cast(
        list[dict[str, object]],
        captured["reasoning_trace"],
    )
    action_counts: Counter[str] = Counter(
        str(item.get("action", "UNKNOWN"))
        for item in reasoning_trace
    )
    gap = TARGET_TRADES - admitted_count
    target_fraction = (
        Decimal(admitted_count) / Decimal(TARGET_TRADES)
        if TARGET_TRADES
        else Decimal(0)
    )

    density = {
        "target_trades_3y": TARGET_TRADES,
        "reasonable_density_floor": REASONABLE_DENSITY_FLOOR,
        "actual_admitted_trades": admitted_count,
        "gap_to_target": gap,
        "target_fraction": format(target_fraction, "f"),
        "reasonable_density_gate_pass": (
            admitted_count >= REASONABLE_DENSITY_FLOOR
        ),
        "market_days": int(captured["market_days"]),
        "eligible_sessions": len(
            cast(list[str], control["eligible_dates"])
        ),
        "structural_terminal_trades_before_comp009_admission": structural_count,
        "admission_rejection_count": max(
            structural_count - admitted_count,
            0,
        ),
        "specialist_status_counts": status_counts,
        "reasoning_action_counts": dict(sorted(action_counts.items())),
        "trades_by_year": _year_counts(rows),
        "trades_by_month": _month_counts(rows),
        "legacy_r5_r6_r8_operating_folds_used": False,
    }

    result = {
        "schema": SCHEMA,
        "base_id": BASE_ID,
        "window": {
            "start_at": evidence["base_start_at"],
            "end_exclusive": evidence["base_end_exclusive"],
            "calendar_days": evidence["requested_calendar_days"],
            "status": "CONSUMED_OWNER_3Y_BASE",
        },
        "current_stack": payload,
        "density": density,
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
    return result


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
    control_name = str(
        cast(dict[str, object], payload["current_stack"])["lab_control_alias"]
    )
    variants = cast(
        dict[str, dict[str, object]],
        cast(dict[str, object], payload["current_stack"])["variants"],
    )
    print(
        json.dumps(
            {
                "base_id": BASE_ID,
                "control": control_name,
                "density": payload["density"],
                "control_stress_0_05r": variants[control_name][
                    "stress_0_05r"
                ],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
