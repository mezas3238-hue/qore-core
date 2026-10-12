"""No-network current ICMarkets spec snapshot exact-id, read-only and provenance guards."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from qore.infrastructure.trader_lab import qore_native_g1_current12_demobroker_symbol_specs_snapshot_v1 as s


class FakeProto:
    def __init__(self, **args):
        self.__dict__.update(args)
        self.DESCRIPTOR=SimpleNamespace(fields_by_name={
            k:None for k in args
        })

    def HasField(self,name):
        return name in self.__dict__ and self.__dict__[name] is not None


def _fixed():
    listed=[]
    details=[]
    for canonical,(name,ident) in s.PROVIDER_PINS.items():
        listed.append(FakeProto(
            symbolName=name,symbolId=ident,enabled=True
        ))
        digits,pip=s.PRIOR_G0_PRICE_PRECISION[canonical]
        details.append(FakeProto(
            symbolId=ident,digits=digits,pipPosition=pip,
            lotSize=100000,minVolume=100,stepVolume=100,
            commission=20,commissionType=1,swapLong=-1,swapShort=2,
        ))
    return listed,details


def test_fixed_scope_source_independent_original_12_names_and_symbols():
    assert len(s.PROVIDER_PINS)==12
    assert len({sym for sym,_ in s.PROVIDER_PINS.values()})==12
    assert len({i for _,i in s.PROVIDER_PINS.values()})==12
    assert s.PROVIDER_PINS["NAS100"]==("USTEC",10014)
    assert s.PROVIDER_PINS["SP500"]==("US500",10013)
    assert s.PRIOR_G0_PRICE_PRECISION["NAS100"]==(2,1)


def test_positive_exact_current_demobroker_spec_without_historic_promotion():
    market,details=_fixed()
    rows=s.collect_spec_rows(market,details)
    assert len(rows)==12
    assert all(x["historic_G0_digits_pip_position_agree"] for x in rows)
    assert all(not x["broker_execution_contract_historically_certified"] for x in rows)
    assert all(x["current_lot_size_raw"]==100000 for x in rows)
    assert next(x for x in rows if x["canonical_symbol"]=="NAS100")["current_broker_symbol_id"]==10014


def test_unmatched_broker_provider_id_blocks_before_current_contract():
    market,details=_fixed()
    market[0].symbolId=9999
    with pytest.raises(ValueError,match="NAME_OR_ID_DIVERGENT"):
        s.collect_spec_rows(market,details)


def test_missing_or_disabled_source_and_duplicate_provider_fail_closed():
    market,details=_fixed()
    market[0].enabled=False
    with pytest.raises(ValueError,match="NOT_ENABLED"):
        s.collect_spec_rows(market,details)
    market,details=_fixed()
    market.append(market[-1])
    with pytest.raises(ValueError,match="DUPLICATE_PROVIDER"):
        s.collect_spec_rows(market,details)


def test_price_precision_drift_prohibited_and_optional_field_absence_not_zero():
    market,details=_fixed()
    details[0].pipPosition+=1
    with pytest.raises(ValueError,match="PRECISION_MISMATCH"):
        s.collect_spec_rows(market,details)
    clean=FakeProto(symbolId=11,digits=3,pipPosition=2)
    assert s.optional_value(clean,"commission") is None
    assert s.optional_value(clean,"swapLong") is None


def test_credentials_and_orders_can_never_be_sent_by_research_client():
    assert s.READ_ONLY_NAMES==frozenset({
        "ProtoOAApplicationAuthReq","ProtoOAGetAccountListByAccessTokenReq",
        "ProtoOAAccountAuthReq","ProtoOASymbolsListReq","ProtoOASymbolByIdReq",
    })
    assert s._SpecsReadOnlyClient._HISTORY_ONLY_REQUEST_NAMES==s.READ_ONLY_NAMES
    assert "ProtoOAGetTickDataReq" not in s.READ_ONLY_NAMES
    assert "ProtoOAGetTrendbarsReq" not in s.READ_ONLY_NAMES
    assert "ProtoOANewOrderReq" not in s.READ_ONLY_NAMES
    assert "ProtoOARefreshTokenReq" not in s.READ_ONLY_NAMES


def test_bool_not_accepted_as_native_int():
    with pytest.raises(ValueError,match="REQUIRED_INTEGER_FIELD_NOT_VALID"):
        s.mandatory_int(SimpleNamespace(lotSize=True),"lotSize")
    assert s.mandatory_int(SimpleNamespace(digits=0),"digits",allow_zero=True)==0
