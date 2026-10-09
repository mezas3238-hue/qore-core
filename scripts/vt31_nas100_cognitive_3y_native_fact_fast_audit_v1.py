#!/usr/bin/env python3
"""Read-only VT31 3Y native-fact audit on the ONE consumed development base.

This is a SHADOW sensor: it intercepts the existing specialist's selected
executable while returning its unchanged structural simulation. It does NOT
re-admit, veto, reroute, replay Comparator-010 economics, or open a holdout.
Terminal timestamps are used *only* to classify whether an observed fact
could have reached a next valid open before the control trade ended.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

import vt31_nas100_specialist_r1_candidate as specialist

from qore.infrastructure.traders.vt31_nas100_causal_fact_producers import (
    produce_market_native_facts,
)
from qore.infrastructure.traders.vt31_nas100_market_context_runtime import (
    _completed_hour_closes,
    _trend_state,
)

SCHEMA = "qore.vt31.nas100.cognitive_3y_native_fact_shadow.v1"
BASE_ID = "VT31_NAS100_OWNER_3Y_BASE_001"
BOOLEAN_FACTS = (
    "structure_invalidated",
    "liquidity_failure_confirmed",
    "regime_changed_against_thesis",
)


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _validate(path: Path) -> str:
    payload = json.loads(path.read_text(encoding="utf-8"))
    required = {
        "base_id": BASE_ID,
        "market": "NAS100",
        "base_start_at": "2023-10-01T00:00:00+00:00",
        "base_end_exclusive": "2026-10-01T00:00:00+00:00",
        "coverage_sufficient": True,
        "consumed_for_development_after_first_inspection": True,
    }
    for key, expected in required.items():
        if payload.get(key) != expected:
            raise ValueError(f"non-canonical consumed development input: {key}")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _status_dict(counts: Counter[str]) -> dict[str, int]:
    return dict(sorted(counts.items()))


def audit(evidence_path: Path) -> dict[str, object]:
    digest = _validate(evidence_path)
    state_counts: Counter[str] = Counter()
    event_counts: Counter[str] = Counter()
    actionable_counts: Counter[str] = Counter()
    independent_trade_true_counts: Counter[str] = Counter()
    trade_not_evaluable_counts: Counter[str] = Counter()
    zero_call_trade_ids: list[str] = []
    family_counts: Counter[str] = Counter()
    selected_count = 0
    filled_count = 0
    zero_preterminal_count = 0
    timeline_count = 0
    sample_rows: list[dict[str, object]] = []

    original_simulator = specialist._simulate_selected_plan
    original_mc = specialist._monte_carlo

    def unchanged_simulator(
        day_bars: tuple[Any, ...],
        executable: Any,
        state: dict[str, object],
    ) -> dict[str, object]:
        nonlocal selected_count, filled_count, zero_preterminal_count
        nonlocal timeline_count
        selected_count += 1
        structural = specialist._simulate_structural_boundary_only(
            day_bars, executable
        )
        family = str(executable.selected_family.value)
        family_counts[family] += 1
        state_counts[str(structural["status"])] += 1

        fill_index = specialist.v2b._fill_index(day_bars, executable)
        if fill_index is None:
            return structural
        filled_count += 1
        fill_bar = day_bars[fill_index]
        # Ambiguous fill-bar paths are censored, not open trades. Do not
        # invent hundreds of post-entry cognitive calls on these fills.
        if structural["status"] != "terminal":
            if len(sample_rows) < 14:
                sample_rows.append({
                    "signal_at": executable.decision_at.isoformat(),
                    "entry_family": family,
                    "fill_open_at": fill_bar.opened_at.isoformat(),
                    "structural_status": structural["status"],
                    "preterminal_closed_m1_observations": 0,
                    "excluded_from_cognitive_denominator": True,
                    "exit_at": None,
                })
            return structural
        fill_open = cast(datetime, fill_bar.opened_at)
        if fill_open < executable.decision_at:
            raise AssertionError("fill precedes signal")
        stop = _d(executable.stop_price)
        target = _d(executable.target_price)
        side = str(executable.side.value)
        source = executable.source_setup
        reclaim_observed = state.get("reference_reclaim_age_minutes") is not None
        liquidity_boundary = (
            _d(source.reference.low)
            if side == "long"
            else _d(source.reference.high)
        )
        entry_regime = str(state.get("h1_state", "unavailable"))

        # Structural control is unchanged. Only its actually closed M1 path is
        # shadow-observed; the terminal bar cannot route an action before exit.
        exit_at = datetime.fromisoformat(str(structural["exit_at"]))
        causal_closed: list[Any] = []
        preterminal = 0
        true_in_trade: set[str] = set()
        not_evaluable_in_trade: set[str] = set()
        # Existing control invokes post-fill cognition only after the
        # filling candle. The terminal candle has already closed a position
        # before a next-open actuator could act. Both are out of scope.
        for bar in day_bars[fill_index + 1:]:
            at = cast(datetime, bar.closed_at)
            if at >= exit_at:
                break
            if specialist.baseline._local_minute(bar) >= specialist.LIFECYCLE_MINUTE:
                break
            causal_closed.append(bar)
            h1 = _trend_state(_completed_hour_closes(
                cast(tuple[Any, ...], day_bars),
                at,
                1,
            ))
            # Do not use contemporaneous terminal status/return as a producer.
            touched = (
                _d(bar.high) >= target if side == "long"
                else _d(bar.low) <= target
            )
            accepted = (
                _d(bar.close) > target if side == "long"
                else _d(bar.close) < target
            ) if touched else False
            facts = produce_market_native_facts(
                bars_since_fill=causal_closed,
                as_of=at,
                side=side,
                structural_invalidation_level=stop,
                liquidity_failure_boundary=liquidity_boundary,
                reference_reclaim_confirmed_at_entry=reclaim_observed,
                entry_regime=entry_regime,
                current_regime=h1,
                regime_observed_at=at if h1 != "unavailable" else None,
                primary_target=target,
                primary_target_reached=touched,
                primary_target_accepted=accepted,
                # DO NOT invent the next market-confirmed target.
                confirmed_next_destinations=(),
            )
            timeline_count += 1
            preterminal += 1
            for name in BOOLEAN_FACTS:
                fact = getattr(facts, name)
                key = f"{name}:{fact.status}:{fact.value}"
                event_counts[key] += 1
                if fact.value is True:
                    actionable_counts[name] += 1
                    true_in_trade.add(name)
                if fact.status == "NOT_EVALUABLE":
                    not_evaluable_in_trade.add(name)
            target_fact = facts.next_structural_target
            event_counts[
                f"next_structural_target:{target_fact.status}"
            ] += 1

        for name in true_in_trade:
            independent_trade_true_counts[name] += 1
        for name in not_evaluable_in_trade:
            trade_not_evaluable_counts[name] += 1
        if preterminal == 0:
            zero_preterminal_count += 1
            zero_call_trade_ids.append(executable.decision_at.isoformat())
        if len(sample_rows) < 14:
            sample_rows.append({
                "signal_at": executable.decision_at.isoformat(),
                "entry_family": family,
                "fill_open_at": fill_open.isoformat(),
                "structural_status": structural["status"],
                "preterminal_closed_m1_observations": preterminal,
                "exit_at": exit_at.isoformat(),
                "excluded_from_cognitive_denominator": False,
            })
        return structural

    try:
        specialist._simulate_selected_plan = unchanged_simulator
        specialist._monte_carlo = lambda _: {
            "status": "NOT_RUN_SHADOW_SENSOR_AUDIT",
            "paths": 0,
            "positive_terminal_probability": "0",
            "p95_max_drawdown_r": "0",
        }
        actual = specialist.replay(evidence_path)
    finally:
        specialist._simulate_selected_plan = original_simulator
        specialist._monte_carlo = original_mc

    if selected_count != sum(family_counts.values()):
        raise AssertionError("source-family sensor accounting mismatch")
    if selected_count != sum(state_counts.values()):
        raise AssertionError("structural disposition sensor accounting mismatch")
    if int(actual["trade_count"]) != state_counts["terminal"]:
        raise AssertionError("shadow changed structural terminal count")
    return {
        "schema": SCHEMA,
        "base_id": BASE_ID,
        "base_sha256": digest,
        "selected_source_count": selected_count,
        "prospective_filled_count": filled_count,
        "structural_terminal_count": int(actual["trade_count"]),
        "zero_preterminal_closed_m1_count": zero_preterminal_count,
        "total_shadow_closed_m1_observations": timeline_count,
        "structural_dispositions": _status_dict(state_counts),
        "selected_families": _status_dict(family_counts),
        "native_fact_event_counts": _status_dict(event_counts),
        "preterminal_true_observation_counts": _status_dict(actionable_counts),
        "independent_trades_with_true_fact_counts": _status_dict(
            independent_trade_true_counts
        ),
        "trades_with_not_evaluable_fact_counts": _status_dict(
            trade_not_evaluable_counts
        ),
        "zero_call_structural_trade_signal_ids": sorted(zero_call_trade_ids),
        "example_structural_lifecycles": sample_rows,
        "governance": {
            "consumed_development_evidence_only": True,
            "source_selection_control_unchanged": True,
            "structural_control_returned_unchanged": True,
            "comparator010_replay_run": False,
            "fill_revalidation_execution_authority": False,
            "post_entry_actions_executed": False,
            "read_only_observation": True,
            "next_target_missing_not_fabricated": True,
            "future_bar_used_for_producer": False,
            "terminal_outcome_used_for_producer": False,
            "terminal_timestamp_used_only_for_sensor_attribution": True,
            "censored_fills_excluded_from_cognition_denominator": True,
            "fill_candle_and_terminal_candle_excluded": True,
            "r5_r6_r8_operating_folds_used": False,
            "fresh_holdout_opened": False,
            "sizing_or_leverage_used": False,
            "candidate_certified": False,
            "live_authorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = audit(args.evidence)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
