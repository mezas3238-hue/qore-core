"""VT31_NAS100 handoff intelligence forensics over consumed replay.

Implements the Turtle Soup research architecture using VT31/NAS100 evidence:
- loss forensics;
- WAIT / entry-sequence forensics;
- journey-capacity calibration;
- invalidation geometry buckets learned from NAS100 quantiles;
- destination alignment;
- intelligence metrics.

No rule is selected. No fresh holdout is opened.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path
from statistics import median
from typing import Any, cast

IDENTITY = "VT31_NAS100_HANDOFF_INTELLIGENCE_FORENSICS_V1"


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _quantile(values: list[Decimal], p: Decimal) -> Decimal | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = p * Decimal(len(ordered) - 1)
    lo = int(position)
    hi = min(lo + 1, len(ordered) - 1)
    weight = position - Decimal(lo)
    return ordered[lo] * (Decimal(1) - weight) + ordered[hi] * weight


def _fmt(value: Decimal | None) -> str | None:
    return None if value is None else format(value, "f")


def _rate(n: int, d: int) -> str | None:
    return None if d == 0 else format(Decimal(n) / Decimal(d), "f")


def _median(values: list[Decimal]) -> str | None:
    return None if not values else format(median(values), "f")


def _loss_family(trade: dict[str, Any]) -> str:
    reason = str(trade.get("exit_reason", "unknown"))
    if reason == "initial-stop":
        return "STRUCTURAL_INVALIDATION"
    if "breakeven" in reason:
        return "PROTECTION_EXIT"
    if "16:00" in reason or "lifecycle" in reason:
        return "LIFECYCLE_NO_DESTINATION"
    if "partial" in reason and _d(trade["r_multiple"]) <= 0:
        return "PARTIAL_MANAGEMENT_FAILURE"
    return "OTHER_TERMINAL_LOSS"


def _risk_bucket(
    value: Decimal,
    q1: Decimal,
    q2: Decimal,
    q3: Decimal,
) -> str:
    if value <= q1:
        return "Q1_TIGHTEST"
    if value <= q2:
        return "Q2"
    if value <= q3:
        return "Q3"
    return "Q4_WIDEST"


def _boundary_r(trade: dict[str, Any]) -> Decimal | None:
    if trade.get("boundary_r") is not None:
        return _d(trade["boundary_r"])
    if trade.get("planned_target_r") is not None:
        return _d(trade["planned_target_r"])
    state = trade.get("intelligence_state")
    if isinstance(state, dict) and state.get("planned_target_r") is not None:
        return _d(state["planned_target_r"])
    return None


def _risk_ref(trade: dict[str, Any]) -> Decimal | None:
    state = trade.get("intelligence_state")
    if not isinstance(state, dict):
        return None
    value = state.get("risk_ref")
    return None if value is None else _d(value)


def _entry_sequences(
    trace: list[dict[str, Any]],
) -> dict[str, object]:
    by_date: dict[str, list[str]] = defaultdict(list)
    for row in trace:
        by_date[str(row["local_date"])].append(str(row["action"]))

    transitions: Counter[str] = Counter()
    wait_depths: list[int] = []
    for actions in by_date.values():
        waits = sum(action == "WAIT" for action in actions)
        if waits:
            wait_depths.append(waits)
        if not actions:
            continue
        if waits and "EXECUTE" in actions:
            transitions["WAIT_TO_EXECUTE"] += 1
        elif waits and "ABSTAIN" in actions:
            transitions["WAIT_TO_ABSTAIN"] += 1
        elif waits:
            transitions["WAIT_EXPIRED"] += 1
        elif "EXECUTE" in actions:
            transitions["DIRECT_EXECUTE"] += 1
        elif "ABSTAIN" in actions:
            transitions["DIRECT_ABSTAIN"] += 1

    return {
        "dates_with_reasoning": len(by_date),
        "transition_counts": dict(sorted(transitions.items())),
        "wait_observations": sum(
            action == "WAIT" for actions in by_date.values() for action in actions
        ),
        "wait_depth_median": (
            None if not wait_depths else str(median(wait_depths))
        ),
        "wait_depth_max": max(wait_depths, default=0),
    }


def _capacity_group(
    rows: list[dict[str, Any]],
) -> dict[str, object]:
    ranks = [
        int(row["max_distinct_active_dol_rank_touched_before_invalidation"])
        for row in rows
    ]
    return {
        "n": len(rows),
        "rank_median": None if not ranks else str(median(ranks)),
        "dol1_reach_rate": _rate(sum(rank >= 1 for rank in ranks), len(ranks)),
        "dol2_reach_rate": _rate(sum(rank >= 2 for rank in ranks), len(ranks)),
        "dol3_reach_rate": _rate(sum(rank >= 3 for rank in ranks), len(ranks)),
        "dol4plus_reach_rate": _rate(
            sum(rank >= 4 for rank in ranks),
            len(ranks),
        ),
        "mfe_r_median": _median(
            [
                _d(row["max_favorable_r_before_invalidation"])
                for row in rows
            ]
        ),
        "mae_r_median": _median(
            [
                _d(row["max_adverse_r_before_invalidation"])
                for row in rows
            ]
        ),
        "risk_ref_median": _median([_d(row["risk_ref"]) for row in rows]),
    }


def _capacity_context_tables(
    rows: list[dict[str, Any]],
) -> dict[str, object]:
    dimensions = (
        "prior_day_state",
        "h4_state",
        "h1_state",
        "premarket_state",
        "cash_open_state",
        "position_in_prior_day_range",
        "reference_volatility_state",
        "last_structure_event_family",
    )
    result: dict[str, object] = {}
    for dimension in dimensions:
        groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            context = row.get("pre_entry_context")
            if not isinstance(context, dict):
                continue
            groups[str(context.get(dimension, "unavailable"))].append(row)
        result[dimension] = {
            key: _capacity_group(group)
            for key, group in sorted(groups.items())
            if len(group) >= 5
        }
    return result


def build(replay: dict[str, Any]) -> dict[str, object]:
    if replay.get("research_only") is not True:
        raise ValueError("forensics requires research-only replay")
    if replay.get("opens_new_holdout") is not False:
        raise ValueError("forensics cannot consume a fresh holdout")
    if replay.get("candidate_frozen") is not False:
        raise ValueError("forensics expects development candidate")

    trades = cast(list[dict[str, Any]], replay["trades"])
    trace = cast(list[dict[str, Any]], replay["reasoning_trace"])
    capacity_rows = cast(
        list[dict[str, Any]],
        replay.get("journey_capacity_observations", []),
    )

    losses = [trade for trade in trades if _d(trade["r_multiple"]) <= 0]
    loss_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for trade in losses:
        loss_groups[_loss_family(trade)].append(trade)
    loss_forensics = {
        family: {
            "n": len(rows),
            "mfe_r_median": _median([_d(row["mfe_r"]) for row in rows]),
            "mae_r_median": _median([_d(row["mae_r"]) for row in rows]),
            "planned_target_r_median": _median(
                [
                    value
                    for row in rows
                    if (value := _boundary_r(row)) is not None
                ]
            ),
        }
        for family, rows in sorted(loss_groups.items())
    }

    risk_values = [_d(row["risk_ref"]) for row in capacity_rows]
    q1 = _quantile(risk_values, Decimal("0.25"))
    q2 = _quantile(risk_values, Decimal("0.50"))
    q3 = _quantile(risk_values, Decimal("0.75"))
    geometry: dict[str, object] = {}
    if q1 is not None and q2 is not None and q3 is not None:
        groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in capacity_rows:
            risk = _d(row["risk_ref"])
            groups[_risk_bucket(risk, q1, q2, q3)].append(row)
        for bucket, rows in sorted(groups.items()):
            geometry[bucket] = _capacity_group(rows)

    boundaries = [
        (trade, boundary)
        for trade in trades
        if (boundary := _boundary_r(trade)) is not None
    ]
    reached = sum(_d(trade["mfe_r"]) >= boundary for trade, boundary in boundaries)
    partial = sum(bool(trade.get("partial_done")) for trade in trades)
    protection = sum(
        "breakeven" in str(trade.get("exit_reason", ""))
        for trade in trades
    )

    execute_traces = [row for row in trace if row.get("action") == "EXECUTE"]
    contradiction_execute = sum(
        bool(row.get("reasoning_contradictions")) for row in execute_traces
    )
    uncertainty_events = sum(
        bool(row.get("reasoning_uncertainty")) for row in trace
    )

    capacity_rank_counts = Counter(
        int(row["max_distinct_active_dol_rank_touched_before_invalidation"])
        for row in capacity_rows
    )
    capacity_summary = _capacity_group(capacity_rows)

    return {
        "identity": IDENTITY,
        "candidate_id": replay["candidate_id"],
        "contract_fingerprint": replay["contract_fingerprint"],
        "market": "NAS100",
        "source_evidence": replay["evidence"],
        "loss_forensics": {
            "losses": len(losses),
            "families": loss_forensics,
        },
        "entry_wait_forensics": _entry_sequences(trace),
        "journey_capacity": {
            "label": (
                "MAX_DISTINCT_ACTIVE_DOL_RANK_TOUCHED_BEFORE_INVALIDATION"
            ),
            "labeled_opportunities": len(capacity_rows),
            "rank_counts": {
                str(key): value
                for key, value in sorted(capacity_rank_counts.items())
            },
            "overall": capacity_summary,
            "risk_ref_quantile_boundaries": {
                "q25": _fmt(q1),
                "q50": _fmt(q2),
                "q75": _fmt(q3),
            },
            "by_invalidation_geometry_quantile": geometry,
            "by_pre_entry_context": _capacity_context_tables(capacity_rows),
            "legacy_selected_trade_boundary_assessed": len(boundaries),
            "legacy_selected_trade_boundary_reached": reached,
            "partial_milestone_reached_count": partial,
            "protection_exit_count": protection,
        },
        "intelligence_metrics": {
            "reasoning_events": len(trace),
            "execute_reasoning_events": len(execute_traces),
            "uncertainty_event_rate": _rate(
                uncertainty_events,
                len(trace),
            ),
            "execute_contradiction_count": contradiction_execute,
            "execute_contradiction_rate": _rate(
                contradiction_execute,
                len(execute_traces),
            ),
            "dol1_alignment_rate": _rate(reached, len(boundaries)),
        },
        "governance": {
            "labels_are_structural_not_direct_pnl_rules": True,
            "risk_buckets_are_nas100_quantiles_not_xauusd_thresholds": True,
            "rule_selection_allowed": False,
            "opens_new_holdout": False,
            "live_authorized": False,
            "production_authorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("replay", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    replay = json.loads(args.replay.read_text(encoding="utf-8"))
    payload = build(replay)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "identity": IDENTITY,
                "losses": payload["loss_forensics"]["losses"],
                "entry_wait": payload["entry_wait_forensics"],
                "journey_capacity": payload["journey_capacity"],
                "intelligence_metrics": payload["intelligence_metrics"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
