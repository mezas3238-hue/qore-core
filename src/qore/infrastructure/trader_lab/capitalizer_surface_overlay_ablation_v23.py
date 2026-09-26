"""Ablate only the existing Surface stability overlay for Capitalizer V23.

This experiment keeps the development-frozen contextual router, memory, risk
multiplier, entries, stops, target, MAX3 and causal chronology unchanged. It
compares the four router overlay policies that already exist in the repository.

No new policy or threshold is introduced here.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    capitalizer_causal_probe_ranker_v10 as v10,
)
from qore.infrastructure.trader_lab import (
    capitalizer_contextual_stability_router_2r_v1 as router,
)
from qore.infrastructure.trader_lab import (
    capitalizer_factor_journey_probe_ranker_v11 as v11,
)
from qore.infrastructure.trader_lab import (
    capitalizer_intratrade_hypothesis_invalidation_v18 as v18,
)
from qore.infrastructure.trader_lab import (
    capitalizer_sequence_failure_memory_abstention_v13 as v13,
)

IDENTITY = "QORE_CAPITALIZER_SURFACE_OVERLAY_ABLATION_V23"
CONTROL_POLICY = "CONTEXT_STABILITY_STAGE"
POLICIES = (
    CONTROL_POLICY,
    "CONTEXT_ONLY",
    "CONTEXT_DEFENSIVE_STAGE",
    "CONTEXT_LOCK_STABILITY",
)


def _run_surface(
    *,
    period: str,
    overlay_policy: str,
    ledgers: dict[str, Any],
    contexts: dict[tuple[str, str], Any],
    contextual_model: dict[str, Any],
) -> tuple[dict[str, Any], tuple[v18.InvalidationDecision, ...]]:
    if overlay_policy not in POLICIES:
        raise ValueError("V23 overlay outside predeclared policy family")
    previous = v10.BASE_POSITION_POLICY
    v10.BASE_POSITION_POLICY = overlay_policy
    try:
        return v18._simulate(
            period=period,
            policy="SURFACE_CONTROL",
            ledgers=ledgers,
            contexts=contexts,
            contextual_model=contextual_model,
            events={},
        )
    finally:
        v10.BASE_POSITION_POLICY = previous


def build_report(
    development_root: Path,
    validation_root: Path,
    reserved_root: Path,
    development_validation_context_root: Path,
    reserved_context_root: Path,
) -> tuple[dict[str, Any], tuple[v18.InvalidationDecision, ...]]:
    windows, contextual_model = v13._load_windows(
        development_root,
        validation_root,
        reserved_root,
        development_validation_context_root,
        reserved_context_root,
    )

    simultaneous: dict[tuple[str, str, str], tuple[Any, ...]] = {}
    for period, (ledgers, _contexts) in windows.items():
        simultaneous.update(
            v11._simultaneous_map(period=period, ledgers=ledgers)
        )

    previous_simultaneous = dict(v11._SIMULTANEOUS)
    v11._SIMULTANEOUS.clear()
    v11._SIMULTANEOUS.update(simultaneous)

    all_audits: list[v18.InvalidationDecision] = []
    try:
        controls: dict[str, dict[str, Any]] = {}
        for period, (ledgers, contexts) in windows.items():
            control, audit = _run_surface(
                period=period,
                overlay_policy=CONTROL_POLICY,
                ledgers=ledgers,
                contexts=contexts,
                contextual_model=contextual_model,
            )
            controls[period] = control
            all_audits.extend(audit)

        results: list[dict[str, Any]] = []
        for overlay_policy in POLICIES:
            heldouts: dict[str, Any] = {}
            for period, (ledgers, contexts) in windows.items():
                if overlay_policy == CONTROL_POLICY:
                    current = controls[period]
                else:
                    current, audit = _run_surface(
                        period=period,
                        overlay_policy=overlay_policy,
                        ledgers=ledgers,
                        contexts=contexts,
                        contextual_model=contextual_model,
                    )
                    all_audits.extend(audit)

                v10._annotate(current, controls[period])
                current["losing_streak_not_worse"] = (
                    int(current["metrics"]["max_losing_streak"])
                    <= int(controls[period]["metrics"]["max_losing_streak"])
                )
                heldouts[period] = current

            full_gate = (
                overlay_policy != CONTROL_POLICY
                and all(
                    row["pf_at_least_surface_control"]
                    and row["total_r_at_least_surface_control"]
                    and row["dd_below_surface_control"]
                    and row["dd_at_or_below_6r"]
                    and row["losing_streak_not_worse"]
                    for row in heldouts.values()
                )
            )
            results.append(
                {
                    "overlay_policy": overlay_policy,
                    "heldouts": heldouts,
                    "all_consumed_full_gate": full_gate,
                }
            )
    finally:
        v11._SIMULTANEOUS.clear()
        v11._SIMULTANEOUS.update(previous_simultaneous)

    candidates = tuple(
        row for row in results if row["all_consumed_full_gate"]
    )
    return {
        "identity": IDENTITY,
        "evaluation": "EXISTING_SURFACE_OVERLAY_ABLATION",
        "control_policy": CONTROL_POLICY,
        "policies": list(POLICIES),
        "policy_count": len(POLICIES),
        "results": results,
        "candidate_count": len(candidates),
        "all_entries_preserved": True,
        "density_retention": "1",
        "development_context_model_unchanged": True,
        "adaptive_memory_unchanged": True,
        "surface_risk_multiplier_logic_unchanged": True,
        "simultaneous_factor_state_preserved": True,
        "fixed_target_r": "2.00",
        "original_stop_geometry_preserved": True,
        "max3_preserved": True,
        "new_overlay_policy_created": False,
        "new_threshold_created": False,
        "current_trade_outcome_visible_to_decision": False,
        "open_trade_future_visible_to_decision": False,
        "unchosen_counterfactual_visible_to_decision": False,
        "validation_reserved_outcomes_visible_to_context_training": False,
        "historical_fresh_oos_available": False,
        "2018_2020_status": "CONSUMED_NOT_FRESH",
        "full_source_recompetition_required_before_freeze": True,
        "automatic_policy_promotion": False,
        "trader_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "next_phase": (
            "FULL_SOURCE_RECOMPETITION_V23_SURVIVOR"
            if candidates
            else "V23_OVERLAY_HYPOTHESIS_FALSIFIED"
        ),
    }, tuple(all_audits)


def write_report(
    report: dict[str, Any],
    audits: tuple[v18.InvalidationDecision, ...],
    output: Path,
) -> None:
    from dataclasses import asdict

    output.mkdir(parents=True, exist_ok=True)
    (output / "capitalizer-surface-overlay-ablation-v23.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (
        output / "capitalizer-surface-overlay-ablation-v23-decisions.jsonl"
    ).open("w", encoding="utf-8") as handle:
        for audit_row in audits:
            handle.write(json.dumps(asdict(audit_row), sort_keys=True) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("development_root", type=Path)
    parser.add_argument("validation_root", type=Path)
    parser.add_argument("reserved_root", type=Path)
    parser.add_argument("development_validation_context_root", type=Path)
    parser.add_argument("reserved_context_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    report, audits = build_report(
        args.development_root,
        args.validation_root,
        args.reserved_root,
        args.development_validation_context_root,
        args.reserved_context_root,
    )
    write_report(report, audits, args.output)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
