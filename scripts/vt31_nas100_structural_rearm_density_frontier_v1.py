"""VT31 NAS100 structural-rearm density frontier V1.

Consumed-evidence research only.

Goal:
- measure how much *genuine* extra density exists after a completed trade;
- keep the frozen 09:00-10:00 NY reference;
- require each additional event to form strictly after the previous terminal exit;
- require a new raid, new structural confirmation and new decision;
- allow at most one trade per source event;
- do not manufacture density with duplicate fills or micro-entries.

This is a capacity/frontier experiment, not an operating policy. Economics are
reported only to characterize the frontier. No fresh holdout is opened.
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

import vt31_nas100_r1_candidate as baseline
import vt31_nas100_specialist_r1_candidate as specialist

from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_5_multi_index_research import (
    _day,
    _metrics,
    _wall,
    load_market_evidence,
)
from qore.infrastructure.traders.vt31_nas100_position_intelligence import (
    structurally_rearmed,
)
from qore.infrastructure.traders.vt31_silver_bullet_r2_2 import (
    Vt31R22ExecutableSetup,
    Vt31R22ExecutionPolicy,
    Vt31R22SourceSetup,
    evaluate_vt31_r2_2_source,
    make_executable_setup,
)

SCHEMA = "qore.vt31.nas100.structural_rearm_density_frontier.v1"
IDENTITY = "VT31_NAS100_STRUCTURAL_REARM_DENSITY_FRONTIER_V1"
MARKET = "NAS100"
MAX_EVENTS_PER_DAY = 4
FRICTION = Decimal("0.05")


def _next_executable_after(
    *,
    reference: tuple[object, ...],
    session: tuple[object, ...],
    after_at: datetime,
    evidence: str,
    policy: Vt31R22ExecutionPolicy,
) -> tuple[Vt31R22SourceSetup, Vt31R22ExecutableSetup] | None:
    """Find first executable source built only from bars closed after after_at."""
    prefix: list[object] = list(reference)
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
            if evaluation.both_sides_swept:
                return None
            continue
        executable, _ = make_executable_setup(
            evaluation.setup,
            policy,
        )
        if executable is None:
            continue
        return evaluation.setup, executable
    return None


def _terminal_trade(
    day_bars: tuple[object, ...],
    setup: Vt31R22ExecutableSetup,
) -> dict[str, object] | None:
    outcome = baseline._simulate(day_bars, setup)
    if outcome.get("status") != "terminal":
        return None
    return outcome


def replay(
    evidence_path: Path,
    *,
    partition: str,
) -> dict[str, object]:
    series, account, evidence, checked, evidence_sha, provider = (
        load_market_evidence(evidence_path)
    )
    if not series or getattr(series[0], "instrument").symbol != MARKET:
        raise ValueError("structural rearm frontier requires NAS100 evidence")

    raw: dict[date, list[object]] = defaultdict(list)
    for bar in series:
        raw[_day(getattr(bar, "opened_at"))].append(bar)
    by_day = {
        local_day: tuple(
            sorted(items, key=lambda item: getattr(item, "opened_at"))
        )
        for local_day, items in raw.items()
    }

    policy = Vt31R22ExecutionPolicy()
    status: Counter[str] = Counter()
    events_per_day: Counter[int] = Counter()
    terminal_trades: list[dict[str, object]] = []
    rearm_trades: list[dict[str, object]] = []
    traces: list[dict[str, object]] = []

    for local_day in sorted(by_day):
        day_bars = by_day[local_day]
        reference = specialist._slice(
            day_bars,
            (9, 0, 0),
            (10, 0, 0),
        )
        session = specialist._slice(
            day_bars,
            (10, 0, 0),
            (11, 0, 0),
        )
        if len(reference) != 60 or len(session) != 60:
            status["incomplete-day"] += 1
            continue

        cursor = cast(datetime, getattr(reference[-1], "closed_at"))
        previous_exit: datetime | None = None
        day_count = 0

        for event_index in range(1, MAX_EVENTS_PER_DAY + 1):
            selected = _next_executable_after(
                reference=reference,
                session=session,
                after_at=cursor,
                evidence=evidence,
                policy=policy,
            )
            if selected is None:
                status[f"event-{event_index}-none"] += 1
                break

            source, executable = selected
            is_rearmed = structurally_rearmed(
                protected_exit_at_epoch=(
                    None
                    if previous_exit is None
                    else int(previous_exit.timestamp())
                ),
                new_raid_at_epoch=int(
                    source.structure.raid_at.timestamp()
                ),
                new_confirmation_at_epoch=int(
                    source.structure.confirmation_at.timestamp()
                ),
                new_decision_at_epoch=int(
                    executable.decision_at.timestamp()
                ),
            )
            if not is_rearmed:
                status["rearm-invariant-failed"] += 1
                break

            outcome = _terminal_trade(day_bars, executable)
            if outcome is None:
                status[f"event-{event_index}-nonterminal"] += 1
                break

            exit_at = datetime.fromisoformat(
                cast(str, outcome["exit_at"])
            )
            if exit_at.tzinfo is None:
                raise ValueError("terminal exit must be timezone-aware")

            row = dict(outcome)
            row.update(
                {
                    "partition": partition,
                    "local_date": local_day.isoformat(),
                    "event_index": event_index,
                    "is_rearm": event_index > 1,
                    "raid_at": source.structure.raid_at.astimezone(
                        UTC
                    ).isoformat(),
                    "confirmation_at": (
                        source.structure.confirmation_at.astimezone(
                            UTC
                        ).isoformat()
                    ),
                    "decision_at": executable.decision_at.astimezone(
                        UTC
                    ).isoformat(),
                    "entry_family": executable.selected_family.value,
                    "source_event_reused": False,
                    "used_for_runtime_decision": False,
                }
            )
            terminal_trades.append(row)
            if event_index > 1:
                rearm_trades.append(row)

            traces.append(
                {
                    "partition": partition,
                    "local_date": local_day.isoformat(),
                    "event_index": event_index,
                    "raid_at": row["raid_at"],
                    "confirmation_at": row["confirmation_at"],
                    "decision_at": row["decision_at"],
                    "filled_at": row["filled_at"],
                    "exit_at": row["exit_at"],
                    "entry_family": row["entry_family"],
                    "r_multiple": row["r_multiple"],
                }
            )
            day_count += 1
            status[f"event-{event_index}-terminal"] += 1

            previous_exit = exit_at
            cursor = exit_at
            if _wall(exit_at) >= (11, 0, 0):
                status["exit-after-source-window"] += 1
                break

        events_per_day[day_count] += 1

    terminal_trades.sort(
        key=lambda row: cast(str, row["signal_at"])
    )
    rearm_trades.sort(
        key=lambda row: cast(str, row["signal_at"])
    )

    metrics = _metrics(terminal_trades, friction=FRICTION)
    rearm_metrics = _metrics(rearm_trades, friction=FRICTION)
    trade_count = len(terminal_trades)
    rearm_count = len(rearm_trades)

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "market": MARKET,
        "partition": partition,
        "candidate_contract_fingerprint": specialist.contract_fingerprint(),
        "frontier_objective": {
            "target_trade_count_2y_equivalent": "300-350",
            "stretch_observed_drawdown_r": "4-5",
            "profit_factor": "high-cross-fold",
            "purpose": (
                "measure genuine structural density before final "
                "risk/management optimization"
            ),
        },
        "evidence": {
            "account_fingerprint": account,
            "evidence_fingerprint": evidence,
            "evidence_software_sha": evidence_sha,
            "checked_at": checked.astimezone(UTC).isoformat(),
            "provider_symbol_name": provider,
        },
        "market_days": len(by_day),
        "terminal_trade_count": trade_count,
        "rearm_trade_count": rearm_count,
        "events_per_day": {
            str(key): value
            for key, value in sorted(events_per_day.items())
        },
        "terminal_metrics": metrics,
        "rearm_only_metrics": rearm_metrics,
        "density_frontier": {
            "at_least_300": trade_count >= 300,
            "inside_300_350": 300 <= trade_count <= 350,
            "above_350": trade_count > 350,
            "incremental_rearm_trades": rearm_count,
        },
        "status_counts": dict(sorted(status.items())),
        "traces": traces,
        "governance": {
            "consumed_evidence_only": True,
            "opens_new_holdout": False,
            "one_trade_max_per_source_event": True,
            "new_raid_required_after_previous_exit": True,
            "new_confirmation_required_after_previous_exit": True,
            "new_decision_required_after_previous_exit": True,
            "cooldown_rule_used": False,
            "duplicate_fill_density_used": False,
            "micro_entry_density_used": False,
            "future_outcome_used_to_form_event": False,
            "terminal_pnl_used_to_authorize_event": False,
            "policy_promoted": False,
            "live_authorized": False,
            "real_capital_authorized": False,
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
                "terminal_trade_count": payload[
                    "terminal_trade_count"
                ],
                "rearm_trade_count": payload["rearm_trade_count"],
                "events_per_day": payload["events_per_day"],
                "terminal_metrics": payload["terminal_metrics"],
                "density_frontier": payload["density_frontier"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
