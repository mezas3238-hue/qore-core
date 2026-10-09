#!/usr/bin/env python3
"""Join frozen VT31 NY 55-trade control with causal prospective-fill SHADOW.

This is NOT a new trade replay. Counterfactual numbers assume removing a
rejected filled trade without retrying the pending order and without
changing future trades. It is therefore a diagnostic, not executable PnL,
not a new strategy, and not a Core certification metric.
"""
from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

SCHEMA = "qore.vt31.nas100.3y_fill_shadow_control_join.v1"
BASE_ID = "VT31_NAS100_OWNER_3Y_BASE_001"
FROZEN_SOURCE_SHA = (
    "0563370fd021ad091392eb26f60cda0d3356d38c801fc1c2083cceafc5043cfa"
)
COST_R = Decimal("0.05")


def _identity(raw: object) -> str:
    timestamp = datetime.fromisoformat(str(raw))
    if timestamp.utcoffset() is None:
        raise ValueError("signal_at must be timezone-aware")
    return timestamp.astimezone(UTC).isoformat()


def _ratio(numer: Decimal, denom: Decimal) -> str | None:
    return None if denom == 0 else format(numer / denom, "f")


def _observed_metrics(rows: list[dict[str, Any]]) -> dict[str, object]:
    ordered = sorted(rows, key=lambda row: _identity(row["signal_at"]))
    values = [Decimal(str(row["r_multiple"])) - COST_R for row in ordered]
    positive = sum((n for n in values if n > 0), Decimal(0))
    negative = sum((-n for n in values if n < 0), Decimal(0))
    total = sum(values, Decimal(0))
    eq = Decimal(0)
    peak = Decimal(0)
    dd = Decimal(0)
    streak = 0
    longest = 0
    for value in values:
        eq += value
        peak = max(peak, eq)
        dd = max(dd, peak - eq)
        streak = streak + 1 if value < 0 else 0
        longest = max(longest, streak)
    return {
        "trade_count": len(rows),
        "stressed_winners": sum(v > 0 for v in values),
        "stressed_nonwinners": sum(v <= 0 for v in values),
        "raw_total_r_minus_0_05r_cost_each": format(total, "f"),
        "stressed_mean_r": _ratio(total, Decimal(len(values))),
        "stressed_profit_factor": _ratio(positive, negative),
        "observed_max_drawdown_r": format(dd, "f"),
        "longest_consecutive_negative_stressed_trades": longest,
    }


def audit(
    baseline: dict[str, object],
    shadow: dict[str, object],
) -> dict[str, object]:
    if baseline.get("base_id") != BASE_ID:
        raise ValueError("control must be canonical owner 3Y")
    if shadow.get("base_id") != BASE_ID:
        raise ValueError("fill shadow must be canonical owner 3Y")
    if shadow.get("schema") != "qore.vt31.nas100.3y_causal_fill_time_shadow.v1":
        raise ValueError("unrecognized fill time shadow schema")
    if shadow.get("source_sha256") != FROZEN_SOURCE_SHA:
        raise ValueError("source 3Y digest mismatch")
    governance = cast(dict[str, object], shadow["governance"])
    if (
        governance.get("runtime_action_altered") is not False
        or governance.get("fill_cancel_authority") is not False
        or governance.get("fresh_holdout_opened") is not False
    ):
        raise ValueError("shadow did not preserve control execution")
    chain = cast(dict[str, object], baseline["current_stack"])
    control_alias = str(chain["lab_control_alias"])
    control = cast(
        dict[str, object],
        cast(dict[str, object], chain["variants"])[control_alias],
    )
    rows = cast(list[dict[str, Any]], control["candidate_rows"])
    shadow_rows = cast(
        list[dict[str, Any]],
        shadow["per_fill_ledger"],
    )
    if len(rows) != int(control["trade_count"]):
        raise ValueError("frozen admitted control trade count drift")
    if len(shadow_rows) != int(shadow["realized_fill_opportunities"]):
        raise ValueError("fill shadow ledger count drift")

    indexed: dict[str, dict[str, Any]] = {}
    for item in shadow_rows:
        k = _identity(item["signal_at"])
        if k in indexed:
            raise ValueError("duplicate fill candidate identity")
        indexed[k] = item
    matched: list[dict[str, Any]] = []
    preserved: list[dict[str, Any]] = []
    removed: list[dict[str, Any]] = []
    zero_all: list[dict[str, Any]] = []
    zero_rejected = 0
    rejected_winners = 0
    rejected_nonwinners = 0
    for row in rows:
        k = _identity(row["signal_at"])
        decision = indexed.get(k)
        if decision is None:
            raise ValueError(f"missing fill-time reasoning for admitted trade {k}")
        if str(decision.get("structural_status")) != "terminal":
            raise ValueError(f"admitted control trade not a terminal fill: {k}")
        raw_r = Decimal(str(row["r_multiple"]))
        if decision.get("structural_r_multiple") is None:
            raise ValueError("shadow terminal R missing for parity")
        # The admitted Comparator-009 exit can differ from structural-only
        # control. Never force these two exit R values to match.
        enriched = {
            "signal_at": k,
            "raw_admitted_r": format(raw_r, "f"),
            "shadow_accepted": decision["candidate_fill_accepted"],
            "shadow_comp008_accepted": decision["comp008_shadow_fill_accepted"],
            "fill_reasoning_action": decision["revalidated_reasoning_action"],
            "entry_blockers": decision["entry_mandatory_blockers"],
            "zero_postfill_cognition": bool(
                decision.get("has_zero_preterminal_post_entry_m1", False)
            ),
            "entry_family": row.get("entry_family"),
            "side": row.get("side"),
        }
        matched.append(enriched)
        if enriched["zero_postfill_cognition"]:
            zero_all.append(enriched)
        if decision["candidate_fill_accepted"] is True:
            preserved.append(row)
        else:
            removed.append(row)
            if enriched["zero_postfill_cognition"]:
                zero_rejected += 1
            if raw_r > 0:
                rejected_winners += 1
            else:
                rejected_nonwinners += 1

    if len(matched) != len(rows):
        raise AssertionError("admitted population mapping is incomplete")
    return {
        "schema": SCHEMA,
        "base_id": BASE_ID,
        "canonical_source_sha256": FROZEN_SOURCE_SHA,
        "control_alias": control_alias,
        "control_admitted_trade_count": len(rows),
        "shadow_accepted_admitted_trades": len(preserved),
        "shadow_rejected_admitted_trades": len(removed),
        "rejected_admitted_raw_winners": rejected_winners,
        "rejected_admitted_raw_nonwinners": rejected_nonwinners,
        "zero_postfill_admitted_trades": len(zero_all),
        "zero_postfill_rejected_in_shadow": zero_rejected,
        "retrospective_control_metrics_recomputed": _observed_metrics(rows),
        "naive_delete_rejected_trades_diagnostic": _observed_metrics(
            preserved
        ),
        "frozen_control_reported_stress_0_05r": control.get("stress_0_05r"),
        "joined_55_control_trade_ledger": matched,
        "governance": {
            "research_shadow_only": True,
            "naive_removal_not_real_counterfactual": True,
            "pending_order_retries_not_simulated": True,
            "new_admission_decision_simulation_run": False,
            "source_execution_altered": False,
            "zero_future_data_for_candidate_action": True,
            "matched_only_to_retrospective_frozen_control": True,
            "fresh_holdout_opened": False,
            "position_sizing_used": False,
            "capital_used": False,
            "drawdown_certification_claimed": False,
            "candidate_certified": False,
            "live_authorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline-replay", required=True, type=Path)
    parser.add_argument("--fill-shadow", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = audit(
        json.loads(args.baseline_replay.read_text(encoding="utf-8")),
        json.loads(args.fill_shadow.read_text(encoding="utf-8")),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(
        {k: v for k, v in result.items() if k != "joined_55_control_trade_ledger"},
        sort_keys=True,
    ))


if __name__ == "__main__":
    main()
