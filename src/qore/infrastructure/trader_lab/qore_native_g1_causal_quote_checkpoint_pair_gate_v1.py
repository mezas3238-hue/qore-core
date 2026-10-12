"""Strict historical BID/ASK source gate for paired fictitious decision clocks.

It never computes fills, fees, trade outcomes, PnL or a NET strategy. Enforce
causal >=0 ages with no future ticks and prohibit zero/crossed source prices.
"""
from __future__ import annotations

import argparse
import bisect
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import qore_native_g1_proto_wire_second_decoder_qa_v1 as verified

IDENTITY = "QORE_NATIVE_G1_CAUSAL_TWO_TIME_SOURCE_QUOTE_ELIGIBILITY_V1"
AGE_LIMIT_MS = 5000
CHECKPOINT_MINUTES = ((5, 15), (10, 25))
SOURCE_RUN = 38288411671
SOURCE_ARTIFACT = 11764163362

STATES = (
    "MISSING_SIDE", "STALE_SIDE", "CROSSED_SPREAD", "ZERO_SPREAD",
    "OK_POSITIVE_BIDASK",
)


def _validate_ticks(events: list[tuple[int, int]]) -> list[int]:
    clocks: list[int] = []
    preceding = None
    for event in events:
        if (not isinstance(event, tuple) or len(event) != 2
                or type(event[0]) is not int or type(event[1]) is not int or event[1] <= 0):
            raise ValueError("G1_SOURCE_TICK_TYPE_OR_PRICE_INVALID")
        if preceding and event[0] < preceding[0]:
            raise ValueError("G1_SOURCE_SIDE_CLOCK_NONMONOTONE")
        if preceding and event[0] == preceding[0] and event[1] != preceding[1]:
            raise ValueError("G1_SOURCE_CONFLICTING_SAME_MILLISECOND_PRICES")
        clocks.append(event[0])
        preceding = event
    return clocks


def _lookup(
    decisions: int, stream: list[tuple[int, int]], clocks: list[int]
) -> tuple[int, int] | None:
    found = bisect.bisect_right(clocks, decisions) - 1
    if found < 0:
        return None
    value = stream[found]
    if value[0] > decisions:
        raise ValueError("G1_CAUSAL_LOOKAHEAD_IMPOSSIBLE")
    return value


def decision_quality(
    at_ms: int, bids: list[tuple[int, int]], asks: list[tuple[int, int]],
    *, max_age_ms: int = AGE_LIMIT_MS,
) -> str:
    if type(at_ms) is not int or type(max_age_ms) is not int or max_age_ms <= 0:
        raise ValueError("G1_DECISION_TIMESTAMP_OR_MAX_AGE_INVALID")
    btimes = _validate_ticks(bids)
    atimes = _validate_ticks(asks)
    b = _lookup(at_ms, bids, btimes)
    a = _lookup(at_ms, asks, atimes)
    if b is None or a is None:
        return "MISSING_SIDE"
    if at_ms - b[0] > max_age_ms or at_ms - a[0] > max_age_ms:
        return "STALE_SIDE"
    if b[1] > a[1]:
        return "CROSSED_SPREAD"
    if b[1] == a[1]:
        return "ZERO_SPREAD"
    return "OK_POSITIVE_BIDASK"


def check_pair(
    entry_time: int, exit_time: int,
    bids: list[tuple[int, int]], asks: list[tuple[int, int]],
) -> dict[str, Any]:
    if (type(entry_time) is not int or type(exit_time) is not int
            or entry_time >= exit_time):
        raise ValueError("G1_SOURCE_PAIR_TIMES_INVALID")
    entry = decision_quality(entry_time, bids, asks)
    exit_ = decision_quality(exit_time, bids, asks)
    return {
        "entry_source_quality": entry, "exit_source_quality": exit_,
        "source_pair_eligible": entry == "OK_POSITIVE_BIDASK" and exit_ == "OK_POSITIVE_BIDASK",
        "economic_PnL_or_execution_authorized": False,
    }


def actual_source_checkpoints(folder: Path) -> dict[str, Any]:
    """Gate original producer fields through independent protobuf second decoder."""
    parent = verified.audit(folder)
    if (parent["status"] != "SOURCE_WIRE_INDEPENDENT_CUMULATIVE_DELTA_PARITY_PASS_NO_NET"
            or parent["source_markets"] != 5 or parent["source_windows_per_market"] != 2
            or parent["NET_authorized"] is not False):
        raise ValueError("G1_SECOND_DECODER_OR_SOURCE_IDENTITY_NOT_PASS")
    reports = []
    states_entry: Counter[str] = Counter()
    states_exit: Counter[str] = Counter()
    eligibility = 0
    for canonical in verified.TARGETS:
        market_dir = folder / canonical
        m = json.loads((market_dir / "SOURCE_MARKET_MANIFEST_NOT_NET.json").read_bytes())
        for win_idx, frozen in enumerate(verified.WINDOWS, 1):
            source = m["windows"][win_idx-1]
            if source.get("frozen") != list(frozen):
                raise ValueError("G1_FROZEN_SOURCE_WINDOW_DRIFT")
            start, stop = (int(datetime.fromisoformat(s).timestamp()*1000) for s in frozen)
            bids = verified.verify_side(
                market_dir, canonical, win_idx, "BID",
                source["by_side"]["BID"], start, stop,
            )
            asks = verified.verify_side(
                market_dir, canonical, win_idx, "ASK",
                source["by_side"]["ASK"], start, stop,
            )
            for pair_idx, (m_entry, m_exit) in enumerate(CHECKPOINT_MINUTES, 1):
                entry_clock = start + m_entry * 60000
                exit_clock = start + m_exit * 60000
                if entry_clock >= stop or exit_clock >= stop:
                    raise ValueError("G1_FROZEN_CHECKPOINT_OUTSIDE_WINDOW")
                outcome = check_pair(entry_clock, exit_clock, bids, asks)
                states_entry[outcome["entry_source_quality"]] += 1
                states_exit[outcome["exit_source_quality"]] += 1
                eligibility += int(outcome["source_pair_eligible"])
                reports.append({
                    "canonical":canonical, "source_window_index":win_idx,
                    "clock_checkpoint_pair_id":pair_idx,
                    "entry_minutes_from_start":m_entry,
                    "exit_minutes_from_start":m_exit,
                    **outcome,
                })
    expected = len(verified.TARGETS) * len(verified.WINDOWS) * len(CHECKPOINT_MINUTES)
    if len(reports) != expected or expected != 20:
        raise ValueError("G1_FROZEN_CHECKPOINT_COUNT_INCONSISTENT")
    if sum(states_entry.values()) != expected or sum(states_exit.values()) != expected:
        raise ValueError("G1_CHECKPOINT_COVERAGE_PARTITION_INVALID")
    if eligibility != sum(int(r["source_pair_eligible"]) for r in reports):
        raise ValueError("G1_CHECKPOINT_ELIGIBILITY_COUNT_INVALID")
    return {
        "identity": IDENTITY, "status": "G1_SOURCE_CHECKPOINT_20_CAUSAL_ASOF_GATE_ASSESSED_NO_NET",
        "source_run": SOURCE_RUN, "original_artifact_id": SOURCE_ARTIFACT,
        "source_field_protobuf_independent_redecode_verified": True,
        "frozen_checkpoints_are_fictitious_not_strategy_entries": True,
        "time_freshness_policy_milliseconds": AGE_LIMIT_MS,
        "source_test_pairs": expected, "eligible_positive_both_times": eligibility,
        "source_only_rejected_pairs": expected-eligibility,
        "entry_states": {k: states_entry[k] for k in STATES},
        "exit_states": {k: states_exit[k] for k in STATES},
        "real_signal_trade_entry_or_exit_tested": False,
        "broker_fills_commission_slippage_swap_measured": False,
        "historical_NET_authorized": False, "certified_traders": 0,
        "records": reports,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("original_proto_source", type=Path)
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()
    result = actual_source_checkpoints(args.original_proto_source)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    p = args.output_dir / "G1_CAUSAL_SOURCE_ONLY_CHECKPOINT_PAIR_GATE.json"
    p.write_text(json.dumps(result, sort_keys=True, indent=2)+"\n", encoding="utf-8")
    (args.output_dir/"SHA256SUMS.txt").write_text(
        verified.digest(p.read_bytes())+"  "+p.name+"\n", encoding="utf-8")
    print(json.dumps({
        "status":result["status"],"source_test_pairs":result["source_test_pairs"],
        "eligible_positive_both_times":result["eligible_positive_both_times"],
        "entry_states":result["entry_states"],"exit_states":result["exit_states"],
        "NET":False,"certified":0,
    },sort_keys=True))


if __name__ == "__main__":
    main()
