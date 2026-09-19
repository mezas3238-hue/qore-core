"""VT31 NAS100 conjunctive reasoning-gate frontier V1.

Consumed-evidence research only.

This frontier keeps Reasoning sovereign but tests whether the current
"any contradiction => ABSTAIN" semantics are over-restrictive.

All variants are causal and pre-entry only. The key research hypothesis is that
two currently independent hard gates should be reasoned conjunctively:
- current path not compressed; and
- non-compressed reference outside the retained low-DD fallback.

Their exact conjunction was negative in R5/R6/R8/consumed evidence, while each
component alone was not stable enough to justify a universal veto.

Order-block entry family and >=11m confirmation latency are tested as separate
causal additions because both were negative across all four consumed windows.
No variant is promoted here.
"""
# ruff: noqa: B009
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

import vt31_nas100_causal_hybrid_replay_v1 as activation
import vt31_nas100_sovereign_reasoned_event_scanner_v1 as sovereign
import vt31_nas100_specialist_r1_candidate as specialist

from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_5_multi_index_research import (
    _day,
    _wall,
    load_market_evidence,
)
from qore.infrastructure.traders.vt31_silver_bullet_r2_2 import (
    Vt31R22ExecutableSetup,
    Vt31R22ExecutionPolicy,
    Vt31R22SourceSetup,
    evaluate_vt31_r2_2_source,
    make_executable_setup,
)

SCHEMA = "qore.vt31.nas100.reasoning_gate_frontier.v1"
IDENTITY = "VT31_NAS100_REASONING_GATE_FRONTIER_V1"
MARKET = "NAS100"
MAX_SOURCE_CYCLES_PER_DAY = 8
MAX_EXECUTIONS_PER_DAY = 4

VARIANTS = (
    "CURRENT_GATES",
    "DUAL_EXPANSION",
    "DUAL_EXPANSION_PLUS_OB",
    "DUAL_EXPANSION_PLUS_LAT11",
    "DUAL_EXPANSION_PLUS_OB_LAT11",
)

_TRANSIENT_WAIT_CODES = {
    "STRATEGY:SOURCE_CONFIRMATION_NOT_COMPLETE",
    "STRATEGY:ENTRY_EVIDENCE_NOT_ACTIONABLE",
    "SITUATION:REFERENCE_LIQUIDITY_STATE_NOT_YET_PRESENT",
    "EXPERIENCE:SEQUENCE_STALE_8_14_REQUIRES_REEVALUATION",
}


def _research_action(
    *,
    variant: str,
    state: dict[str, object],
    setup: Vt31R22ExecutableSetup,
) -> tuple[str, tuple[str, ...]]:
    if variant == "CURRENT_GATES":
        return (
            cast(str, state["action"]),
            tuple(
                cast(
                    list[str],
                    state.get("reasoning_contradictions", []),
                )
            ),
        )

    ratio_raw = state.get("current_path_vs_previous")
    ratio = None if ratio_raw is None else Decimal(str(ratio_raw))
    path_not_compressed = ratio is not None and ratio >= Decimal("0.75")

    reference_compressed = (
        state.get("reference_volatility_state") == "compressed"
    )
    low_dd_fallback = (
        setup.side.value == "short"
        and state.get("h1_state") == "mixed"
    )
    noncompressed_outside_gate = (
        not reference_compressed and not low_dd_fallback
    )
    dual_expansion = path_not_compressed and noncompressed_outside_gate

    latency_raw = state.get("confirmation_latency_minutes")
    latency = None if latency_raw is None else int(latency_raw)
    late_confirmation = latency is not None and latency >= 11
    order_block = setup.selected_family.value == "order-block"

    hard: list[str] = []
    if dual_expansion:
        hard.append("CAUSAL:DUAL_EXPANSION_CONFLICT")
    if variant in {
        "DUAL_EXPANSION_PLUS_OB",
        "DUAL_EXPANSION_PLUS_OB_LAT11",
    } and order_block:
        hard.append("CAUSAL:ORDER_BLOCK_STABLE_NEGATIVE")
    if variant in {
        "DUAL_EXPANSION_PLUS_LAT11",
        "DUAL_EXPANSION_PLUS_OB_LAT11",
    } and late_confirmation:
        hard.append("CAUSAL:CONFIRMATION_LATENCY_11M_PLUS")

    uncertainty = set(
        cast(list[str], state.get("reasoning_uncertainty", []))
    )
    transient_wait = bool(uncertainty & _TRANSIENT_WAIT_CODES)

    if hard:
        return "ABSTAIN", tuple(hard)
    if transient_wait:
        return "WAIT", ()
    return "EXECUTE", ()


def _next_event(
    *,
    variant: str,
    day_bars: tuple[object, ...],
    reference: tuple[object, ...],
    session: tuple[object, ...],
    after_at: datetime,
    previous_path_range: Decimal | None,
    prior_ref_median: Decimal | None,
    prior_admitted_day_bars: tuple[object, ...],
    evidence: str,
    policy: Vt31R22ExecutionPolicy,
) -> dict[str, object]:
    event_prefix: list[object] = list(reference)
    saw_wait = False
    active_source_raid: datetime | None = None

    for bar in session:
        closed_at = cast(datetime, getattr(bar, "closed_at"))
        if closed_at <= after_at:
            continue
        event_prefix.append(bar)

        evaluation = evaluate_vt31_r2_2_source(
            instrument=getattr(bar, "instrument"),
            as_of=closed_at,
            m1_candles=cast(Any, tuple(event_prefix)),
            evidence_fingerprint=evidence,
        )
        if evaluation.setup is None:
            if saw_wait and evaluation.both_sides_swept:
                return {
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

        if (
            active_source_raid is not None
            and source.structure.raid_at != active_source_raid
        ):
            saw_wait = False
        active_source_raid = source.structure.raid_at

        executable, _ = make_executable_setup(source, policy)
        if executable is None:
            return {
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
        action, hard_reasons = _research_action(
            variant=variant,
            state=state,
            setup=executable,
        )
        if action == "WAIT":
            saw_wait = True
            continue
        if action == "ABSTAIN":
            return {
                "status": "ABSTAIN",
                "decision_at": closed_at,
                "source": source,
                "setup": executable,
                "state": state,
                "research_hard_reasons": hard_reasons,
            }
        if action != "EXECUTE":
            raise ValueError(action)

        activated = activation._activation_setup(executable, closed_at)
        return {
            "status": "EXECUTE",
            "decision_at": closed_at,
            "source": source,
            "setup": activated,
            "state": state,
            "research_hard_reasons": hard_reasons,
        }

    return {
        "status": "NO_EVENT",
        "decision_at": after_at,
    }


def _run_variant(
    *,
    variant: str,
    by_day: dict[date, tuple[object, ...]],
    context_by_day: dict[
        date,
        tuple[Decimal | None, Decimal | None, tuple[object, ...]],
    ],
    evidence: str,
    partition: str,
) -> dict[str, object]:
    policy = Vt31R22ExecutionPolicy()
    rows: list[dict[str, object]] = []
    status: Counter[str] = Counter()
    hard_reason_counts: Counter[str] = Counter()
    events_per_day: Counter[int] = Counter()

    for local_day in sorted(by_day):
        day_bars = by_day[local_day]
        reference = specialist._slice(day_bars, (9, 0, 0), (10, 0, 0))
        session = specialist._slice(day_bars, (10, 0, 0), (11, 0, 0))
        if len(reference) != 60 or len(session) != 60:
            status["incomplete-day"] += 1
            continue

        previous_path_range, prior_ref_median, prior_bars = (
            context_by_day[local_day]
        )
        cursor = cast(datetime, getattr(reference[-1], "closed_at"))
        previous_exit: datetime | None = None
        executions = 0

        for cycle_index in range(1, MAX_SOURCE_CYCLES_PER_DAY + 1):
            if executions >= MAX_EXECUTIONS_PER_DAY:
                status["execution-cap-reached"] += 1
                break

            event = _next_event(
                variant=variant,
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
            event_status = cast(str, event["status"])
            status[event_status] += 1

            if event_status == "NO_EVENT":
                break
            if event_status in {"INVALIDATED", "NON_EXECUTABLE"}:
                cursor = cast(datetime, event["decision_at"])
                continue

            source = cast(Vt31R22SourceSetup, event["source"])
            setup = cast(Vt31R22ExecutableSetup, event["setup"])
            state = cast(dict[str, object], event["state"])
            for code in cast(
                tuple[str, ...],
                event["research_hard_reasons"],
            ):
                hard_reason_counts[code] += 1

            if not (
                source.structure.raid_at > cursor
                and source.structure.confirmation_at > cursor
                and setup.decision_at > cursor
            ):
                raise AssertionError(
                    "source must be strictly newer than current cursor"
                )

            if event_status == "ABSTAIN":
                cursor = setup.decision_at
                continue

            if previous_exit is not None and not (
                previous_exit
                < source.structure.raid_at
                < source.structure.confirmation_at
                <= setup.decision_at
            ):
                raise AssertionError(
                    "post-trade source violates structural rearm invariant"
                )

            outcome = specialist._simulate_selected_plan(
                day_bars,
                setup,
                state,
            )
            status[f"outcome-{outcome['status']}"] += 1
            if outcome.get("status") != "terminal":
                break

            exit_at = datetime.fromisoformat(cast(str, outcome["exit_at"]))
            if exit_at.tzinfo is None:
                raise ValueError("terminal exit must be timezone-aware")

            row = dict(outcome)
            row.update(
                {
                    "partition": partition,
                    "variant": variant,
                    "local_date": local_day.isoformat(),
                    "event_index": executions + 1,
                    "cycle_index": cycle_index,
                    "raid_at": source.structure.raid_at.astimezone(
                        UTC
                    ).isoformat(),
                    "confirmation_at": (
                        source.structure.confirmation_at.astimezone(
                            UTC
                        ).isoformat()
                    ),
                    "decision_at": setup.decision_at.astimezone(
                        UTC
                    ).isoformat(),
                    "entry_family": setup.selected_family.value,
                    "side": setup.side.value,
                    "research_action": "EXECUTE",
                    "original_reasoning_action": state["action"],
                    "net_r_after_friction": format(
                        sovereign._net_r(outcome),
                        "f",
                    ),
                    "loss_path_class": sovereign._loss_path(outcome),
                    "reasoning_sovereign": True,
                    "same_source_secondary_disabled": True,
                }
            )
            rows.append(row)
            executions += 1
            previous_exit = exit_at
            cursor = exit_at
            if _wall(exit_at) >= (11, 0, 0):
                break

        events_per_day[executions] += 1

    rows.sort(key=lambda row: cast(str, row["signal_at"]))
    metrics = sovereign._metrics_net(rows)
    mc = sovereign._monte_carlo_net(
        rows,
        partition=f"{partition}:{variant}",
    )
    loss_counts = Counter(
        str(row["loss_path_class"])
        for row in rows
        if Decimal(cast(str, row["net_r_after_friction"])) < 0
    )
    return {
        "trade_count": len(rows),
        "unique_trade_days": len(
            {cast(str, row["local_date"]) for row in rows}
        ),
        "events_per_day": {
            str(key): value for key, value in sorted(events_per_day.items())
        },
        "metrics": metrics,
        "monte_carlo": mc,
        "annual_metrics": sovereign._annual(rows),
        "loss_path_counts": dict(sorted(loss_counts.items())),
        "status_counts": dict(sorted(status.items())),
        "hard_reason_counts": dict(sorted(hard_reason_counts.items())),
    }


def replay(path: Path, *, partition: str) -> dict[str, object]:
    series, account, evidence, checked, evidence_sha, provider = (
        load_market_evidence(path)
    )
    if not series or getattr(series[0], "instrument").symbol != MARKET:
        raise ValueError("reasoning-gate frontier requires NAS100")

    raw: dict[date, list[object]] = defaultdict(list)
    for bar in series:
        raw[_day(getattr(bar, "opened_at"))].append(bar)
    by_day = {
        local_day: tuple(
            sorted(items, key=lambda item: getattr(item, "opened_at"))
        )
        for local_day, items in raw.items()
    }
    context_by_day = specialist._context_map(by_day)

    variants = {
        variant: _run_variant(
            variant=variant,
            by_day=by_day,
            context_by_day=context_by_day,
            evidence=evidence,
            partition=partition,
        )
        for variant in VARIANTS
    }

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "partition": partition,
        "market": MARKET,
        "variants": variants,
        "evidence": {
            "account_fingerprint": account,
            "evidence_fingerprint": evidence,
            "checked_at": checked.isoformat(),
            "evidence_software_sha": evidence_sha,
            "provider_symbol_name": provider,
        },
        "governance": {
            "consumed_evidence_only": True,
            "predeclared_variants_only": True,
            "pre_entry_causal_features_only": True,
            "reasoning_sovereign_for_every_execution": True,
            "same_source_secondary_disabled": True,
            "scout_after_wait_disabled": True,
            "new_source_required_after_abstain": True,
            "event_detection_resets_after_cursor": True,
            "situation_model_preserves_full_session_history": True,
            "post_exit_structural_rearm_required": True,
            "uses_terminal_pnl_at_runtime": False,
            "uses_fold_identity_at_runtime": False,
            "uses_calendar_time_at_runtime": False,
            "opens_new_holdout": False,
            "policy_promoted": False,
            "candidate_certified": False,
            "live_authorized": False,
            "production_authorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path)
    parser.add_argument("--partition", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    payload = replay(args.evidence, partition=args.partition)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "partition": payload["partition"],
                "variants": payload["variants"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
