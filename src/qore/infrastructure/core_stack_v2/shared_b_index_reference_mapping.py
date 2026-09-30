"""Architect-B provider-index reference mapping.

Applies frozen official-authority evidence to the exact 25 provider index
sensors. Only explicit provider descriptions that name an official current
reference index are promoted. Legacy and generic descriptions remain bounded.
"""

from __future__ import annotations

import hashlib
import json
from typing import cast

IDENTITY = "SHARED_B_INDEX_REFERENCE_MAPPING_001"
EXPECTED_ATTESTED_IDENTITY = (
    "SHARED_B_PROVIDER_ATTESTED_ECONOMIC_IDENTITY_BOUNDARY_001"
)
EXPECTED_AUTHORITY_IDENTITY = "SHARED_B_INDEX_REFERENCE_AUTHORITY_EVIDENCE_001"


class SharedBIndexReferenceMappingError(ValueError):
    """Index reference mapping failed closed."""


def _fingerprint(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()


def _mapping_rows(
    authority_evidence: dict[str, object],
    field: str,
) -> list[dict[str, object]]:
    value = authority_evidence.get(field)
    if not isinstance(value, list):
        raise SharedBIndexReferenceMappingError(f"{field} missing")
    rows: list[dict[str, object]] = []
    for raw in value:
        if not isinstance(raw, dict):
            raise SharedBIndexReferenceMappingError(f"{field} row invalid")
        rows.append(cast(dict[str, object], raw))
    return rows


def build_index_reference_mapping(
    *,
    provider_attested: dict[str, object],
    authority_evidence: dict[str, object],
) -> dict[str, object]:
    if provider_attested.get("identity") != EXPECTED_ATTESTED_IDENTITY:
        raise SharedBIndexReferenceMappingError(
            "unexpected provider-attested identity"
        )
    if authority_evidence.get("identity") != EXPECTED_AUTHORITY_IDENTITY:
        raise SharedBIndexReferenceMappingError(
            "unexpected authority evidence identity"
        )

    policy = authority_evidence.get("mapping_policy")
    if not isinstance(policy, dict):
        raise SharedBIndexReferenceMappingError("mapping policy missing")
    required_policy = {
        "provider_symbol_name_used_as_mapping_proof": False,
        "provider_description_required": True,
        "official_authority_required": True,
        "semantic_guessing_allowed": False,
        "generic_country_plus_constituent_count_is_sufficient": False,
        "legacy_constituent_count_auto_promotes_to_current_index": False,
    }
    for key, expected in required_policy.items():
        if policy.get(key) != expected:
            raise SharedBIndexReferenceMappingError(
                f"mapping policy mismatch: {key}"
            )

    records = provider_attested.get("records")
    if not isinstance(records, list):
        raise SharedBIndexReferenceMappingError("attested records missing")
    provider_indices: dict[int, dict[str, object]] = {}
    for raw in records:
        if not isinstance(raw, dict):
            raise SharedBIndexReferenceMappingError("attested row invalid")
        row = cast(dict[str, object], raw)
        if str(row.get("provider_asset_class_name", "")).casefold() != "indices":
            continue
        symbol_id = row.get("provider_symbol_id")
        if type(symbol_id) is not int or symbol_id <= 0:
            raise SharedBIndexReferenceMappingError("index symbol id invalid")
        if symbol_id in provider_indices:
            raise SharedBIndexReferenceMappingError("duplicate index symbol id")
        provider_indices[symbol_id] = row
    if len(provider_indices) != 25:
        raise SharedBIndexReferenceMappingError(
            f"expected exact 25 provider indices, got {len(provider_indices)}"
        )

    current = _mapping_rows(authority_evidence, "current_reference_mappings")
    legacy = _mapping_rows(authority_evidence, "legacy_lineage_only")
    unresolved = _mapping_rows(
        authority_evidence,
        "unresolved_provider_bindings",
    )
    if (len(current), len(legacy), len(unresolved)) != (11, 2, 12):
        raise SharedBIndexReferenceMappingError(
            "authority partition must be exact 11/2/12"
        )

    output: list[dict[str, object]] = []
    seen: set[int] = set()

    def provider_row(authority_row: dict[str, object]) -> dict[str, object]:
        symbol_id = authority_row.get("provider_symbol_id")
        if type(symbol_id) is not int:
            raise SharedBIndexReferenceMappingError(
                "authority provider_symbol_id invalid"
            )
        if symbol_id in seen:
            raise SharedBIndexReferenceMappingError(
                "authority partition overlaps"
            )
        row = provider_indices.get(symbol_id)
        if row is None:
            raise SharedBIndexReferenceMappingError(
                "authority references absent provider index"
            )
        if row.get("provider_symbol") != authority_row.get("provider_symbol"):
            raise SharedBIndexReferenceMappingError("provider symbol drift")
        if row.get("provider_description") != authority_row.get(
            "expected_provider_description"
        ):
            raise SharedBIndexReferenceMappingError(
                "provider description drift"
            )
        seen.add(symbol_id)
        return row

    for authority_row in current:
        row = provider_row(authority_row)
        source_url = authority_row.get("source_url")
        if (
            not isinstance(source_url, str)
            or not source_url.startswith("https://")
        ):
            raise SharedBIndexReferenceMappingError(
                "official authority URL invalid"
            )
        canonical_identity = authority_row.get("canonical_reference_identity")
        canonical_name = authority_row.get("canonical_reference_name")
        if (
            not isinstance(canonical_identity, str)
            or not canonical_identity.startswith("INDEX:")
            or not isinstance(canonical_name, str)
            or not canonical_name
        ):
            raise SharedBIndexReferenceMappingError(
                "canonical reference identity invalid"
            )
        output.append(
            {
                "provider": row["provider"],
                "provider_symbol_id": row["provider_symbol_id"],
                "provider_symbol": row["provider_symbol"],
                "provider_description": row["provider_description"],
                "resolution_stage": "CURRENT_OFFICIAL_REFERENCE_MAPPED",
                "canonical_reference_identity": canonical_identity,
                "canonical_reference_name": canonical_name,
                "authority": authority_row.get("authority"),
                "authority_url": source_url,
                "provider_neutral_reference_identity_verified": True,
                "canonical_economic_identity_verified": True,
                "tradable_product_identity_verified": False,
                "listing_identity_verified": False,
                "canonical_calendar_binding_verified": False,
            }
        )

    for authority_row in legacy:
        row = provider_row(authority_row)
        source_url = authority_row.get("source_url")
        if (
            not isinstance(source_url, str)
            or not source_url.startswith("https://")
        ):
            raise SharedBIndexReferenceMappingError(
                "legacy authority URL invalid"
            )
        output.append(
            {
                "provider": row["provider"],
                "provider_symbol_id": row["provider_symbol_id"],
                "provider_symbol": row["provider_symbol"],
                "provider_description": row["provider_description"],
                "resolution_stage": "LEGACY_REFERENCE_LINEAGE_ONLY",
                "legacy_reference_family": authority_row.get(
                    "legacy_reference_family"
                ),
                "current_reference_identity": authority_row.get(
                    "current_reference_identity"
                ),
                "disposition": authority_row.get("disposition"),
                "authority": authority_row.get("authority"),
                "authority_url": source_url,
                "provider_neutral_reference_identity_verified": False,
                "canonical_economic_identity_verified": True,
                "current_reference_binding_verified": False,
                "tradable_product_identity_verified": False,
                "listing_identity_verified": False,
                "canonical_calendar_binding_verified": False,
            }
        )

    for authority_row in unresolved:
        row = provider_row(authority_row)
        reason = authority_row.get("reason")
        if not isinstance(reason, str) or not reason:
            raise SharedBIndexReferenceMappingError(
                "unresolved reason missing"
            )
        output.append(
            {
                "provider": row["provider"],
                "provider_symbol_id": row["provider_symbol_id"],
                "provider_symbol": row["provider_symbol"],
                "provider_description": row["provider_description"],
                "resolution_stage": "PROVIDER_BINDING_UNRESOLVED",
                "reason": reason,
                "provider_neutral_reference_identity_verified": False,
                "canonical_economic_identity_verified": False,
                "current_reference_binding_verified": False,
                "tradable_product_identity_verified": False,
                "listing_identity_verified": False,
                "canonical_calendar_binding_verified": False,
            }
        )

    if seen != set(provider_indices):
        raise SharedBIndexReferenceMappingError(
            "authority partition does not cover all 25 provider indices"
        )

    output.sort(key=lambda item: int(cast(int, item["provider_symbol_id"])))
    stage_counts: dict[str, int] = {}
    for row in output:
        stage = str(row["resolution_stage"])
        stage_counts[stage] = stage_counts.get(stage, 0) + 1

    expected_stage_counts = {
        "CURRENT_OFFICIAL_REFERENCE_MAPPED": 11,
        "LEGACY_REFERENCE_LINEAGE_ONLY": 2,
        "PROVIDER_BINDING_UNRESOLVED": 12,
    }
    if stage_counts != expected_stage_counts:
        raise SharedBIndexReferenceMappingError(
            f"unexpected index stage counts: {stage_counts}"
        )

    payload: dict[str, object] = {
        "identity": IDENTITY,
        "status": "INDEX_REFERENCE_MAPPING_PARTIAL_EVIDENCE_FROZEN",
        "provider_index_sensor_count": 25,
        "current_official_reference_mapped_count": 11,
        "legacy_reference_lineage_only_count": 2,
        "provider_binding_unresolved_count": 12,
        "stage_counts": stage_counts,
        "records": output,
        "full_index_identity_complete": False,
        "tradable_product_identity_complete": False,
        "listing_identity_complete": False,
        "canonical_calendar_binding_complete": False,
        "provider_symbol_name_used_as_mapping_proof": False,
        "semantic_guessing_used": False,
        "target_or_outcome_read": False,
        "r6_r5_read": False,
        "fresh_holdout_opened": False,
        "historical_market_data_read": False,
        "broker_mutation": False,
        "productive_authority": False,
        "b06_complete": False,
    }
    payload["mapping_fingerprint_sha256"] = _fingerprint(payload)
    return payload
