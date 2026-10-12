"""No-network tests for G0↔G1 provider field identity, no contract promotion."""
from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from qore.infrastructure.trader_lab import qore_native_g1_g0_12_original_provider_id_concordance_v1 as g


def test_original_universe_and_historic_zip_sha_custody_frozen():
    assert len(g.ORIGINAL12)==12
    assert len(g.SOURCE_DIGESTS)==6
    assert all(len(s)==64 for s in g.SOURCE_DIGESTS.values())
    assert ("NAS100" in g.ORIGINAL12 and "SP500" in g.ORIGINAL12)
    assert g.G0_RUN==35166210458


def test_false_numeric_contract_witnesses_fail_closed():
    for value in (True,False,0,-1,"10014",1.2,None):
        with pytest.raises(ValueError,match="CONTRACT_SOURCE_"):
            g._int(value,"SYMBOL_ID")
    assert g._int(10014,"SYMBOL_ID")==10014


def test_source_register_hash_tamper_and_incomplete_file_set(tmp_path:Path):
    payload=tmp_path/"SOURCE-CROSSASSET-NOT-NET.json"
    payload.write_bytes(b'{"test":"source-only"}')
    registered=hashlib.sha256(payload.read_bytes()).hexdigest()
    (tmp_path/"OUTPUT_SHA256SUMS.txt").write_text(
        registered+"  "+payload.name+"\n"
    )
    assert g.verify_files(tmp_path,"OUTPUT_SHA256SUMS.txt")=={payload.name:registered}
    payload.write_bytes(b'{"test":"tampered"}')
    with pytest.raises(ValueError,match="ORIGINAL_SHA_CHANGED"):
        g.verify_files(tmp_path,"OUTPUT_SHA256SUMS.txt")
    payload.write_bytes(b'{"test":"source-only"}')
    (tmp_path/"EXTRA_UNDECLARED.txt").write_text("unregistered")
    with pytest.raises(ValueError,match="REGISTER_INCOMPLETE"):
        g.verify_files(tmp_path,"OUTPUT_SHA256SUMS.txt")


def test_provider_mismatch_rejected_before_contract_promotion(tmp_path:Path,monkeypatch):
    old={
        sym:{"g0_provider_symbol":sym,"g0_symbol_id":44,
             "g0_digits":5,"g0_pip_position":4,"g0_source_partitions":11}
        for sym in g.ORIGINAL12
    }
    # A failed historical identity should never become a NET fill.
    monkeypatch.setattr(g,"original_g0",lambda path:old)
    monkeypatch.setattr(g,"current_ustec_details",lambda path:{
        "digits":5,"pipPosition":4,"lotSize":100,"minVolume":10,"stepVolume":10,
    })
    monkeypatch.setattr(g,"g1_29",lambda path,sym:{
        "provider_symbol":sym, "provider_symbol_id":45,
    })
    monkeypatch.setattr(g,"g1_ustec",lambda path:{
        "provider_symbol":"USTEC","provider_symbol_id":10014,
    })
    monkeypatch.setattr(g,"g1_crossasset",lambda path,sym:{
        "provider_symbol":sym,"provider_symbol_id":44,
    })
    with pytest.raises(ValueError,match="SYMBOL_OR_NUMERIC_ID_CONCORDANCE_FAIL"):
        g.reconcile(tmp_path)


def test_matching_provider_symbol_id_can_never_prove_same_contract(tmp_path:Path,monkeypatch):
    old={}
    for sym in g.ORIGINAL12:
        name="USTEC" if sym=="NAS100" else "US500" if sym=="SP500" else sym
        old[sym]={
            "g0_provider_symbol":name,"g0_symbol_id":10014 if sym=="NAS100" else 10013 if sym=="SP500" else 11,
            "g0_digits":2 if sym=="NAS100" else 5,
            "g0_pip_position":1 if sym=="NAS100" else 4,
            "g0_source_partitions":11,
        }
    monkeypatch.setattr(g,"original_g0",lambda path:old)
    monkeypatch.setattr(g,"current_ustec_details",lambda path:{
        "digits":2,"pipPosition":1,"lotSize":100,"minVolume":10,"stepVolume":10,
    })
    monkeypatch.setattr(g,"g1_29",lambda path,sym:{
        "provider_symbol":sym,"provider_symbol_id":11,
    })
    monkeypatch.setattr(g,"g1_ustec",lambda path:{
        "provider_symbol":"USTEC","provider_symbol_id":10014,
    })
    monkeypatch.setattr(g,"g1_crossasset",lambda path,sym:{
        "provider_symbol":"US500" if sym=="SP500" else sym,
        "provider_symbol_id":10013 if sym=="SP500" else 11,
    })
    result=g.reconcile(tmp_path)
    assert result["g0_and_g1_provider_symbol_name_and_id_same_count"]==12
    assert result["total_g0_historical_year_partitions_sha_verified"]==132
    assert result["g0_g1_historic_execution_contracts_proven"] is False
    assert result["historical_execution_NET_authorized"] is False
    assert result["traders_certified"]==0
    assert all(row["contract_gate"]=="UNHOMOLOGATED_BROKER_EXECUTION_CONTRACT"
               for row in result["rows"])
    assert next(x for x in result["rows"] if x["canonical_symbol"]=="NAS100")[
        "g0_g1_digits_and_pip_position_concordant_only"
    ]
