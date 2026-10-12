"""QORE Alpha2 G2 29 original BID/ASK source-quality grid, research only.

Event-time as-of for *source quality*, NOT historically delivered/available_at;
no fills, orders, net costs, trading decisions or unsealing 2026 data.
"""
from __future__ import annotations

import argparse
import json
import math
from datetime import datetime
from pathlib import Path
from statistics import median

from qore.research.alpha2_g2_29_real_bidask_reuse import (
    ORIGINAL_HEAD,
    ORIGINAL_RUN,
    SOURCE_29,
    WINDOWS,
    audit,
    digest,
)

GRID_SECONDS = 600
MAX_SIDE_AGE_MS = 5000
IDENTITY = "QORE_ALPHA2_G2_29_REAL_BIDASK_FIXED_1SEC_SOURCE_QUALITY_V1"


def percentile_linear(values: list[float], probability: float) -> float | None:
    if not values:
        return None
    if not 0 <= probability <= 1:
        raise ValueError("PERCENTILE_OUTSIDE_UNIT_RANGE")
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    low = math.floor(position)
    high = math.ceil(position)
    return float(ordered[low] * (high - position) +
                 ordered[high] * (position - low)) if high != low else float(ordered[low])


def read_int_side(
    folder: Path, symbol: str, index: int, side: str,
) -> list[tuple[int, int]]:
    if symbol not in SOURCE_29 or index not in (1, 2) or side not in ("BID", "ASK"):
        raise ValueError("HOLDOUT_OR_MARKET_OUTSIDE_FROZEN_SCOPE")
    name = f"{symbol}-{index}-{side}-integer.jsonl"
    rows: list[tuple[int, int]] = []
    start, end = (
        int(datetime.fromisoformat(t).timestamp() * 1000) for t in WINDOWS[index-1]
    )
    with (folder / name).open(encoding="utf-8") as file:
        for line in file:
            raw = json.loads(line)
            if not isinstance(raw, dict) or set(raw) != {"epoch_ms", "integer_price_1e5"}:
                raise ValueError("UNVERIFIED_NATIVE_SIDE_FORMAT")
            epoch, price = raw["epoch_ms"], raw["integer_price_1e5"]
            if (type(epoch) is not int or type(price) is not int or price <= 0
                    or not start <= epoch < end
                    or rows and epoch < rows[-1][0]):
                raise ValueError("UNVERIFIED_NATIVE_SIDE_TIMESTAMP_OR_PRICE")
            rows.append((epoch, price))
    if not rows:
        raise ValueError("SOURCE_SIDE_EMPTY")
    return rows


def one_second_grid(
    bids: list[tuple[int, int]],
    asks: list[tuple[int, int]],
    *,
    start_ms: int,
    seconds: int = GRID_SECONDS,
    max_age_ms: int = MAX_SIDE_AGE_MS,
) -> dict:
    if (type(start_ms) is not int or seconds < 1 or max_age_ms < 0
            or seconds > GRID_SECONDS or max_age_ms > MAX_SIDE_AGE_MS):
        raise ValueError("SECOND_GRID_SCOPE_DRIFT")
    for side in (bids, asks):
        previous: int | None = None
        for epoch, price in side:
            if (type(epoch) is not int or type(price) is not int or price <= 0
                    or previous is not None and epoch < previous):
                raise ValueError("SIDE_INTEGER_TICK_INVALID")
            previous = epoch
    stale = positive = crossed = zero = 0
    positive_bps: list[float] = []
    freshest_bid_age: list[int] = []
    freshest_ask_age: list[int] = []
    b = a = -1
    for i in range(seconds):
        now = start_ms + 1000 * i
        while b+1 < len(bids) and bids[b+1][0] <= now:
            b += 1
        while a+1 < len(asks) and asks[a+1][0] <= now:
            a += 1
        if b < 0 or a < 0:
            stale += 1
            continue
        bid_age = now - bids[b][0]
        ask_age = now - asks[a][0]
        if bid_age > max_age_ms or ask_age > max_age_ms:
            stale += 1
            continue
        freshest_bid_age.append(bid_age)
        freshest_ask_age.append(ask_age)
        bid_price, ask_price = bids[b][1], asks[a][1]
        if ask_price < bid_price:
            crossed += 1
        elif ask_price == bid_price:
            zero += 1
        else:
            positive += 1
            positive_bps.append(20000.0 * (ask_price-bid_price) /
                                (ask_price+bid_price))
    if stale + crossed + zero + positive != seconds:
        raise ValueError("SOURCE_GRID_CLASSIFICATION_DOES_NOT_RECONCILE")
    return {
        "clock_points": seconds,
        "stale_or_missing": stale,
        "crossed": crossed,
        "zero_spread": zero,
        "positive_spread": positive,
        "fresh_bid_age_max_ms":max(freshest_bid_age,default=None),
        "fresh_ask_age_max_ms":max(freshest_ask_age,default=None),
        "positive_spread_median_bps":median(positive_bps) if positive_bps else None,
        "positive_spread_p95_bps":percentile_linear(positive_bps,0.95),
        "ticks_after_clock_never_looked_ahead": True,
        "zero_and_crossed_never_counted_as_free_execution": True,
    }


def audit_quality(source: Path) -> dict:
    # Source audit performs native+decoded SHA/price/time checks for both
    # consumed windows across EXACTLY 29 markets before any spread calculations.
    admitted = audit(source)
    if (admitted.get("market_count") != 29
            or admitted.get("status") != "SOURCE29_TWO_PAST_WINDOWS_SHA_VERIFIED_NOT_NET"
            or admitted.get("source_original_actions_run") != ORIGINAL_RUN
            or admitted.get("source_original_code_head") != ORIGINAL_HEAD
            or admitted.get("holdout_2026_quote_values_unread") is not True):
        raise ValueError("G2_ORIGINAL29_PRESPREAD_SOURCE_ADMISSION_BLOCKED")
    per_market: dict[str, dict] = {}
    total = {"clock_points": 0,"stale_or_missing": 0, "crossed": 0,
             "zero_spread": 0, "positive_spread": 0}
    for symbol in sorted(SOURCE_29):
        samples: dict[str, dict] = {}
        for index in (1, 2):
            original = admitted["all_29"][symbol]["consumed_past_windows_only"][str(index)]
            folder = source / symbol
            bids = read_int_side(folder,symbol,index,"BID")
            asks = read_int_side(folder,symbol,index,"ASK")
            if (len(bids) != original["BID"]["tick_count"]
                    or len(asks) != original["ASK"]["tick_count"]):
                raise ValueError("SOURCE_TICK_COUNT_REPLAY_DISCREPANCY")
            start=int(datetime.fromisoformat(WINDOWS[index-1][0]).timestamp()*1000)
            got=one_second_grid(bids,asks,start_ms=start)
            samples[str(index)]=got
            for name in total:
                total[name]+=got[name]
        per_market[symbol] = {
            "2020_2023_only_quote_quality":samples,
            "source_witness_original_sha256":admitted["all_29"][symbol][
                "original_manifest_sha256"],
            "net_authorized":False,
        }
    if (len(per_market) != 29 or total["clock_points"] != 29*2*GRID_SECONDS
            or sum(total[k] for k in (
                "stale_or_missing","crossed","zero_spread","positive_spread"
            )) != total["clock_points"]):
        raise ValueError("FIXED_SECOND_GRID_SOURCE_COUNT_DOES_NOT_RECONCILE")
    return {
        "identity":IDENTITY,
        "original_source_run":ORIGINAL_RUN,
        "original_head":ORIGINAL_HEAD,
        "source_manifest_29_sha256":admitted["source_root_sha256"],
        "markets":29, "windows_per_market":2,
        "fixed_grid_points_per_window":GRID_SECONDS,
        "max_side_event_age_ms":MAX_SIDE_AGE_MS,
        "total":total,
        "by_market":per_market,
        "source_event_timestamp_asof_only":True,
        "historical_terminal_quote_available_at_verified":False,
        "positive_spread_NOT_execution_cost":True,
        "zero_or_crossed_NOT_free_cost":True,
        "no_2026_09_15_quote_price_access":True,
        "historical_full_10y_costs_verified":False,
        "all_W1_W2_W3_economic_methods_frozen":True,
        "NET_CERTIFICATION":False,
        "orders":0,
    }


def main() -> None:
    parser=argparse.ArgumentParser()
    parser.add_argument("source29",type=Path)
    parser.add_argument("out",type=Path)
    a=parser.parse_args()
    result=audit_quality(a.source29)
    a.out.mkdir(parents=True,exist_ok=True)
    output=a.out/"alpha2-g2-29-two-window-second-grid-quality.json"
    output.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({
        "status":result["identity"],
        "markets":result["markets"],
        "total":result["total"],
        "no_2026_09_15_quote_price_access":True,
        "NET":"BLOCKED",
        "output_sha256":digest(output),
    },sort_keys=True))


if __name__=="__main__":
    main()
