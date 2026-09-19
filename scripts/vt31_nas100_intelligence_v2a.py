"""VT31_NAS100 Intelligence V2A: causal sequence-freshness ablation.

This is development research, not a frozen candidate.  The only policy change
is to abstain from a source-valid setup when the causal Market State V2
snapshot says that the reference reclaim is 8-14 minutes old.  That bucket was
predeclared in the immutable Market State V2 run before its economic result was
read.

No outcome field participates in the decision.
"""
from __future__ import annotations

import argparse
import json
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

SCHEMA = "qore.vt31.nas100.intelligence.v2a.sequence_freshness"
SOURCE_SCHEMA = "qore.vt31.nas100.market_state_lab.v2"
FRICTION = Decimal("0.05")
POLICY_ID = "vt31-nas100-v2a-abstain-reclaim-latency-8-14-predeclared-v1"


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _metrics(rows: list[dict[str, Any]]) -> dict[str, object]:
    terminal = sorted(
        (row for row in rows if row.get("status") == "terminal"),
        key=lambda row: cast(str, row["signal_at"]),
    )
    values = [_d(row["r_multiple"]) - FRICTION for row in terminal]
    total = sum(values, Decimal(0))
    equity = Decimal(0)
    peak = Decimal(0)
    max_drawdown = Decimal(0)
    gross_profit = Decimal(0)
    gross_loss = Decimal(0)
    losing_streak = 0
    max_losing_streak = 0
    wins = 0
    losses = 0
    for value in values:
        equity += value
        peak = max(peak, equity)
        max_drawdown = max(max_drawdown, peak - equity)
        if value > 0:
            wins += 1
            gross_profit += value
            losing_streak = 0
        elif value < 0:
            losses += 1
            gross_loss += -value
            losing_streak += 1
            max_losing_streak = max(max_losing_streak, losing_streak)
        else:
            losing_streak = 0
    sample = len(values)
    return {
        "sample": sample,
        "wins": wins,
        "losses": losses,
        "total_r": format(total, "f"),
        "mean_r": format(total / Decimal(sample), "f") if sample else None,
        "profit_factor": (
            format(gross_profit / gross_loss, "f") if gross_loss else None
        ),
        "max_drawdown_r": format(max_drawdown, "f"),
        "max_losing_streak": max_losing_streak,
    }


def evaluate(path: Path) -> dict[str, object]:
    source = json.loads(path.read_text())
    if source.get("schema") != SOURCE_SCHEMA:
        raise ValueError("unexpected source schema")
    contract = cast(dict[str, object], source["causal_contract"])
    assert contract["runtime_features_are_predecision_only"] is True
    assert contract["date_level_outcome_lookup"] is False
    assert contract["future_bar_lookup"] is False
    assert contract["cibo_post_outcome_fields_runtime_access"] is False

    rows = cast(list[dict[str, Any]], source["state_matrix"])
    selected: list[dict[str, Any]] = []
    decisions: list[dict[str, object]] = []
    abstained = 0
    for row in rows:
        stale = row.get("reclaim_latency_bin") == "8-14"
        if stale:
            abstained += 1
            action = "ABSTAIN_STALE_SEQUENCE"
        else:
            selected.append(row)
            action = "ALLOW_BASELINE_EXECUTION"
        decisions.append(
            {
                "local_date": row["local_date"],
                "signal_at": row["signal_at"],
                "action": action,
                "runtime_inputs": {
                    "reference_reclaimed": row["reference_reclaimed"],
                    "minutes_reclaim_to_decision": row[
                        "minutes_reclaim_to_decision"
                    ],
                    "reclaim_latency_bin": row["reclaim_latency_bin"],
                },
                "outcome_fields_used_for_decision": False,
            }
        )

    baseline = _metrics(rows)
    policy = _metrics(selected)
    return {
        "schema": SCHEMA,
        "policy_id": POLICY_ID,
        "market": "NAS100",
        "partition": source["partition"],
        "research_only": True,
        "candidate_frozen": False,
        "opens_new_holdout": False,
        "live_authorized": False,
        "production_authorized": False,
        "causal_contract": {
            "decision_feature": "reclaim_latency_bin",
            "abstain_state": "8-14",
            "bucket_predeclared_before_economic_read": True,
            "date_level_outcome_lookup": False,
            "future_bar_lookup": False,
            "post_outcome_runtime_access": False,
            "stop_changed": False,
            "target_changed": False,
            "management_changed": False,
        },
        "source_binding": {
            "market_state_schema": source["schema"],
            "market_state_evidence": source["evidence"],
        },
        "source_setup_rows": len(rows),
        "abstained_rows": abstained,
        "allowed_rows": len(selected),
        "baseline_terminal_economics": baseline,
        "v2a_terminal_economics": policy,
        "decision_trace": decisions,
        "interpretation": (
            "isolated sequence-freshness ablation; improvement is development "
            "evidence only and cannot freeze or certify VT31_NAS100"
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = evaluate(args.input)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "partition": payload["partition"],
                "abstained_rows": payload["abstained_rows"],
                "baseline": payload["baseline_terminal_economics"],
                "v2a": payload["v2a_terminal_economics"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
