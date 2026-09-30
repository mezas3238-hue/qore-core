"""Architect-B 177-sensor identity frontier V3.

Reconciles the sealed V2 frontier with the sealed official index reference
mapping. It upgrades exactly 11 current index references, isolates 2 legacy
index lineages, preserves 12 unresolved index bindings, and leaves the exact
73 cryptocurrency sensors at provider-attested economic-object scope.

No tradable/listing/calendar/historical/admission/relational/execution
authority is widened by this reducer.
"""

from __future__ import annotations

import hashlib
import json
from typing import cast

IDENTITY = "SHARED_B_GLOBAL_IDENTITY_FRONTIER_V3_001"
EXPECTED_V2_IDENTITY = "SHARED_B_GLOBAL_IDENTITY_FRONTIER_V2_001"
EXPECTED_INDEX_IDENTITY = "SHARED_B_INDEX_REFERENCE_MAPPING_001"


class SharedBIdentityFrontierV3Error(ValueError):
    """Identity frontier V3 reconciliation failed closed."""


def _fingerprint(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()


def _provider_key(row: dict[str, object]) -> tuple[str, int]:
    provider = row.get("provider")
    symbol_id = row.get("provider_symbol_id")
    if not isinstance(provider, str) or not provider:
        raise SharedBIdentityFrontierV3Error("provider missing")
    if type(symbol_id) is not int or symbol_id <= 0:
        raise SharedBIdentityFrontierV3Error("provider_symbol_id invalid")
    return (provider, symbol_id)


def build_identity_frontier_v3(
    *,
    frontier_v2: dict[str, object],
    index_mapping: dict[str, object],
) -> dict[str, object]:
    if frontier_v2.get("identity") != EXPECTED_V2_IDENTITY:
        raise SharedBIdentityFrontierV3Error("unexpected frontier V2 identity")
    if index_mapping.get("identity") != EXPECTED_INDEX_IDENTITY:
        raise SharedBIdentityFrontierV3Error("unexpected index mapping identity")
    if frontier_v2.get("sensor_count") != 177:
        raise SharedBIdentityFrontierV3Error("frontier V2 is not exact 177")
    if index_mapping.get("provider_index_sensor_count") != 25:
        raise SharedBIdentityFrontierV3Error("index mapping is not exact 25")
    if index_mapping.get("current_official_reference_mapped_count") != 11:
        raise SharedBIdentityFrontierV3Error("index mapping current count drift")
    if index_mapping.get("legacy_reference_lineage_only_count") != 2:
        raise SharedBIdentityFrontierV3Error("index mapping legacy count drift")
    if index_mapping.get("provider_binding_unresolved_count") != 12:
        raise SharedBIdentityFrontierV3Error(
            "index mapping unresolved count drift"
        )
    if index_mapping.get("b06_complete") is not False:
        raise SharedBIdentityFrontierV3Error(
            "index mapping illegally claims B-06 completion"
        )

    v2_records = frontier_v2.get("records")
    index_records = index_mapping.get("records")
    if not isinstance(v2_records, list) or len(v2_records) != 177:
        raise SharedBIdentityFrontierV3Error("frontier V2 records invalid")
    if not isinstance(index_records, list) or len(index_records) != 25:
        raise SharedBIdentityFrontierV3Error("index mapping records invalid")

    mapped_indices: dict[tuple[str, int], dict[str, object]] = {}
    for raw in index_records:
        if not isinstance(raw, dict):
            raise SharedBIdentityFrontierV3Error("index mapping row invalid")
        row = cast(dict[str, object], raw)
        key = _provider_key(row)
        if key in mapped_indices:
            raise SharedBIdentityFrontierV3Error("duplicate index mapping key")
        stage = row.get("resolution_stage")
        if stage not in {
            "CURRENT_OFFICIAL_REFERENCE_MAPPED",
            "LEGACY_REFERENCE_LINEAGE_ONLY",
            "PROVIDER_BINDING_UNRESOLVED",
        }:
            raise SharedBIdentityFrontierV3Error(
                "unexpected index resolution stage"
            )
        for forbidden in (
            "tradable_product_identity_verified",
            "listing_identity_verified",
            "canonical_calendar_binding_verified",
        ):
            if row.get(forbidden) is not False:
                raise SharedBIdentityFrontierV3Error(
                    f"index mapping authority widening: {forbidden}"
                )
        mapped_indices[key] = row

    output: list[dict[str, object]] = []
    seen_v2: set[tuple[str, int]] = set()
    replaced_indices: set[tuple[str, int]] = set()
    for raw in v2_records:
        if not isinstance(raw, dict):
            raise SharedBIdentityFrontierV3Error("frontier V2 row invalid")
        row = cast(dict[str, object], raw)
        key = _provider_key(row)
        if key in seen_v2:
            raise SharedBIdentityFrontierV3Error("duplicate frontier V2 key")
        seen_v2.add(key)

        replacement = mapped_indices.get(key)
        if replacement is None:
            output.append(dict(row))
            continue

        if row.get("resolution_stage") != "PROVIDER_ATTESTED_ECONOMIC_OBJECT":
            raise SharedBIdentityFrontierV3Error(
                "index replacement source is not provider-attested"
            )
        if row.get("provider_symbol") != replacement.get("provider_symbol"):
            raise SharedBIdentityFrontierV3Error("index provider symbol drift")
        if row.get("provider_description") != replacement.get(
            "provider_description"
        ):
            raise SharedBIdentityFrontierV3Error(
                "index provider description drift"
            )

        updated = dict(row)
        updated.update(replacement)
        updated["frontier_source_stage"] = (
            "PROVIDER_ATTESTED_ECONOMIC_OBJECT"
        )
        updated["historical_pre_freeze_mapping_authorized"] = False
        updated["sensor_admission_authorized"] = False
        updated["relational_claims_authorized"] = False
        updated["execution_authority"] = False
        output.append(updated)
        replaced_indices.add(key)

    if replaced_indices != set(mapped_indices):
        raise SharedBIdentityFrontierV3Error(
            "index mapping does not exactly match V2 index population"
        )

    output.sort(
        key=lambda item: (
            str(item["provider"]),
            int(cast(int, item["provider_symbol_id"])),
        )
    )

    stage_counts: dict[str, int] = {}
    for row in output:
        stage = str(row.get("resolution_stage"))
        stage_counts[stage] = stage_counts.get(stage, 0) + 1

    expected_stage_counts = {
        "CURRENT_REFERENCE_OBJECT_MAPPED": 74,
        "CURRENT_OFFICIAL_REFERENCE_MAPPED": 11,
        "DATED_CONTRACT_DESCRIPTOR_VERIFIED": 5,
        "LEGACY_REFERENCE_LINEAGE_ONLY": 2,
        "PROVIDER_BINDING_UNRESOLVED": 12,
        "PROVIDER_ATTESTED_ECONOMIC_OBJECT": 73,
    }
    if stage_counts != expected_stage_counts:
        raise SharedBIdentityFrontierV3Error(
            f"unexpected V3 stage counts: {stage_counts}"
        )

    if len(output) != 177:
        raise SharedBIdentityFrontierV3Error("V3 lost exact 177 population")

    payload: dict[str, object] = {
        "identity": IDENTITY,
        "status": "EXACT_177_SENSOR_IDENTITY_FRONTIER_V3_MATERIALIZED",
        "sensor_count": 177,
        "current_reference_mapped_count": 85,
        "preexisting_current_reference_mapped_count": 74,
        "new_current_official_index_reference_mapped_count": 11,
        "dated_contract_descriptor_verified_count": 5,
        "legacy_index_reference_lineage_only_count": 2,
        "index_provider_binding_unresolved_count": 12,
        "cryptocurrency_provider_attested_only_count": 73,
        "provider_native_only_count": 0,
        "stage_counts": stage_counts,
        "records": output,
        "frontier_v2_fingerprint_sha256": frontier_v2.get(
            "frontier_v2_fingerprint_sha256"
        ),
        "index_mapping_fingerprint_sha256": index_mapping.get(
            "mapping_fingerprint_sha256"
        ),
        "full_177_canonical_identity_complete": False,
        "tradable_product_identity_complete": False,
        "listing_identity_complete": False,
        "canonical_calendar_binding_complete": False,
        "historical_pre_freeze_mapping_complete": False,
        "automatic_identity_inference": False,
        "symbol_name_similarity_used": False,
        "sensor_admission_authorized": False,
        "relational_claims_authorized": False,
        "target_or_outcome_read": False,
        "r6_r5_read": False,
        "fresh_holdout_opened": False,
        "historical_market_data_read": False,
        "broker_mutation": False,
        "productive_authority": False,
        "b06_complete": False,
    }
    payload["frontier_v3_fingerprint_sha256"] = _fingerprint(payload)
    return payload
