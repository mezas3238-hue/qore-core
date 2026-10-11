"""London-only external BID/ASK tick evidence T0: bounded, no live trading.

Investigates two deterministic previously-reported dual-touch M1 cases per
EURUSD and GBPUSD. Public historical market quotes are NOT the execution
broker's quotes or fills and cannot certify P&L. Uses no private credentials.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import lzma
import statistics
import struct
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

SYMBOLS = ("EURUSD", "GBPUSD")
PER_SYMBOL_LIMIT = 2
DUPLICATE_M1_COUNTS = {"EURUSD": 18, "GBPUSD": 16}
ROOTS = (
    "https://datafeed.dukascopy.com/datafeed",
    "https://www.dukascopy.com/datafeed",
)
FIXTURE_INSTANT = datetime(2025, 11, 12, 9, tzinfo=UTC)
MAX_COMPRESSED_BYTES = 8_000_000
MAX_DECOMPRESSED_BYTES = 100_000_000
POINT_SCALE = 100_000


@dataclass(frozen=True)
class Quote:
    observed_at: datetime
    bid: float
    ask: float


def bi5_path(symbol: str, hour: datetime) -> str:
    """Legacy Dukascopy hourly path, month zero-indexed, UTC hour."""
    if symbol not in SYMBOLS:
        raise ValueError("only EURUSD/GBPUSD")
    if hour.tzinfo is None:
        raise ValueError("naive tick timestamp")
    z = hour.astimezone(UTC)
    return f"{symbol}/{z.year:04d}/{z.month-1:02d}/{z.day:02d}/{z.hour:02d}h_ticks.bi5"


def decode_bi5(payload: bytes, hour: datetime) -> list[Quote]:
    if len(payload) > MAX_COMPRESSED_BYTES:
        raise ValueError("compressed bi5 payload too large")
    if not payload:
        raise ValueError("empty payload")
    if hour.tzinfo is None:
        raise ValueError("naive hour")
    raw = lzma.decompress(payload)
    if len(raw) > MAX_DECOMPRESSED_BYTES or len(raw) % 20:
        raise ValueError("invalid bi5 decoded size")
    utc_hour = hour.astimezone(UTC).replace(minute=0, second=0, microsecond=0)
    quotes: list[Quote] = []
    prior_ms = -1
    for ms, ask_raw, bid_raw, ask_volume, bid_volume in struct.iter_unpack(">IIIff", raw):
        if ms >= 3_600_000 or ms < prior_ms:
            raise ValueError("tick chronology invalid")
        if bid_raw <= 0 or ask_raw < bid_raw:
            raise ValueError("crossed/negative bid-ask quote")
        # This bounded test is only for major FX with ~1 to 2 price scale.
        bid, ask = bid_raw / POINT_SCALE, ask_raw / POINT_SCALE
        if not (0.4 < bid < 3 and 0.4 < ask < 3):
            raise ValueError("unexpected EUR/GBP FX price scale")
        if not (abs(ask_volume) < 1e30 and abs(bid_volume) < 1e30):
            raise ValueError("invalid volume field")
        quotes.append(Quote(
            observed_at=utc_hour + timedelta(milliseconds=ms),
            bid=bid, ask=ask,
        ))
        prior_ms = ms
    if not quotes:
        raise ValueError("zero tick observations")
    return quotes


def download_public_hour(symbol: str, instant: datetime) -> dict:
    route = bi5_path(symbol, instant)
    errors: list[str] = []
    for root in ROOTS:
        url = root + "/" + route
        try:
            req = Request(url, headers={"User-Agent": "QORE-Research-Tick-Probe/1.0"})
            with urlopen(req, timeout=18) as resp:
                status = resp.status
                body = resp.read(MAX_COMPRESSED_BYTES + 1)
            if status != 200:
                raise ValueError(f"HTTP {status}")
            quotes = decode_bi5(body, instant)
            return {
                "status": "QUOTE_SOURCE_AVAILABLE",
                "url": url, "sha256_compressed": hashlib.sha256(body).hexdigest(),
                "compressed_bytes": len(body),
                "n_ticks": len(quotes),
                "quotes": quotes,
            }
        except (HTTPError, URLError, TimeoutError, OSError, ValueError, lzma.LZMAError) as ex:
            errors.append(f"{root}: {type(ex).__name__} {str(ex)[:180]}")
    return {"status": "QUOTE_SOURCE_NOT_RETRIEVED", "errors": errors, "quotes": []}


def choose_cases(root: Path) -> tuple[list[dict], dict]:
    files = sorted(root.rglob("issue775-london-*-daily-events.jsonl"))
    if len(files) != 2:
        raise ValueError(f"must read exactly 2 original market-ledger artifacts: {len(files)}")
    events = [
        json.loads(line)
        for file in files for line in file.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if {x["symbol"] for x in events} != set(SYMBOLS):
        raise ValueError("missing EURUSD/GBPUSD")
    chosen: list[dict] = []
    counts: dict[str, int] = {}
    for symbol in SYMBOLS:
        all_ambiguities = sorted(
            (e for e in events if e["symbol"] == symbol and e["dual_touch_stop_first"]),
            key=lambda e: (e["exit_at"], e["entry_at"], e["pattern"]),
        )
        counts[symbol] = len(all_ambiguities)
        if len(all_ambiguities) != DUPLICATE_M1_COUNTS[symbol]:
            raise ValueError(f"frozen original dual-touch count changed {symbol}: {len(all_ambiguities)}")
        if len(all_ambiguities) < PER_SYMBOL_LIMIT:
            raise ValueError("not enough cases")
        chosen.extend(all_ambiguities[:PER_SYMBOL_LIMIT])
    return chosen, counts


def analyse_case(event: dict, fetched: dict) -> dict:
    row = {
        "symbol": event["symbol"], "london_day": event["london_day"],
        "pattern": event["pattern"], "entry_at": event["entry_at"],
        "m1_ambiguous_exit_at": event["exit_at"],
        "source_class": "EXTERNAL_DUKASCOPY_QUOTE_NOT_ORIGINAL_M1_OR_EXECUTION_BROKER",
        "quote_status": fetched["status"],
        "quote_url": fetched.get("url"),
        "sha256_compressed": fetched.get("sha256_compressed"),
        "download_errors": fetched.get("errors", []),
        "price_side_policy": "LONG_EXIT_BID_SHORT_EXIT_ASK",
        "true_fill_or_slippage_known": False,
        "adjudicated_broker_execution": False,
    }
    if fetched["status"] != "QUOTE_SOURCE_AVAILABLE":
        row["tick_first_touch_status"] = "UNRESOLVED_NO_TICK_DATA"
        return row
    expiry = datetime.fromisoformat(event["exit_at"])
    minute_start = expiry - timedelta(minutes=1)
    quotes: list[Quote] = fetched["quotes"]
    relevant = [q for q in quotes if minute_start <= q.observed_at < expiry]
    all_spreads = [(q.ask-q.bid) / .0001 for q in quotes]
    row.update(
        n_hour_ticks=len(quotes),
        n_quote_ticks_in_original_dual_touch_minute=len(relevant),
        hour_spread_pips_p50=statistics.median(all_spreads),
        hour_spread_pips_p95=sorted(all_spreads)[int(.95*(len(all_spreads)-1))],
        intended_stop_distance_pips=float(abs(
            float(event["entry"]) - float(event["stop"])
        ) / .0001),
    )
    if not relevant:
        row["tick_first_touch_status"] = "UNRESOLVED_NO_QUOTES_IN_M1"
        return row
    stop, target = float(event["stop"]), float(event["target"])
    direction = event["direction"]
    touches: list[tuple[str, str]] = []
    for q in relevant:
        side = q.bid if direction == "LONG" else q.ask
        stop_hit = side <= stop if direction == "LONG" else side >= stop
        target_hit = side >= target if direction == "LONG" else side <= target
        if stop_hit or target_hit:
            touches.append(("STOP" if stop_hit else "TARGET", q.observed_at.isoformat()))
    row["tick_first_touch_status"] = (
        f"EXTERNAL_QUOTE_{touches[0][0]}_OBSERVED_FIRST"
        if touches else "UNRESOLVED_NO_LEVEL_CROSS_ON_EXTERNAL_QUOTES"
    )
    if touches:
        row["first_touch_at"] = touches[0][1]
    row["intraminute_quotes_first_at"] = relevant[0].observed_at.isoformat()
    row["intraminute_quotes_last_at"] = relevant[-1].observed_at.isoformat()
    row["note"] = "Cross-provider M1 barrier reference; no claim original feed or broker result"
    return row


def run_probe(original_ledger: Path, output: Path) -> dict:
    cases, counts = choose_cases(original_ledger)
    cache: dict[tuple[str, str], dict] = {}
    summaries: list[dict] = []
    for event in cases:
        exit_ts = datetime.fromisoformat(event["exit_at"])
        m1_last = exit_ts - timedelta(minutes=1)
        hour = m1_last.replace(minute=0, second=0, microsecond=0).astimezone(UTC)
        key = (event["symbol"], hour.isoformat())
        if key not in cache:
            cache[key] = download_public_hour(event["symbol"], hour)
        summaries.append(analyse_case(event, cache[key]))
    # Unrelated independently fixed fixture prevents conflating a holiday
    # with a provider access failure. The fixture does NOT enter economics.
    fixture: dict = {}
    for symbol in SYMBOLS:
        f = download_public_hour(symbol, FIXTURE_INSTANT)
        fixture[symbol] = {
            "status": f["status"],
            "n_ticks": f.get("n_ticks", 0),
            "sha256_compressed": f.get("sha256_compressed"),
            "errors": f.get("errors", []),
        }
    result = {
        "identity": "QORE_ISSUE777_LONDON_BID_ASK_PUBLIC_TICK_PROBE_V1",
        "frozen_original_ambiguous_count": counts,
        "cases_queried": len(summaries),
        "cases": summaries,
        "provider_fixture_2025_11_12_09utc": fixture,
        "external_broker_not_verified": True,
        "no_pnl_certification_or_execution_claim": True,
        "quote_source_distinct_from_M1_provider": True,
        "limited_to_London_EURUSD_GBPUSD": True,
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "issue777-london-t0-public-bidask-targeted-probe.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return result


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("original_ledger", type=Path)
    p.add_argument("output", type=Path)
    args = p.parse_args()
    r = run_probe(args.original_ledger, args.output)
    print("ISSUE777_T0_LONDON", json.dumps(r, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
