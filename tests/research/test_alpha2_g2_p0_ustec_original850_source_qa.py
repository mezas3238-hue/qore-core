"""Fake original 850 USTEC catalog source only, no historical fills."""
import json

import pytest

from qore.research.alpha2_g2_p0_ustec_original850_source_qa import (
    EXPECTED_SPECS,
    SOURCE_FILENAME,
    SOURCE_ID,
    STATUS,
    audit,
)


def fixture(root):
    root.mkdir()
    d={
        "identity":SOURCE_ID,
        "status":"USTEC_ALIAS_CANDIDATE_NEEDS_CONTRACT_EQUIVALENCE",
        "source":"ICMARKETS_CTRADER_DEMO","read_only":True,
        "canonical":"NAS100","historical_alias_hint":"USTEC",
        "alias_equivalence_verified":False,
        "historical_execution_contract_verified":False,
        "NET_authorized":False,"native_bidask_fetched":False,
        "trade_orders_submitted":0,"token_refresh_attempts":0,
        "certified_traders":0,
        "catalog_exact_candidates":{"USTEC":10014},
        "current_demo_symbol_metadata":{"USTEC":dict(EXPECTED_SPECS)},
    }
    path=root/SOURCE_FILENAME
    path.write_text(json.dumps(d),encoding="utf-8")
    return path,d


def test_offline_ustec_source_candidate_does_not_certify_historical_nas100(tmp_path):
    path,d=fixture(tmp_path/"original")
    assert path.is_file()
    result=audit(path.parent)
    assert result["status"]==STATUS
    assert result["source_symbol_id"]==10014
    assert result["lotSize_raw_cents"]==100
    assert result["historical_original_CIBO_NAS100_USTEC_contract_equivalent"] is False
    assert result["UTC001_certified"] is False
    assert result["orders"]==0


def test_no_wrong_symbol_alias_or_fake_equivalence_allowed(tmp_path):
    path,d=fixture(tmp_path/"original")
    d["catalog_exact_candidates"]={"NAS100":10014}
    path.write_text(json.dumps(d))
    with pytest.raises(ValueError,match="SCOPE_OR_ALIAS"):
        audit(path.parent)
    d["catalog_exact_candidates"]={"USTEC":10014}
    d["alias_equivalence_verified"]=True
    path.write_text(json.dumps(d))
    with pytest.raises(ValueError,match="SCOPE_OR_ALIAS"):
        audit(path.parent)


def test_commission_or_contract_field_disappearing_cannot_default(tmp_path):
    path,d=fixture(tmp_path/"original")
    del d["current_demo_symbol_metadata"]["USTEC"]["pipPosition"]
    path.write_text(json.dumps(d))
    with pytest.raises(ValueError,match="RAW_BROKER_SPECS"):
        audit(path.parent)


def test_boolean_spoof_or_mutated_lot_size_must_fail(tmp_path):
    path,d=fixture(tmp_path/"original")
    d["current_demo_symbol_metadata"]["USTEC"]["symbol_id"]=True
    path.write_text(json.dumps(d))
    with pytest.raises(ValueError,match="RAW_BROKER_SPECS"):
        audit(path.parent)
    d["current_demo_symbol_metadata"]["USTEC"]["symbol_id"]=10014
    d["current_demo_symbol_metadata"]["USTEC"]["lotSize"]=101
    path.write_text(json.dumps(d))
    with pytest.raises(ValueError,match="RAW_BROKER_SPECS"):
        audit(path.parent)


def test_original_artifact_extra_file_or_missing_file_fails(tmp_path):
    path,_=fixture(tmp_path/"original")
    (path.parent/"secret.txt").write_text("NOT_PERMITTED")
    with pytest.raises(ValueError,match="ONE_FILE_SCOPE"):
        audit(path.parent)
    (path.parent/"secret.txt").unlink()
    path.unlink()
    with pytest.raises(ValueError,match="ONE_FILE_SCOPE"):
        audit(path.parent)
