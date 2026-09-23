"""Outcome-free census of post-H1 OB/FVG retest -> CE50 maturation.

Population comes from the frozen 2Y fill-miss anatomy clean-late reservoir.

The question is structural:
when an old setup first obtains a clean post-H1 OB/FVG overlap retest, does the
same frozen FVG later mature to CE50 before the same structural stop invalidates
and before the frozen +60m observation boundary?

No PnL, target, exit outcome, market result or future selection is used.
No strategy rule is changed.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta
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
from qore.infrastructure.trader_lab.capitalizer_full_ict_density_scanner_1y_v1 import (
    _aggregate_h1,
)
from qore.infrastructure.trader_lab.capitalizer_strict_htf_gate_1y_v1 import (
    TFBar,
    _aggregate_tf,
    _index_day_inputs,
    _pivots,
)
from qore.infrastructure.trader_lab.capitalizer_v3_source_first_cisd_v1 import (
    find_source_first_m3_mss,
)
from qore.infrastructure.trader_lab.capitalizer_v3_source_first_wait5_late60_2y_v1 import (
    _reconstruct_closeback,
)

IDENTITY = (
    "QORE_CAPITALIZER_V3_SOURCE_FIRST_LATE_OVERLAP_CE_MATURATION_CENSUS_2Y_V1"
)
MATRIX_IDENTITY = (
    "QORE_CAPITALIZER_NINE_MARKET_V3_SOURCE_FIRST_"
    "LATE_OVERLAP_CE_MATURATION_CENSUS_2Y_V1"
)
EXPECTED_CLEAN_LATE = 376
EXTENSION_MINUTES = 60

CE_SAME_BAR = "CE_AVAILABLE_SAME_BAR"
CE_LATER = "CE_AVAILABLE_LATER"
STOP_BEFORE_CE = "STOP_INVALIDATED_BEFORE_CE"
NO_CE = "NO_CE_BEFORE_EXTENDED_DEADLINE"


@dataclass(frozen=True, slots=True)
class MaturationRow:
    symbol: str
    session: str
    operating_date: str
    side: str
    source_first_mss_at: str
    original_h1_deadline: str
    overlap_fill_at: str
    ce_status: str
    ce_at: str | None
    overlap_to_ce_minutes: int | None
    ce_stop_same_bar: bool | None
    outcome_used_for_admission: bool = False


def _load_anatomy_rows(
    root: Path,
) -> tuple[tuple[dict[str, Any], ...], tuple[dict[str, Any], ...]]:
    paths = sorted(
        root.rglob(
            "capitalizer-*-v3-source-first-fill-miss-anatomy-2y-v1-rows.jsonl"
        )
    )
    if len(paths) != 1:
        raise ValueError("CE maturation census requires one anatomy ledger")
    clean: list[dict[str, Any]] = []
    overlap: list[dict[str, Any]] = []
    with paths[0].open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            raw = json.loads(line)
            if not isinstance(raw, dict):
                raise ValueError("anatomy row must be object")
            if raw.get("late_status") != "LATE_FILL_WITHIN_60M_CLEAN":
                continue
            clean.append(raw)
            if raw.get("late_fill_mode") == "OB_FVG_RETEST":
                overlap.append(raw)
    return tuple(clean), tuple(overlap)


def _load_funnel_rows(root: Path) -> dict[tuple[str, str], dict[str, Any]]:
    paths = sorted(
        root.rglob(
            "capitalizer-*-v3-source-first-wait5-funnel-atlas-2y-v1-rows.jsonl"
        )
    )
    if len(paths) != 1:
        raise ValueError("CE maturation census requires one funnel ledger")
    result: dict[tuple[str, str], dict[str, Any]] = {}
    with paths[0].open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            raw = json.loads(line)
            if not isinstance(raw, dict):
                raise ValueError("funnel row must be object")
            result[
                (str(raw["operating_date"]), str(raw["source_first_mss_at"]))
            ] = raw
    return result


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


def _delay_band(minutes: int | None) -> str:
    if minutes is None:
        return "NONE"
    if minutes == 0:
        return "SAME_BAR"
    if minutes <= 5:
        return "01_05M"
    if minutes <= 15:
        return "06_15M"
    if minutes <= 30:
        return "16_30M"
    return "31_60M"


def _build_row(
    *,
    raw: dict[str, Any],
    frozen: dict[str, Any],
    symbol: str,
    session: CapitalizerSession,
    execution: tuple[CapitalizerM1Bar, ...],
    all_bars: tuple[CapitalizerM1Bar, ...],
    h1_swings: Any,
    m5: tuple[TFBar, ...],
    m5_closes: tuple[datetime, ...],
    m3: tuple[TFBar, ...],
    m3_closes: tuple[datetime, ...],
    m3_pivots: Any,
    buffer_price: Decimal,
    prior_session: Any,
) -> MaturationRow:
    operating_date = str(raw["operating_date"])
    operating_day = date.fromisoformat(operating_date)
    expected_mss = datetime.fromisoformat(str(raw["source_first_mss_at"]))
    overlap_fill_at = datetime.fromisoformat(str(raw["late_fill_at"]))
    original_deadline = datetime.fromisoformat(str(raw["h1_deadline"]))
    extended_deadline = original_deadline + timedelta(minutes=EXTENSION_MINUTES)
    side = CapitalizerSide(str(raw["side"]))

    closeback = _reconstruct_closeback(
        raw=frozen,
        operating_day=operating_day,
        execution=execution,
        all_bars=all_bars,
        h1_swings=h1_swings,
        m5=m5,
        m5_closes=m5_closes,
        prior_session=prior_session,
    )
    event = find_source_first_m3_mss(
        m3,
        m3_closes,
        m3_pivots,
        sweep_at=closeback.sweep_at,
        after=closeback.closeback_at,
        before=original_deadline,
        side=closeback.side,
    )
    if event is None or event.confirmed_at != expected_mss:
        raise ValueError("CE maturation SOURCE_FIRST MSS mismatch")

    zone = v3._m1_causal_zone(execution, event=event)
    if zone is None or zone.overlap_low is None or zone.overlap_high is None:
        raise ValueError("late overlap candidate lacks OB/FVG overlap")

    stop_price = (
        event.broken_swing_price - buffer_price
        if side is CapitalizerSide.LONG
        else event.broken_swing_price + buffer_price
    )
    ce = (zone.fvg_low + zone.fvg_high) / Decimal("2")
    found_overlap_bar = False

    for bar in execution:
        if bar.opened_at < overlap_fill_at:
            continue
        if bar.opened_at >= extended_deadline:
            break

        if bar.opened_at == overlap_fill_at:
            found_overlap_bar = True
            if not (
                bar.low
                <= (
                    zone.overlap_high
                    if side is CapitalizerSide.LONG
                    else zone.overlap_low
                )
                <= bar.high
            ):
                raise ValueError("frozen late overlap fill does not reconstruct")

        ce_touch = bar.low <= ce <= bar.high
        stop_hit = _stop_hit(bar, side=side, stop_price=stop_price)

        if ce_touch:
            delay = int((bar.opened_at - overlap_fill_at).total_seconds() // 60)
            return MaturationRow(
                symbol=symbol,
                session=session.value,
                operating_date=operating_date,
                side=side.value,
                source_first_mss_at=expected_mss.isoformat(),
                original_h1_deadline=original_deadline.isoformat(),
                overlap_fill_at=overlap_fill_at.isoformat(),
                ce_status=CE_SAME_BAR if delay == 0 else CE_LATER,
                ce_at=bar.opened_at.isoformat(),
                overlap_to_ce_minutes=delay,
                ce_stop_same_bar=stop_hit,
            )
        if stop_hit:
            return MaturationRow(
                symbol=symbol,
                session=session.value,
                operating_date=operating_date,
                side=side.value,
                source_first_mss_at=expected_mss.isoformat(),
                original_h1_deadline=original_deadline.isoformat(),
                overlap_fill_at=overlap_fill_at.isoformat(),
                ce_status=STOP_BEFORE_CE,
                ce_at=None,
                overlap_to_ce_minutes=None,
                ce_stop_same_bar=None,
            )

    if not found_overlap_bar:
        raise ValueError("late overlap fill timestamp missing from execution")

    return MaturationRow(
        symbol=symbol,
        session=session.value,
        operating_date=operating_date,
        side=side.value,
        source_first_mss_at=expected_mss.isoformat(),
        original_h1_deadline=original_deadline.isoformat(),
        overlap_fill_at=overlap_fill_at.isoformat(),
        ce_status=NO_CE,
        ce_at=None,
        overlap_to_ce_minutes=None,
        ce_stop_same_bar=None,
    )


def build_market_report(
    anatomy_root: Path,
    funnel_root: Path,
    m1_root: Path,
    *,
    session: CapitalizerSession,
) -> tuple[dict[str, Any], tuple[MaturationRow, ...]]:
    clean, overlap = _load_anatomy_rows(anatomy_root)
    frozen = _load_funnel_rows(funnel_root)
    if not overlap:
        raise ValueError("CE maturation census found no overlap late fills")

    first_time = min(
        datetime.fromisoformat(str(row["source_first_mss_at"])) for row in clean
    )
    last_time = max(
        datetime.fromisoformat(str(row["late_fill_at"])) for row in clean
    )
    all_bars = tuple(
        bar
        for bar in iter_cibo_m1(m1_root)
        if first_time - timedelta(days=2)
        <= bar.opened_at
        <= last_time + timedelta(minutes=65)
    )
    if not all_bars:
        raise ValueError("CE maturation census found no M1")
    symbol = all_bars[0].symbol
    if any(bar.symbol != symbol for bar in all_bars):
        raise ValueError("CE maturation census requires one symbol")

    h1 = _aggregate_h1(all_bars)
    h1_swings = v3._build_h1_swings(h1)
    m5 = _aggregate_tf(all_bars, minutes=5)
    m5_closes = tuple(item.closed_at for item in m5)
    m3 = _aggregate_tf(all_bars, minutes=3)
    m3_closes = tuple(item.closed_at for item in m3)
    m3_pivots = _pivots(m3)
    buffer_price = v3._stop_buffer(all_bars)
    execution_by_day, reference_by_day = _index_day_inputs(
        all_bars,
        session=session,
    )

    rows: list[MaturationRow] = []
    for raw in overlap:
        key = (str(raw["operating_date"]), str(raw["source_first_mss_at"]))
        funnel = frozen.get(key)
        if funnel is None:
            raise ValueError("CE maturation missing frozen funnel row")
        operating_date = str(raw["operating_date"])
        execution = execution_by_day.get(operating_date, ())
        if not execution:
            raise ValueError("CE maturation missing execution bars")
        rows.append(
            _build_row(
                raw=raw,
                frozen=funnel,
                symbol=symbol,
                session=session,
                execution=execution,
                all_bars=all_bars,
                h1_swings=h1_swings,
                m5=m5,
                m5_closes=m5_closes,
                m3=m3,
                m3_closes=m3_closes,
                m3_pivots=m3_pivots,
                buffer_price=buffer_price,
                prior_session=reference_by_day.get(operating_date),
            )
        )

    ordered = tuple(
        sorted(rows, key=lambda item: (item.overlap_fill_at, item.symbol))
    )
    statuses = Counter(item.ce_status for item in ordered)
    delays = Counter(_delay_band(item.overlap_to_ce_minutes) for item in ordered)
    return {
        "identity": IDENTITY,
        "symbol": symbol,
        "session": session.value,
        "clean_late_control": len(clean),
        "late_overlap_population": len(ordered),
        "ce_status_counts": dict(sorted(statuses.items())),
        "ce_delay_bands": dict(sorted(delays.items())),
        "ce_available": statuses[CE_SAME_BAR] + statuses[CE_LATER],
        "ce_stop_same_bar": sum(
            item.ce_stop_same_bar is True for item in ordered
        ),
        "outcome_used_for_admission": False,
        "strategy_mutated": False,
        "diagnostic_only": True,
        "economic_candidate": False,
        "rule_promotion_allowed": False,
    }, ordered


def write_market(
    report: dict[str, Any],
    rows: tuple[MaturationRow, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    symbol = str(report["symbol"]).lower()
    stem = (
        f"capitalizer-{symbol}-v3-source-first-late-overlap-"
        "ce-maturation-census-2y-v1"
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
            "capitalizer-*-v3-source-first-late-overlap-"
            "ce-maturation-census-2y-v1.json"
        )
    )
    if len(paths) != 9:
        raise ValueError(f"CE maturation matrix requires 9 reports, got {len(paths)}")
    return [dict(json.loads(path.read_text(encoding="utf-8"))) for path in paths]


def build_matrix(root: Path) -> dict[str, Any]:
    reports = _load_reports(root)
    statuses: Counter[str] = Counter()
    delays: Counter[str] = Counter()
    per_session: dict[str, Counter[str]] = {}
    for report in reports:
        for key, value in dict(report["ce_status_counts"]).items():
            statuses[str(key)] += int(value)
        for key, value in dict(report["ce_delay_bands"]).items():
            delays[str(key)] += int(value)
        bucket = per_session.setdefault(str(report["session"]), Counter())
        bucket["clean_late"] += int(report["clean_late_control"])
        bucket["late_overlap"] += int(report["late_overlap_population"])
        for key, value in dict(report["ce_status_counts"]).items():
            bucket[str(key)] += int(value)

    clean = sum(int(item["clean_late_control"]) for item in reports)
    overlap = sum(int(item["late_overlap_population"]) for item in reports)
    return {
        "identity": MATRIX_IDENTITY,
        "market_count": 9,
        "clean_late_population": clean,
        "clean_late_control_reproduced": clean == EXPECTED_CLEAN_LATE,
        "late_overlap_population": overlap,
        "ce_status_counts": dict(sorted(statuses.items())),
        "ce_delay_bands": dict(sorted(delays.items())),
        "ce_available": statuses[CE_SAME_BAR] + statuses[CE_LATER],
        "ce_stop_same_bar": sum(
            int(item["ce_stop_same_bar"]) for item in reports
        ),
        "per_session": {
            key: dict(value) for key, value in sorted(per_session.items())
        },
        "markets": sorted(reports, key=lambda item: str(item["symbol"])),
        "ce_status_partition_reproduced": sum(statuses.values()) == overlap,
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
        / "capitalizer-nine-market-v3-source-first-late-overlap-"
        "ce-maturation-census-2y-v1.json"
    )
    path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    market = sub.add_parser("market")
    market.add_argument("anatomy_root", type=Path)
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
            args.anatomy_root,
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
