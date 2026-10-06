"""VT31 NAS100 DOL2 reloss full-cognition frontier V1.

Consumed-evidence research on the exact sovereign specialist population.

Base mechanism:
- soft DOL1 window = 3 fully closed M1 bars;
- acceptance = subsequent closed M1 beyond DOL1;
- DOL2 = DOL1 +/- 0.25 frozen reference width;
- DOL2 active from the next M1.

After acceptance, a closed M1 back inside DOL1 is a causal reloss event.

Variants:
- DOL1_HARD_EXIT
- W3_DOL2_ALL
- W3_DOL2_RELOSS_EXIT
- W3_DOL2_RELOSS_FULL_COGNITION

The cognition variant keeps the runner only when current position reasoning is
EXECUTE, contextual management is ready, and post-1R persistence remains
PERSISTENT or RECOVERED.

No sizing, leverage, compounding, capital weighting, volume adaptation or
future target labels.
"""
# ruff: noqa: B009
from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_nas100_full_cognition_attribution_v1 as cognition_lab
import vt31_nas100_intelligence_policy_lab_v2b as v2b
import vt31_nas100_post_1r_full_cognition_management_frontier_v2 as post1r
import vt31_nas100_post_1r_persistence_forensics_v1 as persistence
import vt31_nas100_sovereign_r_management_frontier_v1 as r_frontier
import vt31_nas100_specialist_r1_candidate as specialist

from qore.infrastructure.traders.vt31_nas100_position_intelligence import (
    assess_full_cognitive_position,
    validate_contextual_management_readiness_for_research,
)
from qore.infrastructure.traders.vt31_nas100_reasoning_engine import (
    reason_position,
)

SCHEMA = "qore.vt31.nas100.dol2_reloss_full_cognition_frontier.v1"
WINDOW = 3
OFFSET_REF = Decimal("0.25")
CONTINUATION_STATES = {
    "PERSISTENT_1R_FLOOR",
    "RECOVERED_1R_FLOOR",
}
VARIANTS = (
    "DOL1_HARD_EXIT",
    "W3_DOL2_ALL",
    "W3_DOL2_RELOSS_EXIT",
    "W3_DOL2_RELOSS_FULL_COGNITION",
)


def _d(value: object) -> Decimal:
    return Decimal(str(value))


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


def _stop_hit(side: str, bar: object, stop: Decimal) -> bool:
    high = _d(getattr(bar, "high"))
    low = _d(getattr(bar, "low"))
    return low <= stop if side == "long" else high >= stop


def _target_hit(side: str, bar: object, target: Decimal) -> bool:
    high = _d(getattr(bar, "high"))
    low = _d(getattr(bar, "low"))
    return high >= target if side == "long" else low <= target


def _accepted(side: str, close: Decimal, dol1: Decimal) -> bool:
    return close > dol1 if side == "long" else close < dol1


def _inside(side: str, close: Decimal, dol1: Decimal) -> bool:
    return close < dol1 if side == "long" else close > dol1


def _current_cognition_at(
    *,
    day_bars: tuple[object, ...],
    eligible: tuple[object, ...],
    executable: object,
    state: dict[str, object],
    current_index: int,
) -> dict[str, object]:
    side = str(getattr(getattr(executable, "side"), "value"))
    entry = _d(getattr(executable, "entry_price"))
    stop = _d(getattr(executable, "stop_price"))
    risk = abs(entry - stop)

    one_r_index, one_r_status = persistence._first_unambiguous_1r_touch(
        eligible,
        side=side,
        entry=entry,
        stop=stop,
        risk=risk,
    )
    if one_r_index is None or one_r_index >= current_index:
        return {
            "available": False,
            "reason": f"NO_CAUSAL_1R_STATE:{one_r_status}",
            "persistence_state": None,
            "management_ready": False,
            "reasoning_action": None,
            "management_context": None,
            "destination_state": None,
            "blockers": [],
        }

    closes_r = [
        _terminal_r(
            side=side,
            entry=entry,
            price=_d(getattr(bar, "close")),
            risk=risk,
        )
        for bar in eligible[one_r_index + 1 : current_index + 1]
    ]
    persistence_state = persistence._persistence_state(closes_r)
    horizon = current_index - one_r_index

    (
        current,
        _,
        _,
        _,
        _,
    ) = post1r._current_cognition(
        day_bars=day_bars,
        executable=executable,
        state=state,
        observation_at=getattr(eligible[current_index], "closed_at"),
        persistence_state=persistence_state,
        horizon=horizon,
    )
    entry_situation = cognition_lab._reconstruct_situation(
        state=state,
        selected=executable,
        source=getattr(executable, "source_setup"),
        observation_at=getattr(executable, "decision_at"),
    )
    entry_reasoning = cognition_lab._reconstruct_reasoning(state)

    accepted_current = replace(
        current,
        dol1_state="REACHED_ACCEPTED_CLOSED_M1",
    )
    current_reasoning = reason_position(
        accepted_current,
        frozen_entry_reasoning=entry_reasoning,
    )
    cognition = assess_full_cognitive_position(
        situation=accepted_current,
        reasoning=entry_reasoning,
        current_reasoning=current_reasoning,
        entry_tier="CORE",
        dol1_acceptance_observed=True,
        entry_situation_fingerprint=entry_situation.fingerprint(),
    )

    try:
        validate_contextual_management_readiness_for_research(cognition)
        management_ready = True
    except ValueError:
        management_ready = False

    return {
        "available": True,
        "reason": "FULL_COGNITION_AT_RELOSS",
        "persistence_state": persistence_state,
        "management_ready": management_ready,
        "reasoning_action": current_reasoning.action,
        "management_context": cognition.management_context.value,
        "destination_state": cognition.destination_state,
        "blockers": list(cognition.reasoning_max_intelligence_blockers),
    }


def _cognition_holds(cognition: dict[str, object]) -> bool:
    return bool(
        cognition["available"] is True
        and cognition["management_ready"] is True
        and cognition["reasoning_action"] == "EXECUTE"
        and cognition["persistence_state"] in CONTINUATION_STATES
    )


def _simulate(
    day_bars: tuple[object, ...],
    executable: object,
    state: dict[str, object],
    *,
    variant: str,
) -> dict[str, object]:
    if variant == "DOL1_HARD_EXIT":
        return specialist._simulate_structural_boundary_only(
            day_bars,
            executable,
        )

    side = str(getattr(getattr(executable, "side"), "value"))
    entry = _d(getattr(executable, "entry_price"))
    stop = _d(getattr(executable, "stop_price"))
    dol1 = _d(getattr(executable, "target_price"))
    risk = abs(entry - stop)
    source = getattr(executable, "source_setup")
    width = _d(source.reference.high) - _d(source.reference.low)
    if risk <= 0 or width <= 0:
        return {"status": "censored-invalid-geometry"}

    direction = Decimal(1) if side == "long" else Decimal(-1)
    dol2 = dol1 + direction * OFFSET_REF * width

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
    if _stop_hit(side, first, stop) or _target_hit(side, first, dol1):
        return {"status": "censored-fill-bar-path"}

    touch_index: int | None = None
    acceptance_index: int | None = None
    extension_active = False
    reloss_count = 0
    cognition_hold_count = 0
    cognition_exit_count = 0
    last_cognition: dict[str, object] | None = None
    previous = first
    filled_at = getattr(first, "closed_at")
    exit_price: Decimal | None = None
    exit_at = None
    exit_reason: str | None = None

    for index in range(1, len(eligible)):
        bar = eligible[index]
        if getattr(bar, "opened_at") != getattr(previous, "closed_at"):
            return {"status": "censored-gap-after-fill"}
        previous = bar

        if _stop_hit(side, bar, stop):
            exit_price = stop
            exit_at = getattr(bar, "closed_at")
            exit_reason = "structural-invalidation"
            break

        if extension_active:
            if _target_hit(side, bar, dol2):
                exit_price = dol2
                exit_at = getattr(bar, "closed_at")
                exit_reason = "dol2-extended-target"
                break

            close = _d(getattr(bar, "close"))
            if _inside(side, close, dol1):
                reloss_count += 1
                if variant == "W3_DOL2_RELOSS_EXIT":
                    exit_price = close
                    exit_at = getattr(bar, "closed_at")
                    exit_reason = "dol1-reloss-exit"
                    break

                if variant == "W3_DOL2_RELOSS_FULL_COGNITION":
                    cognition = _current_cognition_at(
                        day_bars=day_bars,
                        eligible=eligible,
                        executable=executable,
                        state=state,
                        current_index=index,
                    )
                    last_cognition = cognition
                    if _cognition_holds(cognition):
                        cognition_hold_count += 1
                        continue
                    cognition_exit_count += 1
                    exit_price = close
                    exit_at = getattr(bar, "closed_at")
                    exit_reason = "dol1-reloss-full-cognition-exit"
                    break
            continue

        if touch_index is None:
            if _target_hit(side, bar, dol1):
                touch_index = index
            continue

        bars_after_touch = index - touch_index
        close = _d(getattr(bar, "close"))
        if _accepted(side, close, dol1):
            acceptance_index = index
            extension_active = True
            # DOL2 becomes active only from the next M1.
            continue

        if bars_after_touch >= WINDOW:
            exit_price = close
            exit_at = getattr(bar, "closed_at")
            exit_reason = "soft-dol1-acceptance-timeout"
            break

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
        "dol1_touched": touch_index is not None,
        "dol1_accepted": acceptance_index is not None,
        "extension_active": extension_active,
        "reloss_count": reloss_count,
        "cognition_hold_count": cognition_hold_count,
        "cognition_exit_count": cognition_exit_count,
        "last_reloss_cognition": last_cognition,
        "runtime_volume_decision_authority": False,
    }


def replay(evidence_path: Path) -> dict[str, object]:
    original = specialist._simulate_selected_plan
    payloads: dict[str, dict[str, object]] = {}
    try:
        for variant in VARIANTS:

            def simulator(
                day_bars: tuple[object, ...],
                executable: object,
                state: dict[str, object],
                *,
                _variant: str = variant,
            ) -> dict[str, object]:
                outcome = _simulate(
                    day_bars,
                    executable,
                    state,
                    variant=_variant,
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
        payloads["DOL1_HARD_EXIT"]["trades"],
    )
    baseline_ids = [str(row["signal_at"]) for row in baseline]
    reports: dict[str, object] = {}

    for variant, payload in payloads.items():
        rows = cast(list[dict[str, object]], payload["trades"])
        if [str(row["signal_at"]) for row in rows] != baseline_ids:
            raise AssertionError(
                f"{variant} changed sovereign terminal population"
            )
        reports[variant] = {
            "trade_count": len(rows),
            "stress_0_05r": payload["stress_0_05r"],
            "monte_carlo": payload["monte_carlo"],
            "halfyear_stress": payload["halfyear_stress"],
            "quarter_stress": payload["quarter_stress"],
            "winner_preservation_vs_dol1": (
                None
                if variant == "DOL1_HARD_EXIT"
                else r_frontier._winner_preservation(baseline, rows)
            ),
            "extension_active_count": sum(
                row.get("extension_active") is True for row in rows
            ),
            "reloss_trade_count": sum(
                int(row.get("reloss_count", 0)) > 0 for row in rows
            ),
            "cognition_hold_count": sum(
                int(row.get("cognition_hold_count", 0)) for row in rows
            ),
            "cognition_exit_count": sum(
                int(row.get("cognition_exit_count", 0)) for row in rows
            ),
            "exit_reasons": dict(
                sorted(Counter(str(row["exit_reason"]) for row in rows).items())
            ),
        }

    return {
        "schema": SCHEMA,
        "market": "NAS100",
        "variants": reports,
        "governance": {
            "same_sovereign_terminal_population": True,
            "w3_dol2_calibrated_mechanism": True,
            "dol1_touch_is_not_acceptance": True,
            "acceptance_requires_subsequent_closed_m1": True,
            "extension_active_next_m1_only": True,
            "reloss_requires_closed_m1_inside_dol1": True,
            "full_cognition_reassessed_at_reloss": True,
            "future_target_reach_used_for_action": False,
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
