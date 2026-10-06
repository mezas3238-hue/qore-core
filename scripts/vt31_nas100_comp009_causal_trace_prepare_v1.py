"""Prepare one causal Comparator-009 trace for hot GitHub Trader Lab.

This script pays the expensive closed-M1 cognition reconstruction once per
immutable evidence fold. Downstream hypotheses consume the prepared diagnostic
ledger without replaying market history.

Fresh Holdout remains sealed. Per-fold Monte Carlo is deliberately deferred;
the hot stitched adjudicator runs expensive robustness only after DD and Sharpe
survive.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_nas100_comp010_live_context_adverse_exit_v1 as comp010
import vt31_nas100_specialist_r1_candidate as specialist

SCHEMA = "qore.vt31.nas100.comp009.causal_trace_prepared.v1"


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _deferred_mc(_: list[dict[str, object]]) -> dict[str, object]:
    return {
        "algorithm": "deferred-hot-lab",
        "paths": 0,
        "block_length": 5,
        "positive_terminal_probability": "0",
        "p95_max_drawdown_r": "0",
    }


def _annotate_next_open(
    *,
    day_bars: tuple[object, ...],
    executable: object,
    outcome: dict[str, object],
) -> None:
    by_open = {
        cast(datetime, getattr(bar, "opened_at")): bar
        for bar in day_bars
    }
    entry = _d(getattr(executable, "entry_price"))
    stop = _d(getattr(executable, "stop_price"))
    risk = abs(entry - stop)
    side = str(getattr(getattr(executable, "side"), "value"))
    if risk <= 0:
        raise ValueError("prepared trace requires positive initial risk")

    events = cast(
        list[dict[str, object]],
        outcome.get("cognitive_exit_evaluations", []),
    )
    for event in events:
        observation_at = datetime.fromisoformat(str(event["observation_at"]))
        next_bar = by_open.get(observation_at)
        if next_bar is None:
            event["next_m1_open_at"] = None
            event["next_m1_open_r"] = None
            continue
        opened = _d(getattr(next_bar, "open"))
        terminal = (
            (opened - entry) / risk
            if side == "long"
            else (entry - opened) / risk
        )
        event["next_m1_open_at"] = observation_at.isoformat()
        event["next_m1_open_r"] = format(terminal, "f")


def prepare(evidence_path: Path) -> dict[str, object]:
    original_simulator = specialist._simulate_selected_plan
    original_mc = specialist._monte_carlo
    full_control: list[dict[str, object]] = []

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
        outcome = comp010._simulate_variant(
            day_bars,
            executable,
            state,
            variant=comp010.LAB_CONTROL_ALIAS,
        )
        if outcome.get("status") != "terminal":
            raise AssertionError(
                "prepared control changed sovereign terminal eligibility"
            )
        _annotate_next_open(
            day_bars=day_bars,
            executable=executable,
            outcome=outcome,
        )
        full_control.append(outcome)
        return structural

    try:
        specialist._simulate_selected_plan = simulator
        specialist._monte_carlo = _deferred_mc
        base = specialist.replay(evidence_path)
    finally:
        specialist._simulate_selected_plan = original_simulator
        specialist._monte_carlo = original_mc

    structural = cast(list[dict[str, object]], base["trades"])
    if [str(row["signal_at"]) for row in structural] != [
        str(row["signal_at"]) for row in full_control
    ]:
        raise AssertionError("prepared control identity drift")

    admitted = comp010._apply_comp009_admission(full_control)
    eligible_dates = comp010._eligible_dates(evidence_path)
    return {
        "schema": SCHEMA,
        "control_alias": comp010.LAB_CONTROL_ALIAS,
        "control_research_identity": "COMP009_CONTROL",
        "control_rows": admitted,
        "eligible_dates": eligible_dates,
        "governance": {
            "consumed_evidence_only": True,
            "causal_closed_m1_only": True,
            "next_m1_open_counterfactual_prepared": True,
            "same_comp009_admission": True,
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
            "live_authorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    payload = prepare(args.evidence)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "schema": payload["schema"],
                "trade_count": len(payload["control_rows"]),
                "eligible_session_count": len(payload["eligible_dates"]),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
