"""VT31 NAS100 target-depth economic frontier V2.

Consumed-evidence research only.

V2 fixes the physical execution problem of post-touch extension:
- DOL1 is a soft checkpoint only inside a finite predeclared window;
- acceptance requires a subsequent fully closed M1 beyond DOL1;
- the extension target becomes active only from the next M1;
- if the window expires without acceptance, exit at that causal close.

Acceptance windows: 1, 3, 5 M1.
Targets: DOL2 (+0.25 ref) and DOL3 (+0.50 ref).
Selectors: ALL control vs FULL_COGNITION.

No sizing, leverage, compounding, capital weighting, or volume adaptation.
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
    UniversalTargetIntent,
    assess_full_cognitive_position,
    validate_full_cognitive_accounting_for_research,
)
from qore.infrastructure.traders.vt31_nas100_reasoning_engine import reason_position

SCHEMA = "qore.vt31.nas100.target_depth_economic_frontier.v2"
WINDOWS = (1, 3, 5)
TARGETS = ("DOL2", "DOL3")
SELECTORS = ("ALL", "FULL_COGNITION")


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _terminal_r(
    *,
    side: str,
    entry: Decimal,
    price: Decimal,
    risk: Decimal,
) -> Decimal:
    return (price - entry) / risk if side == "long" else (entry - price) / risk


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


def _acceptance_cognition(
    *,
    day_bars: tuple[object, ...],
    executable: object,
    state: dict[str, object],
    eligible: tuple[object, ...],
    acceptance_index: int,
):
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
    if one_r_index is None or one_r_index >= acceptance_index:
        return None, None, None, f"NO_CAUSAL_1R_STATE:{one_r_status}"

    closes_r = [
        _terminal_r(
            side=side,
            entry=entry,
            price=_d(getattr(bar, "close")),
            risk=risk,
        )
        for bar in eligible[one_r_index + 1 : acceptance_index + 1]
    ]
    persistence_state = persistence._persistence_state(closes_r)
    horizon = acceptance_index - one_r_index
    (
        current,
        current_reasoning,
        _,
        management_ready,
        _,
    ) = post1r._current_cognition(
        day_bars=day_bars,
        executable=executable,
        state=state,
        observation_at=getattr(eligible[acceptance_index], "closed_at"),
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
    accepted_reasoning = reason_position(
        accepted_current,
        frozen_entry_reasoning=entry_reasoning,
    )
    cognition = assess_full_cognitive_position(
        situation=accepted_current,
        reasoning=entry_reasoning,
        current_reasoning=accepted_reasoning,
        entry_tier="CORE",
        dol1_acceptance_observed=True,
        entry_situation_fingerprint=entry_situation.fingerprint(),
    )
    validate_full_cognitive_accounting_for_research(cognition)
    return (
        cognition,
        accepted_reasoning,
        persistence_state,
        "READY" if management_ready else "MANAGEMENT_BLOCKED",
    )


def _selector_allows(
    *,
    selector: str,
    target_name: str,
    cognition: object | None,
    current_reasoning: object | None,
    persistence_state: str | None,
) -> bool:
    if selector == "ALL":
        return True
    if cognition is None or current_reasoning is None:
        return False

    if target_name == "DOL2":
        return (
            getattr(cognition, "target_intent")
            is UniversalTargetIntent.EXTEND_TO_DOL2
            and getattr(current_reasoning, "action") == "EXECUTE"
        )

    return (
        getattr(cognition, "target_intent")
        is UniversalTargetIntent.EXTEND_TO_DOL2
        and getattr(cognition, "destination_state") == "DEEP"
        and persistence_state
        in {"PERSISTENT_1R_FLOOR", "RECOVERED_1R_FLOOR"}
        and getattr(current_reasoning, "action") == "EXECUTE"
    )


def _simulate(
    day_bars: tuple[object, ...],
    executable: object,
    state: dict[str, object],
    *,
    window: int,
    target_name: str,
    selector: str,
) -> dict[str, object]:
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
    offset = Decimal("0.25") if target_name == "DOL2" else Decimal("0.50")
    extended_target = dol1 + direction * width * offset

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
    accepted_index: int | None = None
    extension_active = False
    cognition_allowed = False
    cognition_state = "NOT_EVALUATED"
    persistence_state: str | None = None
    decision_bars: int | None = None
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
            if _target_hit(side, bar, extended_target):
                exit_price = extended_target
                exit_at = getattr(bar, "closed_at")
                exit_reason = f"{target_name.lower()}-extended-target"
                break
            continue

        if touch_index is None:
            if _target_hit(side, bar, dol1):
                touch_index = index
            continue

        bars_after_touch = index - touch_index
        close = _d(getattr(bar, "close"))
        if _accepted(side, close, dol1):
            accepted_index = index
            decision_bars = bars_after_touch
            (
                cognition,
                current_reasoning,
                persistence_state,
                cognition_state,
            ) = _acceptance_cognition(
                day_bars=day_bars,
                executable=executable,
                state=state,
                eligible=eligible,
                acceptance_index=index,
            )
            cognition_allowed = _selector_allows(
                selector=selector,
                target_name=target_name,
                cognition=cognition,
                current_reasoning=current_reasoning,
                persistence_state=persistence_state,
            )
            if cognition_allowed:
                extension_active = True
                continue
            exit_price = close
            exit_at = getattr(bar, "closed_at")
            exit_reason = "accepted-dol1-cognition-declined-extension"
            break

        if bars_after_touch >= window:
            decision_bars = bars_after_touch
            exit_price = close
            exit_at = getattr(bar, "closed_at")
            exit_reason = "soft-dol1-acceptance-timeout"
            break

    if exit_price is None:
        final = eligible[-1]
        exit_price = _d(getattr(final, "close"))
        exit_at = getattr(final, "closed_at")
        exit_reason = "16:00-lifecycle"

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
        "r_multiple": format(
            _terminal_r(side=side, entry=entry, price=exit_price, risk=risk),
            "f",
        ),
        "soft_dol1_window_m1": window,
        "extension_target": target_name,
        "selector": selector,
        "dol1_touched": touch_index is not None,
        "dol1_accepted_in_window": accepted_index is not None,
        "extension_activated": extension_active,
        "cognition_allowed_extension": cognition_allowed,
        "cognition_state": cognition_state,
        "acceptance_persistence_state": persistence_state,
        "touch_to_decision_bars": decision_bars,
        "runtime_volume_decision_authority": False,
    }


def _name(window: int, target: str, selector: str) -> str:
    return f"SOFT{window}_{target}_{selector}"


def replay(evidence_path: Path) -> dict[str, object]:
    original = specialist._simulate_selected_plan
    rows_by_variant: dict[str, list[dict[str, object]]] = {
        _name(w, t, s): []
        for w in WINDOWS
        for t in TARGETS
        for s in SELECTORS
    }

    def simulator(
        day_bars: tuple[object, ...],
        executable: object,
        state: dict[str, object],
    ) -> dict[str, object]:
        baseline = specialist._simulate_structural_boundary_only(
            day_bars,
            executable,
        )
        if baseline.get("status") != "terminal":
            return baseline
        for window in WINDOWS:
            for target in TARGETS:
                for selector in SELECTORS:
                    name = _name(window, target, selector)
                    outcome = _simulate(
                        day_bars,
                        executable,
                        state,
                        window=window,
                        target_name=target,
                        selector=selector,
                    )
                    if outcome.get("status") != "terminal":
                        raise AssertionError(
                            f"{name} lost terminal population: {outcome}"
                        )
                    outcome["target_plan"] = state["target_plan"]
                    rows_by_variant[name].append(outcome)
        return baseline

    try:
        specialist._simulate_selected_plan = simulator
        base_payload = specialist.replay(evidence_path)
    finally:
        specialist._simulate_selected_plan = original

    baseline = cast(list[dict[str, object]], base_payload["trades"])
    ids = [str(row["signal_at"]) for row in baseline]
    reports: dict[str, object] = {
        "DOL1_HARD_EXIT": {
            "trade_count": len(baseline),
            "stress_0_05r": base_payload["stress_0_05r"],
            "monte_carlo": base_payload["monte_carlo"],
            "halfyear_stress": base_payload["halfyear_stress"],
            "quarter_stress": base_payload["quarter_stress"],
        }
    }

    for name, rows in rows_by_variant.items():
        if [str(row["signal_at"]) for row in rows] != ids:
            raise AssertionError(
                f"{name} changed sovereign terminal population"
            )
        reports[name] = {
            "trade_count": len(rows),
            "stress_0_05r": specialist._metrics(
                rows,
                friction=specialist.FRICTION,
            ),
            "monte_carlo": specialist._monte_carlo(rows),
            "halfyear_stress": specialist._block_metrics(rows, halfyear=True),
            "quarter_stress": specialist._block_metrics(rows, halfyear=False),
            "winner_preservation_vs_dol1": r_frontier._winner_preservation(
                baseline,
                rows,
            ),
            "exit_reasons": dict(
                sorted(Counter(str(row["exit_reason"]) for row in rows).items())
            ),
            "dol1_accept_count": sum(
                row["dol1_accepted_in_window"] is True for row in rows
            ),
            "extension_activated_count": sum(
                row["extension_activated"] is True for row in rows
            ),
            "cognition_declined_count": sum(
                row["exit_reason"]
                == "accepted-dol1-cognition-declined-extension"
                for row in rows
            ),
            "timeout_count": sum(
                row["exit_reason"] == "soft-dol1-acceptance-timeout"
                for row in rows
            ),
        }

    return {
        "schema": SCHEMA,
        "market": "NAS100",
        "variants": reports,
        "governance": {
            "target_depth_calibration_prerequisite_passed": True,
            "same_sovereign_terminal_population": True,
            "soft_dol1_windows_predeclared": list(WINDOWS),
            "dol1_touch_is_not_acceptance": True,
            "acceptance_requires_closed_m1": True,
            "extension_target_active_next_m1_only": True,
            "whole_position_extension": True,
            "partial_exit_required": False,
            "position_sizing_used": False,
            "leverage_used": False,
            "compounding_used": False,
            "capital_weighting_used": False,
            "absolute_volume_used": False,
            "future_target_reach_used_for_action": False,
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
