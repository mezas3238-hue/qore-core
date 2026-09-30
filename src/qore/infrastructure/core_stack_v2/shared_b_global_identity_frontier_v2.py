"""Architect-B 177-sensor identity frontier V2.

Reconciles the sealed B-06 frontier with the sealed provider-attested economic
identity boundary. This advances epistemic resolution for the exact 98 index
and cryptocurrency sensors without promoting provider metadata to canonical or
provider-neutral identity.
"""

from __future__ import annotations

import hashlib
import json
from typing import cast

IDENTITY = "SHARED_B_GLOBAL_IDENTITY_FRONTIER_V2_001"
EXPECTED_FRONTIER_IDENTITY = "SHARED_B_GLOBAL_IDENTITY_RESOLUTION_WORKLIST_001"
EXPECTED_ATTESTED_IDENTITY = (
    "SHARED_B_PROVIDER_ATTESTED_ECONOMIC_IDENTITY_BOUNDARY_001"
)


class SharedBIdentityFrontierV2Error(ValueError):
    """Identity frontier reconciliation failed closed."""


def _fingerprint(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()


def build_identity_frontier_v2(
    *,
    frontier_v1: dict[str, object],
    provider_attested: dict[str, object],
) -> dict[str, object]:
    if frontier_v1.get("identity") != EXPECTED_FRONTIER_IDENTITY:
        raise SharedBIdentityFrontierV2Error("unexpected frontier v1 identity")
    if provider_attested.get("identity") != EXPECTED_ATTESTED_IDENTITY:
        raise SharedBIdentityFrontierV2Error(
            "unexpected provider-attested identity"
        )
    if frontier_v1.get("sensor_count") != 177:
        raise SharedBIdentityFrontierV2Error("frontier v1 is not exact 177")
    if provider_attested.get("sensor_count") != 98:
        raise SharedBIdentityFrontierV2Error(
            "provider-attested boundary is not exact 98"
        )
    if provider_attested.get(
        "provider_neutral_reference_identity_verified_count"
    ) != 0:
        raise SharedBIdentityFrontierV2Error(
            "provider-attested evidence widened provider-neutral authority"
        )
    if provider_attested.get(
        "canonical_economic_identity_verified_count"
    ) != 0:
        raise SharedBIdentityFrontierV2Error(
            "provider-attested evidence widened canonical authority"
        )

    old_records = frontier_v1.get("records")
    attested_records = provider_attested.get("records")
    if not isinstance(old_records, list) or len(old_records) != 177:
        raise SharedBIdentityFrontierV2Error("frontier v1 records invalid")
    if not isinstance(attested_records, list) or len(attested_records) != 98:
        raise SharedBIdentityFrontierV2Error(
            "provider-attested records invalid"
        )

    attested_by_key: dict[tuple[str, int], dict[str, object]] = {}
    for raw in attested_records:
        if not isinstance(raw, dict):
            raise SharedBIdentityFrontierV2Error("attested row invalid")
        row = cast(dict[str, object], raw)
        provider = row.get("provider")
        symbol_id = row.get("provider_symbol_id")
        if not isinstance(provider, str) or type(symbol_id) is not int:
            raise SharedBIdentityFrontierV2Error("attested key invalid")
        key = (provider, symbol_id)
        if key in attested_by_key:
            raise SharedBIdentityFrontierV2Error("duplicate attested key")
        if row.get("identity_stage") != "PROVIDER_ATTESTED_ECONOMIC_OBJECT":
            raise SharedBIdentityFrontierV2Error(
                "unexpected attested identity stage"
            )
        for forbidden in (
            "provider_neutral_reference_identity_verified",
            "canonical_economic_identity_verified",
            "tradable_product_identity_verified",
            "listing_identity_verified",
            "canonical_calendar_binding_verified",
            "historical_pre_freeze_mapping_authorized",
            "sensor_admission_authorized",
            "relational_claims_authorized",
            "execution_authority",
        ):
            if row.get(forbidden) is not False:
                raise SharedBIdentityFrontierV2Error(
                    f"attested authority widening: {forbidden}"
                )
        attested_by_key[key] = row

    new_records: list[dict[str, object]] = []
    transformed_keys: set[tuple[str, int]] = set()
    source_keys: set[tuple[str, int]] = set()
    for raw in old_records:
        if not isinstance(raw, dict):
            raise SharedBIdentityFrontierV2Error("frontier v1 row invalid")
        row = cast(dict[str, object], raw)
        provider = row.get("provider")
        symbol_id = row.get("provider_symbol_id")
        if not isinstance(provider, str) or type(symbol_id) is not int:
            raise SharedBIdentityFrontierV2Error("frontier v1 key invalid")
        key = (provider, symbol_id)
        if key in source_keys:
            raise SharedBIdentityFrontierV2Error("duplicate frontier v1 key")
        source_keys.add(key)

        if row.get("resolution_stage") != "PROVIDER_NATIVE_ONLY":
            if key in attested_by_key:
                raise SharedBIdentityFrontierV2Error(
                    "attested evidence overlaps already-resolved sensor"
                )
            new_records.append(dict(row))
            continue

        attested = attested_by_key.get(key)
        if attested is None:
            raise SharedBIdentityFrontierV2Error(
                "provider-native sensor lacks attested evidence"
            )
        if row.get("provider_symbol") != attested.get("provider_symbol"):
            raise SharedBIdentityFrontierV2Error("provider symbol drift")
        if row.get("provider_description") != attested.get(
            "provider_description"
        ):
            raise SharedBIdentityFrontierV2Error("provider description drift")
        if row.get("provider_asset_class_name") != attested.get(
            "provider_asset_class_name"
        ):
            raise SharedBIdentityFrontierV2Error("provider asset-class drift")

        updated = dict(row)
        updated["resolution_stage"] = "PROVIDER_ATTESTED_ECONOMIC_OBJECT"
        updated["identity_evidence_kind"] = "FROZEN_PROVIDER_METADATA"
        updated["provider_attested_economic_identity_key"] = attested.get(
            "provider_attested_economic_identity_key"
        )
        updated["provider_attested_reference_label"] = attested.get(
            "provider_attested_reference_label"
        )
        updated["provider_neutral_reference_identity_verified"] = False
        updated["canonical_economic_identity_verified"] = False
        updated["provider_metadata_is_canonical_proof"] = False
        updated["symbol_name_similarity_used"] = False
        new_records.append(updated)
        transformed_keys.add(key)

    if transformed_keys != set(attested_by_key):
        raise SharedBIdentityFrontierV2Error(
            "provider-attested population does not exactly match v1 native set"
        )
    if len(transformed_keys) != 98:
        raise SharedBIdentityFrontierV2Error(
            "expected exact 98 provider-native transformations"
        )

    new_records.sort(
        key=lambda item: (
            str(item["provider"]),
            int(cast(int, item["provider_symbol_id"])),
        )
    )
    stage_counts: dict[str, int] = {}
    for row in new_records:
        stage = str(row.get("resolution_stage"))
        stage_counts[stage] = stage_counts.get(stage, 0) + 1

    expected_stage_counts = {
        "CURRENT_REFERENCE_OBJECT_MAPPED": 74,
        "DATED_CONTRACT_DESCRIPTOR_VERIFIED": 5,
        "PROVIDER_ATTESTED_ECONOMIC_OBJECT": 98,
    }
    if stage_counts != expected_stage_counts:
        raise SharedBIdentityFrontierV2Error(
            f"unexpected V2 stage counts: {stage_counts}"
        )

    payload: dict[str, object] = {
        "identity": IDENTITY,
        "status": "EXACT_177_SENSOR_IDENTITY_FRONTIER_V2_MATERIALIZED",
        "sensor_count": len(new_records),
        "current_reference_mapped_count": 74,
        "dated_contract_descriptor_verified_count": 5,
        "provider_attested_economic_object_count": 98,
        "provider_native_only_count": 0,
        "provider_neutral_or_reference_mapped_count": 74,
        "full_canonical_identity_complete_count": 0,
        "full_177_identity_complete": False,
        "stage_counts": stage_counts,
        "records": new_records,
        "frontier_v1_fingerprint_sha256": frontier_v1.get(
            "worklist_fingerprint_sha256"
        ),
        "provider_attested_boundary_fingerprint_sha256": provider_attested.get(
            "boundary_fingerprint_sha256"
        ),
        "provider_metadata_is_canonical_proof": False,
        "automatic_identity_inference": False,
        "historical_pre_freeze_mapping_authorized": False,
        "sensor_admission_authorized": False,
        "relational_claims_authorized": False,
        "historical_market_data_read": False,
        "target_or_outcome_read": False,
        "r6_r5_read": False,
        "fresh_holdout_opened": False,
        "broker_mutation": False,
        "productive_authority": False,
        "b06_complete": False,
    }
    payload["frontier_v2_fingerprint_sha256"] = _fingerprint(payload)
    return payload
