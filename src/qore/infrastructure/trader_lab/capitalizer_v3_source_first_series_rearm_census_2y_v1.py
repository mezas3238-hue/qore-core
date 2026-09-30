"""Outcome-free census of SOURCE_FIRST with causal post-sweep series rearm.

The V3_ONLY causal-series atlas established, without outcomes, that 85/87 V3-only
confirmations arise from a new opposing M3 series after the sweep while the
original SOURCE_FIRST boundary remains anchored to an older post-sweep series.

This census tests one structural semantic across all 8,099 frozen closebacks:

SOURCE_FIRST_SERIES_REARM
- observation begins strictly after the real sweep;
- first opposing M3 series establishes boundary at the opening of its first candle;
- boundary persists through subsequent non-opposing bars;
- when a new, distinct opposing M3 series begins after at least one non-opposing
  bar, boundary rearms to the opening of the first candle of that new series;
- all V3 non-CISD conditions remain unchanged;
- no pre-sweep series can establish a boundary.

No outcomes are read and no trading rule is promoted here.
"""

from __future__ import annotations

import argparse
import bisect
import json
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    capitalizer_v3_cisd_boundary_semantics_census_2y_v1 as semantics,
)
from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    iter_cibo_m1,
)
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_strict_htf_gate_1y_v1 import (
    Pivot,
    TFBar,
    _aggregate_tf,
    _pivots,
)

IDENTITY = "QORE_CAPITALIZER_V3_SOURCE_FIRST_SERIES_REARM_CENSUS_2Y_V1"
MATRIX_IDENTITY = (
    "QORE_CAPITALIZER_NINE_MARKET_V3_SOURCE_FIRST_SERIES_REARM_CENSUS_2Y_V1"
)
EXPECTED_CLOSEBACKS = 8099
EXPECTED_SOURCE_FIRST_MSS = 2692
EXPECTED_CURRENT_V3_MSS = 1254
EXPECTED_V3_ONLY = 87

REARM = "SOURCE_FIRST_SERIES_REARM"


@dataclass(frozen=True, slots=True)
class SeriesRearmRow:
    symbol: str
    session: str
    operating_date: str
    side: str
    sweep_at: str
    closeback_at: str
    h1_deadline: str
    m5_state: str
    current_v3_mss_at: str | None
    source_first_mss_at: str | None
    rearm_mss_at: str | None
    rearm_boundary: str | None
    rearm_boundary_started_at: str | None
    opposing_series_seen: int
    boundary_rearms_before_confirmation: int
    rearm_relation_vs_source_first: str
    rearm_relation_vs_v3: str
    frozen_source_relation_vs_v3: str
    outcome_used_for_admission: bool = False


def _load_semantics(root: Path) -> tuple[dict[str, Any], ...]:
    paths = sorted(
        root.rglob(
            "capitalizer-*-v3-cisd-boundary-semantics-census-2y-v1-rows.jsonl"
        )
    )
    if len(paths) != 1:
        raise ValueError("series-rearm census requires one semantics ledger")
    rows: list[dict[str, Any]] = []
    with paths[0].open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            raw = json.loads(line)
            if not isinstance(raw, dict):
                raise ValueError("semantics row must be object")
            rows.append(raw)
    return tuple(rows)


def _rearm_event(
    bars: tuple[TFBar, ...],
    closes: tuple[datetime, ...],
    pivots: tuple[Pivot, ...],
    *,
    sweep_at: datetime,
    after: datetime,
    before: datetime,
    side: CapitalizerSide,
) -> tuple[datetime | None, Any | None, datetime | None, int]:
    start = bisect.bisect_right(closes, sweep_at)
    end = bisect.bisect_right(closes, before)

    boundary: Any | None = None
    boundary_started: datetime | None = None
    in_opposing_series = False
    series_seen = 0

    for index in range(start, end):
        bar = bars[index]
        if semantics._opposing(bar, side):
            if not in_opposing_series:
                boundary = bar.source.open
                boundary_started = bar.closed_at
                series_seen += 1
            in_opposing_series = True
            continue

        in_opposing_series = False
        if bar.closed_at <= after:
            continue
        if not semantics._non_cisd_ready(
            bars,
            pivots,
            index=index,
            side=side,
        ):
            continue
        if (
            boundary is not None
            and semantics._breaks(
                close=bar.source.close,
                boundary=boundary,
                side=side,
            )
        ):
            return (
                bar.closed_at,
                boundary,
                boundary_started,
                series_seen,
            )

    return None, boundary, boundary_started, series_seen


def _relation(
    alternative: datetime | None,
    reference: datetime | None,
) -> str:
    if alternative is None and reference is None:
        return "BOTH_MISSING"
    if alternative is not None and reference is None:
        return "RECOVERS_MISSING"
    if alternative is None and reference is not None:
        return "LOSES_REFERENCE"
    if alternative == reference:
        return "SAME_CONFIRMATION"
    if (
        alternative is not None
        and reference is not None
        and alternative < reference
    ):
        return "PREEMPTS_REFERENCE"
    return "LATER_THAN_REFERENCE"


def _build_row(
    raw: dict[str, Any],
    *,
    m3: tuple[TFBar, ...],
    closes: tuple[datetime, ...],
    pivots: tuple[Pivot, ...],
) -> SeriesRearmRow:
    side = CapitalizerSide(str(raw["side"]))
    sweep_at = datetime.fromisoformat(str(raw["sweep_at"]))
    closeback_at = datetime.fromisoformat(str(raw["closeback_at"]))
    deadline = datetime.fromisoformat(str(raw["h1_deadline"]))
    current = (
        None
        if raw.get("current_v3_mss_at") is None
        else datetime.fromisoformat(str(raw["current_v3_mss_at"]))
    )
    source = (
        None
        if raw.get("source_first_mss_at") is None
        else datetime.fromisoformat(str(raw["source_first_mss_at"]))
    )

    rearm_at, boundary, boundary_started, series_seen = _rearm_event(
        m3,
        closes,
        pivots,
        sweep_at=sweep_at,
        after=closeback_at,
        before=deadline,
        side=side,
    )

    return SeriesRearmRow(
        symbol=str(raw["symbol"]),
        session=str(raw["session"]),
        operating_date=str(raw["operating_date"]),
        side=side.value,
        sweep_at=sweep_at.isoformat(),
        closeback_at=closeback_at.isoformat(),
        h1_deadline=deadline.isoformat(),
        m5_state=str(raw["m5_state"]),
        current_v3_mss_at=None if current is None else current.isoformat(),
        source_first_mss_at=None if source is None else source.isoformat(),
        rearm_mss_at=None if rearm_at is None else rearm_at.isoformat(),
        rearm_boundary=None if boundary is None else str(boundary),
        rearm_boundary_started_at=(
            None if boundary_started is None else boundary_started.isoformat()
        ),
        opposing_series_seen=series_seen,
        boundary_rearms_before_confirmation=max(0, series_seen - 1),
        rearm_relation_vs_source_first=_relation(rearm_at, source),
        rearm_relation_vs_v3=_relation(rearm_at, current),
        frozen_source_relation_vs_v3=str(raw["source_first_relation_vs_v3"]),
    )


def build_market_report(
    semantics_root: Path,
    m1_root: Path,
) -> tuple[dict[str, Any], tuple[SeriesRearmRow, ...]]:
    frozen = _load_semantics(semantics_root)
    if not frozen:
        raise ValueError("series-rearm census found no semantics rows")

    first = min(datetime.fromisoformat(str(row["sweep_at"])) for row in frozen)
    last = max(datetime.fromisoformat(str(row["h1_deadline"])) for row in frozen)
    native = tuple(
        bar
        for bar in iter_cibo_m1(m1_root)
        if first - timedelta(days=2)
        <= bar.opened_at
        <= last + timedelta(minutes=3)
    )
    if not native:
        raise ValueError("series-rearm census found no native M1")
    symbol = native[0].symbol
    if any(bar.symbol != symbol for bar in native):
        raise ValueError("series-rearm census requires one symbol")
    if any(str(row["symbol"]) != symbol for row in frozen):
        raise ValueError("series-rearm semantics/M1 symbol mismatch")

    m3 = _aggregate_tf(native, minutes=3)
    closes = tuple(bar.closed_at for bar in m3)
    pivots = _pivots(m3)

    rows = tuple(
        sorted(
            (
                _build_row(
                    raw,
                    m3=m3,
                    closes=closes,
                    pivots=pivots,
                )
                for raw in frozen
            ),
            key=lambda item: item.closeback_at,
        )
    )
    source_count = sum(item.source_first_mss_at is not None for item in rows)
    current_count = sum(item.current_v3_mss_at is not None for item in rows)
    rearm_count = sum(item.rearm_mss_at is not None for item in rows)

    relation_source = Counter(item.rearm_relation_vs_source_first for item in rows)
    relation_v3 = Counter(item.rearm_relation_vs_v3 for item in rows)
    rearm_buckets = Counter(
        (
            "0"
            if item.boundary_rearms_before_confirmation == 0
            else "1"
            if item.boundary_rearms_before_confirmation == 1
            else "2"
            if item.boundary_rearms_before_confirmation == 2
            else "3+"
        )
        for item in rows
        if item.rearm_mss_at is not None
    )

    v3_only = tuple(
        item
        for item in rows
        if item.frozen_source_relation_vs_v3 == "LOSES_V3_MSS"
    )
    v3_only_recovered = tuple(
        item for item in v3_only if item.rearm_mss_at is not None
    )
    v3_only_same = sum(
        item.rearm_mss_at == item.current_v3_mss_at
        for item in v3_only_recovered
    )

    recovered_by_m5 = Counter(
        item.m5_state
        for item in rows
        if item.source_first_mss_at is None and item.rearm_mss_at is not None
    )

    return {
        "identity": IDENTITY,
        "symbol": symbol,
        "session": str(rows[0].session),
        "closebacks": len(rows),
        "confirmed_mss": {
            "CURRENT_V3": current_count,
            "SOURCE_FIRST": source_count,
            REARM: rearm_count,
        },
        "rearm_relation_vs_source_first": dict(sorted(relation_source.items())),
        "rearm_relation_vs_v3": dict(sorted(relation_v3.items())),
        "rearm_count_by_prior_rearms": dict(sorted(rearm_buckets.items())),
        "v3_only_rows": len(v3_only),
        "v3_only_recovered": len(v3_only_recovered),
        "v3_only_recovered_same_confirmation": v3_only_same,
        "source_first_missing_recovered": sum(
            item.source_first_mss_at is None and item.rearm_mss_at is not None
            for item in rows
        ),
        "source_first_existing_lost": sum(
            item.source_first_mss_at is not None and item.rearm_mss_at is None
            for item in rows
        ),
        "recovered_by_m5_state": dict(sorted(recovered_by_m5.items())),
        "series_rearm_semantics": (
            "FIRST_OPPOSING_OPEN_PER_DISTINCT_POST_SWEEP_SERIES"
        ),
        "pre_sweep_boundary_forbidden": True,
        "outcome_fields_read": False,
        "outcome_used_for_admission": False,
        "strategy_mutated": False,
        "diagnostic_only": True,
        "economic_candidate": False,
        "rule_promotion_allowed": False,
    }, rows


def write_market(
    report: dict[str, Any],
    rows: tuple[SeriesRearmRow, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    symbol = str(report["symbol"]).lower()
    stem = f"capitalizer-{symbol}-v3-source-first-series-rearm-census-2y-v1"
    (output / f"{stem}.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (output / f"{stem}-rows.jsonl").open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(asdict(row), sort_keys=True) + "\n")


def _load_reports(root: Path) -> list[dict[str, Any]]:
    paths = sorted(
        root.rglob(
            "capitalizer-*-v3-source-first-series-rearm-census-2y-v1.json"
        )
    )
    if len(paths) != 9:
        raise ValueError(f"series-rearm matrix requires 9 reports, got {len(paths)}")
    return [dict(json.loads(path.read_text(encoding="utf-8"))) for path in paths]


def _sum_mapping(reports: list[dict[str, Any]], key: str) -> dict[str, int]:
    total: Counter[str] = Counter()
    for report in reports:
        raw = report[key]
        if not isinstance(raw, dict):
            raise ValueError(f"{key} must be mapping")
        for name, value in raw.items():
            total[str(name)] += int(value)
    return dict(sorted(total.items()))


def build_matrix(root: Path) -> dict[str, Any]:
    reports = _load_reports(root)
    closebacks = sum(int(r["closebacks"]) for r in reports)
    current = sum(int(r["confirmed_mss"]["CURRENT_V3"]) for r in reports)
    source = sum(int(r["confirmed_mss"]["SOURCE_FIRST"]) for r in reports)
    rearm = sum(int(r["confirmed_mss"][REARM]) for r in reports)
    v3_only = sum(int(r["v3_only_rows"]) for r in reports)

    return {
        "identity": MATRIX_IDENTITY,
        "market_count": 9,
        "closebacks": closebacks,
        "closeback_control_reproduced": closebacks == EXPECTED_CLOSEBACKS,
        "confirmed_mss": {
            "CURRENT_V3": current,
            "SOURCE_FIRST": source,
            REARM: rearm,
        },
        "source_first_control_reproduced": source == EXPECTED_SOURCE_FIRST_MSS,
        "current_v3_control_reproduced": current == EXPECTED_CURRENT_V3_MSS,
        "rearm_relation_vs_source_first": _sum_mapping(
            reports,
            "rearm_relation_vs_source_first",
        ),
        "rearm_relation_vs_v3": _sum_mapping(
            reports,
            "rearm_relation_vs_v3",
        ),
        "rearm_count_by_prior_rearms": _sum_mapping(
            reports,
            "rearm_count_by_prior_rearms",
        ),
        "v3_only_rows": v3_only,
        "v3_only_control_reproduced": v3_only == EXPECTED_V3_ONLY,
        "v3_only_recovered": sum(int(r["v3_only_recovered"]) for r in reports),
        "v3_only_recovered_same_confirmation": sum(
            int(r["v3_only_recovered_same_confirmation"]) for r in reports
        ),
        "source_first_missing_recovered": sum(
            int(r["source_first_missing_recovered"]) for r in reports
        ),
        "source_first_existing_lost": sum(
            int(r["source_first_existing_lost"]) for r in reports
        ),
        "recovered_by_m5_state": _sum_mapping(
            reports,
            "recovered_by_m5_state",
        ),
        "markets": sorted(reports, key=lambda item: str(item["symbol"])),
        "series_rearm_semantics": (
            "FIRST_OPPOSING_OPEN_PER_DISTINCT_POST_SWEEP_SERIES"
        ),
        "pre_sweep_boundary_forbidden": True,
        "outcome_fields_read": False,
        "outcome_used_for_admission": False,
        "strategy_mutated": False,
        "diagnostic_only": True,
        "economic_candidate": False,
        "rule_promotion_allowed": False,
        "fresh_holdout_claimed": False,
        "live_authorized": False,
        "real_capital_authorized": False,
    }


def write_matrix(report: dict[str, Any], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    path = output / (
        "capitalizer-nine-market-v3-source-first-series-rearm-census-2y-v1.json"
    )
    path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    market = sub.add_parser("market")
    market.add_argument("semantics_root", type=Path)
    market.add_argument("m1_root", type=Path)
    market.add_argument("output", type=Path)

    matrix = sub.add_parser("matrix")
    matrix.add_argument("input_root", type=Path)
    matrix.add_argument("output", type=Path)

    args = parser.parse_args()
    if args.command == "market":
        report, rows = build_market_report(
            args.semantics_root,
            args.m1_root,
        )
        write_market(report, rows, args.output)
        print(json.dumps(report, sort_keys=True))
        return

    report = build_matrix(args.input_root)
    write_matrix(report, args.output)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
