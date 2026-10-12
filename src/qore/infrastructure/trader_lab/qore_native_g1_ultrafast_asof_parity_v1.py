"""Native Trader Lab ultra-fast deterministic as-of BID/ASK source QA.

NumPy searchsorted is an optional ACCELERATION, not a new strategy engine.
Source SHAs, tick-grid, causality and source gates are checked independently.
A fast run can only be relied on after exact output parity vs reference.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

from qore.infrastructure.trader_lab import qore_native_g1_pre_quote_source_gate_v1 as gate
from qore.infrastructure.trader_lab import qore_native_g1_pre_native_side_join_v1 as reference

IDENTITY = "QORE_NATIVE_G1_PRE_ULTRAFAST_ASOF_PARITY_V1"
EPOCH = datetime(1970, 1, 1, tzinfo=UTC)


def _microseconds(at: datetime) -> int:
    dt = at - EPOCH
    return (dt.days * 86400 + dt.seconds) * 1_000_000 + dt.microseconds


def _fast_bytes(source: dict[str, Any], bidraw: bytes, askraw: bytes) -> bytes:
    if (
        source.get("identity") != reference.IDENTITY
        or source.get("mode") != "HISTORICAL_BACKFILL"
        or source.get("native_decoder_provenance_independently_verified") is not False
    ):
        raise ValueError("frozen source identity and decoded-side boundary required")
    bid = reference._read_side(bidraw, source.get("bid_decoded_jsonl_sha256"), "BID")
    ask = reference._read_side(askraw, source.get("ask_decoded_jsonl_sha256"), "ASK")
    contract = source.get("instrument")
    if not isinstance(contract, dict):
        raise ValueError("broker instrument contract required")
    tick_size = gate._price(contract.get("tick_size"), "tick")
    for side, rows in (("BID", bid), ("ASK", ask)):
        for item in rows:
            if gate._price(item.value, side) % tick_size:
                raise ValueError("native side does not respect declared tick-size")
    bid_times = np.asarray([_microseconds(e.clock) for e in bid], dtype=np.int64)
    ask_times = np.asarray([_microseconds(e.clock) for e in ask], dtype=np.int64)
    union = np.union1d(bid_times, ask_times)
    bi = np.searchsorted(bid_times, union, side="right") - 1
    ai = np.searchsorted(ask_times, union, side="right") - 1
    has_both = (bi >= 0) & (ai >= 0)
    bpos = np.clip(bi, 0, len(bid) - 1)
    apos = np.clip(ai, 0, len(ask) - 1)
    age_limit_us = int(gate.MAX_ASOF_AGE_SECONDS * 1_000_000)
    # Strictly past-as-of and NO lookahead/interpolation, independent per side.
    qualifying = has_both & ((union - bid_times[bpos]) <= age_limit_us) & (
        (union - ask_times[apos]) <= age_limit_us
    )
    qualified_times = union[qualifying]
    ib = bpos[qualifying]
    ia = apos[qualifying]
    if len(qualified_times) == 0 or len(qualified_times) > gate.MAX_PILOT_ROWS:
        raise ValueError("no valid quote snapshots or pilot too large")
    clock_map = {_microseconds(e.clock): e.clock for e in bid + ask}
    paired = []
    for t, i, j in zip(qualified_times, ib, ia, strict=True):
        b, a = bid[int(i)], ask[int(j)]
        dt = clock_map[int(t)]
        paired.append({
            "canonical_symbol": contract.get("canonical_symbol"),
            "provider_symbol": contract.get("provider_symbol"),
            "provider_symbol_id": contract.get("provider_symbol_id"),
            "source_sequence": len(paired),
            "decision_time_utc": dt.isoformat(timespec="microseconds").replace("+00:00", "Z"),
            "bid_market_time_utc": b.clock_text,
            "ask_market_time_utc": a.clock_text,
            "both_sides_received_at_utc": None,
            "bid": b.value,
            "ask": a.value,
            "bid_native_sequence_witness": b.native_sequence,
            "ask_native_sequence_witness": a.native_sequence,
        })
    raw = ("\n".join(json.dumps(row, sort_keys=True) for row in paired) + "\n").encode()
    gate_manifest = dict(source.get("quote_gate_manifest", {}))
    gate_manifest["quotes_jsonl_sha256"] = hashlib.sha256(raw).hexdigest()
    gate_result = gate.audit(gate_manifest, raw)
    if gate_result["pilot_market_count"] != 1 or gate_result["historical_NET_authorized"]:
        raise ValueError("G1 source-only safety gate failed")
    return raw


def exact_parity(source: dict[str, Any], bidraw: bytes, askraw: bytes) -> dict[str, Any]:
    """Reference parity against unaccelerated independent code (not a warm cache)."""
    old_report, slow = reference.join_historical(source, bidraw, askraw)
    fast = _fast_bytes(source, bidraw, askraw)
    if fast != slow:
        raise ValueError("ULTRAFAST_SOURCE_JOIN_OUTPUT_PARITY_FAILURE")
    return {
        "identity": IDENTITY,
        "status": "SOURCE_ONLY_FAST_REFERENCE_BYTES_IDENTICAL",
        "sha256": hashlib.sha256(slow).hexdigest(),
        "bid_input_sha256": hashlib.sha256(bidraw).hexdigest(),
        "ask_input_sha256": hashlib.sha256(askraw).hexdigest(),
        "snapshots": old_report["paired_asof_rows"],
        "byte_identical_to_reference": True,
        "native_provider_raw_protobuf_attested": False,
        "historical_NET_authorized": False,
        "certified_traders": 0,
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("manifest", type=Path)
    p.add_argument("bid_jsonl", type=Path)
    p.add_argument("ask_jsonl", type=Path)
    p.add_argument("out_json", type=Path)
    args = p.parse_args()
    result = exact_parity(
        json.loads(args.manifest.read_text()),
        args.bid_jsonl.read_bytes(),
        args.ask_jsonl.read_bytes(),
    )
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
