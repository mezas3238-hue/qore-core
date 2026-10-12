"""No-network negative source tests for original E1 UTC decision clocks vs quote gaps."""
from __future__ import annotations

import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest
from qore.infrastructure.trader_lab import qore_native_g1_e1_original_opportunity_quote_coverage_v1 as q


def sample_seven(symbol: str, date_: str, *, corrupt_method: bool = False) -> dict:
    day = date.fromisoformat(date_)
    all_methods = []
    for n, method in enumerate(q.METHODS):
        if corrupt_method and n == 0:
            method = "HINDSIGHT_PROFIT_MODEL"
        start = q._expected_research_clock(symbol, method, day) if method in q.METHODS else datetime(day.year,day.month,day.day,13,tzinfo=UTC)
        iso = day.isocalendar()
        all_methods.append({
            "method_id": method, "cell_id": f"{method}__{symbol}",
            "net_economics_authorized": False,
            "bidask_measured":False,"news_asof_filtered":False,
            "paired_events":[{
                "utc_date":date_, "iso_week":f"{iso.year}-W{iso.week:02d}",
                "method_id":method,"reference_entry_utc":start.isoformat(),
                "strategy_signal":1,"baseline_signal":-1,
                "strategy_gross_bps":999999999999,
                "baseline_gross_bps":-999999999999,
                "paired_delta_bps":1999999999998,
                "broker_executable_fill":False,"macro_news_asof_filtered":False,
            }],
        })
    return {
        "identity":q.E1_IDENTITY,"status":q.E1_STATUS,
        "source33_sha":q.G0_SOURCE_SHA,"frozen_prereg_commit":q.E1_PREREG,
        "original_symbol":symbol,"future_ohlc_not_read":True,
        "net_certified":False,"traders_certified":0,"production_untouched":True,
        "source_audit":{"original_raw_11_year_sha_checked":True},
        "seven_methods":all_methods,
    }


def store_fake(folder:Path, symbol:str, payload:dict):
    folder.mkdir(parents=True,exist_ok=True)
    name=f"qore-native-e1-seven-{symbol}.json"
    data=folder/name
    data.write_text(json.dumps(payload),encoding="utf-8")
    (folder/(name+".sha256")).write_text(q.sha(data.read_bytes())+"  "+name+"\n")
    (folder/"exact-code-head-sha.txt").write_text(q.E1_CODE_SHA+"\n")
    return data


def test_frozen_horizons_and_historical_preembargo_contract():
    assert q.E1_SOURCE_RUN == 38257207836
    assert q.E1_CODE_SHA == "dfe78f115957a40f4188c30e78bd7f88c2ce6c42"
    assert len(q.TARGETS)==5 and len(q.METHODS)==7
    assert q.METHODS["OPEN_INITIAL_REACTION"] == 15
    assert q.METHODS["SWEEP_RECLAIM"] == q.METHODS["RANGE_BREAK_CONT"] == 120
    assert q.METHODS["TREND_MULTI_DAY"] == 240
    assert q.SAMPLE_DATES=={"2021-03-16","2023-03-21"}


def test_method_clock_matches_dst_proxy_not_random_pnl():
    day=date(2021,3,16)
    assert q._expected_research_clock("EURUSD","OPEN_INITIAL_REACTION",day).isoformat()=="2021-03-16T08:15:00+00:00"
    assert q._expected_research_clock("XAGUSD","OPEN_INITIAL_REACTION",day).isoformat()=="2021-03-16T12:15:00+00:00"
    assert q._expected_research_clock("SP500","OPEN_INITIAL_REACTION",day).isoformat()=="2021-03-16T13:45:00+00:00"
    assert q._expected_research_clock("SP500","POST_OPEN_CONT",day).isoformat()=="2021-03-16T14:00:00+00:00"
    assert q._expected_research_clock("GBPUSD","SWEEP_RECLAIM",day).isoformat()=="2021-03-16T13:00:00+00:00"
    assert q._expected_research_clock("GBPUSD","TREND_MULTI_DAY",day).isoformat()=="2021-03-16T16:00:00+00:00"


def test_seven_signed_research_decisions_without_gross_or_sign_exposure(tmp_path:Path):
    payload=sample_seven("EURUSD","2021-03-16")
    folder=tmp_path/"EURUSD"
    store_fake(folder,"EURUSD",payload)
    rows,sha=q._verify_signed_e1(folder,"EURUSD")
    assert len(rows)==7 and len(sha)==64
    assert {x["method_id"] for x in rows}==set(q.METHODS)
    assert all(x["future_outcome_fields_exported"] is False for x in rows)
    assert all(x["broker_order_open_close_proven"] is False for x in rows)
    assert all("gross" not in k and "signal" not in k
               for x in rows for k in x)
    assert all(
        datetime.fromisoformat(x["theoretical_m5_target_close_clock_utc"])
        == datetime.fromisoformat(x["research_entry_clock_utc"])+timedelta(minutes=x["theoretical_target_minutes"])
        for x in rows
    )


def test_corrupt_sha_head_and_method_or_time_fail_closed(tmp_path:Path):
    folder=tmp_path/"EURUSD"
    d=store_fake(folder,"EURUSD",sample_seven("EURUSD","2021-03-16"))
    d.write_text(d.read_text()+"\n")
    with pytest.raises(ValueError,match="JSON_SHA_MISMATCH"):
        q._verify_signed_e1(folder,"EURUSD")
    store_fake(folder,"EURUSD",sample_seven("EURUSD","2021-03-16",corrupt_method=True))
    with pytest.raises(ValueError,match="SEVEN_METHOD"):
        q._verify_signed_e1(folder,"EURUSD")
    doc=sample_seven("EURUSD","2021-03-16")
    doc["seven_methods"][0]["paired_events"][0]["reference_entry_utc"]="2021-03-16T12:00:00+00:00"
    store_fake(folder,"EURUSD",doc)
    with pytest.raises(ValueError,match="LOOKAHEAD_OR_DST_DRIFT"):
        q._verify_signed_e1(folder,"EURUSD")


def test_only_source_quote_date_can_be_mapped_no_holdout_artifacts(tmp_path:Path):
    with pytest.raises(ValueError,match="SOURCE_SHA_REGISTER_MISSING"):
        q.evaluate(tmp_path/"e1",tmp_path/"quotes")


def test_original_E1_source_not_a_broker_execution():
    assert q.NO_PNL_EXPORTED
    assert q.SOURCE_ARTIFACT == 11764163362
    assert q.HISTORICAL_EMBARGO==datetime(2024,9,17,tzinfo=UTC)
    assert all(len(c[1])==64 for c in q.ARTIFACTS.values())
