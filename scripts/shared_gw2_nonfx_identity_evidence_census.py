#!/usr/bin/env python3
"""Exact real-provider identity census for GW-2 non-FX observed families."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, cast

from shared_global_multi_asset_provider_capability_audit import _family_matches

IDENTITY="QORE_SHARED_GW2_NONFX_IDENTITY_EVIDENCE_CENSUS_001"
EXPECTED_PROVIDER_IDENTITY="QORE_SHARED_GEN2_CTRADER_PROVIDER_SCHEDULE_CATALOG_001"
TARGET_FAMILIES=(
    "EQUITY_INDICES",
    "METALS",
    "ENERGY",
)
EXPECTED_COUNTS={
    "EQUITY_INDICES":25,
    "METALS":16,
    "ENERGY":3,
}


def _sha(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value,sort_keys=True,separators=(",",":")).encode()
    ).hexdigest()


def run(*, provider_schedule: Path, output: Path) -> dict[str,object]:
    p=json.loads(provider_schedule.read_text())
    if p.get("identity") != EXPECTED_PROVIDER_IDENTITY:
        raise ValueError("unexpected provider schedule identity")
    raw=p.get("symbols")
    if not isinstance(raw,list):
        raise ValueError("provider symbols missing")

    families=[]
    for family in TARGET_FAMILIES:
        rows=[]
        for source in raw:
            if not isinstance(source,dict):
                continue
            row=cast(dict[str,Any],source)
            if not _family_matches(family, cast(dict[str, object], row)):
                continue
            rows.append({
                "provider":row.get("provider"),
                "provider_symbol_id":row.get("provider_symbol_id"),
                "provider_symbol":row.get("provider_symbol"),
                "provider_native_symbol_name":row.get("provider_native_symbol_name"),
                "provider_description":row.get("provider_description"),
                "provider_asset_class_name":row.get("provider_asset_class_name"),
                "provider_symbol_category_name":row.get("provider_symbol_category_name"),
                "provider_base_asset_name":row.get("provider_base_asset_name"),
                "provider_quote_asset_name":row.get("provider_quote_asset_name"),
                "underlying_canonical_identity_verified":False,
                "product_construction_verified":False,
                "contract_or_reference_semantics_verified":False,
                "provider_symbol_is_canonical_identity":False,
            })
        rows.sort(key=lambda row:(str(row["provider_symbol"]),int(row["provider_symbol_id"])))
        if len(rows)!=EXPECTED_COUNTS[family]:
            raise ValueError(
                f"{family} expected {EXPECTED_COUNTS[family]} rows, got {len(rows)}"
            )
        families.append({
            "family":family,
            "sensor_count":len(rows),
            "records":rows,
        })

    payload={
        "identity":IDENTITY,
        "status":"REAL_PROVIDER_NONFX_IDENTITY_EVIDENCE_CENSUS",
        "provider_schedule_fingerprint_sha256":p[
            "provider_schedule_catalog_fingerprint_sha256"
        ],
        "families":families,
        "total_sensor_count":sum(row["sensor_count"] for row in families),
        "underlying_canonical_identity_verified_count":0,
        "product_construction_verified_count":0,
        "contract_or_reference_semantics_verified_count":0,
        "provider_symbol_is_canonical_identity":False,
        "automatic_identity_inference":False,
        "historical_market_data_read":False,
        "target_or_outcome_read":False,
        "protected_holdout_opened":False,
        "productive_authority":False,
    }
    payload["census_fingerprint_sha256"]=_sha(payload)
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(payload,sort_keys=True,indent=2)+"\n")
    return cast(dict[str,object],payload)


def main() -> None:
    parser=argparse.ArgumentParser()
    parser.add_argument("--provider-schedule",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    p=run(provider_schedule=args.provider_schedule,output=args.output)
    print(json.dumps({
        "status":p["status"],
        "total_sensor_count":p["total_sensor_count"],
        "families":[
            {
                "family":row["family"],
                "sensor_count":row["sensor_count"],
                "symbols":[item["provider_symbol"] for item in row["records"]],
            }
            for row in p["families"]
        ],
    },sort_keys=True))


if __name__=="__main__":
    main()
