"""Outcome-free readiness atlas for SOURCE_FIRST residual ATR blockers.

Population: residual M3 closebacks whose terminal blocker is ATR_LE_1_2.
No threshold is changed.

For each closeback, inspect M3 candles under the frozen SOURCE_FIRST semantics and
ask whether any candle already satisfies every non-ATR requirement on the SAME
bar:
- persistent source-first boundary exists;
- correct direction;
- body ratio >= 0.60;
- protected/local pivot swing break;
- CISD close through the persistent boundary.

If so, ATR is the sole remaining requirement for that bar. The atlas records the
best displacement-range / ATR14 ratio and predeclared distance bands below the
frozen >1.2 threshold. No outcome, fill, stop, target, PnL or economic selection
is read.
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
    TFBar,
    _aggregate_tf,
    _pivots,
)
from qore.infrastructure.trader_lab.capitalizer_v3_source_first_cisd_v1 import (
    _boundary_crossed,
    _opposing,
)

IDENTITY = "QORE_CAPITALIZER_V3_SOURCE_FIRST_ATR_READINESS_ATLAS_2Y_V1"
MATRIX_IDENTITY = (
    "QORE_CAPITALIZER_NINE_MARKET_V3_SOURCE_FIRST_ATR_READINESS_ATLAS_2Y_V1"
)
EXPECTED_ATR_BLOCKERS = 2232
FROZEN_ATR_MULTIPLIER = Decimal("1.2")
FROZEN_BODY_RATIO_MIN = Decimal("0.60")


@dataclass(frozen=True, slots=True)
class AtrReadinessRow:
    symbol: str
    session: str
    operating_date: str
    side: str
    sweep_at: str
    closeback_at: str
    h1_deadline: str
    body_ready_bars: int
    bars_with_atr: int
    swing_ready_bars: int
    cisd_ready_bars: int
    swing_and_cisd_same_bar: int
    atr_only_ready: bool
    best_all_other_ratio: str | None
    best_all_other_ratio_band: str
    best_body_ready_ratio: str | None
    best_body_ready_ratio_band: str
    outcome_fields_read: bool = False


def _aware(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _ratio_band(value: Decimal | None) -> str:
    if value is None:
        return "NO_RATIO"
    if value < Decimal("0.75"):
        return "LT_0_75"
    if value < Decimal("0.90"):
        return "0_75_TO_LT_0_90"
    if value < Decimal("1.00"):
        return "0_90_TO_LT_1_00"
    if value < Decimal("1.10"):
        return "1_00_TO_LT_1_10"
    if value < FROZEN_ATR_MULTIPLIER:
        return "1_10_TO_LT_1_20"
    if value == FROZEN_ATR_MULTIPLIER:
        return "EQ_1_20"
    return "GT_1_20_UNEXPECTED"


def _load_atr_blockers(root: Path) -> tuple[dict[str, object], ...]:
    paths = sorted(
        root.rglob(
            "capitalizer-*-v3-source-first-residual-m3-bottleneck-atlas-2y-v1-rows.jsonl"
        )
    )
    if len(paths) != 1:
        raise ValueError("ATR readiness requires one residual ledger per market")
    rows: list[dict[str, object]] = []
    with paths[0].open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            raw = json.loads(line)
            if not isinstance(raw, dict):
                raise ValueError("residual M3 row must be object")
            if raw.get("terminal_blocker") == "ATR_LE_1_2":
                rows.append(raw)
    return tuple(rows)


def _build_row(
    raw: dict[str, object],
    *,
    symbol: str,
    session: CapitalizerSession,
    m3: tuple[TFBar, ...],
    m3_closes: tuple[datetime, ...],
    m3_pivots: object,
) -> AtrReadinessRow:
    side = CapitalizerSide(str(raw["side"]))
    sweep_at = _aware(str(raw["sweep_at"]))
    closeback_at = _aware(str(raw["closeback_at"]))
    deadline = _aware(str(raw["h1_deadline"]))

    start = bisect.bisect_right(m3_closes, sweep_at)
    end = bisect.bisect_right(m3_closes, deadline)
    boundary: Decimal | None = None

    body_ready = 0
    atr_count = 0
    swing_ready = 0
    cisd_ready = 0
    both_ready = 0
    body_ratios: list[Decimal] = []
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
        directional = (
            source.close > source.open
            if side is CapitalizerSide.LONG
            else source.close < source.open
        )
        if full_range <= 0 or not directional:
            continue
        body_ratio = abs(source.close - source.open) / full_range
        if body_ratio < FROZEN_BODY_RATIO_MIN:
            continue
        body_ready += 1

        atr = v3._atr14(m3, index)
        if atr is None or atr <= 0:
            continue
        atr_count += 1
        ratio = full_range / atr
        if ratio > FROZEN_ATR_MULTIPLIER:
            raise ValueError("ATR blocker unexpectedly contains an ATR-pass bar")
        body_ratios.append(ratio)

        break_kind = "HIGH" if side is CapitalizerSide.LONG else "LOW"
        broken = v3._latest_pivot(
            m3_pivots,
            before=bar.opened_at,
            kind=break_kind,
        )
        swing = False
        if broken is not None:
            swing = (
                source.close > broken.price
                if side is CapitalizerSide.LONG
                else source.close < broken.price
            )
        cisd = _boundary_crossed(
            close=source.close,
            boundary=boundary,
            side=side,
        )
        if swing:
            swing_ready += 1
        if cisd:
            cisd_ready += 1
        if swing and cisd:
            both_ready += 1
            all_other_ratios.append(ratio)

    best_all_other = max(all_other_ratios, default=None)
    best_body = max(body_ratios, default=None)
    return AtrReadinessRow(
        symbol=symbol,
        session=session.value,
        operating_date=str(raw["operating_date"]),
        side=side.value,
        sweep_at=sweep_at.isoformat(),
        closeback_at=closeback_at.isoformat(),
        h1_deadline=deadline.isoformat(),
        body_ready_bars=body_ready,
        bars_with_atr=atr_count,
        swing_ready_bars=swing_ready,
        cisd_ready_bars=cisd_ready,
        swing_and_cisd_same_bar=both_ready,
        atr_only_ready=best_all_other is not None,
        best_all_other_ratio=(
            None if best_all_other is None else str(best_all_other)
        ),
        best_all_other_ratio_band=_ratio_band(best_all_other),
        best_body_ready_ratio=None if best_body is None else str(best_body),
        best_body_ready_ratio_band=_ratio_band(best_body),
    )


def build_market_report(
    residual_root: Path,
    m1_root: Path,
    *,
    session: CapitalizerSession,
) -> tuple[dict[str, object], tuple[AtrReadinessRow, ...]]:
    frozen = _load_atr_blockers(residual_root)
    if not frozen:
        raise ValueError("ATR readiness found no frozen ATR blockers")

    all_bars = tuple(
        bar
        for bar in iter_cibo_m1(m1_root)
        if LOOKBACK_START <= bar.opened_at < WINDOW_END + timedelta(days=1)
    )
    if not all_bars:
        raise ValueError("ATR readiness found no native M1")
    symbol = all_bars[0].symbol
    if any(bar.symbol != symbol for bar in all_bars):
        raise ValueError("ATR readiness requires one market per M1 root")
    if any(str(row["symbol"]) != symbol for row in frozen):
        raise ValueError("ATR readiness residual/M1 symbol mismatch")

    m3 = _aggregate_tf(all_bars, minutes=3)
    m3_closes = tuple(item.closed_at for item in m3)
    m3_pivots = _pivots(m3)
    rows = tuple(
        _build_row(
            raw,
            symbol=symbol,
            session=session,
            m3=m3,
            m3_closes=m3_closes,
            m3_pivots=m3_pivots,
        )
        for raw in frozen
    )

    all_other_bands = Counter(
        item.best_all_other_ratio_band
        for item in rows
        if item.atr_only_ready
    )
    body_bands = Counter(item.best_body_ready_ratio_band for item in rows)
    return {
        "identity": IDENTITY,
        "symbol": symbol,
        "session": session.value,
        "atr_blockers": len(rows),
        "atr_only_ready": sum(item.atr_only_ready for item in rows),
        "swing_ready_any": sum(item.swing_ready_bars > 0 for item in rows),
        "cisd_ready_any": sum(item.cisd_ready_bars > 0 for item in rows),
        "same_bar_swing_cisd_any": sum(
            item.swing_and_cisd_same_bar > 0 for item in rows
        ),
        "best_all_other_ratio_bands": dict(sorted(all_other_bands.items())),
        "best_body_ready_ratio_bands": dict(sorted(body_bands.items())),
        "frozen_atr_multiplier": str(FROZEN_ATR_MULTIPLIER),
        "frozen_body_ratio_min": str(FROZEN_BODY_RATIO_MIN),
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
    report: dict[str, object],
    rows: tuple[AtrReadinessRow, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    symbol = str(report["symbol"]).lower()
    stem = f"capitalizer-{symbol}-v3-source-first-atr-readiness-atlas-2y-v1"
    (output / f"{stem}.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (output / f"{stem}-rows.jsonl").open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(asdict(row), sort_keys=True) + "\n")


def _load_reports(root: Path) -> list[dict[str, object]]:
    paths = sorted(
        root.rglob("capitalizer-*-v3-source-first-atr-readiness-atlas-2y-v1.json")
    )
    if len(paths) != 9:
        raise ValueError(f"ATR readiness matrix requires 9 reports, got {len(paths)}")
    return [dict(json.loads(path.read_text(encoding="utf-8"))) for path in paths]


def _sum_bands(
    reports: list[dict[str, object]],
    key: str,
) -> dict[str, int]:
    total: Counter[str] = Counter()
    for report in reports:
        raw = report[key]
        if not isinstance(raw, dict):
            raise ValueError(f"{key} must be a mapping")
        for name, value in raw.items():
            total[str(name)] += int(value)
    return dict(sorted(total.items()))


def build_matrix(root: Path) -> dict[str, object]:
    reports = _load_reports(root)
    total = sum(int(item["atr_blockers"]) for item in reports)
    return {
        "identity": MATRIX_IDENTITY,
        "market_count": 9,
        "atr_blockers": total,
        "atr_blocker_control_reproduced": total == EXPECTED_ATR_BLOCKERS,
        "atr_only_ready": sum(int(item["atr_only_ready"]) for item in reports),
        "swing_ready_any": sum(int(item["swing_ready_any"]) for item in reports),
        "cisd_ready_any": sum(int(item["cisd_ready_any"]) for item in reports),
        "same_bar_swing_cisd_any": sum(
            int(item["same_bar_swing_cisd_any"]) for item in reports
        ),
        "best_all_other_ratio_bands": _sum_bands(
            reports, "best_all_other_ratio_bands"
        ),
        "best_body_ready_ratio_bands": _sum_bands(
            reports, "best_body_ready_ratio_bands"
        ),
        "markets": sorted(reports, key=lambda item: str(item["symbol"])),
        "frozen_atr_multiplier": str(FROZEN_ATR_MULTIPLIER),
        "frozen_body_ratio_min": str(FROZEN_BODY_RATIO_MIN),
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


def write_matrix(report: dict[str, object], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    path = output / (
        "capitalizer-nine-market-v3-source-first-atr-readiness-atlas-2y-v1.json"
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
