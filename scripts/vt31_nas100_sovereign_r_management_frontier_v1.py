"""VT31 NAS100 sovereign R-management frontier V1.

Owner rule:
- R is legitimate trader logic.
- sizing/capital engineering cannot obtain or rescue certification.

This experiment holds the current sovereign specialist admission, entry,
initial structural invalidation, structural target, and lifecycle fixed.
It compares:
- STRUCTURAL_ONLY
- BE_1R
- BE_2R
- BE_3R
- BE_4R

Breakeven is armed only after a fully closed M1 has reached the favorable
threshold and becomes effective from the next M1. Volume never enters logic.
"""
# ruff: noqa: B009
from __future__ import annotations

import argparse
import json
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_nas100_intelligence_policy_lab_v2b as v2b
import vt31_nas100_specialist_r1_candidate as specialist

VARIANTS: dict[str, Decimal | None] = {
    "STRUCTURAL_ONLY": None,
    "BE_1R": Decimal("1"),
    "BE_2R": Decimal("2"),
    "BE_3R": Decimal("3"),
    "BE_4R": Decimal("4"),
}
SCHEMA = "qore.vt31.nas100.sovereign_r_management_frontier.v1"


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


def _simulate(
    day_bars: tuple[object, ...],
    executable: object,
    *,
    threshold_r: Decimal | None,
) -> dict[str, object]:
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

    first = day_bars[fill_index]
    low = _d(getattr(first, "low"))
    high = _d(getattr(first, "high"))
    stop_hit = low <= initial_stop if side == "long" else high >= initial_stop
    target_hit = high >= target if side == "long" else low <= target
    if stop_hit or target_hit:
        return {"status": "censored-fill-bar-path"}

    current_stop = initial_stop
    pending_be = False
    be_armed = False
    previous = first
    filled_at = getattr(first, "closed_at")
    exit_price: Decimal | None = None
    exit_at = None
    exit_reason: str | None = None
    max_favorable = Decimal(0)
    max_adverse = Decimal(0)

    for bar in day_bars[fill_index + 1 :]:
        if specialist.baseline._local_minute(bar) >= specialist.LIFECYCLE_MINUTE:
            break
        if getattr(bar, "opened_at") != getattr(previous, "closed_at"):
            return {"status": "censored-gap-after-fill"}
        previous = bar

        if pending_be and not be_armed:
            current_stop = entry
            be_armed = True
            pending_be = False

        high = _d(getattr(bar, "high"))
        low = _d(getattr(bar, "low"))
        favorable_points = (
            high - entry if side == "long" else entry - low
        )
        adverse_points = (
            entry - low if side == "long" else high - entry
        )
        max_favorable = max(max_favorable, favorable_points)
        max_adverse = max(max_adverse, adverse_points)

        stop_now = low <= current_stop if side == "long" else high >= current_stop
        target_now = high >= target if side == "long" else low <= target
        if stop_now and target_now:
            return {"status": "censored-same-bar-stop-target"}
        if stop_now:
            exit_price = current_stop
            exit_at = getattr(bar, "closed_at")
            exit_reason = "breakeven" if be_armed else "structural-invalidation"
            break
        if target_now:
            exit_price = target
            exit_at = getattr(bar, "closed_at")
            exit_reason = "structural-target"
            break

        if threshold_r is not None and not be_armed and not pending_be:
            if favorable_points / risk >= threshold_r:
                pending_be = True

    if exit_price is None:
        eligible = [
            bar
            for bar in day_bars[fill_index:]
            if specialist.baseline._local_minute(bar)
            < specialist.LIFECYCLE_MINUTE
        ]
        if not eligible:
            return {"status": "censored-no-lifecycle-close"}
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
        "local_date": specialist._day(getattr(executable, "decision_at")).isoformat(),
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
        "breakeven_armed": be_armed,
        "breakeven_threshold_r": (
            None if threshold_r is None else format(threshold_r, "f")
        ),
        "runtime_r_strategy_used": threshold_r is not None,
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
    if not winners:
        return {
            "baseline_winner_count": 0,
            "winner_count_preservation": None,
            "winner_r_preservation": None,
        }
    retained = {
        key: cand[key]
        for key in winners
        if key in cand and cand[key] > 0
    }
    return {
        "baseline_winner_count": len(winners),
        "winner_count_preservation": format(
            Decimal(len(retained)) / Decimal(len(winners)),
            "f",
        ),
        "winner_r_preservation": format(
            sum(retained.values(), Decimal(0))
            / sum(winners.values(), Decimal(0)),
            "f",
        ),
    }


def replay(evidence_path: Path) -> dict[str, object]:
    original = specialist._simulate_selected_plan
    payloads: dict[str, dict[str, object]] = {}
    try:
        for name, threshold in VARIANTS.items():
            def simulator(
                day_bars: tuple[object, ...],
                executable: object,
                state: dict[str, object],
                *,
                _threshold: Decimal | None = threshold,
            ) -> dict[str, object]:
                outcome = _simulate(
                    day_bars,
                    executable,
                    threshold_r=_threshold,
                )
                if outcome.get("status") == "terminal":
                    outcome["target_plan"] = state["target_plan"]
                    outcome["maximum_intelligence_ready_at_entry"] = state.get(
                        "max_intelligence_ready",
                        False,
                    )
                return outcome

            specialist._simulate_selected_plan = simulator
            payloads[name] = specialist.replay(evidence_path)
    finally:
        specialist._simulate_selected_plan = original

    baseline = cast(
        list[dict[str, object]],
        payloads["STRUCTURAL_ONLY"]["trades"],
    )
    baseline_ids = [str(row["signal_at"]) for row in baseline]

    variants: dict[str, object] = {}
    for name, payload in payloads.items():
        rows = cast(list[dict[str, object]], payload["trades"])
        ids = [str(row["signal_at"]) for row in rows]
        if ids != baseline_ids:
            raise AssertionError(f"{name} changed sovereign admission population")
        variants[name] = {
            "trade_count": len(rows),
            "stress_0_05r": payload["stress_0_05r"],
            "monte_carlo": payload["monte_carlo"],
            "halfyear_stress": payload["halfyear_stress"],
            "quarter_stress": payload["quarter_stress"],
            "target_plan_counts": payload["target_plan_counts"],
            "breakeven_armed_count": sum(
                row.get("breakeven_armed") is True for row in rows
            ),
            "winner_preservation_vs_structural": (
                None
                if name == "STRUCTURAL_ONLY"
                else _winner_preservation(baseline, rows)
            ),
        }

    return {
        "schema": SCHEMA,
        "market": "NAS100",
        "variants": variants,
        "governance": {
            "same_admission_population": True,
            "entry_changed": False,
            "initial_stop_changed": False,
            "structural_target_changed": False,
            "lifecycle_changed": False,
            "r_runtime_strategy_allowed": True,
            "r_used_for_volume": False,
            "position_sizing_used": False,
            "leverage_used": False,
            "compounding_used": False,
            "capital_weighting_used": False,
            "absolute_volume_used": False,
            "fresh_holdout_opened": False,
            "policy_promoted": False,
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
