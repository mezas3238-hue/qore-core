#!/usr/bin/env python3
"""Prepare reusable Comparator-009 post-entry causal fact ledgers.

Independent GitHub Trader Lab only. Consumed evidence only.
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

import vt31_nas100_breaker_mixed_weak_efficiency_adverse_exit_v1 as weak
import vt31_nas100_bullish_h1_mid_confirmation_conflict_admission_v1 as mid
import vt31_nas100_post_1r_full_cognition_management_frontier_v2 as h3
from qore.infrastructure.traders.vt31_nas100_cibo_causal_structure import (
    causal_structure_events,
)


def d(value: object) -> Decimal:
    return Decimal(str(value))


def iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat()


def reclaim_bucket(value: object) -> str:
    if value is None:
        return "UNKNOWN"
    age = int(value)
    if age < 8:
        return "FRESH_LT8M"
    if age <= 14:
        return "STALE_8_14M"
    return "MATURE_15M_PLUS"


def terminal_r(
    *,
    side: str,
    entry: Decimal,
    stop: Decimal,
    price: Decimal,
) -> Decimal:
    risk = abs(entry - stop)
    if risk <= 0:
        raise ValueError("frozen initial risk must be positive")
    return h3._terminal_r(
        side=side,
        entry=entry,
        price=price,
        risk=risk,
    )


def prepare_one(evidence_path: Path) -> dict[str, Any]:
    original = weak._simulate_candidate
    captures: dict[str, tuple[tuple[object, ...], object, dict[str, object]]] = {}

    def capture(
        day_bars: tuple[object, ...],
        executable: object,
        state: dict[str, object],
    ) -> dict[str, object]:
        outcome = original(day_bars, executable, state)
        if outcome.get("status") == "terminal":
            captures[str(outcome["signal_at"])] = (
                day_bars,
                executable,
                dict(state),
            )
        return outcome

    try:
        weak._simulate_candidate = capture
        structural_rows, comp007_rows = weak._build_candidate_rows(
            evidence_path
        )
    finally:
        weak._simulate_candidate = original

    comp009_rows = [
        row for row in comp007_rows if not mid._conflict(row)
    ]

    prepared_rows: list[dict[str, Any]] = []
    for row in comp009_rows:
        signal_at = str(row["signal_at"])
        if signal_at not in captures:
            raise AssertionError(f"missing causal capture for {signal_at}")
        day_bars, executable, _state = captures[signal_at]
        source = executable.source_setup
        side = str(executable.side.value)
        entry = d(executable.entry_price)
        stop = d(executable.stop_price)
        target = d(executable.target_price)
        structural_level = d(source.structure.structural_level)

        selected = [
            item
            for item in source.candidates
            if item.family.value == str(row["entry_family"])
            and item.formed_at == executable.decision_at
        ]
        if not selected:
            raise AssertionError(
                f"selected entry evidence unavailable for {signal_at}"
            )
        evidence = selected[0]

        by_close = {
            iso(cast(datetime, bar.closed_at)): bar
            for bar in day_bars
        }
        by_open = {
            iso(cast(datetime, bar.opened_at)): bar
            for bar in day_bars
        }

        observations: list[dict[str, Any]] = []
        for raw in cast(
            list[dict[str, object]],
            row.get("cognitive_exit_evaluations", []),
        ):
            observation_at = str(raw["observation_at"])
            bar = by_close.get(observation_at)
            if bar is None:
                raise AssertionError(
                    f"closed M1 not found for {signal_at} @ {observation_at}"
                )
            close = d(bar.close)
            next_bar = by_open.get(observation_at)
            next_open_r = (
                None
                if next_bar is None
                else terminal_r(
                    side=side,
                    entry=entry,
                    stop=stop,
                    price=d(next_bar.open),
                )
            )
            observed_dt = cast(datetime, bar.closed_at)
            causal_path = tuple(
                item
                for item in day_bars
                if cast(datetime, item.closed_at) <= observed_dt
            )
            events = causal_structure_events(
                causal_path,
                source,
                observed_dt,
            )
            last_event = events[-1] if events else None

            structural_failure = (
                close < structural_level
                if side == "long"
                else close > structural_level
            )
            zone_failure = (
                close < d(evidence.zone_lower)
                if side == "long"
                else close > d(evidence.zone_upper)
            )
            adverse_reference_failure = (
                close < d(source.reference.low)
                if side == "long"
                else close > d(source.reference.high)
            )

            observations.append(
                {
                    **raw,
                    "closed_m1_price": format(close, "f"),
                    "next_m1_open_r": (
                        None
                        if next_open_r is None
                        else format(next_open_r, "f")
                    ),
                    "source_structural_level": format(
                        structural_level,
                        "f",
                    ),
                    "selected_zone_lower": format(
                        d(evidence.zone_lower),
                        "f",
                    ),
                    "selected_zone_upper": format(
                        d(evidence.zone_upper),
                        "f",
                    ),
                    "reference_high": format(
                        d(source.reference.high),
                        "f",
                    ),
                    "reference_low": format(
                        d(source.reference.low),
                        "f",
                    ),
                    "closed_back_through_structural_level": (
                        structural_failure
                    ),
                    "closed_through_entry_zone_against_thesis": (
                        zone_failure
                    ),
                    "closed_beyond_adverse_reference_boundary": (
                        adverse_reference_failure
                    ),
                    "reclaim_bucket": reclaim_bucket(
                        raw.get("reference_reclaim_age_minutes")
                    ),
                    "last_causal_event_family": (
                        None if last_event is None else last_event.family
                    ),
                    "last_causal_event_source": (
                        None if last_event is None else last_event.source
                    ),
                    "last_causal_event_age_minutes": (
                        None
                        if last_event is None
                        else max(
                            0,
                            int(
                                (
                                    observed_dt - last_event.observed_at
                                ).total_seconds()
                                // 60
                            ),
                        )
                    ),
                }
            )

        prepared_rows.append(
            {
                "signal_at": signal_at,
                "local_date": row["local_date"],
                "side": side,
                "entry_family": row["entry_family"],
                "control_r_multiple": row["r_multiple"],
                "control_exit_reason": row["exit_reason"],
                "entry_price": format(entry, "f"),
                "initial_stop": format(stop, "f"),
                "primary_target": format(target, "f"),
                "source_structural_level": format(
                    structural_level,
                    "f",
                ),
                "source_swing_extreme": format(
                    d(source.structure.swing_extreme),
                    "f",
                ),
                "selected_zone_lower": format(
                    d(evidence.zone_lower),
                    "f",
                ),
                "selected_zone_upper": format(
                    d(evidence.zone_upper),
                    "f",
                ),
                "reference_high": format(
                    d(source.reference.high),
                    "f",
                ),
                "reference_low": format(
                    d(source.reference.low),
                    "f",
                ),
                "entry_context": row.get("entry_context", {}),
                "observations": observations,
            }
        )

    structural_ids = {str(row["signal_at"]) for row in structural_rows}
    comp009_ids = {row["signal_at"] for row in prepared_rows}
    if not comp009_ids.issubset(structural_ids):
        raise AssertionError("Comparator-009 identity escaped structural pool")

    return {
        "schema": "qore.github-trader-lab.vt31-comp009-post-entry-facts.v1",
        "market": "NAS100",
        "comparator_id": "VT31_AB_COMP009_MAX_INTELLIGENCE_COMPOSED_SURVIVOR",
        "structural_trade_count": len(structural_rows),
        "trade_count": len(prepared_rows),
        "rows": prepared_rows,
        "governance": {
            "observation_only": True,
            "prepared_causal_ledger": True,
            "next_open_is_execution_consequence_only": True,
            "terminal_outcome_runtime_authority": False,
            "fold_identity_runtime_authority": False,
            "date_identity_runtime_authority": False,
            "new_numeric_threshold_added": False,
            "position_sizing_used": False,
            "leverage_used": False,
            "compounding_used": False,
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
                "trade_count": payload["trade_count"],
                "output": str(args.output),
            },
            sort_keys=True,
        ),
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
