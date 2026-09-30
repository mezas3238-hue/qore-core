#!/usr/bin/env python3
"""Extract the real cTrader FX identity evidence census for GW-2.

Provider metadata remains evidence, not canonical identity. This census reduces
the external verification problem to the exact base/quote currency set actually
observed in the sealed 177-sensor provider catalogue.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, cast

IDENTITY = "QORE_SHARED_GW2_FX_IDENTITY_EVIDENCE_CENSUS_001"
EXPECTED_PROVIDER_IDENTITY = "QORE_SHARED_GEN2_CTRADER_PROVIDER_SCHEDULE_CATALOG_001"


def _load(path: Path) -> dict[str, Any]:
    payload=json.loads(path.read_text())
    if not isinstance(payload,dict):
        raise ValueError("provider schedule must be an object")
    return cast(dict[str,Any],payload)


def _sha(payload: object) -> str:
    raw=json.dumps(payload,sort_keys=True,separators=(",",":"))
    return hashlib.sha256(raw.encode()).hexdigest()


def run(*, provider_schedule: Path, output: Path) -> dict[str, object]:
    p=_load(provider_schedule)
    if p.get("identity") != EXPECTED_PROVIDER_IDENTITY:
        raise ValueError("unexpected provider schedule identity")
    rows=p.get("symbols")
    if not isinstance(rows,list):
        raise ValueError("provider symbols missing")

    fx=[
        cast(dict[str,object],row)
        for row in rows
        if isinstance(row,dict)
        and str(row.get("provider_asset_class_name","")).casefold()=="forex"
    ]
    if len(fx) != 60:
        raise ValueError(f"expected 60 provider FX sensors, got {len(fx)}")

    currencies=set()
    unresolved=[]
    pairs=[]
    for row in fx:
        base=row.get("provider_base_asset_name")
        quote=row.get("provider_quote_asset_name")
        symbol=row.get("provider_symbol")
        if not isinstance(base,str) or not base.strip():
            unresolved.append({"provider_symbol":symbol,"missing":"base"})
            continue
        if not isinstance(quote,str) or not quote.strip():
            unresolved.append({"provider_symbol":symbol,"missing":"quote"})
            continue
        currencies.add(base.strip())
        currencies.add(quote.strip())
        pairs.append({
            "provider":row.get("provider"),
            "provider_symbol_id":row.get("provider_symbol_id"),
            "provider_symbol":symbol,
            "provider_native_symbol_name":row.get("provider_native_symbol_name"),
            "base_asset_name":base.strip(),
            "quote_asset_name":quote.strip(),
            "canonical_pair_identity_verified":False,
        })

    pairs.sort(
        key=lambda row: (
            str(row["base_asset_name"]),
            str(row["quote_asset_name"]),
            str(row["provider_symbol"]),
        )
    )
    payload={
        "identity":IDENTITY,
        "status":"REAL_PROVIDER_FX_IDENTITY_EVIDENCE_CENSUS",
        "provider_schedule_fingerprint_sha256":p["provider_schedule_catalog_fingerprint_sha256"],
        "fx_sensor_count":len(fx),
        "pair_descriptor_count":len(pairs),
        "distinct_provider_currency_name_count":len(currencies),
        "distinct_provider_currency_names":sorted(currencies),
        "unresolved_provider_descriptor_count":len(unresolved),
        "unresolved_provider_descriptors":unresolved,
        "pairs":pairs,
        "provider_currency_name_is_iso4217_identity":False,
        "provider_pair_symbol_is_canonical_economic_identity":False,
        "external_currency_identity_evidence_required":True,
        "automatic_identity_inference":False,
        "historical_market_data_read":False,
        "target_or_outcome_read":False,
        "protected_holdout_opened":False,
        "productive_authority":False,
    }
    payload["census_fingerprint_sha256"]=_sha(payload)
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(payload,sort_keys=True,indent=2)+"\n")
    return payload


def main() -> None:
    parser=argparse.ArgumentParser()
    parser.add_argument("--provider-schedule",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    payload=run(provider_schedule=args.provider_schedule,output=args.output)
    print(json.dumps({
        "identity":payload["identity"],
        "fx_sensor_count":payload["fx_sensor_count"],
        "distinct_provider_currency_names":payload["distinct_provider_currency_names"],
        "unresolved_provider_descriptor_count":payload["unresolved_provider_descriptor_count"],
    },sort_keys=True))


if __name__=="__main__":
    main()
