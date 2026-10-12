"""Validate visually transcribed full 33 BID/ASK; never extrapolate to historical fills."""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from qore.infrastructure.trader_lab import qore_native_g1_screenshot_bidask_spot_audit_v1 as a

SOURCE=Path(__file__).resolve().parents[3]/"docs/research/data/QORE_NATIVE_USER_BIDASK_SCREENSHOTS_33_SPOT_TRANSCRIPTION_2026-10-12.json"


def original() -> dict:
    return json.loads(SOURCE.read_text(encoding="utf-8"))


def test_all_33_quoted_symbols_and_spread_units() -> None:
    out=a.spread_stats(original())
    assert out["visible_quote_coverage_33"]==33
    assert len(out["rows"])==33
    assert {x["canonical_symbol"] for x in out["rows"]} == a.universe.FROZEN_UNIVERSE_33
    assert out["eligible_for_spot_spread_descriptive_comparison"] == 30
    assert out["traders_certified"]==0
    assert out["historical_bidask_2016_2024_reconstructed"] is False


def test_known_screenshot_quotes_not_invented() -> None:
    by={x["canonical_symbol"]:x for x in a.spread_stats(original())["rows"]}
    assert by["EURUSD"]["spread_pips_if_fx"]=="0.1"
    assert by["CHFJPY"]["spread_pips_if_fx"]=="1.5"
    assert by["GBPJPY"]["spread_pips_if_fx"]=="1.8"
    assert by["XAUUSD"]["spread_absolute"]=="0.38"
    assert by["XAGUSD"]["spread_absolute"]=="0.055"
    assert by["NAS100"]["spread_absolute"]=="1.60"
    assert by["SP500"]["spread_absolute"]=="0.58"
    assert by["US30"]["spread_absolute"]=="1.98"
    assert by["GBPUSD"]["spread_absolute"]=="0.00000"
    assert by["GBPUSD"]["quality_gate"]=="BLOCKED_ZERO_SPREAD_SNAPSHOT"
    assert by["NAS100"]["quality_gate"]=="BLOCKED_INDEX_ALIAS_UNVERIFIED"
    assert by["SP500"]["quality_gate"]=="BLOCKED_INDEX_ALIAS_UNVERIFIED"
    assert by["XAGUSD"]["spread_bps_approx"]>9
    assert by["EURUSD"]["spread_bps_approx"]<0.1


def test_extra_btc_not_silently_added() -> None:
    x=original()
    assert x["outside_frozen_universe_excluded"][0]["displayed_symbol"]=="BTCUSD"
    x["rows"].append({
        "canonical_symbol":"BTCUSD", "displayed_symbol":"BTCUSD",
        "bid_transcribed":"82630.20","ask_transcribed":"82659.95",
    })
    with pytest.raises(ValueError,match="33"):
        a.spread_stats(x)


def test_fail_closed_bad_quote_and_missing_symbols() -> None:
    x=original()
    x["rows"][0]["ask_transcribed"]="1.00"
    with pytest.raises(ValueError,match="inversion"):
        a.spread_stats(x)
    x=original()
    x["rows"][0]["canonical_symbol"]=x["rows"][1]["canonical_symbol"]
    x["rows"][0]["displayed_symbol"]=x["rows"][1]["displayed_symbol"]
    with pytest.raises(ValueError,match="repeated"):
        a.spread_stats(x)
    x=original()
    x["rows"][0]["bid_transcribed"]="190,443"
    with pytest.raises(ValueError,match="decimal"):
        a.spread_stats(x)


def test_zero_spread_alias_and_screenshot_SHA_cannot_be_promoted() -> None:
    base=original()
    alterations=[]
    x=copy.deepcopy(base)
    next(c for c in x["rows"] if c["canonical_symbol"]=="GBPUSD")["ask_transcribed"]="1.32326"
    alterations.append(x)
    x=copy.deepcopy(base)
    next(c for c in x["rows"] if c["canonical_symbol"]=="NAS100")["legacy_source_alias_equivalence_verified"]=True
    alterations.append(x)
    x=copy.deepcopy(base)
    x["screen_source_images"][0]["sha256"]="f"*64
    alterations.append(x)
    x=copy.deepcopy(base)
    x["quote_calendar_date_verified"]=True
    alterations.append(x)
    x=copy.deepcopy(base)
    x["scope_caveats"]["execution_bidask_in_2016_to_2024_not_proven"]=False
    alterations.append(x)
    for fake in alterations:
        with pytest.raises(ValueError):
            a.spread_stats(fake)


def test_quote_time_has_unknown_timezone_even_when_filled() -> None:
    r=a.spread_stats(original())
    assert not r["quote_calendar_date_verified"]
    assert r["not_historically_time_aligned"]
    assert any(x["quote_local_clock_without_date_or_timezone"] is None for x in r["rows"])
    assert all(x["source_broker_historical_same_contract_verified"] is False for x in r["rows"])
    assert all(x["commission_slippage_or_roll_over_included"] is False for x in r["rows"])


def test_pure_spread_auditor_has_no_trade_or_net_execution_code() -> None:
    src=Path(a.__file__).read_text(encoding="utf-8")
    for banned in ("ProtoOANewOrderReq","send_order(", "place_order(", '["open_relative"]',
                   '["close_relative"]',"net_edge_certified = True"):
        assert banned not in src
