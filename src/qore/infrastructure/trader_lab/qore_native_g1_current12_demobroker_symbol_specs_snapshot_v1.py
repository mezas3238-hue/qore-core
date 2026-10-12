"""Current cTrader IC Markets DEMO symbol specs for original 12 provider IDs.

STRICT READ-ONLY. This is NOT original G0 account / historic contract proof.
Source-only metadata; no market tick, trendbar, refresh-token or order methods.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.qore_native_icmarkets_catalog_preflight_v1 import (
    probe_catalog,
)
from qore.infrastructure.trader_lab.qore_native_icmarkets_missing_m1_capture_v1 import (
    _credentials,
)
from qore.infrastructure.trader_lab.qore_native_icmarkets_missing_m5_capture_v1 import (
    _ReadOnlyIcMarketsHistoryClient,
)
from qore.infrastructure.ctrader_open_api_client import CTraderOpenApiProtocolError
from qore.kernel.result import Failure

IDENTITY="QORE_NATIVE_G1_ORIGINAL12_CURRENT_DEMO_SYMBOL_BY_ID_SPECS_V1"
BROKER="ICMARKETS_CTRADER_DEMO"
PROVIDER_PINS={
    "AUDJPY":("AUDJPY",11),"AUDUSD":("AUDUSD",5),
    "EURUSD":("EURUSD",1),"GBPJPY":("GBPJPY",7),
    "GBPUSD":("GBPUSD",2),"NAS100":("USTEC",10014),
    "SP500":("US500",10013),"US30":("US30",10015),
    "USDCAD":("USDCAD",8),"USDJPY":("USDJPY",4),
    "XAGUSD":("XAGUSD",42),"XAUUSD":("XAUUSD",41),
}
PRIOR_G0_PRICE_PRECISION={
    "AUDJPY":(3,2),"AUDUSD":(5,4),
    "EURUSD":(5,4),"GBPJPY":(3,2),
    "GBPUSD":(5,4),"NAS100":(2,1),
    "SP500":(2,1),"US30":(2,1),
    "USDCAD":(5,4),"USDJPY":(3,2),
    "XAGUSD":(3,2),"XAUUSD":(2,2),
}
OPTIONAL_SCALARS=(
    "maxVolume","commission","commissionType","swapLong","swapShort",
    "swapCalculationType","swapPeriod","baseAssetId","quoteAssetId",
    "measurementUnits","tradingMode","slDistance","tpDistance",
    "minStopLossDistance","minTakeProfitDistance",
)
READ_ONLY_NAMES=frozenset((
    "ProtoOAApplicationAuthReq","ProtoOAGetAccountListByAccessTokenReq",
    "ProtoOAAccountAuthReq","ProtoOASymbolsListReq","ProtoOASymbolByIdReq",
))


def sha(raw:bytes)->str:
    return hashlib.sha256(raw).hexdigest()


class _SpecsReadOnlyClient(_ReadOnlyIcMarketsHistoryClient):
    _HISTORY_ONLY_REQUEST_NAMES=READ_ONLY_NAMES

    def _refresh_tokens(self):
        return Failure(CTraderOpenApiProtocolError(
            "CURRENT_SPECS_REFRESH_TOKEN_PROHIBITED"
        ))


def mandatory_int(obj:Any,name:str,*,allow_zero:bool=False)->int:
    value=getattr(obj,name,None)
    if type(value) is not int or (value<0 if allow_zero else value<=0):
        raise ValueError("CURRENT_SPEC_REQUIRED_INTEGER_FIELD_NOT_VALID_"+name.upper())
    return value


def optional_value(obj:Any,name:str)->int|str|bool|None:
    descriptor=getattr(obj,"DESCRIPTOR",None)
    known=getattr(descriptor,"fields_by_name",{})
    if name not in known:
        return None
    has=getattr(obj,"HasField",None)
    if callable(has):
        try:
            if has(name) is False:
                return None
        except (ValueError,TypeError):
            # A proto3 field without presence may represent an unspecified zero.
            return None
    value=getattr(obj,name,None)
    if isinstance(value,(bool,int,str)) and type(value) in (bool,int,str):
        return value
    return None


def collect_spec_rows(listed:list[Any],details:list[Any])->list[dict[str,Any]]:
    aliases={}
    for item in listed:
        name=getattr(item,"symbolName",None)
        if name not in {p for p,_ in PROVIDER_PINS.values()}:
            continue
        if name in aliases:
            raise ValueError("CURRENT_SPEC_DUPLICATE_PROVIDER_SYMBOL_LISTING")
        symid=mandatory_int(item,"symbolId")
        if getattr(item,"enabled",None) is not True:
            raise ValueError("CURRENT_SPEC_ORIGINAL_SYMBOL_NOT_ENABLED")
        aliases[name]=symid
    if len(aliases)!=12:
        raise ValueError("CURRENT_SPEC_EXACT_BROKER_PROVIDER_UNIVERSE_INCOMPLETE")
    data={}
    for item in details:
        symid=mandatory_int(item,"symbolId")
        if symid in data:
            raise ValueError("CURRENT_SPEC_DUPLICATE_SYMBOL_BY_ID_DETAIL")
        data[symid]=item
    if len(data)!=12:
        raise ValueError("CURRENT_SPEC_SYMBOL_DETAIL_COUNT_MISMATCH")
    rows=[]
    for canonical,(native,expected) in sorted(PROVIDER_PINS.items()):
        if aliases.get(native)!=expected or expected not in data:
            raise ValueError("CURRENT_SPEC_ORIGINAL_PROVIDER_NAME_OR_ID_DIVERGENT")
        detail=data[expected]
        digits=mandatory_int(detail,"digits",allow_zero=True)
        pip=mandatory_int(detail,"pipPosition",allow_zero=True)
        lotsize=mandatory_int(detail,"lotSize")
        volume=mandatory_int(detail,"minVolume")
        step=mandatory_int(detail,"stepVolume")
        comparable=PRIOR_G0_PRICE_PRECISION[canonical]
        if digits != comparable[0] or pip != comparable[1]:
            raise ValueError("CURRENT_SPEC_G0_VS_G1_PRICE_PRECISION_MISMATCH")
        optional={name:optional_value(detail,name) for name in OPTIONAL_SCALARS}
        rows.append({
            "canonical_symbol":canonical,
            "current_broker_provider_symbol":native,
            "current_broker_symbol_id":expected,
            "current_digits":digits,"current_pip_position":pip,
            "current_lot_size_raw":lotsize,
            "current_min_volume_raw":volume,
            "current_step_volume_raw":step,
            "native_optional_numeric_fields_if_explicitly_present":optional,
            "historic_G0_digits_pip_position_agree":True,
            "historical_G0_account_is_current_broker_account_proven":False,
            "historical_lot_value_margin_commissions_swaps_same":False,
            "broker_execution_contract_historically_certified":False,
        })
    return rows


def run(outdir:Path)->dict[str,Any]:
    if len(PROVIDER_PINS)!=12 or len(PRIOR_G0_PRICE_PRECISION)!=12:
        raise ValueError("CURRENT_SPEC_12_FREEZE_FAILED")
    outdir.mkdir(parents=True,exist_ok=True)
    output={
        "identity":IDENTITY,"status":"SOURCE_PRECONDITION_BLOCKED",
        "capture_scope":"CURRENT_DEMO_SYMBOL_SPECS_ONLY_NOT_HISTORIC_PROOF",
        "source_asof_utc":datetime.now(UTC).isoformat(),
        "current_demo_account_id_archived":False,
        "current_demo_broker_label_archived":False,
        "source_broker":BROKER,
        "historical_contract_equivalence_proven":False,
        "actual_broker_tick_requests":0,
        "actual_broker_trendbar_requests":0,
        "broker_orders_submitted":0,"oauth_refresh_attempts":0,
        "NET_authorized":False,"certified_traders":0,"rows":[],
    }
    client=None
    try:
        gate=probe_catalog()
        if (gate.get("status")!="ICMARKETS_DEMO_CATALOG_VERIFIED"
            or gate.get("account_is_live") is not False
            or gate.get("broker_identity_verified_from_account") is not True
            or gate.get("token_refreshed") is not False):
            raise ValueError("CURRENT_SPEC_VERIFIED_ICMARKETS_DEMO_PROOF_REQUIRED")
        account=gate.get("_ephemeral_account_id")
        if type(account) is not int or account<=0:
            raise ValueError("CURRENT_SPEC_EPHEMERAL_ACCOUNT_NOT_VALID")
        for canonical,(provider,symbol_id) in PROVIDER_PINS.items():
            if canonical=="NAS100":
                continue
            row=gate["catalog"]["catalog_exact_matches"].get(provider)
            if (not isinstance(row,dict) or row.get("symbol_id")!=symbol_id
                or row.get("broker_symbol")!=provider
                or row.get("enabled") is not True):
                raise ValueError("CURRENT_SPEC_DEMO_CATALOG_PROVIDER_ID_CHANGED")
        os.environ["QORE_CTRADER_DEMO_ACCOUNT_ID"]=str(account)
        os.environ.pop("QORE_CTRADER_ACCOUNT_ID",None)
        client=_SpecsReadOnlyClient(
            credentials=_credentials(),request_timeout_seconds=35.0
        )
        authenticated=client.connect_and_authenticate()
        if isinstance(authenticated,Failure) or client.account_id!=account:
            raise ValueError("CURRENT_SPEC_DEMO_AUTHENTICATION_FAILED")
        def read(name:str,body:dict[str,Any],cid:str):
            answer=client.request(
                name,body,client_msg_id=cid,timeout_seconds=35.0,
            )
            if isinstance(answer,Failure):
                raise ValueError("CURRENT_SPEC_PROVIDER_QUERY_REJECTED_"+cid)
            return answer.value
        listed=read("ProtoOASymbolsListReq",{
            "ctidTraderAccountId":account,"includeArchivedSymbols":False,
        },"qore-g1-current12-symbols")
        full=read("ProtoOASymbolByIdReq",{
            "ctidTraderAccountId":account,
            "symbolId":sorted(identifier for _,identifier in PROVIDER_PINS.values()),
        },"qore-g1-current12-specs")
        rows=collect_spec_rows(
            list(getattr(listed,"symbol",())),
            list(getattr(full,"symbol",())),
        )
        output["rows"]=rows
        output["source_asof_utc"]=datetime.now(UTC).isoformat()
        output["status"]="CURRENT12_DEMO_NATIVE_SYMBOL_SPECS_PASS_HISTORIC_CONTRACT_UNVERIFIED"
    except (ValueError,RuntimeError,TypeError,KeyError,AttributeError):
        # Never echo exception contents; SDK/provider errors can carry account refs.
        output["safe_blocker"]="CURRENT_SPEC_BROKER_OR_SYMBOL_CONTRACT_FAIL_CLOSED"
    finally:
        if client is not None:
            client.close()
        path=outdir/"CURRENT12_BROKER_NATIVE_SOURCE_METADATA_NOT_HISTORIC_NET.json"
        path.write_text(json.dumps(output,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        (outdir/"SHA256SUMS.txt").write_text(
            sha(path.read_bytes())+"  "+path.name+"\n",encoding="utf-8"
        )
    return output


def main()->None:
    cli=argparse.ArgumentParser()
    cli.add_argument("output",type=Path)
    args=cli.parse_args()
    report=run(args.output)
    print(json.dumps({
        "status":report["status"],"symbols":len(report["rows"]),
        "current_broker_snapshot_only":True,
        "historic_contract_proven":False,"NET":False,"certified":0,
    },sort_keys=True))
    if report["status"]!="CURRENT12_DEMO_NATIVE_SYMBOL_SPECS_PASS_HISTORIC_CONTRACT_UNVERIFIED":
        raise SystemExit(4)


if __name__=="__main__":
    main()
