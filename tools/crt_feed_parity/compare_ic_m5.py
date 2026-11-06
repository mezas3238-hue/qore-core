"""Fail-closed OFFLINE comparison of closed M5 bars: TradingView IC vs cTrader IC DEMO.

This does NOT authenticate an export, certify the seven CRT families, enable alerts,
or authorize trading. Obtain both CSVs via authorized, separate data collection.

CSV fields:
origin,tv_symbol,broker,server,open_time_utc,open,high,low,close,closed
"""
from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path

SCHEMA = "QORE_CRT_IC_M5_CANDLE_PARITY_QA_V1"
HEADER = (
    "origin", "tv_symbol", "broker", "server", "open_time_utc",
    "open", "high", "low", "close", "closed",
)
SOURCES = ("TRADINGVIEW_IC", "CTRADER_IC_DEMO")
IC_SYMBOLS = (
    "AUDJPY", "GBPUSD", "GBPJPY", "XAUUSD", "USTEC", "US500", "US30",
    "BTCUSD", "AUDUSD", "USDCAD", "USDJPY", "EURUSD", "USDCHF", "NZDUSD",
    "NZDJPY", "NZDCHF", "XAGUSD", "AUDCAD", "AUDCHF", "AUDNZD", "CADCHF",
    "CADJPY", "CHFJPY", "EURAUD", "EURCAD", "EURCHF", "EURGBP", "EURJPY",
    "EURNZD", "GBPAUD", "GBPCAD", "GBPCHF", "GBPNZD", "NZDCAD",
)
M5 = timedelta(minutes=5)


class CandleParityError(ValueError):
    """Reject incomplete, contradictory or untrusted-as-structured CSV data."""


@dataclass(frozen=True)
class Candle:
    opened_at: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal

    def values(self) -> tuple[Decimal, Decimal, Decimal, Decimal]:
        return self.open, self.high, self.low, self.close


def _price(row: dict[str, str], field: str) -> Decimal:
    try:
        value = Decimal(row[field])
    except (KeyError, InvalidOperation, TypeError) as exc:
        raise CandleParityError(f"invalid {field} price") from exc
    if not value.is_finite() or value <= 0:
        raise CandleParityError(f"{field} must be positive and finite")
    return value


def _timestamp(text: str) -> datetime:
    try:
        value = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except (ValueError, AttributeError) as exc:
        raise CandleParityError("invalid ISO timestamp") from exc
    if value.tzinfo is None or value.utcoffset() is None:
        raise CandleParityError("timestamp must include UTC offset")
    utc = value.astimezone(UTC)
    if utc.second != 0 or utc.microsecond != 0:
        raise CandleParityError("bar opening must be aligned to the minute")
    return utc


def read_closed_m5_csv(
    path: str | Path, *, source: str, symbol: str,
) -> tuple[dict[datetime, Candle], str]:
    """Strict CSV input with no ticker inference or silent timezone coercion."""
    if source not in SOURCES:
        raise CandleParityError("unrecognized source")
    if symbol not in IC_SYMBOLS:
        raise CandleParityError("symbol is not in the frozen 34 IC instruments")
    result: dict[datetime, Candle] = {}
    server: str | None = None
    with Path(path).open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or tuple(reader.fieldnames) != HEADER:
            raise CandleParityError("CSV columns differ from frozen contract")
        for index, row in enumerate(reader, start=2):
            if None in row or any(v is None for v in row.values()):
                raise CandleParityError(f"line {index}: missing or unexpected field")
            if row["origin"] != source:
                raise CandleParityError(f"line {index}: wrong data origin")
            if row["tv_symbol"] != "IC:" + symbol:
                raise CandleParityError(f"line {index}: source ticker mismatch")
            if row["broker"] != "IC MARKETS":
                raise CandleParityError(f"line {index}: broker mismatch")
            if not row["server"] or row["server"].strip() != row["server"]:
                raise CandleParityError(f"line {index}: missing server/feed identifier")
            if server is not None and server != row["server"]:
                raise CandleParityError("a CSV cannot mix servers/feed identifiers")
            server = row["server"]
            if row["closed"] != "true":
                raise CandleParityError(f"line {index}: unclosed M5 bar refused")
            at = _timestamp(row["open_time_utc"])
            if at in result:
                raise CandleParityError(f"line {index}: duplicate open timestamp")
            o, h, l, c = (_price(row, key) for key in ("open", "high", "low", "close"))
            if l > min(o, c) or h < max(o, c) or l > h:
                raise CandleParityError(f"line {index}: impossible OHLC")
            result[at] = Candle(opened_at=at, open=o, high=h, low=l, close=c)
    if not result:
        raise CandleParityError("empty CSV")
    return result, server or ""


def compare(
    tv: dict[datetime, Candle],
    ctrader: dict[datetime, Candle],
    *,
    symbol: str,
    tv_server: str,
    ctrader_server: str,
    min_overlap: int = 600,
    max_examples: int = 20,
) -> dict[str, object]:
    if symbol not in IC_SYMBOLS or min_overlap < 1 or max_examples < 0:
        raise CandleParityError("invalid comparison parameters")
    tv_times = set(tv)
    ct_times = set(ctrader)
    shared = sorted(tv_times & ct_times)
    price_mismatches: list[dict[str, object]] = []
    mismatch_count = 0
    max_delta = Decimal(0)
    for at in shared:
        a, b = tv[at].values(), ctrader[at].values()
        if a != b:
            mismatch_count += 1
            deltas = tuple(abs(x - y) for x, y in zip(a, b))
            max_delta = max(max_delta, *deltas)
            if len(price_mismatches) < max_examples:
                price_mismatches.append({
                    "open_time_utc": at.isoformat(),
                    "tv": list(map(str, a)),
                    "ctrader": list(map(str, b)),
                    "max_absolute_price_delta": str(max(deltas)),
                })
    only_tv = sorted(tv_times - ct_times)
    only_ct = sorted(ct_times - tv_times)
    if len(shared) < min_overlap:
        status = "INSUFFICIENT"
    elif mismatch_count or only_tv or only_ct:
        status = "DIVERGENT"
    else:
        status = "SAMPLE_MATCH_ONLY"
    return {
        "schema": SCHEMA,
        "symbol": "IC:" + symbol,
        "tradingview_feed": tv_server,
        "ctrader_demo_server": ctrader_server,
        "status": status,
        "tv_closed_m5": len(tv),
        "ctrader_closed_m5": len(ctrader),
        "common_open_timestamps": len(shared),
        "minimum_required_overlap": min_overlap,
        "identical_ohlc": len(shared) - mismatch_count,
        "different_ohlc": mismatch_count,
        "only_tradingview_times": len(only_tv),
        "only_ctrader_times": len(only_ct),
        "only_tradingview_examples": [x.isoformat() for x in only_tv[:max_examples]],
        "only_ctrader_examples": [x.isoformat() for x in only_ct[:max_examples]],
        "different_ohlc_examples": price_mismatches,
        "max_absolute_price_delta": str(max_delta),
        "tv_phase_minutes": sorted({t.minute % 5 for t in tv_times}),
        "ctrader_phase_minutes": sorted({t.minute % 5 for t in ct_times}),
        "overlap_start_utc": shared[0].isoformat() if shared else None,
        "overlap_end_utc": shared[-1].isoformat() if shared else None,
        "crt_mss_fvg_parity_checked": False,
        "verified_tradingview_indicator_source": False,
        "authorized_to_emit_v34_12x_alerts": False,
        "note": (
            "Identical sampled OHLC is NOT equivalence of CRT/MSS/FVG logic, "
            "historical coverage, TV indicator provenance, or future live data."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tv", required=True, type=Path)
    parser.add_argument("--ctrader", required=True, type=Path)
    parser.add_argument("--symbol", required=True, choices=IC_SYMBOLS)
    parser.add_argument("--min-overlap", type=int, default=600)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        tv, tv_server = read_closed_m5_csv(
            args.tv, source="TRADINGVIEW_IC", symbol=args.symbol)
        ct, ct_server = read_closed_m5_csv(
            args.ctrader, source="CTRADER_IC_DEMO", symbol=args.symbol)
        report = compare(tv, ct, symbol=args.symbol,
                         tv_server=tv_server, ctrader_server=ct_server,
                         min_overlap=args.min_overlap)
    except (CandleParityError, OSError) as exc:
        parser.exit(2, f"FEED PARITY REJECTED: {exc}\n")
    rendered = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0 if report["status"] == "SAMPLE_MATCH_ONLY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
