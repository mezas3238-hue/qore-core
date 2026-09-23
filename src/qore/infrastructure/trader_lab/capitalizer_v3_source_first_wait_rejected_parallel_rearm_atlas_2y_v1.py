"""Outcome-free parallel rearm atlas for rejected WAIT5 setups.

Population: frozen funnel rows ending in WAIT_STOP_INVALIDATED or WAIT_NO_REFILL.

From MSS+5m, the stale original setup remains non-executable, but an independent
new hypothesis may be tracked causally in parallel. Recovery requires:
new raid beyond the original sweep extreme -> new M5 closeback -> new
SOURCE_FIRST M3 MSS -> new causal M1 FVG -> new fill -> valid frozen stop.

The original FVG is never reused. No lifecycle outcome or PnL is read.
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
from qore.infrastructure.trader_lab import (
    capitalizer_v3_source_first_wait_rearm_atlas_2y_v1 as rearm,
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

IDENTITY = "QORE_CAPITALIZER_V3_SOURCE_FIRST_WAIT_REJECTED_PARALLEL_REARM_ATLAS_2Y_V1"
MATRIX_IDENTITY = (
    "QORE_CAPITALIZER_NINE_MARKET_V3_SOURCE_FIRST_"
    "WAIT_REJECTED_PARALLEL_REARM_ATLAS_2Y_V1"
)
EXPECTED_POPULATION = 165
WAIT_MINUTES = 5
REJECTED = {"WAIT_STOP_INVALIDATED", "WAIT_NO_REFILL"}


@dataclass(frozen=True, slots=True)
class RejectedWaitRearmRow:
    symbol: str
    session: str
    operating_date: str
    original_terminal_reason: str
    side: str
    original_mss_at: str
    rearm_eligible_at: str
    h1_deadline: str
    new_raid_at: str | None
    new_closeback_at: str | None
    new_mss_at: str | None
    new_fvg_at: str | None
    new_fill_at: str | None
    stop_valid: bool | None
    terminal_stage: str
    outcome_fields_read: bool = False


def _load_rows(root: Path) -> tuple[dict[str, Any], ...]:
    paths = sorted(
        root.rglob(
            "capitalizer-*-v3-source-first-wait5-funnel-atlas-2y-v1-rows.jsonl"
        )
    )
    if len(paths) != 1:
        raise ValueError("parallel rearm requires one funnel ledger per market")
    rows: list[dict[str, Any]] = []
    with paths[0].open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            raw = json.loads(line)
            if raw.get("terminal_reason") in REJECTED:
                rows.append(raw)
    return tuple(rows)


def _result(
    raw: dict[str, Any],
    *,
    eligible_at: datetime,
    raid_at: datetime | None = None,
    closeback_at: datetime | None = None,
    mss_at: datetime | None = None,
    fvg_at: datetime | None = None,
    fill_at: datetime | None = None,
    stop_valid: bool | None = None,
    terminal_stage: str,
) -> RejectedWaitRearmRow:
    return RejectedWaitRearmRow(
        symbol=str(raw["symbol"]),
        session=str(raw["session"]),
        operating_date=str(raw["operating_date"]),
        original_terminal_reason=str(raw["terminal_reason"]),
        side=str(raw["side"]),
        original_mss_at=str(raw["source_first_mss_at"]),
        rearm_eligible_at=eligible_at.isoformat(),
        h1_deadline=str(raw["h1_deadline"]),
        new_raid_at=None if raid_at is None else raid_at.isoformat(),
        new_closeback_at=None if closeback_at is None else closeback_at.isoformat(),
        new_mss_at=None if mss_at is None else mss_at.isoformat(),
        new_fvg_at=None if fvg_at is None else fvg_at.isoformat(),
        new_fill_at=None if fill_at is None else fill_at.isoformat(),
        stop_valid=stop_valid,
        terminal_stage=terminal_stage,
    )


def _build_row(
    raw: dict[str, Any],
    *,
    closeback: v3.SweepCloseback,
    execution: tuple[CapitalizerM1Bar, ...],
    m5: tuple[TFBar, ...],
    m5_closes: tuple[datetime, ...],
    m3: tuple[TFBar, ...],
    m3_closes: tuple[datetime, ...],
    m3_pivots: Any,
    buffer_price: Decimal,
) -> RejectedWaitRearmRow:
    original_mss_at = datetime.fromisoformat(str(raw["source_first_mss_at"]))
    deadline = datetime.fromisoformat(str(raw["h1_deadline"]))
    eligible_at = original_mss_at + timedelta(minutes=WAIT_MINUTES)
    side = CapitalizerSide(str(raw["side"]))

    raid = rearm._new_raid(
        execution,
        after=eligible_at,
        before=deadline,
        liquidity_kind=closeback.reference.kind,
        original_extreme=closeback.sweep_extreme,
    )
    if raid is None:
        return _result(raw, eligible_at=eligible_at, terminal_stage="NO_NEW_RAID")

    new_closeback_at = rearm._new_closeback(
        m5,
        m5_closes,
        raid_at=raid.opened_at,
        deadline=deadline,
        liquidity_kind=closeback.reference.kind,
        liquidity_price=closeback.reference.price,
    )
    if new_closeback_at is None:
        return _result(
            raw,
            eligible_at=eligible_at,
            raid_at=raid.opened_at,
            terminal_stage="NEW_RAID_NO_CLOSEBACK",
        )

    mss = find_source_first_m3_mss(
        m3,
        m3_closes,
        m3_pivots,
        sweep_at=raid.opened_at,
        after=new_closeback_at,
        before=deadline,
        side=side,
    )
    if mss is None:
        return _result(
            raw,
            eligible_at=eligible_at,
            raid_at=raid.opened_at,
            closeback_at=new_closeback_at,
            terminal_stage="NEW_CLOSEBACK_NO_MSS",
        )

    zone = v3._m1_causal_zone(execution, event=mss)
    if zone is None:
        return _result(
            raw,
            eligible_at=eligible_at,
            raid_at=raid.opened_at,
            closeback_at=new_closeback_at,
            mss_at=mss.confirmed_at,
            terminal_stage="NEW_MSS_NO_FVG",
        )

    fill = v3._find_m1_fill(
        execution,
        event=mss,
        zone=zone,
        deadline=deadline,
    )
    if fill is None:
        return _result(
            raw,
            eligible_at=eligible_at,
            raid_at=raid.opened_at,
            closeback_at=new_closeback_at,
            mss_at=mss.confirmed_at,
            fvg_at=zone.fvg_confirmed_at,
            terminal_stage="NEW_FVG_NO_FILL",
        )

    fill_index, entry_price, _ = fill
    fill_at = execution[fill_index].opened_at
    stop_price = (
        mss.broken_swing_price - buffer_price
        if side is CapitalizerSide.LONG
        else mss.broken_swing_price + buffer_price
    )
    valid = (
        stop_price < entry_price
        if side is CapitalizerSide.LONG
        else stop_price > entry_price
    )
    return _result(
        raw,
        eligible_at=eligible_at,
        raid_at=raid.opened_at,
        closeback_at=new_closeback_at,
        mss_at=mss.confirmed_at,
        fvg_at=zone.fvg_confirmed_at,
        fill_at=fill_at,
        stop_valid=valid,
        terminal_stage="REARM_EXECUTABLE" if valid else "REARM_STOP_INVALID",
    )


def build_market_report(
    funnel_root: Path,
    m1_root: Path,
    *,
    session: CapitalizerSession,
) -> tuple[dict[str, Any], tuple[RejectedWaitRearmRow, ...]]:
    frozen = _load_rows(funnel_root)
    if not frozen:
        raise ValueError("parallel rearm found no rejected WAIT rows")

    first = min(datetime.fromisoformat(str(x["sweep_at"])) for x in frozen) - timedelta(days=2)
    last = max(datetime.fromisoformat(str(x["h1_deadline"])) for x in frozen) + timedelta(days=1)
    all_bars = tuple(bar for bar in iter_cibo_m1(m1_root) if first <= bar.opened_at <= last)
    if not all_bars:
        raise ValueError("parallel rearm found no M1")
    symbol = all_bars[0].symbol
    if any(str(x["symbol"]) != symbol for x in frozen):
        raise ValueError("parallel rearm symbol mismatch")
    if any(str(x["session"]) != session.value for x in frozen):
        raise ValueError("parallel rearm session mismatch")

    closebacks = _reconstruct_closebacks(all_bars=all_bars, session=session)
    m5 = _aggregate_tf(all_bars, minutes=5)
    m5_closes = tuple(x.closed_at for x in m5)
    m3 = _aggregate_tf(all_bars, minutes=3)
    m3_closes = tuple(x.closed_at for x in m3)
    m3_pivots = _pivots(m3)
    buffer_price = v3._stop_buffer(all_bars)
    execution_by_day, _ = _index_day_inputs(all_bars, session=session)

    rows: list[RejectedWaitRearmRow] = []
    for raw in frozen:
        closeback = closebacks.get(str(raw["closeback_at"]))
        if closeback is None:
            raise ValueError("parallel rearm missing reconstructed closeback")
        execution = execution_by_day.get(str(raw["operating_date"]), ())
        if not execution:
            raise ValueError("parallel rearm missing execution day")
        rows.append(
            _build_row(
                raw,
                closeback=closeback,
                execution=execution,
                m5=m5,
                m5_closes=m5_closes,
                m3=m3,
                m3_closes=m3_closes,
                m3_pivots=m3_pivots,
                buffer_price=buffer_price,
            )
        )

    ordered = tuple(sorted(rows, key=lambda x: (x.original_mss_at, x.symbol)))
    stages = Counter(x.terminal_stage for x in ordered)
    reasons = Counter(x.original_terminal_reason for x in ordered)
    return {
        "identity": IDENTITY,
        "symbol": symbol,
        "session": session.value,
        "population": len(ordered),
        "original_reasons": dict(sorted(reasons.items())),
        "terminal_stages": dict(sorted(stages.items())),
        "new_raid": sum(x.new_raid_at is not None for x in ordered),
        "new_closeback": sum(x.new_closeback_at is not None for x in ordered),
        "new_mss": sum(x.new_mss_at is not None for x in ordered),
        "new_fvg": sum(x.new_fvg_at is not None for x in ordered),
        "new_fill": sum(x.new_fill_at is not None for x in ordered),
        "rearm_executable": stages["REARM_EXECUTABLE"],
        "parallel_from_mss_plus_5": True,
        "original_fvg_reuse_forbidden": True,
        "new_complete_cycle_required": True,
        "outcome_fields_read": False,
        "strategy_mutated": False,
        "diagnostic_only": True,
        "economic_candidate": False,
        "rule_promotion_allowed": False,
        "live_authorized": False,
        "real_capital_authorized": False,
    }, ordered


def write_market(report: dict[str, Any], rows: tuple[RejectedWaitRearmRow, ...], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    symbol = str(report["symbol"]).lower()
    stem = f"capitalizer-{symbol}-v3-source-first-wait-rejected-parallel-rearm-atlas-2y-v1"
    (output / f"{stem}.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with (output / f"{stem}-rows.jsonl").open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(asdict(row), sort_keys=True) + "\n")


def build_matrix(root: Path) -> dict[str, Any]:
    paths = sorted(root.rglob("capitalizer-*-v3-source-first-wait-rejected-parallel-rearm-atlas-2y-v1.json"))
    if len(paths) != 9:
        raise ValueError(f"parallel rearm matrix requires 9 reports, got {len(paths)}")
    reports = [dict(json.loads(p.read_text(encoding="utf-8"))) for p in paths]
    stages: Counter[str] = Counter()
    reasons: Counter[str] = Counter()
    for report in reports:
        for key, value in dict(report["terminal_stages"]).items():
            stages[str(key)] += int(value)
        for key, value in dict(report["original_reasons"]).items():
            reasons[str(key)] += int(value)
    population = sum(int(x["population"]) for x in reports)
    return {
        "identity": MATRIX_IDENTITY,
        "market_count": 9,
        "population": population,
        "population_control_reproduced": population == EXPECTED_POPULATION,
        "original_reasons": dict(sorted(reasons.items())),
        "terminal_stages": dict(sorted(stages.items())),
        "new_raid": sum(int(x["new_raid"]) for x in reports),
        "new_closeback": sum(int(x["new_closeback"]) for x in reports),
        "new_mss": sum(int(x["new_mss"]) for x in reports),
        "new_fvg": sum(int(x["new_fvg"]) for x in reports),
        "new_fill": sum(int(x["new_fill"]) for x in reports),
        "rearm_executable": sum(int(x["rearm_executable"]) for x in reports),
        "markets": sorted(reports, key=lambda x: str(x["symbol"])),
        "parallel_from_mss_plus_5": True,
        "original_fvg_reuse_forbidden": True,
        "new_complete_cycle_required": True,
        "outcome_fields_read": False,
        "strategy_mutated": False,
        "diagnostic_only": True,
        "economic_candidate": False,
        "rule_promotion_allowed": False,
        "live_authorized": False,
        "real_capital_authorized": False,
    }


def write_matrix(report: dict[str, Any], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    path = output / "capitalizer-nine-market-v3-source-first-wait-rejected-parallel-rearm-atlas-2y-v1.json"
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    market = sub.add_parser("market")
    market.add_argument("funnel_root", type=Path)
    market.add_argument("m1_root", type=Path)
    market.add_argument("output", type=Path)
    market.add_argument("--session", required=True, choices=[x.value for x in CapitalizerSession])
    matrix = sub.add_parser("matrix")
    matrix.add_argument("input_root", type=Path)
    matrix.add_argument("output", type=Path)
    args = parser.parse_args()
    if args.command == "market":
        report, rows = build_market_report(args.funnel_root, args.m1_root, session=CapitalizerSession(args.session))
        write_market(report, rows, args.output)
        print(json.dumps(report, sort_keys=True))
        return
    report = build_matrix(args.input_root)
    write_matrix(report, args.output)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
