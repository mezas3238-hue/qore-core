from __future__ import annotations

from copy import deepcopy

import pytest

from qore.infrastructure.core_stack_v2.shared_b_global_identity_frontier_v3 import (
    SharedBIdentityFrontierV3Error,
    build_identity_frontier_v3,
)


def _frontier_v2() -> dict[str, object]:
    records: list[dict[str, object]] = []
    symbol_id = 1
    for _ in range(74):
        records.append({
            "provider": "CTRADER_DEMO",
            "provider_symbol_id": symbol_id,
            "provider_symbol": f"REF{symbol_id}",
            "provider_description": f"Reference {symbol_id}",
            "provider_asset_class_name": "Forex",
            "resolution_stage": "CURRENT_REFERENCE_OBJECT_MAPPED",
        })
        symbol_id += 1
    for _ in range(5):
        records.append({
            "provider": "CTRADER_DEMO",
            "provider_symbol_id": symbol_id,
            "provider_symbol": f"GC{symbol_id}",
            "provider_description": f"Contract {symbol_id}",
            "provider_asset_class_name": "Commodities",
            "resolution_stage": "DATED_CONTRACT_DESCRIPTOR_VERIFIED",
        })
        symbol_id += 1
    for _ in range(25):
        records.append({
            "provider": "CTRADER_DEMO",
            "provider_symbol_id": symbol_id,
            "provider_symbol": f"IDX{symbol_id}",
            "provider_description": f"Index {symbol_id}",
            "provider_asset_class_name": "Indices",
            "resolution_stage": "PROVIDER_ATTESTED_ECONOMIC_OBJECT",
            "provider_neutral_reference_identity_verified": False,
            "canonical_economic_identity_verified": False,
            "tradable_product_identity_verified": False,
            "listing_identity_verified": False,
            "canonical_calendar_binding_verified": False,
        })
        symbol_id += 1
    for _ in range(73):
        records.append({
            "provider": "CTRADER_DEMO",
            "provider_symbol_id": symbol_id,
            "provider_symbol": f"CRY{symbol_id}",
            "provider_description": f"Crypto {symbol_id}",
            "provider_asset_class_name": "Cryptocurrencies",
            "resolution_stage": "PROVIDER_ATTESTED_ECONOMIC_OBJECT",
            "provider_neutral_reference_identity_verified": False,
            "canonical_economic_identity_verified": False,
            "tradable_product_identity_verified": False,
            "listing_identity_verified": False,
            "canonical_calendar_binding_verified": False,
        })
        symbol_id += 1
    assert len(records) == 177
    return {
        "identity": "SHARED_B_GLOBAL_IDENTITY_FRONTIER_V2_001",
        "sensor_count": 177,
        "records": records,
        "frontier_v2_fingerprint_sha256": "a" * 64,
    }


def _index_mapping() -> dict[str, object]:
    rows: list[dict[str, object]] = []
    first_index_id = 80
    for offset in range(25):
        symbol_id = first_index_id + offset
        base = {
            "provider": "CTRADER_DEMO",
            "provider_symbol_id": symbol_id,
            "provider_symbol": f"IDX{symbol_id}",
            "provider_description": f"Index {symbol_id}",
            "tradable_product_identity_verified": False,
            "listing_identity_verified": False,
            "canonical_calendar_binding_verified": False,
        }
        if offset < 11:
            rows.append({
                **base,
                "resolution_stage": "CURRENT_OFFICIAL_REFERENCE_MAPPED",
                "canonical_reference_identity": f"INDEX:REF_{symbol_id}",
                "canonical_reference_name": f"Reference {symbol_id}",
                "provider_neutral_reference_identity_verified": True,
                "canonical_economic_identity_verified": True,
            })
        elif offset < 13:
            rows.append({
                **base,
                "resolution_stage": "LEGACY_REFERENCE_LINEAGE_ONLY",
                "legacy_reference_family": f"Legacy {symbol_id}",
                "provider_neutral_reference_identity_verified": False,
                "canonical_economic_identity_verified": True,
                "current_reference_binding_verified": False,
            })
        else:
            rows.append({
                **base,
                "resolution_stage": "PROVIDER_BINDING_UNRESOLVED",
                "reason": "BINDING_UNRESOLVED",
                "provider_neutral_reference_identity_verified": False,
                "canonical_economic_identity_verified": False,
                "current_reference_binding_verified": False,
            })
    return {
        "identity": "SHARED_B_INDEX_REFERENCE_MAPPING_001",
        "provider_index_sensor_count": 25,
        "current_official_reference_mapped_count": 11,
        "legacy_reference_lineage_only_count": 2,
        "provider_binding_unresolved_count": 12,
        "records": rows,
        "mapping_fingerprint_sha256": "b" * 64,
        "b06_complete": False,
    }


def test_reconciles_exact_v3_population_without_authority_widening() -> None:
    payload = build_identity_frontier_v3(
        frontier_v2=_frontier_v2(),
        index_mapping=_index_mapping(),
    )
    assert payload["sensor_count"] == 177
    assert payload["current_reference_mapped_count"] == 85
    assert payload["preexisting_current_reference_mapped_count"] == 74
    assert payload["new_current_official_index_reference_mapped_count"] == 11
    assert payload["dated_contract_descriptor_verified_count"] == 5
    assert payload["legacy_index_reference_lineage_only_count"] == 2
    assert payload["index_provider_binding_unresolved_count"] == 12
    assert payload["cryptocurrency_provider_attested_only_count"] == 73
    assert payload["provider_native_only_count"] == 0
    assert payload["stage_counts"] == {
        "CURRENT_REFERENCE_OBJECT_MAPPED": 74,
        "CURRENT_OFFICIAL_REFERENCE_MAPPED": 11,
        "DATED_CONTRACT_DESCRIPTOR_VERIFIED": 5,
        "LEGACY_REFERENCE_LINEAGE_ONLY": 2,
        "PROVIDER_BINDING_UNRESOLVED": 12,
        "PROVIDER_ATTESTED_ECONOMIC_OBJECT": 73,
    }
    assert payload["full_177_canonical_identity_complete"] is False
    assert payload["tradable_product_identity_complete"] is False
    assert payload["listing_identity_complete"] is False
    assert payload["canonical_calendar_binding_complete"] is False
    assert payload["sensor_admission_authorized"] is False
    assert payload["relational_claims_authorized"] is False
    assert payload["b06_complete"] is False
    assert len(payload["frontier_v3_fingerprint_sha256"]) == 64


def test_rejects_index_mapping_count_drift() -> None:
    mapping = deepcopy(_index_mapping())
    mapping["provider_binding_unresolved_count"] = 11
    with pytest.raises(
        SharedBIdentityFrontierV3Error,
        match="unresolved count drift",
    ):
        build_identity_frontier_v3(
            frontier_v2=_frontier_v2(),
            index_mapping=mapping,
        )


def test_rejects_index_authority_widening() -> None:
    mapping = deepcopy(_index_mapping())
    rows = mapping["records"]
    assert isinstance(rows, list)
    rows[0]["canonical_calendar_binding_verified"] = True
    with pytest.raises(
        SharedBIdentityFrontierV3Error,
        match="authority widening",
    ):
        build_identity_frontier_v3(
            frontier_v2=_frontier_v2(),
            index_mapping=mapping,
        )


def test_rejects_provider_identity_drift() -> None:
    mapping = deepcopy(_index_mapping())
    rows = mapping["records"]
    assert isinstance(rows, list)
    rows[0]["provider_symbol"] = "DRIFT"
    with pytest.raises(
        SharedBIdentityFrontierV3Error,
        match="provider symbol drift",
    ):
        build_identity_frontier_v3(
            frontier_v2=_frontier_v2(),
            index_mapping=mapping,
        )
