from __future__ import annotations

from copy import deepcopy

import pytest

from qore.infrastructure.core_stack_v2.shared_b_index_reference_mapping import (
    SharedBIndexReferenceMappingError,
    build_index_reference_mapping,
)


def _provider_attested() -> dict[str, object]:
    records: list[dict[str, object]] = []
    for symbol_id in range(10000, 10025):
        records.append({
            "provider": "CTRADER_DEMO",
            "provider_symbol_id": symbol_id,
            "provider_symbol": f"IDX{symbol_id}",
            "provider_description": f"Index {symbol_id}",
            "provider_asset_class_name": "Indices",
            "identity_stage": "PROVIDER_ATTESTED_ECONOMIC_OBJECT",
        })
    for symbol_id in range(20000, 20073):
        records.append({
            "provider": "CTRADER_DEMO",
            "provider_symbol_id": symbol_id,
            "provider_symbol": f"CRY{symbol_id}",
            "provider_description": f"Crypto {symbol_id}",
            "provider_asset_class_name": "Cryptocurrencies",
            "identity_stage": "PROVIDER_ATTESTED_ECONOMIC_OBJECT",
        })
    return {
        "identity": "SHARED_B_PROVIDER_ATTESTED_ECONOMIC_IDENTITY_BOUNDARY_001",
        "records": records,
    }


def _authority() -> dict[str, object]:
    current = []
    legacy = []
    unresolved = []
    for index, symbol_id in enumerate(range(10000, 10025)):
        base = {
            "provider_symbol_id": symbol_id,
            "provider_symbol": f"IDX{symbol_id}",
            "expected_provider_description": f"Index {symbol_id}",
        }
        if index < 11:
            current.append({
                **base,
                "canonical_reference_identity": f"INDEX:REF_{symbol_id}",
                "canonical_reference_name": f"Reference {symbol_id}",
                "authority": "Official Authority",
                "source_url": f"https://example.test/{symbol_id}",
            })
        elif index < 13:
            legacy.append({
                **base,
                "legacy_reference_family": f"Legacy {symbol_id}",
                "current_reference_identity": f"INDEX:CURRENT_{symbol_id}",
                "disposition": "LEGACY_CONSTITUENT_COUNT_NOT_CURRENT_REFERENCE_BINDING",
                "authority": "Official Authority",
                "source_url": f"https://example.test/{symbol_id}",
            })
        else:
            unresolved.append({
                **base,
                "reason": "BINDING_UNRESOLVED",
            })
    return {
        "identity": "SHARED_B_INDEX_REFERENCE_AUTHORITY_EVIDENCE_001",
        "mapping_policy": {
            "provider_symbol_name_used_as_mapping_proof": False,
            "provider_description_required": True,
            "official_authority_required": True,
            "semantic_guessing_allowed": False,
            "generic_country_plus_constituent_count_is_sufficient": False,
            "legacy_constituent_count_auto_promotes_to_current_index": False,
        },
        "current_reference_mappings": current,
        "legacy_lineage_only": legacy,
        "unresolved_provider_bindings": unresolved,
    }


def test_exact_11_2_12_partition_preserves_boundaries() -> None:
    payload = build_index_reference_mapping(
        provider_attested=_provider_attested(),
        authority_evidence=_authority(),
    )
    assert payload["provider_index_sensor_count"] == 25
    assert payload["current_official_reference_mapped_count"] == 11
    assert payload["legacy_reference_lineage_only_count"] == 2
    assert payload["provider_binding_unresolved_count"] == 12
    assert payload["full_index_identity_complete"] is False
    assert payload["tradable_product_identity_complete"] is False
    assert payload["canonical_calendar_binding_complete"] is False
    assert payload["provider_symbol_name_used_as_mapping_proof"] is False
    assert payload["semantic_guessing_used"] is False
    assert payload["b06_complete"] is False
    assert len(payload["mapping_fingerprint_sha256"]) == 64


def test_rejects_provider_description_drift() -> None:
    authority = deepcopy(_authority())
    rows = authority["current_reference_mappings"]
    assert isinstance(rows, list)
    rows[0]["expected_provider_description"] = "DRIFT"

    with pytest.raises(
        SharedBIndexReferenceMappingError,
        match="provider description drift",
    ):
        build_index_reference_mapping(
            provider_attested=_provider_attested(),
            authority_evidence=authority,
        )


def test_rejects_semantic_guessing_policy() -> None:
    authority = deepcopy(_authority())
    policy = authority["mapping_policy"]
    assert isinstance(policy, dict)
    policy["semantic_guessing_allowed"] = True

    with pytest.raises(
        SharedBIndexReferenceMappingError,
        match="mapping policy mismatch",
    ):
        build_index_reference_mapping(
            provider_attested=_provider_attested(),
            authority_evidence=authority,
        )
