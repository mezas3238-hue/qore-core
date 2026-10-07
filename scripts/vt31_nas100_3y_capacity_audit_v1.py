#!/usr/bin/env python3
"""Owner-3Y causal opportunity-capacity audit for VT31 NAS100.

Enumerates distinct executable VT31 source episodes inside the canonical
10:00-11:00 NY source window without changing Strategy Identity.

This is research-only capacity measurement:
- every candidate episode uses only bars closed at/before its decision time;
- duplicate signatures are removed;
- future outcome simulation is attached only after the causal episode exists;
- no outcome/date/fold information is fed back into admission;
- no sizing/leverage/compounding is used.

The purpose is to determine whether ~450 trades / 3Y is reachable by recovering
valid opportunities inside the current methodology, or whether additional
methodology-native sessions / rearm capacity are required.
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
    _metrics,
    _wall,
    load_market_evidence,
)
from qore.infrastructure.traders.vt31_silver_bullet_r2_2 import (
    Vt31R22ExecutableSetup,
    Vt31R22ExecutionPolicy,
    evaluate_vt31_r2_2_source,
    make_executable_setup,
)

SCHEMA = "qore.vt31.nas100.owner_3y_capacity_audit.v1"
BASE_ID = "VT31_NAS100_OWNER_3Y_BASE_001"
MARKET = "NAS100"
TARGET_TRADES = 450


def _signature(setup: Vt31R22ExecutableSetup) -> tuple[str, ...]:
    source = setup.source_setup
    selected_candidates = [
        item
        for item in source.candidates
        if item.family == setup.selected_family
    ]
    formed_at = min(
        (item.formed_at for item in selected_candidates),
        default=setup.decision_at,
    )
    return (
        setup.side.value,
        source.structure.raid_at.astimezone(UTC).isoformat(),
        source.structure.confirmation_at.astimezone(UTC).isoformat(),
        setup.selected_family.value,
        formed_at.astimezone(UTC).isoformat(),
        format(setup.entry_price, "f"),
        format(setup.stop_price, "f"),
        format(setup.target_price, "f"),
    )


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


def _primary_reason(state: dict[str, object]) -> str:
    contradictions = cast(list[str], state["reasoning_contradictions"])
    uncertainty = cast(list[str], state["reasoning_uncertainty"])
    if contradictions:
        return contradictions[0]
    if uncertainty:
        return uncertainty[0]
    return "NONE"


def _terminal(
    day_bars: tuple[object, ...],
    setup: Vt31R22ExecutableSetup,
    state: dict[str, object],
) -> dict[str, object] | None:
    outcome = specialist._simulate_selected_plan(day_bars, setup, state)
    if outcome.get("status") != "terminal":
        return None
    enriched = dict(outcome)
    enriched["entry_family"] = setup.selected_family.value
    enriched["side"] = setup.side.value
    return enriched


def replay(evidence_path: Path) -> dict[str, object]:
    raw_evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    if raw_evidence.get("base_id") != BASE_ID:
        raise ValueError("capacity audit requires canonical owner 3Y base")
    if raw_evidence.get("legacy_r5_r6_r8_operating_folds_used") is not False:
        raise ValueError("legacy fold identity is forbidden")

    series, account, evidence, checked, evidence_sha, provider = (
        load_market_evidence(evidence_path)
    )
    if not series or getattr(series[0], "instrument").symbol != MARKET:
        raise ValueError("capacity audit requires NAS100 evidence")

    raw_by_day: dict[date, list[object]] = defaultdict(list)
    for bar in series:
        raw_by_day[_day(getattr(bar, "opened_at"))].append(bar)
    by_day = {
        local_day: tuple(
            sorted(items, key=lambda item: getattr(item, "opened_at"))
        )
        for local_day, items in raw_by_day.items()
    }
    context_by_day = specialist._context_map(by_day)
    policy = Vt31R22ExecutionPolicy()

    day_counts: Counter[str] = Counter()
    episode_counts: Counter[str] = Counter()
    daily_episode_counts: Counter[int] = Counter()
    observations: list[dict[str, object]] = []
    all_terminal: list[dict[str, object]] = []
    earliest_terminal_per_day: list[dict[str, object]] = []
    earliest_execute_terminal_per_day: list[dict[str, object]] = []
    by_reason_terminal: dict[str, list[dict[str, object]]] = defaultdict(list)

    for local_day in sorted(by_day):
        day_bars = by_day[local_day]
        reference = specialist._slice(day_bars, (9, 0, 0), (10, 0, 0))
        session = specialist._slice(day_bars, (10, 0, 0), (11, 0, 0))
        if len(reference) != 60 or len(session) != 60:
            day_counts["incomplete_day"] += 1
            continue

        day_counts["complete_day"] += 1
        prefix = list(reference)
        (
            previous_path_range,
            prior_ref_median,
            prior_admitted_day_bars,
            prior_h4_history_bars,
        ) = context_by_day[local_day]

        seen: set[tuple[str, ...]] = set()
        day_terminal: list[dict[str, object]] = []
        day_execute_terminal: list[dict[str, object]] = []
        saw_source = False

        for bar in session:
            prefix.append(bar)
            observation_at = cast(datetime, getattr(bar, "closed_at"))
            evaluation = evaluate_vt31_r2_2_source(
                instrument=getattr(bar, "instrument"),
                as_of=observation_at,
                m1_candles=cast(Any, tuple(prefix)),
                evidence_fingerprint=evidence,
            )
            if evaluation.setup is None:
                continue

            saw_source = True
            executable, _ = make_executable_setup(evaluation.setup, policy)
            if executable is None:
                episode_counts["source_not_executable_observation"] += 1
                continue
            if observation_at > executable.pending_expires_at:
                episode_counts["episode_after_expiry"] += 1
                continue

            selected = _selected_at(executable, observation_at)
            signature = _signature(selected)
            if signature in seen:
                continue
            seen.add(signature)

            session_prefix = tuple(
                item
                for item in prefix
                if (10, 0, 0)
                <= _wall(getattr(item, "opened_at"))
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
            primary_reason = _primary_reason(state)
            terminal = _terminal(day_bars, selected, state)

            observations.append(
                {
                    "local_date": local_day.isoformat(),
                    "episode_signature": list(signature),
                    "decision_at": observation_at.astimezone(UTC).isoformat(),
                    "action": state["action"],
                    "primary_reason": primary_reason,
                    "reasoning_contradictions": state[
                        "reasoning_contradictions"
                    ],
                    "reasoning_uncertainty": state["reasoning_uncertainty"],
                    "side": selected.side.value,
                    "entry_family": selected.selected_family.value,
                    "reference_volatility_state": state[
                        "reference_volatility_state"
                    ],
                    "current_path_vs_previous": state[
                        "current_path_vs_previous"
                    ],
                    "h4_state": state["h4_state"],
                    "h1_state": state["h1_state"],
                    "m15_state": state["m15_state"],
                    "decision_minute_ny": state["decision_minute_ny"],
                    "counterfactual_terminal": terminal is not None,
                    "counterfactual_r_multiple": (
                        None if terminal is None else terminal["r_multiple"]
                    ),
                    "research_only": True,
                    "used_for_runtime_decision": False,
                }
            )
            episode_counts[f"action_{state['action']}"] += 1
            episode_counts[f"reason_{primary_reason}"] += 1

            if terminal is None:
                episode_counts["nonterminal_episode"] += 1
                continue

            terminal["local_date"] = local_day.isoformat()
            terminal["research_episode_action"] = state["action"]
            terminal["research_primary_reason"] = primary_reason
            all_terminal.append(terminal)
            day_terminal.append(terminal)
            by_reason_terminal[primary_reason].append(terminal)
            if state["action"] == "EXECUTE":
                day_execute_terminal.append(terminal)

        if saw_source:
            day_counts["day_with_source"] += 1
        if seen:
            day_counts["day_with_distinct_executable_episode"] += 1
        if len(seen) >= 2:
            day_counts["day_with_2plus_distinct_executable_episodes"] += 1
        if len(seen) >= 3:
            day_counts["day_with_3plus_distinct_executable_episodes"] += 1

        daily_episode_counts[len(seen)] += 1

        if day_terminal:
            earliest_terminal_per_day.append(
                min(day_terminal, key=lambda item: str(item["signal_at"]))
            )
        if day_execute_terminal:
            earliest_execute_terminal_per_day.append(
                min(
                    day_execute_terminal,
                    key=lambda item: str(item["signal_at"]),
                )
            )

    reason_metrics = {
        reason: {
            "sample": len(rows),
            "metrics_0_05r": _metrics(
                rows,
                friction=specialist.FRICTION,
            ),
        }
        for reason, rows in sorted(
            by_reason_terminal.items(),
            key=lambda item: (-len(item[1]), item[0]),
        )
    }

    one_per_day_ceiling = len(earliest_terminal_per_day)
    result = {
        "schema": SCHEMA,
        "base_id": BASE_ID,
        "market": MARKET,
        "target_trades_3y": TARGET_TRADES,
        "candidate_contract_fingerprint": specialist.contract_fingerprint(),
        "evidence": {
            "account_fingerprint": account,
            "evidence_fingerprint": evidence,
            "evidence_software_sha": evidence_sha,
            "checked_at": checked.astimezone(UTC).isoformat(),
            "provider_symbol_name": provider,
            "first_opened_at": getattr(series[0], "opened_at")
            .astimezone(UTC)
            .isoformat(),
            "last_closed_at": getattr(series[-1], "closed_at")
            .astimezone(UTC)
            .isoformat(),
        },
        "market_days": len(by_day),
        "day_counts": dict(sorted(day_counts.items())),
        "daily_distinct_executable_episode_distribution": {
            str(key): value
            for key, value in sorted(daily_episode_counts.items())
        },
        "episode_counts": dict(sorted(episode_counts.items())),
        "unique_executable_episode_count": len(observations),
        "terminal_counterfactual_episode_count": len(all_terminal),
        "one_terminal_per_day_density_ceiling": one_per_day_ceiling,
        "one_terminal_per_day_gap_to_450": TARGET_TRADES - one_per_day_ceiling,
        "one_terminal_per_day_reaches_450": one_per_day_ceiling >= TARGET_TRADES,
        "current_execute_one_terminal_per_day": len(
            earliest_execute_terminal_per_day
        ),
        "all_terminal_counterfactual_metrics_0_05r": _metrics(
            all_terminal,
            friction=specialist.FRICTION,
        ),
        "one_terminal_per_day_ceiling_metrics_0_05r": _metrics(
            earliest_terminal_per_day,
            friction=specialist.FRICTION,
        ),
        "current_execute_one_per_day_metrics_0_05r": _metrics(
            earliest_execute_terminal_per_day,
            friction=specialist.FRICTION,
        ),
        "terminal_metrics_by_primary_reason": reason_metrics,
        "observations": observations,
        "governance": {
            "research_only": True,
            "single_contiguous_3y_base": True,
            "legacy_r5_r6_r8_operating_folds_used": False,
            "strategy_identity_changed": False,
            "future_outcome_used_for_runtime_action": False,
            "counterfactual_outcome_is_research_only": True,
            "duplicate_episode_counted_twice": False,
            "position_sizing_used": False,
            "leverage_used": False,
            "compounding_used": False,
            "policy_promoted": False,
            "candidate_certified": False,
            "live_authorized": False,
        },
    }
    return result


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
                "day_counts": payload["day_counts"],
                "unique_executable_episode_count": payload[
                    "unique_executable_episode_count"
                ],
                "terminal_counterfactual_episode_count": payload[
                    "terminal_counterfactual_episode_count"
                ],
                "one_terminal_per_day_density_ceiling": payload[
                    "one_terminal_per_day_density_ceiling"
                ],
                "one_terminal_per_day_gap_to_450": payload[
                    "one_terminal_per_day_gap_to_450"
                ],
                "one_terminal_per_day_ceiling_metrics_0_05r": payload[
                    "one_terminal_per_day_ceiling_metrics_0_05r"
                ],
                "current_execute_one_terminal_per_day": payload[
                    "current_execute_one_terminal_per_day"
                ],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
