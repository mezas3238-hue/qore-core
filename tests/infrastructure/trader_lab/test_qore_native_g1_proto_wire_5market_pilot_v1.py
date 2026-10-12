"""Synthetic source contract tests; no network, PnL, orders or market quotes."""
from __future__ import annotations

import hashlib
import json
import struct
from dataclasses import dataclass
from pathlib import Path

import pytest

from qore.infrastructure.trader_lab import qore_native_g1_proto_wire_5market_pilot_v1 as p


@dataclass
class NativeTick:
    timestamp: int
    tick: int

    def SerializeToString(self, deterministic: bool = True) -> bytes:
        assert deterministic
        return b"\x08" + (self.timestamp & 0x7F).to_bytes(1, "big") + b"\x10\x01"


class FakeClient:
    account_id = 123


def _catalog():
    return {
        "status": "ICMARKETS_DEMO_CATALOG_VERIFIED",
        "account_is_live": False,
        "_ephemeral_account_id": 123,
        "catalog": {"catalog_exact_matches": {
            name: {"broker_symbol": name, "symbol_id": i + 100, "enabled": True}
            for i, name in enumerate(p.TARGETS.values())
        }},
    }


def test_frozen_5x2_quote_source_without_pnl():
    assert p.TARGETS == {"EURUSD": "EURUSD", "GBPUSD": "GBPUSD",
                         "USDJPY": "USDJPY", "XAGUSD": "XAGUSD",
                         "SP500": "US500"}
    assert len(p.WINDOWS) == 2
    assert all(p.window_milliseconds(w)[1] - p.window_milliseconds(w)[0] == 1800000
               for w in p.WINDOWS)
    assert p.PARENT_SOURCE_RUN == 38283737706


def test_exact_catalog_demonstrates_broker_and_alias():
    account, ids = p._source_auth(_catalog())
    assert account == 123 and len(ids) == 5
    assert ids["SP500"] > 0
    data = _catalog()
    data["catalog"]["catalog_exact_matches"]["US500"]["broker_symbol"] = "SPX500"
    _, ids = p._source_auth(data)
    assert "SP500" not in ids
    data = _catalog()
    data["account_is_live"] = True
    with pytest.raises(p.SourceBlock, match="ACCOUNT_NOT_VERIFIED"):
        p._source_auth(data)


def test_original_tick_field_framed_bytes_sha_and_prices(tmp_path: Path, monkeypatch):
    first, last = p.window_milliseconds(p.WINDOWS[0])
    provider = {
        "has_more": False,
        "tick_data": (NativeTick(first + 200, 110011), NativeTick(-100, -2)),
    }

    def fake_fetch(client, symbol_id, side_type, a, b, sequence):
        assert client.account_id == 123
        assert symbol_id == 105 and side_type == 1
        assert a == first and b == last - 1
        return provider

    monkeypatch.setattr(p, "_history_response", fake_fetch)
    result = p._store_side(FakeClient(), 105, "EURUSD", 1, "BID", tmp_path)
    assert result["count"] == 2
    assert result["total_provider_requests"] == 1
    assert result["wire_tick_fields_only_account_wrapper_excluded"] is True
    raw = (tmp_path / result["wire_file"]).read_bytes()
    assert raw == b"".join(
        struct.pack(">I", len(t.SerializeToString())) + t.SerializeToString()
        for t in provider["tick_data"]
    )
    assert hashlib.sha256(raw).hexdigest() == result["wire_sha256"]
    assert result["wire_pages"][0]["accepted_leaf"] is True
    rows = [json.loads(s) for s in (tmp_path / result["native_file"]).read_text().splitlines()]
    assert [r["epoch_ms"] for r in rows] == [first + 100, first + 200]
    assert [r["integer_price_1e5"] for r in rows] == [110009, 110011]


def test_hasmore_original_wire_is_kept_but_not_counted_as_accepted(tmp_path: Path, monkeypatch):
    start, _ = p.window_milliseconds(p.WINDOWS[0])
    def fetch(client, sym, side, a, b, seq):
        if b - a > 2:
            return {"has_more": True, "tick_data": (NativeTick(b, 200000),)}
        return {"has_more": False, "tick_data": (NativeTick(b, 200001),)}
    # Limit side duration to six milliseconds in this synthetic test only
    monkeypatch.setattr(p, "window_milliseconds", lambda _: (start, start + 6))
    monkeypatch.setattr(p, "_history_response", fetch)
    result = p._store_side(FakeClient(), 123, "EURUSD", 1, "ASK", tmp_path)
    assert result["total_provider_requests"] == 7
    assert result["count"] == 4
    assert sum(not page["accepted_leaf"] for page in result["wire_pages"]) == 3
    assert sum(page["accepted_leaf"] for page in result["wire_pages"]) == 4


def test_safe_blocker_sanitizes_arbitrary_provider_text():
    assert p._safe_failure(p.SourceBlock("CTRADER_SOURCE_REQUEST_FAILURE")) == "CTRADER_SOURCE_REQUEST_FAILURE"
    assert p._safe_failure(RuntimeError("secret account 555551")) == "SOURCE_PROVIDER_OR_PROTOCOL_BLOCKED"
    assert p._safe_failure(p.SourceBlock("user supplied \n token")) == "SOURCE_PROVIDER_OR_PROTOCOL_BLOCKED"


def test_restricted_message_contract_no_orders_or_oauth_refresh():
    allowed = p.ReadOnlyTickPilot._HISTORY_ONLY_REQUEST_NAMES
    assert "ProtoOAGetTickDataReq" in allowed
    assert not any(s in allowed for s in (
        "ProtoOANewOrderReq", "ProtoOACancelOrderReq",
        "ProtoOAModifyOrderReq", "ProtoOARefreshTokenReq", "ProtoOASubscribeSpotsReq",
    ))
