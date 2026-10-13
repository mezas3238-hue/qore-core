"""QORE FUTURES A / M0: STRICT native futures historical source-schema checker.

No price discovery, no broker login, no market orders, no return/PnL/Sharpe.
Never treat synthetic tests or a hand-authored manifest as proof of market data
entitlement, complete custody, or that a trader can be promoted.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

ROOT_EXCHANGES={
    "CL":"NYMEX","NG":"NYMEX",
    "GC":"COMEX","HG":"COMEX",
    "ZC":"CBOT","ZS":"CBOT",
}
RESEARCH_CUTOFF=date(2024,9,17)
NO_LIVE=True
NO_ECONOMIC_PNL=True


class NativeFuturesSourceError(ValueError):
    pass


def _fail(message:str):
    raise NativeFuturesSourceError("QORE_FUTURES_A_M0_"+message)


def _date(raw:Any,label:str)->date:
    if not isinstance(raw,str):
        _fail("BAD_DATE_"+label)
    try:
        d=date.fromisoformat(raw)
    except (ValueError,TypeError):
        _fail("BAD_DATE_"+label)
    if d.isoformat()!=raw:
        _fail("DATE_NOT_ISO_"+label)
    return d


def _utc(raw:Any,label:str)->datetime:
    if not isinstance(raw,str) or not raw.endswith("Z"):
        _fail("REQUIRE_EXPLICIT_UTC_"+label)
    try:
        val=datetime.fromisoformat(raw[:-1]+"+00:00")
    except (ValueError,TypeError):
        _fail("BAD_TIMESTAMP_"+label)
    if val.tzinfo is None or val.utcoffset().total_seconds()!=0:
        _fail("TIMEZONE_"+label)
    return val


def _decimal(raw:Any,label:str,positive:bool=False,allow_negative:bool=False)->Decimal:
    if not isinstance(raw,str):
        _fail("DECIMAL_AS_STRING_"+label)
    try:
        val=Decimal(raw)
    except InvalidOperation:
        _fail("BAD_DECIMAL_"+label)
    if not val.is_finite() or (positive and val<=0) or (not allow_negative and val<0):
        _fail("DECIMAL_RANGE_"+label)
    return val


def _hash(raw:Any,label:str)->str:
    if not isinstance(raw,str) or re.fullmatch("[0-9a-f]{64}",raw) is None:
        _fail("MISSING_OR_BAD_SHA256_"+label)
    if set(raw)=={"0"}:
        _fail("DUMMY_SHA256_"+label)
    return raw


def _closed_keys(obj:dict,expected:set[str],label:str):
    if not isinstance(obj,dict) or set(obj)!=expected:
        _fail("SCHEMA_KEYS_"+label)


DATASET_KEYS={
    "provider","dataset_id","licensed_internal_research","license_receipt_sha256",
    "original_source_sha256","authentic_exchange_contracts",
    "historical_bid_ask_or_fills_supported","settlement_publication_asof_documented",
    "real_contract_specifications_documented","coverage_2012_2024_verified",
    "broker_exchange_clearing_cost_schedule_verified",
}
ROW_KEYS={
    "root","venue","native_contract_id","expiration_month",
    "trade_date","settlement_value","settlement_published_at_utc",
    "volume","volume_published_at_utc","open_interest",
    "open_interest_published_at_utc","exchange_first_notice_date",
    "risk_liquidation_cutoff_date","last_trade_date","contract_multiplier","minimum_tick",
    "source_row_sha256",
}


def validate_dataset_manifest(m:dict)->dict:
    _closed_keys(m,DATASET_KEYS,"DATASET")
    if not isinstance(m["provider"],str) or not m["provider"].strip():
        _fail("PROVIDER_MISSING")
    if not isinstance(m["dataset_id"],str) or not m["dataset_id"].strip():
        _fail("DATASET_ID_MISSING")
    out={"dataset_provider":m["provider"],"dataset_id":m["dataset_id"]}
    for key in (
        "licensed_internal_research","authentic_exchange_contracts",
        "historical_bid_ask_or_fills_supported",
        "settlement_publication_asof_documented",
        "real_contract_specifications_documented","coverage_2012_2024_verified",
        "broker_exchange_clearing_cost_schedule_verified",
    ):
        if type(m[key]) is not bool:
            _fail("REQUIRE_BOOLEAN_"+key)
        out[key]=m[key]
    _hash(m["original_source_sha256"],"ORIGINAL_SOURCE")
    _hash(m["license_receipt_sha256"],"LICENSE_RECEIPT")
    # NOTE hashes from a self-entered manifest are not cryptographic proof
    # of possession of bytes or of rights. Human custody review mandatory.
    out["complete_claims_in_manifest"]=all(
        out[k] for k in (
            "licensed_internal_research","authentic_exchange_contracts",
            "historical_bid_ask_or_fills_supported",
            "settlement_publication_asof_documented",
            "real_contract_specifications_documented","coverage_2012_2024_verified",
            "broker_exchange_clearing_cost_schedule_verified",
        )
    )
    out["external_receipt_and_bytes_verified_independently"]=False
    return out


@dataclass(frozen=True)
class ContractObservation:
    root:str
    venue:str
    contract_id:str
    expiry:date
    trade:date
    publication_settle:datetime
    publication_volume:datetime
    publication_oi:datetime
    cutoff:date
    exchange_first_notice:date|None
    last_trade:date
    settle:Decimal
    multiplier:Decimal
    min_tick:Decimal
    volume:int
    oi:int


def _expiry_month(s:str)->date:
    if not isinstance(s,str) or re.fullmatch(r"20\d{2}-(0[1-9]|1[0-2])",s) is None:
        _fail("BAD_CONTRACT_MONTH")
    return _date(s+"-01","EXPIRY_MONTH")


def validate_contract_row(row:dict)->ContractObservation:
    _closed_keys(row,ROW_KEYS,"NATIVE_CONTRACT_OBSERVATION")
    root=row["root"]
    if root not in ROOT_EXCHANGES:
        _fail("UNREGISTERED_ROOT")
    if row["venue"]!=ROOT_EXCHANGES[root]:
        _fail("ROOT_VENUE_MISMATCH")
    native=row["native_contract_id"]
    if not isinstance(native,str) or re.fullmatch("[A-Z0-9._-]{5,32}",native) is None:
        _fail("NOT_EXPLICIT_NATIVE_CONTRACT_ID")
    if native==root or "CONT" in native or "ADJUST" in native:
        _fail("CONTINUOUS_OR_ROOT_IS_NOT_NATIVE_CONTRACT")
    expiry=_expiry_month(row["expiration_month"])
    trade=_date(row["trade_date"],"TRADE_DATE")
    if trade>=RESEARCH_CUTOFF:
        _fail("QORE_ORIGINAL_HOLDOUT_NOT_ALLOWED")
    cutoff=_date(row["risk_liquidation_cutoff_date"],"RISK_LIQUIDATION_CUTOFF")
    first_notice=(None if row["exchange_first_notice_date"] is None
                  else _date(row["exchange_first_notice_date"],"EXCHANGE_FIRST_NOTICE"))
    lasttrade=_date(row["last_trade_date"],"LAST_TRADE")
    if cutoff>lasttrade:
        _fail("RISK_CUTOFF_AFTER_LAST_TRADE")
    if first_notice is not None and cutoff>first_notice:
        _fail("RISK_CUTOFF_AFTER_EXCHANGE_NOTICE")
    # For CL and NG, exchange notice can occur AFTER last trade. Never demand
    # first_notice <= last_trade: instead require an earlier broker-approved
    # liquidation cutoff and independently retain optional exchange notice.
    if trade>lasttrade:
        _fail("TRADED_AFTER_LAST_TRADE")
    settlement=_decimal(row["settlement_value"],"SETTLEMENT",allow_negative=True)
    mult=_decimal(row["contract_multiplier"],"MULTIPLIER",positive=True)
    tick=_decimal(row["minimum_tick"],"TICK",positive=True)
    volume=row["volume"]
    oi=row["open_interest"]
    if type(volume) is not int or volume<0 or type(oi) is not int or oi<0:
        _fail("INVALID_VOLUME_OI")
    _hash(row["source_row_sha256"],"ROW")
    return ContractObservation(
        root=root,venue=row["venue"],contract_id=native,
        expiry=expiry,trade=trade,
        publication_settle=_utc(row["settlement_published_at_utc"],"SETTLE"),
        publication_volume=_utc(row["volume_published_at_utc"],"VOLUME"),
        publication_oi=_utc(row["open_interest_published_at_utc"],"OI"),
        cutoff=cutoff,exchange_first_notice=first_notice,last_trade=lasttrade,
        settle=settlement,multiplier=mult,min_tick=tick,volume=volume,oi=oi,
    )


def check_decision_asof(row:ContractObservation,decision_at:str):
    when=_utc(decision_at,"DECISION")
    if when.date()<=row.trade:
        _fail("CANNOT_TRADE_SAME_DAY_SETTLEMENT")
    if (row.publication_settle>when or row.publication_volume>when or
            row.publication_oi>when):
        _fail("LOOKAHEAD_PUBLICATION_TIMESTAMP")
    if when.date()>=row.cutoff:
        _fail("DELIVERY_NOTICE_OR_ROLL_CUTOFF_REACHED")
    if when.date()>row.last_trade:
        _fail("EXPIRED_NATIVE_CONTRACT")
    return True


def validate_two_pats_native_curve(rows:list[dict],decision_at:str)->dict:
    """Two different native contract-months for one root/trade session.

    Does not derive a signal or a dollar return; checks inputs and timing only.
    """
    if not isinstance(rows,list) or len(rows)!=2:
        _fail("REQUIRE_EXACTLY_TWO_CURVE_LEGS")
    a,b=(validate_contract_row(x) for x in rows)
    if a.root!=b.root or a.trade!=b.trade or a.venue!=b.venue:
        _fail("INCOMPATIBLE_CURVE_LEGS")
    if a.contract_id==b.contract_id or a.expiry==b.expiry:
        _fail("NOT_TWO_DISTINCT_EXPIRING_CONTRACTS")
    if not a.expiry<b.expiry:
        _fail("CURVE_ORDER_WRONG")
    check_decision_asof(a,decision_at)
    check_decision_asof(b,decision_at)
    if a.volume==0 or b.volume==0 or a.oi==0 or b.oi==0:
        _fail("UNTRADED_OR_ZERO_OI_CURVE_LEG")
    return {
        "root":a.root,"venue":a.venue,"trade_date":a.trade.isoformat(),
        "decision_at_utc":decision_at,
        "native_contracts_distinct":True,"two_settlements_public_before_decision":True,
        "volume_oi_public_before_decision":True,
        "delivery_cutoff_respected":True,
        "no_continuous_series_used":True,
        "PnL_calculated":False,
        "actual_prices_exported":False,
    }


def inspect_local_envelope(doc:dict):
    _closed_keys(doc,{"dataset_manifest","sample_curves","decision_at_utc"},"M0_ENVELOPE")
    man=validate_dataset_manifest(doc["dataset_manifest"])
    samples=doc["sample_curves"]
    if not isinstance(samples,list) or len(samples)!=6:
        _fail("REQUIRE_SIX_ROOT_SAMPLES")
    out=[validate_two_pats_native_curve(x,doc["decision_at_utc"]) for x in samples]
    if set(x["root"] for x in out)!=set(ROOT_EXCHANGES):
        _fail("SAMPLE_ROOT_UNIVERSE_MISMATCH")
    return {
        "identity":"QORE_FUTURES_A_M0_SOURCE_CONTRACT_ONLY_V1",
        "synthetic_or_local_manifest_verification":"SCHEMA_ONLY",
        "status":"M0_CONTRACT_SCHEMA_PASS_NOT_AUTHENTIC_DATA_CERTIFICATION",
        "manifest_claims_complete":man["complete_claims_in_manifest"],
        "manifest_independent_license_or_raw_custody_validation":False,
        "sample_roots":sorted(ROOT_EXCHANGES),
        "sample_leg_count":12,
        "authentic_entitlement_confirmed_by_QORE":False,
        "complete_historical_data_certified_by_QORE":False,
        "historical_bidask_and_fills_certified_by_QORE":False,
        "full_history_PnL_or_Sharpe_calculated":False,
        "economic_holdout_opened":False,
        "source_ready_for_prereg":False,
        "traders_certified":0,
    }


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("envelope",type=Path,help="private JSON source metadata+sample quotes")
    parser.add_argument("output",type=Path,help="output only booleans and metadata")
    args=parser.parse_args()
    raw=args.envelope.read_bytes()
    report=inspect_local_envelope(json.loads(raw))
    report["input_sha256"]=hashlib.sha256(raw).hexdigest()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    print("FUTURES_A_M0_SCHEMA_ONLY_NO_PNL",json.dumps(report,sort_keys=True))


if __name__=="__main__":
    main()
