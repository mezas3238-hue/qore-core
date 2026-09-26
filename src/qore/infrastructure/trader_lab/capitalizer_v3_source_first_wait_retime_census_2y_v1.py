"""Causal retiming census for SOURCE_FIRST immediate no-overlap fills.

Population:
- frozen SOURCE_FIRST 2Y raw trades;
- M1 OB/FVG overlap is false;
- current frozen V3 fill occurs <=5 minutes after the SOURCE_FIRST M3 MSS.

Counterfactual is diagnostic only:
- keep the exact original M1 FVG zone;
- keep the exact structural stop;
- ignore CE fills until 5 full minutes have elapsed after M3 MSS;
- then accept the first later CE touch before the original H1 deadline;
- if the structural stop is touched before an eligible later CE touch, fail closed;
- no PnL, target, or post-entry outcome is used.

This census answers whether a WAIT/rearm state can preserve meaningful density before any
economic A/B is attempted.
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
    CapitalizerM1Bar,
    iter_cibo_m1,
)

IDENTITY = "QORE_CAPITALIZER_V3_SOURCE_FIRST_WAIT_RETIME_CENSUS_2Y_V1"
MATRIX_IDENTITY = (
    "QORE_CAPITALIZER_NINE_MARKET_V3_SOURCE_FIRST_WAIT_RETIME_CENSUS_2Y_V1"
)
WAIT_MINUTES = 5
EXPECTED_SOURCE_FIRST_RAW = 1142


@dataclass(frozen=True, slots=True)
class RetimeRow:
    symbol: str
    session: str
    operating_date: str
    side: str
    m3_mss_at: str
    current_entry_at: str
    current_entry_delay_minutes: str
    h1_deadline: str
    fvg_low: str
    fvg_high: str
    fvg_ce: str
    stop_price: str
    original_entry_mode: str
    original_ob_fvg_overlap: bool
    wait_eligible_at: str
    status: str
    later_fill_at: str | None
    later_fill_delay_from_mss_minutes: str | None
    later_fill_delay_from_current_entry_minutes: str | None
    stop_invalidation_at: str | None
    eligible_fill_stop_same_bar: bool
    same_zone_preserved: bool = True
    same_stop_preserved: bool = True
    target_used_for_admission: bool = False
    outcome_used_for_admission: bool = False


def _load_trades(root: Path) -> tuple[v3.V3Trade, ...]:
    paths = sorted(
        root.rglob("capitalizer-*-v3-source-first-cisd-2y-v1-trades.jsonl")
    )
    if len(paths) != 1:
        raise ValueError("retiming market census requires one SOURCE_FIRST trade ledger")
    rows: list[v3.V3Trade] = []
    with paths[0].open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(v3.V3Trade(**json.loads(line)))
    return tuple(rows)


def _minutes(start: datetime, end: datetime) -> Decimal:
    return Decimal(str((end - start).total_seconds())) / Decimal("60")


def _stop_hit(bar: CapitalizerM1Bar, trade: v3.V3Trade) -> bool:
    stop = Decimal(trade.stop_price)
    return bool(
        bar.low <= stop
        if trade.side == "LONG"
        else bar.high >= stop
    )


def _ce_touch(bar: CapitalizerM1Bar, ce: Decimal) -> bool:
    return bool(bar.low <= ce <= bar.high)


def _scan_counterfactual(
    trade: v3.V3Trade,
    execution: tuple[CapitalizerM1Bar, ...],
    opens: tuple[datetime, ...],
) -> RetimeRow:
    mss_at = datetime.fromisoformat(trade.m3_mss_at)
    current_entry_at = datetime.fromisoformat(trade.entry_at)
    deadline = datetime.fromisoformat(trade.h1_deadline)
    wait_eligible_at = mss_at + timedelta(minutes=WAIT_MINUTES)
    ce = (
        Decimal(trade.m1_fvg_low) + Decimal(trade.m1_fvg_high)
    ) / Decimal("2")

    later_fill_at: datetime | None = None
    invalidation_at: datetime | None = None
    same_bar_stop = False
    status = "NO_LATER_FILL_BEFORE_DEADLINE"

    start = bisect.bisect_left(opens, mss_at)
    end = bisect.bisect_left(opens, deadline)
    for bar in execution[start:end]:
        stop_hit = _stop_hit(bar, trade)
        eligible = bar.opened_at >= wait_eligible_at
        ce_touch = eligible and _ce_touch(bar, ce)

        if stop_hit and not ce_touch:
            invalidation_at = bar.closed_at
            status = "STOP_INVALIDATED_BEFORE_LATER_FILL"
            break

        if ce_touch:
            later_fill_at = bar.opened_at
            same_bar_stop = stop_hit
            status = (
                "LATER_FILL_AVAILABLE_STOP_SAME_BAR"
                if stop_hit
                else "LATER_FILL_AVAILABLE"
            )
            break

    return RetimeRow(
        symbol=trade.symbol,
        session=trade.session,
        operating_date=trade.operating_date,
        side=trade.side,
        m3_mss_at=trade.m3_mss_at,
        current_entry_at=trade.entry_at,
        current_entry_delay_minutes=str(_minutes(mss_at, current_entry_at)),
        h1_deadline=trade.h1_deadline,
        fvg_low=trade.m1_fvg_low,
        fvg_high=trade.m1_fvg_high,
        fvg_ce=str(ce),
        stop_price=trade.stop_price,
        original_entry_mode=trade.entry_mode,
        original_ob_fvg_overlap=trade.m1_ob_fvg_overlap,
        wait_eligible_at=wait_eligible_at.isoformat(),
        status=status,
        later_fill_at=(
            None if later_fill_at is None else later_fill_at.isoformat()
        ),
        later_fill_delay_from_mss_minutes=(
            None
            if later_fill_at is None
            else str(_minutes(mss_at, later_fill_at))
        ),
        later_fill_delay_from_current_entry_minutes=(
            None
            if later_fill_at is None
            else str(_minutes(current_entry_at, later_fill_at))
        ),
        stop_invalidation_at=(
            None if invalidation_at is None else invalidation_at.isoformat()
        ),
        eligible_fill_stop_same_bar=same_bar_stop,
    )


def _delay_band(row: RetimeRow) -> str:
    if row.later_fill_delay_from_mss_minutes is None:
        return "NO_LATER_FILL"
    value = Decimal(row.later_fill_delay_from_mss_minutes)
    if value <= Decimal("10"):
        return "05_10M"
    if value <= Decimal("15"):
        return "10_15M"
    if value <= Decimal("30"):
        return "15_30M"
    return "30M_PLUS"


def build_market_report(
    replay_root: Path,
    m1_root: Path,
) -> tuple[dict[str, Any], tuple[RetimeRow, ...]]:
    trades = _load_trades(replay_root)
    if not trades:
        raise ValueError("retiming census requires SOURCE_FIRST trades")
    first_mss = min(datetime.fromisoformat(trade.m3_mss_at) for trade in trades)
    last_deadline = max(datetime.fromisoformat(trade.h1_deadline) for trade in trades)
    native = tuple(
        bar
        for bar in iter_cibo_m1(m1_root)
        if first_mss - timedelta(minutes=1) <= bar.opened_at < last_deadline
    )
    if not native:
        raise ValueError("retiming census requires native M1 in the replay window")
    opens = tuple(bar.opened_at for bar in native)

    symbols = {trade.symbol for trade in trades}
    sessions = {trade.session for trade in trades}
    if len(symbols) != 1 or len(sessions) != 1:
        raise ValueError("retiming market input must be one symbol/session")
    symbol = next(iter(symbols))
    session = next(iter(sessions))
    if any(bar.symbol != symbol for bar in native):
        raise ValueError("native M1 symbol mismatch")

    population = tuple(
        trade
        for trade in trades
        if not trade.m1_ob_fvg_overlap
        and _minutes(
            datetime.fromisoformat(trade.m3_mss_at),
            datetime.fromisoformat(trade.entry_at),
        )
        <= Decimal(str(WAIT_MINUTES))
    )

    rows = tuple(
        _scan_counterfactual(trade, native, opens)
        for trade in population
    )
    statuses = Counter(row.status for row in rows)
    delay_bands = Counter(
        _delay_band(row)
        for row in rows
        if row.later_fill_at is not None
    )

    return {
        "identity": IDENTITY,
        "symbol": symbol,
        "session": session,
        "source_first_raw_trades": len(trades),
        "immediate_no_overlap_population": len(rows),
        "status_counts": dict(sorted(statuses.items())),
        "later_fill_available": sum(
            row.later_fill_at is not None for row in rows
        ),
        "later_fill_clean": statuses["LATER_FILL_AVAILABLE"],
        "later_fill_stop_same_bar": statuses[
            "LATER_FILL_AVAILABLE_STOP_SAME_BAR"
        ],
        "stop_invalidated_before_later_fill": statuses[
            "STOP_INVALIDATED_BEFORE_LATER_FILL"
        ],
        "no_later_fill_before_deadline": statuses[
            "NO_LATER_FILL_BEFORE_DEADLINE"
        ],
        "later_fill_delay_bands": dict(sorted(delay_bands.items())),
        "wait_minutes": WAIT_MINUTES,
        "same_zone_preserved": True,
        "same_stop_preserved": True,
        "target_used_for_admission": False,
        "outcome_used_for_admission": False,
        "diagnostic_only": True,
        "economic_candidate": False,
        "rule_promotion_allowed": False,
        "fresh_holdout_claimed": False,
    }, rows


def write_market(
    report: dict[str, Any],
    rows: tuple[RetimeRow, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    symbol = str(report["symbol"]).lower()
    stem = f"capitalizer-{symbol}-v3-source-first-wait-retime-census-2y-v1"
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
            "capitalizer-*-v3-source-first-wait-retime-census-2y-v1.json"
        )
    )
    if len(paths) != 9:
        raise ValueError(f"retiming matrix requires 9 reports, got {len(paths)}")
    return [dict(json.loads(path.read_text(encoding="utf-8"))) for path in paths]


def build_matrix(root: Path) -> dict[str, Any]:
    reports = _load_reports(root)
    raw = sum(int(item["source_first_raw_trades"]) for item in reports)
    population = sum(
        int(item["immediate_no_overlap_population"]) for item in reports
    )
    statuses: Counter[str] = Counter()
    delays: Counter[str] = Counter()
    per_session: dict[str, Counter[str]] = {}
    for report in reports:
        for key, value in dict(report["status_counts"]).items():
            statuses[str(key)] += int(value)
        for key, value in dict(report["later_fill_delay_bands"]).items():
            delays[str(key)] += int(value)
        counter = per_session.setdefault(str(report["session"]), Counter())
        counter["population"] += int(report["immediate_no_overlap_population"])
        counter["later_fill_available"] += int(report["later_fill_available"])
        counter["later_fill_clean"] += int(report["later_fill_clean"])
        counter["later_fill_stop_same_bar"] += int(
            report["later_fill_stop_same_bar"]
        )
        counter["stop_invalidated"] += int(
            report["stop_invalidated_before_later_fill"]
        )
        counter["no_later_fill"] += int(
            report["no_later_fill_before_deadline"]
        )

    later = (
        statuses["LATER_FILL_AVAILABLE"]
        + statuses["LATER_FILL_AVAILABLE_STOP_SAME_BAR"]
    )
    return {
        "identity": MATRIX_IDENTITY,
        "market_count": 9,
        "source_first_raw_trades": raw,
        "source_first_raw_control_reproduced": (
            raw == EXPECTED_SOURCE_FIRST_RAW
        ),
        "immediate_no_overlap_population": population,
        "status_counts": dict(sorted(statuses.items())),
        "later_fill_available": later,
        "later_fill_availability_rate": (
            None
            if population == 0
            else str(Decimal(later) / Decimal(population))
        ),
        "later_fill_clean": statuses["LATER_FILL_AVAILABLE"],
        "later_fill_stop_same_bar": statuses[
            "LATER_FILL_AVAILABLE_STOP_SAME_BAR"
        ],
        "stop_invalidated_before_later_fill": statuses[
            "STOP_INVALIDATED_BEFORE_LATER_FILL"
        ],
        "no_later_fill_before_deadline": statuses[
            "NO_LATER_FILL_BEFORE_DEADLINE"
        ],
        "later_fill_delay_bands": dict(sorted(delays.items())),
        "per_session": {
            key: dict(value) for key, value in sorted(per_session.items())
        },
        "markets": sorted(reports, key=lambda item: str(item["symbol"])),
        "wait_minutes": WAIT_MINUTES,
        "same_zone_preserved": True,
        "same_stop_preserved": True,
        "target_used_for_admission": False,
        "outcome_used_for_admission": False,
        "diagnostic_only": True,
        "economic_candidate": False,
        "rule_promotion_allowed": False,
        "fresh_holdout_claimed": False,
    }


def write_matrix(report: dict[str, Any], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    path = (
        output
        / "capitalizer-nine-market-v3-source-first-wait-retime-census-2y-v1.json"
    )
    path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    market = sub.add_parser("market")
    market.add_argument("replay_root", type=Path)
    market.add_argument("m1_root", type=Path)
    market.add_argument("output", type=Path)
    matrix = sub.add_parser("matrix")
    matrix.add_argument("input_root", type=Path)
    matrix.add_argument("output", type=Path)
    args = parser.parse_args()

    if args.command == "market":
        report, rows = build_market_report(
            args.replay_root,
            args.m1_root,
        )
        write_market(report, rows, args.output)
        print(json.dumps(report, sort_keys=True))
        return

    report = build_matrix(args.input_root)
    write_matrix(report, args.output)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
