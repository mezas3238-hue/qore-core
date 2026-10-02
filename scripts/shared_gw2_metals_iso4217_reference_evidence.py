#!/usr/bin/env python3
"""Bind real provider metal reference components to authoritative ISO 4217.

This lane covers only XAU/XAG/XPT/XPD-style metal-vs-currency references.
GC month/year symbols are excluded and remain in the futures contract lane.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import cast

IDENTITY="QORE_SHARED_GW2_METALS_ISO4217_REFERENCE_EVIDENCE_001"
EXPECTED_CENSUS_IDENTITY="QORE_SHARED_GW2_NONFX_IDENTITY_EVIDENCE_CENSUS_001"
SIX_SOURCE_URL=(
    "https://www.six-group.com/dam/download/financial-information/"
    "data-center/iso-currrency/lists/list-one.xml"
)
METAL_CODES={"XAU","XAG","XPT","XPD"}


def _local(tag: str) -> str:
    return tag.rsplit("}",1)[-1]


def _text_map(element: ET.Element) -> dict[str,str]:
    return {
        _local(child.tag):(child.text or "").strip()
        for child in element
        if (child.text or "").strip()
    }


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(*, census_path: Path, iso_xml_path: Path, output: Path) -> dict[str,object]:
    census=json.loads(census_path.read_text())
    if census.get("identity") != EXPECTED_CENSUS_IDENTITY:
        raise ValueError("unexpected non-FX census identity")

    metals=next(
        row for row in census["families"] if row["family"]=="METALS"
    )
    provider_rows=metals["records"]
    reference_rows=[
        row for row in provider_rows
        if str(row.get("provider_base_asset_name")) in METAL_CODES
    ]
    futures_rows=[
        row for row in provider_rows
        if str(row.get("provider_symbol","")).startswith("GC")
        and row not in reference_rows
    ]
    if len(reference_rows)!=11 or len(futures_rows)!=5:
        raise ValueError(
            f"expected 11 metal references + 5 GC futures, got "
            f"{len(reference_rows)} + {len(futures_rows)}"
        )

    root=ET.parse(iso_xml_path).getroot()
    iso_rows: dict[str,dict[str,str]]={}
    for element in root.iter():
        row=_text_map(element)
        code=row.get("Ccy")
        if code and len(code)==3:
            iso_rows.setdefault(code,row)

    evidence=[]
    unresolved=[]
    for row in reference_rows:
        base=str(row["provider_base_asset_name"])
        quote=str(row["provider_quote_asset_name"])
        base_iso=iso_rows.get(base)
        quote_iso=iso_rows.get(quote)
        verified=base_iso is not None and quote_iso is not None
        item={
            "provider":row["provider"],
            "provider_symbol_id":row["provider_symbol_id"],
            "provider_symbol":row["provider_symbol"],
            "provider_description":row["provider_description"],
            "metal_code":base,
            "quote_currency_code":quote,
            "metal_iso4217_verified":base_iso is not None,
            "quote_iso4217_verified":quote_iso is not None,
            "components_verified":verified,
            "provider_neutral_reference_key":(
                f"QORE:METAL_REFERENCE:{base}/{quote}" if verified else None
            ),
            "provider_symbol_to_reference_mapping_authorized":False,
            "tradable_instrument_identity_verified":False,
        }
        evidence.append(item)
        if not verified:
            unresolved.append(item)

    payload={
        "identity":IDENTITY,
        "status":"AUTHORITATIVE_METAL_COMPONENT_EVIDENCE_BOUND",
        "source":{
            "authority":"SIX_FINANCIAL_INFORMATION_AG",
            "role":"ISO_4217_MAINTENANCE_AGENCY",
            "url":SIX_SOURCE_URL,
            "sha256":_sha256(iso_xml_path),
        },
        "provider_metal_sensor_count":len(provider_rows),
        "metal_reference_sensor_count":len(reference_rows),
        "gold_futures_sensor_count":len(futures_rows),
        "metal_reference_components_verified_count":sum(
            int(row["components_verified"]) for row in evidence
        ),
        "unresolved_reference_count":len(unresolved),
        "reference_evidence":evidence,
        "gold_futures_deferred_symbols":[
            row["provider_symbol"] for row in futures_rows
        ],
        "gold_futures_require_venue_contract_delivery_evidence":True,
        "provider_symbol_to_reference_mapping_authorized":False,
        "tradable_instrument_identity_verified_count":0,
        "historical_market_data_read":False,
        "target_or_outcome_read":False,
        "protected_holdout_opened":False,
        "productive_authority":False,
    }
    raw=json.dumps(payload,sort_keys=True,separators=(",",":"))
    payload["evidence_fingerprint_sha256"]=hashlib.sha256(raw.encode()).hexdigest()
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(payload,sort_keys=True,indent=2)+"\n")
    return cast(dict[str,object],payload)


def main() -> None:
    parser=argparse.ArgumentParser()
    parser.add_argument("--census",type=Path,required=True)
    parser.add_argument("--iso-xml",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    p=run(census_path=args.census,iso_xml_path=args.iso_xml,output=args.output)
    print(json.dumps({
        "status":p["status"],
        "metal_reference_sensor_count":p["metal_reference_sensor_count"],
        "metal_reference_components_verified_count":p[
            "metal_reference_components_verified_count"
        ],
        "gold_futures_deferred_symbols":p["gold_futures_deferred_symbols"],
    },sort_keys=True))


if __name__=="__main__":
    main()
