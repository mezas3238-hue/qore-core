"""VT31 NAS100 CAUTIOUS context decomposition V1.

Research-only consumed-evidence forensic.

Purpose:
- keep the high-density OCO opportunity universe intact;
- decompose the dominant CAUTIOUS management state using causal pre-entry
  structure only;
- measure terminal economics and journey capacity only after subtypes exist;
- expose losing-cluster associations without converting them into runtime
  rules.

No subtype uses terminal PnL, future bars, or date-level outcome oracles.
Nothing in this file promotes an operating policy or opens a fresh holdout.
"""
# ruff: noqa: B009
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_nas100_entry_intelligence_oco_lab_v1 as oco
import vt31_nas100_high_density_management_intelligence_v1 as management
import vt31_nas100_specialist_r1_candidate as specialist

from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_5_multi_index_research import (
    _day,
    _metrics,
    load_market_evidence,
)
from qore.infrastructure.traders.vt31_silver_bullet_r2_2 import (
    Vt31R22ExecutionPolicy,
)

SCHEMA = "qore.vt31.nas100.caution_context_decomposition.v1"
MARKET = "NAS100"
MIN_CLUSTER = 3

DIMENSIONS = (
    "side",
    "entry_family",
    "reference_volatility_state",
    "path_bucket",
    "h1_state",
    "h4_state",
    "prior_day_state",
    "premarket_state",
    "cash_open_state",
    "last_structure_event_family",
    "reclaim_bucket",
    "decision_bucket",
    "confirmation_latency_bucket",
    "risk_ref_bucket",
)

INTERACTIONS: dict[str, tuple[str, ...]] = {
    "volatility_x_path": (
        "reference_volatility_state",
        "path_bucket",
    ),
    "structure_x_reclaim": (
        "last_structure_event_family",
        "reclaim_bucket",
    ),
    "side_x_family": (
        "side",
        "entry_family",
    ),
    "h1_x_h4": (
        "h1_state",
        "h4_state",
    ),
    "cash_x_premarket": (
        "cash_open_state",
        "premarket_state",
    ),
    "geometry_x_latency": (
        "risk_ref_bucket",
        "confirmation_latency_bucket",
    ),
    "timing_x_family": (
        "decision_bucket",
        "entry_family",
    ),
}


def _decimal(value: object) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(value))


def _path_bucket(value: object) -> str:
    number = _decimal(value)
    if number is None:
        return "unknown"
    if number < Decimal("0.75"):
        return "compressed"
    if number <= Decimal("1.25"):
        return "balanced"
    return "extended"


def _reclaim_bucket(value: object) -> str:
    if value is None:
        return "no-reclaim"
    age = int(cast(int, value))
    if age <= 4:
        return "fresh-0-4m"
    if age <= 7:
        return "developing-5-7m"
    if age <= 14:
        return "stale-8-14m"
    return "old-15m-plus"


def _decision_bucket(value: object) -> str:
    minute = int(cast(int, value))
    if minute < 10 * 60 + 20:
        return "1000-1019"
    if minute < 10 * 60 + 40:
        return "1020-1039"
    return "1040-1059"


def _latency_bucket(value: object) -> str:
    latency = int(cast(int, value))
    if latency <= 2:
        return "fast-0-2m"
    if latency <= 5:
        return "medium-3-5m"
    return "slow-6m-plus"


def _risk_bucket(value: object) -> str:
    number = _decimal(value)
    if number is None:
        return "unknown"
    if number <= Decimal("0.25"):
        return "compact-le-0.25ref"
    if number <= Decimal("0.50"):
        return "medium-0.25-0.50ref"
    return "wide-gt-0.50ref"


def _profile(
    state: dict[str, object],
    *,
    side: str,
    entry_family: str,
) -> dict[str, str]:
    return {
        "side": side,
        "entry_family": entry_family,
        "reference_volatility_state": str(
            state["reference_volatility_state"]
        ),
        "path_bucket": _path_bucket(state["current_path_vs_previous"]),
        "h1_state": str(state["h1_state"]),
        "h4_state": str(state["h4_state"]),
        "prior_day_state": str(state["prior_day_state"]),
        "premarket_state": str(state["premarket_state"]),
        "cash_open_state": str(state["cash_open_state"]),
        "last_structure_event_family": str(
            state["last_structure_event_family"]
        ),
        "reclaim_bucket": _reclaim_bucket(
            state["reference_reclaim_age_minutes"]
        ),
        "decision_bucket": _decision_bucket(state["decision_minute_ny"]),
        "confirmation_latency_bucket": _latency_bucket(
            state["confirmation_latency_minutes"]
        ),
        "risk_ref_bucket": _risk_bucket(state["risk_ref"]),
    }


def _median_decimal(values: list[Decimal]) -> str | None:
    if not values:
        return None
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        value = ordered[middle]
    else:
        value = (ordered[middle - 1] + ordered[middle]) / Decimal(2)
    return format(value, "f")


def _group_summary(rows: list[dict[str, object]]) -> dict[str, object]:
    metrics = _metrics(rows, friction=specialist.FRICTION)
    capacity = [
        row
        for row in rows
        if row["capacity_status"] == "labeled"
        and row["max_dol_rank"] is not None
    ]
    ranks = [int(cast(int, row["max_dol_rank"])) for row in capacity]
    mfe = [
        Decimal(cast(str, row["mfe_r_before_invalidation"]))
        for row in capacity
        if row["mfe_r_before_invalidation"] is not None
    ]
    mae = [
        Decimal(cast(str, row["mae_r_before_invalidation"]))
        for row in capacity
        if row["mae_r_before_invalidation"] is not None
    ]
    labeled = len(capacity)
    return {
        "terminal_metrics": metrics,
        "capacity_labeled": labeled,
        "dol1_rate": (
            format(
                Decimal(sum(rank >= 1 for rank in ranks)) / Decimal(labeled),
                "f",
            )
            if labeled
            else None
        ),
        "dol2_rate": (
            format(
                Decimal(sum(rank >= 2 for rank in ranks)) / Decimal(labeled),
                "f",
            )
            if labeled
            else None
        ),
        "dol3_plus_rate": (
            format(
                Decimal(sum(rank >= 3 for rank in ranks)) / Decimal(labeled),
                "f",
            )
            if labeled
            else None
        ),
        "median_mfe_r_before_invalidation": _median_decimal(mfe),
        "median_mae_r_before_invalidation": _median_decimal(mae),
    }


def _interaction_key(
    row: dict[str, object],
    fields: tuple[str, ...],
) -> str:
    return "|".join(f"{field}={row[field]}" for field in fields)


def _loss_clusters(
    rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    clusters: list[list[dict[str, object]]] = []
    current: list[dict[str, object]] = []
    for row in rows:
        net = Decimal(cast(str, row["r_multiple"])) - specialist.FRICTION
        if net < 0:
            current.append(row)
            continue
        if len(current) >= MIN_CLUSTER:
            clusters.append(current)
        current = []
    if len(current) >= MIN_CLUSTER:
        clusters.append(current)

    result: list[dict[str, object]] = []
    for index, cluster in enumerate(clusters, start=1):
        nets = [
            Decimal(cast(str, row["r_multiple"])) - specialist.FRICTION
            for row in cluster
        ]
        result.append(
            {
                "cluster_id": index,
                "length": len(cluster),
                "start_signal_at": cluster[0]["signal_at"],
                "end_signal_at": cluster[-1]["signal_at"],
                "net_r": format(sum(nets, Decimal(0)), "f"),
                "side": dict(
                    Counter(str(row["side"]) for row in cluster).most_common()
                ),
                "entry_family": dict(
                    Counter(
                        str(row["entry_family"]) for row in cluster
                    ).most_common()
                ),
                "reference_volatility_state": dict(
                    Counter(
                        str(row["reference_volatility_state"])
                        for row in cluster
                    ).most_common()
                ),
                "structure_family": dict(
                    Counter(
                        str(row["last_structure_event_family"])
                        for row in cluster
                    ).most_common()
                ),
                "reclaim_bucket": dict(
                    Counter(
                        str(row["reclaim_bucket"]) for row in cluster
                    ).most_common()
                ),
                "runtime_rule_authorized": False,
            }
        )
    return result


def replay(
    evidence_path: Path,
    *,
    partition: str,
) -> dict[str, object]:
    series, account, evidence, checked, evidence_sha, provider = (
        load_market_evidence(evidence_path)
    )
    if not series or getattr(series[0], "instrument").symbol != MARKET:
        raise ValueError("CAUTIOUS decomposition requires NAS100 evidence")

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
    rows: list[dict[str, object]] = []

    for local_day in sorted(by_day):
        day_bars = by_day[local_day]
        reference = specialist._slice(day_bars, (9, 0, 0), (10, 0, 0))
        session = specialist._slice(day_bars, (10, 0, 0), (11, 0, 0))
        if len(reference) != 60 or len(session) != 60:
            status["incomplete-day"] += 1
            continue

        timeline = oco._timeline(
            day_bars,
            evidence_fingerprint=evidence,
        )
        if timeline is None:
            status["no-source-timeline"] += 1
            continue
        selected, selection_status = oco._select_oco(
            day_bars,
            timeline,
            policy,
        )
        status[f"oco-{selection_status}"] += 1
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
        context = management._context_state(state)
        status[f"context-{context.lower()}"] += 1
        if context != "CAUTIOUS":
            continue

        outcome = specialist.baseline._simulate(day_bars, selected)
        status[f"cautious-outcome-{outcome['status']}"] += 1
        if outcome.get("status") != "terminal":
            continue

        capacity = specialist._journey_capacity_label(
            day_bars,
            selected,
        )
        capacity_status = str(capacity.get("status"))
        profile = _profile(
            state,
            side=selected.side.value,
            entry_family=selected.selected_family.value,
        )
        row: dict[str, object] = {
            **profile,
            "partition": partition,
            "local_date": local_day.isoformat(),
            "signal_at": outcome["signal_at"],
            "r_multiple": outcome["r_multiple"],
            "decision_at": observation_at.astimezone(UTC).isoformat(),
            "reference_reclaim_age_minutes": state[
                "reference_reclaim_age_minutes"
            ],
            "confirmation_latency_minutes": state[
                "confirmation_latency_minutes"
            ],
            "risk_ref": state["risk_ref"],
            "current_path_vs_previous": state[
                "current_path_vs_previous"
            ],
            "capacity_status": capacity_status,
            "max_dol_rank": capacity.get(
                "max_distinct_active_dol_rank_touched_before_invalidation"
            ),
            "mfe_r_before_invalidation": capacity.get(
                "max_favorable_r_before_invalidation"
            ),
            "mae_r_before_invalidation": capacity.get(
                "max_adverse_r_before_invalidation"
            ),
            "used_for_runtime_decision": False,
        }
        rows.append(row)

    rows.sort(key=lambda item: cast(str, item["signal_at"]))

    by_dimension: dict[str, dict[str, object]] = {}
    for dimension in DIMENSIONS:
        grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
        for row in rows:
            grouped[str(row[dimension])].append(row)
        by_dimension[dimension] = {
            key: _group_summary(values)
            for key, values in sorted(grouped.items())
        }

    by_interaction: dict[str, dict[str, object]] = {}
    for name, fields in INTERACTIONS.items():
        grouped = defaultdict(list)
        for row in rows:
            grouped[_interaction_key(row, fields)].append(row)
        by_interaction[name] = {
            key: _group_summary(values)
            for key, values in sorted(grouped.items())
        }

    return {
        "schema": SCHEMA,
        "market": MARKET,
        "partition": partition,
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
        "status_counts": dict(sorted(status.items())),
        "cautious_terminal_count": len(rows),
        "cautious_summary": _group_summary(rows),
        "by_dimension": by_dimension,
        "by_interaction": by_interaction,
        "loss_clusters_min_3": _loss_clusters(rows),
        "rows": rows,
        "governance": {
            "subtype_definition_uses_terminal_pnl": False,
            "subtype_definition_uses_future_bars": False,
            "post_outcome_used_for_runtime_decision": False,
            "terminal_outcomes_used_only_for_research_evaluation": True,
            "loss_clusters_used_only_for_forensics": True,
            "oco_universe_filtered_before_context_analysis": False,
            "consumed_evidence_only": True,
            "policy_promoted": False,
            "opens_new_holdout": False,
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
                "status_counts": payload["status_counts"],
                "cautious_terminal_count": payload[
                    "cautious_terminal_count"
                ],
                "cautious_summary": payload["cautious_summary"],
                "loss_cluster_count": len(
                    cast(list[object], payload["loss_clusters_min_3"])
                ),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
