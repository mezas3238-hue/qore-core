"""VT08 Index CIBO 2Y tuning lab — Round 3 anchor-complete.

Round 3 corrects a tuning-lab omission: frozen V7 executes at NY anchors
(22, 2, 6, 10), while Rounds 1-2 searched only (2, 6, 10).

No V7 economic rule changes. Provider-available M15 reconstruction from Round 2
is retained without interpolation or synthetic prices.

The search reports the best PF/DD/stability configuration at multiple activity
floors so activity cannot be improved merely by hiding low-frequency results.
The 2016-09-18 .. 2018-09-15 interval is already consumed tuning evidence.
"""

from __future__ import annotations

import argparse
import itertools
import json
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

from qore.infrastructure.trader_lab import vt08_index_cibo_2y_tuning_round1 as r1
from qore.infrastructure.trader_lab import vt08_index_cibo_2y_tuning_round2 as r2
from qore.infrastructure.trader_lab import vt08_index_v7_ttrades_source_corrected as v7

SCHEMA = "qore.trader_lab.vt08_index_cibo_2y_tuning_round3.v1"
IDENTITY = "VT08_INDEX_CIBO_2Y_TUNING_ROUND3_ANCHOR_COMPLETE"
ANCHORS = tuple(v7.EXECUTABLE_H4_ANCHORS_NY)
ACTIVITY_FLOORS = (100, 200, 300, 400, 500, 600, 700, 800)
PF_GOAL = Decimal("1.15")
DD_GOAL = Decimal("12")


def _anchor_sets() -> tuple[tuple[int, ...], ...]:
    return tuple(
        subset
        for size in range(1, len(ANCHORS) + 1)
        for subset in itertools.combinations(ANCHORS, size)
    )


def _rank(candidate: dict[str, Any]) -> tuple[int, int, Decimal, Decimal, Decimal]:
    primary = cast(dict[str, Any], candidate["primary_stress"])
    secondary = cast(dict[str, Any], candidate["secondary_stress"])
    stable = int(
        int(candidate["positive_halves"]) == 2
        and int(candidate["positive_quarters"]) >= 6
    )
    stress_pf_pass = int(Decimal(str(secondary["profit_factor"])) >= Decimal("1"))
    return (
        stable,
        stress_pf_pass,
        Decimal(str(primary["profit_factor"])),
        -Decimal(str(primary["max_drawdown_r"])),
        Decimal(str(primary["mean_r"])),
    )


def _candidate_search(
    rows: tuple[r1.TradeSurfaceRow, ...],
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for targets in r1._target_maps():
        for anchors in _anchor_sets():
            for sides in r1._side_sets():
                report = r1._candidate_report(
                    rows,
                    targets=targets,
                    anchors=anchors,
                    sides=sides,
                )
                sample = int(cast(dict[str, Any], report["primary_stress"])["sample"])
                if sample < 100:
                    continue
                candidates.append(report)
    candidates.sort(key=_rank, reverse=True)
    return candidates


def _tier_best(
    candidates: list[dict[str, Any]],
) -> dict[str, dict[str, Any] | None]:
    result: dict[str, dict[str, Any] | None] = {}
    for floor in ACTIVITY_FLOORS:
        eligible = [
            candidate
            for candidate in candidates
            if int(cast(dict[str, Any], candidate["primary_stress"])["sample"]) >= floor
        ]
        eligible.sort(key=_rank, reverse=True)
        result[str(floor)] = eligible[0] if eligible else None
    return result


def _goal(candidate: dict[str, Any]) -> bool:
    primary = cast(dict[str, Any], candidate["primary_stress"])
    secondary = cast(dict[str, Any], candidate["secondary_stress"])
    return (
        int(primary["sample"]) >= 600
        and Decimal(str(primary["profit_factor"])) >= PF_GOAL
        and Decimal(str(primary["max_drawdown_r"])) <= DD_GOAL
        and Decimal(str(secondary["profit_factor"])) >= Decimal("1.05")
        and Decimal(str(secondary["max_drawdown_r"])) <= Decimal("15")
        and int(candidate["positive_halves"]) == 2
        and int(candidate["positive_quarters"]) >= 6
    )


def _benchmark(
    rows: tuple[r1.TradeSurfaceRow, ...],
    *,
    name: str,
    anchors: tuple[int, ...],
    sides: tuple[str, ...],
    target: str,
) -> dict[str, Any]:
    targets: dict[str, str | None] = {
        symbol: target for symbol in r1.SYMBOLS
    }
    result = r1._candidate_report(
        rows,
        targets=targets,
        anchors=anchors,
        sides=sides,
    )
    result["benchmark_name"] = name
    return result


def build_report(
    *,
    nas100_root: Path,
    sp500_root: Path,
    us30_root: Path,
) -> dict[str, Any]:
    roots = {
        "NAS100": nas100_root,
        "SP500": sp500_root,
        "US30": us30_root,
    }
    provenance: dict[str, Any] = {}
    market_diagnostics: dict[str, Any] = {}
    all_rows: list[r1.TradeSurfaceRow] = []
    anchor_counts: dict[str, int] = {str(anchor): 0 for anchor in ANCHORS}
    market_anchor_counts: dict[str, dict[str, int]] = {}

    for symbol in r1.SYMBOLS:
        bars, source = r2._load_cibo_m15_available(roots[symbol], symbol=symbol)
        rows, diagnostics = r1._surface_rows(symbol=symbol, bars=bars)
        provenance[symbol] = source
        market_diagnostics[symbol] = diagnostics
        market_anchor_counts[symbol] = {str(anchor): 0 for anchor in ANCHORS}
        for row in rows:
            anchor_counts[str(row.anchor)] = anchor_counts.get(str(row.anchor), 0) + 1
            market_anchor_counts[symbol][str(row.anchor)] = (
                market_anchor_counts[symbol].get(str(row.anchor), 0) + 1
            )
        all_rows.extend(rows)

    ordered = tuple(sorted(all_rows, key=lambda row: (row.signal_at, row.symbol)))
    unknown_anchor_rows = [
        row for row in ordered if row.anchor not in ANCHORS
    ]
    if unknown_anchor_rows:
        raise ValueError(
            f"surface contains {len(unknown_anchor_rows)} non-V7 executable anchors"
        )

    candidates = _candidate_search(ordered)
    goals = [candidate for candidate in candidates if _goal(candidate)]
    goals.sort(key=_rank, reverse=True)
    tier_best = _tier_best(candidates)

    # Prefer the highest activity floor with a candidate that meets the economic
    # goal. If none meets it, expose the ranked >=600 candidate when available,
    # otherwise expose the highest-activity ranked candidate for density
    # diagnosis.
    best: dict[str, Any] | None = None
    for floor in reversed(ACTIVITY_FLOORS):
        candidate = tier_best[str(floor)]
        if candidate is not None and _goal(candidate):
            best = candidate
            break
    if best is None:
        best = tier_best["600"] or (candidates[0] if candidates else None)

    benchmarks = [
        _benchmark(
            ordered,
            name="V7_ALL_EXECUTABLE_ANCHORS_BOTH_SIDES_TARGET_2R",
            anchors=ANCHORS,
            sides=("long", "short"),
            target="2.0",
        ),
        _benchmark(
            ordered,
            name="ALL_EXECUTABLE_ANCHORS_BOTH_SIDES_TARGET_1_5R",
            anchors=ANCHORS,
            sides=("long", "short"),
            target="1.5",
        ),
        _benchmark(
            ordered,
            name="ALL_EXECUTABLE_ANCHORS_LONG_TARGET_1_5R",
            anchors=ANCHORS,
            sides=("long",),
            target="1.5",
        ),
        _benchmark(
            ordered,
            name="ANCHOR_22_BOTH_SIDES_TARGET_1_5R",
            anchors=(22,),
            sides=("long", "short"),
            target="1.5",
        ),
        _benchmark(
            ordered,
            name="ANCHOR_22_LONG_TARGET_1_5R",
            anchors=(22,),
            sides=("long",),
            target="1.5",
        ),
    ]

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "window": {
            "window_id": r1.WINDOW_ID,
            "start_date": r1.START_DATE.isoformat(),
            "end_date_exclusive": r1.END_DATE_EXCLUSIVE.isoformat(),
            "status": "CONSUMED_TUNING",
            "fresh_certification_holdout": False,
        },
        "strategy": {
            "base_candidate_id": v7.CANDIDATE_ID,
            "base_rule_fingerprint": v7.RULE_FINGERPRINT,
            "v7_executable_anchors": list(v7.EXECUTABLE_H4_ANCHORS_NY),
            "tuner_executable_anchors": list(ANCHORS),
            "v7_setup_identity_changed": False,
            "stop_changed": False,
            "lifecycle_changed": False,
            "target_depth_is_tuning_dimension": True,
        },
        "reconstruction": {
            "policy": "PROVIDER_AVAILABLE_M15_NO_INTERPOLATION",
            "synthetic_prices": False,
            "interpolation": False,
        },
        "provenance": provenance,
        "market_diagnostics": market_diagnostics,
        "surface_trade_count": len(ordered),
        "anchor_counts": anchor_counts,
        "market_anchor_counts": market_anchor_counts,
        "candidate_count": len(candidates),
        "goal_candidate_count": len(goals),
        "activity_floors": list(ACTIVITY_FLOORS),
        "best_by_activity_floor": tier_best,
        "best_candidate": best,
        "top_goal_candidates": goals[:25],
        "top_25": candidates[:25],
        "benchmarks": benchmarks,
        "search_contract": {
            "minimum_candidate_sample": 100,
            "preferred_minimum_sample": 600,
            "profit_factor_primary_goal": format(PF_GOAL, "f"),
            "max_drawdown_primary_goal_r": format(DD_GOAL, "f"),
            "profit_factor_secondary_floor": "1.05",
            "max_drawdown_secondary_goal_r": "15",
            "positive_halves_required": 2,
            "minimum_positive_quarters": 6,
            "activity_is_not_optimized_by_suppressing_valid_v7_anchor_22": True,
        },
        "governance": {
            "research_only": True,
            "tuning_window_consumed": True,
            "fresh_holdout_claim": False,
            "rule_promotion_automatic": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--nas100-root", type=Path, required=True)
    parser.add_argument("--sp500-root", type=Path, required=True)
    parser.add_argument("--us30-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    report = build_report(
        nas100_root=args.nas100_root,
        sp500_root=args.sp500_root,
        us30_root=args.us30_root,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    best = cast(dict[str, Any] | None, report["best_candidate"])
    print(
        json.dumps(
            {
                "identity": IDENTITY,
                "surface_trade_count": report["surface_trade_count"],
                "anchor_counts": report["anchor_counts"],
                "candidate_count": report["candidate_count"],
                "goal_candidate_count": report["goal_candidate_count"],
                "best_candidate_id": best["candidate_id"] if best else None,
                "best_primary": best["primary_stress"] if best else None,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
