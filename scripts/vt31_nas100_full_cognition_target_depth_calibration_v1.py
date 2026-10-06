"""VT31 NAS100 full-cognition target-depth calibration V1.

Consumed-evidence diagnostic only.

Uses the exact sovereign specialist admission population.  It separates:
- DOL1 touch: first M1 high/low reaches the frozen structural boundary;
- DOL1 acceptance: a *subsequent fully closed M1* closes beyond DOL1 in the
  trade direction.

Only after acceptance are DOL2/DOL3/DOL4 future reaches labeled.  Those labels
are research-only and never runtime inputs.

The predeclared H3 post-1R cognition checkpoint is attributed only when its
closed-bar observation existed no later than DOL1 acceptance.
"""
# ruff: noqa: B009
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_nas100_high_density_structural_protection_v1 as protection
import vt31_nas100_intelligence_policy_lab_v2b as v2b
import vt31_nas100_post_1r_full_cognition_management_frontier_v2 as post1r
import vt31_nas100_post_1r_persistence_forensics_v1 as persistence
import vt31_nas100_specialist_r1_candidate as specialist

SCHEMA = "qore.vt31.nas100.full_cognition_target_depth_calibration.v1"
H3 = 3


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _direction(side: str) -> Decimal:
    return Decimal(1) if side == "long" else Decimal(-1)


def _beyond(side: str, value: Decimal, level: Decimal) -> bool:
    return value > level if side == "long" else value < level


def _touch(side: str, bar: object, level: Decimal) -> bool:
    high = _d(getattr(bar, "high"))
    low = _d(getattr(bar, "low"))
    return high >= level if side == "long" else low <= level


def _inside_primary(side: str, close: Decimal, dol1: Decimal) -> bool:
    return close < dol1 if side == "long" else close > dol1


def _stop_hit(side: str, bar: object, stop: Decimal) -> bool:
    high = _d(getattr(bar, "high"))
    low = _d(getattr(bar, "low"))
    return low <= stop if side == "long" else high >= stop


def _minutes(left: datetime, right: datetime) -> int:
    return int((right - left).total_seconds() // 60)


def _rate(rows: list[dict[str, object]], field: str) -> str | None:
    if not rows:
        return None
    return format(
        Decimal(sum(bool(row[field]) for row in rows)) / Decimal(len(rows)),
        "f",
    )


def _depth_stats(rows: list[dict[str, object]]) -> dict[str, object]:
    accepted = [row for row in rows if row["dol1_accepted"] is True]
    return {
        "sample": len(rows),
        "dol1_touch_count": sum(row["dol1_touched"] is True for row in rows),
        "dol1_accept_count": len(accepted),
        "dol1_accept_rate": _rate(rows, "dol1_accepted"),
        "dol2_reach_rate_after_acceptance": _rate(accepted, "dol2_reached"),
        "dol3_reach_rate_after_acceptance": _rate(accepted, "dol3_reached"),
        "dol4_reach_rate_after_acceptance": _rate(accepted, "dol4_reached"),
        "close_back_inside_dol1_rate_after_acceptance": _rate(
            accepted,
            "closed_back_inside_dol1_before_dol2",
        ),
    }


def _group_stats(
    rows: list[dict[str, object]],
    fields: tuple[str, ...],
) -> dict[str, object]:
    groups: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        key = "|".join(f"{field}={row.get(field)}" for field in fields)
        groups[key].append(row)
    return {
        key: _depth_stats(items)
        for key, items in sorted(groups.items())
    }


def _h3_context(
    *,
    day_bars: tuple[object, ...],
    executable: object,
    state: dict[str, object],
    eligible: tuple[object, ...],
    acceptance_at: datetime,
) -> dict[str, object]:
    side = str(getattr(getattr(executable, "side"), "value"))
    entry = _d(getattr(executable, "entry_price"))
    stop = _d(getattr(executable, "stop_price"))
    risk = abs(entry - stop)
    touch_index, touch_status = persistence._first_unambiguous_1r_touch(
        eligible,
        side=side,
        entry=entry,
        stop=stop,
        risk=risk,
    )
    if touch_index is None:
        return {
            "h3_available_before_acceptance": False,
            "h3_unavailable_reason": f"1R:{touch_status}",
        }

    observation_index = touch_index + H3
    if observation_index >= len(eligible):
        return {
            "h3_available_before_acceptance": False,
            "h3_unavailable_reason": "H3_OUTSIDE_LIFECYCLE",
        }
    observation_bar = eligible[observation_index]
    observation_at = cast(datetime, getattr(observation_bar, "closed_at"))
    if observation_at > acceptance_at:
        return {
            "h3_available_before_acceptance": False,
            "h3_unavailable_reason": "H3_AFTER_DOL1_ACCEPTANCE",
        }

    post_touch = eligible[touch_index + 1 : observation_index + 1]
    closes_r = [
        post1r._terminal_r(
            side=side,
            entry=entry,
            price=_d(getattr(bar, "close")),
            risk=risk,
        )
        for bar in post_touch
    ]
    persistence_state = persistence._persistence_state(closes_r)
    (
        _,
        current_reasoning,
        cognition,
        management_ready,
        maximum_intelligence_ready,
    ) = post1r._current_cognition(
        day_bars=day_bars,
        executable=executable,
        state=state,
        observation_at=observation_at,
        persistence_state=persistence_state,
        horizon=H3,
    )
    return {
        "h3_available_before_acceptance": True,
        "h3_observed_at": observation_at.astimezone(UTC).isoformat(),
        "h3_persistence_state": persistence_state,
        "h3_management_context": cognition.management_context.value,
        "h3_destination_state": cognition.destination_state,
        "h3_reasoning_action": current_reasoning.action,
        "h3_protection_urgency": cognition.protection_urgency.value,
        "h3_support_score": cognition.support_score,
        "h3_caution_score": cognition.caution_score,
        "h3_contextual_management_ready": management_ready,
        "h3_maximum_intelligence_ready": maximum_intelligence_ready,
        "h3_maximum_intelligence_blockers": list(
            cognition.reasoning_max_intelligence_blockers
        ),
    }


def _diagnose(
    day_bars: tuple[object, ...],
    executable: object,
    state: dict[str, object],
) -> dict[str, object] | None:
    side = str(getattr(getattr(executable, "side"), "value"))
    entry = _d(getattr(executable, "entry_price"))
    stop = _d(getattr(executable, "stop_price"))
    dol1 = _d(getattr(executable, "target_price"))
    source = getattr(executable, "source_setup")
    width = _d(source.reference.high) - _d(source.reference.low)
    if width <= 0:
        return None

    direction = _direction(side)
    dol2 = dol1 + direction * width * Decimal("0.25")
    dol3 = dol1 + direction * width * Decimal("0.50")
    dol4 = dol1 + direction * width * Decimal("1.00")

    fill_index = v2b._fill_index(day_bars, executable)
    if fill_index is None:
        return None
    eligible = tuple(
        bar
        for bar in day_bars[fill_index:]
        if specialist.baseline._local_minute(bar)
        < specialist.LIFECYCLE_MINUTE
    )
    if not eligible:
        return None

    touch_index: int | None = None
    acceptance_index: int | None = None
    invalidated_before_touch = False
    invalidated_before_acceptance = False

    for index, bar in enumerate(eligible):
        if _stop_hit(side, bar, stop):
            if touch_index is None:
                invalidated_before_touch = True
                break
            invalidated_before_acceptance = True
            break
        if touch_index is None and _touch(side, bar, dol1):
            touch_index = index
            continue
        if touch_index is not None and index > touch_index:
            close = _d(getattr(bar, "close"))
            if _beyond(side, close, dol1):
                acceptance_index = index
                break

    base = {
        "signal_at": getattr(executable, "decision_at").astimezone(UTC).isoformat(),
        "local_date": specialist._day(
            getattr(executable, "decision_at")
        ).isoformat(),
        "side": side,
        "entry_family": str(
            getattr(getattr(executable, "selected_family"), "value")
        ),
        "entry": format(entry, "f"),
        "initial_stop": format(stop, "f"),
        "reference_width": format(width, "f"),
        "dol1": format(dol1, "f"),
        "dol2": format(dol2, "f"),
        "dol3": format(dol3, "f"),
        "dol4": format(dol4, "f"),
        "h1_state": state.get("h1_state"),
        "m15_state": state.get("m15_state"),
        "reference_volatility_state": state.get(
            "reference_volatility_state"
        ),
        "entry_management_context": state.get("management_context_state"),
        "entry_journey_capacity_state": state.get("journey_capacity_state"),
        "dol1_touched": touch_index is not None,
        "dol1_accepted": acceptance_index is not None,
        "invalidated_before_dol1_touch": invalidated_before_touch,
        "invalidated_before_dol1_acceptance": invalidated_before_acceptance,
        "future_depth_labels_runtime_input": False,
    }
    if touch_index is None:
        return {
            **base,
            "dol1_outcome": (
                "INVALIDATED_BEFORE_TOUCH"
                if invalidated_before_touch
                else "NO_TOUCH_BY_LIFECYCLE"
            ),
            "dol2_reached": False,
            "dol3_reached": False,
            "dol4_reached": False,
            "closed_back_inside_dol1_before_dol2": False,
        }

    touch_at = cast(datetime, getattr(eligible[touch_index], "closed_at"))
    base["dol1_touch_at"] = touch_at.astimezone(UTC).isoformat()
    if acceptance_index is None:
        return {
            **base,
            "dol1_outcome": (
                "INVALIDATED_AFTER_TOUCH_BEFORE_ACCEPTANCE"
                if invalidated_before_acceptance
                else "TOUCHED_NOT_ACCEPTED_BY_LIFECYCLE"
            ),
            "dol2_reached": False,
            "dol3_reached": False,
            "dol4_reached": False,
            "closed_back_inside_dol1_before_dol2": False,
        }

    acceptance_bar = eligible[acceptance_index]
    acceptance_at = cast(datetime, getattr(acceptance_bar, "closed_at"))
    h3 = _h3_context(
        day_bars=day_bars,
        executable=executable,
        state=state,
        eligible=eligible,
        acceptance_at=acceptance_at,
    )

    dol2_reached = False
    dol3_reached = False
    dol4_reached = False
    dol2_at: datetime | None = None
    dol3_at: datetime | None = None
    dol4_at: datetime | None = None
    back_inside_before_dol2 = False
    max_adverse_after_acceptance = Decimal(0)
    first_protective_swing_before_dol2: Decimal | None = None

    for index in range(acceptance_index + 1, len(eligible)):
        bar = eligible[index]
        if _stop_hit(side, bar, stop):
            break
        high = _d(getattr(bar, "high"))
        low = _d(getattr(bar, "low"))
        close = _d(getattr(bar, "close"))
        adverse = (
            dol1 - low if side == "long" else high - dol1
        )
        max_adverse_after_acceptance = max(
            max_adverse_after_acceptance,
            adverse,
            Decimal(0),
        )

        if not dol2_reached and _inside_primary(side, close, dol1):
            back_inside_before_dol2 = True

        if first_protective_swing_before_dol2 is None and not dol2_reached:
            candidate = protection._protective_swing_level(
                eligible,
                index,
                side,
            )
            if candidate is not None:
                first_protective_swing_before_dol2 = candidate

        if not dol2_reached and (
            high >= dol2 if side == "long" else low <= dol2
        ):
            dol2_reached = True
            dol2_at = cast(datetime, getattr(bar, "closed_at"))
        if not dol3_reached and (
            high >= dol3 if side == "long" else low <= dol3
        ):
            dol3_reached = True
            dol3_at = cast(datetime, getattr(bar, "closed_at"))
        if not dol4_reached and (
            high >= dol4 if side == "long" else low <= dol4
        ):
            dol4_reached = True
            dol4_at = cast(datetime, getattr(bar, "closed_at"))

    deepest = (
        "DOL4"
        if dol4_reached
        else "DOL3"
        if dol3_reached
        else "DOL2"
        if dol2_reached
        else "DOL1"
    )
    return {
        **base,
        **h3,
        "dol1_outcome": "ACCEPTED",
        "dol1_accept_at": acceptance_at.astimezone(UTC).isoformat(),
        "minutes_touch_to_accept": _minutes(touch_at, acceptance_at),
        "dol2_reached": dol2_reached,
        "dol3_reached": dol3_reached,
        "dol4_reached": dol4_reached,
        "minutes_accept_to_dol2": (
            None if dol2_at is None else _minutes(acceptance_at, dol2_at)
        ),
        "minutes_accept_to_dol3": (
            None if dol3_at is None else _minutes(acceptance_at, dol3_at)
        ),
        "minutes_accept_to_dol4": (
            None if dol4_at is None else _minutes(acceptance_at, dol4_at)
        ),
        "deepest_dol_reached": deepest,
        "closed_back_inside_dol1_before_dol2": back_inside_before_dol2,
        "max_adverse_points_after_acceptance": format(
            max_adverse_after_acceptance,
            "f",
        ),
        "protective_swing_before_dol2": (
            None
            if first_protective_swing_before_dol2 is None
            else format(first_protective_swing_before_dol2, "f")
        ),
    }


def replay(evidence_path: Path, *, partition: str) -> dict[str, object]:
    original = specialist._simulate_selected_plan
    observations: list[dict[str, object]] = []

    def simulator(
        day_bars: tuple[object, ...],
        executable: object,
        state: dict[str, object],
    ) -> dict[str, object]:
        row = _diagnose(day_bars, executable, state)
        if row is not None:
            observations.append(row)
        return specialist._simulate_structural_boundary_only(
            day_bars,
            executable,
        )

    try:
        specialist._simulate_selected_plan = simulator
        payload = specialist.replay(evidence_path)
    finally:
        specialist._simulate_selected_plan = original

    terminal = cast(list[dict[str, object]], payload["trades"])
    signal_ids = {str(row["signal_at"]) for row in terminal}
    diagnostic_ids = {str(row["signal_at"]) for row in observations}
    if not diagnostic_ids.issubset(signal_ids):
        raise AssertionError("target-depth diagnostic changed sovereign population")

    return {
        "schema": SCHEMA,
        "partition": partition,
        "market": "NAS100",
        "sovereign_trade_count": len(terminal),
        "diagnostic_count": len(observations),
        "overall": _depth_stats(observations),
        "by_dol1_outcome": _group_stats(observations, ("dol1_outcome",)),
        "by_h3_persistence": _group_stats(
            observations,
            ("h3_persistence_state",),
        ),
        "by_h3_cognition": _group_stats(
            observations,
            (
                "h3_management_context",
                "h3_destination_state",
                "h3_reasoning_action",
            ),
        ),
        "by_entry_family": _group_stats(observations, ("entry_family",)),
        "by_side": _group_stats(observations, ("side",)),
        "by_h1": _group_stats(observations, ("h1_state",)),
        "by_m15": _group_stats(observations, ("m15_state",)),
        "by_volatility": _group_stats(
            observations,
            ("reference_volatility_state",),
        ),
        "rows": observations,
        "governance": {
            "specialist_replay_is_admission_authority": True,
            "trade_admission_changed": False,
            "entry_changed": False,
            "initial_stop_changed": False,
            "primary_structural_target_changed": False,
            "h3_must_precede_dol1_acceptance_for_attribution": True,
            "dol1_touch_is_not_acceptance": True,
            "dol1_acceptance_requires_subsequent_closed_m1": True,
            "future_depth_labels_research_only": True,
            "future_depth_labels_runtime_input": False,
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
                "diagnostic_count": payload["diagnostic_count"],
                "overall": payload["overall"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
