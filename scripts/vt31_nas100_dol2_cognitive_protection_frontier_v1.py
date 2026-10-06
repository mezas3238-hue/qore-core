"""VT31 NAS100 DOL2 cognitive post-acceptance protection frontier V1.

Consumed/burned evidence development only.

Starting mechanism: finite soft-DOL1 W3/W5 + FULL_COGNITION DOL2 extension.
New variable: one confirmed improving M1 protective swing after DOL1 acceptance.

Variants:
- W3_DOL2_COG_NO_PROTECTION
- W3_DOL2_COG_PS1
- W3_DOL2_COG_PS2
- W5_DOL2_COG_NO_PROTECTION
- W5_DOL2_COG_PS1
- W5_DOL2_COG_PS2

A protective swing observed on a closed M1 becomes effective from the next M1.
Only one structural stop improvement is allowed. No sizing or volume authority.
"""
# ruff: noqa: B009
from __future__ import annotations

import argparse
import json
from collections import Counter
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_nas100_high_density_structural_protection_v1 as protection
import vt31_nas100_intelligence_policy_lab_v2b as v2b
import vt31_nas100_sovereign_r_management_frontier_v1 as r_frontier
import vt31_nas100_specialist_r1_candidate as specialist
import vt31_nas100_target_depth_economic_frontier_v2 as depth

SCHEMA = "qore.vt31.nas100.dol2_cognitive_protection_frontier.v1"
WINDOWS = (3, 5)
CONFIRMATIONS = (None, 1, 2)


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _variant(window: int, confirmations: int | None) -> str:
    suffix = (
        "NO_PROTECTION"
        if confirmations is None
        else f"PS{confirmations}"
    )
    return f"W{window}_DOL2_COG_{suffix}"


def _simulate(
    day_bars: tuple[object, ...],
    executable: object,
    state: dict[str, object],
    *,
    window: int,
    confirmations_required: int | None,
) -> dict[str, object]:
    side = str(getattr(getattr(executable, "side"), "value"))
    entry = _d(getattr(executable, "entry_price"))
    initial_stop = _d(getattr(executable, "stop_price"))
    dol1 = _d(getattr(executable, "target_price"))
    risk = abs(entry - initial_stop)
    source = getattr(executable, "source_setup")
    width = _d(source.reference.high) - _d(source.reference.low)
    if risk <= 0 or width <= 0:
        return {"status": "censored-invalid-geometry"}

    direction = Decimal(1) if side == "long" else Decimal(-1)
    dol2 = dol1 + direction * width * Decimal("0.25")

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
    if depth._stop_hit(side, first, initial_stop) or depth._target_hit(
        side, first, dol1
    ):
        return {"status": "censored-fill-bar-path"}

    current_stop = initial_stop
    pending_stop: Decimal | None = None
    protection_committed = False
    protection_confirmations = 0
    touch_index: int | None = None
    accepted_index: int | None = None
    extension_active = False
    cognition_allowed = False
    cognition_state = "NOT_EVALUATED"
    persistence_state: str | None = None
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

        if pending_stop is not None and not protection_committed:
            if protection._improves_stop(
                side,
                current_stop,
                pending_stop,
                dol2,
            ):
                current_stop = pending_stop
                protection_committed = True
            pending_stop = None

        hit_stop = depth._stop_hit(side, bar, current_stop)
        if hit_stop:
            exit_price = current_stop
            exit_at = getattr(bar, "closed_at")
            exit_reason = (
                "post-acceptance-structural-protection-stop"
                if protection_committed
                else "structural-invalidation"
            )
            break

        if extension_active:
            if depth._target_hit(side, bar, dol2):
                exit_price = dol2
                exit_at = getattr(bar, "closed_at")
                exit_reason = "dol2-extended-target"
                break

            if (
                confirmations_required is not None
                and not protection_committed
                and pending_stop is None
            ):
                candidate = protection._protective_swing_level(
                    eligible,
                    index,
                    side,
                )
                if candidate is not None and protection._improves_stop(
                    side,
                    current_stop,
                    candidate,
                    dol2,
                ):
                    protection_confirmations += 1
                    if protection_confirmations >= confirmations_required:
                        pending_stop = candidate
            continue

        if touch_index is None:
            if depth._target_hit(side, bar, dol1):
                touch_index = index
            continue

        bars_after_touch = index - touch_index
        close = _d(getattr(bar, "close"))
        if depth._accepted(side, close, dol1):
            accepted_index = index
            (
                cognition,
                current_reasoning,
                persistence_state,
                cognition_state,
            ) = depth._acceptance_cognition(
                day_bars=day_bars,
                executable=executable,
                state=state,
                eligible=eligible,
                acceptance_index=index,
            )
            cognition_allowed = depth._selector_allows(
                selector="FULL_COGNITION",
                target_name="DOL2",
                cognition=cognition,
                current_reasoning=current_reasoning,
                persistence_state=persistence_state,
            )
            if cognition_allowed:
                extension_active = True
                # DOL2 and protection both begin no earlier than next M1.
                continue
            exit_price = close
            exit_at = getattr(bar, "closed_at")
            exit_reason = "accepted-dol1-cognition-bank"
            break

        if bars_after_touch >= window:
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
            depth._terminal_r(
                side=side,
                entry=entry,
                price=exit_price,
                risk=risk,
            ),
            "f",
        ),
        "window_m1": window,
        "confirmations_required": confirmations_required,
        "dol1_touched": touch_index is not None,
        "dol1_accepted": accepted_index is not None,
        "extension_activated": extension_active,
        "cognition_allowed_extension": cognition_allowed,
        "cognition_state": cognition_state,
        "acceptance_persistence_state": persistence_state,
        "protection_confirmations_seen": protection_confirmations,
        "protection_committed": protection_committed,
        "runtime_volume_decision_authority": False,
    }


def replay(evidence_path: Path) -> dict[str, object]:
    original = specialist._simulate_selected_plan
    rows_by_variant: dict[str, list[dict[str, object]]] = {
        _variant(window, confirmations): []
        for window in WINDOWS
        for confirmations in CONFIRMATIONS
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
            for confirmations in CONFIRMATIONS:
                name = _variant(window, confirmations)
                outcome = _simulate(
                    day_bars,
                    executable,
                    state,
                    window=window,
                    confirmations_required=confirmations,
                )
                if outcome.get("status") != "terminal":
                    raise AssertionError(
                        f"{name} changed terminal eligibility: {outcome}"
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
        }
    }

    for name, rows in rows_by_variant.items():
        if [str(row["signal_at"]) for row in rows] != ids:
            raise AssertionError(f"{name} changed sovereign terminal population")
        reports[name] = {
            "trade_count": len(rows),
            "stress_0_05r": specialist._metrics(
                rows,
                friction=specialist.FRICTION,
            ),
            "monte_carlo": specialist._monte_carlo(rows),
            "halfyear_stress": specialist._block_metrics(rows, halfyear=True),
            "winner_preservation_vs_dol1": r_frontier._winner_preservation(
                baseline,
                rows,
            ),
            "exit_reasons": dict(
                sorted(Counter(str(row["exit_reason"]) for row in rows).items())
            ),
            "extension_activated_count": sum(
                row["extension_activated"] is True for row in rows
            ),
            "protection_committed_count": sum(
                row["protection_committed"] is True for row in rows
            ),
        }

    return {
        "schema": SCHEMA,
        "market": "NAS100",
        "variants": reports,
        "governance": {
            "starting_mechanism_is_full_cognition_dol2": True,
            "windows_predeclared": list(WINDOWS),
            "protection_confirmations_predeclared": [1, 2],
            "one_protection_move_maximum": True,
            "protection_effective_next_m1": True,
            "same_sovereign_terminal_population": True,
            "entry_changed": False,
            "initial_stop_never_widened": True,
            "whole_position_extension": True,
            "position_sizing_used": False,
            "leverage_used": False,
            "compounding_used": False,
            "capital_weighting_used": False,
            "absolute_volume_used": False,
            "future_outcome_used_for_action": False,
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
