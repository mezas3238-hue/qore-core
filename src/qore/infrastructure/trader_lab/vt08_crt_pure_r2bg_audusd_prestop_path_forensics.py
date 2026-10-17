"""R2-BG AUDUSD pre-stop path forensics.

Question
--------
Why is PF thin despite high density?

R2-BE showed that the dominant gross-loss mechanism is the full structural stop.
R2-BG separates two possibilities without changing any trade:

1. ENTRY_SELECTION_FAILURE
   Full-stop trades never establish meaningful favorable progress on a completed
   M15 close.

2. POSITION_RETENTION_FAILURE
   Full-stop trades first establish meaningful favorable progress, then reverse
   back to the stop.

The analysis replays the exact CONTROL_BE075 15Y population using the same
close-confirmed BE_CLOSE_075 contract. Completed-close progress is used to avoid
intrabar path assumptions.

No filter or management rule is promoted.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.vt08_crt_pure_r2_model1_reference_lab import (
    M15Bar,
    Model1LabTrade,
    aggregate_complete_m15,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2az_audusd_protection_family import (
    ProtectionPolicy,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2be_audusd_candidate_robustness import (
    END,
    START,
    build_populations,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_window_evidence import load_m5_window
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket

IDENTITY = "VT08_CRT_PURE_R2BG_AUDUSD_PRESTOP_PATH_FORENSICS_001"
SCHEMA = "qore.vt08.crt_pure.r2bg_audusd_prestop_path_forensics.v1"
TRIGGER_R = Decimal("0.75")


@dataclass(frozen=True, slots=True)
class PathRecord:
    entry_opened_at: str
    parent_direction: str
    timing_triplet: str
    reference_count: int
    exit_reason: str
    realized_r: float
    max_completed_close_r_before_exit: float
    min_completed_close_r_before_exit: float
    completed_bars_before_exit: int
    closed_positive_before_exit: bool
    closed_ge_025_before_exit: bool
    closed_ge_050_before_exit: bool
    closed_ge_075_before_exit: bool


def _r_at_price(
    *,
    bullish: bool,
    entry: Decimal,
    risk: Decimal,
    price: Decimal,
) -> Decimal:
    if bullish:
        return (price - entry) / risk
    return (entry - price) / risk


def _bars(
    *,
    trade: Model1LabTrade,
    m15_by_time: dict[datetime, M15Bar],
) -> tuple[M15Bar, ...]:
    entry = datetime.fromisoformat(trade.entry_opened_at)
    c3_close = datetime.fromisoformat(trade.c3_opened_at) + timedelta(hours=4)
    return tuple(
        m15_by_time[opened_at]
        for opened_at in sorted(m15_by_time)
        if entry <= opened_at < c3_close
    )


def _trace(
    *,
    trade: Model1LabTrade,
    bars: tuple[M15Bar, ...],
) -> PathRecord:
    bullish = trade.parent_direction == "BULLISH"
    entry = Decimal(trade.entry_price_relative)
    original_stop = Decimal(trade.stop_price_relative)
    target = Decimal(trade.target_price_relative)
    risk = abs(entry - original_stop)
    if risk <= 0:
        raise RuntimeError("trade risk must be positive")

    current_stop = original_stop
    closes: list[Decimal] = []

    for bar in bars:
        if bullish:
            stop_hit = Decimal(bar.low_price) <= current_stop
            target_hit = Decimal(bar.high_price) >= target
        else:
            stop_hit = Decimal(bar.high_price) >= current_stop
            target_hit = Decimal(bar.low_price) <= target

        # STOP_FIRST is identical to the source replay. The close of an exit bar
        # is never observed for protection/trajectory purposes.
        if stop_hit or target_hit:
            break

        close_r = _r_at_price(
            bullish=bullish,
            entry=entry,
            risk=risk,
            price=Decimal(bar.close_price),
        )
        closes.append(close_r)

        if close_r >= TRIGGER_R:
            # BE_CLOSE_075 becomes active only on the next bar.
            current_stop = entry

    max_close = max(closes, default=Decimal("0"))
    min_close = min(closes, default=Decimal("0"))
    return PathRecord(
        entry_opened_at=trade.entry_opened_at,
        parent_direction=trade.parent_direction,
        timing_triplet=trade.timing_triplet,
        reference_count=trade.reference_count,
        exit_reason=trade.exit_reason,
        realized_r=float(trade.r_multiple),
        max_completed_close_r_before_exit=round(float(max_close), 8),
        min_completed_close_r_before_exit=round(float(min_close), 8),
        completed_bars_before_exit=len(closes),
        closed_positive_before_exit=max_close > 0,
        closed_ge_025_before_exit=max_close >= Decimal("0.25"),
        closed_ge_050_before_exit=max_close >= Decimal("0.50"),
        closed_ge_075_before_exit=max_close >= Decimal("0.75"),
    )


def _classify(record: PathRecord) -> str:
    if record.exit_reason != "STOP" or abs(record.realized_r + 1.0) > 1e-9:
        return "NOT_FULL_STOP"
    if not record.closed_positive_before_exit:
        return "FULL_STOP_NEVER_POSITIVE_CLOSE"
    if not record.closed_ge_025_before_exit:
        return "FULL_STOP_POSITIVE_LT_025"
    if not record.closed_ge_050_before_exit:
        return "FULL_STOP_REACHED_025_LT_050"
    if not record.closed_ge_075_before_exit:
        return "FULL_STOP_REACHED_050_LT_075"
    return "FULL_STOP_REACHED_GE_075_UNEXPECTED"


def _summary(records: tuple[PathRecord, ...]) -> dict[str, Any]:
    full_stops = tuple(
        record
        for record in records
        if record.exit_reason == "STOP"
        and abs(record.realized_r + 1.0) <= 1e-9
    )
    classes: dict[str, list[PathRecord]] = defaultdict(list)
    for record in records:
        classes[_classify(record)].append(record)

    full_stop_count = len(full_stops)
    return {
        "trades": len(records),
        "full_stop_count": full_stop_count,
        "full_stop_fraction": (
            0.0 if not records else round(full_stop_count / len(records), 8)
        ),
        "full_stop_path_classes": {
            label: {
                "trades": len(rows),
                "share_of_full_stops": (
                    0.0
                    if full_stop_count == 0 or label == "NOT_FULL_STOP"
                    else round(len(rows) / full_stop_count, 8)
                ),
            }
            for label, rows in sorted(classes.items())
            if label != "NOT_FULL_STOP"
        },
        "full_stops_with_positive_close": sum(
            record.closed_positive_before_exit for record in full_stops
        ),
        "full_stops_reached_025_close": sum(
            record.closed_ge_025_before_exit for record in full_stops
        ),
        "full_stops_reached_050_close": sum(
            record.closed_ge_050_before_exit for record in full_stops
        ),
        "full_stops_reached_075_close": sum(
            record.closed_ge_075_before_exit for record in full_stops
        ),
        "median_max_close_r_full_stop": (
            None
            if not full_stops
            else sorted(
                record.max_completed_close_r_before_exit
                for record in full_stops
            )[len(full_stops) // 2]
        ),
    }


def run_forensics() -> tuple[tuple[PathRecord, ...], dict[str, Any]]:
    populations, diagnostics = build_populations()
    control = populations["CONTROL_BE075"]

    m5 = load_m5_window(
        CrtPureMarket.AUDUSD,
        start=START - timedelta(days=2),
        end_exclusive=END + timedelta(days=1),
    )
    m15 = aggregate_complete_m15(m5)
    m15_by_time = {bar.opened_at: bar for bar in m15}

    records = tuple(
        _trace(
            trade=trade,
            bars=_bars(
                trade=trade,
                m15_by_time=m15_by_time,
            ),
        )
        for trade in control
    )

    report: dict[str, Any] = {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "population": "R2_BE_CONTROL_BE075",
        "protection_policy": ProtectionPolicy.BE_CLOSE_075.value,
        "window_start": START.isoformat(),
        "window_end_exclusive": END.isoformat(),
        "diagnostics": diagnostics,
        "trajectory_basis": "COMPLETED_M15_CLOSES_BEFORE_EXIT_ONLY",
        "same_bar_precedence": "STOP_FIRST",
        "summary": _summary(records),
        "interpretation": {
            "selection_failure_proxy": (
                "FULL_STOP_NEVER_POSITIVE_CLOSE + "
                "FULL_STOP_POSITIVE_LT_025"
            ),
            "retention_failure_proxy": (
                "FULL_STOP_REACHED_025_LT_050 + "
                "FULL_STOP_REACHED_050_LT_075"
            ),
            "no_filter_promoted": True,
        },
        "research_only": True,
        "candidate_certified": False,
        "demo_eligible": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "production_authorized": False,
    }
    return records, report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    records, report = run_forensics()
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n"
    )
    with (args.output / "paths.jsonl").open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(asdict(record), sort_keys=True) + "\n")
    print("CRT_R2BG_PRESTOP_JSON=" + json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
