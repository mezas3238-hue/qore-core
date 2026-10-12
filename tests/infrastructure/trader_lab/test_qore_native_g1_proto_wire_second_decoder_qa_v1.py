"""Source-only independent Protobuf tick wire decoder/side custody tests."""
from __future__ import annotations

import hashlib
import json
import struct
from datetime import UTC, datetime
from pathlib import Path

import pytest
from ctrader_open_api.messages.OpenApiModelMessages_pb2 import ProtoOATickData

from qore.infrastructure.trader_lab import qore_native_g1_proto_wire_second_decoder_qa_v1 as a


def encode(*ticks):
    out = bytearray()
    for timestamp, value in ticks:
        wire = ProtoOATickData(timestamp=timestamp, tick=value).SerializeToString(deterministic=True)
        out.extend(struct.pack(">I",len(wire)))
        out.extend(wire)
    return bytes(out)


def test_cumulative_original_wire_unsigned_absolute_signed_delta():
    first = 1615899601000
    payload = encode((first+100, 110020), (-100, -5), (-250, 8))
    observed = a.decode_batch_fields(payload, first, first+1000)
    assert observed == [(first+100,110020), (first,110015), (first-250,110023)] if False else (
        observed == [(first+100,110020), (first,110015), (first-250,110023)]
    )


def test_invalid_framing_or_price_delta_fails_closed():
    with pytest.raises(ValueError, match="FRAME_HEADER"):
        a.decode_batch_fields(b"\x00", 0, 1000)
    with pytest.raises(ValueError, match="FRAME_LENGTH"):
        a.decode_batch_fields(b"\x00\x00\x10\x00" + b"\x01", 0, 1000)
    with pytest.raises(ValueError, match="CUMULATIVE"):
        a.decode_batch_fields(encode((100, 10), (-1, -20)), 0, 1000)


def test_exact_asof_causality_zero_crossed_stale_not_fills():
    bid = [(0, 100000), (2000, 100005), (4000, 100030)]
    ask = [(1000, 100020), (3000, 100005), (5000, 100010)]
    out = a.asof_quality(bid, ask)
    assert out == {
        "missing_side":1, "stale_side":0, "crossed_spread":2,
        "zero_spread":1, "positive_spread":2, "zero_same_millisecond":0,
    }


def test_independent_tick_byte_frames_match_original_integer_decoded_sha(tmp_path: Path):
    start = 1615899600000
    sid = "EURUSD-1-BID"
    fields = encode((start+200,110010), (-100, -2))
    s_wire = tmp_path/(sid+"-tick-fields.pbframes")
    s_native = tmp_path/(sid+"-integer.jsonl")
    s_dec = tmp_path/(sid+"-decimal.jsonl")
    s_wire.write_bytes(fields)
    native_rows = [
        {"epoch_ms":start+100,"integer_price_1e5":110008},
        {"epoch_ms":start+200,"integer_price_1e5":110010},
    ]
    normalized = [
        {"event_time_utc":datetime.fromtimestamp(at/1000,tz=UTC).isoformat(timespec="milliseconds").replace("+00:00","Z"),
         "native_sequence":seq,"price":str(value/100000)}
        for seq,(at,value) in enumerate([(start+100,110008),(start+200,110010)])
    ]
    s_native.write_text("".join(json.dumps(x,sort_keys=True)+"\n" for x in native_rows))
    s_dec.write_text("".join(json.dumps(x,sort_keys=True)+"\n" for x in normalized))
    m = {
        "wire_tick_fields_only_account_wrapper_excluded":True,
        "count":2,"total_provider_requests":1,
        "native_file":s_native.name,"native_sha256":a.digest(s_native.read_bytes()),
        "decimal_file":s_dec.name,"decimal_sha256":a.digest(s_dec.read_bytes()),
        "wire_file":s_wire.name,"wire_sha256":a.digest(s_wire.read_bytes()),
        "wire_pages":[{"from_ms":start,"to_ms":start+1799999,
                       "has_more":False,"accepted_leaf":True,"tick_count":2,
                       "wire_offset":0,"wire_length":len(fields),
                       "wire_section_sha256":a.digest(fields)}],
    }
    got = a.verify_side(tmp_path,"EURUSD",1,"BID",m,start,start+1800000)
    assert got == [(start+100,110008),(start+200,110010)]
    s_wire.write_bytes(fields+b"tampered")
    with pytest.raises(ValueError, match="INTEGRITY"):
        a.verify_side(tmp_path,"EURUSD",1,"BID",m,start,start+1800000)


def test_market_batch_with_hasmore_must_be_completely_split(tmp_path: Path):
    start = 1615899600000
    prefix = "EURUSD-1-ASK"
    n = tmp_path/(prefix+"-integer.jsonl")
    d = tmp_path/(prefix+"-decimal.jsonl")
    wire = tmp_path/(prefix+"-tick-fields.pbframes")
    b0 = encode((start+3,120000))
    b1 = encode((start+1,120000))
    b2 = encode((start+3,120001))
    wire.write_bytes(b0+b1+b2)
    native = [{"epoch_ms":start+1,"integer_price_1e5":120000},
              {"epoch_ms":start+3,"integer_price_1e5":120001}]
    decoded = [
        {"event_time_utc":datetime.fromtimestamp(x["epoch_ms"]/1000,tz=UTC).isoformat(timespec="milliseconds").replace("+00:00","Z"),
         "native_sequence":i,"price":str(x["integer_price_1e5"]/100000)}
        for i,x in enumerate(native)
    ]
    n.write_text("".join(json.dumps(x,sort_keys=True)+"\n" for x in native))
    d.write_text("".join(json.dumps(x,sort_keys=True)+"\n" for x in decoded))
    pages=[]
    offset=0
    for bounds, part, more in (
        ((start,start+3),b0,True),
        ((start,start+1),b1,False),
        ((start+2,start+3),b2,False),
    ):
        pages.append({"from_ms":bounds[0],"to_ms":bounds[1],"wire_offset":offset,
                      "wire_length":len(part),"wire_section_sha256":a.digest(part),
                      "has_more":more,"accepted_leaf":not more,"tick_count":1})
        offset+=len(part)
    meta={"count":2,"total_provider_requests":3,
          "native_file":n.name,"native_sha256":a.digest(n.read_bytes()),
          "decimal_file":d.name,"decimal_sha256":a.digest(d.read_bytes()),
          "wire_file":wire.name,"wire_sha256":a.digest(wire.read_bytes()),
          "wire_tick_fields_only_account_wrapper_excluded":True,"wire_pages":pages}
    assert a.verify_side(tmp_path,"EURUSD",1,"ASK",meta,start,start+4) == [
        (start+1,120000),(start+3,120001)]
    meta["wire_pages"][0]["accepted_leaf"]=True
    with pytest.raises(ValueError, match="HASMORE"):
        a.verify_side(tmp_path,"EURUSD",1,"ASK",meta,start,start+4)


def test_source_absent_requires_witness_not_fake_data(tmp_path: Path):
    with pytest.raises(ValueError, match="SOURCE_SHA_REGISTER_MISSING"):
        a.audit(tmp_path)


def test_synthetic_source_cannot_claim_net_or_full_33():
    assert a.IDENTITY.endswith("_V1")
    assert len(a.TARGETS) == 5
    assert len(a.WINDOWS) == 2
