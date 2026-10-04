from __future__ import annotations

from copy import deepcopy

import pytest

from qore.infrastructure.core_stack_v2.shared_b4_global_identity_disposition import (
    SharedB4IdentityDispositionError,
    build_identity_disposition_registry,
)


def _frontier() -> dict[str, object]:
    records: list[dict[str, object]] = []
    symbol_id = 1
    stages = (
        ("CURRENT_REFERENCE_OBJECT_MAPPED", 74, "Forex"),
        ("CURRENT_OFFICIAL_REFERENCE_MAPPED", 11, "Indices"),
        ("DATED_CONTRACT_DESCRIPTOR_VERIFIED", 5, "Commodities"),
        ("LEGACY_REFERENCE_LINEAGE_ONLY", 2, "Indices"),
        ("PROVIDER_BINDING_UNRESOLVED", 12, "Indices"),
        ("PROVIDER_ATTESTED_ECONOMIC_OBJECT", 73, "Cryptocurrencies"),
    )
    for stage, count, asset_class in stages:
        for _ in range(count):
            records.append(
                {
                    "provider": "CTRADER_DEMO",
                    "provider_symbol_id": symbol_id,
                    "provider_symbol": f"S{symbol_id}",
                    "provider_description": f"Sensor {symbol_id}",
                    "provider_asset_class_name": asset_class,
                    "resolution_stage": stage,
                }
            )
            symbol_id += 1
    assert len(records) == 177
    return {
        "identity": "SHARED_B_GLOBAL_IDENTITY_FRONTIER_V3_001",
        "sensor_count": 177,
        "records": records,
        "provider_native_only_count": 0,
        "automatic_identity_inference": False,
        "symbol_name_similarity_used": False,
        "frontier_v3_fingerprint_sha256": "a" * 64,
    }


def test_closes_exact_177_as_epistemic_dispositions() -> None:
    out = build_identity_disposition_registry(frontier_v3=_frontier())

    assert out["status"] == "B06_EPISTEMIC_IDENTITY_DISPOSITION_CLOSED"
    assert out["sensor_count"] == 177
    assert out["identity_disposition_complete_count"] == 177
    assert out["identity_disposition_coverage_complete"] is True
    assert out["calendar_qualification_candidate_count"] == 90
    assert out["explicit_unknown_or_limited_count"] == 87
    assert out["disposition_counts"] == {
        "CURRENT_REFERENCE_VERIFIED": 85,
        "LEGACY_LINEAGE_ONLY": 2,
        "PROVIDER_ATTESTED_ONLY": 73,
        "PROVIDER_BINDING_UNKNOWN": 12,
        "VERSIONED_CONTRACT_VERIFIED": 5,
    }
    assert out["unknown_is_valid_terminal_identity_disposition"] is True
    assert out["all_provider_symbols_have_canonical_identity"] is False
    assert out["b06_epistemic_closure_complete"] is True
    assert out["b06_all_canonical_identities_verified"] is False
    assert out["calendar_binding_authorized"] is False
    assert out["relational_claims_authorized"] is False
    assert out["productive_authority"] is False
    assert len(str(out["registry_fingerprint_sha256"])) == 64

    rows = out["records"]
    assert isinstance(rows, list)
    limited = [
        row
        for row in rows
        if row["canonical_identity_unknown_or_limited"]
    ]
    assert len(limited) == 87
    assert all(row["eligible_for_calendar_qualification"] is False for row in limited)


def test_unknowns_are_not_promoted_to_temporal_or_relation_authority() -> None:
    out = build_identity_disposition_registry(frontier_v3=_frontier())
    rows = out["records"]
    assert isinstance(rows, list)
    unknown = [
        row
        for row in rows
        if row["identity_disposition"]
        in {"PROVIDER_BINDING_UNKNOWN", "PROVIDER_ATTESTED_ONLY"}
    ]
    assert len(unknown) == 85
    assert all(row["calendar_binding_authorized"] is False for row in unknown)
    assert all(row["relational_claims_authorized"] is False for row in unknown)


def test_rejects_unrecognized_stage_instead_of_guessing() -> None:
    frontier = deepcopy(_frontier())
    records = frontier["records"]
    assert isinstance(records, list)
    records[-1]["resolution_stage"] = "NAME_LOOKS_SIMILAR"

    with pytest.raises(
        SharedB4IdentityDispositionError,
        match="unsupported identity resolution stage",
    ):
        build_identity_disposition_registry(frontier_v3=frontier)


def test_rejects_identity_inference_widening() -> None:
    frontier = deepcopy(_frontier())
    frontier["automatic_identity_inference"] = True

    with pytest.raises(
        SharedB4IdentityDispositionError,
        match="automatic identity inference",
    ):
        build_identity_disposition_registry(frontier_v3=frontier)


def test_rejects_population_drift() -> None:
    frontier = deepcopy(_frontier())
    records = frontier["records"]
    assert isinstance(records, list)
    records.pop()

    with pytest.raises(
        SharedB4IdentityDispositionError,
        match="frontier records invalid",
    ):
        build_identity_disposition_registry(frontier_v3=frontier)
