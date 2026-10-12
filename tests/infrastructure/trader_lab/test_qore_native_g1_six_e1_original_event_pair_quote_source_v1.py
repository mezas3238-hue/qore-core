"""Source-only six original E1 event-pair native protobuf collection guards."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from qore.infrastructure.trader_lab import qore_native_g1_six_e1_original_event_pair_quote_source_v1 as q


class FakeTick:
    def __init__(self, t: int, price: int):
        self.timestamp = t
        self.tick = price

    def SerializeToString(self, deterministic: bool = False) -> bytes:
        assert deterministic is True
        return b"\x08\x01\x10\x01"


class FakeClient:
    account_id = 25


def test_exact_e1_original_research_opportunities_and_bounded_two_windows():
    assert len(q.EVENTS) == 6
    assert len({(x[0],x[2],x[3]) for x in q.EVENTS}) == 6
    assert q.CLOCKS == {"entry":(12,55),"theoretical_close":(14,55)}
    assert q.G0_SOURCE_SHA == "1291d5c2efb4e51c2698ea25ad420a01a213dc405b5070c37efbce4131606b85"
    assert q.E1_ORIGINAL_CODE_SHA == "dfe78f115957a40f4188c30e78bd7f88c2ce6c42"
    for _,_,day,_ in q.EVENTS:
        a,b=q.source_period(day,"entry")
        c,d=q.source_period(day,"theoretical_close")
        assert b-a == d-c == 600000
        assert c-a == 120*60000
        assert a < b < c < d
    assert ("SP500","US500","2021-03-16","SWEEP_RECLAIM") in q.EVENTS


def test_no_new_unfrozen_date_or_clock():
    with pytest.raises(q.SourceBlock,match="FROZEN_CLOCK"):
        q.source_period("2024-09-18","entry")
    with pytest.raises(q.SourceBlock,match="FROZEN_CLOCK"):
        q.source_period("2021-03-16","open")


def test_original_field_bytes_saved_without_account_wrapper(tmp_path:Path, monkeypatch):
    start,end=q.source_period("2021-03-16","entry")
    def fake(client,sym,side,a,b,seq):
        assert client.account_id==25 and sym==11 and side==1
        assert a==start and b==end-1
        return {"has_more":False,"tick_data":(
            FakeTick(start+200,110011),FakeTick(-100,-2),
        )}
    monkeypatch.setattr(q,"_history_response",fake)
    result=q._write_side(FakeClient(),11,"GBPUSD","2021-03-16","entry","BID",tmp_path)
    assert result["provider_requests"]==1
    assert result["native_tick_count"]==2
    assert result["wire_field_protobuf_account_wrapper_archived"] is False
    assert len(result["pages"])==1 and result["pages"][0]["accepted_leaf"]
    assert result["wire_sha256"]==hashlib.sha256((tmp_path/result["wire_file"]).read_bytes()).hexdigest()
    values=[json.loads(t) for t in (tmp_path/result["int_file"]).read_text().splitlines()]
    assert values==[
        {"epoch_ms":start+100,"integer_price_1e5":110009},
        {"epoch_ms":start+200,"integer_price_1e5":110011},
    ]
    assert all("account" not in p.name.lower() for p in tmp_path.iterdir())


def test_nonfrozen_market_and_bad_quote_side_cannot_write(tmp_path:Path):
    with pytest.raises(q.SourceBlock,match="OUT_OF_FROZEN_SCOPE"):
        q._write_side(FakeClient(),11,"NAS100","2021-03-16","entry","BID",tmp_path)
    with pytest.raises(q.SourceBlock,match="OUT_OF_FROZEN_SCOPE"):
        q._write_side(FakeClient(),11,"SP500","2021-03-16","entry","MID",tmp_path)


def test_account_source_gate_failure_produces_sanitized_report_no_trade(tmp_path:Path,monkeypatch):
    monkeypatch.setattr(q,"probe_catalog",lambda:{"status":"NOT_THE_CURRENT_BROKER"})
    report=q.capture(tmp_path)
    assert report["state"]=="SOURCE_PRECONDITION_BLOCKED"
    assert report["fully_acquired_event_rows"]==0
    assert report["certified_traders"]==0
    assert not report["historical_Net_authorized"]
    assert report["trade_orders_sent"]==0
    assert report["oauth_refresh_attempts"]==0
    assert (tmp_path/"SOURCE_SIX_E1_EVENT_CLOCK_PAIR_MANIFEST_NOT_NET.json").is_file()


def test_strict_research_client_only_allows_native_historical_read():
    permitted=q.ReadOnlyTickPilot._HISTORY_ONLY_REQUEST_NAMES
    assert "ProtoOAGetTickDataReq" in permitted
    assert not any(x in permitted for x in (
        "ProtoOANewOrderReq","ProtoOACancelOrderReq","ProtoOAModifyOrderReq",
        "ProtoOARefreshTokenReq","ProtoOASubscribeSpotsReq",
    ))
