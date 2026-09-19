"""VT31 NAS100 sovereign reasoned-event scanner V1.

Consumed-evidence research only.

Purpose:
- remove same-source density overrides after Reasoning WAIT/ABSTAIN;
- make Situation Model -> Reasoning sovereign for every executable event;
- keep WAIT observational (same hypothesis may continue evolving);
- make ABSTAIN terminal for the current source hypothesis;
- after ABSTAIN, invalidation, non-executable routing, or terminal exit,
  require a genuinely new raid + confirmation + decision;
- permit multiple trades only when each is a distinct causal source event.

This is an architecture/capacity experiment, not an operating policy.
No fresh holdout is opened and no production authority is granted.
"""
# ruff: noqa: B009
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

import vt31_nas100_causal_hybrid_replay_v1 as activation
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
    Vt31R22SourceSetup,
    evaluate_vt31_r2_2_source,
    make_executable_setup,
)

SCHEMA = "qore.vt31.nas100.sovereign_reasoned_event_scanner.v1"
IDENTITY = "VT31_NAS100_SOVEREIGN_REASONED_EVENT_SCANNER_V1"
MARKET = "NAS100"
FRICTION = Decimal("0.05")
MAX_SOURCE_CYCLES_PER_DAY = 8
MAX_EXECUTIONS_PER_DAY = 4


def _net_r(outcome: dict[str, object]) -> Decimal:
    return Decimal(cast(str, outcome["r_multiple"])) - FRICTION


def _metrics_net(rows: list[dict[str, object]]) -> dict[str, object]:
    converted = [
        {**row, "r_multiple": row["net_r_after_friction"]}
        for row in rows
    ]
    return _metrics(converted, friction=Decimal(0))


def _monte_carlo_net(
    rows: list[dict[str, object]],
    *,
    partition: str,
) -> dict[str, object]:
    values = [
        Decimal(cast(str, row["net_r_after_friction"]))
        for row in rows
    ]
    n = len(values)
    if not values:
        return {
            "paths": 10000,
            "block_length": 5,
            "positive_terminal_probability": "0",
            "p95_max_drawdown_r": "0",
        }

    domain = f"{IDENTITY}:{partition}".encode()
    terminals: list[Decimal] = []
    drawdowns: list[Decimal] = []
    for path_index in range(10000):
        sampled: list[Decimal] = []
        block_index = 0
        while len(sampled) < n:
            digest = hashlib.sha256(
                domain
                + b":"
                + str(path_index).encode()
                + b":"
                + str(block_index).encode()
            ).digest()
            start = int.from_bytes(digest, "big") % n
            sampled.extend(values[(start + offset) % n] for offset in range(5))
            block_index += 1

        equity = Decimal(0)
        peak = Decimal(0)
        max_dd = Decimal(0)
        for value in sampled[:n]:
            equity += value
            peak = max(peak, equity)
            max_dd = max(max_dd, peak - equity)
        terminals.append(equity)
        drawdowns.append(max_dd)

    terminals.sort()
    drawdowns.sort()
    return {
        "algorithm": "sha256-moving-block-bootstrap-v1",
        "paths": 10000,
        "block_length": 5,
        "positive_terminal_probability": format(
            Decimal(sum(item > 0 for item in terminals)) / Decimal(10000),
            "f",
        ),
        "p05_terminal_r": format(
            terminals[(len(terminals) - 1) * 5 // 100],
            "f",
        ),
        "p50_terminal_r": format(
            terminals[(len(terminals) - 1) * 50 // 100],
            "f",
        ),
        "p95_max_drawdown_r": format(
            drawdowns[(len(drawdowns) - 1) * 95 // 100],
            "f",
        ),
    }


def _next_reasoned_event(
    *,
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
    """Resolve one causal source episode strictly after after_at."""
    # Event identity and market understanding have different causal scopes.
    # A new source event must be detected only from bars after the cursor,
    # while Situation Model / Reasoning must retain every session bar observed
    # up to the decision.
    event_prefix: list[object] = list(reference)
    saw_wait = False
    first_source_raid: datetime | None = None

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
                    "reason": "BOTH_SIDES_SWEPT_AFTER_WAIT",
                }
            continue

        source = evaluation.setup
        if (
            source.structure.raid_at <= after_at
            or source.structure.confirmation_at <= after_at
        ):
            # This is the pre-cursor hypothesis still visible in the complete
            # history.  It is intentionally not reusable after ABSTAIN/exit.
            continue

        if first_source_raid is None:
            first_source_raid = source.structure.raid_at
        elif source.structure.raid_at != first_source_raid:
            # A genuinely new source replaced a WAIT hypothesis.  Continue
            # reasoning on the new source without advancing the cursor past it.
            first_source_raid = source.structure.raid_at
            saw_wait = False

        executable, _ = make_executable_setup(source, policy)
        if executable is None:
            return {
                "status": "NON_EXECUTABLE",
                "decision_at": closed_at,
                "reason": "SOURCE_NOT_SINGLE_ROUTE_EXECUTABLE",
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
                "reason": "REASONING_ABSTAIN",
            }
        if action != "EXECUTE":
            raise ValueError(f"unsupported reasoning action={action}")

        activated = activation._activation_setup(executable, closed_at)
        return {
            "status": "EXECUTE",
            "decision_at": closed_at,
            "source": source,
            "setup": activated,
            "state": state,
            "reason": "REASONING_EXECUTE",
        }

    return {
        "status": "NO_EVENT",
        "decision_at": after_at,
        "reason": "SESSION_EXHAUSTED",
    }


def _annual(rows: list[dict[str, object]]) -> dict[str, dict[str, object]]:
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        grouped[cast(str, row["local_date"])[:4]].append(row)
    return {
        year: _metrics_net(items)
        for year, items in sorted(grouped.items())
    }


def _loss_path(outcome: dict[str, object]) -> str:
    net = _net_r(outcome)
    if net >= 0:
        return "NON_LOSS"
    mfe = Decimal(str(outcome.get("mfe_r") or "0"))
    reason = str(outcome.get("exit_reason"))
    if reason == "breakeven-stop":
        return "BREAKEVEN_FRICTION_LOSS"
    if mfe >= Decimal("1.00"):
        return "GIVEBACK_AFTER_1R_PLUS"
    if reason == "initial-stop" and mfe < Decimal("0.50"):
        return "DEAD_ON_ARRIVAL"
    if reason == "initial-stop" and mfe < Decimal("1.00"):
        return "WEAK_FOLLOW_THROUGH"
    return "OTHER_LOSS"


def replay(path: Path, *, partition: str) -> dict[str, object]:
    series, account, evidence, checked, evidence_sha, provider = (
        load_market_evidence(path)
    )
    if not series or getattr(series[0], "instrument").symbol != MARKET:
        raise ValueError("sovereign reasoned-event scanner requires NAS100")

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
    policy = Vt31R22ExecutionPolicy()

    status: Counter[str] = Counter()
    action_reasons: Counter[str] = Counter()
    contradiction_counts: Counter[str] = Counter()
    uncertainty_counts: Counter[str] = Counter()
    executions_per_day: Counter[int] = Counter()
    rows: list[dict[str, object]] = []
    traces: list[dict[str, object]] = []

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
        previous_terminal_exit: datetime | None = None
        executions = 0

        for cycle_index in range(1, MAX_SOURCE_CYCLES_PER_DAY + 1):
            if executions >= MAX_EXECUTIONS_PER_DAY:
                status["execution-cap-reached"] += 1
                break

            event = _next_reasoned_event(
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
            if event_status in {
                "INVALIDATED",
                "NON_EXECUTABLE",
                "ROLLED_TO_NEW_SOURCE",
            }:
                cursor = cast(datetime, event["decision_at"])
                traces.append(
                    {
                        "local_date": local_day.isoformat(),
                        "cycle_index": cycle_index,
                        "status": event_status,
                        "decision_at": cursor.astimezone(UTC).isoformat(),
                        "reason": event["reason"],
                    }
                )
                continue

            source = cast(Vt31R22SourceSetup, event["source"])
            setup = cast(Vt31R22ExecutableSetup, event["setup"])
            state = cast(dict[str, object], event["state"])
            action_reasons[cast(str, event["reason"])] += 1

            for code in cast(list[str], state.get("reasoning_contradictions", [])):
                contradiction_counts[code] += 1
            for code in cast(list[str], state.get("reasoning_uncertainty", [])):
                uncertainty_counts[code] += 1

            if not (
                source.structure.raid_at > cursor
                and source.structure.confirmation_at > cursor
                and setup.decision_at > cursor
            ):
                raise AssertionError("new source event must be strictly after cursor")

            if event_status == "ABSTAIN":
                traces.append(
                    {
                        "local_date": local_day.isoformat(),
                        "cycle_index": cycle_index,
                        "status": "ABSTAIN",
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
                        "contradictions": list(
                            cast(
                                list[str],
                                state.get("reasoning_contradictions", []),
                            )
                        ),
                        "uncertainty": list(
                            cast(
                                list[str],
                                state.get("reasoning_uncertainty", []),
                            )
                        ),
                    }
                )
                cursor = setup.decision_at
                continue

            if event_status != "EXECUTE":
                raise AssertionError(event_status)

            if (
                previous_terminal_exit is not None
                and not (
                    previous_terminal_exit
                    < source.structure.raid_at
                    < source.structure.confirmation_at
                    <= setup.decision_at
                )
            ):
                raise AssertionError(
                    "post-trade event must satisfy exit < raid < "
                    "confirmation <= decision"
                )

            outcome = specialist._simulate_selected_plan(
                day_bars,
                setup,
                state,
            )
            status[f"outcome-{outcome['status']}"] += 1
            if outcome.get("status") != "terminal":
                traces.append(
                    {
                        "local_date": local_day.isoformat(),
                        "cycle_index": cycle_index,
                        "status": "NONTERMINAL_EXECUTION",
                        "decision_at": setup.decision_at.astimezone(
                            UTC
                        ).isoformat(),
                    }
                )
                break

            exit_at = datetime.fromisoformat(cast(str, outcome["exit_at"]))
            if exit_at.tzinfo is None:
                raise ValueError("terminal exit must be timezone-aware")

            row = dict(outcome)
            row.update(
                {
                    "partition": partition,
                    "local_date": local_day.isoformat(),
                    "event_index": executions + 1,
                    "cycle_index": cycle_index,
                    "tier": "REASONING_SOVEREIGN",
                    "authorization_reason": "REASONING_EXECUTE",
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
                    "reasoning_action": state["action"],
                    "reasoning_contradictions": list(
                        cast(
                            list[str],
                            state.get("reasoning_contradictions", []),
                        )
                    ),
                    "reasoning_uncertainty": list(
                        cast(
                            list[str],
                            state.get("reasoning_uncertainty", []),
                        )
                    ),
                    "reference_volatility_state": state.get(
                        "reference_volatility_state"
                    ),
                    "current_path_vs_previous": state.get(
                        "current_path_vs_previous"
                    ),
                    "h1_state": state.get("h1_state"),
                    "h4_state": state.get("h4_state"),
                    "premarket_state": state.get("premarket_state"),
                    "cash_open_state": state.get("cash_open_state"),
                    "reference_reclaim_age_minutes": state.get(
                        "reference_reclaim_age_minutes"
                    ),
                    "confirmation_latency_minutes": state.get(
                        "confirmation_latency_minutes"
                    ),
                    "risk_ref": state.get("risk_ref"),
                    "net_r_after_friction": format(_net_r(outcome), "f"),
                    "loss_path_class": _loss_path(outcome),
                    "used_same_source_after_abstain": False,
                    "reasoning_sovereign": True,
                }
            )
            rows.append(row)
            traces.append(
                {
                    "local_date": local_day.isoformat(),
                    "cycle_index": cycle_index,
                    "status": "EXECUTED",
                    "event_index": executions + 1,
                    "raid_at": row["raid_at"],
                    "confirmation_at": row["confirmation_at"],
                    "decision_at": row["decision_at"],
                    "exit_at": outcome["exit_at"],
                    "entry_family": row["entry_family"],
                }
            )

            executions += 1
            previous_terminal_exit = exit_at
            cursor = exit_at
            if _wall(exit_at) >= (11, 0, 0):
                break

        executions_per_day[executions] += 1

    rows.sort(key=lambda row: cast(str, row["signal_at"]))
    loss_counts = Counter(
        str(row["loss_path_class"])
        for row in rows
        if Decimal(cast(str, row["net_r_after_friction"])) < 0
    )
    metrics = _metrics_net(rows)
    mc = _monte_carlo_net(rows, partition=partition)

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "partition": partition,
        "market": MARKET,
        "trade_count": len(rows),
        "unique_trade_days": len(
            {cast(str, row["local_date"]) for row in rows}
        ),
        "events_per_day": {
            str(key): value for key, value in sorted(executions_per_day.items())
        },
        "metrics_net_r": metrics,
        "monte_carlo_net_r": mc,
        "annual_metrics_net_r": _annual(rows),
        "loss_path_counts": dict(sorted(loss_counts.items())),
        "status_counts": dict(sorted(status.items())),
        "action_reason_counts": dict(sorted(action_reasons.items())),
        "contradiction_counts": dict(sorted(contradiction_counts.items())),
        "uncertainty_counts": dict(sorted(uncertainty_counts.items())),
        "trades": rows,
        "traces": traces,
        "evidence": {
            "account_fingerprint": account,
            "evidence_fingerprint": evidence,
            "checked_at": checked.isoformat(),
            "evidence_software_sha": evidence_sha,
            "provider_symbol_name": provider,
        },
        "governance": {
            "consumed_evidence_only": True,
            "architecture_capacity_research": True,
            "reasoning_sovereign_for_every_execution": True,
            "wait_keeps_observing_same_source": True,
            "abstain_kills_current_source": True,
            "new_event_requires_new_raid_confirmation_decision": True,
            "event_detection_resets_after_cursor": True,
            "situation_model_preserves_full_session_history": True,
            "same_source_secondary_disabled": True,
            "scout_after_wait_disabled": True,
            "post_exit_event_requires_structural_rearm": True,
            "max_one_trade_per_source_event": True,
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
                "trade_count": payload["trade_count"],
                "unique_trade_days": payload["unique_trade_days"],
                "events_per_day": payload["events_per_day"],
                "metrics_net_r": payload["metrics_net_r"],
                "monte_carlo_net_r": payload["monte_carlo_net_r"],
                "annual_metrics_net_r": payload["annual_metrics_net_r"],
                "loss_path_counts": payload["loss_path_counts"],
                "status_counts": payload["status_counts"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
