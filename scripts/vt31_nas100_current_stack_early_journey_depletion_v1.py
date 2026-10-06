"""VT31 NAS100 current-stack early-journey depletion calibration V1.

Consumed-evidence development only.

Revalidates an already-existing edge-only VT31 hypothesis on the current
A+B population and fixed B-side position stack:

- after 5 or 8 fully closed post-fill M1 bars;
- MFE remains < +0.25R;
- checkpoint close is <= -0.25R;
- exit is decided only after the checkpoint close and executes at the next
  M1 open;
- optional Breaker-only routing.

This is calibration evidence for an EARLY_JOURNEY_DEPLETED state. It does not
directly promote a runtime exit policy.
"""
# ruff: noqa: B009
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_nas100_a_b_admission_integration_frontier_v1 as admission
import vt31_nas100_h3_dol2_composition_frontier_v1 as composition
import vt31_nas100_specialist_r1_candidate as specialist

SCHEMA = "qore.vt31.nas100.current_stack_early_journey_depletion.v1"
ADMISSION_VARIANT = "A_EXPANDED_OB_REQUIRE_SHORT_RECLAIM_15M"
B_COMPARATOR_ID = "VT31_BSIDE_H3_W5_DOL2_PS2_RESEARCH_COMPARATOR_001"
WINDOW = 5
MFE_LIMIT_R = Decimal("0.25")
ADVERSE_CLOSE_R = Decimal("-0.25")

VARIANTS: dict[str, tuple[int | None, bool]] = {
    "CONTROL": (None, False),
    "GLOBAL_5M": (5, False),
    "GLOBAL_8M": (8, False),
    "BREAKER_5M": (5, True),
    "BREAKER_8M": (8, True),
}


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _level_touched_at_open(
    *,
    side: str,
    opened: Decimal,
    stop: Decimal,
    target: Decimal,
) -> bool:
    if side == "long":
        return opened <= stop or opened >= target
    return opened >= stop or opened <= target


def _apply_calibration(
    *,
    day_bars: tuple[object, ...],
    executable: object,
    baseline: dict[str, object],
    checkpoint_bars: int | None,
    breaker_only: bool,
) -> tuple[dict[str, object], str]:
    updated = dict(baseline)
    updated["early_journey_calibration_applied"] = False
    if checkpoint_bars is None:
        return updated, "control"
    if baseline.get("status") != "terminal":
        return updated, "baseline-non-terminal"
    family = str(executable.selected_family.value)
    if breaker_only and family != "breaker":
        return updated, "selector-not-breaker"

    side = str(executable.side.value)
    entry = _d(executable.entry_price)
    stop = _d(executable.stop_price)
    target = _d(executable.target_price)
    risk = abs(entry - stop)
    if risk <= 0:
        return updated, "invalid-risk"

    filled_at = datetime.fromisoformat(cast(str, baseline["filled_at"]))
    original_exit_at = datetime.fromisoformat(cast(str, baseline["exit_at"]))

    observed: list[object] = []
    checkpoint: object | None = None
    for bar in day_bars:
        opened_at = cast(datetime, bar.opened_at)
        closed_at = cast(datetime, bar.closed_at)
        if opened_at < filled_at:
            continue
        if closed_at >= original_exit_at:
            break
        observed.append(bar)
        if len(observed) == checkpoint_bars:
            checkpoint = bar
            break

    if checkpoint is None:
        return updated, "checkpoint-not-reached"

    max_favorable = Decimal(0)
    for bar in observed:
        favorable, _ = specialist.baseline._favorable_adverse(
            bar,
            side,
            entry,
            risk,
        )
        max_favorable = max(max_favorable, favorable)

    checkpoint_close = _d(checkpoint.close)
    close_r = (
        (checkpoint_close - entry) / risk
        if side == "long"
        else (entry - checkpoint_close) / risk
    )
    updated["early_journey_checkpoint_mfe_r"] = format(max_favorable, "f")
    updated["early_journey_checkpoint_close_r"] = format(close_r, "f")
    updated["early_journey_checkpoint_m1"] = checkpoint_bars

    if not (
        max_favorable < MFE_LIMIT_R
        and close_r <= ADVERSE_CLOSE_R
    ):
        return updated, "depletion-condition-not-met"

    checkpoint_at = cast(datetime, checkpoint.closed_at)
    next_bar = next(
        (
            bar
            for bar in day_bars
            if cast(datetime, bar.opened_at) == checkpoint_at
        ),
        None,
    )
    if next_bar is None:
        return updated, "next-m1-missing"

    next_opened_at = cast(datetime, next_bar.opened_at)
    if next_opened_at >= original_exit_at:
        return updated, "baseline-exit-precedes-next-open"

    opened = _d(next_bar.open)
    if _level_touched_at_open(
        side=side,
        opened=opened,
        stop=stop,
        target=target,
    ):
        return updated, "next-open-through-original-level"

    exit_r = (
        (opened - entry) / risk
        if side == "long"
        else (entry - opened) / risk
    )
    updated["r_multiple"] = format(exit_r, "f")
    updated["exit_at"] = next_opened_at.astimezone(UTC).isoformat()
    updated["exit_reason"] = "early-journey-depleted-next-m1-open"
    updated["early_journey_calibration_applied"] = True
    return updated, "early-journey-depleted"


def _report(
    baseline: list[dict[str, object]],
    rows: list[dict[str, object]],
    statuses: Counter[str],
) -> dict[str, object]:
    changed = [
        row
        for row in rows
        if row.get("early_journey_calibration_applied") is True
    ]
    return {
        "trade_count": len(rows),
        "stress_0_05r": specialist._metrics(
            rows,
            friction=specialist.FRICTION,
        ),
        "monte_carlo": specialist._monte_carlo(rows),
        "halfyear_stress": specialist._block_metrics(rows, halfyear=True),
        "winner_preservation_vs_control": admission._winner_preservation(
            baseline,
            rows,
        ),
        "sequence_diagnostics": composition._sequence_diagnostics(rows),
        "calibration_applied_count": len(changed),
        "status_counts": dict(sorted(statuses.items())),
        "exit_reason_counts": dict(
            sorted(Counter(str(row["exit_reason"]) for row in rows).items())
        ),
        "changed_trade_context": {
            "entry_family": dict(
                sorted(
                    Counter(str(row["entry_family"]) for row in changed).items()
                )
            ),
            "side": dict(
                sorted(Counter(str(row["side"]) for row in changed).items())
            ),
        },
    }


def replay(evidence_path: Path) -> dict[str, object]:
    original = specialist._simulate_selected_plan
    day_by_signal: dict[str, tuple[object, ...]] = {}
    executable_by_signal: dict[str, object] = {}
    full_control: list[dict[str, object]] = []

    def simulator(
        day_bars: tuple[object, ...],
        executable: object,
        state: dict[str, object],
    ) -> dict[str, object]:
        structural = specialist._simulate_structural_boundary_only(
            day_bars,
            executable,
        )
        if structural.get("status") != "terminal":
            return structural
        outcome = composition._simulate_composite(
            day_bars,
            executable,
            state,
            window=WINDOW,
        )
        if outcome.get("status") != "terminal":
            raise AssertionError(
                f"fixed B comparator changed terminal eligibility: {outcome}"
            )
        outcome["target_plan"] = state["target_plan"]
        composition._attach_entry_context(outcome, state)
        signal = str(outcome["signal_at"])
        day_by_signal[signal] = day_bars
        executable_by_signal[signal] = executable
        full_control.append(outcome)
        return structural

    try:
        specialist._simulate_selected_plan = simulator
        base_payload = specialist.replay(evidence_path)
    finally:
        specialist._simulate_selected_plan = original

    structural_rows = cast(list[dict[str, object]], base_payload["trades"])
    if [str(row["signal_at"]) for row in structural_rows] != [
        str(row["signal_at"]) for row in full_control
    ]:
        raise AssertionError("fixed B comparator changed sovereign population")

    control = [
        row
        for row in full_control
        if not admission._is_abstained(row, ADMISSION_VARIANT)
    ]
    variants: dict[str, list[dict[str, object]]] = {}
    status_by_variant: dict[str, Counter[str]] = {}
    for name, (checkpoint, breaker_only) in VARIANTS.items():
        rows: list[dict[str, object]] = []
        statuses: Counter[str] = Counter()
        for base in control:
            signal = str(base["signal_at"])
            candidate, status = _apply_calibration(
                day_bars=day_by_signal[signal],
                executable=executable_by_signal[signal],
                baseline=base,
                checkpoint_bars=checkpoint,
                breaker_only=breaker_only,
            )
            statuses[status] += 1
            rows.append(candidate)
        variants[name] = rows
        status_by_variant[name] = statuses

    control_ids = [str(row["signal_at"]) for row in variants["CONTROL"]]
    for name, rows in variants.items():
        if [str(row["signal_at"]) for row in rows] != control_ids:
            raise AssertionError(f"{name} changed fixed admission population")

    reports = {
        name: _report(variants["CONTROL"], rows, status_by_variant[name])
        for name, rows in variants.items()
    }
    return {
        "schema": SCHEMA,
        "market": "NAS100",
        "admission_variant": ADMISSION_VARIANT,
        "b_comparator_id": B_COMPARATOR_ID,
        "calibration_contract": {
            "mfe_limit_r": format(MFE_LIMIT_R, "f"),
            "adverse_close_r": format(ADVERSE_CLOSE_R, "f"),
            "checkpoints_m1": [5, 8],
            "exit_timing": "next-m1-open",
            "hypothesis_preexisting": True,
        },
        "variants": reports,
        "governance": {
            "consumed_evidence_only": True,
            "current_ab_population_revalidation": True,
            "preexisting_hypothesis_only": True,
            "same_admission_population_all_variants": True,
            "same_entry_all_variants": True,
            "same_initial_stop_all_variants": True,
            "same_target_logic_until_calibration_exit": True,
            "checkpoint_closed_m1_only": True,
            "exit_next_m1_open": True,
            "future_outcome_used_for_action": False,
            "future_journey_used_for_action": False,
            "fold_identity_used_for_action": False,
            "position_sizing_used": False,
            "dynamic_sizing_used": False,
            "leverage_used": False,
            "compounding_used": False,
            "capital_weighting_used": False,
            "absolute_volume_used": False,
            "fresh_holdout_opened": False,
            "runtime_policy_changed": False,
            "journey_state_calibrated_for_runtime": False,
            "policy_promoted": False,
            "candidate_frozen": False,
            "candidate_certified": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
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
    print(
        json.dumps(
            {
                "admission_variant": payload["admission_variant"],
                "variants": payload["variants"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
