"""VT31 sovereign post-1R cognition calibration V2.

Exact sovereign specialist admission is retained. For admitted trades that
reach an unambiguous +1R milestone, observe the predeclared 2/3/5 fully closed
M1 horizons. Future journey is a research label only.

Purpose:
- calibrate deeper journey capacity;
- calibrate contextual position management;
- combine causal post-1R persistence with VT31 full entry cognition;
- never use sizing, volume, leverage, or capital weighting.
"""
# ruff: noqa: B009
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_nas100_full_cognition_attribution_v1 as cognition_lab
import vt31_nas100_ny_delivery_journey_forensics_v1 as journey
import vt31_nas100_post_1r_persistence_forensics_v1 as persistence
import vt31_nas100_specialist_r1_candidate as specialist

from qore.infrastructure.traders.vt31_nas100_position_intelligence import (
    assess_full_cognitive_position,
)

SCHEMA = "qore.vt31.nas100.sovereign_post_1r_cognition_calibration.v2"
HORIZONS = (2, 3, 5)


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _rate(n: int, d: int) -> str | None:
    if d == 0:
        return None
    return format(Decimal(n) / Decimal(d), "f")


def _summary(rows: list[dict[str, object]]) -> dict[str, object]:
    n = len(rows)
    return {
        "sample": n,
        "eventual_3r_plus_rate": _rate(
            sum(bool(row["future_label_eventual_3r_plus"]) for row in rows),
            n,
        ),
        "eventual_5r_plus_rate": _rate(
            sum(bool(row["future_label_eventual_5r_plus"]) for row in rows),
            n,
        ),
        "giveback_after_1r_rate": _rate(
            sum(bool(row["future_label_giveback_after_1r"]) for row in rows),
            n,
        ),
        "journey_classes": dict(
            sorted(
                Counter(
                    str(row["future_label_journey_class"]) for row in rows
                ).items()
            )
        ),
    }


def _group(
    rows: list[dict[str, object]],
    fields: tuple[str, ...],
) -> dict[str, object]:
    groups: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        key = "|".join(f"{field}={row[field]}" for field in fields)
        groups[key].append(row)
    return {
        key: _summary(items)
        for key, items in sorted(groups.items())
    }


def replay(
    evidence_path: Path,
    *,
    partition: str,
) -> dict[str, object]:
    original = specialist._simulate_selected_plan
    observations: list[dict[str, object]] = []
    status: Counter[str] = Counter()

    def simulator(
        day_bars: tuple[object, ...],
        executable: object,
        state: dict[str, object],
    ) -> dict[str, object]:
        outcome = specialist._simulate_structural_boundary_only(
            day_bars,
            executable,
        )

        journey_row = journey._journey(day_bars, executable)
        status[f"journey-{journey_row.get('status')}"] += 1
        if journey_row.get("status") != "labeled":
            return outcome

        fill_index = journey.v2b._fill_index(day_bars, executable)
        if fill_index is None:
            status["no-fill"] += 1
            return outcome

        eligible = tuple(
            bar
            for bar in day_bars[fill_index:]
            if specialist.baseline._local_minute(bar)
            < specialist.LIFECYCLE_MINUTE
        )
        if not eligible:
            status["no-lifecycle-bars"] += 1
            return outcome

        side = str(getattr(getattr(executable, "side"), "value"))
        entry = _d(getattr(executable, "entry_price"))
        stop = _d(getattr(executable, "stop_price"))
        risk = _d(getattr(executable, "initial_risk"))
        if risk <= 0:
            status["invalid-risk"] += 1
            return outcome

        touch_index, touch_status = persistence._first_unambiguous_1r_touch(
            eligible,
            side=side,
            entry=entry,
            stop=stop,
            risk=risk,
        )
        status[f"one-r-{touch_status}"] += 1
        if touch_index is None:
            return outcome

        observation_at = getattr(executable, "decision_at")
        situation = cognition_lab._reconstruct_situation(
            state=state,
            selected=executable,
            source=getattr(executable, "source_setup"),
            observation_at=observation_at,
        )
        reasoning = cognition_lab._reconstruct_reasoning(state)
        cognition = assess_full_cognitive_position(
            situation=situation,
            reasoning=reasoning,
            entry_tier="CORE",
            dol1_acceptance_observed=None,
        )
        if not cognition.maximum_cognition_verified:
            raise AssertionError("partial cognition entered journey calibration")

        local_day = specialist._day(getattr(executable, "decision_at"))
        for horizon in HORIZONS:
            row, observation_status = persistence._observation(
                partition=partition,
                local_day=local_day,
                setup=executable,
                eligible=eligible,
                touch_index=touch_index,
                horizon=horizon,
                journey_row=journey_row,
            )
            status[f"h{horizon}-{observation_status}"] += 1
            if row is None:
                continue
            row.update(
                {
                    "entry_management_context": (
                        cognition.management_context.value
                    ),
                    "entry_protection_urgency": (
                        cognition.protection_urgency.value
                    ),
                    "entry_destination_state": cognition.destination_state,
                    "entry_support_score": cognition.support_score,
                    "entry_caution_score": cognition.caution_score,
                    "entry_m15_state": state.get("m15_state", "unavailable"),
                    "entry_h1_state": state.get("h1_state", "unavailable"),
                    "entry_reference_volatility_state": state.get(
                        "reference_volatility_state",
                        "unavailable",
                    ),
                    "entry_last_structure_event_family": state.get(
                        "last_structure_event_family",
                        "unavailable",
                    ),
                    "maximum_cognition_verified": True,
                }
            )
            observations.append(row)

        return outcome

    try:
        specialist._simulate_selected_plan = simulator
        specialist_payload = specialist.replay(evidence_path)
    finally:
        specialist._simulate_selected_plan = original

    by_horizon: dict[str, object] = {}
    for horizon in HORIZONS:
        items = [
            row
            for row in observations
            if int(row["horizon_closed_bars"]) == horizon
        ]
        by_horizon[str(horizon)] = {
            "overall": _summary(items),
            "by_persistence": _group(items, ("persistence_state",)),
            "by_cognition_x_persistence": _group(
                items,
                (
                    "entry_management_context",
                    "entry_destination_state",
                    "persistence_state",
                ),
            ),
            "by_urgency_x_persistence": _group(
                items,
                (
                    "entry_protection_urgency",
                    "persistence_state",
                ),
            ),
            "by_m15_x_persistence": _group(
                items,
                ("entry_m15_state", "persistence_state"),
            ),
        }

    return {
        "schema": SCHEMA,
        "partition": partition,
        "market": "NAS100",
        "sovereign_trade_count": len(
            cast(list[object], specialist_payload["trades"])
        ),
        "observation_count": len(observations),
        "predeclared_horizons_closed_m1": list(HORIZONS),
        "by_horizon": by_horizon,
        "status_counts": dict(sorted(status.items())),
        "rows": observations,
        "governance": {
            "specialist_replay_is_admission_authority": True,
            "trade_admission_changed": False,
            "entry_changed": False,
            "initial_stop_changed": False,
            "structural_target_changed": False,
            "future_labels_research_only": True,
            "future_labels_used_for_runtime_decision": False,
            "maximum_cognition_required": True,
            "r_runtime_strategy_allowed": True,
            "r_used_for_volume": False,
            "position_sizing_used": False,
            "leverage_used": False,
            "compounding_used": False,
            "capital_weighting_used": False,
            "absolute_volume_used": False,
            "fresh_holdout_opened": False,
            "policy_promoted": False,
            "candidate_frozen": False,
            "candidate_certified": False,
            "live_authorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path)
    parser.add_argument("--partition", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    payload = replay(args.evidence, partition=args.partition)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "partition": payload["partition"],
                "sovereign_trade_count": payload["sovereign_trade_count"],
                "observation_count": payload["observation_count"],
                "by_horizon": payload["by_horizon"],
                "status_counts": payload["status_counts"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
