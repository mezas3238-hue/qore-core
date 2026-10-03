#!/usr/bin/env python3
"""Strict rolling train -> frozen test WFO for protected-capital Compound.

This is reused-holdout research only. Five chronological source blocks create
four train/test folds. Each fold selects one member of the preregistered
USD60-equivalent dynamic-capital grid using only the immediately preceding
training block, then freezes that ratio for the next test block.

No test outcome participates in selection. Each block resets research state to
the frozen USD60 protocol so parameter selection cannot rewrite prior account
state. This is deliberately stricter than the descriptive four-way partition in
the reality exam and makes no fresh-OOS or certification claim.
"""

from __future__ import annotations

import argparse
import json
from decimal import Decimal
from pathlib import Path
from typing import Any

from cibo_compound_protected_capital_reality_exam import (
    ELIGIBLE_SIDE,
    _d,
    _fmt,
    _metrics,
    _settled_rows,
    _simulate_observed,
)
from cibo_compound_trader_lab_side_capital_sweep import (
    BASE_REFERENCE_CAPITAL_USD,
    USD60_LIMIT_GRID,
)

BLOCK_COUNT = 5
TEST_FOLD_COUNT = 4


def _chronological_blocks(
    rows: tuple[dict[str, Any], ...],
) -> tuple[tuple[dict[str, Any], ...], ...]:
    ordered = sorted(
        rows,
        key=lambda row: (
            row["market_decision_at"],
            str(row["signal_fingerprint"]),
        ),
    )
    base = len(ordered) // BLOCK_COUNT
    remainder = len(ordered) % BLOCK_COUNT
    result: list[tuple[dict[str, Any], ...]] = []
    cursor = 0
    for index in range(BLOCK_COUNT):
        size = base + (1 if index < remainder else 0)
        block = tuple(ordered[cursor : cursor + size])
        cursor += size
        if not block:
            raise RuntimeError("strict WFO produced empty chronological block")
        result.append(block)
    if cursor != len(ordered):
        raise RuntimeError("strict WFO block partition drift")
    return tuple(result)


def _observed_candidate(
    rows: tuple[dict[str, Any], ...],
    *,
    shared: bool,
    usd60_limit: Decimal,
) -> dict[str, Any]:
    ratio = usd60_limit / BASE_REFERENCE_CAPITAL_USD
    try:
        episodes = _simulate_observed(
            rows,
            shared=shared,
            eligible_sides=(ELIGIBLE_SIDE,),
            max_capital_need_to_current_capital_ratio=ratio,
        )
    except RuntimeError as exc:
        return {
            "usd60_reference_limit_usd": _fmt(usd60_limit),
            "dynamic_ratio": _fmt(ratio),
            "status": "REJECT",
            "reason": str(exc),
            "episode_count": 0,
            "incremental_realized_pnl_usd": None,
            "weighted_average_roi": None,
        }

    observed = _metrics(
        episodes,
        label=("COMPOUND_PORTFOLIO" if shared else "CIBO_COMPOUND"),
    )
    return {
        "usd60_reference_limit_usd": _fmt(usd60_limit),
        "dynamic_ratio": _fmt(ratio),
        "status": observed["status"],
        "reason": None,
        "episode_count": observed["episode_count"],
        "incremental_realized_pnl_usd": observed.get(
            "incremental_realized_pnl_usd"
        ),
        "weighted_average_roi": observed.get("weighted_average_roi"),
        "profit_factor": observed.get("profit_factor"),
        "max_incremental_drawdown_usd": observed.get(
            "max_incremental_drawdown_usd"
        ),
    }


def _selection_key(candidate: dict[str, Any]) -> tuple[Any, ...]:
    measured = candidate["status"] == "MEASURED"
    roi = (
        _d(candidate["weighted_average_roi"])
        if measured
        else Decimal("-Infinity")
    )
    pnl = (
        _d(candidate["incremental_realized_pnl_usd"])
        if measured
        else Decimal("-Infinity")
    )
    count = int(candidate["episode_count"])
    # Tie-break toward the smaller capital limit. The test block is never read.
    limit = _d(candidate["usd60_reference_limit_usd"])
    return (measured, roi, pnl, count, -limit)


def _fold(
    train_rows: tuple[dict[str, Any], ...],
    test_rows: tuple[dict[str, Any], ...],
    *,
    shared: bool,
    fold_number: int,
) -> dict[str, Any]:
    train_candidates = [
        _observed_candidate(
            train_rows,
            shared=shared,
            usd60_limit=limit,
        )
        for limit in USD60_LIMIT_GRID
    ]
    selected = max(train_candidates, key=_selection_key)
    selected_limit = _d(selected["usd60_reference_limit_usd"])
    test = _observed_candidate(
        test_rows,
        shared=shared,
        usd60_limit=selected_limit,
    )
    test_positive = (
        test["status"] == "MEASURED"
        and int(test["episode_count"]) > 0
        and _d(test["incremental_realized_pnl_usd"]) > 0
        and _d(test["weighted_average_roi"]) > 0
    )
    return {
        "fold_id": f"STRICT_WF{fold_number}",
        "selection_source": "TRAIN_BLOCK_ONLY",
        "test_outcome_used_for_selection": False,
        "state_reset_between_blocks": True,
        "selected_usd60_reference_limit_usd": _fmt(selected_limit),
        "selected_dynamic_ratio": selected["dynamic_ratio"],
        "train_candidates": train_candidates,
        "selected_train_candidate": selected,
        "test": test,
        "test_positive": test_positive,
    }


def _surface(
    blocks: tuple[tuple[dict[str, Any], ...], ...],
    *,
    shared: bool,
) -> dict[str, Any]:
    folds = [
        _fold(
            blocks[index],
            blocks[index + 1],
            shared=shared,
            fold_number=index + 1,
        )
        for index in range(TEST_FOLD_COUNT)
    ]
    passed = sum(1 for fold in folds if fold["test_positive"])
    return {
        "surface": "COMPOUND_PORTFOLIO" if shared else "CIBO_COMPOUND",
        "fold_count": len(folds),
        "positive_test_folds": passed,
        "all_test_folds_positive": passed == TEST_FOLD_COUNT,
        "folds": folds,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--decision-trace", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    trace = json.loads(args.decision_trace.read_text(encoding="utf-8"))
    if not isinstance(trace, dict):
        raise ValueError("decision trace root must be object")
    rows = _settled_rows(trace)
    blocks = _chronological_blocks(rows)

    local = _surface(blocks, shared=False)
    portfolio = _surface(blocks, shared=True)
    passed = (
        local["all_test_folds_positive"]
        and portfolio["all_test_folds_positive"]
    )

    block_meta = [
        {
            "block_id": f"B{index + 1}",
            "row_count": len(block),
            "first_decision_at": min(
                row["market_decision_at"] for row in block
            ),
            "last_decision_at": max(
                row["market_decision_at"] for row in block
            ),
        }
        for index, block in enumerate(blocks)
    ]

    report = {
        "schema": "qore.cibo.compound-strict-wfo.v1",
        "source_trace_sha256": trace.get("trace_sha256"),
        "source_settled_core_rows": len(rows),
        "calibration_mode": "NON_CERTIFYING_REUSED_HOLDOUT",
        "eligible_side": ELIGIBLE_SIDE,
        "grid": {
            "usd60_reference_limits_usd": [
                _fmt(value) for value in USD60_LIMIT_GRID
            ],
            "capital_proportional": True,
        },
        "method": {
            "block_count": BLOCK_COUNT,
            "test_fold_count": TEST_FOLD_COUNT,
            "train_rule": "IMMEDIATELY_PRECEDING_BLOCK_ONLY",
            "selection_objective": (
                "max train weighted ROI, then train PnL, density, smaller limit"
            ),
            "test_parameter_frozen": True,
            "test_outcome_used_for_selection": False,
            "state_reset_between_blocks": True,
            "population_gate_used": False,
            "fresh_oos_claimed": False,
            "forward_generalization_claimed": False,
        },
        "blocks": block_meta,
        "cibo_compound": local,
        "compound_portfolio": portfolio,
        "gate_verdict": (
            "PASS_STRICT_4_OF_4_BOTH_SURFACES"
            if passed
            else "FALSIFIED_K_ONLY_FAMILY"
        ),
        "governance": {
            "measurement_only": True,
            "broker_mutation": False,
            "orders": False,
            "live": False,
            "production": False,
            "real_capital": False,
            "certification_claimed": False,
            "merge_authority": False,
            "owner_global_status": "REJECT",
        },
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
                "cibo_compound_positive_test_folds": local[
                    "positive_test_folds"
                ],
                "compound_portfolio_positive_test_folds": portfolio[
                    "positive_test_folds"
                ],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
