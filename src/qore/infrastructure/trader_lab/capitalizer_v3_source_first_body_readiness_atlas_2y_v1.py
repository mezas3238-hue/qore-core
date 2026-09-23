"""Outcome-free readiness atlas for SOURCE_FIRST residual BODY_LT_60 blockers.

Population: residual SOURCE_FIRST M3 closebacks whose deepest terminal blocker
is BODY_LT_60.

The atlas does not change the 60% body threshold. For each directional M3 bar
after the frozen closeback it asks whether every OTHER MSS requirement would
already be satisfied:
- persistent SOURCE_FIRST boundary;
- ATR range > 1.2 * ATR14;
- protected/local pivot close break;
- CISD close through the persistent boundary.

It records the best causal body ratio and predeclared distance bands below 60%.
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
    _boundary_crossed,
    _opposing,
)

IDENTITY = "QORE_CAPITALIZER_V3_SOURCE_FIRST_BODY_READINESS_ATLAS_2Y_V1"
MATRIX_IDENTITY = (
    "QORE_CAPITALIZER_NINE_MARKET_V3_SOURCE_FIRST_BODY_READINESS_ATLAS_2Y_V1"
)
EXPECTED_BODY_BLOCKERS = 825
FROZEN_BODY_RATIO = Decimal("0.60")


@dataclass(frozen=True, slots=True)
class BodyReadinessRow:
    symbol: str
    session: str
    operating_date: str
    side: str
    sweep_at: str
    closeback_at: str
    h1_deadline: str
    directional_bars: int
    atr_ready_bars: int
    swing_ready_bars: int
    cisd_ready_bars: int
    all_other_ready_bars: int
    body_only_ready: bool
    best_body_ratio: str | None
    best_body_ratio_band: str
    best_all_other_body_ratio: str | None
    best_all_other_body_ratio_band: str
    outcome_fields_read: bool = False


def _aware(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _body_band(value: Decimal | None) -> str:
    if value is None:
        return "NO_RATIO"
    if value < Decimal("0.40"):
        return "LT_0_40"
    if value < Decimal("0.50"):
        return "0_40_TO_LT_0_50"
    if value < Decimal("0.55"):
        return "0_50_TO_LT_0_55"
    if value < FROZEN_BODY_RATIO:
        return "0_55_TO_LT_0_60"
    return "GE_0_60_UNEXPECTED"


def _load_body_blockers(root: Path) -> tuple[dict[str, Any], ...]:
    paths = sorted(
        root.rglob(
            "capitalizer-*-v3-source-first-residual-m3-bottleneck-atlas-2y-v1-rows.jsonl"
        )
    )
    if len(paths) != 1:
        raise ValueError("body readiness requires one residual ledger per market")
    rows: list[dict[str, Any]] = []
    with paths[0].open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            raw = json.loads(line)
            if not isinstance(raw, dict):
                raise ValueError("residual row must be an object")
            if raw.get("terminal_blocker") == "BODY_LT_60":
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
) -> BodyReadinessRow:
    side = CapitalizerSide(str(raw["side"]))
    sweep_at = _aware(str(raw["sweep_at"]))
    closeback_at = _aware(str(raw["closeback_at"]))
    deadline = _aware(str(raw["h1_deadline"]))

    start = bisect.bisect_right(m3_closes, sweep_at)
    end = bisect.bisect_right(m3_closes, deadline)
    break_kind = "HIGH" if side is CapitalizerSide.LONG else "LOW"
    boundary: Decimal | None = None

    directional = 0
    atr_ready = 0
    swing_ready = 0
    cisd_ready = 0
    all_other_ready = 0
    ratios: list[Decimal] = []
    all_other_ratios: list[Decimal] = []

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
        same_direction = (
            source.close > source.open
            if side is CapitalizerSide.LONG
            else source.close < source.open
        )
        if full_range <= 0 or not same_direction:
            continue

        directional += 1
        body_ratio = abs(source.close - source.open) / full_range
        if body_ratio >= FROZEN_BODY_RATIO:
            raise ValueError("BODY_LT_60 blocker unexpectedly contains body-pass bar")
        ratios.append(body_ratio)

        atr = v3._atr14(m3, index)
        if atr is None or atr <= 0:
            continue
        if full_range <= v3.ATR_MULTIPLIER * atr:
            continue
        atr_ready += 1

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
        swing_ready += 1

        cisd = _boundary_crossed(
            close=source.close,
            boundary=boundary,
            side=side,
        )
        if not cisd:
            continue
        cisd_ready += 1
        all_other_ready += 1
        all_other_ratios.append(body_ratio)

    best_body = max(ratios, default=None)
    best_all_other = max(all_other_ratios, default=None)
    return BodyReadinessRow(
        symbol=symbol,
        session=session.value,
        operating_date=str(raw["operating_date"]),
        side=side.value,
        sweep_at=sweep_at.isoformat(),
        closeback_at=closeback_at.isoformat(),
        h1_deadline=deadline.isoformat(),
        directional_bars=directional,
        atr_ready_bars=atr_ready,
        swing_ready_bars=swing_ready,
        cisd_ready_bars=cisd_ready,
        all_other_ready_bars=all_other_ready,
        body_only_ready=best_all_other is not None,
        best_body_ratio=None if best_body is None else str(best_body),
        best_body_ratio_band=_body_band(best_body),
        best_all_other_body_ratio=(
            None if best_all_other is None else str(best_all_other)
        ),
        best_all_other_body_ratio_band=_body_band(best_all_other),
    )


def build_market_report(
    residual_root: Path,
    m1_root: Path,
    *,
    session: CapitalizerSession,
) -> tuple[dict[str, Any], tuple[BodyReadinessRow, ...]]:
    frozen = _load_body_blockers(residual_root)
    if not frozen:
        raise ValueError("body readiness found no frozen blockers")

    all_bars = tuple(
        bar
        for bar in iter_cibo_m1(m1_root)
        if LOOKBACK_START <= bar.opened_at < WINDOW_END + timedelta(days=1)
    )
    if not all_bars:
        raise ValueError("body readiness found no native M1")
    symbol = all_bars[0].symbol
    if any(bar.symbol != symbol for bar in all_bars):
        raise ValueError("body readiness requires one market")
    if any(str(row["symbol"]) != symbol for row in frozen):
        raise ValueError("body readiness residual/M1 symbol mismatch")
    if any(str(row["session"]) != session.value for row in frozen):
        raise ValueError("body readiness session mismatch")

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

    all_bands = Counter(item.best_body_ratio_band for item in rows)
    ready_bands = Counter(
        item.best_all_other_body_ratio_band
        for item in rows
        if item.body_only_ready
    )
    return {
        "identity": IDENTITY,
        "symbol": symbol,
        "session": session.value,
        "body_blockers": len(rows),
        "body_only_ready": sum(item.body_only_ready for item in rows),
        "atr_ready_any": sum(item.atr_ready_bars > 0 for item in rows),
        "swing_ready_any": sum(item.swing_ready_bars > 0 for item in rows),
        "cisd_ready_any": sum(item.cisd_ready_bars > 0 for item in rows),
        "best_body_ratio_bands": dict(sorted(all_bands.items())),
        "best_all_other_body_ratio_bands": dict(sorted(ready_bands.items())),
        "frozen_body_ratio": str(FROZEN_BODY_RATIO),
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
    rows: tuple[BodyReadinessRow, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    symbol = str(report["symbol"]).lower()
    stem = f"capitalizer-{symbol}-v3-source-first-body-readiness-atlas-2y-v1"
    (output / f"{stem}.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (output / f"{stem}-rows.jsonl").open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(asdict(row), sort_keys=True) + "\n")


def _load_reports(root: Path) -> list[dict[str, Any]]:
    paths = sorted(
        root.rglob("capitalizer-*-v3-source-first-body-readiness-atlas-2y-v1.json")
    )
    if len(paths) != 9:
        raise ValueError(f"body readiness matrix requires 9 reports, got {len(paths)}")
    return [dict(json.loads(path.read_text(encoding="utf-8"))) for path in paths]


def build_matrix(root: Path) -> dict[str, Any]:
    reports = _load_reports(root)
    total = sum(int(item["body_blockers"]) for item in reports)
    all_bands: Counter[str] = Counter()
    ready_bands: Counter[str] = Counter()
    for report in reports:
        for key, value in dict(report["best_body_ratio_bands"]).items():
            all_bands[str(key)] += int(value)
        for key, value in dict(report["best_all_other_body_ratio_bands"]).items():
            ready_bands[str(key)] += int(value)

    return {
        "identity": MATRIX_IDENTITY,
        "market_count": 9,
        "body_blockers": total,
        "body_blocker_control_reproduced": total == EXPECTED_BODY_BLOCKERS,
        "body_only_ready": sum(int(item["body_only_ready"]) for item in reports),
        "atr_ready_any": sum(int(item["atr_ready_any"]) for item in reports),
        "swing_ready_any": sum(int(item["swing_ready_any"]) for item in reports),
        "cisd_ready_any": sum(int(item["cisd_ready_any"]) for item in reports),
        "best_body_ratio_bands": dict(sorted(all_bands.items())),
        "best_all_other_body_ratio_bands": dict(sorted(ready_bands.items())),
        "markets": sorted(reports, key=lambda item: str(item["symbol"])),
        "frozen_body_ratio": str(FROZEN_BODY_RATIO),
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
    path = output / "capitalizer-nine-market-v3-source-first-body-readiness-atlas-2y-v1.json"
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
