"""High-density management intelligence for VT31_NAS100.

Research-only experiment over consumed R5/R6/R8 evidence.

Entry density comes from the causal OCO router. This lab deliberately does NOT
filter those selected source events. Instead it asks whether the same dense
population can be managed more intelligently.

Predeclared management families:
- BASELINE: original structural boundary + source 3R breakeven.
- REFERENCE_DYNAMIC: compressed 09 reference keeps full structural boundary;
  normal/expanded reference uses 50% at 1.25R + runner to boundary.
- CONTEXT_DYNAMIC: a causal conjunction classifies SUPPORTIVE/MIXED/CAUTIOUS.
  SUPPORTIVE keeps full structural boundary; MIXED uses 50% at 1.25R;
  CAUTIOUS uses 50% at 1.0R. Runner remains structural boundary and moves to
  breakeven only on the next bar after partial.

No entry is rejected by these management states. PnL is an evaluation output,
not an input to state classification. No holdout is opened.
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

import vt31_nas100_entry_intelligence_oco_lab_v1 as oco
import vt31_nas100_intelligence_policy_lab_v2b as v2b
import vt31_nas100_specialist_r1_candidate as specialist

from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_5_multi_index_research import (
    _day,
    _metrics,
    load_market_evidence,
)

SCHEMA = "qore.vt31.nas100.high_density_management_intelligence.v1"
MARKET = "NAS100"
POLICIES = (
    "BASELINE",
    "REFERENCE_DYNAMIC",
    "CONTEXT_DYNAMIC",
)


def _context_state(state: dict[str, object]) -> str:
    ref_state = str(state["reference_volatility_state"])
    path_raw = state["current_path_vs_previous"]
    path_ratio = (
        None if path_raw is None else Decimal(str(path_raw))
    )
    last_family = str(state["last_structure_event_family"])
    reclaim_raw = state["reference_reclaim_age_minutes"]
    reclaim_age = (
        None if reclaim_raw is None else int(cast(int, reclaim_raw))
    )
    stale = reclaim_age is not None and 8 <= reclaim_age < 15

    supportive = (
        ref_state == "compressed"
        and path_ratio is not None
        and path_ratio < Decimal("0.75")
        and last_family == "reference-liquidity-sweep"
        and not stale
    )
    if supportive:
        return "SUPPORTIVE"

    cautious = (
        ref_state == "expanded"
        or (path_ratio is not None and path_ratio > Decimal("1.25"))
        or stale
        or last_family != "reference-liquidity-sweep"
    )
    return "CAUTIOUS" if cautious else "MIXED"


def _simulate_policy(
    policy: str,
    day_bars: tuple[object, ...],
    setup: Any,
    state: dict[str, object],
    context: str,
) -> dict[str, object]:
    if policy == "BASELINE":
        return specialist.baseline._simulate(day_bars, setup)
    if policy == "REFERENCE_DYNAMIC":
        return specialist._simulate_selected_plan(day_bars, setup, state)
    if policy != "CONTEXT_DYNAMIC":
        raise ValueError(policy)
    if context == "SUPPORTIVE":
        return specialist.baseline._simulate(day_bars, setup)
    local_r = Decimal("1.25") if context == "MIXED" else Decimal("1.0")
    return v2b._simulate_partial_runner(day_bars, setup, local_r)


def _metric_bundle(trades: list[dict[str, object]]) -> dict[str, object]:
    return {
        "stress_0_05r": _metrics(trades, friction=specialist.FRICTION),
        "monte_carlo": specialist._monte_carlo(trades),
        "sample": len(trades),
    }


def replay(evidence_path: Path) -> dict[str, object]:
    series, account, evidence, checked, evidence_sha, provider = (
        load_market_evidence(evidence_path)
    )
    if not series or getattr(series[0], "instrument").symbol != MARKET:
        raise ValueError("management intelligence requires NAS100 evidence")

    raw: dict[date, list[object]] = defaultdict(list)
    for bar in series:
        raw[_day(getattr(bar, "opened_at"))].append(bar)
    by_day = {
        day: tuple(sorted(rows, key=lambda item: getattr(item, "opened_at")))
        for day, rows in raw.items()
    }
    context_by_day = specialist._context_map(by_day)
    policy = oco.Vt31R22ExecutionPolicy()

    trades_by_policy: dict[str, list[dict[str, object]]] = {
        name: [] for name in POLICIES
    }
    by_context_policy: dict[
        str, dict[str, list[dict[str, object]]]
    ] = {
        context: {name: [] for name in POLICIES}
        for context in ("SUPPORTIVE", "MIXED", "CAUTIOUS")
    }
    context_counts: Counter[str] = Counter()
    status_counts: Counter[str] = Counter()
    rows: list[dict[str, object]] = []

    for local_day in sorted(by_day):
        day_bars = by_day[local_day]
        reference = specialist._slice(day_bars, (9, 0, 0), (10, 0, 0))
        session = specialist._slice(day_bars, (10, 0, 0), (11, 0, 0))
        if len(reference) != 60 or len(session) != 60:
            status_counts["incomplete-day"] += 1
            continue

        timeline = oco._timeline(
            day_bars,
            evidence_fingerprint=evidence,
        )
        if timeline is None:
            status_counts["no-source-timeline"] += 1
            continue

        selected, selection_status = oco._select_oco(
            day_bars,
            timeline,
            policy,
        )
        status_counts[f"oco-{selection_status}"] += 1
        if selected is None:
            continue

        (
            previous_path_range,
            prior_ref_median,
            prior_admitted_day_bars,
        ) = context_by_day[local_day]
        observation_at = selected.decision_at
        session_prefix = tuple(
            bar
            for bar in session
            if cast(datetime, getattr(bar, "closed_at")) <= observation_at
        )
        state = specialist._state_snapshot(
            day_bars,
            previous_path_range,
            prior_ref_median,
            prior_admitted_day_bars,
            session_prefix,
            timeline.source,
            selected,
            observation_at,
        )
        context = _context_state(state)
        context_counts[context] += 1
        row: dict[str, object] = {
            "local_date": local_day.isoformat(),
            "decision_at": observation_at.astimezone(UTC).isoformat(),
            "side": selected.side.value,
            "entry_family": selected.selected_family.value,
            "management_context": context,
            "reference_volatility_state": state[
                "reference_volatility_state"
            ],
            "current_path_vs_previous": state[
                "current_path_vs_previous"
            ],
            "last_structure_event_family": state[
                "last_structure_event_family"
            ],
            "reference_reclaim_age_minutes": state[
                "reference_reclaim_age_minutes"
            ],
            "policy_results": {},
        }

        for management in POLICIES:
            outcome = _simulate_policy(
                management,
                day_bars,
                selected,
                state,
                context,
            )
            status = str(outcome["status"])
            status_counts[f"{management}:{status}"] += 1
            cast(dict[str, object], row["policy_results"])[management] = {
                "status": status,
                "r_multiple": outcome.get("r_multiple"),
                "exit_reason": outcome.get("exit_reason"),
            }
            if status != "terminal":
                continue
            enriched = dict(outcome)
            enriched["management_context"] = context
            enriched["entry_family"] = selected.selected_family.value
            trades_by_policy[management].append(enriched)
            by_context_policy[context][management].append(enriched)
        rows.append(row)

    policy_metrics = {
        name: _metric_bundle(trades)
        for name, trades in trades_by_policy.items()
    }
    context_metrics = {
        context: {
            name: _metric_bundle(trades)
            for name, trades in policies.items()
        }
        for context, policies in by_context_policy.items()
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
        "oco_selected_setup_count": sum(context_counts.values()),
        "management_context_counts": dict(sorted(context_counts.items())),
        "status_counts": dict(sorted(status_counts.items())),
        "policy_metrics": policy_metrics,
        "context_metrics": context_metrics,
        "rows": rows,
        "governance": {
            "entry_filtering_by_management_context": False,
            "context_classifier_uses_terminal_pnl": False,
            "all_contexts_remain_executable": True,
            "consumed_evidence_only": True,
            "policy_promoted": False,
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
                "oco_selected_setup_count": payload[
                    "oco_selected_setup_count"
                ],
                "management_context_counts": payload[
                    "management_context_counts"
                ],
                "policy_metrics": payload["policy_metrics"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
