"""Hot causal filters over a prepared VT31 Comparator-009 trace.

No M1 market-history reconstruction occurs here. Candidate exits are evaluated
only from diagnostics that were observable on a fully closed M1 in the prepared
control trace, and execute at the recorded next M1 open.
"""
from __future__ import annotations

import argparse
import copy
import json
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_nas100_a_b_admission_integration_frontier_v1 as admission
import vt31_nas100_comp010_live_context_adverse_exit_v1 as comp010
import vt31_nas100_specialist_r1_candidate as specialist

SCHEMA = "qore.vt31.nas100.comp010.hot_filter.v1"
CONTROL = comp010.LAB_CONTROL_ALIAS
VARIANTS = (
    CONTROL,
    comp010.VARIANT_A,
    comp010.VARIANT_B,
    comp010.VARIANT_UNION,
)


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _extra_allowed(event: dict[str, object], variant: str) -> bool:
    a = event.get("comp010_fvg_h1_mixed_exit_authorized") is True
    b = event.get("comp010_long_m15_bearish_exit_authorized") is True
    if variant == comp010.VARIANT_A:
        return a
    if variant == comp010.VARIANT_B:
        return b
    if variant == comp010.VARIANT_UNION:
        return a or b
    if variant == CONTROL:
        return False
    raise ValueError(variant)


def _candidate(
    control: dict[str, object],
    variant: str,
) -> dict[str, object]:
    if variant == CONTROL:
        return copy.deepcopy(control)

    row = copy.deepcopy(control)
    events = cast(
        list[dict[str, object]],
        row.get("cognitive_exit_evaluations", []),
    )
    first_base: int | None = None
    first_extra: int | None = None
    for index, event in enumerate(events):
        if first_base is None and event.get("cognitive_exit_authorized") is True:
            first_base = index
        if first_extra is None and _extra_allowed(event, variant):
            first_extra = index

    if first_extra is None:
        row["cognitive_exit_variant"] = variant
        return row

    for index, event in enumerate(events):
        extra = _extra_allowed(event, variant)
        event["comp010_extra_exit_authorized"] = extra
        event["cognitive_exit_variant"] = variant
        event["cognitive_exit_authorized"] = bool(
            event.get("comp007_base_exit_authorized") is True
            or event.get("comp009_weak_efficiency_exit_authorized") is True
            or extra
        )
        if index >= first_extra:
            break

    # Same-or-later authorization is economically identical to the control.
    if first_base is not None and first_extra >= first_base:
        row["cognitive_exit_variant"] = variant
        return row

    event = events[first_extra]
    next_r = event.get("next_m1_open_r")
    next_at = event.get("next_m1_open_at")
    if next_r is None or next_at is None:
        row["cognitive_exit_variant"] = variant
        return row

    original_exit_at = str(row.get("exit_at", ""))
    if original_exit_at and str(next_at) >= original_exit_at:
        row["cognitive_exit_variant"] = variant
        return row

    row["r_multiple"] = str(next_r)
    row["exit_at"] = str(next_at)
    row["exit_reason"] = "composite-pretarget-cognitive-exit"
    row["cognitive_exit_variant"] = variant
    row["cognitive_exit_evaluations"] = events[: first_extra + 1]
    return row


def _minimal(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    return [
        {
            "signal_at": row["signal_at"],
            "local_date": row["local_date"],
            "entry_family": row.get("entry_family"),
            "side": row.get("side"),
            "exit_reason": row.get("exit_reason"),
            "r_multiple": row["r_multiple"],
        }
        for row in rows
    ]


def _deferred_mc() -> dict[str, object]:
    return {
        "algorithm": "staged-after-stitched-dd-sharpe",
        "paths": 0,
        "block_length": 5,
        "positive_terminal_probability": "0",
        "p95_max_drawdown_r": "0",
    }


def replay(prepared_path: Path) -> dict[str, object]:
    prepared = json.loads(prepared_path.read_text(encoding="utf-8"))
    if prepared.get("schema") != (
        "qore.vt31.nas100.comp009.causal_trace_prepared.v1"
    ):
        raise ValueError("unexpected prepared causal trace schema")

    control = cast(list[dict[str, object]], prepared["control_rows"])
    variants = {
        variant: [_candidate(row, variant) for row in control]
        for variant in VARIANTS
    }
    control_ids = [str(row["signal_at"]) for row in control]
    reports: dict[str, object] = {}
    for variant, rows in variants.items():
        if [str(row["signal_at"]) for row in rows] != control_ids:
            raise AssertionError(f"{variant}: trade identity drift")
        winner = admission._winner_preservation(control, rows)
        changed = sum(
            _d(left["r_multiple"]) != _d(right["r_multiple"])
            or left.get("exit_reason") != right.get("exit_reason")
            for left, right in zip(control, rows, strict=True)
        )
        reports[variant] = {
            "trade_count": len(rows),
            "relative_density_vs_control": "1",
            "relative_density_vs_comp006": "1",
            "stress_0_05r": specialist._metrics(
                rows,
                friction=specialist.FRICTION,
            ),
            "monte_carlo": _deferred_mc(),
            "halfyear_stress": specialist._block_metrics(
                rows,
                halfyear=True,
            ),
            "winner_preservation_vs_control": winner,
            "winner_preservation_vs_comp006": winner,
            "changed_trade_count": changed,
            "candidate_rows": _minimal(rows),
            "eligible_dates": prepared["eligible_dates"],
        }

    return {
        "schema": SCHEMA,
        "market": "NAS100",
        "comparator_id": (
            "VT31_AB_COMP009_MAX_INTELLIGENCE_COMPOSED_SURVIVOR"
        ),
        "lab_control_alias": CONTROL,
        "variants": reports,
        "governance": {
            "prepared_causal_trace_reused": True,
            "market_history_replayed_in_hot_stage": False,
            "decision_on_fully_closed_m1": True,
            "execution_on_next_m1_open": True,
            "new_numeric_threshold_added": False,
            "position_sizing_used": False,
            "dynamic_sizing_used": False,
            "leverage_used": False,
            "compounding_used": False,
            "capital_weighting_used": False,
            "fresh_holdout_opened": False,
            "candidate_certified": False,
            "live_authorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepared", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    payload = replay(args.prepared)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
