"""Fresh reauthorization ladder forensics after stale Order Block states.

Diagnostic-only.

For each current-best-stack Order Block that appears after >=2 already-closed
losses, scan ALL genuinely fresh Silver Bullet source events remaining in the
10:00-11:00 NY session (up to six source events).

A source is genuinely fresh only if its raid, confirmation and decision are
all strictly after the stale Order Block authorization.

For every fresh event the lab records:
- ordinal fresh-event depth;
- decision-time market state;
- state transitions versus the stale authorization;
- terminal outcome as a research-only label.

No event is promoted or traded by this lab.
"""
# ruff: noqa: B009
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_nas100_alt_tier_bifurcation_forensics_v1 as alt
import vt31_nas100_r5_alloc_g_regime_root_cause_forensics_v1 as regime
import vt31_nas100_sequence_state_interaction_forensics_v1 as seq
import vt31_nas100_specialist_r1_candidate as specialist
import vt31_nas100_structural_rearm_density_frontier_v1 as frontier

from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_5_multi_index_research import (
    _day,
    load_market_evidence,
)
from qore.infrastructure.traders.vt31_silver_bullet_r2_2 import (
    Vt31R22ExecutionPolicy,
)

SCHEMA = "qore.vt31.nas100.sequence_ob_reauthorization_ladder_forensics.v1"
MARKET = "NAS100"
MAX_SCAN_EVENTS = 6
FRICTION = Decimal("0.05")

TRANSITION_FIELDS = (
    "entry_family",
    "side",
    "reference_volatility_state",
    "last_structure_event_family",
    "current_path_bucket",
    "risk_ref_bucket",
    "reclaim_age_bucket",
    "confirmation_latency_bucket",
)


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _dt(value: object) -> datetime:
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def _metrics(values: list[Decimal]) -> dict[str, object]:
    wins = [v for v in values if v > 0]
    losses = [v for v in values if v < 0]
    gross_win = sum(wins, Decimal(0))
    gross_loss = abs(sum(losses, Decimal(0)))
    pf = None if gross_loss == 0 else gross_win / gross_loss
    return {
        "sample": len(values),
        "wins": len(wins),
        "losses": len(losses),
        "total_r": format(sum(values, Decimal(0)), "f"),
        "mean_r": (
            "0"
            if not values
            else format(sum(values, Decimal(0)) / Decimal(len(values)), "f")
        ),
        "profit_factor": None if pf is None else format(pf, "f"),
    }


def _fresh_events(
    *,
    day_bars: tuple[object, ...],
    reference: tuple[object, ...],
    session: tuple[object, ...],
    after_at: datetime,
    evidence: str,
    policy: Vt31R22ExecutionPolicy,
    context: tuple[object, object, object],
) -> list[dict[str, object]]:
    previous_path_range, prior_ref_median, prior_admitted_day_bars = context
    cursor = after_at
    events: list[dict[str, object]] = []
    scanned = 0

    while scanned < MAX_SCAN_EVENTS:
        selected = frontier._next_executable_after(
            reference=reference,
            session=session,
            after_at=cursor,
            evidence=evidence,
            policy=policy,
        )
        if selected is None:
            break

        source, setup = selected
        scanned += 1
        cursor = setup.decision_at

        if not (
            source.structure.raid_at > after_at
            and source.structure.confirmation_at > after_at
            and setup.decision_at > after_at
        ):
            continue

        session_prefix = tuple(
            bar
            for bar in session
            if cast(datetime, getattr(bar, "closed_at"))
            <= setup.decision_at
        )
        state = specialist._state_snapshot(
            day_bars,
            previous_path_range,
            prior_ref_median,
            prior_admitted_day_bars,
            session_prefix,
            source,
            setup,
            setup.decision_at,
        )
        decorated = regime._decorate(
            {
                **state,
                "entry_family": setup.selected_family.value,
                "side": setup.side.value,
            }
        )

        outcome = specialist.baseline._simulate(day_bars, setup)
        event: dict[str, object] = {
            "fresh_ordinal": len(events) + 1,
            "family": setup.selected_family.value,
            "side": setup.side.value,
            "raid_at": source.structure.raid_at.isoformat(),
            "confirmation_at": source.structure.confirmation_at.isoformat(),
            "decision_at": setup.decision_at.isoformat(),
            "latency_minutes": int(
                (setup.decision_at - after_at).total_seconds() // 60
            ),
            "reasoning_action": state.get("action"),
            "reference_volatility_state": decorated.get(
                "reference_volatility_state"
            ),
            "last_structure_event_family": decorated.get(
                "last_structure_event_family"
            ),
            "current_path_bucket": decorated.get("current_path_bucket"),
            "risk_ref_bucket": decorated.get("risk_ref_bucket"),
            "reclaim_age_bucket": decorated.get("reclaim_age_bucket"),
            "confirmation_latency_bucket": decorated.get(
                "confirmation_latency_bucket"
            ),
            "outcome_status": outcome.get("status"),
        }
        if outcome.get("status") == "terminal":
            gross = _d(outcome["r_multiple"])
            event.update(
                {
                    "research_terminal_net_005": format(
                        gross - FRICTION,
                        "f",
                    ),
                    "research_exit_reason": outcome.get("exit_reason"),
                }
            )
        events.append(event)

    return events


def replay(path: Path, *, partition: str) -> dict[str, object]:
    rows, evidence_info, diagnostics, source_stats = alt._current_rows(path)
    annotated = seq._annotate(rows)
    stale = [
        row
        for row in annotated
        if bool(row["pre_loss_ge_2"])
        and row.get("entry_family") == "order-block"
    ]

    (
        series,
        account,
        evidence,
        checked,
        evidence_sha,
        provider,
    ) = load_market_evidence(path)
    if not series or getattr(series[0], "instrument").symbol != MARKET:
        raise ValueError("reauthorization ladder requires NAS100")

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

    ladders: list[dict[str, object]] = []
    ordinal_values: dict[int, list[Decimal]] = defaultdict(list)
    ordinal_counts: Counter[int] = Counter()
    ordinal_family: dict[int, Counter[str]] = defaultdict(Counter)
    transition_counts: Counter[str] = Counter()
    first_terminal_winner_depths: Counter[str] = Counter()

    for row in stale:
        local_day = date.fromisoformat(cast(str, row["local_date"]))
        day_bars = by_day.get(local_day)
        if not day_bars:
            continue

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
            continue

        events = _fresh_events(
            day_bars=day_bars,
            reference=reference,
            session=session,
            after_at=_dt(row["signal_at"]),
            evidence=evidence,
            policy=policy,
            context=context_by_day[local_day],
        )

        first_winner: int | None = None
        enriched_events: list[dict[str, object]] = []
        for event in events:
            ordinal = int(event["fresh_ordinal"])
            ordinal_counts[ordinal] += 1
            ordinal_family[ordinal][cast(str, event["family"])] += 1

            transitions: list[str] = []
            stale_map = {
                "entry_family": row.get("entry_family"),
                "side": row.get("side"),
                "reference_volatility_state": row.get(
                    "reference_volatility_state"
                ),
                "last_structure_event_family": row.get(
                    "last_structure_event_family"
                ),
                "current_path_bucket": row.get("current_path_bucket"),
                "risk_ref_bucket": row.get("risk_ref_bucket"),
                "reclaim_age_bucket": row.get("reclaim_age_bucket"),
                "confirmation_latency_bucket": row.get(
                    "confirmation_latency_bucket"
                ),
            }
            fresh_map = {
                "entry_family": event.get("family"),
                "side": event.get("side"),
                "reference_volatility_state": event.get(
                    "reference_volatility_state"
                ),
                "last_structure_event_family": event.get(
                    "last_structure_event_family"
                ),
                "current_path_bucket": event.get("current_path_bucket"),
                "risk_ref_bucket": event.get("risk_ref_bucket"),
                "reclaim_age_bucket": event.get("reclaim_age_bucket"),
                "confirmation_latency_bucket": event.get(
                    "confirmation_latency_bucket"
                ),
            }
            for field in TRANSITION_FIELDS:
                relation = (
                    "same"
                    if stale_map[field] == fresh_map[field]
                    else "changed"
                )
                key = f"ordinal={ordinal}|{field}={relation}"
                transition_counts[key] += 1
                transitions.append(f"{field}:{relation}")

            updated = {**event, "transitions_vs_stale": transitions}
            enriched_events.append(updated)

            if event.get("research_terminal_net_005") is not None:
                value = _d(event["research_terminal_net_005"])
                ordinal_values[ordinal].append(value)
                if value > 0 and first_winner is None:
                    first_winner = ordinal

        first_terminal_winner_depths[
            "none" if first_winner is None else str(first_winner)
        ] += 1

        ladders.append(
            {
                "local_date": row["local_date"],
                "stale_signal_at": row["signal_at"],
                "pre_loss_streak": row["pre_loss_streak"],
                "stale_state": {
                    field: row.get(field)
                    for field in TRANSITION_FIELDS
                },
                "fresh_event_count": len(events),
                "fresh_events": enriched_events,
                "first_terminal_winner_ordinal": first_winner,
            }
        )

    ordinal_summary = {
        str(ordinal): {
            "available_count": ordinal_counts[ordinal],
            "family_counts": dict(
                sorted(ordinal_family[ordinal].items())
            ),
            "terminal_metrics_net_005": _metrics(
                ordinal_values.get(ordinal, [])
            ),
        }
        for ordinal in sorted(ordinal_counts)
    }

    return {
        "schema": SCHEMA,
        "partition": partition,
        "stale_order_block_count": len(stale),
        "ladder_count": len(ladders),
        "ordinal_summary": ordinal_summary,
        "first_terminal_winner_depth_counts": dict(
            sorted(first_terminal_winner_depths.items())
        ),
        "transition_counts": dict(sorted(transition_counts.items())),
        "ladders": ladders,
        "source_stats": source_stats,
        "diagnostics": diagnostics,
        "evidence": {
            **evidence_info,
            "account_fingerprint": account,
            "evidence_fingerprint": evidence,
            "checked_at": checked.isoformat(),
            "evidence_software_sha": evidence_sha,
            "provider_symbol_name": provider,
        },
        "governance": {
            "diagnostic_only": True,
            "stale_state_uses_closed_prior_trades_only": True,
            "all_fresh_events_require_new_raid": True,
            "all_fresh_events_require_new_confirmation": True,
            "terminal_outcome_research_label_only": True,
            "event_ordinal_runtime_policy_forbidden": True,
            "calendar_date_runtime_forbidden": True,
            "fold_identity_runtime_forbidden": True,
            "trade_policy_changed": False,
            "risk_policy_changed": False,
            "silver_bullet_changed": False,
            "opens_new_holdout": False,
            "policy_promoted": False,
            "candidate_certified": False,
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
                "stale_order_block_count": payload[
                    "stale_order_block_count"
                ],
                "ordinal_summary": payload["ordinal_summary"],
                "first_terminal_winner_depth_counts": payload[
                    "first_terminal_winner_depth_counts"
                ],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
