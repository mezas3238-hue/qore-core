"""Reconstruct an as-of BID+ASK pilot from two time-ordered, hashed side streams.

Input streams are DECODED research JSONL, not original cTrader protobuf bytes.
The upstream native decoder, account and broker must be independently attested.
Historical mode only; no delivery-time illusion, no trades, no forward filling.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import qore_native_g1_pre_quote_source_gate_v1 as gate

IDENTITY = "QORE_NATIVE_G1_PRE_TWO_NATIVE_SIDE_ASOF_JOIN_V1"


@dataclass(frozen=True)
class Event:
    clock: Any
    clock_text: str
    native_sequence: int
    value: str


def _read_side(raw: bytes, expected_sha: Any, label: str) -> list[Event]:
    if hashlib.sha256(raw).hexdigest() != gate._sha(expected_sha, label):
        raise ValueError(f"{label} original decoded stream SHA mismatch")
    try:
        body = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"{label} not UTF8") from exc
    events: list[Event] = []
    for line in body.splitlines():
        if not line.strip():
            raise ValueError(f"{label}: blank tick line")
        try:
            row = json.loads(line)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{label}: invalid JSONL") from exc
        if not isinstance(row, dict):
            raise ValueError(f"{label}: tick not an object")
        clock_text = row.get("event_time_utc")
        clock = gate._utc(clock_text, label)
        price = gate._price(row.get("price"), label)
        seq = row.get("native_sequence")
        if isinstance(seq, bool) or not isinstance(seq, int) or seq < 0:
            raise ValueError(f"{label}: invalid native sequence")
        if events and (clock < events[-1].clock or seq <= events[-1].native_sequence):
            raise ValueError(f"{label}: tick chronology or native sequence lost")
        events.append(Event(clock, clock_text, seq, str(price)))
        if len(events) > gate.MAX_PILOT_ROWS:
            raise ValueError("oversized source pilot: split by SHA shards")
    if not events:
        raise ValueError(f"{label}: zero native side events")
    return events


def join_historical(
    source_manifest: dict[str, Any], bid_raw: bytes, ask_raw: bytes
) -> tuple[dict[str, Any], bytes]:
    """Return source audit and paired JSONL; never certify originating protobuf."""
    if source_manifest.get("identity") != IDENTITY:
        raise ValueError("two-side join manifest identity missing")
    if source_manifest.get("mode") != "HISTORICAL_BACKFILL":
        raise ValueError("join is historical ONLY, no invented receive times")
    if source_manifest.get("native_decoder_provenance_independently_verified") is not False:
        raise ValueError("this stage cannot independently attest original protobuf")
    bid = _read_side(bid_raw, source_manifest.get("bid_decoded_jsonl_sha256"), "BID")
    ask = _read_side(ask_raw, source_manifest.get("ask_decoded_jsonl_sha256"), "ASK")
    instrument = source_manifest.get("instrument")
    if not isinstance(instrument, dict):
        raise ValueError("single-contract provenance required")
    symbol = instrument.get("canonical_symbol")
    tick = gate._price(instrument.get("tick_size"), "declared tick")
    for side, events in (("BID", bid), ("ASK", ask)):
        for event in events:
            if gate._price(event.value, side) % tick:
                raise ValueError(f"{side}: native decoded price off tick grid")
    # A union of *past or present* native events, not a nearest-neighbour join.
    timeline = sorted(set(e.clock for e in bid) | set(e.clock for e in ask))
    i = j = 0
    last_bid = last_ask = None
    pairs = []
    for clock in timeline:
        while i < len(bid) and bid[i].clock <= clock:
            last_bid = bid[i]
            i += 1
        while j < len(ask) and ask[j].clock <= clock:
            last_ask = ask[j]
            j += 1
        if last_bid is None or last_ask is None:
            continue
        # Do not carry a silent/stale side forward for arbitrarily long gaps.
        max_age = timedelta(seconds=float(gate.MAX_ASOF_AGE_SECONDS))
        if clock - last_bid.clock > max_age or clock - last_ask.clock > max_age:
            continue
        pairs.append({
            "canonical_symbol": symbol,
            "provider_symbol": instrument.get("provider_symbol"),
            "provider_symbol_id": instrument.get("provider_symbol_id"),
            "source_sequence": len(pairs),
            "decision_time_utc": clock.isoformat(timespec="microseconds").replace("+00:00", "Z"),
            "bid_market_time_utc": last_bid.clock_text,
            "ask_market_time_utc": last_ask.clock_text,
            "both_sides_received_at_utc": None,
            "bid": last_bid.value,
            "ask": last_ask.value,
            "bid_native_sequence_witness": last_bid.native_sequence,
            "ask_native_sequence_witness": last_ask.native_sequence,
        })
        if len(pairs) > gate.MAX_PILOT_ROWS:
            raise ValueError("as-of joined pilot cap exceeded")
    if not pairs:
        raise ValueError("no matched BID/ASK even with as-of chronology")
    joined_raw = ("\n".join(json.dumps(row, sort_keys=True) for row in pairs) + "\n").encode()
    output_manifest = dict(source_manifest.get("quote_gate_manifest", {}))
    output_manifest["quotes_jsonl_sha256"] = hashlib.sha256(joined_raw).hexdigest()
    result = gate.audit(output_manifest, joined_raw)
    if result["pilot_market_count"] != 1:
        raise ValueError("native as-of side join is single market per provenance bundle")
    report = {
        "identity": "QORE_NATIVE_G1_PRE_SIDE_STREAM_JOIN_AUDIT_V1",
        "status": "ASOF_REPRODUCED_ON_DECODED_SIDE_STREAMS_ONLY",
        "canonical_symbol": symbol,
        "decoded_bid_sha256": hashlib.sha256(bid_raw).hexdigest(),
        "decoded_ask_sha256": hashlib.sha256(ask_raw).hexdigest(),
        "decoded_bid_rows": len(bid),
        "decoded_ask_rows": len(ask),
        "paired_asof_rows": len(pairs),
        "source_decoded_side_join_reproducible": True,
        "native_ctrader_protobuf_origin_verified": False,
        "upstream_decoder_and_hasMore_independently_verified": False,
        "entry_exit_historical_coverage_verified": False,
        "historical_NET_authorized": False,
        "certified_traders": 0,
        "format_audit": result,
    }
    return report, joined_raw


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("manifest_json", type=Path)
    p.add_argument("bid_native_decoded_jsonl", type=Path)
    p.add_argument("ask_native_decoded_jsonl", type=Path)
    p.add_argument("output_folder", type=Path)
    args = p.parse_args()
    report, output = join_historical(
        json.loads(args.manifest_json.read_text(encoding="utf-8")),
        args.bid_native_decoded_jsonl.read_bytes(),
        args.ask_native_decoded_jsonl.read_bytes(),
    )
    args.output_folder.mkdir(parents=True, exist_ok=True)
    quotes = args.output_folder / "asof-decoded-native-BID-ASK-NOT-NET.jsonl"
    summary = args.output_folder / "join-source-format-NOT-NET.json"
    quotes.write_bytes(output)
    summary.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (args.output_folder / "SHA256SUMS.txt").write_text(
        hashlib.sha256(output).hexdigest() + f"  {quotes.name}\n"
        + hashlib.sha256(summary.read_bytes()).hexdigest() + f"  {summary.name}\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "status": report["status"],
        "decoded_bid_rows": report["decoded_bid_rows"],
        "decoded_ask_rows": report["decoded_ask_rows"],
        "historical_NET_authorized": False,
    }))


if __name__ == "__main__":
    main()
