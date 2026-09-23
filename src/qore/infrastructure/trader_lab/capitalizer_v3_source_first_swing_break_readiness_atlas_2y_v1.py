"""Outcome-free readiness atlas for SOURCE_FIRST residual SWING_BREAK blockers.

Population: residual SOURCE_FIRST M3 rows whose deepest terminal blocker is
SWING_BREAK after passing direction, body >=60%, and range >1.2*ATR.

This atlas changes no MSS semantics. It measures only pre-confirmation geometry:
- whether a latest same-side break pivot exists;
- whether CISD is already crossed on an otherwise-ready bar;
- whether price wicks through the pivot without closing through it;
- the closest M3 close-to-pivot distance normalized by ATR14.

No outcome, fill, stop, target, PnL, or economic selection is read.
"""

from __future__ import annotations

import argparse
import bisect
import json
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    capitalizer_owner_h1_m3_m1_causal_reversal_1y_v3 as v3,
)
from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import iter_cibo_m1
from qore.infrastructure.trader_lab.capitalizer_contract import CapitalizerSession
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_m3_mss_bottleneck_forensics_2y_v1 import (
    LOOKBACK_START,
    WINDOW_END,
)
from qore.infrastructure.trader_lab.capitalizer_strict_htf_gate_1y_v1 import (
    Pivot,
    TFBar,
    _aggregate_tf,
    _pivots,
)
from qore.infrastructure.trader_lab.capitalizer_v3_source_first_cisd_v1 import (
    _boundary_crossed,
    _opposing,
)

IDENTITY = "QORE_CAPITALIZER_V3_SOURCE_FIRST_SWING_BREAK_READINESS_ATLAS_2Y_V1"
MATRIX_IDENTITY = (
    "QORE_CAPITALIZER_NINE_MARKET_V3_SOURCE_FIRST_"
    "SWING_BREAK_READINESS_ATLAS_2Y_V1"
)
EXPECTED_SWING_BLOCKERS = 1679


@dataclass(frozen=True, slots=True)
class SwingBreakReadinessRow:
    symbol: str
    session: str
    operating_date: str
    side: str
    sweep_at: str
    closeback_at: str
    h1_deadline: str
    ready_bars: int
    pivot_available_bars: int
    cisd_ready_bars: int
    wick_through_no_close_bars: int
    touch_no_close_bars: int
    cisd_and_wick_through_any: bool
    cisd_without_close_break_any: bool
    best_close_gap_atr: str | None
    best_close_gap_band: str
    outcome_fields_read: bool = False


def _aware(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _gap_band(value: Decimal | None) -> str:
    if value is None:
        return "NO_PIVOT_GAP"
    if value <= Decimal("0.02"):
        return "LE_0_02_ATR"
    if value <= Decimal("0.05"):
        return "GT_0_02_TO_0_05_ATR"
    if value <= Decimal("0.10"):
        return "GT_0_05_TO_0_10_ATR"
    if value <= Decimal("0.20"):
        return "GT_0_10_TO_0_20_ATR"
    return "GT_0_20_ATR"


def _load_swing_blockers(root: Path) -> tuple[dict[str, Any], ...]:
    paths = sorted(
        root.rglob(
            "capitalizer-*-v3-source-first-residual-m3-bottleneck-atlas-2y-v1-rows.jsonl"
        )
    )
    if len(paths) != 1:
        raise ValueError("swing readiness requires one residual ledger per market")
    rows: list[dict[str, Any]] = []
    with paths[0].open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            raw = json.loads(line)
            if not isinstance(raw, dict):
                raise ValueError("residual row must be an object")
            if raw.get("terminal_blocker") == "SWING_BREAK":
                rows.append(raw)
    return tuple(rows)


def _build_row(
    raw: dict[str, Any],
    *,
    symbol: str,
    session: CapitalizerSession,
    m3: tuple[TFBar, ...],
    m3_closes: tuple[datetime, ...],
    pivots: tuple[Pivot, ...],
) -> SwingBreakReadinessRow:
    side = CapitalizerSide(str(raw["side"]))
    sweep_at = _aware(str(raw["sweep_at"]))
    closeback_at = _aware(str(raw["closeback_at"]))
    deadline = _aware(str(raw["h1_deadline"]))

    start = bisect.bisect_right(m3_closes, sweep_at)
    end = bisect.bisect_right(m3_closes, deadline)
    boundary: Decimal | None = None
    ready = 0
    pivot_available = 0
    cisd_ready = 0
    wick_through = 0
    touch_no_close = 0
    cisd_and_wick = False
    cisd_without_close_break = False
    gaps: list[Decimal] = []

    break_kind = "HIGH" if side is CapitalizerSide.LONG else "LOW"

    for index in range(start, end):
        bar = m3[index]
        source = bar.source

        if _opposing(bar, side=side):
            if boundary is None:
                boundary = source.open
            continue
        if bar.closed_at <= closeback_at or boundary is None:
            continue

        full_range = source.high - source.low
        directional = (
            source.close > source.open
            if side is CapitalizerSide.LONG
            else source.close < source.open
        )
        if full_range <= 0 or not directional:
            continue

        body_ratio = abs(source.close - source.open) / full_range
        if body_ratio < v3.BODY_RATIO_MIN:
            continue

        atr = v3._atr14(m3, index)
        if atr is None or atr <= 0:
            continue
        if full_range <= v3.ATR_MULTIPLIER * atr:
            continue

        ready += 1
        pivot = v3._latest_pivot(
            pivots,
            before=bar.opened_at,
            kind=break_kind,
        )
        if pivot is None:
            continue
        pivot_available += 1

        cisd = _boundary_crossed(
            close=source.close,
            boundary=boundary,
            side=side,
        )
        if cisd:
            cisd_ready += 1

        close_broke = (
            source.close > pivot.price
            if side is CapitalizerSide.LONG
            else source.close < pivot.price
        )
        if close_broke:
            raise ValueError("SWING_BREAK blocker unexpectedly has close break")

        wick_broke = (
            source.high > pivot.price
            if side is CapitalizerSide.LONG
            else source.low < pivot.price
        )
        touched = (
            source.high >= pivot.price
            if side is CapitalizerSide.LONG
            else source.low <= pivot.price
        )
        if wick_broke:
            wick_through += 1
            if cisd:
                cisd_and_wick = True
        if touched:
            touch_no_close += 1
        if cisd:
            cisd_without_close_break = True

        gap = (
            pivot.price - source.close
            if side is CapitalizerSide.LONG
            else source.close - pivot.price
        )
        if gap < 0:
            raise ValueError("negative swing-break close gap")
        gaps.append(gap / atr)

    best_gap = min(gaps, default=None)
    return SwingBreakReadinessRow(
        symbol=symbol,
        session=session.value,
        operating_date=str(raw["operating_date"]),
        side=side.value,
        sweep_at=sweep_at.isoformat(),
        closeback_at=closeback_at.isoformat(),
        h1_deadline=deadline.isoformat(),
        ready_bars=ready,
        pivot_available_bars=pivot_available,
        cisd_ready_bars=cisd_ready,
        wick_through_no_close_bars=wick_through,
        touch_no_close_bars=touch_no_close,
        cisd_and_wick_through_any=cisd_and_wick,
        cisd_without_close_break_any=cisd_without_close_break,
        best_close_gap_atr=None if best_gap is None else str(best_gap),
        best_close_gap_band=_gap_band(best_gap),
    )


def build_market_report(
    residual_root: Path,
    m1_root: Path,
    *,
    session: CapitalizerSession,
) -> tuple[dict[str, Any], tuple[SwingBreakReadinessRow, ...]]:
    frozen = _load_swing_blockers(residual_root)
    if not frozen:
        raise ValueError("swing readiness found no frozen blockers")

    all_bars = tuple(
        bar
        for bar in iter_cibo_m1(m1_root)
        if LOOKBACK_START <= bar.opened_at < WINDOW_END + timedelta(days=1)
    )
    if not all_bars:
        raise ValueError("swing readiness found no native M1")
    symbol = all_bars[0].symbol
    if any(bar.symbol != symbol for bar in all_bars):
        raise ValueError("swing readiness requires one market")
    if any(str(row["symbol"]) != symbol for row in frozen):
        raise ValueError("swing readiness residual/M1 symbol mismatch")
    if any(str(row["session"]) != session.value for row in frozen):
        raise ValueError("swing readiness session mismatch")

    m3 = _aggregate_tf(all_bars, minutes=3)
    m3_closes = tuple(item.closed_at for item in m3)
    pivots = _pivots(m3)
    rows = tuple(
        _build_row(
            row,
            symbol=symbol,
            session=session,
            m3=m3,
            m3_closes=m3_closes,
            pivots=pivots,
        )
        for row in frozen
    )
    bands = Counter(item.best_close_gap_band for item in rows)
    return {
        "identity": IDENTITY,
        "symbol": symbol,
        "session": session.value,
        "swing_break_blockers": len(rows),
        "pivot_available": sum(item.pivot_available_bars > 0 for item in rows),
        "cisd_ready_without_close_break": sum(
            item.cisd_without_close_break_any for item in rows
        ),
        "wick_through_without_close": sum(
            item.wick_through_no_close_bars > 0 for item in rows
        ),
        "cisd_and_wick_through": sum(
            item.cisd_and_wick_through_any for item in rows
        ),
        "best_close_gap_bands": dict(sorted(bands.items())),
        "thresholds_changed": False,
        "swing_break_semantics_changed": False,
        "outcome_fields_read": False,
        "outcome_used_for_classification": False,
        "strategy_mutated": False,
        "diagnostic_only": True,
        "economic_candidate": False,
        "rule_promotion_allowed": False,
        "fresh_holdout_claimed": False,
        "live_authorized": False,
        "real_capital_authorized": False,
    }, rows


def write_market(
    report: dict[str, Any],
    rows: tuple[SwingBreakReadinessRow, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    symbol = str(report["symbol"]).lower()
    stem = (
        f"capitalizer-{symbol}-v3-source-first-"
        "swing-break-readiness-atlas-2y-v1"
    )
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
            "capitalizer-*-v3-source-first-swing-break-readiness-atlas-2y-v1.json"
        )
    )
    if len(paths) != 9:
        raise ValueError(f"swing readiness matrix requires 9 reports, got {len(paths)}")
    return [dict(json.loads(path.read_text(encoding="utf-8"))) for path in paths]


def build_matrix(root: Path) -> dict[str, Any]:
    reports = _load_reports(root)
    total = sum(int(item["swing_break_blockers"]) for item in reports)
    bands: Counter[str] = Counter()
    for report in reports:
        for key, value in dict(report["best_close_gap_bands"]).items():
            bands[str(key)] += int(value)
    return {
        "identity": MATRIX_IDENTITY,
        "market_count": 9,
        "swing_break_blockers": total,
        "swing_blocker_control_reproduced": total == EXPECTED_SWING_BLOCKERS,
        "pivot_available": sum(int(item["pivot_available"]) for item in reports),
        "cisd_ready_without_close_break": sum(
            int(item["cisd_ready_without_close_break"]) for item in reports
        ),
        "wick_through_without_close": sum(
            int(item["wick_through_without_close"]) for item in reports
        ),
        "cisd_and_wick_through": sum(
            int(item["cisd_and_wick_through"]) for item in reports
        ),
        "best_close_gap_bands": dict(sorted(bands.items())),
        "markets": sorted(reports, key=lambda item: str(item["symbol"])),
        "thresholds_changed": False,
        "swing_break_semantics_changed": False,
        "outcome_fields_read": False,
        "outcome_used_for_classification": False,
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
        "capitalizer-nine-market-v3-source-first-"
        "swing-break-readiness-atlas-2y-v1.json"
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
