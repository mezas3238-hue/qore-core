"""Metadata-only evidence preserving 33 ORIGINAL source artifacts before expiry.

No source ZIP bytes, no price/outcome/trading/credentials, no raw public backup.
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from qore.research.alpha2_intermarket import MARKETS

ORIGINAL12=(
    "AUDJPY","AUDUSD","EURUSD","GBPJPY","GBPUSD","NAS100","SP500",
    "US30","USDCAD","USDJPY","XAGUSD","XAUUSD",
)
NEW21=tuple(sorted(set(MARKETS)-set(ORIGINAL12)))
ATLAS_RUN=35166210458
NEW21_RUN=38193802541
SOURCE33_RUN=38207337960
HEADS={
    ATLAS_RUN:"ab782b8e9f890f86a2b6500070f0556b4b685e3d",
    NEW21_RUN:"e0ca5a13c866a19d8505c68cffc473598984b340",
    SOURCE33_RUN:"dba0e0c3b61e430d3ed51abab562ebd92060a0ff",
}
ATLAS_PREFIX="qore-cibo-market-atlas-10y-windowed-"
NEW21_PREFIX="qore-native-icmarkets-10Y-provider-M5-"
SIGNED33_PREFIX="qore-native-final33-source-manifest-"
IDENTITY="QORE_ALPHA2_P0_ORIGINAL33_GITHUB_ARTIFACT_EXPIRY_VAULT_READINESS_V1"
HASH=re.compile(r"sha256:[a-f0-9]{64}\Z")


def _at(value:Any)->datetime:
    if type(value) is not str:
        raise ValueError("GITHUB_ARTIFACT_TIME_NOT_PRESENT")
    try:
        d=datetime.fromisoformat(value.replace("Z","+00:00"))
    except ValueError:
        raise ValueError("GITHUB_ARTIFACT_TIME_INVALID") from None
    if d.utcoffset()!=timedelta(0):
        raise ValueError("GITHUB_ARTIFACT_TIME_NOT_UTC")
    return d


def _run_meta(data:dict,run_id:int)->None:
    if (data.get("id")!=run_id or
            data.get("head_sha")!=HEADS[run_id] or
            data.get("conclusion")!="success" or
            data.get("status")!="completed"):
        raise ValueError("GITHUB_ORIGINAL_RUN_HEAD_OR_SUCCESS_DRIFT")


def _artifacts(data:dict,run_id:int,now:datetime)->dict[str,dict]:
    rows=data.get("artifacts")
    if (not isinstance(rows,list)
            or data.get("total_count")!=len(rows)):
        raise ValueError("GITHUB_ORIGINAL_ARCHIVE_LIST_INCOMPLETE")
    found={}
    ids=set()
    for a in rows:
        name=a.get("name")
        if type(name) is not str or not name or name in found:
            raise ValueError("GITHUB_ORIGINAL_SOURCE_ARTIFACT_DUPLICATE")
        aid=a.get("id")
        byte_count=a.get("size_in_bytes")
        digest=a.get("digest")
        if (type(aid) is not int or aid<=0 or aid in ids
                or type(byte_count) is not int or byte_count<=0
                or type(digest) is not str or HASH.fullmatch(digest) is None
                or a.get("expired") is not False):
            raise ValueError("GITHUB_ORIGINAL_ARTIFACT_MISSING_SHA_OR_EXPIRED")
        start,end=_at(a.get("created_at")),_at(a.get("expires_at"))
        if not start < end or end<=now:
            raise ValueError("GITHUB_ORIGINAL_ARTIFACT_ALREADY_UNAVAILABLE")
        ids.add(aid)
        found[name]={
            "name":name,"run_id":run_id,"id":aid,
            "zip_sha256_from_github":digest,"bytes":byte_count,
            "expires_at_utc":end.isoformat(),
            "days_remaining":round((end-now).total_seconds()/86400,3),
        }
    return found


def audit(
    metadata:dict[int,dict],
    run_metadata:dict[int,dict],
    *,
    now:datetime,
)->dict:
    if (set(metadata)!=set(HEADS)
            or set(run_metadata)!=set(HEADS)
            or now.utcoffset()!=timedelta(0)
            or len(ORIGINAL12)!=12 or len(NEW21)!=21
            or set(ORIGINAL12).intersection(NEW21)
            or set(ORIGINAL12).union(NEW21)!=set(MARKETS)):
        raise ValueError("G0_ORIGINAL33_ROSTER_RUN_OR_UTC_DRIFT")
    for rid in HEADS:
        _run_meta(run_metadata[rid],rid)
    archives={rid:_artifacts(metadata[rid],rid,now) for rid in HEADS}
    atlas={
        symbol:ATLAS_PREFIX+symbol+"-"+HEADS[ATLAS_RUN]
        for symbol in ORIGINAL12
    }
    original_aggregate=ATLAS_PREFIX+"aggregate-"+HEADS[ATLAS_RUN]
    newly={
        symbol:NEW21_PREFIX+symbol+"-"+HEADS[NEW21_RUN]
        for symbol in NEW21
    }
    manifest=SIGNED33_PREFIX+HEADS[SOURCE33_RUN]
    for name in list(atlas.values())+[original_aggregate]:
        if name not in archives[ATLAS_RUN]:
            raise ValueError("G0_ORIGINAL_ATLAS12_AND_AGGREGATE_NOT_COMPLETE")
    for name in newly.values():
        if name not in archives[NEW21_RUN]:
            raise ValueError("G0_ORIGINAL_NEW21_M5_NOT_COMPLETE")
    if manifest not in archives[SOURCE33_RUN]:
        raise ValueError("G0_SOURCE33_SIGNED_METADATA_NOT_PRESERVED")
    per_market={
        symbol:archives[ATLAS_RUN][name] for symbol,name in sorted(atlas.items())
    } | {
        symbol:archives[NEW21_RUN][name] for symbol,name in sorted(newly.items())
    }
    if len(per_market)!=33:
        raise ValueError("SOURCE33_ARTIFACT_MARKET_DUPLICATE")
    atlas_earliest=min(_at(x["expires_at_utc"]) for x in
                      [archives[ATLAS_RUN][n] for n in atlas.values()])
    new21_earliest=min(_at(x["expires_at_utc"]) for x in
                      [archives[NEW21_RUN][n] for n in newly.values()])
    first=min(atlas_earliest,new21_earliest)
    remaining=(first-now).total_seconds()/86400
    level=(
        "SOURCE_UNAVAILABLE" if remaining<=0 else
        "P0_CRITICAL_SOURCE_EXPIRY" if remaining<30 else
        "P0_ARCHIVE_VAULT_LICENSE_AND_RESTORE_BEFORE_EXPIRY"
        if remaining<75 else "SOURCE33_ARTIFACT_TIME_LEFT_TRACK_EXPIRY"
    )
    by_cohort={
        "ATLAS_ORIGINAL12":{
            "original_m5_markets":12,
            "archive_bytes":sum(per_market[x]["bytes"] for x in ORIGINAL12),
            "earliest_expiry_utc":atlas_earliest.isoformat(),
            "aggregate_sha":archives[ATLAS_RUN][original_aggregate][
                "zip_sha256_from_github"],
        },
        "ICMARKETS_NEW21":{
            "original_m5_markets":21,
            "archive_bytes":sum(per_market[x]["bytes"] for x in NEW21),
            "earliest_expiry_utc":new21_earliest.isoformat(),
        },
    }
    extras={
        str(rid):sorted(set(archives[rid])-(
            set(atlas.values())|{original_aggregate} if rid==ATLAS_RUN else
            set(newly.values()) if rid==NEW21_RUN else {manifest}
        ))
        for rid in HEADS
    }
    return {
        "identity":IDENTITY,"status":level,
        "as_of_utc":now.isoformat(),
        "original_code_heads":{str(rid):sha for rid,sha in HEADS.items()},
        "original_source_manifest_sha256":
            archives[SOURCE33_RUN][manifest]["zip_sha256_from_github"],
        "original_source_33_sha256_previously_frozen":
            "1291d5c2efb4e51c2698ea25ad420a01a213dc405b5070c37efbce4131606b85",
        "original_m5_source_markets_verified":len(per_market),
        "original12_aggregate_manifest_available":True,
        "per_original_market_artifact_ids_digests_expiry":per_market,
        "total_compressed_original33_m5_bytes":
            sum(x["bytes"] for x in per_market.values()),
        "total_compressed_original33_m5_megabytes":
            round(sum(x["bytes"] for x in per_market.values())/1e6,3),
        "cohorts":by_cohort,
        "earliest_original_m5_expiry_utc":first.isoformat(),
        "minimum_days_until_expiry":round(remaining,3),
        "extra_non_primary_artifacts_per_run_metadata_only":extras,
        "authorized_private_durable_vault_backup_verified":False,
        "broker_data_redistribution_license_verified":False,
        "archive_restore_rehearsal_verified":False,
        "public_GitHub_repository_raw_prices_uploaded":False,
        "OHLC_or_2026_held_bidask_quote_values_read":False,
        "trade_orders_sent":0,
        "Alpha2_traders_certified":0,
        "gross_methods_W1_W2_W3_frozen":True,
        "UTC001_certified":False,
    }


def main()->None:
    parser=argparse.ArgumentParser()
    parser.add_argument("github_api_metadata",type=Path)
    parser.add_argument("output",type=Path)
    args=parser.parse_args()
    data={}
    runs={}
    for rid in HEADS:
        p=args.github_api_metadata
        data[rid]=json.loads((p/f"artifacts-run-{rid}.json").read_text(encoding="utf-8"))
        runs[rid]=json.loads((p/f"run-{rid}.json").read_text(encoding="utf-8"))
    result=audit(data,runs,now=datetime.now(UTC))
    args.output.mkdir(parents=True,exist_ok=True)
    target=args.output/"alpha2-source33-github-artifact-expiry-digest-inventory.json"
    target.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({
        "status":result["status"],
        "market_archives":result["original_m5_source_markets_verified"],
        "megabytes":result["total_compressed_original33_m5_megabytes"],
        "first_expiry":result["earliest_original_m5_expiry_utc"],
        "days_until_expiry":result["minimum_days_until_expiry"],
        "licensed_vault_proven":False,
        "new_orders":0,
    },sort_keys=True))


if __name__=="__main__":
    main()
