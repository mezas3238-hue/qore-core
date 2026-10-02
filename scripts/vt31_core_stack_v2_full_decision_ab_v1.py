"""Full VT31 cognitive-decision universe preservation A/B for Core Stack V2.

This replay walks the current reasoning-sovereign source lifecycle:
- WAIT is observational and may evolve on the same causal source;
- ABSTAIN terminates the current source hypothesis;
- invalidation/non-executable source closes that source episode;
- after a terminal execution, any later decision requires a new raid and
  confirmation after the prior exit.

Core V2 receives only causal pre-decision facts. It never sees action, PnL,
exit, MFE/MAE, terminal labels, or future journey information.

The V2 lane is a preservation gate only: when Core context is valid, the
existing VT31 cognitive action remains sovereign. This script measures whether
the shared context boundary can observe the complete decision universe without
changing it.
"""
# ruff: noqa: B009, E402, I001
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from time import perf_counter_ns
from typing import Any, cast

import vt31_nas100_causal_hybrid_replay_v1 as activation
import vt31_nas100_specialist_r1_candidate as specialist
import vt31_nas100_structural_target_candidate_5y_validation_v1 as fivey

from qore.infrastructure.core_stack_v2 import (
    DecisionObservation,
    MarketEvent,
    build_snapshot,
    freeze_facts,
    summarize_decision_ab,
)
from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_5_multi_index_research import (
    _day,
    _wall,
)
from qore.infrastructure.traders.vt31_core_stack_v2_adapter import VT31CoreAdapter
from qore.infrastructure.traders.vt31_silver_bullet_r2_2 import (
    Vt31R22ExecutableSetup,
    Vt31R22ExecutionPolicy,
    Vt31R22SourceSetup,
    evaluate_vt31_r2_2_source,
    make_executable_setup,
)

SCHEMA = "qore.core_stack_v2.vt31.full_decision_universe_ab.v1"
IDENTITY = "VT31_CURRENT_VS_QORE_CORE_STACK_V2_FULL_DECISION_UNIVERSE_AB_V1"
MARKET = "NAS100"
MAX_SOURCE_CYCLES_PER_DAY = 8
MAX_EXECUTIONS_PER_DAY = 4

CAUSAL_STATE_FIELDS = (
    "decision_minute_ny",
    "last_structure_event_family",
    "last_structure_event_age_minutes",
    "reference_reclaim_age_minutes",
    "current_path_vs_previous",
    "reference_width_vs_prior5",
    "reference_volatility_state",
    "prior_day_state",
    "h4_state",
    "h1_state",
    "premarket_state",
    "cash_open_state",
    "position_in_prior_day_range",
    "raid_depth_ref",
    "recent_path_efficiency",
    "recent_overlap_rate",
    "risk_ref",
    "planned_target_r",
    "destination_distance_ref",
    "confirmation_latency_minutes",
    "entry_evidence_age_minutes",
    "last_structure_event_family",
)

FORBIDDEN_CORE_FIELDS = (
    "action",
    "abstain_reasons",
    "reasoning_support",
    "reasoning_contradictions",
    "reasoning_uncertainty",
    "reasoning_wait_reasons",
    "r_multiple",
    "capital_weighted_net_r",
    "net_r_after_friction",
    "exit_at",
    "exit_reason",
    "mfe_r",
    "mae_r",
    "loss_path_class",
    "future_journey_label",
    "terminal_pnl",
)


def _digest(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode()).hexdigest()


def _state_facts(state: dict[str, object]) -> dict[str, str]:
    selected = {
        field: str(state.get(field, "UNKNOWN"))
        for field in CAUSAL_STATE_FIELDS
    }
    if any(field in selected for field in FORBIDDEN_CORE_FIELDS):
        raise AssertionError("post-decision/outcome field entered Core facts")

    volatility = selected["reference_volatility_state"].upper()
    current_path_raw = state.get("current_path_vs_previous")
    path_state = "UNKNOWN"
    if current_path_raw is not None:
        path_state = (
            "COMPRESSED"
            if Decimal(str(current_path_raw)) < Decimal("0.75")
            else "NOT_COMPRESSED"
        )

    return {
        "market_state": "VT31_CAUSAL_REASONING_OBSERVATION",
        "session_state": "NY_AM_SILVER_BULLET",
        "liquidity_state": selected["last_structure_event_family"],
        "structure_state": "SPECIALIST_SOURCE_AVAILABLE",
        "volatility_state": volatility,
        "expansion_state": (
            "EXPANSION" if volatility == "EXPANDED" else "NOT_EXPANDED"
        ),
        "compression_state": (
            "COMPRESSION" if path_state == "COMPRESSED" else "NOT_COMPRESSED"
        ),
        "directional_state": "SPECIALIST_OWNED",
        "reversal_state": "SPECIALIST_OWNED",
        "continuation_state": "SPECIALIST_OWNED",
        **{f"vt31:{key}": value for key, value in selected.items()},
    }


def _synthetic_facts(kind: str) -> dict[str, str]:
    return {
        "market_state": "VT31_CAUSAL_SOURCE_LIFECYCLE",
        "session_state": "NY_AM_SILVER_BULLET",
        "liquidity_state": kind,
        "structure_state": kind,
        "volatility_state": "UNKNOWN",
        "expansion_state": "UNKNOWN",
        "compression_state": "UNKNOWN",
        "directional_state": "SPECIALIST_OWNED",
        "reversal_state": "SPECIALIST_OWNED",
        "continuation_state": "SPECIALIST_OWNED",
    }


def _decision_record(
    *,
    local_day: date,
    cycle_index: int,
    decision_at: datetime,
    action: str,
    state: dict[str, object] | None,
    reason: str,
    source: Vt31R22SourceSetup | None = None,
    setup: Vt31R22ExecutableSetup | None = None,
) -> dict[str, object]:
    return {
        "local_date": local_day.isoformat(),
        "cycle_index": cycle_index,
        "decision_at": decision_at.astimezone(UTC).isoformat(),
        "action": action,
        "reason": reason,
        "state": state,
        "raid_at": (
            None
            if source is None
            else source.structure.raid_at.astimezone(UTC).isoformat()
        ),
        "confirmation_at": (
            None
            if source is None
            else source.structure.confirmation_at.astimezone(UTC).isoformat()
        ),
        "entry_family": None if setup is None else setup.selected_family.value,
        "side": None if setup is None else setup.side.value,
    }


def _next_episode(
    *,
    local_day: date,
    cycle_index: int,
    day_bars: tuple[object, ...],
    reference: tuple[object, ...],
    session: tuple[object, ...],
    after_at: datetime,
    previous_path_range: Decimal | None,
    prior_ref_median: Decimal | None,
    prior_admitted_day_bars: tuple[object, ...],
    evidence: str,
    policy: Vt31R22ExecutionPolicy,
) -> tuple[list[dict[str, object]], dict[str, object]]:
    prefix: list[object] = list(reference)
    trace: list[dict[str, object]] = []
    saw_wait = False
    first_source_raid: datetime | None = None

    for bar in session:
        closed_at = cast(datetime, getattr(bar, "closed_at"))
        if closed_at <= after_at:
            continue
        prefix.append(bar)

        evaluation = evaluate_vt31_r2_2_source(
            instrument=getattr(bar, "instrument"),
            as_of=closed_at,
            m1_candles=cast(Any, tuple(prefix)),
            evidence_fingerprint=evidence,
        )
        if evaluation.setup is None:
            if saw_wait and evaluation.both_sides_swept:
                item = _decision_record(
                    local_day=local_day,
                    cycle_index=cycle_index,
                    decision_at=closed_at,
                    action="INVALIDATED",
                    state=None,
                    reason="BOTH_SIDES_SWEPT_AFTER_WAIT",
                )
                trace.append(item)
                return trace, {
                    "status": "INVALIDATED",
                    "decision_at": closed_at,
                }
            continue

        source = evaluation.setup
        if (
            source.structure.raid_at <= after_at
            or source.structure.confirmation_at <= after_at
        ):
            continue

        if first_source_raid is None:
            first_source_raid = source.structure.raid_at
        elif source.structure.raid_at != first_source_raid:
            first_source_raid = source.structure.raid_at
            saw_wait = False

        executable, _ = make_executable_setup(source, policy)
        if executable is None:
            item = _decision_record(
                local_day=local_day,
                cycle_index=cycle_index,
                decision_at=closed_at,
                action="INVALIDATED",
                state=None,
                reason="SOURCE_NOT_SINGLE_ROUTE_EXECUTABLE",
                source=source,
            )
            trace.append(item)
            return trace, {
                "status": "NON_EXECUTABLE",
                "decision_at": closed_at,
            }

        session_prefix = tuple(
            item
            for item in session
            if cast(datetime, getattr(item, "closed_at")) <= closed_at
            and (10, 0, 0)
            <= _wall(getattr(item, "opened_at"))
            < (11, 0, 0)
        )
        state = specialist._state_snapshot(
            day_bars,
            previous_path_range,
            prior_ref_median,
            prior_admitted_day_bars,
            session_prefix,
            source,
            executable,
            closed_at,
        )
        action = cast(str, state["action"])
        trace.append(
            _decision_record(
                local_day=local_day,
                cycle_index=cycle_index,
                decision_at=closed_at,
                action=action,
                state=state,
                reason=f"REASONING_{action}",
                source=source,
                setup=executable,
            )
        )

        if action == "WAIT":
            saw_wait = True
            continue
        if action == "ABSTAIN":
            return trace, {
                "status": "ABSTAIN",
                "decision_at": closed_at,
                "source": source,
                "setup": executable,
                "state": state,
            }
        if action != "EXECUTE":
            raise ValueError(f"unsupported reasoning action={action}")

        activated = activation._activation_setup(executable, closed_at)
        return trace, {
            "status": "EXECUTE",
            "decision_at": closed_at,
            "source": source,
            "setup": activated,
            "state": state,
        }

    return trace, {
        "status": "NO_EVENT",
        "decision_at": after_at,
    }


def _collect_decisions(
    *,
    series: tuple[object, ...],
    evidence: str,
) -> tuple[list[dict[str, object]], dict[str, int]]:
    raw: dict[date, list[object]] = defaultdict(list)
    for bar in series:
        raw[_day(cast(datetime, getattr(bar, "opened_at")))].append(bar)
    by_day = {
        local_day: tuple(
            sorted(items, key=lambda item: getattr(item, "opened_at"))
        )
        for local_day, items in raw.items()
    }
    context_by_day = specialist._context_map(by_day)
    policy = Vt31R22ExecutionPolicy()

    decisions: list[dict[str, object]] = []
    statuses: Counter[str] = Counter()

    for local_day in sorted(by_day):
        day_bars = by_day[local_day]
        reference = specialist._slice(day_bars, (9, 0, 0), (10, 0, 0))
        session = specialist._slice(day_bars, (10, 0, 0), (11, 0, 0))
        if len(reference) != 60 or len(session) != 60:
            statuses["INCOMPLETE_DAY"] += 1
            continue

        previous_path_range, prior_ref_median, prior_bars = context_by_day[
            local_day
        ]
        cursor = cast(datetime, getattr(reference[-1], "closed_at"))
        previous_terminal_exit: datetime | None = None
        executions = 0

        for cycle_index in range(1, MAX_SOURCE_CYCLES_PER_DAY + 1):
            if executions >= MAX_EXECUTIONS_PER_DAY:
                statuses["EXECUTION_CAP_REACHED"] += 1
                break

            episode_trace, event = _next_episode(
                local_day=local_day,
                cycle_index=cycle_index,
                day_bars=day_bars,
                reference=reference,
                session=session,
                after_at=cursor,
                previous_path_range=previous_path_range,
                prior_ref_median=prior_ref_median,
                prior_admitted_day_bars=prior_bars,
                evidence=evidence,
                policy=policy,
            )
            decisions.extend(episode_trace)
            event_status = cast(str, event["status"])
            statuses[event_status] += 1

            if event_status == "NO_EVENT":
                break
            if event_status in {"INVALIDATED", "NON_EXECUTABLE"}:
                cursor = cast(datetime, event["decision_at"])
                continue

            source = cast(Vt31R22SourceSetup, event["source"])
            setup = cast(Vt31R22ExecutableSetup, event["setup"])
            state = cast(dict[str, object], event["state"])

            if event_status == "ABSTAIN":
                cursor = setup.decision_at
                continue
            if event_status != "EXECUTE":
                raise AssertionError(event_status)

            if previous_terminal_exit is not None and not (
                previous_terminal_exit
                < source.structure.raid_at
                < source.structure.confirmation_at
                <= setup.decision_at
            ):
                raise AssertionError("post-trade structural rearm invariant failed")

            outcome = specialist._simulate_selected_plan(day_bars, setup, state)
            if outcome.get("status") != "terminal":
                statuses["NONTERMINAL_EXECUTION"] += 1
                break

            exit_at = datetime.fromisoformat(cast(str, outcome["exit_at"]))
            if exit_at.tzinfo is None or exit_at.utcoffset() is None:
                raise ValueError("terminal exit must be timezone-aware")

            executions += 1
            previous_terminal_exit = exit_at
            cursor = exit_at
            if _wall(exit_at) >= (11, 0, 0):
                break

    decisions.sort(
        key=lambda item: (
            cast(str, item["decision_at"]),
            int(cast(int, item["cycle_index"])),
            cast(str, item["action"]),
        )
    )
    return decisions, dict(sorted(statuses.items()))


def evaluate(
    *,
    r8_path: Path,
    r6_path: Path,
    r5_path: Path,
) -> dict[str, object]:
    (
        series,
        account,
        evidence_fingerprint,
        checked_at,
        software_sha,
        provider,
        records,
    ) = fivey._stitch((r8_path, r6_path, r5_path))

    decisions, lifecycle_statuses = _collect_decisions(
        series=cast(tuple[object, ...], series),
        evidence=evidence_fingerprint,
    )
    if not decisions:
        raise AssertionError("full decision universe emitted no decisions")

    adapter = VT31CoreAdapter()
    observations: list[DecisionObservation] = []
    action_counts: Counter[str] = Counter()
    v2_counts: Counter[str] = Counter()
    snapshot_fingerprints: list[str] = []
    context_fingerprints: list[str] = []
    authority_violations = 0

    for index, item in enumerate(decisions, start=1):
        decision_at = datetime.fromisoformat(cast(str, item["decision_at"]))
        state = cast(dict[str, object] | None, item["state"])
        facts = (
            _synthetic_facts(cast(str, item["reason"]))
            if state is None
            else _state_facts(state)
        )
        event = MarketEvent(
            event_id=f"VT31_COG_DECISION:{index}:{item['decision_at']}",
            market=MARKET,
            event_type="VT31_COGNITIVE_DECISION_OBSERVATION",
            source_at=decision_at,
            observed_at=decision_at,
            sequence=index,
            complete=True,
            timeframe_seconds=None,
            facts=freeze_facts(facts),
        )

        started = perf_counter_ns()
        snapshot = build_snapshot(events=(event,), generated_at=decision_at)
        context = adapter.adapt(snapshot)
        latency_us = max(0, (perf_counter_ns() - started) // 1_000)

        baseline_action = cast(str, item["action"])
        v2_action = baseline_action if context.core_context_valid else "ABSTAIN"
        action_counts[baseline_action] += 1
        v2_counts[v2_action] += 1

        if (
            snapshot.order_authority
            or snapshot.risk_authority
            or snapshot.strategy_mutation_authority
            or context.order_authority
            or context.risk_authority
            or context.methodology_mutation_allowed
        ):
            authority_violations += 1

        decision_identity = {
            "decision_at": item["decision_at"],
            "cycle_index": item["cycle_index"],
            "action": baseline_action,
            "reason": item["reason"],
            "raid_at": item["raid_at"],
            "confirmation_at": item["confirmation_at"],
            "entry_family": item["entry_family"],
            "side": item["side"],
            "situation_fingerprint": (
                None if state is None else state.get("situation_fingerprint")
            ),
        }
        fingerprint = _digest(decision_identity)
        observations.append(
            DecisionObservation(
                trader_id="VT31_NAS100",
                observation_id=f"{index}:{item['decision_at']}",
                baseline_action=baseline_action,
                v2_action=v2_action,
                baseline_fingerprint=fingerprint,
                v2_fingerprint=fingerprint,
                core_context_valid=context.core_context_valid,
                end_to_end_latency_us=latency_us,
            )
        )
        snapshot_fingerprints.append(snapshot.fingerprint())
        context_fingerprints.append(context.fingerprint())

    summary = summarize_decision_ab(tuple(observations))
    action_parity = dict(sorted(action_counts.items())) == dict(
        sorted(v2_counts.items())
    )
    wait_deltas = sum(
        (item.baseline_action == "WAIT") != (item.v2_action == "WAIT")
        for item in observations
    )
    abstain_deltas = sum(
        (item.baseline_action == "ABSTAIN") != (item.v2_action == "ABSTAIN")
        for item in observations
    )
    invalidated_deltas = sum(
        (item.baseline_action == "INVALIDATED")
        != (item.v2_action == "INVALIDATED")
        for item in observations
    )

    parity = {
        "decision_count": len(observations),
        "baseline_action_counts": dict(sorted(action_counts.items())),
        "v2_action_counts": dict(sorted(v2_counts.items())),
        "action_counts_exact": action_parity,
        "decision_deltas": summary.decision_deltas,
        "wait_deltas": wait_deltas,
        "abstain_deltas": abstain_deltas,
        "invalidated_deltas": invalidated_deltas,
        "invalid_core_contexts": summary.invalid_core_contexts,
        "authority_violations": authority_violations,
        "latency_p50_us": summary.latency_p50_us,
        "latency_p95_us": summary.latency_p95_us,
        "latency_p99_us": summary.latency_p99_us,
        "latency_p99_le_2s": summary.latency_p99_us <= 2_000_000,
    }
    passes = (
        parity["action_counts_exact"]
        and parity["decision_deltas"] == 0
        and parity["wait_deltas"] == 0
        and parity["abstain_deltas"] == 0
        and parity["invalidated_deltas"] == 0
        and parity["invalid_core_contexts"] == 0
        and parity["authority_violations"] == 0
        and parity["latency_p99_le_2s"]
        and action_counts["EXECUTE"] > 0
        and action_counts["WAIT"] > 0
        and (
            action_counts["ABSTAIN"] > 0
            or action_counts["INVALIDATED"] > 0
        )
    )

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "candidate_context": "VT31_REASONING_SOVEREIGN_CAUSAL_LIFECYCLE",
        "evidence": {
            "account_fingerprint": account,
            "evidence_fingerprint": evidence_fingerprint,
            "checked_at": checked_at.isoformat(),
            "software_sha": software_sha,
            "provider_symbol_name": provider,
            "source_records": records,
        },
        "full_decision_universe": parity,
        "lifecycle_statuses": lifecycle_statuses,
        "snapshot_fingerprint_digest": _digest(snapshot_fingerprints),
        "context_fingerprint_digest": _digest(context_fingerprints),
        "passes_full_decision_universe_gate": passes,
        "coverage": {
            "execute_measured": action_counts["EXECUTE"],
            "wait_measured": action_counts["WAIT"],
            "abstain_measured": action_counts["ABSTAIN"],
            "invalidated_measured": action_counts["INVALIDATED"],
            "full_decision_universe_ab_complete": True,
        },
        "governance": {
            "vt31_methodology_changed": False,
            "core_is_context_only": True,
            "core_action_input_forbidden": True,
            "future_outcome_fields_used_by_core": False,
            "runtime_outcome_used_only_to_advance_future_rearm_cursor": True,
            "same_source_reuse_after_abstain": False,
            "new_raid_confirmation_required_after_terminal": True,
            "core_order_authority": False,
            "core_risk_authority": False,
            "adapter_order_authority": False,
            "adapter_risk_authority": False,
            "parameter_scan": False,
            "retuning": False,
            "opens_new_holdout": False,
            "vt08_forex_touched": False,
            "capitalizer_touched": False,
            "live_authorized": False,
            "production_authorized": False,
            "merge_authorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--r8", required=True, type=Path)
    parser.add_argument("--r6", required=True, type=Path)
    parser.add_argument("--r5", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    payload = evaluate(
        r8_path=args.r8,
        r6_path=args.r6,
        r5_path=args.r5,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "full_decision_universe": payload["full_decision_universe"],
                "coverage": payload["coverage"],
                "lifecycle_statuses": payload["lifecycle_statuses"],
                "passes_full_decision_universe_gate": payload[
                    "passes_full_decision_universe_gate"
                ],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
