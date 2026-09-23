"""2Y structural funnel atlas from SOURCE_FIRST MSS to WAIT5 executability.

This is diagnostic-only and reads no outcomes for admission.

Frozen inputs:
- exact SOURCE_FIRST MSS timestamps from the completed boundary-semantics census;
- immutable native CIBO M1;
- exact SOURCE_FIRST boundary helper;
- exact WAIT5 execution maturation helper.

Every SOURCE_FIRST MSS is assigned one terminal downstream reason:
- FVG_MISSING
- NORMAL_FILL_MISSING
- WAIT_STOP_INVALIDATED
- WAIT_NO_REFILL
- STOP_INVALID_GEOMETRY
- EXECUTABLE

The atlas intentionally evaluates every frozen SOURCE_FIRST MSS, not merely the
opportunities reached before runtime MAX3 ceilings.
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
from qore.infrastructure.trader_lab.capitalizer_v3_source_first_wait5_2y_v1 import (
    WAIT_MINUTES,
    _find_wait5_fill,
)

IDENTITY = "QORE_CAPITALIZER_V3_SOURCE_FIRST_WAIT5_FUNNEL_ATLAS_2Y_V1"
MATRIX_IDENTITY = (
    "QORE_CAPITALIZER_NINE_MARKET_V3_SOURCE_FIRST_WAIT5_FUNNEL_ATLAS_2Y_V1"
)
EXPECTED_SOURCE_FIRST_MSS = 2692
EXPECTED_WAIT5_RAW = 1003

FVG_MISSING = "FVG_MISSING"
NORMAL_FILL_MISSING = "NORMAL_FILL_MISSING"
WAIT_STOP_INVALIDATED = "WAIT_STOP_INVALIDATED"
WAIT_NO_REFILL = "WAIT_NO_REFILL"
STOP_INVALID_GEOMETRY = "STOP_INVALID_GEOMETRY"
EXECUTABLE = "EXECUTABLE"


@dataclass(frozen=True, slots=True)
class FunnelRow:
    symbol: str
    session: str
    operating_date: str
    side: str
    closeback_at: str
    sweep_at: str
    h1_deadline: str
    source_first_mss_at: str
    fvg_present: bool
    ob_fvg_overlap: bool | None
    normal_fill_present: bool
    normal_entry_at: str | None
    normal_entry_mode: str | None
    wait5_armed: bool
    wait5_status: str | None
    final_fill_at: str | None
    final_entry_mode: str | None
    valid_stop_geometry: bool | None
    terminal_reason: str
    outcome_used_for_admission: bool = False


def _load_semantics_rows(root: Path) -> tuple[dict[str, Any], ...]:
    paths = sorted(
        root.rglob(
            "capitalizer-*-v3-cisd-boundary-semantics-census-2y-v1-rows.jsonl"
        )
    )
    if len(paths) != 1:
        raise ValueError("funnel atlas requires one semantics ledger")
    rows: list[dict[str, Any]] = []
    with paths[0].open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            raw = json.loads(line)
            if not isinstance(raw, dict):
                raise ValueError("semantics row must be object")
            if raw.get("source_first_mss_at") is not None:
                rows.append(raw)
    return tuple(rows)


def _load_wait5_trade_count(root: Path) -> int:
    paths = sorted(
        root.rglob("capitalizer-*-v3-source-first-wait5-2y-v1-trades.jsonl")
    )
    if len(paths) != 1:
        raise ValueError("funnel atlas requires one WAIT5 market trade ledger")
    count = 0
    with paths[0].open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                count += 1
    return count


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


def _valid_stop(
    *,
    side: CapitalizerSide,
    entry_price: Decimal,
    stop_price: Decimal,
) -> bool:
    return bool(
        stop_price < entry_price
        if side is CapitalizerSide.LONG
        else stop_price > entry_price
    )


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
) -> FunnelRow:
    side = CapitalizerSide(str(raw["side"]))
    sweep_at = datetime.fromisoformat(str(raw["sweep_at"]))
    closeback_at = datetime.fromisoformat(str(raw["closeback_at"]))
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
        raise ValueError("SOURCE_FIRST MSS reconstruction mismatch")

    zone = v3._m1_causal_zone(execution, event=event)
    if zone is None:
        return FunnelRow(
            symbol=symbol,
            session=session.value,
            operating_date=str(raw["operating_date"]),
            side=side.value,
            closeback_at=closeback_at.isoformat(),
            sweep_at=sweep_at.isoformat(),
            h1_deadline=deadline.isoformat(),
            source_first_mss_at=frozen_mss_at.isoformat(),
            fvg_present=False,
            ob_fvg_overlap=None,
            normal_fill_present=False,
            normal_entry_at=None,
            normal_entry_mode=None,
            wait5_armed=False,
            wait5_status=None,
            final_fill_at=None,
            final_entry_mode=None,
            valid_stop_geometry=None,
            terminal_reason=FVG_MISSING,
        )

    overlap = zone.overlap_low is not None and zone.overlap_high is not None
    normal_fill = v3._find_m1_fill(
        execution,
        event=event,
        zone=zone,
        deadline=deadline,
    )
    if normal_fill is None:
        return FunnelRow(
            symbol=symbol,
            session=session.value,
            operating_date=str(raw["operating_date"]),
            side=side.value,
            closeback_at=closeback_at.isoformat(),
            sweep_at=sweep_at.isoformat(),
            h1_deadline=deadline.isoformat(),
            source_first_mss_at=frozen_mss_at.isoformat(),
            fvg_present=True,
            ob_fvg_overlap=overlap,
            normal_fill_present=False,
            normal_entry_at=None,
            normal_entry_mode=None,
            wait5_armed=False,
            wait5_status=None,
            final_fill_at=None,
            final_entry_mode=None,
            valid_stop_geometry=None,
            terminal_reason=NORMAL_FILL_MISSING,
        )

    normal_index, normal_price, normal_mode = normal_fill
    normal_entry_at = execution[normal_index].opened_at
    stop_price = _stop_price(
        side=side,
        broken_swing_price=event.broken_swing_price,
        buffer_price=buffer_price,
    )
    eligible_at = event.confirmed_at + timedelta(minutes=WAIT_MINUTES)
    wait_required = not overlap and normal_entry_at < eligible_at

    final_index = normal_index
    final_price = normal_price
    final_mode = normal_mode
    wait_status: str | None = None

    if wait_required:
        wait_fill, wait_status = _find_wait5_fill(
            execution,
            event=event,
            zone=zone,
            stop_price=stop_price,
            deadline=deadline,
        )
        if wait_fill is None:
            terminal = (
                WAIT_STOP_INVALIDATED
                if wait_status == "STOP_INVALIDATED_BEFORE_REFILL"
                else WAIT_NO_REFILL
            )
            return FunnelRow(
                symbol=symbol,
                session=session.value,
                operating_date=str(raw["operating_date"]),
                side=side.value,
                closeback_at=closeback_at.isoformat(),
                sweep_at=sweep_at.isoformat(),
                h1_deadline=deadline.isoformat(),
                source_first_mss_at=frozen_mss_at.isoformat(),
                fvg_present=True,
                ob_fvg_overlap=overlap,
                normal_fill_present=True,
                normal_entry_at=normal_entry_at.isoformat(),
                normal_entry_mode=normal_mode,
                wait5_armed=True,
                wait5_status=wait_status,
                final_fill_at=None,
                final_entry_mode=None,
                valid_stop_geometry=None,
                terminal_reason=terminal,
            )
        final_index, final_price, final_mode = wait_fill

    valid_stop = _valid_stop(
        side=side,
        entry_price=final_price,
        stop_price=stop_price,
    )
    return FunnelRow(
        symbol=symbol,
        session=session.value,
        operating_date=str(raw["operating_date"]),
        side=side.value,
        closeback_at=closeback_at.isoformat(),
        sweep_at=sweep_at.isoformat(),
        h1_deadline=deadline.isoformat(),
        source_first_mss_at=frozen_mss_at.isoformat(),
        fvg_present=True,
        ob_fvg_overlap=overlap,
        normal_fill_present=True,
        normal_entry_at=normal_entry_at.isoformat(),
        normal_entry_mode=normal_mode,
        wait5_armed=wait_required,
        wait5_status=wait_status,
        final_fill_at=execution[final_index].opened_at.isoformat(),
        final_entry_mode=final_mode,
        valid_stop_geometry=valid_stop,
        terminal_reason=EXECUTABLE if valid_stop else STOP_INVALID_GEOMETRY,
    )


def build_market_report(
    semantics_root: Path,
    wait5_root: Path,
    m1_root: Path,
    *,
    session: CapitalizerSession,
) -> tuple[dict[str, Any], tuple[FunnelRow, ...]]:
    semantics = _load_semantics_rows(semantics_root)
    if not semantics:
        raise ValueError("funnel atlas found no SOURCE_FIRST MSS rows")

    all_bars = tuple(iter_cibo_m1(m1_root))
    if not all_bars:
        raise ValueError("funnel atlas found no native M1")
    symbol = all_bars[0].symbol
    if any(bar.symbol != symbol for bar in all_bars):
        raise ValueError("funnel atlas requires one symbol per M1 root")
    if any(str(row["symbol"]) != symbol for row in semantics):
        raise ValueError("semantics/M1 symbol mismatch")

    m3 = _aggregate_tf(all_bars, minutes=3)
    m3_closes = tuple(item.closed_at for item in m3)
    m3_pivots = _pivots(m3)
    buffer_price = v3._stop_buffer(all_bars)
    execution_by_day, _reference_by_day = _index_day_inputs(
        all_bars,
        session=session,
    )

    rows: list[FunnelRow] = []
    for raw in semantics:
        operating_date = str(raw["operating_date"])
        execution = execution_by_day.get(operating_date, ())
        if not execution:
            raise ValueError("missing session execution bars for semantics row")
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
        sorted(
            rows,
            key=lambda item: (
                item.source_first_mss_at,
                item.symbol,
            ),
        )
    )
    terminal = Counter(item.terminal_reason for item in ordered)
    wait_status = Counter(
        item.wait5_status
        for item in ordered
        if item.wait5_status is not None
    )
    overlap = Counter(
        "OVERLAP" if item.ob_fvg_overlap else "NO_OVERLAP"
        for item in ordered
        if item.ob_fvg_overlap is not None
    )
    actual_wait5_raw = _load_wait5_trade_count(wait5_root)
    executable = terminal[EXECUTABLE]

    return {
        "identity": IDENTITY,
        "symbol": symbol,
        "session": session.value,
        "source_first_mss": len(ordered),
        "terminal_counts": dict(sorted(terminal.items())),
        "wait5_status_counts": dict(sorted(wait_status.items())),
        "overlap_counts": dict(sorted(overlap.items())),
        "fvg_confirmed": sum(1 for item in ordered if item.fvg_present),
        "normal_fill_present": sum(
            1 for item in ordered if item.normal_fill_present
        ),
        "wait5_armed": sum(1 for item in ordered if item.wait5_armed),
        "structurally_executable_before_runtime_ceiling": executable,
        "actual_wait5_raw_trades": actual_wait5_raw,
        "runtime_ceiling_or_ordering_gap": executable - actual_wait5_raw,
        "outcome_used_for_admission": False,
        "strategy_mutated": False,
        "diagnostic_only": True,
        "economic_candidate": False,
        "rule_promotion_allowed": False,
    }, ordered


def write_market(
    report: dict[str, Any],
    rows: tuple[FunnelRow, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    symbol = str(report["symbol"]).lower()
    stem = f"capitalizer-{symbol}-v3-source-first-wait5-funnel-atlas-2y-v1"
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
            "capitalizer-*-v3-source-first-wait5-funnel-atlas-2y-v1.json"
        )
    )
    if len(paths) != 9:
        raise ValueError(f"funnel matrix requires 9 reports, got {len(paths)}")
    return [dict(json.loads(path.read_text(encoding="utf-8"))) for path in paths]


def build_matrix(root: Path) -> dict[str, Any]:
    reports = _load_reports(root)
    terminal: Counter[str] = Counter()
    wait_status: Counter[str] = Counter()
    overlap: Counter[str] = Counter()
    per_session: dict[str, Counter[str]] = {}

    for report in reports:
        for key, value in dict(report["terminal_counts"]).items():
            terminal[str(key)] += int(value)
        for key, value in dict(report["wait5_status_counts"]).items():
            wait_status[str(key)] += int(value)
        for key, value in dict(report["overlap_counts"]).items():
            overlap[str(key)] += int(value)
        bucket = per_session.setdefault(str(report["session"]), Counter())
        bucket["source_first_mss"] += int(report["source_first_mss"])
        bucket["fvg_confirmed"] += int(report["fvg_confirmed"])
        bucket["normal_fill_present"] += int(report["normal_fill_present"])
        bucket["wait5_armed"] += int(report["wait5_armed"])
        bucket["executable"] += int(
            report["structurally_executable_before_runtime_ceiling"]
        )
        bucket["actual_wait5_raw"] += int(report["actual_wait5_raw_trades"])

    total_mss = sum(int(item["source_first_mss"]) for item in reports)
    fvg = sum(int(item["fvg_confirmed"]) for item in reports)
    normal_fill = sum(int(item["normal_fill_present"]) for item in reports)
    armed = sum(int(item["wait5_armed"]) for item in reports)
    executable = sum(
        int(item["structurally_executable_before_runtime_ceiling"])
        for item in reports
    )
    actual_raw = sum(int(item["actual_wait5_raw_trades"]) for item in reports)

    return {
        "identity": MATRIX_IDENTITY,
        "market_count": 9,
        "source_first_mss": total_mss,
        "source_first_mss_control_reproduced": (
            total_mss == EXPECTED_SOURCE_FIRST_MSS
        ),
        "fvg_confirmed": fvg,
        "fvg_missing": terminal[FVG_MISSING],
        "normal_fill_present": normal_fill,
        "normal_fill_missing": terminal[NORMAL_FILL_MISSING],
        "wait5_armed": armed,
        "wait5_stop_invalidated": terminal[WAIT_STOP_INVALIDATED],
        "wait5_no_refill": terminal[WAIT_NO_REFILL],
        "stop_invalid_geometry": terminal[STOP_INVALID_GEOMETRY],
        "structurally_executable_before_runtime_ceiling": executable,
        "actual_wait5_raw_trades": actual_raw,
        "actual_wait5_raw_control_reproduced": (
            actual_raw == EXPECTED_WAIT5_RAW
        ),
        "runtime_ceiling_or_ordering_gap": executable - actual_raw,
        "terminal_counts": dict(sorted(terminal.items())),
        "wait5_status_counts": dict(sorted(wait_status.items())),
        "overlap_counts": dict(sorted(overlap.items())),
        "per_session": {
            key: dict(value) for key, value in sorted(per_session.items())
        },
        "markets": sorted(reports, key=lambda item: str(item["symbol"])),
        "terminal_partition_reproduced": sum(terminal.values()) == total_mss,
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
        / "capitalizer-nine-market-v3-source-first-wait5-funnel-atlas-2y-v1.json"
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
    market.add_argument("wait5_root", type=Path)
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
            args.wait5_root,
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
