"""Fresh reauthorization forensics after stale Order Block sequence states.

Diagnostic-only.

Root-cause condition already established:
- current best-stack Order Block trades after >=2 already-closed losses are
  persistently pathological across R5/R6/R8/consumed.

This lab does NOT veto days and does NOT modify risk.
For every such stale Order Block authorization it searches the remainder of
the 10:00-11:00 NY Silver Bullet session for the first genuinely fresh source
with BOTH:
- a new raid strictly after the stale authorization;
- a new structural confirmation strictly after the stale authorization.

The future terminal outcome of the fresh source is attached only as a research
label. It is not used to decide whether the source is fresh.

Silver Bullet remains frozen.
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

SCHEMA = "qore.vt31.nas100.sequence_ob_fresh_reauthorization_forensics.v1"
MARKET = "NAS100"
MAX_SCAN_EVENTS = 6
FRICTION = Decimal("0.05")


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


def _fresh_replacement(
    *,
    day_bars: tuple[object, ...],
    reference: tuple[object, ...],
    session: tuple[object, ...],
    after_at: datetime,
    evidence: str,
    policy: Vt31R22ExecutionPolicy,
) -> dict[str, object]:
    cursor = after_at
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
            return {
                "status": "NO_FRESH_REPLACEMENT",
                "events_scanned": scanned,
            }

        source, setup = selected
        scanned += 1

        raid_at = source.structure.raid_at
        confirmation_at = source.structure.confirmation_at
        genuinely_fresh = (
            raid_at > after_at
            and confirmation_at > after_at
            and setup.decision_at > after_at
        )
        if not genuinely_fresh:
            cursor = setup.decision_at
            continue

        outcome = specialist.baseline._simulate(day_bars, setup)
        payload: dict[str, object] = {
            "status": "FRESH_REPLACEMENT_FOUND",
            "events_scanned": scanned,
            "fresh_family": setup.selected_family.value,
            "fresh_side": setup.side.value,
            "fresh_raid_at": raid_at.isoformat(),
            "fresh_confirmation_at": confirmation_at.isoformat(),
            "fresh_decision_at": setup.decision_at.isoformat(),
            "fresh_latency_minutes": int(
                (setup.decision_at - after_at).total_seconds() // 60
            ),
            "outcome_status": outcome.get("status"),
        }
        if outcome.get("status") == "terminal":
            gross = _d(outcome["r_multiple"])
            payload.update(
                {
                    "research_terminal_r_gross": format(gross, "f"),
                    "research_terminal_r_net_005": format(
                        gross - FRICTION,
                        "f",
                    ),
                    "research_exit_reason": outcome.get("exit_reason"),
                    "research_exit_at": outcome.get("exit_at"),
                }
            )
        return payload

    return {
        "status": "NO_FRESH_REPLACEMENT_WITHIN_SCAN",
        "events_scanned": scanned,
    }


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
        raise ValueError("fresh reauthorization forensics requires NAS100")

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
    observations: list[dict[str, object]] = []
    status_counts: Counter[str] = Counter()
    family_counts: Counter[str] = Counter()
    latencies: list[int] = []
    terminal_values: list[Decimal] = []

    for row in stale:
        local_day = date.fromisoformat(cast(str, row["local_date"]))
        day_bars = by_day.get(local_day)
        if not day_bars:
            status_counts["MISSING_DAY"] += 1
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
            status_counts["INCOMPLETE_DAY"] += 1
            continue

        after_at = _dt(row["signal_at"])
        result = _fresh_replacement(
            day_bars=day_bars,
            reference=reference,
            session=session,
            after_at=after_at,
            evidence=evidence,
            policy=policy,
        )
        status = cast(str, result["status"])
        status_counts[status] += 1

        observation = {
            "local_date": row["local_date"],
            "stale_signal_at": row["signal_at"],
            "pre_loss_streak": row["pre_loss_streak"],
            "stale_family": row["entry_family"],
            "stale_side": row.get("side"),
            "stale_loss_path_class": row.get("loss_path_class"),
            **result,
        }
        observations.append(observation)

        if status == "FRESH_REPLACEMENT_FOUND":
            family_counts[cast(str, result["fresh_family"])] += 1
            latencies.append(int(result["fresh_latency_minutes"]))
            if result.get("research_terminal_r_net_005") is not None:
                terminal_values.append(
                    _d(result["research_terminal_r_net_005"])
                )

    found = status_counts["FRESH_REPLACEMENT_FOUND"]
    total = len(stale)
    availability = (
        Decimal(found) / Decimal(total)
        if total
        else Decimal(0)
    )

    return {
        "schema": SCHEMA,
        "partition": partition,
        "stale_order_block_count": total,
        "fresh_replacement_found_count": found,
        "fresh_replacement_availability": format(availability, "f"),
        "status_counts": dict(sorted(status_counts.items())),
        "fresh_family_counts": dict(sorted(family_counts.items())),
        "fresh_latency_minutes": {
            "sample": len(latencies),
            "min": None if not latencies else min(latencies),
            "max": None if not latencies else max(latencies),
            "mean": (
                None
                if not latencies
                else format(
                    Decimal(sum(latencies)) / Decimal(len(latencies)),
                    "f",
                )
            ),
        },
        "research_terminal_net_005_metrics": _metrics(terminal_values),
        "observations": observations,
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
            "freshness_requires_new_raid_after_stale_authorization": True,
            "freshness_requires_new_confirmation_after_stale_authorization": True,
            "terminal_outcome_research_label_only": True,
            "trade_policy_changed": False,
            "risk_policy_changed": False,
            "silver_bullet_changed": False,
            "calendar_date_runtime_forbidden": True,
            "fold_identity_runtime_forbidden": True,
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
                "stale_order_block_count": payload[
                    "stale_order_block_count"
                ],
                "fresh_replacement_found_count": payload[
                    "fresh_replacement_found_count"
                ],
                "fresh_replacement_availability": payload[
                    "fresh_replacement_availability"
                ],
                "fresh_family_counts": payload["fresh_family_counts"],
                "fresh_latency_minutes": payload[
                    "fresh_latency_minutes"
                ],
                "research_terminal_net_005_metrics": payload[
                    "research_terminal_net_005_metrics"
                ],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
