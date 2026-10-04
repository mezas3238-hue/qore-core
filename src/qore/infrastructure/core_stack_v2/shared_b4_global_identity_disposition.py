"""Architect B4 exact 177-sensor identity disposition closure.

B-06 closes when every governed sensor has an explicit, evidence-backed
epistemic identity disposition. Closure does not require pretending that every
provider symbol has a provider-neutral canonical identity.

UNKNOWN / limited dispositions are terminal B-06 outcomes and remain ineligible
for downstream temporal or relational admission until independent evidence
upgrades them.
"""

from __future__ import annotations

import hashlib
import json
from enum import StrEnum
from typing import cast

IDENTITY = "SHARED_B4_GLOBAL_IDENTITY_DISPOSITION_001"
EXPECTED_FRONTIER = "SHARED_B_GLOBAL_IDENTITY_FRONTIER_V3_001"
EXPECTED_SENSOR_COUNT = 177


class SharedB4IdentityDispositionError(ValueError):
    """B4 identity-disposition reconciliation failed closed."""


class IdentityDisposition(StrEnum):
    CURRENT_REFERENCE_VERIFIED = "CURRENT_REFERENCE_VERIFIED"
    VERSIONED_CONTRACT_VERIFIED = "VERSIONED_CONTRACT_VERIFIED"
    LEGACY_LINEAGE_ONLY = "LEGACY_LINEAGE_ONLY"
    PROVIDER_BINDING_UNKNOWN = "PROVIDER_BINDING_UNKNOWN"
    PROVIDER_ATTESTED_ONLY = "PROVIDER_ATTESTED_ONLY"


_STAGE_TO_DISPOSITION: dict[str, IdentityDisposition] = {
    "CURRENT_REFERENCE_OBJECT_MAPPED": (
        IdentityDisposition.CURRENT_REFERENCE_VERIFIED
    ),
    "CURRENT_OFFICIAL_REFERENCE_MAPPED": (
        IdentityDisposition.CURRENT_REFERENCE_VERIFIED
    ),
    "DATED_CONTRACT_DESCRIPTOR_VERIFIED": (
        IdentityDisposition.VERSIONED_CONTRACT_VERIFIED
    ),
    "LEGACY_REFERENCE_LINEAGE_ONLY": IdentityDisposition.LEGACY_LINEAGE_ONLY,
    "PROVIDER_BINDING_UNRESOLVED": IdentityDisposition.PROVIDER_BINDING_UNKNOWN,
    "PROVIDER_ATTESTED_ECONOMIC_OBJECT": (
        IdentityDisposition.PROVIDER_ATTESTED_ONLY
    ),
}


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
    if not isinstance(provider, str) or not provider.strip():
        raise SharedB4IdentityDispositionError("provider identity missing")
    if type(symbol_id) is not int or symbol_id <= 0:
        raise SharedB4IdentityDispositionError("provider_symbol_id invalid")
    return provider, symbol_id


def _reason_codes(
    disposition: IdentityDisposition,
) -> tuple[str, ...]:
    if disposition is IdentityDisposition.CURRENT_REFERENCE_VERIFIED:
        return ("CURRENT_PROVIDER_NEUTRAL_REFERENCE_EVIDENCE_VERIFIED",)
    if disposition is IdentityDisposition.VERSIONED_CONTRACT_VERIFIED:
        return (
            "DATED_CONTRACT_IDENTITY_EVIDENCE_VERIFIED",
            "CALENDAR_AND_LISTING_SEMANTICS_REQUIRE_SEPARATE_QUALIFICATION",
        )
    if disposition is IdentityDisposition.LEGACY_LINEAGE_ONLY:
        return (
            "LEGACY_REFERENCE_LINEAGE_PRESERVED",
            "CURRENT_IDENTITY_BINDING_NOT_AUTHORIZED",
            "HISTORICAL_VERSIONING_REQUIRED",
        )
    if disposition is IdentityDisposition.PROVIDER_BINDING_UNKNOWN:
        return (
            "PROVIDER_BINDING_UNRESOLVED",
            "CANONICAL_IDENTITY_UNKNOWN",
        )
    return (
        "PROVIDER_ATTESTED_ECONOMIC_OBJECT_ONLY",
        "PROVIDER_NEUTRAL_IDENTITY_UNPROVEN",
    )


def build_identity_disposition_registry(
    *,
    frontier_v3: dict[str, object],
) -> dict[str, object]:
    """Materialize terminal B-06 epistemic state for all 177 sensors."""

    if frontier_v3.get("identity") != EXPECTED_FRONTIER:
        raise SharedB4IdentityDispositionError(
            "unexpected identity frontier V3"
        )
    if frontier_v3.get("sensor_count") != EXPECTED_SENSOR_COUNT:
        raise SharedB4IdentityDispositionError(
            "identity frontier is not exact 177"
        )
    if frontier_v3.get("provider_native_only_count") != 0:
        raise SharedB4IdentityDispositionError(
            "provider-native-only identity debt remains"
        )
    if frontier_v3.get("automatic_identity_inference") is not False:
        raise SharedB4IdentityDispositionError(
            "automatic identity inference must remain disabled"
        )
    if frontier_v3.get("symbol_name_similarity_used") is not False:
        raise SharedB4IdentityDispositionError(
            "symbol-name similarity inference is forbidden"
        )

    raw_records = frontier_v3.get("records")
    if not isinstance(raw_records, list) or len(raw_records) != EXPECTED_SENSOR_COUNT:
        raise SharedB4IdentityDispositionError("frontier records invalid")

    records: list[dict[str, object]] = []
    seen: set[tuple[str, int]] = set()
    disposition_counts: dict[str, int] = {}
    temporal_candidate_count = 0
    explicit_unknown_or_limited_count = 0

    for raw in raw_records:
        if not isinstance(raw, dict):
            raise SharedB4IdentityDispositionError("frontier row invalid")
        row = cast(dict[str, object], raw)
        key = _provider_key(row)
        if key in seen:
            raise SharedB4IdentityDispositionError("duplicate provider identity")
        seen.add(key)

        stage = row.get("resolution_stage")
        if not isinstance(stage, str) or stage not in _STAGE_TO_DISPOSITION:
            raise SharedB4IdentityDispositionError(
                f"unsupported identity resolution stage: {stage}"
            )
        disposition = _STAGE_TO_DISPOSITION[stage]
        disposition_counts[disposition.value] = (
            disposition_counts.get(disposition.value, 0) + 1
        )

        temporal_candidate = disposition in {
            IdentityDisposition.CURRENT_REFERENCE_VERIFIED,
            IdentityDisposition.VERSIONED_CONTRACT_VERIFIED,
        }
        temporal_candidate_count += int(temporal_candidate)
        explicit_unknown_or_limited_count += int(not temporal_candidate)

        records.append(
            {
                "provider": key[0],
                "provider_symbol_id": key[1],
                "provider_symbol": row.get("provider_symbol"),
                "provider_description": row.get("provider_description"),
                "provider_asset_class_name": row.get(
                    "provider_asset_class_name"
                ),
                "source_resolution_stage": stage,
                "identity_disposition": disposition.value,
                "identity_disposition_terminal": True,
                "provider_neutral_reference_verified": (
                    disposition
                    is IdentityDisposition.CURRENT_REFERENCE_VERIFIED
                ),
                "versioned_contract_identity_verified": (
                    disposition
                    is IdentityDisposition.VERSIONED_CONTRACT_VERIFIED
                ),
                "canonical_identity_unknown_or_limited": not temporal_candidate,
                "eligible_for_calendar_qualification": temporal_candidate,
                "calendar_binding_authorized": False,
                "relational_claims_authorized": False,
                "sensor_admission_authorized": False,
                "reason_codes": _reason_codes(disposition),
            }
        )

    records.sort(
        key=lambda item: (
            str(item["provider"]),
            int(cast(int, item["provider_symbol_id"])),
        )
    )
    disposition_counts = dict(sorted(disposition_counts.items()))

    expected_counts = {
        IdentityDisposition.CURRENT_REFERENCE_VERIFIED.value: 85,
        IdentityDisposition.VERSIONED_CONTRACT_VERIFIED.value: 5,
        IdentityDisposition.LEGACY_LINEAGE_ONLY.value: 2,
        IdentityDisposition.PROVIDER_BINDING_UNKNOWN.value: 12,
        IdentityDisposition.PROVIDER_ATTESTED_ONLY.value: 73,
    }
    if disposition_counts != expected_counts:
        raise SharedB4IdentityDispositionError(
            f"identity disposition count drift: {disposition_counts}"
        )

    payload: dict[str, object] = {
        "identity": IDENTITY,
        "status": "B06_EPISTEMIC_IDENTITY_DISPOSITION_CLOSED",
        "sensor_count": EXPECTED_SENSOR_COUNT,
        "identity_disposition_complete_count": len(records),
        "identity_disposition_coverage_complete": len(records)
        == EXPECTED_SENSOR_COUNT,
        "disposition_counts": disposition_counts,
        "calendar_qualification_candidate_count": temporal_candidate_count,
        "explicit_unknown_or_limited_count": (
            explicit_unknown_or_limited_count
        ),
        "records": records,
        "frontier_v3_fingerprint_sha256": frontier_v3.get(
            "frontier_v3_fingerprint_sha256"
        ),
        "all_provider_symbols_have_canonical_identity": False,
        "unknown_is_valid_terminal_identity_disposition": True,
        "provider_symbol_is_canonical_identity_proof": False,
        "provider_schedule_is_identity_proof": False,
        "automatic_identity_inference": False,
        "symbol_name_similarity_used": False,
        "calendar_binding_authorized": False,
        "relational_claims_authorized": False,
        "sensor_admission_authorized": False,
        "target_or_outcome_read": False,
        "r6_r5_read": False,
        "fresh_holdout_opened": False,
        "historical_market_data_read": False,
        "broker_mutation": False,
        "productive_authority": False,
        "b06_epistemic_closure_complete": True,
        "b06_all_canonical_identities_verified": False,
    }
    payload["registry_fingerprint_sha256"] = _fingerprint(payload)
    return payload
