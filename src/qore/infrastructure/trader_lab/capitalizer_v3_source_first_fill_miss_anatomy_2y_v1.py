"""2Y structural anatomy of SOURCE_FIRST WAIT5 NORMAL_FILL_MISSING events.

No outcomes are read. No entry rule is changed.

For every frozen funnel row whose terminal reason is NORMAL_FILL_MISSING, measure:
- how deeply price mitigated the frozen M1 FVG before the H1 deadline;
- whether OB/FVG overlap existed;
- minutes remaining in the H1 at MSS confirmation;
- whether the structural stop was hit before the H1 deadline;
- whether the exact frozen fill logic would have found a fill within the next
  60 minutes, and whether the structural stop had already invalidated first.

This is diagnostic-only evidence for the next causal research step.
"""

from __future__ import annotations

import argparse
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
    CapitalizerM1Bar,
    iter_cibo_m1,
)
from qore.infrastructure.trader_lab.capitalizer_contract import CapitalizerSession
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_strict_htf_gate_1y_v1 import (
    TFBar,
    _aggregate_tf,
    _index_day_inputs,
    _pivots,
)
from qore.infrastructure.trader_lab.capitalizer_v3_source_first_cisd_v1 import (
    find_source_first_m3_mss,
)
from qore.infrastructure.trader_lab.capitalizer_v3_source_first_wait5_funnel_atlas_2y_v1 import (
    NORMAL_FILL_MISSING,
)

IDENTITY = "QORE_CAPITALIZER_V3_SOURCE_FIRST_FILL_MISS_ANATOMY_2Y_V1"
MATRIX_IDENTITY = (
    "QORE_CAPITALIZER_NINE_MARKET_V3_SOURCE_FIRST_FILL_MISS_ANATOMY_2Y_V1"
)
EXPECTED_FILL_MISS = 1091

NO_TOUCH = "NO_FVG_TOUCH"
TOUCH_00_10 = "FVG_TOUCH_00_10"
TOUCH_10_25 = "FVG_TOUCH_10_25"
TOUCH_25_40 = "FVG_TOUCH_25_40"
TOUCH_40_50 = "FVG_TOUCH_40_50"

NO_LATE_FILL = "NO_LATE_FILL_WITHIN_60M"
LATE_FILL_CLEAN = "LATE_FILL_WITHIN_60M_CLEAN"
LATE_FILL_AFTER_STOP = "LATE_FILL_WITHIN_60M_AFTER_STOP"


@dataclass(frozen=True, slots=True)
class FillMissRow:
    symbol: str
    session: str
    operating_date: str
    side: str
    closeback_at: str
    source_first_mss_at: str
    h1_deadline: str
    ob_fvg_overlap: bool
    mitigation_depth: str
    mitigation_band: str
    minutes_remaining_at_mss: int
    stop_before_deadline: bool
    late_fill_at: str | None
    late_fill_mode: str | None
    late_fill_delay_minutes: int | None
    stop_before_late_fill: bool | None
    late_status: str
    outcome_used_for_admission: bool = False


def _load_fill_miss_rows(root: Path) -> tuple[dict[str, Any], ...]:
    paths = sorted(
        root.rglob(
            "capitalizer-*-v3-source-first-wait5-funnel-atlas-2y-v1-rows.jsonl"
        )
    )
    if len(paths) != 1:
        raise ValueError("fill-miss anatomy requires one funnel ledger")
    rows: list[dict[str, Any]] = []
    with paths[0].open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            raw = json.loads(line)
            if not isinstance(raw, dict):
                raise ValueError("funnel row must be object")
            if raw.get("terminal_reason") == NORMAL_FILL_MISSING:
                rows.append(raw)
    return tuple(rows)


def _stop_price(
    *,
    side: CapitalizerSide,
    broken_swing_price: Decimal,
    buffer_price: Decimal,
) -> Decimal:
    return (
        broken_swing_price - buffer_price
        if side is CapitalizerSide.LONG
        else broken_swing_price + buffer_price
    )


def _stop_hit(
    bar: CapitalizerM1Bar,
    *,
    side: CapitalizerSide,
    stop_price: Decimal,
) -> bool:
    return bool(
        bar.low <= stop_price
        if side is CapitalizerSide.LONG
        else bar.high >= stop_price
    )


def _mitigation_depth(
    execution: tuple[CapitalizerM1Bar, ...],
    *,
    event: v3.M3MssEvent,
    zone: v3.M1EntryZone,
    deadline: datetime,
) -> Decimal:
    width = zone.fvg_high - zone.fvg_low
    if width <= 0:
        raise ValueError("FVG width must be positive")
    depth = Decimal("0")
    for bar in execution:
        if bar.opened_at < event.confirmed_at:
            continue
        if bar.opened_at >= deadline:
            break
        current = (
            (zone.fvg_high - bar.low) / width
            if event.side is CapitalizerSide.LONG
            else (bar.high - zone.fvg_low) / width
        )
        current = max(Decimal("0"), min(Decimal("1"), current))
        depth = max(depth, current)
    return depth


def _depth_band(depth: Decimal) -> str:
    if depth <= 0:
        return NO_TOUCH
    if depth < Decimal("0.10"):
        return TOUCH_00_10
    if depth < Decimal("0.25"):
        return TOUCH_10_25
    if depth < Decimal("0.40"):
        return TOUCH_25_40
    return TOUCH_40_50


def _stop_before(
    execution: tuple[CapitalizerM1Bar, ...],
    *,
    event: v3.M3MssEvent,
    before: datetime,
    side: CapitalizerSide,
    stop_price: Decimal,
) -> bool:
    for bar in execution:
        if bar.opened_at < event.confirmed_at:
            continue
        if bar.opened_at >= before:
            break
        if _stop_hit(bar, side=side, stop_price=stop_price):
            return True
    return False


def _build_row(
    *,
    raw: dict[str, Any],
    symbol: str,
    session: CapitalizerSession,
    execution: tuple[CapitalizerM1Bar, ...],
    m3: tuple[TFBar, ...],
    m3_closes: tuple[datetime, ...],
    m3_pivots: Any,
    buffer_price: Decimal,
) -> FillMissRow:
    side = CapitalizerSide(str(raw["side"]))
    closeback_at = datetime.fromisoformat(str(raw["closeback_at"]))
    sweep_at = datetime.fromisoformat(str(raw["sweep_at"]))
    deadline = datetime.fromisoformat(str(raw["h1_deadline"]))
    frozen_mss_at = datetime.fromisoformat(str(raw["source_first_mss_at"]))

    event = find_source_first_m3_mss(
        m3,
        m3_closes,
        m3_pivots,
        sweep_at=sweep_at,
        after=closeback_at,
        before=deadline,
        side=side,
    )
    if event is None or event.confirmed_at != frozen_mss_at:
        raise ValueError("fill-miss SOURCE_FIRST MSS reconstruction mismatch")

    zone = v3._m1_causal_zone(execution, event=event)
    if zone is None:
        raise ValueError("fill-miss row unexpectedly lacks FVG")
    if v3._find_m1_fill(
        execution,
        event=event,
        zone=zone,
        deadline=deadline,
    ) is not None:
        raise ValueError("fill-miss row unexpectedly has in-H1 fill")

    overlap = zone.overlap_low is not None and zone.overlap_high is not None
    depth = _mitigation_depth(
        execution,
        event=event,
        zone=zone,
        deadline=deadline,
    )
    if depth >= Decimal("0.5"):
        raise ValueError("fill-miss mitigation unexpectedly reached CE")

    stop_price = _stop_price(
        side=side,
        broken_swing_price=event.broken_swing_price,
        buffer_price=buffer_price,
    )
    stop_before_deadline = _stop_before(
        execution,
        event=event,
        before=deadline,
        side=side,
        stop_price=stop_price,
    )

    extended_deadline = deadline + timedelta(minutes=60)
    late_fill = v3._find_m1_fill(
        execution,
        event=event,
        zone=zone,
        deadline=extended_deadline,
    )
    late_fill_at: datetime | None = None
    late_fill_mode: str | None = None
    late_delay: int | None = None
    stop_before_late: bool | None = None
    late_status = NO_LATE_FILL

    if late_fill is not None:
        late_index, _late_price, late_fill_mode = late_fill
        late_fill_at = execution[late_index].opened_at
        if late_fill_at < deadline:
            raise ValueError("late-fill diagnostic found pre-deadline fill")
        late_delay = int((late_fill_at - deadline).total_seconds() // 60)
        stop_before_late = _stop_before(
            execution,
            event=event,
            before=late_fill_at,
            side=side,
            stop_price=stop_price,
        )
        late_status = (
            LATE_FILL_AFTER_STOP if stop_before_late else LATE_FILL_CLEAN
        )

    return FillMissRow(
        symbol=symbol,
        session=session.value,
        operating_date=str(raw["operating_date"]),
        side=side.value,
        closeback_at=closeback_at.isoformat(),
        source_first_mss_at=frozen_mss_at.isoformat(),
        h1_deadline=deadline.isoformat(),
        ob_fvg_overlap=overlap,
        mitigation_depth=str(depth),
        mitigation_band=_depth_band(depth),
        minutes_remaining_at_mss=int(
            (deadline - event.confirmed_at).total_seconds() // 60
        ),
        stop_before_deadline=stop_before_deadline,
        late_fill_at=None if late_fill_at is None else late_fill_at.isoformat(),
        late_fill_mode=late_fill_mode,
        late_fill_delay_minutes=late_delay,
        stop_before_late_fill=stop_before_late,
        late_status=late_status,
    )


def _remaining_band(minutes: int) -> str:
    if minutes <= 5:
        return "00_05M"
    if minutes <= 15:
        return "06_15M"
    if minutes <= 30:
        return "16_30M"
    if minutes <= 45:
        return "31_45M"
    return "46M_PLUS"


def _late_delay_band(minutes: int | None) -> str:
    if minutes is None:
        return "NONE"
    if minutes <= 5:
        return "00_05M"
    if minutes <= 15:
        return "06_15M"
    if minutes <= 30:
        return "16_30M"
    return "31_60M"


def build_market_report(
    funnel_root: Path,
    m1_root: Path,
    *,
    session: CapitalizerSession,
) -> tuple[dict[str, Any], tuple[FillMissRow, ...]]:
    frozen = _load_fill_miss_rows(funnel_root)
    if not frozen:
        raise ValueError("fill-miss anatomy found no frozen rows")

    first_sweep = min(
        datetime.fromisoformat(str(row["sweep_at"])) for row in frozen
    )
    last_deadline = max(
        datetime.fromisoformat(str(row["h1_deadline"])) for row in frozen
    )
    scan_start = first_sweep - timedelta(days=2)
    scan_end = last_deadline + timedelta(minutes=61)
    all_bars = tuple(
        bar
        for bar in iter_cibo_m1(m1_root)
        if scan_start <= bar.opened_at <= scan_end
    )
    if not all_bars:
        raise ValueError("fill-miss anatomy found no native M1")
    symbol = all_bars[0].symbol
    if any(bar.symbol != symbol for bar in all_bars):
        raise ValueError("fill-miss anatomy requires one symbol per M1 root")
    if any(str(row["symbol"]) != symbol for row in frozen):
        raise ValueError("funnel/M1 symbol mismatch")

    m3 = _aggregate_tf(all_bars, minutes=3)
    m3_closes = tuple(item.closed_at for item in m3)
    m3_pivots = _pivots(m3)
    buffer_price = v3._stop_buffer(all_bars)
    execution_by_day, _ = _index_day_inputs(all_bars, session=session)

    rows: list[FillMissRow] = []
    for raw in frozen:
        execution = execution_by_day.get(str(raw["operating_date"]), ())
        if not execution:
            raise ValueError("missing execution bars for fill-miss row")
        rows.append(
            _build_row(
                raw=raw,
                symbol=symbol,
                session=session,
                execution=execution,
                m3=m3,
                m3_closes=m3_closes,
                m3_pivots=m3_pivots,
                buffer_price=buffer_price,
            )
        )

    ordered = tuple(
        sorted(rows, key=lambda item: (item.source_first_mss_at, item.symbol))
    )
    mitigation = Counter(item.mitigation_band for item in ordered)
    remaining = Counter(
        _remaining_band(item.minutes_remaining_at_mss) for item in ordered
    )
    late_status = Counter(item.late_status for item in ordered)
    late_delay = Counter(
        _late_delay_band(item.late_fill_delay_minutes)
        for item in ordered
        if item.late_fill_delay_minutes is not None
    )
    overlap = Counter(
        "OVERLAP" if item.ob_fvg_overlap else "NO_OVERLAP"
        for item in ordered
    )

    return {
        "identity": IDENTITY,
        "symbol": symbol,
        "session": session.value,
        "fill_miss_population": len(ordered),
        "mitigation_bands": dict(sorted(mitigation.items())),
        "minutes_remaining_bands": dict(sorted(remaining.items())),
        "overlap_counts": dict(sorted(overlap.items())),
        "stop_before_deadline": sum(
            1 for item in ordered if item.stop_before_deadline
        ),
        "late_status_counts": dict(sorted(late_status.items())),
        "late_delay_bands": dict(sorted(late_delay.items())),
        "late_fill_clean": late_status[LATE_FILL_CLEAN],
        "late_fill_after_stop": late_status[LATE_FILL_AFTER_STOP],
        "no_late_fill": late_status[NO_LATE_FILL],
        "outcome_used_for_admission": False,
        "strategy_mutated": False,
        "diagnostic_only": True,
        "economic_candidate": False,
        "rule_promotion_allowed": False,
    }, ordered


def write_market(
    report: dict[str, Any],
    rows: tuple[FillMissRow, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    symbol = str(report["symbol"]).lower()
    stem = f"capitalizer-{symbol}-v3-source-first-fill-miss-anatomy-2y-v1"
    (output / f"{stem}.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (output / f"{stem}-rows.jsonl").open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(asdict(row), sort_keys=True) + "\n")


def _load_reports(root: Path) -> list[dict[str, Any]]:
    paths = sorted(
        root.rglob("capitalizer-*-v3-source-first-fill-miss-anatomy-2y-v1.json")
    )
    if len(paths) != 9:
        raise ValueError(f"fill-miss matrix requires 9 reports, got {len(paths)}")
    return [dict(json.loads(path.read_text(encoding="utf-8"))) for path in paths]


def build_matrix(root: Path) -> dict[str, Any]:
    reports = _load_reports(root)
    mitigation: Counter[str] = Counter()
    remaining: Counter[str] = Counter()
    overlap: Counter[str] = Counter()
    late_status: Counter[str] = Counter()
    late_delay: Counter[str] = Counter()
    per_session: dict[str, Counter[str]] = {}

    for report in reports:
        for key, value in dict(report["mitigation_bands"]).items():
            mitigation[str(key)] += int(value)
        for key, value in dict(report["minutes_remaining_bands"]).items():
            remaining[str(key)] += int(value)
        for key, value in dict(report["overlap_counts"]).items():
            overlap[str(key)] += int(value)
        for key, value in dict(report["late_status_counts"]).items():
            late_status[str(key)] += int(value)
        for key, value in dict(report["late_delay_bands"]).items():
            late_delay[str(key)] += int(value)
        bucket = per_session.setdefault(str(report["session"]), Counter())
        bucket["fill_miss"] += int(report["fill_miss_population"])
        bucket["stop_before_deadline"] += int(report["stop_before_deadline"])
        bucket["late_fill_clean"] += int(report["late_fill_clean"])
        bucket["late_fill_after_stop"] += int(report["late_fill_after_stop"])
        bucket["no_late_fill"] += int(report["no_late_fill"])

    population = sum(int(item["fill_miss_population"]) for item in reports)
    return {
        "identity": MATRIX_IDENTITY,
        "market_count": 9,
        "fill_miss_population": population,
        "fill_miss_control_reproduced": population == EXPECTED_FILL_MISS,
        "mitigation_bands": dict(sorted(mitigation.items())),
        "minutes_remaining_bands": dict(sorted(remaining.items())),
        "overlap_counts": dict(sorted(overlap.items())),
        "stop_before_deadline": sum(
            int(item["stop_before_deadline"]) for item in reports
        ),
        "late_status_counts": dict(sorted(late_status.items())),
        "late_delay_bands": dict(sorted(late_delay.items())),
        "late_fill_clean": late_status[LATE_FILL_CLEAN],
        "late_fill_after_stop": late_status[LATE_FILL_AFTER_STOP],
        "no_late_fill": late_status[NO_LATE_FILL],
        "per_session": {
            key: dict(value) for key, value in sorted(per_session.items())
        },
        "markets": sorted(reports, key=lambda item: str(item["symbol"])),
        "late_status_partition_reproduced": (
            sum(late_status.values()) == population
        ),
        "outcome_used_for_admission": False,
        "strategy_mutated": False,
        "diagnostic_only": True,
        "economic_candidate": False,
        "rule_promotion_allowed": False,
    }


def write_matrix(report: dict[str, Any], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    path = (
        output
        / "capitalizer-nine-market-v3-source-first-fill-miss-anatomy-2y-v1.json"
    )
    path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    market = sub.add_parser("market")
    market.add_argument("funnel_root", type=Path)
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
            args.funnel_root,
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
