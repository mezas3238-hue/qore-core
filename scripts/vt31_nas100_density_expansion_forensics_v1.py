"""VT31 NAS100 density-expansion forensics on consumed evidence.

Research-only lab. It does not authorize an operating policy.

Purpose:
- enumerate distinct causal VT31 executable episodes that the current daily
  replay can hide after WAIT/ABSTAIN/break behavior;
- measure the opportunity-density ceiling before adding new sessions or
  changing Strategy Identity;
- attach post-outcome economics and journey labels only for research;
- preserve a one-trade-per-day ceiling view so density is not manufactured by
  overlapping hypothetical trades.

No holdout is opened. No date-level outcome lookup enters runtime reasoning.
"""
# ruff: noqa: B009
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

SCHEMA = "qore.vt31.nas100.density_expansion_forensics.v1"
MARKET = "NAS100"


def _signature(
    setup: Vt31R22ExecutableSetup,
) -> tuple[str, ...]:
    source = setup.source_setup
    candidates = [
        item
        for item in source.candidates
        if item.family == setup.selected_family
    ]
    formed_at = min(
        (item.formed_at for item in candidates),
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


def _terminal_trade(
    day_bars: tuple[object, ...],
    setup: Vt31R22ExecutableSetup,
    state: dict[str, object],
) -> dict[str, object] | None:
    outcome = specialist._simulate_selected_plan(day_bars, setup, state)
    if outcome.get("status") != "terminal":
        return None
    return outcome


def replay(evidence_path: Path) -> dict[str, object]:
    series, account, evidence, checked, evidence_sha, provider = (
        load_market_evidence(evidence_path)
    )
    if not series or getattr(series[0], "instrument").symbol != MARKET:
        raise ValueError("density lab requires NAS100 evidence")

    raw_by_day: dict[date, list[object]] = defaultdict(list)
    for bar in series:
        raw_by_day[_day(getattr(bar, "opened_at"))].append(bar)
    by_day = {
        day: tuple(sorted(bars, key=lambda item: getattr(item, "opened_at")))
        for day, bars in raw_by_day.items()
    }
    context_by_day = specialist._context_map(by_day)
    policy = Vt31R22ExecutionPolicy()

    observations: list[dict[str, object]] = []
    all_terminal: list[dict[str, object]] = []
    first_terminal_per_day: list[dict[str, object]] = []
    current_execute_terminal: list[dict[str, object]] = []
    day_counts: Counter[str] = Counter()
    episode_counts: Counter[str] = Counter()
    daily_episode_counts: Counter[int] = Counter()
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
        ) = context_by_day[local_day]
        seen: set[tuple[str, ...]] = set()
        day_terminal: list[dict[str, object]] = []
        day_execute_terminal: list[dict[str, object]] = []
        saw_source = False

        for bar in session:
            prefix.append(bar)
            evaluation = evaluate_vt31_r2_2_source(
                instrument=getattr(bar, "instrument"),
                as_of=getattr(bar, "closed_at"),
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
            signature = _signature(executable)
            if signature in seen:
                continue
            seen.add(signature)

            observation_at = cast(datetime, getattr(bar, "closed_at"))
            if observation_at > executable.pending_expires_at:
                episode_counts["episode_after_expiry"] += 1
                continue
            selected = _selected_at(executable, observation_at)
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
                session_prefix,
                evaluation.setup,
                selected,
                observation_at,
            )
            capacity = specialist._journey_capacity_label(day_bars, selected)
            terminal = _terminal_trade(day_bars, selected, state)
            primary_reason = _primary_reason(state)
            row: dict[str, object] = {
                "local_date": local_day.isoformat(),
                "episode_signature": list(signature),
                "decision_at": observation_at.astimezone(UTC).isoformat(),
                "action": state["action"],
                "primary_reason": primary_reason,
                "side": selected.side.value,
                "entry_family": selected.selected_family.value,
                "entry": format(selected.entry_price, "f"),
                "stop": format(selected.stop_price, "f"),
                "target": format(selected.target_price, "f"),
                "reference_volatility_state": state[
                    "reference_volatility_state"
                ],
                "current_path_vs_previous": state[
                    "current_path_vs_previous"
                ],
                "h1_state": state["h1_state"],
                "h4_state": state["h4_state"],
                "premarket_state": state["premarket_state"],
                "cash_open_state": state["cash_open_state"],
                "risk_ref": state["risk_ref"],
                "decision_minute_ny": state["decision_minute_ny"],
                "last_structure_event_family": state[
                    "last_structure_event_family"
                ],
                "reference_reclaim_age_minutes": state[
                    "reference_reclaim_age_minutes"
                ],
                "journey_capacity_label": capacity,
                "counterfactual_terminal": terminal is not None,
                "counterfactual_r_multiple": (
                    None if terminal is None else terminal["r_multiple"]
                ),
                "research_only": True,
                "used_for_runtime_decision": False,
            }
            observations.append(row)
            episode_counts[f"action_{state['action']}"] += 1
            episode_counts[f"reason_{primary_reason}"] += 1
            if terminal is None:
                episode_counts["nonterminal_episode"] += 1
                continue

            enriched = dict(terminal)
            enriched["local_date"] = local_day.isoformat()
            enriched["research_episode_action"] = state["action"]
            enriched["research_primary_reason"] = primary_reason
            enriched["research_entry_family"] = selected.selected_family.value
            enriched["research_side"] = selected.side.value
            enriched["research_reference_volatility_state"] = state[
                "reference_volatility_state"
            ]
            enriched["research_h1_state"] = state["h1_state"]
            enriched["research_h4_state"] = state["h4_state"]
            all_terminal.append(enriched)
            day_terminal.append(enriched)
            by_reason_terminal[primary_reason].append(enriched)
            if state["action"] == "EXECUTE":
                day_execute_terminal.append(enriched)

        if saw_source:
            day_counts["day_with_source"] += 1
        if seen:
            day_counts["day_with_executable_episode"] += 1
        daily_episode_counts[len(seen)] += 1
        if day_terminal:
            first_terminal_per_day.append(
                sorted(
                    day_terminal,
                    key=lambda item: cast(str, item["signal_at"]),
                )[0]
            )
        if day_execute_terminal:
            current_execute_terminal.append(
                sorted(
                    day_execute_terminal,
                    key=lambda item: cast(str, item["signal_at"]),
                )[0]
            )

    reason_metrics = {
        key: {
            "sample": len(values),
            "metrics": _metrics(values, friction=specialist.FRICTION),
        }
        for key, values in sorted(
            by_reason_terminal.items(),
            key=lambda item: (-len(item[1]), item[0]),
        )
    }

    return {
        "schema": SCHEMA,
        "market": MARKET,
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
        "density_ceiling_one_terminal_per_day": len(first_terminal_per_day),
        "current_execute_one_terminal_per_day": len(current_execute_terminal),
        "all_terminal_counterfactual_metrics": _metrics(
            all_terminal,
            friction=specialist.FRICTION,
        ),
        "one_terminal_per_day_ceiling_metrics": _metrics(
            first_terminal_per_day,
            friction=specialist.FRICTION,
        ),
        "current_execute_one_per_day_metrics": _metrics(
            current_execute_terminal,
            friction=specialist.FRICTION,
        ),
        "terminal_metrics_by_primary_reason": reason_metrics,
        "observations": observations,
        "governance": {
            "consumed_evidence_only": True,
            "operating_policy_selection_allowed": False,
            "strategy_identity_changed": False,
            "opens_new_holdout": False,
            "live_authorized": False,
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
                "day_counts": payload["day_counts"],
                "episode_count": payload["unique_executable_episode_count"],
                "terminal_episode_count": payload[
                    "terminal_counterfactual_episode_count"
                ],
                "one_per_day_ceiling": payload[
                    "density_ceiling_one_terminal_per_day"
                ],
                "current_execute_one_per_day": payload[
                    "current_execute_one_terminal_per_day"
                ],
                "one_per_day_ceiling_metrics": payload[
                    "one_terminal_per_day_ceiling_metrics"
                ],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
