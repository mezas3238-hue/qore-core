"""Synthetic fake 29-source fixtures: no market quotes, no network."""
import hashlib
import json
from datetime import UTC, datetime, timedelta

import pytest

from qore.research.alpha2_g2_29_forward_original_independent_qa import (
    CODE_HEAD,
    COMPLETE_SHA,
    MANIFEST,
    ORIGINAL_SHA,
    SOURCE_HEAD,
    SOURCE_ID,
    SOURCE_PASS,
    STATUS,
    _quality_reconstruct,
    inspect_original,
)
from qore.research.alpha2_g2_29_real_bidask_reuse import SOURCE_29

T=datetime(2026,10,12,20,tzinfo=UTC)


def record(symbol,seq,*,stamp=None,bid=100000,ask=100005,quality="POSITIVE_SPREAD_SOURCE_ONLY"):
    now=stamp or T+timedelta(milliseconds=seq*10)
    return {
        "source_symbol":symbol,
        "global_sequence":seq,
        "symbol_sequence":0,
        "first_observed_by_runner_utc":now.isoformat(),
        "provider_event_at_ms":int(T.timestamp()*1000),
        "native_bid_1e5":bid,"native_ask_1e5":ask,
        "trade_fill_verified":False,
        "source_quote_quality":quality,
    }


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fixture(folder):
    folder.mkdir()
    originals={}
    records=[]
    by_market={}
    witness={}
    for seq,sym in enumerate(sorted(SOURCE_29)):
        d=record(sym,seq)
        records.append(d)
        filename=f"firstrecv-{sym}-spot-events.jsonl"
        file=folder/filename
        file.write_text(json.dumps(d,sort_keys=True)+"\n",encoding="utf-8")
        witness[sym]={"original_file":filename,"source_bytes":file.stat().st_size,
                      "sha256":sha(file)}
        by_market[sym]={
            "event_count":1,"bid_updates":1,"ask_updates":1,
            "first_observed_utc":d["first_observed_by_runner_utc"],
            "last_observed_utc":d["first_observed_by_runner_utc"],
            "state_counts":{"POSITIVE_SPREAD_SOURCE_ONLY":1},
        }
        originals[filename]=sha(file)
    data={
        "identity":SOURCE_ID,"status":SOURCE_PASS,"target_market_count":29,
        "requested_duration_seconds":60,"provider":"ICMARKETS_CTRADER_DEMO",
        "excluded_four_unverified_or_separate":["NAS100","NZDUSD","SP500","XAGUSD"],
        "all_exact_symbols_verified":True,
        "provider_symbol_ids_broker_verified":True,
        "symbols_with_received_bid_and_ask":29,
        "account_id_or_oauth_persisted":False,"broker_orders_sent":0,
        "refresh_token_attempts":0,"G2_NET_CERTIFIED":False,
        "UTC001_certified":False,"historical_reserve_tick_values_unread":True,
        "by_market":by_market,"by_market_source_witness":witness,
        "received_event_count":len(records),
        "session_first_dequeued_utc":records[0]["first_observed_by_runner_utc"],
        "session_last_dequeued_utc":records[-1]["first_observed_by_runner_utc"],
    }
    root=folder/MANIFEST
    root.write_text(json.dumps(data,sort_keys=True),encoding="utf-8")
    originals[MANIFEST]=sha(root)
    head=folder/CODE_HEAD
    head.write_text(SOURCE_HEAD+"\n",encoding="utf-8")
    (folder/ORIGINAL_SHA).write_text(
        "".join(f"{digest}  {name}\n" for name,digest in sorted(originals.items())),
        encoding="utf-8",
    )
    (folder/COMPLETE_SHA).write_text(
        "".join(f"{digest}  {name}\n" for name,digest in sorted(originals.items()))
        +f"{sha(head)}  {CODE_HEAD}\n",encoding="utf-8",
    )
    return sorted(originals),records


def test_29_original_sha_and_per_market_bidask_reconcile(tmp_path):
    original=tmp_path/"original"
    fixture(original)
    result=inspect_original(original)
    assert result["status"]==STATUS
    assert result["market_count"]==29
    assert result["event_count"]==29
    assert result["quality_class_counts"]=={"POSITIVE_SPREAD_SOURCE_ONLY":29}
    assert result["raw_prices_republished"] is False
    assert result["broker_actual_NET_certified"] is False


def test_native_quote_value_mutation_must_break_original_checksum(tmp_path):
    original=tmp_path/"original"
    names,_=fixture(original)
    path=original/next(name for name in names if name.startswith("firstrecv-"))
    path.write_text(path.read_text().replace("100005","100006"))
    with pytest.raises(ValueError,match="SHA256_TAMPERED"):
        inspect_original(original)


def test_spot_second_side_absent_is_missing_until_available():
    rows=[
        record("EURCHF",0,bid=100000,ask=None,quality="MISSING_OR_STALE_SIDE"),
        record("EURCHF",1,bid=None,ask=100002),
    ]
    rows[1]["symbol_sequence"]=1
    value=_quality_reconstruct(rows)
    assert value["by_market"]["EURCHF"]["bid_updates"]==1
    assert value["by_market"]["EURCHF"]["ask_updates"]==1
    assert value["by_market"]["EURCHF"]["state_counts"]=={
        "MISSING_OR_STALE_SIDE":1,"POSITIVE_SPREAD_SOURCE_ONLY":1,
    }


def test_future_provider_event_or_backward_collector_clock_rejected():
    rows=[record("EURCHF",0)]
    rows[0]["provider_event_at_ms"]=int(
        (T+timedelta(milliseconds=100)).timestamp()*1000
    )
    with pytest.raises(ValueError,match="NOT_YET_RECEIVED"):
        _quality_reconstruct(rows)
    first=record("EURCHF",0)
    second=record("EURUSD",1,stamp=T-timedelta(seconds=1))
    with pytest.raises(ValueError,match="CLOCK_REVERSED"):
        _quality_reconstruct([first,second])


def test_global_sequence_duplicate_banned_even_when_market_file_is_valid():
    a=record("EURCHF",0)
    b=record("EURUSD",0)
    with pytest.raises(ValueError,match="SEQUENCE_INVALID"):
        _quality_reconstruct([a,b])


def test_zero_or_crossed_quote_cannot_be_reported_as_positive():
    a=record("EURCHF",0,ask=100000)
    with pytest.raises(ValueError,match="QUALITY_RECONSTRUCTION_DIFFERENT"):
        _quality_reconstruct([a])
    a["source_quote_quality"]="ZERO_SPREAD_NO_FILL"
    assert _quality_reconstruct([a])["by_market"]["EURCHF"][
        "state_counts"]["ZERO_SPREAD_NO_FILL"]==1


def test_metadata_manifest_scope_cannot_include_account_identifiers(tmp_path):
    folder=tmp_path/"original"
    fixture(folder)
    (folder/"oauth-token.bin").write_text("fake-secret")
    with pytest.raises(ValueError,match="EXACT_FILE_SCOPE_CHANGED"):
        inspect_original(folder)
