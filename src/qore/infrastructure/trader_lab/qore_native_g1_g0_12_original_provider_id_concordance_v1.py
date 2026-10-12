"""G0 CIBO 12 × G1 IC Markets native BID/ASK source-only identity concordance.

Original numeric symbol IDs MAY BE scoped to accounts/brokers. A match here
NEVER certifies historic contract, commission, account or NET profitability.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

IDENTITY = "QORE_NATIVE_G1_ORIGINAL12_G0_G1_PROVIDER_SYMBOL_ID_CONCORDANCE_V1"
ORIGINAL12 = frozenset((
    "AUDJPY","AUDUSD","EURUSD","GBPJPY","GBPUSD","USDCAD",
    "USDJPY","NAS100","SP500","US30","XAUUSD","XAGUSD",
))
G0_RUN=35166210458
G0_HEAD="ab782b8e9f890f86a2b6500070f0556b4b685e3d"
SOURCE_DIGESTS = {
    "G0":"aa7aef2222ddd89536090110cc03ed4a9f2e0ca8e8e50d5ba40912cec0cd9ba7",
    "G1_29":"be123f91e2069390e3bb44f9ce8b9398e3216b9ce483b7441f7f2aebb918f1c0",
    "US500":"a1fa1a7c22062f2b20970c5a8540634f3fc3ab0a165f136dce97aa3cbe26f5f5",
    "XAGUSD":"aaa32406dd4e2a5cc826da47e088f645f3963b88735d4ced4d7f366e5f00843e",
    "USTEC":"402831fcf2ba60070bdcf92671a1470838bda44208bf40ff373d95dc066c5da4",
    "USTEC_SPEC":"7f927792e575c5cccb9932c55a8db6733430c34629681701c6acd98491ac5c2e",
}
G0_ID = "CIBO_MARKET_ATLAS_10Y_CONSUMPTION_V1"
G0_EXPECTED_SOURCE="CIBO_MARKET_ATLAS_20Y_V1"


def sha(blob:bytes)->str:
    return hashlib.sha256(blob).hexdigest()


def verify_files(folder:Path, register:str, *, strict:bool=True)->dict[str,str]:
    p=folder/register
    if not p.is_file():
        raise ValueError("CONTRACT_SOURCE_SHA_REGISTER_MISSING")
    records={}
    for line in p.read_text(encoding="utf-8").splitlines():
        match=re.fullmatch(r"([0-9a-f]{64})  ([A-Za-z0-9_.-]+)",line)
        if match is None or match[2] in records:
            raise ValueError("CONTRACT_SOURCE_SHA_REGISTER_UNSAFE")
        records[match[2]]=match[1]
    actual={p.name for p in folder.iterdir() if p.is_file()} - {register}
    if strict and actual!=set(records):
        raise ValueError("CONTRACT_SOURCE_SHA_REGISTER_INCOMPLETE")
    for name,expected in records.items():
        file=folder/name
        if not file.is_file() or sha(file.read_bytes())!=expected:
            raise ValueError("CONTRACT_SOURCE_ORIGINAL_SHA_CHANGED")
    return records


def _int(value:Any,label:str)->int:
    if type(value) is not int or value<=0:
        raise ValueError("CONTRACT_SOURCE_"+label+"_INVALID")
    return value


def original_g0(folder:Path)->dict[str,dict]:
    checks=verify_files(folder,"SHA256SUMS.txt")
    if "ten-year-consumption-index.json" not in checks:
        raise ValueError("G0_ORIGINAL_AGGREGATE_INDEX_MISSING")
    if (folder/"git-sha.txt").read_text().strip()!=G0_HEAD:
        raise ValueError("G0_SOURCE_CODE_SHA_MISMATCH")
    data=json.loads((folder/"ten-year-consumption-index.json").read_bytes())
    if (data.get("identity")!=G0_ID or data.get("symbol_count")!=12
            or data.get("production_authorized") is not False
            or data.get("live_authorized") is not False
            or data.get("real_capital_authorized") is not False):
        raise ValueError("G0_ORIGINAL_SOURCE_OR_PRODUCTION_BOUNDARY_DRIFT")
    rows={}
    for symbol in data["symbols"]:
        canonical=symbol.get("canonical_symbol")
        if canonical not in ORIGINAL12 or canonical in rows:
            raise ValueError("G0_ORIGINAL_12_UNIVERSE_DUPLICATE")
        pids={}
        meta=set()
        partitions=symbol.get("partitions")
        if not isinstance(partitions,list) or len(partitions)!=11:
            raise ValueError("G0_HISTORICAL_PROVIDER_PARTITIONS_INCOMPLETE")
        for partition in partitions:
            if (partition.get("identity")!=G0_ID
                or partition.get("canonical_symbol")!=canonical
                or partition.get("raw_integrity_status")!="CLEAN_PROVIDER_PAYLOAD"
                or partition.get("read_only") is not True
                or partition.get("live_authorized") is not False
                or partition.get("production_authorized") is not False):
                raise ValueError("G0_PROVIDER_NATIVE_PARTITION_NOT_VERIFIED")
            n=partition.get("partition")
            if n in pids:
                raise ValueError("G0_DUPLICATE_HISTORICAL_SOURCE_YEAR")
            pids[n]=partition
            meta.add((
                partition.get("provider_symbol"),
                _int(partition.get("provider_symbol_id"),"G0_SYMBOL_ID"),
                _int(partition.get("digits"),"G0_DIGITS"),
                _int(partition.get("pip_position"),"G0_PIP_POSITION"),
            ))
        if set(pids)!={str(year) for year in range(2016,2027)} or len(meta)!=1:
            raise ValueError("G0_PROVIDER_IDENTITY_CHANGED_ACROSS_HISTORICAL_PARTITIONS")
        provider,symbol_id,digits,pip_position=meta.pop()
        if (symbol.get("provider_symbol")!=provider
            or symbol.get("provider_symbol_id")!=symbol_id
            or symbol.get("digits")!=digits
            or symbol.get("pip_position")!=pip_position):
            raise ValueError("G0_SOURCE_PARENT_SYMBOL_METADATA_DRIFT")
        rows[canonical]={
            "g0_provider_symbol":provider,"g0_symbol_id":symbol_id,
            "g0_digits":digits,"g0_pip_position":pip_position,
            "g0_source_partitions":len(partitions),
        }
    if set(rows)!=ORIGINAL12:
        raise ValueError("G0_ORIGINAL_12_INCOMPLETE")
    return rows


def g1_29(folder:Path,canonical:str)->dict:
    target=folder/canonical
    checks=verify_files(target,"SOURCE_SHA256SUMS.txt")
    if "SOURCE-MANIFEST-NOT-NET.json" not in checks:
        raise ValueError("G1_29_PROVIDER_MANIFEST_NOT_SIGNED")
    record=json.loads((target/"SOURCE-MANIFEST-NOT-NET.json").read_bytes())
    if (record.get("canonical_symbol")!=canonical
        or record.get("provider")!="ICMARKETS_CTRADER_DEMO"
        or record.get("account_type")!="DEMO"
        or record.get("complete_windows")!=3
        or record.get("state")!="THREE_WINDOWS_NATIVE_BID_ASK_PRESENT_NOT_NET"
        or record.get("source_captured_both_sides") is not True
        or record.get("historical_NET_authorized") is not False
        or record.get("trade_orders_sent")!=0):
        raise ValueError("G1_29_BROKER_SOURCE_UNTRUSTED")
    return record


def g1_crossasset(folder:Path,canonical:str)->dict:
    checks=verify_files(folder,"OUTPUT_SHA256SUMS.txt")
    if "SOURCE-CROSSASSET-NOT-NET.json" not in checks:
        raise ValueError("G1_CROSSASSET_MANIFEST_SHA_MISSING")
    rec=json.loads((folder/"SOURCE-CROSSASSET-NOT-NET.json").read_bytes())
    if (rec.get("canonical_symbol")!=canonical
        or rec.get("provider")!="ICMARKETS_CTRADER_DEMO"
        or rec.get("account_type")!="DEMO"
        or rec.get("complete_windows")!=3
        or rec.get("source_result")!="THREE_WINDOWS_NATIVE_BID_ASK_PRESENT_NOT_NET"
        or rec.get("historical_contract_equivalence_to_G0_proven") is not False
        or rec.get("NET_economics_authorized") is not False
        or rec.get("trade_orders_sent")!=0):
        raise ValueError("G1_CROSSASSET_CONTRACT_SOURCE_NOT_PROVEN")
    return rec


def g1_ustec(folder:Path)->dict:
    checks=verify_files(folder,"SHA256SUMS.txt")
    if "USTEC-CANDIDATE-SOURCE-NOT-NET.json" not in checks:
        raise ValueError("G1_USTEC_SIGNED_MANIFEST_ABSENT")
    r=json.loads((folder/"USTEC-CANDIDATE-SOURCE-NOT-NET.json").read_bytes())
    if (r.get("canonical_alias_candidate")!="NAS100"
        or r.get("actual_provider_symbol")!="USTEC"
        or r.get("provider")!="ICMARKETS_CTRADER_DEMO"
        or r.get("complete_windows")!=3
        or r.get("source_state")!="USTEC_SOURCE_THREE_WINDOWS_AVAILABLE_ALIAS_UNVERIFIED_NOT_NET"
        or r.get("current_symbol_id_exact_match") is not True
        or r.get("nas100_original_CIBO_contract_equivalence_verified") is not False
        or r.get("historical_NET_authorized") is not False
        or r.get("order_submission_count")!=0):
        raise ValueError("G1_USTEC_PROVENANCE_OR_SAFETY_MISMATCH")
    return {"provider_symbol":"USTEC","provider_symbol_id":r["provider_symbol_id_pinned"]}


def current_ustec_details(folder:Path)->dict:
    expected=folder/"nas100-ustec-source-NOT-CONTRACT-PROOF.json"
    if set(x.name for x in folder.iterdir() if x.is_file())!={expected.name}:
        raise ValueError("G1_USTEC_CONTRACT_PREFLIGHT_FILES_MISMATCH")
    d=json.loads(expected.read_bytes())
    if (d.get("canonical")!="NAS100"
        or d.get("alias_equivalence_verified") is not False
        or d.get("historical_execution_contract_verified") is not False
        or d.get("NET_authorized") is not False
        or d.get("trade_orders_submitted")!=0):
        raise ValueError("G1_USTEC_CONTRACT_PREFLIGHT_INVALID")
    spec=d["current_demo_symbol_metadata"]["USTEC"]
    if (d.get("catalog_exact_candidates",{}).get("USTEC")!=10014
        or spec.get("symbol_id")!=10014):
        raise ValueError("G1_USTEC_CONTRACT_CATALOG_ID_DRIFT")
    for k in ("digits","pipPosition","lotSize","minVolume","stepVolume"):
        _int(spec.get(k),"USTEC_"+k.upper())
    return spec


def reconcile(root:Path)->dict:
    old=original_g0(root/"g0")
    spec=current_ustec_details(root/"current-ustec-spec")
    rows=[]
    for canonical in sorted(ORIGINAL12):
        if canonical=="NAS100":
            source=g1_ustec(root/"g1-ustec")
        elif canonical in ("SP500","XAGUSD"):
            source=g1_crossasset(root/("g1-us500" if canonical=="SP500" else "g1-xagusd"),canonical)
        else:
            source=g1_29(root/"g1-29",canonical)
        provider=source.get("provider_symbol")
        number=_int(source.get("provider_symbol_id"),"CURRENT_SYMBOL_ID")
        e=old[canonical]
        if e["g0_provider_symbol"]!=provider or e["g0_symbol_id"]!=number:
            raise ValueError("BROKER_PROVIDER_SYMBOL_OR_NUMERIC_ID_CONCORDANCE_FAIL")
        row={
            "canonical_symbol":canonical,
            "g0_historical_provider_symbol":e["g0_provider_symbol"],
            "g1_current_provider_symbol":provider,
            "g0_historical_symbol_id":e["g0_symbol_id"],
            "g1_current_symbol_id":number,
            "g0_historical_digits":e["g0_digits"],
            "g0_historical_pip_position":e["g0_pip_position"],
            "g0_historical_year_partitions_sha_verified":e["g0_source_partitions"],
            "provider_name_and_numeric_id_concordant":True,
            "original_G0_account_identity_or_broker_proven_same_as_G1":False,
            "lot_tickvalue_currency_commission_swap_sessions_historic_equivalent":False,
            "contract_gate":"UNHOMOLOGATED_BROKER_EXECUTION_CONTRACT",
            "NET_authorized":False,
        }
        if canonical=="NAS100":
            row.update({
                "g1_current_digits_readonly":spec["digits"],
                "g1_current_pip_position_readonly":spec["pipPosition"],
                "g1_current_lot_size_readonly":spec["lotSize"],
                "g1_current_min_volume_readonly":spec["minVolume"],
                "g1_current_step_volume_readonly":spec["stepVolume"],
                "g0_g1_digits_and_pip_position_concordant_only":(
                    e["g0_digits"]==spec["digits"]
                    and e["g0_pip_position"]==spec["pipPosition"]
                ),
            })
            if not row["g0_g1_digits_and_pip_position_concordant_only"]:
                raise ValueError("G1_USTEC_ORIGINAL_PRICE_PRECISION_DIVERGENCE")
        rows.append(row)
    return {
        "identity":IDENTITY,
        "status":"G0_G1_12_NATIVE_PROVIDER_NAME_AND_ID_CONCORDANCE_PASS_NOT_CONTRACT_NET",
        "source_G0_aggregate_run":G0_RUN,
        "source_G0_original_commit":G0_HEAD,
        "original_CIBO_12_per_year_provider_metadata_verified":True,
        "g0_and_g1_provider_symbol_name_and_id_same_count":len(rows),
        "total_g0_historical_year_partitions_sha_verified":sum(x["g0_historical_year_partitions_sha_verified"] for x in rows),
        "g0_g1_account_identity_proven":False,
        "g0_g1_historic_execution_contracts_proven":False,
        "nas100_to_ustec_broker_execution_contract_certified":False,
        "sp500_to_us500_broker_execution_contract_certified":False,
        "current_cTrader_broker_read_requests_this_test":0,
        "historical_execution_NET_authorized":False,
        "traders_certified":0,
        "source_artifact_zip_sha_register":SOURCE_DIGESTS,
        "rows":rows,
    }


def main()->None:
    cli=argparse.ArgumentParser()
    cli.add_argument("downloaded_source_root",type=Path)
    cli.add_argument("output_report_dir",type=Path)
    args=cli.parse_args()
    report=reconcile(args.downloaded_source_root)
    args.output_report_dir.mkdir(parents=True,exist_ok=True)
    out=args.output_report_dir/"QORE_G0_G1_ORIGINAL12_PROVIDER_ID_SOURCE_CONCORDANCE_NOT_CONTRACT_NET.json"
    out.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    (args.output_report_dir/"SHA256SUMS.txt").write_text(
        sha(out.read_bytes())+"  "+out.name+"\n"
    )
    print(json.dumps({
        "status":report["status"],
        "12_provider_symbols_and_ids_concordant":report["g0_and_g1_provider_symbol_name_and_id_same_count"],
        "G0_original_year_partitions_checked":report["total_g0_historical_year_partitions_sha_verified"],
        "broker_contracts_equivalent":False,"NET":False,"certified_traders":0,
    },sort_keys=True))


if __name__=="__main__":
    main()
