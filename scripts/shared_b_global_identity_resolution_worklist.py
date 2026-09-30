"""Build an exact 177-sensor Architect-B identity resolution worklist."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, cast

IDENTITY = "SHARED_B_GLOBAL_IDENTITY_RESOLUTION_WORKLIST_001"
EXPECTED_PROVIDER_IDENTITY = (
    "QORE_SHARED_GEN2_CTRADER_PROVIDER_SCHEDULE_CATALOG_001"
)
EXPECTED_FX_IDENTITY = "SHARED_B_GW2_FX_PROVIDER_REFERENCE_MAPPING_001"
EXPECTED_COMMODITY_IDENTITY = (
    "SHARED_B_COMMODITY_OBSERVATION_IDENTITY_PACK_001"
)


class SharedBIdentityWorklistError(ValueError):
    """Identity resolution census failed closed."""


def _load(path: Path) -> dict[str, Any]:
    payload=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload,dict):
        raise SharedBIdentityWorklistError(f"{path} must contain object")
    return cast(dict[str,Any],payload)


def _sha(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",",":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()


def run(
    *,
    provider_schedule_path: Path,
    fx_mapping_path: Path,
    commodity_pack_path: Path,
    output_path: Path,
) -> dict[str,object]:
    provider=_load(provider_schedule_path)
    fx=_load(fx_mapping_path)
    commodity=_load(commodity_pack_path)

    if provider.get("identity") != EXPECTED_PROVIDER_IDENTITY:
        raise SharedBIdentityWorklistError("unexpected provider schedule")
    if fx.get("identity") != EXPECTED_FX_IDENTITY:
        raise SharedBIdentityWorklistError("unexpected FX mapping")
    if commodity.get("identity") != EXPECTED_COMMODITY_IDENTITY:
        raise SharedBIdentityWorklistError("unexpected commodity pack")

    symbols=provider.get("symbols")
    fx_rows=fx.get("mappings")
    commodity_rows=commodity.get("records")
    if not isinstance(symbols,list) or len(symbols) != 177:
        raise SharedBIdentityWorklistError("expected exact 177 provider symbols")
    if not isinstance(fx_rows,list) or len(fx_rows) != 60:
        raise SharedBIdentityWorklistError("expected exact 60 FX mappings")
    if not isinstance(commodity_rows,list) or len(commodity_rows) != 19:
        raise SharedBIdentityWorklistError("expected exact 19 commodity rows")

    fx_by_key: dict[tuple[str,int],dict[str,object]]={}
    for row_any in fx_rows:
        if not isinstance(row_any,dict):
            raise SharedBIdentityWorklistError("FX row invalid")
        row=cast(dict[str,object],row_any)
        provider_name=row.get("provider")
        symbol_id=row.get("provider_symbol_id")
        if not isinstance(provider_name,str) or type(symbol_id) is not int:
            raise SharedBIdentityWorklistError("FX provider key invalid")
        key=(provider_name,symbol_id)
        if key in fx_by_key:
            raise SharedBIdentityWorklistError("duplicate FX provider key")
        fx_by_key[key]=row

    commodity_by_key: dict[tuple[str,int],dict[str,object]]={}
    for row_any in commodity_rows:
        if not isinstance(row_any,dict):
            raise SharedBIdentityWorklistError("commodity row invalid")
        row=cast(dict[str,object],row_any)
        provider_name=row.get("provider")
        symbol_id=row.get("provider_symbol_id")
        if not isinstance(provider_name,str) or type(symbol_id) is not int:
            raise SharedBIdentityWorklistError("commodity provider key invalid")
        key=(provider_name,symbol_id)
        if key in commodity_by_key:
            raise SharedBIdentityWorklistError(
                "duplicate commodity provider key"
            )
        commodity_by_key[key]=row

    overlap=set(fx_by_key) & set(commodity_by_key)
    if overlap:
        raise SharedBIdentityWorklistError(
            "FX/commodity identity populations overlap"
        )

    records: list[dict[str,object]]=[]
    source_keys: set[tuple[str,int]]=set()
    for row_any in symbols:
        if not isinstance(row_any,dict):
            raise SharedBIdentityWorklistError("provider symbol row invalid")
        row=cast(dict[str,object],row_any)
        provider_name=row.get("provider")
        symbol_id=row.get("provider_symbol_id")
        symbol=row.get("provider_symbol")
        if (
            not isinstance(provider_name,str)
            or type(symbol_id) is not int
            or not isinstance(symbol,str)
        ):
            raise SharedBIdentityWorklistError(
                "provider symbol identity invalid"
            )
        key=(provider_name,symbol_id)
        if key in source_keys:
            raise SharedBIdentityWorklistError(
                "duplicate provider symbol identity"
            )
        source_keys.add(key)

        fx_row=fx_by_key.get(key)
        commodity_row=commodity_by_key.get(key)
        missing: tuple[str, ...]
        if fx_row is not None:
            if fx_row.get("provider_symbol") != symbol:
                raise SharedBIdentityWorklistError("FX provider symbol drift")
            observation_identity=fx_row.get("reference_key")
            resolution_stage="CURRENT_REFERENCE_OBJECT_MAPPED"
            evidence_kind="FX_REFERENCE_OBJECT"
            canonical_tradable_verified=False
            missing=(
                "TRADABLE_PRODUCT_IDENTITY",
                "LISTING_IDENTITY",
                "CANONICAL_CALENDAR_BINDING",
                "HISTORICAL_PRE_FREEZE_MAPPING",
            )
        elif commodity_row is not None:
            if commodity_row.get("provider_symbol") != symbol:
                raise SharedBIdentityWorklistError(
                    "commodity provider symbol drift"
                )
            observation_identity=commodity_row.get("observation_identity")
            kind=commodity_row.get("identity_kind")
            evidence_kind=str(kind)
            dated_verified=(
                commodity_row.get("dated_contract_identity_verified") is True
            )
            if dated_verified:
                resolution_stage="DATED_CONTRACT_DESCRIPTOR_VERIFIED"
                canonical_tradable_verified=True
                missing=(
                    "FRONT_CONTRACT_POLICY",
                    "ROLL_SEMANTICS",
                    "CONTINUOUS_SERIES_IDENTITY",
                    "CANONICAL_CALENDAR_BINDING",
                    "HISTORICAL_PRE_FREEZE_MAPPING",
                )
            else:
                resolution_stage="CURRENT_REFERENCE_OBJECT_MAPPED"
                canonical_tradable_verified=False
                missing=(
                    "TRADABLE_PRODUCT_IDENTITY",
                    "LISTING_IDENTITY",
                    "CANONICAL_CALENDAR_BINDING",
                    "HISTORICAL_PRE_FREEZE_MAPPING",
                )
        else:
            observation_identity=None
            resolution_stage="PROVIDER_NATIVE_ONLY"
            evidence_kind="NONE"
            canonical_tradable_verified=False
            missing=(
                "CANONICAL_ECONOMIC_IDENTITY",
                "TRADABLE_PRODUCT_OR_REFERENCE_IDENTITY",
                "LISTING_OR_MARKET_STRUCTURE",
                "CANONICAL_CALENDAR_BINDING",
                "HISTORICAL_PRE_FREEZE_MAPPING",
            )

        records.append({
            "provider":provider_name,
            "provider_symbol_id":symbol_id,
            "provider_symbol":symbol,
            "provider_asset_class_name":row.get(
                "provider_asset_class_name"
            ),
            "provider_symbol_category_name":row.get(
                "provider_symbol_category_name"
            ),
            "provider_description":row.get("provider_description"),
            "provider_base_asset_name":row.get(
                "provider_base_asset_name"
            ),
            "provider_quote_asset_name":row.get(
                "provider_quote_asset_name"
            ),
            "observation_identity":observation_identity,
            "identity_evidence_kind":evidence_kind,
            "resolution_stage":resolution_stage,
            "canonical_tradable_identity_verified":(
                canonical_tradable_verified
            ),
            "historical_pre_freeze_mapping_authorized":False,
            "missing_evidence":list(missing),
            "automatic_identity_inference":False,
            "sensor_admission_authorized":False,
            "relational_claims_authorized":False,
            "execution_authority":False,
        })

    resolved_keys = set(fx_by_key) | set(commodity_by_key)
    if resolved_keys - source_keys:
        raise SharedBIdentityWorklistError(
            "sealed identity evidence escaped provider universe"
        )

    records.sort(
        key=lambda item:(
            str(item["provider"]),
            int(cast(int,item["provider_symbol_id"])),
        )
    )
    stage_counts: dict[str,int]={}
    asset_class_counts: dict[str,int]={}
    for row in records:
        stage=str(row["resolution_stage"])
        stage_counts[stage]=stage_counts.get(stage,0)+1
        asset_class=str(row.get("provider_asset_class_name") or "UNKNOWN")
        asset_class_counts[asset_class]=asset_class_counts.get(asset_class,0)+1

    provider_native_only=sum(
        row["resolution_stage"]=="PROVIDER_NATIVE_ONLY"
        for row in records
    )
    mapped_current_reference=sum(
        row["resolution_stage"]=="CURRENT_REFERENCE_OBJECT_MAPPED"
        for row in records
    )
    dated_contracts=sum(
        row["resolution_stage"]=="DATED_CONTRACT_DESCRIPTOR_VERIFIED"
        for row in records
    )
    payload: dict[str,object]={
        "identity":IDENTITY,
        "status":"EXACT_177_SENSOR_IDENTITY_FRONTIER_MATERIALIZED",
        "provider_schedule_fingerprint_sha256":provider.get(
            "provider_schedule_catalog_fingerprint_sha256"
        ),
        "fx_mapping_fingerprint_sha256":fx.get(
            "mapping_fingerprint_sha256"
        ),
        "commodity_pack_fingerprint_sha256":commodity.get(
            "pack_fingerprint_sha256"
        ),
        "sensor_count":len(records),
        "current_reference_mapped_count":mapped_current_reference,
        "dated_contract_descriptor_verified_count":dated_contracts,
        "provider_native_only_count":provider_native_only,
        "canonical_identity_complete_count":0,
        "full_177_identity_complete":False,
        "stage_counts":dict(sorted(stage_counts.items())),
        "provider_asset_class_counts":dict(
            sorted(asset_class_counts.items())
        ),
        "records":records,
        "provider_symbol_name_is_canonical_proof":False,
        "automatic_identity_inference":False,
        "historical_market_data_read":False,
        "target_or_outcome_read":False,
        "r6_r5_read":False,
        "fresh_holdout_opened":False,
        "broker_mutation":False,
        "productive_authority":False,
    }
    payload["worklist_fingerprint_sha256"]=_sha(payload)
    output_path.parent.mkdir(parents=True,exist_ok=True)
    output_path.write_text(
        json.dumps(payload,sort_keys=True,indent=2)+"\n",
        encoding="utf-8",
    )
    return payload


def main() -> None:
    parser=argparse.ArgumentParser()
    parser.add_argument("--provider-schedule",type=Path,required=True)
    parser.add_argument("--fx-mapping",type=Path,required=True)
    parser.add_argument("--commodity-pack",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    payload=run(
        provider_schedule_path=args.provider_schedule,
        fx_mapping_path=args.fx_mapping,
        commodity_pack_path=args.commodity_pack,
        output_path=args.output,
    )
    print(json.dumps({
        "status":payload["status"],
        "sensor_count":payload["sensor_count"],
        "current_reference_mapped_count":payload[
            "current_reference_mapped_count"
        ],
        "dated_contract_descriptor_verified_count":payload[
            "dated_contract_descriptor_verified_count"
        ],
        "provider_native_only_count":payload[
            "provider_native_only_count"
        ],
    },sort_keys=True))


if __name__=="__main__":
    main()
