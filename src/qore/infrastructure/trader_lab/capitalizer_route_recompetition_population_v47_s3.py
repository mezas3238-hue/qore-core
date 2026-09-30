"""V47-S3 empirical route population builder.

The recompetition law is frozen by PR #623 comment 5902060715. Empirical
execution is impossible until an authoritative FTM source run and SHA are
explicitly bound by the caller/workflow.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from dataclasses import asdict
from pathlib import Path

from qore.infrastructure.trader_lab import (
    capitalizer_route_recompetition_v47_s3 as s3,
)
from qore.infrastructure.trader_lab import (
    capitalizer_source_strategy_ftm_isolation_v47_s2 as ftm,
)
from qore.infrastructure.trader_lab import (
    capitalizer_source_strategy_isolation_v47_s2 as fractal,
)

IDENTITY = "QORE_CAPITALIZER_V47_S3_ROUTE_RECOMPETITION"
PREDECLARATION_COMMENT_ID = 5902060715
FRACTAL_RUN_ID = 36642644284
FRACTAL_SHA = "ff6c9745690dde76520aecf608e44401622a1074"
SHA40 = re.compile(r"^[0-9a-f]{40}$")


def _load_fractal(root: Path) -> tuple[s3.RouteCandidate, ...]:
    rows: list[s3.RouteCandidate] = []
    seen_paths: set[Path] = set()
    for path in sorted(root.rglob("capitalizer-s2a-*-fills.jsonl")):
        if path in seen_paths:
            continue
        seen_paths.add(path)
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            raw = json.loads(line)
            if not isinstance(raw, dict):
                raise ValueError("S3 FRACTAL row must be object")
            row = fractal.S2AdmittedFillRow(**raw)
            rows.append(s3.from_fractal(row))
    return s3.recompact_exact_duplicates(tuple(rows))


def _load_ftm(root: Path) -> tuple[s3.RouteCandidate, ...]:
    rows: list[s3.RouteCandidate] = []
    seen: set[tuple[str, str, str, str, str]] = set()
    for path in sorted(root.rglob("capitalizer-ftm-s2-*-fills.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            raw = json.loads(line)
            if not isinstance(raw, dict):
                raise ValueError("S3 FTM row must be object")
            row = ftm.FTMAdmittedFillRow(**raw)
            candidate = s3.from_ftm(row)
            key = (
                candidate.source_identity,
                candidate.period,
                candidate.symbol,
                candidate.route,
                candidate.entry_at,
            )
            if key in seen:
                continue
            seen.add(key)
            rows.append(candidate)
    return s3.recompact_exact_duplicates(tuple(rows))


def _validate_source_binding(ftm_run_id: int, ftm_sha: str) -> None:
    if ftm_run_id <= 0:
        raise ValueError("S3 requires positive authoritative FTM run id")
    if SHA40.fullmatch(ftm_sha) is None:
        raise ValueError("S3 requires authoritative 40-char lowercase FTM SHA")


def _collision_key(row: s3.RouteCandidate) -> tuple[str, str, str, str]:
    return row.period, row.session, row.operating_date, row.entry_at


def _same_symbol_time_key(
    row: s3.RouteCandidate,
) -> tuple[str, str, str, str, str]:
    return (
        row.period,
        row.session,
        row.operating_date,
        row.symbol,
        row.entry_at,
    )


def build_population(
    fractal_root: Path,
    ftm_root: Path,
    *,
    ftm_run_id: int,
    ftm_sha: str,
    output: Path,
) -> dict[str, object]:
    _validate_source_binding(ftm_run_id, ftm_sha)
    fractal_rows = _load_fractal(fractal_root)
    ftm_rows = _load_ftm(ftm_root)
    entrants = (*fractal_rows, *ftm_rows)
    result = s3.select_max3_across_routes(tuple(entrants))

    before = s3.entrant_counts_by_route(result.entrants)
    after = s3.selected_counts_by_route(result)
    collision_groups = Counter(_collision_key(row) for row in result.entrants)
    same_symbol_time = Counter(
        _same_symbol_time_key(row) for row in result.entrants
    )

    output.mkdir(parents=True, exist_ok=True)
    with (output / "capitalizer-v47-s3-selected-population.jsonl").open(
        "w",
        encoding="utf-8",
    ) as handle:
        for row in result.selected:
            handle.write(json.dumps(asdict(row), sort_keys=True) + "\n")

    periods: dict[str, object] = {}
    for period in ("reserved", "validation", "development"):
        period_entrants = tuple(
            row for row in result.entrants if row.period == period
        )
        period_selected = tuple(
            row for row in result.selected if row.period == period
        )
        periods[period] = {
            "entrant_count": len(period_entrants),
            "selected_count": len(period_selected),
            "entrants_by_route": s3.entrant_counts_by_route(period_entrants),
            "selected_by_route": s3.entrant_counts_by_route(period_selected),
        }

    payload: dict[str, object] = {
        "identity": IDENTITY,
        "predeclaration_comment_id": PREDECLARATION_COMMENT_ID,
        "fractal_source": {
            "run_id": FRACTAL_RUN_ID,
            "sha": FRACTAL_SHA,
            "identity": fractal.IDENTITY,
        },
        "ftm_source": {
            "run_id": ftm_run_id,
            "sha": ftm_sha,
            "identity": ftm.IDENTITY,
        },
        "entrants": len(result.entrants),
        "selected": len(result.selected),
        "entrants_by_route": before,
        "selected_by_route": after,
        "periods": periods,
        "max3_ceiling": result.max3_ceiling,
        "max3_collision_groups": sum(
            count > result.max3_ceiling for count in collision_groups.values()
        ),
        "max3_displaced_candidates": len(result.entrants) - len(result.selected),
        "same_symbol_time_cross_route_collision_groups": sum(
            count > 1 for count in same_symbol_time.values()
        ),
        "outcome_used_for_selection": result.outcome_used_for_selection,
        "route_priority_used": result.route_priority_used,
        "economics_calculated": False,
        "fresh_holdout_opened": False,
        "trader_certified": False,
        "next_phase": "S3_POPULATION_READY_FOR_FROZEN_GROSS_ECONOMICS",
    }
    (output / "capitalizer-v47-s3-route-recompetition.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, sort_keys=True))
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("fractal_root", type=Path)
    parser.add_argument("ftm_root", type=Path)
    parser.add_argument("--ftm-run-id", type=int, required=True)
    parser.add_argument("--ftm-sha", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    build_population(
        args.fractal_root,
        args.ftm_root,
        ftm_run_id=args.ftm_run_id,
        ftm_sha=args.ftm_sha,
        output=args.output,
    )


if __name__ == "__main__":
    main()
