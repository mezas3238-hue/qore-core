#!/usr/bin/env python3
"""Bind GW-2 real FX currency codes to authoritative ISO 4217 List One evidence.

SIX is the official ISO 4217 Maintenance Agency. This script compares only the
exact provider currency-code universe already observed in Core. Absence from
the current authoritative list remains unresolved and is never aliased.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, cast

IDENTITY = "QORE_SHARED_GW2_FX_ISO4217_EVIDENCE_001"
EXPECTED_CENSUS_IDENTITY = "QORE_SHARED_GW2_FX_IDENTITY_EVIDENCE_CENSUS_001"
SIX_SOURCE_URL = (
    "https://www.six-group.com/dam/download/financial-information/"
    "data-center/iso-currrency/lists/list-one.xml"
)


def _local(tag: str) -> str:
    return tag.rsplit("}",1)[-1]


def _text_map(element: ET.Element) -> dict[str,str]:
    return {
        _local(child.tag): (child.text or "").strip()
        for child in element
        if (child.text or "").strip()
    }


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(*, census_path: Path, iso_xml_path: Path, output: Path) -> dict[str,object]:
    census=json.loads(census_path.read_text())
    if census.get("identity") != EXPECTED_CENSUS_IDENTITY:
        raise ValueError("unexpected GW-2 FX census identity")

    provider_codes=census.get("distinct_provider_currency_names")
    if not isinstance(provider_codes,list) or not provider_codes:
        raise ValueError("provider currency universe missing")
    provider_codes=sorted(str(value).strip() for value in provider_codes)

    root=ET.parse(iso_xml_path).getroot()
    iso_rows: dict[str,dict[str,str]]={}
    for element in root.iter():
        row=_text_map(element)
        code=row.get("Ccy")
        if code and len(code)==3:
            iso_rows.setdefault(code,row)

    resolved=[]
    unresolved=[]
    for code in provider_codes:
        row=iso_rows.get(code)
        if row is None:
            unresolved.append({
                "provider_currency_code":code,
                "iso4217_current_verified":False,
                "canonical_alias_inferred":False,
                "resolution":"UNRESOLVED_NOT_PRESENT_IN_CURRENT_ISO4217_LIST_ONE",
            })
            continue
        resolved.append({
            "provider_currency_code":code,
            "iso4217_current_verified":True,
            "iso4217_alphabetic_code":row.get("Ccy"),
            "iso4217_numeric_code":row.get("CcyNbr"),
            "iso4217_currency_name":row.get("CcyNm"),
            "iso4217_entity":row.get("CtryNm"),
            "iso4217_minor_unit":row.get("CcyMnrUnts"),
            "canonical_alias_inferred":False,
            "resolution":"AUTHORITATIVE_ISO4217_CURRENT_CODE_MATCH",
        })

    verified_codes={row["provider_currency_code"] for row in resolved}
    pairs=[]
    for pair in census["pairs"]:
        base=str(pair["base_asset_name"])
        quote=str(pair["quote_asset_name"])
        components_verified=base in verified_codes and quote in verified_codes
        pairs.append({
            "provider":pair["provider"],
            "provider_symbol_id":pair["provider_symbol_id"],
            "provider_symbol":pair["provider_symbol"],
            "base_currency_code":base,
            "quote_currency_code":quote,
            "base_iso4217_verified":base in verified_codes,
            "quote_iso4217_verified":quote in verified_codes,
            "currency_components_verified":components_verified,
            "fx_pair_canonical_identity_verified":False,
            "remaining_obligations":(
                [
                    "PRODUCT_CONSTRUCTION_EVIDENCE",
                    "DISTRIBUTED_OTC_SCOPE_EVIDENCE",
                    "EFFECTIVE_DATED_EXTERNAL_TO_CANONICAL_MAPPING",
                ]
                if components_verified
                else [
                    "UNRESOLVED_CURRENCY_COMPONENT",
                    "PRODUCT_CONSTRUCTION_EVIDENCE",
                    "DISTRIBUTED_OTC_SCOPE_EVIDENCE",
                    "EFFECTIVE_DATED_EXTERNAL_TO_CANONICAL_MAPPING",
                ]
            ),
        })

    payload={
        "identity":IDENTITY,
        "status":"AUTHORITATIVE_ISO4217_COMPONENT_EVIDENCE_BOUND",
        "source":{
            "authority":"SIX_FINANCIAL_INFORMATION_AG",
            "role":"ISO_4217_MAINTENANCE_AGENCY",
            "url":SIX_SOURCE_URL,
            "sha256":_sha256(iso_xml_path),
        },
        "provider_currency_code_count":len(provider_codes),
        "iso4217_verified_currency_code_count":len(resolved),
        "unresolved_currency_code_count":len(unresolved),
        "verified_currency_codes":resolved,
        "unresolved_currency_codes":unresolved,
        "fx_pair_count":len(pairs),
        "fx_pairs_with_all_currency_components_verified":sum(
            int(bool(row["currency_components_verified"])) for row in pairs
        ),
        "pairs":pairs,
        "provider_code_absence_is_not_alias_permission":True,
        "cnh_auto_aliased_to_cny":False,
        "fx_pair_canonical_identity_verified_count":0,
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
        "verified":p["iso4217_verified_currency_code_count"],
        "unresolved":p["unresolved_currency_code_count"],
        "unresolved_currency_codes":p["unresolved_currency_codes"],
        "pairs_with_verified_components":p[
            "fx_pairs_with_all_currency_components_verified"
        ],
    },sort_keys=True))


if __name__=="__main__":
    main()
