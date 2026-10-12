"""Verify optimized quote as-of has exact reference parity; SYNTHETIC SOURCE."""
from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.trader_lab import qore_native_g1_ultrafast_asof_parity_v1 as fast
from test_qore_native_g1_pre_native_side_join_v1 import inputs, payload


def ready():
    src, b, a = inputs()
    br, ar = payload(b), payload(a)
    src["bid_decoded_jsonl_sha256"] = hashlib.sha256(br).hexdigest()
    src["ask_decoded_jsonl_sha256"] = hashlib.sha256(ar).hexdigest()
    return src, br, ar


def large_fixture(n=2500):
    src, _, _ = ready()
    base = datetime(2026, 10, 12, 13, tzinfo=UTC)
    b, a = [], []
    for i in range(n):
        for stream, delay, offset in ((b, 0, 0), (a, 50, 10)):
            at = base + timedelta(milliseconds=100 * i + delay)
            stream.append({
                "event_time_utc": at.isoformat(timespec="milliseconds").replace("+00:00", "Z"),
                "native_sequence": i,
                "price": format(Decimal("1.10000") + Decimal((i % 4) + offset) / 100000, "f"),
            })
    br, ar = payload(b), payload(a)
    src["bid_decoded_jsonl_sha256"] = hashlib.sha256(br).hexdigest()
    src["ask_decoded_jsonl_sha256"] = hashlib.sha256(ar).hexdigest()
    return src, br, ar


def test_two_source_side_pilot_exact_byte_parity():
    src, br, ar = ready()
    result = fast.exact_parity(src, br, ar)
    assert result["snapshots"] == 2
    assert result["byte_identical_to_reference"] is True
    assert result["historical_NET_authorized"] is False
    assert result["certified_traders"] == 0


def test_5000_synthetic_side_events_fast_matches_reference():
    src, br, ar = large_fixture()
    result = fast.exact_parity(src, br, ar)
    assert result["snapshots"] == 4999
    assert result["sha256"] == hashlib.sha256(fast._fast_bytes(src, br, ar)).hexdigest()
    assert result["native_provider_raw_protobuf_attested"] is False


def test_bad_source_shas_do_not_become_fast_cache_hit():
    src, br, ar = ready()
    src["bid_decoded_jsonl_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="SHA mismatch"):
        fast.exact_parity(src, br, ar)


def test_unattested_protobuf_source_cannot_be_promoted():
    src, br, ar = ready()
    src["native_decoder_provenance_independently_verified"] = True
    with pytest.raises(ValueError, match="cannot independently attest"):
        fast.exact_parity(src, br, ar)


def test_wrong_tick_contract_fails_closed():
    src, br, ar = ready()
    src["instrument"]["tick_size"] = "0.00003"
    with pytest.raises(ValueError, match="tick"):
        fast.exact_parity(src, br, ar)


def test_out_of_order_timestamp_rejected_before_vectorized_join():
    src, _, ar = ready()
    b = [
        {"event_time_utc": "2026-10-12T13:00:02Z", "native_sequence": 1, "price": "1.10000"},
        {"event_time_utc": "2026-10-12T13:00:01Z", "native_sequence": 2, "price": "1.10001"},
    ]
    br = payload(b)
    src["bid_decoded_jsonl_sha256"] = hashlib.sha256(br).hexdigest()
    with pytest.raises(ValueError, match="chronology"):
        fast.exact_parity(src, br, ar)


def test_duplicate_same_millisecond_uses_last_known_native_sequence():
    src, b, a = inputs()
    b.append({"event_time_utc": b[-1]["event_time_utc"], "native_sequence": 3,
              "price": "1.10002"})
    br, ar = payload(b), payload(a)
    src["bid_decoded_jsonl_sha256"] = hashlib.sha256(br).hexdigest()
    src["ask_decoded_jsonl_sha256"] = hashlib.sha256(ar).hexdigest()
    report = fast.exact_parity(src, br, ar)
    assert report["snapshots"] == 2
