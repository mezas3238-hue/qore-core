"""Independent SHA-traced original QORE Native USTEC catalog source, NO NET.

Proof is an already stored immutable GitHub Actions artifact from #38284304699,
not fresh account access and not historical CIBO NAS100/USTEC equivalence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

IDENTITY="QORE_ALPHA2_G2_P0_ORIGINAL_G1_USTEC_CURRENT_DEMO_METADATA_SHA_AUDIT_V1"
SOURCE_ID="QORE_NATIVE_G1_NAS100_USTEC_READONLY_BROKER_ALIAS_PREFLIGHT_V1"
STATUS="USTEC_OLD_PROVIDER_METADATA_SHA_VERIFIED_ONLY_CURRENT_DEMO_NO_NAS100_EQUIVALENCE"
ORIGINAL_RUN=38284304699
HEAD="716996e0f893af0aeb2b990ac11d644cf62a5c5f"
ARTIFACT_ID=11762018327
ARTIFACT_SHA="7f927792e575c5cccb9932c55a8db6733430c34629681701c6acd98491ac5c2e"
SOURCE_FILENAME="nas100-ustec-source-NOT-CONTRACT-PROOF.json"
EXPECTED_SPECS={
    "symbol_id":10014,
    "digits":2,
    "pipPosition":1,
    "lotSize":100,
    "minVolume":10,
    "stepVolume":10,
    "historical_original_CIBO_contract_equivalence_proven":False,
}


def audit(root:Path)->dict[str,Any]:
    if not root.is_dir() or {x.name for x in root.iterdir()}!={SOURCE_FILENAME}:
        raise ValueError("ORIGINAL_850_IMMUTABLE_ONE_FILE_SCOPE_NOT_PROVEN")
    source_file=root/SOURCE_FILENAME
    raw=source_file.read_bytes()
    source=json.loads(raw)
    if (source.get("identity")!=SOURCE_ID
            or source.get("source")!="ICMARKETS_CTRADER_DEMO"
            or source.get("read_only") is not True
            or source.get("canonical")!="NAS100"
            or source.get("historical_alias_hint")!="USTEC"
            or source.get("status")!="USTEC_ALIAS_CANDIDATE_NEEDS_CONTRACT_EQUIVALENCE"
            or source.get("alias_equivalence_verified") is not False
            or source.get("historical_execution_contract_verified") is not False
            or source.get("NET_authorized") is not False
            or source.get("native_bidask_fetched") is not False
            or source.get("trade_orders_submitted")!=0
            or source.get("token_refresh_attempts")!=0
            or source.get("certified_traders")!=0
            or source.get("catalog_exact_candidates")!={"USTEC":10014}):
        raise ValueError("ORIGINAL_850_SOURCE_WITNESS_SCOPE_OR_ALIAS_STATUS_DRIFT")
    details=source.get("current_demo_symbol_metadata",{})
    if not isinstance(details,dict) or set(details)!={"USTEC"}:
        raise ValueError("ORIGINAL_850_USTEC_SOURCE_DETAILS_NOT_ONLY_ALIAS")
    candidate=details["USTEC"]
    if (not isinstance(candidate,dict)
            or set(candidate)!=set(EXPECTED_SPECS)
            or any(type(candidate[k]) is not type(v) or candidate[k]!=v
                   for k,v in EXPECTED_SPECS.items())):
        raise ValueError("ORIGINAL_850_USTEC_RAW_BROKER_SPECS_DIFFER_FROM_SIGNED_PR")
    return {
        "identity":IDENTITY,"status":STATUS,
        "original_immutable_github_actions_run":ORIGINAL_RUN,
        "original_code_head":HEAD,
        "original_artifact_id":ARTIFACT_ID,
        "original_github_zip_sha256":ARTIFACT_SHA,
        "original_manifest_sha256":hashlib.sha256(raw).hexdigest(),
        "original_source_broker_label":"ICMARKETS_CTRADER_DEMO",
        "canonical":"NAS100",
        "current_provider_alias_candidate":"USTEC",
        "source_symbol_id":candidate["symbol_id"],
        "digits":candidate["digits"],
        "pipPosition":candidate["pipPosition"],
        "lotSize_raw_cents":candidate["lotSize"],
        "minVolume_raw":candidate["minVolume"],
        "stepVolume_raw":candidate["stepVolume"],
        "raw_integer_units_NOT_deposit_currency":True,
        "historical_original_CIBO_NAS100_USTEC_contract_equivalent":False,
        "same_account_as_Alpha2_source29_verified":False,
        "historical_2016_2024_broker_contract_verified":False,
        "commission_swap_quote_currency_or_point_value_verified":False,
        "real_execution_price_or_PnL_computed":False,
        "UTC001_certified":False,"orders":0,
    }


def main()->None:
    p=argparse.ArgumentParser()
    p.add_argument("original_artifact",type=Path)
    p.add_argument("output",type=Path)
    args=p.parse_args()
    report=audit(args.original_artifact)
    args.output.mkdir(parents=True,exist_ok=True)
    (args.output/"alpha2-g2-p0-original850-ustec-source-only-qa.json").write_text(
        json.dumps(report,sort_keys=True,indent=2)+"\n",encoding="utf-8"
    )
    print(json.dumps({
        "status":report["status"],
        "alias":report["current_provider_alias_candidate"],
        "provider_symbol_id":report["source_symbol_id"],
        "historical_equivalence":False,
        "orders":0,
    },sort_keys=True))


if __name__=="__main__":
    main()
