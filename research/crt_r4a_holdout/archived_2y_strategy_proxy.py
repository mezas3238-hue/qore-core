"""Research-only 24-month real-OHLC *proxy*, not the certified QORE Pine engine.

This tool studies two causal approximations of CRT_2C+MSS15 and TRUE3C+MSS5.
It reuses original source decoder from pinned QORE CRT PR #1004. No bid/ask,
trading fee, broker semantics or production authority. Never call it a certified
holdout or net profitability result. Outputs only aggregate numbers.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from statistics import mean
from typing import Any

from scripts.crt_radar_archived_m5_prescreen import (
    H4,
    M5,
    completed_h4,
    frozen_bucket,
    native_to_bar,
)

from research.crt_r4a_holdout.native_archive_2y_probe import inspect as verify

MODELS = ("A_2C_MSS15_PROXY", "B_TRUE3C_MSS5_PROXY")
YEARS = (2024, 2025)
START = datetime(2024, 1, 1, tzinfo=UTC)
END = datetime(2026, 1, 1, tzinfo=UTC)
EXPIRY_HOURS = 12
ATR_LENGTH = 14
ATR_BUFFER = 0.25
MAX_ENTRY_DISTANCE_ATR = 0.5
ALIASES = {"NAS100": "USTEC", "SP500": "US500"}


@dataclass(frozen=True)
class Block:
    h4: H4
    m5: tuple[M5, ...]


@dataclass(frozen=True)
class Candidate:
    model: str
    direction: int
    ratified_at: datetime
    mss_at: datetime
    c1: H4
    sweep: H4
    atr: float

    @property
    def available_at(self) -> datetime:
        return max(self.ratified_at, self.mss_at)


def source_m5(root: Path, symbol: str, cohort: str) -> tuple[list[M5], dict[str, Any]]:
    provenance = verify(root, symbol, cohort)
    manifest_path = list(root.rglob("symbol-consumption-manifest.json"))[0]
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    provider = ALIASES.get(symbol, symbol) if cohort == "ATLAS_DEMO_BROKER_UNVERIFIED" else symbol
    result: list[M5] = []
    for year in YEARS:
        path = manifest_path.parent / "RAW_M5_LEDGER" / f"{year}.jsonl"
        with path.open(encoding="utf-8") as h:
            for line in h:
                if line.strip():
                    result.append(
                        native_to_bar(
                            json.loads(line), symbol, provider,
                            data["provider_symbol_id"]
                        )
                    )
    if not result or any(
        result[i].opened_at <= result[i - 1].opened_at
        for i in range(1, len(result))
    ):
        raise ValueError("native M5 out of order")
    return result, provenance


def h4_blocks(m5: list[M5], family: str) -> tuple[list[Block], int]:
    blocks: list[Block] = []
    partial = 0
    group: list[M5] = []
    key = None
    for b in m5:
        k, _ = frozen_bucket(b, family)
        if k != key:
            if group:
                h = completed_h4(group, family)
                if h is not None:
                    blocks.append(Block(h, tuple(group)))
                else:
                    partial += 1
            group = []
            key = k
        group.append(b)
    if group:
        h = completed_h4(group, family)
        if h is not None:
            blocks.append(Block(h, tuple(group)))
        else:
            partial += 1
    return blocks, partial


def atr_at(blocks: list[Block], idx: int) -> float | None:
    if idx < ATR_LENGTH:
        return None
    values: list[float] = []
    for i in range(idx - ATR_LENGTH + 1, idx + 1):
        cur = blocks[i].h4
        prev = blocks[i - 1].h4
        tr = max(
            cur.high - cur.low,
            abs(cur.high - prev.close),
            abs(cur.low - prev.close),
        )
        values.append(float(tr))
    a = mean(values)
    return a if a > 0 else None


def sweep_info(c1: H4, target: Block) -> tuple[int, datetime] | None:
    bullish = target.h4.low < c1.low
    bearish = target.h4.high > c1.high
    if bullish == bearish or not (c1.low < target.h4.close < c1.high):
        return None
    side = 1 if bullish else -1
    for b in target.m5:
        if (b.low < c1.low if bullish else b.high > c1.high):
            return (side, b.opened_at + timedelta(minutes=5))
    return None


def mss5_within(
    pre: tuple[M5, ...], c3: Block, side: int, sweep_at: datetime
) -> datetime | None:
    earlier = [x for x in pre + c3.m5 if x.opened_at < sweep_at - timedelta(minutes=5)]
    if len(earlier) < 8:
        return None
    # Frozen pre-sweep level from available previous eight M5. This is
    # deliberately a PROXY, not Pine's confirmed pivot mechanism.
    level = max(x.high for x in earlier[-8:]) if side == 1 else min(
        x.low for x in earlier[-8:]
    )
    previous = None
    for b in c3.m5:
        end = b.opened_at + timedelta(minutes=5)
        if end <= sweep_at:
            previous = b.close
            continue
        crossed = (b.close > level and previous <= level) if side == 1 else (
            b.close < level and previous >= level
        ) if previous is not None else False
        if crossed:
            return end
        previous = b.close
    return None


def mss15_c2_c3(
    c1: Block, c2: Block, next_c3: Block | None,
    side: int, sweep_at: datetime
) -> datetime | None:
    prev = list(c1.m5[-24:]) + list(c2.m5)
    frozen = [
        bar for bar in prev if
        bar.opened_at + timedelta(minutes=5) <= sweep_at
    ]
    if len(frozen) < 9:
        return None
    level = max(x.high for x in frozen[-9:]) if side == 1 else min(
        x.low for x in frozen[-9:]
    )
    stream = list(c2.m5) + (
        list(next_c3.m5) if next_c3 and c2.h4.closed_at == next_c3.h4.opened_at else []
    )
    previous_close = None
    quarter: list[M5] = []
    for b in stream:
        if quarter and b.opened_at - quarter[-1].opened_at != timedelta(minutes=5):
            quarter = []
        quarter.append(b)
        if len(quarter) > 3:
            quarter = quarter[-3:]
        end = b.opened_at + timedelta(minutes=5)
        if end.minute % 15 != 0 or len(quarter) != 3:
            continue
        if quarter[0].opened_at.minute % 15 != 0:
            continue
        close = b.close
        if end > sweep_at and previous_close is not None:
            hit = (close > level and previous_close <= level) if side == 1 else (
                close < level and previous_close >= level
            )
            if hit:
                return end
        previous_close = close
    return None


def candidates(blocks: list[Block]) -> tuple[list[Candidate], Counter[str]]:
    found: list[Candidate] = []
    reasons: Counter[str] = Counter()
    for i in range(2, len(blocks)):
        p, c1, c2 = blocks[i - 2], blocks[i - 1], blocks[i]
        a = atr_at(blocks, i)
        if a is None:
            continue
        if c1.h4.c1_allowed and c1.h4.closed_at == c2.h4.opened_at:
            sweep = sweep_info(c1.h4, c2)
            if sweep is not None:
                reasons["A_2C_STRUCTURAL"] += 1
                side, swept_at = sweep
                next_c3 = blocks[i + 1] if i + 1 < len(blocks) else None
                mss = mss15_c2_c3(c1, c2, next_c3, side, swept_at)
                if mss is not None:
                    reasons["A_MSS15_PROXY_CONFIRMED"] += 1
                    found.append(Candidate(
                        MODELS[0], side, c2.h4.closed_at, mss,
                        c1.h4, c2.h4, a
                    ))
        # Independent TRUE3C: p=C1, c1=C2, c2=C3.
        if (p.h4.c1_allowed and
                p.h4.closed_at == c1.h4.opened_at and
                c1.h4.closed_at == c2.h4.opened_at and
                c1.h4.high <= p.h4.high and c1.h4.low >= p.h4.low and
                p.h4.low < c1.h4.close < p.h4.high):
            sweep = sweep_info(p.h4, c2)
            if sweep is not None:
                reasons["B_TRUE3C_STRUCTURAL"] += 1
                side, swept_at = sweep
                mss = mss5_within(
                    c1.m5, c2, side, swept_at
                )
                if mss is not None:
                    reasons["B_MSS5_PROXY_CONFIRMED"] += 1
                    found.append(Candidate(
                        MODELS[1], side, c2.h4.closed_at, mss,
                        p.h4, c2.h4, a
                    ))
    return sorted(found, key=lambda c: c.available_at), reasons


def outcome(c: Candidate, m5: list[M5]) -> tuple[str, float | None]:
    mid = (c.sweep.open + c.sweep.close) / 2
    buffer = ATR_BUFFER * c.atr
    stop = min(c.c1.low, c.sweep.low) - buffer if c.direction == 1 else (
        max(c.c1.high, c.sweep.high) + buffer
    )
    tp = c.c1.high if c.direction == 1 else c.c1.low
    risk = mid - stop if c.direction == 1 else stop - mid
    if risk <= 0 or (tp <= mid if c.direction == 1 else tp >= mid):
        return "INVALID_LEVELS", None
    if abs(mid - c.sweep.close) > MAX_ENTRY_DISTANCE_ATR * c.atr:
        return "ENTRY_DISTANCE", None
    expiry = c.available_at + timedelta(hours=EXPIRY_HOURS)
    entered = False
    for b in m5:
        if b.opened_at < c.available_at:
            continue
        if not entered:
            if b.opened_at >= expiry:
                return "EXPIRED_LIMIT", None
            if b.low <= stop if c.direction == 1 else b.high >= stop:
                return "CANCEL_STOP_BEFORE_FILL", None
            if b.low > mid if c.direction == 1 else b.high < mid:
                continue
            entered = True
            # Unknown intrabar sequence; no same-M5 target profit credited.
            if b.high >= tp if c.direction == 1 else b.low <= tp:
                return "AMBIGUOUS_ENTRY_TP", None
        stop_hit = b.low <= stop if c.direction == 1 else b.high >= stop
        tp_hit = b.high >= tp if c.direction == 1 else b.low <= tp
        if stop_hit:
            return "SL_GROSS", -1.0
        if tp_hit:
            return "TP_GROSS", abs(tp - mid) / risk
    return "OPEN_UNRESOLVED", None


def research(root: Path, symbol: str, family: str, cohort: str) -> dict[str, Any]:
    m5, provenance = source_m5(root, symbol, cohort)
    blocks, incomplete = h4_blocks(m5, family)
    events, reasons = candidates(blocks)
    # Read-only, event by event on genuine archived OHLC; no broker quotes.
    from bisect import bisect_left

    start_keys = [b.opened_at for b in m5]
    trades: dict[str, list[float]] = {model: [] for model in MODELS}
    endings: Counter[str] = Counter()
    for c in events:
        # Binary search avoids rescanning full history from first bar per event.
        start = bisect_left(start_keys, c.available_at)
        status, r = outcome(c, m5[start:])
        endings[status] += 1
        if r is not None:
            trades[c.model].append(r)
    metrics = {}
    for model in MODELS:
        rs = trades[model]
        pos = sum(x for x in rs if x > 0)
        neg = -sum(x for x in rs if x < 0)
        eq = high = dd = 0.0
        for x in rs:
            eq += x
            high = max(eq, high)
            dd = max(dd, high - eq)
        metrics[model] = {
            "closed_trades": len(rs),
            "gross_win_rate": (sum(x > 0 for x in rs) / len(rs) if rs else None),
            "gross_profit_factor": pos / neg if neg else None,
            "gross_net_R_unscaled": sum(rs),
            "gross_expectancy_R": (mean(rs) if rs else None),
            "gross_max_drawdown_R_sequential": dd,
        }
    return {
        "symbol": symbol,
        "cohort": cohort,
        "period": "2024-01-01/2025-12-31",
        "native_M5_rows": len(m5),
        "closed_H4": len(blocks),
        "incomplete_H4": incomplete,
        "source_sha256": "2024_AND_2025_VERIFIED",
        "two_hypotheses": metrics,
        "signals": dict(reasons),
        "exit_reasons": dict(endings),
        "status": "REAL_OHLC_EXPLORATORY_PROXY_ONLY",
        "is_qore_pine_f_engine": False,
        "is_Pine_parity_100pct": False,
        "is_broker_bid_ask": False,
        "costs_included": False,
        "holdout_certified": False,
        "portfolio_certified": False,
        "provider_lineage": provenance["cohort"],
        "btc_missing": symbol != "BTCUSD",
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--root", type=Path, required=True)
    p.add_argument("--symbol", required=True)
    p.add_argument("--family", choices=("forex", "index"), required=True)
    p.add_argument("--cohort", required=True)
    args = p.parse_args()
    output = research(args.root, args.symbol, args.family, args.cohort)
    print(json.dumps(output, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
