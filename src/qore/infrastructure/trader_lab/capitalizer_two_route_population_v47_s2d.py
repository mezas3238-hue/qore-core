"""V47-S2D outcome-blind two-route population freeze.

Unions the already-frozen FRACTAL S2-A population with the pre-economic S2-C
FTM population, fails closed on exact route collisions, and applies MAX3 only
after the union. No economics are read here.

Frozen by PR #623 comment 5901846384.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

from qore.infrastructure.trader_lab import (
    capitalizer_full_ftm_stream_v47_s2c as s2c,
)
from qore.infrastructure.trader_lab import (
    capitalizer_source_strategy_isolation_v47_s2 as s2a,
)
from qore.infrastructure.trader_lab.capitalizer_contract import (
    MAX_EXECUTIONS_PER_SESSION,
)

IDENTITY = "QORE_CAPITALIZER_V47_S2D_TWO_ROUTE_POPULATION_FREEZE"
PREDECLARATION_COMMENT_ID = 5901846384
SOURCE_S2A_RUN_ID = 36642644284
SOURCE_S2A_SHA = "ff6c9745690dde76520aecf608e44401622a1074"
EXPECTED_S2A_PERIOD_COUNTS = {
    "reserved": 30,
    "validation": 30,
    "development": 31,
}


@dataclass(frozen=True, slots=True)
class S2DPopulationRow:
    identity: str
    source_stream: str
    source_identity: str
    period: str
    symbol: str
    session: str
    operating_date: str
    route: str
    entry_at: str
    entry_price: str
    stop_price: str
    target_price: str
    target_kind: str
    source_run_id: int
    source_sha: str
    collision_failed_closed: bool = False
    outcome_used_for_selection: bool = False
    economics_read: bool = False
    fresh_holdout_opened: bool = False
    trader_certified: bool = False

    def __post_init__(self) -> None:
        if self.identity != IDENTITY:
            raise ValueError("S2D identity drift")
        if self.source_stream not in {"FRACTAL", "FTM"}:
            raise ValueError("S2D source stream drift")
        if self.period not in EXPECTED_S2A_PERIOD_COUNTS:
            raise ValueError("S2D period drift")
        if self.source_run_id <= 0 or len(self.source_sha) != 40:
            raise ValueError("S2D immutable source provenance missing")
        datetime.fromisoformat(self.entry_at)
        if (
            self.collision_failed_closed
            or self.outcome_used_for_selection
            or self.economics_read
            or self.fresh_holdout_opened
            or self.trader_certified
        ):
            raise ValueError("S2D selected row governance drift")


@dataclass(frozen=True, slots=True)
class S2DReport:
    identity: str
    source_s2a_run_id: int
    source_s2a_sha: str
    source_s2c_run_id: int
    source_s2c_sha: str
    fractal_rows: int
    ftm_rows: int
    route_collision_rows: int
    surviving_union_rows: int
    max3_selected_rows: int
    periods: dict[str, dict[str, int | bool]]
    max3_applied_after_union: bool = True
    outcome_used_for_selection: bool = False
    economics_read: bool = False
    fresh_holdout_opened: bool = False
    trader_certified: bool = False

    def __post_init__(self) -> None:
        if self.identity != IDENTITY:
            raise ValueError("S2D report identity drift")
        if self.source_s2a_run_id != SOURCE_S2A_RUN_ID:
            raise ValueError("S2D S2A run drift")
        if self.source_s2a_sha != SOURCE_S2A_SHA:
            raise ValueError("S2D S2A SHA drift")
        if self.source_s2c_run_id <= 0 or len(self.source_s2c_sha) != 40:
            raise ValueError("S2D S2C provenance missing")
        if (
            not self.max3_applied_after_union
            or self.outcome_used_for_selection
            or self.economics_read
            or self.fresh_holdout_opened
            or self.trader_certified
        ):
            raise ValueError("S2D report governance drift")


def _from_s2a(row: s2a.S2AdmittedFillRow) -> S2DPopulationRow:
    return S2DPopulationRow(
        identity=IDENTITY,
        source_stream="FRACTAL",
        source_identity=row.identity,
        period=row.period,
        symbol=row.symbol,
        session=row.session,
        operating_date=row.operating_date,
        route=row.route,
        entry_at=row.entry_at,
        entry_price=row.entry_price,
        stop_price=row.stop_price,
        target_price=row.target_price,
        target_kind=row.target_kind,
        source_run_id=SOURCE_S2A_RUN_ID,
        source_sha=SOURCE_S2A_SHA,
    )


def _from_s2c(
    row: s2c.S2CAdmittedFillRow,
    *,
    source_run_id: int,
    source_sha: str,
) -> S2DPopulationRow:
    return S2DPopulationRow(
        identity=IDENTITY,
        source_stream="FTM",
        source_identity=row.identity,
        period=row.period,
        symbol=row.symbol,
        session=row.session,
        operating_date=row.operating_date,
        route=row.route,
        entry_at=row.entry_at,
        entry_price=row.entry_price,
        stop_price=row.stop_price,
        target_price=row.target_price,
        target_kind=row.target_kind,
        source_run_id=source_run_id,
        source_sha=source_sha,
    )


def _load_s2a(root: Path) -> tuple[S2DPopulationRow, ...]:
    rows: list[S2DPopulationRow] = []
    for path in sorted(root.glob("capitalizer-s2a-*-max3.jsonl")):
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    rows.append(_from_s2a(s2a.S2AdmittedFillRow(**json.loads(line))))
    counts = {
        period: sum(row.period == period for row in rows)
        for period in EXPECTED_S2A_PERIOD_COUNTS
    }
    if counts != EXPECTED_S2A_PERIOD_COUNTS:
        raise ValueError(f"S2D frozen S2A population drift: {counts}")
    return tuple(rows)


def _load_s2c(
    root: Path,
    *,
    source_run_id: int,
    source_sha: str,
) -> tuple[S2DPopulationRow, ...]:
    path = root / "capitalizer-s2c-all-admitted.jsonl"
    if not path.is_file():
        raise ValueError("S2D S2C full admitted population artifact missing")
    rows: list[S2DPopulationRow] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(
                    _from_s2c(
                        s2c.S2CAdmittedFillRow(**json.loads(line)),
                        source_run_id=source_run_id,
                        source_sha=source_sha,
                    )
                )
    return tuple(rows)


def fail_closed_route_collisions(
    rows: tuple[S2DPopulationRow, ...],
) -> tuple[tuple[S2DPopulationRow, ...], tuple[S2DPopulationRow, ...]]:
    grouped: dict[tuple[str, str], list[S2DPopulationRow]] = defaultdict(list)
    for row in rows:
        grouped[(row.symbol, row.entry_at)].append(row)

    surviving: list[S2DPopulationRow] = []
    collisions: list[S2DPopulationRow] = []
    for group in grouped.values():
        routes = {row.route for row in group}
        streams = {row.source_stream for row in group}
        if len(group) > 1 and (len(routes) > 1 or len(streams) > 1):
            collisions.extend(group)
        else:
            surviving.extend(group)

    key = lambda row: (
        datetime.fromisoformat(row.entry_at),
        row.symbol,
        row.route,
    )
    return tuple(sorted(surviving, key=key)), tuple(sorted(collisions, key=key))


def select_combined_max3(
    rows: tuple[S2DPopulationRow, ...],
) -> tuple[S2DPopulationRow, ...]:
    grouped: dict[tuple[str, str, str], list[S2DPopulationRow]] = defaultdict(list)
    for row in rows:
        grouped[(row.period, row.session, row.operating_date)].append(row)

    selected: list[S2DPopulationRow] = []
    for key in sorted(grouped):
        ordered = sorted(
            grouped[key],
            key=lambda row: (
                datetime.fromisoformat(row.entry_at),
                row.symbol,
                row.route,
            ),
        )
        selected.extend(ordered[:MAX_EXECUTIONS_PER_SESSION])
    return tuple(
        sorted(
            selected,
            key=lambda row: (
                datetime.fromisoformat(row.entry_at),
                row.symbol,
                row.route,
            ),
        )
    )


def freeze(
    *,
    s2a_root: Path,
    s2c_root: Path,
    s2c_run_id: int,
    s2c_sha: str,
    output: Path,
) -> S2DReport:
    fractal = _load_s2a(s2a_root)
    ftm = _load_s2c(
        s2c_root,
        source_run_id=s2c_run_id,
        source_sha=s2c_sha,
    )
    union = (*fractal, *ftm)
    surviving, collisions = fail_closed_route_collisions(tuple(union))
    selected = select_combined_max3(surviving)

    output.mkdir(parents=True, exist_ok=True)
    with (output / "capitalizer-s2d-selected.jsonl").open(
        "w",
        encoding="utf-8",
    ) as handle:
        for row in selected:
            handle.write(json.dumps(asdict(row), sort_keys=True) + "\n")
    with (output / "capitalizer-s2d-collisions.jsonl").open(
        "w",
        encoding="utf-8",
    ) as handle:
        for row in collisions:
            payload = asdict(row)
            payload["collision_failed_closed"] = True
            handle.write(json.dumps(payload, sort_keys=True) + "\n")

    periods: dict[str, dict[str, int | bool]] = {}
    for period in EXPECTED_S2A_PERIOD_COUNTS:
        periods[period] = {
            "fractal_rows": sum(row.period == period for row in fractal),
            "ftm_rows": sum(row.period == period for row in ftm),
            "surviving_union_rows": sum(row.period == period for row in surviving),
            "max3_selected_rows": sum(row.period == period for row in selected),
            "max3_is_ceiling_not_quota": True,
            "outcome_used_for_selection": False,
        }

    report = S2DReport(
        identity=IDENTITY,
        source_s2a_run_id=SOURCE_S2A_RUN_ID,
        source_s2a_sha=SOURCE_S2A_SHA,
        source_s2c_run_id=s2c_run_id,
        source_s2c_sha=s2c_sha,
        fractal_rows=len(fractal),
        ftm_rows=len(ftm),
        route_collision_rows=len(collisions),
        surviving_union_rows=len(surviving),
        max3_selected_rows=len(selected),
        periods=periods,
    )
    (output / "capitalizer-s2d-report.json").write_text(
        json.dumps(asdict(report), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("s2a_root", type=Path)
    parser.add_argument("s2c_root", type=Path)
    parser.add_argument("--s2c-run-id", required=True, type=int)
    parser.add_argument("--s2c-sha", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    report = freeze(
        s2a_root=args.s2a_root,
        s2c_root=args.s2c_root,
        s2c_run_id=args.s2c_run_id,
        s2c_sha=args.s2c_sha,
        output=args.output,
    )
    print(json.dumps(asdict(report), sort_keys=True))


if __name__ == "__main__":
    main()
