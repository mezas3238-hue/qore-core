"""Synthetic cTrader BID ASK source integrity tests: no original quote values."""
import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from qore.research.alpha2_g2_29_real_bidask_reuse import (
    WINDOWS,
    audit_two_sides,
    digest,
)


def fixture(folder: Path, *, side="BID", count=3):
    symbol="EURCHF"
    prefix=f"{symbol}-1-{side}"
    source=folder/f"{prefix}-integer.jsonl"
    decoded=folder/f"{prefix}-decoded.jsonl"
    first=int(datetime.fromisoformat(WINDOWS[0][0]).timestamp()*1000)+1000
    original=[]
    human=[]
    for i in range(count):
        timestamp=first+i*100
        amount=110000+i*5
        original.append({"epoch_ms":timestamp,"integer_price_1e5":amount})
        human.append({
            "event_time_utc":datetime.fromtimestamp(timestamp/1000,tz=UTC)
            .isoformat(timespec="milliseconds").replace("+00:00","Z"),
            "native_sequence":i,
            "price":format(Decimal(amount)/Decimal(100000),"f"),
        })
    source.write_text("".join(json.dumps(x)+"\n" for x in original))
    decoded.write_text("".join(json.dumps(x)+"\n" for x in human))
    meta={
        "native_int_file":source.name,"native_int_sha256":digest(source),
        "decoded_file":decoded.name,"decoded_sha256":digest(decoded),
        "native_tick_count":count,
    }
    return meta,{source.name:digest(source),decoded.name:digest(decoded)},source,decoded


def test_native_integer_matches_human_decimal_and_exact_timestamp(tmp_path):
    meta,sha,_,_=fixture(tmp_path)
    result=audit_two_sides(tmp_path,"EURCHF",1,WINDOWS[0],"BID",meta,sha)
    assert result["tick_count"]==3
    assert result["trade_fills_proven"] is False


def test_price_byte_mutation_detected_even_with_matching_file_count(tmp_path):
    meta,sha,raw,_=fixture(tmp_path)
    raw.write_text(raw.read_text().replace("110000","110001"))
    with pytest.raises(ValueError,match="SHA_MISMATCH"):
        audit_two_sides(tmp_path,"EURCHF",1,WINDOWS[0],"BID",meta,sha)


def test_2026_quote_side_is_strictly_out_of_scope(tmp_path):
    meta,sha,_,_=fixture(tmp_path)
    with pytest.raises(ValueError,match="HOLDOUT_OR_SIDE"):
        audit_two_sides(tmp_path,"EURCHF",3,WINDOWS[2],"BID",meta,sha)


def test_wrong_decoded_price_cannot_be_claimed_as_provider_quote(tmp_path):
    meta,sha,_,human=fixture(tmp_path)
    rows=human.read_text().splitlines()
    d=json.loads(rows[0])
    d["price"]="0.00000"
    human.write_text(json.dumps(d)+"\n"+"\n".join(rows[1:])+"\n")
    sha[human.name]=digest(human)
    meta["decoded_sha256"]=sha[human.name]
    with pytest.raises(ValueError,match="NATIVE_INTEGER_VS_DECIMAL"):
        audit_two_sides(tmp_path,"EURCHF",1,WINDOWS[0],"BID",meta,sha)


def test_outside_source_time_even_if_file_is_rehashed(tmp_path):
    meta,sha,raw,_=fixture(tmp_path)
    rows=raw.read_text().splitlines()
    d=json.loads(rows[0])
    d["epoch_ms"]=int(
        datetime.fromisoformat(WINDOWS[1][0]).timestamp()*1000)
    raw.write_text(json.dumps(d)+"\n"+"\n".join(rows[1:])+"\n")
    sha[raw.name]=digest(raw)
    meta["native_int_sha256"]=sha[raw.name]
    with pytest.raises(ValueError,match="SOURCE_INVALID"):
        audit_two_sides(tmp_path,"EURCHF",1,WINDOWS[0],"BID",meta,sha)
