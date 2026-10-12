"""Negative synthetic native ProtoOA tick source and zero/stale eligibility tests."""
from __future__ import annotations

import json
import struct
from datetime import UTC, datetime
from pathlib import Path

import pytest
from ctrader_open_api.messages.OpenApiModelMessages_pb2 import ProtoOATickData

from qore.infrastructure.trader_lab import qore_native_g1_six_e1_original_proto_bidask_pair_qa_v1 as a
from qore.infrastructure.trader_lab import qore_native_g1_six_e1_original_event_pair_quote_source_v1 as source


def make_original_field_source(folder:Path, *, canonical:str="GBPUSD",
                               day:str="2021-03-16",clock:str="entry",side:str="BID",
                               native_price:int=110000,minute_offset:int=5):
    first,last=source.source_period(day,clock)
    at=first+minute_offset*60_000
    native=ProtoOATickData(timestamp=at,tick=native_price)
    encoded=native.SerializeToString(deterministic=True)
    original_wire=struct.pack(">I",len(encoded))+encoded
    prefix=f"{canonical}-{day}-{clock}-{side}"
    fields=folder/(prefix+"-proto-fields.pbframes")
    ints=folder/(prefix+"-integer.jsonl")
    decimal=folder/(prefix+"-decimal.jsonl")
    fields.write_bytes(original_wire)
    ints.write_text(json.dumps({"epoch_ms":at,"integer_price_1e5":native_price})+"\n")
    decimal.write_text(json.dumps({
        "event_time_utc":datetime.fromtimestamp(at/1000,tz=UTC).isoformat(timespec="milliseconds").replace("+00:00","Z"),
        "native_sequence":0,
        "price":format(native_price/100000,"f"),
    })+"\n")
    return {
        "start_utc_ms_inclusive":first,"end_utc_ms_exclusive":last,
        "provider_requests":1,"native_tick_count":1,
        "wire_field_protobuf_account_wrapper_archived":False,
        "pages":[{
            "from_ms":first,"to_ms":last-1,
            "has_more":False,"accepted_leaf":True,"tick_count":1,
            "wire_offset":0,"wire_length":len(original_wire),
            "wire_section_sha256":a.proto.digest(original_wire),
        }],
        "wire_file":fields.name,"wire_sha256":a.proto.digest(fields.read_bytes()),
        "int_file":ints.name,"int_sha256":a.proto.digest(ints.read_bytes()),
        "decimal_file":decimal.name,"decimal_sha256":a.proto.digest(decimal.read_bytes()),
    }


def test_original_proto_field_redecoded_identical_to_int_and_decimal(tmp_path:Path):
    meta=make_original_field_source(tmp_path)
    rows=a._witness_original_side(tmp_path,"GBPUSD","2021-03-16","entry","BID",meta)
    start,_=source.source_period("2021-03-16","entry")
    assert rows==[(start+300_000,110000)]
    assert meta["wire_field_protobuf_account_wrapper_archived"] is False


def test_mutated_original_wire_and_hasmore_must_not_pass(tmp_path:Path):
    meta=make_original_field_source(tmp_path)
    (tmp_path/meta["wire_file"]).write_bytes(b"altered")
    with pytest.raises(ValueError,match="SHA_BYTE_DRIFT"):
        a._witness_original_side(tmp_path,"GBPUSD","2021-03-16","entry","BID",meta)
    meta=make_original_field_source(tmp_path)
    meta["pages"][0]["accepted_leaf"]=False
    with pytest.raises(ValueError,match="HASMORE_BOUNDARY"):
        a._witness_original_side(tmp_path,"GBPUSD","2021-03-16","entry","BID",meta)


def test_original_quote_zero_or_stale_not_eligible_with_bidask_at_both_clocks():
    entry_ms=0
    healthy_bid=[(entry_ms,100000)]
    equal_ask=[(entry_ms,100000)]
    positive_ask=[(entry_ms,100010)]
    assert a.gate.decision_quality(entry_ms,healthy_bid,equal_ask)=="ZERO_SPREAD"
    assert a.gate.decision_quality(entry_ms,healthy_bid,positive_ask)=="OK_POSITIVE_BIDASK"
    assert a.gate.decision_quality(5001,healthy_bid,positive_ask)=="STALE_SIDE"
    assert a.gate.decision_quality(-1,healthy_bid,positive_ask)=="MISSING_SIDE"


def test_original_E1_signatures_must_be_extracted_before_event_promotion(tmp_path:Path):
    with pytest.raises(ValueError,match="SOURCE_SHA_REGISTER_MISSING"):
        a.analyze(tmp_path/"signed-e1",tmp_path/"not-mounted-real-provider")


def test_all_six_sources_and_original_E1_clocks_are_frozen_not_pnl_selection():
    assert a.EXPECTED_ORIGINAL_E1_ROWS==6
    assert a.SOURCE_RUN==38293565282
    assert a.SOURCE_ARTIFACT==11767003876
    assert a.SOURCE_HEAD=="7b7cd8339a4a1d135f531db90fd3931213708de4"
    assert len(a.source.EVENTS)==6
    assert a.source.G0_SOURCE_SHA == a.e1.G0_SOURCE_SHA
    assert a.source.E1_ORIGINAL_CODE_SHA==a.e1.E1_CODE_SHA
