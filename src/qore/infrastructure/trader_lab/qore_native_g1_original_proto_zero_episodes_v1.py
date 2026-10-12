"""Original-wire G1 BID/ASK equality and zero-episode source forensics.

EXPLORATORY post hoc, not preregistered alpha; no fill/cost interpretation.
Requires exact independent original field ProtoOATickData re-decode PASS.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import qore_native_g1_proto_wire_second_decoder_qa_v1 as reference

IDENTITY = "QORE_NATIVE_G1_ORIGINAL_PROTO_DUAL_SIDE_ZERO_EPISODES_EXPLORATORY_V1"
ORIGINAL_RUN = 38288411671
ORIGINAL_ARTIFACT = 11764163362
ORIGINAL_SHA256 = "b4eb9e66d76bcd439d4db8f2b8707afa06fe2d211a275c8af8b8605714b58684"
CLOCK_LIMIT_MS = 5000


def investigate(bid: list[tuple[int, int]], ask: list[tuple[int, int]]) -> dict[str, Any]:
    """Counts distinct updated instants; independent quote side update times."""
    if not bid or not ask:
        raise ValueError("G1_ORIGINAL_SOURCE_BOTH_SIDES_REQUIRED")
    previous = None
    for stream in (bid, ask):
        previous = None
        for event in stream:
            if type(event[0]) is not int or type(event[1]) is not int or event[1] <= 0:
                raise ValueError("G1_NATIVE_SOURCE_TICK_NOT_INTEGER")
            if previous is not None and event[0] < previous[0]:
                raise ValueError("G1_NATIVE_SOURCE_CLOCK_INVERTED")
            if previous is not None and event[0] == previous[0] and event[1] != previous[1]:
                raise ValueError("G1_NATIVE_SOURCE_SAME_MS_CAUSAL_AMBIGUITY")
            previous = event
    clock = sorted({t for t, _ in bid} | {t for t, _ in ask})
    i = j = 0
    b = a = None
    counts: Counter[str] = Counter()
    active_zero_run = 0
    max_zero_run = 0
    episode_count = 0
    lag_ms_for_zeros: Counter[str] = Counter()
    for t in clock:
        while i < len(bid) and bid[i][0] <= t:
            b = bid[i]
            i += 1
        while j < len(ask) and ask[j][0] <= t:
            a = ask[j]
            j += 1
        status: str
        if b is None or a is None:
            status = "missing_side"
        elif t - b[0] < 0 or t - a[0] < 0:
            raise ValueError("G1_CAUSAL_QUOTE_LOOKAHEAD")
        elif max(t-b[0], t-a[0]) > CLOCK_LIMIT_MS:
            status = "stale_side"
        elif a[1] < b[1]:
            status = "crossed_spread"
        elif a[1] > b[1]:
            status = "positive_spread"
        else:
            status = "zero_spread"
        counts[status] += 1
        if status == "zero_spread":
            active_zero_run += 1
            if active_zero_run == 1:
                episode_count += 1
            max_zero_run = max(max_zero_run, active_zero_run)
            if b[0] == a[0] == t:
                counts["zero_same_millisecond"] += 1
            elif b[0] < a[0]:
                counts["zero_bid_older"] += 1
            else:
                counts["zero_ask_older"] += 1
            gap = max(t-b[0], t-a[0])
            k = ("0" if gap == 0 else "1_100" if gap <= 100 else
                 "101_500" if gap <= 500 else "501_1000" if gap <= 1000 else "1001_5000")
            lag_ms_for_zeros[k] += 1
        else:
            active_zero_run = 0
        if status == "positive_spread" and b[0] == a[0] == t:
            counts["positive_same_millisecond"] += 1
    if (counts["zero_bid_older"] + counts["zero_ask_older"]
            + counts["zero_same_millisecond"] != counts["zero_spread"]):
        raise ValueError("G1_ZERO_SIDE_CLOCK_PARTITION_NOT_EXHAUSTIVE")
    if sum(counts[k] for k in (
            "missing_side", "stale_side", "crossed_spread",
            "positive_spread", "zero_spread")) != len(clock):
        raise ValueError("G1_SOURCE_STATE_COUNTER_NOT_EXHAUSTIVE")
    same_ms_bid: dict[int, int] = {}
    same_ms_ask: dict[int, int] = {}
    for t, px in bid:
        same_ms_bid[t] = px
    for t, px in ask:
        same_ms_ask[t] = px
    coincident_times = set(same_ms_bid).intersection(same_ms_ask)
    coincident_same_price = sum(same_ms_bid[t] == same_ms_ask[t] for t in coincident_times)
    coincident_positive = sum(same_ms_bid[t] < same_ms_ask[t] for t in coincident_times)
    coincident_crossed = sum(same_ms_bid[t] > same_ms_ask[t] for t in coincident_times)
    if (coincident_same_price != counts["zero_same_millisecond"]
            or coincident_positive != counts["positive_same_millisecond"]
            or coincident_crossed != counts["crossed_spread"] and coincident_crossed > 0):
        # Intra-millisecond tie order is otherwise rejected above.
        raise ValueError("G1_NATIVE_BOTH_UPDATE_CLOCK_MISMATCH")
    return {
        "asof_source_distinct_instants": len(clock),
        "source_quality_counts": {k: counts[k] for k in (
            "missing_side", "stale_side", "crossed_spread",
            "positive_spread", "zero_spread", "zero_same_millisecond")},
        "simultaneous_native_bid_ask_updated_instants": len(coincident_times),
        "simultaneous_native_equal_price": coincident_same_price,
        "simultaneous_native_positive_price_gap": coincident_positive,
        "simultaneous_native_crossed_price_gap": coincident_crossed,
        "zero_last_known_bid_older": counts["zero_bid_older"],
        "zero_last_known_ask_older": counts["zero_ask_older"],
        "zero_episode_count_consecutive_source_instants": episode_count,
        "zero_episode_max_consecutive_source_instants": max_zero_run,
        "zero_last_known_max_side_lag_ms_buckets": {
            k: lag_ms_for_zeros[k] for k in (
                "0", "1_100", "101_500", "501_1000", "1001_5000")},
        "is_original_historical_fill_execution_verified": False,
    }


def analyze_original(root: Path) -> dict[str, Any]:
    """Only examine source if the separate SHA+Protobuf decoder is fully GREEN."""
    original = reference.audit(root)
    if (original["status"] != "SOURCE_WIRE_INDEPENDENT_CUMULATIVE_DELTA_PARITY_PASS_NO_NET"
            or original["source_markets"] != 5 or original["NET_authorized"] is not False):
        raise ValueError("G1_PROTO_SECOND_AUDITOR_MUST_PASS_FIRST")
    market_reports = []
    aggregate: Counter[str] = Counter()
    for canonical in reference.TARGETS:
        folder = root / canonical
        data = json.loads((folder/"SOURCE_MARKET_MANIFEST_NOT_NET.json").read_bytes())
        by_window = []
        for index, frame in enumerate(data["windows"], 1):
            bmeta = frame["by_side"]["BID"]
            ameta = frame["by_side"]["ASK"]
            # Full original protobuf pages were already verified above;
            # use precisely the producer normalized integer records.
            bid = [json.loads(line) for line in (folder/bmeta["native_file"]).read_bytes().splitlines()]
            ask = [json.loads(line) for line in (folder/ameta["native_file"]).read_bytes().splitlines()]
            result = investigate(
                [(r["epoch_ms"],r["integer_price_1e5"]) for r in bid],
                [(r["epoch_ms"],r["integer_price_1e5"]) for r in ask],
            )
            by_window.append({"window_index": index, **result})
            aggregate.update(result["source_quality_counts"])
            aggregate["coincident_ticks"] += result["simultaneous_native_bid_ask_updated_instants"]
            aggregate["coincident_zero"] += result["simultaneous_native_equal_price"]
            aggregate["coincident_positive"] += result["simultaneous_native_positive_price_gap"]
        market_reports.append({"canonical":canonical, "windows":by_window})
        independent = next(m for m in original["per_market"] if m["canonical_symbol"] == canonical)
        for original_key in (
            "missing_side", "stale_side", "crossed_spread",
            "positive_spread", "zero_spread", "zero_same_millisecond"):
            if sum(w["source_quality_counts"][original_key] for w in by_window) != independent["counts"].get(original_key,0):
                raise ValueError("G1_NEW_FORENSIC_VS_PROTO_AUDITOR_PARITY_FAILURE")
    return {
        "identity": IDENTITY,
        "status": "EXPLORATORY_ORIGINAL_WIRE_DUAL_SIDE_SOURCE_FORENSIC_SHA_PASS_NO_NET",
        "source_run": ORIGINAL_RUN, "source_artifact_id": ORIGINAL_ARTIFACT,
        "source_expected_zip_sha256": ORIGINAL_SHA256,
        "source_markets_verified": len(market_reports),
        "independent_protobuf_second_decode_gate_passed": True,
        "asof_total_quality_counts": {
            k: aggregate[k] for k in (
                "missing_side","stale_side","crossed_spread","positive_spread",
                "zero_spread","zero_same_millisecond")},
        "native_same_ms_bidask_updates": aggregate["coincident_ticks"],
        "native_same_ms_equal_prices": aggregate["coincident_zero"],
        "native_same_ms_positive_spread": aggregate["coincident_positive"],
        "source_data_selection_posthoc_exploratory": True,
        "broker_executability_of_equal_quotes_proven": False,
        "historical_NET_authorized": False,
        "certified_traders": 0,
        "per_market": market_reports,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("original_source", type=Path)
    parser.add_argument("report_folder", type=Path)
    args = parser.parse_args()
    report = analyze_original(args.original_source)
    args.report_folder.mkdir(parents=True, exist_ok=True)
    file = args.report_folder / "G1_NATIVE_PROTO_ZERO_EPISODES_EXPLORATORY_NOT_NET.json"
    file.write_text(json.dumps(report, indent=2, sort_keys=True)+"\n", encoding="utf-8")
    (args.report_folder/"SHA256SUMS.txt").write_text(
        reference.digest(file.read_bytes())+"  "+file.name+"\n")
    print(json.dumps({
        "status": report["status"],
        "native_same_ms": report["native_same_ms_bidask_updates"],
        "native_zero_same_ms": report["native_same_ms_equal_prices"],
        "native_positive_same_ms": report["native_same_ms_positive_spread"],
        "quality": report["asof_total_quality_counts"],
        "NET": False, "certified": 0,
    },sort_keys=True))


if __name__ == "__main__":
    main()
