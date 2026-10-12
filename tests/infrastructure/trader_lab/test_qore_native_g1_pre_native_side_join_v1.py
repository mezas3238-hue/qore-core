"""Strict as-of BID and ASK reconstruction tests, synthetic decoded native sides only."""
from __future__ import annotations

import hashlib
import json

import pytest

from qore.infrastructure.trader_lab import qore_native_g1_pre_native_side_join_v1 as j
from test_qore_native_g1_pre_quote_source_gate_v1 import example


def payload(rows):
    return ("\n".join(json.dumps(x, sort_keys=True) for x in rows) + "\n").encode()


def inputs():
    m, _ = example()
    m["instruments"] = m["instruments"][:1]
    bid = [
        {"event_time_utc": "2026-10-12T13:00:00Z", "native_sequence": 1, "price": "1.10000"},
        {"event_time_utc": "2026-10-12T13:00:02Z", "native_sequence": 2, "price": "1.10001"},
    ]
    ask = [
        {"event_time_utc": "2026-10-12T13:00:01Z", "native_sequence": 1, "price": "1.10002"},
        {"event_time_utc": "2026-10-12T13:00:02Z", "native_sequence": 2, "price": "1.10003"},
    ]
    src = {
        "identity": j.IDENTITY,
        "mode": "HISTORICAL_BACKFILL",
        "native_decoder_provenance_independently_verified": False,
        "instrument": m["instruments"][0],
        "quote_gate_manifest": m,
    }
    return src, bid, ask


def run(src, bid, ask):
    bb, aa = payload(bid), payload(ask)
    src["bid_decoded_jsonl_sha256"] = hashlib.sha256(bb).hexdigest()
    src["ask_decoded_jsonl_sha256"] = hashlib.sha256(aa).hexdigest()
    return j.join_historical(src, bb, aa)


def test_asof_does_not_interpolate_or_backfill_from_future_tick():
    src, bids, asks = inputs()
    report, pairs_raw = run(src, bids, asks)
    pairs = [json.loads(line) for line in pairs_raw.splitlines()]
    assert len(pairs) == 2
    assert pairs[0]["decision_time_utc"] == "2026-10-12T13:00:01.000000Z"
    assert pairs[0]["bid"] == "1.10000"
    assert pairs[0]["ask"] == "1.10002"
    assert pairs[0]["bid_native_sequence_witness"] == 1
    assert pairs[1]["bid"] == "1.10001"
    assert pairs[1]["ask"] == "1.10003"
    assert report["format_audit"]["asof_format_valid_rows_not_fills"] == 2
    assert report["native_ctrader_protobuf_origin_verified"] is False
    assert report["historical_NET_authorized"] is False


def test_same_timestamp_both_sides_join_once_after_all_updates():
    src, bids, asks = inputs()
    bids[0]["event_time_utc"] = "2026-10-12T13:00:01Z"
    out, raw = run(src, bids, asks)
    assert len(raw.splitlines()) == 2
    assert out["paired_asof_rows"] == 2


def test_sha_tamper_fails_and_no_fake_decoder_attestation():
    src, bids, asks = inputs()
    run(src, bids, asks)
    with pytest.raises(ValueError, match="SHA mismatch"):
        j.join_historical(src, b'{"fake":true}\n', payload(asks))
    src, bids, asks = inputs()
    src["native_decoder_provenance_independently_verified"] = True
    with pytest.raises(ValueError, match="independently attest"):
        run(src, bids, asks)


def test_out_of_order_native_side_and_tick_off_grid_are_rejected():
    src, bids, asks = inputs()
    bids[1]["event_time_utc"] = "2026-10-12T12:59:58Z"
    with pytest.raises(ValueError, match="chronology"):
        run(src, bids, asks)
    src, bids, asks = inputs()
    bids[1]["price"] = "1.100011"
    with pytest.raises(ValueError, match="tick grid"):
        run(src, bids, asks)


def test_no_bid_and_ask_overlap_fails_closed():
    src, bids, asks = inputs()
    bids[0]["event_time_utc"] = "2026-10-12T13:00:10Z"
    bids[1]["event_time_utc"] = "2026-10-12T13:00:11Z"
    with pytest.raises(ValueError, match="no matched"):
        run(src, bids, asks)


def test_forward_receipt_not_synthesized_from_backfill():
    src, bids, asks = inputs()
    src["mode"] = "FORWARD_PAPER_CAPTURE"
    with pytest.raises(ValueError, match="historical ONLY"):
        run(src, bids, asks)
