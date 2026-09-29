"""Outcome-blind cross-market event-time M1 coverage census.

This census is a provider-availability diagnostic only. It asks whether every
already-reconciled Capitalizer entrant timestamp can be causally paired with the
latest completed M1 bar from one peer market. It does not build a predictive
representation, read terminal outcomes for selection, run STOP/TARGET
separability, or touch the sealed Fresh Holdout.

The result is deliberately descriptive: quote/bar-age thresholds are reported
as coverage statistics, never used as post-observation admission gates.
"""

from __future__ import annotations

import argparse
import json
from bisect import bisect_right
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

from qore.infrastructure.trader_lab import (
    capitalizer_preentry_native_m1_geometry_separability_v38 as v38,
)
from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    iter_cibo_m1,
)

IDENTITY = "QORE_CAPITALIZER_CROSS_MARKET_EVENT_TIME_M1_COVERAGE_CENSUS_V1"
MATRIX_IDENTITY = (
    "QORE_CAPITALIZER_CROSS_MARKET_EVENT_TIME_M1_COVERAGE_MATRIX_V1"
)
SLUGS = ("development", "validation", "reserved")
DESCRIPTIVE_AGE_SECONDS = (60, 300, 900)
EXPECTED_PERIOD_COUNTS = {
    "development": 948,
    "validation": 1034,
    "reserved": 1088,
}


@dataclass(frozen=True, slots=True)
class AgeSummary:
    entrant_count: int
    prior_bar_count: int
    missing_prior_bar_count: int
    p50_age_seconds: int | None
    p95_age_seconds: int | None
    p99_age_seconds: int | None
    max_age_seconds: int | None
    within_60s: int
    within_300s: int
    within_900s: int
    all_entrants_have_prior_bar: bool
    future_bar_used: bool = False
    outcome_used_for_coverage: bool = False
    exit_used_for_coverage: bool = False


def _aware(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("cross-market census requires timezone-aware timestamps")
    return parsed


def _nearest_rank(sorted_values: tuple[int, ...], percentile: int) -> int | None:
    if not sorted_values:
        return None
    if percentile <= 0 or percentile > 100:
        raise ValueError("percentile must be in 1..100")
    rank = (percentile * len(sorted_values) + 99) // 100
    return sorted_values[max(0, rank - 1)]


def summarize_event_time_ages(
    *,
    entrant_times: tuple[datetime, ...],
    completed_bar_times: tuple[datetime, ...],
) -> AgeSummary:
    """Summarize causal latest-completed-bar age without reading bar prices."""

    if tuple(sorted(entrant_times)) != entrant_times:
        raise ValueError("entrant_times must be sorted")
    if tuple(sorted(completed_bar_times)) != completed_bar_times:
        raise ValueError("completed_bar_times must be sorted")
    if len(set(completed_bar_times)) != len(completed_bar_times):
        raise ValueError("completed_bar_times must be unique")

    ages: list[int] = []
    for entry_at in entrant_times:
        index = bisect_right(completed_bar_times, entry_at) - 1
        if index < 0:
            continue
        completed_at = completed_bar_times[index]
        if completed_at > entry_at:
            raise ValueError("cross-market census attempted future-bar use")
        age = int((entry_at - completed_at).total_seconds())
        if age < 0:
            raise ValueError("cross-market census produced negative bar age")
        ages.append(age)

    ordered = tuple(sorted(ages))
    entrant_count = len(entrant_times)
    prior_count = len(ordered)
    return AgeSummary(
        entrant_count=entrant_count,
        prior_bar_count=prior_count,
        missing_prior_bar_count=entrant_count - prior_count,
        p50_age_seconds=_nearest_rank(ordered, 50),
        p95_age_seconds=_nearest_rank(ordered, 95),
        p99_age_seconds=_nearest_rank(ordered, 99),
        max_age_seconds=None if not ordered else ordered[-1],
        within_60s=sum(age <= 60 for age in ordered),
        within_300s=sum(age <= 300 for age in ordered),
        within_900s=sum(age <= 900 for age in ordered),
        all_entrants_have_prior_bar=prior_count == entrant_count,
    )


def _completed_bar_times(m1_root: Path, *, peer_symbol: str) -> tuple[datetime, ...]:
    times: list[datetime] = []
    for bar in iter_cibo_m1(m1_root):
        if bar.symbol != peer_symbol:
            raise ValueError("cross-market census M1 artifact symbol mismatch")
        times.append(bar.closed_at)
    if not times:
        raise ValueError("cross-market census M1 source is empty")
    result = tuple(times)
    if tuple(sorted(result)) != result or len(set(result)) != len(result):
        raise ValueError("cross-market census M1 chronology drift")
    return result


def census_peer_market(
    *,
    peer_symbol: str,
    m1_root: Path,
    selected_geometry_root: Path,
    output: Path,
) -> dict[str, object]:
    completed = _completed_bar_times(m1_root, peer_symbol=peer_symbol)
    period_rows: list[dict[str, object]] = []

    for slug in SLUGS:
        selected = v38._load_period_geometry(selected_geometry_root, slug=slug)
        entrant_times = tuple(
            sorted(_aware(row.entry_at) for row in selected.values())
        )
        expected = EXPECTED_PERIOD_COUNTS[slug]
        if len(entrant_times) != expected:
            raise ValueError(
                f"cross-market census {slug} entrant count drift: "
                f"{len(entrant_times)} != {expected}"
            )
        summary = summarize_event_time_ages(
            entrant_times=entrant_times,
            completed_bar_times=completed,
        )
        period_rows.append(
            {
                "slug": slug,
                "expected_entrants": expected,
                **asdict(summary),
            }
        )

    report: dict[str, object] = {
        "identity": IDENTITY,
        "peer_symbol": peer_symbol,
        "population_source": "V38_RECONCILED_SELECTED_ENTRANTS",
        "periods": period_rows,
        "descriptive_age_thresholds_seconds": list(DESCRIPTIVE_AGE_SECONDS),
        "thresholds_are_admission_gates": False,
        "bar_prices_used_for_coverage_decision": False,
        "terminal_outcomes_used_for_coverage_decision": False,
        "stop_target_labels_evaluated": False,
        "separability_run": False,
        "policy_economics_run": False,
        "fresh_holdout_opened": False,
        "runtime_policy_candidate": False,
        "trader_certified": False,
    }
    output.mkdir(parents=True, exist_ok=True)
    path = output / (
        "capitalizer-cross-market-event-time-m1-coverage-"
        f"{peer_symbol.lower()}-v1.json"
    )
    path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report


def build_matrix(root: Path, output: Path) -> dict[str, object]:
    paths = sorted(
        root.rglob("capitalizer-cross-market-event-time-m1-coverage-*-v1.json")
    )
    if len(paths) != 9:
        raise ValueError(f"cross-market coverage matrix requires 9 reports, got {len(paths)}")
    reports = [json.loads(path.read_text(encoding="utf-8")) for path in paths]
    symbols = {str(report["peer_symbol"]) for report in reports}
    if len(symbols) != 9:
        raise ValueError("cross-market coverage matrix peer-symbol duplication")

    rows: list[dict[str, object]] = []
    for report in reports:
        if report["identity"] != IDENTITY:
            raise ValueError("cross-market coverage report identity mismatch")
        for period in report["periods"]:
            rows.append(
                {
                    "peer_symbol": report["peer_symbol"],
                    **period,
                }
            )

    result: dict[str, object] = {
        "identity": MATRIX_IDENTITY,
        "peer_market_count": len(reports),
        "period_market_rows": len(rows),
        "all_rows_have_prior_bar": all(
            bool(row["all_entrants_have_prior_bar"]) for row in rows
        ),
        "max_observed_age_seconds": max(
            int(row["max_age_seconds"])
            for row in rows
            if row["max_age_seconds"] is not None
        ),
        "rows": sorted(
            rows,
            key=lambda row: (str(row["slug"]), str(row["peer_symbol"])),
        ),
        "descriptive_only": True,
        "representation_frozen": False,
        "labels_opened_for_this_census": False,
        "separability_run": False,
        "fresh_holdout_opened": False,
        "runtime_policy_candidate": False,
        "trader_certified": False,
        "next_phase": "PREDECLARE_CROSS_MARKET_STATE_ONLY_IF_COVERAGE_CONTRACT_IS_VIABLE",
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "capitalizer-cross-market-event-time-m1-coverage-matrix-v1.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    market = sub.add_parser("market")
    market.add_argument("--peer-symbol", required=True)
    market.add_argument("--m1-root", type=Path, required=True)
    market.add_argument("--selected-geometry-root", type=Path, required=True)
    market.add_argument("--output", type=Path, required=True)

    matrix = sub.add_parser("matrix")
    matrix.add_argument("--root", type=Path, required=True)
    matrix.add_argument("--output", type=Path, required=True)

    args = parser.parse_args()
    if args.command == "market":
        report = census_peer_market(
            peer_symbol=args.peer_symbol,
            m1_root=args.m1_root,
            selected_geometry_root=args.selected_geometry_root,
            output=args.output,
        )
    else:
        report = build_matrix(args.root, args.output)
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
