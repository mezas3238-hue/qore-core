"""Synthetic forward receipt independent QA; never re-download broker quotes."""
import hashlib
import json
from datetime import UTC, datetime, timedelta

import pytest

from qore.research.alpha2_g2_nzdusd_independent_forward_receipt_qa import (
    CODE_HEAD,
    HEAD,
    MANIFEST,
    RAW,
    SHA_COMPLETE,
    SHA_SOURCE,
    SOURCE_IDENTITY,
    SUCCESS,
    STATUS,
    audit,
    qa_events,
)

T=datetime(2026,10,12,19,0,tzinfo=UTC)


def bidask_entries():
    return [
        {
            "sequence":0, "source_symbol":"NZDUSD",
            "first_observed_by_runner_utc":T.isoformat(),
            "provider_event_at_ms":None,
            "native_bid_1e5":60812,
            "native_ask_1e5":None,
            "event_is_NOT_fill":True,
            "current_side_freshness_class":"MISSING_OR_STALE_BIDASK",
        },
        {
            "sequence":1, "source_symbol":"NZDUSD",
            "first_observed_by_runner_utc":(T+timedelta(milliseconds=500)).isoformat(),
            "provider_event_at_ms":int(T.timestamp()*1000),
            "native_bid_1e5":None,
            "native_ask_1e5":60823,
            "event_is_NOT_fill":True,
            "current_side_freshness_class":"POSITIVE_SPREAD_OBSERVATION_NO_FILL",
        },
    ]


def test_independent_bidask_reconstruction_and_optional_provider_timestamp():
    d=qa_events(bidask_entries())
    assert d["counts"]["all_received"]==2
    assert d["counts"]["bid_updates"]==1
    assert d["counts"]["ask_updates"]==1
    assert d["counts"]["MISSING_OR_STALE_BIDASK"]==1
    assert d["counts"]["POSITIVE_SPREAD_OBSERVATION_NO_FILL"]==1
    assert d["provider_clock_latency_calibrated"] is False


def test_stale_one_side_does_not_become_reused_fresh_bidask():
    records=bidask_entries()
    records[1]["first_observed_by_runner_utc"]=(T+timedelta(seconds=6)).isoformat()
    records[1]["current_side_freshness_class"]="MISSING_OR_STALE_BIDASK"
    d=qa_events(records)
    assert d["counts"]["MISSING_OR_STALE_BIDASK"]==2


def test_future_provider_or_decreasing_dequeue_clock_rejected():
    r=bidask_entries()
    r[1]["provider_event_at_ms"]=int((T+timedelta(seconds=3)).timestamp()*1000)
    with pytest.raises(ValueError,match="LATER_THAN_RECEIPT"):
        qa_events(r)
    r=bidask_entries()
    r[1]["first_observed_by_runner_utc"]=(T-timedelta(seconds=1)).isoformat()
    with pytest.raises(ValueError,match="CLOCK_REVERSED"):
        qa_events(r)


def test_tampered_side_value_or_label_is_not_trusted():
    r=bidask_entries()
    r[1]["current_side_freshness_class"]="ZERO_QUOTE_QUARANTINED"
    with pytest.raises(ValueError,match="CLASSIFICATION_DIFFERENT"):
        qa_events(r)
    r=bidask_entries()
    r[1]["native_ask_1e5"]=-1
    with pytest.raises(ValueError,match="PRICE_TYPE_INVALID"):
        qa_events(r)
    r=bidask_entries()
    r[0]["provider_account_id"]="SECRET_NEVER_ALLOWED"
    with pytest.raises(ValueError,match="SCHEMA_UNEXPECTED"):
        qa_events(r)


def test_zero_and_crossed_are_unequivocal_and_not_free_quotes():
    z=bidask_entries()
    z[1]["native_ask_1e5"]=60812
    z[1]["current_side_freshness_class"]="ZERO_QUOTE_QUARANTINED"
    assert qa_events(z)["counts"]["ZERO_QUOTE_QUARANTINED"]==1
    z[1]["native_ask_1e5"]=60811
    z[1]["current_side_freshness_class"]="CROSSED_QUOTE_QUARANTINED"
    assert qa_events(z)["counts"]["CROSSED_QUOTE_QUARANTINED"]==1


def _hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def signed_synthetic_source(folder):
    folder.mkdir(exist_ok=True)
    rows=bidask_entries()
    raw=folder/RAW
    raw.write_text("".join(json.dumps(x)+"\n" for x in rows),encoding="utf-8")
    manifest={
        "identity":SOURCE_IDENTITY,"status":SUCCESS,"source_observation_state":SUCCESS,
        "symbol":"NZDUSD","broker":"ICMARKETS_CTRADER","account_type":"DEMO",
        "duration_seconds_fixed":45,"broker_account_or_token_persisted":False,
        "orders_sent":0,"token_refresh_attempts":0,
        "both_sides_seen_nonzero":True,"historical_available_at_proven":False,
        "actual_execution_fill_proven":False,"NET_certified":False,
        "native_provider_symbol_id":734,
        "received_events":2,
        "first_collector_utc":rows[0]["first_observed_by_runner_utc"],
        "last_collector_utc":rows[1]["first_observed_by_runner_utc"],
        "observed_classifications":{
            "MISSING_OR_STALE_BIDASK":1,
            "POSITIVE_SPREAD_OBSERVATION_NO_FILL":1,
        },
        "original_spot_events_sha256":_hash(raw),
    }
    meta=folder/MANIFEST
    meta.write_text(json.dumps(manifest),encoding="utf-8")
    head=folder/CODE_HEAD
    head.write_text(HEAD+"\n",encoding="utf-8")
    (folder/SHA_SOURCE).write_text(
        f"{_hash(meta)}  {MANIFEST}\n{_hash(raw)}  {RAW}\n",encoding="utf-8")
    (folder/SHA_COMPLETE).write_text(
        f"{_hash(meta)}  {MANIFEST}\n{_hash(raw)}  {RAW}\n"
        f"{_hash(head)}  {CODE_HEAD}\n",encoding="utf-8",
    )
    return raw


def test_all_witness_layers_and_original_code_head_required(tmp_path):
    original=tmp_path/"original"
    raw=signed_synthetic_source(original)
    report=audit(original)
    assert report["status"]==STATUS
    assert report["orders"]==0
    raw.write_text(raw.read_text()+"{}\n")
    with pytest.raises(ValueError,match="TAMPERED"):
        audit(original)


def test_no_unverified_extra_file_allowed(tmp_path):
    original=tmp_path/"original"
    signed_synthetic_source(original)
    (original/"secret.csv").write_text("never")
    with pytest.raises(ValueError,match="SCOPE_CHANGED"):
        audit(original)
