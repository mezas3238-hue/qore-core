"""Provider-native causal market context for Capitalizer direct-M1 trades.

Binds entry-time regime and destination evidence directly from immutable M1.
No trade outcome or milestone counterfactual is read.

Regime facts:
- completed M15 directional slope versus trade side;
- last completed H1 body alignment;
- recent M15 range expansion/compression versus prior completed history.

Destination fact:
- nearest causally CONFIRMED H1 pivot liquidity in the trade direction,
  expressed in original structural-risk R and bucketed without inspecting the
  later trade path.

All bars used by a row are closed at or before entry.  A pivot is usable only
after its confirmation timestamp.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from statistics import median
from typing import Any

from qore.infrastructure.trader_lab import (
    capitalizer_max_recovery_direct_m1_replay_v1 as direct,
)
from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
    iter_cibo_m1,
)
from qore.infrastructure.trader_lab.capitalizer_strict_htf_gate_1y_v1 import (
    _aggregate_tf,
    _pivots,
)

IDENTITY = "QORE_CAPITALIZER_NATIVE_MARKET_CONTEXT_V1"

RECENT_M15 = 4
BASELINE_M15 = 12
COMPRESSION_RATIO = Decimal("0.80")
EXPANSION_RATIO = Decimal("1.20")


@dataclass(frozen=True, slots=True)
class NativeContextRow:
    symbol: str
    session: str
    operating_date: str
    side: str
    entry_at: str
    provenance: str
    risk_price: str
    m15_slope_alignment: str
    h1_body_alignment: str
    volatility_state: str
    volatility_ratio: str | None
    destination_state: str
    destination_room_r: str | None
    destination_pivot_confirmed_at: str | None
    regime_signature: str
    context_signature: str
    bars_after_entry_used: bool = False
    unconfirmed_pivot_used: bool = False
    outcome_visible_to_context: bool = False


def _aware(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("native context requires timezone-aware timestamps")
    return parsed


def _load_raw(root: Path) -> tuple[direct.DirectTrade, ...]:
    paths = sorted(
        root.rglob("capitalizer-*-max-recovery-direct-m1-replay-v1-final-raw.jsonl")
    )
    if len(paths) != 1:
        raise ValueError("native context requires one direct market raw ledger")
    rows: list[direct.DirectTrade] = []
    with paths[0].open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(direct.DirectTrade(**json.loads(line)))
    if not rows:
        raise ValueError("native context direct ledger is empty")
    if len({row.symbol for row in rows}) != 1:
        raise ValueError("native context direct ledger must contain one symbol")
    return tuple(
        sorted(rows, key=lambda row: (_aware(row.entry_at), row.symbol))
    )


def _alignment(
    *,
    delta: Decimal,
    side: str,
) -> str:
    if delta == 0:
        return "FLAT"
    favorable = (side == "LONG" and delta > 0) or (side == "SHORT" and delta < 0)
    return "ALIGNED" if favorable else "OPPOSED"


def _volatility_state(
    completed_m15: tuple[Any, ...],
) -> tuple[str, Decimal | None]:
    needed = RECENT_M15 + BASELINE_M15
    if len(completed_m15) < needed:
        return "UNBOUND", None
    recent = completed_m15[-RECENT_M15:]
    baseline = completed_m15[-needed:-RECENT_M15]
    recent_ranges = [
        bar.source.high - bar.source.low
        for bar in recent
    ]
    baseline_ranges = [
        bar.source.high - bar.source.low
        for bar in baseline
    ]
    baseline_median = Decimal(str(median([float(value) for value in baseline_ranges])))
    recent_median = Decimal(str(median([float(value) for value in recent_ranges])))
    if baseline_median <= 0:
        return "UNBOUND", None
    ratio = recent_median / baseline_median
    if ratio <= COMPRESSION_RATIO:
        return "COMPRESSION", ratio
    if ratio >= EXPANSION_RATIO:
        return "EXPANSION", ratio
    return "NORMAL", ratio


def _destination(
    *,
    side: str,
    entry: Decimal,
    risk: Decimal,
    pivots: tuple[Any, ...],
    entry_at: datetime,
) -> tuple[str, Decimal | None, datetime | None]:
    confirmed = tuple(
        pivot
        for pivot in pivots
        if pivot.confirmed_at <= entry_at
    )
    if side == "LONG":
        candidates = tuple(
            pivot for pivot in confirmed
            if pivot.kind == "HIGH" and pivot.price > entry
        )
        if not candidates:
            return "OPEN", None, None
        nearest = min(candidates, key=lambda pivot: pivot.price)
        distance = nearest.price - entry
    else:
        candidates = tuple(
            pivot for pivot in confirmed
            if pivot.kind == "LOW" and pivot.price < entry
        )
        if not candidates:
            return "OPEN", None, None
        nearest = max(candidates, key=lambda pivot: pivot.price)
        distance = entry - nearest.price

    room_r = distance / risk
    if room_r < Decimal("1"):
        state = "LT_1R"
    elif room_r < Decimal("2"):
        state = "R1_TO_2"
    else:
        state = "GE_2R"
    return state, room_r, nearest.confirmed_at


def build_report(
    direct_root: Path,
    m1_root: Path,
    *,
    role: str,
) -> tuple[dict[str, Any], tuple[NativeContextRow, ...]]:
    trades = _load_raw(direct_root)
    symbol = trades[0].symbol
    start = min(_aware(row.entry_at) for row in trades) - timedelta(days=5)
    end = max(_aware(row.entry_at) for row in trades) + timedelta(hours=1)
    bars = tuple(
        bar
        for bar in iter_cibo_m1(m1_root)
        if start <= bar.opened_at <= end
    )
    if not bars:
        raise ValueError("native context found no M1")
    if {bar.symbol for bar in bars} != {symbol}:
        raise ValueError("native context M1 symbol mismatch")

    m15 = _aggregate_tf(bars, minutes=15)
    h1 = _aggregate_tf(bars, minutes=60)
    h1_pivots = _pivots(h1)

    result: list[NativeContextRow] = []
    for trade in trades:
        entry_at = _aware(trade.entry_at)
        entry = Decimal(trade.entry_price)
        stop = Decimal(trade.stop_price)
        risk = abs(entry - stop)
        if risk <= 0:
            raise ValueError("native context requires positive structural risk")

        completed_m15 = tuple(bar for bar in m15 if bar.closed_at <= entry_at)
        completed_h1 = tuple(bar for bar in h1 if bar.closed_at <= entry_at)

        if len(completed_m15) >= 4:
            slope_delta = (
                completed_m15[-1].source.close
                - completed_m15[-4].source.close
            )
            m15_alignment = _alignment(delta=slope_delta, side=trade.side)
        else:
            m15_alignment = "UNBOUND"

        if completed_h1:
            last_h1 = completed_h1[-1]
            h1_delta = last_h1.source.close - last_h1.source.open
            h1_alignment = _alignment(delta=h1_delta, side=trade.side)
        else:
            h1_alignment = "UNBOUND"

        vol_state, vol_ratio = _volatility_state(completed_m15)
        destination_state, room_r, pivot_at = _destination(
            side=trade.side,
            entry=entry,
            risk=risk,
            pivots=h1_pivots,
            entry_at=entry_at,
        )
        regime_signature = (
            f"M15={m15_alignment}|H1={h1_alignment}|VOL={vol_state}"
        )
        context_signature = f"{regime_signature}|DEST={destination_state}"

        result.append(
            NativeContextRow(
                symbol=trade.symbol,
                session=trade.session,
                operating_date=trade.operating_date,
                side=trade.side,
                entry_at=trade.entry_at,
                provenance=trade.provenance,
                risk_price=str(risk),
                m15_slope_alignment=m15_alignment,
                h1_body_alignment=h1_alignment,
                volatility_state=vol_state,
                volatility_ratio=(
                    None if vol_ratio is None else str(vol_ratio)
                ),
                destination_state=destination_state,
                destination_room_r=None if room_r is None else str(room_r),
                destination_pivot_confirmed_at=(
                    None if pivot_at is None else pivot_at.isoformat()
                ),
                regime_signature=regime_signature,
                context_signature=context_signature,
            )
        )

    rows = tuple(result)
    return {
        "identity": IDENTITY,
        "role": role,
        "symbol": symbol,
        "trades": len(rows),
        "context_rows": len(rows),
        "regime_bound_rows": sum(
            row.m15_slope_alignment != "UNBOUND"
            and row.h1_body_alignment != "UNBOUND"
            and row.volatility_state != "UNBOUND"
            for row in rows
        ),
        "destination_open_rows": sum(
            row.destination_state == "OPEN" for row in rows
        ),
        "destination_lt_1r_rows": sum(
            row.destination_state == "LT_1R" for row in rows
        ),
        "destination_1_to_2r_rows": sum(
            row.destination_state == "R1_TO_2" for row in rows
        ),
        "destination_ge_2r_rows": sum(
            row.destination_state == "GE_2R" for row in rows
        ),
        "compression_ratio": str(COMPRESSION_RATIO),
        "expansion_ratio": str(EXPANSION_RATIO),
        "bars_after_entry_used": False,
        "unconfirmed_pivots_used": False,
        "outcome_visible_to_context": False,
        "target_result_visible_to_context": False,
        "milestone_result_visible_to_context": False,
        "strategy_rules_changed": False,
        "entry_changed": False,
        "stop_changed": False,
        "target_changed": False,
        "max3_changed": False,
    }, rows


def write_report(
    report: dict[str, Any],
    rows: tuple[NativeContextRow, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    symbol = str(report["symbol"]).lower()
    role = str(report["role"]).lower()
    stem = f"capitalizer-{symbol}-native-market-context-{role}-v1"
    (output / f"{stem}.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (output / f"{stem}-rows.jsonl").open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(asdict(row), sort_keys=True) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("direct_root", type=Path)
    parser.add_argument("m1_root", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--role", required=True)
    args = parser.parse_args()
    report, rows = build_report(
        args.direct_root,
        args.m1_root,
        role=args.role,
    )
    write_report(report, rows, args.output)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
