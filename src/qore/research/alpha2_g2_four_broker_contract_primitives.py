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
        # V2: reuse the SAME verified, authenticated DEMO source catalog.
        # No second SymbolList request (original adapter returned Failure).
        # The verified census does NOT ask USTEC by name; absence is explicit.
        verified=proof.get("catalog",{})
        matches=verified.get("catalog_exact_matches",{})
        exact_enabled=set(verified.get("available_exact",()))
        catalog={}
        for name in sorted(NAMES):
            item=matches.get(name)
            if not isinstance(item,dict) or name not in exact_enabled:
                continue
            sid=item.get("symbol_id")
            if (item.get("broker_symbol")!=name or
                    item.get("enabled") is not True or
                    type(sid) is not int or sid<=0):
                raise SourceBlockedError("P0_BROKER_VERIFIED_CATALOG_ITEM_INVALID")
            catalog[name]=sid
        if len(set(catalog.values()))!=len(catalog):
            raise SourceBlockedError("P0_BROKER_VERIFIED_CATALOG_ID_COLLISION")
        if not {"NZDUSD","XAGUSD"}.issubset(catalog):
            raise SourceBlockedError("P0_TWO_EXACT_FX_METAL_BROKER_NAMES_MISSING")
        if not any(name in catalog for name in ("SP500","US500")):
            raise SourceBlockedError("P0_US500_SP500_BROKER_NAME_MISSING")
        ids=sorted(catalog.values())
        specs=client.request(
            "ProtoOASymbolByIdReq",
            {"ctidTraderAccountId":account,"symbolId":ids},
            client_msg_id="alpha2-g2-p0-four-broker-symbol-details",
            timeout_seconds=35,
        )
        if isinstance(specs,Failure):
            raise SourceBlockedError("P0_FULL_SYMBOL_RESPONSE_FAILURE")
        if not isinstance(
            specs.value,client._bindings.messages["ProtoOASymbolByIdRes"]
        ):
            raise SourceBlockedError("P0_FULL_SYMBOL_RESPONSE_WRONG_PROTO")
        detail_response_account=getattr(specs.value,"ctidTraderAccountId",None)
        if type(detail_response_account) is not int or detail_response_account<=0:
            raise SourceBlockedError("P0_FULL_SYMBOL_RESPONSE_ACCOUNT_ID_MISSING")
        if detail_response_account!=account:
            raise SourceBlockedError("P0_FULL_SYMBOL_RESPONSE_ACCOUNT_ID_MISMATCH")
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
        matrix=build_canonical_matrix(catalog,named)
        resolved=sum(
            value["provider_detail_name"] is not None for value in matrix.values()
        )
        # Audit label even when 3 of 4 broker specs available: no guesses.
        source_state=(
            STATUS if resolved==4 else
            "CURRENT_DEMO_3OF4_CONTRACT_PRIMITIVES_PARTIAL_NOT_EQUIVALENT"
            if resolved==3 else BLOCKED
        )
        return {
            "catalog_enabled_exact":catalog,
            "broker_catalog_source":"AUTHENTICATED_PREFLIGHT_SINGLE_SOURCE",
            "catalog_names_not_covered":sorted(NAMES-set(catalog)),
            "full_current_demo_symbol_details":named,
            "four_canonical_matrix":matrix,
            "current_contract_primitive_market_count":resolved,
            "source_state":source_state,
        }
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
        result["status"]=payload["source_state"]
    except Exception as exc:  # no raw auth / account / SDK exception leak
        static={
            "P0_ICMARKETS_DEMO_CATALOG_NOT_VERIFIED",
            "P0_DEMO_ACCOUNT_SOURCE_INVALID",
            "P0_DEMO_CLIENT_AUTH_FAILURE",
            "P0_BROKER_VERIFIED_CATALOG_ITEM_INVALID",
            "P0_BROKER_VERIFIED_CATALOG_ID_COLLISION",
            "P0_TWO_EXACT_FX_METAL_BROKER_NAMES_MISSING",
            "P0_US500_SP500_BROKER_NAME_MISSING",
            "P0_CATALOG_RESPONSE_FAILURE",
            "P0_CATALOG_RESPONSE_WRONG_PROTO",
            "P0_CATALOG_RESPONSE_ACCOUNT_ID_MISSING",
            "P0_CATALOG_RESPONSE_ACCOUNT_ID_MISMATCH",
            "P0_ALL_FOUR_BROKER_NAME_CANDIDATES_UNAVAILABLE",
            "P0_FULL_SYMBOL_RESPONSE_FAILURE",
            "P0_FULL_SYMBOL_RESPONSE_WRONG_PROTO",
            "P0_FULL_SYMBOL_RESPONSE_ACCOUNT_ID_MISSING",
            "P0_FULL_SYMBOL_RESPONSE_ACCOUNT_ID_MISMATCH",
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
    if value["status"] not in (
        STATUS,"CURRENT_DEMO_3OF4_CONTRACT_PRIMITIVES_PARTIAL_NOT_EQUIVALENT",
    ):
        raise SystemExit(4)


if __name__=="__main__":
    main()
