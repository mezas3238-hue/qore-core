"""Bridge CIBO Atlas market knowledge into causal VT31_NAS100 observations.

Two strictly separated layers are produced:

1. historical_knowledge
   Aggregate, consumed-only market priors learned from CIBO Atlas.  These may
   inform reasoning, but never identify the outcome of a specific runtime date.

2. runtime_observations
   CIBO-derived events that were already observable no later than each VT31
   decision timestamp.  Future structure touches, departure pivots, objectives,
   day-regime labels, target extensions and trader terminal labels are excluded.

Research only.  No rule selection, candidate freeze, holdout opening or live
authorization is performed here.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, cast
from zoneinfo import ZoneInfo

SCHEMA = "qore.vt31.nas100.cibo_intelligence_bridge.v1"
STATE_SCHEMA = "qore.vt31.nas100.market_state_lab.v2"
CIBO_SCHEMA = "qore.cibo_atlas.vt31.eight_ledger_bundle.v1"
MARKET = "NAS100"
PEERS = ("SP500", "US30")
NY = ZoneInfo("America/New_York")
PARTITIONS = ("r8_fresh", "r6", "r5")
STRUCTURE_FAMILIES = (
    "local-liquidity-sweep",
    "reference-liquidity-sweep",
    "fair-value-gap",
    "breaker",
    "order-block",
)
POST_OUTCOME_RUNTIME_PROHIBITED = (
    "day_regime",
    "departure_pivot_at",
    "last_structure_before_departure",
    "opposite_boundary_at",
    "opposite_boundary_hit_by_16",
    "post_boundary_extension_ref",
    "post_boundary_ladder",
    "post_objective_farthest_at",
    "terminal_family",
    "terminal_r",
    "terminal_status",
    "trader_stopped_before_eventual_source_objective",
)


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        cast(dict[str, Any], json.loads(line))
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _dt(value: object) -> datetime | None:
    if value in (None, ""):
        return None
    parsed = datetime.fromisoformat(str(value))
    if parsed.tzinfo is None:
        raise ValueError(f"timezone-naive timestamp: {value}")
    return parsed


def _fmt(value: Decimal | None) -> str | None:
    return None if value is None else format(value, "f")


def _fraction(n: int, d: int) -> str | None:
    return None if d == 0 else _fmt(Decimal(n) / Decimal(d))


def _quantile(values: list[int], p: Decimal) -> Decimal | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return Decimal(ordered[0])
    position = p * Decimal(len(ordered) - 1)
    lo = int(position)
    hi = min(lo + 1, len(ordered) - 1)
    weight = position - Decimal(lo)
    return (
        Decimal(ordered[lo]) * (Decimal(1) - weight)
        + Decimal(ordered[hi]) * weight
    )


def _local_minute(value: datetime) -> int:
    local = value.astimezone(NY)
    return local.hour * 60 + local.minute


def _bucket_15(value: datetime) -> str:
    minute = _local_minute(value)
    return f"{minute // 60:02d}:{((minute % 60) // 15) * 15:02d}"


def _safe_structure_events(
    events: list[dict[str, Any]],
    decision_at: datetime,
) -> list[dict[str, Any]]:
    safe: list[dict[str, Any]] = []
    for event in events:
        formed_at = _dt(event.get("formed_at"))
        first_touch_at = _dt(event.get("first_touch_at"))
        if formed_at is None or first_touch_at is None:
            continue
        if formed_at <= decision_at and first_touch_at <= decision_at:
            safe.append(event)
    return sorted(
        safe,
        key=lambda row: cast(datetime, _dt(row["first_touch_at"])),
    )


def _age_minutes(decision_at: datetime, event_at: object) -> int | None:
    parsed = _dt(event_at)
    if parsed is None or parsed > decision_at:
        return None
    return int((decision_at - parsed).total_seconds() // 60)


def _recent_count(
    events: list[dict[str, Any]],
    decision_at: datetime,
    family: str | None,
    minutes: int,
) -> int:
    count = 0
    for event in events:
        if family is not None and event.get("structure_family") != family:
            continue
        age = _age_minutes(decision_at, event.get("first_touch_at"))
        if age is not None and 0 <= age <= minutes:
            count += 1
    return count


def _peer_state(
    row: dict[str, Any] | None,
    decision_at: datetime,
) -> dict[str, object]:
    if row is None:
        return {
            "available": False,
            "breach_observed": False,
            "breach_side": "unavailable",
            "minutes_since_breach": None,
            "source_confirmation_observed": False,
            "minutes_since_source_confirmation": None,
        }

    breach_at = _dt(row.get("first_breach_at"))
    confirmation_at = _dt(row.get("source_confirmation_at"))
    breach_observed = breach_at is not None and breach_at <= decision_at
    confirmation_observed = (
        confirmation_at is not None and confirmation_at <= decision_at
    )
    return {
        "available": True,
        "breach_observed": breach_observed,
        "breach_side": (
            str(row.get("first_breach"))
            if breach_observed
            else "not-observed-by-decision"
        ),
        "minutes_since_breach": (
            int((decision_at - breach_at).total_seconds() // 60)
            if breach_observed and breach_at is not None
            else None
        ),
        "source_confirmation_observed": confirmation_observed,
        "minutes_since_source_confirmation": (
            int((decision_at - confirmation_at).total_seconds() // 60)
            if confirmation_observed and confirmation_at is not None
            else None
        ),
    }


def _cross_index_state(
    side: str,
    peers: dict[str, dict[str, object]],
) -> dict[str, object]:
    expected_breach = "low" if side == "long" else "high"
    observed_sides = [
        str(payload["breach_side"])
        for payload in peers.values()
        if payload["breach_observed"] is True
    ]
    same = sum(value == expected_breach for value in observed_sides)
    opposite = sum(
        value in {"high", "low"} and value != expected_breach
        for value in observed_sides
    )
    confirmations = sum(
        payload["source_confirmation_observed"] is True
        for payload in peers.values()
    )
    if same == 2:
        state = "both-peers-same-breach"
    elif opposite == 2:
        state = "both-peers-opposite-breach"
    elif same == 1 and opposite == 1:
        state = "peer-divergence"
    elif same == 1:
        state = "one-peer-same-breach"
    elif opposite == 1:
        state = "one-peer-opposite-breach"
    else:
        state = "no-peer-breach-observed"
    return {
        "expected_breach_for_trade_side": expected_breach,
        "peer_same_breach_count": same,
        "peer_opposite_breach_count": opposite,
        "peer_source_confirmation_count": confirmations,
        "state": state,
    }


def _runtime_observation(
    state_row: dict[str, Any],
    structure_events: list[dict[str, Any]],
    journeys: dict[tuple[str, str, str], dict[str, Any]],
) -> dict[str, object]:
    decision_at = cast(datetime, _dt(state_row["signal_at"]))
    partition = str(state_row["partition"])
    ny_date = str(state_row["local_date"])
    side = str(state_row["side"])

    safe_events = _safe_structure_events(structure_events, decision_at)
    family_counts = Counter(
        str(event["structure_family"]) for event in safe_events
    )
    last_event = safe_events[-1] if safe_events else None
    liquidity_events = [
        event
        for event in safe_events
        if event["structure_family"]
        in {"local-liquidity-sweep", "reference-liquidity-sweep"}
    ]
    pd_array_events = [
        event
        for event in safe_events
        if event["structure_family"] in {"fair-value-gap", "breaker", "order-block"}
    ]
    last_liquidity = liquidity_events[-1] if liquidity_events else None
    last_pd_array = pd_array_events[-1] if pd_array_events else None

    peers = {
        peer: _peer_state(
            journeys.get((partition, ny_date, peer)),
            decision_at,
        )
        for peer in PEERS
    }
    cross_index = _cross_index_state(side, peers)

    structure_payload: dict[str, object] = {
        "total_events_observed": len(safe_events),
        "last_event_family": (
            str(last_event["structure_family"]) if last_event else "none"
        ),
        "last_event_age_minutes": (
            _age_minutes(decision_at, last_event["first_touch_at"])
            if last_event else None
        ),
        "last_liquidity_event_family": (
            str(last_liquidity["structure_family"])
            if last_liquidity else "none"
        ),
        "last_liquidity_event_age_minutes": (
            _age_minutes(decision_at, last_liquidity["first_touch_at"])
            if last_liquidity else None
        ),
        "last_pd_array_family": (
            str(last_pd_array["structure_family"])
            if last_pd_array else "none"
        ),
        "last_pd_array_age_minutes": (
            _age_minutes(decision_at, last_pd_array["first_touch_at"])
            if last_pd_array else None
        ),
        "recent_liquidity_events_5m": _recent_count(
            liquidity_events, decision_at, None, 5
        ),
        "recent_liquidity_events_10m": _recent_count(
            liquidity_events, decision_at, None, 10
        ),
        "recent_liquidity_events_15m": _recent_count(
            liquidity_events, decision_at, None, 15
        ),
    }
    for family in STRUCTURE_FAMILIES:
        structure_payload[f"{family}_count_observed"] = family_counts[family]
        structure_payload[f"{family}_count_last_10m"] = _recent_count(
            safe_events,
            decision_at,
            family,
            10,
        )

    return {
        "partition": partition,
        "local_date": ny_date,
        "decision_at": decision_at.isoformat(),
        "side": side,
        "market_state": {
            "decision_time_bucket": state_row["decision_time_bucket"],
            "first_breach_side": state_row["first_breach_side"],
            "double_sided_before_decision": state_row[
                "double_sided_before_decision"
            ],
            "minutes_raid_to_decision": state_row["minutes_raid_to_decision"],
            "reference_reclaimed": state_row["reference_reclaimed"],
            "minutes_reclaim_to_decision": state_row[
                "minutes_reclaim_to_decision"
            ],
            "raid_depth_ref": state_row["raid_depth_ref"],
            "session_range_ref": state_row["session_range_ref"],
            "recent_range_ref": state_row["recent_range_ref"],
            "recent_path_efficiency": state_row[
                "recent_path_efficiency"
            ],
            "recent_overlap_rate": state_row["recent_overlap_rate"],
            "risk_ref": state_row["risk_ref"],
            "planned_target_r": state_row["planned_target_r"],
        },
        "cibo_structure_state": structure_payload,
        "cibo_peer_state": peers,
        "cibo_cross_index_state": cross_index,
        "research_labels": {
            "status": state_row.get("status"),
            "exit_reason": state_row.get("exit_reason"),
            "r_multiple": state_row.get("r_multiple"),
            "mfe_r": state_row.get("mfe_r"),
            "mae_r": state_row.get("mae_r"),
        },
    }


def _historical_knowledge(
    daily: list[dict[str, Any]],
    departures: list[dict[str, Any]],
    sequences: list[dict[str, Any]],
    targets: list[dict[str, Any]],
    trader: list[dict[str, Any]],
) -> dict[str, object]:
    nas_daily = [row for row in daily if row.get("market") == MARKET]
    nas_departures = [
        row for row in departures if row.get("market") == MARKET
    ]
    nas_sequences = [
        row for row in sequences if row.get("market") == MARKET
    ]
    nas_targets = [row for row in targets if row.get("market") == MARKET]
    nas_trader = [row for row in trader if row.get("market") == MARKET]

    partition_knowledge: dict[str, object] = {}
    for partition in PARTITIONS:
        part_departures = [
            row
            for row in nas_departures
            if row.get("partition") == partition
        ]
        part_targets = [
            row for row in nas_targets if row.get("partition") == partition
        ]
        completed_targets = [
            row
            for row in part_targets
            if row.get("opposite_boundary_hit_by_16") is True
        ]
        last_structure = Counter(
            str(row.get("last_structure_before_departure"))
            for row in part_departures
        )
        touch_to_departure = [
            int(row["minutes_last_structure_touch_to_departure"])
            for row in part_departures
            if isinstance(
                row.get("minutes_last_structure_touch_to_departure"),
                int,
            )
        ]
        breach_to_departure = [
            int(row["minutes_breach_to_departure"])
            for row in part_departures
            if isinstance(row.get("minutes_breach_to_departure"), int)
        ]
        departure_to_objective = [
            int(row["minutes_departure_to_objective"])
            for row in part_departures
            if isinstance(row.get("minutes_departure_to_objective"), int)
        ]
        partition_knowledge[partition] = {
            "completed_reversal_episodes": len(part_departures),
            "last_structure_before_departure_counts": dict(
                sorted(last_structure.items())
            ),
            "last_structure_touch_to_departure_minutes": {
                "p25": _fmt(_quantile(touch_to_departure, Decimal("0.25"))),
                "p50": _fmt(_quantile(touch_to_departure, Decimal("0.50"))),
                "p75": _fmt(_quantile(touch_to_departure, Decimal("0.75"))),
            },
            "breach_to_departure_minutes": {
                "p25": _fmt(_quantile(breach_to_departure, Decimal("0.25"))),
                "p50": _fmt(_quantile(breach_to_departure, Decimal("0.50"))),
                "p75": _fmt(_quantile(breach_to_departure, Decimal("0.75"))),
            },
            "departure_to_objective_minutes": {
                "p25": _fmt(_quantile(departure_to_objective, Decimal("0.25"))),
                "p50": _fmt(_quantile(departure_to_objective, Decimal("0.50"))),
                "p75": _fmt(_quantile(departure_to_objective, Decimal("0.75"))),
            },
            "opposite_boundary_hit_rate": _fraction(
                len(completed_targets),
                len(part_targets),
            ),
            "post_boundary_extension_rate_given_hit": {
                level: _fraction(
                    sum(
                        bool(
                            cast(dict[str, bool], row["post_boundary_ladder"])[
                                level
                            ]
                        )
                        for row in completed_targets
                    ),
                    len(completed_targets),
                )
                for level in ("0.25", "0.5", "1", "1.5", "2")
            },
        }

    last_touch_families = Counter(
        str(row.get("last_structure_before_departure"))
        for row in nas_departures
    )
    departure_buckets = Counter(
        _bucket_15(cast(datetime, _dt(row["departure_at"])))
        for row in nas_departures
    )
    sequence_tail = Counter()
    for row in nas_sequences:
        departure_at = cast(datetime, _dt(row["departure_pivot_at"]))
        observed = []
        for event in cast(list[dict[str, Any]], row["event_sequence"]):
            event_at = cast(datetime, _dt(event["at"]))
            if event_at > departure_at:
                continue
            if event["event"] in {"departure_pivot", "opposite_09_boundary"}:
                continue
            observed.append(str(event["event"]))
        if observed:
            sequence_tail[observed[-1]] += 1

    initial_stops = [
        row for row in nas_trader if row.get("terminal_family") == "initial_stop"
    ]
    protected_stops = [
        row
        for row in nas_trader
        if row.get("terminal_family") == "protected_stop"
    ]
    return {
        "timing_class": "AGGREGATE_POST_OUTCOME_RESEARCH_PRIOR",
        "runtime_date_lookup_allowed": False,
        "market_days": len(nas_daily),
        "completed_reversal_episodes": len(nas_departures),
        "definitive_trader_roots": len(nas_trader),
        "last_structure_before_departure_counts": dict(
            sorted(last_touch_families.items())
        ),
        "departure_15m_bucket_counts": dict(sorted(departure_buckets.items())),
        "last_predeparture_event_counts": dict(sorted(sequence_tail.items())),
        "stop_mismatch": {
            "initial_stop": {
                "n": len(initial_stops),
                "eventual_source_objective_count": sum(
                    bool(
                        row.get(
                            "trader_stopped_before_eventual_source_objective"
                        )
                    )
                    for row in initial_stops
                ),
            },
            "protected_stop": {
                "n": len(protected_stops),
                "eventual_source_objective_count": sum(
                    bool(
                        row.get(
                            "trader_stopped_before_eventual_source_objective"
                        )
                    )
                    for row in protected_stops
                ),
            },
        },
        "partition_stability": partition_knowledge,
        "interpretation": (
            "Historical priors describe NAS100 behavior.  They may support "
            "reasoning but cannot identify or select the outcome of a runtime "
            "date.  Runtime decisions consume only runtime_observations."
        ),
    }


def build(ledger_dir: Path, state_path: Path) -> dict[str, object]:
    summary = json.loads(
        (ledger_dir / "CIBO_ATLAS_VT31_EIGHT_LEDGER_SUMMARY.json").read_text(
            encoding="utf-8"
        )
    )
    if summary.get("schema") != CIBO_SCHEMA:
        raise ValueError("unexpected CIBO schema")
    if summary.get("research_only") is not True:
        raise ValueError("CIBO bundle is not research-only")

    state = json.loads(state_path.read_text(encoding="utf-8"))
    if state.get("schema") != STATE_SCHEMA:
        raise ValueError("unexpected Market State schema")
    state_contract = cast(dict[str, object], state["causal_contract"])
    if state_contract.get("date_level_outcome_lookup") is not False:
        raise ValueError("Market State date-outcome guard failed")
    if state_contract.get("future_bar_lookup") is not False:
        raise ValueError("Market State future-bar guard failed")

    daily = _read_jsonl(ledger_dir / "DAILY_PATH_LEDGER.jsonl")
    departures = _read_jsonl(
        ledger_dir / "DEPARTURE_TIMING_LEDGER.jsonl"
    )
    journeys = _read_jsonl(ledger_dir / "MARKET_JOURNEY_LEDGER.jsonl")
    sequences = _read_jsonl(
        ledger_dir / "PRE_DEPARTURE_SEQUENCE_LEDGER.jsonl"
    )
    structures = _read_jsonl(
        ledger_dir / "STRUCTURE_TOUCH_LEDGER.jsonl"
    )
    targets = _read_jsonl(
        ledger_dir / "TARGET_DESTINATION_LEDGER.jsonl"
    )
    trader = _read_jsonl(
        ledger_dir / "TRADER_MARKET_SYNC_LEDGER.jsonl"
    )

    journey_index = {
        (str(row["partition"]), str(row["ny_date"]), str(row["market"])): row
        for row in journeys
    }
    structure_index: dict[
        tuple[str, str], list[dict[str, Any]]
    ] = defaultdict(list)
    for row in structures:
        if row.get("market") != MARKET:
            continue
        structure_index[
            (str(row["partition"]), str(row["ny_date"]))
        ].append(row)

    observations = []
    for row in cast(list[dict[str, Any]], state["state_matrix"]):
        partition = str(row["partition"])
        ny_date = str(row["local_date"])
        observations.append(
            _runtime_observation(
                row,
                structure_index.get((partition, ny_date), []),
                journey_index,
            )
        )

    return {
        "schema": SCHEMA,
        "market": MARKET,
        "partition": state["partition"],
        "research_only": True,
        "selection_prohibited": True,
        "runtime_policy_selected": False,
        "candidate_frozen": False,
        "opens_new_holdout": False,
        "live_authorized": False,
        "production_authorized": False,
        "evidence_binding": {
            "cibo_schema": CIBO_SCHEMA,
            "cibo_source_sha": (
                ledger_dir / "git-sha.txt"
            ).read_text(encoding="utf-8").strip(),
            "market_state_schema": STATE_SCHEMA,
            "market_state_evidence": state["evidence"],
        },
        "causal_firewall": {
            "historical_knowledge_is_aggregate_only": True,
            "runtime_date_level_outcome_lookup": False,
            "runtime_future_structure_touch_lookup": False,
            "runtime_future_peer_breach_lookup": False,
            "runtime_future_peer_confirmation_lookup": False,
            "runtime_post_outcome_fields_prohibited": list(
                POST_OUTCOME_RUNTIME_PROHIBITED
            ),
            "structure_fields_allowed_runtime": [
                "structure_family",
                "formed_at<=decision_at",
                "first_touch_at<=decision_at",
            ],
            "structure_fields_explicitly_ignored_runtime": [
                "last_structure_before_departure",
                "last_touch_at",
                "bars_touched",
                "dwell_minutes",
                "max_penetration_fraction",
            ],
        },
        "historical_knowledge": _historical_knowledge(
            daily,
            departures,
            sequences,
            targets,
            trader,
        ),
        "runtime_observation_count": len(observations),
        "runtime_observations": observations,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ledger-dir", type=Path, required=True)
    parser.add_argument("--market-state", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = build(args.ledger_dir, args.market_state)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    knowledge = cast(dict[str, object], payload["historical_knowledge"])
    print(
        json.dumps(
            {
                "partition": payload["partition"],
                "runtime_observations": payload[
                    "runtime_observation_count"
                ],
                "market_days": knowledge["market_days"],
                "completed_reversal_episodes": knowledge[
                    "completed_reversal_episodes"
                ],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
