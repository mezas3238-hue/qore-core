"""Research-only synthetic unit tests for actual cTrader BID/ASK pilot logic."""
from __future__ import annotations

from dataclasses import dataclass

import pytest

from qore.infrastructure.trader_lab import qore_native_icmarkets_bidask_source_pilot_v1 as source


@dataclass
class FakeTick:
    timestamp: int
    tick: int


def test_three_predeclared_windows_are_utc_and_fixed():
    assert source.SYMBOL == "NZDUSD"
    assert len(source.FROZEN_WINDOWS) == 3
    assert source.SOURCE_M1_PILOT_RUN == 38262534602
    assert all(
        source.window_milliseconds(w)[1] - source.window_milliseconds(w)[0] == 600000
        for w in source.FROZEN_WINDOWS
    )


def test_native_differential_epoch_ms_decode_newest_first():
    ticks = source.decode_native(
        (FakeTick(1100, 110000), FakeTick(50, 110002), FakeTick(50, 110001)),
        1000, 1100,
    )
    assert ticks == [(1100, 110000), (1050, 110002), (1000, 110001)]


def test_outside_and_negative_tick_deltas_block():
    with pytest.raises(source.SourceBlock, match="TICK_TIME_OUTSIDE"):
        source.decode_native((FakeTick(200, 1000),), 0, 199)
    with pytest.raises(source.SourceBlock, match="NEGATIVE_TICK_DELTA"):
        source.decode_native((FakeTick(200, 1000), FakeTick(-1, 1001)), 0, 200)
    with pytest.raises(source.SourceBlock, match="BAD_PROVIDER_TICK"):
        source.decode_native((FakeTick(200, 0),), 0, 200)


def test_hasmore_exact_disjoint_split_keeps_source_ticks():
    called = []
    def fake(a, b):
        called.append((a, b))
        if b - a > 1:
            return {"has_more": True, "tick_data": (FakeTick(b, 10001),)}
        return {"has_more": False, "tick_data": (FakeTick(b, 10002),)}
    ticks, requests = source.complete_side(fake, 0, 7)
    assert requests == 7
    assert len(ticks) == 4
    assert [t[0] for t in ticks] == [1, 3, 5, 7]
    assert len(called) == len(set(called))


def test_missing_hasmore_or_unpageable_ms_block():
    with pytest.raises(source.SourceBlock, match="MISSING_HASMORE"):
        source.complete_side(lambda _a, _b: {"tick_data": ()}, 0, 3)
    with pytest.raises(source.SourceBlock, match="UNPAGEABLE_SAME_MS"):
        source.complete_side(lambda _a, _b: {"has_more": True, "tick_data": ()}, 0, 0)


def test_no_improper_live_execution_or_token_refresh_allowed():
    permitted = source.ReadOnlyTickPilot._HISTORY_ONLY_REQUEST_NAMES
    assert "ProtoOAGetTickDataReq" in permitted
    for name in (
        "ProtoOANewOrderReq", "ProtoOACancelOrderReq",
        "ProtoOAModifyOrderReq", "ProtoOARefreshTokenReq", "ProtoOASubscribeSpotsReq",
    ):
        assert name not in permitted


def test_bad_windows_fail_closed():
    for bad in (
        ("2020-09-15T13:00:00", "2020-09-15T13:10:00"),
        ("2020-09-15T13:10:00+00:00", "2020-09-15T13:00:00+00:00"),
    ):
        with pytest.raises(source.SourceBlock):
            source.window_milliseconds(bad)

def test_official_sdk_quote_req_res_are_admitted_only_to_pilot_instance():
    from qore.infrastructure.ctrader_open_api_client import CTraderOpenApiCredentials
    creds = CTraderOpenApiCredentials(
        client_id="synthetic-client", client_secret="synthetic-secret",
        access_token="synthetic-access", refresh_token="synthetic-refresh",
        ctid_trader_account_id=1,
    )
    pilot = source.ReadOnlyTickPilot(credentials=creds, request_timeout_seconds=10.0)
    try:
        assert "ProtoOAGetTickDataReq" in pilot._bindings.messages
        assert "ProtoOAGetTickDataRes" in pilot._bindings.messages
        assert "ProtoOANewOrderReq" not in pilot._HISTORY_ONLY_REQUEST_NAMES
    finally:
        pilot.close()
