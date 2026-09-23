"""Outcome-free residual bottleneck atlas for SOURCE_FIRST M3 MSS.

Population: frozen 2Y boundary-semantics closebacks where SOURCE_FIRST produced
no M3 MSS. Expected population: 8,099 closebacks - 2,692 SOURCE_FIRST MSS =
5,407 residual closebacks.

The atlas follows the exact SOURCE_FIRST helper order and assigns each residual
closeback to the deepest causal stage reached before its H1 deadline:

NO_M3_AFTER_CLOSEBACK
NO_SOURCE_BOUNDARY
NO_DIRECTIONAL_AFTER_BOUNDARY
BODY_LT_60
ATR_LE_1_2
SWING_BREAK
CISD_NOT_CROSSED

It changes no threshold, reads no outcomes and admits no trades.
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
from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    iter_cibo_m1,
)
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
    find_source_first_m3_mss,
)

IDENTITY = "QORE_CAPITALIZER_V3_SOURCE_FIRST_RESIDUAL_M3_BOTTLENECK_ATLAS_2Y_V1"
MATRIX_IDENTITY = (
    "QORE_CAPITALIZER_NINE_MARKET_V3_SOURCE_FIRST_"
    "RESIDUAL_M3_BOTTLENECK_ATLAS_2Y_V1"
)
EXPECTED_CLOSEBACKS = 8099
EXPECTED_SOURCE_FIRST_MSS = 2692
EXPECTED_RESIDUAL = 5407


@dataclass(frozen=True, slots=True)
class ResidualM3Row:
    symbol: str
    session: str
    operating_date: str
    side: str
    sweep_at: str
    closeback_at: str
    h1_deadline: str
    liquidity_source: str
    terminal_blocker: str
    m3_bars_after_closeback: int
    source_boundary_available: bool
    directional_bars: int
    body_pass_bars: int
    atr_pass_bars: int
    swing_break_bars: int
    cisd_cross_bars: int
    minutes_remaining_after_closeback: str
    outcome_fields_read: bool = False


def _aware(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _load_semantics(root: Path) -> tuple[dict[str, Any], ...]:
    paths = sorted(
        root.rglob(
            "capitalizer-*-v3-cisd-boundary-semantics-census-2y-v1-rows.jsonl"
        )
    )
    if len(paths) != 1:
        raise ValueError("residual M3 atlas requires one semantics ledger per market")
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


def _swing_break(
    bars: tuple[TFBar, ...],
    pivots: tuple[Pivot, ...],
    *,
    index: int,
    side: CapitalizerSide,
) -> bool:
    break_kind = "HIGH" if side is CapitalizerSide.LONG else "LOW"
    broken = v3._latest_pivot(
        pivots,
        before=bars[index].opened_at,
        kind=break_kind,
    )
    if broken is None:
        return False
    source = bars[index].source
    return bool(
        source.close > broken.price
        if side is CapitalizerSide.LONG
        else source.close < broken.price
    )


def _diagnose(
    raw: dict[str, Any],
    *,
    symbol: str,
    session: CapitalizerSession,
    m3: tuple[TFBar, ...],
    m3_closes: tuple[datetime, ...],
    m3_pivots: tuple[Pivot, ...],
) -> ResidualM3Row:
    side = CapitalizerSide(str(raw["side"]))
    sweep_at = _aware(str(raw["sweep_at"]))
    closeback_at = _aware(str(raw["closeback_at"]))
    deadline = _aware(str(raw["h1_deadline"]))

    if raw.get("source_first_mss_at") is not None:
        raise ValueError("residual M3 atlas received a SOURCE_FIRST MSS row")

    if (
        find_source_first_m3_mss(
            m3,
            m3_closes,
            m3_pivots,
            sweep_at=sweep_at,
            after=closeback_at,
            before=deadline,
            side=side,
        )
        is not None
    ):
        raise ValueError("residual M3 reconstruction unexpectedly found MSS")

    start = bisect.bisect_right(m3_closes, sweep_at)
    end = bisect.bisect_right(m3_closes, deadline)
    boundary: Decimal | None = None
    m3_after = 0
    directional = 0
    body_pass = 0
    atr_pass = 0
    swing_pass = 0
    cisd_pass = 0

    for index in range(start, end):
        bar = m3[index]
        source = bar.source

        if _opposing(bar, side=side):
            if boundary is None:
                boundary = source.open
            continue

        if bar.closed_at <= closeback_at:
            continue
        m3_after += 1
        if boundary is None:
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
        if body_ratio < v3.BODY_RATIO_MIN:
            continue
        body_pass += 1

        atr = v3._atr14(m3, index)
        if atr is None or full_range <= v3.ATR_MULTIPLIER * atr:
            continue
        atr_pass += 1

        if not _swing_break(m3, m3_pivots, index=index, side=side):
            continue
        swing_pass += 1

        if not _boundary_crossed(
            close=source.close,
            boundary=boundary,
            side=side,
        ):
            continue
        cisd_pass += 1

    if m3_after == 0:
        blocker = "NO_M3_AFTER_CLOSEBACK"
    elif boundary is None:
        blocker = "NO_SOURCE_BOUNDARY"
    elif directional == 0:
        blocker = "NO_DIRECTIONAL_AFTER_BOUNDARY"
    elif body_pass == 0:
        blocker = "BODY_LT_60"
    elif atr_pass == 0:
        blocker = "ATR_LE_1_2"
    elif swing_pass == 0:
        blocker = "SWING_BREAK"
    elif cisd_pass == 0:
        blocker = "CISD_NOT_CROSSED"
    else:
        raise ValueError("residual M3 row reached full MSS unexpectedly")

    remaining = deadline - closeback_at
    return ResidualM3Row(
        symbol=symbol,
        session=session.value,
        operating_date=str(raw["operating_date"]),
        side=side.value,
        sweep_at=sweep_at.isoformat(),
        closeback_at=closeback_at.isoformat(),
        h1_deadline=deadline.isoformat(),
        liquidity_source=str(raw["liquidity_source"]),
        terminal_blocker=blocker,
        m3_bars_after_closeback=m3_after,
        source_boundary_available=boundary is not None,
        directional_bars=directional,
        body_pass_bars=body_pass,
        atr_pass_bars=atr_pass,
        swing_break_bars=swing_pass,
        cisd_cross_bars=cisd_pass,
        minutes_remaining_after_closeback=str(
            Decimal(str(remaining.total_seconds())) / Decimal("60")
        ),
    )


def build_market_report(
    semantics_root: Path,
    m1_root: Path,
    *,
    session: CapitalizerSession,
) -> tuple[dict[str, Any], tuple[ResidualM3Row, ...]]:
    semantics = _load_semantics(semantics_root)
    residual = tuple(
        row for row in semantics if row.get("source_first_mss_at") is None
    )
    if not residual:
        raise ValueError("residual M3 atlas found no residual closebacks")

    all_bars = tuple(
        bar
        for bar in iter_cibo_m1(m1_root)
        if LOOKBACK_START <= bar.opened_at < WINDOW_END + timedelta(days=1)
    )
    if not all_bars:
        raise ValueError("residual M3 atlas found no native M1")
    symbol = all_bars[0].symbol
    if any(bar.symbol != symbol for bar in all_bars):
        raise ValueError("residual M3 atlas requires one market per M1 root")
    if any(str(row["symbol"]) != symbol for row in semantics):
        raise ValueError("residual M3 semantics/M1 symbol mismatch")
    if any(str(row["session"]) != session.value for row in semantics):
        raise ValueError("residual M3 session mismatch")

    m3 = _aggregate_tf(all_bars, minutes=3)
    m3_closes = tuple(item.closed_at for item in m3)
    m3_pivots = _pivots(m3)

    rows = tuple(
        _diagnose(
            raw,
            symbol=symbol,
            session=session,
            m3=m3,
            m3_closes=m3_closes,
            m3_pivots=m3_pivots,
        )
        for raw in residual
    )
    ordered = tuple(sorted(rows, key=lambda item: item.closeback_at))
    blockers = Counter(item.terminal_blocker for item in ordered)
    return {
        "identity": IDENTITY,
        "symbol": symbol,
        "session": session.value,
        "closebacks": len(semantics),
        "source_first_mss": len(semantics) - len(ordered),
        "residual_closebacks": len(ordered),
        "terminal_blockers": dict(sorted(blockers.items())),
        "source_boundary_available": sum(
            item.source_boundary_available for item in ordered
        ),
        "m3_time_available": sum(
            item.m3_bars_after_closeback > 0 for item in ordered
        ),
        "directional_available": sum(
            item.directional_bars > 0 for item in ordered
        ),
        "body_pass_available": sum(
            item.body_pass_bars > 0 for item in ordered
        ),
        "atr_pass_available": sum(
            item.atr_pass_bars > 0 for item in ordered
        ),
        "swing_break_available": sum(
            item.swing_break_bars > 0 for item in ordered
        ),
        "thresholds_changed": False,
        "source_first_semantics_changed": False,
        "outcome_fields_read": False,
        "outcome_used_for_classification": False,
        "strategy_mutated": False,
        "diagnostic_only": True,
        "economic_candidate": False,
        "rule_promotion_allowed": False,
        "fresh_holdout_claimed": False,
        "live_authorized": False,
        "real_capital_authorized": False,
    }, ordered


def write_market(
    report: dict[str, Any],
    rows: tuple[ResidualM3Row, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    symbol = str(report["symbol"]).lower()
    stem = (
        f"capitalizer-{symbol}-v3-source-first-"
        "residual-m3-bottleneck-atlas-2y-v1"
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
            "capitalizer-*-v3-source-first-residual-m3-bottleneck-atlas-2y-v1.json"
        )
    )
    if len(paths) != 9:
        raise ValueError(f"residual M3 matrix requires 9 reports, got {len(paths)}")
    return [dict(json.loads(path.read_text(encoding="utf-8"))) for path in paths]


def build_matrix(root: Path) -> dict[str, Any]:
    reports = _load_reports(root)
    closebacks = sum(int(item["closebacks"]) for item in reports)
    source_first = sum(int(item["source_first_mss"]) for item in reports)
    residual = sum(int(item["residual_closebacks"]) for item in reports)
    blockers: Counter[str] = Counter()
    for report in reports:
        for key, value in dict(report["terminal_blockers"]).items():
            blockers[str(key)] += int(value)

    return {
        "identity": MATRIX_IDENTITY,
        "market_count": 9,
        "closebacks": closebacks,
        "closeback_control_reproduced": closebacks == EXPECTED_CLOSEBACKS,
        "source_first_mss": source_first,
        "source_first_control_reproduced": (
            source_first == EXPECTED_SOURCE_FIRST_MSS
        ),
        "residual_closebacks": residual,
        "residual_control_reproduced": residual == EXPECTED_RESIDUAL,
        "terminal_blockers": dict(sorted(blockers.items())),
        "source_boundary_available": sum(
            int(item["source_boundary_available"]) for item in reports
        ),
        "m3_time_available": sum(
            int(item["m3_time_available"]) for item in reports
        ),
        "directional_available": sum(
            int(item["directional_available"]) for item in reports
        ),
        "body_pass_available": sum(
            int(item["body_pass_available"]) for item in reports
        ),
        "atr_pass_available": sum(
            int(item["atr_pass_available"]) for item in reports
        ),
        "swing_break_available": sum(
            int(item["swing_break_available"]) for item in reports
        ),
        "markets": sorted(reports, key=lambda item: str(item["symbol"])),
        "thresholds_changed": False,
        "source_first_semantics_changed": False,
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
        "residual-m3-bottleneck-atlas-2y-v1.json"
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
            args.semantics_root,
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
