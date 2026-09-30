from __future__ import annotations

from copy import deepcopy

import pytest

from qore.infrastructure.core_stack_v2.shared_b_global_identity_frontier_v2 import (
    SharedBIdentityFrontierV2Error,
    build_identity_frontier_v2,
)


def _frontier_v1() -> dict[str, object]:
    records: list[dict[str, object]] = []
    symbol_id = 1
    for _ in range(74):
        records.append(
            {
                "provider": "CTRADER_DEMO",
                "provider_symbol_id": symbol_id,
                "provider_symbol": f"REF{symbol_id}",
                "provider_description": f"Reference {symbol_id}",
                "provider_asset_class_name": "Forex",
                "resolution_stage": "CURRENT_REFERENCE_OBJECT_MAPPED",
                "identity_evidence_kind": "FX_REFERENCE_OBJECT",
            }
        )
        symbol_id += 1
    for _ in range(5):
        records.append(
            {
                "provider": "CTRADER_DEMO",
                "provider_symbol_id": symbol_id,
                "provider_symbol": f"GC{symbol_id}",
                "provider_description": f"Contract {symbol_id}",
                "provider_asset_class_name": "Commodities",
                "resolution_stage": "DATED_CONTRACT_DESCRIPTOR_VERIFIED",
                "identity_evidence_kind": "DATED_FUTURES_CONTRACT_DESCRIPTOR",
            }
        )
        symbol_id += 1
    for index in range(98):
        asset_class = "Indices" if index < 25 else "Cryptocurrencies"
        records.append(
            {
                "provider": "CTRADER_DEMO",
                "provider_symbol_id": symbol_id,
                "provider_symbol": f"NATIVE{symbol_id}",
                "provider_description": f"Native {symbol_id}",
                "provider_asset_class_name": asset_class,
                "resolution_stage": "PROVIDER_NATIVE_ONLY",
                "identity_evidence_kind": "NONE",
                "missing_evidence": ["CANONICAL_ECONOMIC_IDENTITY"],
            }
        )
        symbol_id += 1

    return {
        "identity": "SHARED_B_GLOBAL_IDENTITY_RESOLUTION_WORKLIST_001",
        "sensor_count": 177,
        "records": records,
        "worklist_fingerprint_sha256": "a" * 64,
    }


def _attested() -> dict[str, object]:
    records: list[dict[str, object]] = []
    for symbol_id in range(80, 178):
        asset_class = "Indices" if symbol_id < 105 else "Cryptocurrencies"
        records.append(
            {
                "provider": "CTRADER_DEMO",
                "provider_symbol_id": symbol_id,
                "provider_symbol": f"NATIVE{symbol_id}",
                "provider_description": f"Native {symbol_id}",
                "provider_asset_class_name": asset_class,
                "identity_stage": "PROVIDER_ATTESTED_ECONOMIC_OBJECT",
                "provider_attested_economic_identity_key": (
                    f"QORE:PROVIDER_ATTESTED:{asset_class}:{symbol_id}"
                ),
                "provider_attested_reference_label": f"Native {symbol_id}",
                "provider_neutral_reference_identity_verified": False,
                "canonical_economic_identity_verified": False,
                "tradable_product_identity_verified": False,
                "listing_identity_verified": False,
                "canonical_calendar_binding_verified": False,
                "historical_pre_freeze_mapping_authorized": False,
                "sensor_admission_authorized": False,
                "relational_claims_authorized": False,
                "execution_authority": False,
            }
        )
    return {
        "identity": (
            "SHARED_B_PROVIDER_ATTESTED_ECONOMIC_IDENTITY_BOUNDARY_001"
        ),
        "sensor_count": 98,
        "provider_neutral_reference_identity_verified_count": 0,
        "canonical_economic_identity_verified_count": 0,
        "records": records,
        "boundary_fingerprint_sha256": "b" * 64,
    }


def test_reconciles_exact_177_without_canonical_widening() -> None:
    payload = build_identity_frontier_v2(
        frontier_v1=_frontier_v1(),
        provider_attested=_attested(),
    )

    assert payload["sensor_count"] == 177
    assert payload["current_reference_mapped_count"] == 74
    assert payload["dated_contract_descriptor_verified_count"] == 5
    assert payload["provider_attested_economic_object_count"] == 98
    assert payload["provider_native_only_count"] == 0
    assert payload["full_canonical_identity_complete_count"] == 0
    assert payload["full_177_identity_complete"] is False
    assert payload["stage_counts"] == {
        "CURRENT_REFERENCE_OBJECT_MAPPED": 74,
        "DATED_CONTRACT_DESCRIPTOR_VERIFIED": 5,
        "PROVIDER_ATTESTED_ECONOMIC_OBJECT": 98,
    }
    assert payload["provider_metadata_is_canonical_proof"] is False
    assert payload["automatic_identity_inference"] is False
    assert payload["sensor_admission_authorized"] is False
    assert payload["relational_claims_authorized"] is False
    assert payload["fresh_holdout_opened"] is False
    assert payload["broker_mutation"] is False
    assert payload["productive_authority"] is False
    assert payload["b06_complete"] is False
    assert len(payload["frontier_v2_fingerprint_sha256"]) == 64

    rows = payload["records"]
    assert isinstance(rows, list)
    transformed = [
        row
        for row in rows
        if row["resolution_stage"] == "PROVIDER_ATTESTED_ECONOMIC_OBJECT"
    ]
    assert len(transformed) == 98
    assert all(
        row["provider_neutral_reference_identity_verified"] is False
        and row["canonical_economic_identity_verified"] is False
        for row in transformed
    )


def test_rejects_attested_population_drift() -> None:
    attested = deepcopy(_attested())
    rows = attested["records"]
    assert isinstance(rows, list)
    rows.pop()

    with pytest.raises(
        SharedBIdentityFrontierV2Error,
        match="provider-attested records invalid",
    ):
        build_identity_frontier_v2(
            frontier_v1=_frontier_v1(),
            provider_attested=attested,
        )


def test_rejects_authority_widening() -> None:
    attested = deepcopy(_attested())
    rows = attested["records"]
    assert isinstance(rows, list)
    rows[0]["canonical_economic_identity_verified"] = True

    with pytest.raises(
        SharedBIdentityFrontierV2Error,
        match="attested authority widening",
    ):
        build_identity_frontier_v2(
            frontier_v1=_frontier_v1(),
            provider_attested=attested,
        )


def test_rejects_provider_descriptor_drift() -> None:
    attested = deepcopy(_attested())
    rows = attested["records"]
    assert isinstance(rows, list)
    rows[0]["provider_description"] = "DRIFT"

    with pytest.raises(
        SharedBIdentityFrontierV2Error,
        match="provider description drift",
    ):
        build_identity_frontier_v2(
            frontier_v1=_frontier_v1(),
            provider_attested=attested,
        )
