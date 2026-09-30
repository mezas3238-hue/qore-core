"""Outcome-free readiness atlas for SOURCE_FIRST residual CISD_NOT_CROSSED blockers.

Population: residual SOURCE_FIRST M3 closebacks whose deepest terminal blocker
is CISD_NOT_CROSSED after passing direction, body >=60%, ATR >1.2 and swing break.

The atlas does not change SOURCE_FIRST boundary semantics. It measures:
- bars already ready except CISD close;
- whether wick crosses the persistent boundary without close confirmation;
- the closest close-to-boundary gap normalized by ATR14;
- whether the close touches the boundary exactly.

No fill, stop, target, outcome, PnL, or economic selection is read.
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
    _opposing,
)

IDENTITY = "QORE_CAPITALIZER_V3_SOURCE_FIRST_CISD_READINESS_ATLAS_2Y_V1"
MATRIX_IDENTITY = (
    "QORE_CAPITALIZER_NINE_MARKET_V3_SOURCE_FIRST_CISD_READINESS_ATLAS_2Y_V1"
)
EXPECTED_CISD_BLOCKERS = 213


@dataclass(frozen=True, slots=True)
class CisdReadinessRow:
    symbol: str
    session: str
    operating_date: str
    side: str
    sweep_at: str
    closeback_at: str
    h1_deadline: str
    ready_except_cisd_bars: int
    wick_cross_without_close_bars: int
    exact_close_touch_bars: int
    wick_cross_any: bool
    best_close_gap_atr: str | None
    best_close_gap_band: str
    outcome_fields_read: bool = False


def _aware(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _gap_band(value: Decimal | None) -> str:
    if value is None:
        return "NO_GAP"
    if value <= Decimal("0.02"):
        return "LE_0_02_ATR"
    if value <= Decimal("0.05"):
        return "GT_0_02_TO_0_05_ATR"
    if value <= Decimal("0.10"):
        return "GT_0_05_TO_0_10_ATR"
    if value <= Decimal("0.20"):
        return "GT_0_10_TO_0_20_ATR"
    return "GT_0_20_ATR"


def _load_blockers(root: Path) -> tuple[dict[str, Any], ...]:
    paths = sorted(
        root.rglob(
            "capitalizer-*-v3-source-first-residual-m3-bottleneck-atlas-2y-v1-rows.jsonl"
        )
    )
    if len(paths) != 1:
        raise ValueError("CISD readiness requires one residual ledger per market")
    rows: list[dict[str, Any]] = []
    with paths[0].open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            raw = json.loads(line)
            if not isinstance(raw, dict):
                raise ValueError("residual row must be an object")
            if raw.get("terminal_blocker") == "CISD_NOT_CROSSED":
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
) -> CisdReadinessRow:
    side = CapitalizerSide(str(raw["side"]))
    sweep_at = _aware(str(raw["sweep_at"]))
    closeback_at = _aware(str(raw["closeback_at"]))
    deadline = _aware(str(raw["h1_deadline"]))

    start = bisect.bisect_right(m3_closes, sweep_at)
    end = bisect.bisect_right(m3_closes, deadline)
    break_kind = "HIGH" if side is CapitalizerSide.LONG else "LOW"
    boundary: Decimal | None = None

    ready = 0
    wick_cross = 0
    exact_touch = 0
    gaps: list[Decimal] = []

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

        pivot = v3._latest_pivot(
            pivots,
            before=bar.opened_at,
            kind=break_kind,
        )
        if pivot is None:
            continue
        swing = (
            source.close > pivot.price
            if side is CapitalizerSide.LONG
            else source.close < pivot.price
        )
        if not swing:
            continue

        crossed = (
            source.close > boundary
            if side is CapitalizerSide.LONG
            else source.close < boundary
        )
        if crossed:
            raise ValueError("CISD blocker unexpectedly contains close crossing")

        ready += 1
        if source.close == boundary:
            exact_touch += 1

        wick = (
            source.high > boundary
            if side is CapitalizerSide.LONG
            else source.low < boundary
        )
        if wick:
            wick_cross += 1

        gap = (
            boundary - source.close
            if side is CapitalizerSide.LONG
            else source.close - boundary
        )
        if gap < 0:
            raise ValueError("negative CISD close gap")
        gaps.append(gap / atr)

    best_gap = min(gaps, default=None)
    return CisdReadinessRow(
        symbol=symbol,
        session=session.value,
        operating_date=str(raw["operating_date"]),
        side=side.value,
        sweep_at=sweep_at.isoformat(),
        closeback_at=closeback_at.isoformat(),
        h1_deadline=deadline.isoformat(),
        ready_except_cisd_bars=ready,
        wick_cross_without_close_bars=wick_cross,
        exact_close_touch_bars=exact_touch,
        wick_cross_any=wick_cross > 0,
        best_close_gap_atr=None if best_gap is None else str(best_gap),
        best_close_gap_band=_gap_band(best_gap),
    )


def build_market_report(
    residual_root: Path,
    m1_root: Path,
    *,
    session: CapitalizerSession,
) -> tuple[dict[str, Any], tuple[CisdReadinessRow, ...]]:
    frozen = _load_blockers(residual_root)
    if not frozen:
        raise ValueError("CISD readiness found no frozen blockers")

    all_bars = tuple(
        bar
        for bar in iter_cibo_m1(m1_root)
        if LOOKBACK_START <= bar.opened_at < WINDOW_END + timedelta(days=1)
    )
    if not all_bars:
        raise ValueError("CISD readiness found no native M1")
    symbol = all_bars[0].symbol
    if any(bar.symbol != symbol for bar in all_bars):
        raise ValueError("CISD readiness requires one market")
    if any(str(row["symbol"]) != symbol for row in frozen):
        raise ValueError("CISD readiness residual/M1 symbol mismatch")
    if any(str(row["session"]) != session.value for row in frozen):
        raise ValueError("CISD readiness session mismatch")

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
        "cisd_blockers": len(rows),
        "ready_except_cisd": sum(item.ready_except_cisd_bars > 0 for item in rows),
        "wick_cross_without_close": sum(item.wick_cross_any for item in rows),
        "exact_close_touch": sum(item.exact_close_touch_bars > 0 for item in rows),
        "best_close_gap_bands": dict(sorted(bands.items())),
        "source_first_boundary_changed": False,
        "thresholds_changed": False,
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
    rows: tuple[CisdReadinessRow, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    symbol = str(report["symbol"]).lower()
    stem = f"capitalizer-{symbol}-v3-source-first-cisd-readiness-atlas-2y-v1"
    (output / f"{stem}.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (output / f"{stem}-rows.jsonl").open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(asdict(row), sort_keys=True) + "\n")


def _load_reports(root: Path) -> list[dict[str, Any]]:
    paths = sorted(
        root.rglob("capitalizer-*-v3-source-first-cisd-readiness-atlas-2y-v1.json")
    )
    if len(paths) != 9:
        raise ValueError(f"CISD readiness matrix requires 9 reports, got {len(paths)}")
    return [dict(json.loads(path.read_text(encoding="utf-8"))) for path in paths]


def build_matrix(root: Path) -> dict[str, Any]:
    reports = _load_reports(root)
    total = sum(int(item["cisd_blockers"]) for item in reports)
    bands: Counter[str] = Counter()
    for report in reports:
        for key, value in dict(report["best_close_gap_bands"]).items():
            bands[str(key)] += int(value)
    return {
        "identity": MATRIX_IDENTITY,
        "market_count": 9,
        "cisd_blockers": total,
        "cisd_blocker_control_reproduced": total == EXPECTED_CISD_BLOCKERS,
        "ready_except_cisd": sum(int(item["ready_except_cisd"]) for item in reports),
        "wick_cross_without_close": sum(
            int(item["wick_cross_without_close"]) for item in reports
        ),
        "exact_close_touch": sum(int(item["exact_close_touch"]) for item in reports),
        "best_close_gap_bands": dict(sorted(bands.items())),
        "markets": sorted(reports, key=lambda item: str(item["symbol"])),
        "source_first_boundary_changed": False,
        "thresholds_changed": False,
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
    path = output / "capitalizer-nine-market-v3-source-first-cisd-readiness-atlas-2y-v1.json"
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
