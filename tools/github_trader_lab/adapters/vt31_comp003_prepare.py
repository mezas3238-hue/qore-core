#!/usr/bin/env python3
"""Prepare reusable VT31 upstream ledgers for the independent GitHub Trader Lab.

This intentionally stops before comparator/admission research. The expensive
M1 reconstruction is paid only when upstream VT31 dependencies change.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, cast

import vt31_nas100_adverse_journey_cognitive_exit_frontier_v1 as adverse
import vt31_nas100_specialist_r1_candidate as specialist

POSITION_VARIANT = "BASE_PLUS_FVG_NONSHALLOW_OR_NONOB_NORMAL"


def prepare_one(evidence_path: Path) -> dict[str, Any]:
    original_selected = specialist._simulate_selected_plan
    original_mc = specialist._monte_carlo
    comp003_rows: list[dict[str, object]] = []

    def cheap_mc(_: list[dict[str, object]]) -> dict[str, object]:
        return {
            "algorithm": "deferred-to-github-trader-lab",
            "paths": 0,
            "block_length": 5,
            "positive_terminal_probability": None,
            "p95_max_drawdown_r": None,
        }

    def simulator(
        day_bars: tuple[object, ...],
        executable: object,
        state: dict[str, object],
    ) -> dict[str, object]:
        structural = specialist._simulate_structural_boundary_only(
            day_bars,
            executable,
        )
        if structural.get("status") != "terminal":
            return structural
        outcome = adverse._simulate(
            day_bars,
            executable,
            state,
            variant=POSITION_VARIANT,
        )
        if outcome.get("status") != "terminal":
            raise AssertionError(
                "Comparator 003 changed terminal eligibility"
            )
        comp003_rows.append(outcome)
        return structural

    try:
        specialist._monte_carlo = cheap_mc
        specialist._simulate_selected_plan = simulator
        base = specialist.replay(evidence_path)
    finally:
        specialist._simulate_selected_plan = original_selected
        specialist._monte_carlo = original_mc

    structural_rows = cast(list[dict[str, object]], base["trades"])
    structural_ids = [str(row["signal_at"]) for row in structural_rows]
    comp_ids = [str(row["signal_at"]) for row in comp003_rows]
    if comp_ids != structural_ids:
        raise AssertionError(
            "prepared comparator changed sovereign terminal identity"
        )

    return {
        "schema": "qore.github-trader-lab.vt31-comp003-prepared.v1",
        "market": "NAS100",
        "position_variant": POSITION_VARIANT,
        "structural_trade_count": len(structural_rows),
        "comp003_rows": comp003_rows,
        "governance": {
            "prepared_upstream_only": True,
            "monte_carlo_deferred": True,
            "admission_research_applied": False,
            "fresh_holdout_opened": False,
            "certification_claimed": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    payload = prepare_one(args.evidence)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "prepared": True,
                "structural_trade_count": payload["structural_trade_count"],
                "output": str(args.output),
            },
            sort_keys=True,
        ),
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
