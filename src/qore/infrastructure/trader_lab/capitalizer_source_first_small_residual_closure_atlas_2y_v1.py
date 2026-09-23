"""Outcome-free closure atlas for the final small SOURCE_FIRST M3 blockers.

Population:
- NO_DIRECTIONAL_AFTER_BOUNDARY (55)
- NO_SOURCE_BOUNDARY (13)

This atlas does not propose relaxed semantics. It verifies whether any of these
rows contain a complete causal path under the frozen SOURCE_FIRST definition and
records whether only a semantic change (for example using a pre-sweep opposing
bar as boundary) could alter the result.

No outcomes, fills, targets, stops, or PnL are read.
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

from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import iter_cibo_m1
from qore.infrastructure.trader_lab.capitalizer_contract import CapitalizerSession
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_m3_mss_bottleneck_forensics_2y_v1 import (
    LOOKBACK_START,
    WINDOW_END,
)
from qore.infrastructure.trader_lab.capitalizer_strict_htf_gate_1y_v1 import (
    TFBar,
    _aggregate_tf,
)
from qore.infrastructure.trader_lab.capitalizer_v3_source_first_cisd_v1 import (
    _opposing,
)

IDENTITY = "QORE_CAPITALIZER_SOURCE_FIRST_SMALL_RESIDUAL_CLOSURE_ATLAS_2Y_V1"
MATRIX_IDENTITY = (
    "QORE_CAPITALIZER_NINE_MARKET_SOURCE_FIRST_SMALL_RESIDUAL_CLOSURE_ATLAS_2Y_V1"
)
EXPECTED_NO_DIRECTIONAL = 55
EXPECTED_NO_SOURCE_BOUNDARY = 13
TARGET_BLOCKERS = {"NO_DIRECTIONAL_AFTER_BOUNDARY", "NO_SOURCE_BOUNDARY"}


@dataclass(frozen=True, slots=True)
class SmallResidualRow:
    symbol: str
    session: str
    operating_date: str
    blocker: str
    side: str
    sweep_at: str
    closeback_at: str
    h1_deadline: str
    completed_m3_after_closeback: int
    opposing_after_sweep: int
    directional_after_boundary: int
    pre_sweep_opposing_in_same_h1: int
    frozen_semantics_recoverable: bool
    semantic_change_required: bool
    outcome_fields_read: bool = False


def _load_rows(root: Path) -> tuple[dict[str, Any], ...]:
    paths = sorted(
        root.rglob(
            "capitalizer-*-v3-source-first-residual-m3-bottleneck-atlas-2y-v1-rows.jsonl"
        )
    )
    if len(paths) != 1:
        raise ValueError("small residual closure requires one residual ledger")
    rows: list[dict[str, Any]] = []
    with paths[0].open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            raw = json.loads(line)
            if raw.get("terminal_blocker") in TARGET_BLOCKERS:
                rows.append(raw)
    return tuple(rows)


def _same_direction(bar: TFBar, side: CapitalizerSide) -> bool:
    source = bar.source
    return bool(
        source.close > source.open
        if side is CapitalizerSide.LONG
        else source.close < source.open
    )


def _build_row(
    raw: dict[str, Any],
    *,
    symbol: str,
    session: CapitalizerSession,
    m3: tuple[TFBar, ...],
    m3_closes: tuple[datetime, ...],
) -> SmallResidualRow:
    side = CapitalizerSide(str(raw["side"]))
    sweep_at = datetime.fromisoformat(str(raw["sweep_at"]))
    closeback_at = datetime.fromisoformat(str(raw["closeback_at"]))
    deadline = datetime.fromisoformat(str(raw["h1_deadline"]))
    h1_open = deadline - timedelta(hours=1)

    start = bisect.bisect_right(m3_closes, sweep_at)
    end = bisect.bisect_right(m3_closes, deadline)

    boundary_seen = False
    opposing_after = 0
    completed_after = 0
    directional_after_boundary = 0
    for index in range(start, end):
        bar = m3[index]
        if _opposing(bar, side=side):
            opposing_after += 1
            boundary_seen = True
            continue
        if bar.closed_at <= closeback_at:
            continue
        completed_after += 1
        if boundary_seen and _same_direction(bar, side):
            directional_after_boundary += 1

    pre_sweep_opposing = sum(
        h1_open <= bar.opened_at < sweep_at and _opposing(bar, side=side)
        for bar in m3
    )

    blocker = str(raw["terminal_blocker"])
    if blocker == "NO_SOURCE_BOUNDARY":
        frozen_recoverable = opposing_after > 0
    else:
        frozen_recoverable = boundary_seen and directional_after_boundary > 0

    if frozen_recoverable:
        raise ValueError("small residual unexpectedly recoverable under frozen semantics")

    semantic_change_required = (
        blocker == "NO_SOURCE_BOUNDARY" and pre_sweep_opposing > 0
    )
    return SmallResidualRow(
        symbol=symbol,
        session=session.value,
        operating_date=str(raw["operating_date"]),
        blocker=blocker,
        side=side.value,
        sweep_at=sweep_at.isoformat(),
        closeback_at=closeback_at.isoformat(),
        h1_deadline=deadline.isoformat(),
        completed_m3_after_closeback=completed_after,
        opposing_after_sweep=opposing_after,
        directional_after_boundary=directional_after_boundary,
        pre_sweep_opposing_in_same_h1=pre_sweep_opposing,
        frozen_semantics_recoverable=False,
        semantic_change_required=semantic_change_required,
    )


def build_market_report(
    residual_root: Path,
    m1_root: Path,
    *,
    session: CapitalizerSession,
) -> tuple[dict[str, Any], tuple[SmallResidualRow, ...]]:
    frozen = _load_rows(residual_root)
    if not frozen:
        raise ValueError("small residual closure found no target blockers")

    bars = tuple(
        bar
        for bar in iter_cibo_m1(m1_root)
        if LOOKBACK_START <= bar.opened_at < WINDOW_END + timedelta(days=1)
    )
    if not bars:
        raise ValueError("small residual closure found no M1")
    symbol = bars[0].symbol
    if any(str(row["symbol"]) != symbol for row in frozen):
        raise ValueError("small residual symbol mismatch")

    m3 = _aggregate_tf(bars, minutes=3)
    m3_closes = tuple(item.closed_at for item in m3)
    rows = tuple(
        _build_row(
            raw,
            symbol=symbol,
            session=session,
            m3=m3,
            m3_closes=m3_closes,
        )
        for raw in frozen
    )
    blockers = Counter(item.blocker for item in rows)
    return {
        "identity": IDENTITY,
        "symbol": symbol,
        "session": session.value,
        "population": len(rows),
        "blockers": dict(sorted(blockers.items())),
        "frozen_semantics_recoverable": sum(
            item.frozen_semantics_recoverable for item in rows
        ),
        "semantic_change_required": sum(
            item.semantic_change_required for item in rows
        ),
        "outcome_fields_read": False,
        "strategy_mutated": False,
        "diagnostic_only": True,
        "recovery_phase": True,
        "target_phase": False,
    }, rows


def write_market(
    report: dict[str, Any],
    rows: tuple[SmallResidualRow, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    symbol = str(report["symbol"]).lower()
    stem = f"capitalizer-{symbol}-source-first-small-residual-closure-atlas-2y-v1"
    (output / f"{stem}.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (output / f"{stem}-rows.jsonl").open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(asdict(row), sort_keys=True) + "\n")


def build_matrix(root: Path) -> dict[str, Any]:
    paths = sorted(
        root.rglob(
            "capitalizer-*-source-first-small-residual-closure-atlas-2y-v1.json"
        )
    )
    if len(paths) != 9:
        raise ValueError(f"small residual matrix requires 9 reports, got {len(paths)}")
    reports = [dict(json.loads(path.read_text(encoding="utf-8"))) for path in paths]
    blockers: Counter[str] = Counter()
    for report in reports:
        for key, value in dict(report["blockers"]).items():
            blockers[str(key)] += int(value)
    return {
        "identity": MATRIX_IDENTITY,
        "market_count": 9,
        "population": sum(int(item["population"]) for item in reports),
        "blockers": dict(sorted(blockers.items())),
        "no_directional_control": blockers["NO_DIRECTIONAL_AFTER_BOUNDARY"]
        == EXPECTED_NO_DIRECTIONAL,
        "no_source_boundary_control": blockers["NO_SOURCE_BOUNDARY"]
        == EXPECTED_NO_SOURCE_BOUNDARY,
        "frozen_semantics_recoverable": sum(
            int(item["frozen_semantics_recoverable"]) for item in reports
        ),
        "semantic_change_required": sum(
            int(item["semantic_change_required"]) for item in reports
        ),
        "markets": sorted(reports, key=lambda item: str(item["symbol"])),
        "outcome_fields_read": False,
        "strategy_mutated": False,
        "diagnostic_only": True,
        "recovery_phase": True,
        "target_phase": False,
    }


def write_matrix(report: dict[str, Any], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    path = output / (
        "capitalizer-nine-market-source-first-"
        "small-residual-closure-atlas-2y-v1.json"
    )
    path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    market = sub.add_parser("market")
    market.add_argument("residual_root", type=Path)
    market.add_argument("m1_root", type=Path)
    market.add_argument("output", type=Path)
    market.add_argument(
        "--session",
        required=True,
        choices=[item.value for item in CapitalizerSession],
    )
    matrix = sub.add_parser("matrix")
    matrix.add_argument("input_root", type=Path)
    matrix.add_argument("output", type=Path)
    args = parser.parse_args()
    if args.command == "market":
        report, rows = build_market_report(
            args.residual_root,
            args.m1_root,
            session=CapitalizerSession(args.session),
        )
        write_market(report, rows, args.output)
        print(json.dumps(report, sort_keys=True))
        return
    report = build_matrix(args.input_root)
    write_matrix(report, args.output)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
