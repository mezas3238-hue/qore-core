#!/usr/bin/env python3
"""Construct provider-neutral FX reference-object candidates from verified components.

This does not map a broker symbol to a canonical tradable instrument. It creates
only the economic FX pair reference candidate after both currency components
are verified by authoritative ISO 4217 evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

IDENTITY="QORE_SHARED_GW2_FX_REFERENCE_OBJECT_CANDIDATES_001"
EXPECTED_EVIDENCE_ID="QORE_SHARED_GW2_FX_ISO4217_EVIDENCE_001"


def _fingerprint(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value,sort_keys=True,separators=(",",":")).encode()
    ).hexdigest()


def run(*, evidence_path: Path, output: Path) -> dict[str,object]:
    evidence=json.loads(evidence_path.read_text())
    if evidence.get("identity") != EXPECTED_EVIDENCE_ID:
        raise ValueError("unexpected FX ISO4217 evidence identity")

    refs={}
    unresolved=[]
    for row in evidence["pairs"]:
        base=str(row["base_currency_code"])
        quote=str(row["quote_currency_code"])
        if not row["currency_components_verified"]:
            unresolved.append({
                "provider_symbol":row["provider_symbol"],
                "base_currency_code":base,
                "quote_currency_code":quote,
                "reason":"UNVERIFIED_CURRENCY_COMPONENT",
            })
            continue
        key=f"QORE:FX_REFERENCE:{base}/{quote}"
        candidate={
            "reference_key":key,
            "kind":"REFERENCE_OBJECT",
            "family":"FX_PAIR",
            "construction":"COMPOSITE",
            "base_currency_iso4217":base,
            "quote_currency_iso4217":quote,
            "economic_semantics":"ONE_UNIT_BASE_PRICED_IN_QUOTE",
            "provider_neutral":True,
            "tradable_instrument_claim":False,
            "provider_listing_mapping_claim":False,
            "canonical_tradable_identity_verified":False,
            "evidence_refs":[
                evidence["evidence_fingerprint_sha256"],
                evidence["source"]["sha256"],
            ],
        }
        existing=refs.get(key)
        if existing is not None and existing != candidate:
            raise ValueError(f"contradictory FX reference candidate {key}")
        refs[key]=candidate

    rows=[refs[key] for key in sorted(refs)]
    payload={
        "identity":IDENTITY,
        "status":"PROVIDER_NEUTRAL_REFERENCE_OBJECT_CANDIDATES_BUILT",
        "source_evidence_fingerprint":evidence["evidence_fingerprint_sha256"],
        "reference_candidate_count":len(rows),
        "reference_candidates":rows,
        "unresolved_provider_pair_count":len(unresolved),
        "unresolved_provider_pairs":unresolved,
        "provider_symbol_to_reference_mapping_authorized":False,
        "provider_symbol_to_tradable_identity_mapping_authorized":False,
        "canonical_tradable_identity_verified_count":0,
        "historical_market_data_read":False,
        "target_or_outcome_read":False,
        "protected_holdout_opened":False,
        "productive_authority":False,
    }
    payload["registry_fingerprint_sha256"]=_fingerprint(payload)
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(payload,sort_keys=True,indent=2)+"\n")
    return payload


def main() -> None:
    parser=argparse.ArgumentParser()
    parser.add_argument("--evidence",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    p=run(evidence_path=args.evidence,output=args.output)
    print(json.dumps({
        "status":p["status"],
        "reference_candidate_count":p["reference_candidate_count"],
        "unresolved_provider_pair_count":p["unresolved_provider_pair_count"],
    },sort_keys=True))


if __name__=="__main__":
    main()
