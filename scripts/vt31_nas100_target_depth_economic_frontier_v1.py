"""VT31 NAS100 target-depth economic frontier V1.

Runs only after consumed target-depth calibration produced DOL2/DOL3 witnesses.

Fixed:
- sovereign specialist admission/terminal population;
- entry;
- initial structural invalidation;
- lifecycle;
- certification exposure.

Variants:
- DOL1_EXIT_BASELINE
- ACCEPTED_DOL1_EXTEND_DOL2
- ACCEPTED_DOL1_EXTEND_DOL2_STRUCTURAL_PROTECTION
- ACCEPTED_DOL1_EXTEND_DOL3
- ACCEPTED_DOL1_EXTEND_DOL3_STRUCTURAL_PROTECTION

DOL1 touch is not acceptance. Extension activates only after a subsequent
fully closed M1 closes beyond DOL1. An extension target is active only from
the next M1. Structural protection may move the stop once to the first
confirmed improving M1 swing after acceptance, effective from the next M1.

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

import vt31_nas100_high_density_structural_protection_v1 as protection
import vt31_nas100_intelligence_policy_lab_v2b as v2b
import vt31_nas100_sovereign_r_management_frontier_v1 as r_frontier
import vt31_nas100_specialist_r1_candidate as specialist

SCHEMA = "qore.vt31.nas100.target_depth_economic_frontier.v1"
VARIANTS: dict[str, tuple[Decimal | None, bool]] = {
    "DOL1_EXIT_BASELINE": (None, False),
    "ACCEPTED_DOL1_EXTEND_DOL2": (Decimal("0.25"), False),
    "ACCEPTED_DOL1_EXTEND_DOL2_STRUCTURAL_PROTECTION": (
        Decimal("0.25"),
        True,
    ),
    "ACCEPTED_DOL1_EXTEND_DOL3": (Decimal("0.50"), False),
    "ACCEPTED_DOL1_EXTEND_DOL3_STRUCTURAL_PROTECTION": (
        Decimal("0.50"),
        True,
    ),
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
    return (
        (price - entry) / risk
        if side == "long"
        else (entry - price) / risk
    )


def _simulate_extension(
    day_bars: tuple[object, ...],
    executable: object,
    *,
    offset_ref: Decimal | None,
    structural_protection: bool,
) -> dict[str, object]:
    if offset_ref is None:
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

    current_stop = initial_stop
    pending_stop: Decimal | None = None
    protection_committed = False
    dol1_touched = False
    dol1_accepted = False
    touch_at = None
    acceptance_at = None
    previous = first
    filled_at = getattr(first, "closed_at")
    exit_at = None
    exit_price: Decimal | None = None
    exit_reason: str | None = None
    max_favorable = Decimal(0)
    max_adverse = Decimal(0)

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
                extension_target,
            ):
                current_stop = pending_stop
                protection_committed = True
            pending_stop = None

        high = _d(getattr(bar, "high"))
        low = _d(getattr(bar, "low"))
        close = _d(getattr(bar, "close"))
        favorable = high - entry if side == "long" else entry - low
        adverse = entry - low if side == "long" else high - entry
        max_favorable = max(max_favorable, favorable)
        max_adverse = max(max_adverse, adverse)

        hit_stop = (
            low <= current_stop if side == "long" else high >= current_stop
        )
        hit_dol1 = high >= dol1 if side == "long" else low <= dol1

        if not dol1_touched:
            if hit_stop and hit_dol1:
                return {"status": "censored-same-bar-stop-target"}
            if hit_stop:
                exit_price = current_stop
                exit_at = getattr(bar, "closed_at")
                exit_reason = "structural-invalidation"
                break
            if hit_dol1:
                dol1_touched = True
                touch_at = getattr(bar, "closed_at")
            continue

        if not dol1_accepted:
            if hit_stop:
                exit_price = current_stop
                exit_at = getattr(bar, "closed_at")
                exit_reason = "invalidation-before-dol1-acceptance"
                break
            accepted = close > dol1 if side == "long" else close < dol1
            if accepted:
                dol1_accepted = True
                acceptance_at = getattr(bar, "closed_at")
            continue

        hit_extension = (
            high >= extension_target
            if side == "long"
            else low <= extension_target
        )
        if hit_stop and hit_extension:
            # Conservative causal resolution after extension is active:
            # adverse side first when intrabar ordering is unknowable.
            exit_price = current_stop
            exit_at = getattr(bar, "closed_at")
            exit_reason = "extension-same-bar-adverse-first"
            break
        if hit_stop:
            exit_price = current_stop
            exit_at = getattr(bar, "closed_at")
            exit_reason = (
                "structural-protection-stop"
                if protection_committed
                else "structural-invalidation"
            )
            break
        if hit_extension:
            exit_price = extension_target
            exit_at = getattr(bar, "closed_at")
            exit_reason = "extended-structural-target"
            break

        if (
            structural_protection
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
                extension_target,
            ):
                pending_stop = candidate

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
        "dol1_touched": dol1_touched,
        "dol1_touch_at": None if touch_at is None else touch_at.isoformat(),
        "dol1_accepted": dol1_accepted,
        "dol1_acceptance_at": (
            None if acceptance_at is None else acceptance_at.isoformat()
        ),
        "extension_target_ref_offset": format(offset_ref, "f"),
        "extension_target_price": format(extension_target, "f"),
        "structural_protection_enabled": structural_protection,
        "structural_protection_armed": protection_committed,
        "runtime_volume_decision_authority": False,
    }


def replay(evidence_path: Path) -> dict[str, object]:
    original = specialist._simulate_selected_plan
    payloads: dict[str, dict[str, object]] = {}
    try:
        for variant, (offset, protect) in VARIANTS.items():

            def simulator(
                day_bars: tuple[object, ...],
                executable: object,
                state: dict[str, object],
                *,
                _offset: Decimal | None = offset,
                _protect: bool = protect,
            ) -> dict[str, object]:
                outcome = _simulate_extension(
                    day_bars,
                    executable,
                    offset_ref=_offset,
                    structural_protection=_protect,
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
        ids = [str(row["signal_at"]) for row in rows]
        if ids != baseline_ids:
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
            "extension_target_exit_count": sum(
                row.get("exit_reason") == "extended-structural-target"
                for row in rows
            ),
            "protection_armed_count": sum(
                row.get("structural_protection_armed") is True
                for row in rows
            ),
            "exit_reasons": dict(
                sorted(
                    Counter(
                        str(row["exit_reason"]) for row in rows
                    ).items()
                )
            ),
        }

    return {
        "schema": SCHEMA,
        "market": "NAS100",
        "variants": variants,
        "governance": {
            "target_depth_calibration_required_before_run": True,
            "dol2_calibration_witness_required": True,
            "dol3_calibration_witness_required": True,
            "same_sovereign_terminal_population": True,
            "trade_admission_changed": False,
            "entry_changed": False,
            "initial_stop_changed": False,
            "lifecycle_changed": False,
            "dol1_touch_is_not_acceptance": True,
            "dol1_acceptance_requires_subsequent_closed_m1": True,
            "extension_target_active_only_after_acceptance_close": True,
            "extension_same_bar_ambiguity_resolved_adverse_first": True,
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
