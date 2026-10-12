"""Only fake cTrader SymbolById proto fixtures; never broker/auth/secret."""
from types import SimpleNamespace

import pytest

from qore.research.alpha2_g2_four_broker_contract_primitives import (
    ALIASES,
    CANONICAL,
    NAMES,
    SourceBlockedError,
    build_canonical_matrix,
    extract_detail,
    source_catalog,
)


def light(name, symid, enabled=True):
    return SimpleNamespace(symbolName=name,symbolId=symid,enabled=enabled)


class FakeProto:
    def __init__(self, symbol_id, **overrides):
        self.symbolId=symbol_id
        self.values={
            "digits":2,"pipPosition":1,"lotSize":100,
            "minVolume":10,"stepVolume":10,
        }
        self.values.update(overrides)
        self.DESCRIPTOR=SimpleNamespace(
            fields_by_name=dict.fromkeys(self.values, True)
        )

    def HasField(self, name):  # noqa: N802 -- exact protocol method
        return name in self.values

    def __getattr__(self, name):
        return self.values[name]


def test_frozen_four_canonical_and_only_two_index_alias_candidates():
    assert CANONICAL==("NAS100","NZDUSD","SP500","XAGUSD")
    assert ALIASES=={"NAS100":"USTEC","SP500":"US500"}
    assert NAMES=={"NAS100","USTEC","SP500","US500","NZDUSD","XAGUSD"}


def test_exact_broker_catalog_filters_unrelated_and_records_only_enabled():
    rows=(light("USTEC",10014),light("US500",99),
          light("NZDUSD",101),light("XAGUSD",102),
          light("NOT_A_TRADING_SYMBOL",3),light("NAS100",103,False))
    assert source_catalog(rows)=={
        "USTEC":10014,"US500":99,"NZDUSD":101,"XAGUSD":102
    }


def test_symbolbyid_request_must_preserve_raw_proto_fields_no_zeros_inferred():
    d=extract_detail("USTEC",10014,FakeProto(10014))
    assert d["current_demo_raw_fields_as_reported"]=={
        "digits":2,"pipPosition":1,
        "lotSize":100,"minVolume":10,"stepVolume":10,
    }
    assert "preciseTradingCommissionRate" in d["missing_optional_fields"]
    assert d["history_2016_to_2024_fee_schedule_proven"] is False
    assert d["quote_cash_per_unit_price_proven"] is False


def test_present_source_zeros_are_not_missing_or_fee_authorization():
    d=extract_detail(
        "US500",91,FakeProto(
            91,commissionType=0,preciseTradingCommissionRate=0,
            swapLong=0,swapShort=0,
        )
    )
    raw=d["current_demo_raw_fields_as_reported"]
    assert raw["commissionType"]==0
    assert raw["preciseTradingCommissionRate"]==0
    assert d["historical_CIBO_original12_contract_equal"] is False


def test_boolean_spoof_and_bad_trade_volume_invalid():
    with pytest.raises(SourceBlockedError,match="INTEGER_FIELD_TYPE"):
        extract_detail("XAGUSD",91,FakeProto(91,digits=True))
    with pytest.raises(SourceBlockedError,match="SIZE_UNVERIFIED"):
        extract_detail("XAGUSD",91,FakeProto(91,lotSize=0))
    with pytest.raises(SourceBlockedError,match="SIZE_UNVERIFIED"):
        extract_detail("XAGUSD",91,FakeProto(91,stepVolume=-1))


def test_alias_market_is_only_candidate_not_g0_equivalent():
    catalog={"USTEC":10014,"US500":10022,"NZDUSD":12,"XAGUSD":22}
    details={s:extract_detail(s,i,FakeProto(i)) for s,i in catalog.items()}
    out=build_canonical_matrix(catalog,details)
    assert out["NAS100"]["provider_detail_name"]=="USTEC"
    assert out["NAS100"]["contract_source_status"]==(
        "ALIAS_CURRENT_DEMO_DETAILS_ONLY_HISTORICAL_EQ_BLOCKED"
    )
    assert out["SP500"]["provider_detail_name"]=="US500"
    assert out["NAS100"]["NET_contract_authorized"] is False
    assert out["SP500"]["original_CIBO_contract_equivalence_proven"] is False
    assert out["NZDUSD"]["exact_canonical_present"]
    assert out["XAGUSD"]["exact_canonical_present"]


def test_exact_canonical_takes_precedence_but_not_historical_claim():
    catalog={"NAS100":15,"USTEC":16,"SP500":11,"US500":12,
             "NZDUSD":3,"XAGUSD":4}
    details={s:extract_detail(s,i,FakeProto(i)) for s,i in catalog.items()}
    out=build_canonical_matrix(catalog,details)
    assert out["NAS100"]["provider_detail_name"]=="NAS100"
    assert out["NAS100"]["alias_candidate_present"] is True
    assert out["NAS100"]["same_demo_account_as_original_ATLAS12_proven"] is False


def test_duplicate_provider_name_and_duplicate_symbol_id_blocked():
    with pytest.raises(SourceBlockedError,match="DUPLICATE_EXACT"):
        source_catalog((light("USTEC",1),light("USTEC",2)))
    with pytest.raises(SourceBlockedError,match="ID_COLLISION"):
        source_catalog((light("USTEC",1),light("US500",1)))


def test_details_wrong_provider_id_cannot_be_accepted():
    with pytest.raises(SourceBlockedError,match="WRONG_ID"):
        extract_detail("USTEC",10014,FakeProto(10022))
    with pytest.raises(SourceBlockedError,match="SCOPE_INVALID"):
        extract_detail("GBPUSD",10014,FakeProto(10014))


def test_incomplete_detail_and_source_catalog_fail_closed():
    d=FakeProto(101)
    d.values.pop("digits")
    d.DESCRIPTOR.fields_by_name.pop("digits")
    with pytest.raises(SourceBlockedError,match="PRICE_PRECISION"):
        extract_detail("NZDUSD",101,d)
    with pytest.raises(SourceBlockedError,match="CATALOG_DETAIL_SCOPE_MISMATCH"):
        build_canonical_matrix({"USTEC":1},{"US500":{}})


def test_absent_one_provider_is_reported_missing_not_substituted():
    catalog={"NZDUSD":100,"XAGUSD":101}
    details={s:extract_detail(s,i,FakeProto(i)) for s,i in catalog.items()}
    result=build_canonical_matrix(catalog,details)
    assert result["NAS100"]["contract_source_status"]=="BROKER_SYMBOL_NOT_PRESENT"
    assert result["SP500"]["provider_detail_name"] is None
