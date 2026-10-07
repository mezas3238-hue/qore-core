#!/usr/bin/env python3
"""Single-pass 3Y admission-selection map for VT31 NAS100.

Measures how many market days each causal admission ablation would reach an
EXECUTE decision without replaying post-entry economics. All variants inspect
the same full cognitive state. The only experimental degree of freedom is
whether selected historical pre-entry contradictions remain hard vetoes or are
demoted to context.

Research only. No policy promotion and no outcome-aware action.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, cast

import vt31_nas100_specialist_r1_candidate as specialist

from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_5_multi_index_research import (
    _day,
    _wall,
    load_market_evidence,
)
from qore.infrastructure.traders.vt31_silver_bullet_r2_2 import (
    Vt31R22ExecutableSetup,
    Vt31R22ExecutionPolicy,
    evaluate_vt31_r2_2_source,
    make_executable_setup,
)

SCHEMA = "qore.vt31.nas100.owner_3y_density_selection_map.v1"
BASE_ID = "VT31_NAS100_OWNER_3Y_BASE_001"
TARGET_TRADES = 450

PATH_NOT_COMPRESSED = "SITUATION:CURRENT_PATH_NOT_COMPRESSED"
LOW_DD_REFERENCE = "EXPERIENCE:NONCOMPRESSED_REFERENCE_OUTSIDE_LOW_DD_GATE"
TOO_LATE = "EXPERIENCE:CURRENT_SELECTED_STATE_TOO_LATE"
NO_REFERENCE_LIQUIDITY = "SITUATION:NO_REFERENCE_LIQUIDITY_STATE_BY_CUTOFF"

TRANSIENT_WAIT = frozenset(
    {
        "STRATEGY:SOURCE_CONFIRMATION_NOT_COMPLETE",
        "STRATEGY:ENTRY_EVIDENCE_NOT_ACTIONABLE",
        "SITUATION:REFERENCE_LIQUIDITY_STATE_NOT_YET_PRESENT",
        "EXPERIENCE:SEQUENCE_STALE_8_14_REQUIRES_REEVALUATION",
    }
)

VARIANTS: dict[str, frozenset[str]] = {
    "CURRENT": frozenset(),
    "RELAX_PATH_COMPRESSION": frozenset({PATH_NOT_COMPRESSED}),
    "RELAX_LOW_DD_REFERENCE": frozenset({LOW_DD_REFERENCE}),
    "RELAX_LATE_ENTRY": frozenset({TOO_LATE}),
    "RELAX_REFERENCE_LIQUIDITY_CUTOFF": frozenset(
        {NO_REFERENCE_LIQUIDITY}
    ),
    "RELAX_PATH_AND_REFERENCE_GATE": frozenset(
        {PATH_NOT_COMPRESSED, LOW_DD_REFERENCE}
    ),
    "RELAX_LIQUIDITY_AND_LATE": frozenset(
        {NO_REFERENCE_LIQUIDITY, TOO_LATE}
    ),
    "RELAX_ALL_FOUR": frozenset(
        {
            PATH_NOT_COMPRESSED,
            LOW_DD_REFERENCE,
            TOO_LATE,
            NO_REFERENCE_LIQUIDITY,
        }
    ),
}


def _selected_at(
    setup: Vt31R22ExecutableSetup,
    observation_at: datetime,
) -> Vt31R22ExecutableSetup:
    return Vt31R22ExecutableSetup(
        side=setup.side,
        entry_price=setup.entry_price,
        stop_price=setup.stop_price,
        target_price=setup.target_price,
        three_r_price=setup.three_r_price,
        selected_family=setup.selected_family,
        candidate_families=setup.candidate_families,
        decision_at=observation_at,
        pending_expires_at=setup.pending_expires_at,
        source_setup=setup.source_setup,
        execution_policy_fingerprint=setup.execution_policy_fingerprint,
    )


def _action(
    state: dict[str, object],
    ignored: frozenset[str],
) -> tuple[str, tuple[str, ...], tuple[str, ...]]:
    contradictions = tuple(
        str(item)
        for item in cast(list[str], state["reasoning_contradictions"])
    )
    uncertainty = tuple(
        str(item)
        for item in cast(list[str], state["reasoning_uncertainty"])
    )
    kept = tuple(item for item in contradictions if item not in ignored)
    demoted = tuple(item for item in contradictions if item in ignored)
    if kept:
        return "ABSTAIN", kept, demoted
    if any(item in TRANSIENT_WAIT for item in uncertainty):
        return "WAIT", kept, demoted
    return "EXECUTE", kept, demoted


def replay(evidence_path: Path) -> dict[str, object]:
    evidence_payload = json.loads(evidence_path.read_text(encoding="utf-8"))
    if evidence_payload.get("base_id") != BASE_ID:
        raise ValueError("selection map requires canonical owner 3Y base")

    series, _, evidence, _, _, _ = load_market_evidence(evidence_path)
    raw: dict[date, list[object]] = defaultdict(list)
    for bar in series:
        raw[_day(bar.opened_at)].append(bar)
    by_day = {
        local_day: tuple(
            sorted(items, key=lambda item: item.opened_at)
        )
        for local_day, items in raw.items()
    }
    context_by_day = specialist._context_map(by_day)
    policy = Vt31R22ExecutionPolicy()

    status: dict[str, Counter[str]] = {
        name: Counter() for name in VARIANTS
    }
    abstain_reasons: dict[str, Counter[str]] = {
        name: Counter() for name in VARIANTS
    }
    demoted_reasons: dict[str, Counter[str]] = {
        name: Counter() for name in VARIANTS
    }
    selections: dict[str, list[dict[str, object]]] = {
        name: [] for name in VARIANTS
    }

    complete_days = 0
    for local_day in sorted(by_day):
        day_bars = by_day[local_day]
        reference = specialist._slice(day_bars, (9, 0, 0), (10, 0, 0))
        session = specialist._slice(day_bars, (10, 0, 0), (11, 0, 0))
        if len(reference) != 60 or len(session) != 60:
            for name in VARIANTS:
                status[name]["INCOMPLETE_DAY"] += 1
            continue
        complete_days += 1

        (
            previous_path_range,
            prior_ref_median,
            prior_admitted_day_bars,
            prior_h4_history_bars,
        ) = context_by_day[local_day]

        unresolved = set(VARIANTS)
        saw_wait = {name: False for name in VARIANTS}
        prefix = list(reference)
        saw_source = False

        for bar in session:
            prefix.append(bar)
            observation_at = cast(datetime, bar.closed_at)
            evaluation = evaluate_vt31_r2_2_source(
                instrument=bar.instrument,
                as_of=observation_at,
                m1_candles=cast(Any, tuple(prefix)),
                evidence_fingerprint=evidence,
            )
            if evaluation.setup is None:
                if evaluation.both_sides_swept:
                    invalidated = [
                        name
                        for name in unresolved
                        if saw_wait[name]
                    ]
                    for name in invalidated:
                        status[name]["ABSTAIN_SOURCE_INVALIDATED"] += 1
                        abstain_reasons[name][
                            "STRATEGY:BOTH_SIDES_SWEPT_AFTER_WAIT"
                        ] += 1
                        unresolved.remove(name)
                if not unresolved:
                    break
                continue

            saw_source = True
            executable, _ = make_executable_setup(evaluation.setup, policy)
            if executable is None:
                for name in tuple(unresolved):
                    status[name]["SOURCE_NOT_EXECUTABLE"] += 1
                    unresolved.remove(name)
                break

            selected = _selected_at(executable, observation_at)
            session_prefix = tuple(
                item
                for item in prefix
                if (10, 0, 0)
                <= _wall(item.opened_at)
                < (11, 0, 0)
            )
            state = specialist._state_snapshot(
                day_bars,
                previous_path_range,
                prior_ref_median,
                prior_admitted_day_bars,
                prior_h4_history_bars,
                session_prefix,
                evaluation.setup,
                selected,
                observation_at,
            )

            for name in tuple(unresolved):
                action, kept, demoted = _action(state, VARIANTS[name])
                demoted_reasons[name].update(demoted)
                if action == "WAIT":
                    saw_wait[name] = True
                    status[name]["WAIT_OBSERVATION"] += 1
                    continue
                if action == "ABSTAIN":
                    status[name]["ABSTAIN"] += 1
                    abstain_reasons[name].update(kept)
                    unresolved.remove(name)
                    continue

                status[name]["EXECUTE_SELECTED"] += 1
                selections[name].append(
                    {
                        "local_date": local_day.isoformat(),
                        "decision_at": observation_at.astimezone(
                            UTC
                        ).isoformat(),
                        "side": selected.side.value,
                        "entry_family": selected.selected_family.value,
                        "raw_action": state["action"],
                        "raw_contradictions": state[
                            "reasoning_contradictions"
                        ],
                        "demoted_contradictions": list(demoted),
                        "h4_state": state["h4_state"],
                        "h1_state": state["h1_state"],
                        "m15_state": state["m15_state"],
                        "reference_volatility_state": state[
                            "reference_volatility_state"
                        ],
                        "decision_minute_ny": state[
                            "decision_minute_ny"
                        ],
                    }
                )
                unresolved.remove(name)

            if not unresolved:
                break

        for name in tuple(unresolved):
            if saw_wait[name]:
                status[name]["WAIT_EXPIRED"] += 1
            elif saw_source:
                status[name]["NO_SELECTION_AFTER_SOURCE"] += 1
            else:
                status[name]["NO_SOURCE_SETUP"] += 1

    current_selected = len(selections["CURRENT"])
    if current_selected != 124:
        raise AssertionError(
            f"current selection count drift: expected 124, got {current_selected}"
        )

    reports: dict[str, dict[str, object]] = {}
    for name in VARIANTS:
        rows = selections[name]
        family = Counter(str(row["entry_family"]) for row in rows)
        sides = Counter(str(row["side"]) for row in rows)
        reports[name] = {
            "ignored_admission_contradictions": sorted(VARIANTS[name]),
            "selected_execute_days": len(rows),
            "delta_selected_days_vs_current": len(rows) - current_selected,
            "selection_fraction_of_450": format(
                len(rows) / TARGET_TRADES,
                ".6f",
            ),
            "status_counts": dict(sorted(status[name].items())),
            "abstain_reason_counts": dict(
                sorted(abstain_reasons[name].items())
            ),
            "demoted_reason_observation_counts": dict(
                sorted(demoted_reasons[name].items())
            ),
            "selected_entry_family_counts": dict(sorted(family.items())),
            "selected_side_counts": dict(sorted(sides.items())),
            "selections": rows,
        }

    ranking = sorted(
        (
            {
                "variant": name,
                "selected_execute_days": int(
                    report["selected_execute_days"]
                ),
                "delta_vs_current": int(
                    report["delta_selected_days_vs_current"]
                ),
            }
            for name, report in reports.items()
        ),
        key=lambda row: (
            -int(row["selected_execute_days"]),
            str(row["variant"]),
        ),
    )
    return {
        "schema": SCHEMA,
        "base_id": BASE_ID,
        "target_trades_3y": TARGET_TRADES,
        "complete_days": complete_days,
        "current_selected_execute_days": current_selected,
        "variants": reports,
        "density_ranking": ranking,
        "governance": {
            "single_pass": True,
            "same_causal_state_all_variants": True,
            "full_cognition_state_computed": True,
            "outcome_used_for_action": False,
            "future_information_used_for_action": False,
            "date_or_fold_identity_used_for_action": False,
            "sizing_or_leverage_used": False,
            "policy_promoted": False,
            "candidate_certified": False,
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
                "base_id": BASE_ID,
                "target_trades_3y": TARGET_TRADES,
                "density_ranking": payload["density_ranking"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
