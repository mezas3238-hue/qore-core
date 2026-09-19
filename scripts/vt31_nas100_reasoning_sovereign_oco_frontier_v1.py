"""Reasoning-sovereign OCO entry frontier for VT31 NAS100.

Consumed development evidence only.

Purpose:
- keep source-level Situation Model -> Reasoning sovereign;
- never reactivate a source after source-level ABSTAIN;
- when a source is approved, let every legitimate entry family compete as an
  OCO order only after that family's evidence has formed and its candidate-
  specific causal state also reaches EXECUTE;
- WAIT remains observational; candidate ABSTAIN never activates an order;
- at most one fill per source event;
- same-bar multi-price ambiguity and post-fill path ambiguity remain censored;
- after a terminal trade, any further trade requires a genuinely new source
  satisfying exit < raid < confirmation <= decision.

This changes entry routing only. No fresh holdout is opened and no policy is
promoted by this lab.
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
import vt31_nas100_entry_intelligence_oco_lab_v1 as oco
import vt31_nas100_reasoning_gate_frontier_v1 as gate
import vt31_nas100_sovereign_reasoned_event_scanner_v1 as sovereign
import vt31_nas100_specialist_r1_candidate as specialist

from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_5_multi_index_research import (
    _day,
    _wall,
    load_market_evidence,
)
from qore.infrastructure.traders.vt31_silver_bullet_r2_2 import (
    Vt31R22EntryEvidence,
    Vt31R22ExecutableSetup,
    Vt31R22ExecutionPolicy,
    Vt31R22SourceSetup,
    evaluate_vt31_r2_2_source,
)

SCHEMA = "qore.vt31.nas100.reasoning_sovereign_oco_frontier.v1"
IDENTITY = "VT31_NAS100_REASONING_SOVEREIGN_OCO_FRONTIER_V1"
MARKET = "NAS100"
MAX_SOURCE_CYCLES_PER_DAY = 8
MAX_EXECUTIONS_PER_DAY = 4
VARIANTS = gate.VARIANTS


def _source_key(source: Vt31R22SourceSetup) -> tuple[str, ...]:
    return oco._source_key(source)


def _candidate_key(candidate: Vt31R22EntryEvidence) -> tuple[str, ...]:
    return oco._candidate_key(candidate)


def _timeline_for_approved_source(
    *,
    reference: tuple[object, ...],
    session: tuple[object, ...],
    after_at: datetime,
    source: Vt31R22SourceSetup,
    evidence: str,
) -> tuple[oco.SourceTimeline, datetime | None]:
    """Collect candidate evidence for one approved post-cursor source."""
    event_prefix: list[object] = list(reference)
    target_key = _source_key(source)
    candidates: dict[tuple[str, ...], Vt31R22EntryEvidence] = {}
    invalidated_at: datetime | None = None
    source_seen = False

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
        if evaluation.both_sides_swept:
            if source_seen:
                invalidated_at = closed_at
                break
            continue
        if evaluation.setup is None:
            continue

        current = evaluation.setup
        current_key = _source_key(current)
        if current_key != target_key:
            if source_seen:
                invalidated_at = closed_at
                break
            continue

        source_seen = True
        for item in current.candidates:
            candidates[_candidate_key(item)] = item

    ordered = tuple(
        candidates[key]
        for key in sorted(
            candidates,
            key=lambda item: (
                datetime.fromisoformat(item[1]),
                item[0],
                item[2],
                item[3],
            ),
        )
    )
    return (
        oco.SourceTimeline(
            source=source,
            candidates=ordered,
            both_sides_swept_at=invalidated_at,
        ),
        invalidated_at,
    )


def _candidate_reasoning_authorization(
    *,
    variant: str,
    day_bars: tuple[object, ...],
    session: tuple[object, ...],
    source: Vt31R22SourceSetup,
    candidate: Vt31R22EntryEvidence,
    source_authorized_at: datetime,
    invalidated_at: datetime | None,
    previous_path_range: Decimal | None,
    prior_ref_median: Decimal | None,
    prior_admitted_day_bars: tuple[object, ...],
    policy: Vt31R22ExecutionPolicy,
) -> tuple[Vt31R22ExecutableSetup, dict[str, object]] | None:
    raw_setup = oco._candidate_order(source, candidate, policy)
    if raw_setup is None:
        return None

    active_from = max(candidate.formed_at, source_authorized_at)
    for bar in session:
        closed_at = cast(datetime, getattr(bar, "closed_at"))
        if closed_at < active_from:
            continue
        if closed_at > raw_setup.pending_expires_at:
            break
        if invalidated_at is not None and closed_at >= invalidated_at:
            break

        setup = activation._activation_setup(raw_setup, closed_at)
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
            setup,
            closed_at,
        )
        action, _ = gate._research_action(
            variant=variant,
            state=state,
            setup=setup,
        )
        if action == "WAIT":
            continue
        if action == "ABSTAIN":
            return None
        if action != "EXECUTE":
            raise ValueError(action)
        return setup, state
    return None


def _select_reasoned_oco(
    *,
    variant: str,
    day_bars: tuple[object, ...],
    session: tuple[object, ...],
    timeline: oco.SourceTimeline,
    source_authorized_at: datetime,
    previous_path_range: Decimal | None,
    prior_ref_median: Decimal | None,
    prior_admitted_day_bars: tuple[object, ...],
    policy: Vt31R22ExecutionPolicy,
) -> tuple[
    Vt31R22ExecutableSetup | None,
    dict[str, object] | None,
    str,
    dict[str, int],
]:
    authorized: list[
        tuple[int, Vt31R22ExecutableSetup, dict[str, object]]
    ] = []
    counts: Counter[str] = Counter()
    censored_second_side = False

    for candidate in timeline.candidates:
        result = _candidate_reasoning_authorization(
            variant=variant,
            day_bars=day_bars,
            session=session,
            source=timeline.source,
            candidate=candidate,
            source_authorized_at=source_authorized_at,
            invalidated_at=timeline.both_sides_swept_at,
            previous_path_range=previous_path_range,
            prior_ref_median=prior_ref_median,
            prior_admitted_day_bars=prior_admitted_day_bars,
            policy=policy,
        )
        family = candidate.family.value
        if result is None:
            counts[f"candidate-{family}-not-authorized"] += 1
            continue

        setup, state = result
        counts[f"candidate-{family}-authorized"] += 1
        fill_index, reason = activation._fill_after_authorization(
            day_bars,
            setup,
            authorization_at=setup.decision_at,
            both_sides_swept_at=timeline.both_sides_swept_at,
        )
        if reason == "censored-same-bar-fill-vs-second-side-sweep":
            censored_second_side = True
        if fill_index is not None:
            authorized.append((fill_index, setup, state))

    if not authorized:
        return (
            None,
            None,
            (
                "censored-second-side-fill-ambiguity"
                if censored_second_side
                else "no-fill"
            ),
            dict(sorted(counts.items())),
        )

    first_index = min(item[0] for item in authorized)
    first = [item for item in authorized if item[0] == first_index]
    prices = {item[1].entry_price for item in first}
    if len(prices) > 1:
        return (
            None,
            None,
            "censored-same-bar-multi-price-oco-fill",
            dict(sorted(counts.items())),
        )

    _, setup, state = sorted(
        first,
        key=lambda item: (
            item[1].decision_at,
            item[1].selected_family.value,
        ),
    )[0]
    return setup, state, "selected", dict(sorted(counts.items()))


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
    candidate_counts: Counter[str] = Counter()
    selected_families: Counter[str] = Counter()
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

            event = gate._next_event(
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
            status[f"source-{event_status.lower()}"] += 1

            if event_status == "NO_EVENT":
                break
            if event_status in {"INVALIDATED", "NON_EXECUTABLE"}:
                cursor = cast(datetime, event["decision_at"])
                continue
            if event_status == "ABSTAIN":
                setup = cast(Vt31R22ExecutableSetup, event["setup"])
                cursor = setup.decision_at
                continue
            if event_status != "EXECUTE":
                raise AssertionError(event_status)

            source = cast(Vt31R22SourceSetup, event["source"])
            source_setup = cast(Vt31R22ExecutableSetup, event["setup"])
            source_authorized_at = source_setup.decision_at

            timeline, invalidated_at = _timeline_for_approved_source(
                reference=reference,
                session=session,
                after_at=cursor,
                source=source,
                evidence=evidence,
            )
            selected, selected_state, selection_status, local_counts = (
                _select_reasoned_oco(
                    variant=variant,
                    day_bars=day_bars,
                    session=session,
                    timeline=timeline,
                    source_authorized_at=source_authorized_at,
                    previous_path_range=previous_path_range,
                    prior_ref_median=prior_ref_median,
                    prior_admitted_day_bars=prior_bars,
                    policy=policy,
                )
            )
            candidate_counts.update(local_counts)
            status[f"oco-{selection_status}"] += 1

            if selected is None or selected_state is None:
                if (
                    selection_status == "no-fill"
                    and invalidated_at is not None
                    and invalidated_at > cursor
                ):
                    cursor = invalidated_at
                    status["oco-no-fill-source-invalidated-continue"] += 1
                    continue
                # No-fill without a causal invalidation is only known at the
                # 11:00 pending expiry. Ambiguous fills also make downstream
                # account state unknowable. Fail closed for the rest of the day.
                break

            if previous_exit is not None and not (
                previous_exit
                < selected.source_setup.structure.raid_at
                < selected.source_setup.structure.confirmation_at
                <= selected.decision_at
            ):
                raise AssertionError(
                    "post-trade source violates structural rearm invariant"
                )

            outcome = specialist._simulate_selected_plan(
                day_bars,
                selected,
                selected_state,
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
                    "tier": "REASONING_SOVEREIGN_OCO",
                    "authorization_reason": (
                        "SOURCE_EXECUTE_AND_CANDIDATE_EXECUTE"
                    ),
                    "raid_at": (
                        selected.source_setup.structure.raid_at
                        .astimezone(UTC)
                        .isoformat()
                    ),
                    "confirmation_at": (
                        selected.source_setup.structure.confirmation_at
                        .astimezone(UTC)
                        .isoformat()
                    ),
                    "decision_at": selected.decision_at.astimezone(
                        UTC
                    ).isoformat(),
                    "entry_family": selected.selected_family.value,
                    "side": selected.side.value,
                    "net_r_after_friction": format(
                        sovereign._net_r(outcome),
                        "f",
                    ),
                    "loss_path_class": sovereign._loss_path(outcome),
                    "reasoning_sovereign": True,
                    "same_source_after_abstain": False,
                    "oco_max_one_fill_per_source": True,
                }
            )
            rows.append(row)
            selected_families[selected.selected_family.value] += 1
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
        partition=f"{partition}:OCO:{variant}",
    )
    losses = Counter(
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
        "loss_path_counts": dict(sorted(losses.items())),
        "status_counts": dict(sorted(status.items())),
        "candidate_authorization_counts": dict(
            sorted(candidate_counts.items())
        ),
        "selected_family_counts": dict(sorted(selected_families.items())),
    }


def replay(path: Path, *, partition: str) -> dict[str, object]:
    series, account, evidence, checked, evidence_sha, provider = (
        load_market_evidence(path)
    )
    if not series or getattr(series[0], "instrument").symbol != MARKET:
        raise ValueError("reasoning-sovereign OCO requires NAS100")

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
            "source_reasoning_sovereign": True,
            "candidate_reasoning_sovereign": True,
            "same_source_after_abstain_disabled": True,
            "one_fill_max_per_source_event": True,
            "candidate_order_activates_after_evidence_forms": True,
            "candidate_wait_remains_observational": True,
            "candidate_abstain_never_activates_order": True,
            "same_bar_multi_price_fill_censored": True,
            "second_side_sweep_cancels_source": True,
            "post_exit_structural_rearm_required": True,
            "event_detection_resets_after_cursor": True,
            "situation_model_preserves_full_session_history": True,
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
