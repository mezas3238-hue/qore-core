"""R33 AUDJPY rank-1 structural subfamily discovery.

This is consumed-development research only. Candidate families are generated
exclusively from categorical state known before entry. Economic outcomes never
define a feature or threshold; they only validate pre-existing categorical
states. Fresh holdout remains sealed.

A family qualifies only when its rank-1 STATIC full-lifecycle outcome after
0.10R friction is positive in all five equal-count chronological quintiles,
has sufficient sample breadth, and meets the predeclared aggregate PF floor.
Selected families greedily maximize incremental historical coverage only after
passing those stability gates.
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from collections.abc import Sequence
from decimal import Decimal
from pathlib import Path
from typing import Any

IDENTITY = "TURTLE_SOUP_AUDJPY_R33_RANK1_SUBFAMILY_DISCOVERY_V1"

MIN_OBSERVATIONS = 200
MIN_PF_010 = Decimal("1.35")
REQUIRED_POSITIVE_QUINTILES = 5
MAX_FAMILIES = 8
MIN_INCREMENTAL_OBSERVATIONS = 100

PRE_ENTRY_FEATURES = (
    "timeframe",
    "side",
    "session",
    "prior_body_alignment",
    "fvg_before_entry",
    "exact_equal_liquidity",
    "raid_depth_range_bucket",
    "reclaim_latency_bucket",
    "cisd_progress_bucket",
    "protected_risk_range_bucket",
    "source_range_state_bucket",
    "body_fraction_bucket",
    "rejection_wick_bucket",
    "close_location_bucket",
    "h1_range_state",
    "h4_range_state",
    "d1_range_state",
    "h1_body_alignment",
    "h4_body_alignment",
    "d1_body_alignment",
    "m5_volatility_state",
    "m5_efficiency_state",
    "m5_displacement_alignment",
)


def _single(root: Path, name: str) -> Path:
    matches = list(root.rglob(name))
    if len(matches) != 1:
        raise ValueError(f"expected exactly one {name}, got {len(matches)}")
    return matches[0]


def _load_rank1(root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    path = _single(root, "turtle-soup-audjpy-specialist-observations-v2.jsonl")
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            if int(row["target_rank"]) == 1:
                rows.append(row)
    if not rows:
        raise ValueError("no AUDJPY rank-1 observations")
    return rows


def _stat(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    ordered = sorted(rows, key=lambda row: str(row["strategy_entry_at"]))
    values = [Decimal(str(row["STATIC_net_010_r"])) for row in ordered]
    gains = sum((value for value in values if value > 0), Decimal(0))
    losses = -sum((value for value in values if value < 0), Decimal(0))
    pf = None if losses == 0 else gains / losses
    equity = Decimal(0)
    peak = Decimal(0)
    max_dd = Decimal(0)
    losing = 0
    max_losing = 0
    for value in values:
        equity += value
        peak = max(peak, equity)
        max_dd = max(max_dd, peak - equity)
        if value < 0:
            losing += 1
            max_losing = max(max_losing, losing)
        else:
            losing = 0
    return {
        "n": len(values),
        "total_r": str(sum(values, Decimal(0))),
        "mean_r": str(sum(values, Decimal(0)) / Decimal(len(values))),
        "profit_factor": None if pf is None else str(pf),
        "max_drawdown_r": str(max_dd),
        "max_losing_streak": max_losing,
    }


def _quintiles(rows: Sequence[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    ordered = sorted(rows, key=lambda row: str(row["strategy_entry_at"]))
    n = len(ordered)
    cuts = [(i * n) // 5 for i in range(6)]
    parts = [ordered[cuts[i]:cuts[i + 1]] for i in range(5)]
    if any(not part for part in parts):
        raise ValueError("five non-empty quintiles required")
    return parts


def _profile(
    fields: tuple[str, ...],
    values: tuple[str, ...],
    rows: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    stat = _stat(rows)
    qstats = [_stat(part) for part in _quintiles(rows)]
    positive = sum(Decimal(str(item["total_r"])) > 0 for item in qstats)
    pf_raw = stat["profit_factor"]
    pf = None if pf_raw is None else Decimal(str(pf_raw))
    qualified = bool(
        len(rows) >= MIN_OBSERVATIONS
        and pf is not None
        and pf >= MIN_PF_010
        and Decimal(str(stat["total_r"])) > 0
        and positive == REQUIRED_POSITIVE_QUINTILES
    )
    return {
        "fields": list(fields),
        "values": list(values),
        "observations": len(rows),
        "aggregate": stat,
        "chronological_quintiles": qstats,
        "positive_quintiles": positive,
        "qualified": qualified,
    }


def _groups(
    rows: Sequence[dict[str, Any]],
    fields: tuple[str, ...],
) -> dict[tuple[str, ...], list[dict[str, Any]]]:
    result: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        result[tuple(str(row[field]) for field in fields)].append(row)
    return result


def _observation_key(row: dict[str, Any]) -> str:
    return "|".join(
        (
            str(row["master_episode_id"]),
            str(row["strategy_entry_at"]),
            str(row["target_rank"]),
            str(row["target_route"]),
        )
    )


def build(v2_root: Path, output: Path) -> dict[str, Any]:
    rows = _load_rank1(v2_root)
    candidates: list[dict[str, Any]] = []
    diagnostics: list[dict[str, Any]] = []

    feature_sets: list[tuple[str, ...]] = [(feature,) for feature in PRE_ENTRY_FEATURES]
    feature_sets.extend(
        (left, right)
        for index, left in enumerate(PRE_ENTRY_FEATURES)
        for right in PRE_ENTRY_FEATURES[index + 1:]
    )

    for fields in feature_sets:
        for values, members in _groups(rows, fields).items():
            if len(members) < MIN_OBSERVATIONS:
                continue
            profile = _profile(fields, values, members)
            diagnostics.append(dict(profile))
            if profile["qualified"]:
                profile["member_keys"] = sorted(_observation_key(row) for row in members)
                candidates.append(profile)

    # Remove exact duplicate member sets, keeping the simpler family first and
    # then the higher-PF description if complexity ties.
    dedup: dict[tuple[str, ...], dict[str, Any]] = {}
    for item in sorted(
        candidates,
        key=lambda x: (
            len(x["fields"]),
            -Decimal(str(x["aggregate"]["profit_factor"])),
            -int(x["observations"]),
            tuple(x["fields"]),
            tuple(x["values"]),
        ),
    ):
        key = tuple(item["member_keys"])
        dedup.setdefault(key, item)
    candidates = list(dedup.values())

    selected: list[dict[str, Any]] = []
    covered: set[str] = set()
    remaining = list(candidates)
    while remaining and len(selected) < MAX_FAMILIES:
        ranked: list[tuple[int, Decimal, int, dict[str, Any]]] = []
        for item in remaining:
            member_key_set: set[str] = set(item["member_keys"])
            incremental = len(member_key_set - covered)
            if incremental < MIN_INCREMENTAL_OBSERVATIONS:
                continue
            ranked.append(
                (
                    incremental,
                    Decimal(str(item["aggregate"]["profit_factor"])),
                    int(item["observations"]),
                    item,
                )
            )
        if not ranked:
            break
        _, _, _, winner = max(
            ranked,
            key=lambda x: (
                x[0],
                x[1],
                x[2],
                -len(x[3]["fields"]),
                tuple(x[3]["fields"]),
                tuple(x[3]["values"]),
            ),
        )
        winner_member_keys: set[str] = set(winner["member_keys"])
        family = {
            key: value
            for key, value in winner.items()
            if key != "member_keys"
        }
        family["family_id"] = f"AUDJPY_F{len(selected) + 1}"
        family["incremental_observations_at_selection"] = len(winner_member_keys - covered)
        selected.append(family)
        covered.update(winner_member_keys)
        remaining = [item for item in remaining if item is not winner]

    def diagnostic_key(item: dict[str, Any]) -> tuple[int, Decimal, int]:
        pf_raw = item["aggregate"]["profit_factor"]
        pf = Decimal(0) if pf_raw is None else Decimal(str(pf_raw))
        return (
            int(item["positive_quintiles"]),
            pf,
            int(item["observations"]),
        )

    diagnostic_frontier = sorted(
        diagnostics,
        key=diagnostic_key,
        reverse=True,
    )[:50]

    output.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": "qore.turtle_soup_audjpy.r33_rank1_subfamily_discovery.v1",
        "identity": IDENTITY,
        "source": {
            "cognitive_memory": "TURTLE_SOUP_AUDJPY_SPECIALIST_COGNITIVE_MEMORY_V2",
            "rank": 1,
            "lifecycle": "STATIC",
            "economic_field": "STATIC_net_010_r",
            "observations": len(rows),
        },
        "candidate_contract": {
            "features_are_pre_entry_only": True,
            "calendar_fields_forbidden": True,
            "target_route_not_a_family_feature": True,
            "target_rank_fixed_to_one": True,
            "one_or_two_categorical_predicates_only": True,
            "minimum_observations": MIN_OBSERVATIONS,
            "minimum_profit_factor_010": str(MIN_PF_010),
            "required_positive_chronological_quintiles": REQUIRED_POSITIVE_QUINTILES,
            "maximum_selected_families": MAX_FAMILIES,
            "minimum_incremental_observations": MIN_INCREMENTAL_OBSERVATIONS,
            "selection_after_qualification": "GREEDY_INCREMENTAL_COVERAGE_THEN_PF",
        },
        "evaluated_family_count": len(diagnostics),
        "diagnostic_positive_quintile_counts": {
            str(value): sum(
                int(item["positive_quintiles"]) == value
                for item in diagnostics
            )
            for value in range(6)
        },
        "diagnostic_frontier": diagnostic_frontier,
        "qualified_candidate_count": len(candidates),
        "selected_families": selected,
        "selected_family_count": len(selected),
        "selected_union_observations": len(covered),
        "governance": {
            "consumed_development_only": True,
            "fresh_holdout_consumed": False,
            "candidate_promoted": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        },
    }
    (output / "r33-rank1-subfamily-discovery-report.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n"
    )
    (output / "r33-rank1-subfamily-freeze.json").write_text(
        json.dumps(
            {
                "identity": "TURTLE_SOUP_AUDJPY_R33_SUBFAMILY_FREEZE_V1",
                "status": "FROZEN_FOR_2Y_ENSEMBLE_REPLAY",
                "families": selected,
                "fresh_holdout_status": "SEALED_UNTOUCHED",
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    return payload


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("usage: module COGNITIVE_V2_ROOT OUTPUT_DIR")
    print(json.dumps(build(Path(sys.argv[1]), Path(sys.argv[2])), sort_keys=True))


if __name__ == "__main__":
    main()
