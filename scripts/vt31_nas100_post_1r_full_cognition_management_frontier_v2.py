"""VT31 NAS100 post-1R full-cognition management frontier V2.

Consumed-evidence research only.

At H2/H3/H5 after the first unambiguous +1R touch, VT31 rebuilds the current
causal Situation Model and reruns full reasoning. Management may act only when
that current cognition is maximum-intelligence ready. Otherwise the trade keeps
its sovereign structural baseline.

No sizing, volume adaptation, leverage, compounding, or capital weighting.
"""
# ruff: noqa: B009
from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import replace
from datetime import UTC
from decimal import Decimal
from pathlib import Path
from typing import cast
from zoneinfo import ZoneInfo

import vt31_nas100_full_cognition_attribution_v1 as cognition_lab
import vt31_nas100_intelligence_policy_lab_v2b as v2b
import vt31_nas100_post_1r_persistence_forensics_v1 as persistence
import vt31_nas100_specialist_r1_candidate as specialist

from qore.infrastructure.traders import vt31_nas100_market_context_runtime as ctx
from qore.infrastructure.traders.vt31_nas100_position_intelligence import (
    ManagementContext,
    assess_full_cognitive_position,
    validate_full_cognitive_accounting_for_research,
    validate_maximum_cognition_for_certification,
)
from qore.infrastructure.traders.vt31_nas100_reasoning_engine import reason

SCHEMA = "qore.vt31.nas100.post_1r_full_cognition_management_frontier.v2"
VARIANTS: dict[str, int | None] = {
    "STRUCTURAL_ONLY": None,
    "H2_FULL_COGNITION": 2,
    "H3_FULL_COGNITION": 3,
    "H5_FULL_COGNITION": 5,
}
_NY = ZoneInfo("America/New_York")


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _opt_d(value: object) -> Decimal | None:
    return None if value is None else Decimal(str(value))


def _terminal_r(
    *,
    side: str,
    entry: Decimal,
    price: Decimal,
    risk: Decimal,
) -> Decimal:
    return (
        (price - entry) / risk
        if side == "long"
        else (entry - price) / risk
    )


def _range_state(ratio: Decimal | None) -> str:
    if ratio is None:
        return "unavailable"
    if ratio < Decimal("0.75"):
        return "compressed"
    if ratio <= Decimal("1.25"):
        return "normal"
    return "expanded"


def _extension_state(persistence_state: str) -> tuple[str, str]:
    if persistence_state in {"PERSISTENT_1R_FLOOR", "RECOVERED_1R_FLOOR"}:
        return "CALIBRATED_POST1R_CONTINUATION_SUPPORTED", "UNKNOWN"
    if persistence_state == "POSITIVE_BELOW_1R":
        return "CALIBRATED_POST1R_CONTINUATION_WEAKENED", "UNKNOWN"
    if persistence_state == "ENTRY_OR_WORSE":
        return (
            "CALIBRATED_POST1R_CONTINUATION_DEPLETED",
            "FAILED_CONTINUATION_CONFIRMED",
        )
    raise ValueError(f"unsupported persistence state: {persistence_state}")


def _current_cognition(
    *,
    day_bars: tuple[object, ...],
    executable: object,
    state: dict[str, object],
    observation_at: object,
    persistence_state: str,
    horizon: int,
):
    entry_situation = cognition_lab._reconstruct_situation(
        state=state,
        selected=executable,
        source=getattr(executable, "source_setup"),
        observation_at=getattr(executable, "decision_at"),
    )
    entry_reasoning = cognition_lab._reconstruct_reasoning(state)

    observed_at = cast(object, observation_at)
    observed_dt = getattr(observed_at, "astimezone")(UTC)
    causal_today = tuple(
        bar
        for bar in day_bars
        if getattr(bar, "closed_at") <= observation_at
    )
    local = getattr(observation_at, "astimezone")(_NY)
    previous_range = _opt_d(state.get("previous_admitted_path_range"))
    current_path = tuple(
        bar
        for bar in causal_today
        if (0, 0, 0)
        <= specialist._wall(getattr(bar, "opened_at"))
        < (16, 0, 0)
    )
    current_range = specialist._interval_range(current_path)
    current_ratio = (
        current_range / previous_range
        if current_range is not None
        and previous_range is not None
        and previous_range > 0
        else None
    )

    h1 = ctx._trend_state(ctx._completed_hour_closes(causal_today, observation_at, 1))
    h4 = ctx._trend_state(ctx._completed_hour_closes(causal_today, observation_at, 4))
    m15 = ctx._trend_state(
        ctx._completed_minute_bucket_closes(causal_today, observation_at, 15)
    )
    premarket = ctx._directional_state(
        ctx._slice(causal_today, (8, 0, 0), (9, 0, 0), observation_at)
    )
    cash_open = ctx._directional_state(
        ctx._slice(causal_today, (9, 30, 0), (10, 0, 0), observation_at)
    )

    source = getattr(executable, "source_setup")
    session_prefix = tuple(
        bar
        for bar in causal_today
        if (10, 0, 0)
        <= specialist._wall(getattr(bar, "opened_at"))
        < (11, 0, 0)
    )
    reclaim_at = specialist._first_reference_reclaim_at(session_prefix, source)
    reclaim_age = (
        None
        if reclaim_at is None
        else int((observation_at - reclaim_at).total_seconds() // 60)
    )
    last_family, last_age = specialist._last_structure_event_family(
        session_prefix,
        source,
        observation_at,
    )
    extension, exhaustion = _extension_state(persistence_state)

    current = replace(
        entry_situation,
        as_of=observed_dt.isoformat(),
        decision_minute_ny=local.hour * 60 + local.minute,
        h4_state=h4,
        h1_state=h1,
        m15_state=m15,
        premarket_state=premarket,
        cash_open_state=cash_open,
        range_state=_range_state(current_ratio),
        current_path_vs_previous=current_ratio,
        raid_depth_ref=ctx._raid_depth_ref(
            causal_today,
            decision_at=observation_at,
            side=str(getattr(getattr(executable, "side"), "value")),
            reference_high=source.reference.high,
            reference_low=source.reference.low,
        ),
        recent_path_efficiency=ctx._recent_efficiency(
            causal_today,
            observation_at,
        ),
        recent_overlap_rate=ctx._recent_overlap(
            causal_today,
            observation_at,
        ),
        reference_reclaimed=reclaim_at is not None,
        reference_reclaim_age_minutes=reclaim_age,
        last_structure_event_family=last_family,
        last_structure_event_age_minutes=last_age,
        journey_stage=f"POST_1R_H{horizon}_{persistence_state}",
        extension_capacity_state=extension,
        exhaustion_state=exhaustion,
    )
    current_reasoning = reason(current)
    cognition = assess_full_cognitive_position(
        situation=current,
        reasoning=entry_reasoning,
        current_reasoning=current_reasoning,
        entry_tier="CORE",
        dol1_acceptance_observed=None,
        entry_situation_fingerprint=entry_situation.fingerprint(),
    )
    validate_full_cognitive_accounting_for_research(cognition)

    max_ready = True
    try:
        validate_maximum_cognition_for_certification(cognition)
    except ValueError:
        max_ready = False

    return current, current_reasoning, cognition, max_ready


def _simulate(
    day_bars: tuple[object, ...],
    executable: object,
    state: dict[str, object],
    *,
    horizon: int | None,
) -> dict[str, object]:
    if horizon is None:
        return specialist._simulate_structural_boundary_only(
            day_bars,
            executable,
        )

    side = str(getattr(getattr(executable, "side"), "value"))
    entry = _d(getattr(executable, "entry_price"))
    initial_stop = _d(getattr(executable, "stop_price"))
    target = _d(getattr(executable, "target_price"))
    risk = abs(entry - initial_stop)
    if risk <= 0:
        return {"status": "censored-invalid-risk"}

    fill_index = v2b._fill_index(day_bars, executable)
    if fill_index is None:
        return {"status": "no-fill"}

    eligible = tuple(
        bar
        for bar in day_bars[fill_index:]
        if specialist.baseline._local_minute(bar)
        < specialist.LIFECYCLE_MINUTE
    )
    if not eligible:
        return {"status": "censored-no-lifecycle"}

    first = eligible[0]
    first_low = _d(getattr(first, "low"))
    first_high = _d(getattr(first, "high"))
    stop_first = (
        first_low <= initial_stop
        if side == "long"
        else first_high >= initial_stop
    )
    target_first = (
        first_high >= target
        if side == "long"
        else first_low <= target
    )
    if stop_first or target_first:
        return {"status": "censored-fill-bar-path"}

    touch_index, touch_status = persistence._first_unambiguous_1r_touch(
        eligible,
        side=side,
        entry=entry,
        stop=initial_stop,
        risk=risk,
    )
    observation_index = (
        None if touch_index is None else touch_index + horizon
    )

    current_stop = initial_stop
    pending_be = False
    be_armed = False
    cognitive_state: str | None = None
    cognitive_action = "NONE"
    current_reasoning_action: str | None = None
    max_ready_at_action: bool | None = None
    max_blockers: list[str] = []
    previous = first
    filled_at = getattr(first, "closed_at")
    exit_price: Decimal | None = None
    exit_at = None
    exit_reason: str | None = None
    max_favorable = Decimal(0)
    max_adverse = Decimal(0)

    for local_index in range(1, len(eligible)):
        bar = eligible[local_index]
        if getattr(bar, "opened_at") != getattr(previous, "closed_at"):
            return {"status": "censored-gap-after-fill"}
        previous = bar

        if pending_be and not be_armed:
            current_stop = entry
            be_armed = True
            pending_be = False

        high = _d(getattr(bar, "high"))
        low = _d(getattr(bar, "low"))
        close = _d(getattr(bar, "close"))
        favorable = high - entry if side == "long" else entry - low
        adverse = entry - low if side == "long" else high - entry
        max_favorable = max(max_favorable, favorable)
        max_adverse = max(max_adverse, adverse)

        stop_now = (
            low <= current_stop if side == "long" else high >= current_stop
        )
        target_now = (
            high >= target if side == "long" else low <= target
        )
        if stop_now and target_now:
            return {"status": "censored-same-bar-stop-target"}
        if stop_now:
            exit_price = current_stop
            exit_at = getattr(bar, "closed_at")
            exit_reason = (
                "full-cognition-breakeven"
                if be_armed
                else "structural-invalidation"
            )
            break
        if target_now:
            exit_price = target
            exit_at = getattr(bar, "closed_at")
            exit_reason = "structural-target"
            break

        if (
            observation_index is not None
            and local_index == observation_index
            and cognitive_state is None
        ):
            post_touch = eligible[touch_index + 1 : observation_index + 1]
            closes_r = [
                _terminal_r(
                    side=side,
                    entry=entry,
                    price=_d(getattr(item, "close")),
                    risk=risk,
                )
                for item in post_touch
            ]
            cognitive_state = persistence._persistence_state(closes_r)
            _, current_reasoning, cognition, max_ready = _current_cognition(
                day_bars=day_bars,
                executable=executable,
                state=state,
                observation_at=getattr(bar, "closed_at"),
                persistence_state=cognitive_state,
                horizon=horizon,
            )
            current_reasoning_action = current_reasoning.action
            max_ready_at_action = max_ready
            max_blockers = list(cognition.reasoning_max_intelligence_blockers)

            if not max_ready:
                cognitive_action = "HOLD_BASELINE_MAX_INTELLIGENCE_BLOCKED"
                continue

            if cognitive_state in {
                "PERSISTENT_1R_FLOOR",
                "RECOVERED_1R_FLOOR",
            }:
                cognitive_action = "HOLD_RUNNER"
            elif cognitive_state == "ENTRY_OR_WORSE":
                exit_price = close
                exit_at = getattr(bar, "closed_at")
                exit_reason = "full-cognition-depleted-exit"
                cognitive_action = "EXIT_DEPLETED_AT_OBSERVATION_CLOSE"
                break
            elif (
                cognitive_state == "POSITIVE_BELOW_1R"
                and (
                    cognition.management_context is ManagementContext.CAUTIOUS
                    or cognition.destination_state == "SHALLOW"
                    or current_reasoning.action != "EXECUTE"
                )
            ):
                pending_be = True
                cognitive_action = "ARM_BE_NEXT_M1"
            else:
                cognitive_action = "HOLD_RUNNER"

    if exit_price is None:
        final = eligible[-1]
        exit_price = _d(getattr(final, "close"))
        exit_at = getattr(final, "closed_at")
        exit_reason = "16:00-lifecycle"

    terminal = _terminal_r(
        side=side,
        entry=entry,
        price=exit_price,
        risk=risk,
    )
    return {
        "status": "terminal",
        "local_date": specialist._day(
            getattr(executable, "decision_at")
        ).isoformat(),
        "side": side,
        "signal_at": getattr(executable, "decision_at").isoformat(),
        "filled_at": filled_at.isoformat(),
        "exit_at": exit_at.isoformat(),
        "entry_family": str(
            getattr(getattr(executable, "selected_family"), "value")
        ),
        "exit_reason": exit_reason,
        "r_multiple": format(terminal, "f"),
        "mfe_r": format(max_favorable / risk, "f"),
        "mae_r": format(max_adverse / risk, "f"),
        "first_1r_touch_status": touch_status,
        "cognitive_horizon": horizon,
        "post_1r_persistence_state": cognitive_state,
        "full_cognition_action": cognitive_action,
        "current_reasoning_action": current_reasoning_action,
        "maximum_intelligence_ready_at_action": max_ready_at_action,
        "maximum_intelligence_blockers": max_blockers,
        "breakeven_armed": be_armed,
        "runtime_r_strategy_used": True,
        "runtime_volume_decision_authority": False,
    }


def replay(evidence_path: Path) -> dict[str, object]:
    original = specialist._simulate_selected_plan
    payloads: dict[str, dict[str, object]] = {}
    try:
        for variant, horizon in VARIANTS.items():
            def simulator(
                day_bars: tuple[object, ...],
                executable: object,
                state: dict[str, object],
                *,
                _horizon: int | None = horizon,
            ) -> dict[str, object]:
                outcome = _simulate(
                    day_bars,
                    executable,
                    state,
                    horizon=_horizon,
                )
                if outcome.get("status") == "terminal":
                    outcome["target_plan"] = state["target_plan"]
                return outcome

            specialist._simulate_selected_plan = simulator
            payloads[variant] = specialist.replay(evidence_path)
    finally:
        specialist._simulate_selected_plan = original

    baseline = cast(
        list[dict[str, object]],
        payloads["STRUCTURAL_ONLY"]["trades"],
    )
    baseline_ids = [str(row["signal_at"]) for row in baseline]
    variants: dict[str, object] = {}

    for variant, payload in payloads.items():
        rows = cast(list[dict[str, object]], payload["trades"])
        if [str(row["signal_at"]) for row in rows] != baseline_ids:
            raise AssertionError(
                f"{variant} changed sovereign terminal population"
            )
        variants[variant] = {
            "trade_count": len(rows),
            "stress_0_05r": payload["stress_0_05r"],
            "monte_carlo": payload["monte_carlo"],
            "halfyear_stress": payload["halfyear_stress"],
            "quarter_stress": payload["quarter_stress"],
            "winner_preservation_vs_structural": (
                None
                if variant == "STRUCTURAL_ONLY"
                else __import__(
                    "vt31_nas100_sovereign_r_management_frontier_v1"
                )._winner_preservation(baseline, rows)
            ),
            "persistence_state_counts": dict(
                sorted(
                    Counter(
                        str(row.get("post_1r_persistence_state"))
                        for row in rows
                    ).items()
                )
            ),
            "full_cognition_action_counts": dict(
                sorted(
                    Counter(
                        str(row.get("full_cognition_action"))
                        for row in rows
                    ).items()
                )
            ),
            "max_ready_action_count": sum(
                row.get("maximum_intelligence_ready_at_action") is True
                for row in rows
            ),
            "max_blocked_action_count": sum(
                row.get("maximum_intelligence_ready_at_action") is False
                for row in rows
            ),
            "breakeven_armed_count": sum(
                row.get("breakeven_armed") is True for row in rows
            ),
        }

    return {
        "schema": SCHEMA,
        "market": "NAS100",
        "variants": variants,
        "governance": {
            "full_post_entry_reasoning_reassessed": True,
            "maximum_intelligence_required_before_management_action": True,
            "blocked_cognition_falls_back_to_structural_baseline": True,
            "same_sovereign_admission_population": True,
            "entry_changed": False,
            "initial_structural_invalidation_changed": False,
            "structural_target_changed": False,
            "lifecycle_changed": False,
            "future_outcome_used_for_runtime_action": False,
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
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    payload = replay(args.evidence)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
