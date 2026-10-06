"""VT31 NAS100 rejected structural positive-edge audit V1.

Observation-only consumed-evidence audit under the predeclared gate:
VT31_ARCH2_REJECTED_STRUCTURAL_POSITIVE_EDGE_AUDIT_GATE_001.md

The experiment freezes structural trade identity first, reconstructs the exact
Comparator-009 admission decision from causal entry-time facts, and only then
uses terminal structural R for retrospective measurement. No terminal outcome,
date, fold, or future path can influence admission classification.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_nas100_breaker_mixed_weak_efficiency_adverse_exit_v1 as weak
import vt31_nas100_comp009_final_preholdout_metric_pack_v1 as pack
import vt31_nas100_specialist_r1_candidate as specialist

from qore.infrastructure.traders.vt31_nas100_comp008_policy import (
    comparator008_admission_decision,
    comparator008_facts_from_replay_row,
    confirmation_latency_state,
    reclaim_sequence_state,
)

SCHEMA = "qore.vt31.nas100.rejected_structural_positive_edge_audit.v1"
BASE_COMPARATOR_ID = "VT31_AB_COMP009_MAX_INTELLIGENCE_COMPOSED_SURVIVOR"
FRICTION = pack.BASELINE_FRICTION_R

STATE_FIELDS = (
    "entry_family",
    "side",
    "prior_day_state",
    "h4_state",
    "h1_state",
    "m15_state",
    "premarket_state",
    "cash_open_state",
    "position_in_prior_day_range",
    "reference_volatility_state",
    "last_structure_event_family",
    "confirmation_latency_bucket",
    "reclaim_sequence_bucket",
)


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _pf(metrics: dict[str, object]) -> Decimal:
    value = metrics.get("profit_factor")
    if value is not None:
        return _d(value)
    if int(metrics.get("wins", 0)) > 0 and int(metrics.get("losses", 0)) == 0:
        return Decimal("Infinity")
    return Decimal("-Infinity")


def _halfyear(value: str) -> str:
    dt = datetime.fromisoformat(value)
    return f"{dt.year}-H{1 if dt.month <= 6 else 2}"


def _year(value: str) -> str:
    return str(datetime.fromisoformat(value).year)


def _metrics(rows: list[dict[str, object]]) -> dict[str, object]:
    ordered = sorted(rows, key=lambda row: str(row["signal_at"]))
    metrics = specialist._metrics(ordered, friction=FRICTION)
    stressed_winner_r = sum(
        (
            _d(row["r_multiple"]) - FRICTION
            for row in ordered
            if _d(row["r_multiple"]) - FRICTION > 0
        ),
        Decimal(0),
    )
    return {
        **metrics,
        "winner_r": format(stressed_winner_r, "f"),
    }


def _temporal(rows: list[dict[str, object]]) -> dict[str, object]:
    by_year: dict[str, list[dict[str, object]]] = defaultdict(list)
    by_halfyear: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        signal_at = str(row["signal_at"])
        by_year[_year(signal_at)].append(row)
        by_halfyear[_halfyear(signal_at)].append(row)
    return {
        "years": {
            key: _metrics(value)
            for key, value in sorted(by_year.items())
        },
        "halfyears": {
            key: _metrics(value)
            for key, value in sorted(by_halfyear.items())
        },
    }


def _state(row: dict[str, object]) -> dict[str, str]:
    context = cast(dict[str, object], row["entry_context"])
    confirmation = context.get("confirmation_latency_minutes")
    reclaim = context.get("reference_reclaim_age_minutes")
    return {
        "entry_family": str(row["entry_family"]),
        "side": str(row["side"]),
        "prior_day_state": str(context.get("prior_day_state")),
        "h4_state": str(context.get("h4_state")),
        "h1_state": str(context.get("h1_state")),
        "m15_state": str(context.get("m15_state")),
        "premarket_state": str(context.get("premarket_state")),
        "cash_open_state": str(context.get("cash_open_state")),
        "position_in_prior_day_range": str(
            context.get("position_in_prior_day_range")
        ),
        "reference_volatility_state": str(
            context.get("reference_volatility_state")
        ),
        "last_structure_event_family": str(
            context.get("last_structure_event_family")
        ),
        "confirmation_latency_bucket": confirmation_latency_state(
            confirmation
        ).value,
        "reclaim_sequence_bucket": reclaim_sequence_state(reclaim).value,
    }


def _reconstruct_population(
    evidence_path: Path,
) -> tuple[
    list[dict[str, object]],
    list[dict[str, object]],
    list[dict[str, object]],
]:
    original = specialist._simulate_selected_plan
    position_rows: list[dict[str, object]] = []

    def simulator(
        day_bars: tuple[object, ...],
        executable: object,
        state: dict[str, object],
    ) -> dict[str, object]:
        structural = specialist._simulate_structural_boundary_only(
            day_bars,
            executable,
        )
        if structural.get("status") != "terminal":
            return structural
        position = weak._simulate_candidate(day_bars, executable, state)
        if position.get("status") != "terminal":
            raise AssertionError(
                "position reconstruction changed structural terminal identity"
            )
        position_rows.append(position)
        return structural

    try:
        specialist._simulate_selected_plan = simulator
        payload = specialist.replay(evidence_path)
    finally:
        specialist._simulate_selected_plan = original

    structural = cast(list[dict[str, object]], payload["trades"])
    structural_ids = [str(row["signal_at"]) for row in structural]
    position_ids = [str(row["signal_at"]) for row in position_rows]
    if structural_ids != position_ids:
        raise AssertionError("structural/position identity drift")

    enriched: list[dict[str, object]] = []
    admitted: list[dict[str, object]] = []
    rejected: list[dict[str, object]] = []
    for structural_row, position_row in zip(
        structural,
        position_rows,
        strict=True,
    ):
        row = dict(structural_row)
        row["entry_context"] = position_row["entry_context"]
        row["position_exit_reason_if_admitted"] = position_row.get(
            "exit_reason"
        )
        row["position_r_if_admitted_before_final_admission"] = position_row.get(
            "r_multiple"
        )
        decision = comparator008_admission_decision(
            comparator008_facts_from_replay_row(row)
        )
        row["comp008_admitted"] = decision.admitted
        row["rejection_reasons"] = list(decision.abstention_reasons)
        row["comp008_reasoning_action"] = (
            "EXECUTE" if decision.admitted else "ABSTAIN"
        )
        row["comp008_reasoning_contradictions"] = list(
            decision.abstention_reasons
        )
        row["entry_state"] = _state(row)
        enriched.append(row)
        (admitted if decision.admitted else rejected).append(row)

    return enriched, admitted, rejected


def _groups(
    rows: list[dict[str, object]],
) -> tuple[
    dict[str, list[dict[str, object]]],
    dict[str, list[dict[str, object]]],
]:
    by_reason: dict[str, list[dict[str, object]]] = defaultdict(list)
    by_state: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        for reason in cast(list[str], row["rejection_reasons"]):
            by_reason[reason].append(row)
        state = cast(dict[str, str], row["entry_state"])
        for field in STATE_FIELDS:
            by_state[f"{field}={state[field]}"].append(row)
    return by_reason, by_state


def _group_report(
    groups: dict[str, list[dict[str, object]]],
) -> dict[str, object]:
    return {
        key: {
            "sample": len(rows),
            "metrics": _metrics(rows),
            "temporal": _temporal(rows),
            "signal_ids": [str(row["signal_at"]) for row in rows],
            "rejection_reason_union": sorted(
                {
                    reason
                    for row in rows
                    for reason in cast(list[str], row["rejection_reasons"])
                }
            ),
        }
        for key, rows in sorted(groups.items())
    }


def _compact(row: dict[str, object]) -> dict[str, object]:
    return {
        "signal_at": row["signal_at"],
        "local_date": row["local_date"],
        "entry_family": row["entry_family"],
        "side": row["side"],
        "exit_reason": row["exit_reason"],
        "r_multiple": row["r_multiple"],
        "mfe_r": row.get("mfe_r"),
        "mae_r": row.get("mae_r"),
        "entry_state": row["entry_state"],
        "rejection_reasons": row["rejection_reasons"],
        "comp008_reasoning_action": row["comp008_reasoning_action"],
        "comp008_reasoning_contradictions": row[
            "comp008_reasoning_contradictions"
        ],
    }


def partition_report(
    evidence_path: Path,
    *,
    partition: str,
) -> dict[str, object]:
    full, admitted, rejected = _reconstruct_population(evidence_path)

    frozen = pack._candidate_rows(evidence_path)
    frozen_ids = [str(row["signal_at"]) for row in frozen]
    policy_ids = [str(row["signal_at"]) for row in admitted]
    if policy_ids != frozen_ids:
        missing = sorted(set(frozen_ids) - set(policy_ids))
        extra = sorted(set(policy_ids) - set(frozen_ids))
        raise AssertionError(
            "Comparator-008 runtime admission does not reproduce "
            f"Comparator-009 identity: missing={missing}, extra={extra}"
        )

    by_reason, by_state = _groups(rejected)
    return {
        "schema": SCHEMA,
        "mode": "partition",
        "partition": partition,
        "base_comparator_id": BASE_COMPARATOR_ID,
        "structural_trade_count": len(full),
        "admitted_trade_count": len(admitted),
        "rejected_trade_count": len(rejected),
        "admission_identity_exact": True,
        "full_structural_metrics": _metrics(full),
        "admitted_structural_metrics": _metrics(admitted),
        "rejected_structural_metrics": _metrics(rejected),
        "rejected_temporal": _temporal(rejected),
        "rejection_reason_groups": _group_report(by_reason),
        "rejected_single_state_groups": _group_report(by_state),
        "rejected_rows": [_compact(row) for row in rejected],
        "governance": {
            "observation_only": True,
            "structural_identity_frozen_before_outcome_analysis": True,
            "terminal_outcome_runtime_authority": False,
            "future_path_runtime_authority": False,
            "fold_identity_runtime_authority": False,
            "date_identity_runtime_authority": False,
            "new_numeric_threshold_added": False,
            "new_conjunction_mined": False,
            "position_sizing_used": False,
            "dynamic_sizing_used": False,
            "leverage_used": False,
            "compounding_used": False,
            "portfolio_weighting_used": False,
            "capital_weighting_used": False,
            "fresh_holdout_opened": False,
            "policy_promoted": False,
            "candidate_frozen": False,
            "candidate_certified": False,
        },
    }


def _aggregate_group(
    rows: list[dict[str, object]],
    *,
    partition_field: str = "partition",
) -> dict[str, object]:
    by_partition: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        by_partition[str(row[partition_field])].append(row)
    partition_metrics = {
        key: _metrics(items)
        for key, items in sorted(by_partition.items())
    }
    temporal = _temporal(rows)
    negative_halfyears = [
        key
        for key, metrics in cast(
            dict[str, dict[str, object]],
            temporal["halfyears"],
        ).items()
        if _d(metrics["mean_r"]) <= 0
    ]
    return {
        "sample": len(rows),
        "partition_support": sorted(by_partition),
        "partition_count": len(by_partition),
        "metrics": _metrics(rows),
        "partition_metrics": partition_metrics,
        "temporal": temporal,
        "all_supporting_partition_mean_positive": all(
            _d(metrics["mean_r"]) > 0
            for metrics in partition_metrics.values()
        ),
        "negative_halfyears": negative_halfyears,
    }


def aggregate(reports: list[dict[str, object]]) -> dict[str, object]:
    expected = {"r5", "r6", "r8", "consumed"}
    by_partition = {
        str(report["partition"]): report
        for report in reports
    }
    if set(by_partition) != expected:
        raise AssertionError(
            f"expected {sorted(expected)}, got {sorted(by_partition)}"
        )
    if not all(
        report["admission_identity_exact"] is True
        for report in reports
    ):
        raise AssertionError("admission identity parity failed")

    rejected: list[dict[str, object]] = []
    for partition in ("r5", "r6", "r8", "consumed"):
        for row in cast(
            list[dict[str, object]],
            by_partition[partition]["rejected_rows"],
        ):
            rejected.append({"partition": partition, **row})
    rejected.sort(key=lambda row: str(row["signal_at"]))

    reason_groups: dict[str, list[dict[str, object]]] = defaultdict(list)
    state_groups: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rejected:
        for reason in cast(list[str], row["rejection_reasons"]):
            reason_groups[reason].append(row)
        state = cast(dict[str, str], row["entry_state"])
        for field in STATE_FIELDS:
            state_groups[f"{field}={state[field]}"].append(row)

    reasons = {
        key: _aggregate_group(rows)
        for key, rows in sorted(reason_groups.items())
    }
    states = {
        key: _aggregate_group(rows)
        for key, rows in sorted(state_groups.items())
    }

    positive_candidates = []
    for family, groups in (("rejection_reason", reasons), ("single_state", states)):
        for key, report in groups.items():
            item = cast(dict[str, object], report)
            metrics = cast(dict[str, object], item["metrics"])
            if (
                int(item["partition_count"]) >= 3
                and item["all_supporting_partition_mean_positive"] is True
                and _d(metrics["mean_r"]) > 0
                and _pf(metrics) > Decimal(1)
            ):
                positive_candidates.append(
                    {
                        "family": family,
                        "key": key,
                        **item,
                    }
                )
    positive_candidates.sort(
        key=lambda item: (
            -_d(cast(dict[str, object], item["metrics"])["mean_r"]),
            -int(item["sample"]),
            str(item["key"]),
        )
    )

    return {
        "schema": SCHEMA,
        "mode": "aggregate",
        "base_comparator_id": BASE_COMPARATOR_ID,
        "partitions": {
            key: {
                "structural_trade_count": report["structural_trade_count"],
                "admitted_trade_count": report["admitted_trade_count"],
                "rejected_trade_count": report["rejected_trade_count"],
                "full_structural_metrics": report["full_structural_metrics"],
                "admitted_structural_metrics": report[
                    "admitted_structural_metrics"
                ],
                "rejected_structural_metrics": report[
                    "rejected_structural_metrics"
                ],
            }
            for key, report in sorted(by_partition.items())
        },
        "rejected_trade_count": len(rejected),
        "rejected_structural_metrics": _metrics(rejected),
        "rejected_temporal": _temporal(rejected),
        "rejection_reason_groups": reasons,
        "rejected_single_state_groups": states,
        "positive_cross_partition_candidates": positive_candidates,
        "positive_candidate_count": len(positive_candidates),
        "interpretation": {
            "candidate_quality_is_observation_only": True,
            "candidate_requires_separate_promotion_gate": True,
            "no_global_readmission_authority": True,
        },
        "governance": {
            "observation_only": True,
            "admission_identity_exact_all_partitions": True,
            "terminal_outcome_runtime_authority": False,
            "future_path_runtime_authority": False,
            "fold_identity_runtime_authority": False,
            "date_identity_runtime_authority": False,
            "new_numeric_threshold_added": False,
            "new_conjunction_mined": False,
            "position_sizing_used": False,
            "dynamic_sizing_used": False,
            "leverage_used": False,
            "compounding_used": False,
            "portfolio_weighting_used": False,
            "capital_weighting_used": False,
            "fresh_holdout_opened": False,
            "policy_promoted": False,
            "candidate_frozen": False,
            "candidate_certified": False,
        },
    }


def _write(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("partition")
    p.add_argument("evidence", type=Path)
    p.add_argument("--partition", required=True)
    p.add_argument("--output", required=True, type=Path)

    a = sub.add_parser("aggregate")
    a.add_argument("reports", nargs="+", type=Path)
    a.add_argument("--output", required=True, type=Path)

    args = parser.parse_args()
    if args.command == "partition":
        payload = partition_report(
            args.evidence,
            partition=args.partition,
        )
    else:
        payload = aggregate(
            [
                json.loads(path.read_text(encoding="utf-8"))
                for path in args.reports
            ]
        )
    _write(args.output, payload)
    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
