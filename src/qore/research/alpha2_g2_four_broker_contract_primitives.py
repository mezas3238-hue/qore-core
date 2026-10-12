"""P0 current ICMarkets cTrader DEMO four canonical symbol contract SOURCE probe.

No guessed alias equivalence. No historical spec, NET, orders, token refresh,
ticker/PnL lookup, broker account identifier or secret in artifacts.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from qore.kernel.result import Failure
from qore.research.alpha2_g2_nzdusd_forward_spot_receipt import (
    SourceBlockedError,
    _read_only_spot_client,
)

IDENTITY="QORE_ALPHA2_G2_P0_FOUR_CANONICAL_CURRENT_DEMO_CONTRACT_PRIMITIVES_V1"
CANONICAL=("NAS100","NZDUSD","SP500","XAGUSD")
ALIASES={"NAS100":"USTEC","SP500":"US500"}
NAMES=frozenset(CANONICAL)|frozenset(ALIASES.values())
INT_FIELDS=(
    "digits","pipPosition","lotSize","minVolume","stepVolume","maxVolume",
    "commissionType","preciseTradingCommissionRate","preciseMinCommission",
    "minCommissionAsset","pnlConversionFeeRate","swapCalculationType",
    "swapLong","swapShort","swapPeriod","swapTime","rolloverCommission3Days",
    "baseAssetId","quoteAssetId","leverageId","tradingMode",
)
BOOL_FIELDS=("enableShortSelling",)
STRING_FIELDS=("measurementUnits",)
STATUS="FOUR_CANONICAL_CURRENT_DEMO_SOURCE_PRIMITIVES_PASS_NO_HISTORICAL_EQUIVALENCE"
BLOCKED="FOUR_CANONICAL_SOURCE_CONTRACT_PRIMITIVES_BLOCKED_NOT_NET"


def _proto_value(message: object, name: str) -> object | None:
    descriptor=getattr(message,"DESCRIPTOR",None)
    fields=getattr(descriptor,"fields_by_name",{})
    if name not in fields:
        return None
    present=getattr(message,"HasField",None)
    if not callable(present):
        raise SourceBlockedError("PROTO_FIELD_PRESENCE_NOT_VERIFIABLE")
    try:
        if not present(name):
            return None
    except (ValueError,TypeError):
        raise SourceBlockedError("PROTO_FIELD_PRESENCE_NOT_VERIFIABLE") from None
    return getattr(message,name)


def source_catalog(entries: tuple[object,...]) -> dict[str,int]:
    seen={}
    encountered=set()
    for row in entries:
        name=getattr(row,"symbolName",None)
        if name not in NAMES:
            continue
        if name in encountered:
            raise SourceBlockedError("DUPLICATE_EXACT_SOURCE_NAME")
        encountered.add(name)
        sid=getattr(row,"symbolId",None)
        if type(sid) is not int or sid<=0:
            raise SourceBlockedError("BROKER_SYMBOL_ID_INVALID")
        if getattr(row,"enabled",None) is True:
            seen[name]=sid
    if len(set(seen.values()))!=len(seen):
        raise SourceBlockedError("BROKER_PROVIDER_SYMBOL_ID_COLLISION")
    return dict(sorted(seen.items()))


def extract_detail(symbol_name: str,symbol_id: int,detail: object)->dict:
    if symbol_name not in NAMES or type(symbol_id) is not int or symbol_id<=0:
        raise SourceBlockedError("P0_SYMBOL_ID_SCOPE_INVALID")
    if getattr(detail,"symbolId",None)!=symbol_id:
        raise SourceBlockedError("P0_SYMBOL_DETAIL_WRONG_ID")
    declared:dict[str,Any]={}
    for name in INT_FIELDS:
        value=_proto_value(detail,name)
        if value is not None:
            if type(value) is not int:
                raise SourceBlockedError("P0_PROTO_INTEGER_FIELD_TYPE_INVALID")
            declared[name]=value
    for name in BOOL_FIELDS:
        value=_proto_value(detail,name)
        if value is not None:
            if type(value) is not bool:
                raise SourceBlockedError("P0_PROTO_BOOLEAN_FIELD_TYPE_INVALID")
            declared[name]=value
    for name in STRING_FIELDS:
        value=_proto_value(detail,name)
        if value is not None:
            if type(value) is not str:
                raise SourceBlockedError("P0_PROTO_STRING_FIELD_TYPE_INVALID")
            declared[name]=value
    if (declared.get("digits") is None or
            declared.get("pipPosition") is None or
            declared["digits"]<0 or declared["pipPosition"]<0
            or declared["pipPosition"]>declared["digits"]):
        raise SourceBlockedError("P0_FULL_SYMBOL_PRICE_PRECISION_UNVERIFIED")
    for name in ("lotSize","minVolume","stepVolume"):
        if name not in declared or declared[name]<=0:
            raise SourceBlockedError("P0_FULL_SYMBOL_TRADE_SIZE_UNVERIFIED")
    return {
        "provider_symbol":symbol_name,
        "symbol_id":symbol_id,
        "current_demo_raw_fields_as_reported":declared,
        "missing_optional_fields":sorted(
            set(INT_FIELDS+BOOL_FIELDS+STRING_FIELDS)-set(declared)),
        "raw_numeric_enums_NOT_cash_or_historical_fees":True,
        "historical_CIBO_original12_contract_equal":False,
        "quote_cash_per_unit_price_proven":False,
        "history_2016_to_2024_fee_schedule_proven":False,
    }


def build_canonical_matrix(catalog:dict[str,int],details:dict[str,dict])->dict:
    if not set(catalog)<=NAMES or set(details)!=set(catalog):
        raise SourceBlockedError("P0_PROVIDER_CATALOG_DETAIL_SCOPE_MISMATCH")
    result={}
    for canonical in CANONICAL:
        candidate=ALIASES.get(canonical)
        exact_present=canonical in catalog
        alias_present=bool(candidate and candidate in catalog)
        chosen=canonical if exact_present else candidate if alias_present else None
        result[canonical]={
            "exact_canonical_present":exact_present,
            "alias_candidate_present":alias_present,
            "alias_hint_not_equivalence":candidate,
            "provider_detail_name":chosen,
            "current_demo_detail":details.get(chosen) if chosen else None,
            "contract_source_status":(
                "EXACT_CURRENT_BROKER_NAME_CONTRACT_NOT_HISTORICAL"
                if exact_present else
                "ALIAS_CURRENT_DEMO_DETAILS_ONLY_HISTORICAL_EQ_BLOCKED"
                if alias_present else "BROKER_SYMBOL_NOT_PRESENT"
            ),
            "original_CIBO_contract_equivalence_proven":False,
            "same_demo_account_as_original_ATLAS12_proven":False,
            "NET_contract_authorized":False,
        }
    return result


def _read_demo_contract_source()->dict:
    from qore.infrastructure.trader_lab.qore_native_icmarkets_catalog_preflight_v1 import (
        probe_catalog,
    )
    proof=probe_catalog()
    if (proof.get("status")!="ICMARKETS_DEMO_CATALOG_VERIFIED"
            or proof.get("account_is_live") is not False
            or proof.get("broker_identity_verified_from_account") is not True
            or proof.get("token_refreshed") is not False):
        raise SourceBlockedError("P0_ICMARKETS_DEMO_CATALOG_NOT_VERIFIED")
    account=proof.get("_ephemeral_account_id")
    if type(account) is not int or account<=0:
        raise SourceBlockedError("P0_DEMO_ACCOUNT_SOURCE_INVALID")
    os.environ["QORE_CTRADER_DEMO_ACCOUNT_ID"]=str(account)
    os.environ.pop("QORE_CTRADER_ACCOUNT_ID",None)
    from qore.infrastructure.trader_lab import cibo_market_atlas_10y_m5_consumer_v1 as original

    client=_read_only_spot_client(original._credentials())
    try:
        authenticated=client.connect_and_authenticate()
        if isinstance(authenticated,Failure) or client.account_id!=account:
            raise SourceBlockedError("P0_DEMO_CLIENT_AUTH_FAILURE")
        answer=client.request(
            "ProtoOASymbolsListReq",
            {"ctidTraderAccountId":account,"includeArchivedSymbols":False},
            client_msg_id="alpha2-g2-p0-4name-2alias-exact-catalog",
            timeout_seconds=35,
        )
        if (isinstance(answer,Failure)
                or not isinstance(answer.value,
                    client._bindings.messages["ProtoOASymbolsListRes"])
                or getattr(answer.value,"ctidTraderAccountId",None)!=account):
            raise SourceBlockedError("P0_CATALOG_RESPONSE_UNTRUSTED")
        catalog=source_catalog(tuple(getattr(answer.value,"symbol",())))
        # Require known exact source names NZDUSD and XAGUSD, and one
        # broker name for each index; alias only labels source candidates.
        if ("NZDUSD" not in catalog or "XAGUSD" not in catalog
                or not any(n in catalog for n in ("NAS100","USTEC"))
                or not any(n in catalog for n in ("SP500","US500"))):
            raise SourceBlockedError("P0_ALL_FOUR_BROKER_NAME_CANDIDATES_UNAVAILABLE")
        ids=sorted(catalog.values())
        specs=client.request(
            "ProtoOASymbolByIdReq",
            {"ctidTraderAccountId":account,"symbolId":ids},
            client_msg_id="alpha2-g2-p0-four-broker-symbol-details",
            timeout_seconds=35,
        )
        if (isinstance(specs,Failure)
                or not isinstance(specs.value,
                    client._bindings.messages["ProtoOASymbolByIdRes"])
                or getattr(specs.value,"ctidTraderAccountId",None)!=account):
            raise SourceBlockedError("P0_FULL_SYMBOL_PROVIDER_RESPONSE_UNTRUSTED")
        provided={}
        for row in getattr(specs.value,"symbol",()):
            sid=getattr(row,"symbolId",None)
            if sid not in ids or sid in provided:
                raise SourceBlockedError("P0_SYMBOLBYID_PROVIDER_DETAIL_DUPLICATE_OR_UNREQUESTED")
            provided[sid]=row
        if set(provided)!=set(ids):
            raise SourceBlockedError("P0_FULL_SYMBOL_DETAILS_INCOMPLETE")
        named={
            name:extract_detail(name,sid,provided[sid])
            for name,sid in catalog.items()
        }
        return {"catalog_enabled_exact":catalog,
                "full_current_demo_symbol_details":named,
                "four_canonical_matrix":build_canonical_matrix(catalog,named)}
    finally:
        client.close()


def execute(destination:Path)->dict:
    destination.mkdir(parents=True,exist_ok=True)
    result={
        "identity":IDENTITY,"status":BLOCKED,
        "provider":"ICMARKETS_CTRADER_DEMO",
        "collected_at_utc":datetime.now(UTC).isoformat(),
        "original_request_exact_names":sorted(NAMES),
        "canonicals":list(CANONICAL),"account_id_or_tokens_in_output":False,
        "broker_orders_submitted":0,"token_refreshes":0,
        "historical_quote_prices_accessed":False,
        "W1_W2_W3_original_gross_retested":False,
        "source_current_not_historical":True,
        "historical_contract_equivalence_certified":False,
        "real_account_deposit_point_value_verified":False,
        "real_broker_NET_certified":False,
        "UTC001_certified":False,
    }
    try:
        payload=_read_demo_contract_source()
        result.update(payload)
        result["status"]=STATUS
    except Exception as exc:  # no raw auth / account / SDK exception leak
        static={
            "P0_ICMARKETS_DEMO_CATALOG_NOT_VERIFIED",
            "P0_DEMO_ACCOUNT_SOURCE_INVALID",
            "P0_DEMO_CLIENT_AUTH_FAILURE",
            "P0_CATALOG_RESPONSE_UNTRUSTED",
            "P0_ALL_FOUR_BROKER_NAME_CANDIDATES_UNAVAILABLE",
            "P0_FULL_SYMBOL_PROVIDER_RESPONSE_UNTRUSTED",
            "P0_SYMBOLBYID_PROVIDER_DETAIL_DUPLICATE_OR_UNREQUESTED",
            "P0_FULL_SYMBOL_DETAILS_INCOMPLETE",
            "P0_FULL_SYMBOL_PRICE_PRECISION_UNVERIFIED",
            "P0_FULL_SYMBOL_TRADE_SIZE_UNVERIFIED",
        }
        code=str(exc) if type(exc) is SourceBlockedError else ""
        result["safe_blocker"]=code if code in static else "P0_DEMO_SYMBOL_SOURCE_UNAVAILABLE"
    witness=destination/"alpha2-g2-four-current-demo-symbol-contract-source.json"
    witness.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    (destination/"SOURCE_SHA256SUMS.txt").write_text(
        hashlib.sha256(witness.read_bytes()).hexdigest()+"  "+witness.name+"\n",
        encoding="utf-8",
    )
    return result


def main()->None:
    p=argparse.ArgumentParser()
    p.add_argument("out",type=Path)
    args=p.parse_args()
    value=execute(args.out)
    print(json.dumps({
        "status":value["status"],
        "exact_enabled_names":sorted(value.get("catalog_enabled_exact",{})),
        "canonical_count":len(value.get("four_canonical_matrix",{})),
        "historical_contract_equal":False,
        "net_certified":False,
        "safe_blocker":value.get("safe_blocker"),
    },sort_keys=True))
    if value["status"]!=STATUS:
        raise SystemExit(4)


if __name__=="__main__":
    main()
