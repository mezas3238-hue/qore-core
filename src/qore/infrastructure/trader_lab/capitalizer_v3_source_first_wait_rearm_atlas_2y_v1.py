"""Outcome-free rearm atlas for stale WAIT5 setups.

Population: the frozen SOURCE_FIRST + WAIT5 raw trades whose entry mode is
FVG_CE_50_WAIT5. The No-Rearm candidate correctly abstains from these stale
same-setup CE refills.

This atlas asks whether density can be recovered causally with NEW evidence
before the original H1 deadline. A rearm candidate requires, in order:

1. after MSS+5m, a new raid beyond the original sweep extreme of the same
   frozen liquidity reference;
2. a new completed M5 closeback through that frozen liquidity price;
3. a new SOURCE_FIRST M3 MSS on the same side after that closeback;
4. a new causal M1 OB/FVG zone linked to that new MSS;
5. a normal causal M1 fill after the new MSS;
6. valid frozen V3 stop geometry using the new MSS broken swing and the same
   market buffer.

No lifecycle outcome, realized R, target result, stop result, or PnL is read.
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
from qore.infrastructure.trader_lab.capitalizer_v3_source_first_cisd_v1 import (
    find_source_first_m3_mss,
)

IDENTITY = "QORE_CAPITALIZER_V3_SOURCE_FIRST_WAIT_REARM_ATLAS_2Y_V1"
MATRIX_IDENTITY = "QORE_CAPITALIZER_NINE_MARKET_V3_SOURCE_FIRST_WAIT_REARM_ATLAS_2Y_V1"
WAIT_MINUTES = 5
EXPECTED_STALE_WAIT5_RAW = 199


@dataclass(frozen=True, slots=True)
class RearmRow:
    symbol: str
    session: str
    operating_date: str
    side: str
    original_mss_at: str
    original_stale_fill_at: str
    original_h1_deadline: str
    rearm_eligible_at: str
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


def _load_stale_wait5(root: Path) -> tuple[v3.V3Trade, ...]:
    paths = sorted(
        root.rglob("capitalizer-*-v3-source-first-wait5-2y-v1-trades.jsonl")
    )
    if len(paths) != 1:
        raise ValueError("rearm atlas requires one frozen WAIT5 trade ledger per market")
    rows: list[v3.V3Trade] = []
    with paths[0].open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            trade = v3.V3Trade(**json.loads(line))
            if trade.entry_mode == "FVG_CE_50_WAIT5":
                rows.append(trade)
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


def _build_row(
    *,
    trade: v3.V3Trade,
    execution: tuple[CapitalizerM1Bar, ...],
    m5: tuple[TFBar, ...],
    m5_closes: tuple[datetime, ...],
    m3: tuple[TFBar, ...],
    m3_closes: tuple[datetime, ...],
    m3_pivots: Any,
) -> RearmRow:
    original_mss = _aware(trade.m3_mss_at)
    deadline = _aware(trade.h1_deadline)
    eligible_at = original_mss + timedelta(minutes=WAIT_MINUTES)
    side = CapitalizerSide(trade.side)
    original_extreme = Decimal(trade.h1_sweep_extreme)
    liquidity_price = Decimal(trade.liquidity_price)

    raid = _new_raid(
        execution,
        after=eligible_at,
        before=deadline,
        liquidity_kind=trade.liquidity_kind,
        original_extreme=original_extreme,
    )
    if raid is None:
        return RearmRow(
            symbol=trade.symbol,
            session=trade.session,
            operating_date=trade.operating_date,
            side=trade.side,
            original_mss_at=trade.m3_mss_at,
            original_stale_fill_at=trade.entry_at,
            original_h1_deadline=trade.h1_deadline,
            rearm_eligible_at=eligible_at.isoformat(),
            new_raid_at=None,
            new_closeback_at=None,
            new_mss_at=None,
            new_fvg_confirmed_at=None,
            new_fill_at=None,
            new_entry_mode=None,
            new_stop_valid_geometry=None,
            terminal_stage="NO_NEW_RAID",
        )

    closeback_at = _new_closeback(
        m5,
        m5_closes,
        raid_at=raid.opened_at,
        deadline=deadline,
        liquidity_kind=trade.liquidity_kind,
        liquidity_price=liquidity_price,
    )
    if closeback_at is None:
        return RearmRow(
            symbol=trade.symbol,
            session=trade.session,
            operating_date=trade.operating_date,
            side=trade.side,
            original_mss_at=trade.m3_mss_at,
            original_stale_fill_at=trade.entry_at,
            original_h1_deadline=trade.h1_deadline,
            rearm_eligible_at=eligible_at.isoformat(),
            new_raid_at=raid.opened_at.isoformat(),
            new_closeback_at=None,
            new_mss_at=None,
            new_fvg_confirmed_at=None,
            new_fill_at=None,
            new_entry_mode=None,
            new_stop_valid_geometry=None,
            terminal_stage="NEW_RAID_NO_CLOSEBACK",
        )

    mss = find_source_first_m3_mss(
        m3,
        m3_closes,
        m3_pivots,
        sweep_at=raid.opened_at,
        after=closeback_at,
        before=deadline,
        side=side,
    )
    if mss is None:
        return RearmRow(
            symbol=trade.symbol,
            session=trade.session,
            operating_date=trade.operating_date,
            side=trade.side,
            original_mss_at=trade.m3_mss_at,
            original_stale_fill_at=trade.entry_at,
            original_h1_deadline=trade.h1_deadline,
            rearm_eligible_at=eligible_at.isoformat(),
            new_raid_at=raid.opened_at.isoformat(),
            new_closeback_at=closeback_at.isoformat(),
            new_mss_at=None,
            new_fvg_confirmed_at=None,
            new_fill_at=None,
            new_entry_mode=None,
            new_stop_valid_geometry=None,
            terminal_stage="NEW_CLOSEBACK_NO_MSS",
        )

    zone = v3._m1_causal_zone(execution, event=mss)
    if zone is None:
        return RearmRow(
            symbol=trade.symbol,
            session=trade.session,
            operating_date=trade.operating_date,
            side=trade.side,
            original_mss_at=trade.m3_mss_at,
            original_stale_fill_at=trade.entry_at,
            original_h1_deadline=trade.h1_deadline,
            rearm_eligible_at=eligible_at.isoformat(),
            new_raid_at=raid.opened_at.isoformat(),
            new_closeback_at=closeback_at.isoformat(),
            new_mss_at=mss.confirmed_at.isoformat(),
            new_fvg_confirmed_at=None,
            new_fill_at=None,
            new_entry_mode=None,
            new_stop_valid_geometry=None,
            terminal_stage="NEW_MSS_NO_FVG",
        )

    fill = v3._find_m1_fill(
        execution,
        event=mss,
        zone=zone,
        deadline=deadline,
    )
    if fill is None:
        return RearmRow(
            symbol=trade.symbol,
            session=trade.session,
            operating_date=trade.operating_date,
            side=trade.side,
            original_mss_at=trade.m3_mss_at,
            original_stale_fill_at=trade.entry_at,
            original_h1_deadline=trade.h1_deadline,
            rearm_eligible_at=eligible_at.isoformat(),
            new_raid_at=raid.opened_at.isoformat(),
            new_closeback_at=closeback_at.isoformat(),
            new_mss_at=mss.confirmed_at.isoformat(),
            new_fvg_confirmed_at=zone.fvg_confirmed_at.isoformat(),
            new_fill_at=None,
            new_entry_mode=None,
            new_stop_valid_geometry=None,
            terminal_stage="NEW_FVG_NO_FILL",
        )

    fill_index, entry_price, entry_mode = fill
    fill_at = execution[fill_index].opened_at
    buffer_price = Decimal(trade.stop_buffer_price)
    stop_price = (
        mss.broken_swing_price - buffer_price
        if side is CapitalizerSide.LONG
        else mss.broken_swing_price + buffer_price
    )
    valid_stop = (
        stop_price < entry_price
        if side is CapitalizerSide.LONG
        else stop_price > entry_price
    )
    return RearmRow(
        symbol=trade.symbol,
        session=trade.session,
        operating_date=trade.operating_date,
        side=trade.side,
        original_mss_at=trade.m3_mss_at,
        original_stale_fill_at=trade.entry_at,
        original_h1_deadline=trade.h1_deadline,
        rearm_eligible_at=eligible_at.isoformat(),
        new_raid_at=raid.opened_at.isoformat(),
        new_closeback_at=closeback_at.isoformat(),
        new_mss_at=mss.confirmed_at.isoformat(),
        new_fvg_confirmed_at=zone.fvg_confirmed_at.isoformat(),
        new_fill_at=fill_at.isoformat(),
        new_entry_mode=entry_mode,
        new_stop_valid_geometry=valid_stop,
        terminal_stage=(
            "REARM_EXECUTABLE"
            if valid_stop
            else "REARM_STOP_INVALID_GEOMETRY"
        ),
    )


def build_market_report(
    wait5_root: Path,
    m1_root: Path,
    *,
    session: CapitalizerSession,
) -> tuple[dict[str, Any], tuple[RearmRow, ...]]:
    stale = _load_stale_wait5(wait5_root)
    if not stale:
        raise ValueError("rearm atlas requires stale WAIT5 trades")

    first = min(_aware(item.h1_open) for item in stale) - timedelta(days=2)
    last = max(_aware(item.h1_deadline) for item in stale) + timedelta(minutes=5)
    all_bars = tuple(
        bar for bar in iter_cibo_m1(m1_root) if first <= bar.opened_at <= last
    )
    if not all_bars:
        raise ValueError("rearm atlas found no native M1")
    symbol = all_bars[0].symbol
    if any(bar.symbol != symbol for bar in all_bars):
        raise ValueError("rearm atlas requires one market per M1 root")
    if any(item.symbol != symbol for item in stale):
        raise ValueError("rearm atlas WAIT5/M1 symbol mismatch")
    if any(item.session != session.value for item in stale):
        raise ValueError("rearm atlas WAIT5/session mismatch")

    m5 = _aggregate_tf(all_bars, minutes=5)
    m5_closes = tuple(item.closed_at for item in m5)
    m3 = _aggregate_tf(all_bars, minutes=3)
    m3_closes = tuple(item.closed_at for item in m3)
    m3_pivots = _pivots(m3)
    execution_by_day, _ = _index_day_inputs(all_bars, session=session)

    rows: list[RearmRow] = []
    for trade in stale:
        execution = execution_by_day.get(trade.operating_date, ())
        if not execution:
            raise ValueError("rearm atlas missing execution day")
        rows.append(
            _build_row(
                trade=trade,
                execution=execution,
                m5=m5,
                m5_closes=m5_closes,
                m3=m3,
                m3_closes=m3_closes,
                m3_pivots=m3_pivots,
            )
        )

    ordered = tuple(sorted(rows, key=lambda item: (item.original_mss_at, item.symbol)))
    stages = Counter(item.terminal_stage for item in ordered)
    return {
        "identity": IDENTITY,
        "symbol": symbol,
        "session": session.value,
        "stale_wait5_population": len(ordered),
        "terminal_stages": dict(sorted(stages.items())),
        "new_raid": sum(item.new_raid_at is not None for item in ordered),
        "new_closeback": sum(item.new_closeback_at is not None for item in ordered),
        "new_mss": sum(item.new_mss_at is not None for item in ordered),
        "new_fvg": sum(item.new_fvg_confirmed_at is not None for item in ordered),
        "new_fill": sum(item.new_fill_at is not None for item in ordered),
        "rearm_executable": stages["REARM_EXECUTABLE"],
        "same_reference_requires_new_extreme": True,
        "new_raid_required": True,
        "new_closeback_required": True,
        "new_source_first_mss_required": True,
        "new_causal_fvg_required": True,
        "new_fill_required": True,
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
    rows: tuple[RearmRow, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    symbol = str(report["symbol"]).lower()
    stem = f"capitalizer-{symbol}-v3-source-first-wait-rearm-atlas-2y-v1"
    (output / f"{stem}.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (output / f"{stem}-rows.jsonl").open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(asdict(row), sort_keys=True) + "\n")


def _load_reports(root: Path) -> list[dict[str, Any]]:
    paths = sorted(
        root.rglob("capitalizer-*-v3-source-first-wait-rearm-atlas-2y-v1.json")
    )
    if len(paths) != 9:
        raise ValueError(f"rearm matrix requires 9 reports, got {len(paths)}")
    return [dict(json.loads(path.read_text(encoding="utf-8"))) for path in paths]


def build_matrix(root: Path) -> dict[str, Any]:
    reports = _load_reports(root)
    stale = sum(int(item["stale_wait5_population"]) for item in reports)
    stages: Counter[str] = Counter()
    for report in reports:
        for key, value in dict(report["terminal_stages"]).items():
            stages[str(key)] += int(value)
    return {
        "identity": MATRIX_IDENTITY,
        "market_count": 9,
        "stale_wait5_population": stale,
        "stale_wait5_control_reproduced": stale == EXPECTED_STALE_WAIT5_RAW,
        "terminal_stages": dict(sorted(stages.items())),
        "new_raid": sum(int(item["new_raid"]) for item in reports),
        "new_closeback": sum(int(item["new_closeback"]) for item in reports),
        "new_mss": sum(int(item["new_mss"]) for item in reports),
        "new_fvg": sum(int(item["new_fvg"]) for item in reports),
        "new_fill": sum(int(item["new_fill"]) for item in reports),
        "rearm_executable": sum(int(item["rearm_executable"]) for item in reports),
        "markets": sorted(reports, key=lambda item: str(item["symbol"])),
        "same_reference_requires_new_extreme": True,
        "new_raid_required": True,
        "new_closeback_required": True,
        "new_source_first_mss_required": True,
        "new_causal_fvg_required": True,
        "new_fill_required": True,
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
    path = output / "capitalizer-nine-market-v3-source-first-wait-rearm-atlas-2y-v1.json"
    path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    market = sub.add_parser("market")
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
