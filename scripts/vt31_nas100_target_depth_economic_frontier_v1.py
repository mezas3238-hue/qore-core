"""VT31 NAS100 target-depth economic frontier V1.

This implementation follows the frozen economic plan:
- DOL1 hard-exit baseline;
- soft-DOL1 acceptance windows of 1/3/5 fully closed M1 bars;
- DOL2 ALL control vs DOL2 FULL_COGNITION;
- DOL3 ALL control vs DOL3 DEEP_COGNITION.

Extension activates only after a subsequent closed M1 accepts DOL1. The target
becomes active from the next M1. If an acceptance window expires, the position
exits at that causal close.

Full-cognition variants rebuild live-position cognition at the acceptance
close. No future DOL reach label selects the action.

No sizing, leverage, compounding, capital weighting, or volume adaptation.
"""
# ruff: noqa: B009
from __future__ import annotations

import argparse
import json
from collections import Counter
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_nas100_intelligence_policy_lab_v2b as v2b
import vt31_nas100_post_1r_full_cognition_management_frontier_v2 as fullmgmt
import vt31_nas100_post_1r_persistence_forensics_v1 as persistence
import vt31_nas100_sovereign_r_management_frontier_v1 as r_frontier
import vt31_nas100_specialist_r1_candidate as specialist

from qore.infrastructure.traders.vt31_nas100_position_intelligence import (
    ManagementContext,
)

SCHEMA = "qore.vt31.nas100.target_depth_economic_frontier.v1"
CONTINUATION_STATES = {
    "PERSISTENT_1R_FLOOR",
    "RECOVERED_1R_FLOOR",
}
WINDOWS = (1, 3, 5)


def _variants() -> dict[str, tuple[int | None, Decimal | None, str]]:
    variants: dict[str, tuple[int | None, Decimal | None, str]] = {
        "DOL1_EXIT_BASELINE": (None, None, "BASELINE"),
    }
    for window in WINDOWS:
        variants[f"W{window}_DOL2_ALL"] = (
            window,
            Decimal("0.25"),
            "ALL",
        )
        variants[f"W{window}_DOL2_FULL_COGNITION"] = (
            window,
            Decimal("0.25"),
            "FULL",
        )
        variants[f"W{window}_DOL3_ALL"] = (
            window,
            Decimal("0.50"),
            "ALL",
        )
        variants[f"W{window}_DOL3_DEEP_COGNITION"] = (
            window,
            Decimal("0.50"),
            "DEEP",
        )
    return variants


VARIANTS = _variants()


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


def _acceptance_cognition(
    *,
    day_bars: tuple[object, ...],
    eligible: tuple[object, ...],
    executable: object,
    state: dict[str, object],
    acceptance_index: int,
    side: str,
    entry: Decimal,
    initial_stop: Decimal,
    risk: Decimal,
) -> dict[str, object]:
    touch_index, touch_status = persistence._first_unambiguous_1r_touch(
        eligible,
        side=side,
        entry=entry,
        stop=initial_stop,
        risk=risk,
    )
    if touch_index is None or touch_index >= acceptance_index:
        return {
            "available": False,
            "reason": f"POST1R_UNAVAILABLE:{touch_status}",
            "persistence_state": None,
            "management_ready": False,
            "reasoning_action": None,
            "management_context": None,
            "destination_state": None,
            "maximum_intelligence_ready": False,
            "blockers": [],
        }

    post_touch = eligible[touch_index + 1 : acceptance_index + 1]
    closes_r = [
        _terminal_r(
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
    ) = fullmgmt._current_cognition(
        day_bars=day_bars,
        executable=executable,
        state=state,
        observation_at=getattr(eligible[acceptance_index], "closed_at"),
        persistence_state=persistence_state,
        horizon=len(post_touch),
    )
    return {
        "available": True,
        "reason": "FULL_COGNITION_AT_ACCEPTANCE",
        "persistence_state": persistence_state,
        "management_ready": management_ready,
        "reasoning_action": current_reasoning.action,
        "management_context": cognition.management_context.value,
        "destination_state": cognition.destination_state,
        "maximum_intelligence_ready": maximum_intelligence_ready,
        "blockers": list(cognition.reasoning_max_intelligence_blockers),
    }


def _cognition_allows_extension(
    *,
    mode: str,
    cognition: dict[str, object],
) -> bool:
    if mode == "ALL":
        return True
    if cognition["available"] is not True:
        return False
    continuation = (
        cognition["management_ready"] is True
        and cognition["reasoning_action"] == "EXECUTE"
        and cognition["management_context"] == ManagementContext.SUPPORTIVE.value
        and cognition["persistence_state"] in CONTINUATION_STATES
    )
    if mode == "FULL":
        return bool(
            continuation
            and cognition["destination_state"] in {"DEEP", "NEUTRAL"}
        )
    if mode == "DEEP":
        return bool(
            continuation
            and cognition["destination_state"] == "DEEP"
        )
    raise ValueError(f"unsupported cognition mode: {mode}")


def _simulate(
    day_bars: tuple[object, ...],
    executable: object,
    state: dict[str, object],
    *,
    window: int | None,
    offset_ref: Decimal | None,
    mode: str,
) -> dict[str, object]:
    if window is None or offset_ref is None:
        return specialist._simulate_structural_boundary_only(
            day_bars,
            executable,
        )

    side = str(getattr(getattr(executable, "side"), "value"))
    entry = _d(getattr(executable, "entry_price"))
    initial_stop = _d(getattr(executable, "stop_price"))
    dol1 = _d(getattr(executable, "target_price"))
    risk = abs(entry - initial_stop)
    source = getattr(executable, "source_setup")
    ref_width = _d(source.reference.high) - _d(source.reference.low)
    if risk <= 0 or ref_width <= 0:
        return {"status": "censored-invalid-geometry"}

    direction = Decimal(1) if side == "long" else Decimal(-1)
    extension_target = dol1 + direction * offset_ref * ref_width

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
    first_high = _d(getattr(first, "high"))
    first_low = _d(getattr(first, "low"))
    first_stop = (
        first_low <= initial_stop
        if side == "long"
        else first_high >= initial_stop
    )
    first_dol1 = (
        first_high >= dol1
        if side == "long"
        else first_low <= dol1
    )
    if first_stop or first_dol1:
        return {"status": "censored-fill-bar-path"}

    touched = False
    accepted = False
    extension_active = False
    bars_after_touch = 0
    touch_at = None
    acceptance_at = None
    acceptance_cognition: dict[str, object] | None = None
    filled_at = getattr(first, "closed_at")
    previous = first
    exit_price: Decimal | None = None
    exit_at = None
    exit_reason: str | None = None
    max_favorable = Decimal(0)
    max_adverse = Decimal(0)

    for index in range(1, len(eligible)):
        bar = eligible[index]
        if getattr(bar, "opened_at") != getattr(previous, "closed_at"):
            return {"status": "censored-gap-after-fill"}
        previous = bar

        high = _d(getattr(bar, "high"))
        low = _d(getattr(bar, "low"))
        close = _d(getattr(bar, "close"))
        favorable = high - entry if side == "long" else entry - low
        adverse = entry - low if side == "long" else high - entry
        max_favorable = max(max_favorable, favorable)
        max_adverse = max(max_adverse, adverse)

        hit_stop = (
            low <= initial_stop
            if side == "long"
            else high >= initial_stop
        )
        hit_dol1 = high >= dol1 if side == "long" else low <= dol1

        if not touched:
            if hit_stop and hit_dol1:
                return {"status": "censored-same-bar-stop-target"}
            if hit_stop:
                exit_price = initial_stop
                exit_at = getattr(bar, "closed_at")
                exit_reason = "structural-invalidation"
                break
            if hit_dol1:
                touched = True
                touch_at = getattr(bar, "closed_at")
            continue

        if not accepted:
            if hit_stop:
                exit_price = initial_stop
                exit_at = getattr(bar, "closed_at")
                exit_reason = "invalidation-before-dol1-acceptance"
                break

            bars_after_touch += 1
            accepted_now = close > dol1 if side == "long" else close < dol1
            if accepted_now:
                accepted = True
                acceptance_at = getattr(bar, "closed_at")
                acceptance_cognition = _acceptance_cognition(
                    day_bars=day_bars,
                    eligible=eligible,
                    executable=executable,
                    state=state,
                    acceptance_index=index,
                    side=side,
                    entry=entry,
                    initial_stop=initial_stop,
                    risk=risk,
                )
                extension_active = _cognition_allows_extension(
                    mode=mode,
                    cognition=acceptance_cognition,
                )
                if not extension_active:
                    exit_price = close
                    exit_at = getattr(bar, "closed_at")
                    exit_reason = "dol1-accepted-cognition-bank"
                    break
                # Extension target activates only from the next M1.
                continue

            if bars_after_touch >= window:
                exit_price = close
                exit_at = getattr(bar, "closed_at")
                exit_reason = "dol1-acceptance-window-expired"
                break
            continue

        if extension_active:
            hit_extension = (
                high >= extension_target
                if side == "long"
                else low <= extension_target
            )
            if hit_stop and hit_extension:
                exit_price = initial_stop
                exit_at = getattr(bar, "closed_at")
                exit_reason = "extension-same-bar-adverse-first"
                break
            if hit_stop:
                exit_price = initial_stop
                exit_at = getattr(bar, "closed_at")
                exit_reason = "structural-invalidation"
                break
            if hit_extension:
                exit_price = extension_target
                exit_at = getattr(bar, "closed_at")
                exit_reason = "extended-structural-target"
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
    cognition = acceptance_cognition or {}
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
        "acceptance_window_m1": window,
        "dol1_touched": touched,
        "dol1_touch_at": None if touch_at is None else touch_at.isoformat(),
        "dol1_accepted": accepted,
        "dol1_acceptance_at": (
            None if acceptance_at is None else acceptance_at.isoformat()
        ),
        "extension_active": extension_active,
        "extension_target_ref_offset": format(offset_ref, "f"),
        "extension_target_price": format(extension_target, "f"),
        "cognition_mode": mode,
        "acceptance_cognition_available": cognition.get("available"),
        "acceptance_persistence_state": cognition.get("persistence_state"),
        "acceptance_reasoning_action": cognition.get("reasoning_action"),
        "acceptance_management_context": cognition.get("management_context"),
        "acceptance_destination_state": cognition.get("destination_state"),
        "acceptance_maximum_intelligence_ready": cognition.get(
            "maximum_intelligence_ready"
        ),
        "runtime_volume_decision_authority": False,
    }


def replay(evidence_path: Path) -> dict[str, object]:
    original = specialist._simulate_selected_plan
    payloads: dict[str, dict[str, object]] = {}
    try:
        for variant, (window, offset, mode) in VARIANTS.items():

            def simulator(
                day_bars: tuple[object, ...],
                executable: object,
                state: dict[str, object],
                *,
                _window: int | None = window,
                _offset: Decimal | None = offset,
                _mode: str = mode,
            ) -> dict[str, object]:
                outcome = _simulate(
                    day_bars,
                    executable,
                    state,
                    window=_window,
                    offset_ref=_offset,
                    mode=_mode,
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
        payloads["DOL1_EXIT_BASELINE"]["trades"],
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
            "winner_preservation_vs_dol1": (
                None
                if variant == "DOL1_EXIT_BASELINE"
                else r_frontier._winner_preservation(baseline, rows)
            ),
            "dol1_touched_count": sum(
                row.get("dol1_touched") is True for row in rows
            ),
            "dol1_accepted_count": sum(
                row.get("dol1_accepted") is True for row in rows
            ),
            "extension_active_count": sum(
                row.get("extension_active") is True for row in rows
            ),
            "extension_target_exit_count": sum(
                row.get("exit_reason") == "extended-structural-target"
                for row in rows
            ),
            "acceptance_window_expired_count": sum(
                row.get("exit_reason") == "dol1-acceptance-window-expired"
                for row in rows
            ),
            "cognition_bank_count": sum(
                row.get("exit_reason") == "dol1-accepted-cognition-bank"
                for row in rows
            ),
            "exit_reasons": dict(
                sorted(Counter(str(row["exit_reason"]) for row in rows).items())
            ),
        }

    return {
        "schema": SCHEMA,
        "market": "NAS100",
        "variants": variants,
        "governance": {
            "target_depth_calibration_passed_before_run": True,
            "same_sovereign_terminal_population": True,
            "trade_admission_changed": False,
            "entry_changed": False,
            "initial_stop_changed": False,
            "lifecycle_changed": False,
            "acceptance_windows_m1": list(WINDOWS),
            "dol1_touch_is_not_acceptance": True,
            "dol1_acceptance_requires_subsequent_closed_m1": True,
            "acceptance_window_expiry_exits_at_causal_close": True,
            "extension_target_active_only_after_acceptance_close": True,
            "full_cognition_reassessed_at_acceptance": True,
            "future_depth_label_used_for_runtime_action": False,
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
