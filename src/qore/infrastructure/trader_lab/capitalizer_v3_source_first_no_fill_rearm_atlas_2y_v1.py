"""Outcome-free rearm atlas for frozen NORMAL_FILL_MISSING setups.

Population: the 1,091 SOURCE_FIRST funnel rows whose original causal M1 FVG
exists but never receives a normal fill before the original H1 deadline.

This atlas does NOT extend, retime, or reuse the original unfilled FVG.
It asks whether density can be recovered only through a completely NEW causal
sequence inside the same frozen H1 context:

1. after the original setup is fully confirmed by its SOURCE_FIRST MSS, a new
   raid must exceed the original sweep extreme of the same frozen liquidity reference;
2. a new completed M5 closeback must cross back through that reference;
3. a new SOURCE_FIRST M3 MSS must confirm on the same side;
4. a new causal M1 OB/FVG zone must exist for that new MSS;
5. a new normal M1 fill must occur after that new MSS and before the original
   H1 deadline;
6. the frozen V3 broken-swing stop + same market buffer must be valid.

No lifecycle outcome, realized R, stop/target result, or PnL is read.
This is a structural reservoir atlas only.
"""

from __future__ import annotations

import argparse
import json
from bisect import bisect_right
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
from qore.infrastructure.trader_lab.capitalizer_v3_cisd_boundary_semantics_census_2y_v1 import (
    _reconstruct_closebacks,
)
from qore.infrastructure.trader_lab.capitalizer_v3_source_first_cisd_v1 import (
    find_source_first_m3_mss,
)

IDENTITY = "QORE_CAPITALIZER_V3_SOURCE_FIRST_NO_FILL_REARM_ATLAS_2Y_V1"
MATRIX_IDENTITY = (
    "QORE_CAPITALIZER_NINE_MARKET_V3_SOURCE_FIRST_NO_FILL_REARM_ATLAS_2Y_V1"
)
EXPECTED_NORMAL_FILL_MISSING = 1091
NORMAL_FILL_MISSING = "NORMAL_FILL_MISSING"


@dataclass(frozen=True, slots=True)
class NoFillRearmRow:
    symbol: str
    session: str
    operating_date: str
    side: str
    original_closeback_at: str
    original_mss_at: str
    original_fvg_confirmed_at: str
    original_h1_deadline: str
    new_raid_at: str | None
    new_closeback_at: str | None
    new_mss_at: str | None
    new_fvg_confirmed_at: str | None
    new_fill_at: str | None
    new_entry_mode: str | None
    new_stop_valid_geometry: bool | None
    terminal_stage: str
    outcome_fields_read: bool = False


def _aware(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _load_no_fill(root: Path) -> tuple[dict[str, Any], ...]:
    paths = sorted(
        root.rglob(
            "capitalizer-*-v3-source-first-wait5-funnel-atlas-2y-v1-rows.jsonl"
        )
    )
    if len(paths) != 1:
        raise ValueError("no-fill rearm atlas requires one funnel ledger per market")
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


def _new_raid(
    execution: tuple[CapitalizerM1Bar, ...],
    *,
    after: datetime,
    before: datetime,
    liquidity_kind: str,
    original_extreme: Decimal,
) -> CapitalizerM1Bar | None:
    for bar in execution:
        if bar.opened_at < after:
            continue
        if bar.opened_at >= before:
            break
        if liquidity_kind == "HIGH" and bar.high > original_extreme:
            return bar
        if liquidity_kind == "LOW" and bar.low < original_extreme:
            return bar
    return None


def _new_closeback(
    m5: tuple[TFBar, ...],
    m5_closes: tuple[datetime, ...],
    *,
    raid_at: datetime,
    deadline: datetime,
    liquidity_kind: str,
    liquidity_price: Decimal,
) -> datetime | None:
    start = bisect_right(m5_closes, raid_at)
    end = bisect_right(m5_closes, deadline)
    for bar in m5[start:end]:
        closed_back = (
            bar.source.close < liquidity_price
            if liquidity_kind == "HIGH"
            else bar.source.close > liquidity_price
        )
        if closed_back:
            return bar.closed_at
    return None


def _terminal(
    *,
    raw: dict[str, Any],
    original_fvg_at: datetime,
    new_raid_at: datetime | None = None,
    new_closeback_at: datetime | None = None,
    new_mss_at: datetime | None = None,
    new_fvg_at: datetime | None = None,
    new_fill_at: datetime | None = None,
    new_entry_mode: str | None = None,
    new_stop_valid: bool | None = None,
    terminal_stage: str,
) -> NoFillRearmRow:
    return NoFillRearmRow(
        symbol=str(raw["symbol"]),
        session=str(raw["session"]),
        operating_date=str(raw["operating_date"]),
        side=str(raw["side"]),
        original_closeback_at=str(raw["closeback_at"]),
        original_mss_at=str(raw["source_first_mss_at"]),
        original_fvg_confirmed_at=original_fvg_at.isoformat(),
        original_h1_deadline=str(raw["h1_deadline"]),
        new_raid_at=None if new_raid_at is None else new_raid_at.isoformat(),
        new_closeback_at=(
            None if new_closeback_at is None else new_closeback_at.isoformat()
        ),
        new_mss_at=None if new_mss_at is None else new_mss_at.isoformat(),
        new_fvg_confirmed_at=(
            None if new_fvg_at is None else new_fvg_at.isoformat()
        ),
        new_fill_at=None if new_fill_at is None else new_fill_at.isoformat(),
        new_entry_mode=new_entry_mode,
        new_stop_valid_geometry=new_stop_valid,
        terminal_stage=terminal_stage,
    )


def _build_row(
    *,
    raw: dict[str, Any],
    execution: tuple[CapitalizerM1Bar, ...],
    closeback: v3.SweepCloseback,
    m5: tuple[TFBar, ...],
    m5_closes: tuple[datetime, ...],
    m3: tuple[TFBar, ...],
    m3_closes: tuple[datetime, ...],
    m3_pivots: Any,
    buffer_price: Decimal,
) -> NoFillRearmRow:
    side = CapitalizerSide(str(raw["side"]))
    deadline = _aware(str(raw["h1_deadline"]))
    frozen_mss_at = _aware(str(raw["source_first_mss_at"]))

    original_mss = find_source_first_m3_mss(
        m3,
        m3_closes,
        m3_pivots,
        sweep_at=closeback.sweep_at,
        after=closeback.closeback_at,
        before=deadline,
        side=side,
    )
    if original_mss is None or original_mss.confirmed_at != frozen_mss_at:
        raise ValueError("no-fill rearm original MSS reconstruction mismatch")

    original_zone = v3._m1_causal_zone(execution, event=original_mss)
    if original_zone is None:
        raise ValueError("NORMAL_FILL_MISSING row lost original causal FVG")
    if (
        v3._find_m1_fill(
            execution,
            event=original_mss,
            zone=original_zone,
            deadline=deadline,
        )
        is not None
    ):
        raise ValueError("NORMAL_FILL_MISSING row unexpectedly has original fill")

    raid = _new_raid(
        execution,
        after=original_mss.confirmed_at,
        before=deadline,
        liquidity_kind=closeback.reference.kind,
        original_extreme=closeback.sweep_extreme,
    )
    if raid is None:
        return _terminal(
            raw=raw,
            original_fvg_at=original_zone.fvg_confirmed_at,
            terminal_stage="NO_NEW_RAID",
        )

    closeback_at = _new_closeback(
        m5,
        m5_closes,
        raid_at=raid.opened_at,
        deadline=deadline,
        liquidity_kind=closeback.reference.kind,
        liquidity_price=closeback.reference.price,
    )
    if closeback_at is None:
        return _terminal(
            raw=raw,
            original_fvg_at=original_zone.fvg_confirmed_at,
            new_raid_at=raid.opened_at,
            terminal_stage="NEW_RAID_NO_CLOSEBACK",
        )

    new_mss = find_source_first_m3_mss(
        m3,
        m3_closes,
        m3_pivots,
        sweep_at=raid.opened_at,
        after=closeback_at,
        before=deadline,
        side=side,
    )
    if new_mss is None:
        return _terminal(
            raw=raw,
            original_fvg_at=original_zone.fvg_confirmed_at,
            new_raid_at=raid.opened_at,
            new_closeback_at=closeback_at,
            terminal_stage="NEW_CLOSEBACK_NO_MSS",
        )

    new_zone = v3._m1_causal_zone(execution, event=new_mss)
    if new_zone is None:
        return _terminal(
            raw=raw,
            original_fvg_at=original_zone.fvg_confirmed_at,
            new_raid_at=raid.opened_at,
            new_closeback_at=closeback_at,
            new_mss_at=new_mss.confirmed_at,
            terminal_stage="NEW_MSS_NO_FVG",
        )

    new_fill = v3._find_m1_fill(
        execution,
        event=new_mss,
        zone=new_zone,
        deadline=deadline,
    )
    if new_fill is None:
        return _terminal(
            raw=raw,
            original_fvg_at=original_zone.fvg_confirmed_at,
            new_raid_at=raid.opened_at,
            new_closeback_at=closeback_at,
            new_mss_at=new_mss.confirmed_at,
            new_fvg_at=new_zone.fvg_confirmed_at,
            terminal_stage="NEW_FVG_NO_FILL",
        )

    fill_index, entry_price, entry_mode = new_fill
    fill_at = execution[fill_index].opened_at
    stop_price = (
        new_mss.broken_swing_price - buffer_price
        if side is CapitalizerSide.LONG
        else new_mss.broken_swing_price + buffer_price
    )
    valid_stop = (
        stop_price < entry_price
        if side is CapitalizerSide.LONG
        else stop_price > entry_price
    )
    return _terminal(
        raw=raw,
        original_fvg_at=original_zone.fvg_confirmed_at,
        new_raid_at=raid.opened_at,
        new_closeback_at=closeback_at,
        new_mss_at=new_mss.confirmed_at,
        new_fvg_at=new_zone.fvg_confirmed_at,
        new_fill_at=fill_at,
        new_entry_mode=entry_mode,
        new_stop_valid=valid_stop,
        terminal_stage=(
            "REARM_EXECUTABLE"
            if valid_stop
            else "REARM_STOP_INVALID_GEOMETRY"
        ),
    )


def build_market_report(
    funnel_root: Path,
    m1_root: Path,
    *,
    session: CapitalizerSession,
) -> tuple[dict[str, Any], tuple[NoFillRearmRow, ...]]:
    frozen = _load_no_fill(funnel_root)
    if not frozen:
        raise ValueError("no-fill rearm atlas found no frozen rows")

    first = min(_aware(str(row["sweep_at"])) for row in frozen) - timedelta(days=2)
    last = max(_aware(str(row["h1_deadline"])) for row in frozen) + timedelta(days=1)
    all_bars = tuple(
        bar
        for bar in iter_cibo_m1(m1_root)
        if first <= bar.opened_at <= last
    )
    if not all_bars:
        raise ValueError("no-fill rearm atlas found no native M1")
    symbol = all_bars[0].symbol
    if any(bar.symbol != symbol for bar in all_bars):
        raise ValueError("no-fill rearm atlas requires one market per M1 root")
    if any(str(row["symbol"]) != symbol for row in frozen):
        raise ValueError("no-fill rearm funnel/M1 symbol mismatch")
    if any(str(row["session"]) != session.value for row in frozen):
        raise ValueError("no-fill rearm session mismatch")

    closebacks = _reconstruct_closebacks(all_bars=all_bars, session=session)
    m5 = _aggregate_tf(all_bars, minutes=5)
    m5_closes = tuple(item.closed_at for item in m5)
    m3 = _aggregate_tf(all_bars, minutes=3)
    m3_closes = tuple(item.closed_at for item in m3)
    m3_pivots = _pivots(m3)
    buffer_price = v3._stop_buffer(all_bars)
    execution_by_day, _ = _index_day_inputs(all_bars, session=session)

    rows: list[NoFillRearmRow] = []
    for raw in frozen:
        closeback = closebacks.get(str(raw["closeback_at"]))
        if closeback is None:
            raise ValueError("no-fill rearm missing reconstructed closeback")
        execution = execution_by_day.get(str(raw["operating_date"]), ())
        if not execution:
            raise ValueError("no-fill rearm missing execution day")
        rows.append(
            _build_row(
                raw=raw,
                execution=execution,
                closeback=closeback,
                m5=m5,
                m5_closes=m5_closes,
                m3=m3,
                m3_closes=m3_closes,
                m3_pivots=m3_pivots,
                buffer_price=buffer_price,
            )
        )

    ordered = tuple(
        sorted(
            rows,
            key=lambda item: (item.original_fvg_confirmed_at, item.symbol),
        )
    )
    stages = Counter(item.terminal_stage for item in ordered)
    return {
        "identity": IDENTITY,
        "symbol": symbol,
        "session": session.value,
        "normal_fill_missing_population": len(ordered),
        "terminal_stages": dict(sorted(stages.items())),
        "new_raid": sum(item.new_raid_at is not None for item in ordered),
        "new_closeback": sum(item.new_closeback_at is not None for item in ordered),
        "new_mss": sum(item.new_mss_at is not None for item in ordered),
        "new_fvg": sum(item.new_fvg_confirmed_at is not None for item in ordered),
        "new_fill": sum(item.new_fill_at is not None for item in ordered),
        "rearm_executable": stages["REARM_EXECUTABLE"],
        "original_fvg_reuse_forbidden": True,
        "same_reference_requires_new_extreme": True,
        "new_raid_required": True,
        "new_closeback_required": True,
        "new_source_first_mss_required": True,
        "new_causal_fvg_required": True,
        "new_normal_fill_required": True,
        "valid_stop_geometry_required": True,
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
    rows: tuple[NoFillRearmRow, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    symbol = str(report["symbol"]).lower()
    stem = f"capitalizer-{symbol}-v3-source-first-no-fill-rearm-atlas-2y-v1"
    (output / f"{stem}.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (output / f"{stem}-rows.jsonl").open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(asdict(row), sort_keys=True) + "\n")


def _load_reports(root: Path) -> list[dict[str, Any]]:
    paths = sorted(
        root.rglob("capitalizer-*-v3-source-first-no-fill-rearm-atlas-2y-v1.json")
    )
    if len(paths) != 9:
        raise ValueError(f"no-fill rearm matrix requires 9 reports, got {len(paths)}")
    return [dict(json.loads(path.read_text(encoding="utf-8"))) for path in paths]


def build_matrix(root: Path) -> dict[str, Any]:
    reports = _load_reports(root)
    total = sum(int(item["normal_fill_missing_population"]) for item in reports)
    stages: Counter[str] = Counter()
    for report in reports:
        for key, value in dict(report["terminal_stages"]).items():
            stages[str(key)] += int(value)
    return {
        "identity": MATRIX_IDENTITY,
        "market_count": 9,
        "normal_fill_missing_population": total,
        "normal_fill_missing_control_reproduced": (
            total == EXPECTED_NORMAL_FILL_MISSING
        ),
        "terminal_stages": dict(sorted(stages.items())),
        "new_raid": sum(int(item["new_raid"]) for item in reports),
        "new_closeback": sum(int(item["new_closeback"]) for item in reports),
        "new_mss": sum(int(item["new_mss"]) for item in reports),
        "new_fvg": sum(int(item["new_fvg"]) for item in reports),
        "new_fill": sum(int(item["new_fill"]) for item in reports),
        "rearm_executable": sum(int(item["rearm_executable"]) for item in reports),
        "markets": sorted(reports, key=lambda item: str(item["symbol"])),
        "original_fvg_reuse_forbidden": True,
        "same_reference_requires_new_extreme": True,
        "new_raid_required": True,
        "new_closeback_required": True,
        "new_source_first_mss_required": True,
        "new_causal_fvg_required": True,
        "new_normal_fill_required": True,
        "valid_stop_geometry_required": True,
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
    path = output / "capitalizer-nine-market-v3-source-first-no-fill-rearm-atlas-2y-v1.json"
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
