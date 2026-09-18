"""Compare stable and failing Turtle Soup R3 journey topology.

This is post-result diagnostic work over already-consumed R3/CIBO evidence. It
must not promote retrospective filters or consume a fresh holdout. The analysis
compares a stable raid-depth family (5-10% of recent mean source range) with the
consistently failing 25-50% raid + late-CISD family, including Protected Swing
risk geometry and active DOL topology known at entry.
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from statistics import median
from typing import Any

IDENTITY = "TURTLE_SOUP_XAUUSD_R3_JOURNEY_TOPOLOGY_FORENSICS_V1"
EVIDENCE_STATUS = "CONSUMED_R3_CAUSAL_DIAGNOSTIC_NOT_FRESH_HOLDOUT"
STABLE_RAID = "q2:<=0.10"
FAIL_RAID = "q4:<=0.50"
LATE_CISD = "q4:>0.75"
TARGET_REASONS = {"TARGET", "GAP_TARGET_CAPPED"}
STOP_REASONS = {"STOP", "GAP_STOP", "STOP_FIRST"}


def _dt(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return parsed


def _family(row: dict[str, Any]) -> str:
    if row["raid_depth_range_bucket"] == STABLE_RAID:
        return "RAID_5_10_STABLE"
    if row["raid_depth_range_bucket"] == FAIL_RAID and row["cisd_progress_bucket"] == LATE_CISD:
        return "RAID_25_50_LATE_CISD_FAILING"
    return "OTHER"


def _candidate_route(row: dict[str, Any]) -> str:
    kind = str(row["candidate_type"])
    timeframe = str(row["source_timeframe"])
    if kind == "SOURCE_OPPOSITE_BOUNDARY":
        return "SOURCE_OPPOSITE"
    if kind == "PRIOR_CANDLE_DIRECTIONAL_BOUNDARY":
        return f"PRIOR_{timeframe}"
    if kind == "ACTIVE_SWING_3_DIRECTIONAL_BOUNDARY":
        return f"SWING_{timeframe}"
    return f"OTHER_{timeframe}"


def _load_one(root: Path, name: str) -> Path:
    matches = list(root.rglob(name))
    if len(matches) != 1:
        raise ValueError(f"expected one {name}, found {len(matches)}")
    return matches[0]


def _load_targets(root: Path) -> dict[str, list[dict[str, Any]]]:
    path = _load_one(root, "TARGET_DESTINATION_LEDGER_V2.jsonl")
    episodes: dict[str, list[dict[str, Any]]] = defaultdict(list)
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                row = json.loads(line)
                episodes[str(row["episode_id"])].append(row)
    return dict(episodes)


def _active_topology(trade: dict[str, Any], candidates: Sequence[dict[str, Any]]) -> dict[str, Any]:
    entry = Decimal(str(trade["entry"]))
    target = Decimal(str(trade["target"]))
    side = str(trade["side"])
    at = _dt(str(trade["entry_at"]))
    active: list[dict[str, Any]] = []
    for row in candidates:
        if _dt(str(row["candidate_known_at"])) > at:
            continue
        touch_raw = row.get("touch_m5_opened_at")
        if touch_raw is not None and _dt(str(touch_raw)) < at:
            continue
        level = Decimal(str(row["candidate_price"]))
        ahead = level > entry if side == "long" else level < entry
        if ahead:
            active.append(row)
    active.sort(key=lambda item: abs(Decimal(str(item["candidate_price"])) - entry))
    selected_rank: int | None = None
    same_route = 0
    route_counts: Counter[str] = Counter()
    for index, row in enumerate(active, start=1):
        route = _candidate_route(row)
        route_counts[route] += 1
        if route == trade["target_route"]:
            same_route += 1
        if (
            Decimal(str(row["candidate_price"])) == target
            and str(row["candidate_type"]) == str(trade["target_kind"])
            and str(row["source_timeframe"]) == str(trade["target_timeframe"])
        ):
            selected_rank = index
    return {
        "active_ahead_count": len(active),
        "selected_rank_all_active": selected_rank,
        "same_route_active_count": same_route,
        "active_route_counts": dict(route_counts),
    }


def _pf(values: Sequence[Decimal]) -> str | None:
    gross_profit = sum((value for value in values if value > 0), Decimal(0))
    gross_loss = -sum((value for value in values if value < 0), Decimal(0))
    if gross_loss == 0:
        return None
    return str(gross_profit / gross_loss)


def _med(values: Sequence[Decimal]) -> str | None:
    return None if not values else str(median(values))


def _stat(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    values = [Decimal(str(row["primary_net_r"])) for row in rows]
    risks_bps = [
        Decimal("10000") * Decimal(str(row["risk_abs"])) / Decimal(str(row["entry"]))
        for row in rows
        if Decimal(str(row["entry"])) != 0
    ]
    structural_rr = [Decimal(str(row["structural_rr"])) for row in rows]
    active_counts = [Decimal(str(row["active_ahead_count"])) for row in rows]
    ranks = [
        Decimal(str(row["selected_rank_all_active"]))
        for row in rows
        if row["selected_rank_all_active"] is not None
    ]
    return {
        "trades": len(rows),
        "total_primary_r": str(sum(values, Decimal(0))),
        "mean_primary_r": str(sum(values, Decimal(0)) / len(values)) if values else None,
        "profit_factor": _pf(values),
        "target_rate": (sum(row["exit_reason"] in TARGET_REASONS for row in rows) / len(rows)) if rows else None,
        "stop_rate": (sum(row["exit_reason"] in STOP_REASONS for row in rows) / len(rows)) if rows else None,
        "median_risk_bps": _med(risks_bps),
        "median_structural_rr": _med(structural_rr),
        "median_active_ahead_dols": _med(active_counts),
        "median_selected_dol_rank": _med(ranks),
    }


def _group_stats(rows: Sequence[dict[str, Any]], key: str) -> dict[str, Any]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[str(row[key])].append(row)
    return {name: _stat(items) for name, items in sorted(groups.items())}


def _distribution(rows: Sequence[dict[str, Any]], key: str) -> dict[str, int]:
    return dict(sorted(Counter(str(row[key]) for row in rows).items()))


def run(causal_root: Path, target_root: Path, output: Path) -> dict[str, Any]:
    trades_path = _load_one(causal_root, "enriched-trades.json")
    trades = json.loads(trades_path.read_text())
    if len(trades) != 5885:
        raise ValueError(f"unexpected enriched R3 trade count: {len(trades)}")
    targets = _load_targets(target_root)

    enriched: list[dict[str, Any]] = []
    missing_episode = 0
    for raw in trades:
        row = dict(raw)
        episode_rows = targets.get(str(row["episode_id"]))
        if episode_rows is None:
            missing_episode += 1
            continue
        row["journey_family"] = _family(row)
        row.update(_active_topology(row, episode_rows))
        enriched.append(row)
    if missing_episode:
        raise ValueError(f"missing target episodes for {missing_episode} trades")

    baseline = [row for row in enriched if 2016 <= int(row["year"]) <= 2019]
    recent = [row for row in enriched if 2024 <= int(row["year"]) <= 2026]

    def family_rows(source: Sequence[dict[str, Any]], family: str) -> list[dict[str, Any]]:
        return [row for row in source if row["journey_family"] == family]

    stable_base = family_rows(baseline, "RAID_5_10_STABLE")
    stable_recent = family_rows(recent, "RAID_5_10_STABLE")
    fail_base = family_rows(baseline, "RAID_25_50_LATE_CISD_FAILING")
    fail_recent = family_rows(recent, "RAID_25_50_LATE_CISD_FAILING")

    feature_keys = (
        "reclaim_latency_bucket",
        "protected_risk_range_bucket",
        "source_range_state_bucket",
        "body_fraction_bucket",
        "rejection_wick_bucket",
        "close_location_bucket",
        "prior_body_alignment",
    )

    payload = {
        "schema": "qore.turtle_soup_xauusd_r3.journey_topology_forensics.v1",
        "identity": IDENTITY,
        "evidence_status": EVIDENCE_STATUS,
        "reproduction": {
            "input_enriched_trades": len(trades),
            "joined_target_episodes": len(enriched),
            "missing_target_episodes": missing_episode,
        },
        "family_definitions": {
            "stable": "raid depth >5% and <=10% of recent mean source range; any CISD timing",
            "failing": "raid depth >25% and <=50% plus CISD after >75% of source candle",
        },
        "stable_family": {
            "baseline_2016_2019": _stat(stable_base),
            "recent_2024_2026": _stat(stable_recent),
            "recent_by_year": _group_stats(stable_recent, "year"),
            "recent_by_target_route": _group_stats(stable_recent, "target_route"),
            "recent_by_source_timeframe": _group_stats(stable_recent, "source_timeframe"),
            "recent_by_side": _group_stats(stable_recent, "side"),
            "recent_feature_distributions": {key: _distribution(stable_recent, key) for key in feature_keys},
            "recent_selected_dol_rank_distribution": _distribution(stable_recent, "selected_rank_all_active"),
        },
        "failing_family": {
            "baseline_2016_2019": _stat(fail_base),
            "recent_2024_2026": _stat(fail_recent),
            "recent_by_year": _group_stats(fail_recent, "year"),
            "recent_by_target_route": _group_stats(fail_recent, "target_route"),
            "recent_by_source_timeframe": _group_stats(fail_recent, "source_timeframe"),
            "recent_by_side": _group_stats(fail_recent, "side"),
            "recent_feature_distributions": {key: _distribution(fail_recent, key) for key in feature_keys},
            "recent_selected_dol_rank_distribution": _distribution(fail_recent, "selected_rank_all_active"),
        },
        "diagnosis": {
            "stable_family_remains_positive_recent": Decimal(_stat(stable_recent)["total_primary_r"] or "0") > 0,
            "failing_family_flips_negative_recent": Decimal(_stat(fail_base)["total_primary_r"] or "0") > 0 and Decimal(_stat(fail_recent)["total_primary_r"] or "0") < 0,
            "active_dol_count_median_equal": _stat(stable_recent)["median_active_ahead_dols"] == _stat(fail_recent)["median_active_ahead_dols"],
            "failing_family_all_observed_target_routes_negative_recent": all(
                Decimal(str(item["total_primary_r"])) < 0
                for item in _group_stats(fail_recent, "target_route").values()
                if item["trades"] > 0
            ),
            "interpretation": "DOL availability/rank alone does not explain the regime failure. The failing family reaches entry with weaker raid-confirmation geometry: wider Protected-Swing risk, lower structural RR, lower target completion and higher stop incidence. CIBO should next model the topology of raid/reclaim/CISD/invalidation before deciding entry/DOL/abstention, rather than adding a blanket side/session/timeframe filter.",
            "rules_promoted": False,
            "fresh_holdout_consumed": False,
        },
        "governance": {
            "retrospective_filter_promotion_allowed": False,
            "economic_contract_changed": False,
            "fresh_holdout": False,
            "demo_eligible": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        },
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "journey-topology-forensics.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    (output / "topology-enriched-trades.json").write_text(json.dumps(enriched, indent=2, sort_keys=True) + "\n")
    return payload


def main() -> None:
    if len(sys.argv) != 4:
        raise SystemExit("usage: module CAUSAL_ARTIFACT_ROOT TARGET_V2_ROOT OUTPUT_DIR")
    print(json.dumps(run(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])), sort_keys=True))


if __name__ == "__main__":
    main()
