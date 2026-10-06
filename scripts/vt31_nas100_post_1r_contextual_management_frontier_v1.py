"""VT31 NAS100 post-1R contextual management frontier V1.

Consumed-evidence economic test of the predeclared 2/3/5 closed-M1
post-1R persistence horizons.

Causal rule at the selected horizon:
- PERSISTENT_1R_FLOOR -> HOLD
- RECOVERED_1R_FLOOR -> HOLD
- POSITIVE_BELOW_1R -> arm breakeven, effective next M1
- ENTRY_OR_WORSE -> exit at the just-closed observation M1 close

The exact sovereign specialist admission, entry, initial stop, structural
target and lifecycle are unchanged. R is trader logic; R never changes volume.
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
import vt31_nas100_post_1r_persistence_forensics_v1 as persistence
import vt31_nas100_specialist_r1_candidate as specialist

SCHEMA = "qore.vt31.nas100.post_1r_contextual_management_frontier.v1"
VARIANTS: dict[str, int | None] = {
    "STRUCTURAL_ONLY": None,
    "H2_CONTEXTUAL": 2,
    "H3_CONTEXTUAL": 3,
    "H5_CONTEXTUAL": 5,
}


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _terminal_r(
    *,
    side: str,
    entry: Decimal,
    price: Decimal,
    risk: Decimal,
) -> Decimal:
    if side == "long":
        return (price - entry) / risk
    return (entry - price) / risk


def _close_r(
    *,
    side: str,
    entry: Decimal,
    close: Decimal,
    risk: Decimal,
) -> Decimal:
    return _terminal_r(side=side, entry=entry, price=close, risk=risk)


def _simulate(
    day_bars: tuple[object, ...],
    executable: object,
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
    contextual_state: str | None = None
    contextual_action = "NONE"
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
                "contextual-breakeven"
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
            and contextual_state is None
        ):
            post_touch = eligible[touch_index + 1 : observation_index + 1]
            closes_r = [
                _close_r(
                    side=side,
                    entry=entry,
                    close=_d(getattr(item, "close")),
                    risk=risk,
                )
                for item in post_touch
            ]
            contextual_state = persistence._persistence_state(closes_r)

            if contextual_state == "POSITIVE_BELOW_1R":
                pending_be = True
                contextual_action = "ARM_BE_NEXT_M1"
            elif contextual_state == "ENTRY_OR_WORSE":
                exit_price = close
                exit_at = getattr(bar, "closed_at")
                exit_reason = "contextual-deterioration-exit"
                contextual_action = "EXIT_AT_OBSERVATION_CLOSE"
                break
            else:
                contextual_action = "HOLD_RUNNER"

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
        "contextual_horizon": horizon,
        "contextual_state": contextual_state,
        "contextual_action": contextual_action,
        "breakeven_armed": be_armed,
        "runtime_r_strategy_used": True,
        "runtime_volume_decision_authority": False,
    }


def _winner_preservation(
    baseline: list[dict[str, object]],
    candidate: list[dict[str, object]],
) -> dict[str, object]:
    base = {
        str(row["signal_at"]): _d(row["r_multiple"]) - specialist.FRICTION
        for row in baseline
    }
    cand = {
        str(row["signal_at"]): _d(row["r_multiple"]) - specialist.FRICTION
        for row in candidate
    }
    winners = {key: value for key, value in base.items() if value > 0}
    retained = {
        key: cand[key]
        for key in winners
        if key in cand and cand[key] > 0
    }
    return {
        "baseline_winner_count": len(winners),
        "winner_count_preservation": (
            None
            if not winners
            else format(
                Decimal(len(retained)) / Decimal(len(winners)),
                "f",
            )
        ),
        "winner_r_preservation": (
            None
            if not winners
            else format(
                sum(retained.values(), Decimal(0))
                / sum(winners.values(), Decimal(0)),
                "f",
            )
        ),
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
                    horizon=_horizon,
                )
                if outcome.get("status") == "terminal":
                    outcome["target_plan"] = state["target_plan"]
                    outcome["maximum_intelligence_ready_at_entry"] = state.get(
                        "max_intelligence_ready",
                        False,
                    )
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
        ids = [str(row["signal_at"]) for row in rows]
        if ids != baseline_ids:
            raise AssertionError(
                f"{variant} changed sovereign admission population"
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
                else _winner_preservation(baseline, rows)
            ),
            "contextual_state_counts": dict(
                sorted(
                    Counter(
                        str(row.get("contextual_state")) for row in rows
                    ).items()
                )
            ),
            "contextual_action_counts": dict(
                sorted(
                    Counter(
                        str(row.get("contextual_action")) for row in rows
                    ).items()
                )
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
            "same_sovereign_admission_population": True,
            "entry_changed": False,
            "initial_structural_invalidation_changed": False,
            "structural_target_changed": False,
            "lifecycle_changed": False,
            "persistence_horizons_predeclared": [2, 3, 5],
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
